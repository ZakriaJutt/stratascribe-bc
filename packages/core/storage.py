"""Object keys and object storage (R-13, AD-11).

Keys are built only by ``key()``: ``b/{brokerage_id}/s/{strata_id}/{purpose}/{uuid}``.
No uploaded file name ever appears in a key. Files are streamed by the API;
there are no signed or expiring links. ``ScopedStore`` refuses any key outside
one building's prefix (worker guard, P-5). The local file store is the B1
stand-in for the S3-compatible store; the S3 adapter is not built.
"""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from typing import Protocol

from core import config

PURPOSES = ("audio", "bylaw", "export", "tmp")
_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
KEY_RE = re.compile(rf"^b/(?P<b>{_UUID})/s/(?P<s>{_UUID})/(?P<p>audio|bylaw|export|tmp)/(?P<id>{_UUID})$")
REPO_ROOT = Path(__file__).resolve().parents[2]


class StorageScopeError(PermissionError):
    pass


class InvalidKey(ValueError):
    pass


def key(brokerage_id: uuid.UUID, strata_id: uuid.UUID, purpose: str, object_id: uuid.UUID) -> str:
    if purpose not in PURPOSES:
        raise InvalidKey("unknown purpose")
    for v in (brokerage_id, strata_id, object_id):
        if not isinstance(v, uuid.UUID):
            raise InvalidKey("key parts must be UUIDs")
    return f"b/{brokerage_id}/s/{strata_id}/{purpose}/{object_id}"


def building_prefix(brokerage_id: uuid.UUID, strata_id: uuid.UUID) -> str:
    return f"b/{brokerage_id}/s/{strata_id}/"


def check_key(k: str) -> re.Match[str]:
    m = KEY_RE.match(k)
    if not m:
        raise InvalidKey("malformed object key")
    return m


class ObjectStore(Protocol):
    def write_at(self, k: str, offset: int, data: bytes) -> int: ...
    def put(self, k: str, data: bytes) -> None: ...
    def read(self, k: str, start: int = 0, end: int | None = None) -> bytes: ...
    def size(self, k: str) -> int | None: ...
    def move(self, src: str, dst: str) -> None: ...
    def delete(self, k: str) -> bool: ...
    def list_prefix(self, prefix: str) -> list[str]: ...


class LocalObjectStore:
    def __init__(self, root: str | Path) -> None:
        p = Path(root)
        self.root = p if p.is_absolute() else REPO_ROOT / p
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, k: str) -> Path:
        check_key(k)
        return self.root / k

    def write_at(self, k: str, offset: int, data: bytes) -> int:
        path = self._path(k)
        path.parent.mkdir(parents=True, exist_ok=True)
        current = path.stat().st_size if path.exists() else 0
        if offset != current:
            raise ValueError("offset does not match stored size")
        with path.open("ab") as fh:
            fh.write(data)
        return current + len(data)

    def put(self, k: str, data: bytes) -> None:
        path = self._path(k)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".partial")
        tmp.write_bytes(data)
        os.replace(tmp, path)

    def read(self, k: str, start: int = 0, end: int | None = None) -> bytes:
        with self._path(k).open("rb") as fh:
            fh.seek(start)
            return fh.read() if end is None else fh.read(max(0, end - start + 1))

    def size(self, k: str) -> int | None:
        path = self._path(k)
        return path.stat().st_size if path.exists() else None

    def move(self, src: str, dst: str) -> None:
        d = self._path(dst)
        d.parent.mkdir(parents=True, exist_ok=True)
        os.replace(self._path(src), d)

    def delete(self, k: str) -> bool:
        path = self._path(k)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_prefix(self, prefix: str) -> list[str]:
        base = self.root / prefix
        if not base.exists():
            return []
        return sorted(str(p.relative_to(self.root)) for p in base.rglob("*") if p.is_file())


class ScopedStore:
    """A store limited to one building's prefix; used by workers."""

    def __init__(self, inner: ObjectStore, brokerage_id: uuid.UUID, strata_id: uuid.UUID) -> None:
        self.inner = inner
        self.prefix = building_prefix(brokerage_id, strata_id)

    def _guard(self, k: str) -> str:
        check_key(k)
        if not k.startswith(self.prefix):
            raise StorageScopeError("key outside the job's building")
        return k

    def write_at(self, k: str, offset: int, data: bytes) -> int:
        return self.inner.write_at(self._guard(k), offset, data)

    def put(self, k: str, data: bytes) -> None:
        self.inner.put(self._guard(k), data)

    def read(self, k: str, start: int = 0, end: int | None = None) -> bytes:
        return self.inner.read(self._guard(k), start, end)

    def size(self, k: str) -> int | None:
        return self.inner.size(self._guard(k))

    def move(self, src: str, dst: str) -> None:
        self.inner.move(self._guard(src), self._guard(dst))

    def delete(self, k: str) -> bool:
        return self.inner.delete(self._guard(k))

    def list_prefix(self, prefix: str) -> list[str]:
        if not prefix.startswith(self.prefix):
            raise StorageScopeError("prefix outside the job's building")
        return self.inner.list_prefix(prefix)


_store: ObjectStore | None = None


def store() -> ObjectStore:
    global _store
    if _store is None:
        _store = LocalObjectStore(config.settings().object_store_root)
    return _store


def set_store(s: ObjectStore | None) -> None:
    global _store
    _store = s

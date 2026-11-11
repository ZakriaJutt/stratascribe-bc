"""Object keys and object storage (R-13, AD-11).

Keys are built only by ``key()``: ``b/{brokerage_id}/s/{strata_id}/{purpose}/{uuid}``.
No uploaded file name ever appears in a key. Files are streamed by the API;
there are no signed or expiring links and no public URLs. ``ScopedStore`` refuses
any key outside one building's prefix (worker guard, P-5).

Two stores behind one interface, chosen by ``STORAGE_BACKEND``: the local file
store, and (B2) ``S3ObjectStore`` for any S3-compatible service, locally MinIO.
S3 has no append, so a resumable upload's ``tmp`` object is held as chunk objects
under ``{key}/.chunks/{offset}`` and composed by ``move`` (multipart upload).
``OBJECT_STORE_PREFIX`` (for example ``test/``) namespaces every object so a test
run can delete exactly what it wrote.
"""

from __future__ import annotations

import os
import re
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Protocol

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


CHUNKS = "/.chunks/"
MIN_PART = 5 * 1024 * 1024  # S3 multipart minimum for every part except the last
PART = 8 * 1024 * 1024


class S3ObjectStore:
    """S3 API adapter (MinIO locally). Private bucket; credentials from settings; no presigned URLs."""

    def __init__(self, endpoint_url: str, region: str, bucket: str, access_key_id: str, secret_access_key: str,
                 namespace: str = "", client: Any = None) -> None:
        if client is None:
            import boto3
            from botocore.config import Config

            client = boto3.client(
                "s3", endpoint_url=endpoint_url, region_name=region, aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                              retries={"max_attempts": 3, "mode": "standard"}),
            )
        self.s3: Any = client
        self.bucket = bucket
        self.namespace = namespace

    # -- internal object names (never exposed; logical keys are always checked first)
    def _obj(self, k: str) -> str:
        check_key(k)
        return self.namespace + k

    def _chunk_name(self, k: str, offset: int) -> str:
        return f"{self._obj(k)}{CHUNKS}{offset:016d}"

    def _list(self, prefix: str) -> Iterator[dict[str, Any]]:
        token: str | None = None
        while True:
            kw: dict[str, Any] = {"Bucket": self.bucket, "Prefix": prefix}
            if token:
                kw["ContinuationToken"] = token
            page = self.s3.list_objects_v2(**kw)
            yield from page.get("Contents", [])
            if not page.get("IsTruncated"):
                return
            token = page.get("NextContinuationToken")

    def _chunks(self, k: str) -> list[tuple[int, int, str]]:
        out = []
        for o in self._list(self._obj(k) + CHUNKS):
            name = str(o["Key"])
            out.append((int(name.rsplit("/", 1)[1]), int(o["Size"]), name))
        return sorted(out)

    def _head(self, k: str) -> int | None:
        from botocore.exceptions import ClientError

        try:
            return int(self.s3.head_object(Bucket=self.bucket, Key=self._obj(k))["ContentLength"])
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return None
            raise

    def _get(self, name: str, start: int, end: int) -> bytes:
        body = self.s3.get_object(Bucket=self.bucket, Key=name, Range=f"bytes={start}-{end}")["Body"]
        return bytes(body.read())

    # -- ObjectStore
    def write_at(self, k: str, offset: int, data: bytes) -> int:
        if self._head(k) is not None:
            raise ValueError("object already complete")
        current = sum(size for _, size, _ in self._chunks(k))
        if offset != current:
            raise ValueError("offset does not match stored size")
        if data:
            self.s3.put_object(Bucket=self.bucket, Key=self._chunk_name(k, offset), Body=data)
        return current + len(data)

    def put(self, k: str, data: bytes) -> None:
        self.s3.put_object(Bucket=self.bucket, Key=self._obj(k), Body=data)
        for _, _, name in self._chunks(k):
            self.s3.delete_object(Bucket=self.bucket, Key=name)

    def size(self, k: str) -> int | None:
        whole = self._head(k)
        if whole is not None:
            return whole
        chunks = self._chunks(k)
        return sum(size for _, size, _ in chunks) if chunks else None

    def read(self, k: str, start: int = 0, end: int | None = None) -> bytes:
        whole = self._head(k)
        if whole is not None:
            last = whole - 1 if end is None else min(end, whole - 1)
            return b"" if whole == 0 or start > last else self._get(self._obj(k), start, last)
        chunks = self._chunks(k)
        if not chunks:
            raise FileNotFoundError("no such object")
        total = sum(size for _, size, _ in chunks)
        last = total - 1 if end is None else min(end, total - 1)
        out = bytearray()
        for off, size, name in chunks:
            lo, hi = max(start, off), min(last, off + size - 1)
            if lo <= hi:
                out += self._get(name, lo - off, hi - off)
        return bytes(out)

    def move(self, src: str, dst: str) -> None:
        dst_name = self._obj(dst)
        if self._head(src) is not None:
            self.s3.copy_object(Bucket=self.bucket, Key=dst_name,
                                CopySource={"Bucket": self.bucket, "Key": self._obj(src)})
            self.s3.delete_object(Bucket=self.bucket, Key=self._obj(src))
            return
        chunks = self._chunks(src)
        if not chunks:
            raise FileNotFoundError("no such object")
        total = sum(size for _, size, _ in chunks)
        if total < MIN_PART:
            self.s3.put_object(Bucket=self.bucket, Key=dst_name, Body=self.read(src))
        else:
            up = self.s3.create_multipart_upload(Bucket=self.bucket, Key=dst_name)["UploadId"]
            try:
                parts: list[dict[str, Any]] = []
                buf = bytearray()

                def flush() -> None:
                    n = len(parts) + 1
                    r = self.s3.upload_part(Bucket=self.bucket, Key=dst_name, UploadId=up, PartNumber=n,
                                            Body=bytes(buf))
                    parts.append({"ETag": r["ETag"], "PartNumber": n})
                    buf.clear()

                for _, size, name in chunks:
                    pos = 0
                    while pos < size:
                        step = min(PART, size - pos)
                        buf += self._get(name, pos, pos + step - 1)
                        pos += step
                        if len(buf) >= PART:
                            flush()
                if buf or not parts:
                    flush()
                self.s3.complete_multipart_upload(Bucket=self.bucket, Key=dst_name, UploadId=up,
                                                  MultipartUpload={"Parts": parts})
            except Exception:
                self.s3.abort_multipart_upload(Bucket=self.bucket, Key=dst_name, UploadId=up)
                raise
        for _, _, name in chunks:
            self.s3.delete_object(Bucket=self.bucket, Key=name)

    def delete(self, k: str) -> bool:
        removed = False
        if self._head(k) is not None:
            self.s3.delete_object(Bucket=self.bucket, Key=self._obj(k))
            removed = True
        for _, _, name in self._chunks(k):
            self.s3.delete_object(Bucket=self.bucket, Key=name)
            removed = True
        return removed

    def list_prefix(self, prefix: str) -> list[str]:
        keys = set()
        for o in self._list(self.namespace + prefix):
            logical = str(o["Key"])[len(self.namespace):].split(CHUNKS, 1)[0]
            keys.add(logical)
        return sorted(keys)

    def ready(self) -> bool:
        self.s3.head_bucket(Bucket=self.bucket)
        return True


_store: ObjectStore | None = None


def from_settings(namespace: str | None = None) -> ObjectStore:
    s = config.settings()
    if s.storage_backend == "s3":
        return S3ObjectStore(s.s3_endpoint_url, s.s3_region, s.s3_bucket, s.s3_access_key_id,
                             s.s3_secret_access_key, s.object_store_prefix if namespace is None else namespace)
    return LocalObjectStore(s.object_store_root)


def store() -> ObjectStore:
    global _store
    if _store is None:
        _store = from_settings()
    return _store


def set_store(s: ObjectStore | None) -> None:
    global _store
    _store = s

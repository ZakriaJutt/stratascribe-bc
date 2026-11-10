"""Static boundary checks (T-2.1.1, U-16, U-8, R-03, R-04, R-05, R-07)."""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = [p for d in ("packages", "apps") for p in (ROOT / d).rglob("*.py") if ".venv" not in p.parts]


def writers_of_computed_result(files: list[Path]) -> list[str]:
    """U-16: any store to ``computed_result`` outside packages/rules (models may declare the column)."""
    bad = []
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith("packages/rules/") or rel == "packages/core/models.py" or "/migrations/" in rel:
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            hit = (
                (isinstance(node, ast.Attribute) and node.attr == "computed_result" and isinstance(node.ctx, ast.Store))
                or (isinstance(node, ast.keyword) and node.arg == "computed_result")
                or (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "setattr"
                    and len(node.args) > 1 and isinstance(node.args[1], ast.Constant)
                    and node.args[1].value == "computed_result")
                or (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and "computed_result" in node.value and ("SET" in node.value or "=" in node.value))
            )
            if hit:
                bad.append(f"{rel}:{getattr(node, 'lineno', '?')}")
    return bad


def test_u16_only_rules_package_writes_computed_result(tmp_path: Path) -> None:
    assert writers_of_computed_result(SOURCES) == []
    seeded = ROOT / "packages" / "core" / "_u16_seeded_example.py"
    try:
        seeded.write_text("def f(item, s):\n    item.computed_result = 'carried'\n"
                          "    s.execute('UPDATE minute_items SET computed_result = 1')\n")
        found = writers_of_computed_result([*SOURCES, seeded])
        assert found == ["packages/core/_u16_seeded_example.py:2", "packages/core/_u16_seeded_example.py:3"]
    finally:
        seeded.unlink()


def _imports(path: Path) -> set[str]:
    mods: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            mods.add(node.module.split(".")[0])
    return mods


def test_import_boundaries() -> None:
    for path in SOURCES:
        rel = path.relative_to(ROOT).as_posix()
        mods = _imports(path)
        if rel.startswith("apps/worker/"):
            assert "api" not in mods and "fastapi" not in mods and "starlette" not in mods, rel
        if rel.startswith("apps/api/"):
            assert "worker" not in mods, rel
        if rel.startswith("packages/"):
            assert not mods & {"fastapi", "starlette", "uvicorn", "api", "worker"}, rel
        if rel.startswith("packages/rules/"):
            assert mods <= {"__future__", "dataclasses", "enum", "typing", "rules"}, (rel, mods)


def test_single_config_loader_and_no_raw_sessions() -> None:
    for path in SOURCES:
        rel = path.relative_to(ROOT).as_posix()
        src = path.read_text()
        if rel != "packages/core/config.py":
            assert "os.environ" not in src and "getenv(" not in src, f"second config loader in {rel}"
        if rel not in ("packages/core/db.py", "packages/core/devdata.py") and "/migrations/" not in rel:
            assert "create_engine(" not in src and "sessionmaker(" not in src, f"raw session in {rel}"
            assert not re.search(r"(?<![A-Za-z_])Session\(", src), f"raw session in {rel}"


def test_u8_storage_keys_built_only_by_core_storage() -> None:
    import uuid

    from core import storage

    b, s, o = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    k = storage.key(b, s, "audio", o)
    assert k == f"b/{b}/s/{s}/audio/{o}" and storage.KEY_RE.match(k)
    for bad in (lambda: storage.key(b, s, "photos", o), lambda: storage.key(b, s, "audio", "x.m4a")):  # type: ignore
        try:
            bad()
        except storage.InvalidKey:
            continue
        raise AssertionError("invalid key accepted")
    for path in SOURCES:
        rel = path.relative_to(ROOT).as_posix()
        if rel == "packages/core/storage.py":
            continue
        assert 'f"b/{' not in path.read_text(), f"object key built by hand in {rel}"

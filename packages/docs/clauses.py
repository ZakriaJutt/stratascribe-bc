"""Clause splitter for bylaw text (T-4.1.1 subtask c, plain-text input only in B1).

Recognises numbered bylaws ("3 Use of property"), subsections ("(1) ...") and
paragraphs ("(a) ..."), producing clause numbers such as "3(4)(b)".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

PARSER_VERSION = "clause-split-0.1"

_TOP = re.compile(r"^(?:Bylaw\s+|Section\s+)?(\d{1,3})\.?\s+(\S.*)$")
_SUB = re.compile(r"^\((\d{1,2})\)\s+(\S.*)$")
_PARA = re.compile(r"^\(([a-z])\)\s+(\S.*)$")


@dataclass(frozen=True)
class Clause:
    clause_number: str
    heading: str | None
    body_text: str
    position: int


def split_clauses(text: str) -> list[Clause]:
    clauses: list[Clause] = []
    top: str | None = None
    heading: str | None = None
    sub: str | None = None
    current_no: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf
        body = " ".join(" ".join(buf).split())
        if current_no is not None and body:
            clauses.append(Clause(current_no, heading, body, len(clauses) + 1))
        buf = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if m := _TOP.match(line):
            flush()
            top, heading, sub = m.group(1), m.group(2).strip(), None
            current_no = None
            continue
        if top is not None and (m := _SUB.match(line)):
            flush()
            sub = m.group(1)
            current_no = f"{top}({sub})"
            buf = [m.group(2)]
            continue
        if top is not None and sub is not None and (m := _PARA.match(line)):
            flush()
            current_no = f"{top}({sub})({m.group(1)})"
            buf = [m.group(2)]
            continue
        if current_no is None and top is not None:
            current_no = top
        buf.append(line)
    flush()
    return clauses

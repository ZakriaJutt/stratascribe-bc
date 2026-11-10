"""Citation validator (U-7), extraction validation and fallback, clause splitter, audio sniffing."""

from __future__ import annotations

import json
import uuid
from typing import Any

from ai.answer import answer, validate_citations
from ai.extraction import extract_items
from ai.llm import FakeLlmClient, InvalidJsonLlm
from ai.search import ClauseHit
from docs.clauses import split_clauses
from docs.filetypes import extension_matches, sniff_audio

CLAUSE = ClauseHit(uuid.uuid4(), uuid.uuid4(), "2(1)", "An owner may keep no more than two dogs or two cats.",
                   None, None, 1.0)


def test_u7_quote_one_character_off_is_rejected() -> None:
    allowed = {CLAUSE.clause_id: CLAUSE}
    exact = [{"clause_id": str(CLAUSE.clause_id), "quote": "no more than two dogs"}]
    assert validate_citations(exact, allowed)
    off = [{"clause_id": str(CLAUSE.clause_id), "quote": "no more than two dogz"}]
    assert validate_citations(off, allowed) is None
    other = [{"clause_id": str(uuid.uuid4()), "quote": "no more than two dogs"}]
    assert validate_citations(other, allowed) is None
    mixed = exact + off  # all-or-nothing
    assert validate_citations(mixed, allowed) is None
    assert validate_citations([], allowed) is None


class Echo:
    model_id = "echo"

    def __init__(self, out: dict[str, Any]) -> None:
        self.out = out

    def complete_json(self, task: str, payload: dict[str, Any]) -> str:
        return json.dumps(self.out)


def test_answer_without_citation_is_refused() -> None:
    r = answer("dogs?", [CLAUSE], Echo({"answer": "Two dogs.", "citations": []}))
    assert r.outcome == "refused" and r.closest == [CLAUSE]
    r = answer("dogs?", [], FakeLlmClient())
    assert r.outcome == "refused"


def test_extraction_rejects_unknown_segment_ids_and_falls_back() -> None:
    segs = [{"id": "s1", "speaker_label": "Speaker 1", "text": "I move that the budget be approved."},
            {"id": "s2", "speaker_label": "Speaker 2", "text": "Seconded."},
            {"id": "s3", "speaker_label": "Speaker 1", "text": "Carried."}]
    items = extract_items(segs, FakeLlmClient())
    assert items is not None and items[0].item_type == "motion" and items[0].spoken_outcome == "carried"
    bad = Echo({"items": [{"item_type": "motion", "text": "x", "segment_ids": ["nope"]}]})
    assert extract_items(segs, bad) is None
    assert extract_items(segs, InvalidJsonLlm()) is None


def test_clause_splitter_numbers() -> None:
    text = "3 Use of property\n(1) First rule.\n(2) Second rule:\n(a) part a;\n(b) part b.\n4 Next\nPlain body."
    got = [(c.clause_number, c.body_text) for c in split_clauses(text)]
    assert got == [("3(1)", "First rule."), ("3(2)", "Second rule:"), ("3(2)(a)", "part a;"),
                   ("3(2)(b)", "part b."), ("4", "Plain body.")]


def test_audio_magic_bytes() -> None:
    assert sniff_audio(b"RIFF\x00\x00\x00\x00WAVEfmt ") == "wav"
    assert sniff_audio(b"\x00\x00\x00\x20ftypM4A \x00\x00") == "mp4"
    assert sniff_audio(b"MZ\x90\x00") is None
    assert not extension_matches(".m4a", b"MZ\x90\x00")
    assert extension_matches(".flac", b"fLaC\x00\x00")

"""Language-model interface with JSON output, plus deterministic fakes.

Real transcript text must never reach a hosted endpoint until AD-5 is decided
with the provider's own terms (CLAUDE.md "Sensitive data").
"""

from __future__ import annotations

import json
import re
from typing import Any, Protocol

STOPWORDS = frozenset(
    "a an and are as at be by can do does for from has have how i if in is it may must of on or the this to "
    "what when where which who will with our my we an any be can council owner owners strata".split()
)


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", text.lower()) if w not in STOPWORDS and len(w) > 2}


class LlmClient(Protocol):
    model_id: str

    def complete_json(self, task: str, payload: dict[str, Any]) -> str: ...


class FakeLlmClient:
    """Deterministic stand-in. Extraction: one item per spoken motion. Answers: quote the best sentence."""

    model_id = "fake-llm-0"

    def complete_json(self, task: str, payload: dict[str, Any]) -> str:
        if task == "extract_minutes":
            return json.dumps(self._extract(payload))
        if task == "answer_question":
            return json.dumps(self._answer(payload))
        raise ValueError("unknown task")

    def _extract(self, payload: dict[str, Any]) -> dict[str, Any]:
        segs: list[dict[str, Any]] = payload["segments"]
        items: list[dict[str, Any]] = []
        for i, seg in enumerate(segs):
            t = seg["text"].lower()
            if t.startswith("i call the meeting to order"):
                items.append({"item_type": "call_to_order", "text": seg["text"], "segment_ids": [seg["id"]]})
            elif t.startswith("i move that"):
                window = segs[i : i + 3]
                spoken = next(
                    (w["text"] for w in window if "carried" in w["text"].lower() or "defeated" in w["text"].lower()),
                    None,
                )
                items.append(
                    {
                        "item_type": "motion",
                        "text": seg["text"][len("I move that ") :].rstrip("."),
                        "mover": seg["speaker_label"],
                        "seconder": window[1]["speaker_label"] if len(window) > 1 else None,
                        "spoken_outcome": ("carried" if spoken and "carried" in spoken.lower() else
                                           "defeated" if spoken else None),
                        "spoken_counts": _counts(spoken),
                        "segment_ids": [w["id"] for w in window],
                    }
                )
            elif "adjourned" in t:
                items.append({"item_type": "adjournment", "text": seg["text"], "segment_ids": [seg["id"]]})
        return {"items": items}

    def _answer(self, payload: dict[str, Any]) -> dict[str, Any]:
        q = words(payload["question"])
        best: tuple[int, dict[str, Any], str] | None = None
        for clause in payload["clauses"]:
            for sentence in re.split(r"(?<=[.])\s+", clause["text"]):
                score = len(q & words(sentence))
                if score >= 2 and (best is None or score > best[0]):
                    best = (score, clause, sentence.strip())
        if best is None:
            return {"answer": None, "citations": []}
        _, clause, sentence = best
        return {
            "answer": f"Bylaw {clause['number']} says: “{sentence}”",
            "citations": [{"clause_id": clause["id"], "quote": sentence}],
        }


def _counts(spoken: str | None) -> dict[str, int] | None:
    if not spoken:
        return None
    nums = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7}
    m = re.search(r"(\w+) in favour, (\w+) against", spoken.lower())
    if not m or m.group(1) not in nums or m.group(2) not in nums:
        return None
    return {"for": nums[m.group(1)], "against": nums[m.group(2)]}


class InvalidJsonLlm:
    model_id = "fake-invalid"

    def complete_json(self, task: str, payload: dict[str, Any]) -> str:
        return "{not json"


class AlteringQuoteLlm(FakeLlmClient):
    """Returns a quote that differs from the clause by one character (U-7)."""

    model_id = "fake-altering"

    def _answer(self, payload: dict[str, Any]) -> dict[str, Any]:
        out = super()._answer(payload)
        for c in out["citations"]:
            q = c["quote"]
            c["quote"] = q[:-1] + ("!" if not q.endswith("!") else ".")
        return out

"""Minutes extraction with schema-validated output (T-3.2.2, MH-05).

The model proposes items with evidence segment IDs. Spoken outcomes and counts
are kept only as suggestions: nothing here sets an outcome or a count. Output
that fails validation twice yields ``None`` and the caller shows an empty
template.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ai.llm import LlmClient

ItemType = Literal["attendance", "quorum", "call_to_order", "motion", "discussion", "adjournment", "other"]


class ExtractedItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_type: ItemType
    text: str = Field(max_length=4000)
    mover: str | None = None
    seconder: str | None = None
    spoken_outcome: Literal["carried", "defeated"] | None = None
    spoken_counts: dict[str, int] | None = None
    segment_ids: list[str] = Field(min_length=1)
    sensitive: bool = False


class ExtractionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[ExtractedItem]


def _parse(raw: str, valid_ids: set[str]) -> list[ExtractedItem] | None:
    try:
        out = ExtractionOutput.model_validate(json.loads(raw))
    except (ValueError, ValidationError):
        return None
    for item in out.items:
        if not set(item.segment_ids) <= valid_ids:
            return None  # evidence must point at real segments
    return out.items


def extract_items(segments: list[dict[str, Any]], llm: LlmClient, attempts: int = 2) -> list[ExtractedItem] | None:
    valid_ids = {s["id"] for s in segments}
    for _ in range(attempts):
        items = _parse(llm.complete_json("extract_minutes", {"segments": segments}), valid_ids)
        if items is not None:
            return items
    return None

"""Transcriber interface (TRD "AI functions"). Real Whisper worker is not built in B1 (T-3.2.1 blocked)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Segment:
    start_ms: int
    end_ms: int
    speaker_label: str
    text: str


class Transcriber(Protocol):
    model_id: str
    params_hash: str

    def transcribe(self, audio: bytes) -> list[Segment]: ...


# Synthetic council meeting (invented names and building; no real people).
FAKE_SCRIPT: tuple[tuple[str, str], ...] = (
    ("Speaker 1", "I call the meeting to order at seven p.m. All seven council members are present."),
    ("Speaker 2", "I move that the minutes of the previous council meeting be approved as circulated."),
    ("Speaker 3", "Seconded."),
    ("Speaker 1", "All in favour? Opposed? That is carried."),
    ("Speaker 4", "I move that council approve the roof repair quote of the lowest bidder."),
    ("Speaker 2", "I second that."),
    ("Speaker 1", "Five in favour, two against. Carried."),
    ("Speaker 1", "There being no further business, the meeting is adjourned."),
)


class FakeTranscriber:
    model_id = "fake-asr-0"
    params_hash = "fake-params-0"

    def __init__(self, fail_times: int = 0) -> None:
        self.fail_times = fail_times
        self.calls = 0

    def transcribe(self, audio: bytes) -> list[Segment]:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("fake transcription failure")
        return [
            Segment(i * 10_000, i * 10_000 + 9_000, speaker, text) for i, (speaker, text) in enumerate(FAKE_SCRIPT)
        ]

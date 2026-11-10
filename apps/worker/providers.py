"""Provider selection from configuration. Only fakes exist in B1 (AD-4, AD-5 undecided)."""

from __future__ import annotations

from ai.llm import FakeLlmClient, LlmClient
from ai.transcription import FakeTranscriber, Transcriber
from core import config


def transcriber() -> Transcriber:
    if config.settings().asr_provider == "fake":
        return FakeTranscriber()
    raise SystemExit("no real transcription provider in B1")  # pragma: no cover


def llm() -> LlmClient:
    if config.settings().llm_provider == "fake":
        return FakeLlmClient()
    raise SystemExit("no real language-model provider in B1")  # pragma: no cover

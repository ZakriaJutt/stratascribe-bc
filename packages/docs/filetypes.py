"""Accepted audio types by magic bytes (TRD "File handling"). Extension and content must agree."""

from __future__ import annotations

AUDIO_EXTENSIONS = {
    ".m4a": "mp4",
    ".mp4": "mp4",
    ".mp3": "mp3",
    ".wav": "wav",
    ".flac": "flac",
    ".ogg": "ogg",
    ".opus": "ogg",
    ".webm": "webm",
}
MAX_MEETING_AUDIO_BYTES = 2_500_000_000  # 2.5 GB per meeting [TRD File handling]
MAX_PARTS = 10


def sniff_audio(head: bytes) -> str | None:
    if len(head) >= 12 and head[4:8] == b"ftyp":
        return "mp4"
    if head[:3] == b"ID3" or (len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0):
        return "mp3"
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "wav"
    if head[:4] == b"fLaC":
        return "flac"
    if head[:4] == b"OggS":
        return "ogg"
    if head[:4] == b"\x1a\x45\xdf\xa3":
        return "webm"
    return None


def extension_matches(filename_ext: str, head: bytes) -> bool:
    expected = AUDIO_EXTENSIONS.get(filename_ext.lower())
    return expected is not None and sniff_audio(head) == expected

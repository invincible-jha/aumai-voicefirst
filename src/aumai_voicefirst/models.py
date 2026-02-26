"""Pydantic models for aumai-voicefirst."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

__all__ = [
    "AudioFormat",
    "VoiceConfig",
    "Utterance",
    "VoiceSession",
    "TextToSpeechConfig",
]


class AudioFormat(str, Enum):
    """Supported audio container formats."""

    wav = "wav"
    mp3 = "mp3"
    ogg = "ogg"
    flac = "flac"


class VoiceConfig(BaseModel):
    """Configuration for a voice session."""

    language: str = Field(description="BCP-47 language code, e.g. 'en', 'hi'.")
    sample_rate: int = Field(default=16000, ge=8000, le=48000)
    channels: int = Field(default=1, ge=1, le=2)
    format: AudioFormat = AudioFormat.wav


class Utterance(BaseModel):
    """A single recognised speech utterance."""

    text: str
    language: str
    start_ms: float = Field(ge=0.0, description="Start time in milliseconds.")
    end_ms: float = Field(ge=0.0, description="End time in milliseconds.")
    confidence: float = Field(ge=0.0, le=1.0)


class VoiceSession(BaseModel):
    """An active or completed voice interaction session."""

    session_id: str
    config: VoiceConfig
    utterances: list[Utterance] = Field(default_factory=list)
    state: Literal["active", "paused", "completed", "error"] = "active"


class TextToSpeechConfig(BaseModel):
    """Configuration for text-to-speech synthesis."""

    voice_id: str = Field(description="Provider-specific voice identifier.")
    speed: float = Field(default=1.0, ge=0.25, le=4.0, description="Playback speed multiplier.")
    pitch: float = Field(default=0.0, ge=-20.0, le=20.0, description="Pitch shift in semitones.")

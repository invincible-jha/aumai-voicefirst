"""Shared test fixtures for aumai-voicefirst."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aumai_voicefirst.core import VoiceRouter, VoiceSessionManager
from aumai_voicefirst.models import AudioFormat, Utterance, VoiceConfig, VoiceSession


@pytest.fixture()
def manager() -> VoiceSessionManager:
    """A fresh VoiceSessionManager instance."""
    return VoiceSessionManager()


@pytest.fixture()
def router() -> VoiceRouter:
    """A fresh VoiceRouter instance."""
    return VoiceRouter()


@pytest.fixture()
def english_config() -> VoiceConfig:
    """Default English voice configuration."""
    return VoiceConfig(language="en", sample_rate=16000, format=AudioFormat.wav)


@pytest.fixture()
def hindi_config() -> VoiceConfig:
    """Hindi voice configuration."""
    return VoiceConfig(language="hi", sample_rate=22050, format=AudioFormat.flac)


@pytest.fixture()
def english_utterance() -> Utterance:
    """A single English utterance."""
    return Utterance(
        text="Hello, how are you?",
        language="en",
        start_ms=0.0,
        end_ms=1500.0,
        confidence=0.95,
    )


@pytest.fixture()
def hindi_utterance() -> Utterance:
    """A single Hindi utterance."""
    return Utterance(
        text="नमस्ते, आप कैसे हैं?",
        language="hi",
        start_ms=500.0,
        end_ms=2200.0,
        confidence=0.88,
    )


@pytest.fixture()
def active_session(
    manager: VoiceSessionManager,
    english_config: VoiceConfig,
) -> VoiceSession:
    """An active VoiceSession with English config."""
    return manager.create_session(english_config)


@pytest.fixture()
def session_json_file(
    active_session: VoiceSession,
    english_utterance: Utterance,
    manager: VoiceSessionManager,
    tmp_path: Path,
) -> Path:
    """A session JSON file containing one utterance."""
    manager.add_utterance(active_session, english_utterance)
    file = tmp_path / "session.json"
    file.write_text(active_session.model_dump_json(indent=2), encoding="utf-8")
    return file


@pytest.fixture()
def empty_session_json_file(active_session: VoiceSession, tmp_path: Path) -> Path:
    """A session JSON file with no utterances."""
    file = tmp_path / "empty_session.json"
    file.write_text(active_session.model_dump_json(indent=2), encoding="utf-8")
    return file

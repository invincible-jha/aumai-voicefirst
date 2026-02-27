"""Comprehensive tests for aumai-voicefirst core module."""

from __future__ import annotations

import pytest

from aumai_voicefirst.core import VoiceRouter, VoiceSessionManager
from aumai_voicefirst.models import (
    AudioFormat,
    TextToSpeechConfig,
    Utterance,
    VoiceConfig,
    VoiceSession,
)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestVoiceConfigModel:
    def test_default_sample_rate(self) -> None:
        config = VoiceConfig(language="en")
        assert config.sample_rate == 16000

    def test_default_channels(self) -> None:
        config = VoiceConfig(language="en")
        assert config.channels == 1

    def test_default_format(self) -> None:
        config = VoiceConfig(language="en")
        assert config.format == AudioFormat.wav

    def test_sample_rate_lower_bound(self) -> None:
        with pytest.raises(Exception):
            VoiceConfig(language="en", sample_rate=7999)

    def test_sample_rate_upper_bound(self) -> None:
        with pytest.raises(Exception):
            VoiceConfig(language="en", sample_rate=48001)

    def test_channels_lower_bound(self) -> None:
        with pytest.raises(Exception):
            VoiceConfig(language="en", channels=0)

    def test_channels_upper_bound(self) -> None:
        with pytest.raises(Exception):
            VoiceConfig(language="en", channels=3)

    def test_valid_formats(self) -> None:
        for fmt in ("wav", "mp3", "ogg", "flac"):
            config = VoiceConfig(language="en", format=AudioFormat(fmt))
            assert config.format.value == fmt


class TestUtteranceModel:
    def test_utterance_fields(self, english_utterance: Utterance) -> None:
        assert english_utterance.text == "Hello, how are you?"
        assert english_utterance.language == "en"
        assert english_utterance.confidence == 0.95

    def test_confidence_upper_bound(self) -> None:
        with pytest.raises(Exception):
            Utterance(text="hi", language="en", start_ms=0.0, end_ms=1.0, confidence=1.1)

    def test_confidence_lower_bound(self) -> None:
        with pytest.raises(Exception):
            Utterance(text="hi", language="en", start_ms=0.0, end_ms=1.0, confidence=-0.1)

    def test_start_ms_non_negative(self) -> None:
        with pytest.raises(Exception):
            Utterance(text="hi", language="en", start_ms=-1.0, end_ms=1.0, confidence=0.9)


class TestVoiceSessionModel:
    def test_default_state_is_active(self, active_session: VoiceSession) -> None:
        assert active_session.state == "active"

    def test_default_utterances_empty(self, active_session: VoiceSession) -> None:
        assert active_session.utterances == []

    def test_session_id_is_string(self, active_session: VoiceSession) -> None:
        assert isinstance(active_session.session_id, str)
        assert len(active_session.session_id) > 0


class TestTextToSpeechConfigModel:
    def test_default_speed(self) -> None:
        tts = TextToSpeechConfig(voice_id="voice-01")
        assert tts.speed == 1.0

    def test_default_pitch(self) -> None:
        tts = TextToSpeechConfig(voice_id="voice-01")
        assert tts.pitch == 0.0

    def test_speed_lower_bound(self) -> None:
        with pytest.raises(Exception):
            TextToSpeechConfig(voice_id="v", speed=0.24)

    def test_speed_upper_bound(self) -> None:
        with pytest.raises(Exception):
            TextToSpeechConfig(voice_id="v", speed=4.1)

    def test_pitch_bounds(self) -> None:
        with pytest.raises(Exception):
            TextToSpeechConfig(voice_id="v", pitch=-21.0)
        with pytest.raises(Exception):
            TextToSpeechConfig(voice_id="v", pitch=21.0)


# ---------------------------------------------------------------------------
# VoiceSessionManager tests
# ---------------------------------------------------------------------------


class TestVoiceSessionManager:
    def test_create_session_returns_session(
        self, manager: VoiceSessionManager, english_config: VoiceConfig
    ) -> None:
        session = manager.create_session(english_config)
        assert isinstance(session, VoiceSession)

    def test_create_session_is_active(
        self, manager: VoiceSessionManager, english_config: VoiceConfig
    ) -> None:
        session = manager.create_session(english_config)
        assert session.state == "active"

    def test_create_session_generates_unique_ids(
        self, manager: VoiceSessionManager, english_config: VoiceConfig
    ) -> None:
        s1 = manager.create_session(english_config)
        s2 = manager.create_session(english_config)
        assert s1.session_id != s2.session_id

    def test_get_session_by_id(
        self, manager: VoiceSessionManager, active_session: VoiceSession
    ) -> None:
        retrieved = manager.get_session(active_session.session_id)
        assert retrieved.session_id == active_session.session_id

    def test_get_session_raises_for_missing(
        self, manager: VoiceSessionManager
    ) -> None:
        with pytest.raises(KeyError):
            manager.get_session("nonexistent-session-id")

    def test_add_utterance_to_active_session(
        self,
        manager: VoiceSessionManager,
        active_session: VoiceSession,
        english_utterance: Utterance,
    ) -> None:
        manager.add_utterance(active_session, english_utterance)
        assert len(active_session.utterances) == 1

    def test_add_utterance_appends_in_order(
        self,
        manager: VoiceSessionManager,
        active_session: VoiceSession,
    ) -> None:
        u1 = Utterance(text="first", language="en", start_ms=0.0, end_ms=500.0, confidence=0.9)
        u2 = Utterance(text="second", language="en", start_ms=600.0, end_ms=1200.0, confidence=0.9)
        manager.add_utterance(active_session, u1)
        manager.add_utterance(active_session, u2)
        assert len(active_session.utterances) == 2

    def test_add_utterance_to_paused_session(
        self,
        manager: VoiceSessionManager,
        english_config: VoiceConfig,
        english_utterance: Utterance,
    ) -> None:
        session = manager.create_session(english_config)
        session.state = "paused"
        manager.add_utterance(session, english_utterance)  # Should not raise
        assert len(session.utterances) == 1

    def test_add_utterance_to_completed_session_raises(
        self,
        manager: VoiceSessionManager,
        english_config: VoiceConfig,
        english_utterance: Utterance,
    ) -> None:
        session = manager.create_session(english_config)
        session.state = "completed"
        with pytest.raises(ValueError, match="completed"):
            manager.add_utterance(session, english_utterance)

    def test_add_utterance_to_error_session_raises(
        self,
        manager: VoiceSessionManager,
        english_config: VoiceConfig,
        english_utterance: Utterance,
    ) -> None:
        session = manager.create_session(english_config)
        session.state = "error"
        with pytest.raises(ValueError):
            manager.add_utterance(session, english_utterance)

    def test_get_transcript_empty_session(
        self, manager: VoiceSessionManager, active_session: VoiceSession
    ) -> None:
        transcript = manager.get_transcript(active_session)
        assert transcript == ""

    def test_get_transcript_single_utterance(
        self,
        manager: VoiceSessionManager,
        active_session: VoiceSession,
        english_utterance: Utterance,
    ) -> None:
        manager.add_utterance(active_session, english_utterance)
        transcript = manager.get_transcript(active_session)
        assert "Hello, how are you?" in transcript

    def test_get_transcript_multiple_utterances_ordered_by_start(
        self,
        manager: VoiceSessionManager,
        active_session: VoiceSession,
    ) -> None:
        u2 = Utterance(text="second", language="en", start_ms=1000.0, end_ms=2000.0, confidence=0.9)
        u1 = Utterance(text="first", language="en", start_ms=0.0, end_ms=900.0, confidence=0.9)
        # Add out of order
        manager.add_utterance(active_session, u2)
        manager.add_utterance(active_session, u1)
        transcript = manager.get_transcript(active_session)
        lines = transcript.split("\n")
        assert lines[0] == "first"
        assert lines[1] == "second"

    def test_get_transcript_newline_separated(
        self,
        manager: VoiceSessionManager,
        active_session: VoiceSession,
    ) -> None:
        u1 = Utterance(text="line one", language="en", start_ms=0.0, end_ms=500.0, confidence=0.9)
        u2 = Utterance(text="line two", language="en", start_ms=600.0, end_ms=1200.0, confidence=0.9)
        manager.add_utterance(active_session, u1)
        manager.add_utterance(active_session, u2)
        transcript = manager.get_transcript(active_session)
        assert transcript == "line one\nline two"


# ---------------------------------------------------------------------------
# VoiceRouter tests
# ---------------------------------------------------------------------------


class TestVoiceRouter:
    def _make_utterance(self, language: str) -> Utterance:
        return Utterance(
            text="test",
            language=language,
            start_ms=0.0,
            end_ms=1000.0,
            confidence=0.9,
        )

    def test_routes_hindi_to_indic(self, router: VoiceRouter) -> None:
        utterance = self._make_utterance("hi")
        assert router.route(utterance) == "handler.indic"

    def test_routes_bengali_to_indic(self, router: VoiceRouter) -> None:
        assert router.route(self._make_utterance("bn")) == "handler.indic"

    def test_routes_tamil_to_indic(self, router: VoiceRouter) -> None:
        assert router.route(self._make_utterance("ta")) == "handler.indic"

    def test_routes_chinese_to_cjk(self, router: VoiceRouter) -> None:
        assert router.route(self._make_utterance("zh")) == "handler.cjk"

    def test_routes_japanese_to_cjk(self, router: VoiceRouter) -> None:
        assert router.route(self._make_utterance("ja")) == "handler.cjk"

    def test_routes_korean_to_cjk(self, router: VoiceRouter) -> None:
        assert router.route(self._make_utterance("ko")) == "handler.cjk"

    def test_routes_arabic_to_arabic(self, router: VoiceRouter) -> None:
        assert router.route(self._make_utterance("ar")) == "handler.arabic"

    def test_routes_persian_to_arabic(self, router: VoiceRouter) -> None:
        assert router.route(self._make_utterance("fa")) == "handler.arabic"

    def test_routes_english_to_default(self, router: VoiceRouter) -> None:
        assert router.route(self._make_utterance("en")) == "handler.default"

    def test_routes_spanish_to_default(self, router: VoiceRouter) -> None:
        assert router.route(self._make_utterance("es")) == "handler.default"

    def test_strips_region_subtag_before_routing(self, router: VoiceRouter) -> None:
        # "hi-IN" should still route to indic
        assert router.route(self._make_utterance("hi-IN")) == "handler.indic"

    def test_strips_region_subtag_for_default(self, router: VoiceRouter) -> None:
        assert router.route(self._make_utterance("en-US")) == "handler.default"

    def test_all_indic_languages_route_to_indic(self, router: VoiceRouter) -> None:
        indic_langs = {
            "hi", "bn", "te", "ta", "mr", "gu", "kn", "ml", "pa",
            "or", "as", "sa", "si", "ne", "kok", "mai", "doi",
            "mni", "sat", "bo",
        }
        for lang in indic_langs:
            result = router.route(self._make_utterance(lang))
            assert result == "handler.indic", f"Expected indic handler for {lang}"

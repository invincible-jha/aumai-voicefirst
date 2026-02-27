"""Comprehensive CLI tests for aumai-voicefirst."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from aumai_voicefirst.cli import main


def _fresh_runner() -> CliRunner:
    """Return a CliRunner without mix_stderr (Click 8.2 compatible)."""
    return CliRunner()


class TestCLIVersion:
    def test_version_flag(self) -> None:
        result = _fresh_runner().invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help_flag(self) -> None:
        result = _fresh_runner().invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "VoiceFirst" in result.output or "voice" in result.output.lower()


class TestSessionCommand:
    def test_session_default_language(self) -> None:
        result = _fresh_runner().invoke(main, ["session"])
        assert result.exit_code == 0
        assert "Session ID:" in result.output

    def test_session_prints_language(self) -> None:
        result = _fresh_runner().invoke(main, ["session", "--language", "hi"])
        assert result.exit_code == 0
        assert "hi" in result.output

    def test_session_prints_format(self) -> None:
        result = _fresh_runner().invoke(main, ["session", "--format", "mp3"])
        assert result.exit_code == 0
        assert "mp3" in result.output

    def test_session_prints_sample_rate(self) -> None:
        result = _fresh_runner().invoke(main, ["session", "--sample-rate", "22050"])
        assert result.exit_code == 0
        assert "22050" in result.output

    def test_session_all_audio_formats(self) -> None:
        for fmt in ("wav", "mp3", "ogg", "flac"):
            result = _fresh_runner().invoke(main, ["session", "--format", fmt])
            assert result.exit_code == 0, f"Failed for format: {fmt}"

    def test_session_invalid_format_errors(self) -> None:
        result = _fresh_runner().invoke(main, ["session", "--format", "aac"])
        assert result.exit_code != 0

    def test_session_saves_to_file(self, tmp_path: Path) -> None:
        output = tmp_path / "session.json"
        result = _fresh_runner().invoke(
            main, ["session", "--output", str(output)]
        )
        assert result.exit_code == 0
        assert output.exists()

    def test_session_saved_file_is_valid_json(self, tmp_path: Path) -> None:
        output = tmp_path / "session.json"
        _fresh_runner().invoke(main, ["session", "--output", str(output)])
        data = json.loads(output.read_text(encoding="utf-8"))
        assert "session_id" in data
        assert "config" in data
        assert "state" in data

    def test_session_saved_file_has_correct_language(self, tmp_path: Path) -> None:
        output = tmp_path / "session.json"
        _fresh_runner().invoke(main, ["session", "--language", "ta", "--output", str(output)])
        data = json.loads(output.read_text(encoding="utf-8"))
        assert data["config"]["language"] == "ta"

    def test_session_without_output_does_not_create_file(self, tmp_path: Path) -> None:
        expected = tmp_path / "session.json"
        _fresh_runner().invoke(main, ["session"])
        assert not expected.exists()

    def test_session_output_mentions_saved_path(self, tmp_path: Path) -> None:
        output = tmp_path / "my_session.json"
        result = _fresh_runner().invoke(main, ["session", "--output", str(output)])
        assert "my_session.json" in result.output or str(output) in result.output

    def test_session_help(self) -> None:
        result = _fresh_runner().invoke(main, ["session", "--help"])
        assert result.exit_code == 0
        assert "language" in result.output.lower()


class TestTranscriptCommand:
    def test_transcript_from_session_file(self, session_json_file: Path) -> None:
        result = _fresh_runner().invoke(
            main, ["transcript", "--session", str(session_json_file)]
        )
        assert result.exit_code == 0
        assert "Hello, how are you?" in result.output

    def test_transcript_empty_session_message(self, empty_session_json_file: Path) -> None:
        result = _fresh_runner().invoke(
            main, ["transcript", "--session", str(empty_session_json_file)]
        )
        assert result.exit_code == 0
        assert "No utterances" in result.output

    def test_transcript_missing_session_file_errors(self, tmp_path: Path) -> None:
        result = _fresh_runner().invoke(
            main, ["transcript", "--session", str(tmp_path / "missing.json")]
        )
        assert result.exit_code != 0

    def test_transcript_missing_flag_errors(self) -> None:
        result = _fresh_runner().invoke(main, ["transcript"])
        assert result.exit_code != 0

    def test_transcript_invalid_json_session(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{invalid json}", encoding="utf-8")
        result = _fresh_runner().invoke(main, ["transcript", "--session", str(bad)])
        assert result.exit_code != 0

    def test_transcript_multi_utterance_order(self, tmp_path: Path) -> None:
        import json as _json
        from aumai_voicefirst.models import AudioFormat, Utterance, VoiceConfig, VoiceSession

        config = VoiceConfig(language="en", format=AudioFormat.wav)
        session = VoiceSession(session_id="test-session", config=config)
        u1 = Utterance(text="first line", language="en", start_ms=0.0, end_ms=500.0, confidence=0.9)
        u2 = Utterance(text="second line", language="en", start_ms=600.0, end_ms=1200.0, confidence=0.9)
        # Add out of order intentionally
        session.utterances.extend([u2, u1])

        session_file = tmp_path / "multi.json"
        session_file.write_text(session.model_dump_json(indent=2), encoding="utf-8")

        result = _fresh_runner().invoke(main, ["transcript", "--session", str(session_file)])
        assert result.exit_code == 0
        lines = [l for l in result.output.splitlines() if l.strip()]
        assert lines[0] == "first line"
        assert lines[1] == "second line"

    def test_transcript_help(self) -> None:
        result = _fresh_runner().invoke(main, ["transcript", "--help"])
        assert result.exit_code == 0
        assert "session" in result.output.lower()

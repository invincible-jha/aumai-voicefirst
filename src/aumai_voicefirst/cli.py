"""CLI entry point for aumai-voicefirst."""

from __future__ import annotations

import json
from pathlib import Path

import click

from aumai_voicefirst.core import VoiceSessionManager
from aumai_voicefirst.models import AudioFormat, VoiceConfig, VoiceSession

_manager = VoiceSessionManager()


@click.group()
@click.version_option()
def main() -> None:
    """AumAI VoiceFirst — Voice-native AI interaction framework CLI."""


@main.command("session")
@click.option("--language", default="en", show_default=True, help="BCP-47 language code.")
@click.option("--sample-rate", default=16000, show_default=True, type=int, help="Sample rate in Hz.")
@click.option(
    "--format",
    "audio_format",
    default="wav",
    show_default=True,
    type=click.Choice([f.value for f in AudioFormat]),
    help="Audio format.",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Save session JSON to this file.",
)
def session(language: str, sample_rate: int, audio_format: str, output: Path | None) -> None:
    """Create a new voice session and print its ID."""
    config = VoiceConfig(
        language=language,
        sample_rate=sample_rate,
        format=AudioFormat(audio_format),
    )
    voice_session = _manager.create_session(config)
    click.echo(f"Session ID: {voice_session.session_id}")
    click.echo(f"Language:   {language}")
    click.echo(f"Format:     {audio_format}  {sample_rate} Hz")

    if output is not None:
        output.write_text(
            voice_session.model_dump_json(indent=2),
            encoding="utf-8",
        )
        click.echo(f"Session saved to {output}")


@main.command("transcript")
@click.option(
    "--session",
    "session_file",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to session JSON file.",
)
def transcript(session_file: Path) -> None:
    """Print the transcript of a saved voice session."""
    data: dict[str, object] = json.loads(session_file.read_text(encoding="utf-8"))
    voice_session = VoiceSession.model_validate(data)
    text = _manager.get_transcript(voice_session)
    if text:
        click.echo(text)
    else:
        click.echo("No utterances recorded in this session.")


if __name__ == "__main__":
    main()

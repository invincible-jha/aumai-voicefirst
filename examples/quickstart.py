"""Quickstart examples for aumai-voicefirst.

Run this file directly to verify your installation and explore the API:

    python examples/quickstart.py

Each demo function is self-contained and prints its own output with a header.
No external services are required — all examples use in-memory session management.
"""

from __future__ import annotations


def demo_create_session() -> None:
    """Demonstrate session creation and basic configuration."""
    from aumai_voicefirst.core import VoiceSessionManager
    from aumai_voicefirst.models import AudioFormat, VoiceConfig

    print("=" * 60)
    print("DEMO 1: Session Creation")
    print("=" * 60)

    manager = VoiceSessionManager()

    # Create sessions for different languages and formats
    configs = [
        VoiceConfig(language="hi", sample_rate=16000, format=AudioFormat.wav),
        VoiceConfig(language="ta", sample_rate=16000, format=AudioFormat.wav),
        VoiceConfig(language="en", sample_rate=44100, format=AudioFormat.mp3),
        VoiceConfig(language="zh", sample_rate=16000, format=AudioFormat.flac),
    ]

    sessions = [manager.create_session(config) for config in configs]

    print(f"\nCreated {len(sessions)} sessions:")
    for session in sessions:
        print(
            f"  ID: {session.session_id[:8]}..."
            f"  lang={session.config.language}"
            f"  rate={session.config.sample_rate}Hz"
            f"  fmt={session.config.format.value}"
            f"  state={session.state}"
        )

    # Retrieve by ID
    retrieved = manager.get_session(sessions[0].session_id)
    print(f"\nRetrieved session matches: {retrieved is sessions[0]}")

    # Demonstrate JSON round-trip
    import json
    json_str = sessions[0].model_dump_json(indent=2)
    from aumai_voicefirst.models import VoiceSession
    restored = VoiceSession.model_validate(json.loads(json_str))
    print(f"JSON round-trip preserves session_id: {restored.session_id == sessions[0].session_id}")


def demo_utterances_and_transcript() -> None:
    """Demonstrate adding utterances and reconstructing transcripts."""
    from aumai_voicefirst.core import VoiceSessionManager
    from aumai_voicefirst.models import AudioFormat, Utterance, VoiceConfig

    print("\n" + "=" * 60)
    print("DEMO 2: Utterances and Transcript Reconstruction")
    print("=" * 60)

    manager = VoiceSessionManager()
    config = VoiceConfig(language="hi", format=AudioFormat.wav)
    session = manager.create_session(config)

    # Simulate a customer support call in Hindi
    # Note: utterance 2 arrives out of order (added after utterance 3)
    utterances = [
        Utterance(
            text="नमस्ते, मुझे मेरे ऑर्डर के बारे में जानकारी चाहिए",
            language="hi",
            start_ms=0.0,
            end_ms=3200.0,
            confidence=0.94,
        ),
        Utterance(
            text="ऑर्डर नंबर एक दो तीन चार है",
            language="hi",
            start_ms=7800.0,
            end_ms=9500.0,
            confidence=0.87,
        ),
        Utterance(
            text="कृपया अपना ऑर्डर नंबर बताएं",
            language="hi",
            start_ms=4200.0,
            end_ms=5800.0,
            confidence=0.96,
        ),
    ]

    for utt in utterances:
        manager.add_utterance(session, utt)

    print(f"\nUtterances added (in insertion order): {len(session.utterances)}")
    print(f"Session state: {session.state}")

    print("\nTranscript (sorted by start_ms, not insertion order):")
    transcript = manager.get_transcript(session)
    for i, line in enumerate(transcript.split("\n"), 1):
        print(f"  {i}. {line}")

    # Demonstrate confidence filtering
    high_confidence = [u for u in session.utterances if u.confidence >= 0.90]
    print(f"\nHigh-confidence utterances (>= 90%): {len(high_confidence)}")
    for u in sorted(high_confidence, key=lambda x: x.start_ms):
        print(f"  [{u.start_ms:.0f}ms] conf={u.confidence:.0%} '{u.text[:40]}...'")


def demo_language_routing() -> None:
    """Demonstrate VoiceRouter routing utterances to language handlers."""
    from aumai_voicefirst.core import VoiceRouter
    from aumai_voicefirst.models import Utterance

    print("\n" + "=" * 60)
    print("DEMO 3: Language Routing")
    print("=" * 60)

    router = VoiceRouter()

    # Simulate a multilingual call center receiving utterances
    test_cases = [
        # Indic languages
        ("hi", "नमस्ते, मुझे मदद चाहिए"),
        ("bn", "আমার সাহায্য দরকার"),
        ("ta", "என்னை உதவுங்கள்"),
        ("te", "నాకు సహాయం కావాలి"),
        ("mr", "मला मदत हवी"),
        ("pa", "ਮੈਨੂੰ ਮਦਦ ਚਾਹੀਦੀ ਹੈ"),
        ("hi-IN", "BCP-47 regional subtag stripped"),  # hi-IN -> hi
        # CJK languages
        ("ja", "助けてください"),
        ("zh", "请帮助我"),
        ("ko", "도움이 필요합니다"),
        # Arabic-script languages
        ("ar", "أحتاج مساعدة"),
        ("fa", "به کمک نیاز دارم"),
        # Default (Latin-script and others)
        ("en", "I need help please"),
        ("es", "Necesito ayuda"),
        ("fr", "J'ai besoin d'aide"),
        ("de", "Ich brauche Hilfe"),
    ]

    handler_groups: dict[str, list[str]] = {}
    for lang, text in test_cases:
        utt = Utterance(
            text=text, language=lang, start_ms=0.0, end_ms=1000.0, confidence=0.9
        )
        handler = router.route(utt)
        handler_groups.setdefault(handler, []).append(f"{lang}")

    print("\nRouting results by handler:")
    for handler, langs in sorted(handler_groups.items()):
        print(f"  {handler:<22} <- {', '.join(langs)}")


def demo_session_lifecycle() -> None:
    """Demonstrate session state transitions and error handling."""
    from aumai_voicefirst.core import VoiceSessionManager
    from aumai_voicefirst.models import Utterance, VoiceConfig

    print("\n" + "=" * 60)
    print("DEMO 4: Session Lifecycle and State Management")
    print("=" * 60)

    manager = VoiceSessionManager()
    session = manager.create_session(VoiceConfig(language="en"))

    def make_utt(text: str, start: float) -> Utterance:
        return Utterance(
            text=text, language="en", start_ms=start, end_ms=start + 500, confidence=0.95
        )

    print(f"\nInitial state: {session.state}")

    # Active: utterances allowed
    manager.add_utterance(session, make_utt("Hello, I need support.", 0.0))
    print(f"Added utterance. State: {session.state}")

    # Pause: still allows utterances
    session.state = "paused"
    manager.add_utterance(session, make_utt("(placed on hold)", 5000.0))
    print(f"Paused and still added utterance. State: {session.state}")

    # Resume
    session.state = "active"
    manager.add_utterance(session, make_utt("Thank you for waiting.", 12000.0))
    print(f"Resumed. State: {session.state}")

    # Complete: no more utterances
    session.state = "completed"
    print(f"Completed. State: {session.state}")

    try:
        manager.add_utterance(session, make_utt("This should fail.", 15000.0))
    except ValueError as exc:
        print(f"Expected error caught: {exc}")

    print(f"\nFinal transcript ({len(session.utterances)} utterances):")
    print(manager.get_transcript(session))


def demo_tts_config() -> None:
    """Demonstrate TextToSpeechConfig for provider-agnostic TTS configuration."""
    from aumai_voicefirst.models import TextToSpeechConfig

    print("\n" + "=" * 60)
    print("DEMO 5: TextToSpeechConfig")
    print("=" * 60)

    # Representative voice profiles for different languages
    profiles = {
        "Hindi (female, slightly faster)": TextToSpeechConfig(
            voice_id="aumai-hi-female-v1",
            speed=1.1,
            pitch=1.5,
        ),
        "Tamil (male, normal)": TextToSpeechConfig(
            voice_id="aumai-ta-male-v1",
            speed=1.0,
            pitch=0.0,
        ),
        "English (neutral, slow for accessibility)": TextToSpeechConfig(
            voice_id="aumai-en-neutral-v1",
            speed=0.85,
            pitch=0.0,
        ),
    }

    print("\nTTS profiles:")
    for name, cfg in profiles.items():
        print(f"\n  [{name}]")
        print(f"    voice_id: {cfg.voice_id}")
        print(f"    speed:    {cfg.speed}x")
        print(f"    pitch:    {cfg.pitch:+.1f} semitones")

    # Validation boundary checks
    print("\nValidation examples:")
    from pydantic import ValidationError

    for label, kwargs in [
        ("Speed too fast (> 4.0)", {"voice_id": "v", "speed": 5.0}),
        ("Pitch out of range (< -20.0)", {"voice_id": "v", "pitch": -25.0}),
    ]:
        try:
            TextToSpeechConfig(**kwargs)
        except ValidationError:
            print(f"  '{label}' -> ValidationError raised (expected)")


def main() -> None:
    """Run all demos in sequence."""
    print("\naumai-voicefirst quickstart\n")

    demo_create_session()
    demo_utterances_and_transcript()
    demo_language_routing()
    demo_session_lifecycle()
    demo_tts_config()

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()

# Getting Started with aumai-voicefirst

Voice-native AI interaction framework. This guide takes you from a clean Python
environment to building, populating, persisting, and replaying voice sessions.

---

## Prerequisites

- Python 3.11 or higher
- `pip` 23+ (or `uv` for faster installs)
- No external service credentials required for session management
- A speech-to-text provider of your choice (Whisper, Google Cloud Speech, Azure, etc.)
  is needed to produce `Utterance` objects from real audio — VoiceFirst models the data,
  it does not perform transcription itself

---

## Installation

### From PyPI

```bash
pip install aumai-voicefirst
```

### From source

```bash
git clone https://github.com/aumai/aumai-voicefirst
cd aumai-voicefirst
pip install -e ".[dev]"
```

### Verify

```bash
python -c "import aumai_voicefirst; print(aumai_voicefirst.__version__)"
# 0.1.0

voicefirst --version
# voicefirst, version 0.1.0
```

---

## Step-by-Step Tutorial

### Step 1 — Configure a voice session

A `VoiceConfig` describes the audio properties of a session. It is immutable once created.

```python
from aumai_voicefirst.models import AudioFormat, VoiceConfig

config = VoiceConfig(
    language="hi",         # BCP-47 language code
    sample_rate=16000,     # Hz — 16kHz is standard for speech recognition
    channels=1,            # mono
    format=AudioFormat.wav,
)

print(config.language)     # hi
print(config.sample_rate)  # 16000
print(config.format)       # AudioFormat.wav
```

Available audio formats: `AudioFormat.wav`, `AudioFormat.mp3`, `AudioFormat.ogg`,
`AudioFormat.flac`.

### Step 2 — Create a session

`VoiceSessionManager` is the stateful object that manages all sessions.

```python
from aumai_voicefirst.core import VoiceSessionManager

manager = VoiceSessionManager()
session = manager.create_session(config)

print(session.session_id)  # UUID, e.g. 3f8a1c2d-...
print(session.state)       # active
print(session.utterances)  # []
```

Each call to `create_session` generates a fresh UUID4 session ID. Sessions are stored
in memory in the manager's internal dictionary.

### Step 3 — Add utterances

As your speech-to-text provider transcribes audio, wrap each result in an `Utterance`
and add it to the session.

```python
from aumai_voicefirst.models import Utterance

# First utterance: caller speaks at t=0ms
u1 = Utterance(
    text="नमस्ते, मुझे सहायता चाहिए",
    language="hi",
    start_ms=0.0,
    end_ms=2100.0,
    confidence=0.94,
)

# Second utterance: a brief pause, then continues
u2 = Utterance(
    text="मेरा ऑर्डर रद्द हो गया",
    language="hi",
    start_ms=3400.0,
    end_ms=5600.0,
    confidence=0.88,
)

manager.add_utterance(session, u1)
manager.add_utterance(session, u2)

print(len(session.utterances))  # 2
```

### Step 4 — Get the transcript

The transcript is reconstructed by sorting utterances on `start_ms`:

```python
transcript = manager.get_transcript(session)
print(transcript)
# नमस्ते, मुझे सहायता चाहिए
# मेरा ऑर्डर रद्द हो गया
```

### Step 5 — Route utterances to handlers

Use `VoiceRouter` to determine which language-specialized handler should process each
utterance.

```python
from aumai_voicefirst.core import VoiceRouter

router = VoiceRouter()

handler_id = router.route(u1)
print(handler_id)  # handler.indic
```

The four handler identifiers are:
- `"handler.indic"` — for all 23 Indic languages
- `"handler.cjk"` — for Chinese, Japanese, Korean
- `"handler.arabic"` — for Arabic, Persian, Urdu (Arabic script), Kashmiri, Sindhi
- `"handler.default"` — for all other languages (English, Spanish, French, etc.)

### Step 6 — Save and restore a session

Sessions are Pydantic models and serialize to JSON natively.

```python
import json
from pathlib import Path
from aumai_voicefirst.models import VoiceSession

# Save to disk
path = Path("call_session.json")
path.write_text(session.model_dump_json(indent=2), encoding="utf-8")

# Restore from disk
data = json.loads(path.read_text(encoding="utf-8"))
restored_session = VoiceSession.model_validate(data)

print(restored_session.session_id == session.session_id)  # True
print(len(restored_session.utterances))                   # 2
```

---

## Common Patterns and Recipes

### Pattern 1 — Streaming STT integration

The typical pattern when integrating with a streaming STT API:

```python
from aumai_voicefirst.core import VoiceSessionManager, VoiceRouter
from aumai_voicefirst.models import AudioFormat, VoiceConfig, Utterance

manager = VoiceSessionManager()
router = VoiceRouter()

def on_call_start(language: str) -> str:
    """Called when a new call begins. Returns the session ID."""
    config = VoiceConfig(language=language, format=AudioFormat.wav)
    session = manager.create_session(config)
    return session.session_id

def on_utterance(
    session_id: str,
    text: str,
    language: str,
    start_ms: float,
    end_ms: float,
    confidence: float,
) -> str:
    """Called for each STT result. Returns the routing handler ID."""
    session = manager.get_session(session_id)
    utterance = Utterance(
        text=text,
        language=language,
        start_ms=start_ms,
        end_ms=end_ms,
        confidence=confidence,
    )
    manager.add_utterance(session, utterance)
    return router.route(utterance)

def on_call_end(session_id: str) -> str:
    """Called when call ends. Returns full transcript."""
    session = manager.get_session(session_id)
    session.state = "completed"
    return manager.get_transcript(session)
```

### Pattern 2 — Filtering low-confidence utterances

When the STT confidence is below a threshold, you may want to skip processing:

```python
def get_reliable_transcript(session_id: str, min_confidence: float = 0.75) -> str:
    session = manager.get_session(session_id)
    reliable = [u for u in session.utterances if u.confidence >= min_confidence]
    ordered = sorted(reliable, key=lambda u: u.start_ms)
    return "\n".join(u.text for u in ordered)
```

### Pattern 3 — Multi-language call detection

Detect if a call switches languages mid-stream:

```python
def detect_language_switch(session_id: str) -> list[tuple[str, float]]:
    """Return (language_code, timestamp_ms) pairs for language switches."""
    session = manager.get_session(session_id)
    ordered = sorted(session.utterances, key=lambda u: u.start_ms)

    switches: list[tuple[str, float]] = []
    last_lang = None
    for utt in ordered:
        lang = utt.language.split("-")[0]
        if lang != last_lang:
            switches.append((lang, utt.start_ms))
            last_lang = lang
    return switches
```

### Pattern 4 — Configuring TTS for voice response

After processing an utterance, configure the TTS response voice:

```python
from aumai_voicefirst.models import TextToSpeechConfig

# Different voices for different languages
TTS_PROFILES: dict[str, TextToSpeechConfig] = {
    "hi": TextToSpeechConfig(voice_id="hindi-f1", speed=1.0, pitch=1.0),
    "ta": TextToSpeechConfig(voice_id="tamil-m1", speed=0.95, pitch=0.0),
    "en": TextToSpeechConfig(voice_id="en-us-f1", speed=1.1, pitch=0.0),
}

def get_tts_config(language: str) -> TextToSpeechConfig:
    return TTS_PROFILES.get(language, TTS_PROFILES["en"])
```

### Pattern 5 — Persisting sessions to a JSON directory

Simple file-based session store for development:

```python
import json
from pathlib import Path
from aumai_voicefirst.models import VoiceSession

SESSION_DIR = Path("./sessions")
SESSION_DIR.mkdir(exist_ok=True)

def save_session(session: VoiceSession) -> None:
    path = SESSION_DIR / f"{session.session_id}.json"
    path.write_text(session.model_dump_json(indent=2), encoding="utf-8")

def load_session(session_id: str) -> VoiceSession:
    path = SESSION_DIR / f"{session_id}.json"
    return VoiceSession.model_validate(json.loads(path.read_text("utf-8")))
```

---

## Troubleshooting FAQ

### Q: `add_utterance` raises `ValueError: Cannot add utterance to session in state 'completed'`.

**A:** This is intentional. Once a session is marked `"completed"` or `"error"`, the
conversation is over. Check your call lifecycle management. If you need to reopen a
completed session for annotation purposes, create a new session and add the utterances
directly to the Pydantic model's `utterances` list — bypassing the manager's state guard.

### Q: The transcript is in the wrong order.

**A:** `get_transcript` sorts by `start_ms`. Ensure you are populating `start_ms` with
the actual start timestamp from your STT provider, not leaving it at `0.0`. If all
utterances have `start_ms=0.0`, they will be returned in the order they were appended.

### Q: My BCP-47 tag like `"hi-IN"` is not matching the Indic handler.

**A:** `VoiceRouter.route` splits on `"-"` and uses the base code. `"hi-IN"` becomes
`"hi"`, which is in `_INDIC_LANGUAGES`. This is by design and supports all regional
BCP-47 subtags.

### Q: `VoiceSessionManager.get_session` raises `KeyError`.

**A:** The in-memory manager only knows about sessions created in the current process
lifetime. If you restart your application, all sessions are lost unless you persisted them
to disk (see Pattern 5 above). For production use, implement a persistent session store.

### Q: Can `VoiceConfig.sample_rate` be 44100 (CD quality)?

**A:** Yes. The `sample_rate` field accepts values from 8000 to 48000 Hz, validated by
Pydantic. Standard speech recognition models work best at 16000 Hz, but the model places
no restriction on higher rates.

### Q: How do I add a new language to the Indic routing group?

**A:** The routing sets in `core.py` are module-level constants. To extend them at
runtime, import and update them before creating any `VoiceRouter` instances:

```python
from aumai_voicefirst import core as vf_core

vf_core._INDIC_LANGUAGES.add("bho")  # Bhojpuri
```

For a permanent change, submit a pull request adding the BCP-47 code to the appropriate
set in `core.py`.

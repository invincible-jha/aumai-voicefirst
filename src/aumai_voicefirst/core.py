"""Core logic for aumai-voicefirst."""

from __future__ import annotations

import uuid

from aumai_voicefirst.models import Utterance, VoiceConfig, VoiceSession

__all__ = ["VoiceSessionManager", "VoiceRouter"]

# Language family groupings for routing
_INDIC_LANGUAGES = {
    "hi", "bn", "te", "ta", "mr", "gu", "kn", "ml", "pa",
    "or", "as", "ur", "sa", "si", "ne", "kok", "mai", "doi",
    "mni", "ks", "sat", "sd", "bo",
}
_CJK_LANGUAGES = {"zh", "ja", "ko"}
_ARABIC_LANGUAGES = {"ar", "fa", "ur", "ks", "sd"}


class VoiceSessionManager:
    """Manages voice interaction sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, VoiceSession] = {}

    def create_session(self, config: VoiceConfig) -> VoiceSession:
        """Create a new voice session.

        Args:
            config: Configuration for the session.

        Returns:
            A new VoiceSession in 'active' state.
        """
        session_id = str(uuid.uuid4())
        session = VoiceSession(session_id=session_id, config=config)
        self._sessions[session_id] = session
        return session

    def add_utterance(self, session: VoiceSession, utterance: Utterance) -> None:
        """Append an utterance to an existing session.

        Args:
            session: The VoiceSession to update.
            utterance: The utterance to append.

        Raises:
            ValueError: If the session is not in 'active' or 'paused' state.
        """
        if session.state not in {"active", "paused"}:
            raise ValueError(
                f"Cannot add utterance to session in state '{session.state}'."
            )
        session.utterances.append(utterance)

    def get_transcript(self, session: VoiceSession) -> str:
        """Return the full transcript of a session as a single string.

        Args:
            session: The VoiceSession to transcribe.

        Returns:
            Newline-separated utterance texts ordered by start_ms.
        """
        ordered = sorted(session.utterances, key=lambda u: u.start_ms)
        return "\n".join(u.text for u in ordered)

    def get_session(self, session_id: str) -> VoiceSession:
        """Retrieve a session by ID.

        Args:
            session_id: The session identifier.

        Returns:
            The VoiceSession.

        Raises:
            KeyError: If the session does not exist.
        """
        return self._sessions[session_id]


class VoiceRouter:
    """Route voice interactions to appropriate language handlers."""

    def route(self, utterance: Utterance) -> str:
        """Determine the handler ID for an utterance based on language.

        Args:
            utterance: The utterance to route.

        Returns:
            A handler identifier string such as 'handler.indic',
            'handler.cjk', 'handler.arabic', or 'handler.default'.
        """
        lang = utterance.language.lower().split("-")[0]

        if lang in _INDIC_LANGUAGES:
            return "handler.indic"
        if lang in _CJK_LANGUAGES:
            return "handler.cjk"
        if lang in _ARABIC_LANGUAGES:
            return "handler.arabic"
        return "handler.default"

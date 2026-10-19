"""Voice provider factory (mirrors the telephony provider factory pattern)."""
from __future__ import annotations

from typing import Optional

from app.core.config import settings
from app.services.voice.gemini_live import GeminiLiveProvider
from app.services.voice.mock_provider import MockVoiceProvider, mock_voice_provider
from app.services.voice.provider import VoiceProvider, VoiceProviderUnavailable

_ALIASES = {
    "mock": "mock",
    "simulation": "mock",
    "gemini": "gemini_live",
    "gemini_live": "gemini_live",
}


class UnknownVoiceProvider(ValueError):
    pass


def build_voice_provider(provider: Optional[str] = None) -> VoiceProvider:
    raw = (provider or settings.VOICE_PROVIDER or "mock").strip().lower()
    resolved = _ALIASES.get(raw)
    if resolved is None:
        raise UnknownVoiceProvider(
            f"Unknown VOICE_PROVIDER '{raw}'. Supported: {', '.join(sorted(set(_ALIASES)))}."
        )
    if resolved == "mock":
        return MockVoiceProvider()
    return GeminiLiveProvider()


def get_voice_provider() -> VoiceProvider:
    """Return the configured provider, falling back to mock when unconfigured."""
    try:
        provider = build_voice_provider()
    except UnknownVoiceProvider:
        return mock_voice_provider
    if not provider.is_configured():
        # Explicit, logged fallback rather than a silent break.
        import logging

        logging.getLogger(__name__).warning(
            "Voice provider %s is not configured; falling back to mock.", provider.name
        )
        return mock_voice_provider
    return provider


__all__ = [
    "build_voice_provider",
    "get_voice_provider",
    "UnknownVoiceProvider",
    "VoiceProviderUnavailable",
    "mock_voice_provider",
]

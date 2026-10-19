"""
Telephony provider factory.

Resolves the adapter named by ``settings.TELEPHONY_PROVIDER``. The API layer must
obtain its adapter from here (never import a concrete adapter directly) so that
swapping providers is a configuration change.
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

from app.core.config import settings
from app.services.telephony.adapter import TelephonyAdapter
from app.services.telephony.asterisk_adapter import AsteriskAdapter
from app.services.telephony.mock_adapter import MockTelephonyAdapter, mock_telephony

logger = logging.getLogger(__name__)

# Aliases keep configuration forgiving while staying explicit.
_PROVIDER_ALIASES = {
    "mock": "mock",
    "simulation": "mock",
    "asterisk": "asterisk",
    "ari": "asterisk",
    "sip_gateway": "asterisk",  # SIP/VoLTE gateway terminates on Asterisk
}

_lock = threading.Lock()
_override: Optional[TelephonyAdapter] = None
_cached: Optional[TelephonyAdapter] = None
_cached_provider: Optional[str] = None


class UnknownTelephonyProvider(ValueError):
    """Raised when a provider name is configured that has no implementation."""


def build_adapter(provider: Optional[str] = None) -> TelephonyAdapter:
    """Construct a fresh adapter for ``provider`` (defaults to settings)."""
    raw = (provider or settings.TELEPHONY_PROVIDER or "mock").strip().lower()
    resolved = _PROVIDER_ALIASES.get(raw)
    if resolved is None:
        raise UnknownTelephonyProvider(
            f"Unknown TELEPHONY_PROVIDER '{provider or settings.TELEPHONY_PROVIDER}'. "
            f"Supported: {', '.join(sorted(set(_PROVIDER_ALIASES)))}."
        )

    if resolved == "mock":
        return MockTelephonyAdapter()
    if resolved == "asterisk":
        return AsteriskAdapter()
    raise UnknownTelephonyProvider(f"No adapter implementation for '{resolved}'.")


def get_adapter() -> TelephonyAdapter:
    """Return the process-wide adapter, building it on first use."""
    global _cached, _cached_provider
    if _override is not None:
        return _override

    with _lock:
        provider = (settings.TELEPHONY_PROVIDER or "mock").strip().lower()
        if _cached is None or _cached_provider != provider:
            _cached = build_adapter(provider)
            _cached_provider = provider
            logger.info("Telephony adapter initialised: %s", _cached.provider_name)
        return _cached


def set_adapter(adapter: Optional[TelephonyAdapter]) -> None:
    """Override the adapter (tests, dependency injection). Pass ``None`` to reset."""
    global _override, _cached, _cached_provider
    with _lock:
        _override = adapter
        _cached = None
        _cached_provider = None


__all__ = [
    "build_adapter",
    "get_adapter",
    "set_adapter",
    "UnknownTelephonyProvider",
    "mock_telephony",
]

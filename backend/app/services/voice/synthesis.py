"""
Text-to-audio for the simulated voice provider.

Two engines, in order of fidelity:

* ``windows-sapi`` - Windows' built-in ``System.Speech`` synthesizer, driven through
  PowerShell. Real, intelligible speech, fully offline, no extra dependency... but
  Windows only.
* ``synthetic-tones`` - a numpy source/filter generator that produces speech-shaped,
  speech-paced tones. Portable and deterministic, but **not intelligible**. It exists
  so the whole pipeline (audio bridge -> stored audio -> playback) still works on
  Linux, in Docker, and in CI.

Both return 16-bit PCM, mono, at the requested sample rate, so callers never need to
know which engine ran. The engine that was actually used is reported by
:func:`active_engine` and surfaces in the provider capabilities, so the UI can state
honestly what the audio is instead of calling it a phone recording.
"""
from __future__ import annotations

import base64
import json
import logging
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from io import BytesIO
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

ENGINE_SYSTEM = "windows-sapi"
ENGINE_TONES = "synthetic-tones"

#: How long a single text may be. Keeps a runaway prompt from blocking a call.
MAX_TEXT_CHARS = 1200
_SAPI_TIMEOUT_SECONDS = 30

_system_disabled_reason: Optional[str] = None


# --------------------------------------------------------------------------- #
# WAV helpers
# --------------------------------------------------------------------------- #
def pcm16_to_wav(pcm: bytes, sample_rate: int) -> bytes:
    """Wrap raw little-endian PCM16 mono samples in a WAV container."""
    buffer = BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(int(sample_rate))
        handle.writeframes(pcm)
    return buffer.getvalue()


def wav_duration_seconds(data: bytes) -> float:
    """Duration of a WAV byte string, or 0.0 when it cannot be read."""
    try:
        with wave.open(BytesIO(data), "rb") as handle:
            frames = handle.getnframes()
            rate = handle.getframerate() or 1
            return round(frames / float(rate), 3)
    except Exception:
        return 0.0


def wav_to_pcm16(data: bytes) -> Tuple[bytes, int]:
    """Strip the WAV container, returning ``(pcm16 bytes, sample_rate)``."""
    with wave.open(BytesIO(data), "rb") as handle:
        return handle.readframes(handle.getnframes()), int(handle.getframerate())


def decode_audio(payload: dict) -> Tuple[bytes, int]:
    """
    Read a provider ``AUDIO_OUT`` payload into ``(pcm16 bytes, sample_rate)``.

    Providers hand us base64 PCM16; the rate comes from the payload, or from a
    ``audio/pcm;rate=NNNN`` mime string when the provider reports it that way.
    """
    encoded = payload.get("audio") or payload.get("data")
    if not encoded:
        return b"", 0
    try:
        pcm = base64.b64decode(encoded)
    except Exception:
        logger.warning("Discarding AUDIO_OUT payload that was not valid base64.")
        return b"", 0

    rate = payload.get("sample_rate")
    if not isinstance(rate, int) or rate <= 0:
        mime = str(payload.get("mime") or "")
        match = re.search(r"rate=(\d+)", mime)
        rate = int(match.group(1)) if match else 0
    return pcm, int(rate)


# --------------------------------------------------------------------------- #
# Engine selection
# --------------------------------------------------------------------------- #
def system_engine_available() -> bool:
    """Whether the Windows speech engine can be used from this process."""
    if _system_disabled_reason:
        return False
    if sys.platform != "win32":
        return False
    return shutil.which("powershell") is not None


def active_engine(preferred: str = "auto") -> str:
    """
    Resolve which engine will be used.

    ``preferred`` is ``auto`` (system when possible), ``system`` or ``tones``.
    An explicit ``system`` request still falls back to tones when the engine is
    unavailable, and says so in the log.
    """
    choice = (preferred or "auto").strip().lower()
    if choice in ("system", "auto") and system_engine_available():
        return ENGINE_SYSTEM
    if choice == "system" and not system_engine_available():
        logger.warning(
            "Mock speech engine 'system' was requested but is unavailable; using %s.",
            ENGINE_TONES,
        )
    return ENGINE_TONES


# --------------------------------------------------------------------------- #
# Windows SAPI engine
# --------------------------------------------------------------------------- #
_SAPI_SCRIPT = r"""
param([string]$InFile, [string]$OutDir, [int]$Rate)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(
    $Rate,
    [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,
    [System.Speech.AudioFormat.AudioChannel]::Mono)
$texts = @(Get-Content -LiteralPath $InFile -Raw | ConvertFrom-Json)
for ($i = 0; $i -lt $texts.Count; $i++) {
    $path = Join-Path $OutDir "$i.wav"
    $synth.SetOutputToWaveFile($path, $fmt)
    $synth.Speak([string]$texts[$i])
}
$synth.Dispose()
"""


def _synthesize_with_system(texts: Sequence[str], sample_rate: int) -> List[Optional[bytes]]:
    """
    Render every text in one PowerShell invocation and return WAV bytes per text.

    Returns ``None`` for any text that could not be rendered. A total failure
    disables the engine for the rest of the process so we do not pay the timeout
    on every sentence.
    """
    global _system_disabled_reason

    with tempfile.TemporaryDirectory(prefix="sf-tts-") as tmp:
        tmp_path = Path(tmp)
        in_file = tmp_path / "texts.json"
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        script_file = tmp_path / "synth.ps1"
        script_file.write_text(_SAPI_SCRIPT, encoding="utf-8")
        in_file.write_text(json.dumps(list(texts)), encoding="utf-8")

        try:
            completed = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script_file),
                    "-InFile",
                    str(in_file),
                    "-OutDir",
                    str(out_dir),
                    "-Rate",
                    str(int(sample_rate)),
                ],
                capture_output=True,
                timeout=_SAPI_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            _system_disabled_reason = str(exc)
            logger.warning("Speech engine disabled for this process: %s", exc)
            return [None for _ in texts]

        if completed.returncode != 0:
            _system_disabled_reason = completed.stderr.decode(errors="replace")[:200]
            logger.warning("Speech engine failed: %s", _system_disabled_reason)
            return [None for _ in texts]

        results: List[Optional[bytes]] = []
        for index in range(len(texts)):
            path = out_dir / f"{index}.wav"
            results.append(path.read_bytes() if path.exists() else None)
        return results


# --------------------------------------------------------------------------- #
# Portable tone engine (numpy source/filter synthesis)
# --------------------------------------------------------------------------- #
# Plausible vowel formant triples (F1, F2, F3) in Hz.
_VOWELS: Tuple[Tuple[float, float, float], ...] = (
    (730.0, 1090.0, 2440.0),  # "ah"
    (530.0, 1840.0, 2480.0),  # "eh"
    (270.0, 2290.0, 3010.0),  # "ee"
    (570.0, 840.0, 2410.0),   # "oh"
    (300.0, 870.0, 2240.0),   # "oo"
    (440.0, 1020.0, 2240.0),  # "uh"
)


def _synthesize_tones(text: str, sample_rate: int) -> bytes:
    """Generate speech-cadenced tones. Audible and paced like speech, not intelligible."""
    import numpy as np

    words = re.findall(r"[A-Za-z0-9']+", text) or ["..."]
    rate = int(sample_rate)
    pieces: List["np.ndarray"] = [np.zeros(int(rate * 0.08), dtype=np.float32)]

    for word_index, word in enumerate(words):
        syllables = max(1, min(4, round(len(word) / 3.0) or 1))
        for syllable in range(syllables):
            vowel = _VOWELS[(len(word) + syllable + word_index) % len(_VOWELS)]
            f0 = 108.0 + 14.0 * ((len(word) + syllable) % 5)
            duration = 0.11 + 0.02 * (vowel[0] / 1000.0)
            count = int(rate * duration)
            t = np.arange(count) / rate

            # Glottal pulse train.
            period = 1.0 / f0
            pulses = np.zeros(count, dtype=np.float32)
            pulses[:: max(1, int(round(period * rate)))] = 1.0

            # Source/filter: decay the formants so the burst is vowel-like.
            h = np.zeros(count, dtype=np.float32)
            for formant, weight in zip(vowel, (1.0, 0.55, 0.3)):
                h += (weight * np.exp(-7.0 * t) * np.sin(2.0 * np.pi * formant * t)).astype(
                    np.float32
                )
            filtered = np.convolve(pulses, h, mode="full")[:count]

            # Syllable envelope with a short attack so words do not click.
            attack = np.clip(t / 0.02, 0.0, 1.0)
            release = np.clip((duration - t) / 0.05, 0.0, 1.0)
            pieces.append((filtered * attack * release).astype(np.float32))
            pieces.append(np.zeros(int(rate * 0.035), dtype=np.float32))
        # Slightly longer pause between words than between syllables.
        pieces.append(np.zeros(int(rate * 0.045), dtype=np.float32))

    joined = np.concatenate(pieces) if pieces else np.zeros(1, dtype=np.float32)
    peak = float(np.max(np.abs(joined))) or 1.0
    pcm = (np.clip(joined / peak * 0.6, -1.0, 1.0) * 32767.0).astype("<i2")
    return pcm.tobytes()


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def synthesize(
    texts: Iterable[str],
    *,
    sample_rate: int = 16000,
    preferred: str = "auto",
    max_chars: int = MAX_TEXT_CHARS,
) -> List[Optional[bytes]]:
    """
    Render each text to WAV bytes.

    Falls back to the tone engine when the system engine is unavailable or fails,
    and returns ``None`` for a text that produced nothing at all - callers must
    tolerate that rather than assume audio exists.
    """
    cleaned = [(text or "").strip()[:max_chars] for text in texts]
    if not cleaned:
        return []

    if active_engine(preferred) == ENGINE_SYSTEM:
        rendered = _synthesize_with_system(cleaned, sample_rate)
        if all(item is not None for item in rendered):
            return rendered
        # Partially failed: retry only the missing ones on the tone engine.
        logger.warning("Falling back to the tone engine for %d item(s).", sum(1 for r in rendered if r is None))
        return [
            item if item is not None else _tones_or_none(cleaned[i], sample_rate)
            for i, item in enumerate(rendered)
        ]

    return [_tones_or_none(text, sample_rate) for text in cleaned]


def _tones_or_none(text: str, sample_rate: int) -> Optional[bytes]:
    if not text:
        return None
    try:
        return pcm16_to_wav(_synthesize_tones(text, sample_rate), sample_rate)
    except Exception:  # numpy missing, memory, anything: no audio, not a crash
        logger.exception("Tone synthesis failed.")
        return None


def engine_report(preferred: str = "auto") -> dict:
    """What the UI/docs should say about the audio this provider produces."""
    engine = active_engine(preferred)
    return {
        "engine": engine,
        "intelligible": engine == ENGINE_SYSTEM,
        "note": (
            "Windows system speech (intelligible, generated locally)."
            if engine == ENGINE_SYSTEM
            else "Synthetic speech-shaped tones (not intelligible)."
        ),
    }

"""Shout a Jev decision out loud.

Whisper only transcribes speech. This uses OpenAI TTS and caches the two
clips once so playback can stay in sync with each step.
"""

from __future__ import annotations

import asyncio
import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("jev.voice")

LINES = {
    "flap": "Flap!",
    "noop": "Noop!",
}

_clips: dict[str, bytes] = {}
_lock = asyncio.Lock()


def _api_key() -> str:
    return os.getenv("OPENAI_API_KEY", "").strip()


async def _synthesize(decision: str) -> bytes:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=_api_key())
    speech = await client.audio.speech.create(
        model="tts-1",
        voice="echo",
        input=LINES.get(decision, f"{decision}!"),
        speed=1.2,
    )
    return speech.content


async def warmup() -> dict[str, bytes]:
    """Generate Flap! and Noop! once. Later shouts are instant."""
    if not _api_key():
        return {}
    async with _lock:
        missing = [name for name in LINES if name not in _clips]
        if missing:
            try:
                rendered = await asyncio.gather(*(_synthesize(name) for name in missing))
            except Exception as exc:
                logger.warning("voice warmup failed: %s", exc)
                return dict(_clips)
            for name, audio in zip(missing, rendered, strict=True):
                _clips[name] = audio
    return dict(_clips)


async def shout(decision: str) -> bytes | None:
    """Return a cached clip. Call as `audio = await shout(name)`."""
    clips = await warmup()
    return clips.get(decision)

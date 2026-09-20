"""One live game session: step the env, ask a policy, broadcast frames."""

from __future__ import annotations

import asyncio
import base64
from typing import Any, Awaitable, Callable

from backend.agent import (
    JevPolicy,
    decide_heuristic,
    decide_random,
    decision_log,
)
from backend.agent.voice import warmup
from backend.engine import encode_jpeg_b64, info_score, make_env, observation_to_state

PHYSICS_HZ = 20
Send = Callable[[dict[str, Any]], Awaitable[None]]


class GameSession:
    def __init__(self, send: Send) -> None:
        self._send = send
        self.agent = "jev"
        self.use_fallback = True
        self.running = False
        self.env = None
        self.obs = None
        self.info: dict[str, Any] = {}
        self.steps = 0
        self.last_decision = None
        self._jev: JevPolicy | None = None
        self._command: dict[str, Any] | None = None
        self.shout_on = True

    async def handle(self, message: dict[str, Any]) -> None:
        self._command = message

    async def run_forever(self) -> None:
        try:
            while True:
                command = self._command
                self._command = None
                if command:
                    await self._apply(command)
                if self.running:
                    await self._tick()
                    if self.agent != "jev":
                        await asyncio.sleep(1 / PHYSICS_HZ)
                else:
                    await asyncio.sleep(0.04)
        finally:
            await self.close()

    async def close(self) -> None:
        self.running = False
        if self.env is not None:
            self.env.close()
            self.env = None
        if self._jev is not None:
            await self._jev.__aexit__(None, None, None)
            self._jev = None

    async def _apply(self, message: dict[str, Any]) -> None:
        kind = message.get("type")
        if kind == "set_voice":
            self.shout_on = bool(message.get("shout", self.shout_on))
            if self.shout_on:
                await self._send_voice_bank()
            await self._status()
            return
        if kind == "set_agent":
            self.agent = str(message.get("agent", self.agent))
            self.use_fallback = bool(message.get("fallback", self.use_fallback))
            await self._status()
            return
        if kind == "pause":
            self.running = False
            await self._status()
            return
        if kind == "reset":
            self.running = False
            self._open_env()
            await self._broadcast(terminated=False)
            await self._status()
            return
        if kind == "start":
            self.agent = str(message.get("agent", self.agent))
            self.use_fallback = bool(message.get("fallback", self.use_fallback))
            self.shout_on = bool(message.get("shout", self.shout_on))
            if self.env is None:
                self._open_env()
            if self.agent == "jev" and self.shout_on:
                await self._send_voice_bank()
            self.running = True
            await self._status()

    def _open_env(self) -> None:
        if self.env is not None:
            self.env.close()
        self.env = make_env()
        self.obs, self.info = self.env.reset()
        self.steps = 0
        self.last_decision = None

    async def _tick(self) -> None:
        if self.env is None or self.obs is None:
            self._open_env()
        state = observation_to_state(self.obs, score=info_score(self.info))
        decision = await self._decide(state)
        self.last_decision = decision
        if self.agent == "jev":
            await self._emit_log(decision)
        self.obs, _reward, terminated, truncated, self.info = self.env.step(decision.action)
        self.steps += 1
        done = bool(terminated or truncated)
        await self._broadcast(terminated=done)
        if done:
            self.running = False
            await self._status()

    async def _decide(self, state: dict):
        if self.agent == "random":
            return decide_random(state)
        if self.agent == "heuristic":
            return decide_heuristic(state)
        if self._jev is None:
            self._jev = await JevPolicy(use_fallback=self.use_fallback).__aenter__()
        self._jev.use_fallback = self.use_fallback
        return await self._jev.decide(state)

    async def _emit_log(self, decision) -> None:
        record = decision_log(decision, step=self.steps, score=info_score(self.info))
        await self._send({"type": "log", **record})

    async def _send_voice_bank(self) -> None:
        clips = await warmup()
        if not clips:
            return
        await self._send(
            {
                "type": "voice_bank",
                "clips": {
                    name: base64.b64encode(audio).decode("ascii")
                    for name, audio in clips.items()
                },
            }
        )

    async def _broadcast(self, *, terminated: bool) -> None:
        frame = self.env.render() if self.env is not None else None
        decision = self.last_decision
        payload: dict[str, Any] = {
            "type": "frame",
            "image": encode_jpeg_b64(frame) if frame is not None else None,
            "score": info_score(self.info),
            "steps": self.steps,
            "terminated": terminated,
            "agent": self.agent,
            "action": decision.name if decision else None,
            "source": decision.source if decision else None,
            "probabilities": decision.probabilities if decision else None,
            "confidence": decision.confidence if decision else None,
            "latency_ms": decision.latency_ms if decision else None,
            "fallback": decision.fallback if decision else False,
            "error": decision.error if decision else None,
            "waiting": False,
        }
        await self._send(payload)

    async def _status(self) -> None:
        await self._send(
            {
                "type": "status",
                "running": self.running,
                "agent": self.agent,
                "fallback": self.use_fallback,
                "shout": self.shout_on,
            }
        )

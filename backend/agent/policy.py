"""Policies that pick flap/noop from named state."""

from __future__ import annotations

import logging
import os
import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Literal

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("jev")

ACTION_NOOP = 0
ACTION_FLAP = 1
CONFIDENCE_THRESHOLD = 0.55
AgentName = Literal["random", "heuristic", "jev"]

ACTION_QUESTION = {
    "instructions": (
        "Pick the best next action so the bird stays inside the next pipe gap. "
        "y grows downward. The bird never moves in x; each step the world closes by "
        "flap_effect.one_step_world_x. One flap lifts by flap_effect.one_flap_y_this_step "
        "this step, or flap_effect.one_flap_full_rise_y if you then noop until it peaks. "
        "If bird_is_below_next_gap_center is true the bird is too low."
    ),
    "criteria": {
        "noop": (
            "Do nothing this frame. Use when the bird is at or above the gap center "
            "or already rising through the gap."
        ),
        "flap": (
            "Flap now. Instantly sets a strong upward vel. Use when the bird is below "
            "the next gap center or falling through it and will miss without lift."
        ),
    },
}


@dataclass(frozen=True)
class Decision:
    action: int
    name: str
    source: str
    probabilities: dict[str, float] | None = None
    confidence: float | None = None
    latency_ms: float | None = None
    fallback: bool = False
    error: str | None = None


def decision_log(decision: Decision, *, step: int, score: int) -> dict[str, Any]:
    """Build a log record and write it to the jev logger."""
    probabilities = decision.probabilities or {}
    record = {
        "step": step,
        "score": score,
        "action": decision.name,
        "source": decision.source,
        "fallback": decision.fallback,
        "confidence": decision.confidence,
        "latency_ms": None if decision.latency_ms is None else round(decision.latency_ms),
        "p_flap": probabilities.get("flap"),
        "p_noop": probabilities.get("noop"),
        "error": decision.error,
    }
    logger.info(
        "step=%s score=%s action=%s source=%s fallback=%s "
        "confidence=%s latency_ms=%s p_flap=%s p_noop=%s error=%s",
        record["step"],
        record["score"],
        record["action"],
        record["source"],
        record["fallback"],
        record["confidence"],
        record["latency_ms"],
        record["p_flap"],
        record["p_noop"],
        record["error"],
    )
    return record


def decide_random(state: dict, rng: random.Random | None = None) -> Decision:
    del state
    roll = (rng or random).choice((ACTION_NOOP, ACTION_FLAP))
    return Decision(
        action=roll,
        name="flap" if roll == ACTION_FLAP else "noop",
        source="random",
    )


def decide_heuristic(state: dict, rng: random.Random | None = None) -> Decision:
    del rng
    if state["bird_is_below_next_gap_center"]:
        return Decision(action=ACTION_FLAP, name="flap", source="heuristic")
    return Decision(action=ACTION_NOOP, name="noop", source="heuristic")


def _with_fallback(state: dict, *, error: str | None, latency_ms: float | None) -> Decision:
    base = decide_heuristic(state)
    return Decision(
        action=base.action,
        name=base.name,
        source="heuristic",
        fallback=True,
        error=error,
        latency_ms=latency_ms,
    )


class JevPolicy:
    """Ask Jev Choice(flap/noop). Falls back to the heuristic when needed."""

    def __init__(
        self,
        *,
        use_fallback: bool = True,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
    ) -> None:
        self.use_fallback = use_fallback
        self.confidence_threshold = confidence_threshold
        self._client = None
        self._init_error = None

    async def __aenter__(self) -> JevPolicy:
        from typesafe_sdk import AsyncTypeSafeClient, TypeSafeError

        try:
            client = AsyncTypeSafeClient()
            self._client = await client.__aenter__()
        except TypeSafeError as exc:
            self._client = None
            self._init_error = str(exc)
        else:
            self._init_error = None
        return self

    async def __aexit__(self, *exc) -> None:
        if self._client is not None:
            await self._client.__aexit__(*exc)
            self._client = None

    async def decide(self, state: dict) -> Decision:
        from typesafe_sdk import Choice, TypeSafeError

        if self._client is None:
            if self.use_fallback:
                return _with_fallback(
                    state,
                    error=self._init_error or "TYPESAFE_API_KEY is missing",
                    latency_ms=None,
                )
            raise RuntimeError(self._init_error or "TYPESAFE_API_KEY is missing")

        started = time.perf_counter()
        try:
            response = await self._client.system_one(
                state=state,
                questions={
                    "action": Choice(
                        instructions=ACTION_QUESTION["instructions"],
                        criteria=ACTION_QUESTION["criteria"],
                    )
                },
            )
        except TypeSafeError as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            if self.use_fallback:
                return _with_fallback(state, error=str(exc), latency_ms=latency_ms)
            raise

        latency_ms = (time.perf_counter() - started) * 1000
        answer = response.choices["action"]
        name = answer.choice if answer.choice in {"flap", "noop"} else "noop"
        action = ACTION_FLAP if name == "flap" else ACTION_NOOP
        uncertain = answer.confidence < self.confidence_threshold
        if uncertain and self.use_fallback:
            fallback = decide_heuristic(state)
            return Decision(
                action=fallback.action,
                name=fallback.name,
                source="heuristic",
                probabilities=dict(answer.probabilities),
                confidence=float(answer.confidence),
                latency_ms=latency_ms,
                fallback=True,
                error="low confidence",
            )
        return Decision(
            action=action,
            name=name,
            source="jev",
            probabilities=dict(answer.probabilities),
            confidence=float(answer.confidence),
            latency_ms=latency_ms,
        )


_POLICIES: dict[str, Callable[..., Decision]] = {
    "random": decide_random,
    "heuristic": decide_heuristic,
}


def get_policy(name: str) -> Callable[..., Decision]:
    try:
        return _POLICIES[name]
    except KeyError as exc:
        known = ", ".join((*_POLICIES, "jev"))
        raise ValueError(f"unknown agent {name!r}; expected one of: {known}") from exc


def has_typesafe_key() -> bool:
    return bool(os.getenv("TYPESAFE_API_KEY", "").strip())

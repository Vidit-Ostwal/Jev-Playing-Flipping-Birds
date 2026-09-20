"""Map FlappyBird-v0's 12-float observation to named JSON for Jev.

The env (with use_lidar=False) yields, in order:

    last pipe x, last top y, last bottom y,
    next pipe x, next top y, next bottom y,
    next-next pipe x, next-next top y, next-next bottom y,
    bird y, bird vy, bird rotation

Default env settings normalize positions to ~[0, 1] and velocity/rotation
by their max. y grows downward: 0 is the top of the screen.
"""

from __future__ import annotations

from typing import Any, Mapping

from backend.engine.physics import flap_effect

OBS_SIZE = 12

_PIPE_FIELDS = (
    "last_pipe_x",
    "last_gap_top",
    "last_gap_bottom",
    "next_pipe_x",
    "next_gap_top",
    "next_gap_bottom",
    "next_next_pipe_x",
    "next_next_gap_top",
    "next_next_gap_bottom",
    "bird_y",
    "bird_vy",
    "bird_rotation",
)


def observation_to_state(
    obs,
    *,
    score: int = 0,
    normalized: bool = True,
) -> dict[str, Any]:
    """Turn a numeric observation (and score) into labeled Jev state."""
    values = [float(v) for v in obs]
    if len(values) != OBS_SIZE:
        raise ValueError(f"expected {OBS_SIZE} observation values, got {len(values)}")

    named = dict(zip(_PIPE_FIELDS, values, strict=True))
    next_gap_center = (named["next_gap_top"] + named["next_gap_bottom"]) / 2
    bird_y_minus_gap = named["bird_y"] - next_gap_center

    return {
        "coordinates": "y grows downward; 0 is the top of the screen. The bird never moves in x; pipes move toward it.",
        "normalized": normalized,
        "score": int(score),
        **named,
        "next_gap_center": next_gap_center,
        "bird_y_minus_next_gap_center": bird_y_minus_gap,
        "bird_is_below_next_gap_center": bird_y_minus_gap > 0,
        "flap_effect": flap_effect(normalized=normalized),
    }


def info_score(info: Mapping[str, Any] | None) -> int:
    if not info:
        return 0
    return int(info.get("score", 0))

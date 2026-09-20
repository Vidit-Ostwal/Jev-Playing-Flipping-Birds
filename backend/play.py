"""Play one headless episode with a baseline or Jev agent."""

from __future__ import annotations

import argparse
import asyncio
import random

from backend.agent import JevPolicy, decision_log, get_policy
from backend.engine import info_score, make_env, observation_to_state


def play_episode(agent_name: str, *, seed: int | None = None) -> dict:
    env = make_env()
    policy = get_policy(agent_name)
    rng = random.Random(seed)
    flaps = 0
    steps = 0
    fallbacks = 0

    try:
        obs, info = env.reset(seed=seed)
        while True:
            state = observation_to_state(obs, score=info_score(info))
            decision = policy(state, rng=rng)
            obs, _reward, terminated, truncated, info = env.step(decision.action)
            steps += 1
            flaps += int(decision.action == 1)
            fallbacks += int(decision.fallback)
            if terminated or truncated:
                break
    finally:
        env.close()

    return {
        "agent": agent_name,
        "steps": steps,
        "score": info_score(info),
        "flaps": flaps,
        "fallbacks": fallbacks,
        "source": "heuristic" if agent_name == "heuristic" else "random",
    }


async def play_jev_episode(*, seed: int | None = None, use_fallback: bool = True) -> dict:
    env = make_env()
    flaps = 0
    steps = 0
    fallbacks = 0
    last_source = "jev"

    async with JevPolicy(use_fallback=use_fallback) as jev:
        try:
            obs, info = env.reset(seed=seed)
            while True:
                state = observation_to_state(obs, score=info_score(info))
                decision = await jev.decide(state)
                last_source = decision.source
                decision_log(decision, step=steps, score=info_score(info))
                obs, _reward, terminated, truncated, info = env.step(decision.action)
                steps += 1
                flaps += int(decision.action == 1)
                fallbacks += int(decision.fallback)
                if terminated or truncated:
                    break
        finally:
            env.close()

    return {
        "agent": "jev",
        "steps": steps,
        "score": info_score(info),
        "flaps": flaps,
        "fallbacks": fallbacks,
        "source": last_source,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agent",
        choices=("random", "heuristic", "jev"),
        default="heuristic",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--no-fallback", action="store_true")
    args = parser.parse_args()
    if args.agent == "jev":
        result = asyncio.run(
            play_jev_episode(seed=args.seed, use_fallback=not args.no_fallback)
        )
    else:
        result = play_episode(args.agent, seed=args.seed)
    print(
        f"episode_done agent={result['agent']} source={result['source']} "
        f"steps={result['steps']} score={result['score']} "
        f"flaps={result['flaps']} fallbacks={result['fallbacks']}"
    )


if __name__ == "__main__":
    main()

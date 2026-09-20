"""Print one named Jev state from a live env observation (no screenshots)."""

import json

from backend.game import make_env
from backend.state import info_score, observation_to_state


def main() -> None:
    env = make_env()
    try:
        obs, info = env.reset()
        state = observation_to_state(obs, score=info_score(info))
        print(json.dumps(state, indent=2))
    finally:
        env.close()


if __name__ == "__main__":
    main()

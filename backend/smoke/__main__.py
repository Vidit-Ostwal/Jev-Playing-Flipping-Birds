"""Run every smoke check in one command: `python -m backend.smoke`."""

from backend.smoke import env, state, ws


def main() -> None:
    env.main()
    state.main()
    ws.main()


if __name__ == "__main__":
    main()

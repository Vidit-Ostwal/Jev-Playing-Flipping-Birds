"""Play one random episode headless and save a single rgb_array frame."""

from pathlib import Path

from backend.game import make_env, save_rgb_frame

FRAME_PATH = Path("artifacts/random_frame.png")


def main() -> None:
    env = make_env()
    obs, info = env.reset()
    steps = 0
    saved = False

    try:
        while True:
            action = env.action_space.sample()
            obs, _reward, terminated, truncated, info = env.step(action)
            steps += 1

            if not saved:
                frame = env.render()
                if frame is None:
                    raise RuntimeError("env.render() returned None; expected rgb_array")
                save_rgb_frame(frame, FRAME_PATH)
                saved = True
                print(
                    f"saved {FRAME_PATH} shape={tuple(frame.shape)} "
                    f"obs_shape={tuple(obs.shape)}"
                )

            if terminated or truncated:
                break
    finally:
        env.close()

    print(f"episode_done steps={steps} score={info['score']}")


if __name__ == "__main__":
    main()

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "hide")

import base64
from io import BytesIO
from pathlib import Path

import flappy_bird_gymnasium  # noqa: F401  registers FlappyBird-v0
import gymnasium
import numpy as np
import pygame
from PIL import Image


def make_env(*, render_mode: str = "rgb_array", use_lidar: bool = False):
    """Create the numeric-state Flappy Bird env with headless rendering."""
    return gymnasium.make(
        "FlappyBird-v0",
        render_mode=render_mode,
        use_lidar=use_lidar,
        audio_on=False,
    )


def save_rgb_frame(frame: np.ndarray, path: Path) -> None:
    """Write an HxWx3 rgb_array frame to disk as a PNG."""
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1, 1))

    surface = pygame.surfarray.make_surface(np.transpose(frame, (1, 0, 2)))
    path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surface, str(path))


def encode_jpeg_b64(frame: np.ndarray, *, quality: int = 70) -> str:
    """Return a base64 JPEG for an HxWx3 rgb_array frame."""
    buffer = BytesIO()
    Image.fromarray(frame).save(buffer, format="JPEG", quality=quality)
    return base64.b64encode(buffer.getvalue()).decode("ascii")

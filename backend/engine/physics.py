"""What one flap does in FlappyBird-v0.

The bird's x never changes. Pipes move left, so a step only buys
horizontal closing speed. A flap sets upward velocity for that step.
"""

SCREEN_W = 288
SCREEN_H = 512
PIPE_STEP_X_PX = 4
FLAP_STEP_Y_PX = -9
GRAVITY_Y_PX = 1
# After a flap, vy is -9, -8, ... -1 if every later action is noop.
FLAP_RISE_FRAMES = 9
FLAP_FULL_RISE_Y_PX = -45  # -(9+8+...+1)
FLAP_RISE_WORLD_X_PX = PIPE_STEP_X_PX * FLAP_RISE_FRAMES


def flap_effect(*, normalized: bool = True) -> dict:
    """Pixel and optional screen-normalized effect of one flap."""
    if normalized:
        return {
            "bird_x_is_fixed": True,
            "y_grows_downward": True,
            "one_step_world_x": PIPE_STEP_X_PX / SCREEN_W,
            "one_flap_y_this_step": FLAP_STEP_Y_PX / SCREEN_H,
            "one_flap_full_rise_y": FLAP_FULL_RISE_Y_PX / SCREEN_H,
            "one_flap_full_rise_world_x": FLAP_RISE_WORLD_X_PX / SCREEN_W,
            "gravity_y_per_step": GRAVITY_Y_PX / SCREEN_H,
            "units": "fraction of screen; x=288 y=512",
        }
    return {
        "bird_x_is_fixed": True,
        "y_grows_downward": True,
        "one_step_world_x_px": PIPE_STEP_X_PX,
        "one_flap_y_this_step_px": FLAP_STEP_Y_PX,
        "one_flap_full_rise_y_px": FLAP_FULL_RISE_Y_PX,
        "one_flap_full_rise_world_x_px": FLAP_RISE_WORLD_X_PX,
        "gravity_y_per_step_px": GRAVITY_Y_PX,
        "units": "pixels",
    }

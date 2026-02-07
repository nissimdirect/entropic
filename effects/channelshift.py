"""
Entropic — Channel Shift Effect
Offsets RGB channels independently to create chromatic aberration.
"""

import numpy as np


def channelshift(frame: np.ndarray, r_offset: tuple = (10, 0),
                 g_offset: tuple = (0, 0), b_offset: tuple = (-10, 0)) -> np.ndarray:
    """Shift R, G, B channels by independent x,y pixel offsets.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        r_offset: (x, y) pixel shift for red channel.
        g_offset: (x, y) pixel shift for green channel.
        b_offset: (x, y) pixel shift for blue channel.

    Returns:
        Channel-shifted frame.
    """
    result = np.zeros_like(frame)

    for ch_idx, (dx, dy) in enumerate([r_offset, g_offset, b_offset]):
        dx, dy = int(dx), int(dy)
        channel = frame[:, :, ch_idx]
        result[:, :, ch_idx] = np.roll(np.roll(channel, dx, axis=1), dy, axis=0)

    return result

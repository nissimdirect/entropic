"""
Entropic — Bit Crush Effect
Reduces color depth (posterization) and/or spatial resolution.
"""

import numpy as np
from PIL import Image


def bitcrush(frame: np.ndarray, color_depth: int = 4,
             resolution_scale: float = 1.0) -> np.ndarray:
    """Reduce color depth and/or resolution.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        color_depth: Bits per channel (1-8). 8 = no change, 1 = black/white.
        resolution_scale: 0.1-1.0. Downscale then upscale for mosaic/pixel effect.

    Returns:
        Bit-crushed frame.
    """
    result = frame.copy()
    h, w, _ = result.shape

    # Color depth reduction (posterization)
    color_depth = max(1, min(8, int(color_depth)))
    if color_depth < 8:
        levels = 2 ** color_depth
        step = 256 / levels
        result = (np.floor(result.astype(np.float32) / step) * step).astype(np.uint8)

    # Resolution reduction (pixel mosaic)
    resolution_scale = max(0.05, min(1.0, float(resolution_scale)))
    if resolution_scale < 1.0:
        new_w = max(2, int(w * resolution_scale))
        new_h = max(2, int(h * resolution_scale))
        img = Image.fromarray(result)
        # Downscale with nearest neighbor (blocky), then upscale back
        small = img.resize((new_w, new_h), Image.Resampling.NEAREST)
        result = np.array(small.resize((w, h), Image.Resampling.NEAREST))

    return result

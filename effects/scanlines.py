"""
Entropic — Scan Lines Effect
Overlays CRT/VHS-style scan lines with optional flicker.
"""

import numpy as np
import random


def scanlines(frame: np.ndarray, line_width: int = 2, opacity: float = 0.3,
              flicker: bool = False, color: tuple = (0, 0, 0)) -> np.ndarray:
    """Overlay horizontal scan lines.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        line_width: Width of each dark line in pixels.
        opacity: 0.0 (invisible) to 1.0 (fully black lines).
        flicker: Randomize opacity per line for CRT flicker effect.
        color: RGB tuple for line color (default black).

    Returns:
        Frame with scan lines.
    """
    result = frame.astype(np.float32)
    h, w, _ = result.shape

    # Clamp parameters to prevent crashes
    line_width = max(1, int(line_width))
    opacity = max(0.0, min(1.0, float(opacity)))
    flicker = bool(flicker)

    # Normalize color to 3-element RGB — UI may send [value, 0] from 'xy' knob
    if isinstance(color, (int, float)):
        color = (int(color), int(color), int(color))
    elif isinstance(color, (tuple, list)):
        if len(color) < 3:
            color = list(color) + [0] * (3 - len(color))
        color = tuple(int(max(0, min(255, c))) for c in color[:3])
    else:
        color = (0, 0, 0)

    line_color = np.array(color, dtype=np.float32)

    # Generate scan line pattern
    spacing = line_width * 2  # lines + gaps
    for y in range(0, h, spacing):
        end_y = min(y + line_width, h)
        line_opacity = opacity
        if flicker:
            line_opacity = opacity * (0.5 + 0.5 * random.random())

        result[y:end_y] = result[y:end_y] * (1 - line_opacity) + line_color * line_opacity

    return np.clip(result, 0, 255).astype(np.uint8)

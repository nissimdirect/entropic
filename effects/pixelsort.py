"""
Entropic — Pixel Sort Effect
Sorts pixels in rows or columns by brightness, hue, or saturation.
Classic glitch art effect.
"""

import numpy as np


def _brightness(pixels):
    """Luminance: 0.299R + 0.587G + 0.114B"""
    return 0.299 * pixels[:, 0] + 0.587 * pixels[:, 1] + 0.114 * pixels[:, 2]


def _hue(pixels):
    """Hue from RGB (simplified — uses arctan2 on color opponents)."""
    r, g, b = pixels[:, 0].astype(float), pixels[:, 1].astype(float), pixels[:, 2].astype(float)
    return np.arctan2(np.sqrt(3) * (g - b), 2 * r - g - b)


def _saturation(pixels):
    """Saturation: (max - min) / max for each pixel."""
    mx = pixels.max(axis=1).astype(float)
    mn = pixels.min(axis=1).astype(float)
    sat = np.zeros_like(mx)
    mask = mx > 0
    sat[mask] = (mx[mask] - mn[mask]) / mx[mask]
    return sat


SORT_KEYS = {
    "brightness": _brightness,
    "hue": _hue,
    "saturation": _saturation,
}


def pixelsort(frame: np.ndarray, threshold: float = 0.5, sort_by: str = "brightness",
              direction: str = "horizontal") -> np.ndarray:
    """Sort pixels in each row (or column) within threshold-defined intervals.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        threshold: 0.0-1.0 — pixels above this value get sorted. Lower = more sorting.
        sort_by: 'brightness', 'hue', or 'saturation'.
        direction: 'horizontal' or 'vertical'.

    Returns:
        Sorted frame.
    """
    result = frame.copy()
    sort_fn = SORT_KEYS.get(sort_by, _brightness)

    if direction == "vertical":
        result = result.transpose(1, 0, 2)  # Swap H and W

    h, w, _ = result.shape
    threshold_val = threshold * 255

    for row_idx in range(h):
        row = result[row_idx]
        keys = sort_fn(row)

        # Find intervals where pixels exceed threshold
        if sort_by == "brightness":
            mask = keys > threshold_val
        else:
            # For hue/saturation, normalize and use threshold directly
            normalized = (keys - keys.min()) / (keys.max() - keys.min() + 1e-8) * 255
            mask = normalized > threshold_val

        # Find contiguous runs of True in mask
        changes = np.diff(mask.astype(int))
        starts = np.where(changes == 1)[0] + 1
        ends = np.where(changes == -1)[0] + 1

        # Handle edge cases
        if mask[0]:
            starts = np.concatenate([[0], starts])
        if mask[-1]:
            ends = np.concatenate([ends, [w]])

        # Sort each interval
        for start, end in zip(starts, ends):
            if end - start < 2:
                continue
            segment = row[start:end]
            seg_keys = sort_fn(segment)
            order = np.argsort(seg_keys)
            result[row_idx, start:end] = segment[order]

    if direction == "vertical":
        result = result.transpose(1, 0, 2)

    return result

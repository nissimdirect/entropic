"""Entropic — Spatial Parameter Modulation (Gravity Concentrations)

Place attraction points on the frame that control where effects are visible.
Effects at full strength near gravity points, fading to zero away from them.
"""

import numpy as np


def compute_gravity_mask(
    points: list[dict],
    frame_shape: tuple,
    falloff: str = "gaussian",
) -> np.ndarray:
    """Generate a weight mask from gravity points.

    Args:
        points: List of gravity point dicts, each with:
            - x: float (0-1, normalized horizontal position)
            - y: float (0-1, normalized vertical position)
            - radius: float (0-1, normalized radius relative to min(h,w))
            - strength: float (0-1, peak intensity at center)
            - falloff: str ("gaussian", "linear", "cosine", "step")
        frame_shape: (h, w) or (h, w, c) tuple
        falloff: Default falloff type if not specified per-point

    Returns:
        np.ndarray: (h, w) float32 mask with values 0-1.
        0 = no effect, 1 = full effect.
        When no points provided, returns all-ones mask (no spatial restriction).
    """
    h, w = frame_shape[0], frame_shape[1]

    if not points:
        return np.ones((h, w), dtype=np.float32)

    mask = np.zeros((h, w), dtype=np.float32)

    # Precompute pixel coordinate grids (center of each pixel)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    min_dim = min(h, w)

    for pt in points:
        px = pt.get("x", 0.5) * w
        py = pt.get("y", 0.5) * h
        r_pixels = pt.get("radius", 0.1) * min_dim
        strength = float(pt.get("strength", 1.0))
        pt_falloff = pt.get("falloff", falloff)

        # Distance from this gravity point
        dist = np.sqrt((xx - px) ** 2 + (yy - py) ** 2)

        if r_pixels <= 0:
            # Zero radius: no contribution
            continue

        blob = _compute_blob(dist, r_pixels, pt_falloff)
        blob *= strength

        # Combine via maximum (avoids exceeding 1.0)
        np.maximum(mask, blob, out=mask)

    np.clip(mask, 0.0, 1.0, out=mask)
    return mask


def _compute_blob(
    dist: np.ndarray, r: float, falloff: str
) -> np.ndarray:
    """Compute a single falloff blob."""
    if falloff == "gaussian":
        # 3-sigma at radius edge so it fades nicely
        return np.exp(-(dist ** 2) / (2.0 * r ** 2))
    elif falloff == "linear":
        return np.maximum(0.0, 1.0 - dist / r).astype(np.float32)
    elif falloff == "cosine":
        blob = np.where(
            dist < r,
            0.5 * (1.0 + np.cos(np.pi * dist / r)),
            0.0,
        )
        return blob.astype(np.float32)
    elif falloff == "step":
        return np.where(dist < r, 1.0, 0.0).astype(np.float32)
    else:
        # Unknown falloff, default to gaussian
        return np.exp(-(dist ** 2) / (2.0 * r ** 2))

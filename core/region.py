"""
Entropic — Region Selection
Apply effects to a rectangular sub-region of the frame.

Region spec formats:
    - Pixels: "100,50,400,300"  (x, y, width, height)
    - Percent: "0.25,0.1,0.5,0.8" (values 0.0-1.0 interpreted as percentages)
    - Preset: "center", "top-half", "bottom-half", "left-half", "right-half"
    - Dict: {"x": 100, "y": 50, "w": 400, "h": 300}

Edge blend: Optional feathered edge for smooth transitions (0 = hard edge).
"""

import numpy as np


# Named region presets (as percentage of frame)
REGION_PRESETS = {
    "center":       (0.25, 0.25, 0.50, 0.50),
    "top-half":     (0.00, 0.00, 1.00, 0.50),
    "bottom-half":  (0.00, 0.50, 1.00, 0.50),
    "left-half":    (0.00, 0.00, 0.50, 1.00),
    "right-half":   (0.50, 0.00, 0.50, 1.00),
    "top-left":     (0.00, 0.00, 0.50, 0.50),
    "top-right":    (0.50, 0.00, 0.50, 0.50),
    "bottom-left":  (0.00, 0.50, 0.50, 0.50),
    "bottom-right": (0.50, 0.50, 0.50, 0.50),
    "center-strip": (0.00, 0.33, 1.00, 0.34),
    "thirds-left":  (0.00, 0.00, 0.33, 1.00),
    "thirds-center":(0.33, 0.00, 0.34, 1.00),
    "thirds-right": (0.66, 0.00, 0.34, 1.00),
}

# Limits
MAX_FEATHER = 100


class RegionError(Exception):
    """Invalid region specification."""
    pass


def parse_region(spec, frame_height: int, frame_width: int) -> tuple[int, int, int, int]:
    """Parse a region spec into absolute pixel coordinates (x, y, w, h).

    Args:
        spec: Region specification — string, dict, tuple, list, or None.
        frame_height: Frame height in pixels.
        frame_width: Frame width in pixels.

    Returns:
        (x, y, w, h) in absolute pixels, clamped to frame bounds.

    Raises:
        RegionError: If the spec is invalid.
    """
    if spec is None:
        return (0, 0, frame_width, frame_height)

    # Preset name
    if isinstance(spec, str):
        if spec in REGION_PRESETS:
            px, py, pw, ph = REGION_PRESETS[spec]
            return _percent_to_pixels(px, py, pw, ph, frame_width, frame_height)

        # Parse "x,y,w,h" string
        parts = spec.replace(" ", "").split(",")
        if len(parts) != 4:
            raise RegionError(
                f"Region must be 'x,y,w,h' or a preset name. Got: '{spec}'. "
                f"Presets: {', '.join(sorted(REGION_PRESETS.keys()))}"
            )
        try:
            values = [float(p) for p in parts]
        except ValueError:
            raise RegionError(f"Region values must be numbers. Got: '{spec}'")

        # Check for percent mode (all values between 0 and 1)
        if all(0.0 <= v <= 1.0 for v in values):
            # Could be pixels 0,0,1,1 or percentages — treat as percent
            # if ALL values are <= 1.0
            return _percent_to_pixels(*values, frame_width, frame_height)
        else:
            return _validate_pixels(int(values[0]), int(values[1]),
                                    int(values[2]), int(values[3]),
                                    frame_width, frame_height)

    # Dict: {"x": ..., "y": ..., "w": ..., "h": ...}
    if isinstance(spec, dict):
        try:
            x = float(spec.get("x", 0))
            y = float(spec.get("y", 0))
            w = float(spec.get("w", frame_width))
            h = float(spec.get("h", frame_height))
        except (TypeError, ValueError) as e:
            raise RegionError(f"Invalid region dict values: {e}")

        if all(0.0 <= v <= 1.0 for v in [x, y, w, h]):
            return _percent_to_pixels(x, y, w, h, frame_width, frame_height)
        return _validate_pixels(int(x), int(y), int(w), int(h),
                                frame_width, frame_height)

    # Tuple/List: (x, y, w, h)
    if isinstance(spec, (tuple, list)):
        if len(spec) != 4:
            raise RegionError(f"Region tuple must have 4 values (x,y,w,h). Got {len(spec)}.")
        x, y, w, h = [float(v) for v in spec]
        if all(0.0 <= v <= 1.0 for v in [x, y, w, h]):
            return _percent_to_pixels(x, y, w, h, frame_width, frame_height)
        return _validate_pixels(int(x), int(y), int(w), int(h),
                                frame_width, frame_height)

    raise RegionError(f"Unknown region spec type: {type(spec).__name__}")


def _percent_to_pixels(px, py, pw, ph, frame_w, frame_h):
    """Convert percentage-based region to pixel coordinates."""
    x = int(px * frame_w)
    y = int(py * frame_h)
    w = int(pw * frame_w)
    h = int(ph * frame_h)
    return _validate_pixels(x, y, w, h, frame_w, frame_h)


def _validate_pixels(x, y, w, h, frame_w, frame_h):
    """Validate and clamp pixel coordinates to frame bounds."""
    if w <= 0 or h <= 0:
        raise RegionError(f"Region size must be positive. Got w={w}, h={h}")
    if x < 0 or y < 0:
        raise RegionError(f"Region position must be non-negative. Got x={x}, y={y}")

    # Clamp to frame bounds
    x = min(x, frame_w - 1)
    y = min(y, frame_h - 1)
    w = min(w, frame_w - x)
    h = min(h, frame_h - y)

    # Final sanity check
    if w <= 0 or h <= 0:
        raise RegionError(
            f"Region has zero area after clamping to frame ({frame_w}x{frame_h}). "
            f"Got x={x}, y={y}, w={w}, h={h}"
        )

    return (x, y, w, h)


def create_feather_mask(w: int, h: int, feather: int = 0) -> np.ndarray:
    """Create a feathered alpha mask for smooth region blending.

    Args:
        w: Region width.
        h: Region height.
        feather: Feather radius in pixels (0 = hard edge).

    Returns:
        Float32 mask array (h, w) with values 0.0 to 1.0.
    """
    feather = max(0, min(feather, MAX_FEATHER, w // 2, h // 2))

    if feather == 0:
        return np.ones((h, w), dtype=np.float32)

    mask = np.ones((h, w), dtype=np.float32)

    # Create linear ramps for each edge
    for i in range(feather):
        alpha = (i + 1) / (feather + 1)
        # Top edge
        mask[i, :] = np.minimum(mask[i, :], alpha)
        # Bottom edge
        mask[h - 1 - i, :] = np.minimum(mask[h - 1 - i, :], alpha)
        # Left edge
        mask[:, i] = np.minimum(mask[:, i], alpha)
        # Right edge
        mask[:, w - 1 - i] = np.minimum(mask[:, w - 1 - i], alpha)

    return mask


def apply_to_region(frame: np.ndarray, effect_fn, region_spec,
                    feather: int = 0, **effect_params) -> np.ndarray:
    """Apply an effect function only to a region of the frame.

    Args:
        frame: Input frame (H, W, 3) uint8.
        effect_fn: Callable that takes (frame, **params) -> frame.
        region_spec: Region specification (string, dict, tuple, or None).
        feather: Feather radius for edge blending (0 = hard edge).
        **effect_params: Parameters to pass to the effect function.

    Returns:
        Frame with effect applied only in the specified region.
    """
    h, w = frame.shape[:2]
    rx, ry, rw, rh = parse_region(region_spec, h, w)

    # Full frame — no masking needed
    if rx == 0 and ry == 0 and rw == w and rh == h and feather == 0:
        return effect_fn(frame, **effect_params)

    # Extract sub-region
    sub = frame[ry:ry + rh, rx:rx + rw].copy()

    # Apply effect to sub-region
    processed_sub = effect_fn(sub, **effect_params)

    # Ensure output matches input shape
    if processed_sub.shape != sub.shape:
        # Effect changed dimensions — resize back
        import cv2
        processed_sub = cv2.resize(processed_sub, (rw, rh))
    if processed_sub.dtype != np.uint8:
        processed_sub = np.clip(processed_sub, 0, 255).astype(np.uint8)

    # Composite back
    result = frame.copy()

    if feather > 0:
        mask = create_feather_mask(rw, rh, feather)
        mask_3d = mask[:, :, np.newaxis]  # Broadcast to 3 channels
        blended = (processed_sub.astype(np.float32) * mask_3d +
                   sub.astype(np.float32) * (1.0 - mask_3d))
        result[ry:ry + rh, rx:rx + rw] = np.clip(blended, 0, 255).astype(np.uint8)
    else:
        result[ry:ry + rh, rx:rx + rw] = processed_sub

    return result


def list_presets() -> dict:
    """Return all available region presets."""
    return REGION_PRESETS.copy()

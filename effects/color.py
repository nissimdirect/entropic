"""
Entropic — Color Manipulation Effects
Hue shift, contrast, saturation, exposure, invert, temperature.
"""

import numpy as np
import cv2


def hue_shift(frame: np.ndarray, degrees: float = 180) -> np.ndarray:
    """Rotate the hue wheel by N degrees.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        degrees: 0-360 degree rotation.

    Returns:
        Hue-shifted frame.
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV).astype(np.float32)
    # OpenCV hue is 0-179 (half-degrees)
    hsv[:, :, 0] = (hsv[:, :, 0] + degrees / 2) % 180
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)


def contrast_crush(frame: np.ndarray, amount: float = 50,
                   curve: str = "linear") -> np.ndarray:
    """Extreme contrast manipulation.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        amount: -100 (flatten) to 100 (extreme contrast).
        curve: 'linear', 's_curve', or 'hard'.

    Returns:
        Contrast-modified frame.
    """
    f = frame.astype(np.float32) / 255.0
    amount = max(-100, min(100, float(amount)))

    if curve == "hard":
        # Hard threshold — push toward black and white
        threshold = 0.5 - (amount / 200)
        f = np.where(f > threshold, 1.0, 0.0)
    elif curve == "s_curve":
        # S-curve contrast using sigmoid
        strength = 1 + abs(amount) / 20
        if amount >= 0:
            f = 1.0 / (1.0 + np.exp(-strength * (f - 0.5) * 10))
        else:
            # Flatten: compress toward midpoint
            f = 0.5 + (f - 0.5) * (1 - abs(amount) / 100)
    else:
        # Linear contrast
        factor = (259 * (amount + 255)) / (255 * (259 - amount))
        f = factor * (f - 0.5) + 0.5

    return np.clip(f * 255, 0, 255).astype(np.uint8)


def saturation_warp(frame: np.ndarray, amount: float = 1.5,
                    channel: str = "all") -> np.ndarray:
    """Boost or kill saturation.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        amount: 0.0 (grayscale) to 5.0 (hypersaturated). 1.0 = no change.
        channel: 'all', 'r', 'g', or 'b'.

    Returns:
        Saturation-modified frame.
    """
    amount = max(0.0, min(5.0, float(amount)))

    if channel == "all":
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * amount, 0, 255)
        return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
    else:
        # Per-channel: desaturate/boost a single channel
        ch_map = {"r": 0, "g": 1, "b": 2}
        ch_idx = ch_map.get(channel, 0)
        result = frame.copy().astype(np.float32)
        gray = np.mean(result, axis=2, keepdims=True)
        # Blend channel between gray and original based on amount
        result[:, :, ch_idx] = np.clip(
            gray[:, :, 0] + (result[:, :, ch_idx] - gray[:, :, 0]) * amount,
            0, 255,
        )
        return result.astype(np.uint8)


def brightness_exposure(frame: np.ndarray, stops: float = 1.0,
                        clip_mode: str = "clip") -> np.ndarray:
    """Push exposure up or down in stops.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        stops: -3.0 (dark) to 3.0 (bright). 0 = no change.
        clip_mode: 'clip' (hard clip at 255), 'wrap' (overflow wraps), 'mirror' (bounces).

    Returns:
        Exposure-modified frame.
    """
    stops = max(-3.0, min(3.0, float(stops)))
    multiplier = 2.0 ** stops

    f = frame.astype(np.float32) * multiplier

    if clip_mode == "wrap":
        f = np.mod(f, 256)
    elif clip_mode == "mirror":
        # Values above 255 bounce back down
        f = np.abs(np.mod(f, 510) - 255)
        f = 255 - np.abs(f - 255)
    else:
        f = np.clip(f, 0, 255)

    return f.astype(np.uint8)


def color_invert(frame: np.ndarray, channel: str = "all",
                 amount: float = 1.0) -> np.ndarray:
    """Full or partial color inversion.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        channel: 'all', 'r', 'g', or 'b'.
        amount: 0.0 (no inversion) to 1.0 (full inversion).

    Returns:
        Inverted frame.
    """
    amount = max(0.0, min(1.0, float(amount)))
    result = frame.astype(np.float32)

    if channel == "all":
        inverted = 255.0 - result
        result = result * (1 - amount) + inverted * amount
    else:
        ch_map = {"r": 0, "g": 1, "b": 2}
        ch_idx = ch_map.get(channel, 0)
        inverted = 255.0 - result[:, :, ch_idx]
        result[:, :, ch_idx] = result[:, :, ch_idx] * (1 - amount) + inverted * amount

    return np.clip(result, 0, 255).astype(np.uint8)


def color_temperature(frame: np.ndarray, temp: float = 30) -> np.ndarray:
    """Warm/cool color temperature shift.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        temp: -100 (cool/blue) to 100 (warm/orange). 0 = no change.

    Returns:
        Temperature-shifted frame.
    """
    temp = max(-100, min(100, float(temp)))
    result = frame.astype(np.float32)

    # Warm = boost red, reduce blue. Cool = boost blue, reduce red.
    shift = temp / 100.0 * 40  # Max ±40 per channel
    result[:, :, 0] = np.clip(result[:, :, 0] + shift, 0, 255)       # Red
    result[:, :, 2] = np.clip(result[:, :, 2] - shift, 0, 255)       # Blue
    # Slight green adjustment for natural look
    result[:, :, 1] = np.clip(result[:, :, 1] + shift * 0.1, 0, 255)  # Green

    return result.astype(np.uint8)


def tape_saturation(frame: np.ndarray, drive: float = 1.5,
                    warmth: float = 0.3) -> np.ndarray:
    """Audio tape saturation curve applied to pixel brightness.

    Warm, compressed highlights with soft roll-off — exactly like
    analog tape soft-clips audio signals.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        drive: Input gain before saturation (0.5-5.0). Higher = more squash.
        warmth: Warm color tint amount (0.0-1.0).

    Returns:
        Tape-saturated frame.
    """
    drive = max(0.5, min(5.0, float(drive)))
    warmth = max(0.0, min(1.0, float(warmth)))
    f = frame.astype(np.float32) / 255.0
    f = np.tanh(f * drive) / np.tanh(drive)
    if warmth > 0:
        f[:, :, 0] = np.clip(f[:, :, 0] + warmth * 0.05, 0, 1)
        f[:, :, 2] = np.clip(f[:, :, 2] - warmth * 0.03, 0, 1)
    return np.clip(f * 255, 0, 255).astype(np.uint8)


def cyanotype(frame: np.ndarray, intensity: float = 1.0) -> np.ndarray:
    """Cyanotype photographic print simulation (Prussian blue tones).

    Maps luminance to blue-and-white palette like 19th century
    cyanotype prints (blueprints, Anna Atkins botanical prints).

    Args:
        frame: (H, W, 3) uint8 RGB array.
        intensity: Effect strength (0.0 = original, 1.0 = full cyanotype).

    Returns:
        Cyanotype-tinted frame.
    """
    intensity = max(0.0, min(1.0, float(intensity)))
    gray = np.mean(frame.astype(np.float32), axis=2)
    r = np.clip(gray * 0.3, 0, 255)
    g = np.clip(gray * 0.5, 0, 255)
    b = np.clip(gray * 0.9 + 30, 0, 255)
    cyan = np.stack([r, g, b], axis=2)
    result = frame.astype(np.float32) * (1 - intensity) + cyan * intensity
    return np.clip(result, 0, 255).astype(np.uint8)


def infrared(frame: np.ndarray, vegetation_glow: float = 1.0) -> np.ndarray:
    """Simulate infrared film photography.

    Vegetation glows white (greens become bright), sky darkens (blues reduce),
    reds shift to green channel. Classic Kodak Aerochrome / IR film look.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        vegetation_glow: How bright greens become (0.0-2.0).

    Returns:
        Infrared-simulated frame.
    """
    vegetation_glow = max(0.0, min(2.0, float(vegetation_glow)))
    f = frame.astype(np.float32)
    r = np.clip(f[:, :, 1] * vegetation_glow + f[:, :, 0] * 0.3, 0, 255)
    g = np.clip(f[:, :, 0] * 0.8, 0, 255)
    b = np.clip(f[:, :, 2] * 0.3, 0, 255)
    return np.stack([r, g, b], axis=2).astype(np.uint8)


def chroma_key(frame: np.ndarray, hue: float = 120.0, tolerance: float = 30.0,
               softness: float = 10.0, replace_color: str = "black") -> np.ndarray:
    """Green screen / chroma key — makes a specific color range transparent (black).

    Converts to HSV, creates a mask for the target hue range, then replaces
    those pixels. Use with blend modes and layer opacity for real transparency.

    Args:
        frame: (H, W, 3) uint8 RGB.
        hue: Target hue to key out in degrees (0-360). 120 = green, 0 = red, 240 = blue.
        tolerance: Hue range to key (degrees). Higher = wider key.
        softness: Edge feathering (0 = hard edge, 50 = very soft).
        replace_color: What to put where keyed pixels were. "black" or "white".

    Returns:
        Frame with keyed areas replaced.
    """
    import cv2

    hue = float(hue) % 360
    tolerance = max(1.0, min(180.0, float(tolerance)))
    softness = max(0.0, min(50.0, float(softness)))

    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    # OpenCV HSV: H is 0-179 (half degrees), S and V are 0-255
    h_center = hue / 2.0  # Convert 360-scale to 180-scale
    h_low = (h_center - tolerance / 2.0) % 180
    h_high = (h_center + tolerance / 2.0) % 180

    h = hsv[:, :, 0].astype(np.float32)
    s = hsv[:, :, 1].astype(np.float32)

    # Create hue mask (handle wraparound)
    if h_low < h_high:
        hue_mask = (h >= h_low) & (h <= h_high)
    else:
        hue_mask = (h >= h_low) | (h <= h_high)

    # Require minimum saturation (don't key grays)
    sat_mask = s > 30

    mask = (hue_mask & sat_mask).astype(np.float32)

    # Soften edges with blur
    if softness > 0:
        ksize = int(softness * 2) | 1  # Ensure odd
        mask = cv2.GaussianBlur(mask, (ksize, ksize), 0)

    # Apply mask: keyed areas become replace color
    mask_3ch = mask[:, :, np.newaxis]
    fill = 0.0 if replace_color == "black" else 255.0
    result = frame.astype(np.float32) * (1.0 - mask_3ch) + fill * mask_3ch
    return np.clip(result, 0, 255).astype(np.uint8)


def luma_key(frame: np.ndarray, threshold: float = 0.3, mode: str = "dark",
             softness: float = 10.0) -> np.ndarray:
    """Luminance key — makes dark or bright areas transparent (black).

    Keys out pixels based on their brightness. Use "dark" to remove shadows/dark
    areas (so bright content shows through), or "light" to remove bright areas.

    Args:
        frame: (H, W, 3) uint8 RGB.
        threshold: Brightness cutoff (0-1). Pixels beyond this threshold are keyed.
        mode: "dark" = key out dark areas, "light" = key out bright areas.
        softness: Edge feathering (0 = hard, 50 = very soft).

    Returns:
        Frame with keyed areas replaced with black.
    """
    import cv2

    threshold = max(0.0, min(1.0, float(threshold)))
    softness = max(0.0, min(50.0, float(softness)))

    # Convert to grayscale for luminance
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0

    # Create mask based on mode
    if mode == "dark":
        # Key out dark areas: pixels darker than threshold become transparent
        mask = (gray < threshold).astype(np.float32)
    else:
        # Key out light areas: pixels brighter than threshold become transparent
        mask = (gray > threshold).astype(np.float32)

    # Soften edges
    if softness > 0:
        ksize = int(softness * 2) | 1
        mask = cv2.GaussianBlur(mask, (ksize, ksize), 0)

    # Apply mask: keyed areas become black
    mask_3ch = mask[:, :, np.newaxis]
    result = frame.astype(np.float32) * (1.0 - mask_3ch)
    return np.clip(result, 0, 255).astype(np.uint8)

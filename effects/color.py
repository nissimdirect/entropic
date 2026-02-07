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

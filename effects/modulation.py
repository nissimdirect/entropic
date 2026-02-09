"""
Entropic — Modulation Effects
Per-frame effects inspired by audio synthesis modulation techniques.
"""

import numpy as np


def ring_mod(
    frame: np.ndarray,
    frequency: float = 4.0,
    direction: str = "horizontal",
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Multiply frame by a sine wave carrier, like audio ring modulation.

    Creates alternating bright/dark bands that shift over time.

    Args:
        frame: Input frame (H, W, 3) uint8.
        frequency: Carrier frequency (cycles across frame width/height).
        direction: "horizontal", "vertical", or "radial".
        frame_index: Current frame number (shifts the pattern over time).
        total_frames: Total frame count.

    Returns:
        Frame modulated by sine carrier.
    """
    frequency = max(0.5, min(50.0, float(frequency)))
    h, w = frame.shape[:2]

    # Phase shifts with frame_index for animation
    phase = frame_index * 0.1

    if direction == "vertical":
        coords = np.arange(h).reshape(-1, 1)
        carrier = 0.5 + 0.5 * np.sin(2.0 * np.pi * frequency * coords / h + phase)
        carrier = carrier[:, :, np.newaxis]  # (H, 1, 1)
    elif direction == "radial":
        cy, cx = h / 2, w / 2
        y = np.arange(h).reshape(-1, 1) - cy
        x = np.arange(w).reshape(1, -1) - cx
        dist = np.sqrt(x**2 + y**2)
        max_dist = np.sqrt(cx**2 + cy**2)
        carrier = 0.5 + 0.5 * np.sin(2.0 * np.pi * frequency * dist / max_dist + phase)
        carrier = carrier[:, :, np.newaxis]  # (H, W, 1)
    else:  # horizontal
        coords = np.arange(w).reshape(1, -1)
        carrier = 0.5 + 0.5 * np.sin(2.0 * np.pi * frequency * coords / w + phase)
        carrier = carrier[:, :, np.newaxis]  # (1, W, 1)

    result = np.clip(frame.astype(np.float32) * carrier, 0, 255).astype(np.uint8)
    return result


def gate(
    frame: np.ndarray,
    threshold: float = 0.3,
    mode: str = "brightness",
) -> np.ndarray:
    """Black out pixels below a brightness threshold — like a noise gate.

    In audio, a noise gate silences signals below a threshold.
    Here, pixels darker than the threshold are pushed to black.

    Args:
        frame: Input frame (H, W, 3) uint8.
        threshold: Cut-off level (0.0-1.0 of max brightness).
        mode: "brightness" (per-pixel luminance) or "channel" (per-channel).

    Returns:
        Frame with below-threshold pixels blacked out.
    """
    threshold = max(0.0, min(1.0, float(threshold)))
    threshold_val = threshold * 255.0

    if mode == "channel":
        # Per-channel: each channel independently gated
        result = frame.copy()
        result[result < threshold_val] = 0
        return result

    # Brightness mode: compute luminance, gate entire pixel
    # ITU-R BT.601 luminance weights
    luminance = (
        0.299 * frame[:, :, 0].astype(np.float32) +
        0.587 * frame[:, :, 1].astype(np.float32) +
        0.114 * frame[:, :, 2].astype(np.float32)
    )
    mask = luminance >= threshold_val
    result = frame.copy()
    result[~mask] = 0
    return result


def wavefold(
    frame: np.ndarray,
    threshold: float = 0.7,
    folds: int = 3,
) -> np.ndarray:
    """Audio wavefolding applied to pixel brightness.

    Values exceeding the threshold fold back down, creating
    psychedelic contrast and banding. Classic synth distortion technique.

    Args:
        frame: Input frame (H, W, 3) uint8.
        threshold: Fold-back point (0.1-0.95).
        folds: Number of folding passes (1-8).

    Returns:
        Wavefolded frame.
    """
    threshold = max(0.1, min(0.95, float(threshold)))
    folds = max(1, min(8, int(folds)))
    f = frame.astype(np.float32) / 255.0
    for _ in range(folds):
        f = np.where(f > threshold, 2.0 * threshold - f, f)
        f = np.abs(f)
    return np.clip(f * 255, 0, 255).astype(np.uint8)


def am_radio(
    frame: np.ndarray,
    carrier_freq: float = 10.0,
    depth: float = 0.8,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """AM radio interference — sine carrier modulation on pixel rows.

    Alternating bright/dark horizontal bands like AM radio interference
    patterns on a CRT. Animates over time.

    Args:
        frame: Input frame (H, W, 3) uint8.
        carrier_freq: Number of bands across frame height (1-100).
        depth: Modulation depth (0.0-1.0).
        frame_index: Current frame (for animation).
        total_frames: Total frames.

    Returns:
        AM-modulated frame.
    """
    carrier_freq = max(1.0, min(100.0, float(carrier_freq)))
    depth = max(0.0, min(1.0, float(depth)))
    h = frame.shape[0]
    phase = frame_index * 0.15
    rows = np.arange(h, dtype=np.float32)
    carrier = 1.0 - depth + depth * (0.5 + 0.5 * np.sin(
        2.0 * np.pi * carrier_freq * rows / h + phase
    ))
    carrier = carrier.reshape(-1, 1, 1)
    result = frame.astype(np.float32) * carrier
    return np.clip(result, 0, 255).astype(np.uint8)

"""
Entropic — Modulation Effects
Per-frame effects inspired by audio synthesis modulation techniques.
"""

import numpy as np


def ring_mod(
    frame: np.ndarray,
    frequency: float = 4.0,
    direction: str = "horizontal",
    mode: str = "am",
    depth: float = 1.0,
    source: str = "internal",
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Ring modulation — multiply frame by a carrier signal.

    Modes:
        am: Classic amplitude modulation (sine carrier on brightness).
        fm: Frequency modulation — brightness modulates carrier frequency.
        phase: Luminance shifts carrier phase per-pixel.
        multi: 3 harmonic carriers per RGB channel (rich color splitting).

    Args:
        frame: Input frame (H, W, 3) uint8.
        frequency: Carrier frequency (cycles across frame width/height).
        direction: "horizontal", "vertical", or "radial".
        mode: Modulation mode — "am", "fm", "phase", "multi".
        depth: Modulation depth (0.0-1.0). 0 = no effect, 1 = full.
        source: Carrier source — "internal" (sine) or "luminance" (self-mod).
        frame_index: Current frame number (shifts the pattern over time).
        total_frames: Total frame count.

    Returns:
        Modulated frame.
    """
    frequency = max(0.5, min(50.0, float(frequency)))
    depth = max(0.0, min(1.0, float(depth)))
    h, w = frame.shape[:2]
    f = frame.astype(np.float32)

    phase = frame_index * 0.1

    def _make_coords(freq, ph):
        if direction == "vertical":
            coords = np.arange(h, dtype=np.float32).reshape(-1, 1)
            return 2.0 * np.pi * freq * coords / h + ph
        elif direction == "radial":
            cy, cx = h / 2, w / 2
            y = np.arange(h, dtype=np.float32).reshape(-1, 1) - cy
            x = np.arange(w, dtype=np.float32).reshape(1, -1) - cx
            dist = np.sqrt(x**2 + y**2)
            max_dist = np.sqrt(cx**2 + cy**2) + 0.01
            return 2.0 * np.pi * freq * dist / max_dist + ph
        else:
            coords = np.arange(w, dtype=np.float32).reshape(1, -1)
            return 2.0 * np.pi * freq * coords / w + ph

    if mode == "fm":
        # Brightness modulates carrier frequency
        lum = np.mean(f, axis=2) / 255.0
        if source == "luminance":
            freq_mod = frequency * (1.0 + lum * depth * 2.0)
        else:
            freq_mod = frequency
        theta = _make_coords(1.0, phase)
        if theta.ndim == 2:
            carrier = 0.5 + 0.5 * np.sin(theta * freq_mod)
        else:
            carrier = 0.5 + 0.5 * np.sin(theta * freq_mod)
        carrier = carrier[:, :, np.newaxis] if carrier.ndim == 2 else carrier[:, :, np.newaxis]
        carrier = (1.0 - depth) + depth * carrier
        return np.clip(f * carrier, 0, 255).astype(np.uint8)

    elif mode == "phase":
        # Luminance shifts the phase per-pixel
        lum = np.mean(f, axis=2) / 255.0
        base_theta = _make_coords(frequency, phase)
        if base_theta.ndim == 1:
            base_theta = base_theta.reshape(1, -1) if direction != "vertical" else base_theta.reshape(-1, 1)
        phase_shift = lum * np.pi * 2.0 * depth
        carrier = 0.5 + 0.5 * np.sin(base_theta + phase_shift)
        carrier = carrier[:, :, np.newaxis]
        return np.clip(f * carrier, 0, 255).astype(np.uint8)

    elif mode == "multi":
        # 3 harmonic carriers per RGB channel
        result = np.zeros_like(f)
        for c, harmonic in enumerate([1.0, 1.5, 2.0]):
            theta = _make_coords(frequency * harmonic, phase + c * 0.7)
            if theta.ndim == 1:
                theta = theta.reshape(1, -1) if direction != "vertical" else theta.reshape(-1, 1)
            carrier = (1.0 - depth) + depth * (0.5 + 0.5 * np.sin(theta))
            result[:, :, c] = f[:, :, c] * carrier
        return np.clip(result, 0, 255).astype(np.uint8)

    else:  # am (default)
        theta = _make_coords(frequency, phase)
        if source == "luminance":
            lum = np.mean(f, axis=2) / 255.0
            carrier = 0.5 + 0.5 * np.sin(theta.reshape(theta.shape[0] if theta.ndim > 1 else 1, -1) * (1.0 + lum))
            carrier = carrier[:, :, np.newaxis]
        else:
            carrier = 0.5 + 0.5 * np.sin(theta)
            if carrier.ndim == 1:
                carrier = carrier.reshape(1, -1) if direction != "vertical" else carrier.reshape(-1, 1)
            carrier = carrier[:, :, np.newaxis]
        carrier = (1.0 - depth) + depth * carrier
        return np.clip(f * carrier, 0, 255).astype(np.uint8)


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
    brightness: float = 1.0,
) -> np.ndarray:
    """Audio wavefolding applied to pixel brightness.

    Values exceeding the threshold fold back down, creating
    psychedelic contrast and banding. Classic synth distortion technique.

    Args:
        frame: Input frame (H, W, 3) uint8.
        threshold: Fold-back point (0.1-0.95).
        folds: Number of folding passes (1-8).
        brightness: Post-fold brightness (0.5-2.0). 1.0 = no change.

    Returns:
        Wavefolded frame.
    """
    threshold = max(0.1, min(0.95, float(threshold)))
    folds = max(1, min(8, int(folds)))
    brightness = max(0.5, min(2.0, float(brightness)))
    f = frame.astype(np.float32) / 255.0
    for _ in range(folds):
        f = np.where(f > threshold, 2.0 * threshold - f, f)
        f = np.abs(f)
    f *= brightness
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

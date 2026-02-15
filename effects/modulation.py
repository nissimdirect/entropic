"""
Entropic — Modulation Effects
Per-frame effects inspired by audio synthesis modulation techniques.
"""

import numpy as np


_VALID_WAVEFORMS = {"sine", "square", "triangle", "saw"}
_VALID_DIRECTIONS = {"horizontal", "vertical", "radial", "temporal"}
_VALID_MODES = {"am", "fm", "phase", "multi"}
_VALID_SOURCES = {"internal", "luminance"}
_VALID_BANDS = {"all", "low", "mid", "high"}


def _waveform(theta: np.ndarray, shape: str = "sine") -> np.ndarray:
    """Generate carrier waveform from phase angles.

    Returns values in [0, 1] range (unipolar) for all waveform types.
    """
    if shape == "square":
        return (np.sin(theta) >= 0).astype(np.float32)
    elif shape == "triangle":
        return np.abs(2.0 * (theta / (2.0 * np.pi) % 1.0) - 1.0).astype(np.float32)
    elif shape == "saw":
        return (theta / (2.0 * np.pi) % 1.0).astype(np.float32)
    else:  # sine
        return (0.5 + 0.5 * np.sin(theta)).astype(np.float32)


def _apply_spectrum_band(frame_f: np.ndarray, result: np.ndarray, band: str) -> np.ndarray:
    """Apply ring modulation only to selected frequency band.

    Decomposes via Gaussian blur (low = blurred, high = original - blurred).
    Returns the recombined frame with only the target band modulated.
    """
    if band == "all":
        return result

    import cv2

    h, w = frame_f.shape[:2]
    ksize = max(3, (min(h, w) // 8) | 1)  # odd kernel

    low = cv2.GaussianBlur(frame_f, (ksize, ksize), 0)
    high = frame_f - low
    mid_ksize = max(3, (ksize // 2) | 1)
    mid_blur = cv2.GaussianBlur(frame_f, (mid_ksize, mid_ksize), 0)
    mid = mid_blur - low

    # result is the fully-modulated frame; frame_f is the original
    # We want: modulated band + unmodulated other bands
    if band == "low":
        import cv2 as _cv2
        mod_low = cv2.GaussianBlur(result, (ksize, ksize), 0)
        return mod_low + mid + high
    elif band == "mid":
        mod_mid_blur = cv2.GaussianBlur(result, (mid_ksize, mid_ksize), 0)
        mod_low = cv2.GaussianBlur(result, (ksize, ksize), 0)
        mod_mid = mod_mid_blur - mod_low
        return low + mod_mid + high
    elif band == "high":
        mod_low = cv2.GaussianBlur(result, (ksize, ksize), 0)
        mod_high = result - mod_low
        return low + mid + mod_high

    return result


def ring_mod(
    frame: np.ndarray,
    frequency: float = 4.0,
    direction: str = "horizontal",
    mode: str = "am",
    depth: float = 1.0,
    source: str = "internal",
    carrier_waveform: str = "sine",
    spectrum_band: str = "all",
    animation_rate: float = 1.0,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Ring modulation — multiply frame by a carrier signal.

    Modes:
        am: Classic amplitude modulation (carrier on brightness).
        fm: Frequency modulation — brightness modulates carrier frequency.
        phase: Luminance shifts carrier phase per-pixel.
        multi: 3 harmonic carriers per RGB channel (rich color splitting).

    Args:
        frame: Input frame (H, W, 3) uint8.
        frequency: Carrier frequency (cycles across frame width/height).
        direction: "horizontal", "vertical", "radial", or "temporal".
        mode: Modulation mode — "am", "fm", "phase", "multi".
        depth: Modulation depth (0.0-1.0). 0 = no effect, 1 = full.
        source: Carrier source — "internal" (generated) or "luminance" (self-mod).
        carrier_waveform: Carrier shape — "sine", "square", "triangle", "saw".
        spectrum_band: Frequency band to modulate — "all", "low", "mid", "high".
        animation_rate: Speed multiplier for temporal animation (0.0-5.0).
        frame_index: Current frame number (shifts the pattern over time).
        total_frames: Total frame count.

    Returns:
        Modulated frame.
    """
    frequency = max(0.5, min(50.0, float(frequency)))
    depth = max(0.0, min(1.0, float(depth)))
    animation_rate = max(0.0, min(5.0, float(animation_rate)))
    if carrier_waveform not in _VALID_WAVEFORMS:
        carrier_waveform = "sine"
    if direction not in _VALID_DIRECTIONS:
        direction = "horizontal"
    if mode not in _VALID_MODES:
        mode = "am"
    if source not in _VALID_SOURCES:
        source = "internal"
    if spectrum_band not in _VALID_BANDS:
        spectrum_band = "all"

    h, w = frame.shape[:2]
    f = frame.astype(np.float32)

    phase = frame_index * 0.1 * animation_rate

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
        elif direction == "temporal":
            # Uniform carrier that changes only over time (flashes)
            return np.full((h, w), 2.0 * np.pi * freq * frame_index / max(total_frames, 1) + ph, dtype=np.float32)
        else:  # horizontal
            coords = np.arange(w, dtype=np.float32).reshape(1, -1)
            return 2.0 * np.pi * freq * coords / w + ph

    def _ensure_2d(arr):
        """Ensure carrier array is (h, w)."""
        if arr.ndim == 1:
            if direction == "vertical":
                return np.broadcast_to(arr.reshape(-1, 1), (h, w))
            else:
                return np.broadcast_to(arr.reshape(1, -1), (h, w))
        return arr

    if mode == "fm":
        lum = np.mean(f, axis=2) / 255.0
        if source == "luminance":
            freq_mod = frequency * (1.0 + lum * depth * 2.0)
        else:
            freq_mod = frequency
        theta = _make_coords(1.0, phase)
        theta = _ensure_2d(theta) * freq_mod
        carrier = _waveform(theta, carrier_waveform)
        carrier = carrier[:, :, np.newaxis]
        carrier = (1.0 - depth) + depth * carrier
        result = np.clip(f * carrier, 0, 255)
        result = _apply_spectrum_band(f, result, spectrum_band)
        return np.clip(result, 0, 255).astype(np.uint8)

    elif mode == "phase":
        lum = np.mean(f, axis=2) / 255.0
        base_theta = _make_coords(frequency, phase)
        base_theta = _ensure_2d(base_theta)
        phase_shift = lum * np.pi * 2.0 * depth
        carrier = _waveform(base_theta + phase_shift, carrier_waveform)
        carrier = (1.0 - depth) + depth * carrier[:, :, np.newaxis]
        result = np.clip(f * carrier, 0, 255)
        result = _apply_spectrum_band(f, result, spectrum_band)
        return np.clip(result, 0, 255).astype(np.uint8)

    elif mode == "multi":
        result = np.zeros_like(f)
        for c, harmonic in enumerate([1.0, 1.5, 2.0]):
            theta = _make_coords(frequency * harmonic, phase + c * 0.7)
            theta = _ensure_2d(theta)
            carrier = (1.0 - depth) + depth * _waveform(theta, carrier_waveform)
            result[:, :, c] = f[:, :, c] * carrier
        result = np.clip(result, 0, 255)
        result = _apply_spectrum_band(f, result, spectrum_band)
        return np.clip(result, 0, 255).astype(np.uint8)

    else:  # am (default)
        theta = _make_coords(frequency, phase)
        if source == "luminance":
            lum = np.mean(f, axis=2) / 255.0
            theta = _ensure_2d(theta)
            carrier = _waveform(theta * (1.0 + lum), carrier_waveform)
            carrier = carrier[:, :, np.newaxis]
        else:
            theta = _ensure_2d(theta)
            carrier = _waveform(theta, carrier_waveform)
            carrier = carrier[:, :, np.newaxis]
        carrier = (1.0 - depth) + depth * carrier
        result = np.clip(f * carrier, 0, 255)
        result = _apply_spectrum_band(f, result, spectrum_band)
        return np.clip(result, 0, 255).astype(np.uint8)


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

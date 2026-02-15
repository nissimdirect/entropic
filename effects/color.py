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
                    warmth: float = 0.3, mode: str = "vintage",
                    output_level: float = 1.0) -> np.ndarray:
    """Tape saturation — harmonic generation, HF rolloff, gentle compression.

    Models real magnetic tape behavior:
    - Odd-harmonic generation via soft clipping (asymmetric, not normalized)
    - HF rolloff: fine detail gets rounded (head bump), broad areas stay punchy
    - Gentle compression: dynamic range squeezed without washing out to white
    - Flutter: subtle spatial wobble simulating tape transport variation

    Modes:
        vintage: Warm reel-to-reel with gentle saturation and head bump.
        hot: Aggressive distortion with color crosstalk (overdriven).
        lo-fi: Cheap cassette — heavy HF loss, noise floor, dropouts.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        drive: Input gain before saturation (0.5-5.0). Higher = more harmonics.
        warmth: Warm color tint amount (0.0-1.0).
        mode: Saturation character — 'vintage', 'hot', 'lo-fi'.
        output_level: Output gain compensation (0.5-1.5).

    Returns:
        Tape-saturated frame.
    """
    import cv2

    drive = max(0.5, min(5.0, float(drive)))
    warmth = max(0.0, min(1.0, float(warmth)))
    output_level = max(0.5, min(1.5, float(output_level)))
    f = frame.astype(np.float32) / 255.0

    # --- Step 1: HF rolloff (head bump) — blur fine detail ---
    # Separate into low-freq (broad areas) and high-freq (detail)
    blur_k = 5 if mode == "lo-fi" else 3
    blur_sigma = 1.5 if mode == "lo-fi" else 0.7 + drive * 0.15
    low_freq = cv2.GaussianBlur(f, (blur_k, blur_k), blur_sigma)
    high_freq = f - low_freq
    # Tape rolls off highs: reduce detail proportional to drive
    hf_retention = max(0.1, 1.0 - drive * 0.15)
    if mode == "lo-fi":
        hf_retention = max(0.05, 1.0 - drive * 0.25)
    f = low_freq + high_freq * hf_retention

    # --- Step 2: Soft-clip saturation (odd harmonic generation) ---
    # Center around midpoint so saturation compresses toward gray, not white
    mid = 0.5
    centered = (f - mid) * drive
    if mode == "hot":
        # Harder clipping: more harmonics, asymmetric
        saturated = np.tanh(centered * 1.3)
        # Stronger drive pushes output harder but tanh caps at [-1,1]
        f = mid + saturated * 0.5 / max(np.tanh(1.3), 0.1)
    elif mode == "lo-fi":
        saturated = np.tanh(centered)
        f = mid + saturated * 0.5
    else:
        # Vintage: gentle odd-harmonic saturation
        saturated = np.tanh(centered * 0.8)
        f = mid + saturated * 0.5 / max(np.tanh(0.8), 0.1)

    # --- Step 3: Gentle compression (reduce dynamic range) ---
    # Push shadows up slightly, pull highlights down slightly
    compress = min(drive * 0.08, 0.3)
    f = f * (1.0 - compress) + 0.5 * compress

    # --- Step 4: Mode-specific character ---
    if mode == "hot":
        # Color bleed: slight channel crosstalk from overdriven heads
        r, g, b = f[:, :, 0].copy(), f[:, :, 1].copy(), f[:, :, 2].copy()
        f[:, :, 0] = r * 0.88 + g * 0.08 + b * 0.04
        f[:, :, 1] = r * 0.06 + g * 0.88 + b * 0.06
        f[:, :, 2] = r * 0.04 + g * 0.08 + b * 0.88

    elif mode == "lo-fi":
        # Noise floor (tape hiss)
        noise = np.random.RandomState(42).normal(0, 0.025 + drive * 0.008, f.shape).astype(np.float32)
        f += noise

    # --- Step 5: Warmth tint (head magnetization color shift) ---
    if warmth > 0:
        f[:, :, 0] = f[:, :, 0] + warmth * 0.05  # Red up
        f[:, :, 1] = f[:, :, 1] + warmth * 0.015  # Green slight
        f[:, :, 2] = f[:, :, 2] - warmth * 0.05  # Blue down

    f *= output_level
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


def color_filter(frame: np.ndarray, preset: str = "cyanotype", intensity: float = 1.0) -> np.ndarray:
    """Color filter presets — curated color grades as a dropdown.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        preset: Filter name — "cyanotype", "infrared", "sepia", "cool", "warm".
        intensity: Effect strength (0.0 = original, 1.0 = full effect).

    Returns:
        Color-filtered frame.
    """
    intensity = max(0.0, min(1.0, float(intensity)))

    if preset == "cyanotype":
        return cyanotype(frame, intensity=intensity)
    elif preset == "infrared":
        return infrared(frame, vegetation_glow=intensity * 2.0)
    elif preset == "sepia":
        gray = np.mean(frame.astype(np.float32), axis=2)
        r = np.clip(gray * 1.1 + 20, 0, 255)
        g = np.clip(gray * 0.9, 0, 255)
        b = np.clip(gray * 0.7, 0, 255)
        sepia = np.stack([r, g, b], axis=2)
        result = frame.astype(np.float32) * (1 - intensity) + sepia * intensity
        return np.clip(result, 0, 255).astype(np.uint8)
    elif preset == "cool":
        f = frame.astype(np.float32)
        f[:, :, 2] = np.clip(f[:, :, 2] * (1 + 0.3 * intensity), 0, 255)
        f[:, :, 0] = np.clip(f[:, :, 0] * (1 - 0.15 * intensity), 0, 255)
        return f.astype(np.uint8)
    elif preset == "warm":
        f = frame.astype(np.float32)
        f[:, :, 0] = np.clip(f[:, :, 0] * (1 + 0.3 * intensity), 0, 255)
        f[:, :, 2] = np.clip(f[:, :, 2] * (1 - 0.15 * intensity), 0, 255)
        return f.astype(np.uint8)
    else:
        return frame.copy()


def chroma_key(frame: np.ndarray, hue: float = 120.0, tolerance: float = 30.0,
               softness: float = 10.0, replace_color: str = "transparent") -> np.ndarray:
    """Green screen / chroma key — makes a specific color range transparent.

    Converts to HSV, creates a mask for the target hue range. With
    replace_color="transparent" (default), outputs RGBA where keyed pixels
    have alpha=0 for true compositing with layers below.

    Args:
        frame: (H, W, 3) uint8 RGB.
        hue: Target hue to key out in degrees (0-360). 120 = green, 0 = red, 240 = blue.
        tolerance: Hue range to key (degrees). Higher = wider key.
        softness: Edge feathering (0 = hard edge, 50 = very soft).
        replace_color: "transparent" = RGBA output, "black" or "white" = RGB output.

    Returns:
        RGBA frame (transparent) or RGB frame (black/white fill).
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

    # Apply mask
    if replace_color == "transparent":
        # Output RGBA: keyed pixels get alpha=0, unkeyed get alpha=255
        alpha = ((1.0 - mask) * 255).astype(np.uint8)
        return np.dstack([frame, alpha])
    else:
        mask_3ch = mask[:, :, np.newaxis]
        fill = 0.0 if replace_color == "black" else 255.0
        result = frame.astype(np.float32) * (1.0 - mask_3ch) + fill * mask_3ch
        return np.clip(result, 0, 255).astype(np.uint8)


def luma_key(frame: np.ndarray, threshold: float = 0.3, mode: str = "dark",
             softness: float = 10.0, replace_color: str = "transparent") -> np.ndarray:
    """Luminance key — makes dark or bright areas transparent.

    Keys out pixels based on their brightness. Use "dark" to remove shadows/dark
    areas (so bright content shows through), or "bright" to remove bright areas.
    With replace_color="transparent" (default), outputs RGBA for layer compositing.

    Args:
        frame: (H, W, 3) uint8 RGB.
        threshold: Brightness cutoff (0-1). Pixels beyond this threshold are keyed.
        mode: "dark" = key out dark areas, "bright" = key out bright areas.
        softness: Edge feathering (0 = hard, 50 = very soft).
        replace_color: "transparent" = RGBA output, "black" = RGB output.

    Returns:
        RGBA frame (transparent) or RGB frame (black fill).
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

    # Apply mask
    if replace_color == "transparent":
        alpha = ((1.0 - mask) * 255).astype(np.uint8)
        return np.dstack([frame, alpha])
    else:
        mask_3ch = mask[:, :, np.newaxis]
        result = frame.astype(np.float32) * (1.0 - mask_3ch)
        return np.clip(result, 0, 255).astype(np.uint8)


def levels(frame: np.ndarray, input_black: float = 0, input_white: float = 255,
           gamma: float = 1.0, output_black: float = 0, output_white: float = 255,
           channel: str = "master") -> np.ndarray:
    """Photoshop-style Levels adjustment.

    Remaps pixel values through input range, gamma curve, and output range.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        input_black: Black point input (0-255). Pixels at or below become output_black.
        input_white: White point input (0-255). Pixels at or above become output_white.
        gamma: Midtone gamma (0.1-10.0). <1 = brighter midtones, >1 = darker midtones.
        output_black: Black point output (0-255).
        output_white: White point output (0-255).
        channel: "master" (all channels), "r", "g", or "b".

    Returns:
        Levels-adjusted frame.
    """
    input_black = max(0, min(255, int(input_black)))
    input_white = max(0, min(255, int(input_white)))
    gamma = max(0.1, min(10.0, float(gamma)))
    output_black = max(0, min(255, int(output_black)))
    output_white = max(0, min(255, int(output_white)))

    # Prevent division by zero
    if input_white <= input_black:
        input_white = input_black + 1

    # Build 256-entry LUT for speed
    lut = np.arange(256, dtype=np.float32)
    lut = np.clip(lut, input_black, input_white)
    lut = (lut - input_black) / (input_white - input_black)
    lut = np.power(lut, 1.0 / gamma)
    lut = lut * (output_white - output_black) + output_black
    lut = np.clip(lut, 0, 255).astype(np.uint8)

    if channel == "master":
        return cv2.LUT(frame, lut)
    else:
        ch_map = {"r": 0, "g": 1, "b": 2}
        ch_idx = ch_map.get(channel, 0)
        result = frame.copy()
        result[:, :, ch_idx] = cv2.LUT(result[:, :, ch_idx], lut)
        return result


def curves(frame: np.ndarray, points: list = None, channel: str = "master",
           interpolation: str = "cubic") -> np.ndarray:
    """Photoshop-style Curves adjustment.

    Maps input values to output values via a spline curve defined by control points.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        points: List of [x, y] control points (0-255). Default: identity diagonal.
        channel: "master" (all channels), "r", "g", or "b".
        interpolation: "cubic" (smooth, monotone) or "linear".

    Returns:
        Curves-adjusted frame.
    """
    if points is None:
        points = [[0, 0], [64, 64], [128, 128], [192, 192], [255, 255]]

    # Validate and sort points by x
    pts = sorted([[max(0, min(255, int(p[0]))), max(0, min(255, int(p[1])))] for p in points])

    # Ensure we have endpoints
    if pts[0][0] != 0:
        pts.insert(0, [0, pts[0][1]])
    if pts[-1][0] != 255:
        pts.append([255, pts[-1][1]])

    xs = np.array([p[0] for p in pts], dtype=np.float64)
    ys = np.array([p[1] for p in pts], dtype=np.float64)

    # Build 256-entry LUT
    x_full = np.arange(256, dtype=np.float64)

    if interpolation == "cubic" and len(pts) >= 3:
        from scipy.interpolate import PchipInterpolator
        interp = PchipInterpolator(xs, ys)
        lut = interp(x_full)
    else:
        lut = np.interp(x_full, xs, ys)

    lut = np.clip(lut, 0, 255).astype(np.uint8)

    if channel == "master":
        return cv2.LUT(frame, lut)
    else:
        ch_map = {"r": 0, "g": 1, "b": 2}
        ch_idx = ch_map.get(channel, 0)
        result = frame.copy()
        result[:, :, ch_idx] = cv2.LUT(result[:, :, ch_idx], lut)
        return result


def hsl_adjust(frame: np.ndarray, target_hue: str = "all", hue_shift: float = 0,
               saturation: float = 0, lightness: float = 0) -> np.ndarray:
    """Per-hue-range HSL adjustment (like Photoshop's Hue/Saturation panel).

    Args:
        frame: (H, W, 3) uint8 RGB array.
        target_hue: Which hues to affect. "all", "reds", "oranges", "yellows",
                    "greens", "cyans", "blues", "magentas".
        hue_shift: Rotate hue (-180 to 180 degrees).
        saturation: Saturation adjustment (-100 to 100). Multiplicative.
        lightness: Lightness adjustment (-100 to 100). Additive to V channel.

    Returns:
        HSL-adjusted frame.
    """
    hue_shift = max(-180, min(180, float(hue_shift)))
    saturation = max(-100, min(100, float(saturation)))
    lightness = max(-100, min(100, float(lightness)))

    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV).astype(np.float32)
    # OpenCV HSV: H is 0-179 (half degrees), S is 0-255, V is 0-255

    if target_hue == "all":
        # Apply to all pixels uniformly
        hsv[:, :, 0] = (hsv[:, :, 0] + hue_shift / 2.0) % 180
        sat_factor = 1.0 + saturation / 100.0
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * sat_factor, 0, 255)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] + lightness * 2.55, 0, 255)
    else:
        # Hue ranges in OpenCV 0-179 scale (center, half-width)
        hue_ranges = {
            "reds":     (0, 15),
            "oranges":  (15, 7),
            "yellows":  (30, 7),
            "greens":   (60, 15),
            "cyans":    (90, 15),
            "blues":    (120, 15),
            "magentas": (150, 15),
        }
        center, half_width = hue_ranges.get(target_hue, (0, 15))

        h = hsv[:, :, 0]

        # Compute angular distance from center (wrapping at 180)
        dist = np.minimum(np.abs(h - center), 180 - np.abs(h - center))

        # Soft mask: 1.0 within half_width, smooth falloff to 0 over feather zone
        feather = half_width * 0.5
        mask = np.clip(1.0 - (dist - half_width) / max(feather, 1.0), 0.0, 1.0)

        # Apply hue shift within mask
        if hue_shift != 0:
            shifted_h = (h + hue_shift / 2.0 * mask) % 180
            hsv[:, :, 0] = shifted_h

        # Apply saturation within mask
        if saturation != 0:
            sat_factor = 1.0 + saturation / 100.0
            adjusted_s = hsv[:, :, 1] * sat_factor
            hsv[:, :, 1] = np.clip(
                hsv[:, :, 1] * (1.0 - mask) + adjusted_s * mask, 0, 255
            )

        # Apply lightness within mask
        if lightness != 0:
            adjusted_v = hsv[:, :, 2] + lightness * 2.55
            hsv[:, :, 2] = np.clip(
                hsv[:, :, 2] * (1.0 - mask) + adjusted_v * mask, 0, 255
            )

    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)


def color_balance(frame: np.ndarray, shadows_r: float = 0, shadows_g: float = 0,
                  shadows_b: float = 0, midtones_r: float = 0, midtones_g: float = 0,
                  midtones_b: float = 0, highlights_r: float = 0, highlights_g: float = 0,
                  highlights_b: float = 0, preserve_luminosity: bool = True) -> np.ndarray:
    """Photoshop-style Color Balance — shift colors in shadows, midtones, highlights.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        shadows_r/g/b: RGB offset for shadows (-100 to 100).
        midtones_r/g/b: RGB offset for midtones (-100 to 100).
        highlights_r/g/b: RGB offset for highlights (-100 to 100).
        preserve_luminosity: Restore original luminance after color shift.

    Returns:
        Color-balanced frame.
    """
    shadows_r = max(-100, min(100, float(shadows_r)))
    shadows_g = max(-100, min(100, float(shadows_g)))
    shadows_b = max(-100, min(100, float(shadows_b)))
    midtones_r = max(-100, min(100, float(midtones_r)))
    midtones_g = max(-100, min(100, float(midtones_g)))
    midtones_b = max(-100, min(100, float(midtones_b)))
    highlights_r = max(-100, min(100, float(highlights_r)))
    highlights_g = max(-100, min(100, float(highlights_g)))
    highlights_b = max(-100, min(100, float(highlights_b)))

    f = frame.astype(np.float32)

    # Compute luminance for range masks
    luma = 0.299 * f[:, :, 0] + 0.587 * f[:, :, 1] + 0.114 * f[:, :, 2]

    # Smooth masks using power falloff (no hard boundaries)
    shadow_mask = np.clip((170.0 - luma) / 170.0, 0, 1) ** 1.5
    highlight_mask = np.clip((luma - 85.0) / 170.0, 0, 1) ** 1.5
    midtone_mask = np.clip(1.0 - shadow_mask - highlight_mask, 0, 1)

    if preserve_luminosity:
        original_luma = luma.copy()

    # Apply RGB offsets weighted by masks
    for ch_idx, (s, m, h) in enumerate([
        (shadows_r, midtones_r, highlights_r),
        (shadows_g, midtones_g, highlights_g),
        (shadows_b, midtones_b, highlights_b),
    ]):
        offset = s * shadow_mask + m * midtone_mask + h * highlight_mask
        f[:, :, ch_idx] = f[:, :, ch_idx] + offset

    f = np.clip(f, 0, 255)

    if preserve_luminosity:
        new_luma = 0.299 * f[:, :, 0] + 0.587 * f[:, :, 1] + 0.114 * f[:, :, 2]
        scale = np.where(new_luma > 0.01, original_luma / new_luma, 1.0)
        scale_3ch = scale[:, :, np.newaxis]
        f = np.clip(f * scale_3ch, 0, 255)

    return f.astype(np.uint8)


def compute_histogram(frame: np.ndarray) -> dict:
    """Compute per-channel and luminance histograms.

    Args:
        frame: (H, W, 3) uint8 RGB array.

    Returns:
        Dict with "r", "g", "b", "luma" — each a list of 256 integers (bin counts).
    """
    r_hist = cv2.calcHist([frame], [0], None, [256], [0, 256]).flatten().astype(int).tolist()
    g_hist = cv2.calcHist([frame], [1], None, [256], [0, 256]).flatten().astype(int).tolist()
    b_hist = cv2.calcHist([frame], [2], None, [256], [0, 256]).flatten().astype(int).tolist()

    luma = (0.299 * frame[:, :, 0].astype(np.float32) +
            0.587 * frame[:, :, 1].astype(np.float32) +
            0.114 * frame[:, :, 2].astype(np.float32)).astype(np.uint8)
    luma_hist = cv2.calcHist([luma], [0], None, [256], [0, 256]).flatten().astype(int).tolist()

    return {"r": r_hist, "g": g_hist, "b": b_hist, "luma": luma_hist}

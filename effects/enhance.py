"""
Entropic — Enhancement Effects
Quick-win effects leveraging Pillow and OpenCV built-in operations.
"""

import numpy as np
from PIL import Image, ImageFilter, ImageOps


def solarize(
    frame: np.ndarray,
    threshold: int = 128,
    brightness: float = 1.0,
) -> np.ndarray:
    """Partially invert pixels above a threshold (Sabattier/Man Ray effect).

    Pixels above the threshold are inverted; below are left alone.
    Creates psychedelic, Warhol-esque color shifts.

    Args:
        frame: Input frame (H, W, 3) uint8.
        threshold: Inversion threshold (0-255).
        brightness: Brightness compensation (0.5-2.0). 1.0 = no change, >1.0 = brighten.

    Returns:
        Solarized frame.
    """
    threshold = max(0, min(255, int(threshold)))
    brightness = max(0.5, min(2.0, float(brightness)))
    img = Image.fromarray(frame)
    result = ImageOps.solarize(img, threshold=threshold)
    result_arr = np.array(result).astype(np.float32)
    # Apply brightness compensation
    result_arr = result_arr * brightness
    return np.clip(result_arr, 0, 255).astype(np.uint8)


def _clamp_rgb(color, default=(128, 128, 128)) -> tuple:
    """Normalize and clamp a color value to a valid RGB (R, G, B) tuple.

    Handles various input types from the UI:
    - tuple/list with 3 elements: standard RGB
    - tuple/list with 2 elements: from 'xy' knob (pad with 0)
    - single number: grayscale (repeat to all channels)
    - None/invalid: returns default
    """
    if color is None:
        return tuple(default)
    if isinstance(color, (int, float)):
        v = max(0, min(255, int(color)))
        return (v, v, v)
    if isinstance(color, (tuple, list)):
        if len(color) >= 3:
            return tuple(max(0, min(255, int(c))) for c in color[:3])
        if len(color) == 2:
            return (max(0, min(255, int(color[0]))), max(0, min(255, int(color[1]))), 0)
        if len(color) == 1:
            v = max(0, min(255, int(color[0])))
            return (v, v, v)
    return tuple(default)


def duotone(
    frame: np.ndarray,
    shadow_color: tuple = (0, 0, 80),
    highlight_color: tuple = (255, 200, 100),
) -> np.ndarray:
    """Map grayscale to a two-color gradient (duotone).

    Shadows mapped to shadow_color, highlights to highlight_color.
    Classic graphic design / risograph aesthetic.

    Args:
        frame: Input frame (H, W, 3) uint8.
        shadow_color: RGB color for shadows.
        highlight_color: RGB color for highlights.

    Returns:
        Duotone frame.
    """
    shadow_color = _clamp_rgb(shadow_color)
    highlight_color = _clamp_rgb(highlight_color)
    img = Image.fromarray(frame)
    gray = ImageOps.grayscale(img)
    result = ImageOps.colorize(gray, black=shadow_color, white=highlight_color)
    return np.array(result)


def emboss(
    frame: np.ndarray,
    amount: float = 1.0,
    transparent_bg: bool = False,
) -> np.ndarray:
    """3D embossed/stamped look by highlighting directional edges.

    Args:
        frame: Input frame (H, W, 3) uint8.
        amount: Blend amount (0.0 = original, 1.0 = fully embossed).
        transparent_bg: If True, makes gray areas (value ~128) black, enabling overlay compositing.

    Returns:
        Embossed frame.
    """
    amount = max(0.0, min(1.0, float(amount)))
    img = Image.fromarray(frame)
    embossed = img.filter(ImageFilter.EMBOSS)

    embossed_arr = np.array(embossed)

    if transparent_bg:
        # Make gray areas (neutral emboss background) transparent/black
        # Emboss filter produces gray (~128) for flat areas, bright/dark for edges
        gray_threshold = 30  # Distance from 128 to consider "gray"
        luminance = np.mean(embossed_arr.astype(np.float32), axis=2)
        gray_mask = np.abs(luminance - 128) < gray_threshold
        # Set gray areas to black (simulates transparency in RGB-only system)
        result_arr = embossed_arr.copy()
        result_arr[gray_mask] = 0

        if amount < 1.0:
            # Blend with original
            result_arr = np.clip(
                frame.astype(np.float32) * (1.0 - amount) + result_arr.astype(np.float32) * amount,
                0, 255,
            ).astype(np.uint8)
        return result_arr

    if amount >= 1.0:
        return embossed_arr
    if amount <= 0.0:
        return frame.copy()

    # Blend
    result = np.clip(
        frame.astype(np.float32) * (1.0 - amount) + embossed_arr.astype(np.float32) * amount,
        0, 255
    ).astype(np.uint8)
    return result


def auto_levels(
    frame: np.ndarray,
    cutoff: float = 5.0,
    strength: float = 1.0,
) -> np.ndarray:
    """Auto-contrast: stretch histogram to fill full range.

    Clips the given percentage of lightest and darkest pixels, then
    stretches the remaining range to 0-255. Professional color correction.

    Args:
        frame: Input frame (H, W, 3) uint8.
        cutoff: Percentage of extreme pixels to clip (0.0-25.0). Higher = more aggressive.
        strength: Blend amount (0.0 = original, 1.0 = fully corrected).

    Returns:
        Auto-leveled frame.
    """
    cutoff = max(0.0, min(25.0, float(cutoff)))
    strength = max(0.0, min(1.0, float(strength)))
    img = Image.fromarray(frame)
    result = np.array(ImageOps.autocontrast(img, cutoff=cutoff))
    if strength >= 1.0:
        return result
    blended = frame.astype(np.float32) * (1.0 - strength) + result.astype(np.float32) * strength
    return np.clip(blended, 0, 255).astype(np.uint8)


def median_filter(
    frame: np.ndarray,
    size: int = 5,
) -> np.ndarray:
    """Median filter — watercolor/noise reduction effect.

    Replaces each pixel with the median of its neighborhood.
    Small sizes remove noise; large sizes create a painted look.

    Args:
        frame: Input frame (H, W, 3) uint8.
        size: Filter kernel size (must be odd, 3-15).

    Returns:
        Median-filtered frame.
    """
    size = max(3, min(15, int(size)))
    if size % 2 == 0:
        size += 1
    img = Image.fromarray(frame)
    result = img.filter(ImageFilter.MedianFilter(size=size))
    return np.array(result)


def false_color(
    frame: np.ndarray,
    colormap: str = "jet",
) -> np.ndarray:
    """Map grayscale luminance to a false-color palette.

    Creates thermal-vision, scientific visualization, and psychedelic looks.
    Uses OpenCV's built-in colormaps.

    Args:
        frame: Input frame (H, W, 3) uint8.
        colormap: One of: jet, hot, cool, spring, summer, autumn, winter,
                  bone, ocean, rainbow, turbo, inferno, magma, plasma, viridis.

    Returns:
        False-colored frame.
    """
    import cv2

    colormap_dict = {
        "jet": cv2.COLORMAP_JET,
        "hot": cv2.COLORMAP_HOT,
        "cool": cv2.COLORMAP_COOL,
        "spring": cv2.COLORMAP_SPRING,
        "summer": cv2.COLORMAP_SUMMER,
        "autumn": cv2.COLORMAP_AUTUMN,
        "winter": cv2.COLORMAP_WINTER,
        "bone": cv2.COLORMAP_BONE,
        "ocean": cv2.COLORMAP_OCEAN,
        "rainbow": cv2.COLORMAP_RAINBOW,
        "turbo": cv2.COLORMAP_TURBO,
        "inferno": cv2.COLORMAP_INFERNO,
        "magma": cv2.COLORMAP_MAGMA,
        "plasma": cv2.COLORMAP_PLASMA,
        "viridis": cv2.COLORMAP_VIRIDIS,
    }

    cmap = colormap_dict.get(colormap, cv2.COLORMAP_JET)

    # Convert to grayscale
    gray = np.mean(frame, axis=2).astype(np.uint8)
    # Apply colormap (returns BGR)
    colored = cv2.applyColorMap(gray, cmap)
    # Convert BGR to RGB
    return cv2.cvtColor(colored, cv2.COLOR_BGR2RGB)


def histogram_eq(
    frame: np.ndarray,
    strength: float = 1.0,
) -> np.ndarray:
    """Equalize histogram per channel — reveals hidden detail in over/underexposed footage.

    Args:
        frame: Input frame (H, W, 3) uint8.
        strength: Blend amount (0.0 = original, 1.0 = fully equalized).

    Returns:
        Histogram-equalized frame.
    """
    import cv2

    strength = max(0.0, min(1.0, float(strength)))
    eq = np.zeros_like(frame)
    for i in range(3):
        eq[:, :, i] = cv2.equalizeHist(frame[:, :, i])
    if strength >= 1.0:
        return eq
    blended = frame.astype(np.float32) * (1.0 - strength) + eq.astype(np.float32) * strength
    return np.clip(blended, 0, 255).astype(np.uint8)


def clahe(
    frame: np.ndarray,
    clip_limit: float = 2.0,
    grid_size: int = 8,
) -> np.ndarray:
    """Contrast Limited Adaptive Histogram Equalization — local contrast enhancement.

    Night-vision / detail-reveal quality. Better than global histogram eq
    because it adapts to local regions.

    Args:
        frame: Input frame (H, W, 3) uint8.
        clip_limit: Contrast limit (1.0-10.0). Higher = more contrast.
        grid_size: Tile grid size (2-16). Smaller = more local adaptation.

    Returns:
        CLAHE-enhanced frame.
    """
    import cv2

    clip_limit = max(1.0, min(10.0, float(clip_limit)))
    grid_size = max(2, min(16, int(grid_size)))
    cl = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid_size, grid_size))
    result = np.zeros_like(frame)
    for i in range(3):
        result[:, :, i] = cl.apply(frame[:, :, i])
    return result


def parallel_compression(
    frame: np.ndarray,
    crush: float = 0.5,
    blend: float = 0.5,
) -> np.ndarray:
    """Blend original with heavily compressed version (New York compression for video).

    Audio technique: mix dry signal with a heavily compressed copy for
    punch without losing dynamics.

    Args:
        frame: Input frame (H, W, 3) uint8.
        crush: Gamma compression amount (0.1-1.0). Lower = more crushed.
        blend: Mix between original and crushed (0.0-1.0).

    Returns:
        Parallel-compressed frame.
    """
    crush = max(0.1, min(1.0, float(crush)))
    blend = max(0.0, min(1.0, float(blend)))
    f = frame.astype(np.float32) / 255.0
    crushed = np.power(f, crush)
    result = f * (1.0 - blend) + crushed * blend
    return np.clip(result * 255, 0, 255).astype(np.uint8)

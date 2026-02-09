"""
Entropic — Enhancement Effects
Quick-win effects leveraging Pillow and OpenCV built-in operations.
"""

import numpy as np
from PIL import Image, ImageFilter, ImageOps


def solarize(
    frame: np.ndarray,
    threshold: int = 128,
) -> np.ndarray:
    """Partially invert pixels above a threshold (Sabattier/Man Ray effect).

    Pixels above the threshold are inverted; below are left alone.
    Creates psychedelic, Warhol-esque color shifts.

    Args:
        frame: Input frame (H, W, 3) uint8.
        threshold: Inversion threshold (0-255).

    Returns:
        Solarized frame.
    """
    threshold = max(0, min(255, int(threshold)))
    img = Image.fromarray(frame)
    result = ImageOps.solarize(img, threshold=threshold)
    return np.array(result)


def _clamp_rgb(color: tuple) -> tuple:
    """Clamp an RGB tuple to valid 0-255 range."""
    if not isinstance(color, (tuple, list)) or len(color) != 3:
        return (128, 128, 128)  # Safe default
    return tuple(max(0, min(255, int(c))) for c in color)


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
) -> np.ndarray:
    """3D embossed/stamped look by highlighting directional edges.

    Args:
        frame: Input frame (H, W, 3) uint8.
        amount: Blend amount (0.0 = original, 1.0 = fully embossed).

    Returns:
        Embossed frame.
    """
    amount = max(0.0, min(1.0, float(amount)))
    img = Image.fromarray(frame)
    embossed = img.filter(ImageFilter.EMBOSS)

    if amount >= 1.0:
        return np.array(embossed)
    if amount <= 0.0:
        return frame.copy()

    # Blend
    result = np.clip(
        frame.astype(np.float32) * (1.0 - amount) + np.array(embossed).astype(np.float32) * amount,
        0, 255
    ).astype(np.uint8)
    return result


def auto_levels(
    frame: np.ndarray,
    cutoff: float = 2.0,
) -> np.ndarray:
    """Auto-contrast: stretch histogram to fill full range.

    Clips the given percentage of lightest and darkest pixels, then
    stretches the remaining range to 0-255. Professional color correction.

    Args:
        frame: Input frame (H, W, 3) uint8.
        cutoff: Percentage of extreme pixels to clip (0.0-10.0).

    Returns:
        Auto-leveled frame.
    """
    cutoff = max(0.0, min(10.0, float(cutoff)))
    img = Image.fromarray(frame)
    result = ImageOps.autocontrast(img, cutoff=cutoff)
    return np.array(result)


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
) -> np.ndarray:
    """Equalize histogram per channel — reveals hidden detail in over/underexposed footage.

    Args:
        frame: Input frame (H, W, 3) uint8.

    Returns:
        Histogram-equalized frame.
    """
    import cv2

    result = np.zeros_like(frame)
    for i in range(3):
        result[:, :, i] = cv2.equalizeHist(frame[:, :, i])
    return result


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

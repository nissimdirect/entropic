"""
Entropic — Video Analysis (Computer Vision)
Analyze rendered video frames to assess effect quality, detect motion,
and provide structured feedback on what effects did to the video.
"""

import numpy as np


def analyze_frame(frame: np.ndarray) -> dict:
    """Analyze a single frame — brightness, contrast, edges, blur level.

    Args:
        frame: (H, W, 3) uint8 RGB array.

    Returns:
        Dict with analysis metrics.
    """
    import cv2

    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    f = frame.astype(np.float32)

    # Brightness (mean luminance 0-255)
    brightness = float(np.mean(gray))

    # Contrast (standard deviation of luminance)
    contrast = float(np.std(gray))

    # Sharpness (Laplacian variance — higher = sharper)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    sharpness = float(laplacian.var())

    # Edge density (fraction of pixels that are edges via Canny)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = float(np.mean(edges > 0))

    # Color saturation (mean saturation in HSV)
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    saturation = float(np.mean(hsv[:, :, 1]))

    # Dominant hue
    hue_hist = cv2.calcHist([hsv], [0], None, [180], [0, 180]).flatten()
    dominant_hue = float(np.argmax(hue_hist))

    # Noise estimate (high-frequency energy)
    blurred = cv2.GaussianBlur(gray.astype(np.float32), (5, 5), 0)
    noise = float(np.mean(np.abs(gray.astype(np.float32) - blurred)))

    return {
        "brightness": round(brightness, 1),
        "contrast": round(contrast, 1),
        "sharpness": round(sharpness, 1),
        "edge_density": round(edge_density, 4),
        "saturation": round(saturation, 1),
        "dominant_hue": round(dominant_hue, 1),
        "noise_level": round(noise, 2),
    }


def compare_frames(original: np.ndarray, processed: np.ndarray) -> dict:
    """Compare original vs processed frame — what changed?

    Args:
        original: Original (H, W, 3) uint8 RGB array.
        processed: Processed (H, W, 3) uint8 RGB array.

    Returns:
        Dict with comparison metrics.
    """
    import cv2

    orig_analysis = analyze_frame(original)
    proc_analysis = analyze_frame(processed)

    # Pixel-level difference
    diff = np.abs(original.astype(np.float32) - processed.astype(np.float32))
    mean_diff = float(np.mean(diff))
    max_diff = float(np.max(diff))

    # Structural similarity (simplified SSIM-like metric)
    orig_gray = cv2.cvtColor(original, cv2.COLOR_RGB2GRAY).astype(np.float32)
    proc_gray = cv2.cvtColor(processed, cv2.COLOR_RGB2GRAY).astype(np.float32)

    mu_o = cv2.GaussianBlur(orig_gray, (11, 11), 1.5)
    mu_p = cv2.GaussianBlur(proc_gray, (11, 11), 1.5)
    sigma_o = cv2.GaussianBlur(orig_gray ** 2, (11, 11), 1.5) - mu_o ** 2
    sigma_p = cv2.GaussianBlur(proc_gray ** 2, (11, 11), 1.5) - mu_p ** 2
    sigma_op = cv2.GaussianBlur(orig_gray * proc_gray, (11, 11), 1.5) - mu_o * mu_p

    C1, C2 = 6.5025, 58.5225
    ssim_map = ((2 * mu_o * mu_p + C1) * (2 * sigma_op + C2)) / \
               ((mu_o ** 2 + mu_p ** 2 + C1) * (sigma_o + sigma_p + C2))
    similarity = float(np.mean(ssim_map))

    # Change percentage (pixels that changed by >10)
    changed_mask = np.mean(diff, axis=2) > 10
    change_pct = float(np.mean(changed_mask))

    return {
        "mean_pixel_diff": round(mean_diff, 2),
        "max_pixel_diff": round(max_diff, 1),
        "similarity": round(similarity, 4),
        "change_pct": round(change_pct * 100, 1),
        "original": orig_analysis,
        "processed": proc_analysis,
        "delta": {
            k: round(proc_analysis[k] - orig_analysis[k], 2)
            for k in orig_analysis
        },
    }


def detect_motion(frame1: np.ndarray, frame2: np.ndarray) -> dict:
    """Detect motion between two consecutive frames.

    Args:
        frame1: Previous frame (H, W, 3) uint8 RGB.
        frame2: Current frame (H, W, 3) uint8 RGB.

    Returns:
        Dict with motion metrics and flow data.
    """
    import cv2

    gray1 = cv2.cvtColor(frame1, cv2.COLOR_RGB2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_RGB2GRAY)

    # Dense optical flow
    flow = cv2.calcOpticalFlowFarneback(
        gray1, gray2, None,
        pyr_scale=0.5, levels=3, winsize=15,
        iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
    )

    # Motion magnitude
    mag = np.sqrt(flow[:, :, 0] ** 2 + flow[:, :, 1] ** 2)

    # Frame difference
    frame_diff = cv2.absdiff(gray1, gray2)

    return {
        "mean_motion": round(float(np.mean(mag)), 2),
        "max_motion": round(float(np.max(mag)), 2),
        "motion_coverage": round(float(np.mean(mag > 1.0)) * 100, 1),
        "frame_diff": round(float(np.mean(frame_diff)), 2),
        "scene_change": float(np.mean(frame_diff)) > 30,
    }


def describe_frame(frame: np.ndarray) -> str:
    """Generate human-readable description of what's in this frame.

    Args:
        frame: (H, W, 3) uint8 RGB array.

    Returns:
        Human-readable description string.
    """
    a = analyze_frame(frame)

    parts = []

    # Brightness
    if a["brightness"] < 50:
        parts.append("very dark")
    elif a["brightness"] < 100:
        parts.append("dark")
    elif a["brightness"] > 200:
        parts.append("very bright/blown out")
    elif a["brightness"] > 150:
        parts.append("bright")

    # Contrast
    if a["contrast"] < 20:
        parts.append("flat/low contrast")
    elif a["contrast"] > 80:
        parts.append("high contrast")

    # Sharpness
    if a["sharpness"] < 50:
        parts.append("blurry")
    elif a["sharpness"] > 500:
        parts.append("very sharp/noisy")

    # Saturation
    if a["saturation"] < 30:
        parts.append("desaturated/near-grayscale")
    elif a["saturation"] > 150:
        parts.append("highly saturated")

    # Noise
    if a["noise_level"] > 15:
        parts.append("noisy/grainy")

    # Edge density
    if a["edge_density"] > 0.3:
        parts.append("complex/detailed")
    elif a["edge_density"] < 0.05:
        parts.append("smooth/minimal detail")

    if not parts:
        parts.append("balanced/normal looking")

    return f"Frame: {', '.join(parts)} (brightness={a['brightness']:.0f}, contrast={a['contrast']:.0f}, sharpness={a['sharpness']:.0f}, noise={a['noise_level']:.1f})"

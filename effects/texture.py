"""
Entropic — Texture & Noise Effects
VHS, noise, posterize, edge detection, blur.
"""

import numpy as np


def vhs(frame: np.ndarray, tracking: float = 0.5, noise_amount: float = 0.2,
        color_bleed: int = 3, seed: int = 42) -> np.ndarray:
    """Simulate VHS tape degradation.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        tracking: Tracking error intensity (0.0-1.0). Higher = more horizontal offset.
        noise_amount: Amount of noise overlay (0.0-1.0).
        color_bleed: Horizontal color bleed in pixels.
        seed: Random seed for reproducibility.

    Returns:
        VHS-degraded frame.
    """
    h, w, c = frame.shape
    rng = np.random.RandomState(seed)
    result = frame.astype(np.float32)
    tracking = max(0.0, min(1.0, tracking))
    noise_amount = max(0.0, min(1.0, noise_amount))
    color_bleed = max(0, min(color_bleed, w // 4))

    # 1. Tracking lines — horizontal shifts at random rows
    if tracking > 0:
        num_glitch_rows = int(h * tracking * 0.1)
        for _ in range(num_glitch_rows):
            row = rng.randint(0, h)
            band_h = rng.randint(1, max(2, int(h * 0.02)))
            shift = rng.randint(-int(w * tracking * 0.1), int(w * tracking * 0.1) + 1)
            end_row = min(row + band_h, h)
            result[row:end_row] = np.roll(result[row:end_row], shift, axis=1)

    # 2. Color bleed — blur chroma horizontally
    if color_bleed > 0:
        kernel = np.ones(color_bleed * 2 + 1) / (color_bleed * 2 + 1)
        for ch in [0, 2]:  # Bleed R and B, leave G sharp
            for y in range(h):
                result[y, :, ch] = np.convolve(result[y, :, ch], kernel, mode='same')

    # 3. Noise overlay
    if noise_amount > 0:
        noise = rng.normal(0, 25 * noise_amount, (h, w, c)).astype(np.float32)
        result = result + noise

    return np.clip(result, 0, 255).astype(np.uint8)


def noise(frame: np.ndarray, amount: float = 0.3,
          noise_type: str = "gaussian", seed: int = 42,
          animate: bool = False, frame_index: int = 0) -> np.ndarray:
    """Add noise to the frame.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        amount: Noise intensity (0.0-1.0).
        noise_type: 'gaussian', 'salt_pepper', or 'uniform'.
        seed: Random seed (base seed when animate=False).
        animate: If True, seed auto-increments each frame for motion noise.
        frame_index: Current frame number for animation.

    Returns:
        Noisy frame.
    """
    h, w, c = frame.shape
    effective_seed = seed + frame_index if animate else seed
    rng = np.random.RandomState(effective_seed)
    amount = max(0.0, min(1.0, amount))
    result = frame.astype(np.float32)

    if noise_type == "salt_pepper":
        mask = rng.random((h, w))
        threshold = amount * 0.05
        result[mask < threshold] = 0
        result[mask > (1 - threshold)] = 255
    elif noise_type == "uniform":
        noise_val = rng.uniform(-128 * amount, 128 * amount, (h, w, c))
        result = result + noise_val
    else:  # gaussian
        noise_val = rng.normal(0, 50 * amount, (h, w, c))
        result = result + noise_val

    return np.clip(result, 0, 255).astype(np.uint8)


def posterize(frame: np.ndarray, levels: int = 4) -> np.ndarray:
    """Reduce color levels for a poster/screen print effect.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        levels: Number of color levels per channel (2-32).

    Returns:
        Posterized frame.
    """
    levels = max(2, min(32, int(levels)))
    step = 256 / levels
    result = (frame // step * step + step // 2).astype(np.uint8)
    return np.clip(result, 0, 255).astype(np.uint8)


def edge_detect(frame: np.ndarray, threshold: float = 0.3,
                mode: str = "overlay") -> np.ndarray:
    """Detect edges using Sobel-like operators.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        threshold: Edge sensitivity (0.0-1.0, lower = more edges).
        mode: 'overlay' (edges on original), 'edges_only' (white edges on black),
              'neon' (colored edges on black).

    Returns:
        Edge-detected frame.
    """
    # Convert to grayscale for edge detection
    gray = np.mean(frame.astype(np.float32), axis=2)
    threshold = max(0.01, min(1.0, threshold))

    # Simple Sobel approximation
    gx = np.zeros_like(gray)
    gy = np.zeros_like(gray)
    gx[:, 1:-1] = gray[:, 2:] - gray[:, :-2]
    gy[1:-1, :] = gray[2:, :] - gray[:-2, :]
    magnitude = np.sqrt(gx**2 + gy**2)

    # Normalize and threshold
    if magnitude.max() > 0:
        magnitude = magnitude / magnitude.max()
    edges = (magnitude > threshold).astype(np.float32)

    if mode == "edges_only":
        result = np.stack([edges * 255] * 3, axis=2)
    elif mode == "neon":
        # Color edges based on gradient direction
        angle = np.arctan2(gy, gx + 1e-7)
        r = ((np.sin(angle) + 1) / 2 * 255 * edges)
        g = ((np.sin(angle + 2.094) + 1) / 2 * 255 * edges)
        b = ((np.sin(angle + 4.189) + 1) / 2 * 255 * edges)
        result = np.stack([r, g, b], axis=2)
    else:  # overlay
        edge_mask = edges[:, :, np.newaxis]
        result = frame.astype(np.float32) * (1 - edge_mask * 0.5) + edge_mask * 128

    return np.clip(result, 0, 255).astype(np.uint8)


def blur(frame: np.ndarray, radius: int = 3, blur_type: str = "box") -> np.ndarray:
    """Apply blur effect.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        radius: Blur radius in pixels (1-20).
        blur_type: 'box', 'gaussian', 'motion', 'radial', or 'median'.

    Returns:
        Blurred frame.
    """
    import cv2
    from PIL import Image, ImageFilter

    radius = max(1, min(20, int(radius)))
    h, w = frame.shape[:2]

    if blur_type == "gaussian":
        # OpenCV GaussianBlur — radius maps to kernel size
        ksize = radius * 2 + 1
        return cv2.GaussianBlur(frame, (ksize, ksize), 0)

    elif blur_type == "motion":
        # Horizontal motion blur using a 1D kernel
        kernel_size = radius * 2 + 1
        kernel = np.zeros((kernel_size, kernel_size), dtype=np.float32)
        kernel[kernel_size // 2, :] = 1.0 / kernel_size
        result = cv2.filter2D(frame, -1, kernel)
        return result

    elif blur_type == "radial":
        # Radial blur from center — warp pixels inward/outward with scaling
        cx, cy = w // 2, h // 2
        strength = radius * 0.02  # Scaling factor
        y_coords, x_coords = np.mgrid[0:h, 0:w].astype(np.float32)
        dx = x_coords - cx
        dy = y_coords - cy
        distance = np.sqrt(dx**2 + dy**2) + 1e-6
        # Scale coordinates toward/away from center
        scale = 1.0 + strength
        map_x = cx + dx * scale
        map_y = cy + dy * scale
        result = cv2.remap(frame, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        # Blend with original for blur effect
        blended = (frame.astype(np.float32) * 0.6 + result.astype(np.float32) * 0.4)
        return np.clip(blended, 0, 255).astype(np.uint8)

    elif blur_type == "median":
        # Median filter — noise reduction, preserves edges
        ksize = min(radius * 2 + 1, 31)  # OpenCV medianBlur max is 31
        if ksize % 2 == 0:
            ksize += 1
        return cv2.medianBlur(frame, ksize)

    else:  # box
        img = Image.fromarray(frame)
        img = img.filter(ImageFilter.BoxBlur(radius))
        return np.array(img)


def sharpen(frame: np.ndarray, amount: float = 1.0) -> np.ndarray:
    """Sharpen the image using unsharp mask approach.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        amount: Sharpening intensity (0.0-3.0).

    Returns:
        Sharpened frame.
    """
    from PIL import Image, ImageFilter

    amount = max(0.0, min(3.0, float(amount)))
    img = Image.fromarray(frame)

    # Apply multiple sharpen passes based on amount
    passes = max(1, int(amount))
    for _ in range(passes):
        img = img.filter(ImageFilter.SHARPEN)

    return np.array(img)


def tv_static(frame: np.ndarray, intensity: float = 0.8,
              sync_drift: float = 0.3, seed: int = 42,
              concentrate_x: float = 0.5, concentrate_y: float = 0.5,
              concentrate_radius: float = 0.0, animate_displacement: bool = False,
              frame_index: int = 0) -> np.ndarray:
    """Full-screen TV static with horizontal sync drift.

    Channel-between-stations aesthetic. Random noise overlay +
    horizontal line displacement simulating lost sync signal.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        intensity: Static overlay amount (0.0-1.0).
        sync_drift: Horizontal sync error amount (0.0-1.0).
        seed: Random seed.
        concentrate_x: X position for spatial concentration (0.0-1.0, 0.5=center).
        concentrate_y: Y position for spatial concentration (0.0-1.0, 0.5=center).
        concentrate_radius: Radius for concentration falloff (0.0=fullscreen, 0.5=half).
        animate_displacement: If True, displacement shifts over time.
        frame_index: Current frame number for animation.

    Returns:
        Static-overlaid frame.
    """
    h, w, c = frame.shape
    effective_seed = seed + frame_index if animate_displacement else seed
    rng = np.random.RandomState(effective_seed)
    intensity = max(0.0, min(1.0, float(intensity)))
    sync_drift = max(0.0, min(1.0, float(sync_drift)))
    concentrate_radius = max(0.0, min(1.0, float(concentrate_radius)))

    static = rng.randint(0, 256, (h, w), dtype=np.uint8)

    # Spatial concentration — fade static based on distance from center
    if concentrate_radius > 0.0:
        cx = int(w * max(0.0, min(1.0, concentrate_x)))
        cy = int(h * max(0.0, min(1.0, concentrate_y)))
        yy, xx = np.ogrid[:h, :w]
        distance = np.sqrt(((xx - cx) / w) ** 2 + ((yy - cy) / h) ** 2)
        mask = 1.0 - np.clip(distance / concentrate_radius, 0.0, 1.0)
        static = (static.astype(np.float32) * mask).astype(np.uint8)

    static_rgb = np.stack([static] * 3, axis=2)
    result = frame.copy()
    if sync_drift > 0:
        num_rows = int(h * sync_drift * 0.2)
        for _ in range(num_rows):
            row = rng.randint(0, h)
            shift = rng.randint(-w // 4, w // 4 + 1)
            result[row] = np.roll(result[row], shift, axis=0)
    blended = result.astype(np.float32) * (1 - intensity) + static_rgb.astype(np.float32) * intensity
    return np.clip(blended, 0, 255).astype(np.uint8)


def contour_lines(frame: np.ndarray, levels: int = 8) -> np.ndarray:
    """Extract contour lines like a topographic map of luminance.

    Quantizes brightness into bands, then highlights the boundaries
    between bands as bright lines on a darkened frame.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        levels: Number of luminance bands (2-16).

    Returns:
        Contour-lined frame.
    """
    levels = max(2, min(16, int(levels)))
    gray = np.mean(frame.astype(np.float32), axis=2)
    step = 256.0 / levels
    quantized = (gray // step) * step
    dx = np.abs(np.diff(quantized, axis=1, prepend=quantized[:, :1]))
    dy = np.abs(np.diff(quantized, axis=0, prepend=quantized[:1, :]))
    edges = ((dx > 0) | (dy > 0)).astype(np.float32)
    dark = frame.astype(np.float32) * 0.3
    lines = edges[:, :, np.newaxis] * 255
    result = dark + lines
    return np.clip(result, 0, 255).astype(np.uint8)

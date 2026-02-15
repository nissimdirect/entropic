"""
Entropic — Distortion Effects
Wave distortion, displacement, mirror, and geometric glitches.
"""

import numpy as np
from PIL import Image


def wave_distort(frame: np.ndarray, amplitude: float = 10.0,
                 frequency: float = 0.05, direction: str = "horizontal",
                 frame_index: int = 0, total_frames: int = 1) -> np.ndarray:
    """Apply sine wave distortion to the image.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        amplitude: Pixel displacement amount.
        frequency: Wave frequency (higher = more waves).
        direction: 'horizontal', 'vertical', 'diagonal', or 'circular'.

    Returns:
        Distorted frame.
    """
    h, w, c = frame.shape
    result = np.zeros_like(frame)
    amplitude = max(0, min(amplitude, max(h, w) // 2))

    if direction == "vertical":
        for x in range(w):
            shift = int(amplitude * np.sin(2 * np.pi * frequency * x))
            result[:, x, :] = np.roll(frame[:, x, :], shift, axis=0)
    elif direction == "diagonal":
        for y in range(h):
            shift = int(amplitude * np.sin(2 * np.pi * frequency * (y + y * w / h)))
            result[y, :, :] = np.roll(frame[y, :, :], shift, axis=0)
    elif direction == "circular":
        cx, cy = w / 2.0, h / 2.0
        y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
        dist = np.sqrt((x_grid - cx) ** 2 + (y_grid - cy) ** 2)
        angle_offset = np.sin(dist * frequency * 0.1) * amplitude
        new_x = np.clip(x_grid + angle_offset, 0, w - 1).astype(np.int32)
        new_y = np.clip(y_grid + angle_offset * 0.5, 0, h - 1).astype(np.int32)
        result = frame[new_y, new_x]
    else:  # horizontal
        for y in range(h):
            shift = int(amplitude * np.sin(2 * np.pi * frequency * y))
            result[y, :, :] = np.roll(frame[y, :, :], shift, axis=0)

    return result


def displacement(frame: np.ndarray, block_size: int = 16,
                 intensity: float = 10.0, seed: int = 42) -> np.ndarray:
    """Randomly displace blocks of the image (glitch block effect).

    Args:
        frame: (H, W, 3) uint8 RGB array.
        block_size: Size of each block in pixels.
        intensity: Maximum displacement in pixels.
        seed: Random seed for reproducibility.

    Returns:
        Frame with displaced blocks.
    """
    h, w, c = frame.shape
    block_size = max(4, min(block_size, min(h, w)))
    intensity = max(0, min(intensity, max(h, w) // 2))
    rng = np.random.RandomState(seed)
    result = frame.copy()

    for y in range(0, h, block_size):
        for x in range(0, w, block_size):
            if rng.random() > 0.6:  # Only displace some blocks
                dy = rng.randint(-int(intensity), int(intensity) + 1)
                dx = rng.randint(-int(intensity), int(intensity) + 1)
                by = min(y + block_size, h)
                bx = min(x + block_size, w)
                # Source coordinates (clamped)
                sy = max(0, min(y + dy, h - block_size))
                sx = max(0, min(x + dx, w - block_size))
                sby = min(sy + (by - y), h)
                sbx = min(sx + (bx - x), w)
                bh = min(by - y, sby - sy)
                bw = min(bx - x, sbx - sx)
                if bh > 0 and bw > 0:
                    result[y:y+bh, x:x+bw] = frame[sy:sy+bh, sx:sx+bw]

    return result


def mirror(frame: np.ndarray, axis: str = "vertical",
           position: float = 0.5) -> np.ndarray:
    """Mirror one half of the image onto the other.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        axis: 'vertical' (left-right) or 'horizontal' (top-bottom).
        position: Split position (0.0-1.0).

    Returns:
        Mirrored frame.
    """
    h, w, c = frame.shape
    position = max(0.1, min(0.9, position))
    result = frame.copy()

    if axis == "horizontal":
        split = int(h * position)
        top = result[:split]
        result[split:split + top.shape[0]] = top[::-1][:h - split]
    else:
        split = int(w * position)
        left = result[:, :split]
        result[:, split:split + left.shape[1]] = left[:, ::-1][:, :w - split]

    return result


def chromatic_aberration(frame: np.ndarray, offset: int = 5,
                         direction: str = "horizontal") -> np.ndarray:
    """Simulate lens chromatic aberration by splitting RGB channels.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        offset: Pixel offset for R and B channels.
        direction: 'horizontal', 'vertical', or 'radial'.

    Returns:
        Frame with chromatic aberration.
    """
    h, w, c = frame.shape
    result = np.zeros_like(frame)

    if direction == "radial":
        # Simple radial: shift R outward, B inward
        cy, cx = h // 2, w // 2
        for ch_idx, mult in enumerate([-1, 0, 1]):
            channel = frame[:, :, ch_idx]
            if mult == 0:
                result[:, :, ch_idx] = channel
            else:
                # Approximate radial with scaled resize
                scale = 1.0 + mult * offset * 0.002
                img = Image.fromarray(channel)
                new_w, new_h = int(w * scale), int(h * scale)
                if new_w < 1 or new_h < 1:
                    result[:, :, ch_idx] = channel
                    continue
                scaled = np.array(img.resize((new_w, new_h), Image.BILINEAR))
                # Center crop/pad
                sy = (new_h - h) // 2
                sx = (new_w - w) // 2
                result[:, :, ch_idx] = scaled[sy:sy+h, sx:sx+w]
    else:
        axis = 0 if direction == "vertical" else 1
        result[:, :, 0] = np.roll(frame[:, :, 0], offset, axis=axis)   # R
        result[:, :, 1] = frame[:, :, 1]                                # G stays
        result[:, :, 2] = np.roll(frame[:, :, 2], -offset, axis=axis)  # B

    return result


def pencil_sketch(frame: np.ndarray, sigma_s: float = 60.0,
                  sigma_r: float = 0.07, shade: float = 0.05) -> np.ndarray:
    """Pencil sketch effect using OpenCV's built-in pencilSketch.

    Instant drawing/illustration effect. Chain with color effects
    for "animated comic" look.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        sigma_s: Spatial sigma for edge-preserving filter (1-200).
        sigma_r: Range sigma for edge-preserving filter (0.0-1.0).
        shade: Shading factor for pencil texture (0.0-0.1).

    Returns:
        Pencil-sketched frame.
    """
    import cv2

    sigma_s = max(1.0, min(200.0, float(sigma_s)))
    sigma_r = max(0.0, min(1.0, float(sigma_r)))
    shade = max(0.0, min(0.1, float(shade)))
    bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    _, color_sketch = cv2.pencilSketch(bgr, sigma_s=sigma_s, sigma_r=sigma_r, shade_factor=shade)
    return cv2.cvtColor(color_sketch, cv2.COLOR_BGR2RGB)


def cumulative_smear(frame: np.ndarray, direction: str = "horizontal",
                     decay: float = 0.95, animate: bool = False,
                     frame_index: int = 0) -> np.ndarray:
    """Cumulative smear — paint-smear / light-trail effect.

    Each pixel takes the max of itself or the decayed previous pixel,
    creating directional streaks like a smeared painting.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        direction: 'horizontal', 'vertical', 'diagonal_left', or 'diagonal_right'.
        decay: Smear decay rate (0.5-0.999). Higher = longer trails.
        animate: If True, direction rotates over time using frame_index.
        frame_index: Current frame number for animation.

    Returns:
        Smeared frame.
    """
    decay = max(0.5, min(0.999, float(decay)))
    f = frame.astype(np.float32) / 255.0

    # Animated direction — cycle through 4 directions every 60 frames
    if animate:
        cycle_pos = (frame_index // 15) % 4
        directions = ["horizontal", "vertical", "diagonal_left", "diagonal_right"]
        direction = directions[cycle_pos]

    if direction == "vertical":
        for y in range(1, f.shape[0]):
            f[y] = np.maximum(f[y], f[y - 1] * decay)
    elif direction == "diagonal_left":
        # Top-left to bottom-right
        for y in range(1, f.shape[0]):
            for x in range(1, f.shape[1]):
                f[y, x] = np.maximum(f[y, x], f[y - 1, x - 1] * decay)
    elif direction == "diagonal_right":
        # Top-right to bottom-left
        for y in range(1, f.shape[0]):
            for x in range(f.shape[1] - 2, -1, -1):
                f[y, x] = np.maximum(f[y, x], f[y - 1, x + 1] * decay)
    else:  # horizontal
        for x in range(1, f.shape[1]):
            f[:, x] = np.maximum(f[:, x], f[:, x - 1] * decay)
    return np.clip(f * 255, 0, 255).astype(np.uint8)

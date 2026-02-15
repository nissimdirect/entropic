"""
Entropic — Whimsy Effects Package

Retro, fantastical, soft effects with less hard edges. Shapes moving,
lens flares drifting, watercolor washes — mutable, animated, warm.

Every effect supports position, mood, and orientation parameters
for maximum creative control.
"""

import numpy as np
import cv2


def kaleidoscope(frame, segments=6, rotation=0.0, center_x=0.5, center_y=0.5,
                 zoom=1.0, mood="classic", frame_index=0, total_frames=1):
    """Mirror segments radiating from center — like looking through a kaleidoscope.

    Moods:
        classic — clean mirror segments
        psychedelic — hue-shifted per segment
        soft — gaussian blur between segments
    """
    h, w = frame.shape[:2]
    cx, cy = int(center_x * w), int(center_y * h)

    # Build angle map
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    dx = xs - cx
    dy = ys - cy
    angle = np.arctan2(dy, dx) + np.radians(rotation)
    radius = np.sqrt(dx * dx + dy * dy)

    # Fold angle into segment
    seg_angle = 2 * np.pi / max(segments, 2)
    folded = np.abs(np.mod(angle, seg_angle) - seg_angle / 2)

    # Map back to coordinates
    map_x = (cx + radius * np.cos(folded) / zoom).astype(np.float32)
    map_y = (cy + radius * np.sin(folded) / zoom).astype(np.float32)
    map_x = np.clip(map_x, 0, w - 1)
    map_y = np.clip(map_y, 0, h - 1)

    result = cv2.remap(frame, map_x, map_y, cv2.INTER_LINEAR)

    if mood == "psychedelic":
        hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV).astype(np.float32)
        segment_idx = np.floor(np.mod(angle, 2 * np.pi) / seg_angle)
        hsv[:, :, 0] = np.mod(hsv[:, :, 0] + segment_idx * (180 / segments), 180)
        result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    elif mood == "soft":
        blurred = cv2.GaussianBlur(result, (0, 0), sigmaX=3)
        # Blend edges between segments
        edge_mask = np.abs(np.mod(angle, seg_angle) - seg_angle / 2) < 0.05
        edge_mask_3 = edge_mask[:, :, np.newaxis].astype(np.float32)
        result = np.clip(
            result.astype(np.float32) * (1 - edge_mask_3) + blurred.astype(np.float32) * edge_mask_3,
            0, 255
        ).astype(np.uint8)

    return result


def soft_bloom(frame, radius=15, intensity=0.6, threshold=180, tint_r=255,
               tint_g=240, tint_b=220, mood="dreamy", frame_index=0, total_frames=1):
    """Dreamy glow/bloom — bright areas bleed soft light outward.

    Moods:
        dreamy — warm soft glow
        neon — saturated color bloom
        ethereal — cool pastel bloom with desaturation
    """
    # Extract bright areas
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, bright_mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
    bright_mask_3 = cv2.merge([bright_mask] * 3)

    # Create bloom from bright areas
    bloom = cv2.bitwise_and(frame, bright_mask_3)

    # Apply large gaussian blur for glow
    ksize = max(3, radius * 2 + 1)
    if ksize % 2 == 0:
        ksize += 1
    bloom = cv2.GaussianBlur(bloom, (ksize, ksize), 0)

    if mood == "dreamy":
        # Warm tint
        tint = np.array([tint_b, tint_g, tint_r], dtype=np.float32) / 255.0
        bloom = (bloom.astype(np.float32) * tint).astype(np.uint8)
    elif mood == "neon":
        # Boost saturation of bloom
        hsv = cv2.cvtColor(bloom, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 2.0, 0, 255)
        bloom = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    elif mood == "ethereal":
        # Cool desaturated bloom
        tint = np.array([1.1, 1.0, 0.9], dtype=np.float32)
        bloom = np.clip(bloom.astype(np.float32) * tint, 0, 255).astype(np.uint8)

    # Additive blend
    result = np.clip(
        frame.astype(np.float32) + bloom.astype(np.float32) * intensity,
        0, 255
    ).astype(np.uint8)

    return result


def shape_overlay(frame, shape="circle", count=5, size=0.1, opacity=0.4,
                  color_r=255, color_g=100, color_b=100, filled=True,
                  animate=True, speed=1.0, orientation="random",
                  mood="playful", seed=42, frame_index=0, total_frames=1):
    """Floating geometric shapes overlaid on video.

    Shapes: circle, triangle, square, star, hexagon, heart
    Orientations: random, grid, spiral, cascade
    Moods:
        playful — bright colors, bouncing
        minimal — monochrome, slow drift
        chaos — rapid, overlapping, varied sizes
    """
    h, w = frame.shape[:2]
    rng = np.random.RandomState(seed)

    overlay = frame.copy()
    color_bgr = (int(color_b), int(color_g), int(color_r))

    base_size = int(min(h, w) * size)
    t = frame_index / max(total_frames, 1) * speed

    for i in range(count):
        # Position based on orientation
        if orientation == "grid":
            cols = int(np.ceil(np.sqrt(count)))
            row, col = divmod(i, cols)
            px = int((col + 0.5) * w / cols)
            py = int((row + 0.5) * h / max(1, int(np.ceil(count / cols))))
        elif orientation == "spiral":
            angle = i * 2.4 + t * 2
            r = (i / max(count, 1)) * min(h, w) * 0.4
            px = int(w / 2 + r * np.cos(angle))
            py = int(h / 2 + r * np.sin(angle))
        elif orientation == "cascade":
            px = int((i / max(count - 1, 1)) * w * 0.8 + w * 0.1)
            py_base = (i / max(count - 1, 1)) * h * 0.6 + h * 0.2
            py = int(py_base + np.sin(t * 3 + i) * h * 0.05) if animate else int(py_base)
        else:  # random
            px = int(rng.rand() * w)
            py = int(rng.rand() * h)
            if animate:
                px = int((px + t * w * 0.1 * (i + 1)) % w)
                py = int((py + np.sin(t * 2 + i) * h * 0.05) % h)

        s = base_size
        if mood == "chaos":
            s = int(base_size * (0.5 + rng.rand() * 1.5))
        elif mood == "minimal":
            s = int(base_size * 0.7)

        thickness = -1 if filled else max(1, s // 10)

        if shape == "circle":
            cv2.circle(overlay, (px, py), s, color_bgr, thickness)
        elif shape == "square":
            cv2.rectangle(overlay, (px - s, py - s), (px + s, py + s), color_bgr, thickness)
        elif shape == "triangle":
            pts = np.array([
                [px, py - s],
                [px - int(s * 0.87), py + s // 2],
                [px + int(s * 0.87), py + s // 2],
            ], dtype=np.int32)
            if filled:
                cv2.fillPoly(overlay, [pts], color_bgr)
            else:
                cv2.polylines(overlay, [pts], True, color_bgr, thickness)
        elif shape == "hexagon":
            pts = np.array([
                [px + int(s * np.cos(a)), py + int(s * np.sin(a))]
                for a in np.linspace(0, 2 * np.pi, 7)[:-1]
            ], dtype=np.int32)
            if filled:
                cv2.fillPoly(overlay, [pts], color_bgr)
            else:
                cv2.polylines(overlay, [pts], True, color_bgr, thickness)
        elif shape == "star":
            pts = []
            for j in range(10):
                a = j * np.pi / 5 - np.pi / 2
                r = s if j % 2 == 0 else s // 2
                pts.append([px + int(r * np.cos(a)), py + int(r * np.sin(a))])
            pts = np.array(pts, dtype=np.int32)
            if filled:
                cv2.fillPoly(overlay, [pts], color_bgr)
            else:
                cv2.polylines(overlay, [pts], True, color_bgr, thickness)
        elif shape == "heart":
            t_vals = np.linspace(0, 2 * np.pi, 100)
            hx = 16 * np.sin(t_vals) ** 3
            hy = -(13 * np.cos(t_vals) - 5 * np.cos(2 * t_vals) -
                    2 * np.cos(3 * t_vals) - np.cos(4 * t_vals))
            scale = s / 18.0
            pts = np.array(
                [[px + int(x * scale), py + int(y * scale)] for x, y in zip(hx, hy)],
                dtype=np.int32
            )
            if filled:
                cv2.fillPoly(overlay, [pts], color_bgr)
            else:
                cv2.polylines(overlay, [pts], True, color_bgr, thickness)

    # Alpha blend
    result = np.clip(
        frame.astype(np.float32) * (1 - opacity) + overlay.astype(np.float32) * opacity,
        0, 255
    ).astype(np.uint8)

    return result


def lens_flare(frame, position_x=0.3, position_y=0.3, intensity=0.7,
               size=0.15, color_r=255, color_g=200, color_b=100,
               streaks=6, animate=True, drift_speed=0.5,
               mood="cinematic", frame_index=0, total_frames=1):
    """Animated lens flare with position control, streaks, and drift.

    Moods:
        cinematic — warm golden flare with subtle streaks
        retro — rainbow prismatic with heavy streaks
        sci_fi — cool blue/white with sharp geometric ghosts
    """
    h, w = frame.shape[:2]

    # Animate position drift
    if animate and total_frames > 1:
        t = frame_index / max(total_frames, 1) * drift_speed
        px = int((position_x + np.sin(t * 1.5) * 0.05) * w)
        py = int((position_y + np.cos(t * 2.0) * 0.03) * h)
    else:
        px = int(position_x * w)
        py = int(position_y * h)

    flare_size = int(min(h, w) * size)
    overlay = np.zeros_like(frame, dtype=np.float32)

    # Central glow
    if mood == "cinematic":
        color = np.array([color_b, color_g, color_r], dtype=np.float32) / 255
    elif mood == "retro":
        color = np.array([0.6, 0.8, 1.0], dtype=np.float32)
    else:  # sci_fi
        color = np.array([1.0, 0.9, 0.7], dtype=np.float32)

    # Radial gradient for main glow
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.sqrt((xs - px) ** 2 + (ys - py) ** 2)
    glow = np.exp(-(dist ** 2) / (2 * (flare_size * 0.5) ** 2))
    for c in range(3):
        overlay[:, :, c] = glow * color[c] * 255

    # Streaks (anamorphic)
    if streaks > 0:
        for s in range(streaks):
            angle = s * np.pi / streaks
            streak_len = flare_size * 3
            streak_w = max(1, flare_size // 8)
            cos_a, sin_a = np.cos(angle), np.sin(angle)

            for sign in [-1, 1]:
                x2 = int(px + sign * streak_len * cos_a)
                y2 = int(py + sign * streak_len * sin_a)
                cv2.line(overlay.astype(np.uint8), (px, py), (x2, y2),
                         (int(color[0] * 200), int(color[1] * 200), int(color[2] * 200)),
                         streak_w)

        # Soften streaks
        overlay = cv2.GaussianBlur(overlay, (0, 0), sigmaX=flare_size * 0.3)

    # Ghost orbs (secondary reflections along axis through center)
    if mood in ("retro", "sci_fi"):
        cx, cy = w // 2, h // 2
        dx, dy = cx - px, cy - py
        for g in range(3):
            gx = int(cx + dx * (0.5 + g * 0.3))
            gy = int(cy + dy * (0.5 + g * 0.3))
            ghost_size = flare_size * (0.3 - g * 0.05)
            ghost_glow = np.exp(-((xs - gx) ** 2 + (ys - gy) ** 2) / (2 * ghost_size ** 2))
            hue_shift = [0.3, 0.6, 0.9][g]
            ghost_color = np.array([
                color[0] * hue_shift,
                color[1] * (1 - hue_shift * 0.3),
                color[2] * (1 - hue_shift * 0.5)
            ])
            for c in range(3):
                overlay[:, :, c] += ghost_glow * ghost_color[c] * 150

    # Additive blend
    result = np.clip(
        frame.astype(np.float32) + overlay * intensity,
        0, 255
    ).astype(np.uint8)

    return result


def watercolor(frame, edge_strength=0.5, blur_radius=7, paper_texture=0.3,
               saturation_boost=1.2, mood="classic", seed=42,
               frame_index=0, total_frames=1):
    """Watercolor paint effect — soft edges bleeding into paper texture.

    Moods:
        classic — traditional watercolor look
        vibrant — high saturation, bold colors
        faded — desaturated, vintage watercolor
    """
    h, w = frame.shape[:2]

    # Step 1: Bilateral filter for paint-like smoothing (preserves edges)
    smooth = cv2.bilateralFilter(frame, d=9, sigmaColor=75, sigmaSpace=75)

    # Step 2: Edge detection for paint boundaries
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 2
    )
    edges_3 = cv2.merge([edges] * 3)

    # Step 3: Combine smooth + edges
    result = cv2.bitwise_and(smooth, edges_3)

    # Step 4: Additional softening pass
    ksize = max(3, blur_radius * 2 + 1)
    if ksize % 2 == 0:
        ksize += 1
    result = cv2.GaussianBlur(result, (ksize, ksize), 0)

    # Step 5: Blend edges back in
    if edge_strength > 0:
        edge_inv = 255 - edges
        edge_color = cv2.merge([edge_inv] * 3).astype(np.float32)
        result = np.clip(
            result.astype(np.float32) - edge_color * edge_strength * 0.3,
            0, 255
        ).astype(np.uint8)

    # Step 6: Paper texture
    if paper_texture > 0:
        rng = np.random.RandomState(seed)
        paper = rng.randint(200, 255, (h, w), dtype=np.uint8)
        paper = cv2.GaussianBlur(paper, (5, 5), 0)
        paper_3 = cv2.merge([paper] * 3).astype(np.float32) / 255.0
        result = np.clip(
            result.astype(np.float32) * (1 - paper_texture * 0.3) +
            result.astype(np.float32) * paper_3 * paper_texture * 0.3,
            0, 255
        ).astype(np.uint8)

    # Step 7: Mood adjustments
    if mood == "vibrant":
        hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation_boost * 1.5, 0, 255)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] * 1.1, 0, 255)
        result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    elif mood == "faded":
        hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = hsv[:, :, 1] * 0.5
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] * 0.9 + 30, 0, 255)
        result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    elif mood == "classic" and saturation_boost != 1.0:
        hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation_boost, 0, 255)
        result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    return result


def rainbow_shift(frame, speed=1.0, direction="horizontal", opacity=0.4,
                  wave=True, mood="smooth", frame_index=0, total_frames=1):
    """Rainbow gradient sweep across the frame.

    Directions: horizontal, vertical, diagonal, radial
    Moods:
        smooth — gentle rainbow wash
        bands — distinct color bands
        prismatic — sharp prismatic rainbow
    """
    h, w = frame.shape[:2]
    t = frame_index / max(total_frames, 1) * speed

    # Create hue gradient
    if direction == "horizontal":
        gradient = np.linspace(0, 180, w, dtype=np.float32)
        hue = np.tile(gradient, (h, 1))
    elif direction == "vertical":
        gradient = np.linspace(0, 180, h, dtype=np.float32)
        hue = np.tile(gradient.reshape(-1, 1), (1, w))
    elif direction == "diagonal":
        ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
        hue = ((xs / w + ys / h) * 90).astype(np.float32)
    else:  # radial
        ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
        cx, cy = w / 2, h / 2
        dist = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
        hue = (dist / max(h, w) * 360).astype(np.float32)

    # Animate by shifting hue over time
    hue = np.mod(hue + t * 180, 180).astype(np.float32)

    if wave:
        ys_wave = np.arange(h, dtype=np.float32).reshape(-1, 1)
        hue = np.mod(hue + np.sin(ys_wave * 0.02 + t * 3) * 20, 180).astype(np.float32)

    # Build rainbow overlay
    sat = np.full((h, w), 255, dtype=np.float32)
    val = np.full((h, w), 255, dtype=np.float32)

    if mood == "bands":
        hue = (np.round(hue / 30) * 30).astype(np.float32)
    elif mood == "prismatic":
        hue = (np.round(hue / 15) * 15).astype(np.float32)
        sat = np.full((h, w), 255, dtype=np.float32)

    hsv = np.stack([hue, sat, val], axis=2).astype(np.uint8)
    rainbow = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    # Blend with original
    result = np.clip(
        frame.astype(np.float32) * (1 - opacity) + rainbow.astype(np.float32) * opacity,
        0, 255
    ).astype(np.uint8)

    return result


def sparkle(frame, density=0.002, size=3, brightness=1.0, color_r=255,
            color_g=255, color_b=255, animate=True, twinkle_speed=2.0,
            spread="random", mood="glitter", seed=42,
            frame_index=0, total_frames=1):
    """Animated sparkle/glitter overlay.

    Spreads: random, highlights (only on bright areas), edges
    Moods:
        glitter — bright sharp points
        fairy — soft warm glow points
        frost — cool blue-white ice crystals
    """
    h, w = frame.shape[:2]
    result = frame.copy()

    # Determine sparkle positions
    num_sparkles = int(h * w * density)
    if num_sparkles < 1:
        return result

    # Seed changes each frame for animation
    if animate:
        frame_seed = seed + frame_index
    else:
        frame_seed = seed
    rng = np.random.RandomState(frame_seed)

    if spread == "highlights":
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        bright_pixels = np.where(gray > 180)
        if len(bright_pixels[0]) == 0:
            return result
        indices = rng.choice(len(bright_pixels[0]), min(num_sparkles, len(bright_pixels[0])), replace=False)
        ys = bright_pixels[0][indices]
        xs = bright_pixels[1][indices]
    elif spread == "edges":
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        edge_pixels = np.where(edges > 0)
        if len(edge_pixels[0]) == 0:
            return result
        indices = rng.choice(len(edge_pixels[0]), min(num_sparkles, len(edge_pixels[0])), replace=False)
        ys = edge_pixels[0][indices]
        xs = edge_pixels[1][indices]
    else:  # random
        ys = rng.randint(0, h, num_sparkles)
        xs = rng.randint(0, w, num_sparkles)

    # Per-sparkle brightness variation (twinkle)
    if animate:
        phases = rng.rand(len(ys)) * 2 * np.pi
        twinkle = (np.sin(phases + frame_index * twinkle_speed * 0.3) + 1) / 2
    else:
        twinkle = np.ones(len(ys))

    # Color per mood
    if mood == "frost":
        color = np.array([255, 230, 200], dtype=np.float32)  # BGR cool
    elif mood == "fairy":
        color = np.array([int(color_b * 0.8), int(color_g), int(color_r)], dtype=np.float32)
    else:  # glitter
        color = np.array([color_b, color_g, color_r], dtype=np.float32)

    for i in range(len(ys)):
        y, x = int(ys[i]), int(xs[i])
        b = twinkle[i] * brightness
        if b < 0.1:
            continue

        s = max(1, int(size * (0.5 + twinkle[i] * 0.5)))
        c = tuple(int(min(255, v * b)) for v in color)

        if mood == "glitter":
            # Sharp cross pattern
            cv2.line(result, (x - s, y), (x + s, y), c, 1)
            cv2.line(result, (x, y - s), (x, y + s), c, 1)
        elif mood == "fairy":
            # Soft glow dot
            cv2.circle(result, (x, y), s, c, -1)
        elif mood == "frost":
            # Star/crystal pattern
            for angle in range(0, 360, 60):
                rad = np.radians(angle)
                x2 = int(x + s * np.cos(rad))
                y2 = int(y + s * np.sin(rad))
                cv2.line(result, (x, y), (x2, y2), c, 1)

    # Optional soft glow pass for fairy mood
    if mood == "fairy":
        diff = cv2.absdiff(result, frame)
        glow = cv2.GaussianBlur(diff, (0, 0), sigmaX=size * 2)
        result = np.clip(result.astype(np.float32) + glow.astype(np.float32) * 0.5, 0, 255).astype(np.uint8)

    return result


def film_grain_warm(frame, amount=0.15, size=1.0, warmth=0.3, flicker=True,
                    mood="vintage", seed=42, frame_index=0, total_frames=1):
    """Warm cinematic film grain — organic texture with color warmth.

    Moods:
        vintage — warm yellowish grain, gentle
        kodak — orange/amber tint, medium grain
        expired — heavy grain, color shifts, light leaks
    """
    h, w = frame.shape[:2]

    # Animated grain
    if flicker:
        rng = np.random.RandomState(seed + frame_index)
    else:
        rng = np.random.RandomState(seed)

    # Generate grain
    if size > 1.5:
        # Coarse grain: generate at lower res and upscale
        sh, sw = max(1, int(h / size)), max(1, int(w / size))
        grain_small = rng.randn(sh, sw).astype(np.float32)
        grain = cv2.resize(grain_small, (w, h), interpolation=cv2.INTER_LINEAR)
    else:
        grain = rng.randn(h, w).astype(np.float32)

    grain = grain * amount * 128

    # Apply grain per channel with warmth bias
    result = frame.astype(np.float32)
    # More grain in blue (shadows), less in red (warmth)
    warm_bias = np.array([1.0 + warmth * 0.3, 1.0, 1.0 - warmth * 0.3])
    for c in range(3):
        result[:, :, c] += grain * warm_bias[c]

    # Mood adjustments
    if mood == "kodak":
        # Amber tint
        result[:, :, 2] += 8   # R
        result[:, :, 1] += 3   # G
        result[:, :, 0] -= 5   # B
    elif mood == "expired":
        # Random light leak
        leak_x = rng.randint(0, max(1, w - w // 3))
        leak_w = w // 3
        leak_grad = np.linspace(0, 1, leak_w).reshape(1, -1)
        leak_strength = amount * 80
        if leak_x + leak_w <= w:
            result[:, leak_x:leak_x + leak_w, 2] += leak_grad * leak_strength  # Red leak
            result[:, leak_x:leak_x + leak_w, 1] += leak_grad * leak_strength * 0.3
        # Extra color shift
        result[:, :, 0] -= 10  # Reduce blue
        result[:, :, 2] += 5   # Boost red

    result = np.clip(result, 0, 255).astype(np.uint8)
    return result

"""
Entropic — Pixel Physics Engine

Simulated physics on pixel displacement fields. Instead of per-pixel
particle sim (too slow), we maintain 2D velocity and displacement fields
that accumulate over time, then remap pixels through them.

Every effect here creates MOTION — pixels flow, get pulled, scatter,
swirl, and melt based on simulated physical forces.
"""

import numpy as np
import cv2

# ─── State buffers ───
_physics_state = {}
_physics_access_order = []  # LRU tracking: most recent at end
_MAX_PHYSICS_ENTRIES = 8    # Cap: ~250MB at 1080p (8 × 31.6MB)

# Number of warm-up iterations for single-frame preview.
# This lets physics effects show visible displacement even on frame 0.
_PREVIEW_WARMUP_FRAMES = 8


def _get_state(key, h, w):
    """Get or create physics state for this effect instance.

    Enforces LRU eviction when state entries exceed _MAX_PHYSICS_ENTRIES.
    Each entry holds 4 float32 fields of shape (H, W) = ~31.6MB at 1080p.
    """
    if key in _physics_state:
        # Move to end (most recently used)
        if key in _physics_access_order:
            _physics_access_order.remove(key)
        _physics_access_order.append(key)
        return _physics_state[key]

    # Evict LRU entries if at capacity
    while len(_physics_state) >= _MAX_PHYSICS_ENTRIES and _physics_access_order:
        evict_key = _physics_access_order.pop(0)
        _physics_state.pop(evict_key, None)

    _physics_state[key] = {
        "dx": np.zeros((h, w), dtype=np.float32),  # x displacement
        "dy": np.zeros((h, w), dtype=np.float32),  # y displacement
        "vx": np.zeros((h, w), dtype=np.float32),  # x velocity
        "vy": np.zeros((h, w), dtype=np.float32),  # y velocity
    }
    _physics_access_order.append(key)
    return _physics_state[key]


def _is_preview(frame_index, total_frames):
    """True when running in single-frame preview mode.

    Detects both true single-frame (total_frames=1) and image uploads
    where the server creates a short pseudo-video (total_frames<=10).
    Physics warmup ensures visible displacement on the first preview.
    """
    return frame_index == 0 and total_frames <= 10


def _remap_frame(frame, dx, dy, boundary="clamp"):
    """Remap frame through displacement field.

    Args:
        boundary: What happens when pixels leave the frame.
            "clamp"  — edge pixel stretches (original behavior)
            "black"  — out-of-bounds reveals black void
            "wrap"   — tiles: bottom bleeds into top, right into left
            "mirror" — reflects at edges
    """
    h, w = frame.shape[:2]
    y_coords, x_coords = np.mgrid[0:h, 0:w].astype(np.float32)
    raw_x = x_coords + dx
    raw_y = y_coords + dy

    if boundary == "wrap":
        map_x = (raw_x % w).astype(np.float32)
        map_y = (raw_y % h).astype(np.float32)
    elif boundary == "mirror":
        # Reflect: fold coordinates back at boundaries
        map_x = raw_x % (2 * w)
        map_x = np.where(map_x >= w, 2 * w - map_x - 1, map_x)
        map_x = np.clip(map_x, 0, w - 1).astype(np.float32)
        map_y = raw_y % (2 * h)
        map_y = np.where(map_y >= h, 2 * h - map_y - 1, map_y)
        map_y = np.clip(map_y, 0, h - 1).astype(np.float32)
    elif boundary == "black":
        map_x = raw_x.astype(np.float32)
        map_y = raw_y.astype(np.float32)
        result = cv2.remap(
            frame.astype(np.float32), map_x, map_y,
            cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0),
        )
        return result
    else:  # clamp
        map_x = np.clip(raw_x, 0, w - 1).astype(np.float32)
        map_y = np.clip(raw_y, 0, h - 1).astype(np.float32)

    return cv2.remap(frame.astype(np.float32), map_x, map_y, cv2.INTER_LINEAR)


def pixel_liquify(
    frame: np.ndarray,
    viscosity: float = 0.92,
    turbulence: float = 3.0,
    flow_scale: float = 40.0,
    speed: float = 1.0,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    boundary: str = "wrap",
) -> np.ndarray:
    """Liquify — pixels become fluid and wash around.

    A turbulent flow field accumulates over time. Pixels drift
    through the field like paint in water. Viscosity controls
    how quickly motion decays.

    Args:
        viscosity: Drag coefficient (0.8-0.99). Higher = flows longer.
        turbulence: Noise amplitude for flow forces (1-10).
        flow_scale: Spatial scale of turbulence (10-100). Larger = bigger swirls.
        speed: Time multiplier for flow evolution (0.5-3.0).
    """
    h, w = frame.shape[:2]
    state = _get_state(f"liquify_{seed}", h, w)

    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
    x_norm = x_grid / flow_scale
    y_norm = y_grid / flow_scale

    # In preview mode, warm up the displacement field so the effect is visible
    iterations = _PREVIEW_WARMUP_FRAMES if _is_preview(frame_index, total_frames) else 1

    for step in range(iterations):
        t = (frame_index + step) * speed / 30.0
        rng = np.random.default_rng(seed)

        # Multi-octave turbulence
        fx = np.zeros((h, w), dtype=np.float32)
        fy = np.zeros((h, w), dtype=np.float32)
        for octave in range(3):
            freq = 2 ** octave
            amp = turbulence / freq
            phase_x = rng.random() * 100
            phase_y = rng.random() * 100
            fx += amp * np.sin(x_norm * freq + t * 2.0 + phase_x) * np.cos(y_norm * freq * 0.7 + t * 1.5 + phase_y)
            fy += amp * np.cos(x_norm * freq * 0.8 + t * 1.8 + phase_x) * np.sin(y_norm * freq + t * 2.2 + phase_y)

        # Apply forces to velocity
        state["vx"] = state["vx"] * viscosity + fx * 0.1
        state["vy"] = state["vy"] * viscosity + fy * 0.1

        # Update displacement
        state["dx"] += state["vx"]
        state["dy"] += state["vy"]

    # Clamp displacement to prevent pixels from going too far
    max_disp = max(h, w) * 0.3
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    result = _remap_frame(frame, state["dx"], state["dy"], boundary)

    if total_frames > 1 and frame_index >= total_frames - 1:
        _physics_state.pop(f"liquify_{seed}", None)

    return np.clip(result, 0, 255).astype(np.uint8)


def pixel_gravity(
    frame: np.ndarray,
    num_attractors: int = 5,
    gravity_strength: float = 8.0,
    damping: float = 0.95,
    attractor_radius: float = 0.3,
    wander: float = 0.5,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    boundary: str = "black",
) -> np.ndarray:
    """Gravity attractors — pixels get pulled toward random points.

    Random attractor points are placed in the frame. Each pixel
    experiences gravitational pull toward nearby attractors. Pixels
    accumulate velocity and get sucked in over time.

    Args:
        num_attractors: How many gravity wells (1-20).
        gravity_strength: Pull force (1-30). Higher = faster collapse.
        damping: Velocity decay (0.8-0.99). Higher = more momentum.
        attractor_radius: Influence radius as fraction of frame size (0.1-1.0).
        wander: How much attractors drift over time (0-2.0).
    """
    h, w = frame.shape[:2]
    key = f"gravity_{seed}"
    state = _get_state(key, h, w)

    rng = np.random.default_rng(seed)
    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
    radius_px = attractor_radius * max(h, w)

    iterations = _PREVIEW_WARMUP_FRAMES if _is_preview(frame_index, total_frames) else 1

    for step in range(iterations):
        t = (frame_index + step) / 30.0

        # Generate attractor positions (seeded, so consistent across frames)
        _rng = np.random.default_rng(seed)
        base_positions = _rng.random((num_attractors, 2))
        attractors_x = base_positions[:, 0] * w
        attractors_y = base_positions[:, 1] * h

        if wander > 0:
            for i in range(num_attractors):
                attractors_x[i] += np.sin(t * 0.5 + i * 2.1) * w * wander * 0.1
                attractors_y[i] += np.cos(t * 0.7 + i * 1.7) * h * wander * 0.1

        fx_total = np.zeros((h, w), dtype=np.float32)
        fy_total = np.zeros((h, w), dtype=np.float32)

        for i in range(num_attractors):
            dx = attractors_x[i] - x_grid
            dy = attractors_y[i] - y_grid
            dist = np.sqrt(dx * dx + dy * dy) + 1.0
            force = gravity_strength / (dist * dist) * np.exp(-dist / radius_px) * 1000
            fx_total += dx / dist * force
            fy_total += dy / dist * force

        state["vx"] = state["vx"] * damping + fx_total * 0.01
        state["vy"] = state["vy"] * damping + fy_total * 0.01
        state["dx"] += state["vx"]
        state["dy"] += state["vy"]

    max_disp = max(h, w) * 0.4
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    result = _remap_frame(frame, state["dx"], state["dy"], boundary)

    if total_frames > 1 and frame_index >= total_frames - 1:
        _physics_state.pop(key, None)

    return np.clip(result, 0, 255).astype(np.uint8)


def pixel_vortex(
    frame: np.ndarray,
    num_vortices: int = 3,
    spin_strength: float = 5.0,
    pull_strength: float = 2.0,
    radius: float = 0.25,
    damping: float = 0.93,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    boundary: str = "wrap",
) -> np.ndarray:
    """Vortex — swirling whirlpools pull pixels into spirals.

    Random vortex centers spin pixels around them while pulling
    inward. Creates spiral distortion that accumulates over time.

    Args:
        num_vortices: How many vortex centers (1-10).
        spin_strength: Rotational force (1-20).
        pull_strength: Inward pull (0-10). 0 = pure spin, no collapse.
        radius: Vortex influence radius as fraction of frame (0.1-1.0).
        damping: Velocity decay (0.8-0.99).
    """
    h, w = frame.shape[:2]
    key = f"vortex_{seed}"
    state = _get_state(key, h, w)

    rng = np.random.default_rng(seed)
    positions = rng.random((num_vortices, 2))
    spins = np.array([(-1) ** i for i in range(num_vortices)], dtype=np.float32)

    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
    radius_px = radius * max(h, w)

    iterations = _PREVIEW_WARMUP_FRAMES if _is_preview(frame_index, total_frames) else 1

    for step in range(iterations):
        fx_total = np.zeros((h, w), dtype=np.float32)
        fy_total = np.zeros((h, w), dtype=np.float32)

        for i in range(num_vortices):
            cx = positions[i, 0] * w
            cy = positions[i, 1] * h
            dx = x_grid - cx
            dy = y_grid - cy
            dist = np.sqrt(dx * dx + dy * dy) + 1.0
            falloff = np.exp(-dist / radius_px)

            fx_spin = -dy / dist * spin_strength * spins[i] * falloff
            fy_spin = dx / dist * spin_strength * spins[i] * falloff
            fx_pull = -dx / dist * pull_strength * falloff
            fy_pull = -dy / dist * pull_strength * falloff

            fx_total += fx_spin + fx_pull
            fy_total += fy_spin + fy_pull

        state["vx"] = state["vx"] * damping + fx_total * 0.05
        state["vy"] = state["vy"] * damping + fy_total * 0.05
        state["dx"] += state["vx"]
        state["dy"] += state["vy"]

    max_disp = max(h, w) * 0.4
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    result = _remap_frame(frame, state["dx"], state["dy"], boundary)

    if total_frames > 1 and frame_index >= total_frames - 1:
        _physics_state.pop(key, None)

    return np.clip(result, 0, 255).astype(np.uint8)


def pixel_explode(
    frame: np.ndarray,
    origin: str = "center",
    force: float = 10.0,
    damping: float = 0.96,
    gravity: float = 0.0,
    scatter: float = 0.0,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    boundary: str = "black",
) -> np.ndarray:
    """Explode — pixels blast outward from a point.

    An explosion radiates pixels outward from the origin. With gravity,
    they arc and fall. With scatter, random turbulence disrupts the
    outward trajectory.

    Args:
        origin: Explosion center ("center", "random", "top", "bottom").
        force: Initial blast force (1-30).
        damping: How fast explosion energy decays (0.8-0.99).
        gravity: Downward pull after explosion (0-5).
        scatter: Random turbulence during flight (0-5).
    """
    h, w = frame.shape[:2]
    key = f"explode_{seed}"
    state = _get_state(key, h, w)

    rng = np.random.default_rng(seed + frame_index)

    # Determine origin
    if origin == "center":
        ox, oy = w / 2, h / 2
    elif origin == "random":
        srng = np.random.default_rng(seed)
        ox, oy = srng.random() * w, srng.random() * h
    elif origin == "top":
        ox, oy = w / 2, 0
    elif origin == "bottom":
        ox, oy = w / 2, h
    else:
        ox, oy = w / 2, h / 2

    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)

    # On first frame, apply initial blast
    if frame_index == 0:
        dx = x_grid - ox
        dy = y_grid - oy
        dist = np.sqrt(dx * dx + dy * dy) + 1.0
        # Blast force — inverse distance (closer to origin = stronger push)
        blast = force * 50.0 / (dist + 10.0)
        state["vx"] = dx / dist * blast * 0.1
        state["vy"] = dy / dist * blast * 0.1

    # Apply ongoing forces
    state["vx"] *= damping
    state["vy"] *= damping

    # Gravity (downward)
    if gravity > 0:
        state["vy"] += gravity * 0.1

    # Scatter (random turbulence)
    if scatter > 0:
        state["vx"] += (rng.random((h, w)).astype(np.float32) - 0.5) * scatter * 0.5
        state["vy"] += (rng.random((h, w)).astype(np.float32) - 0.5) * scatter * 0.5

    state["dx"] += state["vx"]
    state["dy"] += state["vy"]

    max_disp = max(h, w) * 0.5
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    result = _remap_frame(frame, state["dx"], state["dy"], boundary)

    if total_frames > 1 and frame_index >= total_frames - 1:
        _physics_state.pop(key, None)

    return np.clip(result, 0, 255).astype(np.uint8)


def pixel_elastic(
    frame: np.ndarray,
    stiffness: float = 0.3,
    mass: float = 1.0,
    force_type: str = "turbulence",
    force_strength: float = 5.0,
    damping: float = 0.9,
    concentrate_x: float = 0.5,
    concentrate_y: float = 0.5,
    concentrate_radius: float = 0.0,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    boundary: str = "mirror",
) -> np.ndarray:
    """Elastic — pixels are on springs that stretch and snap back.

    Each pixel is attached to its original position by a spring.
    External forces push pixels away, but the spring pulls them back.
    Creates wobbly jello-like distortion that bounces.

    Args:
        stiffness: Spring stiffness (0.05-0.8). Higher = snappier return.
        mass: Pixel mass (0.5-3.0). Heavier = slower, more momentum.
        force_type: What pushes pixels ("turbulence", "brightness",
                    "edges", "radial", "vortex", "wave", "shatter", "pulse").
        force_strength: How hard the push (1-20).
        damping: Energy loss per frame (0.8-0.99).
        concentrate_x: Force center X (0-1). Only used when concentrate_radius > 0.
        concentrate_y: Force center Y (0-1). Only used when concentrate_radius > 0.
        concentrate_radius: Focus force to a region (0 = full frame, 0.1-1.0 = radius).
    """
    h, w = frame.shape[:2]
    key = f"elastic_{seed}"
    state = _get_state(key, h, w)

    # Clamp parameters to useful ranges
    mass = max(0.1, min(5.0, float(mass)))
    stiffness = max(0.05, min(0.8, float(stiffness)))
    force_strength = max(1.0, min(20.0, float(force_strength)))
    damping = max(0.8, min(0.99, float(damping)))

    rng = np.random.default_rng(seed)
    phase_x = rng.random() * 100
    phase_y = rng.random() * 100
    iterations = _PREVIEW_WARMUP_FRAMES if _is_preview(frame_index, total_frames) else 1

    for step in range(iterations):
        t = (frame_index + step) / 30.0

        # Compute external force
        if force_type == "turbulence":
            y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
            fx = force_strength * np.sin(x_grid / 30.0 + t * 3 + phase_x) * np.cos(y_grid / 25.0 + t * 2 + phase_y)
            fy = force_strength * np.cos(x_grid / 25.0 + t * 2.5 + phase_x) * np.sin(y_grid / 30.0 + t * 3.5 + phase_y)

        elif force_type == "brightness":
            gray = np.mean(frame.astype(np.float32), axis=2)
            grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=5)
            grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=5)
            fx = grad_x * force_strength * 0.01
            fy = grad_y * force_strength * 0.01

        elif force_type == "edges":
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            edges = cv2.Canny(gray, 50, 150).astype(np.float32) / 255.0
            edge_rng = np.random.default_rng(seed + step)
            rand_x = (edge_rng.random((h, w)).astype(np.float32) - 0.5) * 2
            rand_y = (edge_rng.random((h, w)).astype(np.float32) - 0.5) * 2
            fx = edges * rand_x * force_strength
            fy = edges * rand_y * force_strength

        elif force_type == "radial":
            y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
            cx, cy = w / 2, h / 2
            dx = x_grid - cx
            dy = y_grid - cy
            dist = np.sqrt(dx * dx + dy * dy) + 1.0
            pulse = np.sin(t * 3) * force_strength
            fx = dx / dist * pulse * 0.3
            fy = dy / dist * pulse * 0.3

        elif force_type == "vortex":
            # Spinning force — pixels orbit around center
            y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
            cx, cy = w / 2, h / 2
            dx = x_grid - cx
            dy = y_grid - cy
            dist = np.sqrt(dx * dx + dy * dy) + 1.0
            spin_speed = np.sin(t * 2) * force_strength
            fx = -dy / dist * spin_speed * 0.3
            fy = dx / dist * spin_speed * 0.3

        elif force_type == "wave":
            # Directional sine wave push
            y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
            fx = force_strength * np.sin(y_grid / 20.0 + t * 4 + phase_x)
            fy = force_strength * 0.3 * np.cos(x_grid / 25.0 + t * 3 + phase_y)

        elif force_type == "shatter":
            # Fragmented displacement — breaks image into displaced blocks
            y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
            block_size = max(8, int(30 - force_strength))
            block_rng = np.random.default_rng(seed + int(t * 5))
            bx = (x_grid / block_size).astype(int)
            by = (y_grid / block_size).astype(int)
            block_id = bx * 97 + by * 31 + seed
            block_angles = np.vectorize(
                lambda bid: np.random.default_rng(int(bid) % (2**31)).random() * 2 * np.pi
            )(block_id).astype(np.float32)
            block_mag = np.vectorize(
                lambda bid: np.random.default_rng((int(bid) + 7) % (2**31)).random()
            )(block_id).astype(np.float32)
            fx = np.cos(block_angles) * block_mag * force_strength * 2
            fy = np.sin(block_angles) * block_mag * force_strength * 2

        elif force_type == "pulse":
            # Concentric rings emanating from center
            y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
            cx, cy = w / 2, h / 2
            dx = x_grid - cx
            dy = y_grid - cy
            dist = np.sqrt(dx * dx + dy * dy) + 1.0
            wave_freq = 0.05
            ring = np.sin(dist * wave_freq - t * 6) * force_strength
            fx = dx / dist * ring * 0.4
            fy = dy / dist * ring * 0.4

        else:
            fx = np.zeros((h, w), dtype=np.float32)
            fy = np.zeros((h, w), dtype=np.float32)

        # Apply spatial concentration mask
        if concentrate_radius > 0:
            cy_px = int(max(0.0, min(1.0, float(concentrate_y))) * h)
            cx_px = int(max(0.0, min(1.0, float(concentrate_x))) * w)
            r_px = max(1, int(concentrate_radius * max(h, w)))
            y_grid_c, x_grid_c = np.mgrid[0:h, 0:w].astype(np.float32)
            dist_c = np.sqrt((x_grid_c - cx_px) ** 2 + (y_grid_c - cy_px) ** 2)
            mask = np.exp(-(dist_c ** 2) / (r_px ** 2 * 2))
            fx *= mask
            fy *= mask

        # Spring physics: F_spring = -stiffness * displacement
        spring_fx = -stiffness * state["dx"]
        spring_fy = -stiffness * state["dy"]

        # Mass affects inertia (how sluggish), not force magnitude.
        # High mass = slower acceleration but same eventual displacement.
        # mass=0.1 → factor=1.82, mass=1 → factor=1.0, mass=3 → factor=0.5, mass=5 → factor=0.33
        mass_factor = 1.0 / mass
        # External force scaled so it visibly displaces even at high mass
        ax = (fx * 0.15 + spring_fx) * mass_factor
        ay = (fy * 0.15 + spring_fy) * mass_factor

        # Update velocity and position (Euler integration)
        state["vx"] = (state["vx"] + ax) * damping
        state["vy"] = (state["vy"] + ay) * damping
        state["dx"] += state["vx"]
        state["dy"] += state["vy"]

    max_disp = max(h, w) * 0.3
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    result = _remap_frame(frame, state["dx"], state["dy"], boundary)

    if total_frames > 1 and frame_index >= total_frames - 1:
        _physics_state.pop(key, None)

    return np.clip(result, 0, 255).astype(np.uint8)


def pixel_melt(
    frame: np.ndarray,
    heat: float = 3.0,
    gravity: float = 2.0,
    viscosity: float = 0.95,
    melt_source: str = "top",
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    boundary: str = "black",
) -> np.ndarray:
    """Melt — pixels drip and flow downward like melting wax.

    Gravity pulls pixels down while heat creates horizontal drift.
    The effect accumulates from one direction, creating a melting
    curtain effect.

    Args:
        heat: Horizontal turbulence during melting (0-10).
        gravity: Downward pull strength (0.5-10).
        viscosity: Flow resistance (0.85-0.99). Higher = flows longer.
        melt_source: Where melting starts ("top", "bottom", "edges", "all").
    """
    h, w = frame.shape[:2]
    key = f"melt_{seed}"
    state = _get_state(key, h, w)

    rng = np.random.default_rng(seed)
    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
    phase = rng.random() * 100

    iterations = _PREVIEW_WARMUP_FRAMES if _is_preview(frame_index, total_frames) else 1
    # In preview, simulate total_frames worth of progression
    sim_total = max(total_frames, iterations * 2)

    for step in range(iterations):
        sim_frame = frame_index + step
        t = sim_frame / 30.0
        progress = min(1.0, sim_frame / max(sim_total * 0.7, 1))

        if melt_source == "top":
            melt_mask = np.clip((progress * h * 1.5 - y_grid) / (h * 0.2), 0, 1)
        elif melt_source == "bottom":
            melt_mask = np.clip((progress * h * 1.5 - (h - y_grid)) / (h * 0.2), 0, 1)
        elif melt_source == "edges":
            dist_x = np.minimum(x_grid, w - x_grid) / (w * 0.5)
            dist_y = np.minimum(y_grid, h - y_grid) / (h * 0.5)
            dist_edge = np.minimum(dist_x, dist_y)
            melt_mask = np.clip((progress * 1.5 - dist_edge) / 0.2, 0, 1)
        else:  # "all"
            melt_mask = np.full((h, w), progress, dtype=np.float32)

        fy_force = gravity * melt_mask * 0.3
        fx_force = heat * np.sin(x_grid / 20.0 + t * 2 + phase) * melt_mask * 0.2

        state["vx"] = state["vx"] * viscosity + fx_force
        state["vy"] = state["vy"] * viscosity + fy_force
        state["dx"] += state["vx"] * melt_mask
        state["dy"] += state["vy"] * melt_mask

    max_disp = max(h, w) * 0.5
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    result = _remap_frame(frame, state["dx"], state["dy"], boundary)

    if total_frames > 1 and frame_index >= total_frames - 1:
        _physics_state.pop(key, None)

    return np.clip(result, 0, 255).astype(np.uint8)


# ══════════════════════════════════════════════════════════════════════
# IMPOSSIBLE PHYSICS — Things that don't exist in nature
# ══════════════════════════════════════════════════════════════════════

def pixel_blackhole(
    frame: np.ndarray,
    mass: float = 10.0,
    spin: float = 3.0,
    event_horizon: float = 0.08,
    spaghettify: float = 5.0,
    accretion_glow: float = 0.8,
    hawking: float = 0.0,
    position: str = "center",
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    boundary: str = "black",
) -> np.ndarray:
    """Black hole — singularity with event horizon, spaghettification, accretion disk.

    Pixels are pulled toward a singularity with increasing force. Inside the
    event horizon, pixels are stretched radially (spaghettification). An
    accretion disk glows around the boundary. Hawking radiation creates
    pixel noise near the horizon.

    Args:
        mass: Gravitational pull strength (1-30).
        spin: Frame-dragging rotation strength (0-10).
        event_horizon: Radius as fraction of frame size (0.02-0.3).
        spaghettify: Radial stretch inside horizon (0-15).
        accretion_glow: Brightness boost around horizon (0-2).
        hawking: Noise emission near horizon (0-3).
        position: Singularity location ("center", "random", "wander").
    """
    h, w = frame.shape[:2]
    key = f"blackhole_{seed}"
    state = _get_state(key, h, w)

    rng = np.random.default_rng(seed)
    t = frame_index / 30.0

    # Singularity position
    if position == "center":
        cx, cy = w / 2, h / 2
    elif position == "random":
        srng = np.random.default_rng(seed)
        cx, cy = srng.random() * w, srng.random() * h
    else:  # wander
        cx = w / 2 + np.sin(t * 0.3) * w * 0.2
        cy = h / 2 + np.cos(t * 0.4) * h * 0.2

    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
    dx = x_grid - cx
    dy = y_grid - cy
    dist = np.sqrt(dx * dx + dy * dy) + 0.1
    horizon_px = event_horizon * max(h, w)

    # Gravitational pull — extreme near singularity
    grav_force = mass * 500.0 / (dist * dist + horizon_px * 0.5)

    # Radial pull
    fx = -dx / dist * grav_force * 0.02
    fy = -dy / dist * grav_force * 0.02

    # Frame-dragging (spin) — tangential force increases near horizon
    spin_factor = spin * np.exp(-dist / (horizon_px * 3))
    fx += -dy / dist * spin_factor * 0.5
    fy += dx / dist * spin_factor * 0.5

    # Spaghettification — stretch radially inside horizon
    inside_horizon = (dist < horizon_px * 2).astype(np.float32)
    stretch = spaghettify * inside_horizon * (1.0 - dist / (horizon_px * 2))
    stretch = np.clip(stretch, 0, spaghettify)
    fx += dx / dist * stretch * 0.3
    fy += dy / dist * stretch * 0.3

    state["vx"] = state["vx"] * 0.92 + fx
    state["vy"] = state["vy"] * 0.92 + fy
    state["dx"] += state["vx"]
    state["dy"] += state["vy"]

    max_disp = max(h, w) * 0.5
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    result = _remap_frame(frame, state["dx"], state["dy"], boundary)

    # Accretion glow — ring around event horizon
    if accretion_glow > 0:
        ring = np.exp(-((dist - horizon_px * 1.5) ** 2) / (horizon_px * horizon_px * 0.5))
        glow = (ring * accretion_glow * 80).astype(np.float32)
        result = result.astype(np.float32)
        result[:, :, 2] += glow  # Red channel glow
        result[:, :, 1] += glow * 0.5  # Warm orange
        result[:, :, 0] += glow * 0.2  # Slight blue

    # Hawking radiation — noise near horizon
    if hawking > 0:
        hawking_zone = np.exp(-((dist - horizon_px) ** 2) / (horizon_px * horizon_px * 0.3))
        noise = rng.random((h, w)).astype(np.float32) * hawking * 60 * hawking_zone
        result = result.astype(np.float32)
        for c in range(min(3, result.shape[2] if result.ndim == 3 else 1)):
            result[:, :, c] += noise

    if total_frames > 1 and frame_index >= total_frames - 1:
        _physics_state.pop(key, None)

    return np.clip(result, 0, 255).astype(np.uint8)


def pixel_antigravity(
    frame: np.ndarray,
    repulsion: float = 8.0,
    num_zones: int = 4,
    zone_radius: float = 0.2,
    oscillate: float = 1.0,
    damping: float = 0.93,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    boundary: str = "wrap",
) -> np.ndarray:
    """Anti-gravity — repulsion zones push pixels away, gravity direction flips.

    Zones of repulsion scatter pixels outward. The gravity direction
    oscillates between push and pull, creating breathing/pulsing distortion.

    Args:
        repulsion: Push-away force (1-20).
        num_zones: Number of repulsion centers (1-10).
        zone_radius: Size of each zone as fraction of frame (0.1-0.8).
        oscillate: Gravity flip rate in Hz (0=constant repulsion, 0.5-3=pulsing).
        damping: Velocity decay (0.8-0.99).
    """
    h, w = frame.shape[:2]
    key = f"antigrav_{seed}"
    state = _get_state(key, h, w)

    rng = np.random.default_rng(seed)

    # Zone positions
    positions = rng.random((num_zones, 2))
    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
    radius_px = zone_radius * max(h, w)

    iterations = _PREVIEW_WARMUP_FRAMES if _is_preview(frame_index, total_frames) else 1

    for step in range(iterations):
        t = (frame_index + step) / 30.0

        # Gravity direction oscillation
        if oscillate > 0:
            grav_dir = np.sin(t * oscillate * np.pi * 2)  # -1 to 1
            # Ensure non-zero force at t=0 by adding phase offset
            if abs(grav_dir) < 0.1:
                grav_dir = -1.0
        else:
            grav_dir = -1.0  # Pure repulsion

        fx_total = np.zeros((h, w), dtype=np.float32)
        fy_total = np.zeros((h, w), dtype=np.float32)

        for i in range(num_zones):
            zx = positions[i, 0] * w
            zy = positions[i, 1] * h
            dx = x_grid - zx
            dy = y_grid - zy
            dist = np.sqrt(dx * dx + dy * dy) + 1.0
            force = repulsion * grav_dir * np.exp(-dist / radius_px) * 100.0 / (dist + 10.0)
            fx_total += dx / dist * force
            fy_total += dy / dist * force

        state["vx"] = state["vx"] * damping + fx_total * 0.01
        state["vy"] = state["vy"] * damping + fy_total * 0.01
        state["dx"] += state["vx"]
        state["dy"] += state["vy"]

    max_disp = max(h, w) * 0.4
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    result = _remap_frame(frame, state["dx"], state["dy"], boundary)

    if total_frames > 1 and frame_index >= total_frames - 1:
        _physics_state.pop(key, None)

    return np.clip(result, 0, 255).astype(np.uint8)


def pixel_magnetic(
    frame: np.ndarray,
    field_type: str = "dipole",
    strength: float = 6.0,
    poles: int = 2,
    rotation_speed: float = 0.5,
    damping: float = 0.92,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    boundary: str = "wrap",
) -> np.ndarray:
    """Magnetic fields — pixels flow along field lines.

    Simulates magnetic field patterns. Pixels experience Lorentz-like force
    perpendicular to their velocity (creating curved paths along field lines).

    Args:
        field_type: "dipole" (N-S), "quadrupole" (4 poles), "toroidal" (donut),
                    "chaotic" (random field lines).
        strength: Magnetic force (1-20).
        poles: Number of poles for multipole fields (2-8).
        rotation_speed: Field rotation rate (0-2).
        damping: Velocity decay (0.8-0.99).
    """
    h, w = frame.shape[:2]
    key = f"magnetic_{seed}"
    state = _get_state(key, h, w)

    # Enforce minimum poles for field types that need them
    if field_type in ("quadrupole", "toroidal") and poles < 2:
        poles = 2

    rng = np.random.default_rng(seed)
    # Seed-based field variation: offset center and tilt angle
    seed_offset_x = (rng.random() - 0.5) * 0.15
    seed_offset_y = (rng.random() - 0.5) * 0.15
    seed_angle = rng.random() * 0.5

    iterations = _PREVIEW_WARMUP_FRAMES if _is_preview(frame_index, total_frames) else 1
    for step in range(iterations):
        t = (frame_index + step) / 30.0
        angle = t * rotation_speed + seed_angle

        y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
        cx, cy = w / 2, h / 2
        nx = (x_grid - cx) / max(w, 1) - seed_offset_x
        ny = (y_grid - cy) / max(h, 1) - seed_offset_y

        # Rotate field over time
        rnx = nx * np.cos(angle) - ny * np.sin(angle)
        rny = nx * np.sin(angle) + ny * np.cos(angle)

        # Clamp helper to prevent overflow near singularities
        field_max = strength * 50.0

        if field_type == "dipole":
            # Multi-pole dipole: `poles` adds additional dipole sources
            bx = np.zeros((h, w), dtype=np.float32)
            by = np.zeros((h, w), dtype=np.float32)
            pole_spread = 0.35  # wider spread makes poles visually distinct
            for p in range(max(1, poles)):
                theta = p * 2 * np.pi / max(1, poles)
                px = pole_spread * np.cos(theta) if poles > 1 else 0.0
                py = pole_spread * np.sin(theta) if poles > 1 else 0.0
                ddx = rnx - px
                ddy = rny - py
                r = np.sqrt(ddx * ddx + ddy * ddy) + 0.05
                sign = (-1) ** p
                bx += sign * 3.0 * ddx * ddy / (r ** 3) * strength
                by += sign * (2.0 * ddy * ddy - ddx * ddx) / (r ** 3) * strength
            bx = np.clip(bx, -field_max, field_max)
            by = np.clip(by, -field_max, field_max)

        elif field_type == "quadrupole":
            bx = np.zeros((h, w), dtype=np.float32)
            by = np.zeros((h, w), dtype=np.float32)
            pole_spread = 0.35
            for p in range(poles):
                theta = p * 2 * np.pi / poles
                px = pole_spread * np.cos(theta)
                py = pole_spread * np.sin(theta)
                ddx = rnx - px
                ddy = rny - py
                r = np.sqrt(ddx * ddx + ddy * ddy) + 0.05
                sign = (-1) ** p
                bx += sign * ddx / (r ** 2.5) * strength
                by += sign * ddy / (r ** 2.5) * strength
            bx = np.clip(bx, -field_max, field_max)
            by = np.clip(by, -field_max, field_max)

        elif field_type == "toroidal":
            r = np.sqrt(rnx * rnx + rny * rny) + 0.01
            # poles controls number of lobes in the toroidal ring
            ring_radius = 0.3
            ring_dist = np.abs(r - ring_radius)
            ring_force = np.exp(-ring_dist * 10) * strength
            # Multi-lobe: modulate around the ring using poles
            theta_field = np.arctan2(rny, rnx)
            lobe_mod = 0.5 + 0.5 * np.cos(theta_field * poles)
            bx = -rny / r * ring_force * lobe_mod
            by = rnx / r * ring_force * lobe_mod

        else:  # chaotic
            field_rng = np.random.default_rng(seed)
            bx = np.zeros((h, w), dtype=np.float32)
            by = np.zeros((h, w), dtype=np.float32)
            for _ in range(5):
                rpx = (field_rng.random() - 0.5) * 0.8
                rpy = (field_rng.random() - 0.5) * 0.8
                ddx = rnx - rpx
                ddy = rny - rpy
                r = np.sqrt(ddx * ddx + ddy * ddy) + 0.05
                bx += ddy / (r ** 2.5) * strength * 0.3
                by += -ddx / (r ** 2.5) * strength * 0.3
            bx = np.clip(bx, -field_max, field_max)
            by = np.clip(by, -field_max, field_max)

        # Lorentz-like force: F perpendicular to v
        # Clamp velocities to prevent overflow in cross products
        vel_max = 50.0
        state["vx"] = np.clip(state["vx"], -vel_max, vel_max)
        state["vy"] = np.clip(state["vy"], -vel_max, vel_max)

        if frame_index == 0 and step == 0:
            state["vx"] = bx * 0.08
            state["vy"] = by * 0.08
        else:
            b_mag = np.sqrt(bx * bx + by * by) + 0.01
            b_mag = np.minimum(b_mag, field_max)
            fx = state["vy"] * b_mag * 0.2 + bx * 0.08
            fy = -state["vx"] * b_mag * 0.2 + by * 0.08
            state["vx"] = state["vx"] * damping + fx
            state["vy"] = state["vy"] * damping + fy

        state["dx"] += state["vx"]
        state["dy"] += state["vy"]

    max_disp = max(h, w) * 0.4
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    result = _remap_frame(frame, state["dx"], state["dy"], boundary)

    if total_frames > 1 and frame_index >= total_frames - 1:
        _physics_state.pop(key, None)

    return np.clip(result, 0, 255).astype(np.uint8)


def pixel_timewarp(
    frame: np.ndarray,
    warp_speed: float = 2.0,
    echo_count: int = 3,
    echo_decay: float = 0.6,
    reverse_probability: float = 0.3,
    damping: float = 0.9,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    boundary: str = "wrap",
) -> np.ndarray:
    """Time warp — displacement reverses, echoes, and ghosts.

    The displacement field periodically reverses direction (pixels spring
    back to origin then overshoot). Multiple "echo" copies of the displacement
    create ghosting/afterimage trails.

    Args:
        warp_speed: How fast time fluctuates (0.5-5).
        echo_count: Number of displacement echoes (1-8).
        echo_decay: How much each echo fades (0.3-0.9).
        reverse_probability: Chance of direction flip per frame (0-1).
        damping: Velocity decay (0.8-0.99).
    """
    h, w = frame.shape[:2]
    key = f"timewarp_{seed}"
    state = _get_state(key, h, w)

    # Guard: at least 1 echo to avoid empty list indexing
    echo_count = max(1, echo_count)
    if "echoes_dx" not in state:
        state["echoes_dx"] = [np.zeros((h, w), dtype=np.float32) for _ in range(echo_count)]
        state["echoes_dy"] = [np.zeros((h, w), dtype=np.float32) for _ in range(echo_count)]
        state["time_dir"] = 1.0

    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
    iterations = _PREVIEW_WARMUP_FRAMES if _is_preview(frame_index, total_frames) else 1

    for step in range(iterations):
        sim_frame = frame_index + step
        rng = np.random.default_rng(seed + sim_frame)
        t = sim_frame / 30.0

        if rng.random() < reverse_probability * 0.1:
            state["time_dir"] *= -1.0

        time_factor = state["time_dir"] * (1.0 + np.sin(t * warp_speed * np.pi) * 0.5)

        phase = rng.random() * 100
        fx = 3.0 * np.sin(x_grid / 30.0 + t * 2 + phase) * np.cos(y_grid / 25.0 + t * 1.5)
        fy = 3.0 * np.cos(x_grid / 25.0 + t * 1.8) * np.sin(y_grid / 30.0 + t * 2.2 + phase)

        state["vx"] = state["vx"] * damping + fx * time_factor * 0.08
        state["vy"] = state["vy"] * damping + fy * time_factor * 0.08

        for i in range(echo_count - 1, 0, -1):
            state["echoes_dx"][i] = state["echoes_dx"][i - 1].copy()
            state["echoes_dy"][i] = state["echoes_dy"][i - 1].copy()
        state["echoes_dx"][0] = state["dx"].copy()
        state["echoes_dy"][0] = state["dy"].copy()

        state["dx"] += state["vx"]
        state["dy"] += state["vy"]

    max_disp = max(h, w) * 0.3
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    # Composite: current + echoes
    result = _remap_frame(frame, state["dx"], state["dy"], boundary).astype(np.float32)
    total_weight = 1.0

    for i in range(echo_count):
        weight = echo_decay ** (i + 1)
        echo_result = _remap_frame(frame, state["echoes_dx"][i], state["echoes_dy"][i], boundary)
        result += echo_result.astype(np.float32) * weight
        total_weight += weight

    result /= total_weight

    if total_frames > 1 and frame_index >= total_frames - 1:
        _physics_state.pop(key, None)

    return np.clip(result, 0, 255).astype(np.uint8)


def pixel_dimensionfold(
    frame: np.ndarray,
    num_folds: int = 3,
    fold_depth: float = 8.0,
    fold_width: float = 0.15,
    rotation_speed: float = 0.3,
    mirror_folds: bool = True,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    boundary: str = "wrap",
) -> np.ndarray:
    """Dimension fold — space folds over itself along rotating axes.

    Strips of the image fold over like pages in a book along
    rotating axes. Pixels on one side of a fold get displaced to the
    other side, creating impossible spatial overlaps.

    Args:
        num_folds: Number of fold axes (1-8).
        fold_depth: How far pixels fold (2-20).
        fold_width: Width of fold zone as fraction of frame (0.05-0.5).
        rotation_speed: How fast fold axes rotate (0-2).
        mirror_folds: Whether folded pixels mirror or wrap.
    """
    h, w = frame.shape[:2]
    key = f"dimensionfold_{seed}"
    state = _get_state(key, h, w)

    rng = np.random.default_rng(seed)

    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w / 2, h / 2

    fold_offsets = rng.random(num_folds) - 0.5
    fold_base_angles = rng.random(num_folds) * np.pi
    fold_width_px = fold_width * max(h, w)

    iterations = _PREVIEW_WARMUP_FRAMES if _is_preview(frame_index, total_frames) else 1

    for step in range(iterations):
        t = (frame_index + step) / 30.0

        fx_total = np.zeros((h, w), dtype=np.float32)
        fy_total = np.zeros((h, w), dtype=np.float32)

        for i in range(num_folds):
            angle = fold_base_angles[i] + t * rotation_speed * ((-1) ** i)
            cos_a = np.cos(angle)
            sin_a = np.sin(angle)

            offset_px = fold_offsets[i] * max(h, w)
            signed_dist = (x_grid - cx) * cos_a + (y_grid - cy) * sin_a - offset_px

            fold_zone = np.exp(-(signed_dist ** 2) / (fold_width_px ** 2 + 1))

            if mirror_folds:
                fold_force = -2.0 * signed_dist / (fold_width_px + 1) * fold_depth
            else:
                fold_force = fold_depth * np.sign(signed_dist)

            fx_total += cos_a * fold_force * fold_zone * 0.3
            fy_total += sin_a * fold_force * fold_zone * 0.3

        state["vx"] = state["vx"] * 0.88 + fx_total * 0.05
        state["vy"] = state["vy"] * 0.88 + fy_total * 0.05
        state["dx"] += state["vx"]
        state["dy"] += state["vy"]

    max_disp = max(h, w) * 0.4
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    result = _remap_frame(frame, state["dx"], state["dy"], boundary)

    if total_frames > 1 and frame_index >= total_frames - 1:
        _physics_state.pop(key, None)

    return np.clip(result, 0, 255).astype(np.uint8)


# ══════════════════════════════════════════════════════════════════════
# IMPOSSIBLE PHYSICS II — Deeper into the impossible
# ══════════════════════════════════════════════════════════════════════

def pixel_wormhole(
    frame: np.ndarray,
    portal_radius: float = 0.1,
    tunnel_strength: float = 8.0,
    spin: float = 2.0,
    distortion_ring: float = 1.5,
    wander: float = 0.3,
    center_x: float = 0.5,
    center_y: float = 0.5,
    damping: float = 0.9,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    boundary: str = "black",
) -> np.ndarray:
    """Wormhole — paired portals teleport pixels between two points.

    Two connected portals warp space so pixels near one get displaced toward
    the other. The throat of each portal spins and distorts surrounding pixels.
    Space between the portals stretches like a rubber sheet.

    Args:
        portal_radius: Size of each portal as fraction of frame (0.03-0.3).
        tunnel_strength: How strongly pixels get pulled through (1-20).
        spin: Rotational distortion at each mouth (0-10).
        distortion_ring: Width of warped ring around portals (0.5-3).
        wander: How much portals drift over time (0-1).
        center_x: Portal pair center X position (0.0-1.0). 0.5 = centered.
        center_y: Portal pair center Y position (0.0-1.0). 0.5 = centered.
        damping: Velocity decay (0.8-0.99).
    """
    h, w = frame.shape[:2]
    key = f"wormhole_{seed}"
    state = _get_state(key, h, w)

    rng = np.random.default_rng(seed)
    t = frame_index / 30.0

    center_x = max(0.0, min(1.0, float(center_x)))
    center_y = max(0.0, min(1.0, float(center_y)))

    # Portal offset from center
    spread_x = rng.random() * 0.2 + 0.1  # 10-30% spread
    spread_y = rng.random() * 0.2 + 0.1
    p1x = (center_x - spread_x) * w
    p1y = (center_y - spread_y) * h
    p2x = (center_x + spread_x) * w
    p2y = (center_y + spread_y) * h

    if wander > 0:
        p1x += np.sin(t * 0.4) * w * wander * 0.15
        p1y += np.cos(t * 0.5) * h * wander * 0.15
        p2x += np.sin(t * 0.3 + 2.0) * w * wander * 0.15
        p2y += np.cos(t * 0.45 + 1.5) * h * wander * 0.15

    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
    radius_px = portal_radius * max(h, w)

    fx_total = np.zeros((h, w), dtype=np.float32)
    fy_total = np.zeros((h, w), dtype=np.float32)

    portals = [(p1x, p1y, p2x, p2y), (p2x, p2y, p1x, p1y)]
    for src_x, src_y, dst_x, dst_y in portals:
        dx = x_grid - src_x
        dy = y_grid - src_y
        dist = np.sqrt(dx * dx + dy * dy) + 0.1

        # Tunnel pull: near this portal -> push toward the other
        proximity = np.exp(-(dist * dist) / (radius_px * radius_px * distortion_ring * distortion_ring))
        tunnel_dx = (dst_x - x_grid) * proximity * tunnel_strength * 0.01
        tunnel_dy = (dst_y - y_grid) * proximity * tunnel_strength * 0.01

        # Spin at the mouth
        spin_factor = spin * np.exp(-dist / (radius_px * 2))
        spin_fx = -dy / dist * spin_factor * 0.3
        spin_fy = dx / dist * spin_factor * 0.3

        fx_total += tunnel_dx + spin_fx
        fy_total += tunnel_dy + spin_fy

    state["vx"] = state["vx"] * damping + fx_total
    state["vy"] = state["vy"] * damping + fy_total
    state["dx"] += state["vx"]
    state["dy"] += state["vy"]

    max_disp = max(h, w) * 0.5
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    result = _remap_frame(frame, state["dx"], state["dy"], boundary)

    # Portal glow — bright rings at each mouth
    result = result.astype(np.float32)
    for px, py in [(p1x, p1y), (p2x, p2y)]:
        pdx = x_grid - px
        pdy = y_grid - py
        pdist = np.sqrt(pdx * pdx + pdy * pdy) + 0.1
        ring = np.exp(-((pdist - radius_px) ** 2) / (radius_px * radius_px * 0.2))
        glow = ring * 60
        result[:, :, 0] += glow * 0.3
        result[:, :, 1] += glow * 0.6
        result[:, :, 2] += glow * 1.0

    if total_frames > 1 and frame_index >= total_frames - 1:
        _physics_state.pop(key, None)

    return np.clip(result, 0, 255).astype(np.uint8)


def pixel_quantum(
    frame: np.ndarray,
    tunnel_prob: float = 0.3,
    barrier_count: int = 4,
    barrier_width: float = 0.05,
    uncertainty: float = 5.0,
    superposition: float = 0.4,
    decoherence: float = 0.02,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    boundary: str = "wrap",
) -> np.ndarray:
    """Quantum — pixels tunnel through barriers and exist in superposition.

    Barriers slice the frame into zones. Pixels near a barrier have a
    probability of tunneling through (teleporting past). Between barriers,
    pixels spread into probability clouds. Multiple superposition copies
    fade in and out, collapsing via decoherence.

    Args:
        tunnel_prob: Chance of tunneling through a barrier (0-1).
        barrier_count: Number of barriers across the frame (1-10).
        barrier_width: Width of each barrier as fraction of frame (0.01-0.15).
        uncertainty: Heisenberg spread — position smear amount (1-15).
        superposition: Strength of ghost copies (0-1). 0=off.
        decoherence: Rate at which superposition collapses (0-0.1).
    """
    h, w = frame.shape[:2]
    key = f"quantum_{seed}"
    state = _get_state(key, h, w)

    rng = np.random.default_rng(seed)
    iterations = _PREVIEW_WARMUP_FRAMES if _is_preview(frame_index, total_frames) else 1

    for step in range(iterations):
        t = (frame_index + step) / 30.0

        y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)

        # Barrier positions (vertical slices with subtle drift)
        barrier_positions = []
        for i in range(barrier_count):
            bx = (i + 1) * w / (barrier_count + 1)
            bx += np.sin(t * 0.5 + i * 1.3) * w * 0.03
            barrier_positions.append(bx)

        barrier_width_px = barrier_width * w

        fx_total = np.zeros((h, w), dtype=np.float32)
        fy_total = np.zeros((h, w), dtype=np.float32)

        for bx in barrier_positions:
            dist_to_barrier = x_grid - bx
            in_barrier = np.exp(-(dist_to_barrier ** 2) / (barrier_width_px ** 2))

            # Tunnel: random pixels near barrier get pushed through
            tunnel_rng = np.random.default_rng(seed + frame_index + step + int(bx))
            tunnel_mask = tunnel_rng.random((h, w)).astype(np.float32) < tunnel_prob
            tunnel_push = in_barrier * tunnel_mask * np.sign(dist_to_barrier) * barrier_width_px * 2
            fx_total += tunnel_push * 0.3

        # Heisenberg uncertainty: visible from the start, scales with slider
        sim_frame = frame_index + step
        sim_total = max(total_frames, iterations * 2) if _is_preview(frame_index, total_frames) else total_frames
        ramp = min(1.0, sim_frame / max(sim_total * 0.3, 1))
        uncertainty_t = uncertainty * (0.4 + 0.6 * ramp)
        unc_rng = np.random.default_rng(seed + sim_frame * 7)
        fx_total += (unc_rng.random((h, w)).astype(np.float32) - 0.5) * uncertainty_t * 1.2
        fy_total += (unc_rng.random((h, w)).astype(np.float32) - 0.5) * uncertainty_t * 1.2

        state["vx"] = state["vx"] * 0.85 + fx_total * 0.2
        state["vy"] = state["vy"] * 0.85 + fy_total * 0.2
        state["dx"] += state["vx"]
        state["dy"] += state["vy"]

    max_disp = max(h, w) * 0.4
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    result = _remap_frame(frame, state["dx"], state["dy"], boundary)

    # Superposition: ghost copies at offset positions
    if superposition > 0:
        # Decoherence controls fade rate: low=ghosts persist, high=ghosts vanish fast
        # decoherence=0.0 → ghosts never fade; =0.02 → fade over ~50 frames; =0.1 → ~10 frames
        if decoherence > 0:
            ghost_decay_frames = max(1.0, 1.0 / decoherence)
            ghost_strength = superposition * max(0.0, 1.0 - frame_index / ghost_decay_frames)
        else:
            ghost_strength = superposition
        if ghost_strength > 0.01:
            result = result.astype(np.float32)
            # Ghost offset proportional to uncertainty (more uncertain = wider spread)
            ghost_spread = max(uncertainty_t * 6, 12.0)
            num_ghosts = 3
            ghost_weight = ghost_strength * 0.7
            for copy_i in range(num_ghosts):
                offset_x = np.sin(t * (1.5 + copy_i) + copy_i * 2.5) * ghost_spread
                offset_y = np.cos(t * (1.2 + copy_i) + copy_i * 1.8) * ghost_spread
                ghost = _remap_frame(frame, state["dx"] + offset_x, state["dy"] + offset_y, boundary)
                result += ghost.astype(np.float32) * ghost_weight
            result /= (1.0 + ghost_weight * num_ghosts)

    # Barrier visualization: faint green vertical lines
    result = result.astype(np.float32)
    for bx in barrier_positions:
        dist = np.abs(x_grid - bx)
        barrier_vis = np.exp(-(dist ** 2) / (barrier_width_px ** 2 * 0.3))
        result[:, :, 1] += barrier_vis * 30
        result[:, :, 2] += barrier_vis * 15

    if total_frames > 1 and frame_index >= total_frames - 1:
        _physics_state.pop(key, None)

    return np.clip(result, 0, 255).astype(np.uint8)


def pixel_darkenergy(
    frame: np.ndarray,
    expansion_rate: float = 3.0,
    acceleration: float = 0.05,
    void_color: tuple = (5, 0, 15),
    structure: float = 0.5,
    hubble_zones: int = 6,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    boundary: str = "black",
) -> np.ndarray:
    """Dark energy — accelerating expansion tears pixels apart.

    Every point expands away from every other point (Hubble expansion).
    The expansion accelerates over time. Gaps between pixel clusters
    fill with void. Structure creates cosmic web — filaments that resist
    expansion while voids grow.

    Args:
        expansion_rate: Base expansion speed (0.5-10).
        acceleration: How much expansion speeds up per frame (0-0.2).
        void_color: RGB color of void between pixels (dark purple default).
        structure: Cosmic web resistance (0-1). Higher = more filaments resist.
        hubble_zones: Number of expansion centers (2-12).
    """
    h, w = frame.shape[:2]
    key = f"darkenergy_{seed}"
    state = _get_state(key, h, w)

    # Parse hex color strings from UI color picker
    if isinstance(void_color, str):
        c = void_color.strip().lstrip('#')
        if len(c) == 6:
            try:
                void_color = (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
            except ValueError:
                void_color = (5, 0, 15)
        else:
            void_color = (5, 0, 15)

    if "expansion_factor" not in state:
        state["expansion_factor"] = 1.0

    rng = np.random.default_rng(seed)
    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
    zone_positions = rng.random((hubble_zones, 2))

    # Cosmic web: edges = dense filaments that resist expansion
    resistance = None
    if structure > 0:
        gray = np.mean(frame.astype(np.float32), axis=2)
        edges = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3) ** 2 + \
                cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3) ** 2
        edges = np.sqrt(edges)
        edges = edges / (edges.max() + 0.01)
        resistance = 1.0 - edges * structure

    iterations = _PREVIEW_WARMUP_FRAMES if _is_preview(frame_index, total_frames) else 1

    for step in range(iterations):
        state["expansion_factor"] += acceleration
        current_rate = expansion_rate * state["expansion_factor"]

        fx_total = np.zeros((h, w), dtype=np.float32)
        fy_total = np.zeros((h, w), dtype=np.float32)

        # Hubble expansion from multiple centers
        for i in range(hubble_zones):
            zx = zone_positions[i, 0] * w
            zy = zone_positions[i, 1] * h
            dx = x_grid - zx
            dy = y_grid - zy
            dist = np.sqrt(dx * dx + dy * dy) + 1.0

            # Hubble's law: velocity proportional to distance
            expand = current_rate * dist * 0.0001
            fx_total += dx / dist * expand
            fy_total += dy / dist * expand

        if resistance is not None:
            fx_total *= resistance
            fy_total *= resistance

        state["vx"] = state["vx"] * 0.95 + fx_total
        state["vy"] = state["vy"] * 0.95 + fy_total
        state["dx"] += state["vx"]
    state["dy"] += state["vy"]

    max_disp = max(h, w) * 0.6
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    result = _remap_frame(frame, state["dx"], state["dy"], boundary)

    # Void fill: displaced pixels reveal dark void
    disp_magnitude = np.sqrt(state["dx"] ** 2 + state["dy"] ** 2)
    void_threshold = max(h, w) * 0.05
    void_mask = np.clip((disp_magnitude - void_threshold) / (void_threshold * 2), 0, 1)

    if void_mask.max() > 0.01:
        result = result.astype(np.float32)
        for c in range(3):
            result[:, :, c] = result[:, :, c] * (1 - void_mask) + void_color[c] * void_mask

    if total_frames > 1 and frame_index >= total_frames - 1:
        _physics_state.pop(key, None)

    return np.clip(result, 0, 255).astype(np.uint8)


def pixel_superfluid(
    frame: np.ndarray,
    flow_speed: float = 6.0,
    quantized_vortices: int = 5,
    vortex_strength: float = 4.0,
    climb_force: float = 2.0,
    viscosity: float = 0.0,
    thermal_noise: float = 0.5,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    boundary: str = "wrap",
) -> np.ndarray:
    """Superfluid — zero-friction flow with quantized vortices and edge climbing.

    Pixels flow with zero viscosity (no energy loss). Vortices only exist at
    quantized strengths (integer multiples). Flow climbs up frame edges
    (superfluidity). Below critical velocity, flow is smooth; above it,
    quantized vortices nucleate.

    Args:
        flow_speed: Base flow velocity (1-15).
        quantized_vortices: Number of quantized vortex cores (1-12).
        vortex_strength: Strength per vortex (integer units) (1-10).
        climb_force: How strongly flow climbs edges (0-5).
        viscosity: 0 for true superfluid, >0 adds drag (0-0.5).
        thermal_noise: Random perturbation (phonon excitations) (0-3).
    """
    h, w = frame.shape[:2]
    key = f"superfluid_{seed}"
    state = _get_state(key, h, w)

    rng = np.random.default_rng(seed)
    t = frame_index / 30.0

    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)

    # Base laminar flow
    base_angle = rng.random() * np.pi * 2
    base_fx = np.cos(base_angle) * flow_speed * 0.02
    base_fy = np.sin(base_angle) * flow_speed * 0.02

    fx_total = np.full((h, w), base_fx, dtype=np.float32)
    fy_total = np.full((h, w), base_fy, dtype=np.float32)

    # Quantized vortices with integer circulation
    vortex_positions = rng.random((quantized_vortices, 2))
    vortex_charges = rng.choice([-1, 1], size=quantized_vortices)

    for i in range(quantized_vortices):
        vx = vortex_positions[i, 0] * w + np.sin(t * 0.3 + i * 1.7) * w * 0.05
        vy = vortex_positions[i, 1] * h + np.cos(t * 0.4 + i * 2.3) * h * 0.05

        ddx = x_grid - vx
        ddy = y_grid - vy
        dist = np.sqrt(ddx * ddx + ddy * ddy) + 1.0

        quant = int(round(vortex_strength)) * vortex_charges[i]
        circ = quant / (dist + 5.0) * 50.0

        fx_total += -ddy / dist * circ * 0.02
        fy_total += ddx / dist * circ * 0.02

    # Edge climbing: flow creeps up frame boundaries
    if climb_force > 0:
        near_left = np.exp(-x_grid / (w * 0.05))
        near_right = np.exp(-(w - x_grid) / (w * 0.05))
        near_top = np.exp(-y_grid / (h * 0.05))
        near_bottom = np.exp(-(h - y_grid) / (h * 0.05))

        fx_total += -(near_top + near_bottom) * climb_force * 0.3
        fy_total += -(near_left + near_right) * climb_force * 0.3

    # Thermal noise (phonon excitations)
    if thermal_noise > 0:
        noise_rng = np.random.default_rng(seed + frame_index * 3)
        fx_total += (noise_rng.random((h, w)).astype(np.float32) - 0.5) * thermal_noise * 0.3
        fy_total += (noise_rng.random((h, w)).astype(np.float32) - 0.5) * thermal_noise * 0.3

    # Zero viscosity = no damping (energy conserved)
    effective_damping = 1.0 - viscosity * 0.1
    state["vx"] = state["vx"] * effective_damping + fx_total * 0.03
    state["vy"] = state["vy"] * effective_damping + fy_total * 0.03
    state["dx"] += state["vx"]
    state["dy"] += state["vy"]

    max_disp = max(h, w) * 0.5
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    result = _remap_frame(frame, state["dx"], state["dy"], boundary)

    # Vortex core glow: colored dots at quantized cores
    result = result.astype(np.float32)
    for i in range(quantized_vortices):
        vx_pos = vortex_positions[i, 0] * w + np.sin(t * 0.3 + i * 1.7) * w * 0.05
        vy_pos = vortex_positions[i, 1] * h + np.cos(t * 0.4 + i * 2.3) * h * 0.05
        cdx = x_grid - vx_pos
        cdy = y_grid - vy_pos
        cdist = np.sqrt(cdx * cdx + cdy * cdy) + 0.1
        core_glow = np.exp(-(cdist ** 2) / 100.0) * 40
        if vortex_charges[i] > 0:
            result[:, :, 0] += core_glow * 0.4
            result[:, :, 1] += core_glow * 0.6
            result[:, :, 2] += core_glow
        else:
            result[:, :, 2] += core_glow
            result[:, :, 1] += core_glow * 0.3

    if total_frames > 1 and frame_index >= total_frames - 1:
        _physics_state.pop(key, None)

    return np.clip(result, 0, 255).astype(np.uint8)


# ══════════════════════════════════════════════════════════════════════
# IMPOSSIBLE PHYSICS III — Oracle-inspired ("Do we need holes?")
# ══════════════════════════════════════════════════════════════════════

def pixel_bubbles(
    frame: np.ndarray,
    num_portals: int = 6,
    min_radius: float = 0.03,
    max_radius: float = 0.12,
    pull_strength: float = 6.0,
    spin: float = 1.5,
    void_mode: str = "black",
    wander: float = 0.4,
    damping: float = 0.91,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    boundary: str = "black",
) -> np.ndarray:
    """Bubbles — multiple portals of random size with negative space inside.

    Like wormhole, but with controllable count, random sizes, and black
    void inside each portal. Inspired by "Do we need holes?" and
    "Astro-Black — color the void."

    Args:
        num_portals: Number of bubble portals (1-20).
        min_radius: Smallest portal as fraction of frame (0.01-0.1).
        max_radius: Largest portal as fraction of frame (0.05-0.3).
        pull_strength: Inward pull toward each portal center (1-15).
        spin: Rotational distortion at each mouth (0-8).
        void_mode: What fills the portal interior ("black", "white", "invert").
        wander: How much portals drift (0-1).
        damping: Velocity decay (0.8-0.99).
    """
    h, w = frame.shape[:2]
    key = f"bubbles_{seed}"
    state = _get_state(key, h, w)

    rng = np.random.default_rng(seed)
    t = frame_index / 30.0

    # Generate portal positions and radii (seeded)
    positions = rng.random((num_portals, 2))
    # Guard: ensure min_radius < max_radius for uniform sampling
    safe_min = min(min_radius, max_radius)
    safe_max = max(min_radius, max_radius)
    if safe_max <= safe_min:
        safe_max = safe_min + 0.01
    radii_frac = rng.uniform(safe_min, safe_max, num_portals)

    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
    fx_total = np.zeros((h, w), dtype=np.float32)
    fy_total = np.zeros((h, w), dtype=np.float32)

    portal_data = []
    for i in range(num_portals):
        px = positions[i, 0] * w
        py = positions[i, 1] * h
        radius_px = radii_frac[i] * max(h, w)

        if wander > 0:
            px += np.sin(t * (0.3 + i * 0.1) + i * 2.1) * w * wander * 0.1
            py += np.cos(t * (0.4 + i * 0.15) + i * 1.7) * h * wander * 0.1

        portal_data.append((px, py, radius_px))

        dx = x_grid - px
        dy = y_grid - py
        dist = np.sqrt(dx * dx + dy * dy) + 0.1

        # Inward pull with strong falloff
        proximity = np.exp(-(dist * dist) / (radius_px * radius_px * 4))
        fx_total += -dx / dist * pull_strength * proximity * 0.3
        fy_total += -dy / dist * pull_strength * proximity * 0.3

        # Spin at mouth
        spin_factor = spin * np.exp(-dist / (radius_px * 1.5))
        fx_total += -dy / dist * spin_factor * 0.2
        fy_total += dx / dist * spin_factor * 0.2

    state["vx"] = state["vx"] * damping + fx_total * 0.05
    state["vy"] = state["vy"] * damping + fy_total * 0.05
    state["dx"] += state["vx"]
    state["dy"] += state["vy"]

    max_disp = max(h, w) * 0.5
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    result = _remap_frame(frame, state["dx"], state["dy"], boundary)
    result = result.astype(np.float32)

    # Void inside each portal + glow ring around edge
    for px, py, radius_px in portal_data:
        dx = x_grid - px
        dy = y_grid - py
        dist = np.sqrt(dx * dx + dy * dy) + 0.1

        # Void mask: inside the portal
        void_mask = np.clip(1.0 - dist / radius_px, 0, 1)
        # Smooth edge with sigmoid
        void_mask = 1.0 / (1.0 + np.exp((dist - radius_px * 0.7) / (radius_px * 0.1 + 0.1)))

        if void_mode == "black":
            for c in range(3):
                result[:, :, c] *= (1.0 - void_mask)
        elif void_mode == "white":
            for c in range(3):
                result[:, :, c] = result[:, :, c] * (1.0 - void_mask) + 255.0 * void_mask
        elif void_mode == "invert":
            for c in range(3):
                result[:, :, c] = result[:, :, c] * (1.0 - void_mask) + (255.0 - result[:, :, c]) * void_mask

        # Glow ring at edge
        ring = np.exp(-((dist - radius_px) ** 2) / (radius_px * radius_px * 0.08))
        result[:, :, 0] += ring * 25
        result[:, :, 1] += ring * 40
        result[:, :, 2] += ring * 50

    if total_frames > 1 and frame_index >= total_frames - 1:
        _physics_state.pop(key, None)

    return np.clip(result, 0, 255).astype(np.uint8)


def pixel_inkdrop(
    frame: np.ndarray,
    num_drops: int = 4,
    diffusion_rate: float = 3.0,
    surface_tension: float = 0.6,
    marangoni: float = 2.0,
    tendrils: int = 8,
    drop_interval: float = 0.3,
    color_shift: float = 0.5,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    boundary: str = "wrap",
) -> np.ndarray:
    """Ink drop — paint dropping into water with diffusion and surface tension.

    Simulates ink/paint drops falling into water. Each drop creates an
    expanding ring that develops tendrils (Marangoni convection from soap).
    Drops interact — their diffusion fronts push against each other.
    Inspired by "Water music — what happens when the medium dissolves?"

    Args:
        num_drops: Number of ink drops (1-12).
        diffusion_rate: How fast ink spreads (0.5-8).
        surface_tension: Resistance at diffusion front (0-1). Higher = tighter circles.
        marangoni: Tendril/finger instability strength (0-5). The soap effect.
        tendrils: Number of fingers/tendrils per drop (3-16).
        drop_interval: Time between drops as fraction of duration (0-1). 0=all at once.
        color_shift: How much drops shift hue as they spread (0-2).
    """
    h, w = frame.shape[:2]
    key = f"inkdrop_{seed}"
    state = _get_state(key, h, w)

    rng = np.random.default_rng(seed)
    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)

    drop_positions = rng.random((num_drops, 2))
    drop_phases = rng.random(num_drops) * np.pi * 2

    iterations = _PREVIEW_WARMUP_FRAMES if _is_preview(frame_index, total_frames) else 1
    sim_total = max(total_frames, iterations * 2)

    for step in range(iterations):
        sim_frame = frame_index + step
        t = sim_frame / 30.0
        progress = sim_frame / max(sim_total - 1, 1)

        fx_total = np.zeros((h, w), dtype=np.float32)
        fy_total = np.zeros((h, w), dtype=np.float32)

        for i in range(num_drops):
            drop_start = i * drop_interval / max(num_drops - 1, 1) if num_drops > 1 else 0
            if progress < drop_start:
                continue

            drop_age = (progress - drop_start) / max(1.0 - drop_start, 0.01)
            drop_age = min(drop_age, 1.0)

            dx_pos = drop_positions[i, 0] * w
            dy_pos = drop_positions[i, 1] * h

            dx = x_grid - dx_pos
            dy = y_grid - dy_pos
            dist = np.sqrt(dx * dx + dy * dy) + 0.1

            front_radius = drop_age * max(h, w) * 0.2 * diffusion_rate
            front_width = front_radius * 0.15 + 5.0
            dist_from_front = dist - front_radius
            at_front = np.exp(-(dist_from_front ** 2) / (front_width ** 2))

            expand_force = at_front * diffusion_rate * 0.5
            fx_total += dx / dist * expand_force
            fy_total += dy / dist * expand_force

            if surface_tension > 0:
                tension_force = -surface_tension * at_front * np.sign(dist_from_front) * 0.3
                fx_total += dx / dist * tension_force
                fy_total += dy / dist * tension_force

            if marangoni > 0 and tendrils > 0:
                angle = np.arctan2(dy, dx)
                tendril_pattern = np.sin(angle * tendrils + drop_phases[i] + t * 0.5)
                tendril_force = tendril_pattern * at_front * marangoni * 0.4

                fx_total += dx / dist * tendril_force * 0.3
                fy_total += dy / dist * tendril_force * 0.3

                swirl = tendril_pattern * at_front * marangoni * 0.2
                fx_total += -dy / dist * swirl * 0.15
                fy_total += dx / dist * swirl * 0.15

        state["vx"] = state["vx"] * 0.88 + fx_total * 0.04
        state["vy"] = state["vy"] * 0.88 + fy_total * 0.04
        state["dx"] += state["vx"]
        state["dy"] += state["vy"]

    max_disp = max(h, w) * 0.4
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    result = _remap_frame(frame, state["dx"], state["dy"], boundary)

    if color_shift > 0:
        disp_mag = np.sqrt(state["dx"] ** 2 + state["dy"] ** 2)
        shift_mask = np.clip(disp_mag / (max(h, w) * 0.1), 0, 1) * color_shift

        if shift_mask.max() > 0.01:
            result = result.astype(np.float32)
            r, g, b = result[:, :, 0], result[:, :, 1], result[:, :, 2]
            cos_a = np.cos(shift_mask * np.pi * 0.5)
            sin_a = np.sin(shift_mask * np.pi * 0.5)
            new_r = r * cos_a + g * sin_a
            new_g = g * cos_a - r * sin_a * 0.5 + b * sin_a * 0.5
            new_b = b * cos_a - g * sin_a
            result[:, :, 0] = new_r
            result[:, :, 1] = new_g
            result[:, :, 2] = new_b

    if total_frames > 1 and frame_index >= total_frames - 1:
        _physics_state.pop(key, None)

    return np.clip(result, 0, 255).astype(np.uint8)


def pixel_haunt(
    frame: np.ndarray,
    force_type: str = "turbulence",
    force_strength: float = 4.0,
    ghost_persistence: float = 0.95,
    ghost_opacity: float = 0.4,
    crackle: float = 0.3,
    damping: float = 0.9,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    boundary: str = "wrap",
) -> np.ndarray:
    """Haunt — ghostly afterimages linger where pixels used to be.

    As pixels get displaced, their old positions leave behind ghosts —
    semi-transparent afterimages that slowly fade. The ghost is the
    presence of an absence. Crackle adds medium-memory noise at ghost
    boundaries. Inspired by Hauntology: "the medium's memory showing through."

    Args:
        force_type: What drives the displacement ("turbulence", "radial", "drift").
        force_strength: How hard pixels get pushed (1-15).
        ghost_persistence: How slowly ghosts fade (0.8-0.99). Higher = longer haunting.
        ghost_opacity: Peak ghost brightness (0.1-1.0).
        crackle: Medium-memory noise at ghost edges (0-1).
        damping: Velocity decay (0.8-0.99).
    """
    h, w = frame.shape[:2]
    key = f"haunt_{seed}"
    state = _get_state(key, h, w)

    if "ghost" not in state:
        state["ghost"] = np.zeros((h, w, 3), dtype=np.float32)

    rng = np.random.default_rng(seed)
    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)

    iterations = _PREVIEW_WARMUP_FRAMES if _is_preview(frame_index, total_frames) else 1

    for step in range(iterations):
        t = (frame_index + step) / 30.0

        if force_type == "turbulence":
            _rng = np.random.default_rng(seed)
            phase_x = _rng.random() * 100
            phase_y = _rng.random() * 100
            fx = force_strength * np.sin(x_grid / 35.0 + t * 1.5 + phase_x) * np.cos(y_grid / 30.0 + t * 1.2 + phase_y)
            fy = force_strength * np.cos(x_grid / 30.0 + t * 1.8 + phase_x) * np.sin(y_grid / 35.0 + t * 2.0 + phase_y)
        elif force_type == "radial":
            cx, cy = w / 2, h / 2
            ddx = x_grid - cx
            ddy = y_grid - cy
            dist = np.sqrt(ddx * ddx + ddy * ddy) + 1.0
            pulse = np.sin(t * 2) * force_strength
            fx = ddx / dist * pulse * 0.2
            fy = ddy / dist * pulse * 0.2
        else:  # drift
            angle = t * 0.3
            fx = np.full((h, w), np.cos(angle) * force_strength * 0.3, dtype=np.float32)
            fy = np.full((h, w), np.sin(angle) * force_strength * 0.3, dtype=np.float32)

        state["vx"] = state["vx"] * damping + fx * 0.03
        state["vy"] = state["vy"] * damping + fy * 0.03
        state["dx"] += state["vx"]
        state["dy"] += state["vy"]

        state["ghost"] = state["ghost"] * ghost_persistence + frame.astype(np.float32) * (1.0 - ghost_persistence) * ghost_opacity

    max_disp = max(h, w) * 0.35
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    # Remap the current frame through displacement
    result = _remap_frame(frame, state["dx"], state["dy"], boundary)
    result = result.astype(np.float32)

    # Composite: displaced pixels on top of ghost afterimage
    # Where displacement is large, the ghost shows through more
    disp_mag = np.sqrt(state["dx"] ** 2 + state["dy"] ** 2)
    ghost_reveal = np.clip(disp_mag / (max(h, w) * 0.1), 0, 1)

    for c in range(3):
        result[:, :, c] = result[:, :, c] * (1.0 - ghost_reveal * ghost_opacity) + \
                          state["ghost"][:, :, c] * ghost_reveal

    # Crackle: medium-memory noise at ghost boundaries
    if crackle > 0:
        crackle_rng = np.random.default_rng(seed + frame_index * 5)
        # Noise concentrated where ghosts are visible
        grad = cv2.Sobel(ghost_reveal, cv2.CV_32F, 1, 0, ksize=3) ** 2 + \
               cv2.Sobel(ghost_reveal, cv2.CV_32F, 0, 1, ksize=3) ** 2
        grad = np.sqrt(grad)
        grad = grad / (grad.max() + 0.01)
        noise = (crackle_rng.random((h, w)).astype(np.float32) - 0.5) * crackle * 80 * grad
        for c in range(3):
            result[:, :, c] += noise

    if total_frames > 1 and frame_index >= total_frames - 1:
        _physics_state.pop(key, None)

    return np.clip(result, 0, 255).astype(np.uint8)


# ══════════════════════════════════════════════════════════════════════
# PRINT DEGRADATION — Fax, Xerox, Risograph
# ══════════════════════════════════════════════════════════════════════

def pixel_xerox(
    frame: np.ndarray,
    generations: int = 8,
    contrast_gain: float = 1.15,
    noise_amount: float = 0.06,
    halftone_size: int = 4,
    edge_fuzz: float = 1.5,
    toner_skip: float = 0.05,
    style: str = "copy",
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    boundary: str = "clamp",
) -> np.ndarray:
    """Xerox — generational copy loss like a billion photocopies.

    Each frame simulates more copy generations: contrast crushes toward
    black and white, noise accumulates, edges get fuzzy, toner skips
    leave white gaps. Progressive degradation over the clip duration.

    Styles:
        copy: Standard copier degradation (default).
        faded: Low-toner office copier — lighter, more grain, more toner skip.
        harsh: High-contrast mode — crushes to near B&W faster.
        zine: DIY zine aesthetic — heavy halftone, max degradation.

    Args:
        generations: How many copy generations to simulate (1-30).
        contrast_gain: Per-generation contrast boost (1.0-1.5). Crushes midtones.
        noise_amount: Per-generation noise (0-0.3).
        halftone_size: Dot screen size for halftone pattern (2-8).
        edge_fuzz: Edge blur per generation (0-4).
        toner_skip: Probability of white toner gaps per generation (0-0.2).
        style: Copier character — 'copy', 'faded', 'harsh', 'zine'.
    """
    h, w = frame.shape[:2]
    rng = np.random.default_rng(seed + frame_index)
    progress = frame_index / max(total_frames - 1, 1)

    # Style presets override base params
    if style == "faded":
        contrast_gain = min(contrast_gain, 1.08)
        noise_amount = max(noise_amount, 0.1)
        toner_skip = max(toner_skip, 0.12)
        edge_fuzz = max(edge_fuzz, 2.5)
    elif style == "harsh":
        contrast_gain = max(contrast_gain, 1.3)
        noise_amount = min(noise_amount, 0.03)
        halftone_size = max(2, halftone_size)
    elif style == "zine":
        contrast_gain = max(contrast_gain, 1.25)
        noise_amount = max(noise_amount, 0.08)
        halftone_size = max(6, halftone_size)
        toner_skip = max(toner_skip, 0.08)
        generations = max(generations, 12)

    # Number of generations scales with progress
    current_gens = max(1, int(generations * progress + 1))

    result = frame.astype(np.float32)

    for gen in range(current_gens):
        gen_rng = np.random.default_rng(seed + gen * 7)

        # Contrast crush: push toward black/white
        mean = np.mean(result)
        result = (result - mean) * contrast_gain + mean

        # Noise accumulation (copy machine sensor noise)
        noise = gen_rng.normal(0, noise_amount * 255, result.shape).astype(np.float32)
        result += noise

        # Edge fuzz (optical blur from glass contact)
        if edge_fuzz > 0 and gen % 2 == 0:
            ksize = max(3, int(edge_fuzz) * 2 + 1)
            result = cv2.GaussianBlur(result, (ksize, ksize), edge_fuzz * 0.5)

        # Toner skip: random white rectangles
        if toner_skip > 0:
            num_skips = int(toner_skip * w * h / 2000)
            for _ in range(num_skips):
                sx = gen_rng.integers(0, w)
                sy = gen_rng.integers(0, h)
                sw = gen_rng.integers(2, max(3, w // 30))
                sh = gen_rng.integers(1, 3)
                result[sy:min(sy + sh, h), sx:min(sx + sw, w)] = 255.0

    # Halftone pattern overlay (copier dot screen)
    if halftone_size >= 2:
        hs = halftone_size
        gray = np.mean(result, axis=2)
        dot_y = np.arange(h) % hs
        dot_x = np.arange(w) % hs
        dot_pattern = np.sqrt((dot_y[:, None] - hs / 2) ** 2 + (dot_x[None, :] - hs / 2) ** 2)
        dot_threshold = (dot_pattern / (hs * 0.7)) * 255
        halftone_influence = progress * 0.3
        for c in range(3):
            channel = result[:, :, c]
            halftone = np.where(gray > dot_threshold, channel * 1.1, channel * 0.85)
            result[:, :, c] = channel * (1.0 - halftone_influence) + halftone * halftone_influence

    return np.clip(result, 0, 255).astype(np.uint8)


def pixel_fax(
    frame: np.ndarray,
    scan_noise: float = 0.3,
    toner_bleed: float = 2.0,
    paper_texture: float = 0.4,
    compression_bands: int = 8,
    thermal_fade: float = 0.2,
    dither: bool = True,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    boundary: str = "clamp",
) -> np.ndarray:
    """Fax — thermal printing with all its characteristic artifacts.

    Converts to near-monochrome with horizontal scan noise, toner bleed,
    thermal fade bands, paper texture, and optional Floyd-Steinberg dither.

    Args:
        scan_noise: Horizontal scan line noise (0-1).
        toner_bleed: Horizontal ink spread (0-5). Higher = more smear.
        paper_texture: Off-white paper grain (0-1).
        compression_bands: Horizontal banding from thermal head (0-20).
        thermal_fade: Vertical fade streaks from uneven heating (0-1).
        dither: Apply Floyd-Steinberg dither for halftone effect.
    """
    h, w = frame.shape[:2]
    rng = np.random.default_rng(seed + frame_index)

    # Convert to grayscale (fax is monochrome)
    if frame.ndim == 3:
        gray = np.mean(frame.astype(np.float32), axis=2)
    else:
        gray = frame.astype(np.float32)

    # Thermal fade: vertical columns that are lighter (uneven print head)
    if thermal_fade > 0:
        fade_cols = rng.integers(3, max(4, w // 20))
        fade_pattern = np.ones(w, dtype=np.float32)
        for _ in range(fade_cols):
            col = rng.integers(0, w)
            fade_w = rng.integers(5, max(6, w // 8))
            x = np.arange(w, dtype=np.float32)
            fade_pattern *= 1.0 - thermal_fade * np.exp(-((x - col) ** 2) / (fade_w ** 2))
        gray *= fade_pattern[None, :]

    # Horizontal scan noise (jitter)
    if scan_noise > 0:
        for row in range(h):
            if rng.random() < scan_noise * 0.3:
                shift = rng.integers(-3, 4)
                gray[row] = np.roll(gray[row], shift)
                gray[row] += rng.normal(0, scan_noise * 30, w).astype(np.float32)

    # Compression bands (thermal head segments)
    if compression_bands > 0:
        band_h = max(1, h // compression_bands)
        for band in range(compression_bands):
            y0 = band * band_h
            y1 = min(y0 + band_h, h)
            band_offset = rng.normal(0, 8)
            gray[y0:y1] += band_offset

    # Toner bleed: horizontal motion blur
    if toner_bleed > 0:
        ksize = max(3, int(toner_bleed * 2) | 1)
        kernel = np.zeros((1, ksize), dtype=np.float32)
        kernel[0] = 1.0 / ksize
        gray = cv2.filter2D(gray, -1, kernel)

    # Dither (Floyd-Steinberg) — use downsampled for performance
    if dither:
        # Downsample for speed, then upsample
        scale = max(1, min(h, w) // 200)
        if scale > 1:
            sh, sw = h // scale, w // scale
            small = cv2.resize(gray, (sw, sh), interpolation=cv2.INTER_AREA)
        else:
            small = gray.copy()
            sh, sw = h, w

        threshold = 128.0
        for y in range(sh - 1):
            for x in range(1, sw - 1):
                old = small[y, x]
                new = 255.0 if old > threshold else 0.0
                small[y, x] = new
                err = old - new
                small[y, x + 1] += err * 7 / 16
                small[y + 1, x - 1] += err * 3 / 16
                small[y + 1, x] += err * 5 / 16
                small[y + 1, x + 1] += err * 1 / 16

        if scale > 1:
            gray = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
        else:
            gray = small

    # Paper texture
    if paper_texture > 0:
        paper = rng.normal(245, paper_texture * 15, (h, w)).astype(np.float32)
        paper_mask = np.clip(gray / 255.0, 0, 1)
        gray = gray * (1.0 - paper_mask * 0.3) + paper * paper_mask * 0.3

    # Convert back to 3-channel (warm fax tone)
    result = np.zeros((h, w, 3), dtype=np.float32)
    gray = np.clip(gray, 0, 255)
    result[:, :, 0] = gray * 0.95
    result[:, :, 1] = gray * 0.92
    result[:, :, 2] = gray * 0.88

    return np.clip(result, 0, 255).astype(np.uint8)


_RISOGRAPH_PALETTES = {
    "classic": ((0, 90, 180), (220, 50, 50)),       # Blue + Red
    "zine": ((0, 0, 0), (0, 160, 80)),              # Black + Green
    "punk": ((230, 50, 130), (255, 220, 0)),         # Hot pink + Yellow
    "ocean": ((0, 60, 120), (0, 180, 180)),          # Navy + Teal
    "sunset": ((200, 60, 20), (240, 160, 0)),        # Rust + Gold
    "custom": None,  # Use color_a/color_b directly
}


def pixel_risograph(
    frame: np.ndarray,
    ink_bleed: float = 2.5,
    registration_offset: int = 3,
    paper_grain: float = 0.3,
    ink_coverage: float = 0.85,
    num_colors: int = 2,
    palette: str = "classic",
    color_a: tuple = (0, 90, 180),
    color_b: tuple = (220, 50, 50),
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    boundary: str = "clamp",
) -> np.ndarray:
    """Risograph — drum printer ink bleed with misregistration.

    Simulates risograph/screen printing: limited color palette,
    ink bleeding into paper fibers, layer misregistration (each color
    layer slightly offset), paper grain shows through in light areas.

    Args:
        ink_bleed: How much ink spreads into paper (0-6).
        registration_offset: Max pixel offset between color layers (0-10).
        paper_grain: Paper texture visibility (0-1).
        ink_coverage: How much ink the drum lays down (0.5-1.0). Lower = more white.
        num_colors: Color separation layers (1-3).
        palette: Color preset — 'classic', 'zine', 'punk', 'ocean', 'sunset', 'custom'.
        color_a: First ink color RGB (used when palette='custom').
        color_b: Second ink color RGB (used when palette='custom').
    """
    h, w = frame.shape[:2]
    rng = np.random.default_rng(seed)

    # Apply palette preset (overrides color_a/color_b unless custom)
    if palette in _RISOGRAPH_PALETTES and _RISOGRAPH_PALETTES[palette] is not None:
        color_a, color_b = _RISOGRAPH_PALETTES[palette]

    # Handle list/tuple/hex color args
    def _parse_color(col, default):
        if isinstance(col, str):
            c = col.strip().lstrip('#')
            if len(c) == 6:
                try:
                    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
                except ValueError:
                    return default
            return default
        return tuple(int(c) for c in col)
    color_a = _parse_color(color_a, (0, 90, 180))
    color_b = _parse_color(color_b, (220, 50, 50))

    # Convert to grayscale for separation
    gray = np.mean(frame.astype(np.float32), axis=2) / 255.0

    # Paper base (warm white with grain)
    paper = np.ones((h, w, 3), dtype=np.float32) * 240
    if paper_grain > 0:
        grain = rng.normal(0, paper_grain * 20, (h, w)).astype(np.float32)
        for c in range(3):
            paper[:, :, c] += grain

    result = paper.copy()

    # Color separation layers
    colors = [list(color_a)]
    if num_colors >= 2:
        colors.append(list(color_b))
    if num_colors >= 3:
        colors.append([
            255 - (color_a[0] + color_b[0]) // 2,
            255 - (color_a[1] + color_b[1]) // 2,
            255 - (color_a[2] + color_b[2]) // 2,
        ])

    for layer_idx, ink_color in enumerate(colors):
        if layer_idx == 0:
            layer_mask = np.clip(1.0 - gray, 0, 1)
        elif layer_idx == 1:
            layer_mask = np.clip(gray * 2 - 0.3, 0, 1) * np.clip(1.5 - gray * 2, 0, 1)
        else:
            layer_mask = np.clip(gray - 0.5, 0, 1) * 2

        layer_mask *= ink_coverage

        if ink_bleed > 0:
            ksize = max(3, int(ink_bleed * 2) | 1)
            layer_mask = cv2.GaussianBlur(layer_mask, (ksize, ksize), ink_bleed * 0.5)

        if registration_offset > 0 and layer_idx > 0:
            ox = rng.integers(-registration_offset, registration_offset + 1)
            oy = rng.integers(-registration_offset, registration_offset + 1)
            layer_mask = np.roll(np.roll(layer_mask, ox, axis=1), oy, axis=0)

        ink_noise = rng.normal(1.0, 0.08, (h, w)).astype(np.float32)
        layer_mask *= ink_noise

        for c in range(3):
            ink_value = ink_color[c] / 255.0
            result[:, :, c] *= (1.0 - layer_mask * (1.0 - ink_value))

    return np.clip(result, 0, 255).astype(np.uint8)


# ══════════════════════════════════════════════════════════════════════
# MEGA-EFFECTS — Unified wrappers that dispatch to original functions
# ══════════════════════════════════════════════════════════════════════

import inspect as _inspect

_DYNAMICS_MODES = {
    "liquify": pixel_liquify,
    "gravity": pixel_gravity,
    "vortex": pixel_vortex,
    "explode": pixel_explode,
    "elastic": pixel_elastic,
    "melt": pixel_melt,
}

_COSMOS_MODES = {
    "blackhole": pixel_blackhole,
    "antigravity": pixel_antigravity,
    "magnetic": pixel_magnetic,
    "timewarp": pixel_timewarp,
    "dimensionfold": pixel_dimensionfold,
    "wormhole": pixel_wormhole,
    "quantum": pixel_quantum,
    "darkenergy": pixel_darkenergy,
    "superfluid": pixel_superfluid,
}

_ORGANIC_MODES = {
    "bubbles": pixel_bubbles,
    "inkdrop": pixel_inkdrop,
    "haunt": pixel_haunt,
}

_DECAY_MODES = {
    "xerox": pixel_xerox,
    "fax": pixel_fax,
    "risograph": pixel_risograph,
}


def _dispatch(mode_map, mode, frame, **kwargs):
    """Dispatch to a specific effect function, passing only matching kwargs."""
    fn = mode_map.get(mode)
    if fn is None:
        raise ValueError(f"Unknown mode: {mode}. Available: {', '.join(mode_map.keys())}")
    sig = _inspect.signature(fn)
    valid = {k: v for k, v in kwargs.items() if k in sig.parameters}
    return fn(frame, **valid)


def pixel_dynamics(
    frame: np.ndarray,
    mode: str = "liquify",
    **kwargs,
) -> np.ndarray:
    """Unified pixel dynamics — 6 modes of physical motion.

    Modes: liquify, gravity, vortex, explode, elastic, melt.
    Pass any parameter from the underlying effect; unrecognized params are ignored.
    """
    return _dispatch(_DYNAMICS_MODES, mode, frame, **kwargs)


def pixel_cosmos(
    frame: np.ndarray,
    mode: str = "blackhole",
    **kwargs,
) -> np.ndarray:
    """Unified pixel cosmos — 9 modes of impossible physics.

    Modes: blackhole, antigravity, magnetic, timewarp, dimensionfold,
           wormhole, quantum, darkenergy, superfluid.
    """
    return _dispatch(_COSMOS_MODES, mode, frame, **kwargs)


def pixel_organic(
    frame: np.ndarray,
    mode: str = "bubbles",
    **kwargs,
) -> np.ndarray:
    """Unified pixel organic — 3 modes of oracle-inspired effects.

    Modes: bubbles, inkdrop, haunt.
    """
    return _dispatch(_ORGANIC_MODES, mode, frame, **kwargs)


def pixel_decay(
    frame: np.ndarray,
    mode: str = "xerox",
    **kwargs,
) -> np.ndarray:
    """Unified pixel decay — 3 modes of print degradation.

    Modes: xerox, fax, risograph.
    """
    return _dispatch(_DECAY_MODES, mode, frame, **kwargs)

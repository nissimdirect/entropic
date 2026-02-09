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


def _get_state(key, h, w):
    """Get or create physics state for this effect instance."""
    if key not in _physics_state:
        _physics_state[key] = {
            "dx": np.zeros((h, w), dtype=np.float32),  # x displacement
            "dy": np.zeros((h, w), dtype=np.float32),  # y displacement
            "vx": np.zeros((h, w), dtype=np.float32),  # x velocity
            "vy": np.zeros((h, w), dtype=np.float32),  # y velocity
        }
    return _physics_state[key]


def _remap_frame(frame, dx, dy):
    """Remap frame through displacement field."""
    h, w = frame.shape[:2]
    y_coords, x_coords = np.mgrid[0:h, 0:w].astype(np.float32)
    map_x = np.clip(x_coords + dx, 0, w - 1).astype(np.float32)
    map_y = np.clip(y_coords + dy, 0, h - 1).astype(np.float32)
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

    t = frame_index * speed / 30.0
    rng = np.random.default_rng(seed)

    # Generate turbulent force field using layered Perlin-like noise
    # Use sine waves at different frequencies for organic flow
    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
    x_norm = x_grid / flow_scale
    y_norm = y_grid / flow_scale

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

    result = _remap_frame(frame, state["dx"], state["dy"])

    if frame_index >= total_frames - 1:
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
    t = frame_index / 30.0

    # Generate attractor positions (seeded, so consistent across frames)
    base_positions = rng.random((num_attractors, 2))
    attractors_x = base_positions[:, 0] * w
    attractors_y = base_positions[:, 1] * h

    # Wander: attractors drift over time
    if wander > 0:
        for i in range(num_attractors):
            attractors_x[i] += np.sin(t * 0.5 + i * 2.1) * w * wander * 0.1
            attractors_y[i] += np.cos(t * 0.7 + i * 1.7) * h * wander * 0.1

    # Compute gravitational force field
    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
    fx_total = np.zeros((h, w), dtype=np.float32)
    fy_total = np.zeros((h, w), dtype=np.float32)
    radius_px = attractor_radius * max(h, w)

    for i in range(num_attractors):
        dx = attractors_x[i] - x_grid
        dy = attractors_y[i] - y_grid
        dist = np.sqrt(dx * dx + dy * dy) + 1.0
        # Inverse-square with radius falloff
        force = gravity_strength / (dist * dist) * np.exp(-dist / radius_px) * 1000
        fx_total += dx / dist * force
        fy_total += dy / dist * force

    # Apply forces
    state["vx"] = state["vx"] * damping + fx_total * 0.01
    state["vy"] = state["vy"] * damping + fy_total * 0.01

    state["dx"] += state["vx"]
    state["dy"] += state["vy"]

    max_disp = max(h, w) * 0.4
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    result = _remap_frame(frame, state["dx"], state["dy"])

    if frame_index >= total_frames - 1:
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
    t = frame_index / 30.0

    # Vortex positions (stable, seeded)
    positions = rng.random((num_vortices, 2))
    # Spin directions (alternating CW/CCW)
    spins = np.array([(-1) ** i for i in range(num_vortices)], dtype=np.float32)

    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
    fx_total = np.zeros((h, w), dtype=np.float32)
    fy_total = np.zeros((h, w), dtype=np.float32)
    radius_px = radius * max(h, w)

    for i in range(num_vortices):
        cx = positions[i, 0] * w
        cy = positions[i, 1] * h
        dx = x_grid - cx
        dy = y_grid - cy
        dist = np.sqrt(dx * dx + dy * dy) + 1.0
        falloff = np.exp(-dist / radius_px)

        # Tangential force (spin) — perpendicular to radius
        fx_spin = -dy / dist * spin_strength * spins[i] * falloff
        fy_spin = dx / dist * spin_strength * spins[i] * falloff

        # Radial force (pull inward)
        fx_pull = -dx / dist * pull_strength * falloff
        fy_pull = -dy / dist * pull_strength * falloff

        fx_total += fx_spin + fx_pull
        fy_total += fy_spin + fy_pull

    state["vx"] = state["vx"] * damping + fx_total * 0.02
    state["vy"] = state["vy"] * damping + fy_total * 0.02
    state["dx"] += state["vx"]
    state["dy"] += state["vy"]

    max_disp = max(h, w) * 0.4
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    result = _remap_frame(frame, state["dx"], state["dy"])

    if frame_index >= total_frames - 1:
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

    result = _remap_frame(frame, state["dx"], state["dy"])

    if frame_index >= total_frames - 1:
        _physics_state.pop(key, None)

    return np.clip(result, 0, 255).astype(np.uint8)


def pixel_elastic(
    frame: np.ndarray,
    stiffness: float = 0.3,
    mass: float = 1.0,
    force_type: str = "turbulence",
    force_strength: float = 5.0,
    damping: float = 0.9,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Elastic — pixels are on springs that stretch and snap back.

    Each pixel is attached to its original position by a spring.
    External forces push pixels away, but the spring pulls them back.
    Creates wobbly jello-like distortion that bounces.

    Args:
        stiffness: Spring stiffness (0.05-0.8). Higher = snappier return.
        mass: Pixel mass (0.5-3.0). Heavier = slower, more momentum.
        force_type: What pushes pixels ("turbulence", "brightness",
                    "edges", "radial").
        force_strength: How hard the push (1-20).
        damping: Energy loss per frame (0.8-0.99).
    """
    h, w = frame.shape[:2]
    key = f"elastic_{seed}"
    state = _get_state(key, h, w)

    t = frame_index / 30.0
    rng = np.random.default_rng(seed)

    # Compute external force
    if force_type == "turbulence":
        y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
        phase_x = rng.random() * 100
        phase_y = rng.random() * 100
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
        # Edges push outward randomly
        rand_x = (rng.random((h, w)).astype(np.float32) - 0.5) * 2
        rand_y = (rng.random((h, w)).astype(np.float32) - 0.5) * 2
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

    else:
        fx = np.zeros((h, w), dtype=np.float32)
        fy = np.zeros((h, w), dtype=np.float32)

    # Spring physics: F_spring = -stiffness * displacement
    spring_fx = -stiffness * state["dx"]
    spring_fy = -stiffness * state["dy"]

    # F_total = F_external + F_spring
    # acceleration = F_total / mass
    ax = (fx * 0.1 + spring_fx) / mass
    ay = (fy * 0.1 + spring_fy) / mass

    # Update velocity and position (Euler integration)
    state["vx"] = (state["vx"] + ax) * damping
    state["vy"] = (state["vy"] + ay) * damping
    state["dx"] += state["vx"]
    state["dy"] += state["vy"]

    max_disp = max(h, w) * 0.3
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    result = _remap_frame(frame, state["dx"], state["dy"])

    if frame_index >= total_frames - 1:
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

    t = frame_index / 30.0
    rng = np.random.default_rng(seed)
    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)

    # Melt zone — progresses over time
    progress = min(1.0, frame_index / max(total_frames * 0.7, 1))

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

    # Forces: gravity down + heat sideways
    phase = rng.random() * 100
    fy_force = gravity * melt_mask * 0.3
    fx_force = heat * np.sin(x_grid / 20.0 + t * 2 + phase) * melt_mask * 0.2

    state["vx"] = state["vx"] * viscosity + fx_force
    state["vy"] = state["vy"] * viscosity + fy_force
    state["dx"] += state["vx"] * melt_mask
    state["dy"] += state["vy"] * melt_mask

    max_disp = max(h, w) * 0.5
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    result = _remap_frame(frame, state["dx"], state["dy"])

    if frame_index >= total_frames - 1:
        _physics_state.pop(key, None)

    return np.clip(result, 0, 255).astype(np.uint8)

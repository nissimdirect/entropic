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

    result = _remap_frame(frame, state["dx"], state["dy"])

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

    if frame_index >= total_frames - 1:
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
    t = frame_index / 30.0

    # Gravity direction oscillation
    if oscillate > 0:
        grav_dir = np.sin(t * oscillate * np.pi * 2)  # -1 to 1
    else:
        grav_dir = -1.0  # Pure repulsion

    # Zone positions
    positions = rng.random((num_zones, 2))
    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
    radius_px = zone_radius * max(h, w)

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

    state["vx"] = state["vx"] * damping + fx_total * 0.005
    state["vy"] = state["vy"] * damping + fy_total * 0.005
    state["dx"] += state["vx"]
    state["dy"] += state["vy"]

    max_disp = max(h, w) * 0.4
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    result = _remap_frame(frame, state["dx"], state["dy"])

    if frame_index >= total_frames - 1:
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

    rng = np.random.default_rng(seed)
    t = frame_index / 30.0
    angle = t * rotation_speed

    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w / 2, h / 2
    nx = (x_grid - cx) / max(w, 1)
    ny = (y_grid - cy) / max(h, 1)

    # Rotate field over time
    rnx = nx * np.cos(angle) - ny * np.sin(angle)
    rny = nx * np.sin(angle) + ny * np.cos(angle)

    if field_type == "dipole":
        r = np.sqrt(rnx * rnx + rny * rny) + 0.01
        bx = 3.0 * rnx * rny / (r ** 4) * strength
        by = (2.0 * rny * rny - rnx * rnx) / (r ** 4) * strength

    elif field_type == "quadrupole":
        bx = np.zeros((h, w), dtype=np.float32)
        by = np.zeros((h, w), dtype=np.float32)
        for p in range(poles):
            theta = p * 2 * np.pi / poles
            px = 0.25 * np.cos(theta)
            py = 0.25 * np.sin(theta)
            ddx = rnx - px
            ddy = rny - py
            r = np.sqrt(ddx * ddx + ddy * ddy) + 0.01
            sign = (-1) ** p
            bx += sign * ddx / (r ** 3) * strength * 0.3
            by += sign * ddy / (r ** 3) * strength * 0.3

    elif field_type == "toroidal":
        r = np.sqrt(rnx * rnx + rny * rny) + 0.01
        ring_dist = np.abs(r - 0.3)
        ring_force = np.exp(-ring_dist * 10) * strength
        bx = -rny / r * ring_force
        by = rnx / r * ring_force

    else:  # chaotic
        bx = np.zeros((h, w), dtype=np.float32)
        by = np.zeros((h, w), dtype=np.float32)
        for _ in range(5):
            rpx = (rng.random() - 0.5) * 0.8
            rpy = (rng.random() - 0.5) * 0.8
            ddx = rnx - rpx
            ddy = rny - rpy
            r = np.sqrt(ddx * ddx + ddy * ddy) + 0.01
            bx += ddy / (r ** 3) * strength * 0.2
            by += -ddx / (r ** 3) * strength * 0.2

    # Lorentz-like force: F perpendicular to v
    if frame_index == 0:
        state["vx"] = bx * 0.01
        state["vy"] = by * 0.01
    else:
        b_mag = np.sqrt(bx * bx + by * by) + 0.01
        fx = state["vy"] * b_mag * 0.1 + bx * 0.01
        fy = -state["vx"] * b_mag * 0.1 + by * 0.01
        state["vx"] = state["vx"] * damping + fx
        state["vy"] = state["vy"] * damping + fy

    state["dx"] += state["vx"]
    state["dy"] += state["vy"]

    max_disp = max(h, w) * 0.4
    state["dx"] = np.clip(state["dx"], -max_disp, max_disp)
    state["dy"] = np.clip(state["dy"], -max_disp, max_disp)

    result = _remap_frame(frame, state["dx"], state["dy"])

    if frame_index >= total_frames - 1:
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

    # Extra state for echoes
    if "echoes_dx" not in state:
        state["echoes_dx"] = [np.zeros((h, w), dtype=np.float32) for _ in range(echo_count)]
        state["echoes_dy"] = [np.zeros((h, w), dtype=np.float32) for _ in range(echo_count)]
        state["time_dir"] = 1.0

    rng = np.random.default_rng(seed + frame_index)
    t = frame_index / 30.0

    # Periodic time reversal
    if rng.random() < reverse_probability * 0.1:
        state["time_dir"] *= -1.0

    # Sinusoidal time warping
    time_factor = state["time_dir"] * (1.0 + np.sin(t * warp_speed * np.pi) * 0.5)

    # Turbulent force
    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
    phase = rng.random() * 100
    fx = 3.0 * np.sin(x_grid / 30.0 + t * 2 + phase) * np.cos(y_grid / 25.0 + t * 1.5)
    fy = 3.0 * np.cos(x_grid / 25.0 + t * 1.8) * np.sin(y_grid / 30.0 + t * 2.2 + phase)

    state["vx"] = state["vx"] * damping + fx * time_factor * 0.05
    state["vy"] = state["vy"] * damping + fy * time_factor * 0.05

    # Shift echo history
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
    result = _remap_frame(frame, state["dx"], state["dy"]).astype(np.float32)
    total_weight = 1.0

    for i in range(echo_count):
        weight = echo_decay ** (i + 1)
        echo_result = _remap_frame(frame, state["echoes_dx"][i], state["echoes_dy"][i])
        result += echo_result.astype(np.float32) * weight
        total_weight += weight

    result /= total_weight

    if frame_index >= total_frames - 1:
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
    t = frame_index / 30.0

    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w / 2, h / 2

    fold_offsets = rng.random(num_folds) - 0.5
    fold_base_angles = rng.random(num_folds) * np.pi

    fx_total = np.zeros((h, w), dtype=np.float32)
    fy_total = np.zeros((h, w), dtype=np.float32)
    fold_width_px = fold_width * max(h, w)

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

    result = _remap_frame(frame, state["dx"], state["dy"])

    if frame_index >= total_frames - 1:
        _physics_state.pop(key, None)

    return np.clip(result, 0, 255).astype(np.uint8)

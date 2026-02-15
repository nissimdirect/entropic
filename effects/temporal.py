"""
Entropic — Temporal Effects
Effects that operate across frames (need frame_index context).
"""

import numpy as np


# Unified state dict for all temporal effects, keyed by f"{effect}_{seed}"
# This allows multiple instances of the same effect (e.g. two timeline regions
# both using "feedback" with different seeds) to maintain independent state.
_temporal_state = {}


def _get_state(key, default_factory):
    """Get or create temporal state for this effect instance."""
    if key not in _temporal_state:
        _temporal_state[key] = default_factory()
    return _temporal_state[key]


def _cleanup_if_done(key, frame_index, total_frames):
    """Remove state at end of render to prevent memory leaks."""
    if frame_index >= total_frames - 1:
        _temporal_state.pop(key, None)


def stutter(
    frame: np.ndarray,
    repeat: int = 3,
    interval: int = 8,
    frame_index: int = 0,
    total_frames: int = 1,
    seed: int = 42,
) -> np.ndarray:
    """Freeze-stutter: hold a frame for `repeat` frames every `interval` frames.

    Creates a visual stutter/freeze effect like a skipping record.

    Args:
        frame: Input frame (H, W, 3) uint8.
        repeat: How many frames to hold (freeze duration).
        interval: How often to trigger a stutter (every N frames).
        frame_index: Current frame number (injected by render loop).
        total_frames: Total frame count (injected by render loop).
        seed: Random seed for state isolation.

    Returns:
        Frame (H, W, 3) uint8 — either the original or a held copy.
    """
    repeat = max(1, int(repeat))
    interval = max(1, int(interval))

    key = f"stutter_{seed}"
    state = _get_state(key, lambda: {"held_frame": None, "hold_until": -1})

    # Reset state at frame 0 (new render)
    if frame_index == 0:
        state["held_frame"] = None
        state["hold_until"] = -1

    # If we're in a hold period, return the held frame
    if frame_index <= state["hold_until"] and state["held_frame"] is not None:
        held = state["held_frame"]
        # Resize if frame dimensions changed (safety)
        if held.shape != frame.shape:
            state["held_frame"] = None
            _cleanup_if_done(key, frame_index, total_frames)
            return frame.copy()
        _cleanup_if_done(key, frame_index, total_frames)
        return held.copy()

    # Check if this frame triggers a new stutter
    if frame_index % interval == 0:
        state["held_frame"] = frame.copy()
        state["hold_until"] = frame_index + repeat - 1
        _cleanup_if_done(key, frame_index, total_frames)
        return frame.copy()

    _cleanup_if_done(key, frame_index, total_frames)
    return frame.copy()


def frame_drop(
    frame: np.ndarray,
    drop_rate: float = 0.3,
    frame_index: int = 0,
    total_frames: int = 1,
    seed: int = 42,
) -> np.ndarray:
    """Randomly drop frames to black, simulating signal dropout.

    Args:
        frame: Input frame (H, W, 3) uint8.
        drop_rate: Probability of dropping each frame (0.0-1.0).
        frame_index: Current frame number.
        total_frames: Total frame count.
        seed: Random seed for reproducibility.

    Returns:
        Frame or black frame.
    """
    drop_rate = max(0.0, min(1.0, float(drop_rate)))

    # Deterministic per-frame randomness (reproducible renders)
    rng = np.random.RandomState(seed + frame_index)
    if rng.random() < drop_rate:
        return np.zeros_like(frame)

    return frame.copy()


def time_stretch(
    frame: np.ndarray,
    speed: float = 0.5,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Simulate speed changes by duplicating or skipping frames.

    When speed < 1.0: slow motion (some frames get duplicated — handled by hold logic)
    When speed > 1.0: fast forward (effectively same frame passes through)

    Note: This is a per-frame pass-through. The actual time-stretch happens
    at the render level by frame selection. This effect adds visual artifacts
    (slight blend/ghost) to emphasize the speed change.

    Args:
        frame: Input frame (H, W, 3) uint8.
        speed: Speed multiplier (0.25 = quarter speed, 2.0 = double speed).
        frame_index: Current frame number.
        total_frames: Total frame count.

    Returns:
        Frame with speed-change artifacts.
    """
    speed = max(0.1, min(4.0, float(speed)))

    # For slow-mo: add slight brightness pulse to emphasize the effect
    if speed < 1.0:
        # Pulse brightness based on position in stretched segment
        cycle = int(1.0 / speed)
        pos_in_cycle = frame_index % max(1, cycle)
        brightness_mod = 1.0 + 0.05 * np.sin(pos_in_cycle * np.pi / max(1, cycle))
        result = np.clip(frame.astype(np.float32) * brightness_mod, 0, 255).astype(np.uint8)
        return result

    return frame.copy()


def feedback(
    frame: np.ndarray,
    decay: float = 0.3,
    frame_index: int = 0,
    total_frames: int = 1,
    seed: int = 42,
) -> np.ndarray:
    """Overlay previous frame at partial opacity, creating ghost trails.

    Like sending output back to input — each frame bleeds into the next.
    Higher decay = longer trails. Classic video feedback / echo effect.

    Args:
        frame: Input frame (H, W, 3) uint8.
        decay: How much of the previous frame persists (0.0-0.95).
        frame_index: Current frame number.
        total_frames: Total frame count.
        seed: Random seed for state isolation.

    Returns:
        Frame with ghost overlay from previous frame.
    """
    decay = max(0.0, min(0.95, float(decay)))

    key = f"feedback_{seed}"
    state = _get_state(key, lambda: {"prev_frame": None})

    # Reset at frame 0
    if frame_index == 0:
        state["prev_frame"] = None

    prev = state["prev_frame"]

    if prev is None or prev.shape != frame.shape:
        # No previous frame — pass through
        state["prev_frame"] = frame.copy()
        _cleanup_if_done(key, frame_index, total_frames)
        return frame.copy()

    # Blend: current * (1 - decay) + previous * decay
    result = np.clip(
        frame.astype(np.float32) * (1.0 - decay) + prev.astype(np.float32) * decay,
        0, 255
    ).astype(np.uint8)

    state["prev_frame"] = result.copy()
    _cleanup_if_done(key, frame_index, total_frames)
    return result


def tape_stop(
    frame: np.ndarray,
    trigger: float = 0.7,
    ramp_frames: int = 15,
    frame_index: int = 0,
    total_frames: int = 1,
    seed: int = 42,
) -> np.ndarray:
    """Tape stop: freeze and darken like a tape machine powering down.

    At the trigger point (fraction of total duration), the video freezes
    on the current frame and progressively darkens to black over ramp_frames.

    Args:
        frame: Input frame (H, W, 3) uint8.
        trigger: When to trigger the stop (0.0-1.0 fraction of total duration).
        ramp_frames: How many frames the fade-to-black takes.
        frame_index: Current frame number.
        total_frames: Total frame count.
        seed: Random seed for state isolation.

    Returns:
        Frame — normal before trigger, frozen+darkening after.
    """
    trigger = max(0.0, min(1.0, float(trigger)))
    ramp_frames = max(1, int(ramp_frames))
    trigger_frame = int(trigger * max(1, total_frames - 1))

    key = f"tapestop_{seed}"
    state = _get_state(key, lambda: {"frozen_frame": None, "trigger_frame": trigger_frame})

    # Reset at frame 0
    if frame_index == 0:
        state["frozen_frame"] = None
        state["trigger_frame"] = trigger_frame

    # Before trigger — pass through
    if frame_index < trigger_frame:
        _cleanup_if_done(key, frame_index, total_frames)
        return frame.copy()

    # At trigger — capture the freeze frame
    if state["frozen_frame"] is None or frame_index == trigger_frame:
        state["frozen_frame"] = frame.copy()

    frozen = state["frozen_frame"]
    if frozen.shape != frame.shape:
        _cleanup_if_done(key, frame_index, total_frames)
        return frame.copy()

    # After trigger — frozen frame with progressive darkening
    frames_since_trigger = frame_index - trigger_frame
    brightness = max(0.0, 1.0 - (frames_since_trigger / ramp_frames))

    result = np.clip(frozen.astype(np.float32) * brightness, 0, 255).astype(np.uint8)
    _cleanup_if_done(key, frame_index, total_frames)
    return result


def tremolo(
    frame: np.ndarray,
    rate: float = 2.0,
    depth: float = 0.5,
    frame_index: int = 0,
    total_frames: int = 1,
    fps: float = 30.0,
) -> np.ndarray:
    """Brightness oscillation over time, like an audio tremolo effect.

    Modulates frame brightness with a sine wave at the given rate.

    Args:
        frame: Input frame (H, W, 3) uint8.
        rate: Oscillation speed in Hz (cycles per second).
        depth: Modulation depth (0.0 = no effect, 1.0 = full black at trough).
        frame_index: Current frame number.
        total_frames: Total frame count.
        fps: Frames per second (for timing the oscillation).

    Returns:
        Frame with brightness modulated by sine wave.
    """
    rate = max(0.1, min(20.0, float(rate)))
    depth = max(0.0, min(1.0, float(depth)))
    fps = max(1.0, float(fps))

    # Sine wave: oscillates between (1 - depth) and 1.0
    t = frame_index / fps
    mod = 1.0 - depth * 0.5 * (1.0 - np.sin(2.0 * np.pi * rate * t))

    result = np.clip(frame.astype(np.float32) * mod, 0, 255).astype(np.uint8)
    return result


def delay(
    frame: np.ndarray,
    delay_frames: int = 5,
    decay: float = 0.4,
    frame_index: int = 0,
    total_frames: int = 1,
    seed: int = 42,
) -> np.ndarray:
    """Ghost frames overlaid with decay — video echo/delay effect.

    Unlike feedback (which blends with the immediately previous output),
    delay looks back a fixed number of frames and blends.

    Args:
        frame: Input frame (H, W, 3) uint8.
        delay_frames: How many frames back to look for the echo.
        decay: Opacity of the delayed frame (0.0-0.9).
        frame_index: Current frame number.
        total_frames: Total frame count.
        seed: Random seed for state isolation.

    Returns:
        Frame blended with a frame from N frames ago.
    """
    delay_frames = max(1, min(60, int(delay_frames)))
    decay = max(0.0, min(0.9, float(decay)))

    key = f"delay_{seed}"
    state = _get_state(key, lambda: {"buffer": []})

    # Reset at frame 0
    if frame_index == 0:
        state["buffer"] = []

    buf = state["buffer"]

    # Store current frame in buffer
    buf.append(frame.copy())

    # Keep buffer bounded
    max_buf = delay_frames + 1
    if len(buf) > max_buf:
        buf[:] = buf[-max_buf:]

    # If we don't have enough history yet, pass through
    if len(buf) <= delay_frames:
        _cleanup_if_done(key, frame_index, total_frames)
        return frame.copy()

    # Get the delayed frame
    delayed = buf[-(delay_frames + 1)]

    if delayed.shape != frame.shape:
        _cleanup_if_done(key, frame_index, total_frames)
        return frame.copy()

    # Blend: current * (1 - decay) + delayed * decay
    result = np.clip(
        frame.astype(np.float32) * (1.0 - decay) + delayed.astype(np.float32) * decay,
        0, 255
    ).astype(np.uint8)
    _cleanup_if_done(key, frame_index, total_frames)
    return result


def decimator(
    frame: np.ndarray,
    factor: int = 3,
    frame_index: int = 0,
    total_frames: int = 1,
    seed: int = 42,
) -> np.ndarray:
    """Reduce effective framerate by holding every Nth frame.

    Like a sample rate reducer for video — drops temporal resolution.
    Creates a choppy, lo-fi motion feel.

    Args:
        frame: Input frame (H, W, 3) uint8.
        factor: Hold every Nth frame (2 = half framerate, 4 = quarter).
        frame_index: Current frame number.
        total_frames: Total frame count.
        seed: Random seed for state isolation.

    Returns:
        Current frame if on a sample point, otherwise the last sampled frame.
    """
    factor = max(1, min(30, int(factor)))

    key = f"decimator_{seed}"
    state = _get_state(key, lambda: {"held_frame": None})

    # Reset at frame 0
    if frame_index == 0:
        state["held_frame"] = None

    # On a sample point: capture and return
    if frame_index % factor == 0:
        state["held_frame"] = frame.copy()
        _cleanup_if_done(key, frame_index, total_frames)
        return frame.copy()

    # Between sample points: return held frame
    held = state.get("held_frame")
    if held is not None and held.shape == frame.shape:
        _cleanup_if_done(key, frame_index, total_frames)
        return held.copy()

    _cleanup_if_done(key, frame_index, total_frames)
    return frame.copy()


def sample_and_hold(
    frame: np.ndarray,
    hold_min: int = 4,
    hold_max: int = 15,
    frame_index: int = 0,
    total_frames: int = 1,
    seed: int = 42,
) -> np.ndarray:
    """Freeze frame at random intervals — like sample & hold in a synth.

    Captures a frame and holds it for a random duration, then grabs the next
    live frame and holds again. Creates an irregular, glitchy freeze pattern.

    Args:
        frame: Input frame (H, W, 3) uint8.
        hold_min: Minimum hold duration in frames.
        hold_max: Maximum hold duration in frames.
        frame_index: Current frame number.
        total_frames: Total frame count.
        seed: Random seed for reproducible hold durations.

    Returns:
        Current frame or a held copy.
    """
    hold_min = max(1, min(60, int(hold_min)))
    hold_max = max(hold_min, min(60, int(hold_max)))

    key = f"samplehold_{seed}"
    state = _get_state(key, lambda: {"held_frame": None, "hold_until": -1})

    # Reset at frame 0
    if frame_index == 0:
        state["held_frame"] = None
        state["hold_until"] = -1

    # If we're in a hold period, return the held frame
    if frame_index <= state["hold_until"] and state["held_frame"] is not None:
        held = state["held_frame"]
        if held.shape != frame.shape:
            state["held_frame"] = None
            _cleanup_if_done(key, frame_index, total_frames)
            return frame.copy()
        _cleanup_if_done(key, frame_index, total_frames)
        return held.copy()

    # Hold expired or first frame — capture new sample
    rng = np.random.RandomState(seed + frame_index)
    hold_duration = rng.randint(hold_min, hold_max + 1)
    state["held_frame"] = frame.copy()
    state["hold_until"] = frame_index + hold_duration - 1

    _cleanup_if_done(key, frame_index, total_frames)
    return frame.copy()


def granulator(
    frame: np.ndarray,
    position: float = 0.5,
    grain_size: int = 4,
    spray: float = 0.0,
    density: int = 1,
    scan_speed: float = 0.0,
    reverse_prob: float = 0.0,
    frame_index: int = 0,
    total_frames: int = 1,
    seed: int = 42,
) -> np.ndarray:
    """Video granulator — rearrange video slices like Ableton's Granulator II.

    Buffers incoming frames and selects grains (slices) from the buffer
    based on position, spray (randomization), and scan speed. Creates
    stuttered, fragmented, time-scrambled textures from video.

    Inspired by granular synthesis: position selects WHERE to read,
    grain_size sets slice length, spray randomizes the read position,
    density layers multiple grains, scan_speed auto-advances position.

    Args:
        frame: Input frame (H, W, 3) uint8.
        position: Base read position in the buffer (0.0-1.0).
        grain_size: Length of each grain in frames (1-60).
        spray: Random offset range from position (0.0 = exact, 1.0 = anywhere).
        density: Number of grains to overlay (1-4). Higher = denser texture.
        scan_speed: Auto-advance rate for position (0.0 = static, 1.0 = normal speed).
        reverse_prob: Probability of playing a grain in reverse (0.0-1.0).
        frame_index: Current frame number (injected by render loop).
        total_frames: Total frame count.
        seed: Random seed for reproducible spray/selection.

    Returns:
        Frame (H, W, 3) uint8 — a grain selected from the buffer.
    """
    grain_size = max(1, min(60, int(grain_size)))
    spray = max(0.0, min(1.0, float(spray)))
    density = max(1, min(4, int(density)))
    scan_speed = max(0.0, min(2.0, float(scan_speed)))
    position = max(0.0, min(1.0, float(position)))
    reverse_prob = max(0.0, min(1.0, float(reverse_prob)))

    key = f"granulator_{seed}"
    state = _get_state(key, lambda: {"buffer": [], "grain_pos": position})

    # Reset at frame 0
    if frame_index == 0:
        state["buffer"] = []
        state["grain_pos"] = position

    buf = state["buffer"]

    # Always buffer the incoming frame
    buf.append(frame.copy())

    # Limit buffer to avoid memory issues (keep last 300 frames = ~10s at 30fps)
    max_buf = 300
    if len(buf) > max_buf:
        buf[:] = buf[-max_buf:]

    # Need at least a few frames before granulating
    if len(buf) < grain_size + 1:
        _cleanup_if_done(key, frame_index, total_frames)
        return frame.copy()

    rng = np.random.RandomState(seed + frame_index)

    # Advance grain position based on scan speed
    state["grain_pos"] += scan_speed / max(1, total_frames)
    if state["grain_pos"] > 1.0:
        state["grain_pos"] -= 1.0

    current_pos = state["grain_pos"]

    # Select grain(s)
    result = np.zeros(frame.shape, dtype=np.float32)

    for grain_idx in range(density):
        # Apply spray: randomize position
        spray_offset = rng.uniform(-spray, spray) * 0.5
        grain_read_pos = current_pos + spray_offset
        grain_read_pos = max(0.0, min(1.0, grain_read_pos))

        # Map position to buffer index
        buf_idx = int(grain_read_pos * (len(buf) - 1))

        # Determine which frame within the grain to show
        grain_phase = frame_index % grain_size
        if rng.random() < reverse_prob:
            grain_phase = grain_size - 1 - grain_phase

        read_idx = buf_idx + grain_phase
        read_idx = max(0, min(len(buf) - 1, read_idx))

        grain_frame = buf[read_idx]
        if grain_frame.shape == frame.shape:
            result += grain_frame.astype(np.float32)
        else:
            result += frame.astype(np.float32)

    # Average overlapping grains
    result = result / density
    _cleanup_if_done(key, frame_index, total_frames)
    return np.clip(result, 0, 255).astype(np.uint8)


def beat_repeat(
    frame: np.ndarray,
    interval: int = 16,
    offset: int = 0,
    gate: int = 8,
    grid: int = 4,
    variation: float = 0.0,
    chance: float = 1.0,
    decay: float = 0.0,
    pitch_decay: float = 0.0,
    frame_index: int = 0,
    total_frames: int = 1,
    seed: int = 42,
) -> np.ndarray:
    """Beat Repeat — triggered frame repetition inspired by Ableton's Beat Repeat.

    At regular intervals, captures a buffer window and repeats its frames.
    Creates glitchy stutters, build-ups, and rhythmic repetitions.

    Args:
        frame: Input frame (H, W, 3) uint8.
        interval: How often to trigger a repeat (in frames). Like "every 16 frames".
        offset: Delay before first trigger (in frames).
        gate: How long the repeat lasts (in frames). 0 = repeats until next trigger.
        grid: Subdivision size for the repeated slice (in frames).
            Smaller grid = faster stutter, larger grid = longer loops.
        variation: Randomize grid size per repeat (0.0 = fixed, 1.0 = wild).
        chance: Probability of triggering on each interval (0.0-1.0).
        decay: Opacity fade per repeat cycle (0.0 = no fade, 1.0 = rapid fade).
        pitch_decay: Speed up repeats over time (0.0 = constant, 1.0 = accelerating).
            Simulates "pitch decay" from Beat Repeat by showing fewer frames per cycle.
        frame_index: Current frame number (injected by render loop).
        total_frames: Total frame count.
        seed: Random seed for chance/variation.

    Returns:
        Frame (H, W, 3) uint8 — original or repeated from buffer.
    """
    interval = max(1, min(120, int(interval)))
    offset = max(0, min(60, int(offset)))
    gate = max(0, min(120, int(gate)))
    grid = max(1, min(60, int(grid)))
    variation = max(0.0, min(1.0, float(variation)))
    chance = max(0.0, min(1.0, float(chance)))
    decay = max(0.0, min(1.0, float(decay)))
    pitch_decay = max(0.0, min(1.0, float(pitch_decay)))

    key = f"beatrepeat_{seed}"
    state = _get_state(key, lambda: {
        "buffer": [],
        "repeating": False,
        "repeat_until": -1,
        "repeat_start": -1,
        "grid_frames": grid,
    })

    # Reset at frame 0
    if frame_index == 0:
        state["buffer"] = []
        state["repeating"] = False
        state["repeat_until"] = -1
        state["repeat_start"] = -1
        state["grid_frames"] = grid

    # Always buffer recent frames (keep enough for the grid)
    state["buffer"].append(frame.copy())
    max_buf = max(grid * 2, 60)
    if len(state["buffer"]) > max_buf:
        state["buffer"][:] = state["buffer"][-max_buf:]

    # Check if we're currently in a repeat phase
    if state["repeating"] and frame_index <= state["repeat_until"]:
        buf = state["buffer"]
        frames_into_repeat = frame_index - state["repeat_start"]

        # Calculate effective grid with pitch decay
        effective_grid = state["grid_frames"]
        if pitch_decay > 0.0:
            # Reduce grid size over time (speeds up repeats)
            repeat_progress = frames_into_repeat / max(1, gate if gate > 0 else interval)
            effective_grid = max(1, int(effective_grid * (1.0 - pitch_decay * repeat_progress)))

        # Which frame in the grid to show
        grid_phase = frames_into_repeat % max(1, effective_grid)

        # How many complete repeat cycles we've done
        repeat_cycle = frames_into_repeat // max(1, effective_grid)

        # Index into the captured buffer
        buf_read = min(grid_phase, len(buf) - 1)
        # Read from the frames captured AT the trigger point
        capture_start = max(0, len(buf) - state["grid_frames"] - (frame_index - state["repeat_start"]))
        read_idx = min(capture_start + grid_phase, len(buf) - 1)
        read_idx = max(0, read_idx)

        repeated = buf[read_idx]

        # Apply decay (opacity fade per repeat cycle)
        if decay > 0.0 and repeat_cycle > 0:
            opacity = max(0.0, 1.0 - decay * repeat_cycle)
            repeated = np.clip(
                repeated.astype(np.float32) * opacity +
                frame.astype(np.float32) * (1.0 - opacity),
                0, 255
            ).astype(np.uint8)

        if repeated.shape == frame.shape:
            _cleanup_if_done(key, frame_index, total_frames)
            return repeated
        _cleanup_if_done(key, frame_index, total_frames)
        return frame.copy()
    else:
        state["repeating"] = False

    # Check for trigger
    adjusted_frame = frame_index - offset
    if adjusted_frame >= 0 and adjusted_frame % interval == 0:
        rng = np.random.RandomState(seed + frame_index)

        # Roll for chance
        if rng.random() < chance:
            # Apply variation to grid
            effective_grid = grid
            if variation > 0.0:
                grid_var = rng.uniform(1.0 - variation * 0.5, 1.0 + variation * 0.5)
                effective_grid = max(1, int(grid * grid_var))

            state["repeating"] = True
            state["repeat_start"] = frame_index
            state["repeat_until"] = frame_index + (gate if gate > 0 else interval) - 1
            state["grid_frames"] = effective_grid

            # Return current frame (first frame of the repeat)
            _cleanup_if_done(key, frame_index, total_frames)
            return frame.copy()

    _cleanup_if_done(key, frame_index, total_frames)
    return frame.copy()


def strobe(
    frame: np.ndarray,
    rate: float = 4.0,
    color: str = "white",
    shape: str = "full",
    opacity: float = 1.0,
    duty: float = 0.5,
    frame_index: int = 0,
    total_frames: int = 1,
    fps: float = 30.0,
    seed: int = 42,
) -> np.ndarray:
    """Video strobe — flash a color, shape, or pattern at regular intervals.

    Like a strobe light in a club. Can overlay solid colors, geometric shapes,
    bars, or inverted versions of the frame. Creates rhythmic visual pulses.

    Args:
        frame: Input frame (H, W, 3) uint8.
        rate: Strobe speed in Hz (flashes per second). 4.0 = club strobe.
        color: Flash color — "white", "black", "red", "blue", "green",
            "invert" (inverts the frame), "random" (random color per flash).
        shape: Flash shape — "full" (whole frame), "circle" (center circle),
            "bars_h" (horizontal bars), "bars_v" (vertical bars),
            "grid" (checkerboard grid).
        opacity: Flash opacity (0.0-1.0). 1.0 = fully opaque flash.
        duty: Duty cycle (0.0-1.0). 0.5 = on half the time. Lower = sharper flash.
        frame_index: Current frame number.
        total_frames: Total frame count.
        fps: Frames per second.
        seed: Random seed for "random" color mode.

    Returns:
        Frame (H, W, 3) uint8.
    """
    rate = max(0.1, min(30.0, float(rate)))
    opacity = max(0.0, min(1.0, float(opacity)))
    duty = max(0.05, min(0.95, float(duty)))
    fps = max(1.0, float(fps))

    # Determine if we're in the "on" phase of the strobe
    t = frame_index / fps
    cycle_pos = (t * rate) % 1.0
    is_on = cycle_pos < duty

    if not is_on:
        return frame.copy()

    h, w = frame.shape[:2]

    # Build the flash color
    color_map = {
        "white": (255, 255, 255),
        "black": (0, 0, 0),
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "yellow": (255, 255, 0),
        "cyan": (0, 255, 255),
        "magenta": (255, 0, 255),
    }

    if color == "invert":
        flash_frame = 255 - frame
    elif color == "random":
        rng = np.random.RandomState(seed + int(t * rate))
        rc = tuple(int(x) for x in rng.randint(0, 256, 3))
        flash_frame = np.full_like(frame, rc)
    else:
        rgb = color_map.get(color, (255, 255, 255))
        flash_frame = np.full_like(frame, rgb)

    # Build the shape mask
    mask = np.zeros((h, w), dtype=np.float32)

    if shape == "full":
        mask[:] = 1.0
    elif shape == "circle":
        cy, cx = h // 2, w // 2
        radius = min(h, w) // 3
        y_coords, x_coords = np.ogrid[:h, :w]
        dist = np.sqrt((x_coords - cx) ** 2 + (y_coords - cy) ** 2)
        mask[dist <= radius] = 1.0
    elif shape == "bars_h":
        bar_height = max(4, h // 8)
        for y in range(0, h, bar_height * 2):
            mask[y:min(y + bar_height, h), :] = 1.0
    elif shape == "bars_v":
        bar_width = max(4, w // 8)
        for x in range(0, w, bar_width * 2):
            mask[:, x:min(x + bar_width, w)] = 1.0
    elif shape == "grid":
        cell_h = max(4, h // 6)
        cell_w = max(4, w // 6)
        for y in range(0, h, cell_h * 2):
            for x in range(0, w, cell_w * 2):
                mask[y:min(y + cell_h, h), x:min(x + cell_w, w)] = 1.0
    else:
        mask[:] = 1.0

    # Apply: blend flash onto frame using mask and opacity
    mask_3d = mask[:, :, np.newaxis] * opacity
    result = frame.astype(np.float32) * (1.0 - mask_3d) + flash_frame.astype(np.float32) * mask_3d
    return np.clip(result, 0, 255).astype(np.uint8)


def lfo(
    frame: np.ndarray,
    rate: float = 2.0,
    depth: float = 0.5,
    target: str = "brightness",
    waveform: str = "sine",
    frame_index: int = 0,
    total_frames: int = 1,
    fps: float = 30.0,
    seed: int = 42,
) -> np.ndarray:
    """Multi-target LFO — oscillate ANY visual parameter over time.

    Enhanced version of tremolo. Instead of just brightness, the LFO can
    modulate pixel displacement, channel shift, blur, moiré patterns,
    and glitch intensity. Think of it as a video synth LFO.

    Args:
        frame: Input frame (H, W, 3) uint8.
        rate: Oscillation speed in Hz.
        depth: Modulation depth (0.0-1.0).
        target: What to modulate:
            "brightness" — classic tremolo (lighter/darker)
            "displacement" — pixel warp/displacement oscillation
            "channelshift" — RGB channels drift apart and back
            "blur" — blur amount oscillates (focus breathing)
            "moire" — interference pattern overlay that shifts
            "glitch" — row shift/block corruption intensity oscillates
            "invert" — oscillating color inversion
            "posterize" — color levels oscillate (lo-fi breathing)
        waveform: LFO shape — "sine", "square", "saw", "triangle", "random".
        frame_index: Current frame number.
        total_frames: Total frame count.
        fps: Frames per second.
        seed: Random seed for "random" waveform.

    Returns:
        Frame (H, W, 3) uint8.
    """
    rate = max(0.1, min(20.0, float(rate)))
    depth = max(0.0, min(1.0, float(depth)))
    fps = max(1.0, float(fps))

    t = frame_index / fps
    phase = (t * rate) % 1.0

    # Generate LFO value based on waveform shape (0.0 to 1.0)
    if waveform == "sine":
        lfo_val = 0.5 * (1.0 + np.sin(2.0 * np.pi * phase))
    elif waveform == "square":
        lfo_val = 1.0 if phase < 0.5 else 0.0
    elif waveform == "saw":
        lfo_val = phase
    elif waveform == "triangle":
        lfo_val = 2.0 * phase if phase < 0.5 else 2.0 * (1.0 - phase)
    elif waveform == "random":
        rng = np.random.RandomState(seed + int(t * rate))
        lfo_val = rng.random()
    else:
        lfo_val = 0.5 * (1.0 + np.sin(2.0 * np.pi * phase))

    # Scale by depth
    amount = lfo_val * depth
    h, w = frame.shape[:2]
    f = frame.astype(np.float32)

    if target == "brightness":
        mod = 1.0 - depth + amount
        result = np.clip(f * mod, 0, 255)

    elif target == "displacement":
        # Pixel displacement — rows shift left/right based on LFO
        max_shift = int(amount * 40)
        result = f.copy()
        if max_shift > 0:
            for y in range(h):
                row_shift = int(np.sin(y * 0.1 + phase * 6.28) * max_shift)
                result[y] = np.roll(f[y], row_shift, axis=0)

    elif target == "channelshift":
        # RGB channels drift apart
        offset = int(amount * 20)
        result = np.zeros_like(f)
        result[:, :, 0] = np.roll(f[:, :, 0], offset, axis=1)      # R shifts right
        result[:, :, 1] = f[:, :, 1]                                 # G stays
        result[:, :, 2] = np.roll(f[:, :, 2], -offset, axis=1)      # B shifts left

    elif target == "blur":
        # Blur amount oscillates
        from cv2 import GaussianBlur
        ksize = max(1, int(amount * 21)) | 1  # Must be odd
        if ksize > 1:
            result = GaussianBlur(frame, (ksize, ksize), 0).astype(np.float32)
        else:
            result = f.copy()

    elif target == "moire":
        # Interference pattern overlay — sine gratings that shift with LFO
        y_coords = np.arange(h).reshape(-1, 1)
        x_coords = np.arange(w).reshape(1, -1)
        freq1 = 0.05 + amount * 0.15
        freq2 = 0.07 + amount * 0.1
        pattern = np.sin(y_coords * freq1 + phase * 6.28) * np.sin(x_coords * freq2 + phase * 3.14)
        pattern = (pattern * 0.5 + 0.5)  # Normalize to 0-1
        pattern_3d = np.stack([pattern] * 3, axis=-1) * 255.0 * amount
        result = f * (1.0 - amount * 0.5) + pattern_3d * (amount * 0.5)

    elif target == "glitch":
        # Row shift + block corruption intensity oscillates
        result = f.copy()
        if amount > 0.05:
            rng = np.random.RandomState(seed + frame_index)
            num_rows = int(amount * h * 0.3)
            for _ in range(num_rows):
                y = rng.randint(0, h)
                shift = rng.randint(-int(amount * 50), int(amount * 50) + 1)
                result[y] = np.roll(f[y], shift, axis=0)
            # Block corruption
            num_blocks = int(amount * 10)
            for _ in range(num_blocks):
                by = rng.randint(0, max(1, h - 16))
                bx = rng.randint(0, max(1, w - 16))
                bh = rng.randint(4, 20)
                bw = rng.randint(4, 20)
                result[by:min(by+bh, h), bx:min(bx+bw, w)] = rng.randint(0, 256, (min(bh, h-by), min(bw, w-bx), 3))

    elif target == "invert":
        # Oscillating color inversion
        result = f * (1.0 - amount) + (255.0 - f) * amount

    elif target == "posterize":
        # Color levels oscillate — at peak, very lo-fi
        levels = max(2, int(16 - amount * 14))
        step = 256.0 / levels
        result = np.floor(f / step) * step

    else:
        # Fallback to brightness
        mod = 1.0 - depth + amount
        result = np.clip(f * mod, 0, 255)

    return np.clip(result, 0, 255).astype(np.uint8)

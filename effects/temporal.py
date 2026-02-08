"""
Entropic — Temporal Effects
Effects that operate across frames (need frame_index context).
"""

import numpy as np


# Module-level state for stateful temporal effects
_stutter_state = {"held_frame": None, "hold_until": -1}
_feedback_state = {"prev_frame": None}
_tapestop_state = {"frozen_frame": None, "trigger_frame": -1}
_delay_state = {"buffer": []}
_decimator_state = {"held_frame": None}
_samplehold_state = {"held_frame": None, "hold_until": -1}


def stutter(
    frame: np.ndarray,
    repeat: int = 3,
    interval: int = 8,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Freeze-stutter: hold a frame for `repeat` frames every `interval` frames.

    Creates a visual stutter/freeze effect like a skipping record.

    Args:
        frame: Input frame (H, W, 3) uint8.
        repeat: How many frames to hold (freeze duration).
        interval: How often to trigger a stutter (every N frames).
        frame_index: Current frame number (injected by render loop).
        total_frames: Total frame count (injected by render loop).

    Returns:
        Frame (H, W, 3) uint8 — either the original or a held copy.
    """
    global _stutter_state

    repeat = max(1, int(repeat))
    interval = max(1, int(interval))

    # Reset state at frame 0 (new render)
    if frame_index == 0:
        _stutter_state = {"held_frame": None, "hold_until": -1}

    # If we're in a hold period, return the held frame
    if frame_index <= _stutter_state["hold_until"] and _stutter_state["held_frame"] is not None:
        held = _stutter_state["held_frame"]
        # Resize if frame dimensions changed (safety)
        if held.shape != frame.shape:
            _stutter_state["held_frame"] = None
            return frame.copy()
        return held.copy()

    # Check if this frame triggers a new stutter
    if frame_index % interval == 0:
        _stutter_state["held_frame"] = frame.copy()
        _stutter_state["hold_until"] = frame_index + repeat - 1
        return frame.copy()

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
) -> np.ndarray:
    """Overlay previous frame at partial opacity, creating ghost trails.

    Like sending output back to input — each frame bleeds into the next.
    Higher decay = longer trails. Classic video feedback / echo effect.

    Args:
        frame: Input frame (H, W, 3) uint8.
        decay: How much of the previous frame persists (0.0-0.95).
        frame_index: Current frame number.
        total_frames: Total frame count.

    Returns:
        Frame with ghost overlay from previous frame.
    """
    global _feedback_state

    decay = max(0.0, min(0.95, float(decay)))

    # Reset at frame 0
    if frame_index == 0:
        _feedback_state = {"prev_frame": None}

    prev = _feedback_state["prev_frame"]

    if prev is None or prev.shape != frame.shape:
        # No previous frame — pass through
        _feedback_state["prev_frame"] = frame.copy()
        return frame.copy()

    # Blend: current * (1 - decay) + previous * decay
    result = np.clip(
        frame.astype(np.float32) * (1.0 - decay) + prev.astype(np.float32) * decay,
        0, 255
    ).astype(np.uint8)

    _feedback_state["prev_frame"] = result.copy()
    return result


def tape_stop(
    frame: np.ndarray,
    trigger: float = 0.7,
    ramp_frames: int = 15,
    frame_index: int = 0,
    total_frames: int = 1,
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

    Returns:
        Frame — normal before trigger, frozen+darkening after.
    """
    global _tapestop_state

    trigger = max(0.0, min(1.0, float(trigger)))
    ramp_frames = max(1, int(ramp_frames))
    trigger_frame = int(trigger * max(1, total_frames - 1))

    # Reset at frame 0
    if frame_index == 0:
        _tapestop_state = {"frozen_frame": None, "trigger_frame": trigger_frame}

    # Before trigger — pass through
    if frame_index < trigger_frame:
        return frame.copy()

    # At trigger — capture the freeze frame
    if _tapestop_state["frozen_frame"] is None or frame_index == trigger_frame:
        _tapestop_state["frozen_frame"] = frame.copy()

    frozen = _tapestop_state["frozen_frame"]
    if frozen.shape != frame.shape:
        return frame.copy()

    # After trigger — frozen frame with progressive darkening
    frames_since_trigger = frame_index - trigger_frame
    brightness = max(0.0, 1.0 - (frames_since_trigger / ramp_frames))

    result = np.clip(frozen.astype(np.float32) * brightness, 0, 255).astype(np.uint8)
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

    Returns:
        Frame blended with a frame from N frames ago.
    """
    global _delay_state

    delay_frames = max(1, min(60, int(delay_frames)))
    decay = max(0.0, min(0.9, float(decay)))

    # Reset at frame 0
    if frame_index == 0:
        _delay_state = {"buffer": []}

    buf = _delay_state["buffer"]

    # Store current frame in buffer
    buf.append(frame.copy())

    # Keep buffer bounded
    max_buf = delay_frames + 1
    if len(buf) > max_buf:
        buf[:] = buf[-max_buf:]

    # If we don't have enough history yet, pass through
    if len(buf) <= delay_frames:
        return frame.copy()

    # Get the delayed frame
    delayed = buf[-(delay_frames + 1)]

    if delayed.shape != frame.shape:
        return frame.copy()

    # Blend: current * (1 - decay) + delayed * decay
    result = np.clip(
        frame.astype(np.float32) * (1.0 - decay) + delayed.astype(np.float32) * decay,
        0, 255
    ).astype(np.uint8)
    return result


def decimator(
    frame: np.ndarray,
    factor: int = 3,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Reduce effective framerate by holding every Nth frame.

    Like a sample rate reducer for video — drops temporal resolution.
    Creates a choppy, lo-fi motion feel.

    Args:
        frame: Input frame (H, W, 3) uint8.
        factor: Hold every Nth frame (2 = half framerate, 4 = quarter).
        frame_index: Current frame number.
        total_frames: Total frame count.

    Returns:
        Current frame if on a sample point, otherwise the last sampled frame.
    """
    global _decimator_state

    factor = max(1, min(30, int(factor)))

    # Reset at frame 0
    if frame_index == 0:
        _decimator_state = {"held_frame": None}

    # On a sample point: capture and return
    if frame_index % factor == 0:
        _decimator_state["held_frame"] = frame.copy()
        return frame.copy()

    # Between sample points: return held frame
    held = _decimator_state.get("held_frame")
    if held is not None and held.shape == frame.shape:
        return held.copy()

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
    global _samplehold_state

    hold_min = max(1, min(60, int(hold_min)))
    hold_max = max(hold_min, min(60, int(hold_max)))

    # Reset at frame 0
    if frame_index == 0:
        _samplehold_state = {"held_frame": None, "hold_until": -1}

    # If we're in a hold period, return the held frame
    if frame_index <= _samplehold_state["hold_until"] and _samplehold_state["held_frame"] is not None:
        held = _samplehold_state["held_frame"]
        if held.shape != frame.shape:
            _samplehold_state["held_frame"] = None
            return frame.copy()
        return held.copy()

    # Hold expired or first frame — capture new sample
    rng = np.random.RandomState(seed + frame_index)
    hold_duration = rng.randint(hold_min, hold_max + 1)
    _samplehold_state["held_frame"] = frame.copy()
    _samplehold_state["hold_until"] = frame_index + hold_duration - 1

    return frame.copy()

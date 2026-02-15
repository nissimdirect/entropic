"""
Entropic — Sidechain Effects (Video-to-Video Ducking)
One video's properties modulate another video's parameters.

Like audio sidechain compression: when the "key" signal is loud,
the "main" signal ducks. Here, the "key" video's properties
(brightness, motion, edges, color) drive effects on the main video.

All effects follow standard Entropic signature with an extra
`key_frame` parameter that provides the sidechain input.
For recipes, the key video frames are loaded via the temporal context system.
"""

import numpy as np
import cv2

# ─── State buffers ───
_sidechain_state = {}


def _extract_sidechain_signal(key_frame: np.ndarray, source: str = "brightness") -> np.ndarray:
    """Extract a modulation signal from the key frame.

    Returns a float32 array normalized 0-1, same H×W as key_frame.
    """
    if source == "brightness":
        gray = np.mean(key_frame.astype(np.float32), axis=2)
        return gray / 255.0

    elif source == "motion":
        # Use edge detection as proxy for motion energy
        gray = cv2.cvtColor(key_frame, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150).astype(np.float32) / 255.0
        # Blur to make it a smooth signal
        return cv2.GaussianBlur(edges, (31, 31), 0)

    elif source == "edges":
        gray = cv2.cvtColor(key_frame, cv2.COLOR_RGB2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_32F)
        signal = np.abs(laplacian)
        return np.clip(signal / (signal.max() + 1e-6), 0, 1)

    elif source == "saturation":
        hsv = cv2.cvtColor(key_frame, cv2.COLOR_RGB2HSV)
        return hsv[:, :, 1].astype(np.float32) / 255.0

    elif source == "hue":
        hsv = cv2.cvtColor(key_frame, cv2.COLOR_RGB2HSV)
        return hsv[:, :, 0].astype(np.float32) / 180.0

    elif source == "contrast":
        gray = np.mean(key_frame.astype(np.float32), axis=2)
        mean = cv2.GaussianBlur(gray, (31, 31), 0)
        contrast = np.abs(gray - mean)
        return np.clip(contrast / (contrast.max() + 1e-6), 0, 1)

    else:
        # Default to brightness
        gray = np.mean(key_frame.astype(np.float32), axis=2)
        return gray / 255.0


def sidechain_duck(
    frame: np.ndarray,
    source: str = "brightness",
    threshold: float = 0.5,
    ratio: float = 4.0,
    attack: float = 0.3,
    release: float = 0.7,
    mode: str = "brightness",
    invert: bool = False,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Sidechain duck — key video's signal ducks the main video's parameter.

    The main frame's brightness/opacity/saturation/contrast is reduced
    wherever the key signal exceeds the threshold. Like a compressor
    with sidechain input.

    Uses the SAME video as key (self-sidechain) with temporal offset.
    For cross-video sidechain, use sidechain_cross.

    Args:
        source: What to extract from key ("brightness", "motion", "edges",
                "saturation", "contrast").
        threshold: Signal level to trigger ducking (0.0-1.0).
        ratio: Compression ratio (1.0-20.0). Higher = harder duck.
        attack: How fast ducking engages (0.0-1.0). 0 = instant.
        release: How fast ducking releases (0.0-1.0). 0 = instant.
        mode: What gets ducked ("brightness", "opacity", "saturation",
              "blur", "invert", "displace").
        invert: Invert sidechain signal (duck where signal is LOW).
    """
    key = f"sidechain_duck_{seed}"
    state = _sidechain_state.get(key, {"envelope": None})

    # Extract sidechain signal from the SAME frame (self-sidechain)
    signal = _extract_sidechain_signal(frame, source)

    if invert:
        signal = 1.0 - signal

    # Compute gain reduction (compressor math)
    above = np.maximum(signal - threshold, 0)
    gain_reduction = above * (1.0 - 1.0 / max(ratio, 1.0))

    # Apply attack/release envelope
    if state["envelope"] is not None:
        envelope = state["envelope"]
        # Where gain_reduction > envelope: attack (getting louder)
        # Where gain_reduction < envelope: release (getting quieter)
        attack_mask = gain_reduction > envelope
        new_envelope = np.where(
            attack_mask,
            envelope + (gain_reduction - envelope) * (1.0 - attack),
            envelope + (gain_reduction - envelope) * (1.0 - release),
        )
        gain_reduction = new_envelope
    state["envelope"] = gain_reduction
    _sidechain_state[key] = state

    # Apply ducking based on mode
    gain = 1.0 - gain_reduction  # 0 = fully ducked, 1 = no ducking
    gain_3d = gain[:, :, np.newaxis]

    f = frame.astype(np.float32)

    if mode == "brightness":
        result = f * gain_3d

    elif mode == "opacity":
        # Fade to black where ducked
        result = f * gain_3d

    elif mode == "saturation":
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV).astype(np.float32)
        hsv[:, :, 1] = hsv[:, :, 1] * gain
        hsv = np.clip(hsv, 0, [180, 255, 255]).astype(np.uint8)
        result = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB).astype(np.float32)

    elif mode == "blur":
        # Blur amount proportional to ducking
        max_blur = 21
        blur_amount = int((1 - gain.mean()) * max_blur)
        blur_amount = blur_amount if blur_amount % 2 == 1 else blur_amount + 1
        blur_amount = max(1, blur_amount)
        blurred = cv2.GaussianBlur(f, (blur_amount, blur_amount), 0)
        # Blend: more ducked = more blurred
        result = f * gain_3d + blurred * (1 - gain_3d)

    elif mode == "invert":
        # Invert where ducked
        inverted = 255.0 - f
        result = f * gain_3d + inverted * (1 - gain_3d)

    elif mode == "displace":
        # Displace pixels based on ducking strength
        h, w = f.shape[:2]
        displacement = (1 - gain) * 30  # Up to 30px displacement
        y_coords, x_coords = np.mgrid[0:h, 0:w].astype(np.float32)
        rng = np.random.default_rng(seed + frame_index)
        x_offset = (rng.random((h, w)).astype(np.float32) - 0.5) * 2 * displacement
        y_offset = (rng.random((h, w)).astype(np.float32) - 0.5) * 2 * displacement
        map_x = np.clip(x_coords + x_offset, 0, w - 1)
        map_y = np.clip(y_coords + y_offset, 0, h - 1)
        result = cv2.remap(f, map_x, map_y, cv2.INTER_LINEAR)

    else:
        result = f * gain_3d

    if frame_index >= total_frames - 1:
        _sidechain_state.pop(key, None)

    return np.clip(result, 0, 255).astype(np.uint8)


def sidechain_pump(
    frame: np.ndarray,
    rate: float = 2.0,
    depth: float = 0.7,
    curve: str = "exponential",
    mode: str = "brightness",
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Sidechain pump — rhythmic ducking at a fixed rate.

    Simulates the classic sidechain pump effect (like a 4-on-the-floor
    kick ducking a pad). The ducking happens at regular intervals.

    Args:
        rate: Pump rate in Hz (0.5-8.0). 2.0 = 120 BPM quarter notes.
        depth: How deep the duck goes (0.0-1.0). 1.0 = full silence.
        curve: Envelope shape ("exponential", "linear", "logarithmic").
        mode: What gets pumped ("brightness", "saturation", "blur",
              "scale", "displace").
    """
    # Generate pump envelope
    phase = (frame_index / 30.0 * rate) % 1.0  # 0-1 per pump cycle

    if curve == "exponential":
        envelope = 1.0 - np.exp(-phase * 5) * depth
    elif curve == "linear":
        envelope = 1.0 - max(0, (1.0 - phase)) * depth
    elif curve == "logarithmic":
        envelope = 1.0 - np.log1p((1.0 - phase) * 10) / np.log1p(10) * depth
    else:
        envelope = 1.0 - max(0, (1.0 - phase)) * depth

    f = frame.astype(np.float32)

    if mode == "brightness":
        return np.clip(f * envelope, 0, 255).astype(np.uint8)

    elif mode == "saturation":
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV).astype(np.float32)
        hsv[:, :, 1] *= envelope
        hsv = np.clip(hsv, 0, [180, 255, 255]).astype(np.uint8)
        return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

    elif mode == "blur":
        blur_amount = int((1 - envelope) * 31)
        blur_amount = blur_amount if blur_amount % 2 == 1 else blur_amount + 1
        blur_amount = max(1, blur_amount)
        blurred = cv2.GaussianBlur(f, (blur_amount, blur_amount), 0)
        blend = 1 - envelope
        return np.clip(f * envelope + blurred * blend, 0, 255).astype(np.uint8)

    elif mode == "scale":
        h, w = f.shape[:2]
        scale = 0.8 + envelope * 0.2  # Scale between 80% and 100%
        new_h, new_w = int(h * scale), int(w * scale)
        scaled = cv2.resize(f, (new_w, new_h))
        # Center on canvas
        result = np.zeros_like(f)
        y_off = (h - new_h) // 2
        x_off = (w - new_w) // 2
        result[y_off:y_off+new_h, x_off:x_off+new_w] = scaled
        return np.clip(result, 0, 255).astype(np.uint8)

    elif mode == "displace":
        h, w = f.shape[:2]
        disp = (1 - envelope) * 20
        rng = np.random.default_rng(seed + frame_index)
        y_coords, x_coords = np.mgrid[0:h, 0:w].astype(np.float32)
        x_offset = (rng.random((h, w)).astype(np.float32) - 0.5) * 2 * disp
        map_x = np.clip(x_coords + x_offset, 0, w - 1).astype(np.float32)
        map_y = y_coords.astype(np.float32)
        return np.clip(cv2.remap(f, map_x, map_y, cv2.INTER_LINEAR), 0, 255).astype(np.uint8)

    return np.clip(f * envelope, 0, 255).astype(np.uint8)


def sidechain_gate(
    frame: np.ndarray,
    source: str = "brightness",
    threshold: float = 0.4,
    mode: str = "freeze",
    hold_frames: int = 5,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Sidechain gate — only pass video when sidechain signal exceeds threshold.

    Like an audio noise gate with sidechain: the main video only shows
    when the key signal is above threshold. Below threshold, the video
    freezes, blacks out, or shows an alternate treatment.

    Args:
        source: What to measure ("brightness", "motion", "edges",
                "saturation", "contrast").
        threshold: Gate open threshold (0.0-1.0).
        mode: What happens when gated ("black", "freeze", "invert",
              "blur", "posterize").
        hold_frames: Minimum frames to stay open after trigger (1-30).
    """
    key = f"gate_{seed}"
    state = _sidechain_state.get(key, {"frozen": None, "hold": 0, "open": False})

    # Measure signal level (global average)
    signal = _extract_sidechain_signal(frame, source)
    level = float(np.mean(signal))

    # Gate logic with hold
    if level > threshold:
        state["open"] = True
        state["hold"] = hold_frames
        state["frozen"] = frame.copy()
    elif state["hold"] > 0:
        state["hold"] -= 1
    else:
        state["open"] = False

    _sidechain_state[key] = state

    if state["open"]:
        result = frame
    else:
        f = frame.astype(np.float32)
        if mode == "black":
            result = np.zeros_like(frame)
        elif mode == "freeze" and state["frozen"] is not None:
            result = state["frozen"]
        elif mode == "invert":
            result = (255 - frame)
        elif mode == "blur":
            result = cv2.GaussianBlur(f, (31, 31), 0).astype(np.uint8)
        elif mode == "posterize":
            levels = 3
            result = (np.round(f / 255.0 * levels) / levels * 255).astype(np.uint8)
        else:
            result = np.zeros_like(frame)

    if frame_index >= total_frames - 1:
        _sidechain_state.pop(key, None)

    return result


# ─── Cross-Video Sidechain (unified two-input effect) ───

def _preprocess(frame: np.ndarray, pre: str) -> np.ndarray:
    """Pre-process a video source before sidechain interaction."""
    if pre == "none":
        return frame
    f = frame.astype(np.float32)
    if pre == "invert":
        return (255.0 - f).astype(np.uint8)
    elif pre == "grayscale":
        gray = np.mean(f, axis=2, keepdims=True)
        return np.broadcast_to(gray, f.shape).astype(np.uint8)
    elif pre == "saturate":
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 2.0, 0, 255)
        return cv2.cvtColor(np.clip(hsv, 0, [180, 255, 255]).astype(np.uint8), cv2.COLOR_HSV2RGB)
    elif pre == "desaturate":
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV).astype(np.float32)
        hsv[:, :, 1] = hsv[:, :, 1] * 0.2
        return cv2.cvtColor(np.clip(hsv, 0, [180, 255, 255]).astype(np.uint8), cv2.COLOR_HSV2RGB)
    elif pre == "high_contrast":
        gray = np.mean(f, axis=2, keepdims=True)
        mean = np.mean(gray)
        contrasted = (f - mean) * 2.5 + mean
        return np.clip(contrasted, 0, 255).astype(np.uint8)
    elif pre == "posterize":
        levels = 4
        return (np.round(f / 255.0 * levels) / levels * 255).astype(np.uint8)
    elif pre == "edges_only":
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        return np.stack([edges, edges, edges], axis=2)
    elif pre == "blur":
        return cv2.GaussianBlur(f, (21, 21), 0).astype(np.uint8)
    return frame


def _apply_blend(f_main, f_key, mask_3d, mask, mode, frame, key_frame, h, w):
    """Apply a blend mode between two float32 frames given a mask."""
    if mode == "blend":
        return f_main * (1 - mask_3d) + f_key * mask_3d

    elif mode == "hardcut":
        hard = (mask > 0.5).astype(np.float32)[:, :, np.newaxis]
        return f_main * (1 - hard) + f_key * hard

    elif mode == "multiply":
        multiplied = (f_main * f_key) / 255.0
        return f_main * (1 - mask_3d) + multiplied * mask_3d

    elif mode == "screen":
        screened = 255.0 - ((255.0 - f_main) * (255.0 - f_key)) / 255.0
        return f_main * (1 - mask_3d) + screened * mask_3d

    elif mode == "difference":
        diff = np.abs(f_main - f_key)
        return f_main * (1 - mask_3d) + diff * mask_3d

    elif mode == "color_steal":
        main_hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV).astype(np.float32)
        key_hsv = cv2.cvtColor(key_frame, cv2.COLOR_RGB2HSV).astype(np.float32)
        blended_hsv = main_hsv.copy()
        blended_hsv[:, :, 0] = main_hsv[:, :, 0] * (1 - mask) + key_hsv[:, :, 0] * mask
        blended_hsv[:, :, 1] = main_hsv[:, :, 1] * (1 - mask) + key_hsv[:, :, 1] * mask
        blended_hsv = np.clip(blended_hsv, 0, [180, 255, 255]).astype(np.uint8)
        return cv2.cvtColor(blended_hsv, cv2.COLOR_HSV2RGB).astype(np.float32)

    elif mode == "luminance_steal":
        main_hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV).astype(np.float32)
        key_hsv = cv2.cvtColor(key_frame, cv2.COLOR_RGB2HSV).astype(np.float32)
        blended_hsv = main_hsv.copy()
        blended_hsv[:, :, 2] = main_hsv[:, :, 2] * (1 - mask) + key_hsv[:, :, 2] * mask
        blended_hsv = np.clip(blended_hsv, 0, [180, 255, 255]).astype(np.uint8)
        return cv2.cvtColor(blended_hsv, cv2.COLOR_HSV2RGB).astype(np.float32)

    elif mode == "displace":
        displacement = mask * 40
        y_coords, x_coords = np.mgrid[0:h, 0:w].astype(np.float32)
        key_gray = np.mean(f_key, axis=2) / 255.0
        grad_x = cv2.Sobel(key_gray, cv2.CV_32F, 1, 0, ksize=5)
        grad_y = cv2.Sobel(key_gray, cv2.CV_32F, 0, 1, ksize=5)
        mag = np.sqrt(grad_x**2 + grad_y**2) + 1e-6
        map_x = np.clip(x_coords + (grad_x / mag) * displacement, 0, w - 1)
        map_y = np.clip(y_coords + (grad_y / mag) * displacement, 0, h - 1)
        return cv2.remap(f_main, map_x, map_y, cv2.INTER_LINEAR)

    elif mode == "rgb_shift":
        return np.stack([
            f_main[:, :, 0],
            f_main[:, :, 1] * (1 - mask) + f_key[:, :, 1] * mask,
            f_main[:, :, 2] * (1 - mask * 0.5) + f_key[:, :, 2] * (mask * 0.5),
        ], axis=2)

    elif mode == "spectral_split":
        blur_main = cv2.GaussianBlur(f_main, (31, 31), 0)
        high_key = f_key - cv2.GaussianBlur(f_key, (31, 31), 0)
        return blur_main + high_key * mask_3d

    elif mode == "phase":
        results = []
        s = np.mean(mask)
        for c in range(3):
            fft_m = np.fft.fft2(f_main[:, :, c])
            fft_k = np.fft.fft2(f_key[:, :, c])
            blended_phase = np.angle(fft_m) * (1 - s) + np.angle(fft_k) * s
            results.append(np.real(np.fft.ifft2(np.abs(fft_m) * np.exp(1j * blended_phase))))
        return np.stack(results, axis=2)

    elif mode == "beat":
        return f_main + (f_key - 128) * mask_3d

    # Default: blend
    return f_main * (1 - mask_3d) + f_key * mask_3d


def sidechain_cross(
    frame: np.ndarray,
    source: str = "brightness",
    threshold: float = 0.3,
    softness: float = 0.3,
    mode: str = "blend",
    strength: float = 0.8,
    invert: bool = False,
    pre_a: str = "none",
    pre_b: str = "none",
    attack: float = 0.0,
    decay: float = 0.0,
    sustain: float = 1.0,
    release: float = 0.0,
    lookahead: int = 0,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    key_frame: np.ndarray = None,
) -> np.ndarray:
    """Cross-video sidechain — one video busts through another with ADSR envelope.

    Video B (key_frame) drives a mask/blend on video A (frame).
    Where B's signal is strong, B shows through A. The interaction
    is shaped by an ADSR envelope, just like a synthesizer.

    Args:
        source: What to extract from key ("brightness", "edges",
                "saturation", "contrast", "hue", "motion").
        threshold: Below this, main shows. Above, key bleeds in (0-1).
        softness: Transition gradient (0=hard cut, 1=very soft).
        mode: How key interacts with main:
              "blend" — crossfade driven by signal
              "hardcut" — binary: above threshold = key, below = main
              "multiply" — key darkens main
              "screen" — key brightens main
              "difference" — absolute difference (interference)
              "color_steal" — key's hue+sat onto main's luminance
              "luminance_steal" — key's luminance onto main's color
              "displace" — key's edges push main's pixels
              "rgb_shift" — cross-channel bleed
              "spectral_split" — low freq main + high freq key
              "phase" — FFT phase blending (ghosting)
              "beat" — additive interference
        strength: Overall mix (0=all main, 1=full effect).
        invert: Invert signal (B shows where B is DARK).
        pre_a: Pre-process video A before interaction:
               "none", "invert", "grayscale", "saturate", "desaturate",
               "high_contrast", "posterize", "edges_only", "blur"
        pre_b: Pre-process video B before interaction (same options).
        attack: ADSR attack — frames to ramp from 0 to peak when signal
                triggers (0=instant, 30=1 sec at 30fps). Makes the
                interaction fade in smoothly.
        decay: ADSR decay — frames to drop from peak to sustain level
               after attack completes (0=instant).
        sustain: ADSR sustain — steady-state level while signal is above
                 threshold (0-1). 1.0 = full strength, 0.5 = half.
        release: ADSR release — frames to fade out when signal drops
                 below threshold (0=instant, 30=1 sec fade).
        lookahead: Look-ahead frames — peek at future key frames to
                   anticipate transients (0=none, 1-10 frames ahead).
                   Only works when key_frames_buffer is available.
    """
    if key_frame is None:
        return frame

    h, w = frame.shape[:2]
    kh, kw = key_frame.shape[:2]
    if (kh, kw) != (h, w):
        key_frame = cv2.resize(key_frame, (w, h))

    # Pre-process both sources
    proc_a = _preprocess(frame, pre_a) if pre_a != "none" else frame
    proc_b = _preprocess(key_frame, pre_b) if pre_b != "none" else key_frame

    # Extract sidechain signal from (processed) key
    signal = _extract_sidechain_signal(proc_b, source)
    if invert:
        signal = 1.0 - signal

    # Compute raw mask from signal + threshold
    if softness > 0:
        raw_mask = np.clip((signal - threshold) / max(softness, 0.01) * 0.5 + 0.5, 0, 1)
    else:
        raw_mask = (signal > threshold).astype(np.float32)

    # Global signal level (for ADSR triggering)
    level = float(np.mean(raw_mask))

    # ─── ADSR Envelope ───
    state_key = f"cross_{seed}"
    state = _sidechain_state.get(state_key, {
        "env_level": 0.0,     # current envelope value 0-1
        "phase": "idle",      # idle, attack, decay, sustain, release
        "phase_frame": 0,     # frames spent in current phase
        "triggered": False,   # whether signal is above threshold
    })

    has_adsr = (attack > 0 or decay > 0 or sustain < 1.0 or release > 0)

    if has_adsr:
        triggered = level > threshold
        prev_triggered = state["triggered"]
        env = state["env_level"]
        phase = state["phase"]
        pf = state["phase_frame"]

        # State transitions
        if triggered and not prev_triggered:
            # Note on → attack
            phase = "attack"
            pf = 0
        elif not triggered and prev_triggered:
            # Note off → release
            phase = "release"
            pf = 0

        # Update envelope based on current phase
        if phase == "attack":
            if attack > 0:
                env = min(1.0, env + 1.0 / max(attack, 1))
            else:
                env = 1.0
            pf += 1
            if env >= 1.0:
                env = 1.0
                phase = "decay"
                pf = 0

        elif phase == "decay":
            if decay > 0:
                env = max(sustain, env - (1.0 - sustain) / max(decay, 1))
            else:
                env = sustain
            pf += 1
            if env <= sustain:
                env = sustain
                phase = "sustain"
                pf = 0

        elif phase == "sustain":
            env = sustain
            pf += 1

        elif phase == "release":
            if release > 0:
                env = max(0.0, env - sustain / max(release, 1))
            else:
                env = 0.0
            pf += 1
            if env <= 0.0:
                env = 0.0
                phase = "idle"
                pf = 0

        else:  # idle
            env = 0.0

        state["env_level"] = env
        state["phase"] = phase
        state["phase_frame"] = pf
        state["triggered"] = triggered
        _sidechain_state[state_key] = state

        # Apply ADSR envelope to the mask
        mask = raw_mask * env * strength
    else:
        mask = raw_mask * strength

    mask_3d = mask[:, :, np.newaxis]

    # Apply blend mode using (optionally pre-processed) frames
    f_main = proc_a.astype(np.float32)
    f_key = proc_b.astype(np.float32)

    result = _apply_blend(f_main, f_key, mask_3d, mask, mode, proc_a, proc_b, h, w)

    # Cleanup state at end
    if frame_index >= total_frames - 1:
        _sidechain_state.pop(state_key, None)

    return np.clip(result, 0, 255).astype(np.uint8)


# Keep backward-compatible aliases
def sidechain_crossfeed(
    frame: np.ndarray,
    channel_map: str = "rgb_shift",
    strength: float = 0.7,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    key_frame: np.ndarray = None,
) -> np.ndarray:
    """Alias → sidechain_cross with rgb_shift/spectral_split modes."""
    return sidechain_cross(
        frame, mode=channel_map, strength=strength, seed=seed,
        frame_index=frame_index, total_frames=total_frames, key_frame=key_frame,
    )


def sidechain_interference(
    frame: np.ndarray,
    mode: str = "phase",
    strength: float = 0.7,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
    key_frame: np.ndarray = None,
) -> np.ndarray:
    """Alias → sidechain_cross with phase/beat modes."""
    return sidechain_cross(
        frame, mode=mode, strength=strength, seed=seed,
        frame_index=frame_index, total_frames=total_frames, key_frame=key_frame,
    )

"""
Entropic — DSP Filter Effects (Phaser, Flanger, Comb, Reverb)
Audio DSP concepts applied to video: frequency-domain phase sweeps,
temporal frame blending, spatial comb filtering, convolution reverb.

All effects follow the standard Entropic signature:
    fn(frame: np.ndarray, **params) -> np.ndarray
Temporal state is stored in module-level dicts, keyed by seed for isolation.
"""

import numpy as np
import cv2

# ─── Temporal state buffers (module-level, like datamosh) ───
_flanger_buffers = {}
_phaser_state = {}
_feedback_phaser_state = {}
_spectral_freeze_state = {}
_reverb_state = {}
_freq_flanger_state = {}


def video_flanger(
    frame: np.ndarray,
    rate: float = 0.5,
    depth: int = 10,
    feedback: float = 0.4,
    wet: float = 0.5,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Temporal flanger — blend current frame with oscillating-delay past frame.

    Like audio flanging: signal + delayed copy with modulating delay creates
    comb-filter-like temporal interference. Feedback feeds output back into buffer.

    Args:
        rate: LFO speed in Hz (0.05-3.0). Lower = slower, more dramatic sweeps.
        depth: Max delay in frames (1-60). Higher = wider flanging range.
        feedback: Output→buffer feedback (0.0-0.95). Higher = self-reinforcing.
        wet: Dry/wet mix (0.0-1.0).
    """
    key = f"video_flanger_{seed}"
    if key not in _flanger_buffers:
        _flanger_buffers[key] = []
    buf = _flanger_buffers[key]

    f = frame.astype(np.float32) / 255.0
    buf.append(f.copy())

    # Trim buffer to max needed size
    max_buf = max(depth + 5, 30)
    if len(buf) > max_buf:
        buf.pop(0)

    # LFO: oscillating delay time
    lfo = (np.sin(2 * np.pi * rate * frame_index / 30.0) + 1) / 2
    delay_frames = max(1, int(lfo * depth))

    # Get delayed frame
    delay_idx = max(0, len(buf) - 1 - delay_frames)
    delayed = buf[delay_idx]

    # Mix: original + delayed
    mixed = f * (1 - wet) + (f + delayed) * 0.5 * wet

    # Feedback into buffer
    if feedback > 0 and len(buf) > 1:
        buf[-1] = buf[-1] * (1 - feedback) + mixed * feedback

    # Reset state at end of video
    if frame_index >= total_frames - 1:
        _flanger_buffers.pop(key, None)

    return (np.clip(mixed, 0, 1) * 255).astype(np.uint8)


def video_phaser(
    frame: np.ndarray,
    rate: float = 0.3,
    stages: int = 4,
    depth: float = 1.0,
    feedback: float = 0.3,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Spatial phaser — FFT phase sweep creates sweeping notch interference.

    Like audio phasing: all-pass filters create notches that sweep through
    the spatial frequency spectrum. Multiple stages deepen the notches.

    Args:
        rate: Sweep speed in Hz (0.05-2.0).
        stages: Number of all-pass stages (2-12). More = deeper notches.
        depth: Sweep range (0.1-5.0). Higher = wider frequency sweep.
        feedback: Output→input feedback (0.0-0.8).
    """
    key = f"video_phaser_{seed}"
    prev = _phaser_state.get(key)

    f = frame.astype(np.float32)
    if prev is not None and feedback > 0:
        f = f * (1 - feedback) + prev * feedback

    result = np.zeros_like(f)
    for ch in range(3):
        channel = f[:, :, ch]
        freq = np.fft.fft(channel, axis=1)
        w = channel.shape[1]
        freqs = np.fft.fftfreq(w)
        sweep = np.sin(2 * np.pi * rate * frame_index / 30.0) * depth

        phase_shift = np.zeros(w)
        for stage in range(stages):
            center = 0.1 + (stage / max(stages, 1)) * 0.4 + sweep * 0.1
            notch = np.exp(-((np.abs(freqs) - center) ** 2) / (0.02 + stage * 0.01))
            phase_shift += notch * np.pi

        shifted = freq * np.exp(1j * phase_shift[np.newaxis, :])
        result[:, :, ch] = np.real(np.fft.ifft(shifted, axis=1))

    mixed = (frame.astype(np.float32) + result) / 2
    output = np.clip(mixed, 0, 255).astype(np.uint8)

    _phaser_state[key] = output.astype(np.float32)
    if frame_index >= total_frames - 1:
        _phaser_state.pop(key, None)

    return output


def spatial_flanger(
    frame: np.ndarray,
    rate: float = 0.8,
    depth: int = 20,
    feedback: float = 0.3,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Spatial flanger — each row mixed with horizontally-shifted copy.

    Per-row LFO with phase offset by vertical position creates diagonal
    sweep pattern. Like flanging in the spatial domain.

    Args:
        rate: LFO speed in Hz (0.1-3.0).
        depth: Max pixel shift per row (1-100).
        feedback: Frame-to-frame feedback (0.0-0.8).
    """
    key = f"spatial_flanger_{seed}"
    prev = _phaser_state.get(f"sf_{key}")

    f = frame.astype(np.float32)
    result = np.zeros_like(f)
    h, w = f.shape[:2]

    for y in range(h):
        lfo = np.sin(2 * np.pi * rate * frame_index / 30.0 + y * 0.02)
        shift = int(lfo * depth)
        shifted_row = np.roll(f[y], shift, axis=0)
        result[y] = (f[y] + shifted_row) / 2

    if prev is not None and feedback > 0:
        result = result * (1 - feedback) + prev * feedback

    _phaser_state[f"sf_{key}"] = result.copy()
    if frame_index >= total_frames - 1:
        _phaser_state.pop(f"sf_{key}", None)

    return np.clip(result, 0, 255).astype(np.uint8)


def channel_phaser(
    frame: np.ndarray,
    r_rate: float = 0.05,
    g_rate: float = 0.3,
    b_rate: float = 1.2,
    stages: int = 5,
    depth: float = 1.5,
    wet: float = 0.8,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Channel phaser — each RGB channel gets its own phase sweep rate.

    Creates color fringing and separation that moves at different speeds
    per channel. R crawls slow, G medium, B fast (or custom rates).

    Args:
        r_rate: Red channel sweep Hz (0.01-3.0).
        g_rate: Green channel sweep Hz (0.01-3.0).
        b_rate: Blue channel sweep Hz (0.01-3.0).
        stages: Notch stages per channel (2-10).
        depth: Sweep depth (0.1-5.0).
        wet: Dry/wet mix (0.0-1.0).
    """
    rates = [r_rate, g_rate, b_rate]
    result = np.zeros_like(frame, dtype=np.float32)

    for ch in range(3):
        channel = frame[:, :, ch].astype(np.float32)
        freq = np.fft.fft2(channel)
        h, w = channel.shape
        fy = np.fft.fftfreq(h)[:, np.newaxis]
        fx = np.fft.fftfreq(w)[np.newaxis, :]
        radius = np.sqrt(fx**2 + fy**2)

        sweep = np.sin(2 * np.pi * rates[ch] * frame_index / 30.0) * depth
        phase_shift = np.zeros_like(radius)
        for stage in range(stages):
            center = 0.02 + stage * 0.05 + sweep * 0.06
            ring = np.exp(-((radius - center)**2) / 0.002)
            phase_shift += ring * np.pi * 2.0

        freq = freq * np.exp(1j * phase_shift)
        result[:, :, ch] = np.real(np.fft.ifft2(freq))

    mixed = frame.astype(np.float32) * (1 - wet) + result * wet
    return np.clip(mixed, 0, 255).astype(np.uint8)


def brightness_phaser(
    frame: np.ndarray,
    rate: float = 0.25,
    bands: int = 6,
    depth: float = 0.3,
    strength: float = 0.8,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Brightness phaser — sweeping inversion bands through brightness levels.

    At certain brightness levels, pixels get inverted. The inversion bands
    sweep over time, creating a psychedelic solarization effect.

    Args:
        rate: Sweep speed in Hz (0.05-1.0). Lower = slower, more dramatic.
        bands: Number of inversion bands (2-16).
        depth: Sweep range (0.1-0.6).
        strength: Inversion strength (0.0-1.0). 1.0 = full inversion at bands.
    """
    f = frame.astype(np.float32)
    brightness = np.mean(f, axis=2, keepdims=True) / 255.0

    sweep = np.sin(2 * np.pi * rate * frame_index / 30.0) * depth
    transfer = brightness.copy()

    band_spacing = 0.9 / max(bands, 1)
    band_width = band_spacing * 0.4

    for band in range(bands):
        center = 0.05 + band * band_spacing + sweep
        mask = np.exp(-((brightness - center) ** 2) / (2 * band_width ** 2))
        transfer = transfer * (1 - mask * strength) + (1 - brightness) * mask * strength

    scale = np.where(brightness > 0.005, transfer / brightness, 1.0)
    return np.clip(f * scale, 0, 255).astype(np.uint8)


def hue_flanger(
    frame: np.ndarray,
    rate: float = 0.3,
    depth: float = 60.0,
    sat_depth: float = 0.0,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Hue flanger — blend with hue-rotated copy, rotation oscillates.

    Creates color interference in the hue domain. Optional saturation
    modulation adds a second dimension of color movement.

    Args:
        rate: LFO speed in Hz (0.05-2.0).
        depth: Max hue shift in degrees (10-180).
        sat_depth: Saturation modulation depth (0-255). 0 = no sat modulation.
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV).astype(np.float32)
    lfo = np.sin(2 * np.pi * rate * frame_index / 30.0)

    shifted_hsv = hsv.copy()
    shifted_hsv[:, :, 0] = (shifted_hsv[:, :, 0] + lfo * depth) % 180

    if sat_depth > 0:
        sat_lfo = np.sin(2 * np.pi * rate * 0.7 * frame_index / 30.0)
        shifted_hsv[:, :, 1] = np.clip(shifted_hsv[:, :, 1] + sat_lfo * sat_depth, 0, 255)

    blended = (hsv + shifted_hsv) / 2
    blended[:, :, 0] = blended[:, :, 0] % 180
    blended = np.clip(blended, 0, [180, 255, 255]).astype(np.uint8)
    return cv2.cvtColor(blended, cv2.COLOR_HSV2RGB)


def resonant_filter(
    frame: np.ndarray,
    rate: float = 0.2,
    q: float = 50.0,
    gain: float = 3.0,
    wet: float = 0.7,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Resonant filter sweep — high-Q bandpass scanning spatial frequencies.

    Like a synth resonant filter but on the image. A narrow frequency band
    gets boosted while everything else is attenuated. The band sweeps.

    Args:
        rate: Sweep speed in Hz (0.05-1.0).
        q: Filter quality/sharpness (5-300). Higher = narrower band.
        gain: Boost at resonant peak (1.0-10.0).
        wet: Dry/wet mix (0.0-1.0).
    """
    result = np.zeros_like(frame, dtype=np.float32)
    h, w = frame.shape[:2]
    fy = np.fft.fftfreq(h)[:, np.newaxis]
    fx = np.fft.fftfreq(w)[np.newaxis, :]
    radius = np.sqrt(fx**2 + fy**2)

    sweep_freq = 0.01 + (np.sin(2 * np.pi * rate * frame_index / 30.0) + 1) * 0.2
    bandpass = np.exp(-((radius - sweep_freq) ** 2) * q)
    filter_gain = (1.0 - bandpass) * 0.15 + bandpass * gain

    for ch in range(3):
        fft = np.fft.fft2(frame[:, :, ch].astype(np.float32))
        result[:, :, ch] = np.real(np.fft.ifft2(fft * filter_gain))

    mixed = frame.astype(np.float32) * (1 - wet) + result * wet
    return np.clip(mixed, 0, 255).astype(np.uint8)


def comb_filter(
    frame: np.ndarray,
    teeth: int = 7,
    spacing: int = 8,
    rate: float = 0.3,
    depth: float = 3.0,
    wet: float = 0.7,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Visual comb filter — multiple offset copies create interference.

    Like audio comb filtering: signal + delayed copies at harmonic intervals.
    Each "tooth" is a spatially-shifted copy, alternating add/subtract.

    Args:
        teeth: Number of comb teeth (2-20). More = denser pattern.
        spacing: Pixel spacing between teeth (2-25).
        rate: Rotation speed in Hz (0.05-1.0).
        depth: Offset oscillation depth (1-10).
        wet: Dry/wet mix (0.0-1.0).
    """
    f = frame.astype(np.float32)
    h, w = f.shape[:2]
    result = f * (1 - wet)

    for tooth in range(1, teeth + 1):
        delay_px = tooth * (spacing + int(np.sin(2 * np.pi * rate * frame_index / 30.0) * depth))
        angle = 2 * np.pi * rate * 0.3 * frame_index / 30.0 + tooth * 0.4
        dx = int(np.cos(angle) * delay_px)
        dy = int(np.sin(angle) * delay_px)

        M = np.float32([[1, 0, dx], [0, 1, dy]])
        shifted = cv2.warpAffine(f, M, (w, h), borderMode=cv2.BORDER_WRAP)

        sign = 1 if tooth % 2 == 0 else -1
        weight = wet * 0.15 / (tooth ** 0.5)
        result += shifted * weight * sign

    return np.clip(result, 0, 255).astype(np.uint8)


def feedback_phaser(
    frame: np.ndarray,
    rate: float = 0.3,
    stages: int = 6,
    feedback: float = 0.5,
    escalation: float = 0.01,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Feedback phaser — self-feeding 2D FFT phase sweep that escalates.

    Output feeds back into input across frames. Phase depth increases
    over time, building to self-oscillation. Like a phaser with
    the feedback knob past unity.

    Args:
        rate: Sweep speed in Hz (0.05-1.0).
        stages: Number of ring stages (2-10).
        feedback: Self-feed amount (0.0-0.95). Above 0.7 = self-oscillation.
        escalation: Depth increase per frame (0.0-0.05).
    """
    key = f"feedback_phaser_{seed}"
    prev = _feedback_phaser_state.get(key)

    f = frame.astype(np.float32)
    if prev is not None and feedback > 0:
        f = f * (1 - feedback) + prev * feedback

    result = np.zeros_like(f)
    h, w = f.shape[:2]
    fy = np.fft.fftfreq(h)[:, np.newaxis]
    fx = np.fft.fftfreq(w)[np.newaxis, :]
    radius = np.sqrt(fx**2 + fy**2)

    depth = min(5.0, 1.0 + frame_index * escalation)
    sweep = np.sin(2 * np.pi * rate * frame_index / 30.0) * depth

    for ch in range(3):
        freq = np.fft.fft2(f[:, :, ch])
        phase_shift = np.zeros_like(radius)
        for stage in range(stages):
            center = 0.03 + stage * 0.06 + sweep * 0.03
            ring = np.exp(-((radius - center)**2) / 0.002)
            phase_shift += ring * np.pi * 1.8
        freq = freq * np.exp(1j * phase_shift)
        result[:, :, ch] = np.real(np.fft.ifft2(freq))

    output = f * (1 - 0.75) + result * 0.75
    _feedback_phaser_state[key] = np.clip(output, 0, 255)

    if frame_index >= total_frames - 1:
        _feedback_phaser_state.pop(key, None)

    return np.clip(output, 0, 255).astype(np.uint8)


def spectral_freeze(
    frame: np.ndarray,
    interval: int = 30,
    blend_peak: float = 0.7,
    envelope_frames: int = 25,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Spectral freeze — capture frequency magnitude, impose on later frames.

    At intervals, freezes the spatial frequency structure. Then gradually
    blends that frozen spectrum onto subsequent frames. Previous scene's
    textures appear in current scene's content.

    Args:
        interval: Frames between freeze captures (10-90).
        blend_peak: Max blend of frozen spectrum (0.1-1.0).
        envelope_frames: Duration of freeze influence in frames (5-60).
    """
    key = f"spectral_freeze_{seed}"
    state = _spectral_freeze_state.get(key, {"frozen": None, "freeze_frame": -999})

    # Capture spectrum at intervals
    if frame_index % interval == 0:
        frozen = []
        for ch in range(3):
            frozen.append(np.abs(np.fft.fft2(frame[:, :, ch].astype(np.float32))))
        state["frozen"] = frozen
        state["freeze_frame"] = frame_index

    _spectral_freeze_state[key] = state

    if state["frozen"] is not None:
        frames_since = frame_index - state["freeze_frame"]
        if 0 < frames_since < envelope_frames:
            envelope = np.sin(np.pi * frames_since / envelope_frames) * blend_peak
            result = np.zeros_like(frame, dtype=np.float32)
            for ch in range(3):
                cur_fft = np.fft.fft2(frame[:, :, ch].astype(np.float32))
                mag = np.abs(cur_fft) * (1 - envelope) + state["frozen"][ch] * envelope
                result[:, :, ch] = np.real(np.fft.ifft2(mag * np.exp(1j * np.angle(cur_fft))))
            if frame_index >= total_frames - 1:
                _spectral_freeze_state.pop(key, None)
            return np.clip(result, 0, 255).astype(np.uint8)

    if frame_index >= total_frames - 1:
        _spectral_freeze_state.pop(key, None)

    return frame.copy()


def visual_reverb(
    frame: np.ndarray,
    rate: float = 0.15,
    depth: float = 0.5,
    ir_interval: int = 30,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Visual reverb — convolve frame with past frame as impulse response.

    Like audio reverb but for images. A previous frame acts as the "room" —
    its frequency structure colors everything that follows.

    Args:
        rate: Blend oscillation Hz (0.05-0.5).
        depth: Max convolution blend (0.1-0.8).
        ir_interval: Frames between IR updates (10-90).
    """
    key = f"visual_reverb_{seed}"
    state = _reverb_state.get(key, {"ir": None})

    # Update impulse response at intervals
    if frame_index % ir_interval == 0:
        state["ir"] = frame.copy()
    _reverb_state[key] = state

    if state["ir"] is not None:
        result = np.zeros_like(frame, dtype=np.float32)
        lfo = (np.sin(2 * np.pi * rate * frame_index / 30.0) + 1) / 2
        blend = depth * (0.5 + lfo * 0.5)

        for ch in range(3):
            cur_fft = np.fft.fft2(frame[:, :, ch].astype(np.float32))
            ir_fft = np.fft.fft2(state["ir"][:, :, ch].astype(np.float32))
            ir_norm = ir_fft / (np.abs(ir_fft) + 1e-6)
            convolved = cur_fft * (1 - blend) + (cur_fft * ir_norm) * blend
            result[:, :, ch] = np.real(np.fft.ifft2(convolved))

        if frame_index >= total_frames - 1:
            _reverb_state.pop(key, None)
        return np.clip(result, 0, 255).astype(np.uint8)

    if frame_index >= total_frames - 1:
        _reverb_state.pop(key, None)
    return frame.copy()


def freq_flanger(
    frame: np.ndarray,
    rate: float = 0.5,
    depth: int = 10,
    mag_blend: float = 0.4,
    phase_blend: float = 0.15,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """2D frequency flanger — blend FFT magnitude+phase with past frame.

    Full 2D FFT flanging: both the frequency magnitudes and phases
    blend with a delayed frame, creating spectral ghosting.

    Args:
        rate: LFO speed in Hz (0.05-2.0).
        depth: Max delay in frames (1-30).
        mag_blend: Magnitude blend amount (0.0-0.8).
        phase_blend: Phase blend amount (0.0-0.6). Higher = more ghostly.
    """
    key = f"freq_flanger_{seed}"
    if key not in _freq_flanger_state:
        _freq_flanger_state[key] = []
    buf = _freq_flanger_state[key]
    buf.append(frame.copy())
    if len(buf) > depth + 5:
        buf.pop(0)

    lfo = np.sin(2 * np.pi * rate * frame_index / 30.0)
    delay_frames = max(1, int((lfo + 1) / 2 * depth))
    past_idx = max(0, len(buf) - 1 - delay_frames)
    past = buf[past_idx]

    result = np.zeros_like(frame, dtype=np.float32)
    blend = mag_blend * (0.5 + lfo * 0.5)

    for ch in range(3):
        cur = np.fft.fft2(frame[:, :, ch].astype(np.float32))
        p = np.fft.fft2(past[:, :, ch].astype(np.float32))
        mag = np.abs(cur) * (1 - blend) + np.abs(p) * blend
        phase = np.angle(cur) * (1 - phase_blend) + np.angle(p) * phase_blend
        result[:, :, ch] = np.real(np.fft.ifft2(mag * np.exp(1j * phase)))

    if frame_index >= total_frames - 1:
        _freq_flanger_state.pop(key, None)

    return np.clip(result, 0, 255).astype(np.uint8)

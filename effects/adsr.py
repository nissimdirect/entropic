"""
Entropic — ADSR Envelope Engine

Universal envelope generator that any effect can use. Modulates
a 0-1 amplitude value over time, triggered by a signal crossing
a threshold — exactly like a synthesizer's amplitude envelope.

Usage:
    env = ADSREnvelope(attack=10, decay=5, sustain=0.6, release=20)
    for frame_index in range(total):
        level = env.process(signal_level, threshold=0.3)
        # level is 0.0 to 1.0 — multiply effect strength by this

The envelope can also be used as a standalone effect wrapper via
adsr_wrap(), which applies ADSR to ANY effect's output by blending
between the original and effected frame based on envelope level.
"""

import numpy as np


class ADSREnvelope:
    """ADSR envelope generator for video effects.

    Args:
        attack: Frames to ramp from 0 to peak (0=instant).
        decay: Frames to drop from peak to sustain level (0=instant).
        sustain: Steady-state level while triggered (0-1).
        release: Frames to fade to 0 after trigger drops (0=instant).
        retrigger: If True, restart attack on every new trigger.
                   If False, only trigger once until released.
    """

    def __init__(
        self,
        attack: float = 0,
        decay: float = 0,
        sustain: float = 1.0,
        release: float = 0,
        retrigger: bool = True,
    ):
        self.attack = max(0, attack)
        self.decay = max(0, decay)
        self.sustain = np.clip(sustain, 0, 1)
        self.release = max(0, release)
        self.retrigger = retrigger

        # State
        self.level = 0.0
        self.phase = "idle"  # idle, attack, decay, sustain, release
        self.was_triggered = False

    def process(self, signal: float, threshold: float = 0.5) -> float:
        """Advance envelope by one frame.

        Args:
            signal: Current signal level (0-1). Compared to threshold.
            threshold: Trigger point (0-1).

        Returns:
            Envelope level (0-1) for this frame.
        """
        triggered = signal > threshold

        # Detect edges
        if triggered and (not self.was_triggered or
                          (self.retrigger and self.phase == "release")):
            self.phase = "attack"

        if not triggered and self.was_triggered:
            if self.phase in ("attack", "decay", "sustain"):
                self.phase = "release"

        self.was_triggered = triggered

        # Advance phase
        if self.phase == "attack":
            if self.attack > 0:
                self.level = min(1.0, self.level + 1.0 / self.attack)
            else:
                self.level = 1.0
            if self.level >= 1.0:
                self.level = 1.0
                self.phase = "decay"

        elif self.phase == "decay":
            if self.decay > 0:
                self.level = max(self.sustain,
                                 self.level - (1.0 - self.sustain) / self.decay)
            else:
                self.level = self.sustain
            if self.level <= self.sustain:
                self.level = self.sustain
                self.phase = "sustain"

        elif self.phase == "sustain":
            self.level = self.sustain

        elif self.phase == "release":
            if self.release > 0:
                self.level = max(0.0, self.level - self.sustain / max(self.release, 1))
            else:
                self.level = 0.0
            if self.level <= 0:
                self.level = 0.0
                self.phase = "idle"

        else:  # idle
            self.level = 0.0

        return self.level

    def trigger_on(self):
        """Explicit MIDI note on — start attack phase.

        Use this for external triggering (MIDI, keyboard) instead of
        the signal-threshold approach in process().
        """
        self.phase = "attack"
        self.was_triggered = True

    def trigger_off(self):
        """Explicit MIDI note off — start release from current level.

        Only transitions to release if currently in attack/decay/sustain.
        """
        if self.phase in ("attack", "decay", "sustain"):
            self.phase = "release"
        self.was_triggered = False

    def advance(self) -> float:
        """Step envelope one frame. Returns level (0-1).

        Use after trigger_on()/trigger_off() for external triggering.
        Reuses the same phase machine as process() but without
        signal/threshold comparison.

        Returns:
            Envelope level (0-1) for this frame.
        """
        if self.phase == "attack":
            if self.attack > 0:
                self.level = min(1.0, self.level + 1.0 / self.attack)
            else:
                self.level = 1.0
            if self.level >= 1.0:
                self.level = 1.0
                self.phase = "decay"

        elif self.phase == "decay":
            if self.decay > 0:
                self.level = max(self.sustain,
                                 self.level - (1.0 - self.sustain) / self.decay)
            else:
                self.level = self.sustain
            if self.level <= self.sustain:
                self.level = self.sustain
                self.phase = "sustain"

        elif self.phase == "sustain":
            self.level = self.sustain

        elif self.phase == "release":
            if self.release > 0:
                self.level = max(0.0, self.level - self.sustain / max(self.release, 1))
            else:
                self.level = 0.0
            if self.level <= 0:
                self.level = 0.0
                self.phase = "idle"

        else:  # idle
            self.level = 0.0

        return self.level

    def reset(self):
        """Reset envelope to idle state."""
        self.level = 0.0
        self.phase = "idle"
        self.was_triggered = False


# ─── Module-level envelope registry ───
_envelopes = {}


def adsr_wrap(
    frame: np.ndarray,
    effect_fn,
    effect_params: dict,
    attack: float = 0,
    decay: float = 0,
    sustain: float = 1.0,
    release: float = 0,
    trigger_source: str = "brightness",
    trigger_threshold: float = 0.5,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Wrap ANY effect with ADSR envelope.

    Applies the effect at full strength, then blends between original
    and effected frame based on envelope level. When envelope is 0,
    you see the original. When 1, you see the full effect.

    Args:
        effect_fn: The effect function to wrap.
        effect_params: Parameters to pass to the effect.
        attack/decay/sustain/release: ADSR in frames.
        trigger_source: What signal triggers the envelope
                       ("brightness", "motion", "edges", "time", "lfo").
        trigger_threshold: Signal level to trigger envelope.
    """
    import cv2
    from effects.sidechain import _extract_sidechain_signal

    # Get or create envelope
    env_key = f"adsr_{seed}_{id(effect_fn)}"
    if env_key not in _envelopes:
        _envelopes[env_key] = ADSREnvelope(attack, decay, sustain, release)
    env = _envelopes[env_key]

    # Compute trigger signal
    if trigger_source == "time":
        # Trigger based on time position (pulse every N frames)
        period = max(15, int(30 / max(trigger_threshold, 0.1)))
        signal = 1.0 if (frame_index % period) < (period // 3) else 0.0
        threshold = 0.5
    elif trigger_source == "lfo":
        # LFO-driven trigger
        t = frame_index / 30.0
        signal = (np.sin(t * np.pi * 2 * trigger_threshold) + 1) / 2
        threshold = 0.5
    else:
        # Extract from frame content
        sig_map = _extract_sidechain_signal(frame, trigger_source)
        signal = float(np.mean(sig_map))
        threshold = trigger_threshold

    # Get envelope level
    level = env.process(signal, threshold)

    # Apply effect — only pass temporal params if the function accepts them
    params = dict(effect_params)
    import inspect
    try:
        sig = inspect.signature(effect_fn)
        fn_params = set(sig.parameters.keys())
    except (ValueError, TypeError):
        fn_params = set()
    if 'frame_index' in fn_params:
        params['frame_index'] = frame_index
    if 'total_frames' in fn_params:
        params['total_frames'] = total_frames
    if 'seed' in fn_params and 'seed' not in params:
        params['seed'] = seed
    effected = effect_fn(frame, **params)

    # Blend based on envelope
    if level <= 0:
        result = frame
    elif level >= 1:
        result = effected
    else:
        result = cv2.addWeighted(
            frame.astype(np.float32), 1.0 - level,
            effected.astype(np.float32), level,
            0,
        )

    # Cleanup
    if frame_index >= total_frames - 1:
        _envelopes.pop(env_key, None)

    return np.clip(result, 0, 255).astype(np.uint8)

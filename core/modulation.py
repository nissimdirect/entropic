"""
Entropic -- LFO Modulation Engine

Server-side deterministic LFO for rendered exports.
Client-side JS handles live preview (60fps via requestAnimationFrame).
This module computes frame-accurate modulated values for export/render.

Waveforms: sine, saw, square, triangle, ramp_up, ramp_down, noise, random, bin
"""

import math
import hashlib


def lfo_waveform(phase: float, waveform: str, seed: int = 42) -> float:
    """Compute LFO value (0.0 to 1.0) for a given phase and waveform.

    Args:
        phase: 0.0 to 1.0 (wraps automatically)
        waveform: One of the 9 supported waveform names
        seed: Random seed for noise/random waveforms (ensures determinism)

    Returns:
        float between 0.0 and 1.0
    """
    p = phase % 1.0

    if waveform == "sine":
        return 0.5 + 0.5 * math.sin(2 * math.pi * p)
    elif waveform == "saw":
        return p
    elif waveform == "square":
        return 1.0 if p < 0.5 else 0.0
    elif waveform == "triangle":
        return 2 * p if p < 0.5 else 2 * (1 - p)
    elif waveform == "ramp_up":
        return p
    elif waveform == "ramp_down":
        return 1.0 - p
    elif waveform == "noise":
        # Deterministic pseudo-noise based on phase quantized to 1/64
        bucket = int(p * 64)
        h = hashlib.md5(f"{seed}:{bucket}".encode()).hexdigest()
        return int(h[:8], 16) / 0xFFFFFFFF
    elif waveform == "random":
        # Step-and-hold: changes once per cycle quarter
        bucket = int(p * 4)
        h = hashlib.md5(f"{seed}:{bucket}".encode()).hexdigest()
        return int(h[:8], 16) / 0xFFFFFFFF
    elif waveform == "bin":
        # Binary: snaps to 0 or 1 based on sine threshold
        return 1.0 if math.sin(2 * math.pi * p) > 0 else 0.0
    else:
        return 0.5


class LfoModulator:
    """Applies LFO modulation to an effect chain for a specific frame.

    Config format:
        {
            "rate": 1.0,          # Hz (cycles per second), 0 = hold
            "depth": 0.5,         # 0.0 to 1.0
            "phase_offset": 0.0,  # 0.0 to 1.0
            "waveform": "sine",
            "seed": 42,
            "mappings": [
                {"effect_idx": 0, "param": "threshold", "base_value": 0.5,
                 "min": 0.0, "max": 1.0}
            ]
        }
    """

    def __init__(self, config: dict):
        self.rate = float(config.get("rate", 1.0))
        self.depth = float(config.get("depth", 0.5))
        self.phase_offset = float(config.get("phase_offset", 0.0))
        self.waveform = config.get("waveform", "sine")
        self.seed = int(config.get("seed", 42))
        self.mappings = config.get("mappings", [])

    def apply_to_chain(
        self, effects: list[dict], frame_index: int, fps: float
    ) -> list[dict]:
        """Return a new effects list with LFO-modulated parameter values.

        Does not mutate the input list.

        Args:
            effects: List of effect dicts [{"name": ..., "params": {...}}, ...]
            frame_index: Current frame number
            fps: Frames per second (for time calculation)

        Returns:
            New list of effect dicts with modulated params
        """
        if not self.mappings or self.depth == 0:
            return effects

        # Compute phase for this frame
        if self.rate == 0 or fps == 0:
            phase = self.phase_offset
        else:
            time_sec = frame_index / fps
            phase = (time_sec * self.rate + self.phase_offset) % 1.0

        lfo_val = lfo_waveform(phase, self.waveform, self.seed)
        bipolar = (lfo_val - 0.5) * 2.0  # -1.0 to 1.0

        # Deep copy effects list
        import copy
        new_effects = copy.deepcopy(effects)

        for mapping in self.mappings:
            idx = mapping.get("effect_idx")
            param_name = mapping.get("param")
            base = mapping.get("base_value", 0.5)
            p_min = mapping.get("min", 0.0)
            p_max = mapping.get("max", 1.0)

            # Skip invalid indices
            if idx is None or idx < 0 or idx >= len(new_effects):
                continue

            param_range = p_max - p_min
            modulated = base + bipolar * self.depth * param_range * 0.5
            clamped = max(p_min, min(p_max, modulated))

            if param_name in new_effects[idx].get("params", {}):
                orig = new_effects[idx]["params"][param_name]
                # Preserve original type: int params stay int (avoids
                # float→int crashes in effects like displacement/block_size)
                if isinstance(orig, int) and not isinstance(orig, bool):
                    clamped = int(round(clamped))
                new_effects[idx]["params"][param_name] = clamped

        return new_effects

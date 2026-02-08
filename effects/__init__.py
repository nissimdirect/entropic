"""
Entropic — Effects Registry
Auto-discovers effects and provides a uniform interface.
Every effect is a function: (frame: np.ndarray, **params) -> np.ndarray
"""

import numpy as np

from effects.pixelsort import pixelsort
from effects.channelshift import channelshift
from effects.scanlines import scanlines
from effects.bitcrush import bitcrush
from effects.color import (
    hue_shift,
    contrast_crush,
    saturation_warp,
    brightness_exposure,
    color_invert,
    color_temperature,
)
from effects.distortion import (
    wave_distort,
    displacement,
    mirror,
    chromatic_aberration,
)
from effects.texture import (
    vhs,
    noise,
    posterize,
    edge_detect,
    blur,
    sharpen,
)
from effects.temporal import stutter, frame_drop, time_stretch, feedback, tape_stop, tremolo, delay, decimator, sample_and_hold
from effects.modulation import ring_mod, gate
from effects.enhance import solarize, duotone, emboss, auto_levels, median_filter, false_color

# Master registry: name -> (function, default_params, description)
EFFECTS = {
    # === GLITCH ===
    "pixelsort": {
        "fn": pixelsort,
        "category": "glitch",
        "params": {"threshold": 0.5, "sort_by": "brightness", "direction": "horizontal"},
        "description": "Sort pixels by brightness, hue, or saturation",
    },
    "channelshift": {
        "fn": channelshift,
        "category": "glitch",
        "params": {"r_offset": (10, 0), "g_offset": (0, 0), "b_offset": (-10, 0)},
        "description": "Offset RGB channels independently",
    },
    "displacement": {
        "fn": displacement,
        "category": "glitch",
        "params": {"block_size": 16, "intensity": 10.0, "seed": 42},
        "description": "Randomly displace image blocks",
    },
    "bitcrush": {
        "fn": bitcrush,
        "category": "glitch",
        "params": {"color_depth": 4, "resolution_scale": 1.0},
        "description": "Reduce color depth and/or resolution",
    },

    # === DISTORTION ===
    "wave": {
        "fn": wave_distort,
        "category": "distortion",
        "params": {"amplitude": 10.0, "frequency": 0.05, "direction": "horizontal"},
        "description": "Sine wave displacement distortion",
    },
    "mirror": {
        "fn": mirror,
        "category": "distortion",
        "params": {"axis": "vertical", "position": 0.5},
        "description": "Mirror one half onto the other",
    },
    "chromatic": {
        "fn": chromatic_aberration,
        "category": "distortion",
        "params": {"offset": 5, "direction": "horizontal"},
        "description": "RGB channel split (lens aberration)",
    },

    # === TEXTURE ===
    "scanlines": {
        "fn": scanlines,
        "category": "texture",
        "params": {"line_width": 2, "opacity": 0.3, "flicker": False, "color": (0, 0, 0)},
        "description": "CRT/VHS scan line overlay",
    },
    "vhs": {
        "fn": vhs,
        "category": "texture",
        "params": {"tracking": 0.5, "noise_amount": 0.2, "color_bleed": 3, "seed": 42},
        "description": "VHS tape degradation simulation",
    },
    "noise": {
        "fn": noise,
        "category": "texture",
        "params": {"amount": 0.3, "noise_type": "gaussian", "seed": 42},
        "description": "Add grain/noise overlay",
    },
    "blur": {
        "fn": blur,
        "category": "texture",
        "params": {"radius": 3, "blur_type": "box"},
        "description": "Box or motion blur",
    },
    "sharpen": {
        "fn": sharpen,
        "category": "texture",
        "params": {"amount": 1.0},
        "description": "Sharpen/enhance edges",
    },
    "edges": {
        "fn": edge_detect,
        "category": "texture",
        "params": {"threshold": 0.3, "mode": "overlay"},
        "description": "Edge detection (overlay, neon, or edges-only)",
    },
    "posterize": {
        "fn": posterize,
        "category": "texture",
        "params": {"levels": 4},
        "description": "Reduce to N color levels per channel",
    },

    # === COLOR ===
    "hueshift": {
        "fn": hue_shift,
        "category": "color",
        "params": {"degrees": 180},
        "description": "Rotate the hue wheel",
    },
    "contrast": {
        "fn": contrast_crush,
        "category": "color",
        "params": {"amount": 50, "curve": "linear"},
        "description": "Extreme contrast manipulation",
    },
    "saturation": {
        "fn": saturation_warp,
        "category": "color",
        "params": {"amount": 1.5, "channel": "all"},
        "description": "Boost or kill saturation",
    },
    "exposure": {
        "fn": brightness_exposure,
        "category": "color",
        "params": {"stops": 1.0, "clip_mode": "clip"},
        "description": "Push exposure up or down",
    },
    "invert": {
        "fn": color_invert,
        "category": "color",
        "params": {"channel": "all", "amount": 1.0},
        "description": "Full or partial color inversion",
    },
    "temperature": {
        "fn": color_temperature,
        "category": "color",
        "params": {"temp": 30},
        "description": "Warm/cool color temperature shift",
    },

    # === TEMPORAL ===
    "stutter": {
        "fn": stutter,
        "category": "temporal",
        "params": {"repeat": 3, "interval": 8},
        "description": "Freeze-stutter: hold frames at intervals (skipping record)",
    },
    "dropout": {
        "fn": frame_drop,
        "category": "temporal",
        "params": {"drop_rate": 0.3, "seed": 42},
        "description": "Random frame drops to black (signal loss)",
    },
    "timestretch": {
        "fn": time_stretch,
        "category": "temporal",
        "params": {"speed": 0.5},
        "description": "Speed change with visual artifacts",
    },
    "feedback": {
        "fn": feedback,
        "category": "temporal",
        "params": {"decay": 0.3},
        "description": "Ghost trails from previous frames (video echo)",
    },
    "tapestop": {
        "fn": tape_stop,
        "category": "temporal",
        "params": {"trigger": 0.7, "ramp_frames": 15},
        "description": "Freeze and fade to black like a tape machine stopping",
    },
    "tremolo": {
        "fn": tremolo,
        "category": "temporal",
        "params": {"rate": 2.0, "depth": 0.5},
        "description": "Brightness oscillation over time (LFO on brightness)",
    },
    "delay": {
        "fn": delay,
        "category": "temporal",
        "params": {"delay_frames": 5, "decay": 0.4},
        "description": "Ghost echo from N frames ago (video delay line)",
    },
    "decimator": {
        "fn": decimator,
        "category": "temporal",
        "params": {"factor": 3},
        "description": "Reduce effective framerate (choppy lo-fi motion)",
    },
    "samplehold": {
        "fn": sample_and_hold,
        "category": "temporal",
        "params": {"hold_min": 4, "hold_max": 15, "seed": 42},
        "description": "Freeze at random intervals (sample & hold)",
    },

    # === MODULATION ===
    "ringmod": {
        "fn": ring_mod,
        "category": "modulation",
        "params": {"frequency": 4.0, "direction": "horizontal"},
        "description": "Sine wave carrier modulation (alternating bands)",
    },
    "gate": {
        "fn": gate,
        "category": "modulation",
        "params": {"threshold": 0.3, "mode": "brightness"},
        "description": "Black out pixels below brightness threshold (noise gate)",
    },

    # === ENHANCE ===
    "solarize": {
        "fn": solarize,
        "category": "enhance",
        "params": {"threshold": 128},
        "description": "Partial inversion above threshold (Sabattier/Man Ray effect)",
    },
    "duotone": {
        "fn": duotone,
        "category": "enhance",
        "params": {"shadow_color": (0, 0, 80), "highlight_color": (255, 200, 100)},
        "description": "Two-color gradient mapping (graphic design aesthetic)",
    },
    "emboss": {
        "fn": emboss,
        "category": "enhance",
        "params": {"amount": 1.0},
        "description": "3D raised/carved texture effect",
    },
    "autolevels": {
        "fn": auto_levels,
        "category": "enhance",
        "params": {"cutoff": 2.0},
        "description": "Auto-contrast histogram stretch (professional color correction)",
    },
    "median": {
        "fn": median_filter,
        "category": "enhance",
        "params": {"size": 5},
        "description": "Median filter (watercolor / noise reduction)",
    },
    "falsecolor": {
        "fn": false_color,
        "category": "enhance",
        "params": {"colormap": "jet"},
        "description": "Map luminance to false-color palette (thermal vision)",
    },
}

# Category display order and labels
CATEGORIES = {
    "glitch": "GLITCH",
    "distortion": "DISTORTION",
    "texture": "TEXTURE",
    "color": "COLOR",
    "temporal": "TEMPORAL",
    "modulation": "MODULATION",
    "enhance": "ENHANCE",
}


def get_effect(name: str):
    """Get an effect by name. Returns (fn, default_params)."""
    if name not in EFFECTS:
        available = ", ".join(sorted(EFFECTS.keys()))
        raise ValueError(f"Unknown effect: {name}. Available: {available}")
    entry = EFFECTS[name]
    return entry["fn"], entry["params"].copy()


def list_effects(category: str = None) -> list[dict]:
    """List all available effects with descriptions.

    Args:
        category: Optional filter — only return effects in this category.
    """
    results = []
    for name, entry in EFFECTS.items():
        if category and entry.get("category") != category:
            continue
        results.append({
            "name": name,
            "description": entry["description"],
            "params": entry["params"],
            "category": entry.get("category", "other"),
        })
    return results


def list_categories() -> list[str]:
    """Return ordered list of category keys."""
    return list(CATEGORIES.keys())


def search_effects(query: str) -> list[dict]:
    """Search effects by name or description substring."""
    query_lower = query.lower()
    results = []
    for name, entry in EFFECTS.items():
        if query_lower in name or query_lower in entry["description"].lower():
            results.append({
                "name": name,
                "description": entry["description"],
                "params": entry["params"],
                "category": entry.get("category", "other"),
            })
    return results


def apply_effect(frame, effect_name: str, frame_index: int = 0, total_frames: int = 1, **params):
    """Apply a named effect to a frame with given params.

    Special param `mix` (0.0-1.0): Dry/wet blend. 1.0 = fully processed (default),
    0.0 = original signal. Works like parallel processing in a DAW — the dry
    (original) and wet (processed) signals are blended together.
    """
    # Extract mix param before passing to effect function
    mix = float(params.pop("mix", 1.0))
    mix = max(0.0, min(1.0, mix))

    fn, defaults = get_effect(effect_name)
    merged = {**defaults, **params}

    # Inject temporal context for effects that need it
    import inspect
    sig = inspect.signature(fn)
    if "frame_index" in sig.parameters:
        merged["frame_index"] = frame_index
    if "total_frames" in sig.parameters:
        merged["total_frames"] = total_frames

    wet = fn(frame, **merged)

    # Dry/wet blend (parallel processing)
    if mix >= 1.0:
        return wet
    if mix <= 0.0:
        return frame.copy()

    # Linear blend: output = dry * (1 - mix) + wet * mix
    blended = (frame.astype(np.float32) * (1.0 - mix) + wet.astype(np.float32) * mix)
    return np.clip(blended, 0, 255).astype(np.uint8)


def apply_chain(frame, effects_list: list[dict], frame_index: int = 0, total_frames: int = 1):
    """Apply a chain of effects sequentially.

    effects_list: [{"name": "pixelsort", "params": {"threshold": 0.6}}, ...]
    """
    from core.safety import validate_chain_depth
    validate_chain_depth(effects_list)

    for effect in effects_list:
        name = effect["name"]
        params = effect.get("params", {})
        frame = apply_effect(frame, name, frame_index=frame_index, total_frames=total_frames, **params)
    return frame

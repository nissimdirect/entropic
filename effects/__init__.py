"""
Entropic — Effects Registry
Auto-discovers effects and provides a uniform interface.
Every effect is a function: (frame: np.ndarray, **params) -> np.ndarray
"""

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

# Master registry: name -> (function, default_params, description)
EFFECTS = {
    "pixelsort": {
        "fn": pixelsort,
        "params": {"threshold": 0.5, "sort_by": "brightness", "direction": "horizontal"},
        "description": "Sort pixels by brightness, hue, or saturation",
    },
    "channelshift": {
        "fn": channelshift,
        "params": {"r_offset": (10, 0), "g_offset": (0, 0), "b_offset": (-10, 0)},
        "description": "Offset RGB channels independently",
    },
    "scanlines": {
        "fn": scanlines,
        "params": {"line_width": 2, "opacity": 0.3, "flicker": False, "color": (0, 0, 0)},
        "description": "CRT/VHS scan line overlay",
    },
    "bitcrush": {
        "fn": bitcrush,
        "params": {"color_depth": 4, "resolution_scale": 1.0},
        "description": "Reduce color depth and/or resolution",
    },
    "hueshift": {
        "fn": hue_shift,
        "params": {"degrees": 180},
        "description": "Rotate the hue wheel",
    },
    "contrast": {
        "fn": contrast_crush,
        "params": {"amount": 50, "curve": "linear"},
        "description": "Extreme contrast manipulation",
    },
    "saturation": {
        "fn": saturation_warp,
        "params": {"amount": 1.5, "channel": "all"},
        "description": "Boost or kill saturation",
    },
    "exposure": {
        "fn": brightness_exposure,
        "params": {"stops": 1.0, "clip_mode": "clip"},
        "description": "Push exposure up or down",
    },
    "invert": {
        "fn": color_invert,
        "params": {"channel": "all", "amount": 1.0},
        "description": "Full or partial color inversion",
    },
    "temperature": {
        "fn": color_temperature,
        "params": {"temp": 30},
        "description": "Warm/cool color temperature shift",
    },
}


def get_effect(name: str):
    """Get an effect by name. Returns (fn, default_params)."""
    if name not in EFFECTS:
        available = ", ".join(sorted(EFFECTS.keys()))
        raise ValueError(f"Unknown effect: {name}. Available: {available}")
    entry = EFFECTS[name]
    return entry["fn"], entry["params"].copy()


def list_effects() -> list[dict]:
    """List all available effects with descriptions."""
    return [
        {"name": name, "description": entry["description"], "params": entry["params"]}
        for name, entry in EFFECTS.items()
    ]


def apply_effect(frame, effect_name: str, **params):
    """Apply a named effect to a frame with given params."""
    fn, defaults = get_effect(effect_name)
    merged = {**defaults, **params}
    return fn(frame, **merged)


def apply_chain(frame, effects_list: list[dict]):
    """Apply a chain of effects sequentially.

    effects_list: [{"name": "pixelsort", "params": {"threshold": 0.6}}, ...]
    """
    for effect in effects_list:
        name = effect["name"]
        params = effect.get("params", {})
        frame = apply_effect(frame, name, **params)
    return frame

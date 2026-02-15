"""
Comprehensive parameter rendering tests for ALL Entropic effects.

Auto-discovers effects and params from the EFFECTS registry.
Goal: No parameter value that the server offers should crash rendering.

Test matrix:
  - 115 effects × default params (must not crash)
  - Every numeric param × min value (must not crash)
  - Every numeric param × max value (must not crash)
  - Every boolean param × True/False (must not crash)
  - Every boundary mode × physics effects (must not crash)
  - Every string mode param × valid options (must not crash)

Written 2026-02-15 per user request:
  "We need to make sure that there are no parameter values that we offer
  on our plugins that will prevent the video from being rendered."
"""

import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from effects import apply_chain, EFFECTS
from effects.physics import _physics_state


# ─── Helpers ───


def make_frame(h=120, w=160):
    """Gradient + rectangle test frame (not blank)."""
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    for x in range(w):
        frame[:, x, 0] = int(255 * x / w)
    for y in range(h):
        frame[y, :, 1] = int(255 * y / h)
    frame[h // 4:3 * h // 4, w // 4:3 * w // 4, 2] = 200
    return frame


def render_effect(effect_name, param_overrides=None):
    """Render one frame of an effect. Returns (result, error_or_none)."""
    _physics_state.clear()
    frame = make_frame()
    params = dict(param_overrides) if param_overrides else {}
    chain = [{"name": effect_name, "params": params}]
    try:
        result = apply_chain(frame, chain, frame_index=0, total_frames=1)
        return result, None
    except Exception as e:
        return None, e


def server_range(param_name, default_value, explicit_ranges):
    """Replicate the server's auto-range logic for params without explicit ranges.

    This matches server.py list_effects() — if no param_ranges defined,
    server uses: float → max(v*4, 2.0), int → max(v*4, 10).
    """
    r = explicit_ranges.get(param_name, {})
    if isinstance(default_value, float):
        return {
            "min": r.get("min", 0.0),
            "max": r.get("max", max(default_value * 4, 2.0)),
            "step": r.get("step", 0.01),
        }
    elif isinstance(default_value, int) and not isinstance(default_value, bool):
        return {
            "min": r.get("min", 0),
            "max": r.get("max", max(default_value * 4, 10)),
            "step": r.get("step", 1),
        }
    return None


# ─── Dynamic Test Case Generation ───

# realdatamosh is a video-level effect (operates on full video files, not frames)
VIDEO_LEVEL_EFFECTS = {"realdatamosh"}
ALL_EFFECTS = sorted(k for k in EFFECTS.keys() if k not in VIDEO_LEVEL_EFFECTS)

# Known valid string options for key params (from source code inspection)
VALID_STRING_OPTIONS = {
    "boundary": ["clamp", "black", "wrap", "mirror"],
    "field_type": ["dipole", "quadrupole", "toroidal", "chaotic"],
    "blur_type": ["box", "gaussian", "median", "motion", "radial"],
    "noise_type": ["gaussian", "uniform", "salt_pepper"],
    "sort_by": ["brightness", "hue", "saturation"],
    "direction": ["horizontal", "vertical"],
    "mode": {
        "datamosh": ["melt", "bloom", "average"],
        "realdatamosh": ["splice", "pframe_extend", "freeze_through"],
        "edges": ["overlay", "replace"],
        "gate": ["brightness", "threshold"],
        "blockcorrupt": ["random", "gradient"],
        "channeldestroy": ["separate", "swap", "invert_self", "shift_self", "xor_channels"],
        "pixelannihilate": ["dissolve", "crush", "eliminate", "annihilate"],
        "luma_key": ["dark", "bright"],
        "sidechaincross": ["blend", "multiply", "replace"],
        "sidechainduck": ["brightness", "invert"],
        "sidechaingate": ["freeze", "replace"],
        "sidechaininterference": ["phase", "invert"],
        "sidechainpump": ["brightness", "invert"],
        "xorglitch": ["fixed", "random"],
    },
    "waveform": ["sine", "square", "triangle", "saw", "random"],
    "target": ["brightness", "blur", "displacement", "channelshift", "invert",
               "posterize", "glitch", "moire"],
    "color_mode": ["mono", "color"],
    "channel": ["all", "master", "red", "green", "blue"],
    "curve": ["linear", "s_curve", "hard"],
    "clip_mode": ["clip", "wrap", "mirror"],
    "shape": ["full", "circle", "bars_h", "bars_v", "grid"],
    "color": ["white", "black", "invert", "random"],
    "axis": ["horizontal", "vertical"],
    "charset": ["basic", "detailed"],
    "melt_source": ["top", "bottom"],
    "origin": ["center", "random"],
    "position": ["center", "random"],
    "replace_color": ["black", "transparent"],
    "channel_map": ["rgb_shift", "channel_swap"],
    "source": ["brightness", "color", "motion"],
    "interpolation": ["cubic", "linear"],
    "void_mode": ["black", "transparent", "mirror"],
    "target_hue": ["all", "red", "green", "blue", "cyan", "magenta", "yellow"],
    "effect": ["echo", "reverse", "shift"],
    "placement": ["random", "grid"],
    "replacement": ["black", "white", "noise"],
    "motion_pattern": ["static", "zoom", "pan"],
    "colormap": ["jet", "hot", "cool", "viridis", "plasma", "turbo"],
    "force_type": ["turbulence", "radial", "directional"],
    "pre_a": ["none", "edges", "blur", "invert"],
    "pre_b": ["none", "edges", "blur", "invert"],
    "blend_mode": ["normal", "multiply", "screen", "overlay", "add",
                   "difference", "soft_light"],
}


def _generate_numeric_boundary_cases():
    """Generate (effect_name, {param: value}, test_id) for every numeric param boundary."""
    cases = []
    for name in ALL_EFFECTS:
        entry = EFFECTS[name]
        params = entry.get("params", {})
        ranges = entry.get("param_ranges", {})

        for k, v in params.items():
            if isinstance(v, bool):
                continue
            if not isinstance(v, (int, float)):
                continue

            r = server_range(k, v, ranges)
            if r is None:
                continue

            # Test at min
            cases.append((name, {k: r["min"]}, f"{name}__{k}__min_{r['min']}"))
            # Test at max
            cases.append((name, {k: r["max"]}, f"{name}__{k}__max_{r['max']}"))

    return cases


def _generate_bool_cases():
    """Generate (effect_name, {param: value}, test_id) for every boolean param."""
    cases = []
    for name in ALL_EFFECTS:
        entry = EFFECTS[name]
        params = entry.get("params", {})

        for k, v in params.items():
            if not isinstance(v, bool):
                continue
            cases.append((name, {k: True}, f"{name}__{k}__true"))
            cases.append((name, {k: False}, f"{name}__{k}__false"))

    return cases


def _generate_string_cases():
    """Generate (effect_name, {param: value}, test_id) for string params with known options."""
    cases = []
    for name in ALL_EFFECTS:
        entry = EFFECTS[name]
        params = entry.get("params", {})

        for k, v in params.items():
            if not isinstance(v, str):
                continue

            # Get valid options for this param
            options = VALID_STRING_OPTIONS.get(k)
            if options is None:
                continue

            # "mode" has per-effect options
            if isinstance(options, dict):
                options = options.get(name, [v])

            for opt in options:
                cases.append((name, {k: opt}, f"{name}__{k}__{opt}"))

    return cases


NUMERIC_CASES = _generate_numeric_boundary_cases()
BOOL_CASES = _generate_bool_cases()
STRING_CASES = _generate_string_cases()


# ─── Fixtures ───


@pytest.fixture(autouse=True)
def clear_physics_state():
    _physics_state.clear()
    yield
    _physics_state.clear()


# ─── Test 1: Every effect renders at defaults ───


class TestAllEffectsRenderDefaults:
    """All 115 effects must produce valid output with default parameters."""

    @pytest.mark.parametrize("effect_name", ALL_EFFECTS)
    def test_renders_at_defaults(self, effect_name):
        result, err = render_effect(effect_name)
        assert err is None, f"{effect_name} crashed at defaults: {err}"
        assert result is not None, f"{effect_name} returned None"
        assert result.shape[:2] == (120, 160), f"{effect_name} spatial: {result.shape}"
        assert result.shape[2] in (3, 4), f"{effect_name} channels: {result.shape[2]}"
        assert result.dtype == np.uint8, f"{effect_name} dtype: {result.dtype}"


# ─── Test 2: Numeric params at min values ───


class TestNumericParamMin:
    """No numeric param at its minimum value should crash rendering."""

    @pytest.mark.parametrize(
        "effect_name, param_overrides, test_id",
        NUMERIC_CASES[::2],  # Even indices = min cases
        ids=[c[2] for c in NUMERIC_CASES[::2]],
    )
    def test_min_value(self, effect_name, param_overrides, test_id):
        result, err = render_effect(effect_name, param_overrides)
        assert err is None, f"{test_id} crashed: {err}"
        assert result is not None, f"{test_id} returned None"
        assert result.shape[:2] == (120, 160) and result.shape[2] in (3, 4), f"{test_id} shape: {result.shape}"
        assert result.dtype == np.uint8, f"{test_id} dtype: {result.dtype}"


# ─── Test 3: Numeric params at max values ───


class TestNumericParamMax:
    """No numeric param at its maximum value should crash rendering."""

    @pytest.mark.parametrize(
        "effect_name, param_overrides, test_id",
        NUMERIC_CASES[1::2],  # Odd indices = max cases
        ids=[c[2] for c in NUMERIC_CASES[1::2]],
    )
    def test_max_value(self, effect_name, param_overrides, test_id):
        result, err = render_effect(effect_name, param_overrides)
        assert err is None, f"{test_id} crashed: {err}"
        assert result is not None, f"{test_id} returned None"
        assert result.shape[:2] == (120, 160) and result.shape[2] in (3, 4), f"{test_id} shape: {result.shape}"
        assert result.dtype == np.uint8, f"{test_id} dtype: {result.dtype}"


# ─── Test 4: Boolean params ───


class TestBoolParams:
    """Every boolean param at True and False should render."""

    @pytest.mark.parametrize(
        "effect_name, param_overrides, test_id",
        BOOL_CASES,
        ids=[c[2] for c in BOOL_CASES],
    )
    def test_bool_value(self, effect_name, param_overrides, test_id):
        result, err = render_effect(effect_name, param_overrides)
        assert err is None, f"{test_id} crashed: {err}"
        assert result is not None, f"{test_id} returned None"
        assert result.shape[:2] == (120, 160), f"{test_id} spatial shape: {result.shape}"
        assert result.shape[2] in (3, 4), f"{test_id} channels: {result.shape[2]}"


# ─── Test 5: String/mode params ───


class TestStringParams:
    """Every valid string option for mode/boundary/type params should render."""

    @pytest.mark.parametrize(
        "effect_name, param_overrides, test_id",
        STRING_CASES,
        ids=[c[2] for c in STRING_CASES],
    )
    def test_string_value(self, effect_name, param_overrides, test_id):
        result, err = render_effect(effect_name, param_overrides)
        assert err is None, f"{test_id} crashed: {err}"
        assert result is not None, f"{test_id} returned None"
        assert result.shape[:2] == (120, 160) and result.shape[2] in (3, 4), f"{test_id} shape: {result.shape}"


# ─── Test 6: Multi-frame rendering (stateful effects) ───

STATEFUL_EFFECTS = [
    name for name in ALL_EFFECTS
    if name.startswith("pixel") or name in (
        "datamosh", "feedback", "stutter", "delay",
        "granulator", "beatrepeat", "samplehold",
        "smear", "realdatamosh", "spectralfreeze",
    )
]


class TestMultiFrameRendering:
    """Stateful effects must not crash across 5 frames of rendering."""

    @pytest.mark.parametrize("effect_name", STATEFUL_EFFECTS)
    def test_five_frames(self, effect_name):
        frame = make_frame()
        chain = [{"name": effect_name, "params": {}}]
        for i in range(5):
            result = apply_chain(frame.copy(), chain, frame_index=i, total_frames=5)
            assert result is not None, f"{effect_name} frame {i} returned None"
            assert result.shape == frame.shape, f"{effect_name} frame {i} shape mismatch"
            assert result.dtype == np.uint8, f"{effect_name} frame {i} dtype mismatch"


# ─── Test 7: Extreme numeric values (beyond server range) ───


class TestExtremeValues:
    """Effects should handle extreme values gracefully (clamp, not crash)."""

    @pytest.mark.parametrize("effect_name", ALL_EFFECTS)
    def test_all_params_zero(self, effect_name):
        """Setting all numeric params to 0 should not crash."""
        entry = EFFECTS[effect_name]
        params = entry.get("params", {})
        overrides = {}
        for k, v in params.items():
            if isinstance(v, bool):
                continue
            if isinstance(v, float):
                overrides[k] = 0.0
            elif isinstance(v, int):
                overrides[k] = 0
        if overrides:
            result, err = render_effect(effect_name, overrides)
            assert err is None, f"{effect_name} crashed with all-zero params: {err}"
            assert result is not None, f"{effect_name} returned None with all-zero params"
            assert result.shape[:2] == (120, 160) and result.shape[2] in (3, 4)

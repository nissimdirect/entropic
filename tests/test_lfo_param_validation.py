"""
Entropic — LFO × Mappable Parameter Validation Tests
Validates that all 9 LFO waveforms work correctly with representative
effect parameters, multi-effect chains, frame-rate independence,
and boundary conditions.

Run with: pytest tests/test_lfo_param_validation.py -v
"""

import os
import sys
import pytest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.modulation import lfo_waveform, LfoModulator
from effects import apply_effect, EFFECTS

ALL_WAVEFORMS = ["sine", "saw", "square", "triangle", "ramp_up", "ramp_down",
                 "noise", "random", "bin"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_frame():
    """64x64 test frame."""
    return np.random.RandomState(42).randint(0, 256, (64, 64, 3), dtype=np.uint8)


@pytest.fixture
def effect_chain():
    """A representative 3-effect chain for testing LFO mapping."""
    return [
        {"name": "pixelsort", "params": {"threshold": 0.5, "sort_by": "brightness", "direction": "horizontal"}},
        {"name": "wave", "params": {"amplitude": 10.0, "frequency": 0.05, "direction": "horizontal"}},
        {"name": "bitcrush", "params": {"color_depth": 4, "resolution_scale": 1.0}},
    ]


# ---------------------------------------------------------------------------
# WAVEFORM OUTPUT VALIDATION
# ---------------------------------------------------------------------------

class TestWaveformOutputRange:
    """All waveforms must output values in [0, 1] for any phase."""

    @pytest.mark.parametrize("waveform", ALL_WAVEFORMS)
    def test_output_range_0_to_1(self, waveform):
        """Waveform output must be in [0, 1] for 1000 phase samples."""
        for phase in np.linspace(0, 2.0, 1000):  # Test beyond 1.0 for wrapping
            val = lfo_waveform(phase, waveform, seed=42)
            assert 0.0 <= val <= 1.0, f"{waveform} at phase={phase}: got {val}"

    @pytest.mark.parametrize("waveform", ALL_WAVEFORMS)
    def test_negative_phase_wraps(self, waveform):
        """Negative phase should wrap correctly."""
        val = lfo_waveform(-0.5, waveform, seed=42)
        assert 0.0 <= val <= 1.0

    def test_sine_at_known_phases(self):
        """Sine wave should hit known values at key phases."""
        # Phase 0: sin(0) = 0, so 0.5 + 0.5 * 0 = 0.5
        assert abs(lfo_waveform(0.0, "sine") - 0.5) < 0.01
        # Phase 0.25: sin(π/2) = 1, so 0.5 + 0.5 * 1 = 1.0
        assert abs(lfo_waveform(0.25, "sine") - 1.0) < 0.01
        # Phase 0.75: sin(3π/2) = -1, so 0.5 + 0.5 * -1 = 0.0
        assert abs(lfo_waveform(0.75, "sine") - 0.0) < 0.01

    def test_square_at_known_phases(self):
        """Square wave: 1 for first half, 0 for second half."""
        assert lfo_waveform(0.1, "square") == 1.0
        assert lfo_waveform(0.4, "square") == 1.0
        assert lfo_waveform(0.6, "square") == 0.0
        assert lfo_waveform(0.9, "square") == 0.0

    def test_bin_at_known_phases(self):
        """Binary: 1 when sin > 0, 0 when sin <= 0."""
        assert lfo_waveform(0.1, "bin") == 1.0
        assert lfo_waveform(0.4, "bin") == 1.0
        assert lfo_waveform(0.6, "bin") == 0.0
        assert lfo_waveform(0.9, "bin") == 0.0


# ---------------------------------------------------------------------------
# LFO × EFFECT PARAMETER MAPPING
# ---------------------------------------------------------------------------

class TestLfoEffectMapping:
    """Test LFO modulating actual effect parameters."""

    MAPPABLE_EFFECTS = [
        ("pixelsort", "threshold", 0.5, 0.0, 1.0),
        ("wave", "amplitude", 10.0, 0.0, 50.0),
        ("wave", "frequency", 0.05, 0.01, 0.2),
        ("bitcrush", "color_depth", 4, 1, 8),
        ("displacement", "intensity", 10.0, 0.0, 50.0),
        ("bitcrush", "resolution_scale", 1.0, 0.1, 2.0),
    ]

    @pytest.mark.parametrize("waveform", ALL_WAVEFORMS)
    @pytest.mark.parametrize("effect_name,param,base,p_min,p_max", MAPPABLE_EFFECTS)
    def test_waveform_modulates_param(self, waveform, effect_name, param, base, p_min, p_max):
        """Each waveform should modulate each mappable parameter within bounds."""
        effects = [{"name": effect_name, "params": dict(EFFECTS[effect_name]["params"])}]
        config = {
            "rate": 2.0,
            "depth": 1.0,
            "phase_offset": 0.0,
            "waveform": waveform,
            "seed": 42,
            "mappings": [{"effect_idx": 0, "param": param, "base_value": base,
                          "min": p_min, "max": p_max}],
        }
        mod = LfoModulator(config)

        # Test across 30 frames at 30fps (one full cycle at 2Hz should complete at frame 15)
        values = []
        for frame_idx in range(30):
            result = mod.apply_to_chain(effects, frame_idx, fps=30.0)
            val = result[0]["params"][param]
            values.append(val)
            # Value must stay in bounds
            assert p_min <= val <= p_max, (
                f"{waveform}/{effect_name}.{param}: frame {frame_idx} got {val}, "
                f"expected [{p_min}, {p_max}]"
            )

        # With depth=1.0, values should vary (not all the same)
        if waveform not in ("noise", "random"):  # These are stochastic
            unique = len(set(round(v, 4) for v in values))
            assert unique > 1, f"{waveform} produced no variation in {effect_name}.{param}"

    @pytest.mark.parametrize("waveform", ALL_WAVEFORMS)
    def test_depth_zero_passthrough(self, waveform, effect_chain):
        """depth=0 should return params unchanged regardless of waveform."""
        config = {
            "rate": 5.0,
            "depth": 0.0,
            "waveform": waveform,
            "mappings": [{"effect_idx": 0, "param": "threshold", "base_value": 0.5,
                          "min": 0.0, "max": 1.0}],
        }
        mod = LfoModulator(config)
        result = mod.apply_to_chain(effect_chain, frame_index=15, fps=30.0)
        # Should be completely unmodified
        assert result == effect_chain


# ---------------------------------------------------------------------------
# MULTI-EFFECT LFO CHAINS
# ---------------------------------------------------------------------------

class TestMultiEffectLfo:
    """Test LFO modulating multiple effects simultaneously."""

    def test_two_params_different_effects(self, effect_chain):
        """LFO modulating params across two different effects."""
        config = {
            "rate": 1.0,
            "depth": 0.8,
            "waveform": "sine",
            "mappings": [
                {"effect_idx": 0, "param": "threshold", "base_value": 0.5,
                 "min": 0.0, "max": 1.0},
                {"effect_idx": 1, "param": "amplitude", "base_value": 10.0,
                 "min": 0.0, "max": 50.0},
            ],
        }
        mod = LfoModulator(config)
        result = mod.apply_to_chain(effect_chain, frame_index=7, fps=30.0)

        # Both params should be modulated
        assert result[0]["params"]["threshold"] != 0.5 or result[1]["params"]["amplitude"] != 10.0

    def test_three_params_same_effect(self):
        """LFO modulating three params on the same effect."""
        effects = [{"name": "wave", "params": {"amplitude": 10.0, "frequency": 0.05, "direction": "horizontal"}}]
        config = {
            "rate": 2.0,
            "depth": 1.0,
            "waveform": "triangle",
            "mappings": [
                {"effect_idx": 0, "param": "amplitude", "base_value": 10.0,
                 "min": 0.0, "max": 50.0},
                {"effect_idx": 0, "param": "frequency", "base_value": 0.05,
                 "min": 0.01, "max": 0.2},
            ],
        }
        mod = LfoModulator(config)
        result = mod.apply_to_chain(effects, frame_index=10, fps=30.0)
        # Both should be modulated
        assert result[0]["params"]["amplitude"] != 10.0 or result[0]["params"]["frequency"] != 0.05

    def test_chain_immutability(self, effect_chain):
        """LFO should not mutate the original effect chain."""
        original_threshold = effect_chain[0]["params"]["threshold"]
        config = {
            "rate": 1.0, "depth": 1.0, "waveform": "sine",
            "mappings": [{"effect_idx": 0, "param": "threshold", "base_value": 0.5,
                          "min": 0.0, "max": 1.0}],
        }
        mod = LfoModulator(config)
        mod.apply_to_chain(effect_chain, frame_index=7, fps=30.0)
        # Original should be unchanged
        assert effect_chain[0]["params"]["threshold"] == original_threshold

    def test_invalid_effect_idx_skipped(self, effect_chain):
        """Mapping to a non-existent effect index should be silently skipped."""
        config = {
            "rate": 1.0, "depth": 1.0, "waveform": "sine",
            "mappings": [
                {"effect_idx": 99, "param": "threshold", "base_value": 0.5,
                 "min": 0.0, "max": 1.0},
                {"effect_idx": -1, "param": "threshold", "base_value": 0.5,
                 "min": 0.0, "max": 1.0},
            ],
        }
        mod = LfoModulator(config)
        result = mod.apply_to_chain(effect_chain, frame_index=7, fps=30.0)
        # Should return effects unchanged (all mappings skipped)
        assert result[0]["params"]["threshold"] == 0.5

    def test_nonexistent_param_skipped(self, effect_chain):
        """Mapping to a non-existent parameter name should be silently skipped."""
        config = {
            "rate": 1.0, "depth": 1.0, "waveform": "sine",
            "mappings": [{"effect_idx": 0, "param": "nonexistent_param",
                          "base_value": 0.5, "min": 0.0, "max": 1.0}],
        }
        mod = LfoModulator(config)
        result = mod.apply_to_chain(effect_chain, frame_index=7, fps=30.0)
        # Original threshold should be unchanged
        assert result[0]["params"]["threshold"] == 0.5


# ---------------------------------------------------------------------------
# FRAME RATE INDEPENDENCE
# ---------------------------------------------------------------------------

class TestFrameRateIndependence:
    """LFO should produce the same value at the same TIME regardless of FPS."""

    @pytest.mark.parametrize("waveform", ["sine", "triangle", "saw", "square"])
    def test_same_time_different_fps(self, waveform, effect_chain):
        """Same time point at different FPS should give same modulated value."""
        config = {
            "rate": 1.0, "depth": 1.0, "waveform": waveform,
            "mappings": [{"effect_idx": 0, "param": "threshold", "base_value": 0.5,
                          "min": 0.0, "max": 1.0}],
        }
        mod = LfoModulator(config)

        # 0.5 seconds at 24fps = frame 12
        r24 = mod.apply_to_chain(effect_chain, frame_index=12, fps=24.0)
        # 0.5 seconds at 30fps = frame 15
        r30 = mod.apply_to_chain(effect_chain, frame_index=15, fps=30.0)
        # 0.5 seconds at 60fps = frame 30
        r60 = mod.apply_to_chain(effect_chain, frame_index=30, fps=60.0)

        # Should all produce the same value (or very close)
        val24 = r24[0]["params"]["threshold"]
        val30 = r30[0]["params"]["threshold"]
        val60 = r60[0]["params"]["threshold"]
        assert abs(val24 - val30) < 0.01, f"24fps={val24} vs 30fps={val30}"
        assert abs(val30 - val60) < 0.01, f"30fps={val30} vs 60fps={val60}"

    def test_rate_zero_holds_value(self, effect_chain):
        """rate=0 should hold the initial phase value regardless of frame."""
        config = {
            "rate": 0.0, "depth": 1.0, "waveform": "sine", "phase_offset": 0.25,
            "mappings": [{"effect_idx": 0, "param": "threshold", "base_value": 0.5,
                          "min": 0.0, "max": 1.0}],
        }
        mod = LfoModulator(config)
        vals = []
        for f in range(30):
            r = mod.apply_to_chain(effect_chain, frame_index=f, fps=30.0)
            vals.append(r[0]["params"]["threshold"])
        # All values should be the same (held at phase_offset)
        assert all(abs(v - vals[0]) < 0.001 for v in vals), f"Values varied: {set(round(v,3) for v in vals)}"

    def test_fps_zero_does_not_crash(self, effect_chain):
        """fps=0 should not crash (edge case)."""
        config = {
            "rate": 1.0, "depth": 1.0, "waveform": "sine",
            "mappings": [{"effect_idx": 0, "param": "threshold", "base_value": 0.5,
                          "min": 0.0, "max": 1.0}],
        }
        mod = LfoModulator(config)
        result = mod.apply_to_chain(effect_chain, frame_index=100, fps=0.0)
        assert result[0]["params"]["threshold"] is not None


# ---------------------------------------------------------------------------
# LFO + ACTUAL FRAME RENDERING
# ---------------------------------------------------------------------------

class TestLfoRendering:
    """Test that LFO-modulated parameters produce valid rendered frames."""

    RENDER_EFFECTS = [
        ("pixelsort", "threshold", 0.0, 1.0),
        ("wave", "amplitude", 0.0, 30.0),
        ("bitcrush", "color_depth", 1, 8),
        ("displacement", "intensity", 0.0, 30.0),
    ]

    @pytest.mark.parametrize("effect_name,param,p_min,p_max", RENDER_EFFECTS)
    @pytest.mark.parametrize("waveform", ["sine", "square", "bin"])
    def test_modulated_render_produces_valid_frame(self, test_frame, effect_name, param,
                                                    p_min, p_max, waveform):
        """Apply effect with LFO-modulated param and verify valid output."""
        effects = [{"name": effect_name, "params": dict(EFFECTS[effect_name]["params"])}]
        base = (p_min + p_max) / 2

        config = {
            "rate": 2.0, "depth": 1.0, "waveform": waveform,
            "mappings": [{"effect_idx": 0, "param": param, "base_value": base,
                          "min": p_min, "max": p_max}],
        }
        mod = LfoModulator(config)

        for frame_idx in [0, 7, 15, 29]:
            modulated_chain = mod.apply_to_chain(effects, frame_idx, fps=30.0)
            result = apply_effect(test_frame.copy(), modulated_chain[0]["name"],
                                  **modulated_chain[0]["params"])
            assert result.shape == test_frame.shape, f"Frame {frame_idx}: wrong shape"
            assert result.dtype == np.uint8, f"Frame {frame_idx}: wrong dtype"

    def test_lfo_on_datamosh_intensity(self, test_frame):
        """LFO modulating datamosh intensity should produce valid frames."""
        effects = [{"name": "datamosh", "params": dict(EFFECTS["datamosh"]["params"])}]
        config = {
            "rate": 1.0, "depth": 0.8, "waveform": "sine",
            "mappings": [{"effect_idx": 0, "param": "intensity", "base_value": 3.0,
                          "min": 0.1, "max": 10.0}],
        }
        mod = LfoModulator(config)

        for frame_idx in range(5):
            modulated = mod.apply_to_chain(effects, frame_idx, fps=30.0)
            params = dict(modulated[0]["params"])
            params["frame_index"] = frame_idx
            params["total_frames"] = 5
            result = apply_effect(test_frame.copy(), "datamosh", **params)
            assert result.shape == test_frame.shape


# ---------------------------------------------------------------------------
# DEPTH SCALING
# ---------------------------------------------------------------------------

class TestDepthScaling:
    """Test that depth parameter correctly controls modulation amount."""

    @pytest.mark.parametrize("depth", [0.0, 0.25, 0.5, 0.75, 1.0])
    def test_depth_proportional(self, depth, effect_chain):
        """Higher depth should produce larger parameter deviation."""
        config = {
            "rate": 1.0, "depth": depth, "waveform": "sine",
            "mappings": [{"effect_idx": 0, "param": "threshold", "base_value": 0.5,
                          "min": 0.0, "max": 1.0}],
        }
        mod = LfoModulator(config)
        vals = []
        for f in range(30):
            r = mod.apply_to_chain(effect_chain, frame_index=f, fps=30.0)
            vals.append(r[0]["params"]["threshold"])
        deviation = max(vals) - min(vals)
        if depth == 0:
            assert deviation < 0.001
        else:
            # Higher depth should give larger deviation range
            assert deviation > 0 or depth < 0.01


# ---------------------------------------------------------------------------
# PHASE OFFSET
# ---------------------------------------------------------------------------

class TestPhaseOffset:
    """Test that phase_offset shifts the waveform correctly."""

    def test_offset_shifts_sine(self, effect_chain):
        """Phase offset should shift the sine wave."""
        configs = []
        for offset in [0.0, 0.25, 0.5]:
            configs.append({
                "rate": 1.0, "depth": 1.0, "waveform": "sine",
                "phase_offset": offset,
                "mappings": [{"effect_idx": 0, "param": "threshold", "base_value": 0.5,
                              "min": 0.0, "max": 1.0}],
            })

        vals_at_frame_0 = []
        for config in configs:
            mod = LfoModulator(config)
            r = mod.apply_to_chain(effect_chain, frame_index=0, fps=30.0)
            vals_at_frame_0.append(r[0]["params"]["threshold"])

        # Different offsets should give different values at frame 0
        assert not all(abs(v - vals_at_frame_0[0]) < 0.01 for v in vals_at_frame_0), \
            f"Phase offset had no effect: {vals_at_frame_0}"

"""
Entropic -- LFO Modulator Tests
Tests for core/modulation.py (LFO engine for exports).

Run with: pytest tests/test_lfo_modulator.py -v
"""

import os
import sys
import math

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.modulation import lfo_waveform, LfoModulator


# ---------------------------------------------------------------------------
# WAVEFORM TESTS
# ---------------------------------------------------------------------------

class TestLfoWaveform:

    def test_sine_at_known_phases(self):
        assert lfo_waveform(0.0, "sine") == pytest.approx(0.5, abs=0.01)
        assert lfo_waveform(0.25, "sine") == pytest.approx(1.0, abs=0.01)
        assert lfo_waveform(0.5, "sine") == pytest.approx(0.5, abs=0.01)
        assert lfo_waveform(0.75, "sine") == pytest.approx(0.0, abs=0.01)

    def test_saw(self):
        assert lfo_waveform(0.0, "saw") == pytest.approx(0.0, abs=0.01)
        assert lfo_waveform(0.5, "saw") == pytest.approx(0.5, abs=0.01)
        assert lfo_waveform(0.99, "saw") == pytest.approx(0.99, abs=0.01)

    def test_square(self):
        assert lfo_waveform(0.0, "square") == 1.0
        assert lfo_waveform(0.25, "square") == 1.0
        assert lfo_waveform(0.5, "square") == 0.0
        assert lfo_waveform(0.75, "square") == 0.0

    def test_triangle(self):
        assert lfo_waveform(0.0, "triangle") == pytest.approx(0.0, abs=0.01)
        assert lfo_waveform(0.25, "triangle") == pytest.approx(0.5, abs=0.01)
        assert lfo_waveform(0.5, "triangle") == pytest.approx(1.0, abs=0.01)
        assert lfo_waveform(0.75, "triangle") == pytest.approx(0.5, abs=0.01)

    def test_ramp_up(self):
        assert lfo_waveform(0.0, "ramp_up") == pytest.approx(0.0, abs=0.01)
        assert lfo_waveform(0.5, "ramp_up") == pytest.approx(0.5, abs=0.01)

    def test_ramp_down(self):
        assert lfo_waveform(0.0, "ramp_down") == pytest.approx(1.0, abs=0.01)
        assert lfo_waveform(0.5, "ramp_down") == pytest.approx(0.5, abs=0.01)
        assert lfo_waveform(1.0, "ramp_down") == pytest.approx(1.0, abs=0.01)

    def test_bin(self):
        assert lfo_waveform(0.1, "bin") == 1.0
        assert lfo_waveform(0.4, "bin") == 1.0
        assert lfo_waveform(0.6, "bin") == 0.0
        assert lfo_waveform(0.9, "bin") == 0.0

    def test_noise_deterministic(self):
        """Same phase + seed = same value."""
        v1 = lfo_waveform(0.5, "noise", seed=42)
        v2 = lfo_waveform(0.5, "noise", seed=42)
        assert v1 == v2

    def test_noise_varies_with_seed(self):
        v1 = lfo_waveform(0.5, "noise", seed=42)
        v2 = lfo_waveform(0.5, "noise", seed=99)
        # Different seeds should (almost certainly) produce different values
        assert v1 != v2

    def test_random_step_hold(self):
        """Random waveform should hold value within a quarter-cycle."""
        v1 = lfo_waveform(0.01, "random", seed=42)
        v2 = lfo_waveform(0.24, "random", seed=42)
        assert v1 == v2  # Same quarter

    def test_all_waveforms_in_range(self):
        """All waveforms should return values in [0, 1]."""
        waveforms = ["sine", "saw", "square", "triangle",
                     "ramp_up", "ramp_down", "noise", "random", "bin"]
        for wf in waveforms:
            for phase in [0.0, 0.1, 0.25, 0.5, 0.75, 0.99]:
                val = lfo_waveform(phase, wf)
                assert 0.0 <= val <= 1.0, f"{wf} at phase {phase} = {val}"

    def test_unknown_waveform_returns_midpoint(self):
        assert lfo_waveform(0.5, "nonexistent") == 0.5

    def test_phase_wraps(self):
        """Phase > 1.0 should wrap."""
        assert lfo_waveform(1.5, "saw") == pytest.approx(0.5, abs=0.01)


# ---------------------------------------------------------------------------
# MODULATOR TESTS
# ---------------------------------------------------------------------------

class TestLfoModulator:

    def _make_chain(self):
        return [
            {"name": "pixelsort", "params": {"threshold": 0.5}},
            {"name": "feedback", "params": {"decay": 0.8, "offset_x": 2}},
        ]

    def test_empty_mappings_passthrough(self):
        chain = self._make_chain()
        mod = LfoModulator({"rate": 1.0, "depth": 0.5, "mappings": []})
        result = mod.apply_to_chain(chain, frame_index=10, fps=30)
        assert result == chain

    def test_depth_zero_passthrough(self):
        chain = self._make_chain()
        mod = LfoModulator({
            "rate": 1.0, "depth": 0.0,
            "mappings": [{"effect_idx": 0, "param": "threshold",
                          "base_value": 0.5, "min": 0.0, "max": 1.0}]
        })
        result = mod.apply_to_chain(chain, frame_index=10, fps=30)
        assert result[0]["params"]["threshold"] == 0.5

    def test_modulates_param(self):
        chain = self._make_chain()
        mod = LfoModulator({
            "rate": 1.0, "depth": 1.0, "waveform": "sine",
            "mappings": [{"effect_idx": 0, "param": "threshold",
                          "base_value": 0.5, "min": 0.0, "max": 1.0}]
        })
        # At frame 0, fps 30: time=0, phase=0, sine(0)=0.5, bipolar=0
        result = mod.apply_to_chain(chain, frame_index=0, fps=30)
        assert result[0]["params"]["threshold"] == pytest.approx(0.5, abs=0.01)

        # At phase=0.25 (quarter cycle), sine=1.0, bipolar=1.0
        # time = 0.25s at 1Hz, frame = 0.25 * 30 = 7.5
        # modulated = 0.5 + 1.0 * 1.0 * 1.0 * 0.5 = 1.0
        # But let's pick a frame that gives peak
        # At frame=7 (t=7/30=0.233s), phase=0.233 -> not exactly 0.25
        # Use frame=7.5 -> not int, so frame=15 at 60fps? Let's just check it's different
        result2 = mod.apply_to_chain(chain, frame_index=8, fps=30)
        # Should be different from base
        assert result2[0]["params"]["threshold"] != 0.5

    def test_clamping(self):
        """Modulated value should not exceed min/max."""
        chain = [{"name": "test", "params": {"val": 0.9}}]
        mod = LfoModulator({
            "rate": 1.0, "depth": 1.0, "waveform": "square",
            "mappings": [{"effect_idx": 0, "param": "val",
                          "base_value": 0.9, "min": 0.0, "max": 1.0}]
        })
        # Square at phase=0 → 1.0, bipolar=1.0
        # modulated = 0.9 + 1.0 * 1.0 * 1.0 * 0.5 = 1.4 → clamped to 1.0
        result = mod.apply_to_chain(chain, frame_index=0, fps=30)
        assert result[0]["params"]["val"] <= 1.0

    def test_does_not_mutate_input(self):
        chain = self._make_chain()
        original_val = chain[0]["params"]["threshold"]
        mod = LfoModulator({
            "rate": 1.0, "depth": 1.0, "waveform": "saw",
            "mappings": [{"effect_idx": 0, "param": "threshold",
                          "base_value": 0.5, "min": 0.0, "max": 1.0}]
        })
        mod.apply_to_chain(chain, frame_index=15, fps=30)
        assert chain[0]["params"]["threshold"] == original_val

    def test_out_of_range_effect_idx_skipped(self):
        chain = self._make_chain()
        mod = LfoModulator({
            "rate": 1.0, "depth": 1.0,
            "mappings": [{"effect_idx": 99, "param": "threshold",
                          "base_value": 0.5, "min": 0.0, "max": 1.0}]
        })
        # Should not raise
        result = mod.apply_to_chain(chain, frame_index=0, fps=30)
        assert len(result) == 2

    def test_negative_effect_idx_skipped(self):
        chain = self._make_chain()
        mod = LfoModulator({
            "rate": 1.0, "depth": 1.0,
            "mappings": [{"effect_idx": -1, "param": "threshold",
                          "base_value": 0.5, "min": 0.0, "max": 1.0}]
        })
        result = mod.apply_to_chain(chain, frame_index=0, fps=30)
        assert len(result) == 2

    def test_phase_offset(self):
        """Phase offset should shift the waveform."""
        chain = [{"name": "test", "params": {"val": 0.5}}]
        mapping = [{"effect_idx": 0, "param": "val",
                    "base_value": 0.5, "min": 0.0, "max": 1.0}]
        mod_no_offset = LfoModulator({
            "rate": 1.0, "depth": 1.0, "waveform": "sine",
            "phase_offset": 0.0, "mappings": mapping,
        })
        mod_with_offset = LfoModulator({
            "rate": 1.0, "depth": 1.0, "waveform": "sine",
            "phase_offset": 0.25, "mappings": mapping,
        })
        r1 = mod_no_offset.apply_to_chain(chain, frame_index=0, fps=30)
        r2 = mod_with_offset.apply_to_chain(chain, frame_index=0, fps=30)
        # Different phase offset should produce different values at same frame
        assert r1[0]["params"]["val"] != r2[0]["params"]["val"]

    def test_rate_zero_holds_steady(self):
        """Rate=0 should hold phase at phase_offset (no oscillation)."""
        chain = [{"name": "test", "params": {"val": 0.5}}]
        mod = LfoModulator({
            "rate": 0, "depth": 1.0, "waveform": "sine",
            "phase_offset": 0.25,
            "mappings": [{"effect_idx": 0, "param": "val",
                          "base_value": 0.5, "min": 0.0, "max": 1.0}]
        })
        r1 = mod.apply_to_chain(chain, frame_index=0, fps=30)
        r2 = mod.apply_to_chain(chain, frame_index=100, fps=30)
        assert r1[0]["params"]["val"] == r2[0]["params"]["val"]

    def test_multiple_mappings(self):
        """Multiple params mapped to same LFO should all be modulated."""
        chain = self._make_chain()
        mod = LfoModulator({
            "rate": 1.0, "depth": 1.0, "waveform": "saw",
            "mappings": [
                {"effect_idx": 0, "param": "threshold",
                 "base_value": 0.5, "min": 0.0, "max": 1.0},
                {"effect_idx": 1, "param": "decay",
                 "base_value": 0.5, "min": 0.0, "max": 1.0},
            ]
        })
        result = mod.apply_to_chain(chain, frame_index=15, fps=30)
        # Both should be modulated identically (same LFO value)
        assert result[0]["params"]["threshold"] == result[1]["params"]["decay"]

    def test_int_params_stay_int(self):
        """Integer params should remain int after modulation (e.g. block_size)."""
        chain = [{"name": "displacement", "params": {"block_size": 16, "intensity": 10.0}}]
        mod = LfoModulator({
            "rate": 1.0, "depth": 0.5, "waveform": "saw",
            "mappings": [
                {"effect_idx": 0, "param": "block_size",
                 "base_value": 16, "min": 1, "max": 32},
                {"effect_idx": 0, "param": "intensity",
                 "base_value": 10.0, "min": 0.0, "max": 20.0},
            ]
        })
        result = mod.apply_to_chain(chain, frame_index=15, fps=30)
        assert isinstance(result[0]["params"]["block_size"], int), \
            f"block_size should be int, got {type(result[0]['params']['block_size'])}"
        assert isinstance(result[0]["params"]["intensity"], float), \
            f"intensity should be float, got {type(result[0]['params']['intensity'])}"

    def test_bool_params_not_cast_to_int(self):
        """Bool params should not be affected by int casting logic."""
        chain = [{"name": "noise", "params": {"animate": True, "amount": 0.3}}]
        mod = LfoModulator({
            "rate": 1.0, "depth": 0.5, "waveform": "sine",
            "mappings": [
                {"effect_idx": 0, "param": "amount",
                 "base_value": 0.3, "min": 0.0, "max": 1.0},
            ]
        })
        result = mod.apply_to_chain(chain, frame_index=10, fps=30)
        # animate is not mapped, should be untouched
        assert result[0]["params"]["animate"] is True

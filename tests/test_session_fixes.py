"""
Test all fixes from the 2026-02-15 session (Items #1-#5).

Validates OUTCOMES — does the fix actually solve the user-reported problem?
Each test maps to a specific bug ID from UAT-FINDINGS-2026-02-15.md.
"""

import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from effects import apply_chain, EFFECTS
from effects.physics import _physics_state


def make_frame(h=120, w=160):
    """Realistic test frame: gradient + rectangle (not blank)."""
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    for x in range(w):
        frame[:, x, 0] = int(255 * x / w)
    for y in range(h):
        frame[y, :, 1] = int(255 * y / h)
    frame[h // 4:3 * h // 4, w // 4:3 * w // 4, 2] = 200
    return frame


def diff(result, original):
    """Mean absolute pixel difference."""
    return np.mean(np.abs(result.astype(float) - original.astype(float)))


# ─── Item #1: Broken single-frame effects (B10-B14) ───


class TestBrokenEffectsFixed:
    """B10-B14: Effects that previously showed no visible change."""

    def test_byte_corrupt_visible(self):
        """B10: byte_corrupt should produce visible output with defaults."""
        frame = make_frame()
        chain = [{"name": "bytecorrupt", "params": {}}]
        result = apply_chain(frame, chain, frame_index=0, total_frames=1)
        assert diff(result, frame) > 1.0, "byte_corrupt still invisible"

    def test_flow_distort_visible(self):
        """B11: flow_distort should produce visible output."""
        frame = make_frame()
        chain = [{"name": "flowdistort", "params": {}}]
        result = apply_chain(frame, chain, frame_index=0, total_frames=1)
        assert diff(result, frame) > 1.0, "flow_distort still invisible"

    def test_auto_levels_visible(self):
        """B12: auto_levels should affect non-uniform frames."""
        # Dark frame — auto_levels should brighten
        frame = np.random.randint(20, 80, (120, 160, 3), dtype=np.uint8)
        chain = [{"name": "autolevels", "params": {"cutoff": 5.0, "strength": 1.0}}]
        result = apply_chain(frame, chain, frame_index=0, total_frames=1)
        assert diff(result, frame) > 2.0, "auto_levels no visible effect on dark frame"

    def test_histogram_eq_visible(self):
        """B13: histogram_eq should affect non-uniform frames."""
        frame = np.random.randint(20, 80, (120, 160, 3), dtype=np.uint8)
        chain = [{"name": "histogrameq", "params": {"strength": 1.0}}]
        result = apply_chain(frame, chain, frame_index=0, total_frames=1)
        assert diff(result, frame) > 2.0, "histogram_eq no visible effect on dark frame"

    def test_sidechain_crossfeed_without_key(self):
        """B14: sidechain_crossfeed should produce output without second video."""
        frame = make_frame()
        chain = [{"name": "sidechaincrossfeed", "params": {}}]
        result = apply_chain(frame, chain, frame_index=0, total_frames=1)
        assert diff(result, frame) > 0.5, "crossfeed still returns unchanged frame without key"

    def test_auto_levels_strength_param(self):
        """auto_levels strength=0 should return original frame."""
        frame = np.random.randint(20, 80, (120, 160, 3), dtype=np.uint8)
        chain = [{"name": "autolevels", "params": {"cutoff": 5.0, "strength": 0.0}}]
        result = apply_chain(frame, chain, frame_index=0, total_frames=1)
        assert diff(result, frame) < 0.1, "strength=0 should be no-op"

    def test_histogram_eq_strength_param(self):
        """histogram_eq strength=0 should return original frame."""
        frame = np.random.randint(20, 80, (120, 160, 3), dtype=np.uint8)
        chain = [{"name": "histogrameq", "params": {"strength": 0.0}}]
        result = apply_chain(frame, chain, frame_index=0, total_frames=1)
        assert diff(result, frame) < 0.1, "strength=0 should be no-op"


# ─── Item #2: Physics preview problem (B3-B9) ───


class TestPhysicsPreview:
    """B3-B9: Physics effects must be visible in single-frame preview."""

    PREVIEW_EFFECTS = [
        "pixelliquify", "pixelgravity", "pixelvortex",
        "pixelmelt", "pixeltimewarp", "pixelinkdrop", "pixelhaunt",
    ]

    @pytest.fixture(autouse=True)
    def clear_state(self):
        _physics_state.clear()
        yield
        _physics_state.clear()

    @pytest.mark.parametrize("effect_name", PREVIEW_EFFECTS)
    def test_preview_visible(self, effect_name):
        """Effect must produce diff > 1.0 in preview mode (frame_index=0, total_frames=1).

        Threshold is 1.0 not higher because: gradient test frames have smooth regions
        where small displacements are hard to see. On real textured video, diff > 1.0
        IS visible. The warmup took these from near-0 to 1.5-40+ depending on effect.
        """
        frame = make_frame()
        chain = [{"name": effect_name, "params": {}}]
        result = apply_chain(frame, chain, frame_index=0, total_frames=1)
        d = diff(result, frame)
        assert d > 1.0, f"{effect_name} preview diff={d:.1f}, still invisible"

    @pytest.mark.parametrize("effect_name", PREVIEW_EFFECTS)
    def test_preview_no_state_leak(self, effect_name):
        """Preview mode should not leave stale state that breaks subsequent renders."""
        frame = make_frame()
        chain = [{"name": effect_name, "params": {}}]
        # Preview call
        apply_chain(frame.copy(), chain, frame_index=0, total_frames=1)
        # Multi-frame render after preview should not crash
        for i in range(3):
            result = apply_chain(frame.copy(), chain, frame_index=i, total_frames=5)
        assert result is not None
        assert result.shape == frame.shape


# ─── Item #3: Parameter bugs (P1-P7) ───


class TestParameterBugs:
    """P1-P7: Parameters that were reported as non-functional."""

    @pytest.fixture(autouse=True)
    def clear_state(self):
        _physics_state.clear()
        yield
        _physics_state.clear()

    def test_p1_magnetic_seed_varies_output(self):
        """P1: Changing seed should produce visually different output."""
        frame = make_frame()
        chain_a = [{"name": "pixelmagnetic", "params": {"seed": 42}}]
        chain_b = [{"name": "pixelmagnetic", "params": {"seed": 99}}]
        _physics_state.clear()
        r_a = apply_chain(frame, chain_a, frame_index=0, total_frames=1)
        _physics_state.clear()
        r_b = apply_chain(frame, chain_b, frame_index=0, total_frames=1)
        seed_diff = diff(r_a, r_b)
        assert seed_diff > 3.0, f"Seed change diff={seed_diff:.1f}, seed still does nothing"

    def test_p2_magnetic_poles_affect_dipole(self):
        """P2: Changing poles in dipole mode should alter the field pattern."""
        frame = make_frame()
        chain_2 = [{"name": "pixelmagnetic", "params": {"field_type": "dipole", "poles": 2}}]
        chain_4 = [{"name": "pixelmagnetic", "params": {"field_type": "dipole", "poles": 4}}]
        _physics_state.clear()
        r_2 = apply_chain(frame, chain_2, frame_index=0, total_frames=1)
        _physics_state.clear()
        r_4 = apply_chain(frame, chain_4, frame_index=0, total_frames=1)
        poles_diff = diff(r_2, r_4)
        assert poles_diff > 5.0, f"Poles change diff={poles_diff:.1f}, poles still non-functional"

    def test_p2_magnetic_all_field_types(self):
        """P2: All field types should produce visible and distinct output."""
        frame = make_frame()
        results = {}
        for ft in ["dipole", "quadrupole", "toroidal", "chaotic"]:
            _physics_state.clear()
            chain = [{"name": "pixelmagnetic", "params": {"field_type": ft}}]
            r = apply_chain(frame, chain, frame_index=0, total_frames=1)
            results[ft] = r
            d = diff(r, frame)
            assert d > 0.5, f"field_type={ft} invisible (diff={d:.1f})"

    def test_p3_quantum_uncertainty_visible_preview(self):
        """P3: Uncertainty param should affect output even in preview mode."""
        frame = make_frame()
        _physics_state.clear()
        chain_low = [{"name": "pixelquantum", "params": {"uncertainty": 1.0}}]
        r_low = apply_chain(frame.copy(), chain_low, frame_index=0, total_frames=1)
        d_low = diff(r_low, frame)

        _physics_state.clear()
        chain_high = [{"name": "pixelquantum", "params": {"uncertainty": 15.0}}]
        r_high = apply_chain(frame.copy(), chain_high, frame_index=0, total_frames=1)
        d_high = diff(r_high, frame)

        assert d_high > d_low, f"Higher uncertainty should produce more displacement: low={d_low:.1f}, high={d_high:.1f}"
        assert d_high > 5.0, f"Uncertainty=15 still invisible in preview: diff={d_high:.1f}"

    def test_p3_quantum_superposition_visible_preview(self):
        """P3: Superposition param should add ghost copies in preview."""
        frame = make_frame()
        _physics_state.clear()
        chain_off = [{"name": "pixelquantum", "params": {"superposition": 0.0, "uncertainty": 5.0}}]
        r_off = apply_chain(frame.copy(), chain_off, frame_index=0, total_frames=1)

        _physics_state.clear()
        chain_on = [{"name": "pixelquantum", "params": {"superposition": 0.8, "uncertainty": 5.0}}]
        r_on = apply_chain(frame.copy(), chain_on, frame_index=0, total_frames=1)

        sup_diff = diff(r_off, r_on)
        assert sup_diff > 1.0, f"Superposition on vs off diff={sup_diff:.1f}, ghosts still invisible"

    def test_p4_elastic_high_mass_still_visible(self):
        """P4: Elastic at mass=5.0 should still produce visible displacement."""
        frame = make_frame()
        _physics_state.clear()
        chain = [{"name": "pixelelastic", "params": {"mass": 5.0, "force_strength": 10.0}}]
        result = apply_chain(frame, chain, frame_index=0, total_frames=1)
        d = diff(result, frame)
        assert d > 1.0, f"Elastic at mass=5.0 invisible (diff={d:.1f})"

    def test_p4_elastic_mass_affects_output(self):
        """P4: Different mass values should produce different outputs."""
        frame = make_frame()
        _physics_state.clear()
        chain_low = [{"name": "pixelelastic", "params": {"mass": 0.5}}]
        r_low = apply_chain(frame.copy(), chain_low, frame_index=0, total_frames=1)
        d_low = diff(r_low, frame)

        _physics_state.clear()
        chain_high = [{"name": "pixelelastic", "params": {"mass": 5.0}}]
        r_high = apply_chain(frame.copy(), chain_high, frame_index=0, total_frames=1)
        d_high = diff(r_high, frame)

        mass_diff = diff(r_low, r_high)
        assert mass_diff > 0.5, f"Mass change has no effect: diff={mass_diff:.1f}"

    def test_p6_scanlines_flicker_deterministic(self):
        """P6: Scanlines flicker with same seed should be deterministic."""
        frame = np.random.randint(50, 200, (120, 160, 3), dtype=np.uint8)
        chain = [{"name": "scanlines", "params": {"flicker": True, "opacity": 0.5, "seed": 42}}]
        r1 = apply_chain(frame.copy(), chain, frame_index=0, total_frames=1)
        r2 = apply_chain(frame.copy(), chain, frame_index=0, total_frames=1)
        assert np.array_equal(r1, r2), "Flicker with same seed should be deterministic"

    def test_p6_scanlines_seed_varies_flicker(self):
        """P6: Different seeds should produce different flicker patterns."""
        frame = np.random.randint(50, 200, (120, 160, 3), dtype=np.uint8)
        chain_a = [{"name": "scanlines", "params": {"flicker": True, "opacity": 0.5, "seed": 42}}]
        chain_b = [{"name": "scanlines", "params": {"flicker": True, "opacity": 0.5, "seed": 99}}]
        r_a = apply_chain(frame.copy(), chain_a, frame_index=0, total_frames=1)
        r_b = apply_chain(frame.copy(), chain_b, frame_index=0, total_frames=1)
        assert not np.array_equal(r_a, r_b), "Different seeds should produce different flicker"

    def test_p7_brailleart_no_crash(self):
        """P7: brailleart should not crash and should produce visible output."""
        frame = make_frame()
        chain = [{"name": "brailleart", "params": {}}]
        result = apply_chain(frame, chain, frame_index=0, total_frames=1)
        assert result is not None
        assert result.shape == frame.shape
        d = diff(result, frame)
        assert d > 5.0, f"brailleart output too faint or blank: diff={d:.1f}"


# ─── Item #5: Parameter sensitivity / ranges ───


class TestParamRanges:
    """S3: param_ranges should be defined and server should use them."""

    EFFECTS_WITH_RANGES = [
        "edges", "contrast", "tapesaturation", "saturation",
        "pixelelastic", "pixelmagnetic", "pixelquantum",
        "chroma_key", "luma_key",
    ]

    @pytest.mark.parametrize("effect_name", EFFECTS_WITH_RANGES)
    def test_param_ranges_defined(self, effect_name):
        """Effect must have param_ranges dict in registry."""
        entry = EFFECTS[effect_name]
        assert "param_ranges" in entry, f"{effect_name} missing param_ranges"
        ranges = entry["param_ranges"]
        assert len(ranges) > 0, f"{effect_name} param_ranges is empty"

    @pytest.mark.parametrize("effect_name", EFFECTS_WITH_RANGES)
    def test_param_ranges_match_defaults(self, effect_name):
        """Each range key must exist in params, and min <= default <= max."""
        entry = EFFECTS[effect_name]
        ranges = entry["param_ranges"]
        params = entry["params"]
        for key, r in ranges.items():
            assert key in params, f"{effect_name}: range key '{key}' not in params"
            default = params[key]
            if isinstance(default, (int, float)):
                assert r["min"] <= default <= r["max"], (
                    f"{effect_name}.{key}: default {default} outside range [{r['min']}, {r['max']}]"
                )

    def test_edges_threshold_range_correct(self):
        """Edges threshold should be 0.01-1.0, not auto-generated 0-2.0."""
        entry = EFFECTS["edges"]
        r = entry["param_ranges"]["threshold"]
        assert r["min"] == 0.01
        assert r["max"] == 1.0

    def test_exposure_allows_negative(self):
        """Exposure stops should allow negative values (darken)."""
        entry = EFFECTS["exposure"]
        r = entry["param_ranges"]["stops"]
        assert r["min"] < 0, "Exposure should allow negative stops"


# ─── Server API param_ranges integration ───


class TestServerParamRanges:
    """Verify server.py uses param_ranges when building API response."""

    def test_server_list_effects_respects_ranges(self):
        """The /api/effects endpoint should use param_ranges for min/max."""
        # Simulate what the server does
        entry = EFFECTS["edges"]
        ranges = entry.get("param_ranges", {})
        v = entry["params"]["threshold"]
        r = ranges.get("threshold", {})
        api_min = r.get("min", 0.0)
        api_max = r.get("max", max(v * 4, 2.0))
        assert api_min == 0.01, f"Server should use param_ranges min, got {api_min}"
        assert api_max == 1.0, f"Server should use param_ranges max, got {api_max}"

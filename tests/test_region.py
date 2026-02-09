"""
Entropic — Region Selection Tests
Tests region parsing, validation, feathering, and integration with apply_effect.

Run with: pytest tests/test_region.py -v
"""

import os
import sys

import pytest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.region import (
    parse_region, create_feather_mask, apply_to_region,
    list_presets, RegionError, REGION_PRESETS,
)
from core.safety import validate_region, SafetyError
from effects import apply_effect, EFFECTS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def frame_100x100():
    """100x100 solid gray frame."""
    return np.full((100, 100, 3), 128, dtype=np.uint8)


@pytest.fixture
def frame_640x480():
    """640x480 random frame (W=640, H=480)."""
    rng = np.random.RandomState(42)
    return rng.randint(0, 256, (480, 640, 3), dtype=np.uint8)


@pytest.fixture
def gradient_frame():
    """100x100 horizontal gradient (black to white) for visual testing."""
    gradient = np.zeros((100, 100, 3), dtype=np.uint8)
    for x in range(100):
        gradient[:, x, :] = int(255 * x / 99)
    return gradient


# ---------------------------------------------------------------------------
# PARSE REGION — String format
# ---------------------------------------------------------------------------

class TestParseRegionString:

    def test_pixel_coords(self):
        x, y, w, h = parse_region("10,20,50,60", 100, 200)
        assert (x, y, w, h) == (10, 20, 50, 60)

    def test_percent_coords(self):
        x, y, w, h = parse_region("0.25,0.1,0.5,0.8", 100, 200)
        assert x == 50   # 0.25 * 200
        assert y == 10   # 0.1 * 100
        assert w == 100   # 0.5 * 200
        assert h == 80   # 0.8 * 100

    def test_preset_center(self):
        x, y, w, h = parse_region("center", 100, 200)
        assert x == 50   # 0.25 * 200
        assert y == 25   # 0.25 * 100
        assert w == 100   # 0.5 * 200
        assert h == 50   # 0.5 * 100

    def test_preset_top_half(self):
        x, y, w, h = parse_region("top-half", 100, 200)
        assert (x, y) == (0, 0)
        assert w == 200
        assert h == 50

    def test_preset_bottom_half(self):
        x, y, w, h = parse_region("bottom-half", 100, 200)
        assert y == 50

    def test_all_presets_valid(self):
        """Every preset should parse without error."""
        for name in REGION_PRESETS:
            x, y, w, h = parse_region(name, 480, 640)
            assert w > 0 and h > 0, f"Preset '{name}' has zero area"

    def test_spaces_in_string(self):
        x, y, w, h = parse_region("10, 20, 50, 60", 100, 200)
        assert (x, y, w, h) == (10, 20, 50, 60)

    def test_invalid_format_raises(self):
        with pytest.raises(RegionError):
            parse_region("10,20,50", 100, 200)  # Only 3 values

    def test_non_numeric_raises(self):
        with pytest.raises(RegionError):
            parse_region("abc,20,50,60", 100, 200)

    def test_unknown_preset_raises(self):
        with pytest.raises(RegionError):
            parse_region("nonexistent-preset", 100, 200)


# ---------------------------------------------------------------------------
# PARSE REGION — Dict format
# ---------------------------------------------------------------------------

class TestParseRegionDict:

    def test_pixel_dict(self):
        x, y, w, h = parse_region({"x": 10, "y": 20, "w": 50, "h": 60}, 100, 200)
        assert (x, y, w, h) == (10, 20, 50, 60)

    def test_percent_dict(self):
        x, y, w, h = parse_region({"x": 0.25, "y": 0.1, "w": 0.5, "h": 0.8}, 100, 200)
        assert x == 50
        assert w == 100

    def test_missing_keys_use_defaults(self):
        x, y, w, h = parse_region({"w": 50, "h": 60}, 100, 200)
        assert x == 0
        assert y == 0


# ---------------------------------------------------------------------------
# PARSE REGION — Tuple/List format
# ---------------------------------------------------------------------------

class TestParseRegionTuple:

    def test_tuple(self):
        x, y, w, h = parse_region((10, 20, 50, 60), 100, 200)
        assert (x, y, w, h) == (10, 20, 50, 60)

    def test_list(self):
        x, y, w, h = parse_region([10, 20, 50, 60], 100, 200)
        assert (x, y, w, h) == (10, 20, 50, 60)

    def test_wrong_length_raises(self):
        with pytest.raises(RegionError):
            parse_region((10, 20, 50), 100, 200)


# ---------------------------------------------------------------------------
# EDGE CASES & CLAMPING
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_region_at_boundary(self):
        """Region touching frame edge should work."""
        x, y, w, h = parse_region("0,0,200,100", 100, 200)
        assert (x, y, w, h) == (0, 0, 200, 100)

    def test_region_exceeds_frame_clamped(self):
        """Region larger than frame should be clamped."""
        x, y, w, h = parse_region("50,50,300,200", 100, 200)
        assert x == 50
        assert y == 50
        assert w == 150  # Clamped: 200 - 50
        assert h == 50   # Clamped: 100 - 50

    def test_zero_width_raises(self):
        with pytest.raises(RegionError):
            parse_region("10,10,0,50", 100, 200)

    def test_zero_height_raises(self):
        with pytest.raises(RegionError):
            parse_region("10,10,50,0", 100, 200)

    def test_negative_position_raises(self):
        with pytest.raises(RegionError):
            parse_region("-10,10,50,50", 100, 200)

    def test_none_returns_full_frame(self):
        x, y, w, h = parse_region(None, 100, 200)
        assert (x, y, w, h) == (0, 0, 200, 100)

    def test_1px_region(self):
        """Smallest possible region."""
        x, y, w, h = parse_region("50,50,1,1", 100, 200)
        assert (x, y, w, h) == (50, 50, 1, 1)

    def test_full_frame_as_percent(self):
        x, y, w, h = parse_region("0.0,0.0,1.0,1.0", 480, 640)
        assert (x, y, w, h) == (0, 0, 640, 480)


# ---------------------------------------------------------------------------
# FEATHER MASK
# ---------------------------------------------------------------------------

class TestFeatherMask:

    def test_no_feather_all_ones(self):
        mask = create_feather_mask(50, 50, feather=0)
        assert mask.shape == (50, 50)
        assert mask.dtype == np.float32
        np.testing.assert_array_equal(mask, 1.0)

    def test_feather_edges_less_than_center(self):
        mask = create_feather_mask(50, 50, feather=10)
        # Center should be 1.0
        assert mask[25, 25] == 1.0
        # Edge pixels should be less than 1.0
        assert mask[0, 25] < 1.0
        assert mask[25, 0] < 1.0
        assert mask[49, 25] < 1.0
        assert mask[25, 49] < 1.0

    def test_feather_clamped_to_half_size(self):
        """Feather can't be larger than half the region."""
        mask = create_feather_mask(10, 10, feather=100)
        assert mask.shape == (10, 10)
        # Should still work, just clamped — no crash
        assert 0.0 < mask[5, 5] <= 1.0

    def test_negative_feather_treated_as_zero(self):
        mask = create_feather_mask(50, 50, feather=-5)
        np.testing.assert_array_equal(mask, 1.0)


# ---------------------------------------------------------------------------
# APPLY TO REGION
# ---------------------------------------------------------------------------

class TestApplyToRegion:

    def _invert_fn(self, frame, **kwargs):
        """Simple inversion for testing."""
        return 255 - frame

    def test_region_only_modifies_specified_area(self, frame_100x100):
        result = apply_to_region(frame_100x100, self._invert_fn, "25,25,50,50")
        # Inside region: inverted (128 → 127)
        assert result[50, 50, 0] == 127
        # Outside region: unchanged (128)
        assert result[0, 0, 0] == 128
        assert result[99, 99, 0] == 128

    def test_full_frame_region_modifies_all(self, frame_100x100):
        result = apply_to_region(frame_100x100, self._invert_fn, None)
        assert result[50, 50, 0] == 127
        assert result[0, 0, 0] == 127

    def test_feathered_region_has_smooth_edges(self, frame_100x100):
        result = apply_to_region(frame_100x100, self._invert_fn, "20,20,60,60", feather=10)
        # Center: fully inverted
        assert result[50, 50, 0] == 127
        # Edge: blended (between 127 and 128)
        edge_val = result[20, 50, 0]
        assert 127 <= edge_val <= 128

    def test_output_shape_preserved(self, frame_640x480):
        result = apply_to_region(frame_640x480, self._invert_fn, "center")
        assert result.shape == frame_640x480.shape
        assert result.dtype == np.uint8

    def test_preset_region_works(self, frame_100x100):
        result = apply_to_region(frame_100x100, self._invert_fn, "top-half")
        # Top half inverted
        assert result[10, 50, 0] == 127
        # Bottom half unchanged
        assert result[75, 50, 0] == 128


# ---------------------------------------------------------------------------
# INTEGRATION WITH apply_effect
# ---------------------------------------------------------------------------

class TestApplyEffectRegion:

    def test_region_param_works(self, frame_100x100):
        """apply_effect should accept region param."""
        result = apply_effect(frame_100x100, "invert", region="center")
        assert result.shape == frame_100x100.shape
        assert result.dtype == np.uint8

    def test_region_with_feather(self, frame_100x100):
        result = apply_effect(frame_100x100, "invert", region="center", feather=5)
        assert result.shape == frame_100x100.shape

    def test_region_with_preset(self, frame_100x100):
        result = apply_effect(frame_100x100, "hueshift", degrees=90, region="left-half")
        assert result.shape == frame_100x100.shape

    def test_region_preserves_outside(self, frame_100x100):
        """Pixels outside region should be identical to input."""
        result = apply_effect(frame_100x100, "invert", region="25,25,50,50")
        # Outside region — should be unchanged
        np.testing.assert_array_equal(result[0, 0], frame_100x100[0, 0])
        np.testing.assert_array_equal(result[99, 99], frame_100x100[99, 99])

    def test_region_none_is_full_frame(self, frame_100x100):
        """region=None should behave like no region (full frame)."""
        r1 = apply_effect(frame_100x100.copy(), "invert")
        r2 = apply_effect(frame_100x100.copy(), "invert", region=None)
        np.testing.assert_array_equal(r1, r2)

    def test_multiple_effects_different_regions(self, frame_100x100):
        """Different effects on different regions should compose."""
        # Invert top half
        result = apply_effect(frame_100x100.copy(), "invert", region="top-half")
        # Then posterize bottom half
        result = apply_effect(result, "posterize", levels=2, region="bottom-half")
        assert result.shape == frame_100x100.shape

    @pytest.mark.parametrize("preset", list(REGION_PRESETS.keys()))
    def test_all_presets_with_effect(self, frame_100x100, preset):
        """Every preset should work with apply_effect."""
        result = apply_effect(frame_100x100, "noise", amount=0.5, region=preset, seed=42)
        assert result.shape == frame_100x100.shape
        assert result.dtype == np.uint8


# ---------------------------------------------------------------------------
# SAFETY VALIDATION
# ---------------------------------------------------------------------------

class TestSafetyValidation:

    def test_valid_string_passes(self):
        validate_region("10,20,50,60")

    def test_valid_preset_passes(self):
        validate_region("center")

    def test_none_passes(self):
        validate_region(None)

    def test_too_long_string_fails(self):
        with pytest.raises(SafetyError):
            validate_region("x" * 201)

    def test_nan_fails(self):
        with pytest.raises(SafetyError):
            validate_region("nan,0,50,50")

    def test_inf_fails(self):
        with pytest.raises(SafetyError):
            validate_region("inf,0,50,50")

    def test_non_numeric_fails(self):
        with pytest.raises(SafetyError):
            validate_region("abc,0,50,50")

    def test_wrong_count_fails(self):
        with pytest.raises(SafetyError):
            validate_region("10,20,50")

    def test_dict_with_bad_values_fails(self):
        with pytest.raises(SafetyError):
            validate_region({"x": "abc", "y": 0, "w": 50, "h": 50})

    def test_tuple_wrong_length_fails(self):
        with pytest.raises(SafetyError):
            validate_region((10, 20))

    def test_with_frame_dims_validates_fully(self):
        validate_region("10,20,50,60", frame_width=200, frame_height=100)

    def test_with_frame_dims_negative_fails(self):
        with pytest.raises(SafetyError):
            validate_region("-10,20,50,60", frame_width=200, frame_height=100)


# ---------------------------------------------------------------------------
# PRESETS LIST
# ---------------------------------------------------------------------------

class TestPresetsList:

    def test_list_presets_returns_all(self):
        presets = list_presets()
        assert "center" in presets
        assert "top-half" in presets
        assert len(presets) >= 12

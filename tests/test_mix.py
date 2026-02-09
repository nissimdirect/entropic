"""
Entropic — Dry/Wet Mix Tests
Tests for the parallel processing (mix) parameter on all effects.

Run with: pytest tests/test_mix.py -v
"""

import os
import sys

import pytest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from effects import apply_effect, apply_chain, EFFECTS


@pytest.fixture
def frame():
    """A 64x64 deterministic frame for consistent testing."""
    rng = np.random.RandomState(123)
    return rng.randint(0, 256, (64, 64, 3), dtype=np.uint8)


# ---------------------------------------------------------------------------
# DRY/WET MIX
# ---------------------------------------------------------------------------

class TestDryWetMix:

    def test_mix_zero_returns_original(self, frame):
        """mix=0.0 should return the original frame (fully dry)."""
        result = apply_effect(frame, "hueshift", mix=0.0, degrees=180)
        np.testing.assert_array_equal(result, frame)

    def test_mix_one_returns_fully_processed(self, frame):
        """mix=1.0 should return the fully processed frame (default)."""
        wet = apply_effect(frame, "hueshift", mix=1.0, degrees=180)
        default = apply_effect(frame, "hueshift", degrees=180)
        np.testing.assert_array_equal(wet, default)

    def test_mix_half_is_blend(self, frame):
        """mix=0.5 should be halfway between dry and wet."""
        dry = frame.copy()
        wet = apply_effect(frame, "invert", mix=1.0)
        blended = apply_effect(frame, "invert", mix=0.5)

        # Manual calculation of expected blend
        expected = np.clip(
            dry.astype(np.float32) * 0.5 + wet.astype(np.float32) * 0.5,
            0, 255
        ).astype(np.uint8)

        # Allow +-1 for rounding differences
        diff = np.abs(blended.astype(int) - expected.astype(int))
        assert diff.max() <= 1, f"Max diff: {diff.max()}"

    def test_mix_clamped_above_one(self, frame):
        """mix > 1.0 should be clamped to 1.0."""
        result = apply_effect(frame, "hueshift", mix=5.0, degrees=90)
        expected = apply_effect(frame, "hueshift", mix=1.0, degrees=90)
        np.testing.assert_array_equal(result, expected)

    def test_mix_clamped_below_zero(self, frame):
        """mix < 0.0 should be clamped to 0.0 (returns original)."""
        result = apply_effect(frame, "hueshift", mix=-1.0, degrees=90)
        np.testing.assert_array_equal(result, frame)

    def test_mix_preserves_shape_and_dtype(self, frame):
        """Mixed output must maintain shape and uint8 dtype."""
        result = apply_effect(frame, "pixelsort", mix=0.3, threshold=0.5)
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_mix_values_in_range(self, frame):
        """Mixed output must stay in 0-255."""
        result = apply_effect(frame, "contrast", mix=0.7, amount=80)
        assert result.min() >= 0
        assert result.max() <= 255

    @pytest.mark.parametrize("effect_name", [
        name for name, entry in EFFECTS.items() if entry["fn"] is not None
    ])
    def test_mix_zero_identity_all_effects(self, effect_name, frame):
        """mix=0.0 should return original for every single effect."""
        result = apply_effect(frame, effect_name, mix=0.0)
        np.testing.assert_array_equal(result, frame)

    def test_mix_in_chain(self, frame):
        """mix should work within effect chains."""
        chain = [
            {"name": "hueshift", "params": {"degrees": 90, "mix": 0.5}},
            {"name": "contrast", "params": {"amount": 30, "mix": 0.3}},
        ]
        result = apply_chain(frame, chain)
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_mix_with_temporal_effect(self, frame):
        """mix should work with temporal effects too."""
        result = apply_effect(frame, "stutter", mix=0.5, repeat=3, interval=4,
                              frame_index=0, total_frames=10)
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

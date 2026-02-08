"""
Entropic — Modulation Effects Tests
Tests for ring_mod and gate effects.

Run with: pytest tests/test_modulation.py -v
"""

import os
import sys

import pytest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from effects.modulation import ring_mod, gate


@pytest.fixture
def small_frame():
    rng = np.random.RandomState(777)
    return rng.randint(0, 256, (64, 64, 3), dtype=np.uint8)


@pytest.fixture
def gradient_frame():
    """Frame with smooth gradient from black to white (left to right)."""
    row = np.linspace(0, 255, 64, dtype=np.uint8)
    frame = np.tile(row, (64, 1))
    return np.stack([frame, frame, frame], axis=2)


# ---------------------------------------------------------------------------
# RING MOD
# ---------------------------------------------------------------------------

class TestRingMod:

    def test_ringmod_returns_correct_shape(self, small_frame):
        result = ring_mod(small_frame, frequency=4.0, direction="horizontal", frame_index=0)
        assert result.shape == small_frame.shape
        assert result.dtype == np.uint8

    def test_ringmod_creates_banding_pattern(self, gradient_frame):
        """Ring mod should create alternating bright/dark bands."""
        result = ring_mod(gradient_frame, frequency=4.0, direction="horizontal", frame_index=0)
        # Middle column should differ from adjacent (bands exist)
        col_means = result[:, :, 0].mean(axis=0)
        # With 4 cycles across 64px, we should see oscillation
        diffs = np.abs(np.diff(col_means.astype(float)))
        assert diffs.max() > 0, "Should have brightness variation across columns"

    def test_ringmod_vertical(self, small_frame):
        """Vertical direction should work."""
        result = ring_mod(small_frame, frequency=4.0, direction="vertical", frame_index=0)
        assert result.shape == small_frame.shape

    def test_ringmod_radial(self, small_frame):
        """Radial direction should work."""
        result = ring_mod(small_frame, frequency=4.0, direction="radial", frame_index=0)
        assert result.shape == small_frame.shape

    def test_ringmod_animates_over_time(self, small_frame):
        """Different frame_index should shift the pattern."""
        r0 = ring_mod(small_frame, frequency=4.0, frame_index=0)
        r5 = ring_mod(small_frame, frequency=4.0, frame_index=5)
        # Should not be identical (phase shifts)
        assert not np.array_equal(r0, r5)

    def test_ringmod_frequency_clamped(self, small_frame):
        """Extreme frequencies should be clamped."""
        result = ring_mod(small_frame, frequency=200.0, frame_index=0)
        assert result.shape == small_frame.shape
        result = ring_mod(small_frame, frequency=-5.0, frame_index=0)
        assert result.shape == small_frame.shape

    def test_ringmod_values_in_range(self, small_frame):
        """Output must stay in 0-255."""
        for i in range(10):
            result = ring_mod(small_frame, frequency=8.0, frame_index=i)
            assert result.min() >= 0
            assert result.max() <= 255


# ---------------------------------------------------------------------------
# GATE
# ---------------------------------------------------------------------------

class TestGate:

    def test_gate_returns_correct_shape(self, small_frame):
        result = gate(small_frame, threshold=0.3)
        assert result.shape == small_frame.shape
        assert result.dtype == np.uint8

    def test_gate_threshold_zero_passthrough(self, small_frame):
        """threshold=0 should keep everything (nothing below 0)."""
        result = gate(small_frame, threshold=0.0)
        np.testing.assert_array_equal(result, small_frame)

    def test_gate_threshold_one_all_black(self, small_frame):
        """threshold=1.0 should black out everything (nothing at max brightness)."""
        # Use a frame that doesn't have pure white pixels
        dim_frame = np.full((32, 32, 3), 200, dtype=np.uint8)
        result = gate(dim_frame, threshold=1.0)
        assert result.max() == 0, "All pixels below threshold should be black"

    def test_gate_brightness_mode(self, gradient_frame):
        """Brightness mode should gate based on pixel luminance."""
        result = gate(gradient_frame, threshold=0.5, mode="brightness")
        # Left half (dark) should be blacked out, right half preserved
        left_mean = result[:, :16, :].mean()
        right_mean = result[:, 48:, :].mean()
        assert left_mean < right_mean, "Dark side should be darker after gate"

    def test_gate_channel_mode(self, small_frame):
        """Channel mode should gate each channel independently."""
        result = gate(small_frame, threshold=0.3, mode="channel")
        assert result.shape == small_frame.shape
        # Values below threshold*255 should be 0
        threshold_val = 0.3 * 255
        below_mask = small_frame < threshold_val
        assert (result[below_mask] == 0).all()

    def test_gate_preserves_above_threshold(self, gradient_frame):
        """Pixels above threshold should be unchanged."""
        threshold = 0.3
        result = gate(gradient_frame, threshold=threshold, mode="brightness")
        threshold_val = threshold * 255
        # For brightness mode, bright pixels should be preserved
        luminance = gradient_frame[:, :, 0].astype(float)  # grayscale, so all channels equal
        bright_mask = luminance >= threshold_val
        np.testing.assert_array_equal(result[bright_mask], gradient_frame[bright_mask])

    def test_gate_values_in_range(self, small_frame):
        """Output must stay in 0-255."""
        result = gate(small_frame, threshold=0.5)
        assert result.min() >= 0
        assert result.max() <= 255

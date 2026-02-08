"""
Entropic — Enhancement Effects Tests
Tests for solarize, duotone, emboss, auto_levels, median_filter, false_color.

Run with: pytest tests/test_enhance.py -v
"""

import os
import sys

import pytest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from effects.enhance import solarize, duotone, emboss, auto_levels, median_filter, false_color


@pytest.fixture
def small_frame():
    rng = np.random.RandomState(555)
    return rng.randint(0, 256, (64, 64, 3), dtype=np.uint8)


@pytest.fixture
def gradient_frame():
    """Smooth gradient left (black) to right (white)."""
    row = np.linspace(0, 255, 64, dtype=np.uint8)
    frame = np.tile(row, (64, 1))
    return np.stack([frame, frame, frame], axis=2)


# ---------------------------------------------------------------------------
# SOLARIZE
# ---------------------------------------------------------------------------

class TestSolarize:

    def test_returns_correct_shape(self, small_frame):
        result = solarize(small_frame, threshold=128)
        assert result.shape == small_frame.shape
        assert result.dtype == np.uint8

    def test_threshold_zero_fully_inverts(self, small_frame):
        """threshold=0 inverts all pixels."""
        result = solarize(small_frame, threshold=0)
        expected = 255 - small_frame
        np.testing.assert_array_equal(result, expected)

    def test_threshold_255_minimal_change(self, small_frame):
        """threshold=255 should only affect pixels AT 255 (PIL inverts >= threshold)."""
        result = solarize(small_frame, threshold=255)
        # Only pixels that were exactly 255 get inverted to 0
        diff_mask = result != small_frame
        if diff_mask.any():
            assert small_frame[diff_mask].min() == 255

    def test_partial_solarize(self, gradient_frame):
        """Middle threshold should partially invert."""
        result = solarize(gradient_frame, threshold=128)
        # Left side (dark, below 128) should be unchanged
        assert np.array_equal(result[:, 0, :], gradient_frame[:, 0, :])
        # Right side (bright, above 128) should be different
        assert not np.array_equal(result[:, -1, :], gradient_frame[:, -1, :])

    def test_values_in_range(self, small_frame):
        result = solarize(small_frame, threshold=100)
        assert result.min() >= 0
        assert result.max() <= 255


# ---------------------------------------------------------------------------
# DUOTONE
# ---------------------------------------------------------------------------

class TestDuotone:

    def test_returns_correct_shape(self, small_frame):
        result = duotone(small_frame)
        assert result.shape == small_frame.shape
        assert result.dtype == np.uint8

    def test_shadow_color_applied(self):
        """Pure black frame should map to shadow color."""
        black = np.zeros((32, 32, 3), dtype=np.uint8)
        result = duotone(black, shadow_color=(255, 0, 0), highlight_color=(0, 0, 255))
        # Should be close to pure red
        assert result[:, :, 0].mean() > 200
        assert result[:, :, 2].mean() < 50

    def test_highlight_color_applied(self):
        """Pure white frame should map to highlight color."""
        white = np.full((32, 32, 3), 255, dtype=np.uint8)
        result = duotone(white, shadow_color=(255, 0, 0), highlight_color=(0, 0, 255))
        # Should be close to pure blue
        assert result[:, :, 2].mean() > 200
        assert result[:, :, 0].mean() < 50

    def test_values_in_range(self, small_frame):
        result = duotone(small_frame)
        assert result.min() >= 0
        assert result.max() <= 255


# ---------------------------------------------------------------------------
# EMBOSS
# ---------------------------------------------------------------------------

class TestEmboss:

    def test_returns_correct_shape(self, small_frame):
        result = emboss(small_frame, amount=1.0)
        assert result.shape == small_frame.shape
        assert result.dtype == np.uint8

    def test_amount_zero_passthrough(self, small_frame):
        """amount=0 should return original."""
        result = emboss(small_frame, amount=0.0)
        np.testing.assert_array_equal(result, small_frame)

    def test_amount_one_differs(self, small_frame):
        """Full emboss should differ from original."""
        result = emboss(small_frame, amount=1.0)
        assert not np.array_equal(result, small_frame)

    def test_values_in_range(self, small_frame):
        result = emboss(small_frame, amount=0.7)
        assert result.min() >= 0
        assert result.max() <= 255


# ---------------------------------------------------------------------------
# AUTO LEVELS
# ---------------------------------------------------------------------------

class TestAutoLevels:

    def test_returns_correct_shape(self, small_frame):
        result = auto_levels(small_frame, cutoff=2.0)
        assert result.shape == small_frame.shape
        assert result.dtype == np.uint8

    def test_stretches_contrast(self):
        """Low-contrast input should have wider range after auto levels."""
        # Create narrow-range frame (100-150)
        narrow = np.random.RandomState(42).randint(100, 151, (32, 32, 3)).astype(np.uint8)
        result = auto_levels(narrow, cutoff=0.0)
        # Output should have wider range
        assert (result.max() - result.min()) > (narrow.max() - narrow.min())

    def test_cutoff_clamped(self, small_frame):
        result = auto_levels(small_frame, cutoff=50.0)
        assert result.shape == small_frame.shape

    def test_values_in_range(self, small_frame):
        result = auto_levels(small_frame)
        assert result.min() >= 0
        assert result.max() <= 255


# ---------------------------------------------------------------------------
# MEDIAN FILTER
# ---------------------------------------------------------------------------

class TestMedianFilter:

    def test_returns_correct_shape(self, small_frame):
        result = median_filter(small_frame, size=5)
        assert result.shape == small_frame.shape
        assert result.dtype == np.uint8

    def test_removes_salt_pepper_noise(self):
        """Median filter should reduce salt-and-pepper noise."""
        base = np.full((64, 64, 3), 128, dtype=np.uint8)
        noisy = base.copy()
        rng = np.random.RandomState(42)
        # Add salt and pepper
        salt = rng.random((64, 64)) > 0.95
        pepper = rng.random((64, 64)) > 0.95
        noisy[salt] = 255
        noisy[pepper] = 0
        result = median_filter(noisy, size=3)
        # Should be closer to the base than the noisy version
        noise_diff = np.abs(noisy.astype(int) - base.astype(int)).mean()
        result_diff = np.abs(result.astype(int) - base.astype(int)).mean()
        assert result_diff < noise_diff

    def test_size_clamped(self, small_frame):
        result = median_filter(small_frame, size=100)
        assert result.shape == small_frame.shape

    def test_values_in_range(self, small_frame):
        result = median_filter(small_frame, size=7)
        assert result.min() >= 0
        assert result.max() <= 255


# ---------------------------------------------------------------------------
# FALSE COLOR
# ---------------------------------------------------------------------------

class TestFalseColor:

    def test_returns_correct_shape(self, small_frame):
        result = false_color(small_frame, colormap="jet")
        assert result.shape == small_frame.shape
        assert result.dtype == np.uint8

    def test_different_colormaps_differ(self, small_frame):
        """Different colormaps should produce different results."""
        r1 = false_color(small_frame, colormap="jet")
        r2 = false_color(small_frame, colormap="hot")
        assert not np.array_equal(r1, r2)

    def test_unknown_colormap_defaults(self, small_frame):
        """Unknown colormap should fall back to jet."""
        result = false_color(small_frame, colormap="nonexistent")
        expected = false_color(small_frame, colormap="jet")
        np.testing.assert_array_equal(result, expected)

    def test_all_colormaps_work(self, small_frame):
        """All supported colormaps should render without error."""
        maps = ["jet", "hot", "cool", "spring", "summer", "autumn", "winter",
                "bone", "ocean", "rainbow", "turbo", "inferno", "magma",
                "plasma", "viridis"]
        for cm in maps:
            result = false_color(small_frame, colormap=cm)
            assert result.shape == small_frame.shape

    def test_values_in_range(self, small_frame):
        result = false_color(small_frame, colormap="plasma")
        assert result.min() >= 0
        assert result.max() <= 255

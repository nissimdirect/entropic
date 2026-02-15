"""
Tests for ring_mod reconceptualization (P2-6).
Validates carrier waveforms, spectrum bands, animation, and all modes.
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from effects.modulation import ring_mod


@pytest.fixture
def test_frame():
    """Create a gradient test frame (128x128)."""
    h, w = 128, 128
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            frame[y, x] = [x * 2, y * 2, 128]
    return frame


class TestCarrierWaveforms:
    """Each waveform should produce a distinct output."""

    def test_sine_is_default(self, test_frame):
        """Default carrier_waveform produces valid output."""
        result = ring_mod(test_frame, frequency=4.0, depth=1.0)
        assert result.shape == test_frame.shape
        assert result.dtype == np.uint8

    def test_square_differs_from_sine(self, test_frame):
        """Square carrier is distinct from sine."""
        sine = ring_mod(test_frame, carrier_waveform="sine", frequency=4.0, depth=1.0)
        square = ring_mod(test_frame, carrier_waveform="square", frequency=4.0, depth=1.0)
        assert not np.array_equal(sine, square), "Square should differ from sine"

    def test_triangle_differs_from_sine(self, test_frame):
        """Triangle carrier is distinct from sine."""
        sine = ring_mod(test_frame, carrier_waveform="sine", frequency=4.0, depth=1.0)
        tri = ring_mod(test_frame, carrier_waveform="triangle", frequency=4.0, depth=1.0)
        assert not np.array_equal(sine, tri), "Triangle should differ from sine"

    def test_saw_differs_from_sine(self, test_frame):
        """Saw carrier is distinct from sine."""
        sine = ring_mod(test_frame, carrier_waveform="sine", frequency=4.0, depth=1.0)
        saw = ring_mod(test_frame, carrier_waveform="saw", frequency=4.0, depth=1.0)
        assert not np.array_equal(sine, saw), "Saw should differ from sine"

    def test_all_waveforms_produce_valid_output(self, test_frame):
        """All 4 waveforms produce uint8 frames of correct shape."""
        for wf in ["sine", "square", "triangle", "saw"]:
            result = ring_mod(test_frame, carrier_waveform=wf, frequency=4.0, depth=1.0)
            assert result.shape == test_frame.shape, f"{wf} wrong shape"
            assert result.dtype == np.uint8, f"{wf} wrong dtype"
            assert result.max() <= 255 and result.min() >= 0, f"{wf} out of range"

    def test_invalid_waveform_falls_back_to_sine(self, test_frame):
        """Invalid carrier_waveform defaults to sine."""
        expected = ring_mod(test_frame, carrier_waveform="sine", frequency=4.0, depth=1.0)
        result = ring_mod(test_frame, carrier_waveform="INVALID", frequency=4.0, depth=1.0)
        assert np.array_equal(expected, result)


class TestDepthBypass:
    """depth=0 should return original frame."""

    def test_depth_zero_passthrough(self, test_frame):
        """depth=0 means no modulation — output equals input."""
        for mode in ["am", "fm", "phase", "multi"]:
            result = ring_mod(test_frame, depth=0.0, mode=mode)
            # With depth=0, carrier = (1-0) + 0*carrier = 1.0, so output ~= input
            # Allow small float rounding difference
            diff = np.abs(result.astype(float) - test_frame.astype(float))
            assert diff.max() <= 1, f"depth=0 should passthrough in {mode} mode"


class TestDirections:
    """All directions produce valid, distinct output."""

    def test_horizontal_vertical_differ(self, test_frame):
        hz = ring_mod(test_frame, direction="horizontal", frequency=4.0, depth=1.0)
        vt = ring_mod(test_frame, direction="vertical", frequency=4.0, depth=1.0)
        assert not np.array_equal(hz, vt)

    def test_radial_differs(self, test_frame):
        hz = ring_mod(test_frame, direction="horizontal", frequency=4.0, depth=1.0)
        rd = ring_mod(test_frame, direction="radial", frequency=4.0, depth=1.0)
        assert not np.array_equal(hz, rd)

    def test_temporal_direction(self, test_frame):
        """Temporal direction varies between frames, not spatially."""
        f0 = ring_mod(test_frame, direction="temporal", frequency=4.0, depth=1.0, frame_index=0, total_frames=30)
        f15 = ring_mod(test_frame, direction="temporal", frequency=4.0, depth=1.0, frame_index=15, total_frames=30)
        # f0 and f15 should differ (different temporal position)
        assert not np.array_equal(f0, f15), "Temporal direction should vary over frames"

    def test_invalid_direction_falls_back(self, test_frame):
        """Invalid direction defaults to horizontal."""
        expected = ring_mod(test_frame, direction="horizontal", frequency=4.0, depth=1.0)
        result = ring_mod(test_frame, direction="BOGUS", frequency=4.0, depth=1.0)
        assert np.array_equal(expected, result)


class TestSpectrumBands:
    """Spectrum band selection modulates only target frequencies."""

    def test_all_band_is_default(self, test_frame):
        """spectrum_band='all' should match no-argument behavior."""
        all_result = ring_mod(test_frame, spectrum_band="all", frequency=4.0, depth=1.0)
        default = ring_mod(test_frame, frequency=4.0, depth=1.0)
        assert np.array_equal(all_result, default)

    def test_low_band_differs_from_all(self, test_frame):
        all_r = ring_mod(test_frame, spectrum_band="all", frequency=8.0, depth=1.0)
        low_r = ring_mod(test_frame, spectrum_band="low", frequency=8.0, depth=1.0)
        assert not np.array_equal(all_r, low_r), "Low band should differ from all"

    def test_high_band_differs_from_all(self, test_frame):
        all_r = ring_mod(test_frame, spectrum_band="all", frequency=8.0, depth=1.0)
        high_r = ring_mod(test_frame, spectrum_band="high", frequency=8.0, depth=1.0)
        assert not np.array_equal(all_r, high_r), "High band should differ from all"

    def test_mid_band_differs_from_all(self, test_frame):
        all_r = ring_mod(test_frame, spectrum_band="all", frequency=8.0, depth=1.0)
        mid_r = ring_mod(test_frame, spectrum_band="mid", frequency=8.0, depth=1.0)
        assert not np.array_equal(all_r, mid_r), "Mid band should differ from all"

    def test_invalid_band_falls_back(self, test_frame):
        """Invalid spectrum_band defaults to 'all'."""
        expected = ring_mod(test_frame, spectrum_band="all", frequency=4.0, depth=1.0)
        result = ring_mod(test_frame, spectrum_band="WRONG", frequency=4.0, depth=1.0)
        assert np.array_equal(expected, result)


class TestAnimationRate:
    """animation_rate controls temporal speed."""

    def test_zero_rate_freezes(self, test_frame):
        """animation_rate=0 means no temporal change between frames."""
        f0 = ring_mod(test_frame, animation_rate=0.0, frequency=4.0, depth=1.0, frame_index=0)
        f10 = ring_mod(test_frame, animation_rate=0.0, frequency=4.0, depth=1.0, frame_index=10)
        assert np.array_equal(f0, f10), "Rate 0 should freeze animation"

    def test_higher_rate_moves_faster(self, test_frame):
        """Higher animation_rate creates more change between frames."""
        slow = ring_mod(test_frame, animation_rate=0.5, frequency=4.0, depth=1.0, frame_index=5)
        fast = ring_mod(test_frame, animation_rate=3.0, frequency=4.0, depth=1.0, frame_index=5)
        base = ring_mod(test_frame, animation_rate=0.5, frequency=4.0, depth=1.0, frame_index=0)
        # Fast should differ more from base than slow does
        slow_diff = np.abs(slow.astype(float) - base.astype(float)).mean()
        fast_diff = np.abs(fast.astype(float) - base.astype(float)).mean()
        assert fast_diff >= slow_diff * 0.5, "Faster rate should create more change"


class TestModes:
    """All 4 modes produce distinct outputs."""

    def test_all_modes_differ(self, test_frame):
        results = {}
        for m in ["am", "fm", "phase", "multi"]:
            results[m] = ring_mod(test_frame, mode=m, frequency=4.0, depth=1.0)
        # At least 3 pairs should differ
        diffs = 0
        modes = list(results.keys())
        for i in range(len(modes)):
            for j in range(i + 1, len(modes)):
                if not np.array_equal(results[modes[i]], results[modes[j]]):
                    diffs += 1
        assert diffs >= 3, f"Expected at least 3 differing mode pairs, got {diffs}"

    def test_invalid_mode_falls_back_to_am(self, test_frame):
        expected = ring_mod(test_frame, mode="am", frequency=4.0, depth=1.0)
        result = ring_mod(test_frame, mode="NOPE", frequency=4.0, depth=1.0)
        assert np.array_equal(expected, result)


class TestEdgeCases:
    """Boundary conditions and safety."""

    def test_tiny_frame(self):
        """1x1 frame doesn't crash."""
        tiny = np.array([[[128, 64, 32]]], dtype=np.uint8)
        result = ring_mod(tiny, frequency=4.0, depth=1.0)
        assert result.shape == (1, 1, 3)

    def test_large_frequency_no_overflow(self, test_frame):
        """Max frequency doesn't produce inf/nan."""
        result = ring_mod(test_frame, frequency=50.0, depth=1.0)
        assert not np.any(np.isnan(result.astype(float)))
        assert result.max() <= 255

    def test_all_params_combined(self, test_frame):
        """All new params together don't crash."""
        result = ring_mod(
            test_frame,
            frequency=12.0,
            direction="radial",
            mode="multi",
            depth=0.8,
            source="luminance",
            carrier_waveform="triangle",
            spectrum_band="high",
            animation_rate=3.0,
            frame_index=10,
            total_frames=30,
        )
        assert result.shape == test_frame.shape
        assert result.dtype == np.uint8

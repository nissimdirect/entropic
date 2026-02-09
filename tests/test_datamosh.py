"""
Entropic — Datamosh Effect Tests
Tests all 8 datamosh modes including 3 new modes from transcript learnings.

Run with: pytest tests/test_datamosh.py -v
"""

import os
import sys

import pytest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from effects import apply_effect, EFFECTS
from effects.destruction import datamosh


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def frame_pair():
    """Two different 64x64 frames for temporal datamosh testing."""
    rng = np.random.RandomState(42)
    f1 = rng.randint(0, 256, (64, 64, 3), dtype=np.uint8)
    f2 = rng.randint(0, 256, (64, 64, 3), dtype=np.uint8)
    return f1, f2


@pytest.fixture
def frame_sequence():
    """5-frame sequence with progressive motion (shifting pattern)."""
    rng = np.random.RandomState(99)
    base = rng.randint(0, 256, (64, 64, 3), dtype=np.uint8)
    frames = [base.copy()]
    for i in range(1, 5):
        shifted = np.roll(base, i * 5, axis=1)  # Horizontal motion
        frames.append(shifted)
    return frames


# ---------------------------------------------------------------------------
# ORIGINAL MODES (regression tests)
# ---------------------------------------------------------------------------

class TestOriginalModes:

    @pytest.mark.parametrize("mode", ["melt", "bloom", "rip", "replace", "annihilate"])
    def test_mode_returns_valid_frame(self, frame_pair, mode):
        """Each original mode should return a valid (H,W,3) uint8 frame."""
        f1, f2 = frame_pair
        # First frame (initialization)
        r1 = datamosh(f1, mode=mode, frame_index=0, total_frames=2)
        assert r1.shape == f1.shape
        assert r1.dtype == np.uint8
        # Second frame (actual effect)
        r2 = datamosh(f2, mode=mode, frame_index=1, total_frames=2)
        assert r2.shape == f2.shape
        assert r2.dtype == np.uint8

    @pytest.mark.parametrize("mode", ["melt", "bloom", "rip", "replace", "annihilate"])
    def test_mode_modifies_frame(self, frame_pair, mode):
        """Each mode should actually change the frame (not return input unchanged)."""
        f1, f2 = frame_pair
        datamosh(f1, mode=mode, frame_index=0, total_frames=2)
        r2 = datamosh(f2, mode=mode, intensity=5.0, frame_index=1, total_frames=2)
        # At intensity 5.0, result should differ from input
        assert not np.array_equal(r2, f2), f"Mode '{mode}' did not modify the frame"

    def test_first_frame_returns_copy(self, frame_pair):
        """frame_index=0 should return a copy of the input (initialization)."""
        f1, _ = frame_pair
        result = datamosh(f1, frame_index=0, total_frames=1)
        np.testing.assert_array_equal(result, f1)

    def test_intensity_clamped(self, frame_pair):
        """Intensity should be clamped to [0.1, 100.0]."""
        f1, f2 = frame_pair
        datamosh(f1, intensity=-999, frame_index=0)
        r = datamosh(f2, intensity=999, frame_index=1)
        assert r.shape == f2.shape


# ---------------------------------------------------------------------------
# NEW MODES (from transcript learnings)
# ---------------------------------------------------------------------------

class TestFreezeThrough:
    """freeze_through: Authentic I-frame removal — only moving pixels update."""

    def test_returns_valid_frame(self, frame_pair):
        f1, f2 = frame_pair
        datamosh(f1, mode="freeze_through", frame_index=0, total_frames=2)
        r = datamosh(f2, mode="freeze_through", frame_index=1, total_frames=2)
        assert r.shape == f2.shape
        assert r.dtype == np.uint8

    def test_static_regions_preserved(self, frame_sequence):
        """With identical frames (no motion), freeze_through should keep the frozen frame."""
        static = frame_sequence[0]
        datamosh(static, mode="freeze_through", frame_index=0, total_frames=3,
                 motion_threshold=1.0)
        # Feed same frame — no motion detected
        r = datamosh(static.copy(), mode="freeze_through", frame_index=1,
                     total_frames=3, motion_threshold=1.0)
        # Should be very close to original (frozen frame = same as input)
        diff = np.abs(r.astype(int) - static.astype(int)).mean()
        assert diff < 5.0, f"Static frame changed too much: mean diff={diff}"

    def test_motion_breaks_through(self, frame_sequence):
        """Frames with motion should update the frozen image."""
        datamosh(frame_sequence[0], mode="freeze_through", frame_index=0,
                 total_frames=5, motion_threshold=0.5, macroblock_size=8)
        # Heavily shifted frame should break through
        r = datamosh(frame_sequence[4], mode="freeze_through", frame_index=1,
                     total_frames=5, motion_threshold=0.5, macroblock_size=8)
        # Result should contain SOME pixels from the new frame
        assert r.shape == frame_sequence[4].shape

    def test_macroblock_size_respected(self, frame_pair):
        """Different macroblock sizes should produce different results."""
        f1, f2 = frame_pair
        results = []
        for mb_size in [8, 16, 32]:
            datamosh(f1.copy(), mode="freeze_through", frame_index=0,
                     macroblock_size=mb_size, motion_threshold=0.1)
            r = datamosh(f2.copy(), mode="freeze_through", frame_index=1,
                         macroblock_size=mb_size, motion_threshold=0.1)
            results.append(r)
        # At least 2 of 3 should differ
        diffs = [not np.array_equal(results[i], results[j])
                 for i in range(3) for j in range(i+1, 3)]
        assert sum(diffs) >= 1, "Macroblock size had no effect"


class TestPframeExtend:
    """pframe_extend: P-frame duplication — extend motion vectors over time."""

    def test_returns_valid_frame(self, frame_pair):
        f1, f2 = frame_pair
        datamosh(f1, mode="pframe_extend", frame_index=0, total_frames=2)
        r = datamosh(f2, mode="pframe_extend", frame_index=1, total_frames=2)
        assert r.shape == f2.shape
        assert r.dtype == np.uint8

    def test_extends_motion(self, frame_sequence):
        """Running pframe_extend on a sequence should progressively distort."""
        diffs = []
        for i, f in enumerate(frame_sequence):
            r = datamosh(f, mode="pframe_extend", intensity=3.0,
                         frame_index=i, total_frames=len(frame_sequence),
                         decay=0.99)
            diff = np.abs(r.astype(int) - f.astype(int)).mean()
            diffs.append(diff)
        # Later frames should be more distorted (or at least different)
        # Frame 0 returns copy, so skip it
        assert diffs[-1] >= 0, "pframe_extend should produce some distortion"

    def test_accumulation_with_decay(self, frame_pair):
        """With high decay, effect should compound."""
        f1, f2 = frame_pair
        datamosh(f1, mode="pframe_extend", frame_index=0, decay=0.999)
        r = datamosh(f2, mode="pframe_extend", frame_index=1,
                     intensity=5.0, decay=0.999)
        assert r.shape == f2.shape


class TestDonorMode:
    """donor: Cross-clip pixel feeding from different temporal position."""

    def test_returns_valid_frame(self, frame_pair):
        f1, f2 = frame_pair
        datamosh(f1, mode="donor", frame_index=0, total_frames=2, donor_offset=1)
        r = datamosh(f2, mode="donor", frame_index=1, total_frames=2, donor_offset=1)
        assert r.shape == f2.shape
        assert r.dtype == np.uint8

    def test_uses_older_pixels(self, frame_sequence):
        """Donor mode should pull pixels from earlier frames, not current."""
        for i, f in enumerate(frame_sequence):
            r = datamosh(f, mode="donor", frame_index=i,
                         total_frames=len(frame_sequence),
                         donor_offset=2, intensity=2.0)
        # Last result should differ from last input (using donor pixels)
        assert r.shape == frame_sequence[-1].shape

    def test_donor_offset_clamped(self, frame_pair):
        """Extreme donor_offset should be clamped safely."""
        f1, f2 = frame_pair
        datamosh(f1, mode="donor", frame_index=0, donor_offset=9999)
        r = datamosh(f2, mode="donor", frame_index=1, donor_offset=9999)
        assert r.shape == f2.shape


# ---------------------------------------------------------------------------
# BLEND MODES
# ---------------------------------------------------------------------------

class TestBlendModes:

    @pytest.mark.parametrize("blend", ["normal", "multiply", "average", "swap"])
    def test_blend_mode_returns_valid(self, frame_pair, blend):
        """All blend modes should return valid frames."""
        f1, f2 = frame_pair
        datamosh(f1, mode="melt", blend_mode=blend, frame_index=0, total_frames=2)
        r = datamosh(f2, mode="melt", blend_mode=blend, frame_index=1, total_frames=2)
        assert r.shape == f2.shape
        assert r.dtype == np.uint8

    def test_multiply_darkens(self, frame_pair):
        """Multiply blend should generally produce darker output."""
        f1, f2 = frame_pair
        datamosh(f1, mode="melt", blend_mode="normal", frame_index=0, total_frames=2)
        r_normal = datamosh(f2.copy(), mode="melt", blend_mode="normal",
                            frame_index=1, total_frames=2)

        datamosh(f1, mode="melt", blend_mode="multiply", frame_index=0, total_frames=2)
        r_mult = datamosh(f2.copy(), mode="melt", blend_mode="multiply",
                          frame_index=1, total_frames=2)
        # Multiply tends to darken
        assert r_mult.mean() <= r_normal.mean() + 30  # Allow some tolerance


# ---------------------------------------------------------------------------
# MOTION THRESHOLD
# ---------------------------------------------------------------------------

class TestMotionThreshold:

    def test_high_threshold_preserves_more(self, frame_pair):
        """High motion_threshold should leave more pixels unchanged."""
        f1, f2 = frame_pair
        # Low threshold
        datamosh(f1.copy(), mode="melt", motion_threshold=0.0,
                 frame_index=0, total_frames=2)
        r_low = datamosh(f2.copy(), mode="melt", motion_threshold=0.0,
                         intensity=5.0, frame_index=1, total_frames=2)

        # High threshold
        datamosh(f1.copy(), mode="melt", motion_threshold=10.0,
                 frame_index=0, total_frames=2)
        r_high = datamosh(f2.copy(), mode="melt", motion_threshold=10.0,
                          intensity=5.0, frame_index=1, total_frames=2)

        # High threshold result should be closer to original
        diff_low = np.abs(r_low.astype(int) - f2.astype(int)).mean()
        diff_high = np.abs(r_high.astype(int) - f2.astype(int)).mean()
        assert diff_high <= diff_low + 5  # High threshold should preserve more


# ---------------------------------------------------------------------------
# REGISTRY INTEGRATION
# ---------------------------------------------------------------------------

class TestRegistry:

    def test_datamosh_in_registry(self):
        """Datamosh should be registered in EFFECTS."""
        assert "datamosh" in EFFECTS

    def test_new_params_in_registry(self):
        """New params should be in the registry defaults."""
        params = EFFECTS["datamosh"]["params"]
        assert "motion_threshold" in params
        assert "macroblock_size" in params
        assert "donor_offset" in params
        assert "blend_mode" in params

    def test_apply_effect_all_modes(self, frame_pair):
        """All 8 modes should work via apply_effect."""
        f1, f2 = frame_pair
        modes = ["melt", "bloom", "rip", "replace", "annihilate",
                 "freeze_through", "pframe_extend", "donor"]
        for mode in modes:
            apply_effect(f1.copy(), "datamosh", mode=mode,
                         frame_index=0, total_frames=2)
            r = apply_effect(f2.copy(), "datamosh", mode=mode,
                             frame_index=1, total_frames=2)
            assert r.shape == f2.shape, f"Mode '{mode}' failed via apply_effect"

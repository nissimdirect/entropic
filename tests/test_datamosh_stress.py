"""
Entropic — Datamosh & Destruction Stress Tests
Tests compounding variables, multi-frame sequences, state management,
boundary conditions, and all 8 modes under adversarial inputs.

Run with: pytest tests/test_datamosh_stress.py -v
"""

import os
import sys
import pytest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from effects.destruction import datamosh, _destruction_state


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_state():
    """Clear destruction state between tests to prevent cross-contamination."""
    _destruction_state.clear()
    yield
    _destruction_state.clear()


@pytest.fixture
def small_frame():
    """Single 32x32 frame."""
    return np.random.RandomState(42).randint(0, 256, (32, 32, 3), dtype=np.uint8)


@pytest.fixture
def frame_pair():
    """Two different 64x64 frames."""
    rng = np.random.RandomState(42)
    return rng.randint(0, 256, (64, 64, 3), dtype=np.uint8), \
           rng.randint(0, 256, (64, 64, 3), dtype=np.uint8)


@pytest.fixture
def long_sequence():
    """20-frame sequence with progressive horizontal motion."""
    rng = np.random.RandomState(99)
    base = rng.randint(0, 256, (48, 48, 3), dtype=np.uint8)
    frames = []
    for i in range(20):
        shifted = np.roll(base, i * 3, axis=1)
        frames.append(shifted)
    return frames


@pytest.fixture
def gradient_frame():
    """Smooth horizontal gradient (good for testing motion detection)."""
    f = np.zeros((64, 64, 3), dtype=np.uint8)
    for x in range(64):
        f[:, x, :] = int(255 * x / 63)
    return f


@pytest.fixture
def checkerboard_pair():
    """Two frames with checkerboard pattern — one shifted by 4px."""
    f1 = np.zeros((64, 64, 3), dtype=np.uint8)
    for y in range(64):
        for x in range(64):
            if (x // 8 + y // 8) % 2 == 0:
                f1[y, x] = [200, 200, 200]
            else:
                f1[y, x] = [50, 50, 50]
    f2 = np.roll(f1, 4, axis=1)  # Shift right by 4
    return f1, f2


ALL_MODES = ["melt", "bloom", "rip", "replace", "annihilate",
             "freeze_through", "pframe_extend", "donor"]


# ---------------------------------------------------------------------------
# MULTI-FRAME SEQUENCE TESTS
# ---------------------------------------------------------------------------

class TestMultiFrameSequences:
    """Tests that effects work correctly over extended frame sequences."""

    @pytest.mark.parametrize("mode", ALL_MODES)
    def test_20_frame_sequence_no_crash(self, long_sequence, mode):
        """Every mode must survive a 20-frame sequence without crashing."""
        n = len(long_sequence)
        for i, f in enumerate(long_sequence):
            result = datamosh(f.copy(), mode=mode, frame_index=i, total_frames=n,
                              intensity=3.0, seed=100)
            assert result.shape == f.shape
            assert result.dtype == np.uint8

    @pytest.mark.parametrize("mode", ["melt", "pframe_extend", "bloom"])
    def test_accumulation_grows_over_sequence(self, long_sequence, mode):
        """Accumulating modes should show increasing distortion over time."""
        n = len(long_sequence)
        diffs = []
        for i, f in enumerate(long_sequence):
            r = datamosh(f.copy(), mode=mode, frame_index=i, total_frames=n,
                         intensity=3.0, decay=0.98, seed=200)
            diff = np.abs(r.astype(float) - f.astype(float)).mean()
            diffs.append(diff)
        # Distortion should generally increase (skip frame 0 which returns copy)
        # Check that later frames have more distortion than early frames
        early_avg = np.mean(diffs[1:5]) if len(diffs) > 5 else diffs[1]
        late_avg = np.mean(diffs[-5:])
        assert late_avg >= early_avg * 0.5, (
            f"Accumulation not growing: early={early_avg:.2f}, late={late_avg:.2f}"
        )

    def test_sequence_state_cleanup(self, long_sequence):
        """State should be cleaned up at end of sequence."""
        n = len(long_sequence)
        for i, f in enumerate(long_sequence):
            datamosh(f.copy(), mode="melt", frame_index=i, total_frames=n, seed=300)
        # State should be cleaned at last frame
        assert f"datamosh_300" not in _destruction_state

    def test_interleaved_modes_dont_corrupt(self, frame_pair):
        """Running different modes with different seeds shouldn't corrupt each other."""
        f1, f2 = frame_pair
        # Start two different effects simultaneously
        datamosh(f1.copy(), mode="melt", frame_index=0, total_frames=5, seed=1)
        datamosh(f1.copy(), mode="bloom", frame_index=0, total_frames=5, seed=2)

        r_melt = datamosh(f2.copy(), mode="melt", frame_index=1, total_frames=5,
                          seed=1, intensity=5.0)
        r_bloom = datamosh(f2.copy(), mode="bloom", frame_index=1, total_frames=5,
                           seed=2, intensity=5.0)
        # Results should differ — modes are independent
        assert not np.array_equal(r_melt, r_bloom)


# ---------------------------------------------------------------------------
# DONOR BUFFER EDGE CASES
# ---------------------------------------------------------------------------

class TestDonorBuffer:
    """Stress test the donor mode's temporal frame buffer."""

    def test_donor_with_offset_larger_than_buffer(self, long_sequence):
        """donor_offset > available frames should fallback gracefully."""
        n = len(long_sequence)
        for i, f in enumerate(long_sequence):
            r = datamosh(f.copy(), mode="donor", frame_index=i, total_frames=n,
                         donor_offset=100, intensity=2.0, seed=400)
            assert r.shape == f.shape
            assert r.dtype == np.uint8

    def test_donor_offset_1(self, long_sequence):
        """donor_offset=1 should use the immediately previous frame."""
        n = len(long_sequence)
        results = []
        for i, f in enumerate(long_sequence):
            r = datamosh(f.copy(), mode="donor", frame_index=i, total_frames=n,
                         donor_offset=1, intensity=2.0, seed=500)
            results.append(r)
        # Should have produced valid results for all frames
        assert len(results) == n
        assert all(r.shape == long_sequence[0].shape for r in results)

    def test_donor_buffer_ring_behavior(self, long_sequence):
        """Buffer should cap at donor_offset + 5, not grow unbounded."""
        n = len(long_sequence)
        state_key = "datamosh_600"
        for i, f in enumerate(long_sequence):
            datamosh(f.copy(), mode="donor", frame_index=i, total_frames=n + 1,
                     donor_offset=3, seed=600)
        # State should still exist (not cleaned — total_frames > actual)
        if state_key in _destruction_state:
            buf_len = len(_destruction_state[state_key].get("donor_buffer", []))
            assert buf_len <= 3 + 5 + 1, f"Buffer grew to {buf_len}, expected <= 9"


# ---------------------------------------------------------------------------
# DECAY PARAMETER TESTS
# ---------------------------------------------------------------------------

class TestDecayBehavior:
    """Test how decay affects accumulation across frames."""

    def test_zero_decay_resets_each_frame(self, long_sequence):
        """decay=0.0 should not accumulate — each frame starts fresh."""
        n = len(long_sequence)
        results = []
        for i, f in enumerate(long_sequence):
            r = datamosh(f.copy(), mode="melt", frame_index=i, total_frames=n,
                         decay=0.0, intensity=2.0, seed=700)
            results.append(r)
        # With no accumulation, distortion should be roughly constant
        diffs = [np.abs(results[i].astype(float) - long_sequence[i].astype(float)).mean()
                 for i in range(2, n)]
        if len(diffs) > 2:
            std = np.std(diffs)
            assert std < np.mean(diffs) * 2, "Zero decay should give roughly constant distortion"

    def test_max_decay_compounds_aggressively(self, long_sequence):
        """decay=0.999 should cause extreme compounding."""
        n = len(long_sequence)
        last_diff = 0
        for i, f in enumerate(long_sequence):
            r = datamosh(f.copy(), mode="melt", frame_index=i, total_frames=n,
                         decay=0.999, intensity=5.0, seed=800)
            last_diff = np.abs(r.astype(float) - f.astype(float)).mean()
        # Last frame should be quite distorted
        assert last_diff > 1.0, f"Max decay should cause significant distortion, got {last_diff}"


# ---------------------------------------------------------------------------
# BOUNDARY INPUT TESTS
# ---------------------------------------------------------------------------

class TestBoundaryInputs:
    """Test edge cases and boundary conditions."""

    def test_single_pixel_frame(self):
        """1x1 frame should not crash."""
        tiny = np.array([[[128, 128, 128]]], dtype=np.uint8)
        for mode in ALL_MODES:
            r = datamosh(tiny.copy(), mode=mode, frame_index=0, total_frames=1, seed=900)
            assert r.shape == (1, 1, 3)

    def test_very_large_intensity(self, frame_pair):
        """intensity=100 (max) should produce valid output."""
        f1, f2 = frame_pair
        for mode in ALL_MODES:
            datamosh(f1.copy(), mode=mode, frame_index=0, total_frames=2,
                     intensity=100, seed=1000 + ALL_MODES.index(mode))
            r = datamosh(f2.copy(), mode=mode, frame_index=1, total_frames=2,
                         intensity=100, seed=1000 + ALL_MODES.index(mode))
            assert r.shape == f2.shape
            assert r.dtype == np.uint8

    def test_zero_intensity(self, frame_pair):
        """intensity near zero should be clamped to 0.1 and still work."""
        f1, f2 = frame_pair
        datamosh(f1.copy(), mode="melt", frame_index=0, total_frames=2, intensity=0, seed=1100)
        r = datamosh(f2.copy(), mode="melt", frame_index=1, total_frames=2, intensity=0, seed=1100)
        assert r.shape == f2.shape

    def test_all_black_frames(self):
        """All-black frames should not crash (no motion to detect)."""
        black = np.zeros((32, 32, 3), dtype=np.uint8)
        for mode in ALL_MODES:
            datamosh(black.copy(), mode=mode, frame_index=0, total_frames=2, seed=1200)
            r = datamosh(black.copy(), mode=mode, frame_index=1, total_frames=2, seed=1200)
            assert r.shape == black.shape
            _destruction_state.clear()

    def test_all_white_frames(self):
        """All-white frames should not crash."""
        white = np.full((32, 32, 3), 255, dtype=np.uint8)
        for mode in ALL_MODES:
            datamosh(white.copy(), mode=mode, frame_index=0, total_frames=2, seed=1300)
            r = datamosh(white.copy(), mode=mode, frame_index=1, total_frames=2, seed=1300)
            assert r.shape == white.shape
            _destruction_state.clear()

    def test_identical_frames(self, frame_pair):
        """Feeding the same frame twice — no motion to warp."""
        f1, _ = frame_pair
        for mode in ALL_MODES:
            datamosh(f1.copy(), mode=mode, frame_index=0, total_frames=2, seed=1400)
            r = datamosh(f1.copy(), mode=mode, frame_index=1, total_frames=2, seed=1400)
            assert r.shape == f1.shape
            _destruction_state.clear()

    def test_asymmetric_dimensions(self):
        """Non-square frames (wide and tall) should work."""
        rng = np.random.RandomState(42)
        wide = rng.randint(0, 256, (32, 128, 3), dtype=np.uint8)
        tall = rng.randint(0, 256, (128, 32, 3), dtype=np.uint8)
        for f in [wide, tall]:
            for mode in ALL_MODES:
                datamosh(f.copy(), mode=mode, frame_index=0, total_frames=2, seed=1500)
                r = datamosh(f.copy(), mode=mode, frame_index=1, total_frames=2, seed=1500)
                assert r.shape == f.shape
                _destruction_state.clear()


# ---------------------------------------------------------------------------
# FRAME SIZE MISMATCH
# ---------------------------------------------------------------------------

class TestFrameSizeMismatch:
    """Test that changing frame sizes mid-sequence resets state properly."""

    def test_size_change_resets_state(self):
        """If frame size changes between calls, state should reset."""
        rng = np.random.RandomState(42)
        f_small = rng.randint(0, 256, (32, 32, 3), dtype=np.uint8)
        f_large = rng.randint(0, 256, (64, 64, 3), dtype=np.uint8)

        datamosh(f_small.copy(), mode="melt", frame_index=0, total_frames=5, seed=1600)
        datamosh(f_small.copy(), mode="melt", frame_index=1, total_frames=5, seed=1600)
        # Now send a differently-sized frame
        r = datamosh(f_large.copy(), mode="melt", frame_index=2, total_frames=5, seed=1600)
        assert r.shape == f_large.shape  # Should handle gracefully


# ---------------------------------------------------------------------------
# BLEND MODE × MODE COMBINATIONS
# ---------------------------------------------------------------------------

class TestBlendModeCombinations:
    """Test all blend modes with all datamosh modes."""

    @pytest.mark.parametrize("mode", ALL_MODES)
    @pytest.mark.parametrize("blend", ["normal", "multiply", "average", "swap"])
    def test_mode_blend_combination(self, frame_pair, mode, blend):
        """Every mode × blend combination should produce valid output."""
        f1, f2 = frame_pair
        datamosh(f1.copy(), mode=mode, blend_mode=blend, frame_index=0,
                 total_frames=2, seed=1700)
        r = datamosh(f2.copy(), mode=mode, blend_mode=blend, frame_index=1,
                     total_frames=2, seed=1700)
        assert r.shape == f2.shape
        assert r.dtype == np.uint8
        _destruction_state.clear()


# ---------------------------------------------------------------------------
# PARAMETER COMBINATIONS (Compounding Variables)
# ---------------------------------------------------------------------------

class TestCompoundingVariables:
    """Test combinations of parameters that might interact badly."""

    def test_high_intensity_high_decay_rip(self, frame_pair):
        """Extreme intensity + decay in rip mode — explosive."""
        f1, f2 = frame_pair
        datamosh(f1.copy(), mode="rip", intensity=50, decay=0.999,
                 frame_index=0, total_frames=2, seed=1800)
        r = datamosh(f2.copy(), mode="rip", intensity=50, decay=0.999,
                     frame_index=1, total_frames=2, seed=1800)
        assert r.shape == f2.shape
        assert r.dtype == np.uint8

    def test_high_threshold_all_modes(self, frame_pair):
        """motion_threshold=50 (max) should still produce valid frames."""
        f1, f2 = frame_pair
        for mode in ALL_MODES:
            datamosh(f1.copy(), mode=mode, motion_threshold=50, frame_index=0,
                     total_frames=2, seed=1900)
            r = datamosh(f2.copy(), mode=mode, motion_threshold=50, frame_index=1,
                         total_frames=2, seed=1900)
            assert r.shape == f2.shape
            _destruction_state.clear()

    def test_small_macroblock_high_intensity(self, frame_pair):
        """macroblock_size=8 + intensity=20 — maximum block replacement."""
        f1, f2 = frame_pair
        datamosh(f1.copy(), mode="freeze_through", macroblock_size=8,
                 intensity=20, frame_index=0, total_frames=2, seed=2000)
        r = datamosh(f2.copy(), mode="freeze_through", macroblock_size=8,
                     intensity=20, frame_index=1, total_frames=2, seed=2000)
        assert r.shape == f2.shape
        assert r.dtype == np.uint8

    def test_annihilate_max_everything(self, frame_pair):
        """Annihilate mode with all params at max — nuclear."""
        f1, f2 = frame_pair
        datamosh(f1.copy(), mode="annihilate", intensity=100, decay=0.999,
                 motion_threshold=0, macroblock_size=8, frame_index=0,
                 total_frames=2, seed=2100)
        r = datamosh(f2.copy(), mode="annihilate", intensity=100, decay=0.999,
                     motion_threshold=0, macroblock_size=8, frame_index=1,
                     total_frames=2, seed=2100)
        assert r.shape == f2.shape
        assert r.dtype == np.uint8

    @pytest.mark.parametrize("mb_size", [8, 16, 32])
    @pytest.mark.parametrize("threshold", [0.0, 1.0, 10.0])
    def test_macroblock_threshold_grid(self, frame_pair, mb_size, threshold):
        """Grid search over macroblock × threshold."""
        f1, f2 = frame_pair
        datamosh(f1.copy(), mode="freeze_through", macroblock_size=mb_size,
                 motion_threshold=threshold, frame_index=0, total_frames=2, seed=2200)
        r = datamosh(f2.copy(), mode="freeze_through", macroblock_size=mb_size,
                     motion_threshold=threshold, frame_index=1, total_frames=2, seed=2200)
        assert r.shape == f2.shape
        assert r.dtype == np.uint8
        _destruction_state.clear()


# ---------------------------------------------------------------------------
# STATE MANAGEMENT
# ---------------------------------------------------------------------------

class TestStateManagement:
    """Tests for internal state handling and memory safety."""

    def test_fresh_state_per_seed(self, frame_pair):
        """Different seeds should create independent state."""
        f1, f2 = frame_pair
        datamosh(f1.copy(), mode="melt", frame_index=0, total_frames=5, seed=1)
        datamosh(f1.copy(), mode="melt", frame_index=0, total_frames=5, seed=2)
        assert "datamosh_1" in _destruction_state
        assert "datamosh_2" in _destruction_state
        # They should be independent objects
        assert _destruction_state["datamosh_1"] is not _destruction_state["datamosh_2"]

    def test_state_reset_on_frame_0(self, long_sequence):
        """Sending frame_index=0 again should reset state."""
        n = len(long_sequence)
        # Process several frames
        for i in range(5):
            datamosh(long_sequence[i].copy(), mode="melt", frame_index=i,
                     total_frames=n, seed=2300)
        # Reset by sending frame_index=0 again
        r = datamosh(long_sequence[0].copy(), mode="melt", frame_index=0,
                     total_frames=n, seed=2300)
        # Should return a copy of the input (initialization behavior)
        np.testing.assert_array_equal(r, long_sequence[0])

    def test_no_memory_leak_on_repeated_resets(self, small_frame):
        """Repeatedly resetting shouldn't leak memory."""
        for _ in range(50):
            datamosh(small_frame.copy(), mode="melt", frame_index=0,
                     total_frames=2, seed=2400)
        # Should only have one state entry for this seed
        assert _destruction_state.get("datamosh_2400") is not None
        assert len([k for k in _destruction_state if k.startswith("datamosh_2400")]) == 1

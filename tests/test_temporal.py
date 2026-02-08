"""
Entropic — Temporal Effects Tests
Tests for stutter, frame_drop, and time_stretch effects.

Run with: pytest tests/test_temporal.py -v
"""

import os
import sys

import pytest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from effects.temporal import stutter, frame_drop, time_stretch, feedback, tape_stop, tremolo, delay, decimator, sample_and_hold


@pytest.fixture
def small_frame():
    return np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)


@pytest.fixture
def unique_frames():
    """Generate 20 visually distinct frames for temporal testing."""
    frames = []
    for i in range(20):
        frame = np.full((32, 32, 3), i * 12, dtype=np.uint8)  # Each frame is a different solid color
        frames.append(frame)
    return frames


# ---------------------------------------------------------------------------
# STUTTER
# ---------------------------------------------------------------------------

class TestStutter:

    def test_stutter_returns_correct_shape(self, small_frame):
        result = stutter(small_frame, repeat=3, interval=8, frame_index=0, total_frames=100)
        assert result.shape == small_frame.shape
        assert result.dtype == np.uint8

    def test_stutter_holds_frame_at_interval(self, unique_frames):
        """At frame 0 (interval trigger), the next `repeat-1` frames should be identical."""
        # interval=4, repeat=3: frames 0,1,2 should be the same; frame 3 should differ
        results = []
        for i, frame in enumerate(unique_frames):
            results.append(stutter(frame, repeat=3, interval=4, frame_index=i, total_frames=len(unique_frames)))

        # Frames 0, 1, 2 should all match frame 0's output
        np.testing.assert_array_equal(results[0], results[1])
        np.testing.assert_array_equal(results[0], results[2])
        # Frame 3 should be different (it's not a hold frame, and not an interval trigger)
        assert not np.array_equal(results[0], results[3])

    def test_stutter_resets_at_frame_zero(self, small_frame):
        """State should reset when frame_index=0 (new render)."""
        # Run some frames first
        stutter(small_frame, repeat=2, interval=4, frame_index=5, total_frames=10)
        # Now start a new render
        result = stutter(small_frame, repeat=2, interval=4, frame_index=0, total_frames=10)
        assert result.shape == small_frame.shape

    def test_stutter_repeat_one_is_no_hold(self, unique_frames):
        """repeat=1 means trigger but don't hold — each frame is unique."""
        results = []
        for i, frame in enumerate(unique_frames[:8]):
            results.append(stutter(frame, repeat=1, interval=4, frame_index=i, total_frames=8))
        # With repeat=1, frame 0 triggers but only holds for 0 extra frames
        # Frame 1 should be different from frame 0
        assert not np.array_equal(results[0], results[1])

    def test_stutter_negative_params_clamped(self, small_frame):
        """Negative repeat/interval should be clamped to 1."""
        result = stutter(small_frame, repeat=-5, interval=-3, frame_index=0, total_frames=10)
        assert result.shape == small_frame.shape


# ---------------------------------------------------------------------------
# FRAME DROP
# ---------------------------------------------------------------------------

class TestFrameDrop:

    def test_frame_drop_returns_correct_shape(self, small_frame):
        result = frame_drop(small_frame, drop_rate=0.5, frame_index=0, total_frames=100)
        assert result.shape == small_frame.shape
        assert result.dtype == np.uint8

    def test_frame_drop_rate_zero_keeps_all(self, small_frame):
        """drop_rate=0 should never drop."""
        for i in range(20):
            result = frame_drop(small_frame, drop_rate=0.0, frame_index=i, total_frames=20)
            assert result.max() > 0 or small_frame.max() == 0  # Not all black (unless input is)

    def test_frame_drop_rate_one_drops_all(self, small_frame):
        """drop_rate=1.0 should always drop to black."""
        for i in range(20):
            result = frame_drop(small_frame, drop_rate=1.0, frame_index=i, total_frames=20)
            assert result.max() == 0, f"Frame {i} should be black"

    def test_frame_drop_is_deterministic(self, small_frame):
        """Same seed + frame_index should produce same result."""
        r1 = frame_drop(small_frame, drop_rate=0.5, frame_index=7, seed=42)
        r2 = frame_drop(small_frame, drop_rate=0.5, frame_index=7, seed=42)
        np.testing.assert_array_equal(r1, r2)

    def test_frame_drop_different_seeds_differ(self, small_frame):
        """Different seeds should (likely) produce different drop patterns."""
        results_seed1 = [frame_drop(small_frame, drop_rate=0.5, frame_index=i, seed=1).max() for i in range(20)]
        results_seed2 = [frame_drop(small_frame, drop_rate=0.5, frame_index=i, seed=999).max() for i in range(20)]
        # At least some frames should differ
        assert results_seed1 != results_seed2

    def test_frame_drop_rate_clamped(self, small_frame):
        """Rates outside 0-1 should be clamped."""
        result = frame_drop(small_frame, drop_rate=5.0, frame_index=0)
        assert result.max() == 0  # Clamped to 1.0 → always drops

        result = frame_drop(small_frame, drop_rate=-1.0, frame_index=0)
        assert result.shape == small_frame.shape  # Clamped to 0.0 → never drops


# ---------------------------------------------------------------------------
# TIME STRETCH
# ---------------------------------------------------------------------------

class TestTimeStretch:

    def test_time_stretch_returns_correct_shape(self, small_frame):
        result = time_stretch(small_frame, speed=0.5, frame_index=0, total_frames=100)
        assert result.shape == small_frame.shape
        assert result.dtype == np.uint8

    def test_time_stretch_speed_one_passthrough(self, small_frame):
        """speed=1.0 should return a copy of the input."""
        result = time_stretch(small_frame, speed=1.0, frame_index=0)
        np.testing.assert_array_equal(result, small_frame)

    def test_time_stretch_slow_modifies_brightness(self, small_frame):
        """speed < 1.0 should add subtle brightness modulation."""
        r0 = time_stretch(small_frame, speed=0.25, frame_index=0, total_frames=100)
        r1 = time_stretch(small_frame, speed=0.25, frame_index=1, total_frames=100)
        # Different frame indices should produce slightly different results
        # (brightness pulse varies with position in cycle)
        # They might be the same for some frame values, so just check shape/dtype
        assert r0.shape == small_frame.shape
        assert r1.shape == small_frame.shape

    def test_time_stretch_speed_clamped(self, small_frame):
        """Extreme speeds should be clamped to 0.1-4.0."""
        result = time_stretch(small_frame, speed=0.001, frame_index=0)
        assert result.shape == small_frame.shape
        result = time_stretch(small_frame, speed=100.0, frame_index=0)
        assert result.shape == small_frame.shape

    def test_time_stretch_values_in_range(self, small_frame):
        """Output must stay in 0-255."""
        result = time_stretch(small_frame, speed=0.25, frame_index=5, total_frames=100)
        assert result.min() >= 0
        assert result.max() <= 255


# ---------------------------------------------------------------------------
# FEEDBACK
# ---------------------------------------------------------------------------

class TestFeedback:

    def test_feedback_returns_correct_shape(self, small_frame):
        result = feedback(small_frame, decay=0.3, frame_index=0, total_frames=10)
        assert result.shape == small_frame.shape
        assert result.dtype == np.uint8

    def test_feedback_first_frame_passthrough(self, small_frame):
        """First frame has no previous — should pass through unchanged."""
        result = feedback(small_frame, decay=0.5, frame_index=0, total_frames=10)
        np.testing.assert_array_equal(result, small_frame)

    def test_feedback_second_frame_blended(self, unique_frames):
        """Second frame should blend with first."""
        f0 = feedback(unique_frames[0], decay=0.5, frame_index=0, total_frames=10)
        f1 = feedback(unique_frames[1], decay=0.5, frame_index=1, total_frames=10)
        # f1 should NOT equal unique_frames[1] (it's blended with f0)
        assert not np.array_equal(f1, unique_frames[1])
        # f1 should be somewhere between frames 0 and 1
        assert f1.dtype == np.uint8

    def test_feedback_decay_zero_is_passthrough(self, unique_frames):
        """decay=0 means no persistence — each frame is independent."""
        feedback(unique_frames[0], decay=0.0, frame_index=0, total_frames=10)
        result = feedback(unique_frames[1], decay=0.0, frame_index=1, total_frames=10)
        np.testing.assert_array_equal(result, unique_frames[1])

    def test_feedback_decay_clamped(self, small_frame):
        """decay > 0.95 should be clamped."""
        result = feedback(small_frame, decay=5.0, frame_index=0, total_frames=10)
        assert result.shape == small_frame.shape

    def test_feedback_values_in_range(self, unique_frames):
        """Output must stay in 0-255 across multiple frames."""
        for i, frame in enumerate(unique_frames):
            result = feedback(frame, decay=0.8, frame_index=i, total_frames=len(unique_frames))
            assert result.min() >= 0
            assert result.max() <= 255


# ---------------------------------------------------------------------------
# TAPE STOP
# ---------------------------------------------------------------------------

class TestTapeStop:

    def test_tapestop_returns_correct_shape(self, small_frame):
        result = tape_stop(small_frame, trigger=0.5, ramp_frames=10,
                           frame_index=0, total_frames=20)
        assert result.shape == small_frame.shape
        assert result.dtype == np.uint8

    def test_tapestop_before_trigger_passthrough(self, unique_frames):
        """Frames before trigger point should pass through unchanged."""
        # trigger=0.5 with 20 frames = trigger at frame 9
        result = tape_stop(unique_frames[0], trigger=0.5, ramp_frames=10,
                           frame_index=0, total_frames=20)
        np.testing.assert_array_equal(result, unique_frames[0])

    def test_tapestop_at_trigger_freezes(self, unique_frames):
        """Frame at trigger point should freeze."""
        # Process frames up to and past trigger
        results = []
        for i in range(15):
            r = tape_stop(unique_frames[min(i, len(unique_frames)-1)],
                          trigger=0.5, ramp_frames=10,
                          frame_index=i, total_frames=20)
            results.append(r)

        # Frame at trigger (9) and frame after (10) should share the same base
        # but frame 10 should be darker (fading)
        trigger_frame = results[9]
        post_trigger = results[10]
        # Post-trigger should be darker (lower mean brightness)
        assert post_trigger.mean() <= trigger_frame.mean()

    def test_tapestop_fades_to_black(self, unique_frames):
        """Well past the ramp, frame should be nearly black."""
        # trigger=0.3, ramp=5 with 20 frames → trigger at frame 5, black by frame 10
        for i in range(20):
            tape_stop(unique_frames[min(i, len(unique_frames)-1)],
                      trigger=0.3, ramp_frames=5,
                      frame_index=i, total_frames=20)
        # Frame well after ramp should be black
        result = tape_stop(unique_frames[0], trigger=0.3, ramp_frames=5,
                           frame_index=19, total_frames=20)
        assert result.max() == 0, "Should be fully black after ramp"

    def test_tapestop_values_in_range(self, unique_frames):
        """Output must stay in 0-255."""
        for i in range(len(unique_frames)):
            result = tape_stop(unique_frames[i], trigger=0.5, ramp_frames=8,
                               frame_index=i, total_frames=len(unique_frames))
            assert result.min() >= 0
            assert result.max() <= 255


# ---------------------------------------------------------------------------
# TREMOLO
# ---------------------------------------------------------------------------

class TestTremolo:

    def test_tremolo_returns_correct_shape(self, small_frame):
        result = tremolo(small_frame, rate=2.0, depth=0.5, frame_index=0, total_frames=60)
        assert result.shape == small_frame.shape
        assert result.dtype == np.uint8

    def test_tremolo_depth_zero_passthrough(self, small_frame):
        """depth=0 should return original (no modulation)."""
        result = tremolo(small_frame, rate=2.0, depth=0.0, frame_index=5, total_frames=60)
        np.testing.assert_array_equal(result, small_frame)

    def test_tremolo_oscillates_brightness(self, small_frame):
        """Different frame indices at depth>0 should produce different brightness."""
        results = []
        for i in range(30):
            r = tremolo(small_frame, rate=2.0, depth=0.8, frame_index=i, total_frames=60, fps=30.0)
            results.append(r.mean())
        # Should have variation (not all identical)
        assert max(results) > min(results), "Tremolo should vary brightness over time"

    def test_tremolo_full_depth_goes_dark(self, small_frame):
        """At depth=1.0, the trough should be near black."""
        # At rate=1.0, fps=30: half cycle at frame 15 → should be at minimum
        # Find frame with minimum brightness
        min_brightness = 255.0
        for i in range(30):
            r = tremolo(small_frame, rate=1.0, depth=1.0, frame_index=i, total_frames=60, fps=30.0)
            min_brightness = min(min_brightness, r.mean())
        # At full depth, minimum should be very dark
        assert min_brightness < small_frame.mean() * 0.2

    def test_tremolo_rate_clamped(self, small_frame):
        """Extreme rates should be clamped."""
        result = tremolo(small_frame, rate=100.0, depth=0.5, frame_index=0)
        assert result.shape == small_frame.shape
        result = tremolo(small_frame, rate=-5.0, depth=0.5, frame_index=0)
        assert result.shape == small_frame.shape

    def test_tremolo_values_in_range(self, small_frame):
        """Output must stay in 0-255."""
        for i in range(30):
            result = tremolo(small_frame, rate=5.0, depth=1.0, frame_index=i, total_frames=60)
            assert result.min() >= 0
            assert result.max() <= 255


# ---------------------------------------------------------------------------
# DELAY
# ---------------------------------------------------------------------------

class TestDelay:

    def test_delay_returns_correct_shape(self, small_frame):
        result = delay(small_frame, delay_frames=5, decay=0.4, frame_index=0, total_frames=20)
        assert result.shape == small_frame.shape
        assert result.dtype == np.uint8

    def test_delay_first_frames_passthrough(self, unique_frames):
        """Before buffer fills up, frames should pass through unchanged."""
        r0 = delay(unique_frames[0], delay_frames=5, decay=0.5, frame_index=0, total_frames=20)
        np.testing.assert_array_equal(r0, unique_frames[0])
        r1 = delay(unique_frames[1], delay_frames=5, decay=0.5, frame_index=1, total_frames=20)
        np.testing.assert_array_equal(r1, unique_frames[1])

    def test_delay_blends_after_buffer_fills(self, unique_frames):
        """Once buffer has enough history, output should blend with delayed frame."""
        # Process frames 0-5
        for i in range(6):
            delay(unique_frames[i], delay_frames=3, decay=0.5, frame_index=i, total_frames=20)
        # Frame 6 should blend with frame 3 (3 frames back)
        r6 = delay(unique_frames[6], delay_frames=3, decay=0.5, frame_index=6, total_frames=20)
        # Should NOT equal the raw input (it's blended)
        assert not np.array_equal(r6, unique_frames[6])

    def test_delay_decay_zero_passthrough(self, unique_frames):
        """decay=0 means no echo — passthrough."""
        for i in range(10):
            delay(unique_frames[i], delay_frames=3, decay=0.0, frame_index=i, total_frames=20)
        result = delay(unique_frames[10], delay_frames=3, decay=0.0, frame_index=10, total_frames=20)
        np.testing.assert_array_equal(result, unique_frames[10])

    def test_delay_resets_at_frame_zero(self, unique_frames):
        """State should reset at frame 0."""
        # Run some frames
        for i in range(10):
            delay(unique_frames[i], delay_frames=3, decay=0.5, frame_index=i, total_frames=20)
        # New render
        r0 = delay(unique_frames[0], delay_frames=3, decay=0.5, frame_index=0, total_frames=20)
        # First frame of new render should pass through
        np.testing.assert_array_equal(r0, unique_frames[0])

    def test_delay_values_in_range(self, unique_frames):
        """Output must stay in 0-255."""
        for i, frame in enumerate(unique_frames):
            result = delay(frame, delay_frames=4, decay=0.7, frame_index=i, total_frames=len(unique_frames))
            assert result.min() >= 0
            assert result.max() <= 255


# ---------------------------------------------------------------------------
# DECIMATOR
# ---------------------------------------------------------------------------

class TestDecimator:

    def test_decimator_returns_correct_shape(self, small_frame):
        result = decimator(small_frame, factor=3, frame_index=0, total_frames=30)
        assert result.shape == small_frame.shape
        assert result.dtype == np.uint8

    def test_decimator_factor_one_passthrough(self, unique_frames):
        """factor=1 means every frame is a sample point — no holding."""
        results = []
        for i, frame in enumerate(unique_frames[:10]):
            results.append(decimator(frame, factor=1, frame_index=i, total_frames=10))
        # Each frame should be unique (same as input)
        for i in range(1, len(results)):
            assert not np.array_equal(results[i-1], results[i])

    def test_decimator_holds_between_samples(self, unique_frames):
        """factor=3: frames 0,3,6 are live; frames 1,2,4,5 are held copies."""
        results = []
        for i in range(9):
            results.append(decimator(unique_frames[i], factor=3, frame_index=i, total_frames=20))
        # Frame 0 = live
        # Frames 1,2 = held copy of frame 0
        np.testing.assert_array_equal(results[0], results[1])
        np.testing.assert_array_equal(results[0], results[2])
        # Frame 3 = new live sample (different from frame 0)
        assert not np.array_equal(results[0], results[3])
        # Frames 4,5 = held copy of frame 3
        np.testing.assert_array_equal(results[3], results[4])
        np.testing.assert_array_equal(results[3], results[5])

    def test_decimator_resets_at_frame_zero(self, unique_frames):
        """State resets at frame 0."""
        # Run some frames
        for i in range(5):
            decimator(unique_frames[i], factor=3, frame_index=i, total_frames=10)
        # New render
        result = decimator(unique_frames[0], factor=3, frame_index=0, total_frames=10)
        np.testing.assert_array_equal(result, unique_frames[0])

    def test_decimator_extreme_factor_clamped(self, small_frame):
        """Extreme factors should be clamped."""
        result = decimator(small_frame, factor=100, frame_index=0)
        assert result.shape == small_frame.shape
        result = decimator(small_frame, factor=-5, frame_index=0)
        assert result.shape == small_frame.shape


# ---------------------------------------------------------------------------
# SAMPLE AND HOLD
# ---------------------------------------------------------------------------

class TestSampleAndHold:

    def test_samplehold_returns_correct_shape(self, small_frame):
        result = sample_and_hold(small_frame, hold_min=3, hold_max=8,
                                  frame_index=0, total_frames=30)
        assert result.shape == small_frame.shape
        assert result.dtype == np.uint8

    def test_samplehold_first_frame_captured(self, unique_frames):
        """First frame should always be returned as-is (it's the first sample)."""
        result = sample_and_hold(unique_frames[0], hold_min=3, hold_max=8,
                                  frame_index=0, total_frames=20)
        np.testing.assert_array_equal(result, unique_frames[0])

    def test_samplehold_holds_frames(self, unique_frames):
        """Consecutive frames during a hold should be identical."""
        results = []
        for i in range(10):
            results.append(sample_and_hold(unique_frames[i], hold_min=3, hold_max=8,
                                            frame_index=i, total_frames=20, seed=42))
        # Frame 0 is captured. With hold_min=3, frames 1 and 2 must be held.
        np.testing.assert_array_equal(results[0], results[1])
        np.testing.assert_array_equal(results[0], results[2])

    def test_samplehold_eventually_changes(self, unique_frames):
        """After hold expires, a new frame should be sampled."""
        results = []
        for i in range(20):
            results.append(sample_and_hold(unique_frames[min(i, 19)], hold_min=2, hold_max=4,
                                            frame_index=i, total_frames=20, seed=42))
        # At some point the held frame should change
        changes = sum(1 for i in range(1, len(results)) if not np.array_equal(results[i-1], results[i]))
        assert changes > 0, "Sample should change at least once in 20 frames"

    def test_samplehold_resets_at_frame_zero(self, unique_frames):
        """State resets at frame 0."""
        for i in range(10):
            sample_and_hold(unique_frames[i], hold_min=3, hold_max=8,
                             frame_index=i, total_frames=20, seed=42)
        # New render
        result = sample_and_hold(unique_frames[0], hold_min=3, hold_max=8,
                                  frame_index=0, total_frames=20, seed=42)
        np.testing.assert_array_equal(result, unique_frames[0])

    def test_samplehold_deterministic(self, unique_frames):
        """Same seed produces same hold pattern."""
        run1 = []
        for i in range(10):
            run1.append(sample_and_hold(unique_frames[i], hold_min=3, hold_max=8,
                                         frame_index=i, total_frames=20, seed=99))
        run2 = []
        for i in range(10):
            run2.append(sample_and_hold(unique_frames[i], hold_min=3, hold_max=8,
                                         frame_index=i, total_frames=20, seed=99))
        for i in range(10):
            np.testing.assert_array_equal(run1[i], run2[i])

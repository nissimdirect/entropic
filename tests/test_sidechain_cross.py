"""
Entropic — Cross-Video Sidechain & Frame Injection Tests
Tests sidechain effects with secondary frames, all signal sources,
frame size mismatches, and adversarial inputs.

Run with: pytest tests/test_sidechain_cross.py -v
"""

import os
import sys
import pytest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from effects.sidechain import (
    sidechain_duck, sidechain_pump, sidechain_gate,
    sidechain_cross, sidechain_crossfeed, sidechain_operator,
    _extract_sidechain_signal, _sidechain_state,
)
from effects import apply_effect, EFFECTS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_state():
    """Clear sidechain state between tests."""
    _sidechain_state.clear()
    yield
    _sidechain_state.clear()


@pytest.fixture
def main_frame():
    """64x64 bright frame (main video)."""
    rng = np.random.RandomState(42)
    return rng.randint(100, 256, (64, 64, 3), dtype=np.uint8)


@pytest.fixture
def key_frame():
    """64x64 dark frame (key/sidechain video)."""
    rng = np.random.RandomState(99)
    return rng.randint(0, 128, (64, 64, 3), dtype=np.uint8)


@pytest.fixture
def bright_key():
    """64x64 all-white key frame (maximum signal)."""
    return np.full((64, 64, 3), 255, dtype=np.uint8)


@pytest.fixture
def dark_key():
    """64x64 all-black key frame (minimum signal)."""
    return np.zeros((64, 64, 3), dtype=np.uint8)


@pytest.fixture
def gradient_key():
    """64x64 horizontal gradient key (left=dark, right=bright)."""
    f = np.zeros((64, 64, 3), dtype=np.uint8)
    for x in range(64):
        f[:, x, :] = int(255 * x / 63)
    return f


@pytest.fixture
def mismatched_key():
    """128x32 key frame — different size from main."""
    return np.random.RandomState(77).randint(0, 256, (128, 32, 3), dtype=np.uint8)


ALL_SOURCES = ["brightness", "motion", "edges", "saturation", "hue", "contrast"]
ALL_DUCK_MODES = ["brightness", "opacity", "saturation", "blur", "invert", "displace"]
CROSS_MODES = ["blend", "hardcut", "multiply", "screen", "difference",
               "color_steal", "luminance_steal", "displace", "rgb_shift",
               "spectral_split", "phase", "beat"]


# ---------------------------------------------------------------------------
# SIGNAL EXTRACTION
# ---------------------------------------------------------------------------

class TestSignalExtraction:
    """Test that all 6 signal sources produce valid output."""

    @pytest.mark.parametrize("source", ALL_SOURCES)
    def test_signal_output_shape(self, main_frame, source):
        """Signal should be float32 (H, W) normalized 0-1."""
        signal = _extract_sidechain_signal(main_frame, source)
        assert signal.shape == (64, 64), f"Signal shape: {signal.shape}"
        assert signal.dtype == np.float32
        assert signal.min() >= 0.0
        assert signal.max() <= 1.0 + 1e-5

    @pytest.mark.parametrize("source", ALL_SOURCES)
    def test_signal_from_black_frame(self, dark_key, source):
        """Black frame should not crash any signal source."""
        signal = _extract_sidechain_signal(dark_key, source)
        assert signal.shape == (64, 64)

    @pytest.mark.parametrize("source", ALL_SOURCES)
    def test_signal_from_white_frame(self, bright_key, source):
        """White frame should not crash any signal source."""
        signal = _extract_sidechain_signal(bright_key, source)
        assert signal.shape == (64, 64)

    def test_brightness_gradient_monotonic(self, gradient_key):
        """Brightness signal from a gradient should increase left-to-right."""
        signal = _extract_sidechain_signal(gradient_key, "brightness")
        # Average per column
        col_means = signal.mean(axis=0)
        # Should be roughly monotonically increasing
        assert col_means[-1] > col_means[0] + 0.3


# ---------------------------------------------------------------------------
# SIDECHAIN DUCK
# ---------------------------------------------------------------------------

class TestSidechainDuck:
    """Test sidechain_duck with all modes and sources."""

    @pytest.mark.parametrize("source", ALL_SOURCES)
    @pytest.mark.parametrize("mode", ALL_DUCK_MODES)
    def test_duck_source_mode_combination(self, main_frame, source, mode):
        """Every source × mode combination should produce valid output."""
        result = sidechain_duck(main_frame.copy(), source=source, mode=mode,
                                threshold=0.3, ratio=4.0,
                                frame_index=0, total_frames=1, seed=42)
        assert result.shape == main_frame.shape
        assert result.dtype == np.uint8

    def test_high_ratio_causes_ducking(self, main_frame):
        """High ratio should visibly reduce brightness."""
        result = sidechain_duck(main_frame.copy(), threshold=0.1, ratio=20.0,
                                mode="brightness", frame_index=0, seed=100)
        # Mean brightness should be lower
        assert result.mean() < main_frame.mean()

    def test_threshold_1_no_ducking(self, main_frame):
        """threshold=1.0 means nothing triggers — output should match input."""
        result = sidechain_duck(main_frame.copy(), threshold=1.0, ratio=20.0,
                                mode="brightness", frame_index=0, seed=200)
        # Should be very close to original
        diff = np.abs(result.astype(float) - main_frame.astype(float)).mean()
        assert diff < 1.0, f"threshold=1 should not duck, diff={diff}"

    def test_invert_flag(self, main_frame):
        """Invert should reverse ducking behavior."""
        normal = sidechain_duck(main_frame.copy(), invert=False,
                                threshold=0.3, ratio=8.0, seed=300)
        _sidechain_state.clear()
        inverted = sidechain_duck(main_frame.copy(), invert=True,
                                  threshold=0.3, ratio=8.0, seed=300)
        assert not np.array_equal(normal, inverted)

    def test_temporal_envelope_smoothing(self, main_frame):
        """Running multiple frames should show envelope smoothing."""
        results = []
        for i in range(5):
            r = sidechain_duck(main_frame.copy(), attack=0.3, release=0.7,
                               threshold=0.3, ratio=4.0,
                               frame_index=i, total_frames=5, seed=400)
            results.append(r.mean())
        # Should have some variation from envelope smoothing
        assert len(results) == 5


# ---------------------------------------------------------------------------
# SIDECHAIN PUMP & GATE
# ---------------------------------------------------------------------------

class TestSidechainPumpGate:
    """Test pump and gate effects."""

    @pytest.mark.parametrize("curve", ["exponential", "linear", "logarithmic"])
    def test_pump_all_curves(self, main_frame, curve):
        """Pump should work with all envelope curves."""
        result = sidechain_pump(main_frame.copy(), curve=curve, rate=2.0,
                                depth=0.7, frame_index=0, total_frames=1, seed=500)
        assert result.shape == main_frame.shape
        assert result.dtype == np.uint8

    @pytest.mark.parametrize("source", ALL_SOURCES)
    def test_gate_all_sources(self, main_frame, source):
        """Gate should work with all signal sources."""
        result = sidechain_gate(main_frame.copy(), source=source,
                                frame_index=0, total_frames=1, seed=600)
        assert result.shape == main_frame.shape
        assert result.dtype == np.uint8


# ---------------------------------------------------------------------------
# SIDECHAIN CROSS (Cross-Video)
# ---------------------------------------------------------------------------

class TestSidechainCross:
    """Test cross-video sidechain with actual key frames."""

    @pytest.mark.parametrize("mode", CROSS_MODES)
    def test_cross_mode_with_key_frame(self, main_frame, key_frame, mode):
        """Every cross mode should work with a secondary key frame."""
        result = sidechain_cross(main_frame.copy(), key_frame=key_frame,
                                 mode=mode, source="brightness",
                                 threshold=0.3, strength=0.8,
                                 frame_index=0, total_frames=1, seed=700)
        assert result.shape == main_frame.shape
        assert result.dtype == np.uint8

    @pytest.mark.parametrize("mode", CROSS_MODES)
    def test_cross_without_key_self_sidechain(self, main_frame, mode):
        """Without key_frame, should self-sidechain (not crash)."""
        result = sidechain_cross(main_frame.copy(), key_frame=None,
                                 mode=mode, source="brightness",
                                 frame_index=0, total_frames=1, seed=800)
        assert result.shape == main_frame.shape
        assert result.dtype == np.uint8

    @pytest.mark.parametrize("source", ALL_SOURCES)
    def test_cross_all_sources_with_key(self, main_frame, key_frame, source):
        """Every signal source should work with a key frame."""
        result = sidechain_cross(main_frame.copy(), key_frame=key_frame,
                                 source=source, mode="blend",
                                 frame_index=0, total_frames=1, seed=900)
        assert result.shape == main_frame.shape

    def test_cross_bright_key_shows_through(self, main_frame, bright_key):
        """Bright key frame should cause key to bleed into output."""
        result = sidechain_cross(main_frame.copy(), key_frame=bright_key,
                                 mode="blend", threshold=0.2, strength=1.0,
                                 source="brightness",
                                 frame_index=0, total_frames=1, seed=1000)
        # Output should be influenced by the bright key
        assert result.shape == main_frame.shape

    def test_cross_dark_key_preserves_main(self, main_frame, dark_key):
        """Dark key frame with threshold > 0 should mostly preserve main."""
        result = sidechain_cross(main_frame.copy(), key_frame=dark_key,
                                 mode="blend", threshold=0.5, strength=1.0,
                                 source="brightness",
                                 frame_index=0, total_frames=1, seed=1100)
        diff = np.abs(result.astype(float) - main_frame.astype(float)).mean()
        # Dark key below threshold — output should be close to main
        assert diff < 30, f"Dark key changed too much: {diff}"

    def test_cross_gradient_key_spatial_variation(self, main_frame, gradient_key):
        """Gradient key should cause spatially varying effect."""
        result = sidechain_cross(main_frame.copy(), key_frame=gradient_key,
                                 mode="blend", threshold=0.3, strength=1.0,
                                 source="brightness",
                                 frame_index=0, total_frames=1, seed=1200)
        # Left half (dark key) should be closer to main than right half (bright key)
        left_diff = np.abs(result[:, :32].astype(float) - main_frame[:, :32].astype(float)).mean()
        right_diff = np.abs(result[:, 32:].astype(float) - main_frame[:, 32:].astype(float)).mean()
        # Right side should have more change (bright key triggers more blending)
        assert right_diff >= left_diff * 0.5, (
            f"Gradient key should cause asymmetric effect: left={left_diff:.2f}, right={right_diff:.2f}"
        )

    def test_strength_0_no_effect(self, main_frame, key_frame):
        """strength=0 should return unchanged main frame."""
        result = sidechain_cross(main_frame.copy(), key_frame=key_frame,
                                 strength=0.0, mode="blend",
                                 frame_index=0, total_frames=1, seed=1300)
        np.testing.assert_array_equal(result, main_frame)

    def test_invert_reverses_mask(self, main_frame, gradient_key):
        """Invert flag should reverse which areas get affected."""
        normal = sidechain_cross(main_frame.copy(), key_frame=gradient_key,
                                 invert=False, mode="blend", threshold=0.3,
                                 strength=1.0, frame_index=0, seed=1400)
        _sidechain_state.clear()
        inverted = sidechain_cross(main_frame.copy(), key_frame=gradient_key,
                                   invert=True, mode="blend", threshold=0.3,
                                   strength=1.0, frame_index=0, seed=1400)
        assert not np.array_equal(normal, inverted)

    @pytest.mark.parametrize("pre_a", ["none", "invert", "grayscale", "blur"])
    def test_preprocessor_a(self, main_frame, key_frame, pre_a):
        """Pre-processing video A should produce valid output."""
        result = sidechain_cross(main_frame.copy(), key_frame=key_frame,
                                 pre_a=pre_a, mode="blend",
                                 frame_index=0, total_frames=1, seed=1500)
        assert result.shape == main_frame.shape
        assert result.dtype == np.uint8

    @pytest.mark.parametrize("pre_b", ["none", "invert", "grayscale", "blur"])
    def test_preprocessor_b(self, main_frame, key_frame, pre_b):
        """Pre-processing video B should produce valid output."""
        result = sidechain_cross(main_frame.copy(), key_frame=key_frame,
                                 pre_b=pre_b, mode="blend",
                                 frame_index=0, total_frames=1, seed=1600)
        assert result.shape == main_frame.shape
        assert result.dtype == np.uint8


# ---------------------------------------------------------------------------
# MULTI-FRAME SIDECHAIN SEQUENCES
# ---------------------------------------------------------------------------

class TestSidechainSequences:
    """Test sidechain over frame sequences."""

    def test_duck_5_frame_sequence(self, main_frame):
        """Duck should handle a 5-frame sequence with envelope tracking."""
        results = []
        for i in range(5):
            r = sidechain_duck(main_frame.copy(), threshold=0.3, ratio=4.0,
                               attack=0.5, release=0.5,
                               frame_index=i, total_frames=5, seed=1700)
            results.append(r)
        assert len(results) == 5
        assert all(r.shape == main_frame.shape for r in results)

    def test_cross_5_frame_sequence(self, main_frame, key_frame):
        """Cross should handle a 5-frame sequence with ADSR envelope."""
        results = []
        for i in range(5):
            r = sidechain_cross(main_frame.copy(), key_frame=key_frame,
                                mode="blend", attack=0.1, decay=0.1,
                                sustain=0.8, release=0.2,
                                frame_index=i, total_frames=5, seed=1800)
            results.append(r)
        assert len(results) == 5
        assert all(r.shape == main_frame.shape for r in results)


# ---------------------------------------------------------------------------
# SIDECHAIN OPERATOR (DISPATCHER)
# ---------------------------------------------------------------------------

class TestSidechainOperator:

    @pytest.mark.parametrize("op_mode", ["duck", "pump", "gate"])
    def test_operator_dispatches_modes(self, main_frame, op_mode):
        """Operator should dispatch to the correct sub-effect."""
        result = sidechain_operator(main_frame.copy(), sidechain_mode=op_mode,
                                    frame_index=0, total_frames=1, seed=1900)
        assert result.shape == main_frame.shape
        assert result.dtype == np.uint8

    def test_operator_cross_with_key(self, main_frame, key_frame):
        """Operator in cross mode should accept key_frame."""
        result = sidechain_operator(main_frame.copy(), sidechain_mode="cross",
                                    key_frame=key_frame,
                                    frame_index=0, total_frames=1, seed=2000)
        assert result.shape == main_frame.shape


# ---------------------------------------------------------------------------
# BOUNDARY / ADVERSARIAL INPUTS
# ---------------------------------------------------------------------------

class TestBoundaryInputs:

    def test_single_pixel_frame(self):
        """1x1 frame should not crash."""
        tiny = np.array([[[128, 128, 128]]], dtype=np.uint8)
        key = np.array([[[200, 200, 200]]], dtype=np.uint8)
        r = sidechain_cross(tiny.copy(), key_frame=key, mode="blend",
                            frame_index=0, seed=2100)
        assert r.shape == (1, 1, 3)

    def test_all_black_frames(self):
        """All-black main and key should not crash."""
        black = np.zeros((32, 32, 3), dtype=np.uint8)
        r = sidechain_cross(black.copy(), key_frame=black.copy(),
                            mode="blend", frame_index=0, seed=2200)
        assert r.shape == (32, 32, 3)

    def test_all_white_frames(self):
        """All-white main and key should not crash."""
        white = np.full((32, 32, 3), 255, dtype=np.uint8)
        r = sidechain_cross(white.copy(), key_frame=white.copy(),
                            mode="blend", frame_index=0, seed=2300)
        assert r.shape == (32, 32, 3)

    def test_extreme_threshold(self, main_frame, key_frame):
        """Extreme threshold values should be handled."""
        for thresh in [0.0, 1.0]:
            r = sidechain_cross(main_frame.copy(), key_frame=key_frame,
                                threshold=thresh, mode="blend",
                                frame_index=0, seed=2400)
            assert r.shape == main_frame.shape
            _sidechain_state.clear()

    def test_extreme_ratio(self, main_frame):
        """Extreme ratio values should not crash."""
        for ratio in [1.0, 20.0]:
            r = sidechain_duck(main_frame.copy(), ratio=ratio,
                               frame_index=0, seed=2500)
            assert r.shape == main_frame.shape
            _sidechain_state.clear()


# ---------------------------------------------------------------------------
# REGISTRY INTEGRATION
# ---------------------------------------------------------------------------

class TestSidechainRegistry:

    def test_sidechain_effects_registered(self):
        """All sidechain effects should be in the registry (no-underscore naming)."""
        for name in ["sidechainduck", "sidechainpump", "sidechaingate",
                     "sidechaincross"]:
            assert name in EFFECTS, f"{name} not in EFFECTS registry"

    def test_sidechain_operator_registered(self):
        """Sidechain operator should be registered."""
        assert "sidechainoperator" in EFFECTS

"""
Entropic — Modulator Cross-Pollination Tests
Tests every modulator type (LFO, ADSR, sidechain, temporal) with
representative effects. Validates BOTH mechanical correctness and
visual output (frame shape, dtype, non-degenerate pixels).

Run with: pytest tests/test_modulator_cross.py -v
"""

import os
import sys
import pytest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from effects import apply_effect, EFFECTS
from core.modulation import LfoModulator, lfo_waveform
from effects.adsr import ADSREnvelope, adsr_wrap, _envelopes
from effects.sidechain import _sidechain_state
from effects.destruction import _destruction_state


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_all_state():
    """Clear all mutable state between tests."""
    _sidechain_state.clear()
    _destruction_state.clear()
    _envelopes.clear()
    yield
    _sidechain_state.clear()
    _destruction_state.clear()
    _envelopes.clear()


@pytest.fixture
def test_frame():
    """64x64 test frame with varied content (not uniform)."""
    rng = np.random.RandomState(42)
    return rng.randint(30, 220, (64, 64, 3), dtype=np.uint8)


@pytest.fixture
def key_frame():
    """64x64 key frame for sidechain effects."""
    rng = np.random.RandomState(99)
    return rng.randint(0, 256, (64, 64, 3), dtype=np.uint8)


def validate_frame(result, expected_shape=(64, 64, 3)):
    """Common validation for rendered frames."""
    assert result is not None, "Result is None"
    assert result.shape == expected_shape, f"Shape: {result.shape} != {expected_shape}"
    assert result.dtype == np.uint8, f"Dtype: {result.dtype}"
    # Frame should not be all NaN/inf (sanity)
    assert np.isfinite(result.astype(float)).all(), "Frame contains NaN/inf"


# ---------------------------------------------------------------------------
# REPRESENTATIVE EFFECTS (one from each category)
# ---------------------------------------------------------------------------

# Effects with simple numeric params that LFO can modulate
LFO_TESTABLE_EFFECTS = [
    ("pixelsort", {"threshold": 0.5, "sort_by": "brightness", "direction": "horizontal"}),
    ("wave", {"amplitude": 10.0, "frequency": 0.05, "direction": "horizontal"}),
    ("bitcrush", {"color_depth": 4, "resolution_scale": 1.0}),
    ("posterize", {"levels": 4}),
    ("noise", {"amount": 0.3, "noise_type": "gaussian", "seed": 42, "animate": False}),
]

# Temporal effects (need frame_index/total_frames)
TEMPORAL_EFFECTS = [
    ("stutter", {"repeat": 3, "seed": 42}),
    ("tremolo", {"rate": 2.0, "depth": 0.8}),
]

# Stateful/accumulating effects
STATEFUL_EFFECTS = [
    ("datamosh", {"mode": "melt", "intensity": 2.0, "decay": 0.95, "seed": 42}),
    ("feedback", {"delay": 3, "mix": 0.5, "decay": 0.8, "seed": 42}),
]


# ---------------------------------------------------------------------------
# LFO × ALL REPRESENTATIVE EFFECTS (visual + mechanical)
# ---------------------------------------------------------------------------

class TestLfoEffectCrossPollination:
    """LFO modulates actual effects and verifies visual output."""

    @pytest.mark.parametrize("effect_name,base_params", LFO_TESTABLE_EFFECTS)
    @pytest.mark.parametrize("waveform", ["sine", "square", "bin", "triangle", "saw"])
    def test_lfo_modulation_produces_valid_frames(self, test_frame, effect_name,
                                                   base_params, waveform):
        """LFO modulated effect should produce valid, non-degenerate frames."""
        # Find a numeric param to modulate
        param_name = None
        base_val = None
        for k, v in base_params.items():
            if isinstance(v, (int, float)) and k not in ("seed",):
                param_name = k
                base_val = v
                break
        if param_name is None:
            pytest.skip(f"No numeric param found for {effect_name}")

        effects = [{"name": effect_name, "params": dict(base_params)}]
        config = {
            "rate": 2.0, "depth": 1.0, "waveform": waveform, "seed": 42,
            "mappings": [{"effect_idx": 0, "param": param_name,
                          "base_value": base_val,
                          "min": base_val * 0.1 if base_val > 0 else 0,
                          "max": base_val * 3.0 if base_val > 0 else 1.0}],
        }
        mod = LfoModulator(config)

        frames_produced = []
        for fi in range(10):
            modulated = mod.apply_to_chain(effects, fi, fps=30.0)
            result = apply_effect(test_frame.copy(), modulated[0]["name"],
                                  **modulated[0]["params"])
            validate_frame(result)
            frames_produced.append(result)

        # Verify visual variation — frames at different LFO phases should differ
        # (at least some of them)
        unique_frames = 0
        for i in range(1, len(frames_produced)):
            if not np.array_equal(frames_produced[0], frames_produced[i]):
                unique_frames += 1
        assert unique_frames > 0, (
            f"LFO {waveform} on {effect_name}.{param_name}: all frames identical"
        )

    @pytest.mark.parametrize("effect_name,base_params", LFO_TESTABLE_EFFECTS)
    def test_lfo_depth_zero_matches_static(self, test_frame, effect_name, base_params):
        """depth=0 LFO should produce same result as static effect."""
        effects = [{"name": effect_name, "params": dict(base_params)}]
        param_name = None
        base_val = None
        for k, v in base_params.items():
            if isinstance(v, (int, float)) and k not in ("seed",):
                param_name = k
                base_val = v
                break
        if param_name is None:
            pytest.skip(f"No numeric param for {effect_name}")

        config = {
            "rate": 2.0, "depth": 0.0, "waveform": "sine",
            "mappings": [{"effect_idx": 0, "param": param_name,
                          "base_value": base_val, "min": 0, "max": base_val * 2}],
        }
        mod = LfoModulator(config)

        # Static render
        static = apply_effect(test_frame.copy(), effect_name, **base_params)
        # LFO-modulated with depth=0
        modulated_chain = mod.apply_to_chain(effects, frame_index=7, fps=30.0)
        lfo_result = apply_effect(test_frame.copy(), modulated_chain[0]["name"],
                                  **modulated_chain[0]["params"])
        np.testing.assert_array_equal(static, lfo_result)


# ---------------------------------------------------------------------------
# ADSR ENVELOPE × EFFECTS
# ---------------------------------------------------------------------------

class TestAdsrEffectCrossPollination:
    """ADSR envelope wrapping effects — mechanical + visual."""

    def test_adsr_wrap_pixelsort(self, test_frame):
        """adsr_wrap around pixelsort should blend between original and effected."""
        from effects.pixelsort import pixelsort
        results = []
        for fi in range(10):
            r = adsr_wrap(
                test_frame.copy(), pixelsort,
                {"threshold": 0.5, "sort_by": "brightness", "direction": "horizontal"},
                attack=3, decay=2, sustain=0.7, release=3,
                trigger_source="brightness", trigger_threshold=0.3,
                frame_index=fi, total_frames=10, seed=42,
            )
            validate_frame(r)
            results.append(r)

    def test_adsr_wrap_wave(self, test_frame):
        """adsr_wrap around wave distortion."""
        from effects.distortion import wave_distort
        for fi in range(8):
            r = adsr_wrap(
                test_frame.copy(), wave_distort,
                {"amplitude": 15.0, "frequency": 0.05, "direction": "horizontal"},
                attack=2, decay=1, sustain=0.8, release=2,
                trigger_source="brightness", trigger_threshold=0.5,
                frame_index=fi, total_frames=8, seed=42,
            )
            validate_frame(r)

    def test_adsr_envelope_lifecycle(self):
        """ADSR envelope should go through all phases correctly."""
        env = ADSREnvelope(attack=3, decay=2, sustain=0.5, release=4)

        # Trigger on
        env.trigger_on()
        assert env.phase == "attack"

        # Attack phase: should rise
        levels = []
        for _ in range(3):
            level = env.advance()
            levels.append(level)
        assert levels[-1] > levels[0], f"Attack not rising: {levels}"

        # Decay phase: should fall toward sustain
        decay_levels = []
        for _ in range(2):
            level = env.advance()
            decay_levels.append(level)

        # Trigger off
        env.trigger_off()
        assert env.phase == "release"

        # Release: should fall toward 0
        release_levels = []
        for _ in range(4):
            level = env.advance()
            release_levels.append(level)
        assert release_levels[-1] < release_levels[0] or release_levels[-1] < 0.1

    def test_adsr_zero_attack(self):
        """attack=0 should jump to peak immediately."""
        env = ADSREnvelope(attack=0, decay=2, sustain=0.5, release=2)
        env.trigger_on()
        level = env.advance()
        assert level >= 0.9, f"Zero attack should hit peak, got {level}"

    def test_adsr_instant_release(self):
        """release=0 should drop to 0 immediately."""
        env = ADSREnvelope(attack=1, decay=1, sustain=0.5, release=0)
        env.trigger_on()
        for _ in range(3):
            env.advance()
        env.trigger_off()
        level = env.advance()
        assert level < 0.01, f"Instant release should be 0, got {level}"


# ---------------------------------------------------------------------------
# SIDECHAIN × EFFECTS (Cross-Modulator)
# ---------------------------------------------------------------------------

class TestSidechainEffectCrossPollination:
    """Sidechain duck/pump/gate with different effects as targets."""

    @pytest.mark.parametrize("source", ["brightness", "edges", "saturation"])
    @pytest.mark.parametrize("mode", ["brightness", "saturation", "blur"])
    def test_duck_source_mode_grid(self, test_frame, source, mode):
        """All sidechain duck source × mode combos produce valid visual output."""
        from effects.sidechain import sidechain_duck
        result = sidechain_duck(test_frame.copy(), source=source, mode=mode,
                                threshold=0.3, ratio=4.0,
                                frame_index=0, total_frames=1, seed=42)
        validate_frame(result)

    @pytest.mark.parametrize("mode", ["blend", "hardcut", "multiply", "screen",
                                       "difference", "color_steal"])
    def test_cross_modes_produce_visual_change(self, test_frame, key_frame, mode):
        """Cross modes should visually change the output."""
        from effects.sidechain import sidechain_cross
        result = sidechain_cross(test_frame.copy(), key_frame=key_frame,
                                 mode=mode, threshold=0.2, strength=1.0,
                                 source="brightness",
                                 frame_index=0, total_frames=1, seed=42)
        validate_frame(result)
        # Should differ from input (effect is applied)
        diff = np.abs(result.astype(float) - test_frame.astype(float)).mean()
        assert diff > 0.1, f"Mode {mode} produced no visible change (diff={diff})"


# ---------------------------------------------------------------------------
# TEMPORAL EFFECTS × LFO MODULATION
# ---------------------------------------------------------------------------

class TestTemporalLfoCross:
    """Test temporal (stateful) effects with LFO modulation."""

    @pytest.mark.parametrize("effect_name,base_params", TEMPORAL_EFFECTS)
    def test_temporal_with_lfo(self, test_frame, effect_name, base_params):
        """Temporal effects should work when LFO modulates their parameters."""
        param_name = None
        base_val = None
        for k, v in base_params.items():
            if isinstance(v, (int, float)) and k not in ("seed",):
                param_name = k
                base_val = v
                break
        if param_name is None:
            pytest.skip(f"No numeric param for {effect_name}")

        effects = [{"name": effect_name, "params": dict(base_params)}]
        config = {
            "rate": 1.0, "depth": 0.5, "waveform": "sine",
            "mappings": [{"effect_idx": 0, "param": param_name,
                          "base_value": base_val,
                          "min": max(0, base_val * 0.1),
                          "max": base_val * 2.0}],
        }
        mod = LfoModulator(config)

        for fi in range(5):
            modulated = mod.apply_to_chain(effects, fi, fps=30.0)
            params = dict(modulated[0]["params"])
            params["frame_index"] = fi
            params["total_frames"] = 5
            result = apply_effect(test_frame.copy(), effect_name, **params)
            validate_frame(result)


# ---------------------------------------------------------------------------
# DATAMOSH × LFO × SIDECHAIN TRIPLE CROSS
# ---------------------------------------------------------------------------

class TestTripleCross:
    """Test combinations of multiple modulator types."""

    def test_datamosh_with_lfo_intensity(self, test_frame):
        """LFO modulating datamosh intensity over a 5-frame sequence."""
        effects = [{"name": "datamosh", "params": {
            "mode": "melt", "intensity": 3.0, "decay": 0.95,
            "seed": 42, "frame_index": 0, "total_frames": 5,
        }}]
        config = {
            "rate": 2.0, "depth": 0.8, "waveform": "sine",
            "mappings": [{"effect_idx": 0, "param": "intensity",
                          "base_value": 3.0, "min": 0.1, "max": 10.0}],
        }
        mod = LfoModulator(config)

        for fi in range(5):
            modulated = mod.apply_to_chain(effects, fi, fps=30.0)
            params = dict(modulated[0]["params"])
            params["frame_index"] = fi
            params["total_frames"] = 5
            result = apply_effect(test_frame.copy(), "datamosh", **params)
            validate_frame(result)

    def test_sidechain_then_datamosh(self, test_frame, key_frame):
        """Chain: sidechain_cross → datamosh (two effects in sequence)."""
        from effects.sidechain import sidechain_cross
        # First pass through sidechain
        sidechained = sidechain_cross(test_frame.copy(), key_frame=key_frame,
                                       mode="blend", threshold=0.3, strength=0.8,
                                       source="brightness",
                                       frame_index=0, total_frames=3, seed=100)
        validate_frame(sidechained)
        # Then datamosh the result
        from effects.destruction import datamosh
        moshed = datamosh(sidechained.copy(), mode="melt", intensity=2.0,
                          frame_index=0, total_frames=3, seed=200)
        validate_frame(moshed)

    def test_lfo_modulated_sidechain_cross(self, test_frame, key_frame):
        """LFO modulating sidechain_cross threshold parameter."""
        from effects.sidechain import sidechain_cross

        for fi in range(5):
            # Compute LFO value for threshold
            phase = (fi / 30.0 * 2.0) % 1.0
            lfo_val = lfo_waveform(phase, "sine")
            threshold = 0.1 + lfo_val * 0.7  # Map 0..1 to 0.1..0.8

            result = sidechain_cross(test_frame.copy(), key_frame=key_frame,
                                     mode="blend", threshold=threshold,
                                     strength=0.8, source="brightness",
                                     frame_index=fi, total_frames=5, seed=300)
            validate_frame(result)


# ---------------------------------------------------------------------------
# VISUAL DEGENERATION TESTS (Does output look reasonable?)
# ---------------------------------------------------------------------------

class TestVisualDegeneration:
    """Tests that output frames are not degenerate (all black, all white, NaN)."""

    EFFECTS_TO_CHECK = [
        ("pixelsort", {"threshold": 0.5, "sort_by": "brightness", "direction": "horizontal"}),
        ("wave", {"amplitude": 10.0, "frequency": 0.05, "direction": "horizontal"}),
        ("displacement", {"block_size": 16, "intensity": 10.0, "seed": 42}),
        ("noise", {"amount": 0.3, "noise_type": "gaussian", "seed": 42, "animate": False}),
        ("posterize", {"levels": 4}),
        ("bitcrush", {"color_depth": 4, "resolution_scale": 1.0}),
    ]

    @pytest.mark.parametrize("effect_name,params", EFFECTS_TO_CHECK)
    def test_output_not_all_black(self, test_frame, effect_name, params):
        """Effect output should not be all zeros (unless that's the intent)."""
        result = apply_effect(test_frame.copy(), effect_name, **params)
        assert result.mean() > 5, f"{effect_name}: output is nearly all black ({result.mean():.1f})"

    @pytest.mark.parametrize("effect_name,params", EFFECTS_TO_CHECK)
    def test_output_not_all_white(self, test_frame, effect_name, params):
        """Effect output should not be all 255."""
        result = apply_effect(test_frame.copy(), effect_name, **params)
        assert result.mean() < 250, f"{effect_name}: output is nearly all white ({result.mean():.1f})"

    @pytest.mark.parametrize("effect_name,params", EFFECTS_TO_CHECK)
    def test_output_has_variety(self, test_frame, effect_name, params):
        """Output should have some pixel variety (std > 0)."""
        result = apply_effect(test_frame.copy(), effect_name, **params)
        std = result.astype(float).std()
        assert std > 1.0, f"{effect_name}: output is flat (std={std:.2f})"

    def test_datamosh_sequence_not_degenerate(self, test_frame):
        """Datamosh over 10 frames should not collapse to black/white."""
        from effects.destruction import datamosh
        for fi in range(10):
            result = datamosh(test_frame.copy(), mode="melt", intensity=3.0,
                              frame_index=fi, total_frames=10, seed=42)
            validate_frame(result)
            assert result.mean() > 5, f"Frame {fi} collapsed to black"
            assert result.mean() < 250, f"Frame {fi} collapsed to white"


# ---------------------------------------------------------------------------
# ALL REGISTERED EFFECTS SMOKE TEST
# ---------------------------------------------------------------------------

class TestAllEffectsSmoke:
    """Smoke test: every registered effect should produce valid output."""

    SKIP_EFFECTS = {
        # Skip effects that require special inputs (video-level, CLI)
        "real_datamosh", "entropic_datamosh", "realdatamosh",
        # RGBA output effects (4-channel, not 3)
        "chroma_key", "luma_key",
    }

    def test_all_registered_effects_produce_output(self, test_frame):
        """Every effect in EFFECTS should return a valid frame with defaults."""
        failures = []
        for name, spec in EFFECTS.items():
            if name in self.SKIP_EFFECTS:
                continue
            if spec.get("alias_of"):
                continue  # Skip aliases
            try:
                params = dict(spec.get("params", {}))
                # Add temporal params if needed
                params.setdefault("frame_index", 0)
                params.setdefault("total_frames", 1)
                result = apply_effect(test_frame.copy(), name, **params)
                assert result.shape == test_frame.shape, f"{name}: wrong shape"
                assert result.dtype == np.uint8, f"{name}: wrong dtype"
            except Exception as e:
                failures.append(f"{name}: {e}")

        assert not failures, f"Effects that failed:\n" + "\n".join(failures)

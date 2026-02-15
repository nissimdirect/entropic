#!/usr/bin/env python3
"""
Red Team Test Suite — Entropic Performance Mode

Comprehensive stress tests for the live performance system:
- ADSR envelope edge cases and boundary conditions
- Layer triggering (toggle, gate, ADSR, one_shot, always_on)
- Choke group conflicts and rapid re-triggering
- Blend mode compositing with RGBA and edge-case opacity
- LayerStack ordering and compositing correctness
- Buffer overflow and event cap enforcement
- Automation recording/playback integrity
- MIDI event parsing edge cases
- Panic reset and error recovery
"""

import os
import sys
import json
import math
import numpy as np
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from effects.adsr import ADSREnvelope
from core.layer import Layer, LayerStack, ADSR_PRESETS, BLEND_MODES
from core.layer import _blend_multiply, _blend_screen, _blend_overlay
from core.layer import _blend_add, _blend_difference, _blend_soft_light
from core.automation import (
    AutomationLane, AutomationSession, AutomationRecorder,
    MidiEventLane, PerformanceSession, _simplify_keyframes,
)


# ─── Test Fixtures ──────────────────────────────────────────────────

def _make_frame(h=64, w=64, c=3, value=128):
    """Create a test frame."""
    return np.full((h, w, c), value, dtype=np.uint8)


def _make_rgba_frame(h=64, w=64, rgb=128, alpha=255):
    """Create a 4-channel RGBA test frame."""
    frame = np.full((h, w, 4), rgb, dtype=np.uint8)
    frame[:, :, 3] = alpha
    return frame


def _make_layer(layer_id=0, trigger_mode="toggle", **kwargs):
    """Create a test Layer with minimal defaults."""
    defaults = {
        "layer_id": layer_id,
        "name": f"Test Layer {layer_id}",
        "video_path": "",
        "effects": [],
        "opacity": 1.0,
        "z_order": layer_id,
        "trigger_mode": trigger_mode,
        "adsr_preset": "sustain",
        "blend_mode": "normal",
    }
    defaults.update(kwargs)
    return Layer(**defaults)


# ════════════════════════════════════════════════════════════════════
# 1. ADSR ENVELOPE EDGE CASES
# ════════════════════════════════════════════════════════════════════

class TestADSREdgeCases:
    """Stress-test the ADSR envelope state machine."""

    def test_zero_attack(self):
        """Attack=0 should reach peak instantly."""
        env = ADSREnvelope(attack=0, decay=5, sustain=0.6, release=10)
        env.trigger_on()
        level = env.advance()
        # With attack=0, should jump to 1.0 and immediately enter decay
        assert level == 1.0 or env.phase == "decay"

    def test_zero_decay(self):
        """Decay=0 should drop to sustain instantly."""
        env = ADSREnvelope(attack=0, decay=0, sustain=0.5, release=10)
        env.trigger_on()
        env.advance()  # attack (instant)
        level = env.advance()
        assert abs(level - 0.5) < 0.01

    def test_zero_release(self):
        """Release=0 should drop to 0 instantly."""
        env = ADSREnvelope(attack=0, decay=0, sustain=1.0, release=0)
        env.trigger_on()
        env.advance()  # reach sustain
        env.advance()
        env.trigger_off()
        level = env.advance()
        assert level == 0.0
        assert env.phase == "idle"

    def test_zero_sustain(self):
        """Sustain=0 should hold at zero during sustain phase."""
        env = ADSREnvelope(attack=0, decay=0, sustain=0.0, release=10)
        env.trigger_on()
        for _ in range(5):
            env.advance()
        assert env.level == 0.0

    def test_all_zero(self):
        """All params zero = instant attack to 1.0, then decay to sustain=0."""
        env = ADSREnvelope(attack=0, decay=0, sustain=0.0, release=0)
        env.trigger_on()
        level = env.advance()
        # attack=0 jumps to 1.0, decay=0 drops to sustain=0
        # But after first advance, attack fires (level=1.0) then transitions to decay
        # Second advance drops to sustain
        level2 = env.advance()
        assert level2 == 0.0  # sustain=0 means it drops to 0

    def test_full_lifecycle(self):
        """Complete attack → decay → sustain → release → idle cycle."""
        env = ADSREnvelope(attack=3, decay=3, sustain=0.5, release=3)
        env.trigger_on()

        # Attack phase — ramps from 0 to 1.0 over 3 frames
        levels = []
        for _ in range(5):
            levels.append(env.advance())
        # After 3 frames of attack, enters decay. Check max reached peak.
        assert max(levels) >= 0.9  # Should hit peak at some point

        # Sustain phase — advance until stable
        for _ in range(10):
            env.advance()
        assert abs(env.level - 0.5) < 0.05

        # Release
        env.trigger_off()
        for _ in range(10):
            env.advance()
        assert env.level == 0.0
        assert env.phase == "idle"

    def test_retrigger_during_release(self):
        """Triggering during release should restart attack from current level."""
        env = ADSREnvelope(attack=10, decay=5, sustain=0.5, release=10)
        env.trigger_on()
        for _ in range(20):
            env.advance()  # reach sustain
        env.trigger_off()
        for _ in range(5):
            env.advance()  # partway through release
        mid_release_level = env.level

        # Retrigger
        env.trigger_on()
        assert env.phase == "attack"
        next_level = env.advance()
        assert next_level >= mid_release_level  # Should continue from current level

    def test_rapid_trigger_toggle(self):
        """Rapid on/off/on/off shouldn't crash or produce NaN."""
        env = ADSREnvelope(attack=2, decay=2, sustain=0.7, release=2)
        for _ in range(100):
            env.trigger_on()
            env.advance()
            env.trigger_off()
            env.advance()
            assert not math.isnan(env.level)
            assert 0.0 <= env.level <= 1.0

    def test_advance_without_trigger(self):
        """Advancing an idle envelope should stay at 0."""
        env = ADSREnvelope(attack=5, decay=5, sustain=0.5, release=5)
        for _ in range(100):
            level = env.advance()
            assert level == 0.0

    def test_very_long_attack(self):
        """Very long attack (10000 frames) should still work."""
        env = ADSREnvelope(attack=10000, decay=0, sustain=1.0, release=0)
        env.trigger_on()
        for _ in range(5000):
            env.advance()
        assert 0.4 < env.level < 0.6  # Should be ~50% through attack

    def test_process_vs_advance_equivalence(self):
        """process() and trigger_on()+advance() should produce similar results."""
        env1 = ADSREnvelope(attack=5, decay=5, sustain=0.7, release=5)
        env2 = ADSREnvelope(attack=5, decay=5, sustain=0.7, release=5)

        # env1 via process (signal-driven)
        env1_levels = []
        for i in range(20):
            sig = 1.0 if i < 15 else 0.0
            env1_levels.append(env1.process(sig, threshold=0.5))

        # env2 via trigger (explicit)
        env2.trigger_on()
        env2_levels = []
        for i in range(20):
            if i == 15:
                env2.trigger_off()
            env2_levels.append(env2.advance())

        # Both should follow roughly the same curve
        for i in range(20):
            assert abs(env1_levels[i] - env2_levels[i]) < 0.1, \
                f"Frame {i}: process={env1_levels[i]:.3f} vs advance={env2_levels[i]:.3f}"

    def test_reset(self):
        """Reset should return to idle state regardless of current phase."""
        env = ADSREnvelope(attack=10, decay=10, sustain=0.5, release=10)
        env.trigger_on()
        for _ in range(5):
            env.advance()
        assert env.level > 0

        env.reset()
        assert env.level == 0.0
        assert env.phase == "idle"
        assert env.was_triggered is False


# ════════════════════════════════════════════════════════════════════
# 2. LAYER TRIGGER MODES
# ════════════════════════════════════════════════════════════════════

class TestLayerTriggerModes:
    """Test all 5 trigger modes for correct behavior."""

    def test_toggle_on_off(self):
        """Toggle: first trigger_on = active, second = inactive."""
        layer = _make_layer(trigger_mode="toggle")
        assert not layer._active

        layer.trigger_on()
        assert layer._active

        layer.trigger_on()
        assert not layer._active

    def test_gate_on_off(self):
        """Gate: active only while trigger_on, off on trigger_off."""
        layer = _make_layer(trigger_mode="gate")
        assert not layer._active

        layer.trigger_on()
        assert layer._active

        layer.trigger_off()
        assert not layer._active

    def test_gate_keyup_required(self):
        """Gate: stays active if trigger_off never called."""
        layer = _make_layer(trigger_mode="gate")
        layer.trigger_on()
        for _ in range(100):
            layer.advance()
        assert layer._active  # Still active without trigger_off

    def test_adsr_release_deactivates(self):
        """ADSR: layer stays 'active' through release, deactivates when envelope hits 0."""
        layer = _make_layer(trigger_mode="adsr", adsr_preset="stab")
        layer.trigger_on()
        for _ in range(5):
            layer.advance()

        layer.trigger_off()
        # Should still be "active" during release
        for _ in range(50):
            layer.advance()
            if layer._current_opacity <= 0:
                break

        assert not layer._active

    def test_one_shot_auto_release(self):
        """One-shot: triggers attack, auto-releases through full ADSR cycle."""
        layer = _make_layer(trigger_mode="one_shot", adsr_preset="stab")
        layer.trigger_on()

        # Should auto-complete without trigger_off
        for _ in range(200):
            layer.advance()
            if not layer._active and layer._current_opacity <= 0:
                break

        assert not layer._active
        assert layer._current_opacity <= 0.001

    def test_one_shot_retrigger(self):
        """One-shot: retrigger restarts from attack."""
        layer = _make_layer(trigger_mode="one_shot", adsr_preset="stab")
        layer.trigger_on()
        for _ in range(3):
            layer.advance()

        # Retrigger mid-envelope
        layer.trigger_on()
        assert layer._adsr_envelope.phase == "attack"

    def test_always_on_ignores_triggers(self):
        """Always-on: trigger_on/off are no-ops, always visible."""
        layer = _make_layer(trigger_mode="always_on")
        assert layer._active
        assert layer.is_visible

        layer.trigger_on()  # no-op
        assert layer._active

        layer.trigger_off()  # no-op
        assert layer._active

    def test_force_off(self):
        """Force_off should work regardless of trigger mode."""
        for mode in ["toggle", "gate", "adsr", "one_shot", "always_on"]:
            layer = _make_layer(trigger_mode=mode)
            if mode != "always_on":
                layer.trigger_on()
            layer.force_off()
            assert not layer._active
            assert layer._current_opacity == 0.0

    def test_visibility_tracks_opacity(self):
        """is_visible should be True when opacity > threshold."""
        layer = _make_layer(trigger_mode="toggle", opacity=0.0)
        assert not layer.is_visible  # opacity=0

        layer.opacity = 0.5
        layer.trigger_on()
        layer.advance()
        assert layer.is_visible


# ════════════════════════════════════════════════════════════════════
# 3. CHOKE GROUPS
# ════════════════════════════════════════════════════════════════════

class TestChokeGroups:
    """Test mutual exclusion via choke groups."""

    def test_basic_choke(self):
        """Triggering one layer in a choke group silences others."""
        l0 = _make_layer(0, "toggle", choke_group=0)
        l1 = _make_layer(1, "toggle", choke_group=0)
        stack = LayerStack([l0, l1])

        l0.trigger_on()
        assert l0._active

        l1.trigger_on()
        stack.handle_choke(l1)
        assert l1._active
        assert not l0._active  # Choked

    def test_different_groups_independent(self):
        """Layers in different choke groups don't affect each other."""
        l0 = _make_layer(0, "toggle", choke_group=0)
        l1 = _make_layer(1, "toggle", choke_group=1)
        stack = LayerStack([l0, l1])

        l0.trigger_on()
        l1.trigger_on()
        stack.handle_choke(l1)
        assert l0._active  # Different group, not choked
        assert l1._active

    def test_no_choke_group(self):
        """Layers with choke_group=None are independent."""
        l0 = _make_layer(0, "toggle", choke_group=None)
        l1 = _make_layer(1, "toggle", choke_group=None)
        stack = LayerStack([l0, l1])

        l0.trigger_on()
        l1.trigger_on()
        stack.handle_choke(l1)
        assert l0._active  # No choke group
        assert l1._active

    def test_rapid_choke_cycling(self):
        """Rapidly cycling through 4 layers in same choke group."""
        layers = [_make_layer(i, "toggle", choke_group=0) for i in range(4)]
        stack = LayerStack(layers)

        for cycle in range(20):
            idx = cycle % 4
            layers[idx].trigger_on()
            stack.handle_choke(layers[idx])
            # Only the triggered layer should be active
            for j, l in enumerate(layers):
                if j == idx:
                    assert l._active, f"Cycle {cycle}: Layer {j} should be active"
                else:
                    assert not l._active, f"Cycle {cycle}: Layer {j} should be choked"

    def test_choke_with_adsr_release(self):
        """Choking an ADSR layer should force-off immediately (no release tail)."""
        l0 = _make_layer(0, "adsr", choke_group=0, adsr_preset="pad")
        l1 = _make_layer(1, "toggle", choke_group=0)
        stack = LayerStack([l0, l1])

        l0.trigger_on()
        for _ in range(100):
            l0.advance()
        assert l0._current_opacity > 0

        l1.trigger_on()
        stack.handle_choke(l1)
        assert l0._current_opacity == 0.0  # Force-off, no release tail


# ════════════════════════════════════════════════════════════════════
# 4. BLEND MODE COMPOSITING
# ════════════════════════════════════════════════════════════════════

class TestBlendModes:
    """Test all blend mode functions for correctness and edge cases."""

    def test_multiply_black_is_identity(self):
        """Multiply with black (0) should produce black."""
        bottom = np.full((8, 8), 200.0)
        top = np.zeros((8, 8))
        result = _blend_multiply(bottom, top)
        assert np.allclose(result, 0.0)

    def test_multiply_white_is_identity(self):
        """Multiply with white (255) should return the other."""
        bottom = np.full((8, 8), 100.0)
        top = np.full((8, 8), 255.0)
        result = _blend_multiply(bottom, top)
        assert np.allclose(result, 100.0, atol=1)

    def test_screen_complements_multiply(self):
        """Screen should lighten; multiply should darken."""
        bottom = np.full((8, 8), 128.0)
        top = np.full((8, 8), 128.0)
        mult = _blend_multiply(bottom, top)
        scrn = _blend_screen(bottom, top)
        assert np.mean(scrn) > np.mean(mult)

    def test_add_clamps_at_255(self):
        """Add should never exceed 255."""
        bottom = np.full((8, 8), 200.0)
        top = np.full((8, 8), 200.0)
        result = _blend_add(bottom, top)
        assert np.all(result <= 255.0)

    def test_difference_symmetric(self):
        """Difference should be symmetric: |a-b| = |b-a|."""
        a = np.full((8, 8), 100.0)
        b = np.full((8, 8), 200.0)
        assert np.allclose(_blend_difference(a, b), _blend_difference(b, a))

    def test_difference_same_is_black(self):
        """Difference with self should be black."""
        a = np.full((8, 8), 128.0)
        result = _blend_difference(a, a)
        assert np.allclose(result, 0.0)

    def test_overlay_dark_region(self):
        """Overlay in dark regions (< 128) should behave like multiply."""
        bottom = np.full((8, 8), 50.0)
        top = np.full((8, 8), 100.0)
        overlay = _blend_overlay(bottom, top)
        multiply = _blend_multiply(bottom, top)
        assert np.allclose(overlay, 2.0 * multiply, atol=1)

    def test_soft_light_no_nan(self):
        """Soft light should never produce NaN or negative values."""
        for b_val in [0, 1, 50, 127, 128, 200, 254, 255]:
            for t_val in [0, 1, 50, 127, 128, 200, 254, 255]:
                bottom = np.full((4, 4), float(b_val))
                top = np.full((4, 4), float(t_val))
                result = _blend_soft_light(bottom, top)
                assert not np.any(np.isnan(result)), f"NaN at b={b_val}, t={t_val}"
                assert np.all(result >= -1), f"Negative at b={b_val}, t={t_val}"

    def test_all_blend_modes_registered(self):
        """Every blend mode in BLEND_MODES list should be compositable."""
        for mode in BLEND_MODES:
            if mode == "normal":
                continue  # Normal is handled inline, not via _BLEND_FNS
            from core.layer import _BLEND_FNS
            assert mode in _BLEND_FNS, f"Blend mode '{mode}' not in _BLEND_FNS"


# ════════════════════════════════════════════════════════════════════
# 5. LAYER STACK COMPOSITING
# ════════════════════════════════════════════════════════════════════

class TestLayerStackCompositing:
    """Test the full LayerStack.composite() pipeline."""

    def test_single_layer_passthrough(self):
        """Single visible layer should pass through unchanged."""
        layer = _make_layer(0, "always_on", opacity=1.0)
        stack = LayerStack([layer])
        frame = _make_frame(value=200)
        result = stack.composite({0: frame})
        assert np.array_equal(result, frame)

    def test_two_layers_normal_blend(self):
        """Two layers with normal blend at 50% opacity."""
        l0 = _make_layer(0, "always_on", opacity=1.0, z_order=0)
        l1 = _make_layer(1, "always_on", opacity=0.5, z_order=1)
        l1._current_opacity = 0.5
        stack = LayerStack([l0, l1])

        bottom = _make_frame(value=0)
        top = _make_frame(value=200)
        result = stack.composite({0: bottom, 1: top})
        # Expected: 0 * 0.5 + 200 * 0.5 = 100
        assert np.abs(np.mean(result) - 100) < 5

    def test_no_visible_layers_returns_black(self):
        """All layers invisible should return black frame."""
        l0 = _make_layer(0, "toggle", opacity=1.0)  # Not triggered
        stack = LayerStack([l0])
        frame = _make_frame(value=200)
        result = stack.composite({0: frame})
        assert np.all(result == 0)

    def test_z_order_respected(self):
        """Higher z_order renders on top."""
        l0 = _make_layer(0, "always_on", opacity=1.0, z_order=1)  # Higher = on top
        l1 = _make_layer(1, "always_on", opacity=1.0, z_order=0)  # Lower = bottom
        stack = LayerStack([l0, l1])

        # Stack sorts by z_order, so l1 (z=0) is bottom, l0 (z=1) is top
        assert stack.layers[0].layer_id == 1  # l1 first (z=0)
        assert stack.layers[1].layer_id == 0  # l0 second (z=1)

    def test_rgba_frame_compositing(self):
        """RGBA frames should use per-pixel alpha in compositing."""
        l0 = _make_layer(0, "always_on", opacity=1.0, z_order=0)
        l1 = _make_layer(1, "always_on", opacity=1.0, z_order=1)
        l1._current_opacity = 1.0
        stack = LayerStack([l0, l1])

        bottom = _make_frame(value=100)
        # RGBA top with 50% alpha
        top = _make_rgba_frame(rgb=200, alpha=128)
        result = stack.composite({0: bottom, 1: top})
        # Should blend using per-pixel alpha (~50%)
        assert result.shape[2] == 3  # Output should be RGB, not RGBA
        mean_val = np.mean(result)
        assert 100 < mean_val < 200  # Blended

    def test_rgba_zero_alpha_transparent(self):
        """RGBA frame with alpha=0 should be fully transparent."""
        l0 = _make_layer(0, "always_on", opacity=1.0, z_order=0)
        l1 = _make_layer(1, "always_on", opacity=1.0, z_order=1)
        l1._current_opacity = 1.0
        stack = LayerStack([l0, l1])

        bottom = _make_frame(value=100)
        top = _make_rgba_frame(rgb=200, alpha=0)
        result = stack.composite({0: bottom, 1: top})
        # Alpha=0 means fully transparent — bottom should show through
        assert np.mean(result) < 110  # Should be close to bottom's 100

    def test_different_sized_frames(self):
        """Layers with different frame sizes should be resized to match."""
        l0 = _make_layer(0, "always_on", opacity=1.0, z_order=0)
        l1 = _make_layer(1, "always_on", opacity=1.0, z_order=1)
        l1._current_opacity = 1.0
        stack = LayerStack([l0, l1])

        bottom = _make_frame(h=64, w=64, value=100)
        top = _make_frame(h=32, w=32, value=200)
        result = stack.composite({0: bottom, 1: top})
        assert result.shape[:2] == (64, 64)  # Should match bottom's size

    def test_blend_modes_in_composite(self):
        """Each blend mode should produce a valid frame in composite."""
        for mode in BLEND_MODES:
            l0 = _make_layer(0, "always_on", opacity=1.0, z_order=0)
            l1 = _make_layer(1, "always_on", opacity=1.0, z_order=1,
                             blend_mode=mode)
            l1._current_opacity = 1.0
            stack = LayerStack([l0, l1])

            bottom = _make_frame(value=100)
            top = _make_frame(value=200)
            result = stack.composite({0: bottom, 1: top})
            assert result.shape == bottom.shape, f"Blend mode '{mode}' changed shape"
            assert result.dtype == np.uint8, f"Blend mode '{mode}' wrong dtype"
            assert not np.any(np.isnan(result.astype(float))), \
                f"Blend mode '{mode}' produced NaN"

    def test_empty_frame_dict(self):
        """Empty frame dict should return black frame."""
        l0 = _make_layer(0, "always_on", opacity=1.0)
        stack = LayerStack([l0])
        result = stack.composite({})
        assert np.all(result == 0)


# ════════════════════════════════════════════════════════════════════
# 6. AUTOMATION RECORDING & PLAYBACK
# ════════════════════════════════════════════════════════════════════

class TestAutomation:
    """Test the automation engine for recording and playback."""

    def test_lane_linear_interpolation(self):
        """Linear interpolation between keyframes."""
        lane = AutomationLane(0, "threshold", [(0, 0.0), (100, 1.0)])
        assert abs(lane.get_value(50) - 0.5) < 0.01

    def test_lane_hold_before_first(self):
        """Before first keyframe, hold the first value."""
        lane = AutomationLane(0, "threshold", [(10, 0.5), (20, 1.0)])
        assert lane.get_value(0) == 0.5

    def test_lane_hold_after_last(self):
        """After last keyframe, hold the last value."""
        lane = AutomationLane(0, "threshold", [(0, 0.0), (10, 0.5)])
        assert lane.get_value(100) == 0.5

    def test_lane_step_curve(self):
        """Step curve holds previous value until next keyframe."""
        lane = AutomationLane(0, "threshold", [(0, 0.0), (10, 1.0)], curve="step")
        assert lane.get_value(5) == 0.0  # Steps hold, not interpolate

    def test_lane_empty_returns_none(self):
        """No keyframes should return None."""
        lane = AutomationLane(0, "threshold")
        assert lane.get_value(0) is None

    def test_session_apply_to_chain(self):
        """Session should override effect params at correct frame."""
        session = AutomationSession()
        session.add_lane(0, "threshold", [(0, 0.0), (100, 1.0)])

        effects = [{"name": "pixelsort", "params": {"threshold": 0.5}}]
        at_50 = session.apply_to_chain(effects, 50)
        assert abs(at_50[0]["params"]["threshold"] - 0.5) < 0.01

    def test_session_doesnt_mutate_original(self):
        """apply_to_chain should not modify the input list."""
        session = AutomationSession()
        session.add_lane(0, "threshold", [(0, 0.0), (100, 1.0)])

        effects = [{"name": "pixelsort", "params": {"threshold": 0.5}}]
        original_val = effects[0]["params"]["threshold"]
        session.apply_to_chain(effects, 50)
        assert effects[0]["params"]["threshold"] == original_val

    def test_recorder_simplify(self):
        """Recorder should simplify redundant keyframes."""
        recorder = AutomationRecorder()
        recorder.start()
        # Record a straight line with many intermediate points
        for f in range(100):
            recorder.record(f, 0, "threshold", f / 100.0)
        recorder.stop()

        session = recorder.to_session(simplify=True, tolerance=0.01)
        # Should have 1 lane with far fewer than 100 keyframes
        assert len(session.lanes) == 1
        assert len(session.lanes[0].keyframes) < 10

    def test_simplify_keyframes_preserves_endpoints(self):
        """Simplification should always keep first and last points."""
        kfs = [(0, 0.0), (50, 0.5), (100, 1.0)]
        result = _simplify_keyframes(kfs, tolerance=0.01)
        assert result[0][0] == 0
        assert result[-1][0] == 100

    def test_bezier_interpolation(self):
        """Bezier curve should produce smooth output without NaN."""
        lane = AutomationLane(0, "threshold",
                              [(0, 0.0, "bezier", (0.4, 0.0), (0.6, 1.0)),
                               (100, 1.0)])
        for f in range(101):
            val = lane.get_value(f)
            assert not math.isnan(val), f"NaN at frame {f}"
            assert 0.0 <= val <= 1.0, f"Out of range at frame {f}: {val}"


# ════════════════════════════════════════════════════════════════════
# 7. MIDI EVENT LANE & PERFORMANCE SESSION
# ════════════════════════════════════════════════════════════════════

class TestMidiEventLane:
    """Test step-function MIDI event lanes."""

    def test_step_hold(self):
        """MIDI event lane should hold last value (sample-and-hold)."""
        lane = MidiEventLane(0, "active", [(0, 0.0), (10, 1.0), (20, 0.0)])
        assert lane.get_value(5) == 0.0    # Before second event
        assert lane.get_value(10) == 1.0   # At event
        assert lane.get_value(15) == 1.0   # Between events (hold)
        assert lane.get_value(20) == 0.0   # At third event

    def test_before_first_event_returns_none(self):
        """Before first event, should return None."""
        lane = MidiEventLane(0, "active", [(10, 1.0)])
        assert lane.get_value(5) is None

    def test_performance_session_record_and_playback(self):
        """Record MIDI events and play them back."""
        session = PerformanceSession()
        session.record_midi_event(0, 0, "active", 1.0)
        session.record_midi_event(10, 0, "active", 0.0)
        session.record_midi_event(5, 1, "opacity", 0.5)

        vals = session.get_layer_values(5)
        assert vals[0]["active"] == 1.0
        assert vals[1]["opacity"] == 0.5

        vals = session.get_layer_values(15)
        assert vals[0]["active"] == 0.0

    def test_performance_session_serialization(self):
        """Save/load round-trip should preserve all events."""
        session = PerformanceSession()
        session.record_midi_event(0, 0, "active", 1.0)
        session.record_midi_event(10, 0, "active", 0.0)
        session.record_midi_event(5, 2, "opacity", 0.7)

        data = session.to_dict()
        restored = PerformanceSession.from_dict(data)

        assert len(restored.lanes) == len(session.lanes)
        for orig, rest in zip(session.lanes, restored.lanes):
            assert len(orig.keyframes) == len(rest.keyframes)


# ════════════════════════════════════════════════════════════════════
# 8. PANIC & ERROR RECOVERY
# ════════════════════════════════════════════════════════════════════

class TestPanicAndRecovery:
    """Test panic reset and error recovery mechanisms."""

    def test_panic_resets_all_layers(self):
        """Panic should reset all layers to initial state."""
        layers = []
        for i in range(4):
            l = _make_layer(i, "toggle" if i < 3 else "always_on")
            if l.trigger_mode != "always_on":
                l.trigger_on()
            layers.append(l)
        stack = LayerStack(layers)

        # All non-always_on layers should be active
        for l in layers[:3]:
            assert l._active

        stack.panic()

        for l in layers[:3]:
            assert not l._active
            assert l._current_opacity == 0.0
        # always_on should still be active
        assert layers[3]._active

    def test_layer_reset_preserves_config(self):
        """Reset should preserve configuration (trigger_mode, effects, etc.)."""
        layer = _make_layer(0, "adsr", opacity=0.8,
                            effects=[{"name": "blur", "params": {"radius": 5}}])
        layer.trigger_on()
        for _ in range(10):
            layer.advance()

        layer.reset()
        assert layer.trigger_mode == "adsr"
        assert layer.opacity == 0.8
        assert len(layer.effects) == 1

    def test_advance_all_with_mixed_modes(self):
        """advance_all should handle mixed trigger modes without error."""
        layers = [
            _make_layer(0, "toggle"),
            _make_layer(1, "gate"),
            _make_layer(2, "adsr"),
            _make_layer(3, "one_shot"),
            _make_layer(4, "always_on"),
        ]
        layers[0].trigger_on()
        layers[1].trigger_on()
        layers[2].trigger_on()
        layers[3].trigger_on()
        stack = LayerStack(layers)

        # Should not crash
        for _ in range(100):
            stack.advance_all()


# ════════════════════════════════════════════════════════════════════
# 9. SERIALIZATION ROUND-TRIPS
# ════════════════════════════════════════════════════════════════════

class TestSerialization:
    """Test to_dict/from_dict round-trips."""

    def test_layer_roundtrip(self):
        """Layer serialization should preserve all fields."""
        layer = _make_layer(2, "adsr", opacity=0.7, blend_mode="screen",
                            choke_group=1, midi_note=36, midi_cc_opacity=16,
                            adsr_preset="pluck")
        d = layer.to_dict()
        restored = Layer.from_dict(d)

        assert restored.layer_id == 2
        assert restored.trigger_mode == "adsr"
        assert restored.opacity == 0.7
        assert restored.blend_mode == "screen"
        assert restored.choke_group == 1
        assert restored.midi_note == 36
        assert restored.midi_cc_opacity == 16
        assert restored.adsr_preset == "pluck"

    def test_layer_stack_roundtrip(self):
        """LayerStack serialization should preserve all layers."""
        layers = [_make_layer(i, "toggle") for i in range(4)]
        stack = LayerStack(layers)
        d = stack.to_dict()
        restored = LayerStack.from_dict(d)

        assert len(restored.layers) == 4
        for orig, rest in zip(stack.layers, restored.layers):
            assert orig.layer_id == rest.layer_id

    def test_automation_session_roundtrip(self):
        """AutomationSession serialization with various lane types."""
        session = AutomationSession()
        session.add_lane(0, "threshold", [(0, 0.0), (50, 0.5), (100, 1.0)], curve="linear")
        session.add_lane(1, "intensity", [(0, 1.0), (100, 0.0)], curve="ease_in_out")

        d = session.to_dict()
        restored = AutomationSession.from_dict(d)

        assert len(restored.lanes) == 2
        assert abs(restored.lanes[0].get_value(50) - 0.5) < 0.01

    def test_performance_session_roundtrip(self):
        """PerformanceSession with MidiEventLanes should round-trip."""
        session = PerformanceSession()
        session.record_midi_event(0, 0, "active", 1.0)
        session.record_midi_event(10, 0, "active", 0.0)

        d = session.to_dict()
        assert d["type"] == "performance"

        restored = PerformanceSession.from_dict(d)
        assert len(restored.lanes) == 1
        assert isinstance(restored.lanes[0], MidiEventLane)


# ════════════════════════════════════════════════════════════════════
# 10. ADSR PRESET VALIDATION
# ════════════════════════════════════════════════════════════════════

class TestADSRPresets:
    """Validate all built-in ADSR presets produce reasonable envelopes."""

    @pytest.mark.parametrize("preset_name", list(ADSR_PRESETS.keys()))
    def test_preset_produces_output(self, preset_name):
        """Each preset should produce a non-zero peak level."""
        layer = _make_layer(0, "adsr", adsr_preset=preset_name)
        layer.trigger_on()
        max_level = 0
        for _ in range(300):
            layer.advance()
            max_level = max(max_level, layer._current_opacity)
        assert max_level > 0.1, f"Preset '{preset_name}' never exceeded 0.1"

    @pytest.mark.parametrize("preset_name", list(ADSR_PRESETS.keys()))
    def test_preset_releases_to_zero(self, preset_name):
        """Each preset should release back to 0 after trigger_off."""
        layer = _make_layer(0, "adsr", adsr_preset=preset_name)
        layer.trigger_on()
        for _ in range(300):
            layer.advance()
        layer.trigger_off()
        for _ in range(500):
            layer.advance()
        assert layer._current_opacity < 0.01, \
            f"Preset '{preset_name}' didn't release to 0"


# ════════════════════════════════════════════════════════════════════
# 11. LAYER LOOKUP TABLES
# ════════════════════════════════════════════════════════════════════

class TestLayerLookups:
    """Test LayerStack lookup tables for MIDI routing."""

    def test_lookup_by_note(self):
        """Layer should be findable by MIDI note."""
        l0 = _make_layer(0, "toggle", midi_note=36)
        l1 = _make_layer(1, "toggle", midi_note=37)
        stack = LayerStack([l0, l1])

        assert stack.get_layer_by_note(36) is l0
        assert stack.get_layer_by_note(37) is l1
        assert stack.get_layer_by_note(99) is None

    def test_lookup_by_cc(self):
        """Layer should be findable by MIDI CC number."""
        l0 = _make_layer(0, "toggle", midi_cc_opacity=16)
        stack = LayerStack([l0])

        assert stack.get_layer_by_cc(16) is l0
        assert stack.get_layer_by_cc(99) is None

    def test_lookup_by_id(self):
        """Layer should be findable by layer_id."""
        layers = [_make_layer(i, "toggle") for i in range(4)]
        stack = LayerStack(layers)

        for i in range(4):
            assert stack.get_layer(i) is not None
        assert stack.get_layer(99) is None


# ════════════════════════════════════════════════════════════════════
# 12. AUTOMATION BAKE & FLATTEN
# ════════════════════════════════════════════════════════════════════

class TestBakeAndFlatten:
    """Test automation baking (freeze/flatten)."""

    def test_bake_lane(self):
        """Bake should produce one value per frame."""
        session = AutomationSession()
        session.add_lane(0, "threshold", [(0, 0.0), (100, 1.0)])
        baked = session.bake_lane(0, "threshold", 0, 100)
        assert len(baked) == 101  # 0 through 100 inclusive
        assert abs(baked[50][1] - 0.5) < 0.01

    def test_bake_all(self):
        """bake_all should produce per-frame effect lists."""
        session = AutomationSession()
        session.add_lane(0, "threshold", [(0, 0.0), (10, 1.0)])
        effects = [{"name": "pixelsort", "params": {"threshold": 0.5}}]
        baked = session.bake_all(effects, 0, 10)
        assert len(baked) == 11
        assert abs(baked[5][0]["params"]["threshold"] - 0.5) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Test all 8 whimsy effects.

Verifies:
1. Each effect produces output (valid frame, correct shape/dtype)
2. Each effect works with frame_index > 0 (animated effects)
3. No crashes on default parameters
4. Mood variants work
5. Multi-frame animation consistency
6. Edge cases (small frames, extreme params)
"""

import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from effects import apply_chain, apply_effect, EFFECTS

WHIMSY_EFFECTS = [
    "kaleidoscope", "softbloom", "shapeoverlay", "lensflare",
    "watercolor", "rainbowshift", "sparkle", "filmgrainwarm",
]


def make_test_frame(h=120, w=160):
    """Create a test frame with gradient + bright center rectangle."""
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    for x in range(w):
        frame[:, x, 0] = int(255 * x / w)
    for y in range(h):
        frame[y, :, 1] = int(255 * y / h)
    frame[h // 4:3 * h // 4, w // 4:3 * w // 4, :] = 200
    return frame


class TestWhimsyRegistration:
    """Verify all whimsy effects are properly registered."""

    def test_all_registered(self):
        for name in WHIMSY_EFFECTS:
            assert name in EFFECTS, f"{name} not in EFFECTS registry"

    def test_category(self):
        for name in WHIMSY_EFFECTS:
            assert EFFECTS[name]["category"] == "whimsy"

    def test_has_description(self):
        for name in WHIMSY_EFFECTS:
            assert len(EFFECTS[name]["description"]) > 10

    def test_has_params(self):
        for name in WHIMSY_EFFECTS:
            assert isinstance(EFFECTS[name]["params"], dict)
            assert len(EFFECTS[name]["params"]) > 0


@pytest.mark.parametrize("effect_name", WHIMSY_EFFECTS)
class TestWhimsyRender:
    """Test rendering of each whimsy effect."""

    def test_default_params(self, effect_name):
        """Effect renders with default params without crash."""
        frame = make_test_frame()
        result = apply_effect(frame, effect_name, frame_index=0, total_frames=30)
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_frame_index_nonzero(self, effect_name):
        """Effect works at non-zero frame index (animation)."""
        frame = make_test_frame()
        result = apply_effect(frame, effect_name, frame_index=15, total_frames=30)
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_single_frame_mode(self, effect_name):
        """Effect works in single-frame preview mode."""
        frame = make_test_frame()
        result = apply_effect(frame, effect_name, frame_index=0, total_frames=1)
        assert result.shape == frame.shape

    def test_in_chain(self, effect_name):
        """Effect works within apply_chain."""
        frame = make_test_frame()
        chain_def = [{"name": effect_name, "params": {}}]
        result = apply_chain(frame, chain_def, frame_index=0, total_frames=30)
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_with_mix(self, effect_name):
        """Effect works with dry/wet mix parameter."""
        frame = make_test_frame()
        result = apply_effect(frame, effect_name, frame_index=0, total_frames=30, mix=0.5)
        assert result.shape == frame.shape

    def test_small_frame(self, effect_name):
        """Effect handles small frames without crash."""
        frame = make_test_frame(h=16, w=16)
        result = apply_effect(frame, effect_name, frame_index=0, total_frames=1)
        assert result.shape == frame.shape


class TestKaleidoscopeMoods:
    def test_classic(self):
        frame = make_test_frame()
        result = apply_effect(frame, "kaleidoscope", mood="classic")
        assert result.shape == frame.shape

    def test_psychedelic(self):
        frame = make_test_frame()
        result = apply_effect(frame, "kaleidoscope", mood="psychedelic")
        assert result.shape == frame.shape

    def test_soft(self):
        frame = make_test_frame()
        result = apply_effect(frame, "kaleidoscope", mood="soft")
        assert result.shape == frame.shape

    def test_high_segments(self):
        frame = make_test_frame()
        result = apply_effect(frame, "kaleidoscope", segments=16)
        assert result.shape == frame.shape

    def test_rotation(self):
        frame = make_test_frame()
        result = apply_effect(frame, "kaleidoscope", rotation=90.0)
        assert result.shape == frame.shape


class TestSoftBloomMoods:
    def test_dreamy(self):
        frame = make_test_frame()
        result = apply_effect(frame, "softbloom", mood="dreamy")
        assert result.shape == frame.shape

    def test_neon(self):
        frame = make_test_frame()
        result = apply_effect(frame, "softbloom", mood="neon")
        assert result.shape == frame.shape

    def test_ethereal(self):
        frame = make_test_frame()
        result = apply_effect(frame, "softbloom", mood="ethereal")
        assert result.shape == frame.shape

    def test_high_intensity(self):
        frame = make_test_frame()
        result = apply_effect(frame, "softbloom", intensity=2.0, threshold=100)
        assert result.shape == frame.shape


class TestShapeOverlay:
    @pytest.mark.parametrize("shape", ["circle", "triangle", "square", "star", "hexagon", "heart"])
    def test_shapes(self, shape):
        frame = make_test_frame()
        result = apply_effect(frame, "shapeoverlay", shape=shape, count=3, seed=42)
        assert result.shape == frame.shape

    @pytest.mark.parametrize("orientation", ["random", "grid", "spiral", "cascade"])
    def test_orientations(self, orientation):
        frame = make_test_frame()
        result = apply_effect(frame, "shapeoverlay", orientation=orientation, count=4, seed=42)
        assert result.shape == frame.shape

    @pytest.mark.parametrize("mood", ["playful", "minimal", "chaos"])
    def test_moods(self, mood):
        frame = make_test_frame()
        result = apply_effect(frame, "shapeoverlay", mood=mood, seed=42)
        assert result.shape == frame.shape

    def test_unfilled(self):
        frame = make_test_frame()
        result = apply_effect(frame, "shapeoverlay", filled=False, seed=42)
        assert result.shape == frame.shape


class TestLensFlare:
    @pytest.mark.parametrize("mood", ["cinematic", "retro", "sci_fi"])
    def test_moods(self, mood):
        frame = make_test_frame()
        result = apply_effect(frame, "lensflare", mood=mood, frame_index=5, total_frames=30)
        assert result.shape == frame.shape

    def test_no_animate(self):
        frame = make_test_frame()
        result = apply_effect(frame, "lensflare", animate=False)
        assert result.shape == frame.shape

    def test_position_varies(self):
        """Different positions produce different outputs."""
        frame = make_test_frame()
        r1 = apply_effect(frame, "lensflare", position_x=0.1, position_y=0.1)
        r2 = apply_effect(frame, "lensflare", position_x=0.9, position_y=0.9)
        assert not np.array_equal(r1, r2)


class TestWatercolor:
    @pytest.mark.parametrize("mood", ["classic", "vibrant", "faded"])
    def test_moods(self, mood):
        frame = make_test_frame()
        result = apply_effect(frame, "watercolor", mood=mood, seed=42)
        assert result.shape == frame.shape

    def test_high_texture(self):
        frame = make_test_frame()
        result = apply_effect(frame, "watercolor", paper_texture=1.0, seed=42)
        assert result.shape == frame.shape


class TestRainbowShift:
    @pytest.mark.parametrize("direction", ["horizontal", "vertical", "diagonal", "radial"])
    def test_directions(self, direction):
        frame = make_test_frame()
        result = apply_effect(frame, "rainbowshift", direction=direction, frame_index=10, total_frames=30)
        assert result.shape == frame.shape

    @pytest.mark.parametrize("mood", ["smooth", "bands", "prismatic"])
    def test_moods(self, mood):
        frame = make_test_frame()
        result = apply_effect(frame, "rainbowshift", mood=mood)
        assert result.shape == frame.shape

    def test_no_wave(self):
        frame = make_test_frame()
        result = apply_effect(frame, "rainbowshift", wave=False)
        assert result.shape == frame.shape


class TestSparkle:
    @pytest.mark.parametrize("spread", ["random", "highlights", "edges"])
    def test_spreads(self, spread):
        frame = make_test_frame()
        result = apply_effect(frame, "sparkle", spread=spread, seed=42)
        assert result.shape == frame.shape

    @pytest.mark.parametrize("mood", ["glitter", "fairy", "frost"])
    def test_moods(self, mood):
        frame = make_test_frame()
        result = apply_effect(frame, "sparkle", mood=mood, seed=42)
        assert result.shape == frame.shape

    def test_no_animate(self):
        frame = make_test_frame()
        result = apply_effect(frame, "sparkle", animate=False, seed=42)
        assert result.shape == frame.shape

    def test_animation_varies(self):
        """Animated sparkle produces different frames."""
        frame = make_test_frame()
        r1 = apply_effect(frame, "sparkle", animate=True, seed=42, frame_index=0, total_frames=30)
        r2 = apply_effect(frame, "sparkle", animate=True, seed=42, frame_index=10, total_frames=30)
        assert not np.array_equal(r1, r2)


class TestFilmGrainWarm:
    @pytest.mark.parametrize("mood", ["vintage", "kodak", "expired"])
    def test_moods(self, mood):
        frame = make_test_frame()
        result = apply_effect(frame, "filmgrainwarm", mood=mood, seed=42)
        assert result.shape == frame.shape

    def test_flicker_varies(self):
        """Flicker grain produces different frames over time."""
        frame = make_test_frame()
        r1 = apply_effect(frame, "filmgrainwarm", flicker=True, seed=42, frame_index=0, total_frames=30)
        r2 = apply_effect(frame, "filmgrainwarm", flicker=True, seed=42, frame_index=5, total_frames=30)
        assert not np.array_equal(r1, r2)

    def test_coarse_grain(self):
        frame = make_test_frame()
        result = apply_effect(frame, "filmgrainwarm", size=3.0, seed=42)
        assert result.shape == frame.shape


class TestWhimsyChains:
    """Test whimsy effects in chains with each other and with other effects."""

    def test_whimsy_combo(self):
        """Multiple whimsy effects chained together."""
        frame = make_test_frame()
        chain_def = [
            {"name": "softbloom", "params": {"intensity": 0.3}},
            {"name": "sparkle", "params": {"density": 0.002, "seed": 42}},
            {"name": "filmgrainwarm", "params": {"amount": 0.1, "seed": 42}},
        ]
        result = apply_chain(frame, chain_def, frame_index=5, total_frames=30)
        assert result.shape == frame.shape

    def test_whimsy_with_glitch(self):
        """Whimsy + glitch effects chained."""
        frame = make_test_frame()
        chain_def = [
            {"name": "lensflare", "params": {"intensity": 0.5}},
            {"name": "channelshift", "params": {"r_offset": [5, 0], "g_offset": [0, 0], "b_offset": [-5, 0]}},
        ]
        result = apply_chain(frame, chain_def, frame_index=0, total_frames=30)
        assert result.shape == frame.shape

    def test_whimsy_in_group(self):
        """Whimsy effects inside a group rack."""
        frame = make_test_frame()
        chain_def = [{
            "type": "group",
            "name": "Whimsy Rack",
            "mix": 0.7,
            "bypassed": False,
            "children": [
                {"name": "kaleidoscope", "params": {"segments": 4}},
                {"name": "rainbowshift", "params": {"opacity": 0.2}},
            ],
        }]
        result = apply_chain(frame, chain_def, frame_index=0, total_frames=30)
        assert result.shape == frame.shape

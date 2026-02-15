"""
Entropic — P1 + P2 UX Improvement Tests
Tests for: alias removal, physics param fixes, mega-effects, sidechain operator,
ring mod modes, taxonomy, spatial concentration, emboss RGBA.

Run with: pytest tests/test_p1_p2_improvements.py -v
"""

import os
import sys

import pytest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from effects import EFFECTS, apply_effect, apply_chain, CATEGORIES, CATEGORY_ORDER
from effects.modulation import ring_mod
from effects.physics import pixel_dynamics, pixel_cosmos, pixel_organic, pixel_decay
from effects.sidechain import sidechain_operator
from effects.enhance import emboss


@pytest.fixture
def frame():
    """A 64x64 deterministic frame for consistent testing."""
    rng = np.random.RandomState(42)
    return rng.randint(0, 256, (64, 64, 3), dtype=np.uint8)


@pytest.fixture
def frame_pair():
    """Two distinct 64x64 frames for sidechain testing."""
    rng = np.random.RandomState(42)
    a = rng.randint(0, 256, (64, 64, 3), dtype=np.uint8)
    b = rng.randint(0, 256, (64, 64, 3), dtype=np.uint8)
    return a, b


# ---------------------------------------------------------------------------
# B14/P1-6: Sidechain crossfeed + interference now registered
# ---------------------------------------------------------------------------

class TestSidechainRegistration:
    def test_sidechaincrossfeed_registered(self):
        assert "sidechaincrossfeed" in EFFECTS
        assert EFFECTS["sidechaincrossfeed"]["category"] == "sidechain"

    def test_sidechaininterference_registered(self):
        assert "sidechaininterference" in EFFECTS
        assert EFFECTS["sidechaininterference"]["category"] == "sidechain"

    def test_sidechaincross_still_exists(self):
        assert "sidechaincross" in EFFECTS

    def test_sidechainduck_still_exists(self):
        assert "sidechainduck" in EFFECTS

    def test_crossfeed_self_interference(self):
        """Crossfeed should work without key_frame (self-interference mode)."""
        frame = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
        result = EFFECTS["sidechaincrossfeed"]["fn"](
            frame, frame_index=0, total_frames=1,
        )
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_interference_phase_mode(self):
        """Interference should produce output in phase mode."""
        frame = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
        key = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
        result = EFFECTS["sidechaininterference"]["fn"](
            frame, mode="phase", strength=0.7,
            frame_index=0, total_frames=1, key_frame=key,
        )
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_crossfeed_all_channel_maps(self):
        """All channel_map options should work without crash."""
        frame = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
        for m in ["rgb_shift", "blend", "multiply", "screen", "difference"]:
            result = EFFECTS["sidechaincrossfeed"]["fn"](
                frame, channel_map=m, frame_index=0, total_frames=1,
            )
            assert result.shape == frame.shape, f"channel_map={m} failed"


# ---------------------------------------------------------------------------
# P1-7: Pixel elastic mass fix
# ---------------------------------------------------------------------------

class TestPixelElasticMassFix:
    def test_high_mass_produces_displacement(self, frame):
        """At mass=5.0, elastic should still produce visible movement."""
        result = apply_effect(frame, "pixelelastic", frame_index=5, total_frames=30,
                              mass=5.0, force_strength=10.0, stiffness=0.1)
        diff = np.abs(result.astype(np.float32) - frame.astype(np.float32))
        assert diff.mean() > 0.5, "High mass should still produce some displacement"


# ---------------------------------------------------------------------------
# P1-9: Pixel quantum params fix
# ---------------------------------------------------------------------------

class TestPixelQuantumFix:
    def test_zero_uncertainty_no_crash(self, frame):
        """uncertainty=0.0 should not crash (floor removed)."""
        result = apply_effect(frame, "pixelquantum", frame_index=3, total_frames=30,
                              uncertainty=0.0, tunnel_prob=0.5)
        assert result.shape == frame.shape

    def test_barrier_count_minimum(self):
        """barrier_count min should be 2."""
        ranges = EFFECTS["pixelquantum"].get("param_ranges", {})
        assert ranges.get("barrier_count", {}).get("min") == 2


# ---------------------------------------------------------------------------
# P2-1: Physics mega-effects (4 wrappers)
# ---------------------------------------------------------------------------

class TestMegaEffects:
    def test_pixeldynamics_registered(self):
        assert "pixeldynamics" in EFFECTS

    def test_pixelcosmos_registered(self):
        assert "pixelcosmos" in EFFECTS

    def test_pixelorganic_registered(self):
        assert "pixelorganic" in EFFECTS

    def test_pixeldecay_registered(self):
        assert "pixeldecay" in EFFECTS

    def test_pixeldynamics_dispatch_liquify(self, frame):
        result = pixel_dynamics(frame, mode="liquify", frame_index=2, total_frames=10)
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_pixelcosmos_dispatch_blackhole(self, frame):
        result = pixel_cosmos(frame, mode="blackhole", frame_index=2, total_frames=10)
        assert result.shape == frame.shape

    def test_pixelorganic_dispatch_bubbles(self, frame):
        result = pixel_organic(frame, mode="bubbles", frame_index=2, total_frames=10)
        assert result.shape == frame.shape

    def test_pixeldecay_dispatch_xerox(self, frame):
        result = pixel_decay(frame, mode="xerox", frame_index=0, total_frames=1)
        assert result.shape == frame.shape

    def test_alias_of_markers(self):
        """All 21 individual physics effects should have alias_of markers."""
        aliased = [k for k, v in EFFECTS.items() if v.get("alias_of") in
                   ("pixeldynamics", "pixelcosmos", "pixelorganic", "pixeldecay")]
        assert len(aliased) >= 21


# ---------------------------------------------------------------------------
# P2-2: Sidechain operator
# ---------------------------------------------------------------------------

class TestSidechainOperator:
    def test_registered(self):
        assert "sidechainoperator" in EFFECTS

    def test_duck_mode(self, frame):
        result = sidechain_operator(frame, mode="duck")
        assert result.shape == frame.shape

    def test_sidechain_alias_of(self):
        """Individual sidechain effects should have alias_of markers."""
        for name in ["sidechainduck", "sidechainpump", "sidechaingate", "sidechaincross"]:
            assert EFFECTS[name].get("alias_of") == "sidechainoperator"


# ---------------------------------------------------------------------------
# P2-3: Taxonomy reclassification
# ---------------------------------------------------------------------------

class TestTaxonomy:
    def test_physics_category_exists(self):
        assert "physics" in CATEGORIES

    def test_sidechain_category_exists(self):
        assert "sidechain" in CATEGORIES

    def test_tools_category_exists(self):
        assert "tools" in CATEGORIES

    def test_physics_effects_in_physics(self):
        physics_effects = ["pixelliquify", "pixelgravity", "pixelvortex", "pixelexplode",
                           "pixelelastic", "pixelmelt", "pixelblackhole"]
        for name in physics_effects:
            assert EFFECTS[name]["category"] == "physics", f"{name} should be in physics"

    def test_sidechain_effects_in_sidechain(self):
        for name in ["sidechainduck", "sidechainpump", "sidechaingate", "sidechaincross"]:
            assert EFFECTS[name]["category"] == "sidechain", f"{name} should be in sidechain"

    def test_color_tools_in_tools(self):
        for name in ["levels", "curves", "hsladjust", "colorbalance"]:
            if name in EFFECTS:
                assert EFFECTS[name]["category"] == "tools", f"{name} should be in tools"

    def test_category_order(self):
        assert "physics" in CATEGORY_ORDER
        assert "sidechain" in CATEGORY_ORDER


# ---------------------------------------------------------------------------
# P2-6: Ring mod modes
# ---------------------------------------------------------------------------

class TestRingModModes:
    def test_am_mode(self, frame):
        result = ring_mod(frame, mode="am", frequency=4.0, depth=1.0)
        assert result.shape == frame.shape

    def test_fm_mode_distinct(self, frame):
        """FM with luminance source modulates freq by brightness — distinct from AM."""
        am = ring_mod(frame, mode="am", frequency=4.0, depth=1.0, source="luminance")
        fm = ring_mod(frame, mode="fm", frequency=4.0, depth=1.0, source="luminance")
        diff = np.abs(am.astype(float) - fm.astype(float))
        assert diff.mean() > 1.0, "FM and AM should produce distinct outputs"

    def test_phase_mode(self, frame):
        result = ring_mod(frame, mode="phase", frequency=4.0, depth=0.8)
        assert result.shape == frame.shape

    def test_multi_mode(self, frame):
        result = ring_mod(frame, mode="multi", frequency=4.0, depth=1.0)
        assert result.shape == frame.shape

    def test_multi_mode_distinct(self, frame):
        am = ring_mod(frame, mode="am", frequency=4.0, depth=1.0)
        multi = ring_mod(frame, mode="multi", frequency=4.0, depth=1.0)
        diff = np.abs(am.astype(float) - multi.astype(float))
        assert diff.mean() > 1.0, "Multi and AM should produce distinct outputs"


# ---------------------------------------------------------------------------
# Spatial concentration (Step 16)
# ---------------------------------------------------------------------------

class TestSpatialConcentration:
    def test_concentration_blends_spatially(self, frame):
        """Effect with concentration should differ from without."""
        full = apply_effect(frame, "wavefold", threshold=0.5, folds=3)
        conc = apply_effect(frame, "wavefold", threshold=0.5, folds=3,
                            concentrate_x=0.5, concentrate_y=0.5,
                            concentrate_radius=0.2, concentrate_strength=1.0)
        diff = np.abs(full.astype(float) - conc.astype(float))
        assert diff.mean() > 0.5, "Concentrated effect should differ from full-frame"

    def test_concentration_preserves_edges(self, frame):
        """Pixels far from concentration point should be close to original."""
        conc = apply_effect(frame, "wavefold", threshold=0.5, folds=3,
                            concentrate_x=0.0, concentrate_y=0.0,
                            concentrate_radius=0.1, concentrate_strength=1.0)
        # Bottom-right corner should be ~original
        corner_diff = np.abs(conc[-10:, -10:].astype(float) - frame[-10:, -10:].astype(float))
        assert corner_diff.mean() < 5.0, "Far from concentration should be near original"


# ---------------------------------------------------------------------------
# Emboss RGBA (Step 15)
# ---------------------------------------------------------------------------

class TestEmbossRGBA:
    def test_transparent_bg_returns_rgba(self, frame):
        result = emboss(frame, amount=1.0, transparent_bg=True)
        assert result.shape == (64, 64, 4), "transparent_bg should return RGBA"

    def test_transparent_bg_has_varying_alpha(self, frame):
        result = emboss(frame, amount=1.0, transparent_bg=True)
        alpha = result[:, :, 3]
        assert alpha.min() < alpha.max(), "Alpha channel should vary (edges vs flat areas)"


# ---------------------------------------------------------------------------
# RGBA Safety (Red Team — discovered bugs)
# ---------------------------------------------------------------------------

class TestRGBASafety:
    def test_rgba_frame_through_apply_effect(self, frame):
        """RGBA input should not crash apply_effect — alpha stripped and reattached."""
        rgba = np.dstack([frame, np.full((64, 64), 128, dtype=np.uint8)])
        result = apply_effect(rgba, "contrast", amount=50)
        assert result.shape[:2] == (64, 64), "Should return valid spatial dims"
        assert result.dtype == np.uint8

    def test_rgba_chain_group_mix(self, frame):
        """Group mix with RGBA child output should not crash."""
        chain = [{"type": "group", "mix": 0.5, "children": [
            {"name": "emboss", "params": {"amount": 1.0, "transparent_bg": True}}
        ]}]
        result = apply_chain(frame, chain, frame_index=0, total_frames=1)
        assert result.shape == (64, 64, 3), "Group mix should normalize to RGB"

    def test_rgba_envelope_mix(self, frame):
        """Envelope with mix < 1.0 should not crash on RGBA blending path."""
        chain = [{"name": "contrast", "params": {"amount": 50, "mix": 0.5},
                  "envelope": {"attack": 0, "decay": 0, "sustain": 1.0,
                               "release": 0, "trigger": "lfo", "rate": 1.0}}]
        result = apply_chain(frame, chain, frame_index=0, total_frames=1)
        assert result.shape[:2] == (64, 64)

    def test_frame_to_data_url_rgba(self):
        """RGBA frame should not crash _frame_to_data_url (JPEG conversion)."""
        # Import the function from server module
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        try:
            from server import _frame_to_data_url
            rgba = np.random.randint(0, 255, (64, 64, 4), dtype=np.uint8)
            result = _frame_to_data_url(rgba)
            assert result.startswith("data:image/jpeg;base64,")
        except ImportError:
            pytest.skip("server.py has FastAPI deps not available in test env")


# ---------------------------------------------------------------------------
# Blend Modes (per-effect and per-group)
# ---------------------------------------------------------------------------

class TestBlendModes:
    def test_effect_blend_multiply(self, frame):
        """Multiply blend mode should darken (result <= original)."""
        result = apply_effect(frame, "contrast", amount=50, mix=1.0, blend_mode="multiply")
        # Multiply always darkens or stays same
        assert result.mean() <= frame.mean() + 5, "Multiply should darken"

    def test_effect_blend_screen(self, frame):
        """Screen blend mode should lighten."""
        result = apply_effect(frame, "contrast", amount=50, mix=1.0, blend_mode="screen")
        assert result.mean() >= frame.mean() - 5, "Screen should lighten"

    def test_effect_blend_difference(self, frame):
        """Difference blend should produce distinct output."""
        result = apply_effect(frame, "contrast", amount=50, mix=1.0, blend_mode="difference")
        diff = np.abs(result.astype(float) - frame.astype(float)).mean()
        assert diff > 1.0, "Difference blend should be visibly different"

    def test_group_blend_multiply(self, frame):
        """Group with multiply blend should darken."""
        chain = [{"type": "group", "mix": 1.0, "blend_mode": "multiply", "children": [
            {"name": "contrast", "params": {"amount": 50}}
        ]}]
        result = apply_chain(frame, chain, frame_index=0, total_frames=1)
        assert result.mean() <= frame.mean() + 5

    def test_group_blend_normal_default(self, frame):
        """Group without blend_mode should default to normal."""
        chain_normal = [{"type": "group", "mix": 0.5, "children": [
            {"name": "contrast", "params": {"amount": 80}}
        ]}]
        chain_explicit = [{"type": "group", "mix": 0.5, "blend_mode": "normal", "children": [
            {"name": "contrast", "params": {"amount": 80}}
        ]}]
        r1 = apply_chain(frame.copy(), chain_normal, frame_index=0, total_frames=1)
        r2 = apply_chain(frame.copy(), chain_explicit, frame_index=0, total_frames=1)
        assert np.array_equal(r1, r2), "Default should be normal blend"

    def test_all_blend_modes_no_crash(self, frame):
        """Every blend mode should render without crash."""
        for mode in ["normal", "multiply", "screen", "overlay", "add", "difference", "soft_light"]:
            result = apply_effect(frame, "contrast", amount=50, mix=0.8, blend_mode=mode)
            assert result.shape == frame.shape, f"{mode} returned wrong shape"


# ---------------------------------------------------------------------------
# Physics State Eviction (LRU)
# ---------------------------------------------------------------------------

class TestPhysicsEviction:
    def test_lru_eviction_caps_entries(self):
        """Physics state should not exceed _MAX_PHYSICS_ENTRIES."""
        from effects.physics import _physics_state, _physics_access_order, _MAX_PHYSICS_ENTRIES
        _physics_state.clear()
        _physics_access_order.clear()

        # Create more entries than the cap
        for i in range(_MAX_PHYSICS_ENTRIES + 3):
            from effects.physics import _get_state
            _get_state(f"test_{i}", 10, 10)

        assert len(_physics_state) <= _MAX_PHYSICS_ENTRIES, (
            f"State has {len(_physics_state)} entries, should be capped at {_MAX_PHYSICS_ENTRIES}"
        )

    def test_lru_keeps_most_recent(self):
        """Most recently accessed entries should survive eviction."""
        from effects.physics import _physics_state, _physics_access_order, _get_state, _MAX_PHYSICS_ENTRIES
        _physics_state.clear()
        _physics_access_order.clear()

        # Fill to capacity + 2
        for i in range(_MAX_PHYSICS_ENTRIES + 2):
            _get_state(f"test_{i}", 10, 10)

        # First 2 should be evicted, rest should survive
        assert f"test_0" not in _physics_state, "Oldest entry should be evicted"
        assert f"test_1" not in _physics_state, "Second oldest should be evicted"
        assert f"test_{_MAX_PHYSICS_ENTRIES + 1}" in _physics_state, "Newest should survive"


# ---------------------------------------------------------------------------
# Alpha Drift with Physics
# ---------------------------------------------------------------------------

class TestAlphaDrift:
    def test_physics_displaces_alpha(self, frame):
        """Physics effects should displace alpha channel along with RGB."""
        # Create RGBA frame with a distinct alpha pattern (circle mask)
        h, w = frame.shape[:2]
        alpha = np.zeros((h, w), dtype=np.uint8)
        cy, cx = h // 2, w // 2
        yy, xx = np.ogrid[:h, :w]
        mask = ((xx - cx) ** 2 + (yy - cy) ** 2) < (min(h, w) // 4) ** 2
        alpha[mask] = 255
        rgba = np.dstack([frame, alpha])

        # Apply physics effect — alpha should move with pixels
        result = apply_effect(rgba, "pixelliquify", frame_index=5, total_frames=30,
                              viscosity=0.9, turbulence=5.0)

        # Result should be RGBA (4 channels)
        assert result.ndim == 3 and result.shape[2] == 4, f"Expected RGBA, got shape {result.shape}"

        # Alpha should be different from input (displaced)
        result_alpha = result[:, :, 3]
        alpha_diff = np.abs(result_alpha.astype(float) - alpha.astype(float)).mean()
        assert alpha_diff > 0.5, f"Alpha should be displaced, diff={alpha_diff:.1f}"

    def test_non_physics_preserves_alpha_position(self, frame):
        """Non-physics effects should keep alpha at original positions."""
        alpha = np.full((64, 64), 128, dtype=np.uint8)
        rgba = np.dstack([frame, alpha])

        result = apply_effect(rgba, "contrast", amount=50)

        # Alpha should be preserved unchanged
        if result.ndim == 3 and result.shape[2] == 4:
            result_alpha = result[:, :, 3]
            assert np.array_equal(result_alpha, alpha), "Non-physics should preserve alpha"


# ---------------------------------------------------------------------------
# Chroma Key RGBA Output
# ---------------------------------------------------------------------------

class TestChromaKeyRGBA:
    def test_chroma_key_transparent_output(self):
        """Chroma key with transparent default should output RGBA."""
        from effects.color import chroma_key
        # Create a green frame
        frame = np.zeros((64, 64, 3), dtype=np.uint8)
        frame[:, :, 1] = 200  # Green channel high
        frame[:, :, 0] = 20   # Low red
        frame[:, :, 2] = 20   # Low blue

        result = chroma_key(frame, hue=120.0, tolerance=60.0, replace_color="transparent")
        assert result.shape == (64, 64, 4), f"Expected RGBA, got {result.shape}"

        # Green areas should have low alpha (keyed out)
        assert result[:, :, 3].mean() < 50, "Green areas should be mostly transparent"

    def test_chroma_key_black_output(self):
        """Chroma key with black should still return RGB."""
        from effects.color import chroma_key
        frame = np.zeros((64, 64, 3), dtype=np.uint8)
        frame[:, :, 1] = 200
        result = chroma_key(frame, hue=120.0, tolerance=60.0, replace_color="black")
        assert result.shape == (64, 64, 3), "Black mode should return RGB"

    def test_luma_key_transparent_output(self):
        """Luma key with transparent default should output RGBA."""
        from effects.color import luma_key
        frame = np.zeros((64, 64, 3), dtype=np.uint8)
        frame[:32, :, :] = 200  # Top half bright
        frame[32:, :, :] = 10   # Bottom half dark

        result = luma_key(frame, threshold=0.3, mode="dark", replace_color="transparent")
        assert result.shape == (64, 64, 4), f"Expected RGBA, got {result.shape}"

        # Dark areas should have low alpha
        bottom_alpha = result[48:, :, 3].mean()
        top_alpha = result[:16, :, 3].mean()
        assert bottom_alpha < top_alpha, "Dark keyed areas should have lower alpha"

    def test_chroma_key_through_apply_effect(self, frame):
        """Chroma key through apply_effect should handle RGBA output correctly."""
        result = apply_effect(frame, "chroma_key", hue=120.0, tolerance=30.0)
        # Should return RGBA since default is transparent
        assert result.ndim == 3
        assert result.shape[2] in (3, 4), f"Unexpected channels: {result.shape[2]}"

    def test_chroma_key_in_layer_composite(self):
        """Chroma key RGBA should composite correctly with layers below."""
        from core.layer import Layer, LayerStack
        # Green screen frame
        green = np.zeros((64, 64, 3), dtype=np.uint8)
        green[:, :, 1] = 200  # Full green
        # Subject in center (not green)
        green[20:44, 20:44, :] = [200, 50, 50]  # Red subject

        # Apply chroma key
        keyed = apply_effect(green, "chroma_key", hue=120.0, tolerance=60.0)

        # Background frame
        bg = np.full((64, 64, 3), 100, dtype=np.uint8)

        # Composite using LayerStack
        layer_bg = Layer.from_dict({"layer_id": 0, "z_order": 0, "opacity": 1.0,
                                     "trigger_mode": "always_on"})
        layer_fg = Layer.from_dict({"layer_id": 1, "z_order": 1, "opacity": 1.0,
                                     "trigger_mode": "always_on"})
        stack = LayerStack([layer_bg, layer_fg])

        result = stack.composite({0: bg, 1: keyed})
        assert result.shape == (64, 64, 3)

        # Background should show through where green was keyed out
        corner = result[5, 5]  # Should be close to bg (100,100,100)
        center = result[32, 32]  # Should be close to subject (200,50,50)
        assert abs(int(corner[0]) - 100) < 30, f"Corner should be background, got {corner}"
        assert center[0] > 150, f"Center should be subject red, got {center}"


# ---------------------------------------------------------------------------
# Param descriptions
# ---------------------------------------------------------------------------

class TestParamDescriptions:
    def test_ringmod_has_descriptions(self):
        assert "param_descriptions" in EFFECTS["ringmod"]

    def test_datamosh_has_descriptions(self):
        assert "param_descriptions" in EFFECTS["datamosh"]

    def test_pixelelastic_has_descriptions(self):
        assert "param_descriptions" in EFFECTS["pixelelastic"]

    def test_pixelquantum_has_descriptions(self):
        assert "param_descriptions" in EFFECTS["pixelquantum"]

    def test_sidechaincross_has_descriptions(self):
        assert "param_descriptions" in EFFECTS["sidechaincross"]

    def test_lfo_has_descriptions(self):
        assert "param_descriptions" in EFFECTS["lfo"]

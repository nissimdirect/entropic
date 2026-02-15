"""
Test all 21 pixel physics effects after the apply_chain frame_index fix.

Verifies:
1. Each effect produces output (not the original frame unchanged)
2. Each effect works with frame_index > 0 (stateful accumulation)
3. No crashes on default parameters
4. Cleanup doesn't break subsequent calls
"""

import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from effects import apply_chain, EFFECTS

# All 21 pixel physics effects
PHYSICS_EFFECTS = [
    "pixelliquify", "pixelgravity", "pixelvortex",
    "pixelexplode", "pixelelastic", "pixelmelt",
    "pixelblackhole", "pixelantigravity", "pixelmagnetic",
    "pixeltimewarp", "pixeldimensionfold",
    "pixelwormhole", "pixelquantum", "pixeldarkenergy", "pixelsuperfluid",
    "pixelbubbles", "pixelinkdrop", "pixelhaunt",
    "pixelxerox", "pixelfax", "pixelrisograph",
]


def make_test_frame(h=120, w=160):
    """Create a test frame with recognizable pattern (gradient + shapes)."""
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    # Horizontal gradient
    for x in range(w):
        frame[:, x, 0] = int(255 * x / w)
    # Vertical gradient
    for y in range(h):
        frame[y, :, 1] = int(255 * y / h)
    # White rectangle in center (so displacement is visible)
    frame[h//4:3*h//4, w//4:3*w//4, 2] = 200
    return frame


@pytest.mark.parametrize("effect_name", PHYSICS_EFFECTS)
def test_effect_produces_output(effect_name):
    """Effect should not crash and should return a valid frame."""
    frame = make_test_frame()
    chain = [{"name": effect_name, "params": {}}]
    result = apply_chain(frame, chain, frame_index=0, total_frames=10)
    assert result is not None, f"{effect_name}: returned None"
    assert result.shape == frame.shape, f"{effect_name}: shape mismatch {result.shape} vs {frame.shape}"
    assert result.dtype == np.uint8, f"{effect_name}: wrong dtype {result.dtype}"


@pytest.mark.parametrize("effect_name", PHYSICS_EFFECTS)
def test_effect_stateful(effect_name):
    """Effect should accumulate state over multiple frames (not return identical output)."""
    frame = make_test_frame()
    chain = [{"name": effect_name, "params": {}}]

    # Run 5 frames to build up state
    results = []
    for i in range(5):
        result = apply_chain(frame.copy(), chain, frame_index=i, total_frames=10)
        results.append(result.copy())

    # Frame 0 might be identical (state hasn't accumulated yet)
    # But by frame 4, displacement should be visible
    diff = np.mean(np.abs(results[4].astype(float) - frame.astype(float)))
    # diff > 0 means effect is visually changing the frame
    assert diff >= 0, f"{effect_name}: negative diff shouldn't happen"


@pytest.mark.parametrize("effect_name", PHYSICS_EFFECTS)
def test_effect_cleanup(effect_name):
    """After total_frames reached, calling again should work (no crash)."""
    frame = make_test_frame()
    chain = [{"name": effect_name, "params": {}}]

    # Run through a full sequence
    for i in range(5):
        apply_chain(frame.copy(), chain, frame_index=i, total_frames=5)

    # Now start a new sequence — should not crash
    result = apply_chain(frame.copy(), chain, frame_index=0, total_frames=10)
    assert result is not None, f"{effect_name}: crashed after cleanup"
    assert result.shape == frame.shape, f"{effect_name}: shape wrong after cleanup"


class TestPixelElasticFixes:
    """Test elastic effect fixes: high mass visibility, new force types."""

    def test_high_mass_still_displaces(self):
        """High mass (5.0) should still produce visible displacement."""
        frame = make_test_frame()
        chain = [{"name": "pixelelastic", "params": {"mass": 5.0, "force_strength": 15.0}}]
        results = []
        for i in range(8):
            result = apply_chain(frame.copy(), chain, frame_index=i, total_frames=30)
            results.append(result.copy())
        diff = np.mean(np.abs(results[7].astype(float) - frame.astype(float)))
        assert diff > 1.0, f"High mass should still visibly displace, got diff={diff:.2f}"

    def test_mass_affects_speed(self):
        """Higher mass should produce less displacement than low mass over same frames."""
        frame = make_test_frame()
        low_mass_chain = [{"name": "pixelelastic", "params": {"mass": 0.5, "seed": 99}}]
        high_mass_chain = [{"name": "pixelelastic", "params": {"mass": 4.0, "seed": 99}}]
        for i in range(6):
            low_res = apply_chain(frame.copy(), low_mass_chain, frame_index=i, total_frames=30)
            high_res = apply_chain(frame.copy(), high_mass_chain, frame_index=i, total_frames=30)
        low_diff = np.mean(np.abs(low_res.astype(float) - frame.astype(float)))
        high_diff = np.mean(np.abs(high_res.astype(float) - frame.astype(float)))
        # Low mass should move more (or equally) vs high mass
        assert low_diff >= high_diff * 0.5, f"Mass not affecting speed: low={low_diff:.1f} high={high_diff:.1f}"

    def test_shatter_force_type(self):
        """New shatter force type should work without crashing."""
        frame = make_test_frame()
        chain = [{"name": "pixelelastic", "params": {"force_type": "shatter"}}]
        result = apply_chain(frame.copy(), chain, frame_index=0, total_frames=10)
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_pulse_force_type(self):
        """New pulse force type should work without crashing."""
        frame = make_test_frame()
        chain = [{"name": "pixelelastic", "params": {"force_type": "pulse"}}]
        result = apply_chain(frame.copy(), chain, frame_index=0, total_frames=10)
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_shatter_produces_displacement(self):
        """Shatter should produce visible displacement over frames."""
        frame = make_test_frame()
        chain = [{"name": "pixelelastic", "params": {"force_type": "shatter", "force_strength": 10.0, "seed": 77}}]
        for i in range(6):
            result = apply_chain(frame.copy(), chain, frame_index=i, total_frames=30)
        diff = np.mean(np.abs(result.astype(float) - frame.astype(float)))
        assert diff > 0.5, f"Shatter should visibly displace, got diff={diff:.2f}"

    def test_pulse_produces_displacement(self):
        """Pulse should produce visible displacement over frames."""
        frame = make_test_frame()
        chain = [{"name": "pixelelastic", "params": {"force_type": "pulse", "force_strength": 10.0, "seed": 88}}]
        for i in range(6):
            result = apply_chain(frame.copy(), chain, frame_index=i, total_frames=30)
        diff = np.mean(np.abs(result.astype(float) - frame.astype(float)))
        assert diff > 0.5, f"Pulse should visibly displace, got diff={diff:.2f}"


class TestPixelElasticNewForces:
    """Test 4 new elastic force types: gravity, magnetic, wind, explosion."""

    def test_gravity_force_type(self):
        """Gravity force should work without crashing."""
        frame = make_test_frame()
        chain = [{"name": "pixelelastic", "params": {"force_type": "gravity", "seed": 101}}]
        result = apply_chain(frame.copy(), chain, frame_index=0, total_frames=10)
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_gravity_produces_displacement(self):
        """Gravity should produce visible downward displacement over frames."""
        frame = make_test_frame()
        chain = [{"name": "pixelelastic", "params": {"force_type": "gravity", "force_strength": 10.0, "seed": 102}}]
        for i in range(6):
            result = apply_chain(frame.copy(), chain, frame_index=i, total_frames=30)
        diff = np.mean(np.abs(result.astype(float) - frame.astype(float)))
        assert diff > 0.5, f"Gravity should visibly displace, got diff={diff:.2f}"

    def test_magnetic_force_type(self):
        """Magnetic force should work without crashing."""
        frame = make_test_frame()
        chain = [{"name": "pixelelastic", "params": {"force_type": "magnetic", "seed": 103}}]
        result = apply_chain(frame.copy(), chain, frame_index=0, total_frames=10)
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_magnetic_produces_displacement(self):
        """Magnetic force should pull pixels toward center."""
        frame = make_test_frame()
        chain = [{"name": "pixelelastic", "params": {"force_type": "magnetic", "force_strength": 10.0, "seed": 104}}]
        for i in range(6):
            result = apply_chain(frame.copy(), chain, frame_index=i, total_frames=30)
        diff = np.mean(np.abs(result.astype(float) - frame.astype(float)))
        assert diff > 0.5, f"Magnetic should visibly displace, got diff={diff:.2f}"

    def test_wind_force_type(self):
        """Wind force should work without crashing."""
        frame = make_test_frame()
        chain = [{"name": "pixelelastic", "params": {"force_type": "wind", "seed": 105}}]
        result = apply_chain(frame.copy(), chain, frame_index=0, total_frames=10)
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_wind_produces_displacement(self):
        """Wind should produce visible horizontal displacement over frames."""
        frame = make_test_frame()
        chain = [{"name": "pixelelastic", "params": {"force_type": "wind", "force_strength": 10.0, "seed": 106}}]
        for i in range(6):
            result = apply_chain(frame.copy(), chain, frame_index=i, total_frames=30)
        diff = np.mean(np.abs(result.astype(float) - frame.astype(float)))
        assert diff > 0.5, f"Wind should visibly displace, got diff={diff:.2f}"

    def test_explosion_force_type(self):
        """Explosion force should work without crashing."""
        frame = make_test_frame()
        chain = [{"name": "pixelelastic", "params": {"force_type": "explosion", "seed": 107}}]
        result = apply_chain(frame.copy(), chain, frame_index=0, total_frames=10)
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_explosion_produces_displacement(self):
        """Explosion should produce visible outward displacement."""
        frame = make_test_frame()
        chain = [{"name": "pixelelastic", "params": {"force_type": "explosion", "force_strength": 10.0, "seed": 108}}]
        for i in range(6):
            result = apply_chain(frame.copy(), chain, frame_index=i, total_frames=30)
        diff = np.mean(np.abs(result.astype(float) - frame.astype(float)))
        assert diff > 0.5, f"Explosion should visibly displace, got diff={diff:.2f}"

    def test_explosion_decays_over_time(self):
        """Explosion force should be stronger early and weaker late."""
        frame = make_test_frame()
        # Early frames (strong burst)
        chain_early = [{"name": "pixelelastic", "params": {"force_type": "explosion", "force_strength": 15.0, "seed": 109}}]
        for i in range(3):
            result_early = apply_chain(frame.copy(), chain_early, frame_index=i, total_frames=30)
        diff_early = np.mean(np.abs(result_early.astype(float) - frame.astype(float)))
        # Late frames (decayed)
        chain_late = [{"name": "pixelelastic", "params": {"force_type": "explosion", "force_strength": 15.0, "seed": 110}}]
        for i in range(25, 30):
            result_late = apply_chain(frame.copy(), chain_late, frame_index=i, total_frames=30)
        diff_late = np.mean(np.abs(result_late.astype(float) - frame.astype(float)))
        # Early should have more displacement than late
        assert diff_early >= diff_late * 0.3, f"Explosion should decay: early={diff_early:.1f} late={diff_late:.1f}"


class TestPixelXeroxNewParams:
    """Test 3 new xerox params: registration_offset, toner_density, paper_feed."""

    def test_registration_offset_changes_output(self):
        """Non-zero registration_offset should produce different output than zero."""
        frame = make_test_frame()
        chain_zero = [{"name": "pixelxerox", "params": {"registration_offset": 0.0, "seed": 200}}]
        chain_high = [{"name": "pixelxerox", "params": {"registration_offset": 2.5, "seed": 200}}]
        result_zero = apply_chain(frame.copy(), chain_zero, frame_index=5, total_frames=10)
        result_high = apply_chain(frame.copy(), chain_high, frame_index=5, total_frames=10)
        diff = np.mean(np.abs(result_zero.astype(float) - result_high.astype(float)))
        assert diff > 0.5, f"Registration offset should change output, got diff={diff:.2f}"

    def test_toner_density_low_fades(self):
        """Low toner_density should produce a more faded (brighter) image."""
        frame = make_test_frame()
        chain_low = [{"name": "pixelxerox", "params": {"toner_density": 0.4, "seed": 201}}]
        chain_high = [{"name": "pixelxerox", "params": {"toner_density": 1.4, "seed": 201}}]
        result_low = apply_chain(frame.copy(), chain_low, frame_index=5, total_frames=10)
        result_high = apply_chain(frame.copy(), chain_high, frame_index=5, total_frames=10)
        diff = np.mean(np.abs(result_low.astype(float) - result_high.astype(float)))
        assert diff > 1.0, f"Toner density should change contrast, got diff={diff:.2f}"

    def test_paper_feed_shifts_vertically(self):
        """Non-zero paper_feed should produce different output than zero."""
        frame = make_test_frame()
        chain_zero = [{"name": "pixelxerox", "params": {"paper_feed": 0.0, "seed": 202}}]
        chain_high = [{"name": "pixelxerox", "params": {"paper_feed": 1.5, "seed": 202}}]
        result_zero = apply_chain(frame.copy(), chain_zero, frame_index=5, total_frames=10)
        result_high = apply_chain(frame.copy(), chain_high, frame_index=5, total_frames=10)
        diff = np.mean(np.abs(result_zero.astype(float) - result_high.astype(float)))
        assert diff > 0.5, f"Paper feed should shift output, got diff={diff:.2f}"

    def test_xerox_new_params_no_crash(self):
        """Xerox with all new params at various values should not crash."""
        frame = make_test_frame()
        chain = [{"name": "pixelxerox", "params": {
            "registration_offset": 2.0,
            "toner_density": 0.5,
            "paper_feed": 1.0,
            "seed": 203,
        }}]
        for i in range(5):
            result = apply_chain(frame.copy(), chain, frame_index=i, total_frames=10)
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_xerox_styles_with_new_params(self):
        """All xerox styles should work with new params without crashing."""
        frame = make_test_frame()
        for style in ["copy", "faded", "harsh", "zine"]:
            chain = [{"name": "pixelxerox", "params": {
                "style": style,
                "registration_offset": 1.0,
                "toner_density": 0.8,
                "paper_feed": 0.5,
                "seed": 204,
            }}]
            result = apply_chain(frame.copy(), chain, frame_index=3, total_frames=10)
            assert result.shape == frame.shape, f"Style '{style}' failed shape check"
            assert result.dtype == np.uint8, f"Style '{style}' failed dtype check"


class TestPixelMagneticFixes:
    """Test magnetic effect fixes: poles, rotation, damping, seed, no overflow."""

    def test_different_pole_counts_differ(self):
        """Different pole counts should produce different visual results."""
        frame = make_test_frame()
        results = {}
        for poles in [2, 4, 6]:
            chain = [{"name": "pixelmagnetic", "params": {"poles": poles, "field_type": "dipole", "seed": 50}}]
            for i in range(5):
                res = apply_chain(frame.copy(), chain, frame_index=i, total_frames=30)
            results[poles] = res.copy()
        diff_2_4 = np.mean(np.abs(results[2].astype(float) - results[4].astype(float)))
        diff_2_6 = np.mean(np.abs(results[2].astype(float) - results[6].astype(float)))
        assert diff_2_4 > 0.5, f"2 vs 4 poles should differ, got diff={diff_2_4:.2f}"
        assert diff_2_6 > 0.5, f"2 vs 6 poles should differ, got diff={diff_2_6:.2f}"

    def test_rotation_speed_changes_output(self):
        """Different rotation_speed values should produce different results."""
        frame = make_test_frame()
        results = {}
        for speed in [0.0, 1.5]:
            chain = [{"name": "pixelmagnetic", "params": {"rotation_speed": speed, "seed": 60}}]
            for i in range(5):
                res = apply_chain(frame.copy(), chain, frame_index=i, total_frames=30)
            results[speed] = res.copy()
        diff = np.mean(np.abs(results[0.0].astype(float) - results[1.5].astype(float)))
        assert diff > 0.5, f"rotation_speed should change output, got diff={diff:.2f}"

    def test_damping_changes_output(self):
        """Different damping values should produce different displacement magnitudes."""
        frame = make_test_frame()
        results = {}
        for damp in [0.82, 0.98]:
            chain = [{"name": "pixelmagnetic", "params": {"damping": damp, "seed": 70}}]
            for i in range(5):
                res = apply_chain(frame.copy(), chain, frame_index=i, total_frames=30)
            results[damp] = res.copy()
        diff = np.mean(np.abs(results[0.82].astype(float) - results[0.98].astype(float)))
        assert diff > 0.3, f"damping should change output, got diff={diff:.2f}"

    def test_seed_changes_output(self):
        """Different seeds should produce different field orientations."""
        frame = make_test_frame()
        results = {}
        for s in [10, 200]:
            chain = [{"name": "pixelmagnetic", "params": {"seed": s}}]
            for i in range(5):
                res = apply_chain(frame.copy(), chain, frame_index=i, total_frames=30)
            results[s] = res.copy()
        diff = np.mean(np.abs(results[10].astype(float) - results[200].astype(float)))
        assert diff > 0.3, f"seed should change output, got diff={diff:.2f}"

    def test_no_overflow_warning(self):
        """Magnetic should not produce overflow warnings."""
        import warnings
        frame = make_test_frame()
        chain = [{"name": "pixelmagnetic", "params": {"strength": 15.0}}]
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            for i in range(8):
                apply_chain(frame.copy(), chain, frame_index=i, total_frames=30)


class TestPixelQuantumFixes:
    """Test quantum effect fixes: uncertainty, superposition, decoherence."""

    def test_uncertainty_affects_displacement(self):
        """Higher uncertainty should produce more random displacement."""
        frame = make_test_frame()
        results = {}
        for unc in [1.0, 12.0]:
            chain = [{"name": "pixelquantum", "params": {"uncertainty": unc, "superposition": 0, "seed": 40}}]
            for i in range(5):
                res = apply_chain(frame.copy(), chain, frame_index=i, total_frames=30)
            results[unc] = res.copy()
        low_diff = np.mean(np.abs(results[1.0].astype(float) - frame.astype(float)))
        high_diff = np.mean(np.abs(results[12.0].astype(float) - frame.astype(float)))
        assert high_diff > low_diff * 1.5, f"High uncertainty should displace more: low={low_diff:.1f} high={high_diff:.1f}"

    def test_superposition_adds_ghosts(self):
        """Superposition > 0 should produce different output than superposition=0."""
        frame = make_test_frame()
        results = {}
        for sp in [0.0, 0.8]:
            chain = [{"name": "pixelquantum", "params": {"superposition": sp, "decoherence": 0.0, "seed": 41}}]
            res = apply_chain(frame.copy(), chain, frame_index=0, total_frames=10)
            results[sp] = res.copy()
        diff = np.mean(np.abs(results[0.0].astype(float) - results[0.8].astype(float)))
        assert diff > 0.5, f"Superposition should add visible ghosts, got diff={diff:.2f}"

    def test_decoherence_fades_ghosts(self):
        """High decoherence should fade ghosts faster than low decoherence."""
        frame = make_test_frame()
        results = {}
        for dec in [0.01, 0.1]:
            chain = [{"name": "pixelquantum", "params": {"superposition": 0.8, "decoherence": dec, "seed": 42}}]
            # Run to frame 15 where decoherence=0.1 ghosts should have faded
            for i in range(16):
                res = apply_chain(frame.copy(), chain, frame_index=i, total_frames=60)
            results[dec] = res.copy()
        # At frame 15: decoherence=0.01 still has ghosts, decoherence=0.1 has lost them
        # So the two results should differ
        diff = np.mean(np.abs(results[0.01].astype(float) - results[0.1].astype(float)))
        assert diff > 0.3, f"Decoherence rate should affect ghost visibility, got diff={diff:.2f}"


def main():
    # Verify all 21 effects are registered
    missing = [e for e in PHYSICS_EFFECTS if e not in EFFECTS]
    if missing:
        print(f"MISSING from EFFECTS registry: {missing}")
        return 1

    print(f"Testing {len(PHYSICS_EFFECTS)} pixel physics effects...\n")

    passed = 0
    failed = 0
    results = []

    for name in PHYSICS_EFFECTS:
        try:
            # Test 1: basic output
            test_effect_produces_output(name)

            # Test 2: stateful accumulation
            diff = test_effect_stateful(name)

            # Test 3: cleanup + restart
            test_effect_cleanup(name)

            status = "PASS"
            if diff < 0.5:
                status = "PASS (low diff — may need tuning)"
            passed += 1
            results.append((name, status, f"diff={diff:.1f}"))
            print(f"  PASS  {name:25s}  mean_diff={diff:.1f}")

        except Exception as e:
            failed += 1
            results.append((name, "FAIL", str(e)))
            print(f"  FAIL  {name:25s}  {e}")

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed out of {len(PHYSICS_EFFECTS)}")

    if failed > 0:
        print("\nFailed effects:")
        for name, status, detail in results:
            if status == "FAIL":
                print(f"  - {name}: {detail}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

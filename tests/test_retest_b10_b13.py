"""
Retest B10-B13 effects + seed audit (2026-02-15).

Part 1: Verify byte_corrupt (B10), flow_distort (B11), auto_levels (B12),
         histogram_eq (B13) work after the frame_index/total_frames fix.

Part 2: Seed audit — check first 10 seed-exposing effects to confirm that
         different seed values produce different outputs.
"""

import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from effects import apply_chain, EFFECTS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_test_frame(h=120, w=160):
    """Gradient + shapes test frame (same pattern as test_physics_effects)."""
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    for x in range(w):
        frame[:, x, 0] = int(255 * x / w)
    for y in range(h):
        frame[y, :, 1] = int(255 * y / h)
    frame[h // 4:3 * h // 4, w // 4:3 * w // 4, 2] = 200
    return frame


# ---------------------------------------------------------------------------
# Part 1: B10-B13 retest
# ---------------------------------------------------------------------------

B10_B13 = [
    ("bytecorrupt", {}),
    ("flowdistort", {}),
    ("autolevels", {}),
    ("histogrameq", {}),
]


@pytest.mark.parametrize("effect_name,extra_params", B10_B13, ids=[e[0] for e in B10_B13])
def test_b10_b13_produces_output(effect_name, extra_params):
    """Effect returns a valid frame (not None, correct shape/dtype)."""
    frame = make_test_frame()
    chain = [{"name": effect_name, "params": extra_params}]
    result = apply_chain(frame.copy(), chain, frame_index=5, total_frames=30)
    assert result is not None, f"{effect_name}: returned None"
    assert result.shape == frame.shape, f"{effect_name}: shape mismatch"
    assert result.dtype == np.uint8, f"{effect_name}: wrong dtype"


@pytest.mark.parametrize("effect_name,extra_params", B10_B13, ids=[e[0] for e in B10_B13])
def test_b10_b13_modifies_frame(effect_name, extra_params):
    """Effect should visibly modify the input frame (not return identical pixels)."""
    frame = make_test_frame()
    chain = [{"name": effect_name, "params": extra_params}]
    result = apply_chain(frame.copy(), chain, frame_index=5, total_frames=30)
    assert not np.array_equal(result, frame), (
        f"{effect_name}: output is identical to input — effect did nothing"
    )


@pytest.mark.parametrize("effect_name,extra_params", B10_B13, ids=[e[0] for e in B10_B13])
def test_b10_b13_multi_frame(effect_name, extra_params):
    """Effect works across multiple frame indices without crashing."""
    frame = make_test_frame()
    chain = [{"name": effect_name, "params": extra_params}]
    for i in range(5):
        result = apply_chain(frame.copy(), chain, frame_index=i, total_frames=30)
        assert result is not None, f"{effect_name}: returned None at frame {i}"
        assert result.shape == frame.shape, f"{effect_name}: shape mismatch at frame {i}"


# ---------------------------------------------------------------------------
# Part 2: Seed audit — first 10 effects that expose a seed param
# ---------------------------------------------------------------------------

# Collect first 10 effects with seed in their default params
SEED_EFFECTS = []
for name, entry in EFFECTS.items():
    if "seed" in entry["params"]:
        SEED_EFFECTS.append(name)
    if len(SEED_EFFECTS) >= 10:
        break


# Effects where seed affects temporal behavior (hold timing, freeze intervals)
# rather than per-frame pixel content — need multi-frame testing
# Effects where seed affects temporal behavior — need multi-frame testing
_TEMPORAL_SEED_EFFECTS = {"samplehold", "granulator", "beatrepeat", "strobe"}

# Effects where seed only activates with non-default params
_CONDITIONAL_SEED_EFFECTS = {
    "scanlines": {"flicker": True},
    "granulator": {"spray": 0.5},
    "beatrepeat": {"chance": 0.5, "variation": 0.5},
    "strobe": {"color": "random"},
}


@pytest.mark.parametrize("effect_name", SEED_EFFECTS)
def test_seed_changes_output(effect_name):
    """Different seed values should produce different outputs."""
    frame = make_test_frame()

    # Get default params and override seed
    defaults = EFFECTS[effect_name]["params"].copy()

    # Enable conditional seed usage
    if effect_name in _CONDITIONAL_SEED_EFFECTS:
        defaults.update(_CONDITIONAL_SEED_EFFECTS[effect_name])

    params_seed1 = {**defaults, "seed": 1}
    params_seed42 = {**defaults, "seed": 42}

    if effect_name in _TEMPORAL_SEED_EFFECTS:
        # Temporal-seed effects: test across frame sequence for divergence
        any_diff = False
        for fi in range(20):
            f1 = make_test_frame()
            f2 = make_test_frame()
            # Vary input slightly per frame to give temporal effects different data
            f1[fi % 120, :, :] = 255
            f2[fi % 120, :, :] = 255
            r1 = apply_chain(f1, [{"name": effect_name, "params": {**params_seed1}}],
                             frame_index=fi, total_frames=30)
            r42 = apply_chain(f2, [{"name": effect_name, "params": {**params_seed42}}],
                              frame_index=fi, total_frames=30)
            if not np.array_equal(r1, r42):
                any_diff = True
                break
        assert any_diff, (
            f"{effect_name}: SEED BROKEN — seed=1 and seed=42 produce identical "
            f"output across 20 frames"
        )
    else:
        chain1 = [{"name": effect_name, "params": params_seed1}]
        chain42 = [{"name": effect_name, "params": params_seed42}]

        result1 = apply_chain(frame.copy(), chain1, frame_index=5, total_frames=30)
        result42 = apply_chain(frame.copy(), chain42, frame_index=5, total_frames=30)

        # Both should be valid
        assert result1 is not None and result42 is not None, f"{effect_name}: returned None"

        # Different seeds should produce different output
        identical = np.array_equal(result1, result42)
        if identical:
            pytest.fail(
                f"{effect_name}: SEED BROKEN — seed=1 and seed=42 produce identical output"
            )


# ---------------------------------------------------------------------------
# Standalone runner (for non-pytest execution)
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("PART 1: B10-B13 RETEST")
    print("=" * 70)

    b10_results = []
    for effect_name, extra_params in B10_B13:
        frame = make_test_frame()
        chain = [{"name": effect_name, "params": extra_params}]
        try:
            result = apply_chain(frame.copy(), chain, frame_index=5, total_frames=30)
            assert result is not None
            assert result.shape == frame.shape
            assert result.dtype == np.uint8
            modified = not np.array_equal(result, frame)
            diff = np.mean(np.abs(result.astype(float) - frame.astype(float)))
            status = "PASS" if modified else "FAIL (no change)"
            b10_results.append((effect_name, status, f"mean_diff={diff:.1f}"))
            print(f"  {status:20s}  {effect_name:20s}  mean_diff={diff:.1f}")
        except Exception as e:
            b10_results.append((effect_name, "FAIL (crash)", str(e)))
            print(f"  FAIL (crash)          {effect_name:20s}  {e}")

    print()
    print("=" * 70)
    print(f"PART 2: SEED AUDIT (first {len(SEED_EFFECTS)} effects with seed)")
    print("=" * 70)

    seed_results = []
    for effect_name in SEED_EFFECTS:
        frame = make_test_frame()
        defaults = EFFECTS[effect_name]["params"].copy()
        if effect_name == "scanlines":
            defaults["flicker"] = True
        try:
            params1 = {**defaults, "seed": 1}
            params42 = {**defaults, "seed": 42}
            r1 = apply_chain(frame.copy(), [{"name": effect_name, "params": params1}],
                             frame_index=5, total_frames=30)
            r42 = apply_chain(frame.copy(), [{"name": effect_name, "params": params42}],
                              frame_index=5, total_frames=30)
            identical = np.array_equal(r1, r42)
            pixel_diff = np.mean(np.abs(r1.astype(float) - r42.astype(float)))
            if identical:
                status = "FAIL (seed broken)"
                seed_results.append((effect_name, status, "identical output"))
            else:
                status = "PASS"
                seed_results.append((effect_name, status, f"seed_diff={pixel_diff:.1f}"))
            print(f"  {status:25s}  {effect_name:25s}  pixel_diff={pixel_diff:.1f}")
        except Exception as e:
            seed_results.append((effect_name, "FAIL (crash)", str(e)))
            print(f"  FAIL (crash)              {effect_name:25s}  {e}")

    print()
    print("=" * 70)
    b10_pass = sum(1 for _, s, _ in b10_results if s == "PASS")
    seed_pass = sum(1 for _, s, _ in seed_results if s == "PASS")
    seed_broken = sum(1 for _, s, _ in seed_results if "broken" in s)
    print(f"B10-B13: {b10_pass}/{len(B10_B13)} passed")
    print(f"Seed:    {seed_pass}/{len(SEED_EFFECTS)} passed, {seed_broken} broken seeds")

    return b10_results, seed_results


if __name__ == "__main__":
    b10_results, seed_results = main()

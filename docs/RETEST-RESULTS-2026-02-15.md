# Retest Results — 2026-02-15

## Part 1: B10-B13 Retest (Post frame_index Fix)

All 4 effects confirmed working after the `frame_index`/`total_frames` fix to `apply_chain()`.

| Bug ID | Effect | Registry Name | Status | Mean Diff |
|--------|--------|---------------|--------|-----------|
| B10 | byte_corrupt | `bytecorrupt` | PASS | 2.6 |
| B11 | flow_distort | `flowdistort` | PASS | 3.7 |
| B12 | auto_levels | `autolevels` | PASS | 9.0 |
| B13 | histogram_eq | `histogrameq` | PASS | 5.5 |

**Test details (3 tests per effect):**
1. **produces_output** — returns valid frame (not None, correct shape/dtype)
2. **modifies_frame** — output differs from input (effect is visually active)
3. **multi_frame** — works across frame_index 0-4 without crashing

**Verdict:** B10-B13 are resolved. The frame_index fix at 8 call sites was sufficient.

---

## Part 2: Seed Audit (First 10 Effects)

Tested whether `seed=1` and `seed=42` produce different outputs on the same input frame.

| Effect | Seed Status | Pixel Diff (seed=1 vs seed=42) |
|--------|-------------|-------------------------------|
| `displacement` | PASS | 6.6 |
| `tvstatic` | PASS | 67.9 |
| `scanlines` | **BROKEN** | 0.0 |
| `vhs` | PASS | 5.2 |
| `noise` | PASS | 14.3 |
| `asciiart` | **BROKEN** | 0.0 |
| `brailleart` | **BROKEN** | 0.0 |
| `stutter` | **BROKEN** | 0.0 |
| `dropout` | PASS | 100.7 |
| `feedback` | **BROKEN** | 0.0 |

**Summary:** 5/10 pass, 5/10 have broken seeds.

### Broken Seed Analysis

- **scanlines** — Seed param is declared but likely not used in the rendering logic (no randomness when `flicker=False`)
- **asciiart** — ASCII conversion is deterministic (character mapping from pixel values); seed has no effect
- **brailleart** — Braille conversion is deterministic (threshold-based dot placement); seed has no effect
- **stutter** — Stutter pattern is interval-based, not random; seed is unused at frame_index=5 with default params
- **feedback** — Feedback blends with previous frame state; on first call with no state, seed has no effect

### Notes

- Some "broken" seeds may be by design — effects like `scanlines` (without flicker), `asciiart`, and `brailleart` are fundamentally deterministic. The seed param exists but has no randomness to control.
- `stutter` and `feedback` are temporal effects — their seed may only matter across multi-frame sequences or with specific param combinations (e.g., `flicker=True` for scanlines).
- Remaining ~60 effects with seed params need auditing in a future pass.

---

## Test File

`tests/test_retest_b10_b13.py` — 22 tests total (12 B10-B13 + 10 seed audit)

Run with:
```bash
cd ~/Development/entropic && python3 -m pytest tests/test_retest_b10_b13.py -v
```

---

*Generated: 2026-02-15*

# P2 Architecture Plan — CTO Analysis

> **Created:** 2026-02-15
> **Status:** PLAN (not yet implemented)
> **Branch:** feature/timeline-editor
> **Current:** 125 effects, 3210 tests, 5224 lines across 5 key files

---

## Implementation Sequence (Dependency-Ordered)

| Order | Item | Effort | Risk | Dependencies |
|-------|------|--------|------|-------------|
| 1 | P2-3 Taxonomy (finish) | Small | Low | None |
| 2 | P2-7 Flanger/Phaser/LFO docs | Small | Low | None |
| 3 | P2-6 Ring mod rework | Medium | Low | P2-7 (clear definitions) |
| 4 | P2-1 Physics consolidation | Medium | Medium | None (pattern exists) |
| 5 | P2-4 Transparent layers | Medium | Medium | None |
| 6 | P2-2 Sidechain operator | Large | High | P2-4 (alpha awareness) |
| 7 | P2-5 Gravity concentrations | Large | High | P2-2 (param targeting model) |

---

## P2-1: Pixel Physics Consolidation

### Feasibility: ✅ Already 80% done

**Discovery:** The consolidation is ALREADY BUILT. physics.py lines 2382-2473 define:
- `_DYNAMICS_MODES` → 6 modes → `pixel_dynamics()` dispatcher
- `_COSMOS_MODES` → 9 modes → `pixel_cosmos()` dispatcher
- `_ORGANIC_MODES` → 3 modes → `pixel_organic()` dispatcher
- `_DECAY_MODES` → 3 modes → `pixel_decay()` dispatcher
- `_dispatch()` — generic mode dispatcher using `inspect.signature`

The `__init__.py` already uses `alias_of` (27 entries) to map individual effects to mega-effects.

### What's Actually Left

1. **param_visibility per mode** — Hide irrelevant params when mode changes (e.g., hide `hawking` when mode is "magnetic"). Each mega-effect needs a `param_visibility` dict.
2. **UI mode selector** — app.js needs a prominent mode dropdown at the top of the params panel when a mega-effect is selected. Currently mode is just another dropdown param.
3. **Shared state management** — All physics effects use `_get_state(key, h, w)` (line 25) which caches velocity/displacement arrays. The key includes effect name — verify aliases share state correctly.

### Implementation Plan

**File: effects/__init__.py** (~30 min)
- Add `param_visibility` to pixeldynamics, pixelcosmos, pixelorganic entries
- Pattern: `"param_visibility": {"hawking": {"hidden_when": {"mode": ["magnetic", "quantum", ...]}}, ...}`
- Already done for pixelmagnetic (line 752) — extend to all mega-effects

**File: ui/static/app.js** (~1 hour)
- When rendering params for a mega-effect, check `param_visibility` rules
- Hide/show params dynamically when mode dropdown changes
- Promote mode dropdown to a prominent position (first param, larger, styled differently)

**Tests:** (~30 min)
- Test that each mode dispatches to correct function
- Test param_visibility rules hide correct params
- Test backward compat: calling `pixelblackhole` still works via alias

### Risk: LOW
The dispatch pattern is proven (pixel_decay works). Main risk is getting param_visibility right for all mode combinations.

---

## P2-2: Modular Sidechain Operator

### Feasibility: ⚠️ Partially built, targeting is the hard part

**Current state:** `sidechain_operator()` at line 675 of sidechain.py already supports duck/pump/gate/cross modes. The 6 individual effects (duck/pump/gate/cross/crossfeed/interference) are registered as aliases.

**The missing piece:** Parameter targeting — making the sidechain envelope modulate a specific parameter on another effect.

### Architecture Design

**Option A: Post-chain modulation (RECOMMENDED)**
```
Chain: [effect1, effect2, sidechain_operator(target="effect1.intensity")]
```
The sidechain operator stores its envelope output. At render time, after computing the envelope, the chain runner reads the target spec and multiplies the target param by the envelope value before calling the target effect.

**Option B: Pre-render injection**
Each frame, the sidechain operator pre-computes the envelope, then the chain runner passes modified params to the target effect. Same outcome, different execution point.

**Recommendation: Option A** — post-chain modulation. It's simpler, doesn't require changing the effect function signatures, and matches how hardware sidechain works (envelope follower → VCA on target).

### Implementation Plan

**File: effects/sidechain.py** (~1 hour)
- `sidechain_operator` already computes envelope. Add: store envelope value in a module-level dict keyed by chain context.
- New function: `get_sidechain_envelope(chain_id) -> float` — returns current envelope (0-1).

**File: server.py** (~2 hours) — The chain runner
- In `_apply_chain()`, identify sidechain operators in the chain
- Before rendering each effect, check if any sidechain targets it
- If targeted, multiply the target param by the envelope value
- Data model: sidechain effect has `target_effect` (str, effect name in chain) and `target_param` (str, param name)

**File: effects/__init__.py** (~30 min)
- Add `target_effect` and `target_param` to sidechain_operator params
- Add `param_options` for target_effect (populated dynamically from chain)
- Add `param_options` for target_param (populated dynamically from selected effect's params)

**File: ui/static/app.js** (~2 hours)
- Dynamic dropdown: when sidechain_operator is in chain, show target_effect dropdown populated with other effects in chain
- When target_effect is selected, populate target_param dropdown with that effect's numeric params
- Visual: draw a routing line from sidechain to target in the chain view

**Tests:** (~1 hour)
- Test envelope computation for each mode
- Test parameter targeting: sidechain duck targeting pixelsort.threshold
- Test that removing target effect doesn't crash
- Test preset save/load with sidechain routing

### Risk: HIGH
This changes the render pipeline. Must preserve existing behavior for chains without sidechain targeting. Dynamic param options are new UI territory.

---

## P2-3: Finish Taxonomy Reclassification

### Feasibility: ✅ Trivial

**Done:** operators category added, LFO moved, CATEGORY_ORDER reordered.

### What's Left

**Move to "tools" category:**
- `levels` (image editing tool)
- `curves` (image editing tool)
- `hsladjust` (image editing tool)
- `colorbalance` (image editing tool)
- `histogrameq` (image editing tool)
- `clahe` (image editing tool)
- `autolevels` (image editing tool)
- `chroma_key` (compositing tool)
- `luma_key` (compositing tool)

**Keep in "color" (creative effects):**
- hueshift, contrast, saturation, exposure, temperature, colorfilter, tapesaturation

**Consider for "operators":**
- `gate` — it gates signal, that's an operator behavior. But it also has standalone visual effect. **Keep in modulation.**
- `sidechain_operator` — already in sidechain category. Fine.

### Implementation Plan

**File: effects/__init__.py** (~15 min)
- Change `"category": "color"` → `"category": "tools"` for: levels, curves, hsladjust, colorbalance
- Change `"category": "enhance"` → `"category": "tools"` for: histogrameq, clahe, autolevels
- Change `"category": "color"` → `"category": "tools"` for: chroma_key, luma_key

**Tests:** (~15 min)
- Update test_taxonomy.py assertions for new category assignments
- Verify CATEGORY_ORDER still contains all used categories

### Risk: LOW
Pure metadata change. No logic changes.

---

## P2-4: Transparent Layer Rendering

### Feasibility: ✅ Already partially supported

**Discovery:** `core/layer.py` ALREADY handles RGBA:
- Lines 304-308: Extracts per-pixel alpha from 4th channel
- Lines 312-314: First layer with alpha composites correctly
- Lines 334-338: Subsequent layers use `eff_alpha = pixel_alpha * layer_opacity`
- Normal blend and non-normal blend both use `eff_alpha`

**What's actually needed:**
1. More effects need to OUTPUT RGBA (currently only emboss transparent_bg and chroma_key)
2. RGBA must propagate through effect chains without being stripped to RGB
3. Preview pipeline must handle RGBA → PNG for display (not JPEG, which drops alpha)

### Implementation Plan

**File: effects/__init__.py** (~30 min)
- Add `"output_alpha": True` flag to effects that should output RGBA: emboss, chroma_key, luma_key
- In `apply_effect()`: if effect has `output_alpha=True` and input is RGB, expand to RGBA (alpha=255) before calling

**File: server.py** (~1 hour)
- In chain rendering: propagate RGBA frames through chain (don't strip alpha between effects)
- In `_frame_to_data_url()`: if frame has alpha, encode as PNG not JPEG
- In preview: composite RGBA onto checkered background for display (Photoshop pattern)

**File: effects/__init__.py `apply_effect()`** (~30 min)
- Currently at ~line 1200. When an effect receives RGBA but doesn't output alpha, strip alpha before calling, reattach after
- Pattern: `if frame.shape[2] == 4: alpha = frame[:,:,3]; frame = frame[:,:,:3]; result = effect(frame); result = np.dstack([result, alpha])`

**Tests:** (~1 hour)
- Test RGBA frame through full chain
- Test layer composite with 2 RGBA layers
- Test emboss transparent_bg composited onto video layer
- Test preview PNG encoding for RGBA frames

### Risk: MEDIUM
Main risk: effects that reshape/resize frames will lose alpha if not handled. The alpha strip-and-reattach pattern in apply_effect mitigates this.

---

## P2-5: Gravity Concentrations (Spatial Parameter Modulation)

### Feasibility: ⚠️ Feasible but needs careful scoping

### Architecture Decision

**Option A: Post-process weight mask (RECOMMENDED for v1)**
- After applying effect at full strength, multiply output by a spatial weight mask
- Weight mask = Gaussian blobs at each gravity point
- `result = original * (1-mask) + effected * mask`
- This means the effect is only visible near gravity points

**Option B: Per-pixel parameter maps (FUTURE)**
- Pass the weight mask into the effect, each pixel uses a different param value
- Requires rewriting every effect to accept arrays instead of scalars
- Far more powerful but invasive — save for v2

### Implementation Plan (Option A)

**File: new file `core/spatial_mod.py`** (~100 lines)
```python
def compute_gravity_mask(points, frame_shape):
    """Generate weight mask from gravity points.

    Args:
        points: [{"x": 0.3, "y": 0.5, "radius": 0.2, "strength": 1.0, "falloff": "gaussian"}, ...]
        frame_shape: (h, w)
    Returns:
        np.ndarray: (h, w) float32 mask, 0-1
    """
    mask = np.zeros(frame_shape[:2], dtype=np.float32)
    for p in points:
        # Gaussian blob at (x,y) with given radius
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        cx, cy = p["x"] * w, p["y"] * h
        r = p["radius"] * min(h, w)
        blob = np.exp(-((x-cx)**2 + (y-cy)**2) / (2 * r * r)) * p["strength"]
        mask = np.maximum(mask, blob)
    return np.clip(mask, 0, 1)
```

**File: server.py** (~30 min)
- In chain rendering: after applying effect, if chain has gravity points, apply weight mask
- `result = orig * (1-mask[:,:,np.newaxis]) + result * mask[:,:,np.newaxis]`

**File: ui/static/app.js** (~2 hours)
- Canvas overlay on preview for placing/dragging gravity points
- Click to add point, drag to move, scroll to resize radius
- Delete key to remove selected point
- Points stored in chain config (serialized with preset save/load)

**Data model:**
```json
{
  "effects": [...],
  "gravity_points": [
    {"x": 0.3, "y": 0.5, "radius": 0.2, "strength": 1.0, "falloff": "gaussian"}
  ]
}
```

**Tests:** (~30 min)
- Test mask generation (single point, multiple points, edge cases)
- Test that gravity mask applies correctly (effect visible near point, absent elsewhere)
- Test with no gravity points (passthrough, no perf impact)

### Risk: HIGH
UI complexity is the main risk. Canvas overlay interaction (click/drag/scroll on preview) must not conflict with existing preview interactions (pan, zoom, diff tool).

---

## P2-6: Ring Mod Reconceptualization

### Feasibility: ✅ Straightforward DSP

**Current problem:** `ring_mod()` in modulation.py (line 9, ~105 lines) applies a simple sine multiplication to pixel brightness, creating uniform stripes. No carrier signal, no frequency selection.

### Design

Ring modulation = `output = input × carrier`

The carrier should be a synthesized waveform (not just brightness × sine). Add:
- **carrier_waveform**: sine, square, triangle, saw (like a synth oscillator)
- **carrier_freq**: frequency of the carrier in cycles per frame width
- **modulation_depth**: 0-1 how much the carrier affects the output
- **spectrum_band**: which frequency range to modulate (low/mid/high/all)
- **carrier_direction**: horizontal, vertical, radial, temporal

### Implementation Plan

**File: effects/modulation.py** (~1 hour)
```python
def ring_mod(frame, carrier_waveform="sine", carrier_freq=8.0,
             modulation_depth=0.7, spectrum_band="all",
             carrier_direction="horizontal", animate=True,
             seed=42, frame_index=0, total_frames=1):
    # Generate carrier signal
    if carrier_direction == "horizontal":
        t = np.linspace(0, carrier_freq * 2 * np.pi, w)
        carrier_1d = _waveform(t, carrier_waveform)
        carrier = np.tile(carrier_1d, (h, 1))
    # ... vertical, radial, temporal variants

    # Apply spectrum band selection
    if spectrum_band != "all":
        # Decompose to frequency bands, modulate selected band
        ...

    # Ring modulate
    carrier_scaled = 1.0 - modulation_depth + modulation_depth * carrier
    result = frame.astype(np.float32) * carrier_scaled[:,:,np.newaxis]
```

**File: effects/__init__.py** (~15 min)
- Update ringmod entry with new params, param_ranges, param_options, param_descriptions

**Tests:** (~30 min)
- Test each carrier waveform produces distinct output
- Test modulation_depth=0 returns original
- Test carrier_direction variants
- Test spectrum_band selection

### Risk: LOW
Self-contained change to one effect. No pipeline changes.

---

## P2-7: Flanger/Phaser/LFO Differentiation

### Feasibility: ✅ Documentation + minor code cleanup

**Current state:** 12 functions in dsp_filters.py + 4 in modulation.py. Many overlap conceptually.

### Conceptual Model

| Type | What it does | Visual result | Key params |
|------|-------------|---------------|------------|
| **Flanger** | Delayed copy mixed back, delay time modulated by LFO | Comb filter sweep = "jet engine" | delay_time, rate, feedback |
| **Phaser** | All-pass filter cascade shifts phase | Notch sweep = "swooshing" | stages, rate, feedback |
| **LFO** | Modulates any parameter periodically | Depends on target | rate, depth, waveform, target |
| **Filter** | Frequency-domain emphasis/cut | Brightness banding | frequency, resonance, type |
| **Reverb** | Accumulation of echoes | Trails, persistence | decay, diffusion |

### Classification of Current 16 Effects

| Effect | Actually is | Action |
|--------|-----------|--------|
| video_flanger | Flanger (frame delay mix) | Keep, rename params for clarity |
| video_phaser | Phaser (all-pass cascade) | Keep |
| spatial_flanger | Flanger (spatial offset) | Keep |
| channel_phaser | Phaser (per-channel phase) | Keep |
| brightness_phaser | Phaser (brightness bands) | Keep |
| hue_flanger | Flanger (hue offset) | Keep |
| resonant_filter | Filter (bandpass sweep) | Recategorize to "filter" or keep |
| comb_filter | Filter (multi-tooth comb) | Keep |
| feedback_phaser | Phaser (with escalation) | Keep |
| spectral_freeze | Freeze (FFT hold) | Unique — keep |
| visual_reverb | Reverb (echo accumulation) | Keep |
| freq_flanger | Flanger (frequency domain) | Keep |
| ring_mod | Modulation (carrier × signal) | Rework per P2-6 |
| gate | Gate (threshold on/off) | Keep in modulation |
| wavefold | Wavefold (reflection) | Keep in modulation |
| lfo | Operator (param modulation) | Already moved to operators |

### Implementation Plan

**File: docs/MODULATION-GUIDE.md** (~30 min)
- Write clear definitions of flanger vs phaser vs LFO vs filter
- Classify each of the 16 effects
- Include diagrams (ASCII) of signal flow for each type

**File: effects/__init__.py** (~15 min)
- Add `param_descriptions` to all modulation effects explaining what they actually do
- Update `description` field with the correct type label (e.g., "Flanger — delayed copy...")

**No code changes needed** — the effects work correctly, they just need better labeling and documentation so users understand the differences.

### Risk: LOW
Documentation-only change for the differentiation. P2-6 ring mod is the only code change.

---

## Summary Table

| Item | Effort | Files Changed | New Files | Tests |
|------|--------|--------------|-----------|-------|
| P2-3 Taxonomy | 30 min | __init__.py | — | 5 |
| P2-7 Differentiation | 45 min | __init__.py, docs/ | MODULATION-GUIDE.md | 0 |
| P2-6 Ring mod | 2 hours | modulation.py, __init__.py | — | 10 |
| P2-1 Physics visibility | 2 hours | __init__.py, app.js | — | 15 |
| P2-4 Transparent layers | 3 hours | layer.py, server.py, __init__.py | — | 15 |
| P2-2 Sidechain targeting | 5 hours | sidechain.py, server.py, __init__.py, app.js | — | 20 |
| P2-5 Gravity concentrations | 4 hours | server.py, app.js | spatial_mod.py | 10 |

**Total estimated: ~17 hours of implementation work**

---

## Build Sequence for Next Session

### Sprint 1 (Quick wins — ~1.5 hours)
1. P2-3: Move 9 effects to "tools" category
2. P2-7: Write modulation guide + update descriptions
3. P2-6: Rework ring_mod with carrier signal

### Sprint 2 (Core architecture — ~5 hours)
4. P2-1: Add param_visibility to mega-effects, UI mode selector
5. P2-4: RGBA propagation, alpha strip-and-reattach in apply_effect

### Sprint 3 (Advanced systems — ~9 hours)
6. P2-2: Sidechain parameter targeting + UI routing
7. P2-5: Gravity concentrations + spatial weight mask + UI overlay

---

*Plan written by CTO skill. Ready for implementation.*

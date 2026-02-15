# Entropic Architecture Deep Dive — CTO Analysis

> **Date:** 2026-02-15
> **Context:** First UAT session revealed 6 major architecture proposals. User requires implementation-ready depth — "not bullet points, but specs someone could build from."
> **Source:** UAT-FINDINGS-2026-02-15.md, all source code in effects/, core/, server.py

---

## Table of Contents

1. [Modular Operator System](#1-modular-operator-system)
2. [Effects / Tools / Operators / Image Editing Taxonomy](#2-effects--tools--operators--image-editing-taxonomy)
3. [Perform Mode as Timeline Automation Layer](#3-perform-mode-as-timeline-automation-layer)
4. [Pixel Physics Consolidation](#4-pixel-physics-consolidation)
5. [Photoshop-Level Color Tools](#5-photoshop-level-color-tools)
6. [Parameter Sensitivity / Metering System](#6-parameter-sensitivity--metering-system)
7. [**Unified Timeline Architecture (UI Redesign)**](#7-unified-timeline-architecture-ui-redesign)

---

## 1. Modular Operator System

### The Problem

Currently, modulation is hardcoded into individual effects:
- `video_flanger()` has its own LFO: `lfo = (np.sin(2 * np.pi * rate * frame_index / 30.0) + 1) / 2` (dsp_filters.py:58)
- `sidechain_duck()` has its own envelope (sidechain.py:110-121)
- `tremolo()` has its own LFO hardcoded to brightness
- `lfo()` in temporal.py has 8 hardcoded targets (brightness, displacement, channelshift, blur, moire, glitch, invert, posterize) but CANNOT modulate arbitrary parameters on other effects
- `gate()` in modulation.py is a per-pixel brightness gate — not a mappable temporal gate

User said: "I see there is an LFO, but I can't map it to anything else. I want to be able to hook it up to other effects."

### What Ableton, TouchDesigner, Max/MSP, Reaktor, VCV Rack Do

**Ableton Live (Max for Live):**
- LFO device: waveform selector (sine/saw/square/tri/random/noise), rate (Hz or synced to BPM), depth (0-100%), mapping button → click any parameter → done
- Envelope Follower: analyzes audio input, outputs a control signal mapped to any parameter
- Macro controls: 8 knobs, each can map to multiple params with min/max ranges
- Sidechain: routed via audio channels, compressor/gate has sidechain input selector

**TouchDesigner:**
- CHOPs (Channel Operators) = modulation signals. LFO CHOP, Noise CHOP, Envelope CHOP
- Any CHOP output → exported as parameter reference → any TOP/SOP/MAT parameter
- Operator wiring is visual: drag connection line from CHOP output to parameter input
- Multiple CHOPs can feed one parameter (additive/multiplicative)

**VCV Rack / Modular Synth:**
- Every module has CV inputs (Control Voltage) on every parameter
- Patch cables connect any output to any input
- Attenuverters scale the modulation range (amount + polarity)
- Clock/gate/trigger signals travel same way

**Max/MSP:**
- Everything is a patchable object with inlets/outlets
- [cycle~] = oscillator, [line~] = envelope, [edge~] = trigger
- Connect anything to anything via patch cords

**Reaktor:**
- Modular routing via internal buses
- Macro pages expose parameters
- Event and audio-rate modulation

### What Makes Video Operators Different from Audio

| Concern | Audio | Video |
|---------|-------|-------|
| Update rate | Sample rate (44.1kHz) | Frame rate (24-60 fps) |
| Sync source | BPM / tempo map | BPM or frame count |
| Value range | -1.0 to 1.0 (bipolar) | Parameter-specific (0-255, 0.0-1.0, degrees, etc.) |
| Latency tolerance | <10ms | <33ms (at 30fps) |
| State | Continuous | Frame-discrete |
| Visualization | Waveform scope | Waveform scope + live preview of modulated output |

**Key insight for Entropic:** Operators run at frame rate, not sample rate. An LFO at 2Hz running at 30fps has only 15 samples per cycle — plenty for smooth video modulation, but the operator engine must be frame-synced.

### Operator Types

#### 1. LFO Operator
**What it does:** Generates a periodic waveform that modulates a target parameter over time.

**Parameters:**
```json
{
  "type": "lfo",
  "id": "lfo_1",
  "waveform": "sine",       // sine, square, saw, triangle, random, noise, sample_hold
  "rate": 2.0,              // Hz (free-running) or float beats (if sync=true)
  "sync": false,            // true = sync to BPM, false = free Hz
  "depth": 1.0,             // 0.0-1.0 — how much of the target range to modulate
  "phase": 0.0,             // 0.0-1.0 — starting phase offset
  "polarity": "bipolar",    // "bipolar" (-1 to +1) or "unipolar" (0 to +1)
  "smoothing": 0.0,         // 0.0-1.0 — low-pass on output (slew limiter)
  "retrigger": false,       // true = reset phase on trigger signal
  "mappings": [
    {
      "target_effect": "pixelsort",     // effect name in chain
      "target_param": "threshold",       // parameter name
      "min": 0.2,                        // minimum mapped value
      "max": 0.8,                        // maximum mapped value
      "curve": "linear"                  // linear, exponential, logarithmic, s-curve
    }
  ]
}
```

**Waveform implementations:**
```python
def _generate_waveform(waveform: str, phase: float) -> float:
    """Generate waveform value at given phase (0.0-1.0). Returns -1.0 to 1.0."""
    if waveform == "sine":
        return math.sin(2 * math.pi * phase)
    elif waveform == "square":
        return 1.0 if phase < 0.5 else -1.0
    elif waveform == "saw":
        return 2.0 * phase - 1.0
    elif waveform == "triangle":
        return 4.0 * abs(phase - 0.5) - 1.0
    elif waveform == "random":
        # New random value each cycle
        return random.uniform(-1.0, 1.0)
    elif waveform == "sample_hold":
        # Hold random value for entire cycle, change on reset
        return _sh_state.get("value", 0.0)
    elif waveform == "noise":
        # Perlin-like smooth noise
        return _noise_1d(phase * 10.0)
```

#### 2. Envelope Operator
**What it does:** ADSR-shaped modulation triggered by events (frame, signal threshold, manual trigger).

**Parameters:**
```json
{
  "type": "envelope",
  "id": "env_1",
  "attack": 10,              // frames to reach peak
  "decay": 5,                // frames from peak to sustain
  "sustain": 0.8,            // sustain level (0.0-1.0)
  "release": 15,             // frames to reach 0 after trigger off
  "curve": "exponential",    // linear, exponential, logarithmic
  "trigger_source": "manual", // manual, lfo, threshold, beat
  "trigger_threshold": 0.5,  // for threshold trigger: signal level
  "trigger_signal": "brightness", // for threshold: brightness, motion, edges
  "loop": false,             // auto-retrigger when release completes
  "mappings": [...]          // same as LFO mappings
}
```

**Envelope state machine (already exists in core/layer.py and effects/adsr.py):**
```
idle → [trigger_on] → attack → [peak reached] → decay → [sustain level] → sustain → [trigger_off] → release → [zero] → idle
```

The existing `ADSREnvelope` class in `effects/adsr.py` is reusable. It just needs to output to arbitrary parameters instead of only layer opacity.

#### 3. Sidechain Operator
**What it does:** Extracts a control signal from video content and maps it to any parameter. This is the modular version of the 6 current sidechain effects.

**Parameters:**
```json
{
  "type": "sidechain",
  "id": "sc_1",
  "source": "brightness",    // brightness, motion, edges, saturation, hue, contrast
  "input": "self",           // "self" (same video) or "key" (second video input)
  "threshold": 0.0,          // below this = 0 signal
  "ratio": 1.0,              // compression ratio above threshold
  "attack": 0.0,             // smoothing attack (frames)
  "release": 0.0,            // smoothing release (frames)
  "invert": false,           // flip the signal
  "spatial_mode": "global",  // "global" (average), "per_pixel" (spatial mask), "zone" (regions)
  "mappings": [...]          // same as LFO mappings
}
```

**How current sidechain effects refactor:**
| Current Effect | Becomes |
|---------------|---------|
| `sidechain_duck` | Sidechain operator → mapped to brightness/opacity of target |
| `sidechain_pump` | LFO operator with exponential waveform → mapped to brightness |
| `sidechain_gate` | Sidechain operator with high ratio + hard threshold → mapped to opacity |
| `sidechain_cross` | Sidechain operator with `input: "key"` + blend mode |
| `sidechain_crossfeed` | Sidechain operator with `input: "key"` + rgb_shift mapping |
| `sidechain_interference` | Sidechain operator with `input: "key"` + phase/beat mode |

The 6 current effects become **presets** of the sidechain operator. The underlying `_extract_sidechain_signal()` function is already the right abstraction.

#### 4. Gate Operator
**What it does:** Passes or blocks the signal (parameter modulation) based on a threshold with hold time. Like a noise gate on a parameter.

**Parameters:**
```json
{
  "type": "gate",
  "id": "gate_1",
  "threshold": 0.3,         // open when signal > threshold
  "hold_frames": 5,         // minimum frames to stay open
  "signal_source": "lfo_1", // what signal to gate on (another operator ID or content signal)
  "behavior_open": 1.0,     // value when gate is open
  "behavior_closed": 0.0,   // value when gate is closed
  "transition": 0,          // frames to fade between open/closed (0 = hard)
  "mappings": [...]
}
```

The current `gate()` in modulation.py is a per-pixel brightness gate (an effect). The Gate Operator is different — it's a modulation source that drives other parameters.

#### 5. Flanger Operator (Temporal Modulation)
**What it does:** Blends current frame with a past frame at a modulating delay depth. Currently `video_flanger()` does this to the entire frame — as an operator, it becomes a mappable temporal modulator.

**Refactored behavior:** The flanger's LFO and frame buffer become an operator that outputs a delayed/mixed frame. The frame buffer and LFO sweep are the operator; the "apply to frame" part is the mapping target (which could be any effect's input frame or any parameter).

#### 6. Phaser Operator (Frequency-Domain Modulation)
**What it does:** Sweeps notch filters through spatial frequencies. Currently `video_phaser()` hardcodes FFT processing — as an operator, the sweep position becomes a mappable control signal.

### Operator Data Model (JSON Schema)

```json
{
  "operators": [
    {
      "type": "lfo",
      "id": "lfo_1",
      "enabled": true,
      "waveform": "sine",
      "rate": 2.0,
      "sync": false,
      "depth": 1.0,
      "phase": 0.0,
      "polarity": "unipolar",
      "smoothing": 0.0,
      "mappings": [
        {
          "target_effect": "pixelsort",
          "target_param": "threshold",
          "min": 0.2,
          "max": 0.8,
          "curve": "linear"
        },
        {
          "target_effect": "wave",
          "target_param": "amplitude",
          "min": 5.0,
          "max": 30.0,
          "curve": "exponential"
        }
      ]
    },
    {
      "type": "sidechain",
      "id": "sc_1",
      "enabled": true,
      "source": "brightness",
      "input": "self",
      "threshold": 0.3,
      "mappings": [
        {
          "target_effect": "blur",
          "target_param": "radius",
          "min": 0,
          "max": 15,
          "curve": "linear"
        }
      ]
    }
  ]
}
```

### Operator Chaining

Operators can feed into each other:
- LFO → Gate → target (LFO signal is gated before reaching parameter)
- Sidechain → Envelope → target (sidechain triggers envelope, envelope shapes modulation)
- LFO → LFO rate (modulate the speed of another LFO — meta-modulation)

**Implementation:** Each operator outputs a float signal per frame. Before `apply_chain()` runs, the operator engine evaluates all operators in dependency order and writes the computed values into the effect params.

```python
class OperatorEngine:
    """Evaluates all operators and injects modulated values into effect chains."""

    def __init__(self, operators: list[dict]):
        self.operators = [create_operator(op) for op in operators]
        self._topo_sort()  # dependency order for chaining

    def evaluate(self, frame_index: int, frame: np.ndarray = None) -> dict:
        """Compute all operator outputs for this frame.

        Returns: {(effect_name, param_name): modulated_value}
        """
        param_overrides = {}
        signals = {}

        for op in self.operators:
            # If this operator's input is another operator's output, feed it
            if hasattr(op, 'signal_source') and op.signal_source in signals:
                op.set_input_signal(signals[op.signal_source])

            # Compute this operator's output signal
            signal = op.compute(frame_index, frame)
            signals[op.id] = signal

            # Map signal to target parameters
            for mapping in op.mappings:
                value = _apply_curve(signal, mapping['min'], mapping['max'], mapping['curve'])
                param_overrides[(mapping['target_effect'], mapping['target_param'])] = value

        return param_overrides

    def inject_into_chain(self, effects_list: list[dict], overrides: dict) -> list[dict]:
        """Merge operator outputs into effect params before apply_chain()."""
        modified = []
        for effect in effects_list:
            effect_copy = {**effect, "params": {**effect.get("params", {})}}
            for (eff_name, param_name), value in overrides.items():
                if effect_copy["name"] == eff_name:
                    effect_copy["params"][param_name] = value
            modified.append(effect_copy)
        return modified
```

### UI Design

**Operator Panel (bottom of effect rack):**
```
┌─────────────────────────────────────────────────┐
│ OPERATORS                               [+ Add] │
├─────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────┐ │
│ │ LFO 1                        [⊗] [≡] [👁]  │ │
│ │ ┌──────────────────────────────────────┐    │ │
│ │ │  ∿∿∿∿∿∿∿  (waveform display)       │    │ │
│ │ └──────────────────────────────────────┘    │ │
│ │ Wave: [sine ▼]  Rate: [2.0 Hz]  Depth: 80% │ │
│ │ Phase: 0°  Polarity: [uni ▼]  Smooth: 0%   │ │
│ │                                              │ │
│ │ MAPPINGS:                                    │ │
│ │ → pixelsort.threshold [0.2 ——●—— 0.8]      │ │
│ │ → wave.amplitude      [5.0 ——●—— 30.0]     │ │
│ │ [+ Map to parameter...]                      │ │
│ └─────────────────────────────────────────────┘ │
│                                                  │
│ ┌─────────────────────────────────────────────┐ │
│ │ Sidechain 1                  [⊗] [≡] [👁]  │ │
│ │ Source: [brightness ▼]  Input: [self ▼]     │ │
│ │ Thresh: 0.3  Ratio: 1.0  Atk: 0  Rel: 0   │ │
│ │ → blur.radius [0 ——●—— 15]                 │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

**Mapping workflow:**
1. Click "+ Map to parameter" on an operator
2. All parameter knobs across all effects in the chain start pulsing/highlighting
3. Click any parameter knob
4. Min/max range editor appears inline
5. Done — operator now modulates that parameter

**Waveform display:** Real-time mini oscilloscope showing the operator's output signal over the last 2 seconds (60 frames). A vertical line shows current position. Mapped parameter values shown as colored dots on the waveform.

**Mapping lines:** SVG lines from operator to target parameter, like TouchDesigner patch cords. Color-coded by operator. Can be hidden/shown.

### Implementation Priority

1. **Phase 1:** LFO operator + mapping engine (most requested, highest impact)
2. **Phase 2:** Sidechain operator (refactor existing sidechain effects)
3. **Phase 3:** Envelope operator (reuse existing ADSREnvelope)
4. **Phase 4:** Gate operator + operator chaining
5. **Phase 5:** Flanger/Phaser as operators (refactor dsp_filters.py)

### Files to Create/Modify

| File | Action |
|------|--------|
| `core/operators.py` | NEW — Operator base class, LFO, Envelope, Sidechain, Gate, OperatorEngine |
| `core/operator_presets.py` | NEW — Preset configurations (current sidechain effects become presets) |
| `effects/__init__.py` | MODIFY — `apply_chain()` accepts `operators` param, evaluates before applying |
| `server.py` | MODIFY — API endpoints accept operator config, pass to apply_chain |
| `ui/static/app.js` | MODIFY — Operator panel UI, mapping workflow, waveform display |
| `effects/sidechain.py` | REFACTOR — Extract signal extraction, keep as legacy aliases |
| `effects/dsp_filters.py` | REFACTOR — Extract LFO/buffer logic, keep as legacy aliases |

---

## 2. Effects / Tools / Operators / Image Editing Taxonomy

### The Problem

All 109 effects are treated identically in the UI — flat list in an effect rack. But they serve fundamentally different purposes:
- Color correction (hueshift, contrast, saturation) should be persistent adjustments with histogram feedback
- Modulation (LFO, flanger, ring mod) should be mappable to any parameter
- Glitch effects (pixelsort, datamosh, blockcorrupt) are the core creative tools
- Transform operations (crop, rotate, resize) don't exist yet but are expected

User said: "Those shouldn't be effects. Those should be part of the toolbar."

### Full Categorization of All 109 Effects

#### EFFECTS (Creative/Destructive — Stay in Effect Rack)

These are the core Entropic experience. They go in the effect chain and process frames.

**Glitch (4):** pixelsort, channelshift, displacement, bitcrush

**Distortion (5):** pencilsketch, smear, wave, mirror, chromatic

**Texture (10):** tvstatic, contours, scanlines, vhs, noise, blur, sharpen, edges, posterize, asciiart, brailleart

**Destruction (15):** datamosh, bytecorrupt, blockcorrupt, rowshift, jpegdamage, invertbands, databend, flowdistort, filmgrain, glitchrepeat, xorglitch, pixelannihilate, framesmash, channeldestroy, realdatamosh

**Temporal (13):** stutter, dropout, timestretch, feedback, tapestop, tremolo, delay, decimator, samplehold, granulator, beatrepeat, strobe, spectralfreeze, visualreverb

**Pixel Physics (21):** All pixel* effects (will be consolidated — see Section 4)

**Enhance (Creative) (5):** duotone, emboss, solarize, falsecolor, median

**Total Effects: 73**

#### TOOLS (Non-Destructive Adjustments — Toolbar / Panel)

These are professional color/image adjustment tools. They get their own panel with histogram visualization, Photoshop-style controls, and are always-on (not chain-ordered).

**Color Correction (move from effects):**
| Current Effect | Becomes Tool | Tool UI |
|---------------|-------------|---------|
| `hueshift` | Hue/Saturation panel | Hue wheel + saturation slider + lightness |
| `contrast` | Levels panel | Black/gray/white point histogram |
| `saturation` | Hue/Saturation panel | Combined with hueshift |
| `exposure` | Exposure panel | Stops slider + highlight recovery |
| `temperature` | White Balance panel | Temp + tint sliders |
| `invert` | Color panel submenu | Toggle button |
| `autolevels` | Levels panel (auto button) | One-click auto in levels panel |
| `histogrameq` | Levels panel (equalize button) | One-click in levels panel |
| `clahe` | Levels panel (adaptive button) | One-click in levels panel |
| `parallelcompress` | Tone panel | Shadows/highlights with blend |

**Color Filters (move from effects, become presets):**
| Current Effect | Becomes | Location |
|---------------|---------|----------|
| `cyanotype` | Color filter preset | Filter panel dropdown |
| `infrared` | Color filter preset | Filter panel dropdown |
| `tapesaturation` | Tone tool | Tone panel (drive + warmth) |
| `chroma_key` | Keying tool | Dedicated keying panel |
| `luma_key` | Keying tool | Dedicated keying panel |

**New Tools (not yet built):**
- Curves (RGB + per-channel)
- Color Balance (shadows/midtones/highlights)
- Selective Color
- Channel Mixer
- Levels (with histogram)

**Total Tools: 15 migrated + 5 new = 20**

#### OPERATORS (Modulation Sources — Operator Panel)

These generate control signals mapped to parameters on effects/tools. See Section 1 for full spec.

**Move from effects to operators:**
| Current Effect | Becomes Operator |
|---------------|-----------------|
| `lfo` | LFO Operator |
| `videoflanger` | Flanger Operator (or preset of LFO + delay) |
| `videophaser` | Phaser Operator |
| `spatialflanger` | Flanger Operator preset |
| `channelphaser` | Phaser Operator preset |
| `brightnessphaser` | Phaser Operator preset |
| `hueflanger` | Flanger Operator preset |
| `resonantfilter` | Filter Operator |
| `combfilter` | Comb Filter Operator |
| `feedbackphaser` | Phaser Operator preset |
| `freqflanger` | Flanger Operator preset |
| `ringmod` | Ring Mod Operator (sine carrier generator) |
| `amradio` | AM Operator (carrier modulation) |
| `gate` (modulation) | Gate Operator |
| `wavefold` | Wavefold Operator |
| All 6 sidechain effects | Sidechain Operator (6 presets) |

**Decision on ring_mod, am_radio, wavefold:** These apply a mathematical function to pixel values — they're "effects" in that they transform the frame, but they're "operators" in that they generate a modulation signal. **Recommendation:** Keep them as effects that CAN be operator-controlled. A ring_mod effect with its frequency parameter mapped from an LFO operator gives you FM synthesis on video. The operator system doesn't replace these — it enhances them.

**Revised count — Move to operators: 17** (LFO, 8 flanger/phaser variants, resonantfilter, combfilter, gate, 6 sidechain effects)

**Keep as effects but operator-mappable: 4** (ringmod, amradio, wavefold, gate)

#### IMAGE EDITING (Direct Manipulation — Canvas Toolbar)

These don't exist yet but are implied by the "Photoshop-level" expectation:
- Crop / Canvas Size
- Transform (rotate, flip, scale)
- Masks / Selections (rectangle, lasso, magic wand)
- Region-based effect application (already partially built via `core/region.py`)

**Priority:** LOW — these are nice-to-have. The region system already handles spatial masking. Full image editing tools are a v2.0 feature.

### Data Model Changes

Current `effects/__init__.py` has one flat `EFFECTS` dict. New model:

```python
# effects/__init__.py — new structure

EFFECT_TYPES = {
    "effect": "Creative frame effects (effect chain)",
    "tool": "Non-destructive adjustment (toolbar panel)",
    "operator": "Modulation source (operator panel)",
}

EFFECTS = {
    "pixelsort": {
        "fn": pixelsort,
        "type": "effect",           # NEW FIELD
        "category": "glitch",
        "params": {...},
        "description": "...",
    },
    "hueshift": {
        "fn": hue_shift,
        "type": "tool",             # RECLASSIFIED
        "category": "color",
        "tool_panel": "hue_sat",    # which tool panel it lives in
        "params": {...},
        "description": "...",
    },
    "lfo": {
        "fn": lfo,
        "type": "operator",         # RECLASSIFIED
        "category": "modulation",
        "params": {...},
        "description": "...",
    },
}
```

### UI Implications

```
┌──────────────────────────────────────────────────────────┐
│ TOOLBAR: [Color ▼] [Keying ▼] [Transform ▼]            │ ← Tools
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─── CANVAS (video preview) ──────────────────────┐    │
│  │                                                   │    │
│  │                                                   │    │
│  └───────────────────────────────────────────────────┘    │
│                                                          │
├──────────────────────────────────────────────────────────┤
│ EFFECT RACK: [pixelsort] → [smear] → [scanlines]       │ ← Effects
│                                                          │
│ OPERATORS: [LFO 1 ∿] [SC 1 ⌇]                         │ ← Operators
├──────────────────────────────────────────────────────────┤
│ TIMELINE / AUTOMATION                                    │ ← Timeline
└──────────────────────────────────────────────────────────┘
```

### Migration Strategy

**Phase 1 (non-breaking):** Add `type` field to all effects in registry. UI reads `type` and groups accordingly. Old API still works.

**Phase 2:** Build tool panels (Hue/Sat, Levels, Curves). Wire existing color effects to new panels.

**Phase 3:** Build operator panel and engine. Migrate LFO, sidechain effects to operators. Keep legacy aliases.

**Phase 4:** Clean up — remove legacy aliases, update all recipes to use new taxonomy.

---

## 3. Perform Mode as Timeline Automation Layer

### The Problem

Currently three separate modes: Quick | Timeline | Perform. User said: "Performance mode should be an automation layer on top of the timeline, with just additional tools being shown at the bottom, like we're combining Premiere and Ableton. It's not like a completely different mode."

Quick mode purpose is unclear: "I also don't know what the purpose of quick mode is."

### Current Architecture

**Quick mode:** Single frame preview. Apply effects to one frame. No timeline concept.

**Timeline mode:** Frame-range regions with effect chains. Scrub through video. Render with effects per region.

**Perform mode:** Real-time layer stack with ADSR envelopes, triggers, blend modes, transport. Uses `core/layer.py` LayerStack. Server-side `_perform_state` dict manages the session.

These share NO code or data model. Switching modes means losing state.

### Target Architecture: Premiere + Ableton Hybrid

**One unified view with three panels that show/hide:**

```
┌──────────────────────────────────────────────────────────────────┐
│ TOOLBAR: [Effects] [Tools] [Operators] [Import] [Export]         │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─── CANVAS ─────────────────────────────────────────────┐      │
│  │                                                         │      │
│  │             (video preview, always visible)             │      │
│  │                                                         │      │
│  └─────────────────────────────────────────────────────────┘      │
│                                                                   │
│  EFFECT RACK (right sidebar, collapsible):                        │
│  ┌────────────────────────────┐                                   │
│  │ [pixelsort] ≡ ✕           │                                   │
│  │   threshold: ───●───       │                                   │
│  │   sort_by: [brightness ▼] │                                   │
│  │ [smear] ≡ ✕               │                                   │
│  │   direction: [horiz ▼]    │                                   │
│  └────────────────────────────┘                                   │
│                                                                   │
├──────────────────────────────────────────────────────────────────┤
│ TIMELINE (always visible):                                        │
│ ┌────────────────────────────────────────────────────────────┐   │
│ │ [▶] 00:00:05 / 00:02:30                    BPM: [120]     │   │
│ ├────────────────────────────────────────────────────────────┤   │
│ │ Track 1: [VIDEO] ████████████████████████████████████████  │   │
│ │          Region A [pixelsort+smear]  Region B [datamosh]   │   │
│ │ Track 2: [LAYER] ░░░░░████████████░░░░░░░░░░░░░░████████  │   │
│ │          (overlay video, triggered by keyboard/MIDI)       │   │
│ │                                                            │   │
│ │ ── AUTOMATION LANES (toggle show/hide) ──                  │   │
│ │ A: pixelsort.threshold  ╱╲╱╲╱╲───────╱╲╱╲╱╲             │   │
│ │ A: smear.decay          ──────╲___╱────────────            │   │
│ │ A: [LFO 1 output]      ∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿              │   │
│ └────────────────────────────────────────────────────────────┘   │
│                                                                   │
│ PERFORM TOOLS (bottom bar, toggled with [P] key):                │
│ ┌────────────────────────────────────────────────────────────┐   │
│ │ Layer 1 [●] Layer 2 [○] Layer 3 [○] Layer 4 [○]          │   │
│ │ Trigger: [toggle ▼]  ADSR: [pluck ▼]  Blend: [normal ▼]  │   │
│ │ [■ REC] [▶ PLAY] [⏸ PAUSE]  Opacity: ───●───              │   │
│ └────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### Data Model for Automation Curves

```json
{
  "project": {
    "video_path": "/path/to/video.mp4",
    "fps": 30,
    "total_frames": 4500,
    "bpm": 120,

    "tracks": [
      {
        "id": "track_1",
        "type": "video",
        "source": "/path/to/video.mp4",
        "regions": [
          {
            "id": "region_a",
            "start_frame": 0,
            "end_frame": 900,
            "effects": [
              {"name": "pixelsort", "params": {"threshold": 0.5}},
              {"name": "smear", "params": {"decay": 0.95}}
            ],
            "muted": false
          }
        ]
      },
      {
        "id": "track_2",
        "type": "layer",
        "source": "/path/to/overlay.mp4",
        "trigger_mode": "toggle",
        "adsr_preset": "pluck",
        "blend_mode": "screen",
        "opacity": 0.8,
        "regions": []
      }
    ],

    "automation": [
      {
        "id": "auto_1",
        "target_track": "track_1",
        "target_region": "region_a",
        "target_effect": "pixelsort",
        "target_param": "threshold",
        "keyframes": [
          {"frame": 0, "value": 0.3, "curve": "linear"},
          {"frame": 150, "value": 0.8, "curve": "ease_in"},
          {"frame": 300, "value": 0.3, "curve": "ease_out"},
          {"frame": 450, "value": 0.9, "curve": "linear"}
        ]
      },
      {
        "id": "auto_2",
        "source": "operator",
        "operator_id": "lfo_1",
        "target_track": "track_1",
        "target_region": "region_a",
        "target_effect": "smear",
        "target_param": "decay",
        "keyframes": []
      }
    ],

    "operators": [
      {
        "type": "lfo",
        "id": "lfo_1",
        "waveform": "sine",
        "rate": 2.0,
        "mappings": [
          {
            "target_effect": "smear",
            "target_param": "decay",
            "min": 0.8,
            "max": 0.99
          }
        ]
      }
    ],

    "perform": {
      "layers": [
        {
          "layer_id": 0,
          "track_id": "track_2",
          "trigger_mode": "toggle",
          "adsr_preset": "pluck",
          "blend_mode": "screen",
          "key_binding": "1"
        }
      ],
      "recording": {
        "active": false,
        "buffer": []
      }
    }
  }
}
```

### Keyframe Interpolation

```python
def interpolate_keyframes(keyframes: list[dict], frame: int) -> float:
    """Interpolate automation value at a given frame.

    Each keyframe: {"frame": int, "value": float, "curve": str}
    Curves: "linear", "ease_in", "ease_out", "ease_in_out", "step", "hold"
    """
    if not keyframes:
        return None

    # Before first keyframe
    if frame <= keyframes[0]["frame"]:
        return keyframes[0]["value"]

    # After last keyframe
    if frame >= keyframes[-1]["frame"]:
        return keyframes[-1]["value"]

    # Find surrounding keyframes
    for i in range(len(keyframes) - 1):
        a, b = keyframes[i], keyframes[i + 1]
        if a["frame"] <= frame <= b["frame"]:
            t = (frame - a["frame"]) / max(1, b["frame"] - a["frame"])

            if b["curve"] == "linear":
                return a["value"] + (b["value"] - a["value"]) * t
            elif b["curve"] == "ease_in":
                return a["value"] + (b["value"] - a["value"]) * (t * t)
            elif b["curve"] == "ease_out":
                return a["value"] + (b["value"] - a["value"]) * (1 - (1 - t) ** 2)
            elif b["curve"] == "ease_in_out":
                t2 = t * t * (3 - 2 * t)  # smoothstep
                return a["value"] + (b["value"] - a["value"]) * t2
            elif b["curve"] in ("step", "hold"):
                return a["value"]  # hold previous value until next keyframe

    return keyframes[-1]["value"]
```

### Quick Mode Resolution

**Recommendation: Remove Quick mode. Replace with "single frame" behavior within Timeline.**

When no regions are defined, Timeline mode behaves exactly like Quick mode — you see one frame, you add effects, you preview. The timeline just shows a single full-length region.

This eliminates user confusion ("I don't know what Quick mode is for") and simplifies the UI to two concepts: **Timeline** (with automation) and **Perform tools** (optional panel).

### Files to Create/Modify

| File | Action |
|------|--------|
| `core/automation.py` | NEW — Keyframe interpolation, automation lane management |
| `core/project.py` | NEW — Unified project data model (tracks, regions, automation, operators, perform) |
| `server.py` | MODIFY — Unified render pipeline reads automation + operators + perform state |
| `ui/static/app.js` | MAJOR REWRITE — Unified view replacing Quick/Timeline/Perform tabs |
| `ui/templates/index.html` | MODIFY — New layout structure |

---

## 4. Pixel Physics Consolidation

### The Problem

21 pixel physics effects share almost identical code structure:
1. Get or create state via `_get_state(key, h, w)` — same 4 numpy arrays (dx, dy, vx, vy)
2. Compute forces (the only part that differs)
3. Apply forces to velocity: `state["vx"] = state["vx"] * damping + fx * scale`
4. Update displacement: `state["dx"] += state["vx"]`
5. Clamp displacement
6. Remap frame: `_remap_frame(frame, state["dx"], state["dy"], boundary)`
7. Cleanup: `if frame_index >= total_frames - 1: _physics_state.pop(key, None)`

The user observed: "it seems like they're all kind of doing similar things and they seem a little bit redundant."

### Consolidation Plan

#### Mega-Effect 1: Pixel Dynamics (6 modes)
**What:** Physical forces that create motion — push, pull, spin, bounce, drip.

| Mode | Source Effect | Force Model |
|------|-------------|-------------|
| `liquify` | pixel_liquify | Multi-octave turbulent flow field (sine + cos noise) |
| `gravity` | pixel_gravity | N-body gravitational attraction toward wandering points |
| `vortex` | pixel_vortex | Spinning whirlpools with radial pull |
| `explode` | pixel_explode | Radial outward force from a point with optional gravity |
| `elastic` | pixel_elastic | Spring-mass system (Hooke's law with damping) |
| `melt` | pixel_melt | Downward gravity + heat-based lateral diffusion |

**Shared parameters (all modes):**
```json
{
  "mode": "liquify",
  "strength": 5.0,          // overall force multiplier
  "damping": 0.92,          // velocity decay per frame
  "boundary": "wrap",       // clamp, black, wrap, mirror
  "seed": 42,
  "frame_index": 0,
  "total_frames": 1
}
```

**Per-mode parameters:**
```json
// liquify
{"viscosity": 0.92, "turbulence": 3.0, "flow_scale": 40.0, "speed": 1.0}

// gravity
{"num_attractors": 5, "attractor_radius": 0.3, "wander": 0.5}

// vortex
{"num_vortices": 3, "spin_strength": 5.0, "pull_strength": 2.0, "radius": 0.25}

// explode
{"origin": "center", "gravity": 0.0, "scatter": 0.0}

// elastic
{"stiffness": 0.3, "mass": 1.0, "force_type": "turbulence"}

// melt
{"heat": 3.0, "gravity": 2.0, "melt_source": "top"}
```

#### Mega-Effect 2: Pixel Cosmos (8 modes)
**What:** Sci-fi/impossible physics — things that don't exist in nature.

| Mode | Source Effect | Force Model |
|------|-------------|-------------|
| `blackhole` | pixel_blackhole | Singularity with event horizon + spaghettification |
| `antigravity` | pixel_antigravity | Repulsion zones with oscillation |
| `magnetic` | pixel_magnetic | Dipole/quadrupole/toroidal field lines |
| `timewarp` | pixel_timewarp | Displacement reversal + echo ghosts |
| `dimensionfold` | pixel_dimensionfold | Space folds over itself along axes |
| `wormhole` | pixel_wormhole | Paired portals that teleport pixels |
| `quantum` | pixel_quantum | Barrier tunneling + superposition ghosts |
| `darkenergy` | pixel_darkenergy | Accelerating expansion |
| `superfluid` | pixel_superfluid | Zero-friction flow + quantized vortices |

**Shared parameters:** Same as Pixel Dynamics (mode, strength, damping, boundary, seed).

**UI:** Mode selector dropdown + shared physics controls + per-mode parameters that appear/disappear based on selected mode.

#### Mega-Effect 3: Pixel Organic (3 modes)
**What:** Natural/material simulations — ink, ghosts, bubbles.

| Mode | Source Effect | Force Model |
|------|-------------|-------------|
| `inkdrop` | pixel_inkdrop | Diffusion + surface tension + Marangoni tendrils |
| `haunt` | pixel_haunt | Ghostly afterimages with crackle |
| `bubbles` | pixel_bubbles | Multiple portals with void interiors |

#### Shared Physics Engine

```python
class PhysicsEngine:
    """Unified pixel physics engine. All 17 modes share this state + remap."""

    def __init__(self, h: int, w: int, seed: int = 42):
        self.h = h
        self.w = w
        self.seed = seed
        self.dx = np.zeros((h, w), dtype=np.float32)
        self.dy = np.zeros((h, w), dtype=np.float32)
        self.vx = np.zeros((h, w), dtype=np.float32)
        self.vy = np.zeros((h, w), dtype=np.float32)
        # Optional per-mode state
        self.extra = {}

    def apply_forces(self, fx: np.ndarray, fy: np.ndarray, damping: float):
        """Universal force application. Every mode calls this."""
        self.vx = self.vx * damping + fx
        self.vy = self.vy * damping + fy
        self.dx += self.vx
        self.dy += self.vy
        # Clamp
        max_disp = max(self.h, self.w) * 0.3
        self.dx = np.clip(self.dx, -max_disp, max_disp)
        self.dy = np.clip(self.dy, -max_disp, max_disp)

    def remap(self, frame: np.ndarray, boundary: str = "wrap") -> np.ndarray:
        """Remap frame through current displacement field."""
        return _remap_frame(frame, self.dx, self.dy, boundary)

    def reset(self):
        """Clear all state."""
        self.dx[:] = 0
        self.dy[:] = 0
        self.vx[:] = 0
        self.vy[:] = 0
        self.extra.clear()


# Force calculators — one per mode
def _compute_forces_liquify(engine, frame_index, **params) -> tuple[np.ndarray, np.ndarray]:
    """Liquify force field — multi-octave turbulence."""
    # ... (extract from current pixel_liquify)
    return fx, fy

def _compute_forces_gravity(engine, frame_index, **params) -> tuple[np.ndarray, np.ndarray]:
    """N-body gravitational attraction."""
    # ... (extract from current pixel_gravity)
    return fx, fy

# ... etc for each mode

FORCE_CALCULATORS = {
    "liquify": _compute_forces_liquify,
    "gravity": _compute_forces_gravity,
    "vortex": _compute_forces_vortex,
    # ... all modes
}


def pixel_dynamics(frame, mode="liquify", strength=5.0, damping=0.92,
                   boundary="wrap", seed=42, frame_index=0, total_frames=1,
                   **mode_params):
    """Unified pixel dynamics effect — 6 physical force modes."""
    h, w = frame.shape[:2]
    key = f"dynamics_{mode}_{seed}"

    # Get or create engine
    if key not in _physics_engines:
        _physics_engines[key] = PhysicsEngine(h, w, seed)
    engine = _physics_engines[key]

    # Compute mode-specific forces
    calc = FORCE_CALCULATORS.get(mode)
    if calc is None:
        return frame
    fx, fy = calc(engine, frame_index, **mode_params)

    # Apply forces and remap
    engine.apply_forces(fx * strength * 0.01, fy * strength * 0.01, damping)
    result = engine.remap(frame, boundary)

    # Cleanup at end (FIX: add preview_mode check)
    if frame_index >= total_frames - 1 and total_frames > 1:
        _physics_engines.pop(key, None)

    return np.clip(result, 0, 255).astype(np.uint8)
```

### State Management Fix for Preview Mode

The root cause of all broken physics effects: `server.py:377` calls `apply_chain()` without `frame_index`/`total_frames`, defaulting to (0, 1). The cleanup condition `frame_index >= total_frames - 1` becomes `0 >= 0` → True → state nuked.

**Fix (two parts):**

1. **Pass frame_index and total_frames in server.py:**
```python
# server.py:377 — FIX
frame = apply_chain(
    frame, chain.effects,
    frame_index=chain.frame_number if hasattr(chain, 'frame_number') else 0,
    total_frames=_state["video_info"].get("total_frames", 1) if _state.get("video_info") else 1,
    watermark=False
)
```

2. **Add preview_mode flag to skip cleanup:**
```python
# In all stateful effects — change cleanup condition:
# OLD:
if frame_index >= total_frames - 1:
    _physics_state.pop(key, None)

# NEW:
if frame_index >= total_frames - 1 and total_frames > 1:
    _physics_state.pop(key, None)
# (single-frame preview has total_frames=1, so 1 > 1 = False, skip cleanup)
```

### Print Degradation Effects

`pixel_xerox`, `pixel_fax`, `pixel_risograph` are NOT pixel physics — they don't use displacement fields. They simulate printing artifacts. **Do NOT consolidate these into the physics mega-effects.** They stay as separate effects in the "destruction" category or become their own mini-group "Print Degradation" within destruction.

### Files to Create/Modify

| File | Action |
|------|--------|
| `effects/physics.py` | MAJOR REFACTOR — PhysicsEngine class, force calculators, 3 mega-effect functions |
| `effects/__init__.py` | MODIFY — Register 3 new mega-effects, deprecate 18 individual effects (keep as aliases) |
| `server.py` | FIX — Pass frame_index/total_frames to apply_chain() in preview endpoint |

---

## 5. Photoshop-Level Color Tools

### The Problem

User said: "Truly, it needs to be as good as Photoshop or Premiere, or any of the free image editing software. We need to copy what competitors do."

Current color tools are basic sliders with no visual feedback. No histogram. No curves. No levels.

### What Competitors Offer

#### Adobe Photoshop
- **Levels:** Input/output histogram with black point, gray point (gamma), white point sliders. Per-channel (RGB, R, G, B). Auto button. Eyedroppers for black/white/gray point sampling.
- **Curves:** 256-point curve per channel. Click-and-drag control points. Histogram underlay. Presets (increase contrast, cross process, etc.).
- **Hue/Saturation:** Hue slider (-180 to +180), Saturation (-100 to +100), Lightness (-100 to +100). Master or per-color-range (Reds, Yellows, Greens, Cyans, Blues, Magentas). Colorize mode.
- **Color Balance:** Shadows/Midtones/Highlights selector. Cyan-Red, Magenta-Green, Yellow-Blue sliders per range.
- **Selective Color:** Per color range (Reds, Yellows, etc.), adjust Cyan/Magenta/Yellow/Black percentages.
- **Channel Mixer:** Per output channel, set percentage from each input channel. Monochrome mode.
- **Brightness/Contrast:** Simple sliders. Legacy mode toggle.

#### DaVinci Resolve
- **Lift/Gamma/Gain color wheels** (shadows, midtones, highlights)
- **Log color wheels** (low, mid, high)
- **Curves:** Custom, Hue vs Hue, Hue vs Sat, Hue vs Lum, Lum vs Sat, Sat vs Sat
- **Color Warper:** 2D mesh deformation of hue/saturation
- **Qualifier:** HSL qualifier for selective keying
- **Scopes:** Waveform, Vectorscope, Histogram, Parade

#### Adobe Premiere
- **Lumetri Color panel:** Basic (exposure, contrast, highlights, shadows, whites, blacks, saturation, vibrance), Creative (look LUT, faded film, sharpen, vibrance, saturation), Curves (RGB + Hue Saturation), Color Wheels (shadows, midtones, highlights), HSL Secondary (per-color targeting), Vignette
- **Scopes:** Waveform, Vectorscope, Histogram, Parade

### Implementation Spec

#### Tool Panel Architecture

Each tool gets a pop-out panel with:
1. A histogram or scope visualization (live-updating)
2. Direct manipulation controls (sliders, color wheels, curves)
3. Apply/Reset buttons
4. Presets dropdown

```
┌─── COLOR TOOLS PANEL ────────────────────────────┐
│ [Levels] [Curves] [Hue/Sat] [Balance] [Mixer]   │
├──────────────────────────────────────────────────┤
│                                                   │
│ ┌─── LEVELS ──────────────────────────────────┐  │
│ │         HISTOGRAM (live)                     │  │
│ │  ▓▓▓▓▓░▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░▓▓▓▓▓▓▓▓░░░    │  │
│ │  ▲        ▲              ▲                   │  │
│ │  black    gray           white               │  │
│ │  [0]      [1.0]          [255]               │  │
│ │                                              │  │
│ │  Output:                                     │  │
│ │  [0] ─────────────────────── [255]           │  │
│ │                                              │  │
│ │  Channel: [RGB ▼] [Auto] [Reset]            │  │
│ └──────────────────────────────────────────────┘  │
│                                                   │
│ ┌─── CURVES ──────────────────────────────────┐  │
│ │  255 ┤            ●                          │  │
│ │      │          /                             │  │
│ │      │        ●                               │  │
│ │      │      /                                 │  │
│ │      │    /                                   │  │
│ │      │  ●                                     │  │
│ │    0 ├────────────────────── 255              │  │
│ │      Channel: [RGB ▼] [Reset]                │  │
│ └──────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

#### Backend Implementation

**Histogram computation (server-side, per preview frame):**
```python
def compute_histogram(frame: np.ndarray) -> dict:
    """Compute RGB histogram for a frame. Returns 256-bin counts per channel."""
    return {
        "r": np.histogram(frame[:, :, 0], bins=256, range=(0, 256))[0].tolist(),
        "g": np.histogram(frame[:, :, 1], bins=256, range=(0, 256))[0].tolist(),
        "b": np.histogram(frame[:, :, 2], bins=256, range=(0, 256))[0].tolist(),
        "lum": np.histogram(
            0.299 * frame[:, :, 0] + 0.587 * frame[:, :, 1] + 0.114 * frame[:, :, 2],
            bins=256, range=(0, 256)
        )[0].tolist(),
    }
```

**Levels tool:**
```python
def levels_adjust(
    frame: np.ndarray,
    input_black: int = 0,       # 0-254
    input_white: int = 255,     # 1-255
    gamma: float = 1.0,         # 0.1-10.0
    output_black: int = 0,      # 0-254
    output_white: int = 255,    # 1-255
    channel: str = "rgb",       # rgb, r, g, b
) -> np.ndarray:
    """Photoshop-compatible levels adjustment."""
    f = frame.astype(np.float32)

    # Input levels: remap input range to 0-1
    input_range = max(1, input_white - input_black)
    if channel == "rgb":
        f = np.clip((f - input_black) / input_range, 0, 1)
    else:
        ch_idx = {"r": 0, "g": 1, "b": 2}[channel]
        f[:, :, ch_idx] = np.clip((f[:, :, ch_idx] - input_black) / input_range, 0, 1)

    # Gamma correction
    if channel == "rgb":
        f = np.power(f / 255.0, 1.0 / gamma) * 255.0 if gamma != 1.0 else f
    else:
        ch = f[:, :, ch_idx] / 255.0
        f[:, :, ch_idx] = np.power(ch, 1.0 / gamma) * 255.0

    # Output levels: remap 0-1 to output range
    output_range = output_white - output_black
    if channel == "rgb":
        f = f / 255.0 * output_range + output_black
    else:
        f[:, :, ch_idx] = f[:, :, ch_idx] / 255.0 * output_range + output_black

    return np.clip(f, 0, 255).astype(np.uint8)
```

**Curves tool:**
```python
def curves_adjust(
    frame: np.ndarray,
    curve_points: list[tuple[int, int]],  # [(input, output), ...] 0-255
    channel: str = "rgb",
) -> np.ndarray:
    """Apply a curves adjustment. Points are interpolated with cubic spline."""
    from scipy.interpolate import CubicSpline

    # Build lookup table from control points
    if len(curve_points) < 2:
        return frame

    xs = [p[0] for p in sorted(curve_points)]
    ys = [p[1] for p in sorted(curve_points)]

    # Cubic spline interpolation
    cs = CubicSpline(xs, ys, bc_type='clamped')
    lut = np.clip(cs(np.arange(256)), 0, 255).astype(np.uint8)

    f = frame.copy()
    if channel == "rgb":
        for c in range(3):
            f[:, :, c] = lut[f[:, :, c]]
    else:
        ch_idx = {"r": 0, "g": 1, "b": 2}[channel]
        f[:, :, ch_idx] = lut[f[:, :, ch_idx]]

    return f
```

**Hue/Saturation tool:**
```python
def hue_saturation_adjust(
    frame: np.ndarray,
    hue: float = 0.0,           # -180 to +180 degrees
    saturation: float = 0.0,     # -100 to +100
    lightness: float = 0.0,      # -100 to +100
    color_range: str = "master", # master, reds, yellows, greens, cyans, blues, magentas
) -> np.ndarray:
    """Photoshop-compatible Hue/Saturation adjustment."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV).astype(np.float32)

    # Color range mask
    if color_range == "master":
        mask = np.ones(frame.shape[:2], dtype=np.float32)
    else:
        hue_ranges = {
            "reds": (0, 30, 330, 360),       # wraps around
            "yellows": (30, 90),
            "greens": (90, 150),
            "cyans": (150, 210),
            "blues": (210, 270),
            "magentas": (270, 330),
        }
        r = hue_ranges[color_range]
        h = hsv[:, :, 0] * 2  # OpenCV hue is 0-180, convert to 0-360
        if len(r) == 4:  # wrapping range (reds)
            mask = ((h >= r[2]) | (h <= r[1])).astype(np.float32)
        else:
            mask = ((h >= r[0]) & (h <= r[1])).astype(np.float32)
        # Soft edges
        mask = cv2.GaussianBlur(mask, (5, 5), 0)

    # Apply adjustments
    hsv[:, :, 0] = (hsv[:, :, 0] + hue / 2.0 * mask) % 180
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] + saturation * 2.55 * mask, 0, 255)
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] + lightness * 2.55 * mask, 0, 255)

    return cv2.cvtColor(np.clip(hsv, 0, [180, 255, 255]).astype(np.uint8), cv2.COLOR_HSV2RGB)
```

**Color Balance tool:**
```python
def color_balance(
    frame: np.ndarray,
    shadows_cr: float = 0.0,    # -100 to +100 (cyan-red)
    shadows_mg: float = 0.0,    # -100 to +100 (magenta-green)
    shadows_yb: float = 0.0,    # -100 to +100 (yellow-blue)
    midtones_cr: float = 0.0,
    midtones_mg: float = 0.0,
    midtones_yb: float = 0.0,
    highlights_cr: float = 0.0,
    highlights_mg: float = 0.0,
    highlights_yb: float = 0.0,
) -> np.ndarray:
    """Photoshop-compatible Color Balance."""
    f = frame.astype(np.float32)
    lum = 0.299 * f[:, :, 0] + 0.587 * f[:, :, 1] + 0.114 * f[:, :, 2]

    # Shadow/midtone/highlight masks (soft transitions)
    shadow_mask = np.clip(1.0 - lum / 128.0, 0, 1)
    highlight_mask = np.clip((lum - 128.0) / 128.0, 0, 1)
    midtone_mask = 1.0 - shadow_mask - highlight_mask
    midtone_mask = np.clip(midtone_mask, 0, 1)

    # Apply per-range color shifts
    for mask, cr, mg, yb in [
        (shadow_mask, shadows_cr, shadows_mg, shadows_yb),
        (midtone_mask, midtones_cr, midtones_mg, midtones_yb),
        (highlight_mask, highlights_cr, highlights_mg, highlights_yb),
    ]:
        if cr != 0 or mg != 0 or yb != 0:
            scale = 2.55  # map -100..100 to -255..255
            f[:, :, 0] += mask * cr * scale   # red channel
            f[:, :, 1] += mask * mg * scale   # green channel
            f[:, :, 2] += mask * yb * scale   # blue channel

    return np.clip(f, 0, 255).astype(np.uint8)
```

### API Changes

```python
# New endpoint for histogram data
@app.post("/api/histogram")
async def get_histogram(req: PreviewRequest):
    """Return histogram data for the current frame + effects."""
    frame = extract_single_frame(...)
    frame = apply_chain(frame, req.effects, ...)
    return {"histogram": compute_histogram(frame)}

# Tools are applied BEFORE the effect chain (non-destructive base layer)
@app.post("/api/preview")
async def preview(chain: EffectChain):
    frame = extract_single_frame(...)
    # 1. Apply tools (color correction, levels, curves)
    frame = apply_tools(frame, chain.tools)
    # 2. Apply effects (glitch, destruction, etc.)
    frame = apply_chain(frame, chain.effects, ...)
    # 3. Return preview + histogram
    return {
        "preview": _frame_to_data_url(frame),
        "histogram": compute_histogram(frame),
    }
```

### Files to Create/Modify

| File | Action |
|------|--------|
| `effects/color_tools.py` | NEW — levels_adjust, curves_adjust, hue_saturation_adjust, color_balance, channel_mixer, selective_color |
| `core/histogram.py` | NEW — compute_histogram, waveform_scope, vectorscope |
| `server.py` | MODIFY — /api/histogram endpoint, apply_tools() before apply_chain() |
| `ui/static/color-panel.js` | NEW — Histogram canvas, curves editor, levels UI, color balance wheels |

---

## 6. Parameter Sensitivity / Metering System

### The Problem

User observed across many effects: "There's like a threshold for some of the parameters where things get really blown out and then underneath kind of nothing happens."

This is a systemic UX problem. Most parameters use linear 0-1 or 0-255 scaling, but the perceptual response is highly non-linear. The "sweet spot" may be 10% of the slider range, with 45% doing nothing visible and 45% completely blown out.

### Root Cause Analysis

**Why linear sliders fail for visual effects:**

1. **Exponential response curves:** Many effects use exponential math (e.g., gravity force `∝ 1/r²`). A linear slider on an exponential curve gives most of the change in the last 10% of travel.

2. **Threshold effects:** Some parameters have hard thresholds where behavior switches (e.g., edge detection threshold). Below = nothing. Above = everything. The transition band is narrow.

3. **Saturation effects:** Parameters like contrast/exposure saturate — once values are clipped to 0 or 255, pushing further does nothing. The useful range is much smaller than the parameter range.

4. **Content-dependent ranges:** The "right" value for a parameter depends on the input image. Dark images need different edge thresholds than bright images. A fixed slider range can't account for this.

### Solution: Non-Linear Parameter Scaling

**Per-parameter scaling functions:**

```python
PARAM_SCALING = {
    # Format: (scale_type, extra_config)
    # "linear" — default, no transformation
    # "exponential" — more resolution at low end
    # "logarithmic" — more resolution at high end
    # "s_curve" — more resolution in the middle
    # "centered" — most resolution around a center point

    "edges.threshold": ("centered", {"center": 0.3, "width": 0.2}),
    "contrast.amount": ("s_curve", {"inflection": 50}),
    "pixelelastic.mass": ("exponential", {"base": 2.0}),
    "pixelgravity.gravity_strength": ("logarithmic", {}),
    "smear.decay": ("centered", {"center": 0.93, "width": 0.05}),
    "exposure.stops": ("linear", {}),  # already perceptual (EV stops)
}

def scale_param(effect_name: str, param_name: str, slider_value: float) -> float:
    """Convert slider position (0.0-1.0) to parameter value using non-linear scaling."""
    key = f"{effect_name}.{param_name}"
    scaling = PARAM_SCALING.get(key, ("linear", {}))
    scale_type, config = scaling

    param_def = EFFECTS[effect_name]["params"][param_name]
    p_min = config.get("min", 0)
    p_max = config.get("max", param_def if isinstance(param_def, (int, float)) else 1.0)

    if scale_type == "linear":
        return p_min + (p_max - p_min) * slider_value

    elif scale_type == "exponential":
        # More resolution at low values
        base = config.get("base", 2.0)
        return p_min + (p_max - p_min) * ((base ** slider_value - 1) / (base - 1))

    elif scale_type == "logarithmic":
        # More resolution at high values
        return p_min + (p_max - p_min) * (1 - math.log(1 + (1 - slider_value) * 9) / math.log(10))

    elif scale_type == "s_curve":
        # More resolution in the middle
        t = slider_value
        s = t * t * (3 - 2 * t)  # smoothstep
        return p_min + (p_max - p_min) * s

    elif scale_type == "centered":
        # Most resolution around a center point
        center = config["center"]
        width = config["width"]
        # Map 0-1 to center-width..center+width with sigmoid-like compression
        t = (slider_value - 0.5) * 2  # -1 to +1
        return center + width * np.tanh(t * 2)
```

### Visual Diagnostics

#### 1. Parameter Histogram / Sensitivity Indicator

For each parameter, show a small inline visualization of what range produces visible changes:

```
threshold: [░░░░░▓▓▓▓▓▓▓▓▓░░░░░]
                 ^^^^^^^^^^^
                 active zone

           Nothing visible  | Sweet spot | Blown out
```

**Implementation:** On first preview, auto-compute the sensitivity profile:
1. Render frame with param at 0%, 10%, 20%, ..., 100%
2. Compute frame difference (mean absolute pixel diff) between each step
3. Identify: dead zone (diff < threshold), active zone (diff > threshold), saturated zone (diff = 0 because values clipped)
4. Display as colored bar beneath the slider

```python
def compute_param_sensitivity(effect_name: str, param_name: str,
                                frame: np.ndarray, steps: int = 11) -> dict:
    """Compute sensitivity profile for a parameter on a given frame."""
    param_def = EFFECTS[effect_name]["params"]
    base_params = param_def.copy()

    # Get parameter range
    p_val = base_params[param_name]
    if isinstance(p_val, float):
        p_min, p_max = 0.0, max(p_val * 3, 1.0)
    elif isinstance(p_val, int):
        p_min, p_max = 0, max(p_val * 3, 10)
    else:
        return {"zones": [], "error": "non-numeric parameter"}

    results = []
    prev_frame = None

    for i in range(steps):
        t = i / (steps - 1)
        value = p_min + (p_max - p_min) * t
        test_params = {**base_params, param_name: value}

        fn, _ = get_effect(effect_name)
        result = fn(frame.copy(), **test_params)

        if prev_frame is not None:
            diff = np.mean(np.abs(result.astype(float) - prev_frame.astype(float)))
            results.append({"position": t, "value": value, "diff": diff})

        prev_frame = result

    # Classify zones
    max_diff = max(r["diff"] for r in results) if results else 1
    zones = []
    for r in results:
        normalized = r["diff"] / max(max_diff, 1e-6)
        if normalized < 0.05:
            zone = "dead"
        elif normalized > 0.8:
            zone = "hot"
        else:
            zone = "active"
        zones.append({**r, "zone": zone, "normalized_diff": normalized})

    return {"zones": zones, "max_diff": max_diff}
```

#### 2. Frame Diff Tool

User said: "Change a parameter, see what pixels actually changed. If seed changes and nothing changes on screen, that's a bug."

```python
@app.post("/api/frame-diff")
async def frame_diff(req: FrameDiffRequest):
    """Compare two parameter values and return a diff visualization."""
    frame = extract_single_frame(...)

    # Apply effect with value A
    frame_a = apply_effect(frame.copy(), req.effect_name, **{req.param_name: req.value_a})
    # Apply effect with value B
    frame_b = apply_effect(frame.copy(), req.effect_name, **{req.param_name: req.value_b})

    # Compute diff
    diff = np.abs(frame_a.astype(float) - frame_b.astype(float))
    diff_normalized = (diff / diff.max() * 255).astype(np.uint8) if diff.max() > 0 else diff.astype(np.uint8)

    # Heatmap visualization
    diff_gray = np.mean(diff_normalized, axis=2).astype(np.uint8)
    heatmap = cv2.applyColorMap(diff_gray, cv2.COLORMAP_JET)

    return {
        "diff_image": _frame_to_data_url(heatmap),
        "mean_diff": float(np.mean(diff)),
        "max_diff": float(np.max(diff)),
        "changed_pixels_pct": float(np.mean(diff_gray > 5) * 100),
    }
```

#### 3. Auto-Range Detection

On effect add, auto-probe the parameter space and set the slider range to the useful zone:

```python
def auto_detect_range(effect_name: str, param_name: str, frame: np.ndarray) -> dict:
    """Find the useful range for a parameter on this specific frame."""
    sensitivity = compute_param_sensitivity(effect_name, param_name, frame, steps=21)
    active_zones = [z for z in sensitivity["zones"] if z["zone"] == "active"]

    if not active_zones:
        return {"min": 0, "max": 1, "recommended": 0.5}

    useful_min = active_zones[0]["value"]
    useful_max = active_zones[-1]["value"]

    # Add 10% padding
    padding = (useful_max - useful_min) * 0.1
    return {
        "min": max(0, useful_min - padding),
        "max": useful_max + padding,
        "recommended": (useful_min + useful_max) / 2,
    }
```

### UI: Sensitivity Meter on Sliders

Each parameter slider gets a background gradient showing the sensitivity profile:

```
threshold: ░░░░░▓▓▓▓▓▓▓▓▓░░░░░
           ←dead→←active→←blown→
                    ●  ← current value (draggable)
```

Colors:
- Gray (░): Dead zone — changing this does nothing visible
- Green (▓): Active zone — parameter changes are visible
- Red: Hot zone — parameter changes blow out the image
- Blue dot (●): Current value

### Perceptual Calibration Process

For each effect release, run this calibration:
1. Test against 10 diverse reference images (dark, bright, colorful, grayscale, high detail, low detail)
2. Compute sensitivity profiles for each parameter on each image
3. Average the profiles to find universal sweet spots
4. Set default scaling curves accordingly
5. Store in `effects/param_calibration.json`

### Files to Create/Modify

| File | Action |
|------|--------|
| `core/param_scaling.py` | NEW — Non-linear scaling functions, scale_param(), PARAM_SCALING config |
| `core/param_sensitivity.py` | NEW — compute_param_sensitivity(), auto_detect_range() |
| `effects/param_calibration.json` | NEW — Pre-computed sensitivity profiles per effect per param |
| `server.py` | MODIFY — /api/frame-diff, /api/param-sensitivity endpoints |
| `ui/static/app.js` | MODIFY — Sensitivity gradient on sliders, diff tool button |

---

## Implementation Roadmap

### Phase 0: Critical Bug Fixes (Before Anything Else)
**Estimated scope: 1 session**

1. Fix `server.py:377` — pass `frame_index`/`total_frames` to `apply_chain()`
2. Fix cleanup condition in all stateful effects: `total_frames > 1` guard
3. Fix `app.js` upload handler — check `res.ok`, show error toasts
4. Fix history order — most recent at top
5. Fix brailleart encoding — ensure UTF-8 font rendering

**This unblocks:** All 7 broken pixel physics effects, datamosh, flow distort, byte corrupt, temporal effects in preview, and file upload.

### Phase 1: Parameter UX (Quick Wins)
**Estimated scope: 1-2 sessions**

1. Non-linear parameter scaling for worst offenders (edges, contrast, elastic, gravity)
2. Scrollable params → horizontal strip or accordion layout
3. Mix slider tooltip/label
4. Seed audit (systematic check which effects actually use seed)

### Phase 2: Color Tools
**Estimated scope: 2-3 sessions**

1. Histogram computation + API endpoint
2. Levels tool (backend + UI)
3. Curves tool (backend + UI)
4. Hue/Saturation tool (backend + UI)
5. Color Balance tool (backend + UI)
6. Migrate existing color effects to tool panel
7. Color filter presets (cyanotype, infrared as presets)

### Phase 3: Taxonomy + UI Restructure
**Estimated scope: 2-3 sessions**

1. Add `type` field to all effects in registry
2. Reorganize UI: toolbar (tools), effect rack (effects), operator panel (operators)
3. Build operator panel UI (empty, ready for operators)
4. Merge Quick mode into Timeline (single full-region behavior)

### Phase 4: Operator System
**Estimated scope: 3-4 sessions**

1. OperatorEngine base class + LFO operator
2. Mapping workflow UI (click operator → click parameter)
3. Waveform display
4. Sidechain operator (refactor existing sidechain effects)
5. Envelope operator (reuse ADSREnvelope)
6. Gate operator
7. Operator chaining

### Phase 5: Timeline Automation
**Estimated scope: 2-3 sessions**

1. Unified project data model
2. Automation lanes on timeline
3. Keyframe editor
4. Perform tools as bottom panel (not separate mode)
5. Recording automation from perform interactions

### Phase 6: Pixel Physics Consolidation
**Estimated scope: 2 sessions**

1. PhysicsEngine class
2. Force calculator extraction (one per mode)
3. 3 mega-effects (Dynamics, Cosmos, Organic)
4. Legacy aliases for backward compatibility
5. Mode selector UI

### Phase 7: Parameter Sensitivity System
**Estimated scope: 1-2 sessions**

1. compute_param_sensitivity() backend
2. Sensitivity gradient on slider backgrounds
3. Frame diff tool
4. Auto-range detection
5. Calibration across reference images

---

## Dependency Graph

```
Phase 0 (Bug Fixes)
  └── Phase 1 (Parameter UX)
        └── Phase 7 (Sensitivity System)
  └── Phase 2 (Color Tools)
  └── Phase 3 (Taxonomy)
        └── Phase 4 (Operators)
              └── Phase 5 (Timeline Automation)
  └── Phase 6 (Physics Consolidation)
```

Phase 0 is the critical path — everything else is blocked until bugs are fixed.
Phases 2, 3, and 6 can run in parallel after Phase 0.
Phase 4 depends on Phase 3 (taxonomy must be in place).
Phase 5 depends on Phase 4 (automation lanes need operators).
Phase 7 can run independently after Phase 1.

---

## 7. Unified Timeline Architecture (UI Redesign)

> **Date:** 2026-02-15 (UAT Round 2)
> **Severity:** CRITICAL — Fundamental architecture change
> **User quotes:**
> - "This separate mixer view is a UX nightmare. It compounds so terribly; it's a completely different interface."
> - "If a performance is supposed to be time-based, why do I have no timeline?"
> - "This UX is awful. Have you actually read up on Ableton's Flow?"
> - "The MIDI effects are like the triggers, the samplers. The operators are like our LFOs, and the audio effects are like our video effects. It's the same thing."

### 7.1 Problem Statement

Entropic has 3 separate modes (Quick/Timeline/Perform) that each present a different UI. Perform mode removes the timeline entirely and shows a Mixer with pre-loaded effects. This violates Don Norman's conceptual model principle — the user must rebuild their mental model every time they switch modes.

### 7.2 Core Decision: Kill Separate Modes, Unify into Timeline

**Before (Broken):**
- Quick mode: Apply effects to single image (no timeline, no layers)
- Timeline mode: Arrange effects over time (no perform controls)
- Perform mode: Trigger effects live (no timeline, separate mixer)

**After (Unified):**
- ONE view: Timeline is always visible
- Perform = a device module on a track (like Ableton's Drum Rack)
- Mixer controls = per-track in timeline (not a separate panel)
- Transport = always in top bar

### 7.3 Mental Model: Ableton Mapping

| Ableton Concept | Entropic Equivalent | Lives WHERE |
|----------------|---------------------|-------------|
| Audio Track | Video Track (1-8 max) | Timeline row |
| Audio Effects (Reverb, Delay) | Video Effects (Pixelsort, VHS) | Per-track chain (bottom panel) |
| MIDI Effects (Arpeggiator) | Triggers / Samplers | Per-track device |
| Operators (LFO, Envelope) | LFO, Envelope, Sidechain | Per-track device |
| Instrument (Drum Rack) | Perform module | Per-track device |
| Mixer faders | Per-track opacity/solo/mute/blend | Track header (LEFT side) |
| Transport (Play/Rec) | Transport | Top bar, center (always visible) |
| Loop brace | Loop region | Timeline ruler selection |
| Computer MIDI Keyboard | Keyboard toggle | Top bar toggle button |
| MIDI Learn | Parameter mapping | Future (click knob → move controller) |

### 7.4 Layout Specification

```
┌─────────────────────────────────────────────────────────────┐
│ TOPBAR                                                       │
│ [Logo] [Load File] [Export]                                  │
│         ◄ ▶/▮▮ ● ◎ ⊡ ↻Loop │ 0:00:00 / 0:30:00           │
│                          [🎹 Keyboard] [Undo↶] [Redo↷]      │
├──────┬──────────────────────────────────────────────────────┤
│ MENU │ File │ Edit │ View                                    │
├──────┴──────────────────────────────────────────────────────┤
│ BROWSER │ PREVIEW CANVAS                                     │
│ (collap-│                                                    │
│  sible) │     ┌──────────────────────┐                      │
│         │     │  Video Preview       │                      │
│ Effects │     │                      │                      │
│ Presets │     └──────────────────────┘                      │
│         │                                                    │
│─────────┼─── drag divider ──────────────────────────────────│
│         │ TIMELINE                                           │
│         │ ┌─ Track 1 ─────────────────────────────────────┐ │
│         │ │[▼ 100% S M │Normal▾] ▓▓▓░░░▓▓▓░░░░░░░░░░░░░│ │
│         │ ├─ Track 2 ─────────────────────────────────────┤ │
│         │ │[▼  80% S M │Multiply▾] ░░▓▓▓▓▓░░░░▓▓░░░░░░░│ │
│         │ ├─ + Add Track ─────────────────────────────────┤ │
│         │ └───────────────────────────────────────────────┘ │
│─────────┼─── drag divider ──────────────────────────────────│
│         │ EFFECT CHAIN (selected track)                      │
│         │ [Pixelsort] → [Scanlines] → [LFO] → [VHS] [+]   │
└─────────┴───────────────────────────────────────────────────┘
  [☽ theme switch]                                bottom-right
```

### 7.5 Panel Behavior

| Panel | Default | Resizable | Collapsible | Method |
|-------|---------|-----------|-------------|--------|
| Browser (left) | 220px width | Yes (drag divider) | Yes (button) | Collapse to 0px |
| Preview | 1fr (fills remaining) | Yes (drag dividers) | No | Always visible |
| Timeline | 140px height | Yes (drag divider) | Yes (▼ toggle) | Collapse to header only |
| Effect Chain | 200px height | Yes (drag divider) | Yes (▼ toggle) | Collapse to header only |
| Menu bar | 24px | No | No | Always visible |
| Top bar | 44px | No | No | Always visible |

**Drag dividers:** Thin (4px) bars between panels. Grab and drag to resize. Sizes saved to localStorage. Standard pattern from VSCode/Ableton/Photoshop.

### 7.6 Track Strip Specification

Each track in the timeline has a LEFT header with controls:

```
┌──────────────────────────────────────────────────────────┐
│ ▼ Track 1          [100%] [S] [M] [Normal ▾]            │
│   └ [Pixelsort, VHS, LFO]  ▓▓▓░░▓▓▓░░░░░░░░░░░░░░░░░  │
├──────────────────────────────────────────────────────────┤
│ ▼ Track 2          [ 80%] [S] [M] [Multiply ▾]          │
│   └ [Scanlines, Curves]    ░░░▓▓▓▓▓▓░░░▓▓░░░░░░░░░░░░  │
├──────────────────────────────────────────────────────────┤
│ + Add Track                                              │
└──────────────────────────────────────────────────────────┘
```

**Controls per track (left header):**
- ▼ Collapse/expand toggle
- Track name (editable, double-click)
- Opacity slider (0-100%, compact inline)
- [S] Solo button (yellow when active)
- [M] Mute button (red when active)
- Blend mode dropdown (Normal, Multiply, Screen, Add, Overlay, Darken, Lighten, etc.)
- Mini chain indicator (effect names or icons, showing what's on this track)

**Right-click context menu on track:**
- Add Track Above / Below
- Duplicate Track
- Delete Track
- Freeze Track (render to cached frames — like Ableton Freeze)
- Flatten Track (commit frozen frames — like Ableton Flatten)
- Move Up / Move Down

**Right-click on timeline background:**
- Add Track
- Paste

**Max tracks:** 8

### 7.7 Transport Bar Specification

**Location:** Top bar, center. Always visible.

```
[◄ Prev] [▶ Play / ▮▮ Pause] [● Rec] [◎ Overdub] [⊡ Capture] [↻ Loop]
                    0:00:00 / 0:30:00    F:0/900
```

**Icons (Ableton-style):**
| Control | Icon | Active State | Shortcut |
|---------|------|-------------|----------|
| Play/Pause | ▶ / ▮▮ (toggles) | Green when playing | Space |
| Record | ● (solid red circle) | Red pulse when recording | R (when NOT in MIDI mode) |
| Overdub | ◎ (hollow red circle) | Red outline pulse | Shift+R |
| Capture | ⊡ (reticle square) | Blinks briefly on capture | Cmd+Shift+C |
| Loop | ↻ | Orange when loop active | L |
| Prev frame | ◄ | — | ← arrow |

**Loop:** When Loop is active, an orange bracket appears on the timeline ruler. User drags edges to set loop region. Playback loops within this region.

### 7.8 Perform Module (Per-Track Device)

A "Perform" device is a device type that goes ON a track's effect chain, just like any effect or operator. Think of it like Ableton's Drum Rack.

**What it contains:**
- Trigger slots (up to 8 per perform device)
- Each slot can be mapped to: toggle a track, trigger an effect, change a parameter
- ADSR envelope per slot (how the trigger fades in/out)
- Trigger modes: toggle, one-shot, hold, retrigger

**How it appears in chain:**
```
[Pixelsort] → [Perform 🎹] → [VHS]
```

Clicking the Perform device expands its UI in the chain panel, showing the trigger grid.

### 7.9 Keyboard / MIDI Input

**Keyboard toggle:** Button in top bar (🎹 icon). When ON:
- Letter/number keys send MIDI notes (A=A3, S=A#3, etc. — Ableton layout)
- Transport shortcuts STILL work (Space, Cmd+Z, Cmd+E, etc.)
- Hotkeys that conflict with MIDI notes are DISABLED (A for automation, S for solo, etc.)
- Visual indicator: 🎹 button glows orange when active

**MIDI routing (Preferences dialog):**
- List all detected MIDI input devices
- Enable/disable per device
- MIDI channel filtering (1-16, or All)
- Future: MIDI Learn for parameter mapping (click knob → move controller)

### 7.10 Toolbar Reorganization

**Top bar layout (left to right):**
```
[Logo] [Load File] [Export] | [◄] [▶/▮▮] [●] [◎] [⊡] [↻] 0:00/0:30 | [🎹] [↶ Undo] [↷ Redo] [Randomize 🎲] [Refresh ↻] [History ▾]
```

**Menu bar (below top bar):**
| Menu | Items |
|------|-------|
| File | Import File..., Export..., Save Preset, Load Preset |
| Edit | Undo, Redo, Randomize Chain, Clear Chain, Preferences... |
| View | Toggle Browser, Toggle Histogram, Keyboard Shortcuts, Help |

**Removed from top bar:**
- Mode toggle (Quick/Timeline/Perform) — KILLED
- "Refresh Preview" text → replaced with ↻ icon
- "Export" text button → moved next to "Load File"

**Undo/Redo:** Small icon buttons (↶ ↷), no text labels.

### 7.11 History

**NOT a sidebar column.** History is a dropdown button in the top bar.

Click "History ▾" → dropdown panel appears (240px wide, max 400px tall, scrollable). Shows undo history entries. Click an entry to jump to that state.

### 7.12 Browser (Effects/Presets)

**Collapsible** via button in browser header. When collapsed, browser width = 0 and preview fills the space. Toggle with Tab key or button.

### 7.13 Histogram

Hidden by default. Available via View > Toggle Histogram. When visible, appears as a small overlay on the preview area (not in the chain). Shows RGB + Luma distribution for the current frame.

### 7.14 Render vs Export

| Term | What it does | How to access |
|------|-------------|---------------|
| Freeze | Cache rendered frames for a track (speeds up playback) | Right-click track → Freeze |
| Flatten | Commit frozen frames permanently (reduces to one baked clip) | Right-click track → Flatten |
| Export | Output final video file (MP4, MOV, GIF, PNG seq, WebM) | File → Export or Cmd+E |

**No separate "Render" button in the toolbar.** Freeze/Flatten are per-track operations via context menu.

### 7.15 Preview Canvas

- Preview should match source resolution when possible (no forced downsampling)
- User can zoom preview with scroll wheel or View menu (Fit, 50%, 100%, 200%)
- Preview quality toggle in View menu: Draft (fast, lower res) / Full (slower, source res)

### 7.16 What Gets Removed

| Component | Status | Reason |
|-----------|--------|--------|
| Quick mode | KILLED | Timeline with 1 track = Quick mode |
| Perform mode | KILLED | Perform module is a per-track device |
| Separate Mixer panel | KILLED | Per-track opacity/solo/mute/blend in track header |
| Perform transport bar | KILLED | Transport always in top bar |
| Right sidebar (Devices/History) | KILLED | History = dropdown, Devices = track strips |
| Info panel | DEFERRED | Feature-flagged off (too cluttered, needs more work) |
| Mode toggle buttons | KILLED | No modes |

### 7.17 Implementation Phases

```
Phase A: Layout Shell (HTML/CSS)
  - New grid: topbar + menubar + (browser | preview) + timeline + chain
  - Drag dividers between panels
  - Transport bar in top bar center
  - Browser collapse button
  - Remove mode toggle, right panel, info panel, perform panel

Phase B: Track System
  - Track strips in timeline (1-8)
  - Per-track header: opacity, solo, mute, blend
  - Right-click context menu (Add/Delete/Freeze/Flatten)
  - "+" button at bottom of track list
  - Selected track → populates chain panel

Phase C: Transport Integration
  - Play/Pause toggle, Rec, Overdub, Capture icons
  - Loop brace on timeline ruler
  - Frame counter + time display
  - Keyboard MIDI toggle

Phase D: Perform Module
  - New device type: "Perform" (goes in chain like any device)
  - Trigger grid UI in chain panel
  - MIDI note routing to trigger slots
  - ADSR per trigger slot

Phase E: MIDI Routing
  - Preferences dialog for MIDI devices
  - MIDI Learn for parameter mapping
  - Computer keyboard → MIDI note mapping
```

---

*CTO Analysis by Claude | 2026-02-15 | Grounded in Entropic source code review + UAT Round 2 user feedback*

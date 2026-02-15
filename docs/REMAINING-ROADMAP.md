# Entropic — Remaining Roadmap

> **Created:** 2026-02-15
> **Source:** UAT Cycle 1 findings, architecture proposals, user feedback, master effects list
> **Reference:** UAT-FINDINGS-2026-02-15.md, ARCHITECTURE-DEEP-DIVE.md, PRODUCT-ANALYSIS.md
> **Current version:** v0.7.0-dev (115 effects, 859 tests)

---

## Status Legend

- `[ ]` Not started
- `[~]` Partially built
- `[x]` Done
- `[R]` Needs retest

---

## P0 — Table Stakes (Usability Blockers)

| # | Item | Source | Effort | Status | Files |
|---|------|--------|--------|--------|-------|
| P0-1 | **Fluid video playback** — press play, watch video move smoothly. Currently debounced at 150ms + server round-trip = ~5 FPS. Need client-side frame cache or pipeline optimization. | User request + UAT S9 | Medium | [x] | app.js, timeline.js |
| P0-2 | **Click-to-type on knob values** — click the value text below a knob, type a specific number. Standard DAW/Photoshop behavior. Currently: drag to change, dblclick to reset. | User request | Small | [x] | app.js, style.css |
| P0-3 | **Text contrast WCAG pass** — `--text-dim` #555→#7a7a7a, `--text-secondary` #888→#999. | User request | Small | [x] | style.css |
| P0-4 | **Retest B10-B13** — byte corrupt, flow distort, auto levels, histogram eq. All 4 PASS after frame_index fix. | UAT findings | Small | [x] | tests/test_retest_b10_b13.py |
| P0-5 | **Seed audit** — removed seed param from 22 effects that used it only for state-key isolation (no visual impact). 48 effects retain seed with proper randomization. Test coverage updated for conditional-seed (scanlines/flicker, granulator/spray, beatrepeat/chance, strobe/random) and temporal-seed (samplehold, granulator, beatrepeat, strobe) effects. | UAT S5, P1 | Medium | [x] | effects/__init__.py, tests/test_retest_b10_b13.py |
| P0-6 | **Loop region selection** — Ableton-style loop brace on timeline. Set loop start/end, playback loops within that range. Drag to reposition, resize by dragging edges. Loop on/off toggle. Currently only perform mode has whole-video loop toggle. | User request | Medium | [x] | timeline.js |
| P0-7 | **Timeline scrub verification** — Click ruler sets playhead, drag scrubs. Both trigger `setPlayhead()` → `onTimelinePlayheadChange()` → `schedulePreview(true)`. Verified in code: lines 1688-1694 (click), 1841-1843 (drag). | User request | Small | [x] | timeline.js |

---

## P1 — Usability Polish

| # | Item | Source | Effort | Status | Files |
|---|------|--------|--------|--------|-------|
| P1-1 | **Knob sensitivity zone indicator** — arc gradient showing dead zone (gray), active zone (colored), blown-out zone (red). Visualization of useful range around the circle. | User request + UAT S2 | Medium | [x] | app.js, style.css (arc-track/arc-zone/arc-danger) |
| P1-2 | **Parameter range recalibration** — hybrid approach: pattern-matched 197 params by name across 76 effects. Coverage: 26→103 complete (85%), 0 missing. | UAT systemic | Large | [x] | effects/__init__.py |
| P1-3 | **Tooltips on everything** — effect descriptions, parameter explanations, mode descriptions in UI. | Don Norman audit (6/10 recognition) | Medium | [x] | app.js (data-tooltip + hover preview system) |
| P1-4 | **Frame diff tool** — change a param, see pixel diff heatmap. If seed changes and nothing on screen changes = bug. | UAT S4 | Medium | [x] | app.js (diffCapture/diffShow/diffClear + toolbar) |
| P1-5 | **Mix slider labeling** — clear "Dry/Wet" label + tooltip explaining what mix does. | UAT U3 | Small | [x] | app.js (renamed Mix→Dry/Wet in 3 locations) |
| P1-6 | **Sidechain crossfeed mapping** — B14 design flaw. Effect not mapped to any output. | UAT B14 | Medium | [x] | effects/__init__.py (registered crossfeed + interference) |
| P1-7 | **Pixel elastic range fix** — works at low mass, nothing at high mass. Recalibrate. | UAT P4 | Small | [x] | effects/physics.py (mass damping scaled, force normalized) |
| P1-8 | **Pixel magnetic params** — poles, damping, rotation, seed all non-functional. Only center pull works. | UAT P2 | Medium | [x] | effects/physics.py (overflow guard, params wired) |
| P1-9 | **Pixel quantum params** — uncertainty, superposition, decoherence sliders dead. | UAT P3 | Medium | [x] | effects/physics.py (visibility boost, params functional) |

---

## P2 — Architecture (Unbuilt Major Systems)

| # | Item | Source | Effort | Status | Files |
|---|------|--------|--------|--------|-------|
| P2-1 | **Pixel physics consolidation** — 4 mega-effects expanded with full params from all modes, param_ranges, param_options, and param_visibility dicts for conditional UI display. pixeldynamics (6 modes, 25 params), pixelcosmos (8 modes), pixelorganic (3 modes), pixeldecay (4 modes). | UAT A6 | Large | [x] | effects/__init__.py |
| P2-2 | **Modular sidechain operator** — one sidechain operator that maps to any parameter. Current 6 sidechain effects → presets. | UAT A4 | Large | [ ] | effects/sidechain.py, app.js |
| P2-3 | **Taxonomy reclassification** — Operators category added, LFO moved, CATEGORY_ORDER reordered, 9 effects moved to tools (levels, curves, hsladjust, colorbalance, histogrameq, clahe, autolevels, chroma_key, luma_key), hueflanger moved to modulation. | UAT A3 | Medium | [x] | effects/__init__.py |
| P2-4 | **Transparent layer rendering** — RGBA pipeline: checkerboard composite preview, PNG encoding for alpha frames, output_alpha flag on emboss/chroma_key/luma_key, alpha preservation through chains. 10 tests. | UAT S7 | Medium | [x] | server.py, effects/__init__.py, tests/test_rgba_pipeline.py |
| P2-5 | **Gravity concentrations** — place attraction points on frame that intensify parameters in that region. Spatial parameter modulation. | UAT S6 | Large | [ ] | new module |
| P2-6 | **Ring mod reconceptualization** — 4 carrier waveforms (sine/square/triangle/saw), spectrum band selection (all/low/mid/high), animation_rate control, temporal direction, depth-bypass fix for phase mode. 23 tests. | UAT rework | Medium | [x] | effects/modulation.py |
| P2-7 | **Flanger vs Phaser vs LFO differentiation** — MODULATION-GUIDE.md written (5 types, 16 effects classified, ASCII signal flow diagrams, quick reference table). All modulation descriptions updated with type prefix and param_descriptions. | UAT ARCH-Q | Design | [x] | docs/MODULATION-GUIDE.md |

---

## P3 — Effect Enhancements (28 UAT Requests)

| # | Effect | Enhancement | Status |
|---|--------|-------------|--------|
| F1 | **Smear** | More directions, animated motion, shifting vectors | [~] Already has 4 directions + animate |
| F2 | **Wave** | More directions, amplitude/frequency modulation, bouncing wave | [x] Added diagonal + circular directions |
| F3 | **ASCII art** | All character modes, expand color modes. "INSANE!" | [x] Added palette + tint color modes, custom_chars param |
| F4 | **Blur** | More types: Gaussian, radial, motion, lens | [x] All 6 types built (box/gaussian/motion/radial/median/lens) |
| F5 | **Contours** | Outline-only mode without affecting interior color | [x] outline_only already built |
| F6 | **Edges** | Color palette control, fix threshold sensitivity | [x] edge_color + mode already built |
| F7 | **Noise** | Animated seed = motion noise. Before pixelsort = animated texture. | [x] animate toggle already built |
| F8 | **TV static** | Spatial concentration, physics/gravity, animated displacement | [x] concentrate_x/y/radius + animate_displacement already built |
| F9 | **Contrast** | (DONE — Photoshop-level via color suite) | [x] |
| F10 | **Pixel elastic** | Added 4 force types: gravity, magnetic, wind, explosion (now 12 total) | [x] |
| F11 | **Pixel wormhole** | Position moves around screen. Currently static. | [x] Added center_x/center_y position control |
| F12 | **Block corrupt** | More non-random modes in dropdown | [x] Already has 6 modes + 4 placement modes |
| F13 | **Channel destroy** | More modes | [x] Already has 6 modes (separate/swap/crush/eliminate/invert/xor) |
| F14 | **Data bend** | More modes, more variability | [x] Added tremolo + ringmod (now 7 DSP modes) |
| F15 | **Film grain** | Automated seed = grain with motion | [x] animate=True default already built |
| F16 | **Framesmash** | Color control / color affect options | [x] color_affect toggle already built |
| F17 | **Glitch repeat** | Motion, flicker, switchable states | [x] shift + flicker already built, seed varies per frame |
| F18 | **Invert bands** | Direction, rotation, vectors, non-linear shapes, CRT motion | [x] Added direction (horizontal/vertical) |
| F19 | **Pixel annihilate** | Differentiate with more params OR cut | [x] CUT |
| F20 | **Pixel risograph** | Changeable colors | [x] Added palette presets (classic/zine/punk/ocean/sunset/custom) |
| F21 | **Xerox** | Added registration_offset, toner_density, paper_feed — better physical model | [x] |
| F22 | **Row shift** | Rotation, gravity concentrations | [x] Added direction (horizontal/vertical/both) |
| F23 | **XOR glitch** | More modes, more params | [x] Already has 6 modes |
| F24 | **Emboss** | Transparent gray for layering | [x] transparent_bg already built |
| F25 | **Parallel compress** | Compress on dimensions beyond black-white | [x] Added mode (luminance/per_channel/saturation) |
| F26 | **Solarize** | Own brightness/black-gray-white control | [x] Added target (all/shadows/midtones/highlights) + brightness |
| F27 | **Wavefold** | Brightness control, histogram for luminosity | [x] Added brightness param |
| F28 | **Tapesaturation** | Reconceptualize. Currently "just makes it more white." | [x] Reworked: HF rolloff, soft-clip harmonics, compression, flutter |

---

## P4 — Cut/Rework Candidates

| Effect | User Feedback | Decision | Status |
|--------|--------------|----------|--------|
| **AM radio** | "Kind of useless" | Cut | [x] REMOVED |
| **Pixel annihilate** | "Redundant with noisy plugins" | Cut | [x] REMOVED |
| **Xerox** | "Maybe chopping block" | Kept — improved with registration, toner, paper params | [x] |
| **Cyanotype** | "Just makes it blue" | Move to color filter preset | [x] → colorfilter preset |
| **Infrared** | Cool but should be a filter preset | Move to color filter preset | [x] → colorfilter preset |

---

## P5 — Master Effects List (278 New Effects — Future)

> Full list at: `~/Development/entropic/docs/MASTER-EFFECTS-LIST.md`

| Category | Count | Priority | Notes |
|----------|-------|----------|-------|
| **Audio-reactive** | 40 | HIGH — differentiator | Beat-sync, onset, spectral, RMS, HPSS, etc. Zero built. |
| **Cross-modal / Mad Scientist** | 30 | HIGH — brand identity | Reverb on video, granular synthesis, wavefold pixels, etc. |
| **Computer vision** | 14 | MEDIUM | Face glitch, pose glitch, YOLO segmentation, feature constellations |
| **Generative / Procedural** | 18 | MEDIUM | Cellular automata, flow fields, L-systems, Voronoi, plasma |
| **Pixel corruption** | 28 | LOW — many overlap existing | Iterative re-encode, hex pattern, amplified corruption |
| **Color & grading** | 22 | LOW — color suite covers basics | Film LUT, decorrelation stretch, chroma smear |
| **Distortion & warp** | 24 | LOW | Vortex, fisheye, Perlin displacement, mesh warp |
| **Temporal & motion** | 22 | MEDIUM | Motion trails, optical flow, frame interpolation |
| **Blend modes** | 10 | LOW — 7 built in perform mode | Oscilloscope overlay, vectorscope |
| **Creative / Art-inspired** | 30 | MEDIUM — unique effects | Cubist, pointillist, Rothko bands, stained glass |
| **Competitive gaps** | 22 | MEDIUM — fill market gaps | Hyperspektiv prism, Resolume wire removal, TouchDesigner chains |
| **Performance & workflow** | 18 | LOW — infrastructure | Streaming pipeline, GLSL shaders, Syphon/NDI output |

---

## UX Debt (Don Norman Audit — Current Score 3.8/10)

| Heuristic | Score | Gap | Fix |
|-----------|-------|-----|-----|
| 1. Visibility of system status | 2/10 | No upload progress, no render status | Progress bars, loading spinners |
| 2. Match system ↔ real world | 6/10 | Audio metaphors work for target users | — |
| 3. User control and freedom | 4/10 | Undo exists (Cmd+Z). Missing: global undo across modes | Full undo stack |
| 4. Consistency and standards | 5/10 | Taxonomy still mixed | P2-3 reclassification |
| 5. Error prevention | 3/10 | No param validation, no range indicators | P1-1, P1-2 |
| 6. Recognition over recall | 4/10 | No tooltips, mode labels unclear | P1-3 |
| 7. Flexibility and efficiency | 5/10 | Chaining works, shortcuts exist | More shortcuts |
| 8. Aesthetic and minimalist | 6/10 | Clean but sparse | Information density |
| 9. Error recognition/recovery | 1/10 | Silent failures | Error toasts (BUILT), expand |
| 10. Help and documentation | 2/10 | No in-app help | Onboarding, help panel |

---

## Positive Reactions (Double Down)

| Effect | Reaction | Strategy |
|--------|----------|----------|
| **ASCII art** | "INSANE! Really crazy." | F3: Expand character sets + color modes |
| **Pixel fax** | "Insane. So cool." | Signature effect — promote in marketing |
| **Blur → Pixelsort** | "So cool, interference patterns" | Create preset recipe, feature in onboarding |
| **Contours** | "Very cool. Topography." | F5: Outline-only mode |
| **Edges** | "Old video game, Obra Dinn" | Create preset at low threshold |
| **XOR glitch** | "Very cool. Makes me want to explore more." | F23: More modes |
| **JPEG damage** | "Awesome." | Feature in presets |
| **Invert bands** | "Very cool." | F18: Direction/rotation |
| **Block corrupt** | "Dope." | F12: More modes |
| **Gate** | "Very cool. Want to maintain." | Keep + make operator |

---

*Total remaining items: 0 P0 + 0 P1 + 2 P2 + 0 P3 + 0 P4 + 278 P5 + 10 UX = 290 items*
*P1 done: 9/9. P3 done: 28/28. P4 done: 5/5. P2 Sprint 1 done: P2-3, P2-6, P2-7. P2 Sprint 2 done: P2-1 (mega-effect param_visibility), P2-4 (RGBA pipeline). Remaining P2: P2-2 (modular sidechain), P2-5 (gravity concentrations).*

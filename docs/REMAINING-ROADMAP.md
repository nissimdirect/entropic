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
| P1-1 | **Knob sensitivity zone indicator** — arc gradient showing dead zone (gray), active zone (colored), blown-out zone (red). Visualization of useful range around the circle. | User request + UAT S2 | Medium | [ ] | app.js, style.css |
| P1-2 | **Parameter range recalibration** — per-effect sweet spot mapping. Full slider width = useful range, not mathematical domain. | UAT systemic | Large | [ ] | effects/*.py, control-map.json |
| P1-3 | **Tooltips on everything** — effect descriptions, parameter explanations, mode descriptions in UI. | Don Norman audit (6/10 recognition) | Medium | [ ] | app.js |
| P1-4 | **Frame diff tool** — change a param, see pixel diff heatmap. If seed changes and nothing on screen changes = bug. | UAT S4 | Medium | [ ] | app.js, server.py |
| P1-5 | **Mix slider labeling** — clear "Dry/Wet" label + tooltip explaining what mix does. | UAT U3 | Small | [ ] | app.js |
| P1-6 | **Sidechain crossfeed mapping** — B14 design flaw. Effect not mapped to any output. | UAT B14 | Medium | [ ] | effects/sidechain.py |
| P1-7 | **Pixel elastic range fix** — works at low mass, nothing at high mass. Recalibrate. | UAT P4 | Small | [ ] | effects/physics.py |
| P1-8 | **Pixel magnetic params** — poles, damping, rotation, seed all non-functional. Only center pull works. | UAT P2 | Medium | [ ] | effects/physics.py |
| P1-9 | **Pixel quantum params** — uncertainty, superposition, decoherence sliders dead. | UAT P3 | Medium | [ ] | effects/physics.py |

---

## P2 — Architecture (Unbuilt Major Systems)

| # | Item | Source | Effort | Status | Files |
|---|------|--------|--------|--------|-------|
| P2-1 | **Pixel physics consolidation** — 21 effects → 3 mega-effects with mode selectors. Pixel Dynamics (6 modes), Pixel Cosmos (8 modes), Pixel Organic (3 modes). Shared PhysicsEngine class. | UAT A6 | Large | [ ] | effects/physics.py, app.js |
| P2-2 | **Modular sidechain operator** — one sidechain operator that maps to any parameter. Current 6 sidechain effects → presets. | UAT A4 | Large | [ ] | effects/sidechain.py, app.js |
| P2-3 | **Taxonomy reclassification** — move color effects (hueshift, contrast, saturation, exposure, temperature) → Tools. Move modulation (flanger, phaser, gate, ring mod) → Operators. Keep glitch/destruction/physics/ASCII as Effects. Add Image Editing category. | UAT A3 | Medium | [ ] | effects/__init__.py, app.js, style.css |
| P2-4 | **Transparent layer rendering** — render effects to transparent layers. Emboss gray = transparent. Pixel distortion over transparent regions. | UAT S7 | Medium | [ ] | core/layer.py, server.py |
| P2-5 | **Gravity concentrations** — place attraction points on frame that intensify parameters in that region. Spatial parameter modulation. | UAT S6 | Large | [ ] | new module |
| P2-6 | **Ring mod reconceptualization** — currently "just black stripes." Needs external modulation source, spectrum value selection. | UAT rework | Medium | [ ] | effects/modulation.py |
| P2-7 | **Flanger vs Phaser vs LFO differentiation** — define clear differences. Phaser/flanger = resonant peak sweep across spectrum. LFO = periodic modulation of any param. | UAT ARCH-Q | Design | [ ] | docs/ |

---

## P3 — Effect Enhancements (28 UAT Requests)

| # | Effect | Enhancement | Status |
|---|--------|-------------|--------|
| F1 | **Smear** | More directions, animated motion, shifting vectors | [ ] |
| F2 | **Wave** | More directions, amplitude/frequency modulation, bouncing wave | [ ] |
| F3 | **ASCII art** | All character modes, expand color modes. "INSANE!" | [ ] |
| F4 | **Blur** | More types: Gaussian, radial, motion, lens | [ ] |
| F5 | **Contours** | Outline-only mode without affecting interior color | [ ] |
| F6 | **Edges** | Color palette control, fix threshold sensitivity | [ ] |
| F7 | **Noise** | Animated seed = motion noise. Before pixelsort = animated texture. | [ ] |
| F8 | **TV static** | Spatial concentration, physics/gravity, animated displacement | [ ] |
| F9 | **Contrast** | (DONE — Photoshop-level via color suite) | [x] |
| F10 | **Pixel elastic** | More force types, concentrations, vectors. Less atmospheric. | [ ] |
| F11 | **Pixel wormhole** | Position moves around screen. Currently static. | [ ] |
| F12 | **Block corrupt** | More non-random modes in dropdown | [ ] |
| F13 | **Channel destroy** | More modes | [ ] |
| F14 | **Data bend** | More modes, more variability | [ ] |
| F15 | **Film grain** | Automated seed = grain with motion | [ ] |
| F16 | **Framesmash** | Color control / color affect options | [ ] |
| F17 | **Glitch repeat** | Motion, flicker, switchable states | [ ] |
| F18 | **Invert bands** | Direction, rotation, vectors, non-linear shapes, CRT motion | [ ] |
| F19 | **Pixel annihilate** | Differentiate with more params OR cut | [ ] |
| F20 | **Pixel risograph** | Changeable colors | [ ] |
| F21 | **Xerox** | Individuate, patchable effect order, better physical model OR cut | [ ] |
| F22 | **Row shift** | Rotation, gravity concentrations | [ ] |
| F23 | **XOR glitch** | More modes, more params | [ ] |
| F24 | **Emboss** | Transparent gray for layering | [ ] |
| F25 | **Parallel compress** | Compress on dimensions beyond black-white | [ ] |
| F26 | **Solarize** | Own brightness/black-gray-white control | [ ] |
| F27 | **Wavefold** | Brightness control, histogram for luminosity | [ ] |
| F28 | **Tapesaturation** | Reconceptualize. Currently "just makes it more white." | [ ] |

---

## P4 — Cut/Rework Candidates

| Effect | User Feedback | Decision |
|--------|--------------|----------|
| **AM radio** | "Kind of useless" | Cut or make preset of ring mod |
| **Pixel annihilate** | "Redundant with noisy plugins" | Differentiate or cut |
| **Xerox** | "Maybe chopping block" | Better physical model or cut |
| **Cyanotype** | "Just makes it blue" | Move to color filter preset |
| **Infrared** | Cool but should be a filter preset | Move to color filter preset |

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

*Total remaining items: 0 P0 + 9 P1 + 7 P2 + 27 P3 + 5 P4 + 278 P5 + 10 UX = 336 items*
*Sprint velocity: ~4-8 items per session depending on size*
*Estimated: 8-12 sessions for P0-P2, ongoing for P3+*

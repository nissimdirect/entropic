# Entropic v0.7.0 — Changelog

> **Release:** 2026-02-15
> **Codename:** "Ableton for Video"
> **Previous:** v0.6.0 (Performance Mode)

---

## Summary

v0.7 transforms Entropic from a feature-rich but rough tool into a professional, discoverable video effects instrument. This release focuses on UX polish, professional color tools, and organizational clarity — making the 111+ effects actually usable.

---

## New Features

### Photoshop-Level Color Suite
Professional color correction tools with live histogram feedback.

- **Levels** — Input/output range remapping with gamma control per channel (Master/R/G/B)
- **Curves** — Interactive bezier curve adjustment with click-to-add control points
- **HSL Adjust** — Per-hue-range Hue/Saturation/Lightness control (target: all/reds/oranges/yellows/greens/cyans/blues/magentas)
- **Color Balance** — Separate color tint for shadows/midtones/highlights with luminosity preservation
- **Live Histogram** — Real-time R/G/B/Luma distribution overlay, updates with every effect change

**Problem solved:** Color tools were too basic — no histogram meant Entropic felt like a toy next to any free image editor. (JTBD #4: Correct Color Professionally)

### Collapsible Effect Taxonomy
Effects organized into expandable folder categories.

- **Categories:** Glitch, Distortion, Texture, Color, Temporal, Modulation, Enhance, Destruction, DSP Filters, Sidechain, Physics, ASCII
- Click folder header to expand/collapse
- Effect count badge per category (e.g., "PHYSICS (21)")
- All folders start collapsed for clean overview

**Problem solved:** 111 effects in a flat list was overwhelming — users couldn't build a mental model of what the tool offers. (JTBD #2: Apply & Tweak Effects / Don Norman: Consistency & Standards)

### Error Feedback System
Comprehensive toast notifications, loading states, and progress indicators.

- **Toast notifications** for all errors, warnings, and successes (auto-dismiss, stackable, click-to-close)
- **Loading overlay** on preview canvas during effect processing
- **Upload progress** with percentage indicator
- **Render progress** with frame count (X of Y)
- Zero silent failures — every `console.error` now has a user-facing toast

**Problem solved:** Silent failures everywhere — users couldn't tell if the tool was broken or just loading. (JTBD #8: Understand What Went Wrong / Don Norman: Visibility of System Status scored 2/10, now targeting 7+/10)

### Perform Panel in Timeline
Performance controls integrated as a toggleable sub-panel within Timeline view.

- Press **P** to toggle Perform panel below the timeline
- Layer mixer with 4 layer strips (opacity, trigger indicator, choke group)
- Transport controls (record/play/stop)
- Keyboard triggers (1-4) work within Timeline view
- Perform tab removed from mode navigation

**Problem solved:** Perform mode was hidden in a separate tab that users couldn't discover. "CLI freaks me out...I need to see what I'm doing." (JTBD #6: Perform Live with Layers)

### Dry/Wet Mix Per Effect
Individual blend control for each effect in the chain.

- Mini mix slider (0-100%) on each effect in the chain
- Default: 100% (fully wet) for backward compatibility
- Blend: `result = original * (1 - mix) + processed * mix`
- Global mix slider still available for master dry/wet

**Problem solved:** No way to partially apply an effect — it was all or nothing.

### Performance Features (3 new)
Three features that close the biggest usability gulfs in Perform mode.

- **Keyboard Input Mode** — Press **M** to enter keyboard perform mode. Q/W/E/R trigger layers 1-4, A/S/D/F trigger layers 5-8. Keys respect gate/adsr trigger modes (hold=on, release=off). Press **K** to show key hint overlay. **Escape** panics all layers and exits mode. Purple "PERFORM" HUD indicator and canvas outline.
- **Retroactive Buffer** — Always-on circular buffer captures the last 60 seconds of all trigger events, even without pressing Record. Press **Capture** button (or **Cmd+Shift+C**) to claim the buffer. Claimed events merge into a performance session for Review, Bake to Timeline, Save, or Discard. Buffer indicator shows duration in HUD. 50,000 event cap with automatic eviction.
- **Automation Recording** — Press **AUTO** button (or **Shift+R**) to arm automation recording. During playback, any knob movement is captured as timeline automation lanes. Keyframe thinning at ~10fps prevents overdense data (skips if frame delta < 3 or value change < 1%). Lanes auto-commit when playback stops. Knobs being recorded glow red. HUD shows `[AUTO]` when armed.

**Problem solved:** "I forgot to hit Record" (Retroactive Buffer), "How do I record knob movements?" (Automation Recording), "How do I trigger without mouse?" (Keyboard Input). Mental models: Ableton MIDI Capture, Ableton Automation Arm, Resolume keyboard overlay.

### UX Refactor (17 improvements)
Discovery, favorites, info panel, complexity meter, hover previews, parameter presets, whimsy effects.

- **Effect search** with fuzzy matching, tag search, live filtering
- **Favorites system** — Star effects, persisted to localStorage, "Favorites" pseudo-category at top
- **Info View panel** — Ableton-style bottom-left info bar, hover any control for context
- **Hover previews** — Effect thumbnails on hover in browser, cached per-effect
- **Complexity meter** — Visual indicator of chain complexity (green/yellow/red)
- **Parameter presets** — Save/load per-effect parameter snapshots, reset to defaults
- **8 Whimsy effects** — Kaleidoscope, Soft Bloom, Shape Overlay, Lens Flare, Watercolor, Rainbow Shift, Sparkle, Film Grain Warm

---

## Breaking Changes

| Change | Impact | Migration |
|--------|--------|-----------|
| Quick mode removed | Quick mode tab no longer visible | Use Timeline (identical features) |
| Perform mode relocated | No longer a separate tab | Press P in Timeline to toggle perform panel |
| Effects panel restructured | Flat list → collapsible folders | Click category headers to expand |

---

## JTBD Coverage

| Job | v0.6 Score | v0.7 Target | Key Feature |
|-----|-----------|-------------|-------------|
| Import & Preview | BROKEN | WORKING | Error feedback, upload progress |
| Apply & Tweak Effects | PARTIAL | GOOD | Taxonomy, tooltips, per-effect mix |
| Chain Effects Creatively | GOOD | GOOD | No change (already strong) |
| Correct Color Professionally | INSUFFICIENT | PROFESSIONAL | Levels, Curves, HSL, Color Balance, Histogram |
| Automate & Modulate | BUILT (LFO Map) | BUILT | LFO Map operator (from other session) |
| Perform Live | HIDDEN | PROFESSIONAL | Keyboard perform, retroactive buffer, automation recording, perform toggle |
| Export | BROKEN | WORKING | Upload fix unblocks export |
| Understand Failures | TERRIBLE | ACCEPTABLE | Toast system, tooltips, error messages |

---

## Don Norman Heuristic Improvements

| Heuristic | v0.6 | v0.7 | How |
|-----------|------|------|-----|
| Visibility of system status | 2/10 | 7/10 | Toasts, loading states, progress bars |
| Consistency and standards | 5/10 | 7/10 | Collapsible taxonomy, unified mode |
| Error prevention | 3/10 | 6/10 | Parameter validation, bounds checking |
| Recognition over recall | 4/10 | 8/10 | Tooltips, folder descriptions, labels, keyboard hint overlay, info-view hover |
| Help recognize/recover errors | 1/10 | 6/10 | Error toasts with details, no silent failures |

---

## Files Changed

### New Files
- `docs/CHANGELOG-v0.7.md` — This file

### Modified Files
- `effects/color.py` — Added: levels, curves, hsl_adjust, color_balance, compute_histogram
- `effects/__init__.py` — Registered new color effects, added CATEGORY_ORDER
- `server.py` — Added POST /api/histogram endpoint
- `ui/static/app.js` — Collapsible taxonomy, toast system, error wiring, per-effect mix, perform toggle, color suite UI, keyboard perform mode, retroactive buffer, automation recording, info-view tooltips
- `ui/static/style.css` — Toast styles, folder styles, histogram canvas, color suite panels, perform sub-panel, keyboard perform styles, auto-recording knob glow, key hint overlay, buffer indicator
- `ui/index.html` — Toast container div, perform panel restructure, AUTO/Capture transport buttons, HUD buffer/keyboard indicators, key hint overlay, shortcut reference additions, info-view tooltips on transport
- `tests/test_color_suite.py` — New test file for color effects
- `tests/test_taxonomy.py` — New test file for category validation
- `tests/test_mix.py` — Updated with per-effect mix tests

---

*Changelog by Claude Code | entropic-v07 team sprint | 2026-02-15*

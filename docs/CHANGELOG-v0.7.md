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
| Perform Live | HIDDEN | ACCESSIBLE | Perform toggle in Timeline |
| Export | BROKEN | WORKING | Upload fix unblocks export |
| Understand Failures | TERRIBLE | ACCEPTABLE | Toast system, tooltips, error messages |

---

## Don Norman Heuristic Improvements

| Heuristic | v0.6 | v0.7 | How |
|-----------|------|------|-----|
| Visibility of system status | 2/10 | 7/10 | Toasts, loading states, progress bars |
| Consistency and standards | 5/10 | 7/10 | Collapsible taxonomy, unified mode |
| Error prevention | 3/10 | 6/10 | Parameter validation, bounds checking |
| Recognition over recall | 4/10 | 7/10 | Tooltips, folder descriptions, labels |
| Help recognize/recover errors | 1/10 | 6/10 | Error toasts with details, no silent failures |

---

## Files Changed

### New Files
- `docs/CHANGELOG-v0.7.md` — This file

### Modified Files
- `effects/color.py` — Added: levels, curves, hsl_adjust, color_balance, compute_histogram
- `effects/__init__.py` — Registered new color effects, added CATEGORY_ORDER
- `server.py` — Added POST /api/histogram endpoint
- `ui/static/app.js` — Collapsible taxonomy, toast system, error wiring, per-effect mix, perform toggle, color suite UI
- `ui/static/style.css` — Toast styles, folder styles, histogram canvas, color suite panels, perform sub-panel
- `ui/index.html` — Toast container div, perform panel restructure
- `tests/test_color_suite.py` — New test file for color effects
- `tests/test_taxonomy.py` — New test file for category validation
- `tests/test_mix.py` — Updated with per-effect mix tests

---

*Changelog by Claude Code | entropic-v07 team sprint | 2026-02-15*

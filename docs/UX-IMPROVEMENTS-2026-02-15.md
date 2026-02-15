# UX Improvements — 2026-02-15

**Team:** entropic-sprint
**Agent:** ux-builder
**Task:** #4 Build scroll affordance + tooltips for param panels
**Status:** ✅ COMPLETED

---

## Problem Statement

From SPRINT-REPORT-2026-02-15.md (L53):
> Every scrollable container MUST have a visible scroll indicator (gradient, scrollbar, or "N more parameters" badge). This is the #1 most impactful UX fix.

**Don Norman violation:** The parameter panel scrolls vertically, but there was NO visible affordance. User tested 40+ effects with no idea they could scroll down. System's conceptual model (scrollable container) didn't match user's mental model (all parameters visible).

**Impact:** 25% of effects appeared broken because users couldn't access hidden parameters. This was compound frustration — users couldn't distinguish "parameter is hidden" from "parameter doesn't work."

---

## Solution Implemented

### 1. Enhanced Scroll Affordance (style.css)

**File:** `/Users/nissimagent/Development/entropic/ui/static/style.css`
**Lines:** 1023-1072

**Changes:**
1. **Always-visible scrollbar** (removed hover-only behavior)
   - Width: 4px (up from 3px)
   - Color: `var(--text-dim)` default, `var(--accent)` on hover
   - Now uses `overflow-y: auto` instead of `overflow-y: hidden`
   - Firefox support via `scrollbar-width: thin` + `scrollbar-color`

2. **Larger gradient fade** when params overflow
   - Height: 48px (up from 36px)
   - Opacity: Stronger gradient (40% start vs 60%)
   - Background: Full `var(--bg-mid)` at bottom (100% opaque)

3. **Bolder "N MORE" badge**
   - Font size: 11px (up from 10px)
   - Font weight: 700 (up from 600)
   - Letter spacing: 1px (up from 0.5px)
   - Added `text-shadow: 0 0 4px rgba(255, 61, 61, 0.5)` for glow effect

4. **Animated down-arrow indicator**
   - Replaced empty `::before` content with `'▼'` character
   - Increased pill size: 80x22px (up from 60x18px)
   - Border color: `var(--accent)` (was `var(--border)`)
   - Added `scroll-pulse` animation: 2s infinite, subtle vertical bounce
   - Arrow flexbox-centered inside pill

5. **Animation:**
```css
@keyframes scroll-pulse {
    0%, 100% { opacity: 0.8; transform: translateX(-50%) translateY(0); }
    50% { opacity: 1; transform: translateX(-50%) translateY(2px); }
}
```

### 2. Parameter Tooltips (app.js)

**File:** `/Users/nissimagent/Development/entropic/ui/static/app.js`
**Functions modified:** 3 (createKnob, createDropdown, createToggle)

**Tooltip formats:**

| Control Type | Tooltip Format | Example |
|--------------|----------------|---------|
| Knob | `{label}: {value} (range: {min}–{max})` | `Threshold: 0.6 (range: 0–1)` |
| Dropdown | `{label}: {value} ({N} options)` | `Mode: horizontal (5 options)` |
| Toggle | `{label}: {ON|OFF} (click to toggle)` | `Flicker: ON (click to toggle)` |

**Implementation:**
- Added `const tooltip = ...` before return statement in each function
- Added `title="${tooltip}"` to outer container div
- Used `–` (en-dash) for ranges (typographic correctness)

---

## Visual Design Alignment

All changes follow **POP CHAOS DESIGN SYSTEM** tokens:
- `--accent` (#ff3d3d) for scroll indicators and glow
- `--text-dim` (#555) for default scrollbar color
- `--bg-mid` (#1e1e22) for gradient background
- Monospace font (inherit from design system)
- 2s animation timing (consistent with other UI animations)

---

## Testing Notes

**How to test:**
1. Open Entropic web UI
2. Add any effect with >6 parameters (e.g., `pixelsort`, `chromatic_aberration`)
3. Verify:
   - ✅ Thin scrollbar visible on right edge
   - ✅ Down-arrow pill visible at bottom with pulse animation
   - ✅ Gradient fade from transparent → solid at bottom
   - ✅ "SCROLL" or "N MORE" text visible in red
   - ✅ Hover over any parameter → tooltip shows name, value, range

**Browser compatibility:**
- Chrome/Edge: `::-webkit-scrollbar` styles apply
- Firefox: `scrollbar-width: thin` + `scrollbar-color` apply
- Safari: `::-webkit-scrollbar` styles apply

---

## Impact

**Fixes:**
- DN-2 (Don Norman UX Review): Violated affordance principle
- L53 (Sprint Report): #1 most impactful UX fix
- UAT Finding (implicit): User couldn't discover hidden parameters

**User benefit:**
- Immediate discoverability of all parameters
- Reduced confusion between "hidden param" vs "broken param"
- Professional feel (matches Ableton/Photoshop scroll patterns)

**Reduction in support burden:**
- Users will no longer report effects as "broken" when params are just hidden
- Tooltips provide self-service parameter information

---

## Files Modified

```
/Users/nissimagent/Development/entropic/ui/static/style.css
  Lines 1023-1072: .device-params scroll affordance

/Users/nissimagent/Development/entropic/ui/static/app.js
  Line 1182: createDropdown() — added tooltip
  Line 1194: createToggle() — added tooltip
  Line 1260: createKnob() — added tooltip
```

---

## Next Steps

Task #5 (dry/wet per-effect + undo/redo stack) is now unblocked. However, this task requires:
- Backend Python work (server.py modifications)
- Complex state management (undo stack implementation)

As UX-builder, I can contribute:
- UI design for dry/wet mix slider per effect
- Styling for undo/redo button states (active/disabled)
- Visual feedback for undo/redo actions (toast notifications, animation)

But core implementation (undo stack logic, server-side blending) is outside my domain.

---

*UX Improvements by ux-builder | 2026-02-15*

# Entropic Alternative Approaches — Brainstorm Before Implementation

> **Date:** 2026-02-15
> **Context:** User asked "brainstorm other routes to get the outcomes we want — don't just do what I said"
> **Source:** ARCHITECTURE-DEEP-DIVE.md proposals vs simpler alternatives

---

## Proposal 1: Modular Operator System

### Option A: Quick Wire (RECOMMENDED for v0.7)
- 3 built-in operators: LFO, Envelope Follower, Gate
- Dropdown UI: "modulate [effect] [param] with [LFO/envelope/gate]"
- No routing matrix, no JSON schema, no waveform display
- **1 session to ship.** Gets the "map LFO to pixelsort" use case working immediately.

### Option B: Full Modular System (Deep Dive proposal)
- OperatorEngine with dependency-ordered evaluation, arbitrary mapping
- Waveform visualizer, routing matrix, operator chaining
- **3-4 sessions.** Beautiful but over-engineered for current needs.

### Open Question
DAW mental model (dropdown) or modular synth mental model (patch cables)?

---

## Proposal 2: Effects / Tools / Operators Taxonomy

### Option A: Section Headers + Icons
- Keep one panel, add category headers
- Cheapest change

### Option B: Separate Tabs (Deep Dive proposal)
- Effects tab, Tools tab, Operators tab
- Different UI per category

### Option C: Tag-Based Filtering (RECOMMENDED)
- Every effect gets tags: `[creative, destructive, color, temporal, modulation]`
- Filter buttons at top of panel
- Additive, flexible, no wrong taxonomy

### Open Question
Physically separate UI sections, or filter buttons on one unified list?

---

## Proposal 3: Mode Merge (Quick/Timeline/Perform)

### Option A: Perform Toggle in Timeline
- Timeline stays primary
- "Perform" button enables keyboard triggers + layer mixer
- Quick mode stays

### Option B: Full Unification (Deep Dive proposal)
- One mode with toggleable panels

### Option C: Kill Quick, Timeline + Perform Toggle (RECOMMENDED)
- Quick mode adds nothing Timeline doesn't have
- Remove Quick, Timeline is default, Perform is sub-panel

### Open Question
Has Quick mode ever been useful? Should it exist?

---

## Proposal 4: Pixel Physics Consolidation

### Option A: Fix Bug First, Test, Then Decide (RECOMMENDED)
- server.py fix → test all 21 effects → data-driven decision
- Maybe some are great when they actually work

### Option B: Consolidate Now (Deep Dive proposal)
- 21 → 3 mega-effects with mode selectors
- Risk of premature abstraction

### Option C: Keep All, Add Preview Thumbnails
- 64x64 thumbnail of each effect's result
- User picks by looking, not reading names

### Open Question
Should we test before consolidating, or consolidate blind?

---

## Proposal 5: Photoshop-Level Color Tools

### Option A: Full Implementation (Deep Dive proposal)
- Levels, Curves, HSL, Color Balance, histograms
- 3-4 sessions

### Option B: Histogram + Curves Only (RECOMMENDED)
- Add histogram visualization to existing sliders
- Add one Curves panel (most impactful)
- 1 session

### Option C: Defer Entirely
- Color correct in Premiere/DaVinci before importing
- Focus 100% on creative destruction effects
- 0 sessions

### Open Question
Does the user color-correct in Entropic or in another tool?

---

## Proposal 6: Parameter Sensitivity System

### Option A: Manual Tuning Pass
- Test each effect, set better min/max/default
- Add sweet_spot indicators
- 1-2 sessions

### Option B: Full Automated Detection (Deep Dive proposal)
- Auto-sweep, frame diff, perceptual weighting
- 3+ sessions

### Option C: Logarithmic Scaling Only (RECOMMENDED as Step 1)
- Change parameter scaling from linear to exponential/logarithmic
- One utility function applied to all numeric params
- 30 minutes

### Open Question
Would log sliders alone solve the "sweet spot" problem?

---

## Effort Summary

| Proposal | Full Plan | Recommended Alternative | Savings |
|----------|-----------|------------------------|---------|
| Operators | 3-4 sessions | Quick Wire | 2-3 sessions |
| Taxonomy | 2 sessions | Tag filtering | 1.5 sessions |
| Mode merge | 2 sessions | Kill Quick + toggle | 1 session |
| Physics | 2 sessions | Fix first, decide later | 2 sessions (deferred) |
| Color tools | 3-4 sessions | Histogram + Curves | 2-3 sessions |
| Sensitivity | 3+ sessions | Log scaling + manual | 2.5 sessions |
| **TOTAL** | **~15 sessions** | **~4 sessions** | **~11 sessions** |

---

## Decisions Needed From User

1. Operators: Dropdown or cables?
2. Taxonomy: Tags, tabs, or headers?
3. Kill Quick mode?
4. Fix and test physics before consolidating?
5. Color correction workflow — in Entropic or before import?
6. Log sliders alone, or full sensitivity system?

---

*Brainstorm by Claude Code | Session 65 | 2026-02-15*

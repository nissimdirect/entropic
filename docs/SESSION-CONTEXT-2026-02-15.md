# Entropic UAT Session Context — 2026-02-15

> **Purpose:** Persistent reference so nothing is lost if conversation compacts.
> **Session scope:** First real UAT cycle — user tested ALL effects in web UI, produced massive feedback.

## What Happened

1. User ran UAT on Entropic web UI (localhost:7860)
2. Found 14 critical bugs, 7 parameter bugs, 3 UX bugs
3. Provided 28 feature requests, 9 system-wide requests
4. Proposed 7 architecture changes (operator system, taxonomy, timeline, consolidation, color tools, metering, quick mode removal)
5. Root cause analysis identified: `server.py:377` calls `apply_chain()` WITHOUT `frame_index`/`total_frames` — all stateful effects broken in preview
6. Frontend `uploadVideo()` doesn't check `res.ok`, catch block swallows errors silently

## Key Files Created/Updated This Session

| File | What |
|------|------|
| `docs/UAT-FINDINGS-2026-02-15.md` | Full findings: bugs, params, UX, architecture, features, quote mapping |
| `docs/UAT-PLAN.md` | Updated with 120+ new test cases (effects params, UIT section) |
| `docs/ARCHITECTURE-DEEP-DIVE.md` | **IN PROGRESS** — CTO analysis of 6 architecture proposals |

## Documents Still Needed

1. `docs/ARCHITECTURE-DEEP-DIVE.md` — Full CTO specs for 6 proposals (IN PROGRESS)
2. `docs/ROOT-CAUSE-ANALYSIS.md` — Red team code-level analysis of all bugs
3. `docs/PRODUCT-ANALYSIS.md` — Lenny/PM product strategy
4. `docs/SPRINT-REPORT.md` — Full sprint cycle report with all-skill learnings
5. Entropic project roadmap (phases, priorities)

## Root Causes Found

### Broken Pixel Physics / Temporal / Datamosh (B3-B9, B10-B11)
- `server.py:377`: `frame = apply_chain(frame, chain.effects, watermark=False)` — NO `frame_index` or `total_frames` passed
- `apply_chain()` defaults: `frame_index=0, total_frames=1`
- `physics.py:133`: `if frame_index >= total_frames - 1:` → with (0,1) → `0 >= 0` → True → state cleared immediately
- Same pattern in ALL stateful effects: physics, temporal, sidechain, dsp_filters

### File Upload Silent Failure (B1)
- `app.js`: `uploadVideo()` doesn't check `res.ok` before parsing JSON
- Catch block: `console.error('Upload failed:', err)` — nothing shown to user
- File name displayed BEFORE validation completes

### Sidechain Crossfeed Not Mapped (B14)
- `sidechain_crossfeed()` is just an alias for `sidechain_cross(mode="rgb_shift")`
- Requires `key_frame` parameter which is never provided in web UI
- Not a code bug — it's an architecture gap (no way to provide second video input)

## User Priorities

1. **Tonight:** Export performance video from friend's video via web UI (needs upload + timeline working)
2. **This session:** Plan everything (architecture, fixes, roadmap)
3. **Next session:** Execute fixes
4. **User constraint:** "CLI freaks me out...I need to be able to see what I'm doing"

## User Requests (All)

- CTO deep architecture analysis (6 proposals, implementation-ready depth)
- Red Team root cause analysis
- Lenny/PM product analysis
- Quality review
- Don Norman UX analysis
- Art Director visual/brand analysis
- ALL skills analyze UAT for learnings
- Sprint report covering the full cycle
- Entropic project roadmap
- Everything planned now, executed in separate session

## Learnings Added (#44-49)

- #44: Stateful effects need `preview_mode` flag to skip cleanup
- #45: Hidden scrollable params caused 30+ false bug reports
- #46: Parameter sensitivity needs non-linear scaling + visual diagnostics
- #47: Effects taxonomy: effects vs tools vs operators vs image editing
- #48: Consolidation principle: similar effects → mega-effects with mode selectors
- #49: User requires implementation-ready depth, not bullet points

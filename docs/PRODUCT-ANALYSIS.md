# Entropic Product Analysis — Jobs to Be Done + UX Bridge

> **Skills consulted:** Lenny (product strategy), Don Norman (UX), ChatPRD (requirements), Art Director (brand)
> **Purpose:** Bridge the gap between architecture proposals and user outcomes. Map every architectural decision to a job the user is trying to do.
> **Source:** UAT findings, user testing quotes, architecture deep dive, live usage context

---

## Jobs to Be Done (Expanded by UAT Context)

### Primary Job
**"I need to transform video footage into visually striking art that I can perform live and export for my creative projects."**

This decomposes into:

### Job 1: Import & Preview
**When I** have a video file,
**I want to** load it into the tool and see it immediately,
**So I can** start working without technical friction.

**Current state:** BROKEN. Upload silently fails. No feedback. User dragged file → nothing happened.
**Architecture link:** Bug fix B1 (server.py upload handler + app.js res.ok check)
**Success metric:** Video visible in canvas within 2 seconds of drop.
**Don Norman principle violated:** Feedback — every action must produce visible system response.

### Job 2: Apply & Tweak Effects
**When I** see my video,
**I want to** add effects and adjust parameters while seeing real-time changes,
**So I can** find the right look through exploration.

**Current state:** PARTIALLY BROKEN. 35% of effects don't work in preview (stateful effects). Parameters hidden below scroll fold. No visual feedback on what parameters do.
**Architecture link:** Bug fix Phase 0 (frame_index/total_frames), UX fix (scrollable params), Parameter Sensitivity System (Section 6)
**Success metric:** Every effect produces a visible change. Every parameter slider shows what range is useful. Changes preview in <500ms.
**Don Norman principles violated:** Affordance (scroll indicator), Visibility (hidden params), Mapping (which slider does what)

### Job 3: Chain Effects Creatively
**When I** have one effect working,
**I want to** stack multiple effects and discover emergent behavior,
**So I can** create unique visuals that no single effect could produce.

**Current state:** WORKS WELL for simple chains. User discovered blur → pixelsort = "so cool, interference patterns." But no way to modulate the chain dynamically.
**Architecture link:** Operator System (Section 1), Timeline Automation (Section 3)
**Success metric:** User can create an effect chain and hear themselves say "that's insane" within 5 minutes.
**User quote mapping:** "This adds so much character in front of things like Pixel Sort. Having things blurred before a layer that affects pixels creates interference patterns and so much texture."

### Job 4: Correct Color Professionally
**When I** have my effect chain set,
**I want to** adjust color, contrast, and exposure with professional tools,
**So I can** make the output look intentional, not accidental.

**Current state:** INSUFFICIENT. Basic sliders with no histogram. "Truly, it needs to be as good as Photoshop or Premiere."
**Architecture link:** Photoshop-Level Color Tools (Section 5), Taxonomy (Section 2 — tools vs effects)
**Success metric:** Levels + Curves + Hue/Sat panels with live histogram. User feels "this is a real tool."
**Competitive gap:** Every free image editor has histograms. Without them, Entropic feels like a toy for color work.

### Job 5: Automate & Modulate Parameters Over Time
**When I** find a good effect setup,
**I want to** make parameters change automatically (LFO, sidechain, envelope),
**So I can** create evolving, breathing visuals without manually tweaking every frame.

**Current state:** NOT POSSIBLE. LFO exists but only modulates brightness/displacement/etc. directly — can't map to arbitrary parameters. Sidechain effects are hardcoded.
**Architecture link:** Operator System (Section 1)
**Success metric:** User creates LFO → maps to pixelsort threshold → sees threshold sweeping automatically → says "this is what I wanted."
**User quote mapping:** "I see there is an LFO, but I can't map it to anything else. I want to be able to hook it up to other effects."

### Job 6: Perform Live with Layers
**When I** have multiple visual sources,
**I want to** trigger layers, blend them, and record the performance,
**So I can** create a live video performance (like a VJ).

**Current state:** BUILT (v0.6.0 perform mode) but INACCESSIBLE — separate mode, not integrated with timeline, "CLI freaks me out."
**Architecture link:** Perform Mode as Timeline Layer (Section 3)
**Success metric:** Perform tools visible as a panel below timeline. Layers trigger from keyboard. Recording captures the performance.
**User quote mapping:** "Performance mode should be an automation layer on top of the timeline, with just additional tools being shown at the bottom, like we're combining Premiere and Ableton."

### Job 7: Export a Finished Video
**When I** have my performance/edit ready,
**I want to** render it to a video file I can share,
**So I can** post it, send it to my friend, use it in my creative work.

**Current state:** CLI render works. Web UI render untested due to upload bug.
**Architecture link:** Bug fix B1 (upload) → this unblocks export
**Tonight's priority:** "The priority is for me to get out this performance video from my friend tonight."
**Success metric:** Click render → progress bar → download MP4.

### Job 8: Understand What Went Wrong
**When** an effect doesn't do what I expect,
**I want to** understand why (is it broken? is the parameter wrong? is it hidden?),
**So I can** either fix it or report it accurately.

**Current state:** TERRIBLE. No error messages. No visual diagnostics. User can't distinguish "effect broken" from "parameter hidden" from "parameter value wrong."
**Architecture link:** Parameter Sensitivity System (Section 6), frame diff tool, scroll affordances
**Success metric:** When a parameter does nothing, the UI shows WHY (e.g., "No pixel change detected at this value. Try range 0.2-0.6.")
**Don Norman principle:** Error prevention + help users recognize, diagnose, and recover from errors.

---

## UX Gap Analysis (Don Norman Audit)

### Nielsen's 10 Heuristics — Entropic Scorecard

| # | Heuristic | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Visibility of system status | 2/10 | No upload progress, no effect processing indicator, no render status |
| 2 | Match between system and real world | 6/10 | Audio metaphors (sidechain, LFO, gate) are intuitive for target users |
| 3 | User control and freedom | 4/10 | Duotone can't revert, scanlines crashes, no global undo |
| 4 | Consistency and standards | 5/10 | Effects/tools/operators mixed together; inconsistent UI patterns |
| 5 | Error prevention | 3/10 | No parameter validation, no range indicators, no confirmation on destructive actions |
| 6 | Recognition over recall | 4/10 | Must remember what Quick/Timeline/Perform do; no tooltips |
| 7 | Flexibility and efficiency | 5/10 | Effect chaining is powerful; keyboard shortcuts exist for perform |
| 8 | Aesthetic and minimalist design | 6/10 | Clean but information-sparse; needs more visual feedback |
| 9 | Help users recognize and recover from errors | 1/10 | Silent failures everywhere; no error toasts; no diagnostics |
| 10 | Help and documentation | 2/10 | No in-app help; effect descriptions not shown in UI |

**Overall: 3.8/10** — The product has powerful features behind a frustrating interface.

### Priority UX Fixes (Ordered by Impact)

1. **Error feedback system** (Heuristic 1, 9) — Toasts for all errors. Loading states. Progress bars.
2. **Scroll affordance on param panels** (Heuristic 1, 6) — Gradient fade + "N more" badge.
3. **Tooltips on everything** (Heuristic 6, 2) — Effect descriptions, parameter explanations, mode descriptions.
4. **Unified mode** (Heuristic 3, 4) — Merge Quick/Timeline/Perform into one view with toggleable panels.
5. **Parameter sensitivity indicators** (Heuristic 5, 9) — Show useful range, dead zones, blow-out points.
6. **Undo/redo** (Heuristic 3) — Global undo stack for effect additions, parameter changes, deletions.

---

## Competitive Positioning (Lenny Framework)

### What We Compete On (Win)
- **Creative destruction effects** — No competitor has 109 glitch/physics/destruction effects
- **Audio-inspired modulation** — Sidechain, ADSR, LFO on video parameters = unique
- **Effect chaining** — Combinatorial creativity (blur → pixelsort → datamosh)
- **Live performance** — Real-time layer triggering with ADSR envelopes

### What We DON'T Compete On (Table Stakes)
- **Color correction** — Must have it, can't win on it (Photoshop/Premiere/DaVinci own this)
- **Basic video editing** — Cut, trim, crop = expected, not differentiating
- **Export quality** — Must work reliably, not a selling point

### What to Cut
- **AM radio** — User said "kind of useless." Consider removing or making it a preset of ring mod.
- **Pixel annihilate** — Too similar to other destruction effects. Cut or merge.
- **Xerox** — "Maybe chopping block." Needs more differentiation or remove.
- 109 effects → aim for 60-70 high-quality effects after consolidation

### Positioning Statement
**For** video artists and VJs **who** want to create glitch art and visual performances,
**Entropic is** an Ableton-for-video effects tool
**that** lets you chain destructive effects, modulate parameters with LFO/sidechain/ADSR, and perform live with triggered layers.
**Unlike** Premiere (editing tool) or After Effects (motion graphics tool),
**Entropic** treats video like an audio signal — with modulators, sidechaining, and real-time performance.

---

## User Journey (Current vs Target)

### Current Journey (Broken)
```
Open tool → Drag video → Nothing happens (B1) → Confused →
Try Quick mode → "What is this?" → Try Timeline →
Add effect → Some work, some don't → Can't tell why →
Scroll params → Don't know scrollable → Think params missing →
Switch to Perform → Different mode, lost context →
Give up on perform → Back to timeline → Can't export → Frustrated
```

### Target Journey (Post-Fixes)
```
Open tool → Drag video → Instant preview (2s) →
Timeline view (default) → Add effect → See change immediately →
Tweak params → Sensitivity indicator shows useful range →
Chain effects → Discover combinations → "This is insane!" →
Open color panel → Levels + curves + histogram → Professional look →
Add operator (LFO) → Map to param → See it modulate → "Ableton for video!" →
Toggle perform panel → Trigger layers → Record performance →
Render → Download MP4 → Share
```

### Critical Path Moments
1. **First 30 seconds:** Upload → see video → add first effect. If this fails, user leaves.
2. **First 5 minutes:** Find 2-3 effects they love. If everything looks the same or broken, user leaves.
3. **First 15 minutes:** Chain effects, discover emergent behavior. This is the "aha" moment.
4. **First session:** Export something they're proud of. This creates retention.

---

## Architecture → Outcome Mapping

| Architecture Proposal | JTBD | User Outcome | Priority |
|----------------------|------|-------------|----------|
| Phase 0: Bug fixes | Job 1, 2, 7 | Can actually USE the tool | P0 (blocking) |
| Phase 1: Parameter UX | Job 2, 8 | Parameters make sense, sweet spots discoverable | P1 |
| Phase 2: Color tools | Job 4 | Professional color correction with histogram feedback | P2 |
| Phase 3: Taxonomy | Job 2, 5 | Clear mental model of what's an effect vs tool vs operator | P2 |
| Phase 4: Operators | Job 5 | Automate + modulate = breathing, evolving visuals | P3 |
| Phase 5: Timeline automation | Job 5, 6 | Premiere + Ableton hybrid workflow | P3 |
| Phase 6: Physics consolidation | Job 2 | Fewer, better, more discoverable physics effects | P3 |
| Phase 7: Sensitivity system | Job 8 | Visual parameter diagnostics | P4 |

---

*Product analysis by Claude Code | Lenny + Don Norman + ChatPRD + Art Director perspectives | 2026-02-15*

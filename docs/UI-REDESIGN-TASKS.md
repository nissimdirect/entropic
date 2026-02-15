# Entropic UI Redesign — Task List

> Source: ARCHITECTURE-DEEP-DIVE.md §7, UAT-FINDINGS-2026-02-15.md Round 2
> Created: 2026-02-15
> Status: IN PROGRESS

---

## Phase A: Layout Foundation (COMPLETE)

- [x] A1. Kill 3-mode system (Quick/Timeline/Perform) — hide mode toggle
- [x] A2. Merge topbar + menubar into single bar (File/Edit/View + logo + status)
- [x] A3. Move Load File + Export into File menu
- [x] A4. Move Undo/Redo into Edit menu, remove from toolbar
- [x] A5. Replace dice emoji with "Rand" text button
- [x] A6. Fix icon sizes (undo/redo/refresh too small → 16px)
- [x] A7. Hide right panel (layers/history sidebar)
- [x] A8. Hide histogram panel + toggle
- [x] A9. Add drag dividers (browser width, canvas↔timeline, timeline↔chain)
- [x] A10. Collapsible browser sidebar (Tab shortcut)
- [x] A11. Fix panel collapse (arrow goes to middle → shrink to header only)
- [x] A12. History as dropdown button (right-aligned)
- [x] A13. Light/dark theme toggle
- [x] A14. Save panel sizes to localStorage on drag end
- [x] A15. Fix collapsed panel grid rows (togglePanel adjusts grid-template-rows)

## Phase B: Track System (DONE)

- [x] B1. Multi-track data model (max 8 tracks, each has: name, effects chain, opacity, solo, mute, blend mode, color)
- [x] B2. Track strip UI in timeline (left header: ▼ name [100%] [S] [M] [Normal▾])
- [x] B3. "+" Add Track button at bottom of timeline
- [x] B4. Right-click context menu on track (Add Above/Below, Duplicate, Delete, Move Up/Down)
- [x] B5. Right-click on timeline background (Add Track, Paste)
- [x] B6. Track selection (click to select, show chain for selected track)
- [x] B7. Track collapse/expand toggle (▼ in track header)
- [x] B8. Track color indicator (left edge strip)
- [x] B9. Opacity slider (compact inline, 0-100%)
- [x] B10. Solo button (yellow active state)
- [x] B11. Mute button (red active state)
- [x] B12. Blend mode dropdown (Normal, Multiply, Screen, Add, Overlay, Darken, Lighten)
- [ ] B13. Backend: multi-track rendering pipeline (composite tracks by blend mode + opacity)

## Phase C: Transport Bar (DONE — UI + wiring)

- [x] C1. Transport controls in topbar center (Play/Pause, Rec, Overdub, Capture, Loop)
- [x] C2. Ableton-style icons (▶/▮▮, ●, ◎, ⊡, ↻)
- [x] C3. Timecode display (HH:MM:SS.ff / duration, frame count)
- [x] C4. Play/Pause toggle (Space bar) — wired to timelineEditor + perform
- [x] C5. Record button (solid red, R key) — wired to perfToggleRecord
- [x] C6. Overdub button (hollow red, Shift+R) — wired to toggleAutoRecording
- [x] C7. Capture button (reticle, Cmd+Shift+C) — wired with blink animation
- [x] C8. Loop toggle (L key) with orange active state
- [ ] C9. Loop region: drag edges on ruler to set boundaries
- [x] C10. Frame navigation (← → arrow keys, already exists)

## Phase D: Perform Module (Per-Track Device)

- [ ] D1. Perform device type (appears in effect chain like any effect)
- [ ] D2. Trigger slots (up to 8 per perform device)
- [ ] D3. Slot mapping (toggle track, trigger effect, change parameter)
- [ ] D4. ADSR envelope per slot
- [ ] D5. Trigger modes (toggle, one-shot, hold, retrigger)
- [ ] D6. Visual: expanded perform device in chain area

## Phase E: Keyboard/MIDI Input

- [ ] E1. Keyboard toggle button in topbar (🎹)
- [ ] E2. When active: letter/number keys → MIDI notes, transport shortcuts still work
- [ ] E3. MIDI routing preferences (dropdown in settings)
- [ ] E4. External MIDI input support (Web MIDI API)
- [ ] E5. MIDI Learn mode (click param → move controller → mapped)

## Phase F: Freeze/Flatten

- [ ] F1. Right-click track → Freeze (render to cached frames, disable editing)
- [ ] F2. Right-click track → Flatten (commit frozen frames, clear chain)
- [ ] F3. Visual: frozen track shows snowflake icon, grayed-out chain
- [ ] F4. Backend: cache rendered frames per track

## Immediate Fixes (from latest UAT) — COMPLETE

- [x] I1. Dice button looks terrible → replaced with "Rand" text
- [x] I2. Undo/redo/refresh icons too small → bumped to 16px
- [x] I3. Combine topbar + menubar → single row
- [x] I4. History to right side
- [x] I5. Panel collapse arrow goes to middle → max-height: 28px when collapsed
- [x] I6. Default Track 1 on startup (before file load)
- [x] I7. Add Track "+" button sizing (channel-strip width)
- [x] I8. Hide diff tools from preview canvas
- [x] I9. Loop and Refresh icons differentiated
- [x] I10. Mixer button removed from toolbar

---

## Phase Round 3 Tasks (NEW — from sprint completion)

- [ ] R3-1. UAT Round 3 execution — test all completed features per checklist
- [ ] R3-2. File upload regression test (was broken in Round 1)
- [ ] R3-3. Verify panel resize persistence across reload
- [ ] R3-4. Test all keyboard shortcuts (Space, R, Shift+R, Cmd+Shift+C, L, Tab)
- [ ] R3-5. Verify transport controls wired correctly
- [ ] R3-6. Test track selection → chain panel update
- [ ] R3-7. Verify Solo/Mute buttons toggle correctly
- [ ] R3-8. Test View menu items (Toggle Histogram, Toggle Sidebar, etc.)

---

## Implementation Priority

1. **Phase A** — Layout foundation ✅ COMPLETE
2. **Phase B** — Track system ✅ COMPLETE (UI layer)
3. **Phase C** — Transport bar ✅ COMPLETE (UI wiring)
4. **Immediate Fixes** — ✅ COMPLETE
5. **Phase Round 3** — UAT testing (CURRENT)
6. **Phase F** — Freeze/Flatten (backend needed)
7. **Phase D** — Perform module (backend needed)
8. **Phase E** — Keyboard/MIDI (backend needed)
9. **Backend: Multi-track rendering** — B13 (render pipeline)

# Entropic Performance Mode — Session Handoff

**Created:** 2026-02-09
**Purpose:** Load this into the next Claude Code session to continue work.

---

## Copy-paste this prompt to start next session:

```
Continue building Entropic Live Performance Mode. Here's where we left off:

**What's done (all 8 steps implemented + red team fixes applied):**
- core/video_io.py — stream_frames(), open_output_pipe(), mux_audio() added
- effects/adsr.py — trigger_on(), trigger_off(), advance() added
- core/midi.py — CREATED (ported from cymatics, note_on/off, Launchpad+MIDI Mix)
- core/automation.py — MidiEventLane + PerformanceSession added
- core/layer.py — CREATED (Layer dataclass, LayerStack compositor, 4 trigger modes, 4 ADSR presets, choke groups)
- core/performer.py — CREATED (pygame preview, MIDI+keyboard, buffer recording, Don Norman safety: Shift+P panic, Shift+Q quit, double-tap Esc, caffeinate, auto-buffer)
- core/render.py — CREATED (offline 1080p render from automation JSON)
- entropic_perform.py — CREATED (CLI: --base, --render, --midi, --midi-list, --midi-learn)

**Red team fixes applied:**
- Generator leak on video loop (explicit .close())
- Buffer cap (50K events max)
- FFmpeg stderr=DEVNULL (prevents pipe block)
- FFmpeg kill() fallback after terminate() timeout
- Video path validation before streaming

**UIT doc created:** docs/PERFORM-UIT.md (59 test cases)

**What to do next:**
1. Run UIT tests with an actual video file — fix any issues found
2. Test MIDI with Launchpad + MIDI Mix if available
3. 30-minute stress test
4. If time: Ableton Clip Mode / Session View grid (future improvement, not P0)

**Deadline:** Saturday Feb 15 (friend's virtual opening set)
**Project path:** ~/Development/entropic/
**Plan file:** Read the plan at ~/.claude/plans/purrfect-sniffing-ritchie.md for full context
```

---

## Files Modified/Created This Session

| File | Lines | What |
|------|-------|------|
| `core/video_io.py` | +115 | stream_frames, open_output_pipe, mux_audio |
| `effects/adsr.py` | +45 | trigger_on, trigger_off, advance |
| `core/midi.py` | ~180 | New — MIDI controller |
| `core/automation.py` | +120 | MidiEventLane, PerformanceSession |
| `core/layer.py` | ~280 | New — Layer + LayerStack |
| `core/performer.py` | ~450 | New — PerformanceEngine |
| `core/render.py` | ~220 | New — offline render |
| `entropic_perform.py` | ~290 | New — CLI entry |
| `docs/PERFORM-UIT.md` | ~250 | New — 59 test cases |

## Token-Saving Tips for Next Session

1. **Don't re-read all 8 files** — only read the ones relevant to current task
2. **Use the UIT doc** to drive testing — it lists every test case
3. **The plan file has full architecture** — read that instead of re-exploring
4. **Compact early** — this feature set is context-heavy

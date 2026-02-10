# Entropic Live Performance Mode — User Integration Testing

**Date:** 2026-02-09
**Version:** v0.1 (initial build)
**Tester:** _______________
**Environment:** macOS, Python 3.x, pygame, FFmpeg, Launchpad (optional), MIDI Mix (optional)

---

## How to Use This Document

1. Run each test case in order (they build on each other)
2. Write your **Actual Result** in the blank column
3. Mark PASS/FAIL
4. If FAIL, note what happened so we can fix it

**Setup before testing:**
```bash
cd ~/Development/entropic
# Quick test with any MP4 you have:
python entropic_perform.py --base YOUR_VIDEO.mp4
```

---

## Section 1: Launch & Display

| # | Test | Steps | Expected Result | Actual Result | P/F |
|---|------|-------|-----------------|---------------|-----|
| 1.1 | Basic launch | `python entropic_perform.py --base video.mp4` | Pygame window opens (960x540), 4 layers listed in console, HUD shows [BUF] indicator | | |
| 1.2 | No video file | `python entropic_perform.py --base nonexistent.mp4` | Console prints "ERROR: Video not found" for each layer, no crash | | |
| 1.3 | No args | `python entropic_perform.py` | Prints "Error: --base or --config required" and exits | | |
| 1.4 | Custom layer count | `python entropic_perform.py --base video.mp4 --layers 2` | Only 2 layers shown in console and HUD | | |
| 1.5 | Custom FPS | `python entropic_perform.py --base video.mp4 --fps 24` | Video plays at ~24fps (check HUD frame counter speed) | | |
| 1.6 | HUD visible | Look at the pygame window | Bottom-left: frame counter + elapsed time. Top-left: [BUF] in gray. Left side: layer status list | | |

---

## Section 2: Keyboard Controls — Basic

| # | Test | Steps | Expected Result | Actual Result | P/F |
|---|------|-------|-----------------|---------------|-----|
| 2.1 | Play/Pause | Press **Space** | Console prints [PAUSED], video freezes. Press again → [PLAYING], video resumes | | |
| 2.2 | Layer toggle (1) | Press **1** | Console prints "Layer 0 (Clean): ON/OFF", HUD updates color | | |
| 2.3 | Layer toggle (2) | Press **2** | Console prints "Layer 1 (VHS+Glitch): ON", visual changes | | |
| 2.4 | Layer toggle (3) | Press **3** | Console prints "Layer 2 (PixelSort): ON", visual changes | | |
| 2.5 | Layer toggle (4) | Press **4** | Console prints "Layer 3 (Feedback): ON", visual changes | | |
| 2.6 | Invalid layer (9) | Press **9** | Nothing happens (no crash, no console output) | | |
| 2.7 | Multiple layers | Press **2**, then **3**, then **4** | All three layers show as ON in HUD, visuals compound | | |

---

## Section 3: Keyboard Controls — Safety (Don Norman Fixes)

| # | Test | Steps | Expected Result | Actual Result | P/F |
|---|------|-------|-----------------|---------------|-----|
| 3.1 | P alone does nothing | Press **P** (no modifier) | Nothing happens. No panic. No console output | | |
| 3.2 | Shift+P = Panic | Turn on layers 2,3,4 then press **Shift+P** | Console prints "[PANIC] All layers reset", all layers off in HUD | | |
| 3.3 | Q alone does nothing | Press **Q** (no modifier) | Nothing happens. App stays open | | |
| 3.4 | Shift+Q = Quit | Press **Shift+Q** | App closes cleanly, returns to terminal | | |
| 3.5 | Esc single tap | Press **Esc** once | Console prints "[Press Esc again to exit]", app stays open | | |
| 3.6 | Esc double tap (fast) | Press **Esc** twice within 0.5 seconds | App closes cleanly | | |
| 3.7 | Esc double tap (slow) | Press **Esc**, wait 2 seconds, press **Esc** again | Second press shows "[Press Esc again to exit]" again (timer reset). App stays open | | |

---

## Section 4: Recording & Buffer

| # | Test | Steps | Expected Result | Actual Result | P/F |
|---|------|-------|-----------------|---------------|-----|
| 4.1 | Buffer indicator | Launch app, look at HUD | [BUF] in gray at top-left (buffer is capturing, not armed) | | |
| 4.2 | Arm recording | Press **R** | Console: "[REC ON] Buffer cleared, recording fresh (gen 1)". HUD: [REC] in red | | |
| 4.3 | Disarm recording | Press **R** again | Console: "[REC OFF] (buffer retained from this take)". HUD: [BUF] in gray | | |
| 4.4 | Re-arm clears buffer | Trigger some layers, press **R** (arm), trigger more layers, press **R** (disarm), press **R** (arm again) | Console: "gen 2" — buffer cleared and restarted | | |
| 4.5 | Exit with recording armed | Arm R, trigger some layers, press **Shift+Q** | Auto-saves perf_TIMESTAMP.json + .layers.json. Console shows paths | | |
| 4.6 | Exit without recording — keep | Don't press R, trigger some layers, press **Shift+Q** | Prompt: "Save buffer? [y/N]:" — type **y** → saves files | | |
| 4.7 | Exit without recording — discard | Don't press R, trigger some layers, press **Shift+Q** | Prompt: "Save buffer? [y/N]:" — type **n** or Enter → "Buffer discarded." | | |
| 4.8 | No events captured | Launch, immediately **Shift+Q** (no layer triggers) | Console: "No events captured." No save prompt | | |

---

## Section 5: MIDI (Skip if no MIDI controller)

| # | Test | Steps | Expected Result | Actual Result | P/F |
|---|------|-------|-----------------|---------------|-----|
| 5.1 | List devices | `python entropic_perform.py --midi-list` | Lists available MIDI ports. No crash if none found | | |
| 5.2 | MIDI learn | `python entropic_perform.py --base video.mp4 --midi-learn` | Prints all incoming MIDI messages (note/CC/channel) in console | | |
| 5.3 | Launchpad trigger | `--midi 0` (adjust ID), hit pad 1 (note 36) | Layer 0 triggers ON. Console confirms | | |
| 5.4 | MIDI Mix fader | Move fader 1 (CC 16) | Layer 0 opacity changes. HUD shows percentage updating | | |
| 5.5 | Note off (gate mode) | Set a layer to gate mode in config, hold pad, release | Layer ON while held, OFF on release | | |
| 5.6 | No MIDI available | `python entropic_perform.py --base video.mp4 --midi 99` | Console: "MIDI init failed: ..." — app continues without MIDI, keyboard still works | | |

---

## Section 6: Trigger Modes

| # | Test | Steps | Expected Result | Actual Result | P/F |
|---|------|-------|-----------------|---------------|-----|
| 6.1 | Always On (L0) | Launch — check Layer 0 | Layer 0 (Clean) is always visible in HUD. Cannot be toggled off | | |
| 6.2 | Toggle (L1) | Press **2** to toggle Layer 1 | ON → stays ON until pressed again → OFF | | |
| 6.3 | ADSR Pluck (L2) | Press **3** (Layer 2 = PixelSort, pluck preset) | Quick attack, fast decay, sustains at 80%, then release when toggled off | | |
| 6.4 | ADSR Stab (L3) | Press **4** (Layer 3 = Feedback, stab preset) | Near-instant attack, zero sustain (fades out on its own), short release | | |

---

## Section 7: Visual Quality

| # | Test | Steps | Expected Result | Actual Result | P/F |
|---|------|-------|-----------------|---------------|-----|
| 7.1 | Preview resolution | Look at window title bar size | ~960x540 (half of 1080p) | | |
| 7.2 | Frame rate feels smooth | Watch playback for 10 seconds | Smooth-ish at 30fps. No stuttering or freezing | | |
| 7.3 | VHS effect visible | Toggle layer 2 ON | Visual noise + tracking artifacts visible | | |
| 7.4 | PixelSort visible | Toggle layer 3 ON | Pixel sorting visible (horizontal bands/streaks) | | |
| 7.5 | Feedback visible | Toggle layer 4 ON | Ghosting/trails visible | | |
| 7.6 | Layer compositing | Turn on layers 2+3 simultaneously | Both effects visible blended together | | |

---

## Section 8: Offline Render

| # | Test | Steps | Expected Result | Actual Result | P/F |
|---|------|-------|-----------------|---------------|-----|
| 8.1 | Render from automation | `python entropic_perform.py --render --automation perf_TIMESTAMP.json --output test_render.mp4` | Progress shows in console, creates test_render.mp4 | | |
| 8.2 | Render with audio | `python entropic_perform.py --render --automation perf.json --audio video.mp4 --output test_audio.mp4` | Output has both video and audio. Play in VLC to confirm | | |
| 8.3 | Render with duration | Add `--duration 10` to render command | Only renders 10 seconds (300 frames at 30fps) | | |
| 8.4 | Companion config auto-detect | Have perf_TIMESTAMP.layers.json next to perf_TIMESTAMP.json, don't pass --config | Console: "Using companion config: ..." | | |
| 8.5 | Missing automation file | `--render --automation nonexistent.json` | Error message, clean exit (no crash) | | |
| 8.6 | Render output plays | Open rendered file in VLC/QuickTime | Video plays, effects match what you saw in performance preview | | |

---

## Section 9: Stability (30-Minute Stress)

| # | Test | Steps | Expected Result | Actual Result | P/F |
|---|------|-------|-----------------|---------------|-----|
| 9.1 | Long playback | Let video play for 5+ minutes without interaction | No crash, no memory growth (check Activity Monitor), video loops smoothly | | |
| 9.2 | Rapid triggering | Rapidly press 1-4 keys for 30 seconds | No crash, layers toggle correctly, no visual artifacts | | |
| 9.3 | macOS sleep prevention | Check Activity Monitor for "caffeinate" process | caffeinate process visible while app runs, disappears after quit | | |
| 9.4 | Clean exit | After any test, Shift+Q | No zombie FFmpeg processes (check: `ps aux | grep ffmpeg`) | | |
| 9.5 | Keyboard interrupt | Press Ctrl+C during performance | Console: "[INTERRUPTED]", clean exit, no zombie processes | | |

---

## Section 10: Edge Cases

| # | Test | Steps | Expected Result | Actual Result | P/F |
|---|------|-------|-----------------|---------------|-----|
| 10.1 | Very short video (<2s) | Use a 1-second MP4 as --base | Video loops correctly, no crash | | |
| 10.2 | Large video (1080p+) | Use a 1080p or 4K MP4 | Preview scales down to 480p, no crash, acceptable FPS | | |
| 10.3 | Pause + trigger layers | Pause (Space), then toggle layers, then unpause | Layers should take effect when unpaused | | |
| 10.4 | All layers off | Turn off all layers (if possible) | Black screen (no crash), HUD still visible | | |

---

## Summary

| Section | Total Tests | Pass | Fail | Notes |
|---------|------------|------|------|-------|
| 1. Launch & Display | 6 | | | |
| 2. Keyboard Basic | 7 | | | |
| 3. Keyboard Safety | 7 | | | |
| 4. Recording & Buffer | 8 | | | |
| 5. MIDI | 6 | | | |
| 6. Trigger Modes | 4 | | | |
| 7. Visual Quality | 6 | | | |
| 8. Offline Render | 6 | | | |
| 9. Stability | 5 | | | |
| 10. Edge Cases | 4 | | | |
| **TOTAL** | **59** | | | |

**Overall Result:** PASS / FAIL (circle one)

**Blocker Issues (must fix before Saturday):**
1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

**Nice-to-Have Issues (fix if time allows):**
1. _______________________________________________
2. _______________________________________________

**Tester Notes:**
_______________________________________________
_______________________________________________
_______________________________________________

# Entropic Alpha v2 — User Acceptance Testing Plan

> **Date:** 2026-02-09
> **Version:** Alpha v2 (109 effects, desktop app, timeline editor, spatial masks, **live performance mode**)
> **Tester:** nissimdirect
> **Prepared by:** CTO, Red Team, Mad Scientist, Lenny, Don Norman
> **Updated:** Added Sections 22-27 for Live Performance Mode (MIDI, layers, recording, render, safety, stability)

---

## How To Use This Document

1. Work through each section top-to-bottom
2. Mark each test: **PASS**, **FAIL**, or **SKIP** (with reason)
3. For FAIL: write what happened in the Notes column
4. You need a **test video** — any MP4 file (5-60 seconds works best)
5. All commands run from `~/Development/entropic/`

---

## Getting Started (Step-by-Step Setup)

> **Read this whole section before running anything.**
> It walks you through opening Terminal, checking your setup, and running your first test.
> If anything goes wrong, copy the error text and paste it to Claude.

---

### Step 1: Open Terminal

1. Press **Cmd + Space** on your keyboard (this opens Spotlight search)
2. Type the word **Terminal**
3. Press **Enter**
4. A window will open with a dark/light background and text that looks something like:
   ```
   nissimagent@Nissimagents-MacBook-Pro ~ %
   ```
   This is your **command prompt**. You type commands here and press Enter to run them.

**What is Terminal?** It's a text-based way to talk to your Mac. Instead of clicking icons, you type commands. Every command in this document goes here.

---

### Step 2: Navigate to the Entropic Project Folder

Type this command and press **Enter**:
```bash
cd ~/Development/entropic
```

**What this does:** `cd` means "change directory" (like opening a folder in Finder). `~/Development/entropic` is the path to the Entropic project on your Mac. The `~` means your home folder.

**How to know it worked:** Your prompt should now show `entropic` somewhere in it:
```
nissimagent@Nissimagents-MacBook-Pro entropic %
```

**If you see "No such file or directory":** The folder might not exist. Tell Claude.

---

### Step 3: Check That Everything Is Installed

Run these three commands **one at a time** (type each one, press Enter, read the output, then do the next):

**Command 1 — Check Python:**
```bash
python3 --version
```
**You should see:** `Python 3.11.x` or `Python 3.12.x` or similar. Any `3.x` is fine.
**If you see "command not found":** Python isn't installed. Tell Claude.

**Command 2 — Check FFmpeg:**
```bash
ffmpeg -version
```
**You should see:** A wall of text starting with `ffmpeg version ...` — that's fine, it means FFmpeg is installed.
**If you see "command not found":** FFmpeg isn't installed. Tell Claude.

**Command 3 — Check Entropic loads:**
```bash
python3 -c "from effects import EFFECTS; print(f'{len(EFFECTS)} effects loaded')"
```
**You should see:** `109 effects loaded`
**If you see an error (ImportError, ModuleNotFoundError):** A dependency might be missing. Copy the full error and tell Claude.

**Command 4 — Check pygame (needed for performance mode):**
```bash
python3 -c "import pygame; print('pygame OK')"
```
**You should see:** `pygame OK` (possibly with a version message above it)
**If you see "ModuleNotFoundError":** Install it by running:
```bash
pip3 install pygame
```
Then try the check again.

---

### Step 4: Get a Test Video

You need **any MP4 video file** to test with. Here's how to get one:

**Option A — Use a video you already have:**
- Check your Desktop, Downloads, or Movies folder for any `.mp4` file
- To find MP4s on your Mac, run:
  ```bash
  find ~/Desktop ~/Downloads ~/Movies -name "*.mp4" -maxdepth 1 2>/dev/null
  ```
  This searches those three folders for MP4 files and lists them.

**Option B — Record one on your phone:**
- Record a 10-second video on your iPhone
- AirDrop it to your Mac (it lands in Downloads)
- The file will be at `~/Downloads/IMG_XXXX.mp4` or similar

**Option C — Check if test clips already exist:**
```bash
ls test-videos/clips/
```
If files appear, you already have test clips.

**Remember the path to your video.** For the rest of this document, replace `YOUR_VIDEO.mp4` with your actual filename. For example, if your video is on the Desktop and called `myvid.mp4`, the path is:
```
~/Desktop/myvid.mp4
```

---

### Step 5: Choose What to Test

Entropic has **three modes**. You don't need to test all three — pick the one that matters most right now:

#### Mode A: Live Performance Mode (Sections 22-27) — TEST THIS FIRST FOR SATURDAY

This is the new MIDI layer compositor you'll use for the live set.

**To start it:**
```bash
python3 entropic_perform.py --base ~/Desktop/YOUR_VIDEO.mp4
```
Replace `YOUR_VIDEO.mp4` with your actual file path.

**What happens next:**
1. Terminal will print some setup info (layer names, MIDI mappings)
2. A **pygame window** pops up showing your video at half resolution (~960x540)
3. The video starts playing automatically
4. You control it with your keyboard:

| Key | What It Does |
|-----|-------------|
| **1** | Toggle Layer 1 (Clean — base video) |
| **2** | Toggle Layer 2 (VHS + Glitch effect) |
| **3** | Toggle Layer 3 (Pixel Sort effect) |
| **4** | Toggle Layer 4 (Feedback/trails effect) |
| **Space** | Pause / Resume playback |
| **R** | Arm recording (captures your layer triggers for later render) |
| **Shift + P** | Panic — reset all layers to OFF |
| **Shift + Q** | Quit the app cleanly |
| **Esc, Esc** | Exit (press Esc twice quickly, within half a second) |

**When you're done:** Press **Shift+Q** to quit. If you triggered any layers, it will ask if you want to save the recording.

**To test with MIDI (optional):**
- Plug in your Launchpad or MIDI Mix **before** starting
- Add `--midi 0` to the command:
  ```bash
  python3 entropic_perform.py --base ~/Desktop/YOUR_VIDEO.mp4 --midi 0
  ```
- Launchpad pads (notes 36-43) trigger layers 1-8
- MIDI Mix faders (CC 16-23) control layer opacity

**To render a recorded performance:**
After quitting, if you saved a recording (e.g., `perf_20260210_143022.json`), render it at full quality:
```bash
python3 entropic_perform.py --render --automation perf_20260210_143022.json --output my_render.mp4 --audio ~/Desktop/YOUR_VIDEO.mp4
```
This creates a 1080p video with your performance baked in. Open `my_render.mp4` in VLC or QuickTime to check it.

---

#### Mode B: CLI Effects (Sections 1-17) — The Original Entropic

Apply glitch effects to videos via command line.

**To start:**
```bash
python3 entropic.py new uat-test --source ~/Desktop/YOUR_VIDEO.mp4
```
This creates a "project" that holds your source video and all the renders.

**Then apply effects like:**
```bash
python3 entropic.py apply uat-test --effect pixelsort
python3 entropic.py apply uat-test --effect vhs
python3 entropic.py apply uat-test --effect feedback
```
Each command processes your video and opens the result automatically.

---

#### Mode C: Desktop App (Sections 18-21) — Web-Based UI

A browser-based DAW-style interface.

**To start:**
```bash
python3 server.py
```
Then open your web browser (Safari or Chrome) and go to:
```
http://localhost:7860
```
The interface should load with 4 panels (browser, canvas, chain, layers).

---

### Troubleshooting

| Problem | Solution |
|---------|----------|
| "command not found: python3" | Python not installed. Run: `brew install python3` |
| "command not found: ffmpeg" | FFmpeg not installed. Run: `brew install ffmpeg` |
| "command not found: brew" | Homebrew not installed. Go to https://brew.sh and follow the one-line install |
| "ModuleNotFoundError: No module named 'pygame'" | Run: `pip3 install pygame` |
| "ModuleNotFoundError: No module named 'numpy'" | Run: `pip3 install numpy` |
| "ModuleNotFoundError: No module named 'PIL'" | Run: `pip3 install Pillow` |
| "No such file or directory" on your video path | Double-check the path. Drag the file from Finder into Terminal — it auto-fills the path |
| Pygame window doesn't appear | Make sure you're not in full-screen Terminal. Try resizing Terminal smaller first |
| Video plays but looks frozen | Press **Space** — you might be paused |
| "MIDI init failed" | Your MIDI device isn't connected, or the device ID is wrong. Try `--midi-list` to see available devices |
| Terminal seems stuck / nothing happening | Press **Ctrl+C** to stop whatever is running, then try again |
| Want to go back to your home folder | Run: `cd ~` |

**Pro tip:** You can **drag any file from Finder into the Terminal window** and it will paste the full file path. This is the easiest way to get video file paths right.

---

---

## SECTION 1: SMOKE TESTS (Do These First)

> **Goal:** Confirm the system boots and basic operations work.
> **Time:** ~5 minutes

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 1.1 | Python runs | `python3 --version` | 3.x output | [ ] | |
| 1.2 | FFmpeg installed | `ffmpeg -version` | Version info | [ ] | |
| 1.3 | Import works | `python3 -c "from effects import EFFECTS; print(len(EFFECTS))"` | `109` | [ ] | |
| 1.4 | CLI help | `python3 entropic.py --help` | Shows commands | [ ] | |
| 1.5 | Version | `python3 entropic.py --version` | `entropic 0.2.0` | [ ] | |
| 1.6 | List effects | `python3 entropic.py list-effects --compact` | 109 effects, 10 categories | [ ] | |
| 1.7 | Packages CLI help | `python3 entropic_packages.py --help` | Shows commands | [ ] | |
| 1.8 | Packages list | `python3 entropic_packages.py list` | 7 packages | [ ] | |
| 1.9 | Existing tests pass | `python3 -m pytest tests/ -v` | All pass (312 expected) | [ ] | |

---

## SECTION 2: PROJECT MANAGEMENT

> **Goal:** Confirm projects can be created, listed, and inspected.
> **Time:** ~5 minutes

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 2.1 | Create project | `python3 entropic.py new uat-test --source test-videos/clips/YOURCLIP.mp4` | "Created project: uat-test" | [ ] | |
| 2.2 | Project dir exists | `ls ~/.entropic/projects/uat-test/` | source/, recipes/, renders/ | [ ] | |
| 2.3 | Source symlinked | `ls -la ~/.entropic/projects/uat-test/source/` | Symlink to clip | [ ] | |
| 2.4 | project.json valid | `cat ~/.entropic/projects/uat-test/project.json` | JSON with name, source, budget | [ ] | |
| 2.5 | List projects | `python3 entropic.py projects` | Shows "uat-test" | [ ] | |
| 2.6 | Project status | `python3 entropic.py status uat-test` | Name, source, 0 recipes | [ ] | |
| 2.7 | Duplicate blocked | `python3 entropic.py new uat-test --source test-videos/clips/YOURCLIP.mp4` | Error: already exists | [ ] | |

---

## SECTION 3: INDIVIDUAL EFFECTS (Original Workflow)

> **Goal:** Every effect produces visible output and doesn't crash.
> **Time:** ~30 minutes (37 effects)
> **Method:** Apply each effect, confirm a lo-res preview renders and opens.

### 3A. Glitch Effects (4)

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 3.1 | pixelsort | `python3 entropic.py apply uat-test --effect pixelsort` | Sorted pixel streaks | [ ] | |
| 3.2 | channelshift | `python3 entropic.py apply uat-test --effect channelshift` | RGB offset visible | [ ] | |
| 3.3 | displacement | `python3 entropic.py apply uat-test --effect displacement` | Block displacement | [ ] | |
| 3.4 | bitcrush | `python3 entropic.py apply uat-test --effect bitcrush` | Reduced colors | [ ] | |

### 3B. Distortion Effects (3)

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 3.5 | wave | `python3 entropic.py apply uat-test --effect wave` | Wavy distortion | [ ] | |
| 3.6 | mirror | `python3 entropic.py apply uat-test --effect mirror` | Symmetrical image | [ ] | |
| 3.7 | chromatic | `python3 entropic.py apply uat-test --effect chromatic` | RGB edge fringing | [ ] | |

### 3C. Texture Effects (7)

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 3.8 | scanlines | `python3 entropic.py apply uat-test --effect scanlines` | Horizontal lines | [ ] | |
| 3.9 | vhs | `python3 entropic.py apply uat-test --effect vhs` | VHS degradation | [ ] | |
| 3.10 | noise | `python3 entropic.py apply uat-test --effect noise` | Grain overlay | [ ] | |
| 3.11 | blur | `python3 entropic.py apply uat-test --effect blur` | Soft/blurred | [ ] | |
| 3.12 | sharpen | `python3 entropic.py apply uat-test --effect sharpen` | Crisper edges | [ ] | |
| 3.13 | edges | `python3 entropic.py apply uat-test --effect edges` | Edge lines visible | [ ] | |
| 3.14 | posterize | `python3 entropic.py apply uat-test --effect posterize` | Fewer color levels | [ ] | |

### 3D. Color Effects (6)

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 3.15 | hueshift | `python3 entropic.py apply uat-test --effect hueshift` | Colors rotated | [ ] | |
| 3.16 | contrast | `python3 entropic.py apply uat-test --effect contrast` | Higher contrast | [ ] | |
| 3.17 | saturation | `python3 entropic.py apply uat-test --effect saturation` | More vivid | [ ] | |
| 3.18 | exposure | `python3 entropic.py apply uat-test --effect exposure` | Brighter | [ ] | |
| 3.19 | invert | `python3 entropic.py apply uat-test --effect invert` | Negative image | [ ] | |
| 3.20 | temperature | `python3 entropic.py apply uat-test --effect temperature` | Warmer tones | [ ] | |

### 3E. Temporal Effects (9)

> **Important:** Temporal effects need VIDEO playback to see. A single frame may look normal.

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 3.21 | stutter | `python3 entropic.py apply uat-test --effect stutter` | Repeating frames | [ ] | |
| 3.22 | dropout | `python3 entropic.py apply uat-test --effect dropout` | Random black frames | [ ] | |
| 3.23 | timestretch | `python3 entropic.py apply uat-test --effect timestretch` | Slowed playback | [ ] | |
| 3.24 | feedback | `python3 entropic.py apply uat-test --effect feedback` | Ghost trails | [ ] | |
| 3.25 | tapestop | `python3 entropic.py apply uat-test --effect tapestop` | Freeze + fade | [ ] | |
| 3.26 | tremolo | `python3 entropic.py apply uat-test --effect tremolo` | Brightness pulsing | [ ] | |
| 3.27 | delay | `python3 entropic.py apply uat-test --effect delay` | Echo ghosts | [ ] | |
| 3.28 | decimator | `python3 entropic.py apply uat-test --effect decimator` | Choppy motion | [ ] | |
| 3.29 | samplehold | `python3 entropic.py apply uat-test --effect samplehold` | Random freezes | [ ] | |

### 3F. Modulation Effects (2)

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 3.30 | ringmod | `python3 entropic.py apply uat-test --effect ringmod` | Sine wave bands | [ ] | |
| 3.31 | gate | `python3 entropic.py apply uat-test --effect gate` | Dark areas → black | [ ] | |

### 3G. Enhance Effects (6)

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 3.32 | solarize | `python3 entropic.py apply uat-test --effect solarize` | Partial inversion | [ ] | |
| 3.33 | duotone | `python3 entropic.py apply uat-test --effect duotone` | Two-color map | [ ] | |
| 3.34 | emboss | `python3 entropic.py apply uat-test --effect emboss` | 3D raised texture | [ ] | |
| 3.35 | autolevels | `python3 entropic.py apply uat-test --effect autolevels` | Better contrast | [ ] | |
| 3.36 | median | `python3 entropic.py apply uat-test --effect median` | Soft/painterly | [ ] | |
| 3.37 | falsecolor | `python3 entropic.py apply uat-test --effect falsecolor` | Heat map colors | [ ] | |

---

## SECTION 4: CUSTOM PARAMETERS

> **Goal:** Verify custom params override defaults correctly.
> **Time:** ~10 minutes

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 4.1 | Pixelsort threshold | `python3 entropic.py apply uat-test --effect pixelsort --params threshold=0.2` | More sorting (lower threshold = more pixels sort) | [ ] | |
| 4.2 | VHS heavy tracking | `python3 entropic.py apply uat-test --effect vhs --params tracking=0.9 noise_amount=0.5` | Very distorted VHS | [ ] | |
| 4.3 | Hueshift 90deg | `python3 entropic.py apply uat-test --effect hueshift --params degrees=90` | Colors shifted 90 degrees | [ ] | |
| 4.4 | Mix param (dry/wet) | `python3 entropic.py apply uat-test --effect pixelsort --params mix=0.3` | Subtle sort (30% wet) | [ ] | |
| 4.5 | Mix=0 (full dry) | `python3 entropic.py apply uat-test --effect invert --params mix=0.0` | Original (unchanged) | [ ] | |
| 4.6 | Tuple param | `python3 entropic.py apply uat-test --effect channelshift --params "r_offset=(20,0)"` | Large red offset | [ ] | |

---

## SECTION 5: RECIPE MANAGEMENT

> **Goal:** Recipes save, load, branch, and favorite correctly.
> **Time:** ~10 minutes

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 5.1 | History shows recipes | `python3 entropic.py history uat-test` | Lists all recipes created above | [ ] | |
| 5.2 | Recipe files exist | `ls ~/.entropic/projects/uat-test/recipes/*.json` | JSON files present | [ ] | |
| 5.3 | Preview single frame | `python3 entropic.py preview uat-test 001` | PNG opens in Preview.app | [ ] | |
| 5.4 | Branch recipe | `python3 entropic.py branch uat-test 001 --params threshold=0.8` | "Branched: NNN from 001" | [ ] | |
| 5.5 | Branch has parent | Check branched recipe JSON | `"parent": "001"` field set | [ ] | |
| 5.6 | Favorite toggle ON | `python3 entropic.py favorite uat-test 001` | "favorited" | [ ] | |
| 5.7 | Favorite toggle OFF | `python3 entropic.py favorite uat-test 001` | "unfavorited" | [ ] | |
| 5.8 | Named recipe | `python3 entropic.py apply uat-test --effect wave --name my-wave-test` | Recipe name = "my-wave-test" | [ ] | |

---

## SECTION 6: RENDERING QUALITY TIERS

> **Goal:** All 3 quality tiers produce valid output at correct resolution.
> **Time:** ~10 minutes

Pick any recipe ID from history (e.g., 001).

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 6.1 | Lo render | `python3 entropic.py render uat-test 001 --quality lo` | 480p MP4, small file | [ ] | |
| 6.2 | Mid render | `python3 entropic.py render uat-test 001 --quality mid` | 720p MP4, medium file | [ ] | |
| 6.3 | Hi render | `python3 entropic.py render uat-test 001 --quality hi` | Full-res MOV (ProRes) | [ ] | |
| 6.4 | Lo file exists | `ls ~/.entropic/projects/uat-test/renders/lo/` | .mp4 file present | [ ] | |
| 6.5 | Mid file exists | `ls ~/.entropic/projects/uat-test/renders/mid/` | .mp4 file present | [ ] | |
| 6.6 | Hi file exists | `ls ~/.entropic/projects/uat-test/renders/hi/` | .mov file present | [ ] | |
| 6.7 | Output plays in QuickTime | Double-click any render | Video plays correctly | [ ] | |

---

## SECTION 7: PACKAGES (Challenger Prototype)

> **Goal:** All 7 packages and 31 recipes render without errors.
> **Time:** ~20 minutes

### 7A. Package Exploration

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 7.1 | List all packages | `python3 entropic_packages.py list` | 7 packages shown | [ ] | |
| 7.2 | Explore analog-decay | `python3 entropic_packages.py explore analog-decay` | 4 recipes with effect chains | [ ] | |
| 7.3 | Explore digital-corruption | `python3 entropic_packages.py explore digital-corruption` | 4 recipes | [ ] | |
| 7.4 | Explore color-lab | `python3 entropic_packages.py explore color-lab` | 5 recipes | [ ] | |
| 7.5 | Explore temporal-chaos | `python3 entropic_packages.py explore temporal-chaos` | 5 recipes | [ ] | |
| 7.6 | Explore distortion-engine | `python3 entropic_packages.py explore distortion-engine` | 4 recipes | [ ] | |
| 7.7 | Explore enhancement-suite | `python3 entropic_packages.py explore enhancement-suite` | 5 recipes | [ ] | |
| 7.8 | Explore signal-processing | `python3 entropic_packages.py explore signal-processing` | 4 recipes | [ ] | |
| 7.9 | Invalid package | `python3 entropic_packages.py explore fake-package` | Error: unknown package | [ ] | |

### 7B. Single Recipe Apply (One Per Package)

| # | Package | Recipe | Command | Expected | Result | Notes |
|---|---------|--------|---------|----------|--------|-------|
| 7.10 | analog-decay | worn-tape | `python3 entropic_packages.py apply uat-test --package analog-decay --recipe worn-tape` | VHS look, renders + opens | [ ] | |
| 7.11 | digital-corruption | data-rot | `python3 entropic_packages.py apply uat-test --package digital-corruption --recipe data-rot` | Bitcrushed, posterized | [ ] | |
| 7.12 | color-lab | psychedelic | `python3 entropic_packages.py apply uat-test --package color-lab --recipe psychedelic` | Wild colors | [ ] | |
| 7.13 | temporal-chaos | echo-trail | `python3 entropic_packages.py apply uat-test --package temporal-chaos --recipe echo-trail` | Ghost trails | [ ] | |
| 7.14 | distortion-engine | earthquake | `python3 entropic_packages.py apply uat-test --package distortion-engine --recipe earthquake` | Heavy warping | [ ] | |
| 7.15 | enhancement-suite | neon-edges | `python3 entropic_packages.py apply uat-test --package enhancement-suite --recipe neon-edges` | Neon outlines | [ ] | |
| 7.16 | signal-processing | full-signal-chain | `python3 entropic_packages.py apply uat-test --package signal-processing --recipe full-signal-chain` | Ring mod + gate + scanlines | [ ] | |

### 7C. Batch (All Recipes in One Package)

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 7.17 | Batch analog-decay | `python3 entropic_packages.py batch uat-test --package analog-decay` | 4 renders, summary table | [ ] | |
| 7.18 | Batch results | Check output | "4 passed, 0 failed" | [ ] | |

### 7D. Full Matrix (If Time Allows)

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 7.19 | Full matrix | `python3 entropic_packages.py matrix uat-test` | 31 renders, summary table | [ ] | |
| 7.20 | Matrix results | Check output | "31 passed, 0 failed" (ideally) | [ ] | |

---

## SECTION 8: SEARCH AND DISCOVERY

> **Goal:** Effect search and info commands work.
> **Time:** ~3 minutes

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 8.1 | Search by name | `python3 entropic.py search pixel` | Finds pixelsort | [ ] | |
| 8.2 | Search by description | `python3 entropic.py search "noise"` | Finds noise, gate (noise gate) | [ ] | |
| 8.3 | No results | `python3 entropic.py search zzzzz` | "No effects matching" | [ ] | |
| 8.4 | Effect info | `python3 entropic.py info pixelsort` | Shows params, example | [ ] | |
| 8.5 | Unknown effect | `python3 entropic.py info doesnt-exist` | Error + fuzzy suggestion | [ ] | |
| 8.6 | Category filter | `python3 entropic.py list-effects --category temporal` | Only temporal effects (9) | [ ] | |

---

## SECTION 9: SAFETY GUARDS (Red Team)

> **Goal:** Entropic rejects bad inputs gracefully — no crashes, no data loss.
> **Time:** ~10 minutes

### 9A. File Safety

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 9.1 | Missing source | `python3 entropic.py new bad-test --source /nonexistent/video.mp4` | Error: file not found | [ ] | |
| 9.2 | Wrong extension | `python3 entropic.py new bad-test --source /etc/passwd` | Error: file type not allowed | [ ] | |
| 9.3 | Path traversal | `python3 entropic.py new bad-test --source ../../../../../../etc/passwd` | Error: path outside home | [ ] | |
| 9.4 | File too large | Create >500MB file, try to use | Error: exceeds limit | [ ] | SKIP if no large file |

### 9B. Effect Chain Safety

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 9.5 | Unknown effect name | `python3 entropic.py apply uat-test --effect DOESNT_EXIST` | Error: unknown effect | [ ] | |
| 9.6 | Chain depth limit | Apply recipe with 11+ effects | SafetyError: max 10 chain depth | [ ] | |
| 9.7 | Invalid param value | `python3 entropic.py apply uat-test --effect pixelsort --params threshold=NaN` | Error: NaN not allowed | [ ] | |
| 9.8 | Infinity param | `python3 entropic.py apply uat-test --effect exposure --params stops=inf` | Error: Inf not allowed | [ ] | |

### 9C. Resource Limits

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 9.9 | Frame limit (3000) | Use a very long video (if available) | Error: exceeds 3000 frames | [ ] | |
| 9.10 | Processing timeout | Set extremely heavy chain on long clip | Timeout after 5 minutes | [ ] | |
| 9.11 | Disk budget tracking | `python3 entropic.py status uat-test` | Shows MB used / 2.0GB budget | [ ] | |

### 9D. Input Sanitization

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 9.12 | Special chars in name | `python3 entropic.py new '../../../tmp/evil' --source clip.mp4` | Sanitized name (no path traversal) | [ ] | |
| 9.13 | Very long name | Use 200+ char project name | Truncated to 100 chars | [ ] | |

---

## SECTION 10: VISUAL QUALITY (Mad Scientist)

> **Goal:** Effects actually look different from each other and produce visually interesting results.
> **Time:** ~15 minutes
> **Method:** A/B comparison — compare original clip to processed output

### 10A. Intensity Gradients

Test that "light" recipes are visibly less intense than "heavy" recipes:

| # | Test | What to Compare | Expected | Result | Notes |
|---|------|----------------|----------|--------|-------|
| 10.1 | Analog light vs heavy | `light-wear` vs `destroyed-tape` | destroyed-tape MUCH more degraded | [ ] | |
| 10.2 | Digital light vs heavy | `minor-glitch` vs `full-corruption` | full-corruption way more broken | [ ] | |
| 10.3 | Warm vs cold | `warm-grade` vs `cold-grade` | Clearly opposite color temps | [ ] | |

### 10B. Effect Distinctiveness

| # | Test | What to Compare | Expected | Result | Notes |
|---|------|----------------|----------|--------|-------|
| 10.4 | VHS vs noise | Apply vhs, then noise separately | Different looks (VHS has tracking/bleed) | [ ] | |
| 10.5 | Pixelsort vs displacement | Apply each separately | Different looks (sort vs block shift) | [ ] | |
| 10.6 | Solarize vs invert | Apply each separately | Different (solarize = partial, invert = full) | [ ] | |

### 10C. Temporal Effects Are Temporal

| # | Test | What to Check | Expected | Result | Notes |
|---|------|--------------|----------|--------|-------|
| 10.7 | Stutter changes over time | Play stutter output | Not a static image — frames repeat/hold | [ ] | |
| 10.8 | Feedback builds | Play feedback output | Ghost trails increase with motion | [ ] | |
| 10.9 | Tapestop ends | Play tapestop output | Video freezes near end | [ ] | |

---

## SECTION 11: EDGE CASES (Lenny's Product Corner)

> **Goal:** Handle real-world usage patterns gracefully.
> **Time:** ~10 minutes

| # | Test | What to Do | Expected | Result | Notes |
|---|------|-----------|----------|--------|-------|
| 11.1 | Very short video (1-2s) | Create project with 1-2 second clip | Works, renders small output | [ ] | |
| 11.2 | No audio video | Use clip with `-an` (no audio) | Renders fine, no audio errors | [ ] | |
| 11.3 | Different formats | Test .mp4, .mov, .webm if available | All accepted | [ ] | |
| 11.4 | Apply to nonexistent project | `python3 entropic.py apply fake-project --effect pixelsort` | Clear error message | [ ] | |
| 11.5 | Preview nonexistent recipe | `python3 entropic.py preview uat-test 999` | Clear error message | [ ] | |
| 11.6 | Empty params list | `python3 entropic.py apply uat-test --effect wave --params` | Uses defaults, prints hint | [ ] | |
| 11.7 | Multiple projects | Create 2+ projects | Both work independently | [ ] | |

---

## SECTION 12: TEST CLIP EXTRACTION

> **Goal:** Verify the clip extraction script works on downloaded videos.
> **Time:** ~5 minutes (after copying videos)

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 12.1 | Copy videos | `cp -r ~/Documents/TrippyVisuals ~/Development/entropic/test-videos` | Files copied | [ ] | |
| 12.2 | Run extraction | `bash scripts/extract_test_clips.sh` | Clips created in test-videos/clips/ | [ ] | |
| 12.3 | Clips are 10s max | `ffprobe -v error -show_entries format=duration -of csv=p=0 test-videos/clips/ANYCLIP.mp4` | <=10 seconds | [ ] | |
| 12.4 | Clips are 640x480 max | `ffprobe -v error -show_entries stream=width,height -of csv=p=0 test-videos/clips/ANYCLIP.mp4` | <=640 wide, <=480 tall | [ ] | |
| 12.5 | Use clip as source | `python3 entropic.py new clip-test --source test-videos/clips/ANYCLIP.mp4` | Project created | [ ] | |

---

## SECTION 13: PIXEL PHYSICS (6 effects)

> **Goal:** All pixel physics effects produce visible displacement and accumulate over frames.
> **Time:** ~15 minutes
> **Method:** Apply each effect, verify displacement builds over time (not a static filter).

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 13.1 | pixelliquify | `python3 entropic.py apply uat-test --effect pixelliquify` | Fluid motion, pixels flow and wash | [ ] | |
| 13.2 | pixelgravity | `python3 entropic.py apply uat-test --effect pixelgravity` | Pixels pulled toward moving points | [ ] | |
| 13.3 | pixelvortex | `python3 entropic.py apply uat-test --effect pixelvortex` | Swirling whirlpool distortion | [ ] | |
| 13.4 | pixelexplode | `python3 entropic.py apply uat-test --effect pixelexplode` | Outward blast from center | [ ] | |
| 13.5 | pixelelastic | `python3 entropic.py apply uat-test --effect pixelelastic` | Stretchy jello-like bounce | [ ] | |
| 13.6 | pixelmelt | `python3 entropic.py apply uat-test --effect pixelmelt` | Downward dripping motion | [ ] | |

### 13B. Boundary Modes

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 13.7 | Wrap boundary | `python3 entropic.py apply uat-test --effect pixelliquify --params boundary=wrap` | Pixels wrap around edges (top↔bottom, left↔right) | [ ] | |
| 13.8 | Black boundary | `python3 entropic.py apply uat-test --effect pixelexplode --params boundary=black` | Black void where pixels leave frame | [ ] | |
| 13.9 | Mirror boundary | `python3 entropic.py apply uat-test --effect pixelelastic --params boundary=mirror` | Pixels reflect at edges | [ ] | |
| 13.10 | Clamp boundary | `python3 entropic.py apply uat-test --effect pixelmelt --params boundary=clamp` | Edge pixels stretch (smear) | [ ] | |

---

## SECTION 14: IMPOSSIBLE PHYSICS (10 effects)

> **Goal:** Impossible physics effects produce visually distinct, otherworldly results.
> **Time:** ~20 minutes

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 14.1 | pixelblackhole | `python3 entropic.py apply uat-test --effect pixelblackhole` | Singularity with accretion glow, spaghettification | [ ] | |
| 14.2 | pixelantigravity | `python3 entropic.py apply uat-test --effect pixelantigravity` | Pixels repulsed outward, oscillating | [ ] | |
| 14.3 | pixelmagnetic | `python3 entropic.py apply uat-test --effect pixelmagnetic` | Curved field line distortion | [ ] | |
| 14.4 | pixeltimewarp | `python3 entropic.py apply uat-test --effect pixeltimewarp` | Displacement reverses with echo ghosts | [ ] | |
| 14.5 | pixeldimensionfold | `python3 entropic.py apply uat-test --effect pixeldimensionfold` | Space folds over itself | [ ] | |
| 14.6 | pixelwormhole | `python3 entropic.py apply uat-test --effect pixelwormhole` | Portal distortion with tunneling | [ ] | |
| 14.7 | pixelquantum | `python3 entropic.py apply uat-test --effect pixelquantum` | Barrier tunneling + superposition ghosts | [ ] | |
| 14.8 | pixeldarkenergy | `python3 entropic.py apply uat-test --effect pixeldarkenergy` | Expanding void, pixel separation | [ ] | |
| 14.9 | pixelsuperfluid | `python3 entropic.py apply uat-test --effect pixelsuperfluid` | Zero-friction flow with glowing vortex cores | [ ] | |
| 14.10 | pixelbubbles | `python3 entropic.py apply uat-test --effect pixelbubbles` | Multiple bubble portals with void inside | [ ] | |

### 14B. Void Modes (Bubbles)

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 14.11 | Black void | `python3 entropic.py apply uat-test --effect pixelbubbles --params void_mode=black` | Black inside portals | [ ] | |
| 14.12 | White void | `python3 entropic.py apply uat-test --effect pixelbubbles --params void_mode=white` | White inside portals | [ ] | |
| 14.13 | Invert void | `python3 entropic.py apply uat-test --effect pixelbubbles --params void_mode=invert` | Inverted colors inside portals | [ ] | |

---

## SECTION 15: ORACLE-INSPIRED + PRINT DEGRADATION (5 effects)

> **Goal:** Art-theory-inspired and print simulation effects produce distinctive visuals.
> **Time:** ~15 minutes

### 15A. Oracle-Inspired

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 15.1 | pixelinkdrop | `python3 entropic.py apply uat-test --effect pixelinkdrop` | Paint drops expanding in water with tendrils | [ ] | |
| 15.2 | inkdrop soap | `python3 entropic.py apply uat-test --effect pixelinkdrop --params marangoni=5.0 tendrils=12` | Pronounced Marangoni finger instabilities | [ ] | |
| 15.3 | pixelhaunt | `python3 entropic.py apply uat-test --effect pixelhaunt` | Ghostly afterimages with crackle noise | [ ] | |
| 15.4 | haunt radial | `python3 entropic.py apply uat-test --effect pixelhaunt --params force_type=radial` | Radial ghost pattern, different from turbulence | [ ] | |

### 15B. Print Degradation

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 15.5 | pixelxerox | `python3 entropic.py apply uat-test --effect pixelxerox` | Progressive copy degradation (contrast, noise, halftone) | [ ] | |
| 15.6 | xerox heavy | `python3 entropic.py apply uat-test --effect pixelxerox --params generations=20 toner_skip=0.1` | Heavily degraded, near B&W with toner gaps | [ ] | |
| 15.7 | pixelfax | `python3 entropic.py apply uat-test --effect pixelfax` | Monochrome fax with dither, warm paper tone | [ ] | |
| 15.8 | fax no-dither | `python3 entropic.py apply uat-test --effect pixelfax --params dither=False` | Continuous-tone grayscale fax (no halftone) | [ ] | |
| 15.9 | pixelrisograph | `python3 entropic.py apply uat-test --effect pixelrisograph` | Blue+red riso print with ink bleed and misregistration | [ ] | |
| 15.10 | riso 3-color | `python3 entropic.py apply uat-test --effect pixelrisograph --params num_colors=3 registration_offset=5` | 3-layer riso with visible misalignment | [ ] | |

---

## SECTION 16: DSP FILTERS (12 effects)

> **Goal:** Audio DSP-inspired video filters produce visible modulation effects.
> **Time:** ~15 minutes

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 16.1 | videoflanger | `python3 entropic.py apply uat-test --effect videoflanger` | Temporal interference pattern | [ ] | |
| 16.2 | videophaser | `python3 entropic.py apply uat-test --effect videophaser` | Sweeping notch pattern | [ ] | |
| 16.3 | spatialflanger | `python3 entropic.py apply uat-test --effect spatialflanger` | Diagonal sweep flanging | [ ] | |
| 16.4 | channelphaser | `python3 entropic.py apply uat-test --effect channelphaser` | Color fringing/tearing | [ ] | |
| 16.5 | brightnessphaser | `python3 entropic.py apply uat-test --effect brightnessphaser` | Psychedelic solarization sweep | [ ] | |
| 16.6 | hueflanger | `python3 entropic.py apply uat-test --effect hueflanger` | Color interference oscillation | [ ] | |
| 16.7 | resonantfilter | `python3 entropic.py apply uat-test --effect resonantfilter` | Synth filter sweep on video | [ ] | |
| 16.8 | combfilter | `python3 entropic.py apply uat-test --effect combfilter` | Multi-tooth interference | [ ] | |
| 16.9 | feedbackphaser | `python3 entropic.py apply uat-test --effect feedbackphaser` | Self-oscillation build-up | [ ] | |
| 16.10 | spectralfreeze | `python3 entropic.py apply uat-test --effect spectralfreeze` | Spectral imprint at intervals | [ ] | |
| 16.11 | visualreverb | `python3 entropic.py apply uat-test --effect visualreverb` | Visual echo/room convolution | [ ] | |
| 16.12 | freqflanger | `python3 entropic.py apply uat-test --effect freqflanger` | Spectral ghosting | [ ] | |

---

## SECTION 17: SIDECHAIN EFFECTS (6 effects)

> **Goal:** Sidechain effects respond to internal signal or cross-video input.
> **Time:** ~10 minutes
> **Note:** Cross-video effects (sidechaincross, crossfeed, interference) need two input videos.

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 17.1 | sidechainduck | `python3 entropic.py apply uat-test --effect sidechainduck` | Brightness ducks on signal | [ ] | |
| 17.2 | sidechainpump | `python3 entropic.py apply uat-test --effect sidechainpump` | Rhythmic 4-on-floor ducking | [ ] | |
| 17.3 | sidechaingate | `python3 entropic.py apply uat-test --effect sidechaingate` | Video gates on/off by signal | [ ] | |
| 17.4 | sidechaincross | Requires 2 videos — see sidechain docs | One video busts through another | [ ] | |
| 17.5 | sidechaincrossfeed | Requires 2 videos — see sidechain docs | Channel mixing between videos | [ ] | |
| 17.6 | sidechaininterference | Requires 2 videos — see sidechain docs | Phase/amplitude interference | [ ] | |

---

## PRIORITY ORDER

If you're short on time, test in this order:

1. **Section 1** (Smoke) — if this fails, stop here
2. **Section 18** (Desktop App) — app must boot
3. **Section 9** (Safety) — security issues are blockers
4. **Section 20A-20B** (Timeline renders) — new feature core
5. **Section 19A-19C** (Video, Browser, Chain) — existing UI works
6. **Section 7B** (One recipe per package) — validates packages work
7. **Section 3** (Individual effects) — the core product
8. Everything else

---

## KNOWN ISSUES / WATCH FOR

- **Temporal effects on single frames:** stutter, feedback, delay, etc. need multi-frame video to show their effect. A single-frame preview will look unchanged. Test by playing the rendered VIDEO, not by looking at a preview PNG.
- **Color tuple params in CLI:** Use quotes around tuples like `"r_offset=(20,0)"` — shells can interpret parentheses.
- **macOS auto-open:** After `apply`, the rendered video auto-opens in your default player. If too many renders pile up, close them periodically.
- **Disk usage:** Each rendered video takes 1-10MB at lo quality. The `matrix` command (7.19) will create ~31 renders. Check `status` afterward.

---

## SECTION 18: DESKTOP APP (Boot + PyWebView)

> **Goal:** The .app bundle launches, PyWebView window renders, server starts cleanly.
> **Time:** ~10 minutes
> **Setup:** `cd ~/Development/entropic && python3 server.py` OR launch Entropic.app from DMG

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 18.1 | Server starts | Run `python3 server.py` | "Uvicorn running on http://0.0.0.0:7860" | [ ] | |
| 18.2 | Web UI loads | Open http://localhost:7860 in browser | 4-panel DAW layout visible, topbar + browser + canvas + chain | [ ] | |
| 18.3 | Boot screen | First load shows boot animation | Logo, "Loading effects...", then fades to main UI | [ ] | |
| 18.4 | Effect count | Check browser panel | All 109 effects listed in 10 categories | [ ] | |
| 18.5 | No console errors | Open browser DevTools → Console | Zero JS errors on load | [ ] | |
| 18.6 | Responsive resize | Resize browser window from 1280px down to 900px | Layout adapts, no overlapping panels | [ ] | |
| 18.7 | Dark theme | Visual check | Dark background, light text, accent color visible | [ ] | |

---

## SECTION 19: UI CORE (Browser, Canvas, Chain, Layers)

> **Goal:** All 4 panels of the DAW layout function correctly in Quick mode.
> **Time:** ~20 minutes
> **Prereq:** Server running, browser open

### 19A. Video Loading

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 19.1 | Upload video | Click upload area or drag .mp4 file onto canvas | Video loads, first frame shown on canvas | [ ] | |
| 19.2 | File name shows | After upload | Filename appears in topbar | [ ] | |
| 19.3 | Frame slider works | Drag the frame scrubber slider | Canvas updates to different frames | [ ] | |
| 19.4 | Frame counter | Move slider | Frame number updates in real time | [ ] | |

### 19B. Effect Browser

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 19.5 | Category collapse | Click category header in browser | Category toggles open/closed | [ ] | |
| 19.6 | Search effects | Type in search field | Effects filter in real-time | [ ] | |
| 19.7 | Add effect (click) | Click an effect name in browser | Effect appears in chain rack | [ ] | |
| 19.8 | Add effect (drag) | Drag effect from browser to chain | Effect added at drop position | [ ] | |

### 19C. Chain Rack

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 19.9 | Effect shows params | Click effect in chain | Knobs/sliders appear for parameters | [ ] | |
| 19.10 | Adjust parameter | Turn a knob or move slider | Value changes, preview updates | [ ] | |
| 19.11 | Bypass effect | Click bypass button on effect | Effect grayed out, preview updates (effect removed) | [ ] | |
| 19.12 | Remove effect | Click X or right-click → Remove | Effect removed from chain | [ ] | |
| 19.13 | Reorder effects | Drag effect to new position in chain | Order changes, preview updates | [ ] | |
| 19.14 | Clear all | Right-click → Clear All | All effects removed | [ ] | |
| 19.15 | Duplicate effect | Right-click → Duplicate | Copy of effect added after original | [ ] | |

### 19D. Preview & Canvas

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 19.16 | Live preview | Add effect with video loaded | Canvas shows processed frame | [ ] | |
| 19.17 | A/B compare | Press Space (in Quick mode) | Toggles between original and processed | [ ] | |
| 19.18 | Mix slider | Adjust dry/wet mix | Blend between original and processed | [ ] | |
| 19.19 | Preview debounce | Rapidly adjust a knob | Preview updates after brief pause (not on every pixel) | [ ] | |

### 19E. Layers / History

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 19.20 | History tracks changes | Add/remove/reorder effects | History panel shows each action | [ ] | |
| 19.21 | Undo (Cmd+Z) | After adding effect | Effect removed, history updated | [ ] | |
| 19.22 | Redo (Cmd+Shift+Z) | After undo | Effect restored | [ ] | |
| 19.23 | Layers list | Add 3+ effects | All visible in layers panel | [ ] | |

### 19F. Export (Quick Mode)

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 19.24 | Export button | Click Export with video + effects | Export dialog appears | [ ] | |
| 19.25 | Format selection | Choose MP4, MOV, GIF, WebM | Format accepted | [ ] | |
| 19.26 | Export completes | Start export | Progress bar → "Export complete" toast | [ ] | |
| 19.27 | Output plays | Open exported file | Correct effects applied, video plays | [ ] | |

### 19G. Keyboard Shortcuts (Quick Mode)

| # | Test | Key | Expected | Result | Notes |
|---|------|-----|----------|--------|-------|
| 19.28 | Undo | `Cmd+Z` | Undo last action | [ ] | |
| 19.29 | Redo | `Cmd+Shift+Z` | Redo last undo | [ ] | |
| 19.30 | A/B compare | `Space` | Toggle original/processed | [ ] | |
| 19.31 | Shortcut overlay | `?` | Shows shortcut reference card | [ ] | |
| 19.32 | Navigate frames | `Left/Right arrow` | Move frame by frame | [ ] | |
| 19.33 | Jump 10 frames | `Shift+Left/Right` | Move 10 frames | [ ] | |

---

## SECTION 20: TIMELINE EDITOR

> **Goal:** Timeline mode adds canvas-based timeline with tracks, regions, playhead, I/O markers, zoom, and spatial masks.
> **Time:** ~30 minutes
> **Prereq:** Video loaded, server running
> **Branch:** `feature/timeline-editor` (must be checked out)

### 20A. Mode Switching

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 20.1 | Default is Quick | Load app fresh | "Quick" button highlighted, no timeline visible | [ ] | |
| 20.2 | Switch to Timeline | Click "Timeline" button in topbar | Timeline panel appears below canvas, grid becomes 4 rows | [ ] | |
| 20.3 | Switch back to Quick | Click "Quick" button | Timeline hides, grid back to 3 rows | [ ] | |
| 20.4 | Frame scrubber hidden | In Timeline mode | Range slider above canvas is hidden (playhead replaces it) | [ ] | |
| 20.5 | Frame scrubber visible | In Quick mode | Range slider visible and functional | [ ] | |
| 20.6 | Existing features intact | Switch back to Quick, test A/B, effects | Everything works as before | [ ] | |

### 20B. Timeline Canvas Rendering

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 20.7 | Time ruler visible | Switch to Timeline with video loaded | Top of timeline shows frame/second markers | [ ] | |
| 20.8 | Track visible | Default "Video 1" track | Track lane with header showing name | [ ] | |
| 20.9 | Full-length region | Auto-created when video loads | Region spanning entire video on Video 1 | [ ] | |
| 20.10 | Playhead renders | Red vertical line at frame 0 | Visible on timeline | [ ] | |
| 20.11 | Click moves playhead | Click anywhere on timeline body | Playhead jumps to that frame | [ ] | |
| 20.12 | Playhead syncs canvas | Move playhead by clicking | Canvas updates to show that frame | [ ] | |
| 20.13 | Arrow keys sync | Press Left/Right in timeline mode | Both timeline playhead and canvas update | [ ] | |

### 20C. Zoom & Scroll

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 20.14 | Zoom in (+) | Click + button or press `+` key | Ruler spreads out, more detail | [ ] | |
| 20.15 | Zoom out (-) | Click - button or press `-` key | Ruler compresses, see more frames | [ ] | |
| 20.16 | Fit to window | Click Fit button or `Cmd+0` | All frames visible in timeline width | [ ] | |
| 20.17 | Mouse wheel zoom | Scroll wheel on timeline | Zooms in/out smoothly | [ ] | |
| 20.18 | Horizontal scroll | Shift+scroll or scroll when zoomed in | Timeline pans left/right | [ ] | |
| 20.19 | Playhead stays centered | Zoom in/out | View adjusts to keep playhead visible | [ ] | |

### 20D. I/O Markers

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 20.20 | Set in-point | Move playhead to frame 30, press `I` | Green marker appears at frame 30, toast "In: 30" | [ ] | |
| 20.21 | Set out-point | Move playhead to frame 90, press `O` | Red marker appears at frame 90, toast "Out: 90" | [ ] | |
| 20.22 | Markers visible | After setting I and O | Both markers render on timeline ruler | [ ] | |
| 20.23 | Range highlighted | Between I and O | Shaded region between the two markers | [ ] | |

### 20E. Region Management

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 20.24 | Create region from I/O | Set I at 30, O at 90, press `Cmd+R` | Region [30-90] appears on Video 1, toast "Region created" | [ ] | |
| 20.25 | Region renders | After creation | Colored rectangle on track between frame 30-90 | [ ] | |
| 20.26 | Click selects region | Click on the region | Region highlights, chain rack updates | [ ] | |
| 20.27 | New region = empty chain | Click newly created region | Chain rack is empty (no effects yet) | [ ] | |
| 20.28 | Add effects to region | With region selected, add effects from browser | Effects appear in chain rack | [ ] | |
| 20.29 | Region stores effects | Click away, click back on region | Same effects reload in chain rack | [ ] | |
| 20.30 | Double-click renames | Double-click region on timeline | Prompt appears, type new name, label updates | [ ] | |
| 20.31 | Drag to move region | Click and drag region body | Region moves to new time position | [ ] | |
| 20.32 | Drag to resize (left) | Drag left edge of region | Start frame changes, region shrinks/grows | [ ] | |
| 20.33 | Drag to resize (right) | Drag right edge of region | End frame changes | [ ] | |
| 20.34 | Delete region | Select region, press `Delete` | Region removed, toast confirms | [ ] | |
| 20.35 | Multiple regions | Create 3+ regions at different time ranges | All visible on timeline, independently selectable | [ ] | |

### 20F. Per-Region Effects

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 20.36 | Region A effects | Select Region A, add pixelsort | Pixelsort in chain | [ ] | |
| 20.37 | Region B effects | Select Region B, add vhs | VHS in chain (pixelsort gone) | [ ] | |
| 20.38 | Switch back to A | Click Region A | Pixelsort reloads in chain | [ ] | |
| 20.39 | Preview inside region | Move playhead to frame inside Region A | Canvas shows pixelsort-processed frame | [ ] | |
| 20.40 | Preview outside region | Move playhead to frame outside any region | Canvas shows original unprocessed frame | [ ] | |
| 20.41 | Bypass persists | Bypass an effect in Region A, switch away, switch back | Bypass state preserved | [ ] | |

### 20G. Spatial Masks (Photoshop-style Selection)

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 20.42 | Draw mask | Alt+click-drag on canvas | Red dashed rectangle appears on canvas | [ ] | |
| 20.43 | Mask overlay visible | After drawing | Semi-transparent overlay shows masked area | [ ] | |
| 20.44 | Mask stored on region | Draw mask, click away, click region back | Mask overlay reappears at same position | [ ] | |
| 20.45 | Masked preview | Add effect with mask set, move playhead to region | Only masked area shows effect, rest is original | [ ] | |
| 20.46 | Clear mask | Press `Cmd+Shift+M` or clear mask button | Mask removed, full frame processes | [ ] | |
| 20.47 | Mask persists on resize | Resize browser window | Mask scales proportionally (stored as 0-1 ratios) | [ ] | |
| 20.48 | Different masks per region | Region A: top-left mask, Region B: bottom-right mask | Each region shows its own mask when selected | [ ] | |

### 20H. Track Controls

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 20.49 | Mute track | Press `M` with track selected | Track header shows "M", regions dimmed | [ ] | |
| 20.50 | Muted preview | Move playhead into muted track's region | Preview shows original (no effects) | [ ] | |
| 20.51 | Solo track | Press `S` | Track header shows "S" | [ ] | |
| 20.52 | Unmute all | Press `Shift+M` | All tracks unmuted | [ ] | |

### 20I. Playback

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 20.53 | Play/pause | Press `Space` in Timeline mode | Playhead advances frame by frame, canvas updates | [ ] | |
| 20.54 | Stop resets | Press `Space` again | Playback pauses at current frame | [ ] | |
| 20.55 | Home key | Press `Home` | Playhead jumps to frame 0 | [ ] | |
| 20.56 | End key | Press `End` | Playhead jumps to last frame | [ ] | |

---

## SECTION 21: TIMELINE EXPORT & PROJECTS

> **Goal:** Timeline-aware export processes per-region effects. Projects save/load correctly.
> **Time:** ~15 minutes

### 21A. Timeline Export

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 21.1 | Export with regions | Create 2 regions with different effects, click Export | Export starts with timeline data | [ ] | |
| 21.2 | Region A processed | Play exported video at Region A's time range | Region A's effects visible | [ ] | |
| 21.3 | Region B processed | Play exported video at Region B's time range | Region B's (different) effects visible | [ ] | |
| 21.4 | Gap = original | Play exported video between regions | Original unprocessed frames | [ ] | |
| 21.5 | Muted region skipped | Mute one track, export | Muted region's effects not applied | [ ] | |
| 21.6 | Spatial mask in export | Region with mask, export | Only masked area has effects in output | [ ] | |
| 21.7 | Quick mode export | Switch to Quick mode, export | Flat chain applied to all frames (existing behavior) | [ ] | |

### 21B. Project Save/Load

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 21.8 | Save project | Press `Cmd+S` in Timeline mode | Prompt for name, saves .entropic file, toast confirms | [ ] | |
| 21.9 | File created | Check `~/Documents/Entropic Projects/` | `.entropic` JSON file present | [ ] | |
| 21.10 | File contents valid | Open .entropic file in text editor | Valid JSON with tracks, regions, effects, playhead, zoom | [ ] | |
| 21.11 | Load project | Press `Cmd+O` in Timeline mode | File picker or list of saved projects | [ ] | |
| 21.12 | State restored | After loading | Timeline shows same tracks, regions, effects, playhead position | [ ] | |
| 21.13 | Effects restored | Click a region after load | Same effects appear in chain rack | [ ] | |
| 21.14 | Mask restored | Region with spatial mask after load | Mask overlay appears at correct position | [ ] | |
| 21.15 | Cross-session | Close browser, reopen, load project | Everything matches original save | [ ] | |

---

---

## SECTION 22: PERFORMANCE MODE — LAUNCH & DISPLAY

> **Goal:** Performance mode boots, pygame window renders, layers initialize.
> **Time:** ~5 minutes
> **Setup:** `cd ~/Development/entropic && python entropic_perform.py --base YOUR_VIDEO.mp4`

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 22.1 | Basic launch | `python entropic_perform.py --base video.mp4` | Pygame window opens (~960x540), 4 layers in console, HUD shows [BUF] | [ ] | |
| 22.2 | No video file | `python entropic_perform.py --base nonexistent.mp4` | "ERROR: Video not found" per layer, no crash | [ ] | |
| 22.3 | No args | `python entropic_perform.py` | "Error: --base or --config required", exits | [ ] | |
| 22.4 | Custom layer count | `python entropic_perform.py --base video.mp4 --layers 2` | Only 2 layers in console + HUD | [ ] | |
| 22.5 | Custom FPS | `python entropic_perform.py --base video.mp4 --fps 24` | Plays at ~24fps (check HUD counter speed) | [ ] | |
| 22.6 | HUD elements | Look at pygame window | Bottom-left: frame counter + time. Top-left: [BUF]. Left: layer list | [ ] | |

---

## SECTION 23: PERFORMANCE MODE — KEYBOARD CONTROLS

> **Goal:** All keyboard shortcuts work correctly, safety measures prevent accidents.
> **Time:** ~10 minutes

### 23A. Basic Controls

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 23.1 | Play/Pause | Press **Space** | [PAUSED] → video freezes. Again → [PLAYING] | [ ] | |
| 23.2 | Layer 1 toggle | Press **1** | "Layer 0 (Clean): ON/OFF", HUD updates | [ ] | |
| 23.3 | Layer 2 toggle | Press **2** | "Layer 1 (VHS+Glitch): ON", visual changes | [ ] | |
| 23.4 | Layer 3 toggle | Press **3** | "Layer 2 (PixelSort): ON", visual changes | [ ] | |
| 23.5 | Layer 4 toggle | Press **4** | "Layer 3 (Feedback): ON", visual changes | [ ] | |
| 23.6 | Invalid layer (9) | Press **9** | Nothing happens (no crash) | [ ] | |
| 23.7 | Multiple layers | Press **2**, **3**, **4** | All show ON in HUD, visuals compound | [ ] | |

### 23B. Safety Controls (Don Norman)

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 23.8 | P alone = nothing | Press **P** (no modifier) | Nothing. No panic. No output | [ ] | |
| 23.9 | Shift+P = Panic | Turn on layers, press **Shift+P** | "[PANIC] All layers reset", all OFF | [ ] | |
| 23.10 | Q alone = nothing | Press **Q** (no modifier) | Nothing. App stays open | [ ] | |
| 23.11 | Shift+Q = Quit | Press **Shift+Q** | Clean exit to terminal | [ ] | |
| 23.12 | Esc single tap | Press **Esc** once | "[Press Esc again to exit]", stays open | [ ] | |
| 23.13 | Esc double (fast) | **Esc** twice within 0.5s | App closes cleanly | [ ] | |
| 23.14 | Esc double (slow) | **Esc**, wait 2s, **Esc** | Second shows warning again. App stays | [ ] | |

---

## SECTION 24: PERFORMANCE MODE — RECORDING & BUFFER

> **Goal:** Buffer captures events, user controls save/discard, re-arm clears buffer.
> **Time:** ~10 minutes

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 24.1 | Buffer indicator | Launch, check HUD | [BUF] in gray top-left | [ ] | |
| 24.2 | Arm recording | Press **R** | "[REC ON] Buffer cleared... (gen 1)". HUD: [REC] red | [ ] | |
| 24.3 | Disarm recording | Press **R** again | "[REC OFF] (buffer retained)". HUD: [BUF] gray | [ ] | |
| 24.4 | Re-arm clears buffer | Trigger layers → R (arm) → trigger → R (off) → R (arm) | "gen 2" — buffer cleared, fresh | [ ] | |
| 24.5 | Exit armed = auto-save | Arm R, trigger layers, **Shift+Q** | Auto-saves perf_TIMESTAMP.json + .layers.json | [ ] | |
| 24.6 | Exit unarmed — keep | Don't press R, trigger layers, **Shift+Q** | "Save buffer? [y/N]:" → **y** saves | [ ] | |
| 24.7 | Exit unarmed — discard | Don't press R, trigger layers, **Shift+Q** | "Save buffer? [y/N]:" → **n** → "Buffer discarded." | [ ] | |
| 24.8 | No events = no prompt | Launch, immediately **Shift+Q** | "No events captured." No save prompt | [ ] | |

---

## SECTION 25: PERFORMANCE MODE — MIDI

> **Goal:** MIDI controllers trigger layers and control opacity.
> **Time:** ~10 minutes
> **Skip if:** No MIDI controller available

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 25.1 | List devices | `python entropic_perform.py --midi-list` | Lists ports. No crash if none | [ ] | |
| 25.2 | MIDI learn | `--base video.mp4 --midi-learn` | Prints all incoming MIDI messages | [ ] | |
| 25.3 | Launchpad trigger | `--midi 0`, hit pad (note 36) | Layer 0 ON. Console confirms | [ ] | |
| 25.4 | MIDI Mix fader | Move fader 1 (CC 16) | Opacity changes. HUD % updates | [ ] | |
| 25.5 | Note off (gate) | Gate mode layer, hold pad, release | ON while held, OFF on release | [ ] | |
| 25.6 | No MIDI fallback | `--base video.mp4 --midi 99` | "MIDI init failed", keyboard still works | [ ] | |

---

## SECTION 26: PERFORMANCE MODE — TRIGGER MODES & VISUALS

> **Goal:** All 4 trigger modes work, effects visible, compositing correct.
> **Time:** ~10 minutes

### 26A. Trigger Modes

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 26.1 | Always On (L0) | Launch, check L0 | Clean layer always visible, can't toggle off | [ ] | |
| 26.2 | Toggle (L1) | Press **2** | ON stays until pressed again → OFF | [ ] | |
| 26.3 | ADSR Pluck (L2) | Press **3** | Quick attack, fast decay, 80% sustain | [ ] | |
| 26.4 | ADSR Stab (L3) | Press **4** | Instant attack, zero sustain (auto-fades) | [ ] | |

### 26B. Visual Quality

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 26.5 | Preview resolution | Check window size | ~960x540 | [ ] | |
| 26.6 | Smooth playback | Watch 10 seconds | ~30fps, no stutter | [ ] | |
| 26.7 | VHS visible | Toggle L2 ON | Noise + tracking artifacts | [ ] | |
| 26.8 | PixelSort visible | Toggle L3 ON | Horizontal bands/streaks | [ ] | |
| 26.9 | Feedback visible | Toggle L4 ON | Ghosting/trails | [ ] | |
| 26.10 | Layer compositing | Turn on L2 + L3 | Both effects blended together | [ ] | |

---

## SECTION 27: PERFORMANCE MODE — RENDER & STABILITY

> **Goal:** Offline render produces valid output, system stable for 30-min sets.
> **Time:** ~20 minutes

### 27A. Offline Render

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 27.1 | Render from automation | `--render --automation perf_TIMESTAMP.json -o test.mp4` | Progress → creates test.mp4 | [ ] | |
| 27.2 | Render with audio | `--render --automation perf.json --audio video.mp4 -o test_audio.mp4` | Output has video + audio | [ ] | |
| 27.3 | Render with duration | Add `--duration 10` | Only 10 seconds (300 frames) | [ ] | |
| 27.4 | Companion config | .layers.json next to .json, no --config | "Using companion config" | [ ] | |
| 27.5 | Missing automation | `--render --automation nonexistent.json` | Error, clean exit | [ ] | |
| 27.6 | Output plays | Open in VLC/QuickTime | Effects match live preview | [ ] | |

### 27B. Stability (30-Minute Stress)

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 27.7 | Long playback (5 min) | Play without interaction for 5+ min | No crash, stable memory, video loops | [ ] | |
| 27.8 | Rapid triggering | Rapidly press 1-4 for 30 seconds | No crash, layers toggle correctly | [ ] | |
| 27.9 | caffeinate running | Check Activity Monitor | caffeinate visible while running, gone after quit | [ ] | |
| 27.10 | Clean exit | **Shift+Q** after any test | No zombie FFmpeg (`ps aux \| grep ffmpeg`) | [ ] | |
| 27.11 | Ctrl+C interrupt | Press Ctrl+C during performance | "[INTERRUPTED]", clean exit | [ ] | |

### 27C. Edge Cases

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 27.12 | Very short video (<2s) | Use 1-second MP4 | Video loops, no crash | [ ] | |
| 27.13 | Large video (1080p+) | Use 1080p or 4K MP4 | Preview scales to 480p, acceptable FPS | [ ] | |
| 27.14 | Pause + trigger | Pause, toggle layers, unpause | Layers take effect on unpause | [ ] | |
| 27.15 | All layers off | Turn off all toggleable layers | Black screen, HUD visible, no crash | [ ] | |

---

## UPDATED SCORING SUMMARY

| Section | Tests | Pass | Fail | Skip |
|---------|-------|------|------|------|
| 1. Smoke Tests | 9 | | | |
| 2. Project Management | 7 | | | |
| 3. Individual Effects | 37 | | | |
| 4. Custom Parameters | 6 | | | |
| 5. Recipe Management | 8 | | | |
| 6. Rendering Tiers | 7 | | | |
| 7. Packages | 20 | | | |
| 8. Search & Discovery | 6 | | | |
| 9. Safety Guards | 13 | | | |
| 10. Visual Quality | 9 | | | |
| 11. Edge Cases | 7 | | | |
| 12. Clip Extraction | 5 | | | |
| 13. Pixel Physics | 10 | | | |
| 14. Impossible Physics | 13 | | | |
| 15. Oracle + Print | 10 | | | |
| 16. DSP Filters | 12 | | | |
| 17. Sidechain | 6 | | | |
| 18. Desktop App | 7 | | | |
| 19. UI Core | 33 | | | |
| 20. Timeline Editor | 56 | | | |
| 21. Timeline Export/Projects | 15 | | | |
| **22. Perform: Launch** | **6** | | | |
| **23. Perform: Keyboard** | **14** | | | |
| **24. Perform: Recording** | **8** | | | |
| **25. Perform: MIDI** | **6** | | | |
| **26. Perform: Triggers/Visuals** | **10** | | | |
| **27. Perform: Render/Stability** | **15** | | | |
| **TOTAL** | **355** | | | |

**Ship criteria:**
- **CLI (Sections 1-17):** 90%+ pass rate (167+ of 185), zero critical failures in Sections 1, 2, 9
- **Desktop App (Section 18):** 100% pass (7/7) — app must boot
- **UI Core (Section 19):** 90%+ pass rate (30+ of 33)
- **Timeline (Section 20):** 85%+ pass rate (48+ of 56) — new feature, some polish acceptable
- **Timeline Export/Projects (Section 21):** 90%+ pass rate (14+ of 15)
- **Performance Mode (Sections 22-27):** 90%+ pass rate (53+ of 59), zero failures in 23B (safety) and 27B (stability)

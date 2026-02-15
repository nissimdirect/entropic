# Entropic Alpha v2 — User Acceptance Testing Plan

> **Date:** 2026-02-09 (updated 2026-02-15)
> **Version:** v0.7.0-dev (115 effects, desktop app, timeline editor, spatial masks, **CLI performance mode**, **Web UI Perform Mode**, **Color Suite**, **LFO Map Operator**, **Parameter Accordion**, **Timeline Automation Lanes**, **Freeze/Flatten**, **Operator Mapping Expansion**)
> **Tester:** nissimdirect
> **Prepared by:** CTO, Red Team, Mad Scientist, Lenny, Don Norman
> **Updated:** Sections 22-27 for CLI Performance Mode. **Sections 28-34 for Web UI Perform Mode (v0.6.0).**

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
**You should see:** `115 effects loaded`
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

A browser-based DAW-style interface with Quick, Timeline, and Perform modes.

**To start:**
```bash
python3 server.py
```
Then open your web browser (Safari or Chrome) and go to:
```
http://localhost:7860
```
The interface should load with 4 panels (browser, canvas, chain, layers).

#### Mode D: Web UI Perform Mode (Sections 28-34) — NEW in v0.6.0

The full live performance workflow inside the browser. 4 channel strips, keyboard triggers, ADSR envelopes, choke groups, recording, review, render.

**To start:** Same as Mode C — run `python3 server.py`, open http://localhost:7860
**Then:** Upload a video, click the **Perform** button in the top bar.

**This is the primary mode to test for live performance readiness.**

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

### 3H. Destruction Effects (14) — "The Nuclear Arsenal"

> **Important:** These effects are AGGRESSIVE. Output may look severely corrupted — that's intentional.
> **Time:** ~30 minutes

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 3.38 | datamosh | `python3 entropic.py apply uat-test --effect datamosh` | Progressive pixel detachment (default: melt mode) | [ ] | |
| 3.39 | datamosh bloom | `python3 entropic.py apply uat-test --effect datamosh --params mode=bloom` | Old image smears, frozen in time | [ ] | |
| 3.40 | datamosh rip | `python3 entropic.py apply uat-test --effect datamosh --params mode=rip` | Violent pixel tearing, chunks fly | [ ] | |
| 3.41 | datamosh replace | `python3 entropic.py apply uat-test --effect datamosh --params mode=replace` | Blocky frozen patches (I-frame skip) | [ ] | |
| 3.42 | datamosh annihilate | `python3 entropic.py apply uat-test --effect datamosh --params mode=annihilate` | Total destruction — all modes combined | [ ] | |
| 3.43 | datamosh freeze_through | `python3 entropic.py apply uat-test --effect datamosh --params mode=freeze_through` | Old image persists (authentic I-frame removal) | [ ] | |
| 3.44 | datamosh pframe_extend | `python3 entropic.py apply uat-test --effect datamosh --params mode=pframe_extend` | Pixels stretch along motion path | [ ] | |
| 3.45 | datamosh donor | `python3 entropic.py apply uat-test --effect datamosh --params mode=donor` | Motion drives pixels from another time | [ ] | |
| 3.46 | datamosh intensity | `python3 entropic.py apply uat-test --effect datamosh --params intensity=50.0 decay=0.3` | More intense melt with faster decay | [ ] | |
| 3.47 | datamosh macroblock | `python3 entropic.py apply uat-test --effect datamosh --params macroblock_size=32` | Larger corruption blocks | [ ] | |
| 3.48 | bytecorrupt | `python3 entropic.py apply uat-test --effect bytecorrupt` | JPEG data bending artifacts | [ ] | |
| 3.49 | bytecorrupt heavy | `python3 entropic.py apply uat-test --effect bytecorrupt --params amount=0.8` | Severely bent data | [ ] | |
| 3.50 | blockcorrupt | `python3 entropic.py apply uat-test --effect blockcorrupt` | Macroblock corruption (default mode) | [ ] | |
| 3.51 | blockcorrupt smear | `python3 entropic.py apply uat-test --effect blockcorrupt --params mode=smear amount=0.6` | Smeared macroblocks | [ ] | |
| 3.52 | rowshift | `python3 entropic.py apply uat-test --effect rowshift` | Horizontal scanline tearing | [ ] | |
| 3.53 | rowshift heavy | `python3 entropic.py apply uat-test --effect rowshift --params amount=0.8` | Severe horizontal displacement | [ ] | |
| 3.54 | jpegdamage | `python3 entropic.py apply uat-test --effect jpegdamage` | Triple JPEG compression + block damage | [ ] | |
| 3.55 | jpegdamage extreme | `python3 entropic.py apply uat-test --effect jpegdamage --params quality=2 iterations=5` | Almost unrecognizable compression | [ ] | |
| 3.56 | invertbands | `python3 entropic.py apply uat-test --effect invertbands` | Alternating inverted horizontal bands | [ ] | |
| 3.57 | invertbands narrow | `python3 entropic.py apply uat-test --effect invertbands --params band_height=10` | Many thin inverted bands | [ ] | |
| 3.58 | databend | `python3 entropic.py apply uat-test --effect databend` | Audio DSP applied to pixels (default) | [ ] | |
| 3.59 | databend feedback | `python3 entropic.py apply uat-test --effect databend --params effect=feedback amount=0.7` | Self-feeding pixel corruption | [ ] | |
| 3.60 | flowdistort | `python3 entropic.py apply uat-test --effect flowdistort` | Optical flow displacement map | [ ] | |
| 3.61 | flowdistort strong | `python3 entropic.py apply uat-test --effect flowdistort --params strength=3.0` | Heavy flow displacement | [ ] | |
| 3.62 | filmgrain | `python3 entropic.py apply uat-test --effect filmgrain` | Realistic brightness-responsive grain | [ ] | |
| 3.63 | filmgrain heavy | `python3 entropic.py apply uat-test --effect filmgrain --params amount=0.8 size=3` | Coarse, heavy grain | [ ] | |
| 3.64 | glitchrepeat | `python3 entropic.py apply uat-test --effect glitchrepeat` | Buffer overflow slice repeat | [ ] | |
| 3.65 | glitchrepeat many | `python3 entropic.py apply uat-test --effect glitchrepeat --params slices=20 repeat_count=5` | Many repeated slices | [ ] | |
| 3.66 | xorglitch | `python3 entropic.py apply uat-test --effect xorglitch` | Bitwise XOR corruption | [ ] | |
| 3.67 | xorglitch pattern | `python3 entropic.py apply uat-test --effect xorglitch --params value=128` | Different XOR pattern | [ ] | |
| 3.68 | pixelannihilate | `python3 entropic.py apply uat-test --effect pixelannihilate` | Kill pixels (default: dissolve) | [ ] | |
| 3.69 | pixelannihilate edge | `python3 entropic.py apply uat-test --effect pixelannihilate --params mode=edge amount=0.7` | Edge-based pixel death | [ ] | |
| 3.70 | framesmash | `python3 entropic.py apply uat-test --effect framesmash` | One-stop apocalypse (6 techniques) | [ ] | |
| 3.71 | framesmash max | `python3 entropic.py apply uat-test --effect framesmash --params intensity=1.0` | Full-power apocalypse | [ ] | |
| 3.72 | channeldestroy | `python3 entropic.py apply uat-test --effect channeldestroy` | Rip channels apart (default mode) | [ ] | |
| 3.73 | channeldestroy swap | `python3 entropic.py apply uat-test --effect channeldestroy --params mode=swap amount=0.9` | Swapped channel chaos | [ ] | |

### 3I. Additional Texture Effects (4)

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 3.74 | tvstatic | `python3 entropic.py apply uat-test --effect tvstatic` | TV static with horizontal sync drift | [ ] | |
| 3.75 | tvstatic heavy | `python3 entropic.py apply uat-test --effect tvstatic --params drift=0.8 noise=0.9` | Heavy sync drift and noise | [ ] | |
| 3.76 | contours | `python3 entropic.py apply uat-test --effect contours` | Topographic contour lines | [ ] | |
| 3.77 | contours detailed | `python3 entropic.py apply uat-test --effect contours --params levels=20` | Many fine contour lines | [ ] | |
| 3.78 | asciiart | `python3 entropic.py apply uat-test --effect asciiart` | ASCII character rendering (default mode) | [ ] | |
| 3.79 | asciiart modes | `python3 entropic.py apply uat-test --effect asciiart --params mode=matrix` | Matrix-rain style ASCII | [ ] | |
| 3.80 | brailleart | `python3 entropic.py apply uat-test --effect brailleart` | Braille unicode art (4x resolution) | [ ] | |
| 3.81 | brailleart dither | `python3 entropic.py apply uat-test --effect brailleart --params dither=True` | Floyd-Steinberg dithered braille | [ ] | |

### 3J. Additional Color Effects (3)

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 3.82 | tapesaturation | `python3 entropic.py apply uat-test --effect tapesaturation` | Analog tape saturation curve | [ ] | |
| 3.83 | tapesaturation drive | `python3 entropic.py apply uat-test --effect tapesaturation --params drive=0.9` | Heavy tape overdrive | [ ] | |
| 3.84 | cyanotype | `python3 entropic.py apply uat-test --effect cyanotype` | Prussian blue cyanotype print | [ ] | |
| 3.85 | cyanotype params | `python3 entropic.py apply uat-test --effect cyanotype --params exposure=1.5` | Overexposed cyanotype | [ ] | |
| 3.86 | infrared | `python3 entropic.py apply uat-test --effect infrared` | Infrared film simulation | [ ] | |
| 3.87 | infrared params | `python3 entropic.py apply uat-test --effect infrared --params intensity=0.8` | Strong IR effect | [ ] | |

### 3K. Additional Modulation Effects (2)

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 3.88 | wavefold | `python3 entropic.py apply uat-test --effect wavefold` | Audio wavefolding on brightness | [ ] | |
| 3.89 | wavefold heavy | `python3 entropic.py apply uat-test --effect wavefold --params folds=5 drive=0.9` | Extreme folding distortion | [ ] | |
| 3.90 | amradio | `python3 entropic.py apply uat-test --effect amradio` | AM radio interference bands | [ ] | |
| 3.91 | amradio params | `python3 entropic.py apply uat-test --effect amradio --params frequency=2.0 noise=0.5` | Tuned AM interference | [ ] | |

### 3L. Additional Enhance Effects (3)

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 3.92 | histogrameq | `python3 entropic.py apply uat-test --effect histogrameq` | Per-channel histogram equalization | [ ] | |
| 3.93 | histogrameq params | `python3 entropic.py apply uat-test --effect histogrameq --params clip_limit=3.0` | Stronger histogram stretching | [ ] | |
| 3.94 | clahe | `python3 entropic.py apply uat-test --effect clahe` | Adaptive local contrast (night vision look) | [ ] | |
| 3.95 | clahe params | `python3 entropic.py apply uat-test --effect clahe --params clip_limit=4.0 tile_size=16` | Extreme local contrast | [ ] | |
| 3.96 | parallelcompress | `python3 entropic.py apply uat-test --effect parallelcompress` | NY compression for video | [ ] | |
| 3.97 | parallelcompress params | `python3 entropic.py apply uat-test --effect parallelcompress --params ratio=0.8 threshold=0.3` | Heavy parallel compression | [ ] | |

### 3M. Additional Distortion Effects (2)

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 3.98 | pencilsketch | `python3 entropic.py apply uat-test --effect pencilsketch` | Pencil sketch drawing effect | [ ] | |
| 3.99 | pencilsketch params | `python3 entropic.py apply uat-test --effect pencilsketch --params detail=0.8` | Detailed sketch look | [ ] | |
| 3.100 | smear | `python3 entropic.py apply uat-test --effect smear` | Cumulative paint-smear streaks | [ ] | |
| 3.101 | smear heavy | `python3 entropic.py apply uat-test --effect smear --params length=20 opacity=0.9` | Long heavy smear trails | [ ] | |

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

### 7E. Missing Packages (5 packages added post-launch)

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 7.21 | Explore total-destruction | `python3 entropic_packages.py explore total-destruction` | 15 recipes with destruction chains | [ ] | |
| 7.22 | Apply light-datamosh | `python3 entropic_packages.py apply uat-test --package total-destruction --recipe light-datamosh` | Gentle datamosh, renders + opens | [ ] | |
| 7.23 | Apply nuclear-smash | `python3 entropic_packages.py apply uat-test --package total-destruction --recipe nuclear-smash` | Heavy multi-destruction chain | [ ] | |
| 7.24 | Explore motion-warp | `python3 entropic_packages.py explore motion-warp` | 5 recipes with motion effects | [ ] | |
| 7.25 | Apply flow-push | `python3 entropic_packages.py apply uat-test --package motion-warp --recipe flow-push` | Optical flow push, opens | [ ] | |
| 7.26 | Apply melt-cascade | `python3 entropic_packages.py apply uat-test --package motion-warp --recipe melt-cascade` | Melting cascade effect | [ ] | |
| 7.27 | Explore NUCLEAR | `python3 entropic_packages.py explore NUCLEAR` | 8 nuclear-level recipes | [ ] | |
| 7.28 | Apply nuclear-everything | `python3 entropic_packages.py apply uat-test --package NUCLEAR --recipe nuclear-everything` | Maximum destruction combo | [ ] | |
| 7.29 | Explore datamosh-combos | `python3 entropic_packages.py explore datamosh-combos` | 6 datamosh combo recipes | [ ] | |
| 7.30 | Apply mosh-then-sort | `python3 entropic_packages.py apply uat-test --package datamosh-combos --recipe mosh-then-sort` | Datamosh + pixelsort combined | [ ] | |
| 7.31 | Apply mosh-vhs | `python3 entropic_packages.py apply uat-test --package datamosh-combos --recipe mosh-vhs` | Datamosh + VHS combined | [ ] | |
| 7.32 | Explore ascii-art | `python3 entropic_packages.py explore ascii-art` | 6 ASCII art recipes | [ ] | |
| 7.33 | Apply terminal-mono | `python3 entropic_packages.py apply uat-test --package ascii-art --recipe terminal-mono` | Monochrome terminal look | [ ] | |
| 7.34 | Apply braille-hires | `python3 entropic_packages.py apply uat-test --package ascii-art --recipe braille-hires` | High-res braille art | [ ] | |
| 7.35 | Batch total-destruction | `python3 entropic_packages.py batch uat-test --package total-destruction` | 15 renders, summary table | [ ] | |
| 7.36 | Updated full matrix | `python3 entropic_packages.py matrix uat-test` | 76 renders (all 12 packages), summary table | [ ] | |

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

## SECTION 17B: CLIP COMMAND

> **Goal:** The `clip` command trims video to a time range correctly.
> **Time:** ~5 minutes

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 17.7 | Basic clip | `python3 entropic.py clip ~/Desktop/YOUR_VIDEO.mp4 --start 2.0 --duration 5 --output ~/Desktop/clipped.mp4` | Creates 5-second clip starting at 2s | [ ] | |
| 17.8 | Clip with end | `python3 entropic.py clip ~/Desktop/YOUR_VIDEO.mp4 --start 1.0 --end 4.0 --output ~/Desktop/clipped2.mp4` | Creates 3-second clip (1s to 4s) | [ ] | |
| 17.9 | Clip plays | Open clipped.mp4 in QuickTime | Correct duration, audio synced | [ ] | |
| 17.10 | No output flag | `python3 entropic.py clip ~/Desktop/YOUR_VIDEO.mp4 --start 0 --duration 3` | Auto-generates output filename | [ ] | |
| 17.11 | Start past end | `python3 entropic.py clip ~/Desktop/YOUR_VIDEO.mp4 --start 9999 --duration 5` | Error: start exceeds duration | [ ] | |
| 17.12 | Missing input | `python3 entropic.py clip nonexistent.mp4 --duration 5` | Error: file not found | [ ] | |

---

## SECTION 17C: DATAMOSH DESKTOP APP

> **Goal:** The `datamosh` command launches the native desktop datamosh application.
> **Time:** ~3 minutes

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 17.13 | Launch command | `python3 entropic.py datamosh` | Desktop datamosh app window opens | [ ] | |
| 17.14 | App renders | Check app window | UI visible, no blank/white screen | [ ] | |

---

## PRIORITY ORDER

If you're short on time, test in this order:

1. **Section 1** (Smoke) — if this fails, stop here
2. **Section 18** (Desktop App) — app must boot
3. **Section 28** (Web Perform: Launch + Mixer) — new v0.6.0 feature
4. **Section 29** (Web Perform: Keyboard Triggers) — core interaction
5. **Section 30** (Web Perform: Transport + Recording) — capture performance
6. **Section 31** (Web Perform: Layer Config) — configure effects/modes
7. **Section 33** (Web Perform: Save + Render) — export
8. **Section 9** (Safety) — security
9. **Section 19** (UI Core) — existing features
10. Everything else

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

## SECTION 28: WEB UI PERFORM MODE — LAUNCH & MIXER (v0.6.0)

> **Goal:** Perform mode activates from the web UI, mixer panel renders with 4 channel strips + master.
> **Time:** ~10 minutes
> **Setup:** `cd ~/Development/entropic && python3 server.py` → open http://localhost:7860
> **Prereq:** Upload a video first (any MP4, drag onto canvas or click upload area)

### 28A. Mode Switch

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 28.1 | Perform button exists | Look at top bar | Three mode buttons: Quick, Timeline, Perform | [ ] | |
| 28.2 | Switch to Perform | Click "Perform" button | Mixer panel appears below preview, transport bar visible | [ ] | |
| 28.3 | Mode accent | Check top bar border | Orange/red border + glow on top bar (not blue/default) | [ ] | |
| 28.4 | Mode badge | Check preview area | `[PERFORM]` badge visible on preview | [ ] | |
| 28.5 | Switch back to Quick | Click "Quick" button | Mixer + transport hide, normal layout returns | [ ] | |
| 28.6 | No video = blocked | Try Perform without uploading video | Toast: "Load a video first" — stays in current mode | [ ] | |
| 28.7 | Quick→Perform handoff | Set up effects in Quick mode, then switch to Perform | L2 inherits your Quick mode chain (check L2 strip label) | [ ] | |

### 28B. Mixer Panel

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 28.8 | 4 strips + master | Count channel strips in mixer | L1, L2, L3, L4, MASTER — 5 columns | [ ] | |
| 28.9 | Strip colors | Check strip headers | L1=red, L2=blue, L3=green, L4=yellow (colored dots) | [ ] | |
| 28.10 | Key labels visible | Check each strip header | [1], [2], [3], [4] labels readable at arm's length | [ ] | |
| 28.11 | Layer names | Check strip headers | L1="Base (Clean)", L2="VHS + Glitch", L3="Pixel Sort", L4="Feedback" | [ ] | |
| 28.12 | Trigger buttons | Check each strip | Each has a trigger button with mode-specific shape | [ ] | |
| 28.13 | Vertical faders | Check each strip | Vertical opacity slider (0-100%) in each strip | [ ] | |
| 28.14 | Mute/Solo buttons | Check strip bottoms | M and S buttons on each strip | [ ] | |
| 28.15 | Master strip | Check rightmost column | Shows "MASTER" with output opacity control | [ ] | |

### 28C. Right Panel (Layers Tab)

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 28.16 | Layers tab in Perform | Click "Layers" tab in right panel | Shows perform layer overview (not Quick mode layers) | [ ] | |
| 28.17 | Layer rows | Check layer list | Each layer: visibility eye, name, opacity %, trigger mode icon | [ ] | |
| 28.18 | Click selects layer | Click a layer row | That layer's effects show in the left sidebar browser | [ ] | |

---

## SECTION 29: WEB UI PERFORM MODE — KEYBOARD TRIGGERS

> **Goal:** Keys 1-4 trigger layers with instant visual feedback (3-tier: instant → server → confirmed).
> **Time:** ~10 minutes
> **Prereq:** In Perform mode with video loaded

### 29A. Basic Triggers

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 29.1 | Key 1 triggers L1 | Press **1** | L1 strip lights up INSTANTLY (before server responds) | [ ] | |
| 29.2 | Key 2 triggers L2 | Press **2** | L2 strip lights up, preview shows VHS+Glitch effect | [ ] | |
| 29.3 | Key 3 triggers L3 | Press **3** | L3 strip lights up, preview shows PixelSort | [ ] | |
| 29.4 | Key 4 triggers L4 | Press **4** | L4 strip lights up, preview shows Feedback | [ ] | |
| 29.5 | Invalid key ignored | Press **5**, **6**, **7**, **8**, **9** | Nothing happens, no error | [ ] | |
| 29.6 | Keys outside perform | Switch to Quick mode, press **1-4** | Nothing happens (keys only active in Perform mode) | [ ] | |

### 29B. Toggle Mode

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 29.7 | Toggle ON | Press **2** once | L2 active (strip lit, trigger button lit) | [ ] | |
| 29.8 | Toggle OFF | Press **2** again | L2 inactive (strip dim, trigger button dim) | [ ] | |
| 29.9 | Multiple toggle | Toggle L2, L3, L4 all ON | All three strips lit, preview shows composited effects | [ ] | |

### 29C. Gate Mode (Hold-to-activate)

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 29.10 | Set gate mode | Change L2's trigger mode dropdown to "gate" | Trigger button shape changes to circle | [ ] | |
| 29.11 | Hold = active | Press and HOLD **2** | L2 active while key held | [ ] | |
| 29.12 | Release = inactive | Release **2** | L2 deactivates immediately | [ ] | |

### 29D. ADSR Mode

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 29.13 | Set ADSR mode | Change L2's trigger mode to "adsr" | Trigger button gets double-border ring shape | [ ] | |
| 29.14 | ADSR trigger | Press **2** during playback | L2 fades in (attack), holds (sustain) | [ ] | |
| 29.15 | ADSR release | Release **2** | L2 fades out (release phase) | [ ] | |
| 29.16 | ADSR preset change | Change ADSR preset dropdown to "stab" | Different envelope shape (faster attack/decay) | [ ] | |

### 29E. One-Shot Mode

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 29.17 | Set one-shot mode | Change L2's trigger mode to "one_shot" | Trigger button shows flash icon | [ ] | |
| 29.18 | One-shot trigger | Press **2** | L2 fires once and auto-fades (release handles itself) | [ ] | |

### 29F. Mouse Triggers

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 29.19 | Click trigger button | Click L2's trigger button with mouse | Same behavior as keyboard (toggles/gates depending on mode) | [ ] | |
| 29.20 | Mouse gate | Set gate mode, mousedown on trigger button | Active while held. Release = off | [ ] | |

---

## SECTION 30: WEB UI PERFORM MODE — TRANSPORT & RECORDING

> **Goal:** Play, record, review, panic controls work. Scrubber, timer, frame counter update.
> **Time:** ~10 minutes

### 30A. Transport Bar

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 30.1 | Transport visible | In Perform mode | Transport bar between preview and mixer: Play, Rec, Loop, Panic buttons | [ ] | |
| 30.2 | Timer shows | Check transport | `0:00:00 / [duration]` and `F:0` frame counter | [ ] | |
| 30.3 | Scrubber works | Drag scrubber slider | Frame counter and preview update | [ ] | |
| 30.4 | Event counter | Check transport right side | "0 events" counter visible | [ ] | |

### 30B. Playback

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 30.5 | Space = play | Press **Space** | Preview advances at ~15fps, timer counts up, scrubber moves | [ ] | |
| 30.6 | Space = pause | Press **Space** again | Preview freezes, timer stops | [ ] | |
| 30.7 | Triggers during play | Play video, press **2** | Layer activates, preview shows effect in real-time | [ ] | |
| 30.8 | Mode buttons locked | During playback, check mode buttons | Quick/Timeline buttons disabled (can't switch mid-play) | [ ] | |

### 30C. Recording

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 30.9 | R = arm recording | Press **R** | REC button pulses red, toast "Recording armed — buffer cleared" | [ ] | |
| 30.10 | Scrubber disabled | While recording | Scrubber grayed out (opacity 0.3), dragging does nothing | [ ] | |
| 30.11 | Perform while recording | Play + trigger layers | Event counter increments with each trigger | [ ] | |
| 30.12 | R = stop recording | Press **R** again | REC stops pulsing, 3 toasts: Save / Review / Discard | [ ] | |
| 30.13 | Scrubber re-enabled | After stopping recording | Scrubber back to full opacity, draggable again | [ ] | |

### 30D. Panic

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 30.14 | Shift+P = panic | Turn on L2, L3, L4, then press **Shift+P** | ALL layers reset, all strips go dim, toast "All layers reset" | [ ] | |
| 30.15 | P alone = nothing | Press **P** without Shift | Nothing happens (modifier required) | [ ] | |

### 30E. HUD Overlay

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 30.16 | HUD shows during play | Start playback | Timer and event count overlay on preview | [ ] | |
| 30.17 | REC indicator in HUD | Arm recording | Red "REC" text visible in HUD | [ ] | |
| 30.18 | H toggles HUD | Press **H** | HUD overlay toggles on/off | [ ] | |

---

## SECTION 31: WEB UI PERFORM MODE — LAYER CONFIGURATION

> **Goal:** All layer settings (trigger mode, ADSR, blend, effects, choke, opacity) configurable via mixer dropdowns.
> **Time:** ~10 minutes

### 31A. Dropdowns

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 31.1 | Trigger mode dropdown | Click trigger mode selector on any strip | Options: toggle, gate, adsr, one_shot, always_on | [ ] | |
| 31.2 | Change trigger mode | Switch L2 from toggle to gate | Trigger button shape changes, behavior changes | [ ] | |
| 31.3 | ADSR preset dropdown | With ADSR mode selected | Options: pluck, sustain, stab, pad | [ ] | |
| 31.4 | Blend mode dropdown | Click blend mode selector | Options: normal, multiply, screen, overlay, add, subtract, difference | [ ] | |
| 31.5 | Change blend mode | Switch L2 to "multiply" | Preview compositing changes visually | [ ] | |

### 31B. Opacity Faders

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 31.6 | Fader moves | Drag L2's vertical fader | Opacity % label updates in real time | [ ] | |
| 31.7 | Preview updates | Move fader with playback on | Effect intensity changes in preview | [ ] | |
| 31.8 | Fader at 0% | Drag to bottom | Layer invisible in preview | [ ] | |
| 31.9 | Fader at 100% | Drag to top | Layer at full strength | [ ] | |

### 31C. Choke Groups

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 31.10 | Choke dropdown | Click choke group selector | Options: No choke, Choke A, Choke B, Choke C | [ ] | |
| 31.11 | Set same choke group | Put L2 and L3 both on "Choke A" | Both show Choke A | [ ] | |
| 31.12 | Choke behavior | Toggle L2 ON, then toggle L3 ON | L2 deactivates (choked by L3), L2 strip flashes red briefly | [ ] | |
| 31.13 | Choke flash visible | Watch L2's strip when L3 activates | Red flash animation (0.3s) on choked strip | [ ] | |

### 31D. Mute/Solo

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 31.14 | Mute layer | Click M on L2 strip | L2 muted — key 2 does nothing, strip dimmed | [ ] | |
| 31.15 | Unmute | Click M again | L2 active again | [ ] | |
| 31.16 | Solo layer | Click S on L2 | Only L2 audible/visible (others suppressed) | [ ] | |

### 31E. Effects (Per-Layer)

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 31.17 | Click effect chain area | Click the effect summary on L2's strip | Left sidebar shows L2's effects for editing | [ ] | |
| 31.18 | Add effect to layer | Add effect from browser while L2 selected | Effect appears on L2 (not global chain) | [ ] | |
| 31.19 | Layer keeps effects | Switch layer selection back and forth | Each layer retains its own effect chain | [ ] | |

---

## SECTION 32: WEB UI PERFORM MODE — REVIEW & VISUAL QUALITY

> **Goal:** After recording, user can review the performance with event density visualization.
> **Time:** ~10 minutes

### 32A. Review Mode

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 32.1 | Enter review | After recording, click "Review" toast | Playback starts from frame 0 with recorded automation | [ ] | |
| 32.2 | Layer states replay | Watch during review | Channel strips light up at the moments you triggered them | [ ] | |
| 32.3 | Event density | Check below preview | Mini-timeline shows event density (bars/waveform) | [ ] | |
| 32.4 | Scrubbing in review | Drag scrubber during review | Preview + strip states update to match recorded state | [ ] | |
| 32.5 | Exit review | Click play or trigger a layer | Exits review mode, back to live perform | [ ] | |

### 32B. Visual Quality

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 32.6 | 15fps preview | Watch preview during playback | ~15fps, smooth enough for performance | [ ] | |
| 32.7 | Trigger shape: toggle | Check L1 trigger button (toggle mode) | Square shape (4px radius) | [ ] | |
| 32.8 | Trigger shape: gate | Set gate mode, check trigger | Circle shape (50% radius, solid) | [ ] | |
| 32.9 | Trigger shape: ADSR | Set ADSR mode, check trigger | Circle with double border (ring/donut — distinct from gate) | [ ] | |
| 32.10 | Trigger shape: one-shot | Set one_shot mode, check trigger | Square with flash icon | [ ] | |
| 32.11 | Trigger shape: always-on | Check L1 (always_on) | Green dot indicator, non-clickable | [ ] | |
| 32.12 | Active strip glow | Trigger a layer ON | Entire strip background lightens | [ ] | |
| 32.13 | REC button pulse | Arm recording | REC button has red pulsing CSS animation | [ ] | |

---

## SECTION 33: WEB UI PERFORM MODE — SAVE, RENDER, PROJECT

> **Goal:** Performance data saves, renders at full quality, integrates with project system.
> **Time:** ~10 minutes

### 33A. Save

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 33.1 | Save after recording | Record a performance, click Save toast | Toast with file path + "Reveal in Finder" | [ ] | |
| 33.2 | File created | Check exported folder | `.json` automation file exists | [ ] | |
| 33.3 | Discard | Record, click "Discard" toast | Buffer cleared, event counter resets to 0 | [ ] | |

### 33B. Render

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 33.4 | Render button | Click "Render" in transport | Export dialog opens (or render starts) | [ ] | |
| 33.5 | Progress indicator | During render | Progress shown (not a blocking modal) | [ ] | |
| 33.6 | Render complete | Wait for finish | Toast: "Rendered: XXmb @ 30fps" + "Reveal in Finder" | [ ] | |
| 33.7 | Output plays | Open rendered file in QuickTime/VLC | Video shows your triggered effects at correct times | [ ] | |
| 33.8 | Audio passthrough | Check rendered file has audio | Audio from source video present in output | [ ] | |

### 33C. Project Integration

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 33.9 | Cmd+S saves project | Press **Cmd+S** in Perform mode | Project saves (same as Quick/Timeline mode) | [ ] | |
| 33.10 | Project includes perform | Save, reload page, load project | Perform layer config restored | [ ] | |
| 33.11 | beforeunload warning | Trigger layers (unsaved), try closing tab | Browser warns: "You have unsaved performance data" | [ ] | |

---

## SECTION 34: WEB UI PERFORM MODE — SAFETY & EDGE CASES

> **Goal:** Error prevention, graceful failures, no data loss during live use.
> **Time:** ~10 minutes

### 34A. Error Prevention (Don Norman)

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 34.1 | Mode switch during play | Start playback, try clicking Quick/Timeline | Mode buttons disabled (grayed out) | [ ] | |
| 34.2 | Scrub during recording | Arm recording, try dragging scrubber | Scrubber disabled + toast "Cannot scrub while recording" | [ ] | |
| 34.3 | No video = no perform | Click Perform without uploading video | Toast: "Load a video first", stays in current mode | [ ] | |
| 34.4 | Shift+P required | Press P alone during performance | Nothing happens (no panic without modifier) | [ ] | |

### 34B. Drag-to-Reorder

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 34.5 | Drag strip | Drag L2's strip header to L4's position | Strips reorder visually | [ ] | |
| 34.6 | Z-order updated | After drag | Layer compositing order changes in preview | [ ] | |
| 34.7 | Keys still match | After reorder, press original key numbers | Keys still trigger the correct layer (not position) | [ ] | |

### 34C. New Effects (v0.6.0)

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 34.8 | Chroma key | Add `chroma_key` effect to a layer | Green/blue screen removal — key color removed | [ ] | |
| 34.9 | Chroma key params | Adjust `hue_center`, `hue_range`, `softness` | Key color and edge quality change | [ ] | |
| 34.10 | Luma key | Add `luma_key` effect to a layer | Dark or light areas become transparent | [ ] | |
| 34.11 | Luma key params | Adjust `threshold`, `softness`, `invert` | Key range and behavior change | [ ] | |

### 34D. Input Validation (Red Team)

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 34.12 | Invalid trigger mode | (DevTools) POST invalid trigger_mode to API | 422 error (pydantic validation) | [ ] | |
| 34.13 | Invalid ADSR preset | (DevTools) POST unknown adsr_preset | 400 error: "Unknown ADSR preset" | [ ] | |
| 34.14 | Too many effects | (DevTools) POST 25+ effects to update_layer | 400 error: "Max 20 effects per layer" | [ ] | |
| 34.15 | Invalid blend mode | (DevTools) POST unknown blend_mode | 400 error: "Unknown blend mode" | [ ] | |

### 34E. Stability

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 34.16 | 5-min continuous play | Play + trigger layers for 5 minutes | No crash, no memory leak, consistent ~15fps | [ ] | |
| 34.17 | Rapid triggers | Rapidly press 1-2-3-4 for 30 seconds | No crash, triggers queue correctly | [ ] | |
| 34.18 | Server restart recovery | Stop server (Ctrl+C), restart | "Engine disconnected" banner, reconnects on restart | [ ] | |

---

---

## SECTION 35: USER INTEGRATION TESTING (UIT)

> **Goal:** Verify that features work together across modes, sessions, and workflows — not just in isolation.
> **UIT ≠ UAT.** UAT tests individual features ("does pixelsort work?"). UIT tests real workflows ("can I go from upload to final exported video using timeline + perform mode together?").
> **Time:** ~60 minutes total
> **Prereq:** Sections 1 (Smoke) and 18 (Desktop App boot) must PASS first.

---

### 35A. Workflow 1: CLI Project → Effects → Render → Verify

> **Scenario:** Create a project, apply multiple effects, render at multiple qualities, verify output files.

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 35.1 | Create project | `python3 entropic.py new uit-flow1 --source ~/Desktop/YOUR_VIDEO.mp4` | Project created | [ ] | |
| 35.2 | Apply 3 effects | Apply pixelsort, then vhs, then feedback (3 separate commands) | 3 recipes in history | [ ] | |
| 35.3 | Verify history | `python3 entropic.py history uit-flow1` | All 3 recipes listed with IDs | [ ] | |
| 35.4 | Branch a recipe | `python3 entropic.py branch uit-flow1 001 --params threshold=0.1` | Branched recipe shows parent=001 | [ ] | |
| 35.5 | Render lo | `python3 entropic.py render uit-flow1 001 --quality lo` | 480p MP4 created | [ ] | |
| 35.6 | Render hi | `python3 entropic.py render uit-flow1 001 --quality hi` | Full-res MOV created | [ ] | |
| 35.7 | Both outputs play | Open both in QuickTime | Same effect, different quality/resolution | [ ] | |
| 35.8 | Status tracks usage | `python3 entropic.py status uit-flow1` | Shows MB used, recipe count, render count | [ ] | |

---

### 35B. Workflow 2: Web UI Quick → Timeline → Export

> **Scenario:** Upload in Quick mode, add effects, switch to Timeline, create regions with different effects, export.

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 35.9 | Upload in Quick | Drag video onto canvas | Video loads, first frame visible | [ ] | |
| 35.10 | Add effect in Quick | Add pixelsort from browser | Preview shows pixelsort on canvas | [ ] | |
| 35.11 | Switch to Timeline | Click "Timeline" button | Timeline panel appears, pixelsort chain preserved | [ ] | |
| 35.12 | Create Region A | Set I at frame 0, O at frame 60, Cmd+R | Region [0-60] on Video 1 track | [ ] | |
| 35.13 | Region A has effect | Click Region A | Chain rack shows pixelsort (inherited from Quick) | [ ] | |
| 35.14 | Create Region B | Set I at frame 90, O at frame 150, Cmd+R | Second region [90-150] | [ ] | |
| 35.15 | Add different effect | Click Region B, add datamosh from browser | Region B has datamosh, Region A still has pixelsort | [ ] | |
| 35.16 | Preview confirms | Move playhead to frame 30 (Region A) | Canvas shows pixelsort | [ ] | |
| 35.17 | Preview gap | Move playhead to frame 75 (gap between regions) | Canvas shows original (no effects) | [ ] | |
| 35.18 | Preview Region B | Move playhead to frame 120 | Canvas shows datamosh | [ ] | |
| 35.19 | Export timeline | Click Export | Export starts with timeline data | [ ] | |
| 35.20 | Output correct | Play exported video | Pixelsort at 0-60, clean at 60-90, datamosh at 90-150 | [ ] | |

---

### 35C. Workflow 3: Web UI Quick → Perform → Record → Save → Render

> **Scenario:** Set up effects in Quick mode, switch to Perform, record a live performance, save, render to file.

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 35.21 | Upload video | Drag MP4 onto canvas | Video loads | [ ] | |
| 35.22 | Switch to Perform | Click "Perform" | Mixer panel appears, 4 channel strips | [ ] | |
| 35.23 | Start playback | Press Space | Preview advances, timer counts | [ ] | |
| 35.24 | Arm recording | Press R | REC button pulses red, "Recording armed" toast | [ ] | |
| 35.25 | Trigger layers | During playback: press 2 at ~2s, press 3 at ~4s, press 4 at ~6s | Event counter increments (3+ events) | [ ] | |
| 35.26 | Stop recording | Press R again | Three toasts: Save / Review / Discard | [ ] | |
| 35.27 | Review performance | Click Review toast | Playback restarts, channel strips replay your triggers | [ ] | |
| 35.28 | Triggers replay correctly | Watch review | L2 activates at ~2s, L3 at ~4s, L4 at ~6s | [ ] | |
| 35.29 | Save performance | Click Save toast | File saved, toast shows path + "Reveal in Finder" | [ ] | |
| 35.30 | Render performance | Click Render in transport | Progress shown, output file created | [ ] | |
| 35.31 | Rendered output correct | Open rendered file in QuickTime/VLC | Effects appear at correct timestamps matching your triggers | [ ] | |
| 35.32 | Audio in output | Check rendered file has audio | Audio from source video present | [ ] | |

---

### 35D. Workflow 4: CLI Performance → Render → Verify

> **Scenario:** Use the CLI pygame performance mode, record a session, render offline, verify output.

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 35.33 | Launch CLI perform | `python3 entropic_perform.py --base ~/Desktop/YOUR_VIDEO.mp4` | Pygame window opens, 4 layers in console | [ ] | |
| 35.34 | Arm and perform | Press R (arm), then toggle layers 2/3/4 during playback | Console shows ON/OFF events, HUD shows [REC] | [ ] | |
| 35.35 | Save on exit | Press Shift+Q | Auto-saves perf_TIMESTAMP.json + .layers.json | [ ] | |
| 35.36 | Files exist | `ls perf_*.json` | Both .json and .layers.json present | [ ] | |
| 35.37 | Offline render | `python3 entropic_perform.py --render --automation perf_TIMESTAMP.json --audio ~/Desktop/YOUR_VIDEO.mp4 -o uit_render.mp4` | Progress bar → creates uit_render.mp4 | [ ] | |
| 35.38 | Output plays | Open uit_render.mp4 | Effects at correct times, audio present, full resolution | [ ] | |

---

### 35E. Workflow 5: Multi-Mode Switching Stress Test

> **Scenario:** Rapidly switch between Quick, Timeline, and Perform modes to verify no state corruption.

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 35.39 | Upload video | Drag video in Quick mode | Video loads | [ ] | |
| 35.40 | Add effects in Quick | Add vhs + channelshift to chain | Both in chain rack | [ ] | |
| 35.41 | Quick → Timeline | Click Timeline | Timeline appears, effects preserved | [ ] | |
| 35.42 | Create region | Set I/O, Cmd+R | Region created with effects | [ ] | |
| 35.43 | Timeline → Perform | Click Perform | Mixer appears, L2 inherits Quick chain | [ ] | |
| 35.44 | Trigger layers | Press 2, 3 | Layers activate, preview updates | [ ] | |
| 35.45 | Perform → Quick | Click Quick | Normal layout returns, original chain intact | [ ] | |
| 35.46 | Quick → Timeline | Click Timeline again | Region still exists with original effects | [ ] | |
| 35.47 | Timeline → Perform → Timeline | Switch rapidly 3x | No crash, no state loss, regions preserved | [ ] | |
| 35.48 | All effects still work | Back in Quick, adjust a parameter | Preview updates correctly | [ ] | |

---

### 35F. Workflow 6: Project Persistence (Save → Close → Reload)

> **Scenario:** Save a project with timeline regions, close the browser, reopen, verify everything restores.

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 35.49 | Set up complex state | Upload video, Timeline mode, 3 regions with different effects, spatial mask on Region A | All visible in UI | [ ] | |
| 35.50 | Save project | Cmd+S → name it "uit-persistence-test" | Toast: "Project saved" | [ ] | |
| 35.51 | Close browser tab | Close the tab (accept unsaved warning if any) | Tab closed | [ ] | |
| 35.52 | Reopen browser | Navigate to http://localhost:7860 | Fresh UI loads | [ ] | |
| 35.53 | Load project | Cmd+O → select "uit-persistence-test" | Project loads | [ ] | |
| 35.54 | Regions restored | Check timeline | All 3 regions at correct positions | [ ] | |
| 35.55 | Effects restored | Click each region | Each has its own effect chain intact | [ ] | |
| 35.56 | Mask restored | Click Region A | Spatial mask overlay visible at correct position | [ ] | |
| 35.57 | Playhead position | Check playhead | Restored to saved position | [ ] | |

---

### 35G. Workflow 7: Sidechain Cross-Video Integration

> **Scenario:** Use two videos together in a sidechain cross-video workflow.

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 35.58 | Create sidechain project | `python3 entropic.py new uit-sidechain --source ~/Desktop/VIDEO_A.mp4` | Project created | [ ] | |
| 35.59 | Apply sidechaincross | Apply sidechaincross with VIDEO_B as key signal | One video busts through another | [ ] | |
| 35.60 | Apply sidechaincrossfeed | Apply sidechaincrossfeed with VIDEO_B | Channel mixing between videos visible | [ ] | |
| 35.61 | Apply sidechaininterference | Apply sidechaininterference with VIDEO_B | Phase/amplitude interference patterns | [ ] | |
| 35.62 | Render sidechain | Render any of the above at mid quality | Output shows cross-video effect | [ ] | |
| 35.63 | Output plays | Open rendered sidechain video | Both video sources contribute to output | [ ] | |

---

### 35H. Workflow 8: Region Selection + Effects Integration

> **Scenario:** Use spatial regions (CLI) with multiple effects and verify masked areas.

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 35.64 | Region preset | `python3 entropic.py apply uat-test --effect pixelsort --region center` | Pixelsort only in center 50% | [ ] | |
| 35.65 | Custom region | `python3 entropic.py apply uat-test --effect vhs --region "100,50,400,300"` | VHS only in specified rectangle | [ ] | |
| 35.66 | Percentage region | `python3 entropic.py apply uat-test --effect invert --region "0.1,0.1,0.8,0.8"` | Inverted in 80% center area | [ ] | |
| 35.67 | Feathered region | `python3 entropic.py apply uat-test --effect datamosh --region center --feather 30` | Datamosh with soft 30px edge blend | [ ] | |
| 35.68 | Region + render | Render any regional recipe at hi quality | Output shows effect only in masked area | [ ] | |

---

### 35I. Workflow 9: Perform Mode Choke Group Integration

> **Scenario:** Configure choke groups and verify mutual exclusion during live triggering.

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 35.69 | Upload + Perform mode | Upload video, switch to Perform | Mixer visible | [ ] | |
| 35.70 | Set choke groups | Put L2 and L3 on Choke A, L4 on Choke B | All three show correct choke labels | [ ] | |
| 35.71 | Trigger L2 | Press 2 | L2 active | [ ] | |
| 35.72 | Trigger L3 (chokes L2) | Press 3 | L3 active, L2 deactivates (red flash), preview updates | [ ] | |
| 35.73 | L4 independent | Press 4 | L4 active, L3 still active (different choke group) | [ ] | |
| 35.74 | Record choke sequence | Arm recording, trigger L2→L3→L4→L2 rapidly | All events captured, choke behavior in recording | [ ] | |
| 35.75 | Review shows chokes | Review recorded performance | Choke deactivations replayed correctly | [ ] | |

---

### 35J. Workflow 10: Blend Mode Compositing Integration

> **Scenario:** Test that different blend modes on different layers composite correctly together.

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 35.76 | Set blend modes | L2=multiply, L3=screen, L4=difference | All three show correct blend mode | [ ] | |
| 35.77 | Trigger all 3 | Press 2, 3, 4 | Preview shows all 3 layers composited with correct blend modes | [ ] | |
| 35.78 | Multiply visible | L2 ON only | Darkened image (multiply darkens) | [ ] | |
| 35.79 | Screen visible | L3 ON only | Brightened image (screen brightens) | [ ] | |
| 35.80 | Difference visible | L4 ON only | Inverted/psychedelic colors (difference) | [ ] | |
| 35.81 | All together | All ON | Complex composited result (not just one mode) | [ ] | |
| 35.82 | Render composited | Render with all blend modes active | Output matches preview compositing | [ ] | |

---

### 35K. Workflow 11: ADSR Envelope Integration

> **Scenario:** Test ADSR envelopes across trigger modes during recording and render.

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 35.83 | Set ADSR on L2 | Change L2 trigger mode to ADSR, preset "pluck" | ADSR controls visible | [ ] | |
| 35.84 | Set ADSR on L3 | Change L3 trigger mode to ADSR, preset "pad" | Different envelope shape | [ ] | |
| 35.85 | Pluck behavior | Press 2 during playback | Quick attack, visible decay, short sustain | [ ] | |
| 35.86 | Pad behavior | Press 3 during playback | Slow attack, long sustain, gradual fade | [ ] | |
| 35.87 | Record ADSR performance | Arm recording, trigger L2 and L3 at different times | Events captured with timing | [ ] | |
| 35.88 | Render preserves envelopes | Render the recorded performance | Output shows gradual fade-ins/outs matching ADSR settings | [ ] | |

---

### 35L. Workflow 12: Error Recovery Integration

> **Scenario:** Test that the system recovers gracefully from errors mid-workflow.

| # | Test | Steps | Expected | Result | Notes |
|---|------|-------|----------|--------|-------|
| 35.89 | Server restart mid-use | In Perform mode, stop server (Ctrl+C in terminal), restart | "Engine disconnected" banner → reconnects on restart | [ ] | |
| 35.90 | State after reconnect | After server restarts | Video reloads, can continue working (may need re-upload) | [ ] | |
| 35.91 | Bad effect mid-chain | In Quick mode, add 2 good effects + 1 that errors | Error toast for bad effect, other 2 still applied | [ ] | |
| 35.92 | Cancel render mid-process | Start export, cancel/close during progress | Partial file cleaned up, no corrupt state | [ ] | |
| 35.93 | Multiple tabs | Open http://localhost:7860 in 2 tabs, use both | Both work (or second shows "session active" warning) | [ ] | |

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
| 22. CLI Perform: Launch | 6 | | | |
| 23. CLI Perform: Keyboard | 14 | | | |
| 24. CLI Perform: Recording | 8 | | | |
| 25. CLI Perform: MIDI | 6 | | | |
| 26. CLI Perform: Triggers/Visuals | 10 | | | |
| 27. CLI Perform: Render/Stability | 15 | | | |
| **28. Web Perform: Launch + Mixer** | **18** | | | |
| **29. Web Perform: Keyboard Triggers** | **20** | | | |
| **30. Web Perform: Transport + Recording** | **18** | | | |
| **31. Web Perform: Layer Config** | **19** | | | |
| **32. Web Perform: Review + Visual** | **13** | | | |
| **33. Web Perform: Save + Render** | **11** | | | |
| **34. Web Perform: Safety + Edge Cases** | **18** | | | |
| **TOTAL** | **472** | | | |

**Ship criteria:**
- **CLI (Sections 1-17):** 90%+ pass rate (167+ of 185), zero critical failures in Sections 1, 2, 9
- **Desktop App (Section 18):** 100% pass (7/7) — app must boot
- **UI Core (Section 19):** 90%+ pass rate (30+ of 33)
- **Timeline (Section 20):** 85%+ pass rate (48+ of 56) — new feature, some polish acceptable
- **Timeline Export/Projects (Section 21):** 90%+ pass rate (14+ of 15)
- **CLI Performance Mode (Sections 22-27):** 90%+ pass rate (53+ of 59), zero failures in 23B (safety) and 27B (stability)
- **Web UI Perform Mode (Sections 28-34):** 90%+ pass rate (106+ of 117), zero failures in 34A (safety) and 34E (stability). **Test this first for live performance.**
- **Cycle 2 (Sections 36-40):** 90%+ pass rate, zero failures in color accuracy tests

---

## UAT CYCLE 2 — Bug Fix Re-Tests + New Features (2026-02-15)

> **Context:** These sections cover everything built AFTER UAT Cycle 1.
> Cycle 1 findings: `docs/UAT-FINDINGS-2026-02-15.md` (116 tracked items).
> Bug fixes applied, 4 new architecture features shipped, 115 effects total.

---

## SECTION 36: BUG FIX RE-TESTS (from Cycle 1 P0/P1)

> Re-test every bug fixed in the Feb 15 sprint. If any FAIL, it's a regression.

### 36A. P0 Fixes — Must All Pass

| # | Test | Steps | Expected | PASS/FAIL |
|---|------|-------|----------|-----------|
| 36A.1 | File upload works | Drag MP4 onto web UI | Video loads, preview shows first frame | |
| 36A.2 | Upload error shown | Drag non-video file (e.g. .txt) | Error toast appears, no crash | |
| 36A.3 | History order | Apply 3 effects, check history panel | Most recent at TOP, oldest at bottom | |
| 36A.4 | Brailleart renders | Add brailleart effect | Braille Unicode chars (not question marks) | |
| 36A.5 | Duotone reverts | Add duotone, adjust params, move back to defaults | Colors revert to original | |
| 36A.6 | Scanlines flickr | Add scanlines, move flickr slider full range | No crash, renders at all positions | |

### 36B. Pixel Physics (were broken, now fixed via frame_index)

| # | Test | Steps | Expected | PASS/FAIL |
|---|------|-------|----------|-----------|
| 36B.1 | Pixel gravity | Add pixelgravity, export 3-sec clip | Visible gravity displacement in output | |
| 36B.2 | Pixel haunt | Add pixelhaunt, export 3-sec clip | Visible ghosting/haunting effect | |
| 36B.3 | Pixel ink drop | Add pixelinkdrop, export 3-sec clip | Visible ink spread | |
| 36B.4 | Pixel liquify | Add pixelliquify, export 3-sec clip | Visible liquefaction | |
| 36B.5 | Pixel melt | Add pixelmelt, export 3-sec clip | Visible melting | |
| 36B.6 | Pixel time warp | Add pixeltimewarp, export 3-sec clip | Visible temporal distortion | |
| 36B.7 | Pixel vortex | Add pixelvortex, export 3-sec clip | Visible vortex spiral | |
| 36B.8 | Byte corrupt | Add bytecorrupt, adjust intensity | Visible corruption artifacts | |
| 36B.9 | Flow distort | Add flowdistort, adjust params | Visible flow displacement | |

**Note:** These effects are STATEFUL — they accumulate over multiple frames. The preview (single frame) may show subtle or no change. **Test by exporting a short clip**, not just preview.

### 36C. Other Fixes

| # | Test | Steps | Expected | PASS/FAIL |
|---|------|-------|----------|-----------|
| 36C.1 | Auto levels | Add autolevels to underexposed video | Visible brightness/contrast improvement | |
| 36C.2 | Histogram EQ | Add histogrameq to low-contrast video | Visible contrast expansion | |
| 36C.3 | Log slider scaling | Add an effect with wide float range (e.g. resonantfilter Q: 0-200) | Slider more sensitive at low values, less at high | |

---

## SECTION 37: COLOR SUITE (New — 4 effects)

> Photoshop-level color tools. Test with a video that has recognizable colors.

### 37A. Levels

| # | Test | Steps | Expected | PASS/FAIL |
|---|------|-------|----------|-----------|
| 37A.1 | Levels default | Add levels effect | No visible change (defaults are passthrough) | |
| 37A.2 | Black point | Set input_black to 50 | Shadows get crushed (darker areas clip to black) | |
| 37A.3 | White point | Set input_white to 200 | Highlights clip to white earlier | |
| 37A.4 | Gamma | Set gamma to 0.5 | Midtones get brighter | |
| 37A.5 | Gamma dark | Set gamma to 2.0 | Midtones get darker | |
| 37A.6 | Per-channel | Set channel to "r", adjust input_black to 80 | Only red channel affected, image gets cyan tint | |

### 37B. Curves

| # | Test | Steps | Expected | PASS/FAIL |
|---|------|-------|----------|-----------|
| 37B.1 | Curves default | Add curves effect | No visible change | |
| 37B.2 | S-curve | Set points to [[0,0],[64,32],[128,128],[192,224],[255,255]] | More contrast (darker darks, brighter brights) | |
| 37B.3 | Inverted | Set points to [[0,255],[255,0]] | Image inverts (negative) | |
| 37B.4 | Per-channel | Set channel to "b", brighten midpoint | Blue cast in midtones | |

### 37C. HSL Adjust

| # | Test | Steps | Expected | PASS/FAIL |
|---|------|-------|----------|-----------|
| 37C.1 | HSL default | Add hsladjust effect | Minimal/no change | |
| 37C.2 | Hue shift all | Set target_hue "all", hue_shift 90 | All colors rotate 90 degrees | |
| 37C.3 | Target reds | Set target_hue "reds", saturation -50 | Red areas desaturate, others unchanged | |
| 37C.4 | Lightness | Set lightness to 30 | Overall image brightens | |

### 37D. Color Balance

| # | Test | Steps | Expected | PASS/FAIL |
|---|------|-------|----------|-----------|
| 37D.1 | Color balance default | Add colorbalance effect | No visible change | |
| 37D.2 | Warm shadows | Adjust shadow_red positive, shadow_blue negative | Shadows get warm/amber | |
| 37D.3 | Cool highlights | Adjust highlight_blue positive | Highlights get cool/blue | |
| 37D.4 | Midtone shift | Adjust midtone_green positive | Midtones get green tint | |

---

## SECTION 38: LFO MAP OPERATOR (New)

> Ableton-style parameter modulation. Test requires adding an effect FIRST, then mapping LFO to its params.

### 38A. Map Flow

| # | Test | Steps | Expected | PASS/FAIL |
|---|------|-------|----------|-----------|
| 38A.1 | LFO panel visible | Click LFO toggle/button in effects panel | LFO panel appears with waveform selector, rate, depth | |
| 38A.2 | Map mode enter | Click "Map" button on LFO | UI enters map mode (visual indicator, knobs blink) | |
| 38A.3 | Map to parameter | In map mode, click a parameter knob on any effect | Knob shows "mapped" indicator, LFO link created | |
| 38A.4 | Map mode exit | Click "Map" again or press Escape | Map mode exits, mapped knob stays linked | |
| 38A.5 | LFO modulates param | Set LFO rate=2, depth=0.5, play/export a clip | Parameter value oscillates visibly in output | |

### 38B. Waveforms

| # | Test | Steps | Expected | PASS/FAIL |
|---|------|-------|----------|-----------|
| 38B.1 | Sine | Select sine waveform, map to brightness, export | Smooth oscillation | |
| 38B.2 | Square | Select square waveform | Hard on/off switching | |
| 38B.3 | Saw | Select saw waveform | Ramp up + instant reset | |
| 38B.4 | Triangle | Select triangle waveform | Linear ramp up + ramp down | |
| 38B.5 | Random (S&H) | Select random waveform | Stepped random values | |

### 38C. Multi-Mapping

| # | Test | Steps | Expected | PASS/FAIL |
|---|------|-------|----------|-----------|
| 38C.1 | Map to 2 params | Map LFO to param A on effect 1, then param B on effect 2 | Both params modulate simultaneously | |
| 38C.2 | Unmap | Right-click or unmap a mapped parameter | Parameter returns to static control | |
| 38C.3 | LFO in export | Export video with LFO active | Modulation baked into output video | |

---

## SECTION 39: UI IMPROVEMENTS (New)

### 39A. Collapsible Category Taxonomy

| # | Test | Steps | Expected | PASS/FAIL |
|---|------|-------|----------|-----------|
| 39A.1 | Categories visible | Open effects panel | Effects grouped by collapsible categories | |
| 39A.2 | Collapse/expand | Click a category header | Category collapses/expands, effects hide/show | |
| 39A.3 | All categories present | Count categories | Should see: ascii, color, destruction, distortion, dsp_filters, enhance, glitch, modulation, operators, physics, pixel, sidechain, temporal, texture (14 total) | |
| 39A.4 | Effect count per category | Expand each category | Total across all categories = 115 | |

### 39B. Quick Mode Status

| # | Test | Steps | Expected | PASS/FAIL |
|---|------|-------|----------|-----------|
| 39B.1 | Quick mode hidden | Load web UI | No "Quick" mode tab/button visible (flagged off) | |
| 39B.2 | Timeline default | Load web UI | Timeline is the default/primary mode | |

---

## SECTION 40: REGRESSION SUITE

> Quick smoke tests to confirm nothing broke.

| # | Test | Steps | Expected | PASS/FAIL |
|---|------|-------|----------|-----------|
| 40.1 | Server starts | `python3 server.py` | No errors, binds to :7860 | |
| 40.2 | Upload + preview | Upload video, add pixelsort | Preview shows sorted pixels | |
| 40.3 | Effect chain | Add blur → pixelsort → scanlines | All 3 visible in chain, preview shows combined | |
| 40.4 | Export MP4 | Export 3-sec clip with effects | MP4 file created, plays in QuickTime | |
| 40.5 | Perform mode | Switch to Perform mode, press 1-4 | Layers toggle, mixer responds | |
| 40.6 | Test suite | `python3 -m pytest tests/ -q` | 859+ passed, 0 failed | |

---

## SECTION 41: PARAMETER ACCORDION (New — Sprint)

> Essential/Advanced param grouping. 40 effects have `essential` arrays in control-map.json.

| # | Test | Steps | Expected | PASS/FAIL |
|---|------|-------|----------|-----------|
| 41.1 | Accordion visible | Add pixelsort → look at param panel | Only essential params shown, "+ N more" button visible | |
| 41.2 | Expand advanced | Click "+ N more" button | Advanced params reveal with smooth animation | |
| 41.3 | Collapse advanced | Click toggle again (shows "- less") | Advanced params hide, toggle returns to "+ N more" | |
| 41.4 | Advanced params work | Expand advanced, drag a knob | Preview updates — advanced params are functional | |
| 41.5 | No accordion when all essential | Add sharpen (1 param) | No toggle button shown — all params are essential | |
| 41.6 | Multi-param effect | Add smear or kaleidoscope | Essential params visible, 2+ advanced params behind toggle | |
| 41.7 | Accordion persists | Toggle advanced open → add another effect → return | Accordion state preserved across chain re-renders | |
| 41.8 | Unmapped effect | Add an effect NOT in control-map.json | All params shown normally (no accordion, no crash) | |

---

## SECTION 42: TIMELINE AUTOMATION LANES (New — Sprint)

> Ableton-quality breakpoint automation on timeline regions.

**Setup:** Switch to Timeline mode. Create a region (drag video). Add at least one effect to the region's chain.

| # | Test | Steps | Expected | PASS/FAIL |
|---|------|-------|----------|-----------|
| 42.1 | Create lane from device | Right-click effect device → "Automate: intensity" | Automation lane appears below track in timeline | |
| 42.2 | Create lane from knob | Right-click a param knob → "Create Automation Lane" | Lane created, knob shows colored dot indicator | |
| 42.3 | Add breakpoint (click line) | Click on the interpolated line in a lane | New breakpoint appears at click position | |
| 42.4 | Add breakpoint (double-click) | Double-click empty area in lane body | Breakpoint created at click frame/value | |
| 42.5 | Drag breakpoint | Click-drag a breakpoint dot | Point moves: X = frame, Y = 0-1 value. Constrained to lane bounds | |
| 42.6 | Fine drag (Shift) | Shift+drag a breakpoint vertically | Y moves at 4x precision (finer adjustment) | |
| 42.7 | Delete breakpoint | Right-click a breakpoint dot | Point removed, line re-interpolates | |
| 42.8 | Toggle visibility | Press 'A' key | All automation lanes show/hide | |
| 42.9 | Multiple lanes | Create 2 lanes on different params | Both render with different colors below the track | |
| 42.10 | Lane header | Look at lane left edge | Shows param name + color bar | |
| 42.11 | Preview responds | Add 3+ breakpoints, scrub playhead | Preview image changes as playhead passes breakpoints | |
| 42.12 | Bezier curves | Alt+drag a line segment between two points | Curve handle appears, line becomes smooth bezier | |
| 42.13 | Marquee selection | Click+drag in lane background (not on a point) | Dashed rectangle appears, enclosed breakpoints get selected | |
| 42.14 | Multi-point drag | Select 3+ points via marquee → drag one | All selected points move together | |
| 42.15 | Insert shape: Sine | Right-click lane → Insert Shape → Sine | Sine wave breakpoints appear across visible range | |
| 42.16 | Insert shape: Ramp | Right-click lane → Insert Shape → Ramp Up | Linear ascending breakpoints appear | |
| 42.17 | Copy breakpoints | Select breakpoints → Cmd+C | Toast or visual confirmation of copy | |
| 42.18 | Paste breakpoints | Move playhead → Cmd+V | Breakpoints paste at new playhead position | |
| 42.19 | Cross-lane paste | Copy from lane A → select lane B → Cmd+V | Points paste into different parameter's lane (normalized 0-1) | |
| 42.20 | Draw mode toggle | Press 'B' key | Draw mode indicator appears (or cursor changes) | |
| 42.21 | Draw mode stroke | In draw mode, click-drag across lane | Grid-quantized step automation created (one point per grid division) | |
| 42.22 | Simplify | Right-click lane → "Simplify" | Point count reduces while preserving curve shape (RDP algorithm) | |
| 42.23 | Delete selected | Select points → press Delete/Backspace | Selected breakpoints removed | |
| 42.24 | Serialize/load | Save timeline project → reload | Automation lanes and breakpoints persist after reload | |

---

## SECTION 43: FREEZE & FLATTEN (New — Sprint)

> Render-in-place for timeline regions. Pre-render effects for instant playback.

**Setup:** Timeline mode with a region that has 2+ effects applied.

| # | Test | Steps | Expected | PASS/FAIL |
|---|------|-------|----------|-----------|
| 43.1 | Freeze region | Right-click region → "Freeze" | Snowflake icon appears on region. Effects chain grays out (read-only) | |
| 43.2 | Frozen preview | Scrub playhead over frozen region | Preview loads instantly (pre-rendered frames) | |
| 43.3 | Frozen params locked | Try to drag a knob while frozen | Knob doesn't respond / params are visually read-only | |
| 43.4 | Unfreeze | Right-click frozen region → "Unfreeze" | Snowflake disappears. Effects chain becomes editable again | |
| 43.5 | Unfreeze restores params | After unfreeze, drag a knob | Knob works, live preview resumes | |
| 43.6 | Flatten | Freeze first → right-click → "Flatten" | Confirmation dialog appears: "This will permanently bake effects..." | |
| 43.7 | Flatten confirm | Click "OK" on flatten dialog | Effects removed from chain. Region label shows "[flattened]". Video now contains baked effects. | |
| 43.8 | Flatten is destructive | After flatten, check effect chain | Chain is empty — effects are baked into the video permanently | |

---

## SECTION 44: OPERATOR MAPPING EXPANSION (New — Sprint)

> Extended modulation mapping: knob context menus, automation lane indicators.

| # | Test | Steps | Expected | PASS/FAIL |
|---|------|-------|----------|-----------|
| 44.1 | Knob right-click menu | Right-click any param knob | Context menu: "Create Automation Lane", "Map to LFO" | |
| 44.2 | Create lane from knob | Right-click knob → "Create Automation Lane" | Lane appears in timeline. Knob gets colored dot badge | |
| 44.3 | Auto-mapped indicator | After creating automation lane, look at the knob | Colored dot (matches lane color) on top-right of knob | |
| 44.4 | Show automation lane | Right-click an auto-mapped knob → "Show Automation Lane" | Timeline scrolls to / highlights the automation lane | |
| 44.5 | Delete lane from knob | Right-click auto-mapped knob → "Delete Automation Lane" | Lane removed. Colored dot disappears from knob | |
| 44.6 | LFO + Automation combined | Map knob to LFO AND create automation lane | Knob shows both tilde (~) and color glow | |
| 44.7 | Map to LFO from knob | Right-click knob → "Map to LFO" | Same behavior as the Map button — knob gets LFO-mapped | |
| 44.8 | Unmap LFO from knob | Right-click LFO-mapped knob → "Unmap from LFO" | LFO mapping removed, knob becomes draggable again | |

---

## UPDATED SCORING SUMMARY (Cycle 3)

| Section | Tests | Pass | Fail | Skip |
|---------|-------|------|------|------|
| 36. Bug Fix Re-Tests | 18 | | | |
| 37. Color Suite | 18 | | | |
| 38. LFO Map Operator | 13 | | | |
| 39. UI Improvements | 6 | | | |
| 40. Regression Suite | 6 | | | |
| 41. Parameter Accordion | 8 | | | |
| 42. Timeline Automation Lanes | 24 | | | |
| 43. Freeze & Flatten | 8 | | | |
| 44. Operator Mapping Expansion | 8 | | | |
| **Cycle 3 Total** | **109** | | | |
| **Grand Total (Cycle 1 + 2 + 3)** | **581** | | | |

**Cycle 3 ship criteria:**
- Sections 36-37: 100% pass (bug fixes + new effects must work)
- Section 38: 90%+ pass (LFO is new, some polish OK)
- Section 39-40: 100% pass (UI + regression = must pass)
- Section 41: 100% pass (accordion is simple, must work)
- Section 42: 85%+ pass (automation lanes are complex, edge cases expected)
- Section 43: 100% pass (freeze/flatten is critical workflow)
- Section 44: 90%+ pass (mapping expansion, polish OK)

---

## UAT CYCLE 4 — UX Refactor + Whimsy + Performance Features (2026-02-15)

> **Added:** UX refactor (Don Norman heuristic analysis), 8 whimsy effects, performance automation features
> **Version:** v0.7.0-dev (123 effects, 12 categories, 16 packages)

---

## SECTION 45: UX REFACTOR — SEARCH & DISCOVERY

| # | Test | Steps | Expected Result | Pass/Fail | Notes |
|---|------|-------|-----------------|-----------|-------|
| 45.1 | Effect search bar visible | Open browser panel | Search input visible at top of effect browser | | |
| 45.2 | Search filters effects | Type "pixel" in search bar | Only effects with "pixel" in name/description shown; matching categories auto-expand | | |
| 45.3 | Search clears | Clear search text | All effects visible again, categories return to normal state | | |
| 45.4 | Search empty state | Type "zzzzz" (no matches) | "No effects matching" message shown | | |
| 45.5 | Search is case-insensitive | Type "BLUR" | blur effect appears | | |
| 45.6 | Search by description | Type "cinematic" | Effects with "cinematic" in description shown | | |

---

## SECTION 46: UX REFACTOR — FAVORITES

| # | Test | Steps | Expected Result | Pass/Fail | Notes |
|---|------|-------|-----------------|-----------|-------|
| 46.1 | Star icon on effects | Hover over any effect item | Star icon visible on left of effect name | | |
| 46.2 | Toggle favorite | Click star icon on an effect | Star fills yellow; effect added to favorites | | |
| 46.3 | Favorites persist | Refresh page | Previously favorited effects still have yellow star | | |
| 46.4 | Favorites tab | Click star tab in browser header | Only favorited effects shown | | |
| 46.5 | Unfavorite from list | Click star on favorited effect | Star unfills; effect removed from favorites view | | |
| 46.6 | Right-click favorite | Right-click effect item | Context menu includes "Add to Favorites" / "Remove from Favorites" | | |
| 46.7 | Empty favorites | Open favorites tab with none favorited | Empty state message shown | | |

---

## SECTION 47: UX REFACTOR — INFO VIEW & PREVIEWS

| # | Test | Steps | Expected Result | Pass/Fail | Notes |
|---|------|-------|-----------------|-----------|-------|
| 47.1 | Info view panel visible | Look at bottom-left area | Info view panel with "Info" label visible | | |
| 47.2 | Hover shows info | Hover over any effect in browser | Info view shows effect name, category, description | | |
| 47.3 | Hover preview thumbnail | Hover over effect for >400ms | Tooltip with thumbnail preview of effect appears near cursor | | |
| 47.4 | Preview dismisses | Move mouse away from effect | Thumbnail tooltip disappears | | |
| 47.5 | Preview caching | Hover same effect twice | Second hover shows preview faster (cached) | | |
| 47.6 | Preview requires uploaded video | Hover with no video loaded | No preview shown (graceful, no error) | | |

---

## SECTION 48: UX REFACTOR — COMPLEXITY METER & PRESETS

| # | Test | Steps | Expected Result | Pass/Fail | Notes |
|---|------|-------|-----------------|-----------|-------|
| 48.1 | Complexity meter visible | Add 1+ effects to chain | Complexity indicator shows count + severity (Light/Medium/Heavy) | | |
| 48.2 | Buffer count shown | Play video with effects | Buffer indicator shows "Buf: N/30" | | |
| 48.3 | Click to clear cache | Click complexity meter | Frame cache cleared; toast notification shown | | |
| 48.4 | Parameter preset save | In device panel, use preset dropdown > "Save" | Prompt for name; preset saved | | |
| 48.5 | Parameter preset load | Select saved preset from dropdown | All params for that effect restored to saved values | | |
| 48.6 | Parameter preset delete | Select preset, choose "Delete" | Preset removed from dropdown | | |
| 48.7 | Presets persist | Refresh page, re-add same effect | Saved presets still available in dropdown | | |
| 48.8 | Default preset | Select "Default" from dropdown | All params reset to effect defaults | | |

---

## SECTION 49: UX REFACTOR — AUTOMATION & TIMELINE

| # | Test | Steps | Expected Result | Pass/Fail | Notes |
|---|------|-------|-----------------|-----------|-------|
| 49.1 | Lane param switching | Right-click automation lane header | Context menu shows "Switch Parameter" with available params | | |
| 49.2 | Switch param | Select different parameter from submenu | Lane header updates to new param name; keyframes cleared | | |
| 49.3 | Lane dropdown triangle | Look at lane header text | Small triangle indicator after param name signals dropdown | | |
| 49.4 | Perform bake to timeline | Record a perform session, stop | Toast offers "Bake to Timeline" option | | |
| 49.5 | Bake creates lanes | Click "Bake to Timeline" | Automation lanes created from perform session events | | |

---

## SECTION 50: WHIMSY EFFECTS (8 new effects)

| # | Test | Steps | Expected Result | Pass/Fail | Notes |
|---|------|-------|-----------------|-----------|-------|
| 50.1 | Whimsy category | Open effect browser | "WHIMSY" category visible with 8 effects | | |
| 50.2 | Kaleidoscope basic | Add kaleidoscope, render | Mirror-segment kaleidoscope visible; segments param works | | |
| 50.3 | Kaleidoscope moods | Test classic/psychedelic/gentle moods | Each mood produces distinct look | | |
| 50.4 | Soft bloom basic | Add softbloom, render | Soft glow/bloom visible on bright areas | | |
| 50.5 | Shape overlay basic | Add shapeoverlay, render | Geometric shapes overlaid on frame | | |
| 50.6 | Shape types | Test circle/triangle/square/hexagon/star/diamond | Each shape renders correctly | | |
| 50.7 | Lens flare basic | Add lensflare, render | Lens flare at specified position | | |
| 50.8 | Lens flare animation | Enable animate, render sequence | Flare drifts across frame | | |
| 50.9 | Watercolor basic | Add watercolor, render | Painterly/watercolor effect visible | | |
| 50.10 | Rainbow shift basic | Add rainbowshift, render | Color-shifting rainbow overlay | | |
| 50.11 | Rainbow directions | Test horizontal/vertical/diagonal/radial | Each direction works | | |
| 50.12 | Sparkle basic | Add sparkle, render | Sparkle/glitter particles visible | | |
| 50.13 | Sparkle animation | Enable animate, render sequence | Sparkles twinkle/move between frames | | |
| 50.14 | Film grain warm | Add filmgrainwarm, render | Warm-tinted film grain overlay | | |
| 50.15 | Whimsy in chain | Chain 2+ whimsy effects | Effects compose correctly | | |
| 50.16 | Whimsy recipes | Load fairy-tale recipe from packages | Multi-effect chain applies correctly | | |

---

## SECTION 51: PERFORMANCE AUTOMATION — KEYBOARD INPUT (Planned)

> **Status:** PLANNED — Not yet implemented. Tests below define acceptance criteria.

| # | Test | Steps | Expected Result | Pass/Fail | Notes |
|---|------|-------|-----------------|-----------|-------|
| 51.1 | Keyboard mode toggle | Press M key | Status bar shows "KEYS: ON" indicator; keyboard now triggers effects | | |
| 51.2 | Keys trigger effects | In keyboard mode, press Q/W/E/R | Corresponding channel triggers fire | | |
| 51.3 | Key mapping visible | Open help panel (H or ?) | Current keyboard-to-trigger mapping shown | | |
| 51.4 | Remap keys | Open key mapping dialog | User can reassign which keys trigger which effects | | |
| 51.5 | Drum rack layout | Map QWERTY row to different effects | Each key triggers a different effect/layer (like Ableton Drum Rack) | | |
| 51.6 | Typing vs performing | With keyboard mode on, click search bar | Keyboard mode temporarily disables; search input works normally | | |
| 51.7 | Mode persists | Toggle keyboard mode on, switch panels | Mode stays active across panel changes | | |

---

## SECTION 52: PERFORMANCE AUTOMATION — RECORD / OVERDUB (Planned)

> **Status:** PLANNED — Not yet implemented.

| # | Test | Steps | Expected Result | Pass/Fail | Notes |
|---|------|-------|-----------------|-----------|-------|
| 52.1 | Separate Rec/Overdub buttons | Look at perform transport | Two distinct buttons: Record (red) and Overdub (amber) | | |
| 52.2 | Record replaces | Hit Record, trigger effects, stop | New recording replaces previous take on those channels | | |
| 52.3 | Overdub layers | Hit Overdub, trigger effects, stop | New triggers added ON TOP of existing recording | | |
| 52.4 | Visual distinction | Compare active states | Record = solid red. Overdub = blinking amber/yellow. Clear difference. | | |
| 52.5 | Overdub preserves | Record take 1. Overdub take 2. Play back. | Both takes play back combined | | |

---

## SECTION 53: PERFORMANCE AUTOMATION — AUTOMATION RECORDING (Planned)

> **Status:** PLANNED — Not yet implemented.

| # | Test | Steps | Expected Result | Pass/Fail | Notes |
|---|------|-------|-----------------|-----------|-------|
| 53.1 | Automation arm | Toggle automation record mode | Arm indicator visible; knob movements will be recorded | | |
| 53.2 | Record knob movement | Arm automation, play, turn a knob | Knob movement recorded as automation breakpoints on timeline | | |
| 53.3 | Multi-param recording | Turn multiple knobs during armed playback | Each knob's movement recorded to its own automation lane | | |
| 53.4 | Automation playback | Stop recording, play timeline | Knobs move automatically following recorded automation | | |
| 53.5 | Automation view toggle | Press A key | Automation lanes show/hide on timeline | | |
| 53.6 | Visual feedback | Knob being recorded | Knob ring turns red/pulsing while recording automation | | |

---

## SECTION 54: PERFORMANCE AUTOMATION — MIDI CAPTURE BUFFER (Planned)

> **Status:** PLANNED — Highest priority. Not yet implemented.

| # | Test | Steps | Expected Result | Pass/Fail | Notes |
|---|------|-------|-----------------|-----------|-------|
| 54.1 | Silent buffering active | No record button pressed; perform triggers | System silently buffers last N seconds of input | | |
| 54.2 | Capture button visible | Look at transport | "Capture" button (or Cmd+Shift+C) visible near Record | | |
| 54.3 | Capture claims buffer | Press Capture after performing without Record | Last N seconds of performance recovered and placed on timeline | | |
| 54.4 | Buffer length setting | Check settings/preferences | Configurable buffer length (default: 60 seconds) | | |
| 54.5 | Buffer wraps | Perform for longer than buffer length | Only last N seconds available; oldest data overwritten | | |
| 54.6 | Capture + automation | Perform with knobs AND triggers without Record, then Capture | Both trigger events AND knob automation captured | | |
| 54.7 | Visual indicator | Buffering active | Subtle indicator showing buffer is recording (small dot or ring) | | |
| 54.8 | Empty buffer | Press Capture with no recent input | Toast: "Nothing to capture" (no crash, graceful) | | |

---

## SECTION 55: PERFORMANCE AUTOMATION — MIDI CONTROLLER (Planned)

> **Status:** PLANNED — Not yet implemented.

| # | Test | Steps | Expected Result | Pass/Fail | Notes |
|---|------|-------|-----------------|-----------|-------|
| 55.1 | MIDI device detected | Connect MIDI controller, open app | Status shows "MIDI: [device name] connected" | | |
| 55.2 | MIDI learn mode | Right-click any knob > "MIDI Learn" | Knob highlights; next MIDI CC input maps to it | | |
| 55.3 | MIDI note triggers | Press MIDI key | Corresponding effect/channel triggered | | |
| 55.4 | MIDI CC controls | Turn MIDI knob mapped to param | Parameter value follows MIDI input | | |
| 55.5 | MIDI mapping visible | Open MIDI map view | All current MIDI mappings listed (CC# -> param name) | | |
| 55.6 | MIDI mapping persists | Close/reopen app with same controller | Mappings restored | | |
| 55.7 | Multiple controllers | Connect 2 MIDI devices | Both recognized; independent mappings | | |

---

## SECTION 56: PERFORMANCE AUTOMATION — MACROS (Planned)

> **Status:** PLANNED — Not yet implemented.

| # | Test | Steps | Expected Result | Pass/Fail | Notes |
|---|------|-------|-----------------|-----------|-------|
| 56.1 | Macro knobs visible | Open macro panel | 8 macro knobs displayed (like Ableton Rack macros) | | |
| 56.2 | Map param to macro | Right-click param knob > "Map to Macro 1" | Param now controlled by Macro 1 | | |
| 56.3 | Multi-param macro | Map 3 different params to Macro 1 | Turning Macro 1 moves all 3 params simultaneously | | |
| 56.4 | Macro ranges | Set min/max per mapping | Each param mapped to different sub-range of macro rotation | | |
| 56.5 | Macro + MIDI | Map MIDI CC to a macro knob | Physical knob controls multiple params at once | | |
| 56.6 | Macro naming | Double-click macro label | Rename macro (e.g., "Chaos Amount") | | |

---

## UPDATED SCORING SUMMARY (Cycle 4)

| Section | Tests | Pass | Fail | Skip |
|---------|-------|------|------|------|
| 45. Search & Discovery | 6 | | | |
| 46. Favorites | 7 | | | |
| 47. Info View & Previews | 6 | | | |
| 48. Complexity Meter & Presets | 8 | | | |
| 49. Automation & Timeline | 5 | | | |
| 50. Whimsy Effects | 16 | | | |
| 51. Keyboard Input (Planned) | 7 | | | |
| 52. Record / Overdub (Planned) | 5 | | | |
| 53. Automation Recording (Planned) | 6 | | | |
| 54. MIDI Capture Buffer (Planned) | 8 | | | |
| 55. MIDI Controller (Planned) | 7 | | | |
| 56. Macros (Planned) | 6 | | | |
| **Cycle 4 Total** | **87** | | | |
| **Grand Total (Cycles 1-4)** | **668** | | | |

**Cycle 4 ship criteria:**
- Sections 45-50: 100% pass (shipped features, must work)
- Sections 51-56: N/A (planned — acceptance criteria only, not yet testable)

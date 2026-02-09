# Entropic v0.4.2 — Effects & Packages Reference

> **Date:** 2026-02-08
> **Version:** 0.4.2
> **Stats:** 65 effects, 8 categories, 12 packages, 76 recipes (16 NUCLEAR), region selection (13 presets), 520 tests

---

## Effects Summary (65 total)

### GLITCH (4)
| Effect | Description | Key Params |
|--------|-------------|------------|
| `pixelsort` | Sort pixels by brightness, hue, or saturation | threshold, sort_by, direction |
| `channelshift` | Offset RGB channels independently | r_offset, g_offset, b_offset |
| `displacement` | Randomly displace image blocks | block_size, intensity, seed |
| `bitcrush` | Reduce color depth and/or resolution | color_depth, resolution_scale |

### DISTORTION (5)
| Effect | Description | Key Params |
|--------|-------------|------------|
| `wave` | Sine wave displacement distortion | amplitude, frequency, direction |
| `mirror` | Mirror one half onto the other | axis, position |
| `chromatic` | RGB channel split (lens aberration) | offset, direction |
| `pencilsketch` | Pencil sketch drawing effect | sigma_s, sigma_r, shade |
| `smear` | Cumulative paint-smear streaks | direction, decay |

### TEXTURE (11)
| Effect | Description | Key Params |
|--------|-------------|------------|
| `scanlines` | CRT/VHS scan line overlay | line_width, opacity, flicker |
| `vhs` | VHS tape degradation simulation | tracking, noise_amount, color_bleed |
| `noise` | Add grain/noise overlay | amount, noise_type |
| `blur` | Box or motion blur | radius, blur_type |
| `sharpen` | Sharpen/enhance edges | amount |
| `edges` | Edge detection (overlay/neon/edges-only) | threshold, mode |
| `posterize` | Reduce to N color levels per channel | levels |
| `tvstatic` | TV static with horizontal sync drift | intensity, sync_drift |
| `contours` | Topographic contour lines | levels |
| `asciiart` | Convert frame to ASCII art (basic/dense/block, mono/green/amber/original) | charset, width, color_mode, edge_mix |
| `brailleart` | Braille unicode art (2×4 dot grid, 4× resolution, Floyd-Steinberg dither) | width, threshold, dither, color_mode |

### COLOR (9)
| Effect | Description | Key Params |
|--------|-------------|------------|
| `hueshift` | Rotate the hue wheel | degrees |
| `contrast` | Extreme contrast manipulation | amount, curve |
| `saturation` | Boost or kill saturation | amount, channel |
| `exposure` | Push exposure up or down | stops, clip_mode |
| `invert` | Full or partial color inversion | channel, amount |
| `temperature` | Warm/cool color temperature shift | temp |
| `tapesaturation` | Analog tape saturation curve | drive, warmth |
| `cyanotype` | Prussian blue cyanotype print | intensity |
| `infrared` | Infrared film simulation | vegetation_glow |

### TEMPORAL (9)
| Effect | Description | Key Params |
|--------|-------------|------------|
| `stutter` | Freeze-stutter at intervals | repeat, interval |
| `dropout` | Random frame drops to black | drop_rate |
| `timestretch` | Speed change with artifacts | speed |
| `feedback` | Ghost trails (video echo) | decay |
| `tapestop` | Tape machine stopping effect | trigger, ramp_frames |
| `tremolo` | Brightness LFO oscillation | rate, depth |
| `delay` | Ghost echo from N frames ago | delay_frames, decay |
| `decimator` | Reduce effective framerate | factor |
| `samplehold` | Freeze at random intervals | hold_min, hold_max |

### MODULATION (4)
| Effect | Description | Key Params |
|--------|-------------|------------|
| `ringmod` | Sine wave carrier modulation | frequency, direction |
| `gate` | Black out below threshold | threshold, mode |
| `wavefold` | Audio wavefolding on brightness | threshold, folds |
| `amradio` | AM radio interference bands | carrier_freq, depth |

### ENHANCE (9)
| Effect | Description | Key Params |
|--------|-------------|------------|
| `solarize` | Sabattier/Man Ray effect | threshold |
| `duotone` | Two-color gradient mapping | shadow_color, highlight_color |
| `emboss` | 3D raised/carved texture | amount |
| `autolevels` | Auto-contrast histogram stretch | cutoff |
| `median` | Median filter (watercolor) | size |
| `falsecolor` | Luminance to false-color palette | colormap |
| `histogrameq` | Per-channel histogram equalization | — |
| `clahe` | Adaptive local contrast (night vision) | clip_limit, grid_size |
| `parallelcompress` | NY compression for video | crush, blend |

### DESTRUCTION (14) — THE NUCLEAR ARSENAL
| Effect | Description | Key Params | Max Destruction |
|--------|-------------|------------|----------------|
| `datamosh` | 8-mode datamosh (melt/bloom/rip/replace/annihilate/freeze_through/pframe_extend/donor) | intensity, mode, decay, motion_threshold, macroblock_size, donor_offset, blend_mode | annihilate @ 50+ |
| `bytecorrupt` | JPEG data bending | amount (1-500), jpeg_quality | amount=300, quality=1 |
| `blockcorrupt` | Macroblock corruption (6 modes incl. smear) | num_blocks (1-200), block_size, mode | 150 blocks, random |
| `rowshift` | Horizontal scanline tearing | max_shift (1-full width), density | full width, density=1.0 |
| `jpegdamage` | Triple JPEG compression + block damage | quality (1-30), block_damage (0-200) | quality=1, damage=150 |
| `invertbands` | Alternating inverted horizontal bands | band_height, offset | height=3 |
| `databend` | Audio DSP on pixels (5 effects incl. feedback) | effect, intensity | feedback @ 1.0 |
| `flowdistort` | Optical flow displacement map | strength (0.5-50) | 40+ |
| `filmgrain` | Realistic brightness-responsive grain | intensity (0.0-2.0), grain_size (1-8) | 1.5, size 5+ |
| `glitchrepeat` | Buffer overflow slice repeat | num_slices (1-60), max_height | 50 slices, height=100 |
| `xorglitch` | Bitwise XOR corruption | pattern, mode (fixed/random/gradient) | random |
| `pixelannihilate` | Kill pixels (dissolve/threshold/edge/channel) | threshold, mode, replacement | dissolve @ 0.8 |
| `framesmash` | One-stop apocalypse (6 techniques stacked) | aggression (0.0-1.0) | 1.0 |
| `channeldestroy` | Rip channels apart (5 modes) | mode, intensity | separate @ 1.0 |

---

## Datamosh Modes (Deep Dive)

The datamosh effect is the crown jewel. It uses OpenCV optical flow to simulate real I-frame removal.
v0.4 adds 3 new modes based on real datamosh tutorial analysis (Avidemux/AE workflows).

| Mode | What It Does | Visual Result |
|------|-------------|---------------|
| `melt` | Warps PREVIOUS frame by current motion vectors. Compounds each frame. | Classic datamosh — pixels progressively detach from reality |
| `bloom` | Smears previous frame outward. Nothing from current frame enters. | Old image smears and bleeds, frozen in time |
| `rip` | Flow vectors amplified 10x + random noise bursts injected | Violent pixel tearing, chunks fly across frame |
| `replace` | Blocks of previous frame randomly stamped over current | I-frame skip — blocky frozen patches |
| `annihilate` | ALL above + row displacement + channel separation | Total destruction — warp + blocks + tears + color split |
| `freeze_through` | Previous frame frozen. Only macroblocks where motion exceeds threshold update. | Authentic I-frame removal — old image persists, new movement "breaks through" |
| `pframe_extend` | Captures motion vectors from one moment, repeats/amplifies them over time. | Bloom/glide look — pixels stretch along their motion path |
| `donor` | Motion from current frame, pixel data pulled from a different temporal position. | Cross-clip feeding — motion drives pixels from another time |

### New Parameters (v0.4)

| Parameter | Default | Range | What It Does |
|-----------|---------|-------|-------------|
| `motion_threshold` | 0.0 | 0.0–50.0 | Only update pixels where motion exceeds this value. 0 = off. Higher = more static preservation. |
| `macroblock_size` | 16 | 8, 16, 32 | Block size for freeze_through mode. 8 = fine detail, 16 = codec-authentic, 32 = chunky. |
| `donor_offset` | 10 | 1–999 | How many frames back to pull donor pixels from. Higher = more temporal displacement. |
| `blend_mode` | "normal" | normal/multiply/average/swap | Post-processing blend between result and current frame. |

### Blend Modes

| Mode | Effect |
|------|--------|
| `normal` | No blend — use result as-is |
| `multiply` | Multiply result × current frame (darkens, creates depth) |
| `average` | 50/50 average of result and current frame |
| `swap` | Replace result with current frame where motion is strong |

**Intensity guide:**
- 1.0 = Visible effect
- 5.0 = Insane
- 20.0 = Apocalyptic
- 50.0 = Nuclear
- 100.0 = Maximum (engine limit)

---

## Packages (12 packages, 76 recipes)

### 1. analog-decay (5 recipes)
VHS tapes, film reels, broadcast signals breaking down.
- `light-wear` — Barely degraded VHS
- `worn-tape` — Played 100 times, tracking wobbles
- `destroyed-tape` — Left in a hot car for a decade
- `broadcast-signal` — Bad antenna, horizontal tears
- **`nuclear-analog`** — VHS left in a bonfire. Maximum everything.

### 2. digital-corruption (5 recipes)
Data rot, compression artifacts, block displacement.
- `minor-glitch` — Small block displacement
- `data-rot` — Bitcrushed with posterized colors
- `full-corruption` — Maximum data destruction
- `pixel-sort` — Clean pixel sorting
- **`nuclear-digital`** — Max displacement, 1-bit color, XOR, frame smash

### 3. color-lab (5 recipes)
Color grading and manipulation.
- `warm-grade` — Golden warmth
- `cold-grade` — Ice blue, clinical
- `psychedelic` — Cranked hue shift, acid trip
- `duotone-poster` — Two-color graphic design
- `thermal-map` — False color heat vision

### 4. temporal-chaos (6 recipes)
Time manipulation — frames stutter, echo, drop.
- `subtle-stutter` — Light frame holding
- `echo-trail` — Ghost trails, dreamy
- `choppy-lofi` — Surveillance cam feel
- `signal-loss` — Random frames drop to black
- `tape-death` — Tape machine stopping
- **`nuclear-temporal`** — Max stutter + dropout + decimation + feedback + strobe

### 5. distortion-engine (5 recipes)
Spatial warping — waves, mirrors, displacement.
- `gentle-wave` — Underwater feeling
- `mirror-world` — Rorschach test
- `earthquake` — Nothing stays put
- `melt` — Image melts upward
- **`nuclear-distortion`** — Max wave + displacement + channel rip + sort

### 6. enhancement-suite (5 recipes)
Artistic filters and transforms.
- `auto-correct` — Auto-levels + sharpen
- `neon-edges` — Tron vibes
- `watercolor` — Painterly, soft
- `sabattier` — Solarization
- `embossed-metal` — Carved in stone

### 7. signal-processing (5 recipes)
Audio-inspired effects on video.
- `ring-mod` — AM radio for video
- `noise-gate` — High contrast cutoff
- `strobe` — Club strobe effect
- `full-signal-chain` — Ring mod + gate + scanlines
- **`nuclear-signal`** — Max ring mod + hard gate + strobe + databend + XOR

### 8. total-destruction (15 recipes)
Maximum violence. The file fights back. v0.4 adds 7 new datamosh recipes from transcript learnings.
- `light-datamosh` — Gentle flow warping
- `heavy-datamosh` — Full melt
- **`datamosh-rip`** — Motion vectors amplified with noise
- **`datamosh-annihilate`** — All datamosh modes combined
- `data-bent` — JPEG bytes corrupted
- `block-massacre` — Random macroblocks destroyed
- `audio-on-video` — Audio feedback + distortion on pixels
- `everything-breaks` — ALL destruction at once
- `freeze-through` — Authentic I-frame removal (16px macroblocks, motion threshold 1.5)
- `freeze-through-fine` — Fine-detail I-frame removal (8px macroblocks)
- `bloom-glide` — P-frame extend with 0.98 decay (smooth motion stretch)
- **`bloom-glide-nuclear`** — Nuclear P-frame extend + channel separation
- `donor-mosh` — Cross-clip pixel feeding (10-frame offset)
- `multiply-mosh` — Melt with multiply blend (darker, deeper)
- `swap-mosh` — Melt with motion-gated swap blend

### 9. motion-warp (5 recipes)
Optical flow effects — react to motion in video.
- `flow-push` — Pixels pushed forward
- `flow-pull` — Pixels pulled backward
- `melt-cascade` — Datamosh + echo, everything melts
- `motion-stutter` — Flow distortion + frame stutter
- **`nuclear-flow`** — Max flow distortion + channel rip

### 10. NUCLEAR (8 recipes) — THE FINAL BOSS
The most extreme settings for every effect. Nothing subtle.
- **`nuclear-datamosh`** — Annihilate mode at intensity 50
- **`nuclear-smash`** — Frame smash at aggression 1.0
- **`nuclear-corrupt`** — Max byte + block + JPEG corruption
- **`nuclear-channel`** — Channels ripped + XOR + pixel death
- **`nuclear-databend`** — Audio feedback loop on pixels (diff=130.6)
- **`nuclear-teardown`** — Max row shift + 50 glitch slices + invert bands
- **`nuclear-everything`** — Every technique at maximum. The final boss.
- **`nuclear-analog`** — VHS + displacement + bitcrush + wave + grain

### 11. datamosh-combos (6 recipes)
Real datamosh (H.264 P-frame manipulation) + Entropic per-frame effects.
- `mosh-then-sort` — Real datamosh → pixel sort into streaks
- `mosh-vhs` — Real datamosh → VHS degradation
- `mosh-feedback` — Real datamosh → video echo + scanlines
- `mosh-color-rip` — Real datamosh → hue shift + channel rip
- `mosh-databend` — Real datamosh → audio DSP on pixels
- **`mosh-nuclear-combo`** — DOUBLE datamosh: real + simulated + byte corrupt

### 12. ascii-art (6 recipes)
Convert video frames to ASCII and braille unicode art. Inspired by ASCII-generator (8K stars),
ascii-image-converter (3K stars), video-to-ascii (1.8K stars).
- `terminal-mono` — Classic white-on-black ASCII art (basic charset)
- `matrix-rain` — Green phosphor terminal (dense charset + scanlines)
- `amber-crt` — Retro amber terminal (block charset + scanlines + noise)
- `braille-hires` — Braille unicode art at 4× resolution (Floyd-Steinberg dithered)
- `edge-ascii` — Edge-detected ASCII art (Sobel outlines pop in dense charset)
- **`nuclear-ascii`** — Inverted braille + scanlines + salt & pepper noise

---

## Test Results (2026-02-08)

| Metric | Value |
|--------|-------|
| Total effects | 65 |
| Total packages | 12 |
| Total recipes | 76 |
| Nuclear recipes | 16 |
| Tests passing | 455 |
| Recipes rated NUCLEAR (diff>50) | 40/57 original (70%) + new modes TBD |
| Highest destruction | nuclear-databend (diff=130.6, 100% pixels changed) |
| Zero errors in full matrix | YES |

---

## Region Selection (NEW in v0.4.2)

Apply any effect to a rectangular sub-region of the frame. Works with all 65 effects.

### Usage

```bash
# Apply to a preset region
python3 entropic.py apply <project> invert --region center
python3 entropic.py apply <project> pixelsort --region top-half threshold=0.5

# Apply to pixel coordinates (x, y, width, height)
python3 entropic.py apply <project> noise amount=0.8 --region "100,50,200,150"

# Apply to percentage coordinates (0.0–1.0)
python3 entropic.py apply <project> hueshift degrees=90 --region "0.25,0.1,0.5,0.8"

# Feathered edges (smooth blend at region boundary)
python3 entropic.py apply <project> invert --region center --feather 20
```

### Region Presets (13)

| Preset | Area |
|--------|------|
| `center` | Center 50% |
| `top-half` / `bottom-half` | Top/bottom 50% |
| `left-half` / `right-half` | Left/right 50% |
| `top-left` / `top-right` / `bottom-left` / `bottom-right` | Corner quadrants (50×50%) |
| `center-strip` | Horizontal strip (center 50% height) |
| `thirds-left` / `thirds-center` / `thirds-right` | Rule of thirds columns |

### Region Params

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `--region` | string | None (full frame) | Preset name, "x,y,w,h" pixels, or "0.x,0.y,0.w,0.h" percent |
| `--feather` | int | 0 | Edge blend radius in pixels (0 = hard edge) |

### Composing Regions

Apply different effects to different regions in sequence:
```bash
# Invert top, posterize bottom
python3 entropic.py apply <project> invert --region top-half
python3 entropic.py apply <project> posterize levels=2 --region bottom-half
```

### Programmatic API

```python
from effects import apply_effect
import numpy as np

frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)

# With preset
result = apply_effect(frame, "pixelsort", region="center", feather=10)

# With coordinates
result = apply_effect(frame, "noise", amount=0.5, region="100,50,200,150")

# With percent
result = apply_effect(frame, "hueshift", degrees=90, region="0.25,0.0,0.5,1.0")
```

---

## CLI Usage

```bash
# List all packages
python3 entropic_packages.py list

# Explore recipes in a package
python3 entropic_packages.py explore nuclear

# Apply single recipe
python3 entropic_packages.py apply <project> --package nuclear --recipe nuclear-everything

# Batch render all recipes in a package
python3 entropic_packages.py batch <project> --package nuclear

# Full matrix (all packages, all recipes)
python3 entropic_packages.py matrix <project>

# Direct effect with custom params
python3 entropic.py apply <project> datamosh intensity=50 mode=annihilate decay=0.999

# Mix (dry/wet blend)
python3 entropic.py apply <project> framesmash aggression=1.0 mix=0.5
```

---

## Architecture

```
effects/
├── __init__.py          # Master registry (65 effects)
├── pixelsort.py         # Pixel sorting
├── channelshift.py      # Channel offset
├── scanlines.py         # CRT scanlines
├── bitcrush.py          # Bit depth reduction
├── color.py             # 9 color effects
├── distortion.py        # 5 distortion effects
├── texture.py           # 9 texture effects
├── temporal.py          # 9 temporal effects
├── modulation.py        # 4 modulation effects
├── enhance.py           # 9 enhancement effects
├── destruction.py       # 14 destruction effects (NUCLEAR)
└── ascii.py             # 2 ASCII/braille art effects

core/
├── safety.py            # Input validation, timeouts, path traversal protection
├── preview.py           # 3-tier render (lo/mid/hi)
├── project.py           # Project management (~/.entropic/projects/)
├── recipe.py            # Recipe CRUD, branching, favorites
├── video_io.py          # FFmpeg frame extraction + reassembly
└── analysis.py          # CV-powered video analysis (OpenCV)

packages.py              # 12 packages, 76 recipes
entropic.py              # CLI entry point
entropic_packages.py     # Package CLI entry point
```

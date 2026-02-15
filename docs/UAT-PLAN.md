# Entropic v0.7.0 — User Acceptance & Integration Testing Plan

> **Date:** 2026-02-15
> **Version:** v0.7.0-dev (123 effects, 12 categories, 2742 unit tests passing)
> **Tester:** nissimdirect
> **Prepared by:** CTO, Red Team, Mad Scientist, Lenny, Don Norman

---

## How To Use This Document

1. Work through each section top-to-bottom (or jump to a specific area)
2. Mark each test: **PASS**, **FAIL**, or **SKIP** (with reason)
3. For FAIL: write what happened in the Notes column
4. You need a **test video** — any MP4 file (5-60 seconds works best)
5. All commands run from `~/Development/entropic/`
6. **UIT sections** (Part L) test end-to-end workflows across multiple features

---

## Part A: Setup & Prerequisites

### A1. Open Terminal

1. Press **Cmd + Space** → type **Terminal** → press **Enter**
2. You should see a command prompt like: `nissimagent@... ~ %`

### A2. Navigate to Project

```bash
cd ~/Development/entropic
```

Your prompt should show `entropic` in it.

### A3. Check Dependencies

Run each command one at a time:

| # | Command | Expected Output |
|---|---------|-----------------|
| 1 | `python3 --version` | `Python 3.x.x` |
| 2 | `ffmpeg -version` | Starts with `ffmpeg version ...` |
| 3 | `python3 -c "from effects import EFFECTS; print(f'{len(EFFECTS)} effects loaded')"` | `123 effects loaded` |
| 4 | `python3 -c "import pygame; print('pygame OK')"` | `pygame OK` |

If any fail, copy the error and tell Claude.

### A4. Get a Test Video

You need an MP4 file (5-60 seconds). Place it somewhere accessible (e.g., `~/Movies/test.mp4`).

### A5. Launch Desktop App

```bash
python3 server.py
```

A window should open. If it doesn't, check the terminal for errors.

---

## Part B: Smoke Tests

Quick pass/fail checks to verify basic functionality before deep testing.

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| B1 | App launches | Run `python3 server.py` | Window opens, empty state visible | |
| B2 | File loads | Cmd+O or drag video onto window | Preview shows first frame, frame info visible | |
| B3 | Effect applies | Drag any effect from browser to chain | Preview updates with effect applied | |
| B4 | Knob adjusts | Drag any knob up/down | Value changes, preview updates | |
| B5 | Undo works | Cmd+Z after adding effect | Effect removed, preview reverts | |
| B6 | Export works | Cmd+E, select MP4, click Export | File appears in ~/Movies/Entropic/ | |
| B7 | Timeline shows | Click Timeline mode | Timeline canvas renders with ruler and track | |
| B8 | Perform works | Click Perform mode (or press P in Timeline) | Mixer panel appears with 4 channel strips | |
| B9 | Shortcut ref | Press ? | Shortcut overlay appears with all keybindings | |
| B10 | Help panel | Press H | Help panel with effect reference appears | |

---

## Part C: Desktop App Core

### C1. Window & Boot

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| C1.1 | Window size | Resize window | Content reflows, no overflow or clipping | |
| C1.2 | Boot time | Time from `python3 server.py` to window | Under 5 seconds | |
| C1.3 | Graceful close | Close window (Cmd+W or X button) | Process exits cleanly, terminal returns to prompt | |
| C1.4 | Multiple launches | Try running server.py while one is already running | Error message about port in use (not a crash) | |

### C2. File Loading

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| C2.1 | MP4 load | Cmd+O → select .mp4 | Preview shows, frame info updates | |
| C2.2 | Image load | Cmd+O → select .jpg or .png | Preview shows, treated as single frame | |
| C2.3 | GIF load | Cmd+O → select .gif | Preview shows, timeline shows frame count | |
| C2.4 | Drag & drop | Drag file onto canvas area | Same as Cmd+O | |
| C2.5 | Large file | Load 1080p or 4K video | Loading indicator shows, then preview appears | |
| C2.6 | No file state | Launch without loading | Empty state message visible, effects disabled | |
| C2.7 | Replace file | Load one file, then load another | Second file replaces first, chain preserved | |

### C3. Mode Switching

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| C3.1 | Timeline → Perform | Load file → Timeline → press P | Mixer panel toggles below timeline | |
| C3.2 | Perform mode | Switch to Perform mode | Transport bar + mixer visible, timeline hidden | |
| C3.3 | Mode indicator | Switch modes | Top bar shows current mode accent color | |
| C3.4 | Mode badge | In Perform mode | "PERFORM" badge visible in top bar | |

---

## Part D: Effect Browser & Chain

### D1. Browser

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| D1.1 | Categories load | Open browser sidebar | 12 collapsible categories with effect counts | |
| D1.2 | Expand/collapse | Click category header | Effects list expands/collapses | |
| D1.3 | All collapsed | On launch | All categories start collapsed | |
| D1.4 | Search | Type in search bar | Effects filter in real-time, fuzzy match works | |
| D1.5 | Tag search | Type category name (e.g., "glitch") | All glitch effects shown | |
| D1.6 | Favorites | Star an effect | Appears in Favorites pseudo-category at top | |
| D1.7 | Favorites persist | Star effect → reload app | Still starred | |
| D1.8 | Hover preview | Hover over effect in browser | Thumbnail preview appears after ~400ms | |
| D1.9 | Info view | Hover over effect | Bottom info bar shows name + category + description | |
| D1.10 | Effect count | Check total | 123 effects across 12 categories | |

**Category counts to verify:**

| Category | Expected Count |
|----------|---------------|
| Physics | 21 |
| Destruction | 18 |
| Temporal | 15 |
| Modulation | 12 |
| Texture | 11 |
| Color | 11 |
| Enhance | 9 |
| Whimsy | 8 |
| Distortion | 5 |
| Sidechain | 5 |
| Glitch | 4 |
| Tools | 4 |

### D2. Chain Editing

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| D2.1 | Add effect | Drag from browser to chain | Effect appears in chain, preview updates | |
| D2.2 | Remove effect | Select effect → press Delete | Effect removed | |
| D2.3 | Reorder | Press [ or ] with effect selected | Effect moves up/down in chain | |
| D2.4 | Duplicate | Cmd+D with effect selected | Copy appears below original | |
| D2.5 | Bypass | Press B with effect selected | Effect greyed out, preview updates without it | |
| D2.6 | Group | Select effects → Cmd+G | Group created with fold indicator | |
| D2.7 | Ungroup | Select group → Cmd+Shift+G | Effects ungrouped, back to flat list | |
| D2.8 | Per-effect mix | Adjust mix slider on an effect | Blends between original and processed (0-100%) | |
| D2.9 | Select with arrows | Up/Down arrows | Previous/next effect selected | |

### D3. Parameters

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| D3.1 | Knob drag | Drag knob up | Value increases, arc fills, preview updates | |
| D3.2 | Fine adjust | Shift+drag knob | Value changes at 1/5th speed | |
| D3.3 | Reset | Double-click knob | Value returns to default | |
| D3.4 | Direct input | Click knob value text | Input field appears, type number, Enter commits | |
| D3.5 | Log scaling | Effect with wide range (e.g., frequency) | Knob sweet spot spread across more travel | |
| D3.6 | Int rounding | Int-type parameter | Snaps to whole numbers | |
| D3.7 | Boolean knob | Bool-type parameter | Toggles at 0.5 threshold | |
| D3.8 | Preset save | Right-click dropdown → Save Current | Preset saved with custom name | |
| D3.9 | Preset load | Select saved preset from dropdown | Parameters restore to preset values | |
| D3.10 | Preset reset | Select "Reset to Default" | All params return to effect defaults | |
| D3.11 | Complexity meter | Add multiple effects | Complexity indicator goes green → yellow → red | |

---

## Part E: Individual Effects (by Category)

For each effect: add to chain, adjust primary parameter, verify preview changes visually.
Mark PASS if effect renders without error and produces visible change. Mark FAIL if broken.

### E1. Glitch (4)

| ID | Effect | Visual Check | Result |
|----|--------|-------------|--------|
| E1.1 | glitch_video | Random block displacement / color shift | |
| E1.2 | jpeg_damage | JPEG artifact blocks | |
| E1.3 | xor_glitch | XOR pattern noise | |
| E1.4 | byte_corrupt | Raw byte-level corruption | |

### E2. Distortion (5)

| ID | Effect | Visual Check | Result |
|----|--------|-------------|--------|
| E2.1 | wave | Sinusoidal wave displacement | |
| E2.2 | smear | Directional pixel smearing | |
| E2.3 | stretch | Horizontal/vertical stretch | |
| E2.4 | mirror | Mirror/reflect portions of frame | |
| E2.5 | flow_distort | Flow field displacement | |

### E3. Texture (11)

| ID | Effect | Visual Check | Result |
|----|--------|-------------|--------|
| E3.1 | scanlines | Horizontal line overlay | |
| E3.2 | film_grain | Noise grain overlay | |
| E3.3 | vignette | Dark corners | |
| E3.4 | halftone | Dot pattern (newspaper look) | |
| E3.5 | contours | Edge contour lines | |
| E3.6 | noise | Random noise overlay | |
| E3.7 | dither | Dithering pattern | |
| E3.8 | chromatic_aberration | RGB channel offset | |
| E3.9 | duotone | Two-color mapping | |
| E3.10 | gradient_map | Custom gradient color mapping | |
| E3.11 | emboss | Raised relief texture | |

### E4. Color (11)

| ID | Effect | Visual Check | Result |
|----|--------|-------------|--------|
| E4.1 | levels | Input/output range remapping | |
| E4.2 | curves | Bezier curve adjustment | |
| E4.3 | hsl_adjust | Hue/saturation/lightness per range | |
| E4.4 | color_balance | Shadow/midtone/highlight tinting | |
| E4.5 | color_shift | RGB channel rotation | |
| E4.6 | invert | Full color inversion | |
| E4.7 | threshold | Binary black/white | |
| E4.8 | posterize | Reduce color levels | |
| E4.9 | sepia | Warm brown tone | |
| E4.10 | auto_levels | Automatic histogram stretch | |
| E4.11 | histogram_eq | Histogram equalization | |

### E5. Temporal (15)

| ID | Effect | Visual Check | Result |
|----|--------|-------------|--------|
| E5.1 | echo | Frame trail / ghosting | |
| E5.2 | trail | Motion trail persistence | |
| E5.3 | time_stretch | Frame rate manipulation | |
| E5.4 | reverse | Reverse playback | |
| E5.5 | freeze | Hold single frame | |
| E5.6 | strobe | Flash on/off | |
| E5.7 | frame_blend | Blend adjacent frames | |
| E5.8 | realdatamosh | I-frame removal datamosh | |
| E5.9 | time_warp | Non-linear time stretching | |
| E5.10 | frame_hold | Hold every Nth frame | |
| E5.11 | buffer_overflow | Frame repetition/stutter | |
| E5.12 | feedback | Recursive feedback loop | |
| E5.13 | timecode | Burn timecode overlay | |
| E5.14 | frame_skip | Skip frames periodically | |
| E5.15 | time_slice | Vertical time slice | |

### E6. Modulation (12)

| ID | Effect | Visual Check | Result |
|----|--------|-------------|--------|
| E6.1 | pixelsort | Pixel sorting by brightness | |
| E6.2 | displacement | Map-based displacement | |
| E6.3 | kaleidoscope | Mirror symmetry | |
| E6.4 | rotate | Rotation transform | |
| E6.5 | zoom | Zoom in/out | |
| E6.6 | tile | Repeating tile grid | |
| E6.7 | crop | Crop region | |
| E6.8 | offset | X/Y pixel offset | |
| E6.9 | flip | Horizontal/vertical flip | |
| E6.10 | scale | Resize transform | |
| E6.11 | pan | Pan position | |
| E6.12 | shear | Shear transform | |

### E7. Enhance (9)

| ID | Effect | Visual Check | Result |
|----|--------|-------------|--------|
| E7.1 | sharpen | Edge sharpening | |
| E7.2 | blur | Gaussian blur | |
| E7.3 | edges | Edge detection highlight | |
| E7.4 | brightness | Brightness adjustment | |
| E7.5 | contrast | Contrast adjustment | |
| E7.6 | saturation | Color saturation boost/cut | |
| E7.7 | gamma | Gamma correction | |
| E7.8 | unsharp_mask | Unsharp mask sharpening | |
| E7.9 | clahe | Contrast-limited adaptive histogram | |

### E8. Destruction (18)

| ID | Effect | Visual Check | Result |
|----|--------|-------------|--------|
| E8.1 | melt | Downward pixel melting | |
| E8.2 | shatter | Fragment explosion | |
| E8.3 | dissolve | Pixel dissolve transition | |
| E8.4 | erode | Morphological erosion | |
| E8.5 | dilate | Morphological dilation | |
| E8.6 | channel_shift | Individual RGB channel displacement | |
| E8.7 | bit_crush | Bit depth reduction | |
| E8.8 | corrupt | Structured corruption | |
| E8.9 | acid | Acid wash color distortion | |
| E8.10 | decimate | Resolution decimation | |
| E8.11 | ascii_art | ASCII character rendering | |
| E8.12 | braille_art | Braille character rendering | |
| E8.13 | pixel_fax | Fax machine degradation | |
| E8.14 | pixel_risograph | Risograph print simulation | |
| E8.15 | pixel_xerox | Xerox copy degradation | |
| E8.16 | pixel_inkdrop | Ink drop diffusion | |
| E8.17 | pixel_haunt | Ghost image overlay | |
| E8.18 | pixel_bubbles | Bubble void mode | |

### E9. Physics (21)

| ID | Effect | Visual Check | Result |
|----|--------|-------------|--------|
| E9.1 | pixel_gravity | Downward pixel fall | |
| E9.2 | pixel_wind | Horizontal pixel drift | |
| E9.3 | pixel_magnetic | Magnetic field distortion | |
| E9.4 | pixel_liquify | Fluid simulation | |
| E9.5 | pixel_vortex | Spiral vortex pull | |
| E9.6 | pixel_electric | Lightning/electric discharge | |
| E9.7 | pixel_wormhole | Space wormhole warp | |
| E9.8 | pixel_quantum | Quantum probability scatter | |
| E9.9 | pixel_dark_energy | Expansion distortion | |
| E9.10 | pixel_superfluid | Zero-friction flow | |
| E9.11 | pixel_ripple | Concentric ripple waves | |
| E9.12 | pixel_fractal | Fractal growth pattern | |
| E9.13 | pixel_thermal | Heat map visualization | |
| E9.14 | pixel_erosion | Natural erosion simulation | |
| E9.15 | pixel_crystallize | Crystal formation | |
| E9.16 | pixel_shockwave | Radial shockwave | |
| E9.17 | pixel_tornado | Tornado-style spiral | |
| E9.18 | pixel_rain | Falling particle rain | |
| E9.19 | pixel_fire | Fire effect simulation | |
| E9.20 | pixel_smoke | Smoke rising effect | |
| E9.21 | pixel_lightning | Fork lightning | |

### E10. Sidechain (5)

| ID | Effect | Visual Check | Result |
|----|--------|-------------|--------|
| E10.1 | sidechain_crossfeed | Cross-video parameter modulation | |
| E10.2 | sidechain_gate | Binary gate based on source | |
| E10.3 | sidechain_duck | Ducking opacity | |
| E10.4 | sidechain_follow | Envelope follower | |
| E10.5 | sidechain_pump | Pumping compression effect | |

### E11. Whimsy (8)

| ID | Effect | Visual Check | Result |
|----|--------|-------------|--------|
| E11.1 | kaleidoscope | Kaleidoscope mirror effect | |
| E11.2 | softbloom | Soft glow bloom | |
| E11.3 | shapeoverlay | Geometric shape overlays | |
| E11.4 | lensflare | Lens flare | |
| E11.5 | watercolor | Watercolor paint simulation | |
| E11.6 | rainbowshift | Rainbow color cycling | |
| E11.7 | sparkle | Sparkle/glitter particles | |
| E11.8 | filmgrainwarm | Warm analog film grain | |

### E12. Tools (4)

| ID | Effect | Visual Check | Result |
|----|--------|-------------|--------|
| E12.1 | histogram | Live histogram overlay | |
| E12.2 | vectorscope | Color vectorscope overlay | |
| E12.3 | waveform | Luma waveform monitor | |
| E12.4 | zebra | Zebra stripe overexposure indicator | |

---

## Part F: Color Suite

### F1. Levels

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| F1.1 | Black point | Add levels → increase input min | Dark areas clip to black | |
| F1.2 | White point | Decrease input max | Bright areas clip to white | |
| F1.3 | Gamma | Adjust gamma | Midtones shift lighter/darker | |
| F1.4 | Output range | Compress output min/max | Overall contrast reduces | |
| F1.5 | Per-channel | Switch to R/G/B channel mode | Only selected channel affected | |

### F2. Curves

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| F2.1 | S-curve | Add two points → make S shape | Contrast increases | |
| F2.2 | Add point | Click on curve | New control point appears | |
| F2.3 | Move point | Drag control point | Curve reshapes, preview updates | |
| F2.4 | Invert | Drag curve to inverted shape | Colors invert in affected range | |

### F3. HSL Adjust

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| F3.1 | Target reds | Set target to "reds" → shift hue | Only red areas change color | |
| F3.2 | Saturation | Reduce saturation | Colors desaturate | |
| F3.3 | Lightness | Increase lightness | Image brightens | |
| F3.4 | All targets | Set target to "all" | Entire image affected | |

### F4. Color Balance

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| F4.1 | Shadow tint | Shift shadows toward blue | Dark areas gain blue tint | |
| F4.2 | Midtone tint | Shift midtones toward red | Middle tones gain warmth | |
| F4.3 | Highlight tint | Shift highlights toward yellow | Bright areas gain warmth | |
| F4.4 | Luminosity | Toggle preserve luminosity | Overall brightness unchanged when on | |

### F5. Live Histogram

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| F5.1 | Display | Add histogram tool | R/G/B/Luma distribution overlay | |
| F5.2 | Updates | Change effect parameters | Histogram redraws with new distribution | |
| F5.3 | Clipping | Push levels to extreme | Histogram shows spikes at edges | |

---

## Part G: Timeline Editor

### G1. Canvas & Navigation

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| G1.1 | Ruler | Switch to Timeline mode | Frame ruler with numbers at top | |
| G1.2 | Zoom in | Press + or scroll | Timeline stretches, more detail | |
| G1.3 | Zoom out | Press - or scroll | Timeline compresses, more frames visible | |
| G1.4 | Fit to window | Cmd+0 | Entire timeline fits in view | |
| G1.5 | Scroll | Scroll horizontally | Timeline pans left/right | |
| G1.6 | Playhead | Click on ruler | Playhead moves to click position | |

### G2. Regions

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| G2.1 | Set in-point | Press I | In-point marker appears at playhead | |
| G2.2 | Set out-point | Press O | Out-point marker appears at playhead | |
| G2.3 | Create region | Set I/O → Cmd+R | Region bar appears between in/out | |
| G2.4 | Select region | Click on region | Region highlighted, effects panel shows region effects | |
| G2.5 | Move region | Drag region | Region repositions on timeline | |
| G2.6 | Resize region | Drag region edge | Region start/end changes | |
| G2.7 | Delete region | Select → Delete key | Region removed | |
| G2.8 | Multiple regions | Create 3+ regions | All visible, independently selectable | |

### G3. Per-Region Effects

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| G3.1 | Add effect | Select region → drag effect to chain | Effect applies only within region bounds | |
| G3.2 | Different regions | Two regions with different effects | Playhead in region A shows its effects, region B shows different | |
| G3.3 | No region | Playhead outside any region | Original video shows (no effects) | |

### G4. Spatial Masks

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| G4.1 | Draw mask | Right-click region → Set Mask | Rectangular selection tool appears on canvas | |
| G4.2 | Masked effect | Apply effect with mask active | Effect only appears within mask rectangle | |
| G4.3 | Full frame | No mask set | Effect applies to entire frame | |

### G5. Automation Lanes

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| G5.1 | Create lane | Right-click knob → Create Automation Lane | Lane appears below region | |
| G5.2 | Add keyframe | Click on lane | Breakpoint added at click position | |
| G5.3 | Move keyframe | Drag breakpoint | Value/position changes | |
| G5.4 | Delete lane | Right-click knob → Delete Automation Lane | Lane removed | |
| G5.5 | Toggle visibility | Toggle automation visibility | Lanes show/hide | |
| G5.6 | Multiple lanes | Create lanes for 3 different params | All render correctly, color-coded | |

### G6. Track Controls

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| G6.1 | Mute track | Press M | Track dims, effects don't apply | |
| G6.2 | Solo track | Press S | Only this track renders | |

### G7. Playback

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| G7.1 | Play | Space in Timeline mode | Playhead advances, preview updates | |
| G7.2 | Pause | Space during playback | Playhead stops | |
| G7.3 | Scrub | Click/drag on ruler | Preview jumps to frame | |
| G7.4 | Frame step | Left/Right arrow | Single frame forward/back | |
| G7.5 | Jump 10 | Shift+Left/Right | 10 frames forward/back | |

### G8. Freeze & Flatten

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| G8.1 | Freeze region | Right-click region → Freeze | Region pre-renders to MP4, playback smoother | |
| G8.2 | Flatten | Right-click region → Flatten | Effects baked into source, chain clears | |

---

## Part H: LFO Map Operator

### H1. Map Flow

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| H1.1 | Enter map mode | Click "Map" button in LFO panel | All unmapped knobs highlight | |
| H1.2 | Map parameter | Click a highlighted knob | Knob gets LFO indicator, pill appears in LFO panel | |
| H1.3 | Verify modulation | Observe mapped knob | Knob rotates automatically with LFO waveform | |
| H1.4 | Unmap | Click pill X or right-click → Unmap from LFO | Knob returns to manual value | |
| H1.5 | Drag blocked | Try dragging LFO-mapped knob | Drag blocked (LFO controls this param) | |

### H2. Waveforms

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| H2.1 | Sine | Select sine waveform | Smooth oscillation | |
| H2.2 | Saw | Select saw | Ramp up then snap down | |
| H2.3 | Square | Select square | Abrupt on/off toggle | |
| H2.4 | Triangle | Select triangle | Linear ramp up and down | |
| H2.5 | Noise | Select noise | Random but quantized steps | |
| H2.6 | Random | Select random | Smooth random | |

### H3. LFO Controls

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| H3.1 | Rate | Adjust Rate knob | Modulation speed changes | |
| H3.2 | Depth | Adjust Depth knob | Modulation amplitude changes | |
| H3.3 | Phase | Adjust Phase knob | Modulation offset shifts | |
| H3.4 | Multi-map | Map LFO to 3 different params | All modulate simultaneously | |
| H3.5 | Clear all | Click "Clear" button | All mappings removed, knobs return to manual | |

---

## Part I: Perform Mode (Mixer & Transport)

### I1. Mixer Panel

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| I1.1 | 4 strips | Enter Perform mode | 4 channel strips (L1-L4) visible | |
| I1.2 | Strip labels | Check strip headers | Layer names, key numbers (1-4), color indicators | |
| I1.3 | Trigger button | Click trigger button | Layer activates (visual feedback immediate) | |
| I1.4 | Opacity fader | Drag fader on a strip | Layer opacity changes | |
| I1.5 | Mute | Click M on strip | Strip dims, layer excluded from render | |
| I1.6 | Solo | Click S on strip | Only this layer renders | |

### I2. Trigger Modes

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| I2.1 | Toggle | Set layer to toggle → press key | Alternates on/off each press | |
| I2.2 | Gate | Set layer to gate → hold key | Active while held, off on release | |
| I2.3 | ADSR | Set layer to adsr → press and release | Attack → Decay → Sustain while held → Release on keyup | |
| I2.4 | One-shot | Set layer to one_shot → press key | Plays full A-D-R cycle regardless of hold | |
| I2.5 | Always on | Set layer to always_on | Layer always visible, trigger button disabled | |
| I2.6 | Mode dropdown | Change trigger mode via dropdown | Mode changes, behavior updates | |

### I3. ADSR Presets

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| I3.1 | Pluck | Select pluck preset → trigger | Fast attack, medium decay, ~80% sustain | |
| I3.2 | Stab | Select stab preset → trigger | Very fast attack, fast decay, no sustain | |
| I3.3 | Pad | Select pad preset → trigger | Slow attack, long decay, full sustain | |
| I3.4 | Sustain | Select sustain preset → trigger | Medium attack, full sustain, long release | |

### I4. Transport Bar

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| I4.1 | Play button | Click Play | Playback starts, button changes to Pause | |
| I4.2 | Pause button | Click Pause during playback | Playback stops | |
| I4.3 | Time display | During playback | Time counter advances (M:SS:FF format) | |
| I4.4 | Frame counter | During playback | Frame number increments | |
| I4.5 | Scrubber | Drag scrubber slider | Playhead jumps to position, preview updates | |
| I4.6 | Loop | Click Loop button | Playback loops at end of video | |
| I4.7 | Event count | Trigger some layers | Event count updates in transport | |

### I5. Recording

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| I5.1 | Arm recording | Press R or click Rec | Button turns red, HUD shows [REC] | |
| I5.2 | Record events | Arm → Play → trigger layers | Events accumulate (event count increases) | |
| I5.3 | Stop recording | Press R again | Toast shows event count, offers Save/Review/Bake/Discard | |
| I5.4 | Review | Click Review after stopping | Performance replays with visual indicators | |
| I5.5 | Bake to timeline | Click Bake to Timeline | Automation lanes created in timeline from recorded events | |
| I5.6 | Save session | Click Save | Session saved to file | |
| I5.7 | Discard | Click Discard | Buffer cleared, event count resets | |
| I5.8 | Buffer cap | Record >45000 events | Warning toast at 90% capacity | |
| I5.9 | Scrub blocked | Try scrubbing while recording | Toast: "Cannot scrub while recording" | |

### I6. Choke Groups

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| I6.1 | Set choke | Set two layers to same choke group | Dropdown shows group numbers | |
| I6.2 | Choke behavior | Trigger layer A then B (same group) | A deactivates when B activates | |
| I6.3 | Choke flash | Trigger choked layer | Choked strip flashes briefly (300ms) | |

### I7. Panic

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| I7.1 | Panic button | Click Panic | All layers reset, toast "ALL LAYERS RESET" | |
| I7.2 | Shift+P | Press Shift+P | Same as panic button | |
| I7.3 | During playback | Trigger layers → Panic during playback | All layers deactivate, server receives panic events | |

### I8. HUD Overlay

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| I8.1 | Visible | Enter Perform mode | HUD visible on preview canvas (bottom-left) | |
| I8.2 | Recording state | Toggle recording | HUD shows [REC] / [BUF] / [AUTO] | |
| I8.3 | Time | During playback | HUD time matches transport time | |
| I8.4 | Events | Record some events | HUD shows event count | |

---

## Part J: Performance Features (NEW)

### J1. Keyboard Input Mode

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| J1.1 | Toggle on | Press M in Perform mode | Purple "PERFORM" indicator in HUD, canvas gets purple outline | |
| J1.2 | Toggle off | Press M again | Indicator hides, outline removed | |
| J1.3 | Q trigger | M → press Q | Layer 1 activates | |
| J1.4 | W trigger | Press W | Layer 2 activates | |
| J1.5 | E trigger | Press E | Layer 3 activates | |
| J1.6 | R trigger | Press R (in keyboard mode) | Layer 4 activates (not recording toggle) | |
| J1.7 | A/S/D/F | Press A, S, D, F | Layers 5-8 activate (if they exist) | |
| J1.8 | Gate release | Set layer to gate → hold Q → release Q | Layer active while held, deactivates on release | |
| J1.9 | ADSR release | Set layer to adsr → hold W → release W | Release phase starts on keyup | |
| J1.10 | Text guard | Click search bar → type Q | Typing goes to search, NOT triggering layers | |
| J1.11 | Escape exits | Press Escape | All layers panic, keyboard mode exits | |
| J1.12 | Key hints | Press K while in keyboard mode | Overlay shows Q=L1, W=L2, etc. | |
| J1.13 | Toggle hints | Press K again | Overlay hides | |
| J1.14 | Extended keys | Press 5, 6, 7, 8 | Layers 5-8 trigger (one-shot, with or without M) | |
| J1.15 | No conflict | Press M when not in perform mode | Nothing happens (M only works in perform context) | |

### J2. Retroactive Buffer

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| J2.1 | Buffer accumulates | Do NOT press Record → Play → trigger layers | Buffer indicator in HUD shows time accumulating | |
| J2.2 | Capture | Click Capture button after performing | Toast: "Captured N events (Xs)" + Review/Bake/Discard options | |
| J2.3 | Cmd+Shift+C | Press Cmd+Shift+C | Same as Capture button | |
| J2.4 | Empty capture | Click Capture without performing | Toast: "Nothing to capture — perform first" | |
| J2.5 | Bake captured | Capture → click Bake to Timeline | Automation lanes created from captured events | |
| J2.6 | Buffer eviction | Perform for >60 seconds | Buffer only keeps last 60s of events | |
| J2.7 | Buffer indicator | Check HUD during performance | Shows "Buf: Ns" with rolling duration | |
| J2.8 | Independent of Record | Arm Record AND perform → stop Record → Capture | Both recording session AND capture buffer have data | |
| J2.9 | Buffer cap | Somehow trigger >50000 events | Oldest events evicted, no crash | |
| J2.10 | Review captured | Capture → Review | Captured events play back with visual indicators | |
| J2.11 | Discard captured | Capture → Discard | Buffer cleared, event count resets | |

### J3. Automation Recording

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| J3.1 | Arm AUTO | Click AUTO button or press Shift+R | Button turns red, HUD shows [AUTO] | |
| J3.2 | Disarm | Click AUTO again or Shift+R | Button returns to normal | |
| J3.3 | Record knob | Arm AUTO → Play → drag any effect knob | Knob gets red glow (auto-recording class) | |
| J3.4 | Stop commits | Stop playback while AUTO armed | Toast: "Automation recorded: N params, M keyframes" | |
| J3.5 | Lanes created | After auto-commit → switch to Timeline | Automation lanes visible for recorded params | |
| J3.6 | Keyframe thinning | Record knob movement → check lane keyframes | NOT 60fps density — thinned to ~10fps | |
| J3.7 | Multiple knobs | Arm → Play → move 3 different knobs | 3 separate automation lanes created | |
| J3.8 | No play no record | Arm AUTO → move knob WITHOUT playing | Nothing recorded (requires playback) | |
| J3.9 | Small change skip | Arm → Play → move knob by tiny amount (<1%) | No keyframe added (tolerance filter) | |
| J3.10 | Visual clear | After commit → check knobs | Red glow removed from all knobs | |
| J3.11 | Empty auto | Arm → Play (don't move knobs) → Stop | Toast: "No automation recorded" | |

---

## Part K: Safety & Edge Cases

### K1. File Safety

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| K1.1 | No overwrite | Export same name twice | Second file gets incremented name or confirmation | |
| K1.2 | Disk space | Export when disk is nearly full | Warning message, not silent failure | |
| K1.3 | Invalid path | Try export to read-only location | Error toast, no crash | |

### K2. Input Validation

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| K2.1 | Extreme knob | Drag knob far beyond range | Value clamped to min/max | |
| K2.2 | Empty chain | Export with no effects | Exports original video (no crash) | |
| K2.3 | Long chain | Add 20+ effects | App handles without crash (may be slow) | |
| K2.4 | Unicode file | Load file with unicode characters in name | Loads correctly | |
| K2.5 | Zero-length video | Load single-frame image | Handles gracefully, timeline shows 1 frame | |

### K3. State Safety

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| K3.1 | Mode switch during play | Switch modes while timeline/perform playing | Playback stops gracefully | |
| K3.2 | Load during play | Load new file during playback | Playback stops, new file loads | |
| K3.3 | Rapid triggers | Mash all number keys rapidly | No crash, events queue correctly | |
| K3.4 | Double-click buttons | Double-click Play rapidly | Doesn't double-start or break state | |

### K4. Error Recovery

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| K4.1 | Error toast | Force an error (e.g., corrupt file) | Toast notification with error details | |
| K4.2 | Continue after error | After error toast → try another action | App still functional | |
| K4.3 | History survives errors | Error during effect → Cmd+Z | Can undo past the error point | |

### K5. Resource Limits

| ID | Test | Steps | Expected | Result |
|----|------|-------|----------|--------|
| K5.1 | Frame cache | Play long video | Cache evicts old frames (max 30) | |
| K5.2 | Record buffer | Record >45000 events | Warning at 90%, stops at 50000 | |
| K5.3 | Large export | Export 4K video | Progress indicator shows, completes without OOM | |

---

## Part L: User Integration Testing (UIT)

End-to-end workflows that test multiple features working together.

### L1. Effect Discovery → Apply → Export

| Step | Action | Verify |
|------|--------|--------|
| 1 | Load MP4 video (Cmd+O) | Preview shows, timeline updates |
| 2 | Search for "glitch" in effect browser | Glitch effects filter to top |
| 3 | Drag `glitch_video` to chain | Preview shows glitch effect |
| 4 | Adjust intensity knob | Effect intensity changes in preview |
| 5 | Star the effect (add to favorites) | Star icon fills |
| 6 | Add second effect: `scanlines` | Both effects stack |
| 7 | Bypass first effect (B key) | Only scanlines visible |
| 8 | Un-bypass (B again) | Both visible again |
| 9 | Export (Cmd+E) | File exports with both effects applied |
| 10 | Verify export file exists | File in ~/Movies/Entropic/ |

**Result:** ____

### L2. Timeline → Regions → Automation → Export

| Step | Action | Verify |
|------|--------|--------|
| 1 | Load video → switch to Timeline mode | Timeline canvas renders |
| 2 | Set in-point at frame 0 (I) | Marker appears |
| 3 | Move playhead to frame 30 → set out-point (O) | Second marker |
| 4 | Create region (Cmd+R) | Region bar appears |
| 5 | Select region → add `blur` effect | Blur within region bounds |
| 6 | Right-click blur "radius" knob → Create Automation Lane | Lane appears below region |
| 7 | Add 3 keyframes: low→high→low | Breakpoints on lane curve |
| 8 | Play timeline (Space) | Blur animates per automation curve |
| 9 | Export | Timeline export includes automated blur |

**Result:** ____

### L3. Color Correction Workflow

| Step | Action | Verify |
|------|--------|--------|
| 1 | Load video | Preview shows |
| 2 | Add `histogram` tool | Histogram overlay visible |
| 3 | Add `levels` → adjust black/white points | Histogram shifts, contrast improves |
| 4 | Add `curves` → create S-curve | Contrast increases further |
| 5 | Add `hsl_adjust` → target reds → shift hue | Red areas change color |
| 6 | Add `color_balance` → warm shadows | Shadow areas gain warmth |
| 7 | Check histogram | Distribution changes reflect all adjustments |
| 8 | Export | Color-corrected video exports |

**Result:** ____

### L4. LFO Modulation → Timeline → Export

| Step | Action | Verify |
|------|--------|--------|
| 1 | Load video, add `wave` effect | Wave distortion visible |
| 2 | Open LFO panel → click Map | Knobs highlight |
| 3 | Click wave "amplitude" knob | Knob gets LFO indicator |
| 4 | Set LFO: sine, Rate=2, Depth=0.8 | Amplitude oscillates smoothly |
| 5 | Map second param: wave "frequency" | Both params modulate |
| 6 | Observe preview | Dynamic, animated wave effect |
| 7 | Switch to Timeline → create region | Timeline region with effects |
| 8 | Export with LFO active | Rendered video has animated modulation |

**Result:** ____

### L5. Perform → Record → Bake → Timeline Export

| Step | Action | Verify |
|------|--------|--------|
| 1 | Load video → switch to Perform mode | Mixer visible with 4 strips |
| 2 | Set L1: toggle, L2: gate, L3: adsr | Trigger modes configured |
| 3 | Arm recording (R) | HUD shows [REC], Rec button red |
| 4 | Play (Space) → trigger layers with 1, 2, 3 keys | Layers activate with visual feedback |
| 5 | Hold 2 key (gate) → release | L2 active during hold, off on release |
| 6 | Stop recording (R) | Toast with event count + options |
| 7 | Click "Bake to Timeline" | Automation lanes appear in timeline |
| 8 | Switch to Timeline → verify lanes | Trigger events visible as automation |
| 9 | Play timeline | Layers replay per recorded automation |
| 10 | Export from timeline | Rendered video includes performance |

**Result:** ____

### L6. Keyboard Perform → Capture Buffer → Bake

| Step | Action | Verify |
|------|--------|--------|
| 1 | Load video → Perform mode → do NOT arm Record | No recording active |
| 2 | Press M to enter keyboard perform mode | Purple PERFORM indicator |
| 3 | Play (Space) | Playback starts |
| 4 | Trigger with Q/W/E/R keys | Layers activate, buffer indicator fills |
| 5 | Hold Q (gate mode) → release | L1 active during hold |
| 6 | Stop playback | Buffer indicator shows accumulated time |
| 7 | Click Capture (or Cmd+Shift+C) | Toast: "Captured N events" |
| 8 | Click "Bake to Timeline" | Automation lanes created from capture |
| 9 | Press M to exit keyboard mode | PERFORM indicator hides |
| 10 | Switch to Timeline → verify lanes | Captured events visible as automation |

**Result:** ____

### L7. Automation Recording → Timeline Verification

| Step | Action | Verify |
|------|--------|--------|
| 1 | Load video → Perform mode | Mixer visible |
| 2 | Click AUTO (or Shift+R) | Button turns red, HUD shows [AUTO] |
| 3 | Play (Space) | Playback starts |
| 4 | Drag effect knob on L1 slowly | Knob gets red glow |
| 5 | Drag a different knob on L2 | Second knob also glows |
| 6 | Stop playback | Toast: "Automation recorded: 2 params, N keyframes" |
| 7 | Switch to Timeline | Two new automation lanes visible |
| 8 | Play timeline | Parameters animate per recorded curves |
| 9 | Edit a keyframe (drag breakpoint) | Lane updates, parameter changes |

**Result:** ____

### L8. Full Performance Workflow (All 3 Features)

| Step | Action | Verify |
|------|--------|--------|
| 1 | Load video → Perform mode | Ready |
| 2 | Press M → enter keyboard mode | Purple indicator |
| 3 | Arm AUTO (Shift+R) | AUTO button red |
| 4 | Play (Space) | Playback runs |
| 5 | Trigger layers with Q/W/E/R | Layers activate |
| 6 | Move knobs while layers active | Knobs glow red (automation recording) |
| 7 | Stop playback | AUTO commits lanes, buffer has events |
| 8 | Capture buffer (Cmd+Shift+C) | Captured trigger events |
| 9 | Bake to Timeline | Both automation (knob) and trigger lanes | |
| 10 | Press Escape | Keyboard mode exits, all panic |
| 11 | Switch to Timeline → verify all lanes | Multiple automation lanes from all sources |
| 12 | Play timeline → export | Complete performance rendered |

**Result:** ____

### L9. Project Save → Close → Reload

| Step | Action | Verify |
|------|--------|--------|
| 1 | Build a chain with 3+ effects | Chain populated |
| 2 | Create timeline regions with automation | Timeline configured |
| 3 | Save project (Cmd+S) | Project file saved |
| 4 | Close app | App exits |
| 5 | Relaunch → load project | Project restores |
| 6 | Verify chain, timeline, automation | All state preserved |

**Result:** ____

### L10. Error Recovery Workflow

| Step | Action | Verify |
|------|--------|--------|
| 1 | Load video → add effects | Working state |
| 2 | Force an error (load corrupt file or trigger broken effect) | Error toast appears |
| 3 | Dismiss error → load valid video | App recovers |
| 4 | Previous chain preserved | Effects still in chain |
| 5 | Export successfully | Export works after recovery |

**Result:** ____

### L11. Mode Switching Stress Test

| Step | Action | Verify |
|------|--------|--------|
| 1 | Load video | Ready |
| 2 | Switch to Timeline → create region → add effect | Timeline works |
| 3 | Press P → toggle perform panel | Perform panel appears below timeline |
| 4 | Trigger layers (1-4) while timeline visible | Layers trigger correctly |
| 5 | Switch to Perform mode | Full perform layout |
| 6 | Switch back to Timeline | Timeline state preserved |
| 7 | Verify region + effects still there | No state loss |
| 8 | Play timeline | Playback works correctly |

**Result:** ____

### L12. Choke Group + ADSR Integration

| Step | Action | Verify |
|------|--------|--------|
| 1 | Set L1 and L2 to same choke group | Both in group 0 |
| 2 | Set both to ADSR mode, pluck preset | Fast attack |
| 3 | Play → trigger L1 (key 1) | L1 activates with ADSR |
| 4 | While L1 sustaining → trigger L2 (key 2) | L1 choked (flash), L2 activates |
| 5 | Release key 2 | L2 enters release phase |
| 6 | Record this sequence | Events captured |
| 7 | Bake → verify timeline | Choke + ADSR timing preserved |

**Result:** ____

---

## Part M: Info View Verification

Hover over each UI element and verify the bottom info bar shows appropriate help text.

| ID | Element | Expected Info Text Contains | Result |
|----|---------|----------------------------|--------|
| M1 | Effect in browser | Effect name + category + description | |
| M2 | Play button | "PLAY" + Space shortcut | |
| M3 | Rec button | "REC" + R shortcut | |
| M4 | AUTO button | "AUTO" + Shift+R + knob recording | |
| M5 | Capture button | "CAPTURE" + Cmd+Shift+C + buffer claim | |
| M6 | Panic button | "PANIC" + Shift+P + reset all | |
| M7 | Knob control | Parameter name or value info | |
| M8 | Timeline region | Region info or instructions | |

---

## Part N: Shortcut Reference Verification

Press ? to open shortcut overlay. Verify ALL shortcuts listed:

### Common Shortcuts

| Shortcut | Action | Listed? |
|----------|--------|---------|
| Cmd+D | Duplicate effect | |
| Del | Remove effect | |
| [ ] | Move up/down | |
| B | Bypass toggle | |
| R | Reset to defaults | |
| Up/Down | Select prev/next | |
| Cmd+G | Create group | |
| Cmd+Shift+G | Ungroup | |
| Drag | Adjust knob | |
| Shift+Drag | Fine adjust | |
| Dbl-click | Reset to default | |
| Space | A/B compare | |
| P | Toggle Perform panel | |
| Left/Right | Prev/next frame | |
| Shift+Left/Right | Jump 10 | |
| Cmd+O | Open file | |
| Cmd+E | Export | |
| Cmd+S | Save preset | |
| Tab | Toggle sidebar | |
| Esc | Close modal | |
| H | Help panel | |
| ? | Shortcut reference | |

### Timeline Shortcuts

| Shortcut | Action | Listed? |
|----------|--------|---------|
| I | Set in-point | |
| O | Set out-point | |
| Cmd+R | Create region | |
| Space | Play/Pause | |
| Home | Jump to start | |
| End | Jump to end | |
| + / - | Zoom in/out | |
| Cmd+0 | Fit to window | |
| M | Mute track | |
| S | Solo track | |

### Perform Shortcuts

| Shortcut | Action | Listed? |
|----------|--------|---------|
| 1-8 | Trigger layers | |
| Space | Play/Pause | |
| R | Toggle recording | |
| Shift+R | Automation record | |
| Shift+P | Panic | |
| Cmd+Shift+C | Capture buffer | |

### Keyboard Perform Shortcuts

| Shortcut | Action | Listed? |
|----------|--------|---------|
| M | Toggle keyboard mode | |
| Q/W/E/R | Trigger L1-L4 | |
| A/S/D/F | Trigger L5-L8 | |
| K | Toggle key hints | |
| Esc | Panic + exit mode | |

---

## Scoring Summary

### Category Scores

| Section | Tests | Pass | Fail | Skip | Score |
|---------|-------|------|------|------|-------|
| B. Smoke Tests | 10 | | | | /10 |
| C. Desktop Core | 15 | | | | /15 |
| D. Browser & Chain | 22 | | | | /22 |
| E. Effects (123) | 123 | | | | /123 |
| F. Color Suite | 14 | | | | /14 |
| G. Timeline | 24 | | | | /24 |
| H. LFO Map | 11 | | | | /11 |
| I. Perform Mode | 38 | | | | /38 |
| J. Performance Features | 37 | | | | /37 |
| K. Safety & Edge Cases | 15 | | | | /15 |
| L. UIT Workflows | 12 | | | | /12 |
| M. Info View | 8 | | | | /8 |
| N. Shortcut Reference | 33 | | | | /33 |
| **TOTAL** | **362** | | | | **/362** |

### Pass Rate

- **Target:** 90%+ (326/362)
- **Actual:** ____/362 = ____%

### Critical Failures

List any FAIL results that block shipping:

1.
2.
3.

---

## Known Issues (Pre-existing)

These are known from previous UAT cycles and may still apply:

- Datamosh (`realdatamosh`) requires video-level processing — may not work in single-frame preview
- Some pixel physics effects produce RuntimeWarning (divide by zero) with zero params — visual output still correct
- `braille_art` may show question marks on systems without braille font support
- Sidechain effects require a second video source — skip if no second video available

---

*UAT Plan v2.0 | 2026-02-15 | Rewritten from scratch to consolidate 4 UAT cycles into unified plan with UIT*

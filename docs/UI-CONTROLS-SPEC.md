# Entropic UI Controls Specification

## Discovery Document: Optimal Control Types for Every Effect Parameter

This document maps each effect parameter to its ideal UI control type based on the parameter's data type, range, semantic meaning, and user interaction model. The goal is a DAW-grade interface where every control *feels right* -- knobs for things you sweep, dropdowns for mode switches, XY pads for spatial offsets, and specialized widgets where they make the interaction more intuitive.

---

## Design Principles

1. **Match the mental model.** A hue rotation is circular, so use a circular control. An XY offset is spatial, so use a 2D pad.
2. **Minimize clicks.** Continuous parameters should be draggable, not typed. Discrete mode selections should be one-click dropdowns.
3. **DAW conventions.** Knobs for sweep-able values, sliders for before/after ranges, toggles for on/off. Users coming from Ableton, Logic, or Photoshop will expect these patterns.
4. **Progressive disclosure.** Some effects have "seed" or "curve" params that most users will never touch. These go behind an "Advanced" disclosure toggle.
5. **Visual feedback.** Every control should show its current value numerically alongside the visual widget.

---

## Available Control Types

| Type | Widget | Best For |
|------|--------|----------|
| `knob` | Rotary knob (Moog-style, already implemented) | Continuous values with a clear min/max. Tactile sweep feel. |
| `slider` | Horizontal slider | Large ranges, bipolar values (e.g., -3 to +3), before/after. Linear mental model. |
| `dropdown` | Select menu | String options with 2-5 choices. One-click selection. |
| `toggle` | On/off switch | Boolean values only. |
| `xy-pad` | 2D pad for X/Y values | Paired offset parameters with two coupled dimensions. |
| `color-picker` | Color wheel + swatch | RGB color tuples. |
| `number-input` | Direct number entry with +/- and randomize button | Integer values like seed (non-sweepable), or values where exact entry matters. |
| `hue-wheel` | Circular hue selector (0-360 degrees) | Hue rotation specifically. Circular nature of hue demands circular control. |

---

## Effect-by-Effect Specification

### GLITCH Category

#### 1. pixelsort

| Parameter | Control | Label | Range | Step | Default | Rationale |
|-----------|---------|-------|-------|------|---------|-----------|
| `threshold` | `knob` | Threshold | 0.0 -- 1.0 | 0.01 | 0.5 | Classic 0-1 sweep value. Knob is the natural fit for a continuous normalized range. |
| `sort_by` | `dropdown` | Sort By | brightness, hue, saturation | -- | brightness | 3 discrete string options. Dropdown is the only sensible choice. |
| `direction` | `dropdown` | Direction | horizontal, vertical | -- | horizontal | 2 discrete options. Quick toggle between two modes. |

**Quick/Advanced mode:** All parameters are essential. No advanced toggle needed.

---

#### 2. channelshift

| Parameter | Control | Label | Range | Step | Default | Rationale |
|-----------|---------|-------|-------|------|---------|-----------|
| `r_offset` | `xy-pad` | Red Offset | -100 -- 100 (both axes) | 1 | (10, 0) | XY tuple is the defining use case for an XY pad. Users drag the red channel in 2D space. |
| `g_offset` | `xy-pad` | Green Offset | -100 -- 100 (both axes) | 1 | (0, 0) | Same as above. Each channel gets its own pad. |
| `b_offset` | `xy-pad` | Blue Offset | -100 -- 100 (both axes) | 1 | (-10, 0) | Same as above. |

**Special behavior:** Each XY pad should be color-tinted to match its channel (red tint, green tint, blue tint on the pad background or border). The three pads should be arranged horizontally in a row labeled R / G / B.

**Quick/Advanced mode:** No split needed. All three pads are the core interaction.

---

#### 3. displacement

| Parameter | Control | Label | Range | Step | Default | Rationale |
|-----------|---------|-------|-------|------|---------|-----------|
| `block_size` | `knob` | Block Size | 4 -- 64 | 1 | 16 | Sweepable integer range. Knob with integer snapping. Bigger blocks = more chaotic, so sweeping feels natural. |
| `intensity` | `knob` | Intensity | 0.0 -- 50.0 | 0.5 | 10.0 | Classic intensity/amount knob. Continuous sweep. |
| `seed` | `number-input` | Seed | 0 -- 99999 | 1 | 42 | Seeds are not swept -- they are either typed or randomized. Number input with a "dice" randomize button next to it. |

**Special behavior:** The seed parameter should have a small dice/shuffle button that generates a random integer on click.

**Quick/Advanced mode:** Seed is **advanced**. Most users just want block_size and intensity.

---

#### 4. bitcrush

| Parameter | Control | Label | Range | Step | Default | Rationale |
|-----------|---------|-------|-------|------|---------|-----------|
| `color_depth` | `knob` | Bit Depth | 1 -- 16 | 1 | 4 | Integer sweep from extreme crush (1-bit) to full depth (16-bit). Knob with integer snapping. Very satisfying to sweep. |
| `resolution_scale` | `knob` | Resolution | 0.1 -- 4.0 | 0.1 | 1.0 | Continuous float. Below 1.0 = pixelation, above 1.0 = oversample. Knob is natural. |

**Quick/Advanced mode:** Both parameters are essential. No split needed.

---

### DISTORTION Category

#### 5. wave

| Parameter | Control | Label | Range | Step | Default | Rationale |
|-----------|---------|-------|-------|------|---------|-----------|
| `amplitude` | `knob` | Amplitude | 0.0 -- 50.0 | 0.5 | 10.0 | How far pixels displace. Classic sweep parameter. |
| `frequency` | `knob` | Frequency | 0.0 -- 1.0 | 0.01 | 0.05 | Wave density. Sweeping from slow undulation to tight ripple. |
| `direction` | `dropdown` | Direction | horizontal, vertical | -- | horizontal | Binary mode selection. |

**Quick/Advanced mode:** All essential. No split needed.

---

#### 6. mirror

| Parameter | Control | Label | Range | Step | Default | Rationale |
|-----------|---------|-------|-------|------|---------|-----------|
| `axis` | `dropdown` | Axis | vertical, horizontal | -- | vertical | Binary mode selection. |
| `position` | `slider` | Position | 0.1 -- 0.9 | 0.01 | 0.5 | A slider is ideal here because the user is choosing WHERE to place the mirror line. A horizontal slider for a spatial "where along the axis" value maps 1:1 to the visual result. More intuitive than a knob for positional values. |

**Quick/Advanced mode:** Both essential.

---

#### 7. chromatic

| Parameter | Control | Label | Range | Step | Default | Rationale |
|-----------|---------|-------|-------|------|---------|-----------|
| `offset` | `knob` | Offset | 0 -- 20 | 1 | 5 | How far channels split. Integer sweep, knob with snapping. |
| `direction` | `dropdown` | Direction | horizontal, vertical, radial | -- | horizontal | 3 discrete modes. Dropdown. |

**Quick/Advanced mode:** Both essential.

---

### TEXTURE Category

#### 8. scanlines

| Parameter | Control | Label | Range | Step | Default | Rationale |
|-----------|---------|-------|-------|------|---------|-----------|
| `line_width` | `knob` | Line Width | 1 -- 10 | 1 | 2 | Small integer range. Knob with integer snapping feels good for "thicker/thinner". |
| `opacity` | `knob` | Opacity | 0.0 -- 1.0 | 0.01 | 0.3 | Classic opacity control. Always a knob. |
| `flicker` | `toggle` | Flicker | on/off | -- | off | Boolean. Toggle switch. |
| `color` | `color-picker` | Line Color | RGB (0-255 per channel) | 1 | (0, 0, 0) | RGB tuple demands a color picker. Shows a swatch of the current color; clicking opens a color wheel/palette. |

**Quick/Advanced mode:** `color` is **advanced** (defaults to black, most users will never change it). Quick mode shows line_width, opacity, and flicker only.

---

#### 9. vhs

| Parameter | Control | Label | Range | Step | Default | Rationale |
|-----------|---------|-------|-------|------|---------|-----------|
| `tracking` | `knob` | Tracking | 0.0 -- 1.0 | 0.01 | 0.5 | Classic VHS tracking knob. Sweepable. The name even evokes a physical knob on old VCRs. |
| `noise_amount` | `knob` | Noise | 0.0 -- 1.0 | 0.01 | 0.2 | Amount/intensity parameter. Always a knob. |
| `color_bleed` | `knob` | Color Bleed | 0 -- 20 | 1 | 3 | Integer sweep for how much color smears. Knob with snapping. |
| `seed` | `number-input` | Seed | 0 -- 99999 | 1 | 42 | Non-sweepable. Number input with randomize button. |

**Special behavior:** Seed gets the dice/randomize button.

**Quick/Advanced mode:** `seed` is **advanced**. Quick mode shows tracking, noise, and color_bleed.

---

#### 10. noise

| Parameter | Control | Label | Range | Step | Default | Rationale |
|-----------|---------|-------|-------|------|---------|-----------|
| `amount` | `knob` | Amount | 0.0 -- 1.0 | 0.01 | 0.3 | How much noise. Classic amount knob. |
| `noise_type` | `dropdown` | Type | gaussian, salt_pepper, uniform | -- | gaussian | 3 discrete algorithm choices. Dropdown. |
| `seed` | `number-input` | Seed | 0 -- 99999 | 1 | 42 | Non-sweepable. Number input with randomize button. |

**Special behavior:** Seed gets the dice/randomize button.

**Quick/Advanced mode:** `seed` is **advanced**. Quick mode shows amount and noise_type.

---

#### 11. blur

| Parameter | Control | Label | Range | Step | Default | Rationale |
|-----------|---------|-------|-------|------|---------|-----------|
| `radius` | `knob` | Radius | 1 -- 20 | 1 | 3 | Integer sweep. Higher radius = more blur. Knob with integer snapping. |
| `blur_type` | `dropdown` | Type | box, motion | -- | box | 2 discrete modes. Dropdown. |

**Quick/Advanced mode:** Both essential.

---

#### 12. sharpen

| Parameter | Control | Label | Range | Step | Default | Rationale |
|-----------|---------|-------|-------|------|---------|-----------|
| `amount` | `knob` | Amount | 0.0 -- 3.0 | 0.05 | 1.0 | Single-parameter effect. Knob is the only control needed. Clean and simple. |

**Quick/Advanced mode:** Single parameter. No split needed.

---

#### 13. edges

| Parameter | Control | Label | Range | Step | Default | Rationale |
|-----------|---------|-------|-------|------|---------|-----------|
| `threshold` | `knob` | Threshold | 0.0 -- 1.0 | 0.01 | 0.3 | Continuous sweep for edge sensitivity. Knob. |
| `mode` | `dropdown` | Mode | overlay, neon, edges_only | -- | overlay | 3 visual modes. Dropdown. |

**Quick/Advanced mode:** Both essential.

---

#### 14. posterize

| Parameter | Control | Label | Range | Step | Default | Rationale |
|-----------|---------|-------|-------|------|---------|-----------|
| `levels` | `knob` | Levels | 2 -- 32 | 1 | 4 | Integer sweep. Fewer levels = more posterized. Very satisfying to sweep with a knob. The visual feedback is immediate and dramatic. |

**Quick/Advanced mode:** Single parameter. No split needed.

---

### COLOR Category

#### 15. hueshift

| Parameter | Control | Label | Range | Step | Default | Rationale |
|-----------|---------|-------|-------|------|---------|-----------|
| `degrees` | `hue-wheel` | Hue Shift | 0 -- 360 | 1 | 180 | This is THE use case for a hue wheel. The parameter is literally a rotation around the hue circle. A linear knob would break the circular mental model (359 and 0 are adjacent, not far apart). The wheel should show the color spectrum around its edge. |

**Special behavior:** The hue wheel should display the full spectrum (ROYGBIV) around its circumference. A draggable handle indicates the current rotation. The center of the wheel can show a preview swatch of what "pure red" maps to at the current rotation.

**Quick/Advanced mode:** Single parameter. No split needed.

---

#### 16. contrast

| Parameter | Control | Label | Range | Step | Default | Rationale |
|-----------|---------|-------|-------|------|---------|-----------|
| `amount` | `knob` | Amount | 0 -- 200 | 1 | 50 | Large integer range representing contrast percentage. Knob with integer snapping. |
| `curve` | `dropdown` | Curve | linear | -- | linear | Currently only one option, but structured as a dropdown for future curve types (sigmoid, s-curve, etc.). |

**Quick/Advanced mode:** `curve` is **advanced** (only one option currently). Quick mode shows amount only.

---

#### 17. saturation

| Parameter | Control | Label | Range | Step | Default | Rationale |
|-----------|---------|-------|-------|------|---------|-----------|
| `amount` | `knob` | Amount | 0.0 -- 5.0 | 0.05 | 1.5 | Continuous multiplier. 0 = grayscale, 1 = original, >1 = boosted. Knob. |
| `channel` | `dropdown` | Channel | all | -- | all | Currently one option. Dropdown for future per-channel saturation (r, g, b). |

**Quick/Advanced mode:** `channel` is **advanced**. Quick mode shows amount only.

---

#### 18. exposure

| Parameter | Control | Label | Range | Step | Default | Rationale |
|-----------|---------|-------|-------|------|---------|-----------|
| `stops` | `slider` | Stops | -3.0 -- 3.0 | 0.1 | 1.0 | Bipolar range (negative = darken, positive = brighten). A horizontal slider is ideal for bipolar/before-after values. The center position (0) is "no change", which maps cleanly to a slider's center detent. |
| `clip_mode` | `dropdown` | Clip Mode | clip | -- | clip | Currently one option. Dropdown for future modes (soft clip, wrap, etc.). |

**Special behavior:** The slider should have a center detent/notch at 0.0 (no exposure change). The left side could be tinted darker, the right side tinted brighter for visual context.

**Quick/Advanced mode:** `clip_mode` is **advanced**. Quick mode shows stops only.

---

#### 19. invert

| Parameter | Control | Label | Range | Step | Default | Rationale |
|-----------|---------|-------|-------|------|---------|-----------|
| `channel` | `dropdown` | Channel | all, r, g, b | -- | all | 4 discrete options for which channel(s) to invert. Dropdown. |
| `amount` | `knob` | Amount | 0.0 -- 1.0 | 0.01 | 1.0 | Partial inversion blend. 0 = no inversion, 1 = full inversion. Knob. |

**Quick/Advanced mode:** Both essential. Inverting specific channels is a core creative choice.

---

#### 20. temperature

| Parameter | Control | Label | Range | Step | Default | Rationale |
|-----------|---------|-------|-------|------|---------|-----------|
| `temp` | `slider` | Temperature | -100 -- 100 | 1 | 30 | Bipolar range. Negative = cool (blue), positive = warm (orange). A slider is perfect because the left-to-right axis maps to cool-to-warm. The slider track itself should have a blue-to-orange gradient for instant visual feedback. |

**Special behavior:** The slider track should render as a gradient from blue (#4488ff) on the left to orange (#ff8844) on the right. This gives instant visual context without reading the number.

**Quick/Advanced mode:** Single parameter. No split needed.

---

## Effect Browser Sidebar Organization

### Category Order and Icons

The categories should appear in this order in the browser sidebar, matching the signal-chain mental model (glitch first as the most destructive, color last as the most subtle):

| Order | Category | Icon | Rationale |
|-------|----------|------|-----------|
| 1 | Glitch | `#` | Hash/fragment symbol suggests breaking apart. Distinct and technical. |
| 2 | Distortion | `~` | Tilde/wave suggests warping and bending. |
| 3 | Texture | `.:.` | Dot pattern suggests grain, scanlines, surface texture. |
| 4 | Color | `@` | At-sign as a circular color-wheel reference. Distinct from other icons. |

### Effect Order Within Categories

Effects within each category are ordered from most dramatic/destructive to most subtle:

**Glitch:** pixelsort, channelshift, displacement, bitcrush
**Distortion:** wave, mirror, chromatic
**Texture:** scanlines, vhs, noise, blur, sharpen, edges, posterize
**Color:** hueshift, contrast, saturation, exposure, invert, temperature

---

## Quick Mode vs Advanced Mode

Effects with advanced parameters should render with a disclosure toggle (small triangle or "..." button) that reveals hidden parameters. The quick mode shows only the most commonly adjusted parameters.

| Effect | Quick Mode Parameters | Advanced Parameters |
|--------|----------------------|---------------------|
| displacement | block_size, intensity | seed |
| scanlines | line_width, opacity, flicker | color |
| vhs | tracking, noise_amount, color_bleed | seed |
| noise | amount, noise_type | seed |
| contrast | amount | curve |
| saturation | amount | channel |
| exposure | stops | clip_mode |

All other effects show all parameters in quick mode (no advanced toggle needed).

---

## Implementation Notes

### Control Rendering Priority

When `renderChain()` builds device controls, it should check the control map and render the appropriate widget type instead of always rendering a knob. The rendering logic should be:

```
1. Look up effect name + param name in control-map.json
2. Based on control_type, call the appropriate renderer:
   - "knob"         -> createKnob() (existing)
   - "slider"       -> createSlider() (new)
   - "dropdown"     -> createDropdown() (new)
   - "toggle"       -> createToggle() (new)
   - "xy-pad"       -> createXYPad() (new)
   - "color-picker" -> createColorPicker() (new)
   - "number-input" -> createNumberInput() (new)
   - "hue-wheel"    -> createHueWheel() (new)
3. If param is in the "advanced" list, wrap it in a collapsible section
```

### Seed Randomize Button

All `seed` parameters across all effects share the same behavior:
- Render as a `number-input` with a dice button
- The dice button calls `Math.floor(Math.random() * 100000)`
- The randomized value is written to the device params and triggers a preview

### Double-Click to Reset

All controls (not just knobs) should support double-click to reset to default value. This is already implemented for knobs and should extend to sliders, XY pads, and number inputs.

### Keyboard Modifiers

- **Shift + drag** on knobs and sliders: Fine adjustment (existing for knobs, extend to sliders)
- **Cmd/Ctrl + click** on a dropdown: Cycle to next option without opening the menu
- **Alt + click** on any control: Reset to default (alternative to double-click)

---

## Data File

The machine-readable control map is located at:
`/ui/static/control-map.json`

This JSON file maps every effect parameter to its control configuration and is consumed by the frontend JavaScript to determine which widget to render.

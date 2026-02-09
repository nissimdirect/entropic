# Pop Chaos Design System v1.0

**For:** PopChaos Labs LLC
**Products:** Entropic (Video Glitch Engine), Audio Plugins (upcoming), Creative Tools
**Authors:** Art Director + Atrium (Art Critical Theory)
**Date:** 2026-02-08

---

## Table of Contents

1. [Philosophical Foundation](#1-philosophical-foundation)
2. [Color System](#2-color-system)
3. [Typography](#3-typography)
4. [Spacing & Layout](#4-spacing--layout)
5. [Visual Motifs](#5-visual-motifs)
6. [Logo Direction](#6-logo-direction)
7. [Iconography](#7-iconography)
8. [Brand Assets: ASCII Patterns](#8-brand-assets-ascii-patterns)
9. [Application to Entropic](#9-application-to-entropic)
10. [Anti-Patterns: What We Refuse](#10-anti-patterns-what-we-refuse)

---

## 1. Philosophical Foundation

### Art-Theoretical Grounding

Pop Chaos does not adopt glitch aesthetic as decoration. The work is positioned within a lineage of practices that treat system failure as epistemological revelation.

**Primary Art-Historical Lineages:**

| Movement | Relevance | Key Connection |
|----------|-----------|----------------|
| **Fluxus** (1960s) | Intermedia, anti-commodity art, the score as instruction | Entropic's recipe system mirrors Fluxus event scores: reproducible instructions for unreproducible outcomes |
| **Situationist International** (1957-1972) | Detournement, psychogeography, the spectacle | We detourne video itself; the tool is a critique of seamless media production |
| **Glitch Art / Post-Digital** (2000s-present) | Error as aesthetic, compression artifact as material | Direct lineage. But we push past surface aesthetics into structural engagement with codec logic |
| **Noise Music** (Merzbow, Wolf Eyes, Prurge) | Signal destruction as composition, the beauty in overload | Cross-modal: our "Mad Scientist" effects literally apply audio DSP to pixel data |
| **Net Art / JODI** (1990s) | Browser as medium, protocol as material, interface deconstruction | Our UI is functional but reveals its own mechanics; the tool does not hide its nature |

**Reference Artists and Why:**

- **Rosa Menkman** -- *The Glitch Moment(um)* and *Vernacular of File Formats*. Menkman's framework distinguishes between "glitch" (the unexpected moment of rupture) and "glitch-alike" (the commodified reproduction of that rupture). Pop Chaos tools produce actual glitches -- real JPEG byte corruption, authentic H.264 P-frame manipulation, genuine optical flow failure. The distinction matters. Our tools do not simulate glitch; they perform it.

- **JODI (Joan Heemskerk & Dirk Paesmans)** -- Their work treats the browser, the operating system, and the file format as sculptural material. Entropic treats the video codec the same way. When we corrupt JPEG scan data after the SOS marker, we are working at the same conceptual level as JODI's `%20Wrong` browser pieces -- intervening in the substrate.

- **Cory Arcangel** -- *Super Mario Clouds*, *Various Self-Playing Bowling Games*. Arcangel's practice of modifying existing systems (NES cartridges, Photoshop gradient tools) rather than building from scratch parallels our approach: we work with FFmpeg, OpenCV, and H.264 as given systems and find creative misuses within them.

- **Nam June Paik** -- The grandfather of video art used magnets on CRT televisions to warp broadcast signals. Entropic's scanline effects, CRT phosphor colors, and signal-processing package are direct descendants. But where Paik worked with analog hardware, we work with digital code that models analog failure.

- **Legacy Russell** -- *Glitch Feminism: A Manifesto*. Russell argues that glitch is not merely aesthetic but an act of refusal: the refusal to render correctly, to perform as expected, to be seamlessly consumed. Pop Chaos tools give users the power of that refusal. Every preset named "Nuclear" is an act of refusal against clean media.

- **Hito Steyerl** -- *In Defense of the Poor Image*. Steyerl's argument that low-resolution, degraded, compressed images carry their own truth and political charge is foundational. Entropic's CRF Degradation effect, its Re-encode Decay, its bitcrushing -- these are not failures of quality but assertions of a different kind of value.

### The Philosophical Stance

**Entropy as creative force.** The second law of thermodynamics guarantees that all ordered systems tend toward disorder. Pop Chaos does not fight this; it collaborates with it. The name "Entropic" is literal: the tool accelerates entropy in digital media and reveals what emerges.

**Destruction as creation.** Every effect in Entropic is an act of controlled destruction. But destruction and creation are not opposites -- they are the same process viewed from different temporal positions. A pixel sort destroys the original image's spatial coherence and creates a new formal arrangement. A datamosh destroys temporal coherence and creates hallucinatory inter-frame hybrids. The tool makes this visible.

**The beauty in broken systems.** When a JPEG file is corrupted, the decoder does not simply fail -- it produces. The macroblock artifacts, the color smearing, the half-rendered frames are not absence of image but a different kind of image, one that reveals the internal logic of the compression algorithm. Pop Chaos aesthetics are grounded in this productive failure.

### Differentiation from Commodified Glitch

The "glitch aesthetic" has been absorbed into mainstream visual culture -- Instagram filters, Tiktok effects, music video production. This is Menkman's "glitch-alike": the appearance of rupture without actual rupture. Pop Chaos differentiates in three ways:

1. **Structural engagement.** Our tools work at the level of actual file formats, codecs, and data structures. Byte corruption is real byte corruption. Datamoshing manipulates real H.264 motion vectors. This is not a Photoshop filter that "looks glitchy."

2. **Process transparency.** Entropic's recipe system, its CLI interface, its open-source code -- the tool does not hide its mechanics. Users understand that `bytecorrupt amount=80 jpeg_quality=15` is a specific intervention in a specific data format. This is the opposite of a one-tap filter.

3. **Escalation without ceiling.** The "Nuclear" tier in every package is not decoration. It represents actual system-stress testing: pushing parameters to values where the output becomes genuinely unpredictable. Commodified glitch is safe. Pop Chaos offers the option to go past safety.

---

## 2. Color System

### Design Rationale

The palette draws from three physical/cultural sources:
- **CRT phosphors** -- The specific greens, ambers, and blues of cathode ray tube displays
- **Warning systems** -- Nuclear/biohazard signage, caution tape, emergency lighting
- **UV-reactive materials** -- Blacklight posters, fluorescent spray paint, rave culture

These are not arbitrary aesthetic choices. Each source connects to the tool's identity: CRT phosphors reference the history of video art (Paik, Steina & Woody Vasulka); warning colors reference the "dangerous" nature of destructive tools; UV-reactive materials reference underground music culture (DnB, jungle, breakbeat).

### Color Tokens

#### Backgrounds (The Void)

| Token | Hex | RGB | Use |
|-------|-----|-----|-----|
| `--bg-void` | `#050506` | 5, 5, 6 | Deepest background, canvas area when empty |
| `--bg-darkest` | `#0a0a0b` | 10, 10, 11 | Primary application background |
| `--bg-dark` | `#111114` | 17, 17, 20 | Panel backgrounds, sidebars |
| `--bg-mid` | `#1a1a1e` | 26, 26, 30 | Device backgrounds, input fields |
| `--bg-raised` | `#222228` | 34, 34, 40 | Elevated surfaces, cards |
| `--bg-hover` | `#2a2a32` | 42, 42, 50 | Interactive hover states |
| `--bg-active` | `#33333d` | 51, 51, 61 | Active/selected surfaces |

Note: Background blacks are not pure black (#000) but carry a subtle blue-violet undertone (the last RGB channel is always slightly higher). This references the phosphor persistence of CRT monitors -- even a "black" CRT screen emits faint blue.

#### Primary: Signal Red

| Token | Hex | RGB | Use |
|-------|-----|-----|-----|
| `--red-core` | `#ff2d2d` | 255, 45, 45 | Primary accent, buttons, active indicators |
| `--red-bright` | `#ff4d4d` | 255, 77, 77 | Hover state, emphasis |
| `--red-dim` | `#cc2222` | 204, 34, 34 | Pressed/active state |
| `--red-glow` | `#ff2d2d33` | 255, 45, 45, 0.2 | Glow/halo effect behind active elements |
| `--red-ember` | `#661111` | 102, 17, 17 | Subtle background tint for danger zones |

Signal Red is not decorative. It is the color of the recording light on a VCR, the LED on a mixing desk that means "clipping," the warning light that means "this will change something irreversibly." In the UI, red means "this does something."

#### Secondary: Phosphor Green

| Token | Hex | RGB | Use |
|-------|-----|-----|-----|
| `--green-phosphor` | `#39ff14` | 57, 255, 20 | Terminal text, matrix effects, "system active" |
| `--green-dim` | `#1a7a0a` | 26, 122, 10 | Muted green for secondary indicators |
| `--green-glow` | `#39ff1422` | 57, 255, 20, 0.13 | Scanline tint, ghost glow |
| `--green-dark` | `#0d3a06` | 13, 58, 6 | Deep background tint for terminal areas |

This is P1 phosphor green -- the specific green of early CRT monitors. Not the blue-green of a modern "Matrix" filter, but the yellow-green of actual hardware. It references both terminal culture and the "Green" color mode already in Entropic's ASCII art effect.

#### Tertiary: CRT Amber

| Token | Hex | RGB | Use |
|-------|-----|-----|-----|
| `--amber-warm` | `#ffbf00` | 255, 191, 0 | Warm warnings, power-on indicators, bypass states |
| `--amber-dim` | `#b38600` | 179, 134, 0 | Muted amber for secondary elements |
| `--amber-glow` | `#ffbf0022` | 255, 191, 0, 0.13 | Warm glow behind active amber elements |

P3 phosphor amber. The color of Hercules graphics adapters, early word processors, and airport departure boards. In the UI, amber means "enabled but not recording" -- device power-on indicators, bypass states, "this is active but not destructive."

#### Accent: Nuclear / UV

| Token | Hex | RGB | Use |
|-------|-----|-----|-----|
| `--uv-violet` | `#7b61ff` | 123, 97, 255 | Secondary accent, selections, links |
| `--uv-bright` | `#9d85ff` | 157, 133, 255 | Hover states for violet elements |
| `--uv-glow` | `#7b61ff22` | 123, 97, 255, 0.13 | Selection glow |
| `--cyan-electric` | `#00fff7` | 0, 255, 247 | Highlight accent, special states, "new" badges |
| `--cyan-dim` | `#00b3ad` | 0, 179, 173 | Muted cyan for secondary use |
| `--magenta-hot` | `#ff00ff` | 255, 0, 255 | Error states, "nuclear" tier, maximum intensity |
| `--magenta-dim` | `#990099` | 153, 0, 153 | Muted magenta |

UV violet references blacklight posters and rave culture. Electric cyan is the color of cheap LED strips in underground club lighting. Hot magenta is the color of CRT color fringing at maximum saturation -- the color a monitor makes when it is failing.

#### Text

| Token | Hex | RGB | Use |
|-------|-----|-----|-----|
| `--text-primary` | `#e0e0e4` | 224, 224, 228 | Primary readable text |
| `--text-secondary` | `#888890` | 136, 136, 144 | Secondary text, labels |
| `--text-dim` | `#555560` | 85, 85, 96 | Hint text, disabled states |
| `--text-ghost` | `#333340` | 51, 51, 64 | Barely visible watermarks, grid lines |

Text colors carry the same blue-violet undertone as backgrounds -- never pure gray but slightly cool, like text on a phosphor display.

#### Semantic Colors

| Token | Hex | Use |
|-------|-----|-----|
| `--status-success` | `#39ff14` | Render complete, build success |
| `--status-warning` | `#ffbf00` | Near limits, budget warnings |
| `--status-error` | `#ff2d2d` | Build failure, file errors |
| `--status-info` | `#7b61ff` | Informational, metadata |
| `--border-default` | `#2a2a35` | Default borders |
| `--border-subtle` | `#1e1e28` | Subtle separators |
| `--border-strong` | `#3a3a48` | Emphasis borders |

### Color Usage Rules

1. **No more than two high-chroma colors on screen simultaneously.** Red + one other accent. The rest is dark backgrounds and neutral text.
2. **Glow effects are always the accent color at 13-20% opacity.** Never a different color.
3. **Backgrounds darken toward the edges.** The center canvas is the darkest; surrounding panels are slightly lighter. This creates a natural vignette that focuses attention on the media being edited.
4. **Color indicates function, not decoration.** Red = destructive action. Amber = active state. Green = system confirmation. Violet = selection/navigation.

---

## 3. Typography

### Design Rationale

Typography is monospace-first. This is not an aesthetic choice made lightly -- it is structural:
- Entropic is a CLI tool first, GUI second. Monospace bridges both interfaces.
- Glitch art involves hex values, byte offsets, coordinate pairs, and parameter numbers. These read best in monospace.
- Terminal culture (hacker aesthetic, tracker music, BBS) is monospace culture.
- Monospace text on a dark background with phosphor-colored characters IS the aesthetic.

### Type Scale

#### Primary: JetBrains Mono

**Role:** Headers, logo text, effect names, anything that needs authority.

| Context | Size | Weight | Letter Spacing | Line Height |
|---------|------|--------|----------------|-------------|
| H1 (Logo/Title) | 24px | 700 | +4px | 1.0 |
| H2 (Section) | 18px | 700 | +3px | 1.2 |
| H3 (Panel Title) | 13px | 600 | +2px | 1.3 |
| H4 (Category) | 10px | 600 | +2px | 1.4 |

**Why JetBrains Mono:** It has programming ligatures that can be disabled, distinctive letterforms at small sizes, and a slightly wider character width than Fira Code. The wider width gives it presence. It reads as "engineered" rather than "designed."

**Fallback stack:** `'JetBrains Mono', 'SF Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace`

#### Secondary: Space Mono

**Role:** Body text, descriptions, longer passages (preset descriptions, documentation).

| Context | Size | Weight | Letter Spacing | Line Height |
|---------|------|--------|----------------|-------------|
| Body | 13px | 400 | +0.5px | 1.5 |
| Small | 11px | 400 | +0.5px | 1.4 |
| Caption | 9px | 400 | +1px | 1.3 |

**Why Space Mono:** Google's Space Mono was designed by Colophon Foundry for headlines but works at body sizes. It has a quirky, slightly irregular quality -- the `g` has an open tail, the `a` is single-story -- that gives it personality without sacrificing readability. It feels "human-made" in a way that purely technical monospace fonts do not.

**Fallback stack:** `'Space Mono', 'IBM Plex Mono', 'Source Code Pro', monospace`

#### Tertiary: System Monospace (for data display)

**Role:** Parameter values, hex codes, file paths, timestamps, frame numbers.

| Context | Size | Weight | Letter Spacing | Line Height |
|---------|------|--------|----------------|-------------|
| Data | 10px | 400 | 0 | 1.2 |
| Data Large | 12px | 400 | 0 | 1.2 |

**Font:** `'SF Mono', 'Menlo', 'Monaco', monospace` (system default)

This uses the system monospace because data display needs maximum legibility and tabular number alignment. No personality needed -- just clarity.

### Typography Rules

1. **ALL CAPS with wide letter-spacing for labels and category headers.** This mimics hardware panel labels on synthesizers and audio equipment. `THRESHOLD`, `INTENSITY`, `EFFECT CHAIN`.
2. **Never use a sans-serif or serif typeface.** Everything is monospace. If something "needs" a proportional font, redesign the layout so it does not.
3. **Numbers use tabular figures (font-variant-numeric: tabular-nums).** Parameter values, frame counts, and percentages must align vertically.
4. **Underscores, not spaces, in multi-word tokens.** `pixel_sort`, not "Pixel Sort." When displaying to users, underscores are kept visible. This is a terminal-culture convention that reinforces the tool's identity.

---

## 4. Spacing & Layout

### Grid System

The layout uses an 8px base grid with a 4px half-grid for fine adjustments.

| Token | Value | Use |
|-------|-------|-----|
| `--space-1` | 4px | Minimum gap, tight padding |
| `--space-2` | 8px | Default gap, standard padding |
| `--space-3` | 12px | Comfortable padding, section gaps |
| `--space-4` | 16px | Panel padding, major gaps |
| `--space-5` | 24px | Section separation |
| `--space-6` | 32px | Major section breaks |
| `--space-8` | 64px | Hero spacing, major landmarks |

### Layout Tokens

| Token | Value | Use |
|-------|-------|-----|
| `--sidebar-width` | 220px | Left browser, right panel |
| `--chain-height` | 200px | Bottom effect chain rack |
| `--topbar-height` | 44px | Top navigation bar |
| `--device-min-width` | 180px | Minimum width for effect device in chain |
| `--device-max-width` | 240px | Maximum width for effect device in chain |
| `--knob-size` | 40px | Standard knob diameter |
| `--knob-size-sm` | 32px | Small knob for compact views |
| `--border-radius-sm` | 2px | Subtle rounding (buttons, tags) |
| `--border-radius-md` | 4px | Standard rounding (devices, cards) |
| `--border-radius-lg` | 8px | Large rounding (modals, dialogs) |
| `--border-width` | 1px | Standard border |

### Layout Principles

1. **The canvas is sacred.** The center preview area is always the largest element. Everything else defers to it. No panel should ever crowd the canvas.

2. **Horizontal flow for effect chains.** Effects flow left-to-right in the bottom rack, mirroring the signal chain mental model from audio production (input -> processing -> output). This is how Ableton Live, Logic Pro, and hardware effect pedalboards work.

3. **Vertical flow for browsing.** The left sidebar scrolls vertically. Categories are stacked. This mirrors file browsers and Photoshop's layers panel.

4. **1px gaps between major panels.** Panels are separated by hairline gaps that reveal the border color behind them. This creates a "tiled" appearance like a terminal multiplexer (tmux) or a tiling window manager. It references hacker culture's workspace organization.

5. **No rounded corners on panels, only on interactive elements.** The overall application frame is sharp-cornered. Only buttons, knobs, and devices get border-radius. This distinction separates "structure" (sharp, architectural) from "interaction" (softer, touchable).

6. **Dense information display.** Text is small (10-12px). Spacing is tight. This is not a consumer app with generous white space -- it is a professional tool. The density communicates "this tool does a lot." Reference: Ableton Live's Session View, Blender's interface.

---

## 5. Visual Motifs

### Scan Lines

The horizontal scan line is the primary visual motif of Pop Chaos. It references:
- CRT display technology (physical scan lines from electron beam raster)
- VHS tracking artifacts
- Entropic's own `scanlines` effect (one of the 8 original shipped effects)
- The horizontal nature of video: scan lines are how video IS

**Implementation:**
- Thin horizontal lines at 50% opacity, spaced 2-4px apart
- Applied as a CSS background pattern on surfaces that need texture:
```css
background-image: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 3px,
    rgba(255, 255, 255, 0.015) 3px,
    rgba(255, 255, 255, 0.015) 4px
);
```
- Used sparingly: only on the canvas empty state, the about page, and marketing materials. NOT on every panel.

### Macroblock Grid

A subtle grid pattern referencing JPEG/H.264 macroblock structure (8x8 or 16x16 pixel blocks).

**Implementation:**
- 16x16 grid overlay at very low opacity (3-5%)
- Visible on hover over the canvas area
- Used in documentation and marketing to frame images

### Data Corruption Patterns

Three signature corruption patterns used as brand textures:

1. **Row Shift** -- Horizontal offset of pixel rows, creating a "torn" appearance. Used as a decorative element in headers and dividers.
2. **Channel Separation** -- RGB channels offset by a few pixels. Used as a hover/active state on the logo and key interactive elements.
3. **Block Damage** -- Random rectangular regions with shifted/inverted content. Used very sparingly as a loading or transition state.

### The Underscore Cursor

A blinking underscore `_` used as a loading indicator and a brand mark. It references:
- The terminal cursor waiting for input
- The creative potential of the blank page/screen
- The "I am alive and processing" state of a system

**Implementation:**
- CSS animation: 1s blink cycle, 50% duty cycle
- Used instead of a spinner for short loading states
- Can be combined with text: `rendering_` or `processing_`

### Noise / Grain

A subtle film grain overlay applied globally at very low intensity. This is NOT random static -- it is structured noise that references:
- Analog video noise (Gaussian distribution)
- Film grain (photographic, organic)
- The `noise` effect in Entropic

**Implementation:**
- SVG filter or CSS `background-image` with a small noise tile
- Opacity: 3-5%, never more
- Static, not animated (animated noise is distracting in a work tool)

---

## 6. Logo Direction

### "Pop Chaos" Wordmark

The Pop Chaos logo should look like it was rendered by a system that is malfunctioning.

**Core approach:** Set "POP CHAOS" in JetBrains Mono Bold, all caps, wide letter spacing (+6px). Then apply one of these treatments:

1. **Channel-Shifted Wordmark (Primary)**
   - The word "POP" is rendered three times, once in each RGB channel, with slight horizontal offsets (R: -3px, G: 0, B: +3px)
   - At rest, the channels overlap to form white text
   - On hover/animation, the channels separate to reveal the RGB split
   - The word "CHAOS" below or beside, in a single channel (green or amber), smaller weight

2. **Row-Shifted Wordmark (Secondary)**
   - "POPCHAOS" with every other row of pixels shifted 2-4px horizontally
   - Creates a subtle visual vibration while remaining readable
   - Works well at small sizes (favicon, watermark)

3. **ASCII Wordmark (Tertiary)**
   - The name rendered in ASCII block characters (see Section 8)
   - Used in CLI output, documentation headers, terminal contexts

### "Entropic" Product Mark

The Entropic logo should communicate "dissolution" or "decay."

**Core approach:** "ENTROPIC" in JetBrains Mono Bold, all caps, where the letterforms progressively degrade from left to right:

- "E" is clean and sharp
- "N" has a slight pixel offset
- "T" has a scan line through it
- "R" has block corruption
- "O" is partially pixelsorted
- "P" has channel separation
- "I" is barely visible through noise
- "C" is almost entirely dissolved

This creates a visual metaphor for entropy itself: order degrading into chaos across the span of the word.

**Color:** The text transitions from white (#e0e0e4) at "E" to signal red (#ff2d2d) at "C" -- cool to hot, order to energy.

### Logo Rules

1. **Minimum size:** 120px wide for the full wordmark. Below that, use the ASCII version or a single-letter mark.
2. **Clear space:** Minimum 1x the cap height on all sides.
3. **Background:** Always on dark backgrounds (--bg-darkest or --bg-void). Never on light.
4. **No containment shapes.** No circles, squares, or shields around the logo. The text IS the mark. Containment shapes imply stability; we communicate instability.

---

## 7. Iconography

### Style: ASCII / Monospace Glyph

Icons in the Pop Chaos system are not drawn illustrations -- they are typographic symbols. This choice:
- Maintains the monospace-terminal aesthetic
- Works at tiny sizes (9-12px)
- Requires no icon font or SVG sprite
- Can be rendered in any text context (CLI, UI, documentation)

### Icon Set

| Function | Glyph | Unicode | Notes |
|----------|-------|---------|-------|
| Glitch category | `#` | U+0023 | Hash/fragment |
| Distortion category | `~` | U+007E | Tilde/wave |
| Texture category | `.:.` | Custom | Dot-colon-dot pattern |
| Color category | `@` | U+0040 | Circle reference |
| Temporal category | `>>` | U+003E x2 | Fast-forward |
| Modulation category | `^v` | Custom | Oscillation |
| Enhance category | `*` | U+002A | Enhancement star |
| Destruction category | `XX` | Custom | Crossed out |
| Play/Preview | `>` | U+25B6 | Standard play |
| Stop | `[ ]` | Custom | Stop block |
| Record/Render | `(*)` | Custom | Record dot |
| Power On | `[ON]` | Custom | Text toggle |
| Power Off | `[--]` | Custom | Text toggle |
| Bypass | `[//]` | Custom | Diagonal slash |
| Add effect | `[+]` | Custom | Plus in brackets |
| Remove | `[x]` | Custom | x in brackets |
| Menu/More | `...` | U+2026 | Ellipsis |
| Upload | `[^]` | Custom | Up caret |
| Download | `[v]` | Custom | Down caret |
| Randomize | `[?]` | Custom | Question in brackets |
| Undo | `<-` | Custom | Left arrow |
| Redo | `->` | Custom | Right arrow |
| Warning | `/!\` | Custom | Exclamation in slashes |
| Folder | `[=]` | Custom | Lines in brackets |
| File | `[ ]` | Custom | Empty brackets |
| Eye (visible) | `(o)` | Custom | Eye open |
| Eye (hidden) | `(-)` | Custom | Eye closed |
| Favorite | `[*]` | Custom | Star in brackets |
| Lock | `{#}` | Custom | Hash in braces |
| Nuclear | `(!!!)` | Custom | Triple exclamation |

### Icon Rendering Rules

1. **Icons are always monospace text, never SVGs or raster images.** They must be renderable in a terminal.
2. **Icon color matches the context color.** Category icons use `--text-dim`. Active icons use the relevant accent color.
3. **Icons are enclosed in brackets `[]`, parens `()`, or braces `{}` when they represent interactive targets.** This gives them a visible hit area.
4. **At sizes below 10px, fall back to single characters.** `+` instead of `[+]`, `x` instead of `[x]`.

---

## 8. Brand Assets: ASCII Patterns

### Pop Chaos ASCII Logo (Primary)

```
 ____   ___  ____     ____ _   _    _    ___  ____
|  _ \ / _ \|  _ \   / ___| | | |  / \  / _ \/ ___|
| |_) | | | | |_) | | |   | |_| | / _ \| | | \___ \
|  __/| |_| |  __/  | |___|  _  |/ ___ \ |_| |___) |
|_|    \___/|_|      \____|_| |_/_/   \_\___/|____/
```

### Entropic ASCII Logo

```
 _____ _   _ _____ ____   ___  ____ ___ ____
| ____| \ | |_   _|  _ \ / _ \|  _ \_ _/ ___|
|  _| |  \| | | | | |_) | | | | |_) | | |
| |___| |\  | | | |  _ <| |_| |  __/| | |___
|_____|_| \_| |_| |_| \_\\___/|_|  |___\____|
```

### Entropic ASCII Logo (Corrupted Variant)

```
 _____ _   _ _____ ____   ___  ____ ___ ____
| ____| \ | |_   _|  _ \ / _ \|  _ \_ _/ ___|
|  _  |  \| | | | | |_) | | | | |_) | | |
| |_  | |\  | |_| |  _ <|_|_| |  __/| | |___
|__ __|_| \_| |_| |_| \_\\___/|_|  |___\_ __|
  d a t a   i s   f r a g i l e
```

### Divider Pattern: Row Shift

```
============================================
=====    ======================================
============================================
==       ==========================================
============================================
```

### Divider Pattern: Scan Line

```
----------------------------------------
    ----    ----    ----    ----    ----
----------------------------------------
```

### Divider Pattern: Block Corruption

```
+--------+--------+--------+--------+
|        | ##  ## |        |  ####  |
|        | ##  ## |        |  ####  |
+--------+--------+--------+--------+
|  ####  |        | ####   |        |
|  ####  |        | ####   |        |
+--------+--------+--------+--------+
```

### Loading States

```
entropic> rendering_
entropic> rendering
entropic> rendering_
```

```
[##########..........] 50% processing
[################....] 80% processing_
[####################] done
```

### Version Badge

```
 +-----------------+
 | ENTROPIC v0.3.0 |
 | 63 effects      |
 | popchaos labs   |
 +-----------------+
```

### Nuclear Warning Badge

```
 /!\ NUCLEAR /!\
 +--------------+
 | DESTRUCTIVE  |
 | IRREVERSIBLE |
 +--------------+
```

---

## 9. Application to Entropic

### Mapping Design System to Existing UI

The existing Entropic UI (`/Users/nissimagent/Development/entropic/ui/static/style.css`) already implements many of these principles. Here is a reconciliation:

| Existing Variable | Design System Token | Status |
|-------------------|---------------------|--------|
| `--bg-darkest: #0a0a0b` | `--bg-darkest: #0a0a0b` | Already aligned |
| `--bg-dark: #141416` | `--bg-dark: #111114` | Adjust slightly bluer |
| `--bg-mid: #1e1e22` | `--bg-mid: #1a1a1e` | Adjust slightly bluer |
| `--accent: #ff3d3d` | `--red-core: #ff2d2d` | Shift slightly. Current is good. |
| `--accent-secondary: #7b61ff` | `--uv-violet: #7b61ff` | Already aligned |
| `--on-color: #f5a623` | `--amber-warm: #ffbf00` | Shift to true amber |
| `--active-green: #4caf50` | `--green-phosphor: #39ff14` | Shift to phosphor green |

### New Tokens to Add

The existing CSS lacks these design system tokens:

```css
/* Add to :root in style.css */
--green-phosphor: #39ff14;
--cyan-electric: #00fff7;
--magenta-hot: #ff00ff;
--red-glow: #ff2d2d33;
--uv-glow: #7b61ff22;
--amber-glow: #ffbf0022;
--text-ghost: #333340;
--border-subtle: #1e1e28;
```

### Effect Chain Visual Language

Each effect category in the bottom chain rack should have a subtle color coding:

| Category | Left-Border Color | Reference |
|----------|-------------------|-----------|
| Glitch | `--red-core` | Destructive, dangerous |
| Distortion | `--uv-violet` | Spatial, bending |
| Texture | `--text-secondary` | Neutral, surface |
| Color | `--cyan-electric` | Chromatic, spectral |
| Temporal | `--amber-warm` | Time-based, sequential |
| Modulation | `--green-phosphor` | Signal, waveform |
| Enhance | `--text-primary` | Clean, corrective |
| Destruction | `--magenta-hot` | Nuclear, extreme |

### Preset Category Badges

In the preset browser, category labels should use color coding:

| Category | Badge Color | Badge Text Style |
|----------|-------------|------------------|
| Classic | `--amber-warm` on `--bg-mid` | Warm, nostalgic |
| Cinematic | `--uv-violet` on `--bg-mid` | Cool, dramatic |
| Experimental | `--cyan-electric` on `--bg-mid` | Electric, unusual |
| Extreme | `--red-core` on `--bg-mid` | Hot, dangerous |
| Subtle | `--text-dim` on `--bg-mid` | Quiet, minimal |

### Gradio UI Theme Mapping

The existing Gradio UI (`gradio_ui.py`) uses `gr.themes.Base(primary_hue="red", secondary_hue="purple", neutral_hue="zinc")`. This already aligns with the design system's red primary / violet secondary / cool neutral pattern. No changes needed for the Gradio interface.

### CLI Output Styling

When Entropic runs in the terminal, it should use ANSI color codes that map to the design system:

| Context | ANSI Code | Design System Token |
|---------|-----------|---------------------|
| Effect names | Bold white | `--text-primary` |
| Parameter values | Default (no color) | `--text-secondary` |
| Categories | Bold + color | Category-specific |
| Errors | Red | `--red-core` |
| Success | Green | `--green-phosphor` |
| Warnings | Yellow | `--amber-warm` |
| Info | Cyan | `--cyan-electric` |

---

## 10. Anti-Patterns: What We Refuse

This section is as important as the system itself. These are the traps we consciously avoid.

### 1. "Aesthetic Rebellion That's Actually Just Another Product"

**The trap:** Making tools that look rebellious but function identically to mainstream creative software. Slapping scan lines on a Figma clone.

**Our response:** The tool IS different, not just its appearance. Entropic's recipe system, its CLI-first design, its open parameters, its datamosh engine that manipulates real H.264 streams -- these are structural differences. The design system reflects these structural differences rather than decorating conventional functionality.

### 2. The "Glitch Filter" Problem

**The trap:** Reducing glitch to a one-tap filter that produces the same result every time. This is what Menkman calls the "glitch-alike" -- it looks like a glitch but has none of the unpredictability, none of the system revelation, none of the productive failure.

**Our response:** Every effect in Entropic has exposed parameters with meaningful ranges. The seed parameter exists for reproducibility, but the default path encourages exploration. The Nuclear tier of every package pushes into genuinely unpredictable territory. The design system reflects this by never showing a "glitch" decoration that is purely cosmetic -- every visual glitch element in the UI maps to an actual capability of the tool.

### 3. Dark Mode Cliche

**The trap:** Using a dark theme because it is trendy, rather than because it serves the work.

**Our response:** Dark backgrounds are required for accurate visual assessment of glitch effects. Bright UI elements create false contrast perception. The dark theme is a professional requirement (reference: DaVinci Resolve, Nuke, Flame -- all color-critical tools use dark interfaces). We use it because the work demands it, not because it "looks cool."

### 4. Nostalgic Cosplay

**The trap:** Fetishizing retro technology (VHS, CRT, tape) as pure nostalgia without engaging with what those technologies actually meant.

**Our response:** Our CRT references are grounded in the physical reality of phosphor displays, not in a romanticized memory of them. Our VHS effects model actual magnetic tape degradation. Our retro aesthetic connects to a real history of video art (Paik, Vasulka) and underground music culture (jungle/DnB pirate radio, DIY tape trading). It is specific, not generic.

### 5. Complexity Theater

**The trap:** Making the interface look complex to seem "professional" without the complexity serving a purpose.

**Our response:** Every parameter in the UI exists because the effect engine actually uses it. No fake knobs. No decorative VU meters. If it is on screen, it does something. The density of the interface reflects the density of the tool's capabilities, not a desire to impress.

### 6. Appropriation Without Credit

**The trap:** Taking from underground/marginalized cultures (rave, hacker, noise music, glitch art) without acknowledging the source.

**Our response:** This design system document explicitly credits its sources: the artists, movements, and cultures that inform the aesthetic. The tool's documentation references Rosa Menkman, Legacy Russell, JODI, and others by name. The design system is not "inspired by" these practices -- it is IN CONVERSATION with them.

---

## Appendix A: Quick Reference Card

### Color Cheat Sheet

```
BACKGROUNDS     #050506  #0a0a0b  #111114  #1a1a1e  #222228
                void     darkest  dark     mid      raised

PRIMARY RED     #ff2d2d  #ff4d4d  #cc2222  #ff2d2d33
                core     bright   dim      glow

PHOSPHOR GREEN  #39ff14  #1a7a0a  #39ff1422
                bright   dim      glow

CRT AMBER       #ffbf00  #b38600  #ffbf0022
                warm     dim      glow

UV VIOLET       #7b61ff  #9d85ff  #7b61ff22
                core     bright   glow

ELECTRIC CYAN   #00fff7  #00b3ad
                bright   dim

HOT MAGENTA     #ff00ff  #990099
                hot      dim

TEXT            #e0e0e4  #888890  #555560  #333340
                primary  secondary dim     ghost
```

### Type Cheat Sheet

```
HEADERS     JetBrains Mono 700   UPPERCASE +4px tracking
BODY        Space Mono 400       Mixed case +0.5px tracking
DATA        System Mono 400      As-is, tabular nums
LABELS      Any Mono 600         UPPERCASE +2px tracking 9-10px
```

### Spacing Cheat Sheet

```
4  8  12  16  24  32  64
|  |  |   |   |   |   |
1  2  3   4   5   6   8
```

---

*This document is the single source of truth for Pop Chaos visual identity. All products (Entropic, future audio plugins, portfolio website, marketing materials) derive from this system.*

*It is a living document. As the tools evolve and the artistic practice deepens, the design system evolves with them. But the philosophical foundation -- entropy as creative force, destruction as creation, structural engagement over surface decoration -- does not change.*

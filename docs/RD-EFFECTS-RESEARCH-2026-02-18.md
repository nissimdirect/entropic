# Entropic R&D: Novel Effects Research

**Date:** 2026-02-18
**Session:** Mad Scientist + Glitch Video workflow (entropic-rd)
**Current State:** 126 effects, 13 categories, Python/numpy/scipy/opencv stack
**Purpose:** Research-backed effect candidates for next Entropic build sprint

---

## Executive Summary

16 novel effect concepts researched across 6 new categories. All prototyped for 1080p CPU timing. Top 5 selected for build based on visual impact, novelty, chainability, brand alignment, and performance.

**Two new categories proposed:** Emergent Systems, Information Theory
**Total build estimate:** ~3 hours for all 5 top picks
**New dependencies:** None (all numpy/scipy/PIL only)

---

## Top 5 Effects to Build (Ranked)

### 1. compression_oracle — Intentional Codec Feedback
**Category:** Information Theory
**Score:** 23/25 | **Time:** 68ms at 1080p | **LOC:** ~20

JPEG-compress the frame at quality Q, diff against original, amplify the diff, add it back. The codec's lossy decisions become visible — block boundaries glow, mosquito noise becomes texture, banding becomes gradient art. Feed output back for iterative amplification.

```python
# Core algorithm
from PIL import Image
import io, numpy as np

def compression_oracle(frame, quality=5, amplification=3.0, iterations=1):
    result = frame.copy()
    for _ in range(iterations):
        img = Image.fromarray(result)
        buf = io.BytesIO()
        img.save(buf, 'JPEG', quality=quality)
        buf.seek(0)
        compressed = np.array(Image.open(buf))
        diff = np.abs(result.astype(np.int16) - compressed.astype(np.int16))
        result = np.clip(result.astype(np.float32) + diff * amplification, 0, 255).astype(np.uint8)
    return result
```

**Params:** quality (1-100), feedback_iterations (1-10), amplification (0.5-10.0), codec (jpeg/webp)
**Why novel:** Everyone hides compression artifacts. This celebrates them — makes the codec's math visible.
**Cross-pollination role:** Principle 3 (measurement to modulation) — diff output drives other effects.

---

### 2. logistic_cascade — Deterministic Chaos Threshold
**Category:** Information Theory
**Score:** 23/25 | **Time:** 13ms at 1080p | **LOC:** ~15

Logistic map x_{n+1} = r*x_n*(1-x_n) generates threshold values per-pixel. At r < 3.57: stable posterization. At r = 3.57-4.0: chaotic bifurcation — thresholds jump unpredictably but deterministically. Animate r from stable to chaos = video falls apart in a mathematically inevitable way.

```python
# Core algorithm
import numpy as np

def logistic_cascade(frame, r=3.9, iterations=20, color_mode='threshold'):
    x = frame.astype(np.float32) / 255.0
    for _ in range(iterations):
        x = r * x * (1 - x)
    if color_mode == 'threshold':
        return (x * 255).clip(0, 255).astype(np.uint8)
    elif color_mode == 'bifurcation':
        # Map final x back as brightness modulation
        return (frame.astype(np.float32) * x).clip(0, 255).astype(np.uint8)
```

**Params:** r_value (2.0-4.0), iterations (1-50), color_mode (threshold/gradient/bifurcation)
**Why novel:** Posterize exists everywhere. Posterize driven by deterministic chaos where math guarantees the order-to-disorder transition — philosophy as code.
**Cross-pollination role:** Principle 5 (chaos boundary) — the r slider IS the edge of chaos.

---

### 3. reaction_diffusion — Turing Pattern Generator
**Category:** Emergent Systems
**Score:** 22/25 | **Time:** 122ms at 1080p (10 iterations) | **LOC:** ~30

Gray-Scott reaction-diffusion using pixel brightness as initial chemical concentration. Video slowly grows organic spots, stripes, and labyrinthine patterns that emerge FROM the content, not overlaid on it.

```python
# Core algorithm
import numpy as np

def reaction_diffusion(frame, feed_rate=0.055, kill_rate=0.062,
                       diffusion_a=1.0, diffusion_b=0.5, iterations=10):
    h, w = frame.shape[:2]
    A = np.ones((h, w), dtype=np.float32)
    B = (frame[:,:,0].astype(np.float32) / 255.0) * 0.5

    for _ in range(iterations):
        lapA = np.roll(A,1,0)+np.roll(A,-1,0)+np.roll(A,1,1)+np.roll(A,-1,1) - 4*A
        lapB = np.roll(B,1,0)+np.roll(B,-1,0)+np.roll(B,1,1)+np.roll(B,-1,1) - 4*B
        A = np.clip(A + diffusion_a*lapA - A*B*B + feed_rate*(1-A), 0, 1)
        B = np.clip(B + diffusion_b*lapB + A*B*B - (kill_rate+feed_rate)*B, 0, 1)

    # Map B concentration to color
    out = frame.copy()
    mask = (B * 255).clip(0, 255).astype(np.uint8)
    out[:,:,0] = mask  # or blend with original
    return out
```

**Params:** feed_rate (0.01-0.1), kill_rate (0.01-0.1), diffusion_speed, iterations_per_frame (1-50)
**Why novel:** RD exists in generative art but nobody applies it as a video filter where the source image seeds the simulation.
**Cross-pollination role:** Principle 1 (output-as-seed) — RD patterns can seed CA, erosion, or crystal growth.
**Note:** Already built in Chaos Visualizer (~/Development/cymatics/modes/reaction.py) — can port.

---

### 4. domain_warp — Recursive Noise Displacement
**Category:** Emergent Systems
**Score:** 22/25 | **Time:** 78ms at 1080p | **LOC:** ~30

Generate Perlin noise field. Displace pixel coordinates. Feed displaced coords BACK through the noise function: noise(x + noise(x,y), y + noise(x,y)). Each recursion adds organic fluid distortion. Animate noise seed for flowing liquid motion.

```python
# Core algorithm
import numpy as np

def domain_warp(frame, octaves=3, recursion_depth=2, warp_strength=30.0,
                scale=50.0, time_offset=0.0):
    h, w = frame.shape[:2]
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)

    # Simplified noise (replace with proper Perlin for production)
    def noise(xx, yy, t):
        return np.sin(xx/scale + t) * np.cos(yy/scale + t*0.7)

    dx, dy = x.copy(), y.copy()
    for _ in range(recursion_depth):
        n1 = noise(dx, dy, time_offset) * warp_strength
        n2 = noise(dx + 100, dy + 100, time_offset) * warp_strength
        dx = x + n1
        dy = y + n2

    nx = np.clip(dx.astype(int), 0, w-1)
    ny = np.clip(dy.astype(int), 0, h-1)
    return frame[ny, nx]
```

**Params:** octaves (1-8), recursion_depth (1-5), warp_strength (0-100), animation_speed, scale
**Why novel:** Displacement exists in Entropic. Recursive displacement where the warp feeds back into itself creates qualitatively different organic motion impossible to get any other way.
**Cross-pollination role:** Principle 2 (multiplier) — stack with anything and it looks better.

---

### 5. entropy_map — Shannon Entropy as Visual Parameter
**Category:** Information Theory
**Score:** 22/25 | **Time:** 387ms at 1080p | **LOC:** ~25

Calculate local Shannon entropy in sliding NxN windows. High entropy regions (complex texture) vs low entropy (flat color). Self-segments video by information density. Universal mask generator for every other effect.

```python
# Core algorithm
import numpy as np
from scipy.ndimage import uniform_filter

def entropy_map(frame, window_size=16, mode='visualize', invert=False):
    gray = frame[:,:,0].astype(np.float32) / 255.0

    # Local variance as entropy proxy (much faster than true Shannon)
    local_mean = uniform_filter(gray, window_size)
    local_sq = uniform_filter(gray**2, window_size)
    entropy = np.clip(local_sq - local_mean**2, 0, None)
    entropy = entropy / entropy.max() if entropy.max() > 0 else entropy

    if invert:
        entropy = 1.0 - entropy

    if mode == 'visualize':
        # Colormap: low entropy = blue, high = red
        out = frame.copy()
        out[:,:,0] = (entropy * 255).astype(np.uint8)
        out[:,:,2] = ((1-entropy) * 255).astype(np.uint8)
        return out
    elif mode == 'mask':
        # Return as alpha mask for other effects
        mask = (entropy * 255).astype(np.uint8)
        return np.stack([mask]*3, axis=-1)
    elif mode == 'modulate':
        # Modulate original brightness by entropy
        return (frame.astype(np.float32) * entropy[:,:,np.newaxis]).clip(0,255).astype(np.uint8)
```

**Params:** window_size (4-64), mode (visualize/mask/modulate), invert, color_map
**Why novel:** The tool is called Entropic. This effect literally measures entropy. Brand thesis as code.
**Cross-pollination role:** Principle 3 (measurement to modulation) — universal mask generator for every other effect.
**Performance note:** 387ms is the slowest of the 5. Could optimize with smaller window or downscale-then-upscale approach (~100ms target).

---

## Remaining 11 Candidates (Backlog)

### Priority B (Build after top 5)

| # | Effect | Category | Time | LOC | Notes |
|---|--------|----------|------|-----|-------|
| 6 | spectral_paint | Cross-Modal | 88ms | ~30 | FFT freq bands mapped to RGB channels. Decompose effect. |
| 7 | sonification_feedback | Cross-Modal | ~80ms | ~40 | Pixel rows treated as audio waveforms, actual DSP applied. Core mad scientist thesis. |
| 16 | harmonic_percussive | Signal Decomposition | ~100ms | ~40 | HPSS from audio applied to 2D spatial frequency. Smooth vs detail separation. |
| 15 | wavelet_split | Signal Decomposition | ~120ms | ~35 | Multi-resolution processing by orientation+scale. Requires pywt. |
| 2 | cellular_automata | Emergent Systems | 59ms | ~20 | Conway/Wolfram on pixels. Video seeds the automaton. |

### Priority C (Exploratory)

| # | Effect | Category | Time | LOC | Notes |
|---|--------|----------|------|-----|-------|
| 8 | temporal_crystal | Temporal | ~50ms | ~25 | Crystallographic time symmetry. Needs frame buffer. |
| 4 | afterimage | Perceptual | 17ms | ~15 | Retinal persistence simulation. Simple but effective. |
| 5 | moire | Perceptual | ~20ms | ~20 | Interference patterns. Usually an artifact; here it's a tool. |
| 11 | strange_attractor | Chaos | ~300ms | ~50 | Lorenz/Rossler particle system. Visually stunning but slower. |
| 13 | crystal_growth | Material Sim | ~400ms | ~60 | DLA dendritic growth. Performance-constrained. |
| 3 | erosion_sim | Material Sim | ~350ms | ~50 | Hydraulic erosion on brightness heightmap. Performance-constrained. |

---

## Cross-Pollination Principles

### Principle 1: Output-as-Seed
Any effect that generates structure (CA cells, RD patterns, DLA crystals, attractor trails) can seed any effect that consumes structure (erosion needs heightmap, CA needs alive/dead, RD needs concentration). Generative effects feed simulation effects.

### Principle 2: Decompose then Process then Recombine
Any splitting effect (spectral_paint by frequency, wavelet_split by scale+orientation, harmonic_percussive by smoothness) creates independent layers. Any processing effect can be applied per-layer. Separation effects multiply the creative space of every other effect.

### Principle 3: Measurement to Modulation
Any effect that measures something (entropy_map = information density, compression_oracle = codec loss, afterimage = temporal change) can drive the parameters of any other effect. Analytical effects become control signals. The video becomes self-reactive.

### Principle 4: Time Domain and Space Domain Swap
Any audio DSP technique (reverb, delay, compression, gating, HPSS) can be applied to pixel rows as waveforms. Any spatial technique (blur, edge detect, morphology) can be applied to the temporal axis. Every spatial effect has a temporal twin. This doubles the effect library conceptually.

### Principle 5: Chaos Boundary as Creative Sweet Spot
Effects with a control parameter that crosses from order to chaos (logistic r value, RD feed/kill rates, CA rule number, domain_warp recursion depth) have a bifurcation point where output is maximally interesting. The edge of chaos is where the art lives. Auto-tuning to hover near bifurcation is a meta-feature.

---

## Interaction Matrix (How Effects Enhance Each Other)

### New to New

| A | B | What Happens |
|---|---|-------------|
| entropy_map | logistic_cascade | Entropy drives r-value: high-info regions go chaotic, low-info stays stable |
| entropy_map | reaction_diffusion | RD runs only in low-entropy (flat) regions, preserves detail in complex areas |
| entropy_map | domain_warp | Warp strength modulated by entropy: flat areas flow, textured areas stay sharp |
| compression_oracle | logistic_cascade | Codec artifacts become the initial state for chaos thresholding |
| compression_oracle | reaction_diffusion | JPEG block boundaries seed RD growth patterns — chemistry follows compression math |
| logistic_cascade | domain_warp | Chaos map output displaces coordinates — chaotic regions warp, stable don't |
| logistic_cascade | reaction_diffusion | Logistic map output becomes RD initial concentration — chaos seeds chemistry |
| reaction_diffusion | domain_warp | RD patterns displaced by recursive noise — organic patterns that flow |
| domain_warp | compression_oracle | Warped frame re-compressed reveals different codec decisions — flow changes what the codec sees |

### New to Existing (126 effects)

| New Effect | + Existing | Result |
|-----------|-----------|--------|
| reaction_diffusion | + sidechain_duck | RD intensity ducks to audio. Beat = patterns freeze. Silence = wild growth. |
| reaction_diffusion | + datamosh | RD patterns in P-frames. Chemistry meets codec corruption. |
| logistic_cascade | + posterize | Double threshold: logistic chaos + color reduction = unpredictable posterization |
| logistic_cascade | + bitcrush | Chaos-driven bit depth: some pixels crushed, others pristine, deterministic but unpredictable |
| domain_warp | + displacement | Recursive warp stacked with content-driven displacement = deep organic distortion |
| domain_warp | + pixelsort | Sort warped pixels — the sorting boundaries follow organic flow lines |
| entropy_map | + any physics effect | Physics runs at entropy-driven intensity: complex regions get more gravity/melt/vortex |
| compression_oracle | + scanlines | Codec block grid + CRT lines = double interference pattern |
| compression_oracle | + jpeg_artifacts | Amplified real artifacts + intentional ones = codec feedback loop |
| entropy_map (mask) | + any existing effect | Apply ANY of the 126 effects selectively by information density |

---

## Proposed New Categories

### Emergent Systems
Effects where simple rules produce complex behavior. The video seeds the simulation; the simulation transforms the video. Output is never predictable from input.
- reaction_diffusion (Turing patterns from pixel brightness)
- domain_warp (recursive noise displacement)
- cellular_automata (Conway/Wolfram on pixels) [backlog]
- crystal_growth (DLA dendritic patterns) [backlog]
- erosion_sim (hydraulic erosion on brightness heightmap) [backlog]

### Information Theory
Effects that measure, reveal, or exploit the information content of video. Named for the tool itself. These effects make visible what is normally hidden.
- entropy_map (Shannon entropy visualization and mask generation)
- compression_oracle (codec decision amplification)
- logistic_cascade (deterministic chaos thresholding)

### Future Categories (when backlog effects are built)
- **Perceptual:** afterimage, moire (retinal/optical phenomena)
- **Cross-Modal:** spectral_paint, sonification_feedback (audio DSP on video data)
- **Signal Decomposition:** wavelet_split, harmonic_percussive (multi-resolution processing)
- **Chaos & Attractors:** strange_attractor (particle systems on chaotic ODEs)

---

## Meta-Feature: Effect Routing as Modular Synth

The real unlock from this research is not any single effect — it's making chaining a first-class feature. Current Entropic has apply_chain (sequential). The cross-pollination principles suggest:

1. **Feedback routing** — output of B feeds back into A (like mixer feedback loop)
2. **Parameter cross-modulation** — A's output brightness drives B's intensity (like CV in modular synths)
3. **Parallel splits** — frame goes to A and B simultaneously, results blend (like parallel compression)

This turns Entropic from a linear effects chain into a modular video synthesizer. 126 effects become 126 modules. Creative space goes from N to N-squared.

---

## Performance Budget

| Effect | 1080p Timing | Status |
|--------|-------------|--------|
| compression_oracle | 68ms | WELL WITHIN |
| logistic_cascade | 13ms | BLAZING |
| reaction_diffusion | 122ms (10 iter) | GOOD |
| domain_warp | 78ms | GOOD |
| entropy_map | 387ms | BORDERLINE — optimize to ~100ms via downscale |
| **Chain of all 5** | **~668ms** | Just over 500ms budget; run 4 of 5 in chain, or reduce iterations |

Optimization path for entropy_map: compute at half resolution, upscale mask with bilinear interpolation. Cuts to ~100ms. Total chain: ~381ms.

---

## Research Sources

### Reference Docs Consulted
- ~/Development/tools/docs/scipy-signal-reference.md — Hilbert transform, filter design, FFT, convolution
- ~/Development/tools/docs/opencv-creative-reference.md — Optical flow, warpAffine, remap
- ~/Development/tools/docs/audio-dsp-creative-projects.md — HPSS, granular, Schroeder reverb, Karplus-Strong, phase vocoder
- ~/Development/tools/docs/glitch-video-creative-projects.md — Flow fields, L-systems, domain warping, DLA
- ~/Development/tools/docs/ffmpeg-filters-reference.md — Displacement, cellauto, mandelbrot, blend modes
- ~/Development/tools/docs/realtime-visual-tools.md — TouchDesigner, Hydra, cables.gl patterns

### Knowledge Base Articles
- Valhalla DSP (reverb/delay DSP concepts applied cross-modally)
- Airwindows (open source plugin algorithms as video effect inspiration)

### Existing Codebase References
- ~/Development/cymatics/modes/reaction.py — Reaction-diffusion already built for Chaos Visualizer (portability)
- ~/Development/entropic/effects/ — 19 effect modules, apply_effect API, EFFECTS registry

---

## Build Plan

**When Entropic comes off the table:**

1. **Sprint 1 (1.5 hours):** compression_oracle + logistic_cascade
   - Both are <25 LOC, fastest to build
   - Test with existing recipe chain system
   - Add to Information Theory category

2. **Sprint 2 (1.5 hours):** reaction_diffusion + domain_warp
   - Port RD from Cymatics codebase
   - Implement proper Perlin noise for domain_warp (or use opensimplex)
   - Add to Emergent Systems category

3. **Sprint 3 (1 hour):** entropy_map + optimization pass
   - Build with downscale optimization
   - Wire mask output mode into chain system as parameter modulator
   - Integration test: entropy_map mask driving logistic_cascade r-value

4. **Sprint 4 (optional):** Cross-pollination wiring
   - Parameter cross-modulation API (effect A output drives effect B params)
   - Feedback routing in apply_chain
   - Document new chain recipes

**Total: ~5 hours across 3-4 sprints. 5 new effects + 2 new categories + modular routing foundation.**

---

---

## CODEC ARCHAEOLOGY: 20 Effects from Compression Math

### Origin Story

User observation: A friend's image had been re-compressed multiple times. When zoomed in, each 8x8 pixel block region had **different shapes and patterns** — like "quantized moire." Different blocks showed different geometric structures, interference patterns at boundaries, and emergent textures that were neither the original image nor random noise.

**What was actually happening:** Three phenomena layered on top of each other:

1. **DCT Basis Pattern Visibility** — JPEG decomposes each 8x8 block into 64 basis functions (horizontal stripes, vertical stripes, checkerboards, diagonals). Heavy compression kills the high-frequency ones, leaving visible geometric patterns. Each block has a *different* surviving pattern set because each block had different content.

2. **Multi-Grid Interference** — If the image was cropped/resized between compressions, the 8x8 grid shifted. Two (or more) grids at different offsets create moiré-like interference. Forensics researchers call this "nonaligned double JPEG compression" — they detect it to find forgeries. We want to CREATE it.

3. **Generation Loss Accumulation** — Each re-compression treats previous artifacts as real data. The codec's quantization decisions compound. After N generations, the image converges toward stable states — but the PATH of convergence creates complex transitional patterns.

**Key insight:** The difference between "degraded" and "dramatic" is CONTROL. Each of these 3 phenomena has multiple independent parameters. Isolate them, make them controllable, dial specific aspects up while suppressing others, and you get art instead of garbage.

**Artistic precedent:** Thomas Ruff's "Jpegs" series (2004-2007) — exhibited massive JPEG artifacts as fine art. Rosa Menkman's glitch art theory treats compression artifacts as a medium. But neither had PROGRAMMATIC CONTROL over individual components. That's what we're building.

---

### The Atomic Components

Before the 20 effects, here are the 6 independent axes of control:

| Axis | What It Controls | Range |
|------|-----------------|-------|
| **A. Frequency Selection** | Which DCT basis functions survive | N² individual coefficients (where N=block_size), or bands (low/mid/high) |
| **B. Quantization Intensity** | How coarsely coefficients are rounded | Quality 1 (brutal) to 100 (transparent) |
| **C. Grid Alignment** | Where the block grid starts | (0,0) to (N-1,N-1) possible offsets |
| **D. Chroma Treatment** | How color information is subsampled | 4:4:4 / 4:2:2 / 4:2:0 / kill chroma entirely |
| **E. Generation Count** | How many re-compression rounds | 1 to N (each with independent params) |
| **F. Cross-Codec** | Which codec does the compression | JPEG / WebP / HEIF / each has different math |
| **G. Block Size** | How large each processing cell is | 2×2 (micro) to 128×128 (architectural). Default: 8×8 (JPEG standard) |

**Axis G (Block Size)** is the newly discovered 7th axis. JPEG hardcodes 8×8 blocks, but our custom DCT implementation via `scipy.fft.dctn` works at ANY block size. This is a **scale multiplier** that transforms every other axis:

| Block Size | # Basis Functions | Character | What Changes |
|-----------|------------------|-----------|-------------|
| 2×2 | 4 | Extreme micro-pixelation. Only 4 frequencies per block. Every 2px is a unit. | Looks like a color palette reduction — but frequency-weighted, not arbitrary |
| 4×4 | 16 | Chunky. Some mid-frequency survives. Visible block structure at close zoom. | Half-scale JPEG. Artifacts are smaller and denser. |
| **8×8** | **64** | **Standard JPEG.** The default codec block size. Most familiar artifact character. | Baseline — this is what Thomas Ruff exhibited. |
| 16×16 | 256 | 256 basis functions. Larger smooth regions. Richer frequency vocabulary per block. | Basis patterns become visible textures spanning 16px. Grid lines are farther apart. |
| 32×32 | 1024 | Huge blocks. Bold geometric structures. Each block captures a significant image region. | DCT patterns become architectural. Block boundaries cross face-sized features. |
| 64×64 | 4096 | Massive. Each block spans a face/object. Basis functions are large-scale projections. | At this scale, frequency isolation creates room-sized geometric patterns. |
| 128×128 | 16384 | Near-whole-image blocks. Basis patterns are full-screen geometric projections. | Processing becomes the image. Extreme: one block = one screen. |

**Implementation:** Replace hardcoded `8` with `block_size` parameter in the DCT processing loop:
```python
# Universal block processing — works for ALL CA effects
def dct_block_process(frame, func, block_size=8):
    h, w = frame.shape[:2]
    output = frame.copy()
    for y in range(0, h, block_size):
        for x in range(0, w, block_size):
            block = frame[y:y+block_size, x:x+block_size]
            if block.shape[0] == block_size and block.shape[1] == block_size:
                coeffs = dctn(block.astype(float), norm='ortho')
                modified = func(coeffs, block_size)  # effect-specific logic
                output[y:y+block_size, x:x+block_size] = np.clip(
                    idctn(modified, norm='ortho'), 0, 255
                ).astype(np.uint8)
    return output
```

**Performance impact:** Block size affects speed. Smaller blocks = more iterations but faster DCT per block. Larger blocks = fewer iterations but O(N²logN) DCT per block.
- 2×2: Very fast (~20ms at 1080p, trivial DCT)
- 8×8: Standard (~50ms, JPEG baseline)
- 32×32: Moderate (~80ms, fewer blocks but larger DCTs)
- 64×64: Slower (~150ms, complex DCT per block)
- 128×128: ~250ms (still within budget)

**Cross-axis interactions with block_size:**
- `dct_isolate` at 64×64: Isolated frequency bands become HUGE visible geometric patterns
- `grid_moire` with mismatched block sizes (8×8 pass1 + 32×32 pass2): Multi-SCALE interference, not just multi-offset
- `generation_loss` with varying block_size per generation: The attractor state changes character completely at each scale
- `block_crystallize` at 2×2: Micro-mosaic. At 128×128: Giant stained glass cathedral windows
- `quant_amplify` at 32×32: Posterization follows 32px regions instead of 8px — completely different spatial rhythm
- `dct_phase_destroy` at 64×64: Frosted glass effect where each 64px region independently scrambles — dreamy large-scale displacement

Any effect below manipulates 1-3 of these axes. Combinations of effects stack all 7.

---

### Category: Codec Archaeology (NEW — 20 effects)

#### Subcategory: Frequency Domain (Axis A)

**CA-01. `dct_isolate` — Basis Function Spotlight**
Kill all DCT coefficients EXCEPT a chosen frequency band in each 8x8 block. Low band only = blurry blocks. High band only = edge-only geometric patterns. Mid band = the most alien textures — striped, checkered, diagonal structures that look like textile weaves.
- **Params:** freq_band (low/mid/high/custom), coefficients (list of 0-63), blend_with_original (0-1)
- **Dramatic angle:** Mid-frequency isolation turns any photo into what looks like a woven fabric. Faces become tapestries.
- **LOC:** ~35 | **Deps:** scipy.fft (dct/idct) | **Est. time:** 50ms

**CA-02. `dct_swap` — Basis Function Transplant**
Take the DCT coefficients from block (x1,y1) and transplant them into block (x2,y2). Or: shuffle all block coefficients randomly. Or: sort blocks by their dominant frequency. The image's spatial frequency content gets rearranged — faces get the frequency signature of backgrounds, skies get the texture of hair.
- **Params:** mode (swap_pairs/shuffle/sort_by_frequency/rotate), seed
- **Dramatic angle:** Sorting by dominant frequency creates a gradient from smooth to detailed across the image, like an X-ray of information density.
- **LOC:** ~40 | **Deps:** scipy.fft | **Est. time:** 60ms

**CA-03. `dct_sculpt` — Frequency Carving**
Multiply each of the 64 DCT coefficients by a user-defined gain vector. Like a 64-band graphic EQ but for spatial frequency. Boost coefficient (3,0) = amplify a specific horizontal stripe pattern. Kill (0,3) = remove a specific vertical pattern. Animate the gain vector over time = the visible basis patterns morph and breathe.
- **Params:** gains (64-element array or preset name), animate_speed, preset (flat/diagonal_only/edges_only/checker_only)
- **Dramatic angle:** Animating gains creates patterns that appear to grow from inside the image — geometric forms emerging and receding like breathing.
- **LOC:** ~45 | **Deps:** scipy.fft | **Est. time:** 55ms

**CA-04. `dct_phase_destroy` — Phase Scramble**
Keep DCT magnitudes but randomize phases within each block. Magnitude = what frequencies exist. Phase = where they are spatially. Destroying phase while keeping magnitude creates images that have the "same texture" but completely wrong spatial arrangement. Like seeing through frosted glass that preserves color but destroys position.
- **Params:** phase_randomness (0-1), seed, preserve_dc (bool — keep overall brightness)
- **Dramatic angle:** At 50% randomness, images look like they're dissolving into their own frequency content — recognizable but displaced.
- **LOC:** ~30 | **Deps:** scipy.fft | **Est. time:** 45ms

#### Subcategory: Quantization Domain (Axis B)

**CA-05. `quant_amplify` — Quantization Exaggeration**
Apply JPEG quantization but with an amplified quantization table. Standard JPEG quantization tables have values from 1-255. Multiply them by N. At 2x, subtle banding appears. At 10x, each block becomes a handful of flat-color rectangles. At 100x, each block collapses to a single color. It's posterization, but following the codec's math instead of arbitrary thresholds.
- **Params:** amplification (1-100), table_preset (luminance/chrominance/custom), per_block_variation (0-1)
- **Dramatic angle:** Unlike posterize, this follows the DCT's frequency-weighted importance. High frequencies die first = organic, not arbitrary.
- **LOC:** ~30 | **Deps:** scipy.fft | **Est. time:** 40ms

**CA-06. `quant_morph` — Quality Gradient**
Apply different JPEG quality levels across the image spatially. Left edge = quality 1, right edge = quality 100. Or: center = pristine, edges = destroyed. Or: radial, following brightness, following entropy_map output. The image exists in multiple quality states simultaneously.
- **Params:** gradient_type (linear_h/linear_v/radial/brightness/entropy), q_low (1-100), q_high (1-100)
- **Dramatic angle:** A face that's pristine at the eyes but disintegrates toward the edges, following the natural information gradient.
- **LOC:** ~45 | **Deps:** PIL JPEG codec | **Est. time:** 80ms

**CA-07. `quant_table_lerp` — Quantization Table Animation**
Smoothly interpolate between two different quantization tables over time. Table A might preserve horizontal frequencies; Table B preserves vertical. The animation morphs between two different "codec personalities" — the visible patterns shift from horizontal to vertical structures.
- **Params:** table_a (preset or custom), table_b (preset or custom), t (0-1 interpolation)
- **Dramatic angle:** Animated, the image appears to change its physical material — from horizontal wood grain to vertical fabric weave.
- **LOC:** ~35 | **Deps:** scipy.fft | **Est. time:** 50ms

#### Subcategory: Grid Domain (Axis C)

**CA-08. `grid_shift` — Misaligned Re-Compression**
Compress the frame with the 8x8 grid starting at offset (0,0), then decompress. Shift the grid to offset (dx,dy), compress again. The two grids interfere. This is exactly what forensics researchers detect as evidence of tampering — but we're doing it on purpose. Different offsets create different interference patterns.
- **Params:** dx (0-7), dy (0-7), quality_pass1 (1-100), quality_pass2 (1-100)
- **Dramatic angle:** Offset (4,4) = maximum interference (half-grid shift). Creates the richest moiré patterns, especially in textured regions.
- **LOC:** ~40 | **Deps:** PIL JPEG | **Est. time:** 80ms

**CA-09. `grid_moire` — Multi-Grid Interference Stack**
Stack 3-8 compression passes, each at a different grid offset. Each pass adds a new interference layer. The result is complex moiré patterns that are mathematically deterministic but visually chaotic — like overlapping screen printing screens.
- **Params:** num_passes (2-8), offsets (list of (dx,dy) or "fibonacci"/"random"/"spiral"), quality_per_pass
- **Dramatic angle:** "Fibonacci" offset pattern creates golden-ratio-spaced interference. "Spiral" creates concentric moire rings.
- **LOC:** ~50 | **Deps:** PIL JPEG | **Est. time:** 120ms (scales with passes)

**CA-10. `grid_phase_animate` — Grid Walk**
Animate the grid offset smoothly over time: (0,0) → (1,0) → (2,0) → ... → (7,7) → (0,0). Each frame has a different grid alignment. The interference pattern shifts across the image like a scanning pattern. Combined with low quality, the block structure appears to crawl across the image.
- **Params:** speed (offsets per frame), path (linear/spiral/random/bounce), quality
- **Dramatic angle:** The blocks appear to float independently of the image content — the grid is a physical object sliding across the surface.
- **LOC:** ~35 | **Deps:** PIL JPEG | **Est. time:** 70ms

**CA-11. `grid_scale_mix` — Block Size Interference**
Compress at 8x8 blocks (JPEG standard), then again at simulated 16x16 blocks (JPEG 2000 style via downscale-compress-upscale), then again at 4x4. Three different block size grids interfere. Each size captures different spatial frequencies. The result: multi-scale geometric patterns.
- **Params:** block_sizes (list like [4,8,16]), quality_per_size, blend_mode (add/multiply/screen)
- **Dramatic angle:** Like looking at an image through three different resolution screens simultaneously.
- **LOC:** ~45 | **Deps:** PIL JPEG | **Est. time:** 100ms

#### Subcategory: Color Domain (Axis D)

**CA-12. `chroma_separate` — Luma/Chroma Split Processing**
Convert to YCbCr. Compress luma (Y) at one quality, chroma (CbCr) at a completely different quality. At extreme settings: sharp grayscale structure with wildly smeared color. Or: perfect color with destroyed luminance. The two layers of human vision (brightness vs color) are independently degraded.
- **Params:** luma_quality (1-100), chroma_quality (1-100), chroma_subsample (444/422/420/411)
- **Dramatic angle:** High luma + low chroma = images that look like hand-tinted black-and-white photos from the 1800s, with color bleeding beyond edges.
- **LOC:** ~40 | **Deps:** PIL, numpy (YCbCr conversion) | **Est. time:** 60ms

**CA-13. `chroma_bleed` — Color Bleeding Amplification**
Apply 4:2:0 chroma subsampling, then AMPLIFY the difference between the subsampled and original chroma. The color bleeding that JPEG normally hides becomes a neon halo around every edge. Saturated objects radiate color into their surroundings.
- **Params:** bleed_amplification (1-20), subsample_ratio (420/411/custom), edge_threshold
- **Dramatic angle:** Red objects glow red into neighboring regions. Blue sky bleeds into tree branches. Everything radiates its own color aura.
- **LOC:** ~35 | **Deps:** numpy, cv2 (resize for subsampling) | **Est. time:** 45ms

**CA-14. `chroma_destroy` — Selective Channel Annihilation**
Kill specific chroma components entirely while preserving others. Remove all blue-difference (Cb) = warm-only image. Remove all red-difference (Cr) = cool-only image. Remove both = pure luminance with no color. Animate the removal = color drains from the image channel by channel.
- **Params:** kill_cb (0-1), kill_cr (0-1), preserve_luma (bool)
- **Dramatic angle:** Animated Cb drainage makes images look like they're being bleached by sunlight — color fading in real time.
- **LOC:** ~25 | **Deps:** numpy (YCbCr) | **Est. time:** 30ms

#### Subcategory: Generation Domain (Axis E)

**CA-15. `generation_loss` — Controlled Re-Compression Cascade**
Re-compress the frame N times at a controlled quality. Unlike random degradation, each generation is tracked. Output can be any specific generation (show generation 5 of 20), or crossfade between generations over time. At low generation counts: subtle softening. At high counts: convergence to stable attractor states.
- **Params:** generations (1-100), quality (1-100), output_generation (int or "animate"), show_diff (bool — show difference from previous gen)
- **Dramatic angle:** Animate from generation 1 to 50: watch the image find its "compression attractor" — the stable state it converges to. The journey there is the art.
- **LOC:** ~30 | **Deps:** PIL JPEG | **Est. time:** 20ms * generations

**CA-16. `quality_oscillate` — Quality Breathing**
Alternate between high and low quality on each re-compression pass. Pass 1: quality 95 (barely touches it). Pass 2: quality 5 (destroys it). Pass 3: quality 95 (tries to faithfully preserve the destruction). Pass 4: quality 5 (destroys the preservation). Creates layered artifacts where each generation's damage is partially healed then re-damaged.
- **Params:** q_high (50-100), q_low (1-30), passes (2-20), pattern (alternate/ramp_down/ramp_up/random)
- **Dramatic angle:** The heal-damage-heal cycle creates textures that look geological — like sedimentary rock layers. Each quality oscillation is a stratum.
- **LOC:** ~25 | **Deps:** PIL JPEG | **Est. time:** 25ms * passes

**CA-17. `cross_codec` — Codec Translation Loss**
Compress through a chain of DIFFERENT codecs: JPEG → WebP → JPEG → PNG (lossless, captures artifacts) → JPEG. Each codec has different math (DCT vs wavelet vs etc). The artifacts from one codec become content for the next. JPEG makes blocks; WebP makes smears; back to JPEG makes blocks OF smears.
- **Params:** codec_chain (list like ["jpeg:20", "webp:10", "jpeg:30"]), capture_intermediates (bool)
- **Dramatic angle:** Each codec has a "personality." JPEG = grid structure. WebP = organic blurring. HEIF = banding. Chaining them = a conversation between algorithms about what matters in the image.
- **LOC:** ~35 | **Deps:** PIL (JPEG, WebP, PNG support built in) | **Est. time:** 30ms * chain length

**CA-18. `selective_generation` — Regional Re-Compression**
Only re-compress specific regions of the frame. Mask defines which areas get N generations of re-compression while the rest stay pristine. The mask can come from: entropy_map, brightness threshold, face detection, or manual coordinates. Creates images where some regions are archaeologically degraded while others are mint.
- **Params:** mask_source (entropy/brightness/center/manual), generations (1-100), quality, feather_radius
- **Dramatic angle:** Compress faces 50 times while keeping backgrounds pristine. Or compress backgrounds while faces stay sharp. Time applied unevenly = visual time travel within one frame.
- **LOC:** ~40 | **Deps:** PIL JPEG, numpy | **Est. time:** varies (generation-dependent)

#### Subcategory: Artifact Amplification (Meta — works on output of other CA effects)

**CA-19. `mosquito_amplify` — Ringing Exaggeration**
Isolate the Gibbs phenomenon (ringing/halos around sharp edges caused by truncated frequency series). Compute: edge-detect the original, compress, diff the compressed against original, mask the diff to edge regions only, amplify. The halos that JPEG creates around every edge become visible neon outlines.
- **Params:** amplification (1-20), edge_threshold, halo_width, color_mode (original/neon/rainbow)
- **Dramatic angle:** In "neon" mode, every edge in the image glows with the complementary color of the ringing artifact. Faces get electric outlines.
- **LOC:** ~35 | **Deps:** cv2 (edge detection), PIL JPEG | **Est. time:** 70ms

**CA-20. `block_crystallize` — Macro-Block Freeze**
Take each 8x8 block and replace ALL pixels with the block's average color. Like extreme mosaic, but following the codec's actual grid — not arbitrary pixel squares. Then apply quantization to the averaged colors (reducing to N colors per block). The image becomes a crystalline grid of colored tiles, sized exactly to the compression grid.
- **Params:** color_depth (1-256 colors), grid_visible (bool — draw grid lines), color_quantize_method (mean/median/mode/dominant)
- **Dramatic angle:** With grid lines visible, images look like stained glass windows. With grid lines hidden, they look like woven pixel quilts. "Mode" color method creates pop-art flat color fields.
- **LOC:** ~25 | **Deps:** numpy | **Est. time:** 30ms

---

### Dramatic Combinations (not just degradation)

The key insight: degradation = applying one axis uniformly. Drama = applying multiple axes NON-uniformly, creating contrast between regions.

| Combination | What Happens | Why It's Dramatic |
|------------|-------------|-------------------|
| `dct_isolate(mid)` + `chroma_bleed(10x)` | Mid-frequency geometric patterns with neon color halos | Textile-like weave patterns that glow — looks like illuminated fabric |
| `grid_moire(5 passes)` + `mosquito_amplify(neon)` | Multi-grid interference with electric edge outlines | Complex geometric interference with every edge outlined in complementary neon |
| `generation_loss(30)` + `dct_sculpt(animate)` | Image finds its compression attractor while frequency visibility morphs | Watching an image die and be reborn through different frequency lenses |
| `quality_oscillate(10)` + `grid_phase_animate` | Sedimentary artifact layers with sliding block grid | Geological strata that physically move — like tectonic plates of compression |
| `cross_codec(jpeg→webp→jpeg)` + `quant_morph(radial)` | Codec conversation with spatial quality gradient | Center is pristine, edges are codec-translated — like a portal between compression realities |
| `selective_generation(entropy mask)` + `chroma_separate(luma:90, chroma:5)` | High-info regions stay sharp; flat regions get destroyed color | Smart degradation: the codec attacks boring regions, leaves interesting ones alone |
| `dct_phase_destroy(0.5)` + `block_crystallize(grid_visible)` | Half-phase-scrambled content in stained glass grid | Recognition and dissolution simultaneously — like seeing yourself in broken glass |
| `grid_scale_mix(4,8,16)` + `dct_isolate(high)` | Multi-scale block interference showing only edge patterns | Three resolutions of geometric edge patterns beating against each other |
| `chroma_destroy(animate Cb drain)` + `generation_loss(50)` | Color drains as image finds compression attractor | Double death: color fades AND detail dissolves — like a photograph decomposing |
| `quant_table_lerp(horizontal→vertical)` + `mosquito_amplify` | Morphing basis pattern visibility with amplified edge ringing | The visible texture shifts from wood grain to vertical weave while edges scream |

### The Meta-Effect: `codec_archaeology`

A single super-effect that exposes all 6 axes as parameters:

```
codec_archaeology(
    freq_band="mid",           # A: which frequencies survive
    quality=15,                # B: how brutal the quantization
    grid_offset=(4,4),         # C: grid alignment
    chroma_subsample="420",    # D: color treatment
    generations=10,            # E: re-compression rounds
    codec="jpeg",              # F: which codec
    amplify_artifacts=3.0,     # meta: make artifacts visible
    animate_axis="generations" # which param changes over time
)
```

One effect, six knobs, infinite space. This is the "parametric EQ" of compression art — total control over every axis of the codec's decision-making.

---

### Implementation Notes

**All 20 effects share a common core:** JPEG encode/decode in PIL BytesIO. The differentiation is in:
- Pre-processing (YCbCr conversion, DCT manipulation)
- Encode parameters (quality, subsampling)
- Post-processing (diff amplification, grid manipulation)
- Iteration patterns (generation loops, codec chains)

**Shared utility functions to build first:**
1. `jpeg_roundtrip(frame, quality, subsample)` — encode and decode in memory
2. `dct_block_process(frame, func)` — apply function to each 8x8 block's DCT coefficients
3. `grid_offset_compress(frame, dx, dy, quality)` — compress with shifted grid
4. `ycbcr_split(frame)` / `ycbcr_merge(y, cb, cr)` — color space conversion

**Performance:** All 20 effects are PIL/numpy/scipy only. No new dependencies. Fastest (chroma_destroy): 30ms. Slowest (grid_moire at 8 passes): ~120ms. All within the 500ms budget.

---

### Art References

- **Thomas Ruff, "Jpegs" (2004-2007):** Large-format prints of heavily compressed JPEG images. Exhibited artifacts as fine art. No programmatic control — just found images.
- **Rosa Menkman, "A Vernacular of File Formats" (2010):** Systematic documentation of how different codecs create different artifacts. Theory, not tools.
- **Takeshi Murata, "Monster Movie" (2005):** Datamoshing as art film. Codec manipulation for narrative effect. Video, not still image.
- **Image forensics research (Chen & Hsu 2011, Amerini et al 2017):** Detection of double JPEG compression via grid inconsistency analysis. They map the phenomenon precisely — we reverse-engineer their detection into creation.

**What we're building that they didn't have:** Parametric, real-time, controllable, chainable, animatable codec manipulation. The difference between finding an artifact and *composing* with it.

---

---

## Section 8: Camera Optics Emulation (New Category: "Optics")

Real lenses have interacting optical properties — each one is an isolated, crankable parameter. No existing glitch tool gives you per-property lens control.

### LO-01: Fisheye

**What:** Extreme barrel distortion with chromatic aberration increasing toward edges.

```
k1, k2 = params  # radial distortion coefficients
for each pixel (x, y):
    r = distance_from_center(x, y) / max_radius
    distortion = 1 + k1*r² + k2*r⁴
    src_x, src_y = center + (x-cx, y-cy) * distortion
    # Per-channel offset for chromatic aberration
    R = sample(frame_r, src_x * 1.02, src_y * 1.02)
    G = sample(frame_g, src_x, src_y)
    B = sample(frame_b, src_x * 0.98, src_y * 0.98)
```

**Params:** `k1` (barrel: -1.0 to 0), `k2` (higher-order: -0.5 to 0), `chromatic_aberration` (0.0–0.05)
**Perf:** ~40ms (cv2.remap with precomputed map)

### LO-02: Anamorphic

**What:** Horizontal squeeze (2:1 or custom ratio) + oval bokeh + horizontal lens flare on bright sources.

```
squeezed = cv2.resize(frame, (w//ratio, h))
padded = pad_to_original(squeezed)
# Horizontal bloom on highlights
bright_mask = luminance(frame) > threshold
flare = gaussian_blur(bright_mask, (1, ksize_h))  # only horizontal
output = addWeighted(padded, 1.0, flare, intensity, 0)
```

**Params:** `squeeze_ratio` (1.0–3.0), `flare_threshold` (0.5–1.0), `flare_intensity` (0.0–1.0), `flare_width` (10–200px)
**Perf:** ~35ms

### LO-03: Tilt-Shift

**What:** Tilted focus plane creates miniature-world effect. Sharp band in the middle, progressive blur above/below. Saturation boost.

```
blur_map = gradient_mask(h, w, band_center, band_width, angle)
blurred = gaussian_blur(frame, ksize=blur_amount)
output = frame * blur_map + blurred * (1 - blur_map)
output = boost_saturation(output, 1.3)
```

**Params:** `band_center` (0.0–1.0), `band_width` (0.05–0.5), `blur_amount` (5–51), `angle` (-45 to 45°), `saturation_boost` (1.0–2.0)
**Perf:** ~30ms

### LO-04: Chromatic Aberration (Isolated)

**What:** Color fringing that increases radially from center. Each channel gets a different radial scale.

```
for channel, scale in [(R, 1+amount), (G, 1.0), (B, 1-amount)]:
    channel_out = cv2.remap(channel, radial_map(scale))
```

**Params:** `amount` (0.0–0.1), `center_x/y` (0.0–1.0), `axial` (bool — longitudinal vs lateral)
**Perf:** ~25ms (3 remaps)

### LO-05: Bokeh Shaper

**What:** Custom out-of-focus rendering. Point sources become shaped highlights (circle, hexagon, cat-eye, donut, heart).

```
depth_mask = estimate_depth(frame)  # luminance proxy or edge-based
in_focus = frame * focus_mask
out_focus = convolve2d(frame, bokeh_kernel(shape))
output = in_focus * depth_mask + out_focus * (1 - depth_mask)
```

**Shapes:** circle (standard), hexagon (vintage), cat-eye (anamorphic edge), donut (mirror lens), heart/star (novelty)
**Params:** `shape` (enum), `size` (5–50px), `focus_depth` (0.0–1.0), `edge_softness` (0.0–1.0)
**Perf:** ~80ms (convolution with custom kernel)

### LO-06: Pinhole Camera

**What:** Everything slightly soft (no depth of field separation), extreme vignette, high contrast.

```
softened = gaussian_blur(frame, ksize=3)
vignetted = apply_radial_falloff(softened, falloff_strength=0.8)
output = adjust_contrast(vignetted, 1.4)
```

**Params:** `softness` (1–11 kernel), `vignette_strength` (0.0–1.0), `contrast` (0.8–2.0)
**Perf:** ~15ms

### LO-07: Holga / Lomography

**What:** Plastic lens look — light leaks, extreme vignette, random color cast, barrel distortion.

```
distorted = barrel_distort(frame, k1=-0.3)
vignetted = heavy_vignette(distorted)
color_cast = random_gradient_overlay(vignetted, hue=random)
light_leak = additive_gradient(color_cast, position=random, color=warm)
```

**Params:** `distortion` (-0.5 to 0), `vignette` (0.0–1.0), `color_cast_hue` (0–360), `light_leak_intensity` (0.0–1.0), `light_leak_position` (enum: corner, edge, random)
**Perf:** ~45ms

### LO-08: Coma (Comet Tail)

**What:** Off-axis point sources get comet-shaped tails. Directional blur that increases with distance from center.

```
angle_map = atan2(y - cy, x - cx)  # direction from center
distance_map = sqrt((x-cx)² + (y-cy)²) / max_r
for each pixel:
    blur_length = distance_map * strength
    blur_angle = angle_map  # radial direction
    output = directional_blur(frame, blur_angle, blur_length)
```

**Params:** `strength` (0.0–1.0), `center_x/y` (0.0–1.0)
**Perf:** ~60ms (per-pixel directional blur approximated via multiple shifted blends)

---

## Section 9: Surveillance Aesthetic (New Category: "Surveillance")

The surveillance look is an aesthetic of **limitations** — each limitation is a controllable parameter.

### SV-01: CCTV Classic

**What:** Complete closed-circuit TV look. Low res, wide angle, timestamp, interlace artifacts, 4:3 crop.

```
# Downscale and upscale (pixelation)
small = cv2.resize(frame, (w//scale, h//scale), INTER_NEAREST)
pixelated = cv2.resize(small, (w, h), INTER_NEAREST)
# Barrel distortion (wide angle)
distorted = barrel_distort(pixelated, k1=-0.2)
# Interlace (keep only even or odd rows per field)
if frame_index % 2 == 0:
    distorted[1::2] = distorted[::2]  # duplicate even rows
else:
    distorted[::2] = distorted[1::2]  # duplicate odd rows
# 4:3 crop
cropped = crop_to_aspect(distorted, 4, 3)
# Timestamp overlay
output = overlay_text(cropped, timestamp_str, position='bottom-right', font='monospace')
```

**Params:** `resolution_scale` (2–8x downscale), `distortion` (-0.4 to 0), `interlace` (bool), `timestamp` (bool), `aspect` (4:3, 16:9), `noise_amount` (0.0–0.3)
**Perf:** ~35ms

### SV-02: Night Vision (Gen 3)

**What:** Green phosphor screen, bloom on bright sources, intensifier tube noise pattern, circular vignette.

```
# Convert to single channel (luminance)
lum = cv2.cvtColor(frame, COLOR_BGR2GRAY)
# Apply gain (intensifier)
gained = np.clip(lum * gain, 0, 255)
# Bloom on highlights
bright = (gained > 200).astype(float)
bloom = gaussian_blur(bright, ksize=21) * bloom_strength
# Phosphor noise (additive, salt-and-pepper style)
noise = np.random.poisson(noise_level, gained.shape)
# Map to green channel
output = np.zeros_like(frame)
output[:,:,1] = np.clip(gained + bloom + noise, 0, 255)  # green only
output[:,:,0] = output[:,:,1] * 0.1  # hint of blue
# Circular vignette (tube shape)
output = circular_vignette(output, radius=0.85)
```

**Params:** `gain` (1.0–5.0), `bloom_strength` (0.0–1.0), `noise_level` (5–30), `phosphor_color` (green, white-hot), `vignette_radius` (0.5–1.0)
**Perf:** ~25ms

### SV-03: Infrared / Thermal

**What:** False-color heat map. Luminance mapped to thermal palette. Heat bloom on bright areas.

```
gray = luminance(frame)
# Apply thermal colormap
colored = cv2.applyColorMap(gray, palette)
# Heat bloom (Gaussian blur on hot spots)
hot = (gray > hot_threshold).astype(float)
bloom = gaussian_blur(hot, ksize=15)
output = addWeighted(colored, 1.0, colorize(bloom, hot_color), 0.5, 0)
# Crosshair overlay
if crosshair:
    draw_crosshair(output, center)
```

**Palettes:** `white_hot` (white=hot, black=cold), `black_hot` (inverted), `iron` (black→purple→red→yellow→white), `rainbow` (full spectrum), `arctic` (blue→white)
**Params:** `palette` (enum), `hot_threshold` (0.5–1.0), `bloom_amount` (0.0–1.0), `crosshair` (bool)
**Perf:** ~20ms (LUT operation)

### SV-04: Body Cam

**What:** Fisheye wide angle, periodic digital glitches, rolling timestamp, motion blur.

```
distorted = barrel_distort(frame, k1=-0.35)
# Periodic glitch (every N frames, corrupt a region)
if frame_index % glitch_interval == 0:
    region = random_rect(distorted)
    distorted[region] = corrupt(distorted[region])
# Motion blur (directional)
if motion_blur:
    kernel = motion_blur_kernel(angle=random, length=8)
    distorted = cv2.filter2D(distorted, -1, kernel)
# Timestamp + badge overlay
output = overlay_text(distorted, f"CAM-{cam_id} {timestamp}", position='top-left')
```

**Params:** `distortion` (-0.5 to 0), `glitch_interval` (30–300 frames), `glitch_severity` (0.0–1.0), `motion_blur` (bool), `cam_id` (string)
**Perf:** ~40ms

### SV-05: Dash Cam

**What:** Wide angle, heavy compression artifacts, frame drops, timestamp, speed overlay.

```
distorted = barrel_distort(frame, k1=-0.25)
# Simulate low bitrate compression
compressed = jpeg_roundtrip(distorted, quality=15)
# Frame drops (hold previous frame)
if random.random() < drop_rate:
    output = previous_frame
else:
    output = compressed
# Overlays
output = overlay_text(output, f"{timestamp} | {speed} MPH", position='bottom')
```

**Params:** `distortion` (-0.4 to 0), `compression_quality` (5–30), `drop_rate` (0.0–0.2), `speed` (0–120, or auto-random)
**Perf:** ~30ms

### SV-06: ATM Camera

**What:** Overhead angle (vertical stretch), fluorescent tint, extreme pinhole, scanlines.

```
# Vertical stretch (simulate overhead angle)
stretched = cv2.resize(frame, (w, int(h * 1.3)))
cropped = stretched[:h, :]
# Fluorescent green/yellow tint
tinted = color_balance(cropped, shadows=(0, 20, -10), midtones=(0, 15, -5))
# Heavy vignette
vignetted = heavy_vignette(tinted, strength=0.7)
# Scanlines
for y in range(0, h, 3):
    vignetted[y, :] = vignetted[y, :] * 0.6
# Low resolution
output = downscale_upscale(vignetted, factor=3)
```

**Params:** `vertical_stretch` (1.0–1.5), `tint_hue` (green, yellow, neutral), `scanline_spacing` (2–6), `resolution_factor` (2–6)
**Perf:** ~25ms

---

## Section 10: Medical Imaging Aesthetic (New Category: "Medical")

Each medical imaging modality has a **completely unique visual signature** defined by its physics. These effects recreate those signatures from regular video.

### MI-01: X-Ray

**What:** Inverted luminance (dense=bright in negative, or dense=dark in positive), edge emphasis for "bone" structure, scatter noise, blue-white colormap.

```
gray = luminance(frame)
# Invert (standard X-ray is negative)
if negative:
    gray = 255 - gray
# Edge emphasis (simulates bone/density boundaries)
edges = cv2.Sobel(gray, cv2.CV_64F, 1, 1, ksize=3)
edges = np.abs(edges)
edges = (edges / edges.max() * 255).astype(np.uint8)
combined = cv2.addWeighted(gray, 0.7, edges, edge_strength, 0)
# Scatter noise (Poisson — physically accurate for X-ray)
noisy = np.random.poisson(combined.astype(float) / noise_scale) * noise_scale
noisy = np.clip(noisy, 0, 255).astype(np.uint8)
# Blue-white colormap
output = cv2.applyColorMap(noisy, xray_lut)  # custom blue-white LUT
```

**Params:** `negative` (bool), `edge_strength` (0.0–1.0), `noise_scale` (1–20), `colormap` (blue-white, bone, gray)
**Perf:** ~30ms

### MI-02: Ultrasound

**What:** Fan-shaped viewing area, multiplicative speckle noise (Rayleigh distribution — physically accurate), low resolution, measurement caliper overlays.

```
gray = luminance(frame)
# Fan-shaped mask (sector of circle)
fan_mask = sector_mask(h, w, apex=(w//2, h), angle_range=(-30, 30), radius=h*0.9)
masked = gray * fan_mask
# Speckle noise (multiplicative Rayleigh — this is what real ultrasound has)
speckle = np.random.rayleigh(scale=speckle_scale, size=gray.shape)
noisy = np.clip(masked * speckle, 0, 255).astype(np.uint8)
# Low resolution (ultrasound is inherently low-res)
low = cv2.resize(noisy, (w//3, h//3))
upscaled = cv2.resize(low, (w, h), interpolation=cv2.INTER_LINEAR)
# Caliper overlay (decorative measurement lines)
if calipers:
    draw_calipers(upscaled, points=random_measurement_points())
# Surround with black (standard ultrasound display)
output = embed_in_black(upscaled, fan_mask)
```

**Params:** `speckle_scale` (0.3–2.0), `fan_angle` (20–60°), `resolution_factor` (2–6), `calipers` (bool), `depth_markers` (bool)
**Perf:** ~35ms

### MI-03: MRI (T1/T2 Weighted)

**What:** Cross-section slice look with specific contrast weighting. T1 = fat bright, fluid dark. T2 = fluid bright, fat dark. Gibbs ringing artifacts at edges.

```
gray = luminance(frame)
# T1 vs T2 contrast remapping
if mode == 'T1':
    # Bright midtones (fat), dark highlights (fluid)
    mapped = apply_curve(gray, t1_curve)
elif mode == 'T2':
    # Bright highlights (fluid), dark midtones
    mapped = apply_curve(gray, t2_curve)
# Gibbs ringing (oscillation near sharp edges)
edges = cv2.Canny(gray, 50, 150)
ringing = np.zeros_like(gray, dtype=float)
for distance in range(1, ring_count+1):
    dilated = cv2.dilate(edges, None, iterations=distance)
    ringing += dilated * ((-1)**distance) * (1.0 / distance)
output = np.clip(mapped + ringing * ring_strength, 0, 255).astype(np.uint8)
# Banding artifacts (periodic intensity modulation)
bands = np.sin(np.arange(h) * 2 * np.pi / band_period).reshape(-1, 1) * band_strength
output = np.clip(output + bands, 0, 255).astype(np.uint8)
```

**Params:** `mode` (T1, T2, FLAIR, PD), `ring_strength` (0.0–1.0), `ring_count` (1–5), `band_period` (50–200), `band_strength` (0–20)
**Perf:** ~45ms

### MI-04: CT Windowing

**What:** Adjustable contrast window like Hounsfield unit windowing. Different tissue types visible at different window settings. Ring artifacts.

```
gray = luminance(frame)
# Window/level (the core CT visualization technique)
# Maps only [center-width/2, center+width/2] to full 0-255 range
low = center - width // 2
high = center + width // 2
windowed = np.clip((gray - low) / (high - low) * 255, 0, 255).astype(np.uint8)
# Ring artifacts (circular banding from CT reconstruction)
cx, cy = w//2, h//2
for r in range(0, max(w,h), ring_spacing):
    ring_mask = circular_ring(cx, cy, r, thickness=1)
    windowed[ring_mask] = np.clip(windowed[ring_mask] + ring_intensity, 0, 255)
```

**Presets:** bone (center=300, width=1500), lung (center=-600, width=1500), soft_tissue (center=40, width=400), brain (center=40, width=80)
**Params:** `center` (-1000 to 1000), `width` (1–4000), `preset` (enum), `ring_spacing` (20–100), `ring_intensity` (5–30)
**Perf:** ~20ms (pure LUT + ring overlay)

### MI-05: PET Scan

**What:** Hot spots in false color (hot LUT) overlaid on grayscale anatomy. Simulates metabolic activity visualization.

```
gray = luminance(frame)
# Anatomy layer (grayscale, slightly blurred)
anatomy = cv2.GaussianBlur(gray, (3,3), 0)
# Activity layer (threshold + blur for "uptake" regions)
activity = (gray > activity_threshold).astype(float)
activity = cv2.GaussianBlur(activity, (15,15), 0)  # diffuse hot spots
# False color the activity
hot_colored = cv2.applyColorMap((activity * 255).astype(np.uint8), hot_lut)
# Composite: anatomy in gray, activity in color
anatomy_rgb = cv2.cvtColor(anatomy, COLOR_GRAY2BGR)
output = cv2.addWeighted(anatomy_rgb, 1.0 - overlay_opacity, hot_colored, overlay_opacity, 0)
```

**Params:** `activity_threshold` (0.3–0.9), `overlay_opacity` (0.3–0.8), `hot_lut` (hot, jet, inferno), `blur_radius` (5–31)
**Perf:** ~25ms

### MI-06: Microscope / Histology

**What:** Circular aperture mask, chromatic aberration, H&E stain color remapping (pink/purple tissue staining).

```
# Circular aperture
mask = circular_mask(h, w, radius=min(h,w)*0.45)
masked = frame * mask[:,:,np.newaxis]
# Chromatic aberration (microscope optics)
masked = chromatic_aberration(masked, amount=0.01)
# H&E stain color remap (hematoxylin = blue/purple, eosin = pink)
hsv = cv2.cvtColor(masked, COLOR_BGR2HSV)
# Remap hues: blue-ish regions → purple (nuclei), red-ish → pink (cytoplasm)
hsv[:,:,0] = remap_hue(hsv[:,:,0], target_palette='he_stain')
hsv[:,:,1] = np.clip(hsv[:,:,1] * 1.3, 0, 255)  # boost saturation
output = cv2.cvtColor(hsv, COLOR_HSV2BGR)
output = output * mask[:,:,np.newaxis]
```

**Stain presets:** `h_and_e` (standard histology), `trichrome` (blue collagen), `pas` (magenta glycogen), `immunofluorescence` (neon green/red/blue channels on black)
**Params:** `stain` (enum), `aperture_radius` (0.3–0.5), `chromatic_amount` (0.0–0.03), `magnification_label` (4x, 10x, 40x, 100x — overlay text)
**Perf:** ~35ms

---

## Section 11: Cross-Category Combinations

The real power is chaining effects across these new categories with existing ones:

| Combination | What It Creates | Why It's Dramatic |
|-------------|----------------|-------------------|
| X-Ray + Datamosh | Skeletal forms that melt between frames | Medical horror aesthetic |
| Night Vision + Pixel Physics (gravity) | Phosphor particles falling through surveillance feed | Haunted camera |
| Thermal + Reaction Diffusion | Heat patterns that evolve via Turing patterns | Living thermal signature |
| Ultrasound + Domain Warp | Speckled fan view that warps like fluid | Prenatal nightmare |
| CCTV + Generation Loss (CA-15) | Surveillance footage degrading over time | Found footage horror |
| Fisheye + Logistic Cascade | Distorted view that bifurcates into chaos at edges | Paranoia lens |
| MRI + Spectral Freeze | Cross-section that freezes in frequency domain | Brain scan from the future |
| Anamorphic + Print Degradation (risograph) | Squeezed cinema printed on cheap paper | Indie film poster in motion |
| CT Windowing + Entropy Map | Different tissue windows revealed by information density | Diagnostic glitch art |
| Microscope + Cellular Automata | Histology slides where cells actually grow | Biology simulation |
| PET Scan + Compression Oracle | Hot spots appear at high-information regions | AI diagnosis aesthetic |
| Body Cam + Stutter + Dropout | Corrupted police footage aesthetic | Found footage / political art |

---

## Section 12: Consolidation Audit

**Goal:** Reduce effect count without losing capability. Only combine where implementation is shared and UX is simpler with one effect + more params.

### Consolidation Map (8 merges, -11 effects)

| Absorbed | Into | Why | Capability Lost? |
|----------|------|-----|-----------------|
| CA-01 `dct_isolate` | **CA-03 `dct_sculpt`** | Isolate = sculpt with binary (0/1) gains. Add `preset: isolate_low/mid/high` | None — isolate is a preset |
| CA-08 `grid_shift` | **CA-09 `grid_moire`** | grid_shift = grid_moire with passes=2. Min passes=2 covers it. | None — shift is minimum case |
| CA-10 `grid_phase_animate` | **CA-09 `grid_moire`** | Add `animate: bool, speed, path` params. Walk = moire with frame-dependent offsets. | None — animate is a mode |
| CA-12 `chroma_separate` | **→ `chroma_control`** | All 3 chroma effects share YCbCr decomposition. One effect, 6 knobs. | None — all 3 become presets |
| CA-13 `chroma_bleed` | **→ `chroma_control`** | `bleed_amplification` param (0=off, 50=max) | None |
| CA-14 `chroma_destroy` | **→ `chroma_control`** | `kill_cb/kill_cr` params (0=keep, 1=annihilate) | None |
| CA-16 `quality_oscillate` | **CA-15 `generation_loss`** | Add `quality_pattern: constant/oscillate/ramp_down/random`. Oscillate = generation_loss with varying q. | None — oscillate is a pattern |
| CA-18 `selective_generation` | **REMOVED** | Entropic v0.4.2 already has region selection. generation_loss + region mask = this effect. | None — already exists |
| LO-06 `pinhole` | **→ `lo_fi_lens`** | Both share: vignette, softness, color cast. Holga adds distortion + leaks. | None — pinhole is a preset |
| LO-07 `holga/lomo` | **→ `lo_fi_lens`** | Presets: pinhole, holga, lomo, diana. Each is a parameter combination. | None |
| SV-01 `cctv` + SV-04 `body_cam` + SV-05 `dash_cam` + SV-06 `atm` | **→ `surveillance_cam`** | All share: barrel distortion, low res, timestamp, noise. Differences = param settings. | None — each becomes a preset |

### Consolidated `chroma_control` params:
```
chroma_control(
    luma_quality=95,          # 1-100 (from chroma_separate)
    chroma_quality=20,        # 1-100 (from chroma_separate)
    subsample="420",          # 444/422/420/411 (from chroma_separate)
    bleed_amplification=0,    # 0-50, 0=off (from chroma_bleed)
    kill_cb=0.0,              # 0-1 (from chroma_destroy)
    kill_cr=0.0               # 0-1 (from chroma_destroy)
)
# Presets: "separate" (luma/chroma split), "bleed" (amplified color bleed), "drain" (channel kill)
```

### Consolidated `generation_loss` params:
```
generation_loss(
    generations=20,
    quality=15,                # base quality (used when pattern=constant)
    quality_pattern="constant", # constant/oscillate/ramp_down/ramp_up/random
    q_high=95,                 # for oscillate pattern
    q_low=5,                   # for oscillate pattern
    output_generation="animate",
    show_diff=False
)
```

### Consolidated `grid_moire` params:
```
grid_moire(
    num_passes=3,              # 2+ (was grid_shift at 2, grid_moire at 3-8)
    offsets="fibonacci",       # list or preset
    quality_per_pass=20,
    animate=False,             # from grid_phase_animate
    animate_speed=1.0,         # offsets per frame
    animate_path="linear"      # linear/spiral/random/bounce
)
```

### Consolidated `lo_fi_lens` params:
```
lo_fi_lens(
    preset="holga",            # pinhole/holga/lomo/diana
    softness=5,                # kernel size 1-11
    vignette=0.7,              # 0-1
    color_cast_hue=30,         # 0-360
    distortion=-0.3,           # barrel distortion (0=none, pinhole default)
    light_leak_intensity=0.5,  # 0-1 (0=none, pinhole default)
    light_leak_position="corner",
    contrast=1.2               # 0.8-2.0
)
```

### Consolidated `surveillance_cam` params:
```
surveillance_cam(
    preset="cctv",             # cctv/body_cam/dash_cam/atm
    distortion=-0.25,          # barrel distortion amount
    resolution_scale=4,        # downscale factor
    interlace=True,            # scanline interlace
    timestamp=True,
    noise_amount=0.1,          # 0-0.3
    compression_quality=20,    # simulated low bitrate
    tint="neutral",            # neutral/green/yellow
    frame_drop_rate=0.0,       # 0-0.2
    glitch_interval=0,         # 0=off, 30-300 frames
    scanline_spacing=0,        # 0=off, 2-6
    aspect="16:9",             # 16:9 or 4:3
    motion_blur=False
)
```

### What stays SEPARATE (genuinely unique)

| Effect | Why It Can't Merge |
|--------|-------------------|
| CA-02 `dct_swap` | Rearranges blocks — different operation than sculpting coefficients |
| CA-04 `dct_phase_destroy` | Phase vs magnitude — fundamentally different transform |
| CA-05 `quant_amplify` | Table amplification — different from spatial gradient (CA-06) or interpolation (CA-07) |
| CA-06 `quant_morph` | Spatial quality variation — WHERE, not WHAT |
| CA-07 `quant_table_lerp` | Table interpolation over time — different math |
| CA-11 `grid_scale_mix` | Block SIZE mixing — different dimension than offset mixing |
| CA-17 `cross_codec` | Codec switching — completely different pipeline |
| CA-19 `mosquito_amplify` | Edge artifact amplification — unique detect+amplify loop |
| CA-20 `block_crystallize` | Block averaging — unique operation |
| SV-02 `night_vision` | Green phosphor + bloom — completely different color science |
| SV-03 `infrared_thermal` | False color LUT — different rendering pipeline |
| All 6 medical (MI-01–06) | Each modality has unique physics — X-ray inversion vs ultrasound speckle vs MRI contrast |
| All 7 optics (LO-01–05, LO-08 + lo_fi_lens) | Each is a different optical phenomenon |
| All 5 top picks (Sec.1) | All genuinely distinct algorithms |

---

## New Category Summary (Post-Consolidation)

| Category | Original Count | Consolidated Count | Effects |
|----------|---------------|-------------------|---------|
| Emergent Systems | 3 | 3 | reaction_diffusion, cellular_automata, crystal_growth |
| Information Theory | 3 | 3 | entropy_map, compression_oracle, logistic_cascade |
| Warping | 2 | 2 | domain_warp, strange_attractor |
| Codec Archaeology | 20 | **13** | dct_sculpt, dct_swap, dct_phase_destroy, quant_amplify, quant_morph, quant_table_lerp, grid_moire, grid_scale_mix, chroma_control, generation_loss, cross_codec, mosquito_amplify, block_crystallize |
| Optics | 8 | **7** | fisheye, anamorphic, tilt_shift, chromatic_aberration, bokeh_shaper, lo_fi_lens, coma |
| Surveillance | 6 | **3** | surveillance_cam, night_vision, infrared_thermal |
| Medical | 6 | 6 | xray, ultrasound, mri, ct_windowing, pet_scan, microscope |
| Recombinants | 10 concepts | 10 concepts | (logic-level, not buildable effects) |
| **TOTAL** | **56 → 45 effects** | | **-11 effects, zero capability lost** |

**All CPU-feasible, all under 500ms at 1080p, all numpy/scipy/opencv only (no new deps).**

---

---

## Section 13: TOP 20 EFFECTS — Priority Build Order

Ranked across all 56 effects by: Visual Impact (V), Novelty (N), Feasibility (F), Chainability (C), Brand Alignment (B). Each scored 1-10, max 50.

| Rank | Effect | ID | V | N | F | C | B | Total | Why Build First |
|------|--------|----|---|---|---|---|---|-------|----------------|
| 1 | **Compression Oracle** | Sec.1 | 10 | 10 | 9 | 10 | 10 | **49** | Defines Entropic's identity. Nothing like it exists. Drives every other effect as modulator. |
| 2 | **Generation Loss** | CA-15 | 9 | 9 | 10 | 10 | 10 | **48** | Core codec archaeology discovery. Animate through generations = mesmerizing. 20ms per gen. |
| 3 | **Reaction Diffusion** | Sec.1 | 10 | 10 | 8 | 8 | 10 | **46** | Turing patterns on video. Scientifically beautiful. Never seen in a video tool. |
| 4 | **Grid Moiré** | CA-09 | 9 | 10 | 8 | 9 | 10 | **46** | The exact phenomenon from the user's observation. Multi-grid interference. Mathematically rich. |
| 5 | **Logistic Cascade** | Sec.1 | 8 | 10 | 10 | 9 | 10 | **47** | Deterministic chaos at 13ms. Bifurcation as visual effect. Profound + fast. |
| 6 | **Night Vision** | SV-02 | 9 | 7 | 10 | 9 | 10 | **45** | Instant cultural recognition. 25ms. Chains with everything. Universal dramatic potential. |
| 7 | **X-Ray** | MI-01 | 9 | 8 | 10 | 9 | 9 | **45** | Medical horror aesthetic. Fast LUT ops. Edge emphasis reveals hidden structure. |
| 8 | **Domain Warp** | Sec.1 | 9 | 9 | 9 | 9 | 9 | **45** | Recursive noise displacement. Organic distortion unlike rigid transforms. |
| 9 | **Cross Codec** | CA-17 | 9 | 10 | 8 | 8 | 10 | **45** | "Conversation between algorithms." Each codec has a personality. Truly novel concept. |
| 10 | **Ultrasound** | MI-02 | 9 | 9 | 10 | 8 | 9 | **45** | Rayleigh speckle + fan mask. Horror/surreal. Physically accurate noise model. |
| 11 | **Entropy Map** | Sec.1 | 8 | 9 | 7 | 10 | 9 | **43** | THE universal modulator. Information density drives all other effects. Meta-tool. |
| 12 | **DCT Sculpt** | CA-03 | 8 | 10 | 9 | 8 | 9 | **44** | 64-band graphic EQ for images. Animatable = breathing geometric patterns. |
| 13 | **Anamorphic** | LO-02 | 8 | 8 | 10 | 8 | 8 | **42** | Cinema look + horizontal flare. Cultural recognition. 35ms. |
| 14 | **Infrared/Thermal** | SV-03 | 8 | 7 | 10 | 9 | 8 | **42** | False color heat mapping. Dramatic palette. 20ms LUT. |
| 15 | **Mosquito Amplify** | CA-19 | 8 | 9 | 8 | 8 | 9 | **42** | Neon edge outlines from compression ringing. Hidden codec artifact made visible. |
| 16 | **DCT Phase Destroy** | CA-04 | 8 | 9 | 9 | 8 | 9 | **43** | Phase scramble = frosted glass. Same texture, wrong positions. Eerie. |
| 17 | **Quality Gradient** | CA-06 | 8 | 9 | 8 | 9 | 9 | **43** | Spatially varying compression. Faces pristine, edges disintegrate. Compositional control. |
| 18 | **Fisheye** | LO-01 | 8 | 6 | 10 | 9 | 7 | **40** | Essential lens distortion. Fast remap. Gateway to optics category. |
| 19 | **CCTV Classic** | SV-01 | 8 | 6 | 10 | 8 | 8 | **40** | Complete surveillance aesthetic. Cultural resonance. Found footage. |
| 20 | **MRI** | MI-03 | 8 | 9 | 9 | 7 | 8 | **41** | T1/T2 contrast + Gibbs ringing. Scientific + deeply eerie. |

### Build Strategy (4 waves)

**Wave 1 — Foundation (5 effects, ~4h):** compression_oracle, logistic_cascade, entropy_map, generation_loss, grid_moiré
- These create the MODULATOR INFRASTRUCTURE. Entropy_map and compression_oracle become inputs for everything else.

**Wave 2 — Visual Showstoppers (5 effects, ~3h):** reaction_diffusion, night_vision, x-ray, domain_warp, cross_codec
- These are the DEMO REEL effects. Each one makes jaws drop on its own.

**Wave 3 — Aesthetic Packs (5 effects, ~3h):** ultrasound, dct_sculpt, anamorphic, thermal, mosquito_amplify
- Complete the medical/optics/codec aesthetic categories.

**Wave 4 — Polish + Remaining (5 effects, ~3h):** dct_phase_destroy, quality_gradient, fisheye, cctv_classic, mri
- Fill out the category coverage. All fast to build.

---

## Section 14: Codec Archaeology Parameterization Audit (Subtle → Fully Fucked)

Every codec archaeology effect MUST work from "barely noticeable" to "completely destroyed." Audit of current param ranges:

| Effect | Subtle Setting | Extreme Setting | Range OK? | Notes |
|--------|---------------|-----------------|-----------|-------|
| CA-01 dct_isolate | blend_with_original=0.95, freq_band=all | blend=0.0, freq_band=single_coefficient | YES | blend param gives full control |
| CA-02 dct_swap | mode=swap_pairs (nearby blocks) | mode=shuffle (all blocks random) | EXTEND | Add `severity` (0-1): 0=swap adjacent only, 1=fully random |
| CA-03 dct_sculpt | all gains=1.0 (bypass) | all gains=0 except one (isolate single basis) | YES | 64 knobs gives infinite range |
| CA-04 dct_phase_destroy | phase_randomness=0.05 | phase_randomness=1.0 | YES | |
| CA-05 quant_amplify | amplification=1.1 | amplification=100 | YES | 1.0=transparent, 100=one color per block |
| CA-06 quant_morph | q_low=90, q_high=100 | q_low=1, q_high=100 | YES | |
| CA-07 quant_table_lerp | t near 0 or 1 (single table) | rapid animation (oscillate t) | EXTEND | Add `oscillation_speed` for auto-animate |
| CA-08 grid_shift | quality_pass1=90, pass2=90 | quality_pass1=5, pass2=5, offset=(4,4) | YES | |
| CA-09 grid_moire | 2 passes, quality 80 | 8 passes, quality 5 | YES | |
| CA-10 grid_phase_animate | speed=0.1, quality=80 | speed=2.0, quality=5 | YES | |
| CA-11 grid_scale_mix | 2 sizes, quality 80 | 4+ sizes, quality 5, blend=multiply | EXTEND | Allow 4+ block sizes, not just 3 |
| CA-12 chroma_separate | luma=95, chroma=80 | luma=5, chroma=1 | YES | |
| CA-13 chroma_bleed | bleed_amplification=1.5 | bleed_amplification=20 | EXTEND to 50 | At 50x, colors completely detach from objects |
| CA-14 chroma_destroy | kill_cb=0.1, kill_cr=0.1 | kill_cb=1.0, kill_cr=1.0 | YES | |
| CA-15 generation_loss | generations=2, quality=80 | generations=100, quality=5 | YES | |
| CA-16 quality_oscillate | q_high=95, q_low=60, 2 passes | q_high=100, q_low=1, 20 passes | YES | |
| CA-17 cross_codec | 2-codec chain, high quality | 5+ codec chain, all quality 5 | EXTEND | Allow arbitrary chain length (not capped at 3) |
| CA-18 selective_generation | 5 gens, quality 60, small mask | 100 gens, quality 1, full mask | YES | |
| CA-19 mosquito_amplify | amplification=1.5 | amplification=20 | EXTEND to 50 | At 50x, ringing halos become dominant visual |
| CA-20 block_crystallize | color_depth=128 | color_depth=1 | YES | 1 color per block = ultimate grid |

**Extended ranges needed (4 effects):**
- CA-02: Add `severity` param (0.0–1.0)
- CA-13: Extend `bleed_amplification` to 50 (not 20)
- CA-17: Remove codec chain length cap (allow 2–20)
- CA-19: Extend `amplification` to 50 (not 20)

**Global additions for ALL 20 codec archaeology effects:**

1. **`dry_wet`** (0.0–1.0): Blends processed output with original. Universal "subtle" knob — at 0.05, ANY effect becomes barely perceptible. At 1.0, full effect. Standard in audio plugins.

2. **`block_size`** (2–128, default 8): Controls the DCT processing cell size. This is Axis G — the scale multiplier that transforms every effect's character. At 2×2: micro-pixelation. At 8×8: standard JPEG. At 64×64: architectural-scale geometric patterns. At 128×128: screen-spanning projections. Implementation uses `scipy.fft.dctn` which works at any block size (not locked to JPEG's 8×8). See Axis G table above for full performance/character breakdown.

Combined, these two global params give EVERY codec archaeology effect a range from "imperceptible 8×8 whisper" (`dry_wet=0.02, block_size=8`) to "128×128 cathedral stained glass at full blast" (`dry_wet=1.0, block_size=128`).

---

## Section 15: Novel Recombinant Concepts (Logic-Level, Not Parameter-Level)

These are new MENTAL MODELS for combining effects across categories. Each recombinant creates a new conceptual space, not just a parameter preset.

### RC-01: Entropy-Gated Optics

**Logic:** Information density controls optical fidelity. The image "knows" where it matters.

```
entropy = entropy_map(frame)
# High-info regions: sharp, correct optics
# Low-info regions: increasing distortion (fisheye, chromatic aberration, coma)
distortion_map = (1 - entropy) * max_distortion
output = apply_variable_lens(frame, distortion_map)
```

**Why novel:** No tool connects information theory to optical simulation. The image's own content determines how the "lens" behaves — smart regions are in focus, boring regions are optically destroyed.

### RC-02: Diagnostic Codec

**Logic:** Medical imaging parameters applied to codec mathematics, not pixel space.

```
dct_coefficients = dct_block_process(frame)
# CT windowing but on DCT coefficients instead of pixel values
# "Bone window" = high-frequency coefficients only (edges)
# "Lung window" = low-frequency coefficients only (smooth regions)
# "Soft tissue window" = mid-frequency band
windowed = ct_window(dct_coefficients, center=freq_center, width=freq_width)
output = idct_reconstruct(windowed)
```

**Why novel:** CT windowing is never applied to frequency domain. Combines medical imaging's core technique with codec's core mathematics. Different "tissue windows" become different frequency perspectives on the same image.

### RC-03: Surveillance Decay

**Logic:** The recording degrades like the camera hardware does over years.

```
for generation in range(years):
    frame = generation_loss(frame, quality=quality_decay[generation])
    frame = add_noise(frame, amount=noise_increase[generation])
    frame = reduce_resolution(frame, factor=resolution_decay[generation])
    frame = corrupt_timestamp(frame, generation)
    frame = interlace_worsen(frame, generation)
```

**Why novel:** Links temporal degradation (generation loss) to hardware degradation (surveillance aesthetic) in a single narrative arc. The video ages like the camera that recorded it.

### RC-04: Chaos Lens

**Logic:** Lens quality is a function of deterministic chaos.

```
chaos = logistic_cascade(frame, r_value)  # per-pixel chaos state
# r < 3.57: stable (clean optics)
# r > 3.57: chaotic (color channels scatter)
stable_mask = chaos < bifurcation_threshold
output[stable_mask] = frame[stable_mask]  # clean
output[~stable_mask] = chromatic_aberration(frame[~stable_mask], amount=chaos_intensity)
```

**Why novel:** Mathematical chaos as a physical property of the "lens." The lens itself is governed by the logistic map — some regions are stable, others are chaotically distorted. Animate r_value to watch the lens "break" at the bifurcation point.

### RC-05: Thermal Diffusion

**Logic:** Heat drives chemical reaction-diffusion dynamics.

```
thermal = infrared_thermal(frame)  # false-color heat map
temperature = luminance(thermal)  # use brightness as "temperature"
# Use temperature as diffusion rate in Gray-Scott model
# Hot spots: fast diffusion (patterns spread quickly, dissolve)
# Cold spots: slow diffusion (patterns form slowly, persist)
rd_output = reaction_diffusion(frame, diffusion_rate=temperature * rate_scale)
```

**Why novel:** Physically motivated: real RD systems are temperature-dependent. The thermal aesthetic becomes the input parameter for emergent pattern formation. Heat literally drives pattern creation.

### RC-06: Compression Microscope

**Logic:** Compression quality as depth of field. The codec becomes a lens.

```
# Center = high quality (sharp focus, high magnification)
# Edges = destroyed (bokeh from compression, not optics)
quality_map = radial_gradient(center=high_q, edge=low_q)
output = quant_morph(frame, gradient=quality_map)
# Add microscope circular aperture
output = circular_mask(output)
# Add chromatic aberration (microscope optics)
output = chromatic_aberration(output, amount=0.01)
```

**Why novel:** Codec artifacts reframed as optical phenomena. "Out of focus" means "heavily compressed." The visual result is similar to real DOF but the mechanism is information-theoretic. A conceptual bridge between optics and information theory.

### RC-07: Tomographic Generation

**Logic:** Iterative compression as depth scanning. Each generation reveals a different layer.

```
layers = []
current = frame
for gen in range(max_generations):
    current = jpeg_roundtrip(current, quality=q)
    layers.append(current)
# Display like MRI slices: scroll through generations
# Generation 1 = surface (most detail)
# Generation 50 = deep structure (compression attractor)
output = layers[current_slice]
# Or: combine like PET/CT overlay
output = overlay(layers[0], colorize(layers[50]), opacity=0.5)
```

**Why novel:** Reframes generation loss as tomography. Each compression pass "peels away" a layer of the image, revealing what the codec considers fundamental. The attractor state IS the deep structure.

### RC-08: Forensic Camera

**Logic:** AI forensics on degraded footage. Compression oracle reveals what the surveillance camera captured.

```
# Start with CCTV aesthetic
degraded = cctv_classic(frame)
# compression_oracle reveals information density
info_map = compression_oracle(degraded)
# Highlight: what actually survived the degradation?
output = overlay_heatmap(degraded, info_map, label="SIGNAL DETECTED")
```

**Why novel:** Combines surveillance aesthetics with information theory analysis. The output looks like forensic software analyzing evidence footage. Has political/documentary art potential.

### RC-09: Phosphor Moiré

**Logic:** The display medium has its own compression grid.

```
# Night vision phosphor screen
nv = night_vision(frame)
# The intensifier tube phosphor screen has a physical pixel grid
# This grid interferes with JPEG's 8x8 block grid
phosphor_grid = generate_phosphor_pattern(pitch=12)  # pixel pitch
output = grid_moire(nv, extra_grid=phosphor_grid)
```

**Why novel:** Two different grid systems (codec mathematical + display physical) interfering. Triple interference if the original content also had a grid (screens, fabrics). Moiré from moiré.

### RC-10: Spectral Medical

**Logic:** Each medical imaging modality applied to a DIFFERENT frequency band, composited.

```
low_freq = dct_isolate(frame, band="low")
mid_freq = dct_isolate(frame, band="mid")
high_freq = dct_isolate(frame, band="high")

low_as_ultrasound = ultrasound(low_freq)     # smooth areas → speckle
mid_as_xray = xray(mid_freq)                  # mid detail → skeletal
high_as_mri = mri(high_freq, mode="T2")       # fine edges → Gibbs ringing

output = composite(low_as_ultrasound, mid_as_xray, high_as_mri, mode="screen")
```

**Why novel:** The image is "diagnosed" by three different medical instruments simultaneously, each seeing a different frequency layer. A full-body scan where different tissues get different imaging modalities.

---

## Updated Category Summary (Post-Consolidation)

| Category | Original | Consolidated | Build Wave |
|----------|----------|-------------|-----------|
| Emergent Systems | 3 | 3 | Wave 2 |
| Information Theory | 3 | 3 | Wave 1 |
| Warping | 2 | 2 | Wave 2 |
| Codec Archaeology | 20 | **13** | Waves 1-4 |
| Optics | 8 | **7** | Waves 2-4 |
| Surveillance | 6 | **3** | Waves 2-3 |
| Medical | 6 | 6 | Waves 2-3 |
| Recombinants | 10 concepts | 10 concepts | Post-Wave 4 |
| **TOTAL** | **56 → 45 effects + 10 recombinant concepts** | | **-11 effects, zero capability lost** |

---

*Generated by /mad-scientist + compression archaeology + optics/surveillance/medical imaging research, 2026-02-18*
*Cross-references: MASTER-EFFECTS-LIST.md, REMAINING-ROADMAP.md, POP-CHAOS-DESIGN-SYSTEM.md*
*Sources: [Compression Artifacts - Wikipedia](https://en.wikipedia.org/wiki/Compression_artifact), [JPEG Quality Loss - Uploadcare](https://uploadcare.com/blog/jpeg-quality-loss/), [DCT Basis Patterns - ResearchGate](https://www.researchgate.net/figure/DCT-patterns-visualization-The-combination-of-the-presented-64-patterns-with-their_fig2_334360686), [Double JPEG Detection - Springer](https://link.springer.com/chapter/10.1007/978-3-642-34263-9_1), [Chroma Subsampling - Wikipedia](https://en.wikipedia.org/wiki/Chroma_subsampling), [Color Bleeding in 4:2:0 - IEEE](https://ieeexplore.ieee.org/document/8526304/), [Barrel Distortion - OpenCV Docs](https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html), [Rayleigh Speckle Noise - Ultrasound Physics](https://en.wikipedia.org/wiki/Speckle_noise), [CT Windowing - Radiopaedia](https://radiopaedia.org/articles/windowing-ct), [Gibbs Ringing - MRI Artifacts](https://mriquestions.com/gibbs-artifact.html), [Gray-Scott Reaction-Diffusion](https://groups.csail.mit.edu/mac/projects/amorphous/GrayScott/), [Logistic Map](https://en.wikipedia.org/wiki/Logistic_map)*

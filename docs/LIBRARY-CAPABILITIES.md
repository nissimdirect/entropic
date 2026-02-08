# Entropic Library Capabilities Audit

**Conducted by:** The Mad Scientist + CTO
**Date:** 2026-02-07
**Scope:** Every third-party package used in the Entropic codebase, audited for current usage versus total capability. New effect ideas and cross-package interaction effects.

---

## Table of Contents

1. [NumPy](#numpy)
2. [Pillow (PIL)](#pillow-pil)
3. [OpenCV (cv2)](#opencv-cv2)
4. [FFmpeg (subprocess)](#ffmpeg-subprocess)
5. [Gradio](#gradio)
6. [FastAPI + Pydantic](#fastapi--pydantic)
7. [Python Standard Library](#python-standard-library)
8. [Interaction Effects (Cross-Package Combos)](#interaction-effects-cross-package-combos)
9. [Summary: Priority-Ranked Ideas](#summary-priority-ranked-ideas)

---

## NumPy

### Currently Used For:
- `np.array()` / `np.zeros()` / `np.zeros_like()` / `np.full()` — Frame allocation and initialization
- `np.clip()` — Clamping pixel values to 0-255 range
- `np.roll()` — Channel shifting (circular pixel displacement)
- `np.argsort()` — Pixel sorting by computed keys
- `np.sin()` / `np.cos()` / `np.arctan2()` — Wave distortion and hue calculations
- `np.sqrt()` — Edge magnitude calculation (Sobel)
- `np.random.RandomState()` — Seeded random generation for noise, displacement, VHS
- `np.convolve()` — 1D convolution for VHS color bleed
- `np.where()` — Conditional pixel operations (contrast hard mode)
- `np.diff()` / `np.concatenate()` — Finding contiguous runs in pixelsort masks
- `np.mod()` — Exposure wrap mode
- `np.frombuffer()` — Raw file byte interpretation
- `np.tile()` — Tiling raw data to fill frame dimensions
- `frame.astype(np.float32)` — Float conversion for intermediate calculations
- Basic arithmetic (`+`, `-`, `*`, `/`, `**`, `//`, `%`) on arrays — Everywhere

### Untapped Capabilities:

1. **`np.fft.fft2()` / `np.fft.ifft2()` — 2D Fast Fourier Transform**
   Converts an image from spatial domain (pixels) to frequency domain (waves). You can manipulate frequencies directly: remove high frequencies (blur), remove low frequencies (edge enhancement), selectively amplify frequency bands, rotate the phase spectrum, or swap magnitude/phase between two images.

2. **`np.fft.fftshift()` — Frequency Spectrum Centering**
   Shifts zero-frequency component to the center of the spectrum, making it visualizable. The raw magnitude spectrum of a frame looks like a glowing cross of light -- an effect itself.

3. **`np.linalg.svd()` — Singular Value Decomposition**
   Decomposes an image into ranked components by importance. Keeping only the top N singular values creates a "lossy compression" look. Low N = ghostly, painterly abstraction. High N = near-original.

4. **`np.linalg.eig()` — Eigendecomposition**
   Can be applied to color covariance matrices to find principal color axes. Useful for color-space rotation, decorrelation stretch (geology/astronomy technique that makes subtle color differences visible).

5. **`np.random.choice()` with probability distributions**
   Currently we use uniform and gaussian noise. NumPy supports Poisson, exponential, beta, gamma, Cauchy, and other distributions. Each produces visually distinct noise textures. Cauchy noise has extreme outliers (spike artifacts). Poisson noise matches photon noise in real cameras.

6. **`np.histogram()` / `np.histogram2d()`**
   Computes pixel intensity distributions. Useful for auto-level (histogram stretching), histogram equalization, and histogram matching (making one frame's color distribution match another).

7. **`np.percentile()` / `np.quantile()`**
   Find specific percentile values in pixel data. Useful for robust contrast stretching (e.g., map 2nd-98th percentile to 0-255, ignoring outliers).

8. **`np.convolve()` (2D via manual kernel) and `np.apply_along_axis()`**
   We use 1D convolution for VHS bleed. Full 2D convolution with custom kernels opens up emboss, edge enhance, ridge detection, unsharp mask, custom artistic kernels, and kernel-based texture generation.

9. **`np.meshgrid()` — Coordinate Grid Generation**
   Creates 2D coordinate arrays. Essential for procedural effects: radial gradients, spiral patterns, Perlin-like noise, polar coordinate transforms, fisheye distortion, and tunnel/vortex effects.

10. **`np.interp()` — Piecewise Linear Interpolation**
    Apply arbitrary tone curves to pixel values. S-curves, film emulation LUTs, solarization curves, and custom transfer functions.

11. **`np.polyval()` / `np.polynomial` — Polynomial Functions**
    Apply polynomial color curves. Quadratic, cubic, or higher-order curves for precise color grading.

12. **`np.cumsum()` — Cumulative Sum**
    Useful for implementing integral images (summed area tables) which enable O(1) box blur at any radius, and for scan-line effects where pixel values accumulate.

13. **`np.sort()` along arbitrary axes**
    Currently pixelsort operates row-by-row with Python loops. `np.sort()` along axis=1 would sort all rows simultaneously (massive speedup), though threshold masking still needs loops.

14. **`np.gradient()` — Numerical Gradient**
    Computes image gradient (direction and magnitude of intensity change) without manual Sobel. Cleaner than our current manual gx/gy computation in `edge_detect`.

15. **`np.correlate()` — Cross-Correlation**
    Pattern matching between image regions. Could detect repeating structures for targeted glitching.

16. **`np.ma.MaskedArray` — Masked Arrays**
    Arrays where certain elements are "masked out" from operations. Apply effects only to regions that meet criteria (bright areas, edges, specific colors) without if/else per-pixel.

17. **`np.einsum()` — Einstein Summation**
    Expresses complex tensor operations concisely. Color matrix transforms (3x3 matrix * RGB vector per pixel) in one line, faster than loops.

### New Effect Ideas from NumPy:

- **Spectral Glitch:** FFT the frame, randomly zero out frequency bands or add noise to the phase spectrum, inverse FFT back. Creates dreamlike ringing artifacts unlike any spatial-domain effect.
- **Phase Swap:** Take the magnitude spectrum from frame A and the phase spectrum from frame B (or a procedural pattern). The result looks structurally like B but colored like A. Eerie double-exposure feel.
- **SVD Rank Crush:** Decompose frame with SVD, keep only the top 5-20 singular values, reconstruct. The image becomes a ghostly, painterly approximation of itself -- like a memory fading.
- **Procedural Gradient Mask:** Use `meshgrid` to create radial, linear, or spiral gradient masks. Apply effects through the mask so they fade from center to edge (or follow any mathematical shape).
- **Histogram Equalization:** Auto-contrast that stretches the histogram to fill the full range. Reveals detail in dark or washed-out footage.
- **Film Curve Emulation:** Use `np.interp()` with lookup tables modeled after real film stocks (Portra, Velvia, Tri-X). Each film has a distinctive S-curve and color response.
- **Poisson Noise:** `np.random.poisson()` produces noise that looks like actual camera sensor noise (photon shot noise). More realistic than gaussian for "low light" looks.
- **Vortex Warp:** Use `meshgrid` + polar coordinates to create a swirl/vortex distortion centered on any point. Strength falls off with distance.
- **Decorrelation Stretch:** Use eigendecomposition of the color covariance matrix to amplify subtle color differences. Turns near-monochrome footage into vivid false color.
- **Cumulative Smear:** `cumsum` along rows or columns with decay, creating a paint-smear or light-trail effect.

---

## Pillow (PIL)

### Currently Used For:
- `Image.fromarray()` / `np.array(img)` — Converting between NumPy arrays and PIL Images
- `Image.open()` / `img.convert("RGB")` — Loading images from disk
- `img.resize()` with `NEAREST`, `BILINEAR`, `LANCZOS`, `BICUBIC` — Resolution scaling (bitcrush, chromatic aberration, preview downscale)
- `img.save()` — Writing frames to disk (PNG, JPEG)
- `ImageFilter.BoxBlur()` — Box blur effect
- `ImageFilter.Kernel()` — Custom convolution kernel (motion blur)
- `ImageFilter.SHARPEN` — Sharpening filter

### Untapped Capabilities:

1. **`ImageFilter.GaussianBlur()`**
   True Gaussian blur (we only use box blur). Gaussian is perceptually smoother and more natural -- the standard blur for photographic effects.

2. **`ImageFilter.EMBOSS`**
   Creates a 3D embossed look by highlighting directional edges. Instant "stamped metal" or "carved stone" aesthetic.

3. **`ImageFilter.CONTOUR`**
   Extracts contour lines from the image, like a topographic map of luminance. Different from our Sobel edge detection -- produces cleaner, thinner lines.

4. **`ImageFilter.FIND_EDGES`**
   Edge detection that differs from our manual Sobel. Built-in, optimized, and produces different visual character.

5. **`ImageFilter.EDGE_ENHANCE` / `EDGE_ENHANCE_MORE`**
   Enhances edges while keeping flat areas intact. Good for adding "crispness" without full sharpening artifacts.

6. **`ImageFilter.DETAIL`**
   Enhances fine detail. Different from sharpen -- brings out texture in fabric, skin, foliage without halos.

7. **`ImageFilter.SMOOTH` / `SMOOTH_MORE`**
   Noise reduction that preserves edges better than box blur. Useful for "soft skin" or "painted" looks.

8. **`ImageFilter.MedianFilter()`**
   Replaces each pixel with the median of its neighborhood. Excellent for removing salt-and-pepper noise while preserving edges. Creates a "posterized watercolor" look at large kernel sizes.

9. **`ImageFilter.ModeFilter()`**
   Replaces each pixel with the most frequent value in its neighborhood. Creates strong posterization with clean edges -- like a screen print.

10. **`ImageFilter.MinFilter()` / `MaxFilter()`**
    MinFilter darkens (erosion), MaxFilter brightens (dilation). These are morphological operations. Erode then dilate = "opening" (removes small bright spots). Dilate then erode = "closing" (fills small dark holes). Sequence them for dramatic structural effects.

11. **`ImageFilter.RankFilter()`**
    Generalized rank filter -- pick any percentile from the neighborhood. size=5, rank=0 = darkest pixel in 5x5 area. rank=24 = brightest. Creates exotic blur/sharpen hybrids.

12. **`ImageFilter.UnsharpMask(radius, percent, threshold)`**
    Professional unsharp masking with radius, amount, and threshold. Much better than our current multi-pass SHARPEN approach. Industry-standard sharpening.

13. **`ImageDraw` module**
    Draw geometric shapes, lines, arcs, polygons, ellipses directly onto frames. Enables: scanline patterns (more precise than our loop), geometric overlays, grid patterns, crosshairs, HUD elements, frame borders, vignettes via radial gradient draw.

14. **`ImageFont` module**
    Render text onto frames with TrueType/OpenType fonts. Enables: timestamp overlays, glitch text effects, ASCII art conversion, subtitle generation, watermarks.

15. **`ImageChops` module — Channel Operations**
    - `ImageChops.add()` — Additive blending (Screen-like)
    - `ImageChops.subtract()` — Difference effect
    - `ImageChops.multiply()` — Multiply blend mode
    - `ImageChops.screen()` — Screen blend mode
    - `ImageChops.difference()` — Exact pixel difference between frames (motion detection)
    - `ImageChops.invert()` — Color inversion (we do this manually with NumPy)
    - `ImageChops.blend()` — Alpha blending between two images
    - `ImageChops.composite()` — Compositing with mask
    - `ImageChops.offset()` — Shift image with wrapping (we do this with np.roll)
    - `ImageChops.lighter()` / `darker()` — Max/min per-pixel compositing

16. **`ImageEnhance` module**
    - `ImageEnhance.Color()` — Saturation adjustment (clean implementation)
    - `ImageEnhance.Contrast()` — Contrast adjustment
    - `ImageEnhance.Brightness()` — Brightness adjustment
    - `ImageEnhance.Sharpness()` — Sharpness with float control
    All return enhanced images with a float factor (0.0 = minimum, 1.0 = original, 2.0 = 2x). Smoother and more predictable than our manual implementations.

17. **`ImageOps` module**
    - `ImageOps.autocontrast()` — Auto-stretch histogram to full range
    - `ImageOps.equalize()` — Histogram equalization
    - `ImageOps.posterize()` — Reduce bits per channel (cleaner than our manual version)
    - `ImageOps.solarize()` — Invert pixels above a threshold (Man Ray / Sabattier effect)
    - `ImageOps.mirror()` — Horizontal flip
    - `ImageOps.flip()` — Vertical flip
    - `ImageOps.invert()` — Full inversion
    - `ImageOps.colorize()` — Map grayscale to a two-color gradient (duotone)
    - `ImageOps.grayscale()` — Convert to grayscale
    - `ImageOps.pad()` — Pad to target size with color
    - `ImageOps.contain()` — Resize to fit within bounds

18. **`ImageMorph` module**
    Morphological operations with custom structuring elements. Dilate, erode, open, close with arbitrary patterns. Creates structured destruction: erode text until it crumbles, dilate edges until they consume the image.

19. **`Image.transform()` with `PERSPECTIVE`, `AFFINE`, `QUAD`, `MESH`**
    Geometric transforms beyond simple resize. Perspective warp (3D tilt/rotation), affine (shear/rotate/scale), quad mapping (pin four corners to new positions), mesh (grid-based warp).

20. **`Image.split()` / `Image.merge()`**
    Split into individual R, G, B channels and merge back. Could simplify channel shift code and enable per-channel filter application.

21. **`img.point()` — Per-Pixel Lookup Table**
    Applies a 256-entry lookup table to every pixel. Extremely fast for tone curves, gamma correction, solarization, thresholding. Faster than NumPy for simple transfer functions.

22. **`Image.quantize()`**
    Color quantization to a limited palette. Create GIF-like aesthetic with N colors, with dithering options.

23. **Color mode conversions: `img.convert("L")`, `img.convert("HSV")`, `img.convert("LAB")`, `img.convert("CMYK")`**
    We primarily work in RGB. LAB color space separates lightness from color, enabling effects that modify only luminance or only chrominance. CMYK enables print-style color separation. HSV via PIL is an alternative to cv2.

### New Effect Ideas from Pillow:

- **Solarize:** `ImageOps.solarize(img, threshold=128)` -- Partially inverts the image. Pixels above the threshold are inverted, below are left alone. Creates psychedelic, Warhol-esque color shifts. One-liner to implement.
- **Duotone:** `ImageOps.colorize(grayscale, black_color, white_color)` -- Maps shadows and highlights to two chosen colors. Classic design look: navy/gold, magenta/cyan, etc.
- **Emboss:** `img.filter(ImageFilter.EMBOSS)` -- Instant raised/carved texture. Chain with color effects for metallic or stone looks.
- **Median Watercolor:** `img.filter(ImageFilter.MedianFilter(size=11))` -- Large median filter produces a smooth, painted look. Edges stay sharp while flat areas become uniform.
- **Mode Posterize:** `img.filter(ImageFilter.ModeFilter(size=7))` -- Hard-edged posterization that looks like screen printing or risograph.
- **Morphological Glow:** Dilate the frame (MaxFilter), subtract the original, and overlay the result as a bloom layer. Produces organic light-bleed from bright areas.
- **Perspective Tilt:** `Image.transform(size, PERSPECTIVE, coefficients)` -- Fake 3D perspective on a flat frame. Make it look like a screen photographed from an angle.
- **Glitch Text Overlay:** `ImageDraw.Draw(img).text()` with deliberately corrupted/layered text. Timestamps, error messages, system text as overlay elements.
- **Blend Modes:** `ImageChops.multiply()`, `screen()`, `difference()` between the original frame and a procedural texture (noise, gradient, pattern). Standard Photoshop-style blend modes.
- **Auto Levels:** `ImageOps.autocontrast(img, cutoff=2)` -- One-line auto-contrast that clips 2% of highlights and shadows. Instant professional color correction.
- **Color Quantize:** `img.quantize(colors=8)` -- Reduce to 8 colors with dithering. Creates a retro, limited-palette game aesthetic.
- **Mesh Warp:** `Image.transform(size, MESH, ...)` -- Grid-based distortion where each cell can be independently warped. Like bending a printed photo.

---

## OpenCV (cv2)

### Currently Used For:
- `cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)` — RGB to HSV color space conversion
- `cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)` — HSV to RGB color space conversion
- Used **only** in `effects/color.py` for `hue_shift` and `saturation_warp`

### Untapped Capabilities:

1. **`cv2.cvtColor()` with other color spaces**
   - `cv2.COLOR_RGB2LAB` / `cv2.COLOR_LAB2RGB` — CIE LAB (perceptually uniform). L = lightness, A = green-red, B = blue-yellow. Manipulate lightness without affecting color, or shift chrominance without affecting brightness.
   - `cv2.COLOR_RGB2YCrCb` / `cv2.COLOR_YCrCb2RGB` — YCbCr (broadcast color space). Used in JPEG/MPEG compression. Separating luma from chroma enables targeted luma noise, chroma smear (VHS-accurate), and compression artifact simulation.
   - `cv2.COLOR_RGB2HLS` / `cv2.COLOR_HLS2RGB` — HLS (Hue, Lightness, Saturation). Similar to HSV but separates lightness differently. Some color effects look better in HLS.
   - `cv2.COLOR_RGB2XYZ` — CIE XYZ (device-independent). Intermediate for color-accurate transforms.
   - `cv2.COLOR_RGB2LUV` — CIE LUV (perceptually uniform, different from LAB). Better for chrominance difference calculations.

2. **`cv2.GaussianBlur()`**
   True Gaussian blur with controllable sigma. More control than Pillow's version.

3. **`cv2.bilateralFilter()`**
   Edge-preserving blur. Smooths flat areas while keeping edges sharp. The basis of "beauty mode" in phone cameras. Creates a painted, editorial look.

4. **`cv2.Sobel()` / `cv2.Scharr()` / `cv2.Laplacian()`**
   Professional edge detection operators. Scharr is more accurate than Sobel. Laplacian detects edges in all directions simultaneously. Would replace our manual Sobel.

5. **`cv2.Canny()`**
   Industry-standard edge detection with hysteresis thresholding. Produces clean, thin, connected edge lines. Much cleaner than our current Sobel approach.

6. **`cv2.adaptiveThreshold()`**
   Threshold that adapts to local brightness. Creates comic-book or woodcut style with clean separation between ink and paper, even with uneven lighting.

7. **`cv2.morphologyEx()`**
   Morphological operations: ERODE, DILATE, OPEN, CLOSE, GRADIENT, TOPHAT, BLACKHAT with custom structuring elements. Morphological gradient = edge of objects. Top-hat = small bright details on dark background.

8. **`cv2.getStructuringElement()`**
   Create rectangular, elliptical, or cross-shaped structuring elements for morphology. Different shapes produce different visual results.

9. **`cv2.remap()`**
   Arbitrary pixel remapping using lookup maps. The fundamental building block for ANY geometric distortion: fisheye, barrel, pincushion, swirl, ripple, kaleidoscope, glitch displacement. Faster than Python loops.

10. **`cv2.warpAffine()` / `cv2.warpPerspective()`**
    Hardware-accelerated affine and perspective transforms. Rotation, shearing, 3D perspective tilt, zoom. Much faster than PIL's transform.

11. **`cv2.getRotationMatrix2D()` / `cv2.getPerspectiveTransform()`**
    Build transform matrices for rotation around any point, or four-point perspective mapping.

12. **`cv2.calcHist()` / `cv2.equalizeHist()` / `cv2.createCLAHE()`**
    - `calcHist()` — Compute histograms per channel
    - `equalizeHist()` — Global histogram equalization
    - `createCLAHE()` — **Contrast Limited Adaptive Histogram Equalization**. Local contrast enhancement that prevents over-amplification. Medical imaging technique that looks incredible on video: brings out detail in shadows and highlights without blowing out.

13. **`cv2.applyColorMap()`**
    Apply false-color maps (COLORMAP_JET, COLORMAP_HOT, COLORMAP_BONE, COLORMAP_INFERNO, etc.) to grayscale images. Instant thermal vision, scientific visualization, or artistic false color.

14. **`cv2.LUT()`**
    Apply a 256-entry lookup table to the entire image. Extremely fast for tone curves, film emulation, and color grading.

15. **`cv2.dft()` / `cv2.idft()`**
    OpenCV's FFT implementation. Can be faster than NumPy's for large images. Same frequency-domain manipulation possibilities.

16. **`cv2.matchTemplate()`**
    Find instances of a pattern within the image. Could enable "targeted glitch" -- find faces or specific objects and apply effects only there.

17. **`cv2.kmeans()`**
    K-means color clustering. Reduce the image to K dominant colors. Creates clean, graphic-design posterization based on actual color clusters rather than arbitrary thresholds.

18. **`cv2.stylization()` / `cv2.edgePreservingFilter()` / `cv2.detailEnhance()` / `cv2.pencilSketch()`**
    Non-photorealistic rendering built into OpenCV:
    - `stylization()` — Painting effect
    - `pencilSketch()` — Returns both grayscale and color pencil sketch
    - `detailEnhance()` — HDR-like detail enhancement
    - `edgePreservingFilter()` — Smoothing with edge preservation (two modes: recursive, normalized convolution)

19. **`cv2.pyrDown()` / `cv2.pyrUp()` — Image Pyramids**
    Multi-scale processing. Build a Laplacian pyramid, modify different scales independently, reconstruct. Enables frequency-selective effects: blur only large features, sharpen only fine detail.

20. **`cv2.connectedComponents()`**
    Label connected regions in a binary image. After edge detection, identify separate objects. Enable per-object effects: glitch one detected region differently from another.

### New Effect Ideas from OpenCV:

- **CLAHE Reveal:** Apply CLAHE to bring out hidden detail in shadows and highlights. Like turning on night vision for underexposed footage. One function call.
- **Bilateral Skin Smooth:** `cv2.bilateralFilter()` produces phone-camera beauty mode. Smooth skin, keep edges. Chain with slight saturation boost for "Instagram filter" look.
- **False Color / Thermal:** Convert to grayscale, apply `cv2.applyColorMap(gray, cv2.COLORMAP_INFERNO)`. Instant thermal vision, much cleaner than our manual posterize+hueshift approach.
- **Pencil Sketch:** `cv2.pencilSketch(frame)` returns a pencil drawing. One line. Chain with edge colorization for "animated comic" look.
- **Canny Neon:** Replace our manual Sobel with `cv2.Canny()` for cleaner edge lines, then colorize. Professional-quality neon edge effect.
- **Fisheye/Barrel Distortion:** Use `cv2.remap()` with polar coordinate lookup tables. Create fisheye, barrel, and pincushion lens distortion.
- **Swirl Distortion:** Use `cv2.remap()` with angle-offset lookup tables centered on a point. Amount of swirl increases with distance from center.
- **K-Means Color Crush:** `cv2.kmeans()` to find the 4-8 dominant colors in the frame, then snap all pixels to their nearest cluster. Clean, graphic posterization.
- **Laplacian Pyramid Glitch:** Build a Laplacian pyramid, corrupt one level (add noise, shift, sort), reconstruct. The corruption appears only at that spatial frequency. Subtle, alien.
- **Adaptive Threshold Woodcut:** Convert to grayscale, apply `cv2.adaptiveThreshold()`. Creates a woodcut/linocut print effect with clean black/white separation that adapts to local brightness.
- **Morphological Edge Glow:** Apply `cv2.morphologyEx(MORPH_GRADIENT)` to extract object boundaries, colorize them, and overlay on the original. Glowing structural edges.

---

## FFmpeg (subprocess)

### Currently Used For:
- `ffprobe -show_format -show_streams` — Video metadata (resolution, fps, duration, audio)
- `ffmpeg -i input -vsync 0 frame_%06d.png` — Frame extraction to PNG sequence
- `ffmpeg -i input -ss timestamp -frames:v 1 output.png` — Single frame extraction
- `ffmpeg -framerate fps -i frames -c:v libx264/prores_ks output` — Frame reassembly to video
- `-c:a aac -b:a 192k` — Audio re-encoding
- `-map 0:v -map 1:a?` — Stream mapping
- `-vf scale=W:H` — Resolution scaling
- `-loop 1 -t duration` — Image to video conversion
- GIF export with `palettegen` / `paletteuse` split filter
- ProRes, VP9/WebM, PNG sequence export
- Various codec presets (CRF, preset, profile, pixel format)

### Untapped Capabilities:

1. **`-filter_complex` — Complex Filter Graphs**
   FFmpeg's filter graph system is a full visual effects pipeline. You can chain, split, and merge streams with arbitrary filter nodes. This is where the real power lies -- everything below is accessed through this.

2. **`blend` filter — Frame Blending / Blend Modes**
   `blend=all_mode=multiply` (or screen, overlay, darken, lighten, difference, addition, subtract, phoenix, negation, softlight, hardlight, and 20+ more). Apply Photoshop blend modes at the video level, during encoding. No frame-by-frame Python needed.

3. **`overlay` filter — Compositing**
   Layer one video on top of another with position control. Enables: picture-in-picture, watermarks, animated overlays, split-screen.

4. **`chromakey` / `colorkey` filter — Chroma Key (Green Screen)**
   Remove a specific color and composite onto another source. Not just for green screen -- could "key out" any color for creative effects.

5. **`geq` filter — Generic Equation Filter**
   Write pixel-level math expressions: `geq=r='128+100*sin(X/10)':g='p(X,Y)':b='p(X,Y)'`. Any mathematical function applied per-pixel in the FFmpeg pipeline. Incredibly powerful for procedural effects.

6. **`lut3d` filter — 3D LUT Application**
   Apply industry-standard .cube LUT files for color grading. Hundreds of free film emulation LUTs available online (Kodak, Fuji, etc.). `lut3d=file=portra400.cube`.

7. **`colorbalance` / `colorchannelmixer` / `hue` / `eq` filters**
   - `colorbalance` — Adjust shadows/midtones/highlights independently (lift/gamma/gain)
   - `colorchannelmixer` — Full RGB matrix transform (color grading)
   - `hue` — Hue, saturation, brightness adjustment
   - `eq` — Brightness, contrast, saturation, gamma per channel

8. **`curves` filter**
   Apply tone curves like Photoshop curves. Specify control points for R, G, B, and master channels. `curves=red='0/0 0.5/0.7 1/1':green=...`

9. **`normalize` / `histeq` filters**
   - `normalize` — Auto-levels (like autocontrast)
   - `histeq` — Histogram equalization within FFmpeg

10. **`boxblur` / `gblur` / `smartblur` / `unsharp` filters**
    - `boxblur` — Box blur with per-axis radius
    - `gblur` — Gaussian blur with sigma control
    - `smartblur` — Adaptive blur that smooths flat areas, preserves edges
    - `unsharp` — Professional unsharp mask (luma size, chroma size, amounts)

11. **`noise` filter**
    `noise=alls=50:allf=t` — Add noise with type control (uniform, temporal, averaged). Temporal noise varies per frame (realistic film grain). FFmpeg-level noise is applied during encode, not in Python -- much faster.

12. **`edgedetect` filter**
    Edge detection at the FFmpeg level. `edgedetect=mode=colormix:low=0.1:high=0.4` for colored edges.

13. **`lagfun` filter**
    Frame lag/echo effect. Each pixel slowly decays to the current value, creating ghost trails of motion. "Persistence of vision" effect -- objects leave phosphor-like trails. Very expensive to do in Python but trivial in FFmpeg.

14. **`tmix` filter — Temporal Mixing**
    Mix multiple consecutive frames together. `tmix=frames=5:weights='1 1 1 1 1'` averages 5 frames (motion blur). Different weights create echo/trail effects.

15. **`tblend` filter — Temporal Blending**
    Blend the current frame with the previous frame using blend modes. `tblend=all_mode=difference` shows only what moved between frames (motion detection).

16. **`random` filter — Frame Reordering**
    Randomly shuffle frame order within a buffer. Creates temporal glitch -- the video stutters and jumps.

17. **`reverse` filter — Reverse Video**
    Reverse frame order. Combine with temporal blend for "rewind" effects.

18. **`setpts` / `asetpts` — Timestamp Manipulation**
    Speed up, slow down, or create variable-speed effects. `setpts=0.5*PTS` = 2x speed. `setpts='PTS+random(0)*0.01'` = micro-stutter.

19. **`tile` filter — Frame Grid**
    Arrange multiple frames in a grid. `tile=4x4` creates a contact sheet. Could show 16 frames at once for overview.

20. **`datascope` / `oscilloscope` / `waveform` / `vectorscope` filters**
    Technical analysis overlays:
    - `datascope` — Show pixel values as numbers
    - `oscilloscope` — Audio-style oscilloscope overlay
    - `waveform` — Luma/chroma waveform monitor
    - `vectorscope` — Color vector display
    These are both diagnostic and visually interesting as overlay effects.

21. **`minterpolate` filter — Frame Interpolation**
    Generate intermediate frames for slow motion. Uses motion estimation to synthesize new frames. Create smooth slow-motion from standard footage.

22. **`deshake` / `vidstabdetect` + `vidstabtransform`**
    Video stabilization. Or: use the inverse of stabilization to ADD camera shake.

23. **`drawtext` filter**
    Render text with TTF fonts, variable position, timecodes, frame numbers. `drawtext=text='%{n}':fontsize=24:fontcolor=white` draws the frame number.

24. **`showinfo` / `showpalette` / `showspectrum` / `showwaves`**
    Visualization filters. `showspectrum` creates beautiful audio-reactive spectral displays from the audio track.

25. **`zoompan` filter**
    Ken Burns effect -- slow zoom and pan across a static image. `zoompan=z='zoom+0.001':d=125:s=1920x1080`.

26. **`xfade` filter**
    Crossfade transitions between two videos. 30+ transition types: fade, wipeleft, circleopen, dissolve, pixelize, etc.

### New Effect Ideas from FFmpeg:

- **Temporal Ghost Trail:** `lagfun=decay=0.95` -- Moving objects leave phosphor-glow trails that slowly fade. Cannot be done frame-by-frame in Python (needs temporal state). Haunting, ethereal.
- **Motion Delta:** `tblend=all_mode=difference` -- Shows only what changed between frames. Static background disappears; only motion is visible. Surveillance/detection aesthetic.
- **Frame Stutter:** `random=frames=10` -- Randomly reorder frames within a 10-frame buffer. Creates temporal glitch without affecting individual frames.
- **Film LUT Grading:** `lut3d=file=film_stock.cube` -- Apply real film stock LUTs. Portra 400, Ektachrome, Cinestill 800T. Download free .cube files, apply in the FFmpeg pipeline.
- **Equation Generator:** `geq=r='128+127*sin((X*X+Y*Y)/1000)':g=...` -- Generate procedural patterns (Moire, interference, plasma) directly in FFmpeg. Use as texture overlays.
- **Oscilloscope Overlay:** `oscilloscope=x=0.5:y=0.5:s=1:c=1` -- Overlay an oscilloscope visualization on the video. Technical/aesthetic hybrid.
- **Speed Ramping:** `setpts` with variable expressions -- Smoothly accelerate and decelerate. Music video staple.
- **Draw Frame Counter:** `drawtext=text='%{n}':x=10:y=10:fontsize=20:fontcolor=green@0.5` -- Technical overlay, frame counter, timecode burned into the video.

---

## Gradio

### Currently Used For:
- `gr.Blocks()` — Application container with custom theme
- `gr.Video()`, `gr.Image()`, `gr.Slider()`, `gr.Dropdown()`, `gr.Radio()`, `gr.Button()`, `gr.Markdown()`, `gr.Textbox()` — UI components
- `gr.Row()`, `gr.Column()` — Layout
- `gr.Progress()` — Progress bar during rendering
- Event wiring (`.click()`, `.change()`)

### Untapped Capabilities:

1. **`gr.Gallery()`** — Display multiple images in a grid. Perfect for showing before/after comparisons, sample frames, or preset previews.

2. **`gr.ColorPicker()`** — Native color selection. Could replace manual RGB tuple entry for scanline color, overlay color, duotone colors.

3. **`gr.Tab()` / `gr.Accordion()`** — Organize UI into tabbed sections or collapsible groups. Separate "Effects", "Color Grading", "Export" into tabs.

4. **`gr.State()`** — Persistent state across interactions. Track effect history, undo stack, A/B comparison state.

5. **`gr.Audio()`** — Audio input/output. Could enable audio-reactive effects: analyze the audio track and map amplitude/frequency to effect parameters.

6. **`gr.Plot()`** — Display matplotlib plots. Show histograms, waveforms, vectorscopes inline.

7. **`gr.HTML()`** — Embed custom HTML. Could render interactive canvases, spectrum analyzers, or custom visualizations.

8. **`gr.File()`** — Generic file upload/download. Enable LUT file upload, preset import/export.

9. **`gr.Examples()`** — Pre-built example inputs. One-click demo with included sample videos.

10. **Live preview via `gr.Interface(live=True)`** — Real-time parameter updates without clicking "Preview". As sliders move, the preview updates.

### New Feature Ideas from Gradio:

- **Audio-Reactive Mode:** Use `gr.Audio()` to upload a track, analyze its spectrum, and drive effect parameters per-frame. Bass hits trigger displacement, treble drives chromatic aberration.
- **Live Preview:** `live=True` with debouncing -- sliders update the preview in real-time as they move. No more click-to-preview.
- **Before/After Gallery:** `gr.Gallery()` showing the original frame alongside each effect in the chain. See the transformation at each step.
- **Histogram Display:** `gr.Plot()` showing the RGB histogram of the processed frame. Real-time feedback on color distribution.

---

## FastAPI + Pydantic

### Currently Used For:
- `FastAPI()`, route decorators (`@app.get`, `@app.post`), `UploadFile`, `File`, `HTTPException` — HTTP API
- `StaticFiles`, `FileResponse`, `JSONResponse` — Static file serving and responses
- `BaseModel` — Request/response schemas (`EffectChain`, `RenderRequest`, `PresetSave`, `ExportSettings`)
- `Field()`, `model_validator` — Validation and documentation
- `Enum` — Typed enumerations for export options

### Untapped Capabilities:

1. **WebSocket support (`@app.websocket`)**
   Real-time bidirectional communication. Enable live preview streaming: as the user adjusts a slider, the server processes and streams preview frames back instantly over WebSocket. No HTTP round-trip overhead.

2. **Background Tasks (`BackgroundTasks`)**
   Offload rendering to a background task and return immediately. The client polls for completion. Prevents HTTP timeout for long renders.

3. **Streaming Response (`StreamingResponse`)**
   Stream processed video data directly to the client without writing to disk first. Useful for lo-res previews.

4. **Dependency Injection**
   Use FastAPI's dependency injection for shared resources (video state, effect registry). Cleaner than the current global `_state` dict.

5. **Event handlers (`@app.on_event("startup")`, `@app.on_event("shutdown")`)**
   Proper lifecycle management. Clean up temp files on shutdown, initialize resources on startup.

### New Feature Ideas:

- **WebSocket Live Preview:** Stream JPEG frames over WebSocket as sliders change. Sub-100ms latency preview loop.
- **Async Render Queue:** Submit renders via API, get a job ID, poll for status. Enable batch rendering of multiple presets.

---

## Python Standard Library

### Modules Currently Used:
`sys`, `os`, `argparse`, `ast`, `shutil`, `subprocess`, `tempfile`, `base64`, `json`, `re`, `time`, `random`, `pathlib`, `io.BytesIO`, `datetime`, `atexit`, `struct`, `inspect`, `enum`, `typing`

### Untapped Capabilities:

1. **`colorsys` module**
   Color space conversions (RGB <-> HLS, HSV, YIQ) in pure Python. Lighter than importing cv2 just for color conversion. YIQ (NTSC color space) separates luminance from chrominance differently than HSV.

2. **`math.sin/cos/tan` with `itertools`**
   Generate procedural patterns: Lissajous curves, spirals, Moiree interference patterns as effect masks.

3. **`struct` module (already imported in tests)**
   Pack/unpack binary data. Could be used to intentionally corrupt specific bytes in image data for authentic data-corruption glitch effects.

4. **`hashlib` / `zlib`**
   - `hashlib` — Generate deterministic seeds from filenames for reproducible "random" effects
   - `zlib.compress/decompress` — Intentionally corrupt compressed data for glitch art. Compress image bytes, flip bits, decompress -- the decompression artifacts ARE the effect.

5. **`functools.lru_cache`**
   Cache expensive computations like FFT results, lookup tables, or kernel matrices. Speed up repeated previews with same parameters.

6. **`multiprocessing` / `concurrent.futures`**
   Parallelize frame processing. Each frame is independent, so a ProcessPoolExecutor could use all CPU cores for rendering.

7. **`wave` module**
   Read WAV audio files to extract amplitude data for audio-reactive effects.

---

## Interaction Effects (Cross-Package Combos)

### 1. FFT Glitch Painting
- **Packages:** NumPy (FFT) + Pillow (blend modes) + OpenCV (color spaces)
- **Technique:** Convert frame to LAB color space (cv2). FFT the L channel (np.fft.fft2). Randomize phase spectrum while keeping magnitude. Inverse FFT. The result is a frame that has the same frequency content (textures, contrast patterns) but completely scrambled spatial arrangement. Blend with original using ImageChops.screen() for a double-exposure ghost effect.
- **Result:** Ethereal, dream-like frames where the image's own texture haunts itself. Like looking at a memory through frosted glass that preserves the feeling but not the details.

### 2. Audio-Driven Frequency Destruction
- **Packages:** FFmpeg (audio extraction) + NumPy (FFT + audio analysis) + OpenCV (remap)
- **Technique:** Extract audio waveform from video via FFmpeg. Compute FFT of audio in short windows. Map bass energy to low-frequency image manipulation (large-scale displacement), mids to mid-frequency (texture disruption), highs to high-frequency (edge corruption). Apply via cv2.remap() with procedurally generated displacement maps scaled by audio energy.
- **Result:** The video literally dances to its own soundtrack. Bass drops cause the image to heave and warp. Cymbal hits shatter edges. The visual destruction is synchronized to the audio at a frequency-domain level, not just amplitude.

### 3. SVD Temporal Decay
- **Packages:** NumPy (SVD) + FFmpeg (temporal mixing)
- **Technique:** For each frame, compute SVD (np.linalg.svd). Keep progressively fewer singular values as the video progresses (start with 50, end with 3). Render the degrading frames. Use FFmpeg's tmix to blend consecutive frames, creating motion trails as the image dissolves.
- **Result:** The video starts sharp and progressively melts into abstract color blobs, with ghostly trails from movement. Like a photograph left in the sun for years, compressed into seconds.

### 4. Morphological Neon Skeleton
- **Packages:** OpenCV (morphology + Canny) + Pillow (ImageChops) + NumPy (color manipulation)
- **Technique:** Apply cv2.Canny() for clean edges. Apply morphological operations: dilate edges, then subtract original edges to get only the "glow" halo. Use cv2.applyColorMap() on the edge magnitude for false-color edges. Composite onto darkened original using ImageChops.screen(). Apply chromatic aberration (NumPy np.roll per channel) to the edge layer only.
- **Result:** Objects outlined in thick, chromatic-shifted neon glow on a dark background. Think Tron, but organic and imperfect.

### 5. Histogram-Matched Time Travel
- **Packages:** NumPy (histogram) + OpenCV (calcHist, LUT) + FFmpeg (frame extraction)
- **Technique:** Extract two frames from different points in the video. Compute the cumulative histogram of the "source" frame and the "target" frame. Build a mapping LUT that transforms the source histogram to match the target. Apply via cv2.LUT(). The source frame inherits the color distribution and mood of the target frame while keeping its own content.
- **Result:** A frame from the beginning of the video colored as if it were the end. Day scenes given the palette of night scenes. Indoor lighting projected onto outdoor footage. Temporal color transfer.

### 6. Procedural Mask Compositing
- **Packages:** NumPy (meshgrid + math) + Pillow (ImageChops.composite) + OpenCV (bilateral filter)
- **Technique:** Generate a procedural mask using np.meshgrid: radial gradient, Perlin noise, Voronoi cells, concentric rings, or spiral. Use this mask to composite between the original frame and a heavily processed version (bilateral-filtered, false-colored, or SVD-crushed). Different mask generators create different spatial patterns of destruction.
- **Result:** Effects that are not uniform across the frame. Glitch radiates from the center. Destruction follows a spiral path. Clean areas and destroyed areas alternate in organic, mathematically generated patterns.

### 7. Frequency-Band Selective Color
- **Packages:** NumPy (FFT) + OpenCV (color space conversion) + Pillow (ImageEnhance)
- **Technique:** Convert to LAB. FFT the L channel. Create bandpass filters (rings in frequency space). Isolate low frequencies (overall shape), mid frequencies (texture), and high frequencies (fine detail) into separate layers. Apply different color treatments to each: warm tones to low-freq, cool tones to mid-freq, neon to high-freq. Reconstruct.
- **Result:** Colors that depend on spatial frequency. Large shapes are warm, textures are cool, edges are neon. An impossible color scheme that the brain reads as "wrong but beautiful."

### 8. Convolution Kernel Gallery
- **Packages:** Pillow (ImageFilter.Kernel) + NumPy (kernel generation + math)
- **Technique:** Generate convolution kernels using mathematical functions: Gabor filters (oriented edge detection at specific angles), Gaussian derivatives (detect features at specific scales), Laplacian of Gaussian (blob detection), custom artistic kernels (asymmetric blur, directional emboss at any angle). Apply via ImageFilter.Kernel().
- **Result:** A library of 50+ one-shot texture effects, each defined by a single matrix. Instant emboss at 45 degrees, directional motion blur at 120 degrees, oriented edge detection for vertical-only or horizontal-only edges.

### 9. Pixel Sort + FFT Hybrid
- **Packages:** NumPy (FFT + sort + meshgrid)
- **Technique:** FFT the frame. In the frequency domain, sort the magnitude values along rows or columns (pixel sort in frequency space, not spatial space). Inverse FFT. The result is an image whose frequency content has been reordered rather than its pixels.
- **Result:** Unlike spatial pixel sort (which creates visible streaks), frequency-sort creates subtle, eerie redistributions of texture and contrast. Sharp areas might become soft while soft areas become sharp. Textures migrate across the image.

### 10. Datamosh Simulation
- **Packages:** NumPy (block operations) + Pillow (resize) + FFmpeg (blend)
- **Technique:** Divide the frame into macroblocks (8x8 or 16x16). For each block, instead of showing the current frame's content, show the same block from a different frame (previous, random, or offset). Use NumPy to copy blocks between frames. Some blocks stay current, others are "stuck" on old data. Apply motion-compensated blending via FFmpeg's tblend for inter-frame smearing.
- **Result:** Authentic datamosh look (I-frame deletion simulation) without actually corrupting the video bitstream. Controllable, seedable, reversible.

### 11. Color Decorrelation Stretch
- **Packages:** NumPy (covariance matrix + eigendecomposition) + OpenCV (color conversion)
- **Technique:** Compute the covariance matrix of all pixel RGB values. Find eigenvalues and eigenvectors. Project all pixels into the principal component space. Stretch each component independently to fill the full range. Project back to RGB. This amplifies subtle color differences that are invisible to the human eye.
- **Result:** Near-monochrome footage becomes vivid and alien. Subtle color variations in skin tones, fabrics, or landscapes are amplified to dramatic, false-color extremes. Used in satellite imagery analysis -- never seen in glitch art.

### 12. Bilateral + Quantize = Oil Painting
- **Packages:** OpenCV (bilateralFilter) + cv2.kmeans or numpy (quantize)
- **Technique:** Apply aggressive bilateral filtering (large d, high sigmaColor, high sigmaSpace) to smooth all flat areas while keeping edges. Then k-means quantize to 8-16 colors. The bilateral smoothing creates uniform color fields; the quantization snaps them to a limited palette.
- **Result:** Photorealistic oil painting effect. Brush strokes follow edges, color areas are flat and confident. Different from posterize because bilateral preserves edge geometry.

### 13. Perlin Displacement
- **Packages:** NumPy (meshgrid + noise generation) + OpenCV (remap)
- **Technique:** Generate 2D Perlin noise (or simplex noise) using NumPy. Use the noise field as a displacement map in cv2.remap(). Scale the noise amplitude and frequency to control the effect. Animate the noise seed per frame for flowing distortion.
- **Result:** Organic, fluid warping that looks like heat shimmer, underwater caustics, or reality bending. Unlike our sine-wave distortion, Perlin displacement is non-repeating and natural.

### 14. Split-Frequency Processing
- **Packages:** Pillow (GaussianBlur) + NumPy (arithmetic) + OpenCV (bilateral)
- **Technique:** Blur the frame heavily (low-frequency layer). Subtract the blur from the original to get the high-frequency detail layer. Process each independently: apply color effects to the low-freq layer, apply texture/edge effects to the high-freq layer. Recombine. This is the "frequency separation" technique used in professional photo retouching.
- **Result:** Color grading that does not affect texture. Texture effects that do not affect color. Professional-quality separation that lets you, for example, add warm tones to skin without affecting hair and fabric detail, or add noise only to smooth areas.

### 15. Temporal Frame Stacking
- **Packages:** FFmpeg (frame extraction) + NumPy (array stacking + statistics) + Pillow (output)
- **Technique:** Extract N consecutive frames. Stack them into a 4D array (N, H, W, 3). Compute per-pixel statistics across the time axis: mean (motion blur), median (remove moving objects), max (light painting), min (darkest frame), standard deviation (show only areas with motion). The std-dev output is particularly interesting: static areas are black, moving areas glow.
- **Result:** Long-exposure photography effects from standard video. Remove tourists from a scene (median). Create light trails (max). Reveal only what moves (std-dev). All from existing footage, no special camera needed.

---

## Summary: Priority-Ranked Ideas

The following ranks all new effect ideas by implementation difficulty (tokens/time) versus visual impact, grouped into tiers.

### Tier 1 — Quick Wins (1-10 lines of new code each)

| # | Effect | Package | Why |
|---|--------|---------|-----|
| 1 | Solarize | Pillow ImageOps | One-liner. Iconic psychedelic look. |
| 2 | Duotone | Pillow ImageOps | One-liner. Instant graphic design aesthetic. |
| 3 | Emboss | Pillow ImageFilter | One-liner. 3D texture effect. |
| 4 | Gaussian Blur | Pillow ImageFilter | Replace box blur option. Perceptually better. |
| 5 | Median Filter | Pillow ImageFilter | Watercolor / noise reduction. One line. |
| 6 | Auto Levels | Pillow ImageOps | One-liner auto-contrast. Professional color correction. |
| 7 | Unsharp Mask | Pillow ImageFilter | Replace multi-pass sharpen. Professional sharpening. |
| 8 | Histogram Equalize | Pillow ImageOps or OpenCV | One-liner. Reveals hidden detail. |
| 9 | False Color Map | OpenCV applyColorMap | One function call. 20+ built-in colormaps. |
| 10 | Pencil Sketch | OpenCV pencilSketch | One function call. Instant drawing effect. |

### Tier 2 — Medium Effort (10-50 lines each)

| # | Effect | Package | Why |
|---|--------|---------|-----|
| 11 | CLAHE Detail Reveal | OpenCV createCLAHE | 3 lines. Adaptive local contrast. Night-vision quality. |
| 12 | Bilateral Smooth | OpenCV bilateralFilter | 1 line. Beauty mode / oil painting base. |
| 13 | Canny Neon Edges | OpenCV Canny | Replace manual Sobel. Cleaner edges. |
| 14 | K-Means Posterize | OpenCV kmeans | ~20 lines. Data-driven color reduction. |
| 15 | Morphological Glow | Pillow MinFilter+MaxFilter or OpenCV | ~15 lines. Organic bloom from edges. |
| 16 | Perspective Warp | Pillow or OpenCV warpPerspective | ~15 lines. Fake 3D tilt. |
| 17 | Vortex/Swirl | OpenCV remap + NumPy meshgrid | ~25 lines. Spiral distortion. |
| 18 | Fisheye Lens | OpenCV remap + NumPy | ~25 lines. Barrel/pincushion distortion. |
| 19 | Radial Gradient Mask | NumPy meshgrid | ~15 lines. Spatial effect fade. |
| 20 | Point LUT Curves | Pillow img.point() or OpenCV LUT | ~20 lines. Film stock emulation. |

### Tier 3 — Significant Features (50-200 lines each)

| # | Effect | Package | Why |
|---|--------|---------|-----|
| 21 | Spectral Glitch (FFT) | NumPy fft2 | ~50 lines. Frequency-domain destruction. Unique. |
| 22 | SVD Rank Crush | NumPy linalg.svd | ~30 lines. Ghostly abstraction. |
| 23 | Perlin Displacement | NumPy + OpenCV remap | ~80 lines. Organic fluid warp. |
| 24 | Oil Painting | OpenCV bilateral + kmeans | ~40 lines. Combo effect. Stunning. |
| 25 | Datamosh Simulation | NumPy block operations | ~80 lines. Most-requested glitch effect. |
| 26 | Split-Frequency | Pillow blur + NumPy | ~40 lines. Professional retouching technique. |
| 27 | Temporal Stacking | FFmpeg + NumPy | ~60 lines. Long-exposure from video. |
| 28 | Blend Modes (library) | Pillow ImageChops | ~30 lines for full set. Core compositing. |
| 29 | Text/Glyph Overlay | Pillow ImageDraw + ImageFont | ~50 lines. Timestamp, glitch text. |
| 30 | Audio-Reactive Driver | FFmpeg audio + NumPy | ~150 lines. Effects synced to music. |

### Tier 4 — Architecture-Level (require pipeline changes)

| # | Feature | Package | Why |
|---|---------|---------|-----|
| 31 | Temporal Effects (lagfun, tblend) | FFmpeg filter_complex | Requires FFmpeg-level pipeline, not frame-by-frame Python. Ghost trails, motion detection. |
| 32 | LUT File Support | FFmpeg lut3d | Requires .cube file upload and management. Instant film emulation. |
| 33 | WebSocket Live Preview | FastAPI WebSocket | Requires frontend changes. Sub-100ms preview loop. |
| 34 | Parallel Frame Rendering | multiprocessing | Requires ProcessPoolExecutor integration. 4-8x render speed. |
| 35 | Laplacian Pyramid Glitch | OpenCV pyrDown/pyrUp + NumPy | Requires multi-scale decomposition pipeline. |

---

*This audit identified 7 packages with a combined 85+ untapped capabilities and 50+ concrete new effect ideas. The Tier 1 quick wins alone would double the effect count with minimal code. The interaction effects represent genuinely novel visual territory that no competing glitch tool offers.*

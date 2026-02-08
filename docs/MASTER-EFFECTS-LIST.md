# Entropic Master Effects List

**Generated:** 2026-02-07
**Skills Used:** `/mad-scientist`, `/creative`, `/glitch-video`, `/audio-production`, `/competitive-analysis`
**Docs Reviewed:** All 17 relevant reference docs (FFmpeg Filters, FFmpeg Codecs, ffmpeg-python, OpenCV Creative, Pillow Glitch, GlitchArt, Glitch Techniques, Datamosh, Librosa, SciPy Signal, PyDub, Audio DSP Creative, MoviePy, Media I/O, Real-Time Video, Real-Time Visual Tools, Glitch Video Creative Projects)
**Related PRDs:** [[ENTROPIC-VISION]], [[ENTROPIC-EFFECTS]], [[ENTROPIC-AUDIO-REACTIVE]], [[ENTROPIC-UI-UX]], [[ENTROPIC-IMPORT-EXPORT]], [[ENTROPIC-SAFETY]]
**Existing Capabilities:** [[LIBRARY-CAPABILITIES.md]] (691 lines, ~/Development/entropic/docs/)

---

## Status Key

| Status | Meaning |
|--------|---------|
| SHIPPED | Already in Entropic v0.2.0 |
| PLANNED | In LIBRARY-CAPABILITIES.md |
| **NEW** | Discovered in this audit |

---

## Currently Shipped (37 Effects)

| # | Effect | Category | Status |
|---|--------|----------|--------|
| 1 | pixelsort | Glitch | SHIPPED |
| 2 | channelshift | Glitch | SHIPPED |
| 3 | displacement | Glitch | SHIPPED |
| 4 | bitcrush | Glitch | SHIPPED |
| 5 | wave | Distortion | SHIPPED |
| 6 | mirror | Distortion | SHIPPED |
| 7 | chromatic | Distortion | SHIPPED |
| 8 | scanlines | Texture | SHIPPED |
| 9 | vhs | Texture | SHIPPED |
| 10 | noise | Texture | SHIPPED |
| 11 | blur | Texture | SHIPPED |
| 12 | sharpen | Texture | SHIPPED |
| 13 | edges | Texture | SHIPPED |
| 14 | posterize | Texture | SHIPPED |
| 15 | hueshift | Color | SHIPPED |
| 16 | contrast | Color | SHIPPED |
| 17 | saturation | Color | SHIPPED |
| 18 | exposure | Color | SHIPPED |
| 19 | invert | Color | SHIPPED |
| 20 | temperature | Color | SHIPPED |
| 21 | stutter | Temporal | SHIPPED |
| 22 | dropout | Temporal | SHIPPED |
| 23 | timestretch | Temporal | SHIPPED |
| 24 | feedback | Temporal | SHIPPED |
| 25 | tapestop | Temporal | SHIPPED |
| 26 | tremolo | Temporal | SHIPPED |
| 27 | delay | Temporal | SHIPPED |
| 28 | decimator | Temporal | SHIPPED |
| 29 | samplehold | Temporal | SHIPPED |
| 30 | ringmod | Modulation | SHIPPED |
| 31 | gate | Modulation | SHIPPED |
| 32 | solarize | Enhance | SHIPPED |
| 33 | duotone | Enhance | SHIPPED |
| 34 | emboss | Enhance | SHIPPED |
| 35 | autolevels | Enhance | SHIPPED |
| 36 | median | Enhance | SHIPPED |
| 37 | falsecolor | Enhance | SHIPPED |

---

## MASTER LIST: New Effects & Capabilities

### Category A: Pixel Corruption & Data Bending (28 effects)

| # | Effect Name | Source | Description | Complexity |
|---|-------------|--------|-------------|------------|
| A1 | JPEG Scan Corrupt | GlitchArt, Glitch Techniques | Save frame as JPEG in memory, corrupt random bytes in scan data (after SOS marker), reload. Produces authentic JPEG macroblocking artifacts. | Easy |
| A2 | BMP Byte Scramble | Pillow Glitch | Save frame as BMP, corrupt raw pixel bytes after 54-byte header. Produces horizontal streak artifacts distinct from JPEG corruption. | Easy |
| A3 | Byte Insertion | Glitch Techniques | Insert random bytes into serialized frame data, causing cascading row misalignment. Diagonal shift artifact unique to insertion. | Easy |
| A4 | Hex Pattern Replace | Glitch Techniques | Search for specific byte patterns in compressed frame data and replace with different values. Produces structured, repeating corruption. | Medium |
| A5 | Iterative Re-encode Decay | GlitchArt, Codecs | Re-encode frame through multiple rounds of lossy JPEG/H.264 compression. Each pass amplifies artifacts. Simulates VHS generation loss. | Easy |
| A6 | PNG Round-Trip Corrupt | GlitchArt | Convert PNG to JPEG, corrupt JPEG data, convert back. Injects block-structure artifacts into lossless format. | Easy |
| A7 | WebP Double-Codec | GlitchArt | Chain multiple codec conversions (JPEG→WebP→back) to stack compression artifacts from different algorithms. | Easy |
| A8 | CRF Degradation | FFmpeg Codecs | Re-encode at CRF 45-51 with ultrafast preset. Heavy macroblocking, smearing, quantization noise as an effect. | Easy |
| A9 | Low-Bitrate Crush | FFmpeg Codecs | Encode MPEG-4 at 200kbps to force huge visible block artifacts, color banding, mosquito noise. | Easy |
| A10 | Bitstream Noise Inject | Datamosh | Use FFmpeg `-bsf:v noise` to inject bit errors into compressed stream. Real decoder artifacts: block flashes, partial frames. | Easy |
| A11 | Audacity Databend | Glitch Techniques | Export frame as raw YUV bytes, apply audio DSP (echo, reverb, phaser) to byte array, reinterpret as pixels. Cross-scanline smearing. | Medium |
| A12 | MJPEG Frame Isolate | FFmpeg Codecs | Encode to MJPEG where each frame is independent, then selectively corrupt individual frames without cascade. | Medium |
| A13 | Shufflepixels | FFmpeg Filters | Randomly rearrange pixels or pixel blocks within frame. Block mode for mosaic-scramble, fine mode for digital static. | Easy |
| A14 | Swaprect | FFmpeg Filters | Swap two rectangular regions within a frame. Animate positions per-frame for haunted copy-paste displacement. | Medium |
| A15 | Pattern Injection | Pillow Glitch | Find repeating byte patterns in JPEG-encoded frames and replace with signature pattern. Consistent, recognizable corruption motifs. | Medium |
| A16 | Seed-Based Glitch Keyframes | GlitchArt | Use PRNG seeds to make corruption reproducible. Design exact glitch patterns at key frames. Choreograph corruption with music. | Easy |
| A17 | Corruption Ramp | GlitchArt | Gradually increase byte corruption intensity over video duration. Narrative arc of degradation from clean to destroyed. | Easy |
| A18 | Stutter Corrupt | GlitchArt | Alternate between clean and heavily corrupted frames at varying intervals. Jittery unstable broadcast signal. | Easy |
| A19 | Amplified Corruption | GlitchArt + Pillow | Run byte corruption then boost contrast to 2x. Makes subtle JPEG artifacts dramatically visible as bold color blocks. | Easy |
| A20 | Corrupt + Detect | GlitchArt + OpenCV | Run JPEG corruption, then apply Canny edge detection. Corruption creates false edges and phantom contours. Ghostly x-ray quality. | Medium |
| A21 | Parallel Corruption Pipeline | GlitchArt Async | Process multiple frames concurrently using async glitching for significantly faster video processing. | Medium |
| A22 | I-Frame-Only Freeze | FFmpeg Codecs | Force every frame to be a keyframe (`-g 1`). Freeze a moshed result into stable frames. | Easy |
| A23 | Tune Grain Preservation | FFmpeg Codecs | Use `-tune grain` on exports to preserve noise/artifact detail that encoders normally smooth away. | Easy |
| A24 | FFV1 Lossless Pipeline | FFmpeg Codecs | Use FFV1 as intermediate format between processing stages. Zero quality loss between pipeline steps. | Easy |
| A25 | HuffYUV Byte Access | FFmpeg Codecs | Export to HuffYUV AVI for simple container structure, enabling easy byte-level frame manipulation. | Medium |
| A26 | rgbashift | FFmpeg Filters | Shift individual RGBA channels by specified pixel amounts. Classic RGB split. Extreme values = broken monitor. | Easy |
| A27 | Negate Strobe | FFmpeg Filters | Alternate negated and normal frames for strobing inversion. Per-component negate for partial color inversions. | Easy |
| A28 | Per-Channel Blend Modes | FFmpeg Filters | Apply different blend modes to individual Y/U/V channels in tblend. Multi-layered glitch textures. | Medium |

### Category B: Color & Grading (22 effects)

| # | Effect Name | Source | Description | Complexity |
|---|-------------|--------|-------------|------------|
| B1 | Film LUT Grading | FFmpeg, NumPy | Apply .cube LUT files for real film stock emulation. Portra 400, Ektachrome, Cinestill 800T. | Easy |
| B2 | Film Curve Emulation | NumPy | Use `np.interp()` with lookup tables modeled after real film S-curves and color response. | Medium |
| B3 | Histogram Equalization | Pillow/OpenCV | Auto-stretch histogram to full range. Reveals hidden detail in over/underexposed footage. | Easy |
| B4 | CLAHE Detail Reveal | OpenCV | Contrast Limited Adaptive Histogram Equalization. Local contrast enhancement. Night-vision quality. | Easy |
| B5 | K-Means Color Crush | OpenCV | Use k-means clustering to find 4-8 dominant colors, snap all pixels to nearest. Clean graphic posterization. | Medium |
| B6 | Color Quantize | Pillow | Reduce to N colors with dithering. Retro limited-palette game aesthetic. | Easy |
| B7 | Decorrelation Stretch | NumPy | Eigendecomposition of color covariance matrix. Amplify subtle color differences. Near-monochrome → vivid alien. | Hard |
| B8 | Chroma Smear | OpenCV (YCrCb) | Heavy blur only on Cr/Cb channels while keeping Y sharp. Analog chroma subsampling / VHS color bleed. | Medium |
| B9 | Perceptual Color Warp | OpenCV (LAB) | Independently manipulate A and B channels in LAB space. Alien color palettes with natural lightness. | Medium |
| B10 | Frequency-Band Color | NumPy FFT + OpenCV | Isolate low/mid/high spatial frequencies, apply different color treatments to each band. | Hard |
| B11 | Colorbalance Lift/Gamma/Gain | FFmpeg | Adjust shadows/midtones/highlights independently. Professional color grading. | Easy |
| B12 | Curves | FFmpeg | Apply tone curves like Photoshop. Control points for R, G, B, and master channels. | Medium |
| B13 | Light Leak | Pillow (Color Dodge) | Blend noise/gradient using Color Dodge mode. Blown-out overexposed light leak effects. | Easy |
| B14 | Shadow Melt | Pillow (Color Burn) | Blend dark texture using Color Burn. Deep saturated shadow regions like ink bleeding. | Easy |
| B15 | Texture Imprint | Pillow (Soft Light) | Blend grain/paper/fabric texture using Soft Light. Tactile analog-printed quality. | Easy |
| B16 | Self-Overlay | Pillow (Overlay) | Blend frame with time-delayed copy using Overlay mode. Intense contrast enhancement, dreamlike double-exposure. | Easy |
| B17 | Harsh Composite | Pillow (Hard Light) | Blend high-contrast mask using Hard Light. Aggressive strobe/flash effects. | Easy |
| B18 | Poisson Noise | NumPy | Camera sensor noise simulation. More realistic than Gaussian for "low light" looks. | Easy |
| B19 | Point LUT Curves | Pillow img.point() | Apply 256-entry lookup tables. Extremely fast for tone curves, gamma correction. | Easy |
| B20 | Polynomial Color | NumPy | Apply polynomial color curves. Quadratic, cubic for precise color grading. | Medium |
| B21 | Gaussian Blur | Pillow/OpenCV | True Gaussian blur (vs box blur). Perceptually smoother, photographic. | Easy |
| B22 | Unsharp Mask | Pillow | Professional sharpening with radius, amount, and threshold. Industry-standard. | Easy |

### Category C: Distortion & Warp (24 effects)

| # | Effect Name | Source | Description | Complexity |
|---|-------------|--------|-------------|------------|
| C1 | Vortex/Swirl | OpenCV remap + NumPy | Spiral distortion centered on any point. Strength falls off with distance from center. | Medium |
| C2 | Fisheye/Barrel | OpenCV remap + NumPy | Barrel and pincushion lens distortion. Classic GoPro / surveillance look. | Medium |
| C3 | Perlin Displacement | NumPy + OpenCV remap | 2D Perlin noise as displacement map. Organic fluid warping like heat shimmer or underwater caustics. | Medium |
| C4 | Domain Warp | NumPy | Feed Perlin noise coordinates through second noise layer. Recursive distortion like fluid dynamics. | Hard |
| C5 | Perspective Warp | Pillow/OpenCV | Fake 3D perspective tilt. Frame looks photographed from an angle. | Medium |
| C6 | Mesh Warp | Pillow | Grid-based distortion where each cell independently warps. Like bending a printed photo. | Medium |
| C7 | FFmpeg Displace | FFmpeg | Use external displacement map videos for X and Y axes. Self-displacement creates feedback-style warp. | Medium |
| C8 | Radial Gradient Mask | NumPy meshgrid | Create radial/linear/spiral masks. Apply effects through mask for spatial fade. | Easy |
| C9 | Procedural Mask Composite | NumPy + Pillow | Generate Perlin/Voronoi/ring masks. Composite clean and destroyed versions. Organic spatial patterns of destruction. | Medium |
| C10 | Cumulative Smear | NumPy cumsum | Cumulative sum along rows/columns with decay. Paint-smear or light-trail effect. | Easy |
| C11 | Spectral Glitch (FFT) | NumPy | FFT frame, randomize frequency bands/phase, inverse FFT. Dreamlike ringing artifacts. | Medium |
| C12 | Phase Swap | NumPy | Magnitude from frame A, phase from frame B. Eerie structural double-exposure. | Medium |
| C13 | SVD Rank Crush | NumPy | Keep only top 5-20 singular values. Ghostly, painterly approximation. Memory fading. | Medium |
| C14 | Pixel Sort Frequency | NumPy FFT | Sort in frequency domain instead of spatial. Subtle, eerie texture redistributions. | Hard |
| C15 | Laplacian Pyramid Glitch | OpenCV | Build pyramid, corrupt one level, reconstruct. Corruption at specific spatial frequency only. | Hard |
| C16 | Bilateral Skin Smooth | OpenCV | Edge-preserving blur. Beauty mode / editorial look. Base for oil painting. | Easy |
| C17 | Oil Painting | OpenCV bilateral + kmeans | Aggressive bilateral + k-means quantize. Flat color fields with confident edges. | Medium |
| C18 | Pencil Sketch | OpenCV | One-line `cv2.pencilSketch()`. Instant drawing effect. Chain with color for "animated comic." | Easy |
| C19 | Adaptive Threshold Woodcut | OpenCV | Local-adaptive B&W threshold. Woodcut/linocut print with clean separation. | Easy |
| C20 | Canny Neon Edges | OpenCV | Replace manual Sobel with Canny. Cleaner edge lines, colorize for professional neon edge effect. | Easy |
| C21 | Contour Lines | Pillow CONTOUR | Extract contour lines like topographic map of luminance. Thinner/cleaner than Sobel. | Easy |
| C22 | Morphological Edge Glow | OpenCV | morphologyEx(MORPH_GRADIENT) to extract object boundaries. Glowing structural edges. | Easy |
| C23 | Kaleidoscope | Glitch Projects, Hydra | Mirror and rotate triangle N times around center. Mandala-like radial symmetry. | Medium |
| C24 | Melt / Tear | Real-Time Video | Select random horizontal strips and stretch vertically. Dripping/melting aesthetic. | Medium |

### Category D: Temporal & Motion (22 effects)

| # | Effect Name | Source | Description | Complexity |
|---|-------------|--------|-------------|------------|
| D1 | Lagfun Decay Trail | FFmpeg | Bright pixels persist and slowly fade. Phosphor-glow trails. CRT persistence of vision. | Easy (FFmpeg) |
| D2 | Motion Delta | FFmpeg tblend | Show only pixels that changed between frames. Static = black, motion = bright outlines. | Easy (FFmpeg) |
| D3 | Frame Stutter/Reorder | FFmpeg random | Randomly shuffle frame order within buffer. Temporal glitch without affecting individual frames. | Easy (FFmpeg) |
| D4 | Speed Ramping | FFmpeg setpts | Variable speed with expressions. Smooth accelerate/decelerate. Music video staple. | Easy (FFmpeg) |
| D5 | Frame Interpolation Morph | FFmpeg minterpolate | Generate in-between frames via motion estimation. Smooth slow-mo from standard footage. | Easy (FFmpeg) |
| D6 | Morph Glitch | FFmpeg minterpolate | Abuse motion interpolation between non-matching scenes. Hallucinated impossible in-between frames. | Medium |
| D7 | Temporal Stacking | FFmpeg + NumPy | Stack N frames, compute statistics: mean (motion blur), median (remove objects), max (light painting), std-dev (show motion). | Medium |
| D8 | Optical Flow Accumulation | OpenCV Farneback | Compute dense optical flow, cumulatively remap reference image. Progressive melt/smear without compression. | Medium |
| D9 | Motion Heatmap | OpenCV Dense Flow | Visualize motion as color (hue = direction, brightness = magnitude). | Medium |
| D10 | Motion Trails | OpenCV Sparse Flow | Track feature points, draw persistent colored lines tracing paths. Light-painting effect. | Medium |
| D11 | P-Frame Bloom | Datamosh | Duplicate specific P-frames N times. Same motion vector applies repeatedly = directional melt. | Hard |
| D12 | Motion Vector Redirect | FFglitch/Datamosh | Edit motion vectors directly. Point them in arbitrary directions. Surreal motion warping. | Hard |
| D13 | Multi-Scene Never-Resolve | Datamosh | Remove I-frames at scene boundaries. Scenes bleed into each other continuously. | Hard |
| D14 | GOP Starvation | Datamosh | Huge GOP + low bitrate + no scene detection. Video slowly decays to abstract mush. | Medium |
| D15 | Cross-Clip Motion Transfer | Datamosh | Apply clip A's motion data to clip B's pixels. Two unrelated videos become one melted hybrid. | Hard |
| D16 | Stutter Cut | ffmpeg-python | Extract tiny 0.1-0.5s segments from random points, concatenate. Rapid-fire jump-cut glitch. | Medium |
| D17 | Deflicker Stabilizer | ffmpeg-python | Smooth luminance variations after aggressive glitch. Tame seizure-inducing flicker. | Easy |
| D18 | Partial Freeze | MoviePy FreezeRegion | Freeze selected region while rest continues. Split-time surreal look. | Medium |
| D19 | Make Loopable | MoviePy | Cross-fade end into beginning for seamless infinite loop. Critical for social media. | Easy |
| D20 | Time Warp | MoviePy time_transform | Arbitrary mathematical time remapping. Sine-wave, logarithmic, random jump playback. | Medium |
| D21 | Ease Speed | MoviePy AccelDecel | Ease-in/ease-out speed curves. Smooth slow-motion transitions. | Easy |
| D22 | Strobe/Blink | MoviePy | Rhythmic on/off at configurable durations. Sync with audio for beat-matched flashes. | Easy |

### Category E: Audio-Reactive (40 effects)

| # | Effect Name | Source | Audio Feature → Visual Mapping | Complexity |
|---|-------------|--------|-------------------------------|------------|
| E1 | Beat-Synced Glitch Triggers | Librosa | Beat timestamps trigger discrete glitch events (pixelsort, channelshift). Fire on every downbeat. | Medium |
| E2 | Onset Explosion | Librosa | Onset detection → radial pixel explosion from center. Strength controls radius. | Medium |
| E3 | Spectral Centroid Brightness | Librosa | Spectral centroid → image brightness. Cymbals = white-hot, bass = deep shadow. | Easy |
| E4 | Chroma Color Mapping | Librosa | 12 pitch classes → 12 hues on color wheel. C major = red/yellow/green tint. | Medium |
| E5 | RMS Energy Zoom | Librosa | RMS loudness → camera zoom. Loud = zoom in (aggressive), quiet = zoom out (expansive). | Easy |
| E6 | Harmonic/Percussive Dual-Layer | Librosa HPSS | Harmonic RMS → smooth flowing distortion. Percussive RMS → sharp angular corruption. | Hard |
| E7 | Pitch-Driven Vertical Shift | Librosa pyin | Fundamental frequency → vertical displacement. Higher notes push up, lower pull down. | Medium |
| E8 | Spectral Flatness Noise Gate | Librosa | Flatness (noise-like vs tonal) → static/noise overlay intensity. Noise audio = noise video. | Easy |
| E9 | Tempogram Pulse Width | Librosa | Local tempo → pulsing border/vignette width. Fast tempo = tight pulses. | Medium |
| E10 | Spectral Contrast Edge Detect | Librosa | Spectral clarity → visual sharpness. Clear tones = sharp edges, muddy mix = blur. | Medium |
| E11 | Hilbert Envelope Follower | SciPy | Smooth amplitude envelope → frame opacity/fade. Loud = full video, quiet = fade to black. | Easy |
| E12 | Band-Isolated 3-Way Reactivity | SciPy Butterworth | Sub-bass → horizontal shake. Mids → saturation. Highs → pixel scatter/noise. Three independent layers. | Hard |
| E13 | Cross-Correlation Pattern Match | SciPy | Cross-correlate with kick drum template → trigger specific effect only on kicks. | Hard |
| E14 | Spectral Peak Color Split | SciPy find_peaks | Top 3 frequency peaks → RGB channel displacement offsets. Harmonic = structured, dissonant = chaotic. | Hard |
| E15 | Spectrogram Displacement | SciPy | Vertical spectrogram slice → horizontal pixel row displacement. Video warps to audio shape. | Medium |
| E16 | Instantaneous Frequency Hue | SciPy Hilbert | Instantaneous frequency → hue rotation speed. Stable pitch = slow color, vibrato = wild cycling. | Medium |
| E17 | Sub-Bass Rumble Shake | SciPy Welch | 20-80 Hz energy → global frame wobble/camera shake. 808s physically shake the image. | Easy |
| E18 | Window Function Vignette | SciPy windows | Audio bandwidth → vignette shape. Narrow audio = tunnel vision, wide = open view. | Medium |
| E19 | Decimation Pixelation | SciPy decimate | Audio detail metric → video resolution. Complex audio = full resolution, sustained = pixelated. | Medium |
| E20 | FIR Convolution Smear | SciPy fftconvolve | Audio envelope → horizontal pixel smear kernel. Long reverb tail = long smear. Punchy = tight. | Medium |
| E21 | dBFS Loudness Contrast | PyDub | Per-frame dBFS → contrast multiplier. Loud = punchy, quiet = washed-out. | Easy |
| E22 | Silence-Detection Scene Cut | PyDub | Silence boundaries → hard scene cuts/inversions/transitions. Musical pauses = visual punctuation. | Easy |
| E23 | Stereo Pan Position | PyDub | Left/right RMS ratio → horizontal frame translation. Ping-pong delay = swaying video. | Easy |
| E24 | Peak Level Flash | PyDub | Near-clipping peaks → white flash. True clipping → color inversion. Hyper-loud = strobe. | Easy |
| E25 | Bit-Depth Visual Quantize | PyDub | Audio smoothness → video color depth. Lo-fi audio gets lo-fi posterized visuals. | Easy |
| E26 | Frequency Sweep Tracker | PyDub + Librosa | Spectral centroid position → vertical distortion zone. Rising sweep = distortion moves bottom to top. | Medium |
| E27 | Silence Segment Shuffle | PyDub | Split video at silence points, shuffle segments. Jump-cut collage from natural pauses. | Medium |
| E28 | HPSS Split-Screen | Audio DSP | Harmonic drives left half (smooth shifts), percussive drives right half (hard glitches). Split-screen dual nature. | Hard |
| E29 | Frequency Shifter Aberration | Audio DSP | Audio inharmonicity (from frequency shifting) → chromatic aberration intensity. Consonance = aligned, dissonance = fractured. | Hard |
| E30 | Creative Convolution Texture | Audio DSP | Spectral difference between original and convolved audio → visual texture overlay density. | Hard |
| E31 | Concatenative Visual Mosaic | Audio DSP | Match audio MFCCs to video clip database. Display clips matching current timbre. | Hard |
| E32 | Karplus-Strong Resonance | Audio DSP | Fundamental frequency → visual pattern spacing (stripe pitch, dot grid). Pitch matches visual frequency. | Medium |
| E33 | Waveshaper Transfer | Audio DSP | Audio distortion level → same nonlinear transfer function applied to pixel brightness. Crushed audio = crushed video. | Medium |
| E34 | Phase Vocoder Time Lag | Audio DSP | Audio rate of change → video speed. Fast passages = normal speed, sustains = slow-mo freeze. | Hard |
| E35 | Euclidean Rhythm Grid | Audio DSP + isobar | Detected time signature → Euclidean rhythm visual grid overlay. Different signatures = different geometric patterns. | Hard |
| E36 | Neural Source Sep Layers | Audio DSP Demucs | Vocals → spotlight effect. Drums → shake/glitch. Bass → depth blur. Synths → color rotation. Four independent layers. | Hard |
| E37 | Onset-Strength Datamosh | Audio DSP + Librosa | Low onset strength = heavy datamosh melting. High onset = sharp I-frame clarity. Corruption ebbs and flows with articulation. | Hard |
| E38 | Audio Spectrum Reactor | Real-Time Video | FFT bands: sub-bass → zoom, bass → displacement, mids → rotation, highs → noise. Full-spectrum reactivity. | Hard |
| E39 | Onset Trigger Mode | Real-Time Video | Glitch effects fire only on detected musical onsets. Musically synchronized corruption. | Medium |
| E40 | Amplitude Follow | Real-Time Video | Smooth envelope → fluid effect intensity. Organic parameter animation that breathes with music. | Easy |

### Category F: Computer Vision & Detection (14 effects)

| # | Effect Name | Source | Description | Complexity |
|---|-------------|--------|-------------|------------|
| F1 | Neon Outlines | OpenCV Contours | Find object contours, overlay as bright neon-colored strokes on darkened frame. Cartoon/vector-art. | Medium |
| F2 | Geometry Overlay | OpenCV Contour Props | Replace detected shapes with bounding circles/ellipses/convex hulls. Geometric primitive abstraction. | Medium |
| F3 | Feature Constellations | OpenCV ORB | Overlay detected keypoints as glowing dots. Star-map visualization of image structure. | Easy |
| F4 | Scale Halos | OpenCV SIFT | Render features as oriented circles showing scale. Radar-pulse/sonar-ping overlays. | Medium |
| F5 | Correspondence Web | OpenCV Feature Match | Draw lines connecting matched features between frames. Web-of-connections showing how content moves. | Medium |
| F6 | Auto Stencil | OpenCV Otsu | Otsu's auto-threshold for two-tone stencil. Printmaking/street-art look. | Easy |
| F7 | Face Glitch | dlib + OpenCV | Detect faces, apply glitch effects only to face regions. Privacy-art and portrait-glitch. | Medium |
| F8 | Pose Glitch | MediaPipe + OpenCV | Detect body keypoints, apply different effects to torso vs limbs vs background. | Hard |
| F9 | YOLO Segmentation Sort | YOLO + pixelsort | ML segmentation masks → pixel sort only within detected objects. Person melts, background stays. | Hard |
| F10 | Edge Interval Pixel Sort | OpenCV Canny | Canny edge detection defines pixel sort boundaries. Glitch streaks follow natural contours. | Medium |
| F11 | Diagonal Pixel Sort | NumPy | Sort pixels along arbitrary angles (45°, 135°). Sweeping diagonal streaks. Animate angle over time. | Easy |
| F12 | Wave Interval Sort | NumPy | Sine-wave intervals define sorting regions. Rhythmic repeating bands of sorted pixels. | Easy |
| F13 | Mask-Guided Pixel Sort | Pillow/NumPy | External B&W mask defines which regions get sorted. Target sky, face, or text only. | Easy |
| F14 | Minimum Channel Sort | NumPy | Sort by min(R,G,B). Dark-toned, shadow-biased streaks with different character than standard sorts. | Easy |

### Category G: Generative & Procedural (18 effects)

| # | Effect Name | Source | Description | Complexity |
|---|-------------|--------|-------------|------------|
| G1 | Cellular Automata Overlay | Glitch Projects, FFmpeg cellauto | Run Conway's Game of Life as texture layer. Composite with blend modes. Living texture. | Medium |
| G2 | Flow Field Particles | Glitch Projects | Perlin noise angles guide particle movement. Trace organic flowing paths. Overlay on video. | Medium |
| G3 | L-System Fractal Overlay | Glitch Projects | Lindenmayer system grammars render branching fractals. Animate iteration depth over time. | Medium |
| G4 | Interference Pattern | Glitch Projects | Concentric sine waves from multiple center points create moire interference. Animate sources. | Easy |
| G5 | Voronoi Overlay/Mask | Hydra | Generate Voronoi cell pattern. Use as overlay or to mask different effects into different cells. Cracked-glass. | Medium |
| G6 | Organic Warp Field | Pillow Glitch | Multi-octave smooth noise as displacement map. Cloud-like, evolving distortion field. | Medium |
| G7 | GEQ Procedural Patterns | FFmpeg geq | Per-pixel math expressions. Generate moire, interference, plasma directly in FFmpeg. Use as texture overlays. | Medium |
| G8 | Mandelbrot/Julia Fractal | NumPy | Generate fractal zoom sequences. Overlay or use as displacement map. Animate zoom parameter. | Medium |
| G9 | Sonification Feedback | Glitch Projects | Convert pixel brightness to audio frequency (sonification), analyze result, feed back as glitch parameters. Closed-loop audio-visual feedback. | Hard |
| G10 | Recursive Feedback | Hydra | Per-frame scale, rotation, and blend. Spiraling, zooming, rotating trails beyond basic feedback. | Medium |
| G11 | Noise Modulation | Hydra | Perlin noise field displaces UV coordinates. Organic, turbulent displacement (not sinusoidal). | Medium |
| G12 | Dynamic Pixelate | Hydra | Pixel block size varies across frame based on noise/gradient. Depth-of-field-like degradation. | Medium |
| G13 | 10-Print Pattern | Generative Art | Random / and \ characters in grid. Simple maze-like glitch texture overlay. | Easy |
| G14 | Lissajous Pattern | Math + NumPy | Parametric curves as overlay or displacement. Oscilloscope-like aesthetic. | Easy |
| G15 | Reaction-Diffusion | NumPy | Gray-Scott model. Organic self-organizing patterns like coral, zebra stripes. Overlay or mask. | Hard |
| G16 | Spiral Pattern | NumPy meshgrid | Logarithmic/Archimedean spirals as masks or overlays. Animated rotation for hypnotic effect. | Easy |
| G17 | Worley/Voronoi Noise | NumPy | Cellular noise patterns resembling cracked earth, cell structures, stained glass. Displacement or texture. | Medium |
| G18 | Plasma Effect | NumPy sin/cos | Classic demoscene plasma: multiple overlapping sine waves in X, Y, and time. Psychedelic color cycling. | Easy |

### Category H: Blend Modes & Compositing (10 effects)

| # | Effect Name | Source | Description | Complexity |
|---|-------------|--------|-------------|------------|
| H1 | Multiply | Pillow ImageChops | Standard multiply blend. Darks darken, whites transparent. | Easy |
| H2 | Screen | Pillow ImageChops | Standard screen blend. Lights lighten, blacks transparent. | Easy |
| H3 | Difference | Pillow ImageChops | Pixel-level absolute difference. Motion detection aesthetic. | Easy |
| H4 | Addition | Pillow ImageChops | Additive blend. Bright+bright = overexposed glow. | Easy |
| H5 | Phoenix | FFmpeg | Min-max blend producing psychedelic neon-like inversions wherever motion occurs. | Easy |
| H6 | Effect Masking | Pillow composite | Grayscale mask confines any effect to specific regions. Edge/threshold/motion masks. | Medium |
| H7 | Blend Mode Library | FFmpeg blend | All 20+ FFmpeg blend modes (multiply, screen, overlay, softlight, hardlight, difference, exclusion, etc.) in one filter pass. | Easy |
| H8 | Oscilloscope Overlay | FFmpeg | Overlay oscilloscope visualization on video. Technical/aesthetic hybrid. | Easy |
| H9 | Waveform/Vectorscope | FFmpeg | Overlay luma/chroma waveform or color vector display. Broadcast monitoring as art. | Easy |
| H10 | Frame Counter/Timecode | FFmpeg drawtext | Burn in frame number, timecode, custom text. Technical glitch overlay. | Easy |

### Category I: Cross-Modal / Mad Scientist (30 effects)

| # | Effect Name | Source | Description | Complexity |
|---|-------------|--------|-------------|------------|
| I1 | Reverb on Video Bytes | Mad Scientist | Load video as raw bytes, convolve with impulse response (reverb), write back. Smeared echo artifacts. | Medium |
| I2 | Chorus on Pixels | Mad Scientist | Apply audio chorus (multiple delayed copies with slight pitch variation) to pixel row data. Layered ghosting. | Medium |
| I3 | Granular Video Synthesis | Mad Scientist | Slice frames into micro-grains (tiny tiles), scatter/rearrange using granular synthesis algorithms. Particle cloud effect. | Hard |
| I4 | Frequency Modulation Video | Mad Scientist | Apply FM synthesis math to pixel values. Carrier × modulator creates complex sidebands in pixel space. | Hard |
| I5 | Wavefold Pixels | Mad Scientist | Apply wavefolding (audio distortion) to pixel brightness. Values that exceed threshold fold back. Psychedelic contrast. | Easy |
| I6 | Bitwise XOR Glitch | Mad Scientist | XOR pixel values with a repeating pattern, sine wave, or another frame. Digital-only aesthetic. | Easy |
| I7 | Slew Rate Limiter | Mad Scientist | Audio slew rate limiting on pixel values. Limits how fast brightness can change between adjacent pixels. Soft edges, rounded corners. | Medium |
| I8 | Envelope Shaper Contrast | Mad Scientist | Audio envelope attack/release controls applied to brightness changes between frames. Sharp attack = instant brightness, slow release = trailing glow. | Medium |
| I9 | Flanger on Rows | Mad Scientist | Audio flanging (comb filter) applied to pixel rows. Variable delay between original and copied row creates phase-cancellation patterns. | Medium |
| I10 | Phaser on Color | Mad Scientist | All-pass filters (audio phaser) applied to color channel values. Sweeping notches in color space. | Medium |
| I11 | Sidechain Video to Audio | Mad Scientist | Video brightness/contrast ducks when audio peaks. Visual equivalent of sidechain compression. | Medium |
| I12 | Pitch Shift Pixels | Mad Scientist | Apply audio pitch-shifting algorithm to pixel rows. "Higher pitch" = stretched/smeared, "lower pitch" = compressed. | Hard |
| I13 | Dither (Audio→Visual) | Mad Scientist | Apply audio dithering algorithms (triangular PDF, noise shaping) to pixel values during bit-depth reduction. Professional-quality posterization. | Medium |
| I14 | Compander Dynamics | Mad Scientist | Audio compander (compress then expand) applied to pixel brightness. Extreme dynamic range manipulation. | Medium |
| I15 | Spectral Freeze | Mad Scientist | FFT a frame, freeze the magnitude spectrum, evolve only the phase over time. Frame "rings" like a resonant body. | Hard |
| I16 | Vocoder Texture | Mad Scientist | Use audio vocoder concept: modulate one frame's "frequency bands" with another frame's envelope. Texture transfer. | Hard |
| I17 | Convolution Reverb on Frame | Mad Scientist | Convolve a frame with another image as "impulse response." The IR's shape smears the source in its pattern. | Medium |
| I18 | Sample Rate Reduce Spatial | Mad Scientist | Audio sample rate reduction applied spatially. Keep every Nth pixel, zero-order hold. Chunky digital aesthetic. | Easy |
| I19 | Noise Gate Visual | Mad Scientist | Audio noise gate concept: black out all pixels below a threshold (already have as "gate"), but add attack/release/hold like real audio gate. Smooth transitions. | Medium |
| I20 | Limiter Clip | Mad Scientist | Audio limiter: hard-clip pixel values at a ceiling, with optional soft-knee curve. Controlled brightness ceiling. | Easy |
| I21 | Mid-Side Processing | Mad Scientist | Audio mid-side applied to video: extract "mid" (center of frame) and "side" (edges), process separately, recombine. | Hard |
| I22 | Parallel Compression | Mad Scientist | Blend original frame with heavily processed (crushed contrast) version. New York compression for video. | Easy |
| I23 | Multiband Processing | Mad Scientist | Split frame into frequency bands (via FFT or pyramid), process each independently (like multiband compressor), recombine. | Hard |
| I24 | Stereo Widener | Mad Scientist | Audio stereo widening applied to left/right halves of frame. Push edges outward, widen or narrow the visual field. | Medium |
| I25 | De-Esser Visual | Mad Scientist | Detect "harsh" high-frequency visual content (fine edges, noise), selectively reduce. Smooth harsh details. | Medium |
| I26 | Transient Shaper | Mad Scientist | Audio transient detection applied to temporal frame changes. Boost or reduce the "attack" of visual motion. Sharp motion sharper, or softened. | Hard |
| I27 | Tape Saturation | Mad Scientist | Audio tape saturation curves applied to pixel values. Warm, compressed highlights with soft roll-off. | Easy |
| I28 | Tube Warmth | Mad Scientist | Even-harmonic distortion (tube amp character) applied to pixel values. Add warmth and subtle glow. | Easy |
| I29 | Crossover Distortion | Mad Scientist | Class-B amplifier crossover distortion applied to pixel values. Dead zone around mid-gray. Creates stark mid-tone artifacts. | Medium |
| I30 | AM Radio Effect | Mad Scientist | Amplitude modulation with carrier frequency applied to pixel rows. Alternating bright/dark bands like AM radio interference. | Easy |

### Category J: Creative / Art-Inspired (30 effects)

| # | Effect Name | Inspiration | Description | Complexity |
|---|-------------|-------------|-------------|------------|
| J1 | Cubist Fragmentation | Cubism | Divide frame into angular polygons, slightly rotate/shift each independently. Multiple viewpoints simultaneously. | Medium |
| J2 | Pointillist Dots | Pointillism | Replace pixels with discrete colored dots. Seurat-style effect at variable dot sizes. | Medium |
| J3 | Suprematist Blocks | Suprematism (Malevich) | Detect dominant shapes, replace with flat geometric color blocks (squares, circles, crosses) on white. | Hard |
| J4 | Action Drip | Abstract Expressionism | Simulate paint drips running down from bright areas. Pollock-inspired gravity-driven color trails. | Medium |
| J5 | Rothko Bands | Color Field Painting | Extract dominant colors, render as soft-edged horizontal bands that transition between hues. | Medium |
| J6 | Crystal Growth | Crystallography | Voronoi cells that expand from seed points over time, each cell preserving the color of its seed pixel. | Medium |
| J7 | Erosion Channels | Geology (Erosion) | Simulate water erosion: bright pixels "flow" downward, carving channels into the image over multiple frames. | Hard |
| J8 | Bioluminescence | Marine biology | Detect edges, make them glow with animated blue-green pulsing. Organic ocean-creature aesthetic. | Medium |
| J9 | Coral Branching | Reaction-Diffusion | Gray-Scott reaction-diffusion patterns that grow from edges into flat areas. Organic structure invasion. | Hard |
| J10 | Aurora Borealis | Atmospheric optics | Animated color curtains (sinusoidal vertical bands with hue cycling) overlaid on darkened frame. Northern lights. | Medium |
| J11 | Weave Pattern | Textile (Weaving) | Overlay interlocking horizontal and vertical strips with over/under crossing pattern. Woven fabric from video. | Medium |
| J12 | Mosaic Tiles | Roman mosaic | Divide into irregular polygonal tiles (Voronoi), fill each with average color. Tesserae effect. | Medium |
| J13 | Stained Glass | Gothic architecture | Canny edges become thick black "leading," regions between edges become flat saturated colors. | Medium |
| J14 | Risograph | Print technique | Simulate risograph printing: limited color palette, halftone dots, slight misregistration between color layers. | Hard |
| J15 | Cyanotype | Photography | Blue-and-white photographic print simulation. Map luminance to Prussian blue tones. | Easy |
| J16 | Infrared | IR Photography | Swap color channels + push greens to white. Simulate infrared film where vegetation glows white. | Easy |
| J17 | Double Exposure | Photography | Blend current frame with a frame from different timestamp using Screen or Lighten mode. | Easy |
| J18 | Tilt-Shift Miniature | Photography | Apply gradient blur (sharp center, blurred top/bottom) + saturation boost. Miniature/toy-like effect. | Medium |
| J19 | Long Exposure Lights | Photography | Max-blend across N frames. Moving lights create trails, static areas stay normal. | Easy |
| J20 | Anamorphic Lens | Cinema | Add horizontal lens flares + subtle squeeze/stretch. Widescreen cinematic look. | Medium |
| J21 | Film Burns | Cinema | Random orange/red/white blotches with soft edges. Simulates film stock damage/light leaks. | Easy |
| J22 | TV Static | Broadcast | Full-screen random noise with horizontal sync drift. Channel-between-stations aesthetic. | Easy |
| J23 | Glitch Text | Typography | Overlay corrupted/flickering text characters (error messages, hex values, timestamps). | Medium |
| J24 | ASCII Art | Typography | Convert frame to ASCII characters based on brightness. Render as monospace text overlay or full replacement. | Medium |
| J25 | Halftone | Print technique | Convert to CMYK halftone dots at different angles per channel. Newspaper/comic book print. | Medium |
| J26 | Cross-Process | Film | Simulate cross-processing (E-6 film in C-41 chemistry). High contrast, shifted colors, cyan shadows. | Easy |
| J27 | Holographic | Optics | Rainbow diffraction pattern overlay that shifts with viewing angle (animated over time). | Medium |
| J28 | Glitch Quilt | Quilting | Divide frame into rectangular patches, apply different random effects to each patch independently. | Easy |
| J29 | Stipple | Drawing | Convert to dot density representation. Darker = more dots, lighter = fewer. Ink drawing aesthetic. | Medium |
| J30 | Woodblock Print | Printmaking | Reduce to 2-4 colors, apply different patterns per color layer. Register slightly offset between layers. | Hard |

### Category K: Competitive / Market Gaps (22 effects)

| # | Effect Name | Competitor Source | Description | Complexity |
|---|-------------|-------------------|-------------|------------|
| K1 | Hyperspektiv Prism | Hyperspektiv | Multi-faceted prism split: duplicate and tile the image in triangular/hexagonal arrangement. | Medium |
| K2 | Lumen Analog Feedback | Lumen | True analog-style video feedback: output feeds back as input with color drift and CRT glow. | Medium |
| K3 | Resolume Wire Removal | Resolume | Luminance-keyed region replacement. Remove (key out) specific brightness ranges and replace with another layer. | Medium |
| K4 | TouchDesigner TOP Chains | TouchDesigner | Node-based effect chain with feedback loops, parallel processing, and conditional routing per-frame. | Hard |
| K5 | After Effects Turbulent Displace | After Effects | Fractal-noise-driven displacement with evolution parameter. Industry-standard organic warp. | Medium |
| K6 | After Effects CC Glass | After Effects | Refraction/glass distortion using a bump map. Makes video look like it's behind textured glass. | Medium |
| K7 | After Effects CC Particle World | After Effects | Emit particles from bright areas of the image. Particles inherit color from source pixel. Disintegration effect. | Hard |
| K8 | Premiere Warp Stabilizer Invert | Premiere Pro | Run stabilization analysis, then apply the INVERSE transform to add realistic camera shake. | Medium |
| K9 | Glitch Lab Pixel Drift | Glitch Lab | Pixels slowly drift from their positions over time based on local gradients. Organic dissolution. | Medium |
| K10 | Signal RGB Bend | Signal (iOS) | Independent RGB channel bending along curves. Each channel follows a different geometric deformation. | Medium |
| K11 | Processing Pixel Sorting Modes | Processing | Additional pixel sort modes: radial (from center), spiral, random-walk paths through image. | Medium |
| K12 | VDMX Layer Masks | VDMX | Audio-reactive layer masks that reveal/hide different effect layers based on frequency bands. | Medium |
| K13 | Max/MSP Jitter Matrix | Max/MSP Jitter | Matrix-based pixel operations: arbitrary 3x3 or 4x4 matrix transforms on pixel neighborhoods. | Medium |
| K14 | Isadora Mapping | Isadora | Projection mapping: warp video to fit arbitrary quadrilateral shapes. Multi-surface output. | Hard |
| K15 | VHS Camcorder Tracking | VHS Camcorder app | Horizontal tracking error simulation: random horizontal offset per scanline that wobbles. | Easy |
| K16 | GlitchCam Glitch Type Mix | GlitchCam | Randomly mix 2-3 different glitch types per frame with weighted probability. Unpredictable variety. | Easy |
| K17 | Particle Disintegrate | After Effects | Frame dissolves into particles that scatter based on luminance or edge proximity. | Hard |
| K18 | Depth-of-Field from ML | Competitor trend | Use monocular depth estimation to create depth-based effect masks. Apply glitch only to foreground or background. | Hard |
| K19 | Color Halation | Film simulation | Red/orange bleed from overexposed highlights into surrounding areas. Film-specific artifact. | Medium |
| K20 | Lens Distortion | Camera simulation | Chromatic fringing + barrel distortion + vignette as unified "lens" effect. | Medium |
| K21 | Film Grain (per-ISO) | Film simulation | Grain patterns that vary by simulated ISO: fine (ISO 100) to heavy (ISO 3200). Not uniform noise. | Medium |
| K22 | Analog Drift | Analog simulation | Slow, organic drift of all parameters over time. Nothing stays perfectly stable. Living, breathing effect. | Medium |

### Category L: Performance & Workflow (18 capabilities)

| # | Capability | Source | Description | Impact |
|---|------------|--------|-------------|--------|
| L1 | Streaming Frame Pipeline | imageio imiter + ffmpeg-python async | Read-process-write frames via pipe. No disk I/O. Enables long video processing. | High |
| L2 | In-Memory Bytes I/O | imageio BytesIO | Process frames entirely in memory. No temp files. Faster, cleaner. | High |
| L3 | PyAV Native Codec | imageio pyav plugin | Replace FFmpeg subprocess with native PyAV. Less overhead, precise frame seeking. | High |
| L4 | GLSL Shader Pipeline | Real-Time Video | Port heavy effects to GPU shaders. Real-time preview at full resolution. | High |
| L5 | ISF Shader Import | Real-Time Video | Import community ISF shaders as custom effects. Hundreds of free effects at isf.video. | High |
| L6 | Parallel Frame Render | Python multiprocessing | ProcessPoolExecutor for frame-independent effects. 4-8x render speed. | High |
| L7 | Multi-Format Simultaneous Export | ffmpeg-python merge_outputs | Export MP4 + MOV + GIF in a single processing pass. | Medium |
| L8 | Dry-Run Command Preview | ffmpeg-python compile() | Show exact FFmpeg command before executing. Debug, learn, share recipes. | Low |
| L9 | Adaptive Processing | ffmpeg-python probe | Auto-adapt parameters to input (resolution-relative displacement, FPS-relative temporal effects). | Medium |
| L10 | URL Source Download | yt-dlp | Paste YouTube/URL, auto-download. Eliminate manual download step. | Medium |
| L11 | Webcam Live Mode | imageio <video0> | Apply effects to live webcam feed. Real-time performance use case. | Medium |
| L12 | Screen Capture Mode | imageio <screen> | Glitch any on-screen content live. | Medium |
| L13 | GIF Export Optimized | imageio | Direct GIF export with per-frame duration and loop control from Gradio UI. | Medium |
| L14 | Syphon Output | Syphon (macOS) | Send processed video to VJ software in real-time. Live performance instrument. | High |
| L15 | NDI Network Output | NDI | Network video sharing to any NDI receiver. Multi-machine setups. | Medium |
| L16 | Virtual Webcam Output | OBS Virtual Camera | Glitched video as camera source in Zoom/Discord/OBS. | Medium |
| L17 | Node-Based Effect Chain | cables.gl style | Visual node-based editor for complex routing: branching, merging, feedback paths. | High |
| L18 | Scroll Effect | MoviePy | Scrolling window moves across frame. Ticker/panorama look. | Easy |

---

## Grand Total Summary

| Category | Count | Description |
|----------|-------|-------------|
| A: Pixel Corruption & Data Bending | 28 | Byte-level, codec-level, compression artifacts |
| B: Color & Grading | 22 | LUTs, curves, color science, blend modes |
| C: Distortion & Warp | 24 | Spatial transforms, FFT, geometric warp |
| D: Temporal & Motion | 22 | Time-based, motion detection, datamosh |
| E: Audio-Reactive | 40 | Audio feature → visual parameter mappings |
| F: Computer Vision & Detection | 14 | Face/pose/feature detection, smart masking |
| G: Generative & Procedural | 18 | Fractals, noise, cellular automata, particles |
| H: Blend Modes & Compositing | 10 | Standard blend modes, overlays, masking |
| I: Cross-Modal / Mad Scientist | 30 | Audio DSP techniques applied to video |
| J: Creative / Art-Inspired | 30 | Art movements, nature, photography, cinema |
| K: Competitive / Market Gaps | 22 | Features from competitors we're missing |
| L: Performance & Workflow | 18 | Speed improvements, new I/O modes |
| **TOTAL NEW** | **278** | |
| **+ Shipped** | **37** | |
| **GRAND TOTAL** | **315** | |

---

## Priority Recommendations

### Tier 1: Quick Wins (< 10 lines each, implement immediately)
A1 (JPEG Corrupt), A5 (Re-encode Decay), A8 (CRF Degradation), A10 (Bitstream Noise), A26 (rgbashift), B3 (Histogram Eq), B4 (CLAHE), B21 (Gaussian Blur), B22 (Unsharp Mask), C16 (Bilateral Smooth), C18 (Pencil Sketch), C19 (Adaptive Woodcut), C20 (Canny Neon), D1 (Lagfun Trail), D2 (Motion Delta), G4 (Interference Pattern), G18 (Plasma), H1-H5 (Blend Modes), J16 (Infrared), J17 (Double Exposure), J22 (TV Static)

### Tier 2: Medium Effort (10-50 lines, high impact)
A11 (Audacity Databend), B1 (Film LUTs), B5 (K-Means Color), C1 (Vortex), C2 (Fisheye), C3 (Perlin Displace), C11 (Spectral Glitch FFT), C13 (SVD Rank Crush), C23 (Kaleidoscope), C24 (Melt/Tear), D7 (Temporal Stacking), E1 (Beat-Synced Glitch), E5 (RMS Zoom), F1 (Neon Outlines), G1 (Cellular Automata), I1 (Reverb on Bytes), I5 (Wavefold), J14 (Risograph), J25 (Halftone), K15 (VHS Tracking)

### Tier 3: Significant Features (50-200 lines, unique selling points)
C4 (Domain Warp), D8 (Optical Flow Accumulation), D11 (P-Frame Bloom), E6 (HPSS Dual-Layer), E12 (Band-Isolated 3-Way), E36 (Neural Source Sep), F7 (Face Glitch), F9 (YOLO Segment Sort), G9 (Sonification Feedback), G15 (Reaction-Diffusion), I15 (Spectral Freeze), I16 (Vocoder Texture), J7 (Erosion Channels), K7 (Particle Disintegrate)

### Tier 4: Architecture-Level (require pipeline changes)
D12 (Motion Vector Redirect), D13 (Multi-Scene Never-Resolve), D15 (Cross-Clip Motion Transfer), E28 (HPSS Split-Screen), L1 (Streaming Pipeline), L4 (GLSL Shaders), L6 (Parallel Rendering), L14 (Syphon Output), L17 (Node-Based Chain)

---

*This document is the single source of truth for Entropic's effect expansion roadmap. All 17 reference docs were reviewed, 5 skills were consulted, and every idea is tagged by source, category, and complexity.*

*Last updated: 2026-02-07 by Claude + Mad Scientist + Creative + Glitch Video + Audio Production + Competitive Analysis*

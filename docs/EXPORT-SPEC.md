# Entropic Export System Specification

**Version:** 1.0.0
**Status:** Design
**Author:** CTO Advisory / Claude Opus 4.6

---

## Overview

This document specifies a comprehensive export system for Entropic, inspired by
Adobe Premiere Pro's Media Encoder and Photoshop's Export As / Save for Web
dialogs. The goal is to replace the current 3-tier export (`lo`/`mid`/`hi`)
with a professional, granular export pipeline that gives users full control
while maintaining sensible defaults.

### Design Principles

1. **Sensible defaults** -- Users who just click "Export" get a good MP4.
2. **Progressive disclosure** -- Basic options visible; advanced options collapsed.
3. **FFmpeg-native** -- Every option maps directly to FFmpeg flags. No abstractions that leak.
4. **Presets first** -- Ship presets for common workflows (Instagram, YouTube, editing pipeline).
5. **Validation at model level** -- Pydantic enforces valid combinations before FFmpeg ever runs.

### Current System (Being Replaced)

```python
class RenderRequest(BaseModel):
    effects: list[dict]
    quality: str = "mid"   # "lo" (480p h264 crf28), "mid" (720p h264 crf23), "hi" (prores 422)
    mix: float = 1.0
```

---

## 1. Output Formats

### 1.1 MP4 (H.264)

**Use case:** Web delivery, social media, general sharing. Universally playable.

| Setting | FFmpeg Flag | Default | Valid Range | Notes |
|---------|------------|---------|-------------|-------|
| Codec | `-c:v libx264` | libx264 | libx264 | Software encoder; hardware (`h264_videotoolbox`) possible future addition |
| Container | output suffix `.mp4` | -- | -- | MPEG-4 Part 14 container |
| Pixel format | `-pix_fmt yuv420p` | yuv420p | yuv420p, yuv422p, yuv444p | yuv420p required for broad compatibility |
| Profile | `-profile:v` | high | baseline, main, high, high10 | `high` is the safe default for HD content |
| Level | `-level` | 4.1 | 3.0, 3.1, 4.0, 4.1, 5.0, 5.1, 5.2 | Constrains resolution/bitrate combinations |

**Why it matters:** MP4/H.264 is the lingua franca of video. Every browser, phone, and player supports it. CRF 18-23 is visually transparent for most content.

### 1.2 MOV (ProRes)

**Use case:** Post-production editing pipeline. Highest quality for compositing and color grading.

| Setting | FFmpeg Flag | Default | Valid Range | Notes |
|---------|------------|---------|-------------|-------|
| Codec | `-c:v prores_ks` | prores_ks | prores_ks | Kostya's ProRes encoder (best FFmpeg ProRes) |
| Container | output suffix `.mov` | -- | -- | QuickTime container required for ProRes |
| Profile | `-profile:v` | 3 (HQ) | 0=Proxy, 1=LT, 2=422, 3=HQ, 4=4444, 5=4444XQ | See profile table below |
| Pixel format (422) | `-pix_fmt yuv422p10le` | yuv422p10le | yuv422p10le | 10-bit 4:2:2 for profiles 0-3 |
| Pixel format (4444) | `-pix_fmt yuva444p10le` | yuva444p10le | yuva444p10le | 10-bit 4:4:4 + alpha for profiles 4-5 |
| Vendor tag | `-vendor apl0` | apl0 | apl0 | Required for Apple compatibility |

**ProRes Profile Reference:**

| Profile | Value | FourCC | Target Bitrate (1080p30) | Chroma | Use Case |
|---------|-------|--------|--------------------------|--------|----------|
| Proxy | 0 | apco | ~45 Mbps | 4:2:2 | Offline editing, low storage |
| LT | 1 | apcs | ~102 Mbps | 4:2:2 | Lightweight editing |
| 422 | 2 | apcn | ~147 Mbps | 4:2:2 | Standard post-production |
| 422 HQ | 3 | apch | ~220 Mbps | 4:2:2 | High-quality mastering |
| 4444 | 4 | ap4h | ~330 Mbps | 4:4:4 | VFX/compositing with alpha |
| 4444 XQ | 5 | ap4x | ~500 Mbps | 4:4:4 | HDR / maximum quality |

**Why it matters:** ProRes preserves every bit of the glitch effect detail. If the user plans to bring footage into Premiere, Final Cut, or DaVinci Resolve for further editing, this avoids generation loss from H.264 recompression.

### 1.3 GIF

**Use case:** Short loops for social sharing, embedding in web pages, quick previews.

| Setting | FFmpeg Flag | Default | Valid Range | Notes |
|---------|------------|---------|-------------|-------|
| Palette generation | `-filter_complex "[0:v]palettegen=max_colors=N"` | 256 | 2-256 | Fewer colors = smaller file |
| Palette mode | `stats_mode=` | full | full, diff, single | `diff` better for motion, `full` for static |
| Dithering | `dither=` | sierra2_4a | none, bayer, floyd_steinberg, sierra2, sierra2_4a | Controls color approximation method |
| Bayer scale | `bayer_scale=` | 2 | 0-5 | Only applies when dither=bayer; lower = more visible pattern |
| Loop count | `-loop` | 0 | 0 = infinite, 1-65535 | 0 means loop forever |
| FPS override | `-r` | 15 | 1-30 | GIFs should be 10-15 fps to keep file size sane |
| Max width | via `-vf scale=` | 480 | 120-1920 | GIFs above 480px get enormous |

**Two-pass GIF pipeline:**
```bash
# Pass 1: Generate optimal palette
ffmpeg -i input.mp4 -vf "fps=15,scale=480:-1:flags=lanczos,palettegen=max_colors=256:stats_mode=full" palette.png

# Pass 2: Apply palette with dithering
ffmpeg -i input.mp4 -i palette.png -lavfi "fps=15,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=sierra2_4a" -loop 0 output.gif
```

**Why it matters:** GIFs are the universal format for sharing short visual loops. Critical for showing off glitch effects on social media, Discord, forums. File size management (palette + dithering) is the entire game.

### 1.4 PNG Sequence

**Use case:** Frame-by-frame compositing in After Effects, Nuke, or Blender. Maximum quality, no temporal compression.

| Setting | FFmpeg Flag | Default | Valid Range | Notes |
|---------|------------|---------|-------------|-------|
| Codec | `-c:v png` | png | png | Lossless compression |
| Pixel format | `-pix_fmt` | rgb24 | rgb24, rgba, rgb48be, rgba64be | `rgba` for alpha, `rgb48be` for 16-bit |
| Compression level | `-compression_level` | 6 | 0-9 | 0=fastest (larger files), 9=slowest (smallest). Does NOT affect quality. |
| Naming pattern | output path | `frame_%06d.png` | -- | 6-digit zero-padded frame number |
| Start number | `-start_number` | 1 | 0+ | First frame number in sequence |

**Why it matters:** PNG sequences are the gold standard for VFX compositing. Each frame is a standalone lossless image. Users doing After Effects work or multi-layer compositing need this.

### 1.5 WebM (VP9)

**Use case:** Web embedding with smaller file sizes than H.264. Supported in Chrome, Firefox, Edge. Open format.

| Setting | FFmpeg Flag | Default | Valid Range | Notes |
|---------|------------|---------|-------------|-------|
| Codec | `-c:v libvpx-vp9` | libvpx-vp9 | libvpx-vp9 | VP9 encoder |
| Container | output suffix `.webm` | -- | -- | WebM container |
| CRF | `-crf` | 31 | 0-63 | Lower = better quality. 15-35 recommended range |
| Bitrate (for CQ mode) | `-b:v 0` | 0 | 0 (for pure CQ) or target bitrate | Set to 0 for constant quality mode |
| Bitrate cap | `-b:v` | 2M | 500k-50M | Maximum bitrate for constrained quality |
| Speed | `-speed` | 2 | 0-4 (VOD) | 0=slowest/best, 4=fastest/worst |
| Tile columns | `-tile-columns` | 2 | 0-6 | Enables multi-threaded encoding |
| Row MT | `-row-mt 1` | 1 | 0, 1 | Row-based multi-threading |
| Pixel format | `-pix_fmt` | yuv420p | yuv420p, yuva420p | yuva420p for alpha channel support |

**Why it matters:** WebM/VP9 achieves 30-50% better compression than H.264 at the same quality. Ideal for web embedding where bandwidth matters. Also supports alpha channel transparency, which H.264 cannot do.

---

## 2. Resolution and Scaling

### 2.1 Preset Resolutions

| Name | Dimensions | Typical Use |
|------|-----------|-------------|
| 480p | 854x480 | Quick preview, mobile |
| 720p | 1280x720 | Social media, web |
| 1080p | 1920x1080 | Standard HD delivery |
| 1440p (2K) | 2560x1440 | High-res displays |
| 2160p (4K) | 3840x2160 | UHD / maximum quality |

**FFmpeg flag:** `-vf scale=W:H`

**Default:** Match source resolution (no scaling).

### 2.2 Custom Dimensions

Allow user to specify exact width and height.

| Setting | FFmpeg Flag | Default | Valid Range | Notes |
|---------|------------|---------|-------------|-------|
| Width | `-vf scale=W:` | source width | 120-7680 | Must be even number for most codecs |
| Height | `-vf scale=:H` | source height | 120-4320 | Must be even number for most codecs |

**Enforcement:** Both width and height are rounded to nearest even number before passing to FFmpeg. Odd dimensions cause encoder failures.

### 2.3 Scale Factor

Instead of absolute dimensions, scale relative to source.

| Setting | FFmpeg Flag | Default | Valid Range | Notes |
|---------|------------|---------|-------------|-------|
| Scale factor | `-vf scale=iw*S:ih*S` | 1.0 | 0.25-4.0 | 0.5 = half size, 2.0 = double |

**Default:** 1.0 (original size).

### 2.4 Aspect Ratio Handling

| Mode | FFmpeg Flag | Behavior |
|------|------------|----------|
| Maintain (fit) | `scale=W:H:force_original_aspect_ratio=decrease` | Fits within bounds, may be smaller than target |
| Fill | `scale=W:H:force_original_aspect_ratio=increase,crop=W:H` | Fills target, crops overflow |
| Stretch | `scale=W:H` | Distorts to exact dimensions |
| Pad (letterbox) | `scale=W:H:force_original_aspect_ratio=decrease,pad=W:H:(ow-iw)/2:(oh-ih)/2:color=black` | Fits within bounds, pads with color |

**Default:** `maintain` -- fit within target dimensions without distortion.

**Pad color options:** `black` (default), `white`, custom hex (e.g. `0x1a1a1a`).

**Why it matters:** Users posting to Instagram (1:1, 4:5, 9:16) or YouTube (16:9) need precise control over how their glitch art fits the target aspect ratio. Stretching glitch art destroys the effect. Padding preserves it.

---

## 3. Quality Settings per Format

### 3.1 H.264 Quality

#### Rate Control Mode

| Mode | FFmpeg Flags | Default | Notes |
|------|-------------|---------|-------|
| CRF (Constant Rate Factor) | `-crf N` | Yes (default) | Best for file-based delivery. Consistent quality throughout. |
| VBR 1-pass | `-b:v N -maxrate M -bufsize B` | No | Target average bitrate. Faster than 2-pass. |
| VBR 2-pass | Pass 1: `-pass 1 -f null /dev/null`, Pass 2: `-pass 2 -b:v N` | No | Best bitrate accuracy. 2x encode time. |
| CBR | `-b:v N -maxrate N -minrate N -bufsize N` | No | Fixed bitrate. Streaming / broadcast use. |

#### CRF Values

| Setting | FFmpeg Flag | Default | Valid Range | Notes |
|---------|------------|---------|-------------|-------|
| CRF | `-crf` | 20 | 0-51 | 0=lossless, 18=visually transparent, 23=good, 28=acceptable, 51=worst |

**Entropic default is CRF 20** (slightly better than FFmpeg's default of 23) because glitch art has high-frequency detail that compresses poorly. Artifacts in glitch art look like bugs, not compression.

#### Encoding Preset

| Setting | FFmpeg Flag | Default | Options | Notes |
|---------|------------|---------|---------|-------|
| Preset | `-preset` | medium | ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow | Speed vs. compression efficiency |

| Preset | Approximate Speed | File Size (relative) | Use Case |
|--------|-------------------|---------------------|----------|
| ultrafast | 10x | 150% | Quick preview renders |
| fast | 3x | 110% | Draft exports |
| medium | 1x (baseline) | 100% | General use |
| slow | 0.5x | 95% | Final delivery |
| veryslow | 0.2x | 90% | Archive / maximum compression |

**Default:** `medium` -- good balance. Users can switch to `fast` for preview renders or `slow` for final delivery.

#### Bitrate (for VBR/CBR modes)

| Setting | FFmpeg Flag | Default | Valid Range | Notes |
|---------|------------|---------|-------------|-------|
| Target bitrate | `-b:v` | 8M | 500k-100M | Average target bitrate |
| Max bitrate | `-maxrate` | 12M | 500k-150M | Peak bitrate cap |
| Buffer size | `-bufsize` | 16M | 1M-200M | Rate control buffer |

### 3.2 ProRes Quality

ProRes quality is controlled entirely by profile selection (see Section 1.2). There is no CRF or bitrate control -- the codec determines its own bitrate based on the content.

| Setting | FFmpeg Flag | Default | Valid Range |
|---------|------------|---------|-------------|
| Profile | `-profile:v` | 3 (HQ) | 0-5 (see profile table in Section 1.2) |
| Quantization | `-qscale:v` | (auto) | 0-64 | Optional: lower = higher quality/larger file |

### 3.3 GIF Quality

See Section 1.3 for full GIF pipeline. Key quality controls:

| Setting | Default | Impact |
|---------|---------|--------|
| Max colors | 256 | Fewer colors = smaller file, more banding |
| Dithering | sierra2_4a | Better dithering = smoother gradients, larger file |
| FPS | 15 | Lower fps = smaller file, choppier motion |
| Max width | 480 | Smaller = much smaller file |

**Estimated file sizes (5-second clip):**
- 480px, 15fps, 256 colors: ~2-5 MB
- 320px, 10fps, 128 colors: ~0.5-2 MB
- 640px, 24fps, 256 colors: ~5-15 MB

### 3.4 WebM Quality

| Setting | FFmpeg Flag | Default | Valid Range | Notes |
|---------|------------|---------|-------------|-------|
| CRF | `-crf` | 31 | 0-63 | VP9 CRF scale. 31 is good quality. |
| Bitrate mode | See below | CQ | CQ, Constrained, VBR | CQ recommended for file-based |
| Speed | `-speed` | 2 | 0-4 | 0=best quality, 4=fastest |

**Bitrate modes:**
- **CQ (Constant Quality):** `-crf 31 -b:v 0` -- Pure quality target, variable file size
- **Constrained Quality:** `-crf 31 -b:v 2M` -- Quality target with bitrate cap
- **VBR:** `-b:v 2M -minrate 1M -maxrate 4M` -- Traditional variable bitrate

---

## 4. Frame Rate

### 4.1 Options

| Setting | FFmpeg Flag | Default | Notes |
|---------|------------|---------|-------|
| Match source | (no -r flag) | Yes (default) | Uses source video's frame rate |
| 23.976 | `-r 24000/1001` | -- | Film standard (NTSC pulldown) |
| 24 | `-r 24` | -- | Cinema |
| 25 | `-r 25` | -- | PAL broadcast |
| 29.97 | `-r 30000/1001` | -- | NTSC broadcast |
| 30 | `-r 30` | -- | Web / social media common |
| 50 | `-r 50` | -- | PAL high frame rate |
| 59.94 | `-r 60000/1001` | -- | NTSC high frame rate |
| 60 | `-r 60` | -- | Smooth motion / gaming |
| Custom | `-r N` | -- | Any positive float |

**Valid range for custom:** 1.0 - 120.0

**Why it matters:** Frame rate affects the feel of glitch effects. Some effects look better at lower frame rates (more "broken" feel) while smooth 60fps gives a different aesthetic. Users posting to Instagram (30fps max) or YouTube (any) need control.

---

## 5. Trim / Range Selection

### 5.1 Options

| Mode | FFmpeg Flags | Default | Notes |
|------|-------------|---------|-------|
| Full video | (no trim flags) | Yes (default) | Exports entire source |
| Frame range | `-vf "select='between(n,START,END)'" -vsync vfr` | -- | Start and end frame numbers (0-indexed) |
| Time range | `-ss START -to END` | -- | Start and end in seconds or HH:MM:SS.mmm |
| Duration | `-ss START -t DURATION` | -- | Start time + duration |

**Time format:** Accepts both seconds (e.g. `12.5`) and timecode (e.g. `00:00:12.500`).

| Setting | Default | Valid Range | Notes |
|---------|---------|-------------|-------|
| Start frame | 0 | 0 to total_frames-1 | Inclusive |
| End frame | total_frames-1 | start_frame to total_frames-1 | Inclusive |
| Start time | 0.0 | 0.0 to duration | Seconds |
| End time | duration | start_time to duration | Seconds |

**Why it matters:** Users often want to export just the best section of a glitched video. Frame-level precision matters for glitch art where a single frame can be the "money shot."

---

## 6. Pre-export Processing

### 6.1 Scaling Algorithm

| Algorithm | FFmpeg `sws_flags` | Default | Best For |
|-----------|-------------------|---------|----------|
| Lanczos | `lanczos` | Yes (default) | Downscaling. Sharpest, slight ringing on edges. Best for live-action and detailed content. |
| Bicubic | `bicubic` | -- | General purpose. Good balance of sharpness and smoothness. |
| Bilinear | `bilinear` | -- | Fast. Softer results. OK for previews. |
| Nearest Neighbor | `neighbor` | -- | Pixel art / intentional blocky look. Preserves hard edges. Critical for some glitch aesthetics. |
| Area | `area` | -- | Best for large downscale factors (e.g. 4K to 480p). Averages pixels. |
| Sinc | `sinc` | -- | Mathematically ideal but slow. |
| Spline | `spline` | -- | Smooth interpolation, less ringing than Lanczos. |

**Applied via:** `-vf "scale=W:H:flags=lanczos"`

**Default for upscaling:** `lanczos`
**Default for downscaling:** `lanczos`

**Why it matters for Entropic specifically:** Nearest neighbor scaling is a glitch aesthetic tool in itself. Upscaling a 240p glitched video to 1080p with nearest neighbor gives a chunky pixel look. Lanczos would smooth it out. This is a creative choice, not just a technical one.

### 6.2 Crop

| Setting | FFmpeg Flag | Default | Valid Range | Notes |
|---------|------------|---------|-------------|-------|
| Crop width | `-vf crop=W:H:X:Y` | source width | 1 to source width | Output width after crop |
| Crop height | (part of above) | source height | 1 to source height | Output height after crop |
| Crop X offset | (part of above) | 0 | 0 to (source_width - crop_width) | Left edge position |
| Crop Y offset | (part of above) | 0 | 0 to (source_height - crop_height) | Top edge position |

**Center crop shorthand:** `crop=W:H` (auto-centers).

### 6.3 Padding (Letterbox / Pillarbox)

| Setting | FFmpeg Flag | Default | Notes |
|---------|------------|---------|-------|
| Pad to dimensions | `-vf pad=W:H:(ow-iw)/2:(oh-ih)/2:color` | -- | Centers video within padded frame |
| Pad color | `:color=black` | black | black, white, or hex color (e.g. `0x1a1a1a`) |

**Common use cases:**
- 16:9 video to 1:1 (Instagram square): pad with black bars top/bottom
- 16:9 video to 9:16 (Stories/Reels/TikTok): pad with black bars left/right (pillarbox)
- Add breathing room around glitch art

---

## 7. Audio

### 7.1 Options

| Mode | FFmpeg Flags | Default | Notes |
|------|-------------|---------|-------|
| Copy from source | `-c:a copy` | -- | Fastest. No re-encoding. May fail if container doesn't support source codec. |
| Re-encode AAC | `-c:a aac -b:a BITRATE` | Yes (default) | Universal compatibility |
| Strip audio | `-an` | -- | No audio in output. Smaller file. |

### 7.2 AAC Re-encode Settings

| Setting | FFmpeg Flag | Default | Valid Range | Notes |
|---------|------------|---------|-------------|-------|
| Bitrate | `-b:a` | 192k | 64k, 96k, 128k, 160k, 192k, 256k, 320k | Higher = better quality, larger file |
| Sample rate | `-ar` | 44100 | 22050, 32000, 44100, 48000 | Match source recommended |
| Channels | `-ac` | 2 (stereo) | 1 (mono), 2 (stereo) | Mono halves audio file size |

**Quality reference:**
- 128k stereo: Acceptable for web / social media
- 192k stereo: Good quality (Entropic default)
- 256k stereo: High quality, hard to distinguish from lossless
- 320k stereo: Maximum AAC quality

### 7.3 Audio Handling by Format

| Format | Audio Support | Default Behavior |
|--------|--------------|-----------------|
| MP4 (H.264) | Yes | Re-encode to AAC 192k |
| MOV (ProRes) | Yes | Re-encode to AAC 256k |
| WebM (VP9) | Yes (Opus/Vorbis) | Re-encode to libopus 128k (`-c:a libopus -b:a 128k`) |
| GIF | No | Automatically stripped |
| PNG sequence | No | Automatically stripped |

**Why it matters:** Many glitch effects are applied to music videos. Losing or corrupting the audio would ruin the output. The default should be "preserve audio, re-encode for compatibility."

---

## 8. Export Presets

Ship these presets out of the box. Users can also save custom presets.

### 8.1 Built-in Presets

| Preset Name | Format | Resolution | Quality | FPS | Audio | Notes |
|-------------|--------|------------|---------|-----|-------|-------|
| `quick_preview` | mp4 | 480p | CRF 28, fast | match | strip | Fast preview, small file |
| `social_media` | mp4 | 1080p | CRF 20, medium | 30 | AAC 192k | Instagram, Twitter, general |
| `youtube_hd` | mp4 | 1080p | CRF 18, slow | match | AAC 256k | YouTube upload optimized |
| `youtube_4k` | mp4 | 2160p | CRF 18, slow | match | AAC 256k | YouTube 4K upload |
| `instagram_square` | mp4 | 1080x1080 | CRF 20, medium | 30 | AAC 192k | 1:1 with padding |
| `instagram_story` | mp4 | 1080x1920 | CRF 20, medium | 30 | AAC 192k | 9:16 with padding |
| `tiktok` | mp4 | 1080x1920 | CRF 20, medium | 30 | AAC 192k | 9:16 vertical video |
| `web_embed` | webm | 720p | CRF 31, speed 2 | match | opus 128k | Small file for websites |
| `gif_loop` | gif | 480p | 256 colors, sierra2_4a | 15 | -- | Social sharing loops |
| `gif_tiny` | gif | 320p | 128 colors, bayer | 10 | -- | Ultra-small for messaging |
| `editing_proxy` | mov | match | ProRes Proxy | match | AAC 192k | Lightweight editing proxy |
| `editing_hq` | mov | match | ProRes 422 HQ | match | AAC 256k | High-quality editing master |
| `compositing` | mov | match | ProRes 4444 | match | AAC 256k | VFX with alpha channel |
| `frame_sequence` | png | match | lossless | match | -- | PNG sequence for compositing |
| `archive` | mp4 | match | CRF 14, veryslow | match | AAC 320k | Maximum quality archive |

### 8.2 Custom Presets

Users can save any configuration as a named preset. Stored as JSON in the project directory under `presets/export/`.

```json
{
  "name": "my_instagram_preset",
  "created": "2026-02-07T12:00:00",
  "settings": { ... }  // Full ExportSettings model
}
```

---

## 9. FFmpeg Command Construction

### 9.1 Command Template

The export system constructs FFmpeg commands in this order:

```
ffmpeg [input_options] -i input [filter_chain] [video_codec_options] [audio_options] [output_options] output_path
```

### 9.2 Filter Chain Construction

Filters are applied in this order via `-vf` (or `-filter_complex` for GIF):

1. **Trim** (if specified): `trim=start_frame=N:end_frame=M`
2. **Crop** (if specified): `crop=W:H:X:Y`
3. **Scale** (if not match source): `scale=W:H:flags=lanczos`
4. **Pad** (if specified): `pad=W:H:(ow-iw)/2:(oh-ih)/2:color`
5. **FPS** (if not match source): `fps=N`

Example combined filter: `-vf "crop=1920:1080:0:0,scale=1280:720:flags=lanczos,fps=30"`

### 9.3 Full Command Examples

**MP4 for YouTube (1080p):**
```bash
ffmpeg -y \
  -framerate 30 -i frames/frame_%06d.png \
  -i original.mp4 -map 0:v -map 1:a? -shortest \
  -vf "scale=1920:1080:flags=lanczos" \
  -c:v libx264 -crf 18 -preset slow -profile:v high -level 4.1 -pix_fmt yuv420p \
  -c:a aac -b:a 256k -ar 48000 \
  output.mp4
```

**ProRes 422 HQ for editing:**
```bash
ffmpeg -y \
  -framerate 24 -i frames/frame_%06d.png \
  -i original.mp4 -map 0:v -map 1:a? -shortest \
  -c:v prores_ks -profile:v 3 -pix_fmt yuv422p10le -vendor apl0 \
  -c:a aac -b:a 256k \
  output.mov
```

**GIF loop (2-pass):**
```bash
# Pass 1: palette
ffmpeg -y -framerate 30 -i frames/frame_%06d.png \
  -vf "fps=15,scale=480:-1:flags=lanczos,palettegen=max_colors=256:stats_mode=full" \
  /tmp/palette.png

# Pass 2: encode
ffmpeg -y -framerate 30 -i frames/frame_%06d.png -i /tmp/palette.png \
  -lavfi "fps=15,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=sierra2_4a" \
  -loop 0 \
  output.gif
```

**WebM for web embed:**
```bash
ffmpeg -y \
  -framerate 30 -i frames/frame_%06d.png \
  -i original.mp4 -map 0:v -map 1:a? -shortest \
  -vf "scale=1280:720:flags=lanczos" \
  -c:v libvpx-vp9 -crf 31 -b:v 0 -speed 2 -tile-columns 2 -row-mt 1 -pix_fmt yuv420p \
  -c:a libopus -b:a 128k \
  output.webm
```

**PNG sequence:**
```bash
ffmpeg -y \
  -framerate 30 -i frames/frame_%06d.png \
  -c:v png -pix_fmt rgb24 -compression_level 6 \
  -start_number 1 \
  output/frame_%06d.png
```

---

## 10. Validation Rules

The Pydantic model enforces these constraints before FFmpeg execution:

1. **ProRes requires MOV container** -- If format is `prores`, output must be `.mov`.
2. **GIF has no audio** -- `audio_mode` is forced to `strip` for GIF format.
3. **PNG sequence has no audio** -- Same as above.
4. **Even dimensions** -- Width and height are rounded to nearest even number.
5. **CRF range per codec** -- H.264: 0-51. VP9: 0-63.
6. **ProRes profile + pixel format** -- Profiles 0-3 use yuv422p10le. Profiles 4-5 use yuva444p10le.
7. **Bitrate sanity** -- Max bitrate must be >= target bitrate.
8. **Frame range sanity** -- End frame must be > start frame.
9. **Time range sanity** -- End time must be > start time.
10. **GIF dimensions warning** -- Warn (don't block) if GIF width > 640px.
11. **Scale factor bounds** -- 0.25x to 4.0x only.
12. **Custom FPS bounds** -- 1.0 to 120.0.

---

## 11. API Endpoint Design

### 11.1 New Render Endpoint

Replace the current `/api/render` with:

```
POST /api/export
Body: ExportSettings (see Pydantic model)
Response: { status, path, size_mb, duration_seconds, format, estimated_bitrate }
```

### 11.2 Preset Endpoints

```
GET  /api/export/presets          -- List all presets (built-in + custom)
GET  /api/export/presets/{name}   -- Get a specific preset's settings
POST /api/export/presets          -- Save a custom preset
DELETE /api/export/presets/{name} -- Delete a custom preset (built-in cannot be deleted)
```

### 11.3 Estimate Endpoint

```
POST /api/export/estimate
Body: ExportSettings
Response: { estimated_size_mb, estimated_duration_seconds, warnings: [] }
```

This lets the UI show an estimated file size and render time before the user commits to a full export.

---

## 12. Migration Path

### Phase 1: Model + Presets (Current)
- Write `ExportSettings` Pydantic model
- Write preset definitions
- Add validation

### Phase 2: FFmpeg Builder
- Write `build_ffmpeg_command(settings: ExportSettings) -> list[str]` function
- Handle 2-pass GIF pipeline
- Handle 2-pass VBR

### Phase 3: Integration
- Replace `reassemble_video()` in `core/video_io.py` with new export engine
- Update `/api/render` endpoint to accept `ExportSettings`
- Backward compatibility: map old `quality: "lo"/"mid"/"hi"` to presets

### Phase 4: UI
- Export dialog in web UI with preset dropdown and advanced options
- Real-time estimated file size
- Progress reporting via WebSocket

---

## References

- [Adobe Premiere Pro Export Settings Reference](https://helpx.adobe.com/premiere-pro/using/export-settings-reference-premiere-pro.html)
- [Premiere Pro Encoding Settings](https://helpx.adobe.com/premiere-pro/using/encoding-settings.html)
- [Photoshop Save for Web](https://helpx.adobe.com/photoshop/desktop/save-and-export/save-files/save-for-web.html)
- [VP9 Encoding Guide (WebM Project)](https://wiki.webmproject.org/ffmpeg/vp9-encoding-guide)
- [VP9 Bitrate Modes (Google)](https://developers.google.com/media/vp9/bitrate-modes)
- [High Quality GIF with FFmpeg](https://blog.pkh.me/p/21-high-quality-gif-with-ffmpeg.html)
- [FFmpeg Scaler Documentation](https://ffmpeg.org/ffmpeg-scaler.html)
- [CRF Guide (x264, x265, libvpx)](https://slhck.info/video/2017/02/24/crf-guide.html)
- [Understanding Rate Control Modes](https://slhck.info/video/2017/03/01/rate-control.html)
- [ProRes FFmpeg Guide](https://github.com/oyvindln/vhs-decode/wiki/ProRes-The-Definitive-FFmpeg-Guide)
- [FFmpeg Compression Parameters Guide](https://www.videoscompress.com/blog/FFmpeg-Compression-Parameters-Guide)

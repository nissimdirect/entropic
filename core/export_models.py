"""
Entropic -- Export Settings Models

Pydantic models for the comprehensive export system.
Maps 1:1 to FFmpeg flags. See docs/EXPORT-SPEC.md for full specification.

Inspired by Adobe Premiere Pro Media Encoder and Photoshop Export As dialogs.
Every option maps directly to an FFmpeg flag -- no leaky abstractions.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ExportFormat(str, Enum):
    """Output container / format."""
    MP4 = "mp4"          # H.264 in MP4 container -- web/social
    MOV = "mov"          # ProRes in QuickTime container -- editing pipeline
    GIF = "gif"          # Animated GIF -- short loops, social sharing
    PNG_SEQ = "png_seq"  # PNG image sequence -- compositing
    WEBM = "webm"        # VP9 in WebM container -- web embedding


class H264Profile(str, Enum):
    """H.264 encoding profile. Higher = better compression, less compatible."""
    BASELINE = "baseline"  # Video conferencing, fast decode
    MAIN = "main"          # SD broadcast
    HIGH = "high"          # HD devices (most common)
    HIGH10 = "high10"      # 10-bit decode support


class H264Preset(str, Enum):
    """Encoding speed vs. compression efficiency tradeoff.

    Slower presets produce smaller files at the same quality.
    Does NOT affect visual quality -- only file size and encode time.
    """
    ULTRAFAST = "ultrafast"  # ~10x speed, ~150% file size
    SUPERFAST = "superfast"
    VERYFAST = "veryfast"
    FASTER = "faster"
    FAST = "fast"            # ~3x speed, ~110% file size
    MEDIUM = "medium"        # 1x baseline
    SLOW = "slow"            # ~0.5x speed, ~95% file size
    SLOWER = "slower"
    VERYSLOW = "veryslow"    # ~0.2x speed, ~90% file size


class H264RateControl(str, Enum):
    """Bitrate control strategy for H.264 encoding."""
    CRF = "crf"         # Constant Rate Factor -- best for files (default)
    VBR_1PASS = "vbr1"  # Variable Bitrate, single pass -- faster
    VBR_2PASS = "vbr2"  # Variable Bitrate, two-pass -- best bitrate accuracy
    CBR = "cbr"          # Constant Bitrate -- streaming/broadcast


class ProResProfile(int, Enum):
    """ProRes profile. Maps directly to FFmpeg -profile:v value.

    Higher profiles = higher quality = larger files.
    Profiles 0-3 are 4:2:2 (no alpha). Profiles 4-5 are 4:4:4 (with alpha).
    """
    PROXY = 0      # ~45 Mbps @ 1080p30, 4:2:2, offline editing
    LT = 1         # ~102 Mbps, 4:2:2, lightweight editing
    STANDARD = 2   # ~147 Mbps, 4:2:2, standard post-production
    HQ = 3         # ~220 Mbps, 4:2:2, high-quality mastering
    P4444 = 4      # ~330 Mbps, 4:4:4 + alpha, VFX/compositing
    P4444XQ = 5    # ~500 Mbps, 4:4:4 + alpha, HDR/maximum quality


class GifDither(str, Enum):
    """GIF dithering algorithm for color reduction.

    Dithering approximates colors not in the palette by mixing nearby colors.
    """
    NONE = "none"                    # No dithering -- banding visible
    BAYER = "bayer"                  # Ordered dithering -- crosshatch pattern
    FLOYD_STEINBERG = "floyd_steinberg"  # Error diffusion -- smooth
    SIERRA2 = "sierra2"             # Error diffusion -- slightly different
    SIERRA2_4A = "sierra2_4a"       # Fast approximation of Sierra (default)


class GifStatsMode(str, Enum):
    """How palettegen analyzes the video for optimal palette."""
    FULL = "full"      # Analyze entire video as one block
    DIFF = "diff"      # Favor pixels that change (better for motion)
    SINGLE = "single"  # Single-frame palette


class ScaleAlgorithm(str, Enum):
    """FFmpeg sws_flags scaling algorithm.

    Applied via: -vf "scale=W:H:flags=<value>"
    """
    LANCZOS = "lanczos"    # Sharpest, slight ringing. Best general-purpose.
    BICUBIC = "bicubic"    # Good balance of sharpness and smoothness.
    BILINEAR = "bilinear"  # Fast, softer results. OK for previews.
    NEAREST = "neighbor"   # Pixel-art / intentional blocky look. Preserves hard edges.
    AREA = "area"          # Best for large downscale factors (e.g. 4K to 480p).
    SINC = "sinc"          # Mathematically ideal, slow.
    SPLINE = "spline"      # Smooth interpolation, less ringing than Lanczos.


class AspectMode(str, Enum):
    """How to handle aspect ratio mismatch between source and target dimensions."""
    MAINTAIN = "maintain"  # Fit within bounds, may be smaller than target
    FILL = "fill"          # Fill target dimensions, crop overflow
    STRETCH = "stretch"    # Distort to exact dimensions
    PAD = "pad"            # Fit within bounds, pad remainder with color


class AudioMode(str, Enum):
    """Audio handling strategy."""
    COPY = "copy"          # Passthrough -- fastest, no re-encoding
    REENCODE = "reencode"  # Re-encode to AAC (or Opus for WebM)
    STRIP = "strip"        # Remove audio entirely


class TrimMode(str, Enum):
    """How to specify the export range."""
    FULL = "full"          # Export entire video
    FRAMES = "frames"      # Specify start/end frame numbers
    TIME = "time"          # Specify start/end timestamps (seconds)


class PngPixelFormat(str, Enum):
    """PNG pixel format. Controls bit depth and alpha channel."""
    RGB24 = "rgb24"          # 8-bit RGB, no alpha
    RGBA = "rgba"            # 8-bit RGBA with alpha channel
    RGB48BE = "rgb48be"      # 16-bit RGB, no alpha
    RGBA64BE = "rgba64be"    # 16-bit RGBA with alpha channel


# ---------------------------------------------------------------------------
# Codec Sub-models
# ---------------------------------------------------------------------------

class H264Settings(BaseModel):
    """H.264 (libx264) codec-specific settings.

    FFmpeg flags:
        -c:v libx264 -crf {crf} -preset {preset} -profile:v {profile}
        -level {level} -pix_fmt {pixel_format}

    For VBR/CBR modes:
        -b:v {target_bitrate} -maxrate {max_bitrate} -bufsize {bufsize}
    """
    profile: H264Profile = Field(
        default=H264Profile.HIGH,
        description="H.264 profile. 'high' for HD, 'baseline' for max compatibility.",
    )
    preset: H264Preset = Field(
        default=H264Preset.MEDIUM,
        description="Encoding speed vs. compression. Slower = smaller file at same quality.",
    )
    rate_control: H264RateControl = Field(
        default=H264RateControl.CRF,
        description="Rate control mode. CRF is best for file-based delivery.",
    )
    crf: int = Field(
        default=20,
        ge=0,
        le=51,
        description=(
            "Constant Rate Factor (0-51). "
            "0=lossless, 18=visually transparent, 23=good default, 28=acceptable. "
            "Entropic default is 20 because glitch art has high-frequency detail."
        ),
    )
    target_bitrate: str = Field(
        default="8M",
        description="Target bitrate for VBR/CBR modes (e.g. '8M', '5000k').",
    )
    max_bitrate: str = Field(
        default="12M",
        description="Max bitrate cap for VBR mode (e.g. '12M').",
    )
    bufsize: str = Field(
        default="16M",
        description="Rate control buffer size (e.g. '16M').",
    )
    pixel_format: Literal["yuv420p", "yuv422p", "yuv444p"] = Field(
        default="yuv420p",
        description="Chroma subsampling. yuv420p for maximum browser/device compatibility.",
    )
    level: str = Field(
        default="4.1",
        description="H.264 level. Constrains resolution/bitrate combinations.",
    )


class ProResSettings(BaseModel):
    """ProRes (prores_ks) codec-specific settings.

    FFmpeg flags:
        -c:v prores_ks -profile:v {profile} -pix_fmt {pixel_format} -vendor apl0

    ProRes quality is controlled entirely by profile selection.
    There is no CRF or bitrate control.
    """
    profile: ProResProfile = Field(
        default=ProResProfile.HQ,
        description="ProRes profile. HQ (3) is a good default for mastering.",
    )

    @property
    def pixel_format(self) -> str:
        """Pixel format is determined by profile.

        Profiles 0-3 (422 variants): yuv422p10le (10-bit 4:2:2)
        Profiles 4-5 (4444 variants): yuva444p10le (10-bit 4:4:4 + alpha)
        """
        if self.profile.value >= 4:
            return "yuva444p10le"
        return "yuv422p10le"


class GifSettings(BaseModel):
    """GIF-specific settings.

    GIF export uses a 2-pass FFmpeg pipeline:
        Pass 1 (palettegen): Generate optimal 256-color palette
        Pass 2 (paletteuse): Encode frames using palette + dithering

    FFmpeg filter_complex:
        "[0:v]fps={fps},scale={max_width}:-1:flags=lanczos,
         palettegen=max_colors={max_colors}:stats_mode={stats_mode}"
        "[0:v]fps={fps},scale={max_width}:-1:flags=lanczos[x];
         [x][1:v]paletteuse=dither={dither}"
    Output flag: -loop {loop_count}
    """
    max_colors: int = Field(
        default=256,
        ge=2,
        le=256,
        description="Maximum palette colors (2-256). Fewer = smaller file, more banding.",
    )
    dither: GifDither = Field(
        default=GifDither.SIERRA2_4A,
        description="Dithering algorithm for color reduction.",
    )
    bayer_scale: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Bayer dithering crosshatch scale (0-5). Only used when dither=bayer.",
    )
    stats_mode: GifStatsMode = Field(
        default=GifStatsMode.FULL,
        description="Palette analysis mode. 'diff' favors moving content.",
    )
    loop_count: int = Field(
        default=0,
        ge=0,
        le=65535,
        description="GIF loop count. 0 = infinite loop.",
    )
    fps: int = Field(
        default=15,
        ge=1,
        le=30,
        description="GIF frame rate. 10-15 recommended to keep file size manageable.",
    )
    max_width: int = Field(
        default=480,
        ge=120,
        le=1920,
        description="Maximum width in pixels. Height scaled proportionally.",
    )


class WebMSettings(BaseModel):
    """VP9/WebM codec-specific settings.

    FFmpeg flags:
        -c:v libvpx-vp9 -crf {crf} -b:v {bitrate}
        -speed {speed} -tile-columns {tile_columns}
        -row-mt {1 if row_mt else 0} -pix_fmt {pixel_format}

    For pure constant quality: -b:v 0 (no bitrate cap)
    For constrained quality: -b:v 2M (quality target with bitrate ceiling)
    """
    crf: int = Field(
        default=31,
        ge=0,
        le=63,
        description="VP9 CRF (0-63). Lower = better. 15-35 is the recommended range.",
    )
    bitrate: str = Field(
        default="0",
        description=(
            "Bitrate cap. '0' for pure constant quality mode, "
            "'2M' for constrained quality with bitrate ceiling."
        ),
    )
    speed: int = Field(
        default=2,
        ge=0,
        le=4,
        description="Encoding speed (0-4). 0=best quality (slowest), 4=fastest.",
    )
    tile_columns: int = Field(
        default=2,
        ge=0,
        le=6,
        description="Tile columns for multi-threaded encoding.",
    )
    row_mt: bool = Field(
        default=True,
        description="Enable row-based multi-threading for faster encoding.",
    )
    pixel_format: Literal["yuv420p", "yuva420p"] = Field(
        default="yuv420p",
        description="yuva420p enables alpha channel transparency (VP9 supports this).",
    )


class PngSeqSettings(BaseModel):
    """PNG image sequence export settings.

    FFmpeg flags:
        -c:v png -pix_fmt {pixel_format}
        -compression_level {compression_level}
        -start_number {start_number}
    Output pattern: frame_%06d.png
    """
    pixel_format: PngPixelFormat = Field(
        default=PngPixelFormat.RGB24,
        description="Pixel format. 'rgba' for alpha channel, 'rgb48be' for 16-bit depth.",
    )
    compression_level: int = Field(
        default=6,
        ge=0,
        le=9,
        description=(
            "PNG compression level (0-9). "
            "0=fastest/larger files, 9=slowest/smallest files. "
            "This is lossless compression -- it does NOT affect image quality."
        ),
    )
    start_number: int = Field(
        default=1,
        ge=0,
        description="First frame number in the output sequence.",
    )


# ---------------------------------------------------------------------------
# Processing Sub-models
# ---------------------------------------------------------------------------

class ResolutionSettings(BaseModel):
    """Output resolution and scaling configuration.

    Modes:
        'source'  -- Match input dimensions (no scaling)
        'preset'  -- Named size (480p, 720p, 1080p, 1440p, 2160p)
        'custom'  -- Exact width x height
        'scale'   -- Multiply source by scale_factor
    """
    mode: Literal["source", "preset", "custom", "scale"] = Field(
        default="source",
        description="Resolution mode.",
    )
    preset: Literal["480p", "720p", "1080p", "1440p", "2160p"] | None = Field(
        default=None,
        description="Named resolution preset. Only used when mode='preset'.",
    )
    width: int | None = Field(
        default=None,
        ge=120,
        le=7680,
        description="Custom width in pixels. Rounded to even. Only used when mode='custom'.",
    )
    height: int | None = Field(
        default=None,
        ge=120,
        le=4320,
        description="Custom height in pixels. Rounded to even. Only used when mode='custom'.",
    )
    scale_factor: float = Field(
        default=1.0,
        ge=0.25,
        le=4.0,
        description="Scale relative to source. 0.5=half, 2.0=double. Used when mode='scale'.",
    )
    aspect_mode: AspectMode = Field(
        default=AspectMode.MAINTAIN,
        description="How to handle aspect ratio mismatch between source and target.",
    )
    pad_color: str = Field(
        default="black",
        description="Padding color for 'pad' aspect mode. 'black', 'white', or hex '0x1a1a1a'.",
    )
    upscale_algorithm: ScaleAlgorithm = Field(
        default=ScaleAlgorithm.LANCZOS,
        description="Scaling algorithm when output is larger than source.",
    )
    downscale_algorithm: ScaleAlgorithm = Field(
        default=ScaleAlgorithm.LANCZOS,
        description="Scaling algorithm when output is smaller than source.",
    )

    # Lookup table for preset resolutions (width, height)
    PRESET_DIMENSIONS: dict[str, tuple[int, int]] = {
        "480p": (854, 480),
        "720p": (1280, 720),
        "1080p": (1920, 1080),
        "1440p": (2560, 1440),
        "2160p": (3840, 2160),
    }

    model_config = {"arbitrary_types_allowed": True}

    def resolve_dimensions(
        self, source_width: int, source_height: int
    ) -> tuple[int, int]:
        """Compute final (width, height) given source dimensions.

        Returns even-number dimensions ready for FFmpeg.
        """
        if self.mode == "source":
            w, h = source_width, source_height
        elif self.mode == "preset" and self.preset:
            w, h = self.PRESET_DIMENSIONS[self.preset]
        elif self.mode == "custom" and self.width is not None and self.height is not None:
            w, h = self.width, self.height
        elif self.mode == "scale":
            w = int(source_width * self.scale_factor)
            h = int(source_height * self.scale_factor)
        else:
            w, h = source_width, source_height

        # Ensure even dimensions (required by H.264, ProRes, VP9)
        w += w % 2
        h += h % 2

        # Minimum 16px in each dimension
        w = max(16, w)
        h = max(16, h)

        return w, h

    def get_scale_algorithm(
        self, source_width: int, source_height: int
    ) -> ScaleAlgorithm:
        """Choose the right scaling algorithm based on whether we are
        upscaling or downscaling."""
        target_w, target_h = self.resolve_dimensions(source_width, source_height)
        target_pixels = target_w * target_h
        source_pixels = source_width * source_height
        if target_pixels >= source_pixels:
            return self.upscale_algorithm
        return self.downscale_algorithm


class CropSettings(BaseModel):
    """Optional crop applied before scaling.

    FFmpeg flag: -vf "crop={width}:{height}:{x}:{y}"
    """
    enabled: bool = Field(default=False, description="Whether cropping is active.")
    width: int | None = Field(default=None, ge=1, description="Crop output width in pixels.")
    height: int | None = Field(default=None, ge=1, description="Crop output height in pixels.")
    x: int = Field(default=0, ge=0, description="Horizontal offset from left edge.")
    y: int = Field(default=0, ge=0, description="Vertical offset from top edge.")


class TrimSettings(BaseModel):
    """Trim / range selection for partial exports.

    FFmpeg flags:
        Time mode:  -ss {start_time} -to {end_time}
        Frame mode: -vf "select='between(n,{start_frame},{end_frame})'" -vsync vfr
    """
    mode: TrimMode = Field(
        default=TrimMode.FULL,
        description="'full'=entire video, 'frames'=frame range, 'time'=time range.",
    )
    start_frame: int = Field(
        default=0,
        ge=0,
        description="Start frame number (0-indexed, inclusive). Used when mode='frames'.",
    )
    end_frame: int | None = Field(
        default=None,
        ge=0,
        description="End frame number (inclusive). None = last frame. Used when mode='frames'.",
    )
    start_time: float = Field(
        default=0.0,
        ge=0.0,
        description="Start time in seconds. Used when mode='time'.",
    )
    end_time: float | None = Field(
        default=None,
        ge=0.0,
        description="End time in seconds. None = end of video. Used when mode='time'.",
    )

    @model_validator(mode="after")
    def validate_ranges(self) -> "TrimSettings":
        """Ensure end > start for both frame and time modes."""
        if self.mode == TrimMode.FRAMES:
            if self.end_frame is not None and self.end_frame <= self.start_frame:
                raise ValueError(
                    f"end_frame ({self.end_frame}) must be greater than "
                    f"start_frame ({self.start_frame})"
                )
        if self.mode == TrimMode.TIME:
            if self.end_time is not None and self.end_time <= self.start_time:
                raise ValueError(
                    f"end_time ({self.end_time}) must be greater than "
                    f"start_time ({self.start_time})"
                )
        return self


class AudioSettings(BaseModel):
    """Audio export configuration.

    FFmpeg flags:
        Copy:     -c:a copy
        AAC:      -c:a aac -b:a {bitrate} -ar {sample_rate} -ac {channels}
        Opus:     -c:a libopus -b:a {bitrate}  (for WebM)
        Strip:    -an
    """
    mode: AudioMode = Field(
        default=AudioMode.REENCODE,
        description="'copy'=passthrough, 'reencode'=AAC/Opus, 'strip'=no audio.",
    )
    bitrate: str = Field(
        default="192k",
        description="Audio bitrate for re-encoding. '128k'=web, '192k'=good, '256k'=high.",
    )
    sample_rate: int = Field(
        default=44100,
        description="Sample rate in Hz. 44100 or 48000 recommended.",
    )
    channels: Literal[1, 2] = Field(
        default=2,
        description="1=mono, 2=stereo.",
    )

    VALID_BITRATES: list[str] = [
        "64k", "96k", "128k", "160k", "192k", "256k", "320k",
    ]
    VALID_SAMPLE_RATES: list[int] = [22050, 32000, 44100, 48000]

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def validate_audio(self) -> "AudioSettings":
        if self.bitrate not in self.VALID_BITRATES:
            raise ValueError(
                f"Audio bitrate '{self.bitrate}' not valid. "
                f"Choose from: {', '.join(self.VALID_BITRATES)}"
            )
        if self.sample_rate not in self.VALID_SAMPLE_RATES:
            raise ValueError(
                f"Sample rate {self.sample_rate} not valid. "
                f"Choose from: {self.VALID_SAMPLE_RATES}"
            )
        return self


class FrameRateSettings(BaseModel):
    """Output frame rate configuration.

    FFmpeg flag: -r {value}
    Omitted entirely when matching source (lets FFmpeg use input fps).
    """
    mode: Literal["source", "preset", "custom"] = Field(
        default="source",
        description="'source'=match input, 'preset'=common value, 'custom'=any value.",
    )
    preset: Literal[
        "23.976", "24", "25", "29.97", "30", "50", "59.94", "60"
    ] | None = Field(
        default=None,
        description="Named frame rate. Only used when mode='preset'.",
    )
    custom: float | None = Field(
        default=None,
        ge=1.0,
        le=120.0,
        description="Custom frame rate value. Only used when mode='custom'.",
    )

    # Fractional values for NTSC accuracy
    PRESET_FFMPEG_VALUES: dict[str, str] = {
        "23.976": "24000/1001",
        "24": "24",
        "25": "25",
        "29.97": "30000/1001",
        "30": "30",
        "50": "50",
        "59.94": "60000/1001",
        "60": "60",
    }

    model_config = {"arbitrary_types_allowed": True}

    def resolve_ffmpeg_value(self, source_fps: float | None = None) -> str | None:
        """Return the -r flag value for FFmpeg, or None to match source."""
        if self.mode == "source":
            return None
        if self.mode == "preset" and self.preset:
            return self.PRESET_FFMPEG_VALUES[self.preset]
        if self.mode == "custom" and self.custom is not None:
            return str(self.custom)
        return None

    def resolve_numeric(self, source_fps: float) -> float:
        """Return the output fps as a float for calculations."""
        if self.mode == "source":
            return source_fps
        if self.mode == "preset" and self.preset:
            return float(self.preset)
        if self.mode == "custom" and self.custom is not None:
            return self.custom
        return source_fps


# ---------------------------------------------------------------------------
# Main Export Settings Model
# ---------------------------------------------------------------------------

class ExportSettings(BaseModel):
    """Complete export configuration for Entropic.

    Every field maps to FFmpeg flags. Validation catches invalid
    combinations before FFmpeg runs.

    Quick start:
        ExportSettings()                            # Sensible MP4 default
        ExportSettings(format="gif")                # GIF with defaults
        ExportSettings.from_preset("youtube_hd")    # Named preset
        from_legacy_quality("hi", effects, mix)     # Backward compat
    """

    # -- Format --
    format: ExportFormat = Field(
        default=ExportFormat.MP4,
        description="Output format / container.",
    )

    # -- Effect chain (passed through from the UI) --
    effects: list[dict] = Field(
        default_factory=list,
        description="Effect chain: [{'name': 'pixelsort', 'params': {...}}, ...]",
    )
    mix: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Wet/dry blend. 0.0 = original, 1.0 = fully processed.",
    )

    # -- Codec-specific settings --
    # Only the sub-model matching `format` is used at export time.
    h264: H264Settings = Field(default_factory=H264Settings)
    prores: ProResSettings = Field(default_factory=ProResSettings)
    gif: GifSettings = Field(default_factory=GifSettings)
    webm: WebMSettings = Field(default_factory=WebMSettings)
    png_seq: PngSeqSettings = Field(default_factory=PngSeqSettings)

    # -- Resolution & Scaling --
    resolution: ResolutionSettings = Field(default_factory=ResolutionSettings)

    # -- Crop --
    crop: CropSettings = Field(default_factory=CropSettings)

    # -- Frame Rate --
    frame_rate: FrameRateSettings = Field(default_factory=FrameRateSettings)

    # -- Trim / Range --
    trim: TrimSettings = Field(default_factory=TrimSettings)

    # -- Audio --
    audio: AudioSettings = Field(default_factory=AudioSettings)

    # -- Output filename --
    filename: str | None = Field(
        default=None,
        description="Output filename (without extension). Auto-generated if None.",
    )

    @model_validator(mode="after")
    def validate_format_constraints(self) -> "ExportSettings":
        """Enforce cross-field validation rules.

        1. GIF and PNG sequences cannot have audio.
        2. ProRes requires MOV container (enforced by format enum).
        3. WebM audio should use Opus, not AAC (handled at build time).
        """
        # Force audio strip for formats that don't support it
        if self.format in (ExportFormat.GIF, ExportFormat.PNG_SEQ):
            self.audio.mode = AudioMode.STRIP

        return self

    @classmethod
    def from_preset(cls, name: str) -> "ExportSettings":
        """Create ExportSettings from a named built-in preset.

        Args:
            name: Preset name (e.g. 'youtube_hd', 'gif_loop', 'editing_hq').

        Raises:
            KeyError: If preset name is not found.

        Returns:
            Fully configured ExportSettings instance.
        """
        if name not in EXPORT_PRESETS:
            available = ", ".join(sorted(EXPORT_PRESETS.keys()))
            raise KeyError(f"Unknown preset '{name}'. Available: {available}")
        return cls(**EXPORT_PRESETS[name])

    def get_output_extension(self) -> str:
        """Return the file extension (with dot) for the chosen format."""
        return {
            ExportFormat.MP4: ".mp4",
            ExportFormat.MOV: ".mov",
            ExportFormat.GIF: ".gif",
            ExportFormat.PNG_SEQ: ".png",
            ExportFormat.WEBM: ".webm",
        }[self.format]


# ---------------------------------------------------------------------------
# Built-in Export Presets
# ---------------------------------------------------------------------------

EXPORT_PRESETS: dict[str, dict] = {
    # -- Quick / Preview --
    "quick_preview": {
        "format": "mp4",
        "resolution": {"mode": "preset", "preset": "480p"},
        "h264": {"crf": 28, "preset": "fast"},
        "audio": {"mode": "strip"},
        "frame_rate": {"mode": "source"},
    },

    # -- Social Media --
    "social_media": {
        "format": "mp4",
        "resolution": {"mode": "preset", "preset": "1080p"},
        "h264": {"crf": 20, "preset": "medium"},
        "frame_rate": {"mode": "preset", "preset": "30"},
        "audio": {"mode": "reencode", "bitrate": "192k"},
    },
    "instagram_square": {
        "format": "mp4",
        "resolution": {
            "mode": "custom", "width": 1080, "height": 1080,
            "aspect_mode": "pad",
        },
        "h264": {"crf": 20, "preset": "medium"},
        "frame_rate": {"mode": "preset", "preset": "30"},
        "audio": {"mode": "reencode", "bitrate": "192k"},
    },
    "instagram_story": {
        "format": "mp4",
        "resolution": {
            "mode": "custom", "width": 1080, "height": 1920,
            "aspect_mode": "pad",
        },
        "h264": {"crf": 20, "preset": "medium"},
        "frame_rate": {"mode": "preset", "preset": "30"},
        "audio": {"mode": "reencode", "bitrate": "192k"},
    },
    "tiktok": {
        "format": "mp4",
        "resolution": {
            "mode": "custom", "width": 1080, "height": 1920,
            "aspect_mode": "pad",
        },
        "h264": {"crf": 20, "preset": "medium"},
        "frame_rate": {"mode": "preset", "preset": "30"},
        "audio": {"mode": "reencode", "bitrate": "192k"},
    },

    # -- YouTube --
    "youtube_hd": {
        "format": "mp4",
        "resolution": {"mode": "preset", "preset": "1080p"},
        "h264": {"crf": 18, "preset": "slow"},
        "frame_rate": {"mode": "source"},
        "audio": {"mode": "reencode", "bitrate": "256k"},
    },
    "youtube_4k": {
        "format": "mp4",
        "resolution": {"mode": "preset", "preset": "2160p"},
        "h264": {"crf": 18, "preset": "slow"},
        "frame_rate": {"mode": "source"},
        "audio": {"mode": "reencode", "bitrate": "256k"},
    },

    # -- Web --
    "web_embed": {
        "format": "webm",
        "resolution": {"mode": "preset", "preset": "720p"},
        "webm": {"crf": 31, "speed": 2},
        "frame_rate": {"mode": "source"},
        "audio": {"mode": "reencode", "bitrate": "128k"},
    },

    # -- GIF --
    "gif_loop": {
        "format": "gif",
        "gif": {
            "max_colors": 256, "dither": "sierra2_4a",
            "fps": 15, "max_width": 480,
        },
        "audio": {"mode": "strip"},
    },
    "gif_tiny": {
        "format": "gif",
        "gif": {
            "max_colors": 128, "dither": "bayer",
            "fps": 10, "max_width": 320,
        },
        "audio": {"mode": "strip"},
    },

    # -- Editing / Post-Production --
    "editing_proxy": {
        "format": "mov",
        "resolution": {"mode": "source"},
        "prores": {"profile": 0},
        "frame_rate": {"mode": "source"},
        "audio": {"mode": "reencode", "bitrate": "192k"},
    },
    "editing_hq": {
        "format": "mov",
        "resolution": {"mode": "source"},
        "prores": {"profile": 3},
        "frame_rate": {"mode": "source"},
        "audio": {"mode": "reencode", "bitrate": "256k"},
    },
    "compositing": {
        "format": "mov",
        "resolution": {"mode": "source"},
        "prores": {"profile": 4},
        "frame_rate": {"mode": "source"},
        "audio": {"mode": "reencode", "bitrate": "256k"},
    },

    # -- Frame Sequence --
    "frame_sequence": {
        "format": "png_seq",
        "resolution": {"mode": "source"},
        "png_seq": {"pixel_format": "rgb24", "compression_level": 6},
        "audio": {"mode": "strip"},
    },

    # -- Archive --
    "archive": {
        "format": "mp4",
        "resolution": {"mode": "source"},
        "h264": {"crf": 14, "preset": "veryslow"},
        "frame_rate": {"mode": "source"},
        "audio": {"mode": "reencode", "bitrate": "320k"},
    },
}


# ---------------------------------------------------------------------------
# Backward Compatibility
# ---------------------------------------------------------------------------

LEGACY_QUALITY_MAP: dict[str, str] = {
    "lo": "quick_preview",   # Was: 480p h264 crf28
    "mid": "social_media",   # Was: 720p h264 crf23
    "hi": "editing_hq",      # Was: prores 422
}


def from_legacy_quality(
    quality: str,
    effects: list[dict],
    mix: float = 1.0,
) -> ExportSettings:
    """Convert old-style RenderRequest quality tier to ExportSettings.

    Maintains backward compatibility:
        "lo"  -> quick_preview preset  (480p, CRF 28, fast)
        "mid" -> social_media preset   (1080p, CRF 20, medium)
        "hi"  -> editing_hq preset     (source res, ProRes 422 HQ)

    Args:
        quality: Legacy quality string ("lo", "mid", "hi").
        effects: Effect chain list.
        mix: Wet/dry blend value.

    Returns:
        Fully configured ExportSettings.
    """
    preset_name = LEGACY_QUALITY_MAP.get(quality, "social_media")
    settings = ExportSettings.from_preset(preset_name)
    settings.effects = effects
    settings.mix = mix
    return settings


def list_presets() -> list[dict[str, str]]:
    """List all available export presets with their format.

    Returns:
        List of dicts: [{"name": "youtube_hd", "format": "mp4"}, ...]
    """
    result = []
    for name, config in sorted(EXPORT_PRESETS.items()):
        result.append({
            "name": name,
            "format": config.get("format", "mp4"),
        })
    return result

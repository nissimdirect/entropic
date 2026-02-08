"""
Entropic — Video I/O Engine
Handles frame extraction (video → numpy arrays) and reassembly (arrays → video).
Uses FFmpeg subprocess for codec work. Preserves audio.
"""

import subprocess
import shutil
import tempfile
import json
from pathlib import Path

import numpy as np
from PIL import Image


def get_ffmpeg():
    """Find FFmpeg binary."""
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError("FFmpeg not found. Install with: brew install ffmpeg")
    return path


def get_ffprobe():
    """Find FFprobe binary."""
    path = shutil.which("ffprobe")
    if not path:
        raise RuntimeError("FFprobe not found. Install with: brew install ffmpeg")
    return path


def probe_video(video_path: str) -> dict:
    """Get video metadata: resolution, fps, duration, has_audio."""
    video_path = str(video_path)
    cmd = [
        get_ffprobe(),
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
    data = json.loads(result.stdout)

    video_stream = None
    has_audio = False
    for stream in data.get("streams", []):
        if stream["codec_type"] == "video" and video_stream is None:
            video_stream = stream
        if stream["codec_type"] == "audio":
            has_audio = True

    if not video_stream:
        raise ValueError(f"No video stream found in {video_path}")

    fps_parts = video_stream.get("r_frame_rate", "30/1").split("/")
    fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30.0

    return {
        "width": int(video_stream["width"]),
        "height": int(video_stream["height"]),
        "fps": fps,
        "duration": float(data.get("format", {}).get("duration", 0)),
        "has_audio": has_audio,
        "codec": video_stream.get("codec_name", "unknown"),
        "total_frames": int(float(data.get("format", {}).get("duration", 0)) * fps),
    }


def extract_frames(video_path: str, output_dir: str, scale: float = 1.0) -> list[Path]:
    """Extract all frames from video as PNG files.

    Args:
        video_path: Path to input video.
        output_dir: Directory to write frame PNGs.
        scale: Resolution scale factor (1.0 = original, 0.5 = half).

    Returns:
        List of frame file paths, sorted.
    """
    video_path = str(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [get_ffmpeg(), "-i", video_path]

    if scale < 1.0:
        info = probe_video(video_path)
        w = int(info["width"] * scale)
        h = int(info["height"] * scale)
        # Ensure even dimensions (required by most codecs)
        w = w + (w % 2)
        h = h + (h % 2)
        cmd += ["-vf", f"scale={w}:{h}"]

    cmd += [
        "-vsync", "0",
        str(output_dir / "frame_%06d.png"),
    ]

    subprocess.run(cmd, capture_output=True, check=True, timeout=300)

    frames = sorted(output_dir.glob("frame_*.png"))
    if not frames:
        raise RuntimeError(f"No frames extracted from {video_path}")

    MAX_FRAMES = 3000
    if len(frames) > MAX_FRAMES:
        raise RuntimeError(
            f"Video has {len(frames)} frames (max {MAX_FRAMES}). "
            f"Use a shorter clip or lower resolution."
        )
    return frames


def load_frame(frame_path: str) -> np.ndarray:
    """Load a frame PNG as a numpy array (H, W, 3) uint8 RGB."""
    img = Image.open(str(frame_path)).convert("RGB")
    return np.array(img)


def save_frame(array: np.ndarray, output_path: str):
    """Save a numpy array (H, W, 3) as PNG."""
    img = Image.fromarray(np.clip(array, 0, 255).astype(np.uint8))
    img.save(str(output_path))


def reassemble_video(
    frames_dir: str,
    output_path: str,
    fps: float,
    audio_source: str | None = None,
    quality: str = "lo",
) -> Path:
    """Reassemble frames into a video file.

    Args:
        frames_dir: Directory containing frame_XXXXXX.png files.
        output_path: Output video file path.
        fps: Frames per second.
        audio_source: Original video to copy audio from (or None).
        quality: 'lo' (480p h264), 'mid' (720p h264), 'hi' (prores 422).

    Returns:
        Path to output video.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        get_ffmpeg(),
        "-y",
        "-framerate", str(fps),
        "-i", str(Path(frames_dir) / "frame_%06d.png"),
    ]

    # Add audio from original
    if audio_source:
        cmd += ["-i", str(audio_source), "-map", "0:v", "-map", "1:a?", "-shortest"]

    # Quality presets
    if quality == "hi":
        cmd += ["-c:v", "prores_ks", "-profile:v", "2", "-pix_fmt", "yuv422p10le"]
        if str(output_path).endswith(".mp4"):
            output_path = output_path.with_suffix(".mov")
    elif quality == "mid":
        cmd += ["-c:v", "libx264", "-crf", "23", "-preset", "medium", "-pix_fmt", "yuv420p"]
    else:  # lo
        cmd += ["-c:v", "libx264", "-crf", "28", "-preset", "fast", "-pix_fmt", "yuv420p"]

    if audio_source:
        cmd += ["-c:a", "aac", "-b:a", "192k"]

    cmd.append(str(output_path))
    subprocess.run(cmd, capture_output=True, check=True, timeout=600)

    if not output_path.exists():
        raise RuntimeError(f"Failed to create output video: {output_path}")

    return output_path


def extract_single_frame(video_path: str, frame_number: int = 0) -> np.ndarray:
    """Extract a single frame as numpy array. Fast — doesn't decode entire video."""
    video_path = str(video_path)
    info = probe_video(video_path)
    # Clamp frame number to valid range
    total = max(1, info.get("total_frames", 1))
    frame_number = max(0, min(frame_number, total - 1))
    timestamp = frame_number / info["fps"]

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        cmd = [
            get_ffmpeg(),
            "-ss", str(timestamp),
            "-i", video_path,
            "-frames:v", "1",
            "-y",
            tmp_path,
        ]
        subprocess.run(cmd, capture_output=True, check=True, timeout=30)
        return load_frame(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

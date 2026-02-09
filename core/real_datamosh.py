"""
Entropic — Real Datamosh Engine
ACTUAL H.264 P-frame manipulation (not optical flow simulation).

Technique learned from SuperMosh Studio (Nino Filiu):
  FFmpeg -g 99999999 -bf 0 creates all-P-frame video (one keyframe only).
  When you splice P-frames from Video B after Video A's keyframe,
  the decoder applies B's motion vectors onto A's pixels = datamosh.

This module provides:
  - preprocess_for_datamosh(): Strip keyframes from a video
  - real_datamosh(): Splice P-frames between two videos at byte level
  - multi_datamosh(): Interleave P-frames from 3+ sources
  - audio_reactive_datamosh(): Switch P-frame source based on audio transients
"""

import math
import os
import subprocess
import tempfile
import shutil
import struct
from pathlib import Path

import numpy as np

from .video_io import get_ffmpeg, get_ffprobe, probe_video


def preprocess_for_datamosh(
    input_path: str,
    output_path: str,
    width: int = 0,
    height: int = 0,
    crf: int = 15,
) -> Path:
    """Preprocess video for datamosh: re-encode with no keyframes after first.

    This is the SuperMosh trick:
      -g 99999999  = GOP of infinity (one keyframe at start, rest are P-frames)
      -bf 0        = no B-frames (only I and P)
      -flags:v +cgop = closed GOP

    Args:
        input_path: Source video.
        output_path: Output path for preprocessed video.
        width: Target width (0 = keep original).
        height: Target height (0 = keep original).
        crf: Quality (lower = better, 15 = high quality).

    Returns:
        Path to preprocessed video.
    """
    input_path = str(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    info = probe_video(input_path)
    if width == 0:
        width = info["width"]
    if height == 0:
        height = info["height"]
    # Ensure even dimensions
    width += width % 2
    height += height % 2

    cmd = [
        get_ffmpeg(), "-y",
        "-i", input_path,
        "-vf", f"scale={width}:{height}",
        "-vcodec", "libx264",
        "-g", "99999999",       # One keyframe only (the datamosh trick)
        "-bf", "0",              # No B-frames
        "-flags:v", "+cgop",     # Closed GOP
        "-pix_fmt", "yuv420p",
        "-movflags", "faststart",
        "-crf", str(crf),
        "-an",                   # Strip audio for splicing
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg preprocessing failed: {result.stderr[-500:]}")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError(f"Preprocessing produced empty file: {output_path}")

    return output_path


def _find_nal_units(data: bytes) -> list[tuple[int, int, int]]:
    """Find H.264 NAL unit boundaries in raw byte stream.

    Returns list of (offset, length, nal_type) tuples.
    NAL types: 1=non-IDR slice (P-frame), 5=IDR slice (I-frame/keyframe),
               6=SEI, 7=SPS, 8=PPS
    """
    nals = []
    i = 0
    while i < len(data) - 4:
        # Look for start codes: 00 00 00 01 or 00 00 01
        if data[i:i+4] == b'\x00\x00\x00\x01':
            start = i
            nal_type = data[i + 4] & 0x1F
            # Find next start code
            j = i + 4
            while j < len(data) - 3:
                if data[j:j+4] == b'\x00\x00\x00\x01' or data[j:j+3] == b'\x00\x00\x01':
                    break
                j += 1
            else:
                j = len(data)
            nals.append((start, j - start, nal_type))
            i = j
        elif data[i:i+3] == b'\x00\x00\x01':
            start = i
            nal_type = data[i + 3] & 0x1F
            j = i + 3
            while j < len(data) - 3:
                if data[j:j+4] == b'\x00\x00\x00\x01' or data[j:j+3] == b'\x00\x00\x01':
                    break
                j += 1
            else:
                j = len(data)
            nals.append((start, j - start, nal_type))
            i = j
        else:
            i += 1
    return nals


def real_datamosh(
    video_a: str,
    video_b: str,
    output_path: str,
    switch_frame: int = 30,
    width: int = 640,
    height: int = 480,
    fps: float = 30.0,
    mode: str = "splice",
    audio_source: str | None = None,
    skip_preprocess: bool = False,
) -> Path:
    """Create a REAL datamosh by splicing P-frames between two videos.

    Modes:
        splice: Take keyframe + N frames from A, then all P-frames from B.
                Classic datamosh — B's motion warps A's pixels.

        interleave: Alternate P-frames between A and B every N frames.
                    Creates flickering melt between two sources.

        replace: Keep A's video but replace P-frames at random intervals
                 with P-frames from B. Unpredictable glitch bursts.

    Args:
        video_a: First video (provides the keyframe / base image).
        video_b: Second video (provides P-frames / motion vectors).
        output_path: Output file path.
        switch_frame: Frame number to switch from A to B (splice mode),
                      or interval for interleaving.
        width: Output width.
        height: Output height.
        fps: Output framerate.
        mode: 'splice', 'interleave', or 'replace'.
        audio_source: Optional video to copy audio from.
        skip_preprocess: If True, skip the preprocess step (use when inputs
                         are already preprocessed, e.g. from strategic_keyframes).

    Returns:
        Path to datamoshed output video.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="entropic_datamosh_") as tmpdir:
        tmpdir = Path(tmpdir)

        # Step 1: Preprocess both videos with the all-P-frame trick
        # (skip if already preprocessed, e.g. strategic_keyframes output)
        prep_a = tmpdir / "prep_a.mp4"
        prep_b = tmpdir / "prep_b.mp4"
        if skip_preprocess:
            shutil.copy2(str(video_a), str(prep_a))
            shutil.copy2(str(video_b), str(prep_b))
        else:
            preprocess_for_datamosh(video_a, str(prep_a), width, height)
            preprocess_for_datamosh(video_b, str(prep_b), width, height)

        # Step 2: Extract raw H.264 bitstreams
        raw_a = tmpdir / "raw_a.h264"
        raw_b = tmpdir / "raw_b.h264"
        for src, dst in [(prep_a, raw_a), (prep_b, raw_b)]:
            cmd = [
                get_ffmpeg(), "-y",
                "-i", str(src),
                "-vcodec", "copy",
                "-bsf:v", "h264_mp4toannexb",
                str(dst),
            ]
            subprocess.run(cmd, capture_output=True, check=True, timeout=120)

        # Step 3: Parse NAL units from both streams
        data_a = raw_a.read_bytes()
        data_b = raw_b.read_bytes()

        nals_a = _find_nal_units(data_a)
        nals_b = _find_nal_units(data_b)

        # Separate into header NALs (SPS/PPS) and frame NALs
        header_nals_a = [(o, l, t) for o, l, t in nals_a if t in (6, 7, 8)]
        frame_nals_a = [(o, l, t) for o, l, t in nals_a if t in (1, 5)]
        frame_nals_b = [(o, l, t) for o, l, t in nals_b if t in (1, 5)]

        if not frame_nals_a or not frame_nals_b:
            raise RuntimeError(
                f"Could not extract frame NALs. A has {len(frame_nals_a)}, "
                f"B has {len(frame_nals_b)} frames."
            )

        # Step 4: Splice bitstreams based on mode
        output_stream = bytearray()

        # Always start with SPS/PPS from video A
        for offset, length, _ in header_nals_a:
            output_stream.extend(data_a[offset:offset + length])

        if mode == "splice":
            # Take first N frames from A (including keyframe), then B's P-frames
            for i, (offset, length, nal_type) in enumerate(frame_nals_a):
                if i >= switch_frame:
                    break
                output_stream.extend(data_a[offset:offset + length])

            # Now splice in B's P-frames (skip B's keyframe — that's the trick)
            for offset, length, nal_type in frame_nals_b:
                if nal_type == 5:  # Skip B's keyframe (IDR)
                    continue
                output_stream.extend(data_b[offset:offset + length])

        elif mode == "interleave":
            # Alternate between A and B every switch_frame frames
            max_frames = min(len(frame_nals_a), len(frame_nals_b))
            use_a = True
            count = 0
            for i in range(max_frames):
                if i == 0:
                    # First frame must be from A (has keyframe)
                    offset, length, _ = frame_nals_a[0]
                    output_stream.extend(data_a[offset:offset + length])
                else:
                    if use_a:
                        offset, length, nal_type = frame_nals_a[i]
                        if nal_type == 5 and i > 0:
                            # Skip extra keyframes from A (shouldn't exist after preprocess, but guard)
                            continue
                        output_stream.extend(data_a[offset:offset + length])
                    else:
                        offset, length, nal_type = frame_nals_b[i]
                        if nal_type == 5:
                            continue
                        output_stream.extend(data_b[offset:offset + length])

                count += 1
                if count >= switch_frame:
                    use_a = not use_a
                    count = 0

        elif mode == "replace":
            # Use A as base, randomly inject B's P-frames
            import random
            rng = random.Random(42)
            b_idx = 0
            for i, (offset, length, nal_type) in enumerate(frame_nals_a):
                if i == 0:
                    # Always keep first frame (keyframe)
                    output_stream.extend(data_a[offset:offset + length])
                elif rng.random() < 0.3 and b_idx < len(frame_nals_b):
                    # 30% chance to inject B's P-frame
                    b_offset, b_length, b_type = frame_nals_b[b_idx]
                    if b_type != 5:  # Skip B's keyframes
                        output_stream.extend(data_b[b_offset:b_offset + b_length])
                    b_idx += 1
                else:
                    output_stream.extend(data_a[offset:offset + length])

        # Step 5: Write spliced bitstream
        spliced_h264 = tmpdir / "spliced.h264"
        spliced_h264.write_bytes(bytes(output_stream))

        # Step 6: Mux raw h264 into MP4 container
        video_only = tmpdir / "video_only.mp4"
        cmd = [
            get_ffmpeg(), "-y",
            "-fflags", "+genpts",
            "-r", str(fps),
            "-i", str(spliced_h264),
            "-c:v", "copy",
            "-movflags", "faststart",
            str(video_only),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"Video muxing failed: {result.stderr[-500:]}")

        if audio_source:
            # Step 7: Add audio in second pass (video already has proper timestamps)
            cmd = [
                get_ffmpeg(), "-y",
                "-i", str(video_only),
                "-i", str(Path(audio_source).resolve()),
                "-c:v", "copy",
                "-map", "0:v", "-map", "1:a",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                "-movflags", "faststart",
                str(output_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                raise RuntimeError(f"Audio muxing failed: {result.stderr[-500:]}")
        else:
            shutil.copy2(str(video_only), str(output_path))

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError(f"Datamosh produced empty file: {output_path}")

    return output_path


def multi_datamosh(
    videos: list[str],
    output_path: str,
    frames_per_source: int = 15,
    width: int = 640,
    height: int = 480,
    fps: float = 30.0,
    audio_source: str | None = None,
) -> Path:
    """Datamosh across 3+ video sources by round-robin P-frame injection.

    Takes keyframe from first video, then cycles through all sources'
    P-frames. Each source's motion vectors warp whatever pixels are
    currently in the decoder buffer.

    Args:
        videos: List of 2+ video paths.
        output_path: Output file path.
        frames_per_source: How many P-frames to take from each source before switching.
        width: Output width.
        height: Output height.
        fps: Output framerate.
        audio_source: Optional audio source.

    Returns:
        Path to multi-datamoshed output.
    """
    if len(videos) < 2:
        raise ValueError("Need at least 2 videos for multi_datamosh")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="entropic_multimosh_") as tmpdir:
        tmpdir = Path(tmpdir)

        # Preprocess all videos — store raw data in a list indexed by source
        raw_data_by_source = []  # bytes objects (shared, not duplicated per NAL)
        all_frame_nals = []      # list of [(offset, length, nal_type), ...]
        header_nals = None       # [(offset, length, nal_type)] from source 0

        for i, video in enumerate(videos):
            prep = tmpdir / f"prep_{i}.mp4"
            raw = tmpdir / f"raw_{i}.h264"

            preprocess_for_datamosh(video, str(prep), width, height)

            cmd = [
                get_ffmpeg(), "-y",
                "-i", str(prep),
                "-vcodec", "copy",
                "-bsf:v", "h264_mp4toannexb",
                str(raw),
            ]
            subprocess.run(cmd, capture_output=True, check=True, timeout=120)

            data = raw.read_bytes()
            raw_data_by_source.append(data)
            nals = _find_nal_units(data)

            if i == 0:
                header_nals = [(o, l, t) for o, l, t in nals if t in (6, 7, 8)]

            frame_nals = [(o, l, t) for o, l, t in nals if t in (1, 5)]
            all_frame_nals.append(frame_nals)

        # Build output stream
        output_stream = bytearray()
        data_0 = raw_data_by_source[0]

        # Header from first video
        for offset, length, _ in header_nals:
            output_stream.extend(data_0[offset:offset + length])

        # Keyframe from first video
        first_frame = all_frame_nals[0][0]
        output_stream.extend(data_0[first_frame[0]:first_frame[0] + first_frame[1]])

        # Round-robin P-frames from all sources
        source_idx = 0
        frame_cursors = [1] * len(videos)  # Skip frame 0 (keyframe) for all
        total_output_frames = 1

        max_total = sum(len(nals) for nals in all_frame_nals)

        while total_output_frames < max_total:
            source_nals = all_frame_nals[source_idx]
            source_data = raw_data_by_source[source_idx]
            cursor = frame_cursors[source_idx]

            frames_taken = 0
            while cursor < len(source_nals) and frames_taken < frames_per_source:
                offset, length, nal_type = source_nals[cursor]
                if nal_type == 5:  # Skip keyframes (except the very first)
                    cursor += 1
                    continue
                output_stream.extend(source_data[offset:offset + length])
                cursor += 1
                frames_taken += 1
                total_output_frames += 1

            frame_cursors[source_idx] = cursor
            source_idx = (source_idx + 1) % len(videos)

            # Check if all sources exhausted
            if all(frame_cursors[i] >= len(all_frame_nals[i]) for i in range(len(videos))):
                break

        # Write and mux
        spliced = tmpdir / "spliced.h264"
        spliced.write_bytes(bytes(output_stream))

        video_only = tmpdir / "video_only.mp4"
        cmd = [
            get_ffmpeg(), "-y",
            "-fflags", "+genpts",
            "-r", str(fps),
            "-i", str(spliced),
            "-c:v", "copy",
            "-movflags", "faststart",
            str(video_only),
        ]
        subprocess.run(cmd, capture_output=True, check=True, timeout=120)

        if audio_source:
            cmd = [
                get_ffmpeg(), "-y",
                "-i", str(video_only),
                "-i", str(Path(audio_source).resolve()),
                "-c:v", "copy",
                "-map", "0:v", "-map", "1:a",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                "-movflags", "faststart",
                str(output_path),
            ]
            subprocess.run(cmd, capture_output=True, check=True, timeout=120)
        else:
            shutil.copy2(str(video_only), str(output_path))

    return output_path


def strategic_keyframes(
    input_path: str,
    output_path: str,
    keyframe_interval: int = 60,
    width: int = 0,
    height: int = 0,
) -> Path:
    """Create datamosh-ready video with strategic keyframe placement.

    Instead of one keyframe (full chaos), place keyframes at intervals
    to create zones of stability within the datamosh. The video periodically
    "resets" to clarity before melting again.

    Args:
        input_path: Source video.
        output_path: Output path.
        keyframe_interval: Frames between keyframes (higher = more melt between resets).
        width: Target width (0 = keep original).
        height: Target height (0 = keep original).

    Returns:
        Path to output.
    """
    input_path = str(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    info = probe_video(input_path)
    if width == 0:
        width = info["width"]
    if height == 0:
        height = info["height"]
    width += width % 2
    height += height % 2

    cmd = [
        get_ffmpeg(), "-y",
        "-i", input_path,
        "-vf", f"scale={width}:{height}",
        "-vcodec", "libx264",
        "-g", str(keyframe_interval),
        "-bf", "0",
        "-flags:v", "+cgop",
        "-pix_fmt", "yuv420p",
        "-movflags", "faststart",
        "-crf", "15",
        "-an",
        str(output_path),
    ]

    subprocess.run(cmd, capture_output=True, check=True, timeout=600)
    return output_path


def extract_motion_vectors(
    input_path: str,
    output_path: str | None = None,
) -> Path:
    """Extract and visualize motion vectors from a video.

    Uses FFmpeg's codecview filter to render motion vectors as arrows
    overlaid on the video. Useful for understanding what the datamosh
    will do before committing.

    Args:
        input_path: Source video.
        output_path: Output path (None = auto-generate).

    Returns:
        Path to motion vector visualization video.
    """
    input_path = Path(input_path)
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_mvectors.mp4"
    output_path = Path(output_path)

    cmd = [
        get_ffmpeg(), "-y",
        "-flags2", "+export_mvs",
        "-i", str(input_path),
        "-vf", "codecview=mv=pf+bf+bb",
        "-c:v", "libx264",
        "-crf", "18",
        "-an",
        str(output_path),
    ]

    subprocess.run(cmd, capture_output=True, check=True, timeout=300)
    return output_path


def datamosh_with_transforms(
    video_a: str,
    video_b: str,
    output_path: str,
    mode: str = "splice",
    switch_frame: int = 30,
    width: int = 640,
    height: int = 480,
    fps: float = 30.0,
    rotation: float = 0.0,
    x_offset: int = 0,
    y_offset: int = 0,
    motion_pattern: str = "static",
    motion_speed: float = 1.0,
    audio_source: str | None = None,
) -> Path:
    """Datamosh with spatial transforms and animated frame selection.

    Wraps real_datamosh() and adds:
    - Rotation of the datamoshed output
    - Position offset (shifts mosh center)
    - Motion patterns that animate which frames get moshed

    Motion patterns:
        static: Fixed switch_frame (default behavior)
        sweep_lr: Switch point sweeps left to right over the video
        sweep_tb: Switch point sweeps top to bottom (via crop transform)
        circular: Switch point oscillates sinusoidally
        random: Random switch point per output frame
        pulse: Switch frame pulses between min and max

    Args:
        video_a, video_b: Input videos.
        output_path: Output file.
        mode: Datamosh mode (splice/interleave/replace).
        switch_frame: Base switch frame.
        width, height, fps: Output dimensions.
        rotation: Rotation in degrees (0 = none).
        x_offset, y_offset: Pixel offset for mosh center.
        motion_pattern: How frame selection changes over time.
        motion_speed: Speed multiplier for motion patterns.
        audio_source: Optional audio source video.

    Returns:
        Path to output video.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if motion_pattern == "static":
        # Standard datamosh, no animation
        result = real_datamosh(
            video_a, video_b, str(output_path),
            switch_frame=switch_frame,
            width=width, height=height, fps=fps,
            mode=mode, audio_source=audio_source,
        )
    else:
        # Animated frame selection: render multiple short segments with varying switch_frame
        # and concatenate them
        info_a = probe_video(video_a)
        total_frames = info_a["total_frames"]
        segment_length = max(1, int(fps * 0.5 / motion_speed))  # ~0.5s segments

        with tempfile.TemporaryDirectory(prefix="entropic_motiondm_") as tmpdir:
            tmpdir = Path(tmpdir)
            segments = []
            concat_list = tmpdir / "concat.txt"

            num_segments = max(1, total_frames // segment_length)
            for seg_idx in range(num_segments):
                t = seg_idx / max(1, num_segments - 1)  # 0.0 to 1.0

                if motion_pattern == "sweep_lr":
                    sw = int(1 + t * min(total_frames - 1, 120))
                elif motion_pattern == "circular":
                    sw = int(switch_frame + switch_frame * 0.5 * math.sin(t * 2 * math.pi * motion_speed))
                    sw = max(1, sw)
                elif motion_pattern == "random":
                    import random
                    rng = random.Random(42 + seg_idx)
                    sw = rng.randint(1, max(2, switch_frame * 2))
                elif motion_pattern == "pulse":
                    sw = switch_frame if seg_idx % 2 == 0 else max(1, switch_frame // 4)
                else:
                    sw = switch_frame

                seg_out = tmpdir / f"seg_{seg_idx:04d}.mp4"
                try:
                    real_datamosh(
                        video_a, video_b, str(seg_out),
                        switch_frame=sw,
                        width=width, height=height, fps=fps,
                        mode=mode,
                    )
                    if seg_out.exists() and seg_out.stat().st_size > 0:
                        segments.append(seg_out)
                except Exception:
                    continue

            if not segments:
                # Fallback to standard
                return real_datamosh(
                    video_a, video_b, str(output_path),
                    switch_frame=switch_frame,
                    width=width, height=height, fps=fps,
                    mode=mode, audio_source=audio_source,
                )

            # Write concat file
            with open(concat_list, "w") as f:
                for seg in segments:
                    f.write(f"file '{seg}'\n")

            # Concatenate
            cmd = [
                get_ffmpeg(), "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(concat_list),
                "-c:v", "copy",
                "-movflags", "faststart",
            ]
            if audio_source:
                cmd += ["-i", str(Path(audio_source).resolve()),
                        "-map", "0:v", "-map", "1:a",
                        "-c:a", "aac", "-b:a", "192k", "-shortest"]
            cmd.append(str(output_path))

            subprocess.run(cmd, capture_output=True, check=True, timeout=300)

        result = output_path

    # Apply rotation and offset if needed
    if rotation != 0 or x_offset != 0 or y_offset != 0:
        _apply_ffmpeg_transforms(str(result), rotation, x_offset, y_offset)

    return Path(result)


def _apply_ffmpeg_transforms(video_path: str, rotation: float, x_off: int, y_off: int):
    """Apply rotation and position offset to a video in-place."""
    filters = []
    if rotation != 0:
        rad = rotation * math.pi / 180
        filters.append(f"rotate={rad}:fillcolor=black")
    if x_off != 0 or y_off != 0:
        info = probe_video(video_path)
        w, h = info["width"], info["height"]
        cx = max(0, -x_off)
        cy = max(0, -y_off)
        px = max(0, x_off)
        py = max(0, y_off)
        filters.append(f"crop={w}:{h}:{cx}:{cy},pad={w}:{h}:{px}:{py}:color=black")

    if not filters:
        return

    tmp = video_path + ".xform.mp4"
    cmd = [
        get_ffmpeg(), "-y",
        "-i", video_path,
        "-vf", ",".join(filters),
        "-c:v", "libx264", "-crf", "18",
        "-c:a", "copy",
        tmp,
    ]
    subprocess.run(cmd, capture_output=True, check=True, timeout=120)
    os.replace(tmp, video_path)


def audio_datamosh(
    video_path: str,
    audio_a_path: str,
    audio_b_path: str,
    output_path: str,
    intensity: float = 0.3,
    chunk_ms: int = 100,
    mode: str = "swap",
) -> Path:
    """Datamosh audio: corrupt/swap audio chunks between two sources.

    Modes:
        swap: Randomly replace chunks of A's audio with B's audio
        blend: Crossfade between A and B audio randomly
        corrupt: Apply byte-level corruption to audio data
        stutter: Repeat random audio chunks (buffer overflow effect)

    Args:
        video_path: Video to attach moshed audio to.
        audio_a_path: Primary audio source.
        audio_b_path: Secondary audio source.
        output_path: Output path.
        intensity: 0.0-1.0, probability of corruption per chunk.
        chunk_ms: Chunk size in milliseconds.
        mode: swap, blend, corrupt, or stutter.

    Returns:
        Path to output video with moshed audio.
    """
    output_path = Path(output_path)

    with tempfile.TemporaryDirectory(prefix="entropic_audiomosh_") as tmpdir:
        tmpdir = Path(tmpdir)
        wav_a = tmpdir / "a.wav"
        wav_b = tmpdir / "b.wav"
        moshed_wav = tmpdir / "moshed.wav"

        # Extract audio as WAV
        for src, dst in [(audio_a_path, wav_a), (audio_b_path, wav_b)]:
            cmd = [
                get_ffmpeg(), "-y",
                "-i", src,
                "-vn", "-acodec", "pcm_s16le", "-ar", "44100",
                str(dst),
            ]
            subprocess.run(cmd, capture_output=True, timeout=60)

        if not wav_a.exists() or not wav_b.exists():
            # No audio to mosh, just copy video
            shutil.copy2(video_path, str(output_path))
            return output_path

        try:
            import soundfile as sf
        except ImportError:
            shutil.copy2(video_path, str(output_path))
            return output_path

        data_a, sr = sf.read(str(wav_a))
        data_b, _ = sf.read(str(wav_b))

        # Normalize to same channel count (mono → stereo or vice versa)
        if data_a.ndim == 1 and data_b.ndim == 2:
            data_a = np.column_stack([data_a, data_a])
        elif data_a.ndim == 2 and data_b.ndim == 1:
            data_b = np.column_stack([data_b, data_b])

        min_len = min(len(data_a), len(data_b))
        data_a = data_a[:min_len]
        data_b = data_b[:min_len]
        moshed = data_a.copy()

        rng = np.random.RandomState(42)
        chunk_samples = int(sr * chunk_ms / 1000)
        fade_samples = min(int(sr * 0.005), chunk_samples // 4)  # 5ms crossfade

        for start in range(0, min_len - chunk_samples, chunk_samples):
            end = start + chunk_samples

            if rng.random() >= intensity:
                continue

            if mode == "swap":
                moshed[start:end] = data_b[start:end]
            elif mode == "blend":
                alpha = rng.uniform(0.3, 0.7)
                moshed[start:end] = data_a[start:end] * (1 - alpha) + data_b[start:end] * alpha
            elif mode == "corrupt":
                # Bit-flip corruption on audio samples
                raw = moshed[start:end].copy()
                corrupt_mask = rng.random(raw.shape) < 0.1
                raw[corrupt_mask] = rng.uniform(-1, 1, size=corrupt_mask.sum())
                moshed[start:end] = raw
            elif mode == "stutter":
                # Repeat a small sub-chunk multiple times
                sub = chunk_samples // 4
                if sub > 0:
                    chunk_len = end - start
                    repeated = np.tile(
                        data_a[start:start+sub],
                        (math.ceil(chunk_len / sub),) + ((1,) if data_a.ndim == 2 else ()),
                    )
                    moshed[start:end] = repeated[:chunk_len]

            # Crossfade at boundaries
            if fade_samples > 0 and start > fade_samples:
                fade = np.linspace(0, 1, fade_samples)
                if moshed.ndim == 2:
                    fade = fade[:, np.newaxis]
                moshed[start:start+fade_samples] = (
                    data_a[start:start+fade_samples] * (1 - fade) +
                    moshed[start:start+fade_samples] * fade
                )

        sf.write(str(moshed_wav), moshed, sr)

        # Mux moshed audio with video
        cmd = [
            get_ffmpeg(), "-y",
            "-i", video_path,
            "-i", str(moshed_wav),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-movflags", "faststart",
            str(output_path),
        ]
        subprocess.run(cmd, capture_output=True, check=True, timeout=120)

    return output_path

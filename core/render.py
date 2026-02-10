"""
Entropic — Offline Render Pipeline for Recorded Performances

Takes recorded MIDI automation + layer config and renders to
1080p H.264 video with audio pass-through.

Two-phase VJ workflow:
  1. Perform live (480p preview) → records automation JSON
  2. This module renders offline (1080p) from that recording
"""

import sys
import time
from pathlib import Path

import numpy as np

from core.video_io import probe_video, stream_frames, open_output_pipe, mux_audio
from core.layer import Layer, LayerStack
from core.automation import PerformanceSession
from effects import apply_chain


def render_performance(
    layers_config,
    automation_path,
    output_path,
    fps=30,
    duration=None,
    audio_source=None,
    crf=18,
    progress_callback=None,
):
    """Render a recorded performance to video.

    Args:
        layers_config: List of Layer dicts (from performance session).
        automation_path: Path to automation JSON (recorded MIDI events).
        output_path: Output video file path.
        fps: Output framerate.
        duration: Duration in seconds (None = use longest video).
        audio_source: Path to video to take audio from (None = no audio).
        crf: H.264 quality (lower = better, 18 = near-lossless).
        progress_callback: Optional fn(frame_index, total_frames) for progress.

    Returns:
        Path to rendered video.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load automation
    session = PerformanceSession.load(automation_path)
    print(f"  Loaded automation: {len(session.lanes)} lanes")

    # Build layers
    layers = [Layer.from_dict(lc) if isinstance(lc, dict) else lc
              for lc in layers_config]
    layer_stack = LayerStack(layers)

    # Determine output dimensions and total frames
    width, height = None, None
    max_frames = 0
    for layer in layers:
        if layer.video_path:
            info = probe_video(layer.video_path)
            if width is None:
                width = info["width"]
                height = info["height"]
                # Ensure even dims
                width = width + (width % 2)
                height = height + (height % 2)
            max_frames = max(max_frames, info["total_frames"])

    if width is None:
        raise ValueError("No layer has a video_path")

    if duration:
        total_frames = int(duration * fps)
    else:
        total_frames = max_frames

    print(f"  Rendering: {width}x{height} @ {fps}fps, {total_frames} frames "
          f"({total_frames / fps:.1f}s)")

    # Start frame generators at full resolution (scale=1.0)
    generators = {}
    current_frames = {}
    for layer in layers:
        if layer.video_path:
            gen = stream_frames(layer.video_path, scale=1.0)
            generators[layer.layer_id] = gen
            try:
                current_frames[layer.layer_id] = next(gen)
            except StopIteration:
                pass

    # Open output pipe
    video_only = output_path.with_suffix(".tmp.mp4") if audio_source else output_path
    pipe = open_output_pipe(video_only, width, height, fps=fps, crf=crf)

    start_time = time.time()

    try:
        for frame_idx in range(total_frames):
            # Read automation values for this frame
            layer_values = session.get_layer_values(frame_idx)

            # Apply automation to layers
            for layer in layers:
                vals = layer_values.get(layer.layer_id, {})

                # Handle triggers
                if "trigger_on" in vals and vals["trigger_on"] > 0:
                    layer.trigger_on()
                    layer_stack.handle_choke(layer)
                if "trigger_off" in vals:
                    layer.trigger_off()

                # Handle active state (toggle mode from keyboard)
                if "active" in vals:
                    if vals["active"] > 0 and not layer._active:
                        layer.trigger_on()
                        layer_stack.handle_choke(layer)
                    elif vals["active"] <= 0 and layer._active:
                        layer.force_off()

                # Handle opacity
                if "opacity" in vals:
                    layer.set_opacity(vals["opacity"])

            # Advance ADSR envelopes
            layer_stack.advance_all()

            # Read next frames from generators
            for layer in layers:
                if not layer.is_visible:
                    continue
                gen = generators.get(layer.layer_id)
                if gen is None:
                    continue
                try:
                    current_frames[layer.layer_id] = next(gen)
                except StopIteration:
                    # Loop video
                    gen = stream_frames(layer.video_path, scale=1.0)
                    generators[layer.layer_id] = gen
                    try:
                        current_frames[layer.layer_id] = next(gen)
                    except StopIteration:
                        pass

            # Apply effect chains
            processed = {}
            for layer in layers:
                if not layer.is_visible:
                    continue
                frame = current_frames.get(layer.layer_id)
                if frame is None:
                    continue

                # Resize to output dims if needed
                if frame.shape[:2] != (height, width):
                    from PIL import Image
                    img = Image.fromarray(frame)
                    frame = np.array(img.resize((width, height), Image.LANCZOS))

                if layer.effects:
                    frame = apply_chain(
                        frame, layer.effects,
                        frame_index=frame_idx,
                        total_frames=total_frames,
                        watermark=False,
                    )
                processed[layer.layer_id] = frame

            # Composite layers
            composited = layer_stack.composite(processed)

            # Ensure correct size
            if composited.shape[:2] != (height, width):
                from PIL import Image
                img = Image.fromarray(composited)
                composited = np.array(img.resize((width, height), Image.LANCZOS))

            # Write to FFmpeg pipe
            pipe.stdin.write(composited.tobytes())

            # Progress
            if progress_callback:
                progress_callback(frame_idx, total_frames)
            elif frame_idx % 100 == 0:
                elapsed = time.time() - start_time
                pct = (frame_idx + 1) / total_frames * 100
                fps_actual = (frame_idx + 1) / max(elapsed, 0.001)
                eta = (total_frames - frame_idx) / max(fps_actual, 0.001)
                print(f"\r  Rendering: {pct:.1f}% ({frame_idx}/{total_frames}) "
                      f"@ {fps_actual:.1f} fps, ETA {eta:.0f}s", end="", flush=True)

    finally:
        pipe.stdin.close()
        pipe.wait(timeout=60)
        print()

        # Close generators
        for gen in generators.values():
            gen.close()

    elapsed = time.time() - start_time
    print(f"  Render complete: {elapsed:.1f}s ({total_frames / elapsed:.1f} fps)")

    # Mux audio if needed
    if audio_source:
        print(f"  Muxing audio from: {audio_source}")
        mux_audio(video_only, audio_source, output_path)
        video_only.unlink(missing_ok=True)
        print(f"  Output: {output_path}")
    else:
        print(f"  Output: {output_path}")

    return output_path

#!/usr/bin/env python3
"""
Entropic — Real Datamosh CLI
ACTUAL H.264 P-frame manipulation. Not simulation.

Usage:
    # Basic datamosh (splice B's motion onto A's image)
    python entropic_datamosh.py splice video_a.mp4 video_b.mp4 -o output.mp4

    # Interleave P-frames (flicker melt between two sources)
    python entropic_datamosh.py interleave video_a.mp4 video_b.mp4 -o output.mp4 --interval 15

    # Multi-source datamosh (3+ videos)
    python entropic_datamosh.py multi video_a.mp4 video_b.mp4 video_c.mp4 -o output.mp4

    # Replace mode (random P-frame injection)
    python entropic_datamosh.py replace video_a.mp4 video_b.mp4 -o output.mp4

    # Visualize motion vectors (see what the datamosh will do)
    python entropic_datamosh.py visualize video.mp4 -o vectors.mp4

    # Preprocess only (create all-P-frame video for manual editing)
    python entropic_datamosh.py preprocess video.mp4 -o preprocessed.mp4

    # Strategic keyframes (controlled zones of stability)
    python entropic_datamosh.py strategic video_a.mp4 video_b.mp4 -o output.mp4 --keyframe-interval 60

    # Chain with Entropic effects (datamosh THEN apply effects)
    python entropic_datamosh.py splice video_a.mp4 video_b.mp4 -o output.mp4 --then pixelsort --then-params threshold=0.3

Technique: FFmpeg -g 99999999 (all P-frames, one keyframe).
Learned from SuperMosh Studio by Nino Filiu.
"""

import argparse
import sys
import time
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.real_datamosh import (
    real_datamosh,
    multi_datamosh,
    preprocess_for_datamosh,
    extract_motion_vectors,
    strategic_keyframes,
)
from core.video_io import probe_video


def cmd_splice(args):
    """Splice P-frames from B onto A's keyframe."""
    print(f"Real datamosh: {args.video_a} + {args.video_b}")
    print(f"Mode: splice at frame {args.switch_frame}")
    print(f"Resolution: {args.width}x{args.height} @ {args.fps}fps")

    t0 = time.time()
    output = real_datamosh(
        args.video_a, args.video_b, args.output,
        switch_frame=args.switch_frame,
        width=args.width, height=args.height, fps=args.fps,
        mode="splice",
        audio_source=args.audio,
    )
    elapsed = time.time() - t0

    print(f"Output: {output} ({output.stat().st_size / 1024:.0f} KB)")
    print(f"Time: {elapsed:.1f}s")

    if args.then:
        _apply_post_effects(output, args)


def cmd_interleave(args):
    """Alternate P-frames between A and B."""
    print(f"Real datamosh interleave: {args.video_a} + {args.video_b}")
    print(f"Switch every {args.interval} frames")

    t0 = time.time()
    output = real_datamosh(
        args.video_a, args.video_b, args.output,
        switch_frame=args.interval,
        width=args.width, height=args.height, fps=args.fps,
        mode="interleave",
        audio_source=args.audio,
    )
    elapsed = time.time() - t0

    print(f"Output: {output} ({output.stat().st_size / 1024:.0f} KB)")
    print(f"Time: {elapsed:.1f}s")

    if args.then:
        _apply_post_effects(output, args)


def cmd_replace(args):
    """Random P-frame injection from B into A."""
    print(f"Real datamosh replace: {args.video_a} + {args.video_b}")

    t0 = time.time()
    output = real_datamosh(
        args.video_a, args.video_b, args.output,
        width=args.width, height=args.height, fps=args.fps,
        mode="replace",
        audio_source=args.audio,
    )
    elapsed = time.time() - t0

    print(f"Output: {output} ({output.stat().st_size / 1024:.0f} KB)")
    print(f"Time: {elapsed:.1f}s")


def cmd_multi(args):
    """Multi-source datamosh (3+ videos)."""
    print(f"Multi-datamosh: {len(args.videos)} sources")
    for v in args.videos:
        print(f"  - {v}")

    t0 = time.time()
    output = multi_datamosh(
        args.videos, args.output,
        frames_per_source=args.interval,
        width=args.width, height=args.height, fps=args.fps,
        audio_source=args.audio,
    )
    elapsed = time.time() - t0

    print(f"Output: {output} ({output.stat().st_size / 1024:.0f} KB)")
    print(f"Time: {elapsed:.1f}s")


def cmd_visualize(args):
    """Visualize motion vectors."""
    print(f"Extracting motion vectors from: {args.video}")

    t0 = time.time()
    output = extract_motion_vectors(args.video, args.output)
    elapsed = time.time() - t0

    print(f"Motion vector visualization: {output}")
    print(f"Time: {elapsed:.1f}s")


def cmd_preprocess(args):
    """Create all-P-frame video (strip keyframes)."""
    print(f"Preprocessing for datamosh: {args.video}")
    info = probe_video(args.video)
    print(f"  Source: {info['width']}x{info['height']} @ {info['fps']:.1f}fps, {info['duration']:.1f}s")

    t0 = time.time()
    output = preprocess_for_datamosh(
        args.video, args.output,
        width=args.width, height=args.height,
    )
    elapsed = time.time() - t0

    print(f"Output: {output} ({output.stat().st_size / 1024:.0f} KB)")
    print(f"  All P-frames, one keyframe at start. Ready for splicing.")
    print(f"Time: {elapsed:.1f}s")


def cmd_strategic(args):
    """Datamosh with strategic keyframe placement for controlled stability zones."""
    print(f"Strategic keyframe datamosh: {args.video_a} + {args.video_b}")
    print(f"Keyframe interval: {args.keyframe_interval} frames")
    print(f"  (video resets to clarity every {args.keyframe_interval / args.fps:.1f}s)")

    t0 = time.time()

    # First, create strategic-keyframe version of video A
    import tempfile
    with tempfile.TemporaryDirectory(prefix="entropic_strategic_") as tmpdir:
        tmpdir = Path(tmpdir)
        prep_a = tmpdir / "strategic_a.mp4"

        strategic_keyframes(
            args.video_a, str(prep_a),
            keyframe_interval=args.keyframe_interval,
            width=args.width, height=args.height,
        )

        # Now do the datamosh splice using the strategic version
        output = real_datamosh(
            str(prep_a), args.video_b, args.output,
            switch_frame=1,  # Switch immediately after first keyframe
            width=args.width, height=args.height, fps=args.fps,
            mode="splice",
            audio_source=args.audio,
        )

    elapsed = time.time() - t0
    print(f"Output: {output} ({output.stat().st_size / 1024:.0f} KB)")
    print(f"Time: {elapsed:.1f}s")


def _apply_post_effects(video_path, args):
    """Apply Entropic effects chain to datamoshed output."""
    from core.video_io import extract_frames, load_frame, save_frame, reassemble_video, probe_video
    from effects import apply_effect
    import tempfile

    effect_name = args.then
    params = {}
    if args.then_params:
        for p in args.then_params.split(","):
            k, v = p.split("=")
            try:
                params[k.strip()] = float(v.strip())
            except ValueError:
                params[k.strip()] = v.strip()

    print(f"\nApplying post-effect: {effect_name} {params}")

    info = probe_video(str(video_path))

    with tempfile.TemporaryDirectory(prefix="entropic_post_") as tmpdir:
        tmpdir = Path(tmpdir)
        frames_dir = tmpdir / "frames"
        out_dir = tmpdir / "processed"
        out_dir.mkdir()

        frames = extract_frames(str(video_path), str(frames_dir))
        total = len(frames)

        for i, frame_path in enumerate(frames):
            frame = load_frame(str(frame_path))
            processed = apply_effect(frame, effect_name, frame_index=i, total_frames=total, **params)
            save_frame(processed, str(out_dir / frame_path.name))
            if (i + 1) % 30 == 0:
                print(f"  Processed {i + 1}/{total} frames")

        final = reassemble_video(
            str(out_dir), str(video_path),
            fps=info["fps"],
            audio_source=str(video_path) if info["has_audio"] else None,
        )
        print(f"Post-processed: {final}")


def main():
    parser = argparse.ArgumentParser(
        description="Entropic Real Datamosh — actual H.264 P-frame manipulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--width", "-W", type=int, default=640, help="Output width (default: 640)")
    parser.add_argument("--height", "-H", type=int, default=480, help="Output height (default: 480)")
    parser.add_argument("--fps", type=float, default=30.0, help="Output FPS (default: 30)")
    parser.add_argument("--audio", "-a", type=str, default=None, help="Audio source video")

    sub = parser.add_subparsers(dest="command", help="Datamosh mode")

    # splice
    p = sub.add_parser("splice", help="Splice B's P-frames onto A's keyframe (classic datamosh)")
    p.add_argument("video_a", help="Video A (provides keyframe / base image)")
    p.add_argument("video_b", help="Video B (provides motion vectors)")
    p.add_argument("-o", "--output", required=True, help="Output path")
    p.add_argument("--switch-frame", type=int, default=30, help="Frame to switch from A to B")
    p.add_argument("--then", type=str, default=None, help="Entropic effect to apply after datamosh")
    p.add_argument("--then-params", type=str, default=None, help="Params for post-effect (k=v,k=v)")

    # interleave
    p = sub.add_parser("interleave", help="Alternate P-frames between A and B")
    p.add_argument("video_a")
    p.add_argument("video_b")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--interval", type=int, default=15, help="Frames per source before switching")
    p.add_argument("--then", type=str, default=None)
    p.add_argument("--then-params", type=str, default=None)

    # replace
    p = sub.add_parser("replace", help="Random P-frame injection from B into A")
    p.add_argument("video_a")
    p.add_argument("video_b")
    p.add_argument("-o", "--output", required=True)

    # multi
    p = sub.add_parser("multi", help="Multi-source datamosh (3+ videos)")
    p.add_argument("videos", nargs="+", help="Video files (2+)")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--interval", type=int, default=15)

    # visualize
    p = sub.add_parser("visualize", help="Visualize motion vectors as arrows")
    p.add_argument("video")
    p.add_argument("-o", "--output", default=None)

    # preprocess
    p = sub.add_parser("preprocess", help="Create all-P-frame video (for manual editing)")
    p.add_argument("video")
    p.add_argument("-o", "--output", required=True)

    # strategic
    p = sub.add_parser("strategic", help="Datamosh with strategic keyframe placement")
    p.add_argument("video_a")
    p.add_argument("video_b")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--keyframe-interval", type=int, default=60, help="Frames between keyframes")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        "splice": cmd_splice,
        "interleave": cmd_interleave,
        "replace": cmd_replace,
        "multi": cmd_multi,
        "visualize": cmd_visualize,
        "preprocess": cmd_preprocess,
        "strategic": cmd_strategic,
    }

    try:
        commands[args.command](args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

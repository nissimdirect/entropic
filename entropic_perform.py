#!/usr/bin/env python3
"""
Entropic — Live Performance Mode CLI

Two-phase VJ workflow:
  1. PERFORM: Preview at 480p with MIDI triggering, record automation
  2. RENDER:  Render offline at 1080p from recorded automation

Usage:
    # Start performance with base video (4 layers, same source)
    python entropic_perform.py --base video.mp4

    # Performance with layer config file
    python entropic_perform.py --config layers.json

    # Render from recorded performance
    python entropic_perform.py --render --automation perf.json --output final.mp4

    # List MIDI devices
    python entropic_perform.py --midi-list

    # MIDI learn mode (print all incoming MIDI)
    python entropic_perform.py --base video.mp4 --midi-learn

Examples:
    # Quick start: 4 layers of same video, different effects
    python entropic_perform.py --base myvideo.mp4 --layers 4

    # With MIDI controller
    python entropic_perform.py --base myvideo.mp4 --midi 0

    # Render recorded session
    python entropic_perform.py --render \\
        --automation session_20260210.json \\
        --config layers.json \\
        --output rendered.mp4 \\
        --audio myvideo.mp4
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def build_default_layers(base_video, num_layers=4):
    """Create default layer config: N layers from same video with different effects.

    Layer 0: Clean (always on) — base layer
    Layer 1: VHS + glitch — toggle
    Layer 2: Pixel sort + chromatic aberration — ADSR (pluck)
    Layer 3: Feedback + stutter — ADSR (stab)
    """
    presets = [
        {
            "name": "Clean",
            "effects": [],
            "trigger_mode": "always_on",
            "adsr_preset": "sustain",
            "opacity": 1.0,
        },
        {
            "name": "VHS+Glitch",
            "effects": [
                {"name": "vhs", "params": {"tracking": 0.4, "noise": 0.3}},
            ],
            "trigger_mode": "toggle",
            "adsr_preset": "sustain",
            "opacity": 0.8,
        },
        {
            "name": "PixelSort",
            "effects": [
                {"name": "pixelsort", "params": {"threshold": 0.5, "direction": "horizontal"}},
            ],
            "trigger_mode": "adsr",
            "adsr_preset": "pluck",
            "opacity": 1.0,
        },
        {
            "name": "Feedback",
            "effects": [
                {"name": "feedback", "params": {"decay": 0.85, "offset_x": 2}},
            ],
            "trigger_mode": "adsr",
            "adsr_preset": "stab",
            "opacity": 0.9,
        },
    ]

    layers = []
    for i in range(min(num_layers, len(presets))):
        layers.append({
            "layer_id": i,
            "video_path": str(base_video),
            "z_order": i,
            "midi_note": 36 + i,       # Launchpad pads
            "midi_cc_opacity": 16 + i,  # MIDI Mix faders
            "choke_group": None,
            **presets[i],
        })

    return layers


def cmd_perform(args):
    """Run live performance mode."""
    from core.performer import PerformanceEngine

    # Build layer config
    if args.config:
        config_path = Path(args.config)
        layers_config = json.loads(config_path.read_text())
        if isinstance(layers_config, dict):
            layers_config = layers_config.get("layers", [])
    elif args.base:
        layers_config = build_default_layers(args.base, args.layers)
    else:
        print("Error: --base or --config required for performance mode")
        sys.exit(1)

    print(f"\n  Entropic Performance Mode")
    print(f"  {'─' * 40}")
    print(f"  Layers: {len(layers_config)}")
    for lc in layers_config:
        print(f"    L{lc['layer_id']}: {lc.get('name', '???')} "
              f"[{lc.get('trigger_mode', '?')}] "
              f"note={lc.get('midi_note', '-')} "
              f"cc={lc.get('midi_cc_opacity', '-')}")

    engine = PerformanceEngine(
        layers_config=layers_config,
        preview_scale=args.preview_scale,
        fps=args.fps,
    )

    # MIDI setup
    if args.midi is not None or args.midi_learn:
        engine.init_midi(device_id=args.midi, learn=args.midi_learn)

    # Run
    engine.run()

    # Handle recorded automation buffer
    if engine.session.lanes:
        n_events = sum(len(l.keyframes) for l in engine.session.lanes)
        duration = engine.frame_index / engine.fps

        if engine._user_opted_in:
            # User explicitly armed recording — save automatically
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            auto_path = Path(args.auto_output or f"perf_{timestamp}.json")
            engine.save_automation(auto_path)
            config_out = auto_path.with_suffix(".layers.json")
            config_out.write_text(json.dumps(engine.get_layers_config(), indent=2))
            print(f"  Layer config: {config_out}")
        else:
            # User never armed — buffer exists, let them choose
            print(f"\n  Buffer captured: {n_events} events over {duration:.1f}s")
            try:
                choice = input("  Save buffer? [y/N]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                choice = "n"

            if choice == "y":
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                auto_path = Path(args.auto_output or f"perf_{timestamp}.json")
                engine.save_automation(auto_path)
                config_out = auto_path.with_suffix(".layers.json")
                config_out.write_text(json.dumps(engine.get_layers_config(), indent=2))
                print(f"  Layer config: {config_out}")
            else:
                print("  Buffer discarded.")
    else:
        print("  No events captured.")


def cmd_render(args):
    """Render from recorded automation."""
    from core.render import render_performance

    if not args.automation:
        print("Error: --automation required for render mode")
        sys.exit(1)

    auto_path = Path(args.automation)
    if not auto_path.exists():
        print(f"Error: Automation file not found: {auto_path}")
        sys.exit(1)

    # Load layer config
    if args.config:
        config_path = Path(args.config)
        data = json.loads(config_path.read_text())
        layers_config = data.get("layers", data) if isinstance(data, dict) else data
    else:
        # Try companion .layers.json file
        companion = auto_path.with_suffix(".layers.json")
        if companion.exists():
            data = json.loads(companion.read_text())
            layers_config = data.get("layers", data) if isinstance(data, dict) else data
            print(f"  Using companion config: {companion}")
        elif args.base:
            layers_config = build_default_layers(args.base, args.layers)
        else:
            print("Error: --config, --base, or companion .layers.json required")
            sys.exit(1)

    output = Path(args.output or f"render_{time.strftime('%Y%m%d_%H%M%S')}.mp4")

    render_performance(
        layers_config=layers_config,
        automation_path=str(auto_path),
        output_path=str(output),
        fps=args.fps,
        duration=args.duration,
        audio_source=args.audio,
        crf=args.crf,
    )


def cmd_midi_list(args):
    """List MIDI devices."""
    from core.midi import MidiController
    MidiController.list_devices()


def main():
    parser = argparse.ArgumentParser(
        description="Entropic Live Performance Mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Mode
    parser.add_argument("--render", action="store_true",
                        help="Render from recorded automation (offline mode)")
    parser.add_argument("--midi-list", action="store_true",
                        help="List available MIDI devices")

    # Input
    parser.add_argument("--base", type=str,
                        help="Base video file (used for all layers)")
    parser.add_argument("--config", type=str,
                        help="Layer configuration JSON file")
    parser.add_argument("--automation", type=str,
                        help="Automation JSON file (for render mode)")
    parser.add_argument("--audio", type=str,
                        help="Audio source video (for render mode)")

    # Performance options
    parser.add_argument("--layers", type=int, default=4,
                        help="Number of layers (default: 4)")
    parser.add_argument("--midi", type=int, default=None,
                        help="MIDI device ID (None = no MIDI)")
    parser.add_argument("--midi-learn", action="store_true",
                        help="Print all incoming MIDI messages")
    parser.add_argument("--fps", type=int, default=30,
                        help="Target framerate (default: 30)")
    parser.add_argument("--preview-scale", type=float, default=0.5,
                        help="Preview resolution scale (default: 0.5 = 480p)")

    # Render options
    parser.add_argument("--output", "-o", type=str,
                        help="Output video file")
    parser.add_argument("--duration", type=float, default=None,
                        help="Render duration in seconds (None = full length)")
    parser.add_argument("--crf", type=int, default=18,
                        help="H.264 quality (lower=better, default: 18)")
    parser.add_argument("--auto-output", type=str, default=None,
                        help="Automation output path (default: perf_TIMESTAMP.json)")

    args = parser.parse_args()

    if args.midi_list:
        cmd_midi_list(args)
    elif args.render:
        cmd_render(args)
    else:
        cmd_perform(args)


if __name__ == "__main__":
    main()

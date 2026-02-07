#!/usr/bin/env python3
"""
Entropic — Gradio Visual Interface
Drag-and-drop UI for applying glitch effects to video.
Launches at http://localhost:7860
"""

import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gradio as gr
import numpy as np
from PIL import Image

from effects import EFFECTS, apply_effect, apply_chain
from core.video_io import probe_video, extract_single_frame, extract_frames, load_frame, save_frame, reassemble_video


def get_effect_names():
    return list(EFFECTS.keys())


def get_effect_params(effect_name):
    if effect_name not in EFFECTS:
        return "Select an effect"
    params = EFFECTS[effect_name]["params"]
    desc = EFFECTS[effect_name]["description"]
    lines = [f"**{effect_name}** — {desc}", ""]
    for k, v in params.items():
        lines.append(f"- `{k}`: {v}")
    return "\n".join(lines)


def preview_single_frame(video_file, effect_name, param1_val, param2_val, param3_val, frame_num):
    """Apply effect to a single frame and return the image."""
    if video_file is None:
        return None, "Upload a video first"

    if effect_name not in EFFECTS:
        return None, "Select an effect"

    try:
        # Extract frame
        frame = extract_single_frame(video_file, int(frame_num))

        # Build params from sliders
        defaults = EFFECTS[effect_name]["params"].copy()
        param_keys = list(defaults.keys())

        params = {}
        slider_vals = [param1_val, param2_val, param3_val]
        for i, key in enumerate(param_keys[:3]):
            default = defaults[key]
            if isinstance(default, (int, float)):
                params[key] = type(default)(slider_vals[i])
            elif isinstance(default, tuple) and len(default) == 2:
                params[key] = (int(slider_vals[i]), 0)
            elif isinstance(default, bool):
                params[key] = slider_vals[i] > 0.5
            elif isinstance(default, str):
                pass  # Skip string params for sliders

        # Apply effect
        result = apply_effect(frame, effect_name, **params)

        # Convert to PIL
        original_img = Image.fromarray(frame)
        result_img = Image.fromarray(result)

        info = f"Effect: {effect_name} | Params: {params}"
        return result_img, info

    except Exception as e:
        return None, f"Error: {e}"


def process_full_video(video_file, effect_name, param1_val, param2_val, param3_val, quality, progress=gr.Progress()):
    """Process entire video with effect."""
    if video_file is None:
        return None, "Upload a video first"

    if effect_name not in EFFECTS:
        return None, "Select an effect"

    try:
        # Build params
        defaults = EFFECTS[effect_name]["params"].copy()
        param_keys = list(defaults.keys())
        params = {}
        slider_vals = [param1_val, param2_val, param3_val]
        for i, key in enumerate(param_keys[:3]):
            default = defaults[key]
            if isinstance(default, (int, float)):
                params[key] = type(default)(slider_vals[i])
            elif isinstance(default, tuple) and len(default) == 2:
                params[key] = (int(slider_vals[i]), 0)
            elif isinstance(default, bool):
                params[key] = slider_vals[i] > 0.5

        effects = [{"name": effect_name, "params": params}]

        info = probe_video(video_file)

        # Scale for quality
        scale_map = {"lo": 0.5, "mid": 0.75, "hi": 1.0}
        scale = scale_map.get(quality, 0.5)

        with tempfile.TemporaryDirectory() as tmp_extract, \
             tempfile.TemporaryDirectory() as tmp_processed:

            progress(0, desc="Extracting frames...")
            frames = extract_frames(video_file, tmp_extract, scale=scale)
            total = len(frames)

            for i, frame_path in enumerate(frames):
                frame = load_frame(str(frame_path))
                processed = apply_chain(frame, effects)
                save_frame(processed, str(Path(tmp_processed) / frame_path.name))
                progress((i + 1) / total, desc=f"Processing frame {i + 1}/{total}")

            progress(0.95, desc="Assembling video...")

            # Output to temp file
            output_path = tempfile.mktemp(suffix=".mp4")
            reassemble_video(
                tmp_processed, output_path,
                fps=info["fps"],
                audio_source=video_file if info["has_audio"] else None,
                quality=quality,
            )

        size_mb = Path(output_path).stat().st_size / (1024 * 1024)
        result_info = f"Done! {total} frames | {size_mb:.1f}MB | {quality} quality"
        return output_path, result_info

    except Exception as e:
        return None, f"Error: {e}"


def update_sliders(effect_name):
    """Update slider labels and ranges when effect changes."""
    if effect_name not in EFFECTS:
        return (
            gr.update(label="Param 1", minimum=0, maximum=1, value=0.5, visible=False),
            gr.update(label="Param 2", minimum=0, maximum=1, value=0.5, visible=False),
            gr.update(label="Param 3", minimum=0, maximum=1, value=0.5, visible=False),
            "Select an effect",
        )

    defaults = EFFECTS[effect_name]["params"]
    param_keys = list(defaults.keys())
    desc = EFFECTS[effect_name]["description"]

    sliders = []
    for i in range(3):
        if i < len(param_keys):
            key = param_keys[i]
            val = defaults[key]
            if isinstance(val, bool):
                sliders.append(gr.update(label=key, minimum=0, maximum=1, step=1, value=int(val), visible=True))
            elif isinstance(val, int):
                sliders.append(gr.update(label=key, minimum=0, maximum=max(val * 4, 10), step=1, value=val, visible=True))
            elif isinstance(val, float):
                sliders.append(gr.update(label=key, minimum=0, maximum=max(val * 4, 2.0), step=0.01, value=val, visible=True))
            elif isinstance(val, tuple):
                sliders.append(gr.update(label=f"{key} (x)", minimum=-100, maximum=100, step=1, value=val[0], visible=True))
            else:
                sliders.append(gr.update(label=key, minimum=0, maximum=1, value=0.5, visible=False))
        else:
            sliders.append(gr.update(visible=False))

    info = f"**{effect_name}** — {desc}"
    return (*sliders, info)


def launch_ui():
    """Build and launch the Gradio interface."""
    with gr.Blocks(
        title="Entropic — Video Glitch Engine",
        theme=gr.themes.Base(
            primary_hue="red",
            secondary_hue="purple",
            neutral_hue="zinc",
        ),
    ) as app:
        gr.Markdown("# Entropic\n### Video Glitch Engine by PopChaos Labs")

        with gr.Row():
            with gr.Column(scale=1):
                video_input = gr.Video(label="Drop Video Here")
                effect_dropdown = gr.Dropdown(
                    choices=get_effect_names(),
                    label="Effect",
                    value="pixelsort",
                )
                effect_info = gr.Markdown("Select an effect")

                param1 = gr.Slider(label="threshold", minimum=0, maximum=1, step=0.01, value=0.5)
                param2 = gr.Slider(label="sort_by", minimum=0, maximum=1, value=0.5, visible=False)
                param3 = gr.Slider(label="direction", minimum=0, maximum=1, value=0.5, visible=False)

                frame_slider = gr.Slider(label="Preview Frame", minimum=0, maximum=300, step=1, value=0)

                with gr.Row():
                    preview_btn = gr.Button("Preview Frame", variant="secondary")
                    render_btn = gr.Button("Render Full Video", variant="primary")

                quality_radio = gr.Radio(
                    choices=["lo", "mid", "hi"],
                    label="Render Quality",
                    value="lo",
                )

            with gr.Column(scale=2):
                result_image = gr.Image(label="Preview", type="pil")
                result_video = gr.Video(label="Rendered Output")
                status_text = gr.Textbox(label="Status", interactive=False)

        # Wire up events
        effect_dropdown.change(
            fn=update_sliders,
            inputs=[effect_dropdown],
            outputs=[param1, param2, param3, effect_info],
        )

        preview_btn.click(
            fn=preview_single_frame,
            inputs=[video_input, effect_dropdown, param1, param2, param3, frame_slider],
            outputs=[result_image, status_text],
        )

        render_btn.click(
            fn=process_full_video,
            inputs=[video_input, effect_dropdown, param1, param2, param3, quality_radio],
            outputs=[result_video, status_text],
        )

    app.launch(server_name="127.0.0.1", server_port=7860)


if __name__ == "__main__":
    launch_ui()

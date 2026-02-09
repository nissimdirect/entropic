"""
Entropic — Preview System
3-tier rendering: lo (480p fast), mid (720p draft), hi (full-res ProRes).
Handles disk budget enforcement.
"""

import tempfile
import shutil
from pathlib import Path

from core.video_io import (
    probe_video,
    extract_frames,
    load_frame,
    save_frame,
    reassemble_video,
    extract_single_frame,
)
from core.project import get_project_dir, load_project
from core.recipe import load_recipe
from core.automation import AutomationSession
from effects import apply_chain

# Quality tier settings
QUALITY_TIERS = {
    "lo": {"scale": 480, "desc": "480p preview"},
    "mid": {"scale": 720, "desc": "720p draft"},
    "hi": {"scale": None, "desc": "Full resolution (ProRes)"},
}


def _scale_for_tier(quality: str, source_height: int) -> float:
    """Calculate scale factor for a quality tier."""
    tier = QUALITY_TIERS.get(quality, QUALITY_TIERS["lo"])
    target = tier["scale"]
    if target is None:
        return 1.0
    return min(1.0, target / source_height)


def render_recipe(
    project_name: str,
    recipe_id: str,
    quality: str = "lo",
    base: Path | None = None,
    automation: AutomationSession | None = None,
) -> Path:
    """Render a recipe at the specified quality tier.

    Args:
        project_name: Project name.
        recipe_id: Recipe ID to render.
        quality: 'lo', 'mid', or 'hi'.

    Returns:
        Path to rendered video file.
    """
    project_dir = get_project_dir(project_name, base)
    recipe = load_recipe(project_name, recipe_id, base)
    effects = recipe["effects"]

    # Find source video
    source_dir = project_dir / "source"
    source_files = list(source_dir.iterdir())
    if not source_files:
        raise FileNotFoundError("No source video in project")
    source_video = source_files[0].resolve()

    # Probe video
    info = probe_video(str(source_video))
    scale = _scale_for_tier(quality, info["height"])

    # Output path
    output_dir = project_dir / "renders" / quality
    output_name = f"{recipe_id}-{recipe['name']}"
    output_ext = ".mov" if quality == "hi" else ".mp4"
    output_path = output_dir / f"{output_name}{output_ext}"

    # Extract frames to temp dir
    with tempfile.TemporaryDirectory() as tmp_extract, \
         tempfile.TemporaryDirectory() as tmp_processed:

        frames = extract_frames(str(source_video), tmp_extract, scale=scale)

        # Apply effects to each frame
        total = len(frames)
        for i, frame_path in enumerate(frames):
            frame = load_frame(str(frame_path))
            # Apply automation overrides if present
            frame_effects = automation.apply_to_chain(effects, i) if automation else effects
            processed = apply_chain(frame, frame_effects, frame_index=i, total_frames=total)
            out_frame = Path(tmp_processed) / frame_path.name
            save_frame(processed, str(out_frame))

            # Progress (every 10%)
            if total > 10 and (i + 1) % (total // 10) == 0:
                pct = (i + 1) / total * 100
                print(f"  Rendering: {pct:.0f}% ({i + 1}/{total} frames)")

        # Reassemble
        output = reassemble_video(
            tmp_processed,
            str(output_path),
            fps=info["fps"],
            audio_source=str(source_video) if info["has_audio"] else None,
            quality=quality,
        )

    return output


def preview_frame(
    project_name: str,
    recipe_id: str,
    frame_number: int = 0,
    base: Path | None = None,
) -> Path:
    """Render a single frame preview. Fast — no full video decode.

    Returns:
        Path to preview PNG.
    """
    project_dir = get_project_dir(project_name, base)
    recipe = load_recipe(project_name, recipe_id, base)
    effects = recipe["effects"]

    # Get source
    source_dir = project_dir / "source"
    source_files = list(source_dir.iterdir())
    source_video = source_files[0].resolve()

    # Extract single frame
    frame = extract_single_frame(str(source_video), frame_number)

    # Apply effects
    processed = apply_chain(frame, effects)

    # Save preview
    preview_path = project_dir / "renders" / "lo" / f"{recipe_id}-preview.png"
    save_frame(processed, str(preview_path))

    return preview_path


def render_sample_frames(
    project_name: str,
    recipe_id: str,
    count: int = 5,
    base: Path | None = None,
) -> list[Path]:
    """Render evenly-spaced sample frames. Fast way to preview an effect.

    Returns:
        List of preview PNG paths.
    """
    project_dir = get_project_dir(project_name, base)
    recipe = load_recipe(project_name, recipe_id, base)
    effects = recipe["effects"]

    source_dir = project_dir / "source"
    source_files = list(source_dir.iterdir())
    source_video = source_files[0].resolve()

    info = probe_video(str(source_video))
    total_frames = info["total_frames"]

    # Pick evenly-spaced frame numbers
    if total_frames <= count:
        frame_nums = list(range(total_frames))
    else:
        frame_nums = [int(i * total_frames / (count - 1)) for i in range(count)]
        frame_nums[-1] = min(frame_nums[-1], total_frames - 1)

    paths = []
    for fn in frame_nums:
        frame = extract_single_frame(str(source_video), fn)
        processed = apply_chain(frame, effects)
        out = project_dir / "renders" / "lo" / f"{recipe_id}-sample-{fn:06d}.png"
        save_frame(processed, str(out))
        paths.append(out)

    return paths

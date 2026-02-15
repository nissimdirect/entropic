#!/usr/bin/env python3
"""
Entropic — FastAPI Backend
Serves the DAW-style UI and handles effect processing via API.
"""

import asyncio
import sys
import os
import shutil
import subprocess
import tempfile
import base64
from pathlib import Path
from io import BytesIO

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import numpy as np
from PIL import Image

from effects import EFFECTS, CATEGORIES, CATEGORY_ORDER, apply_chain, is_video_level
from effects.color import compute_histogram
from packages import PACKAGES
from core.video_io import probe_video, extract_single_frame
from core.export_models import ExportSettings

# Preset system — use writable location for bundled app
_bundled_presets = Path(__file__).parent / "user_presets"
try:
    _bundled_presets.mkdir(exist_ok=True)
    PRESETS_DIR = _bundled_presets
except OSError:
    # Read-only filesystem (DMG, signed .app) — use ~/Library/Application Support/
    PRESETS_DIR = Path.home() / "Library" / "Application Support" / "Entropic" / "user_presets"
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Entropic")

# Serve static files (UI)
UI_DIR = Path(__file__).parent / "ui"
app.mount("/static", StaticFiles(directory=str(UI_DIR / "static")), name="static")

# Default export directory — user-visible location
EXPORT_DIR = Path.home() / "Movies" / "Entropic"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# In-memory state for current session
_state = {
    "video_path": None,
    "video_info": None,
    "current_frame": None,
}
_state_lock = asyncio.Lock()

# Render progress tracking (polled by frontend during export)
_render_progress = {
    "active": False,
    "current_frame": 0,
    "total_frames": 0,
    "phase": "idle",  # "extracting", "processing", "encoding", "idle"
}

# Safety guard: max frames per render to prevent CPU/memory exhaustion
MAX_FRAMES_PER_RENDER = 10000

# Structured error recovery hints for user-facing errors
ERROR_RECOVERY = {
    "no_video": {"code": "NO_VIDEO", "hint": "Load a video or image file first.", "action": "load_file"},
    "no_frame": {"code": "NO_FRAME", "hint": "Load a file to generate a frame.", "action": "load_file"},
    "too_many_effects": {"code": "TOO_MANY_EFFECTS", "hint": "Remove some effects or flatten bypassed ones.", "action": "flatten"},
    "file_too_large": {"code": "FILE_TOO_LARGE", "hint": "Try a shorter video or lower resolution.", "action": None},
    "video_too_long": {"code": "VIDEO_TOO_LONG", "hint": f"Maximum {MAX_FRAMES_PER_RENDER} frames. Trim the video or use a region.", "action": "trim"},
    "upload_failed": {"code": "UPLOAD_FAILED", "hint": "Check the file format and try again.", "action": "retry"},
    "processing_failed": {"code": "PROCESSING_FAILED", "hint": "Try removing the last effect or resetting parameters.", "action": "undo"},
    "preset_not_found": {"code": "PRESET_NOT_FOUND", "hint": "The preset may have been deleted. Refresh the preset list.", "action": "refresh"},
    "render_failed": {"code": "RENDER_FAILED", "hint": "Try exporting at a lower resolution or shorter duration.", "action": "retry"},
}


def _error_detail(key: str, message: str) -> dict:
    """Build structured error detail dict for frontend handleApiError()."""
    recovery = ERROR_RECOVERY.get(key, {})
    return {
        "detail": message,
        "code": recovery.get("code", "UNKNOWN"),
        "hint": recovery.get("hint", ""),
        "action": recovery.get("action"),
    }


class EffectChain(BaseModel):
    effects: list[dict]  # [{"name": "pixelsort", "params": {"threshold": 0.5}}, ...]
    frame_number: int = 0
    mix: float = 1.0  # Wet/dry blend: 0.0 = original, 1.0 = fully processed


class RenderRequest(BaseModel):
    """Simple render request (backwards compat)."""
    effects: list[dict]
    quality: str = "mid"  # lo, mid, hi
    mix: float = 1.0
    automation: dict | None = None  # Optional automation session data
    lfo_config: dict | None = None  # Optional LFO modulation for export


@app.get("/")
async def index():
    return FileResponse(str(UI_DIR / "index.html"))


@app.get("/api/health")
async def health_check():
    """Health check endpoint for desktop app heartbeat."""
    return {"status": "ok"}


@app.get("/api/render/progress")
async def render_progress():
    """Poll render progress during export. Returns frame counts and phase."""
    return _render_progress


@app.get("/api/file-types")
async def get_file_types():
    """List all accepted file types and how they're handled."""
    return {
        "video": {"extensions": sorted(FILE_TYPES["video"]), "description": "Native video — processed directly"},
        "image": {"extensions": sorted(FILE_TYPES["image"]), "description": "Still image — single frame effects"},
        "gif": {"extensions": sorted(FILE_TYPES["gif"]), "description": "Animated GIF — extracted as frames"},
        "raw": {"extensions": sorted(FILE_TYPES["raw"]), "description": "Creative interpretation — raw bytes visualized as pixels"},
    }


@app.get("/api/effects")
async def list_effects():
    """List all available effects grouped by category with ordering."""
    effects = []
    for name, entry in EFFECTS.items():
        params = {}
        ranges = entry.get("param_ranges", {})
        for k, v in entry["params"].items():
            r = ranges.get(k, {})
            if isinstance(v, bool):
                params[k] = {"type": "bool", "default": v}
            elif isinstance(v, int):
                params[k] = {
                    "type": "int", "default": v,
                    "min": r.get("min", 0),
                    "max": r.get("max", max(v * 4, 10)),
                }
            elif isinstance(v, float):
                params[k] = {
                    "type": "float", "default": v,
                    "min": r.get("min", 0.0),
                    "max": r.get("max", max(v * 4, 2.0)),
                    "step": r.get("step", 0.01),
                }
            elif isinstance(v, tuple):
                if len(v) == 3 and all(isinstance(c, (int, float)) and 0 <= c <= 255 for c in v):
                    params[k] = {"type": "rgb", "default": list(v)}
                else:
                    params[k] = {"type": "xy", "default": list(v), "min": r.get("min", -100), "max": r.get("max", 100)}
            elif isinstance(v, list):
                params[k] = {"type": "list", "default": v}
            elif isinstance(v, str):
                params[k] = {"type": "string", "default": v}
        # Add per-param descriptions and ui ranges
        param_descs = entry.get("param_descriptions", {})
        for k in params:
            if k in param_descs:
                params[k]["description"] = param_descs[k]
            # Sweet spot zone and UI range from param_ranges
            r = ranges.get(k, {})
            if params[k].get("type") in ("float", "int"):
                ui_min = r.get("ui_min")
                ui_max = r.get("ui_max")
                if ui_min is not None:
                    params[k]["sweet_min"] = ui_min
                    params[k]["ui_min"] = ui_min
                if ui_max is not None:
                    params[k]["sweet_max"] = ui_max
                    params[k]["ui_max"] = ui_max

        eff_entry = {
            "name": name,
            "category": entry.get("category", "other"),
            "description": entry["description"],
            "params": params,
        }
        if entry.get("alias_of"):
            eff_entry["alias_of"] = entry["alias_of"]
        effects.append(eff_entry)
    return {
        "effects": effects,
        "categories": CATEGORIES,
        "category_order": CATEGORY_ORDER,
    }


@app.post("/api/histogram")
async def get_histogram():
    """Compute RGB + luminance histogram of the current frame."""
    if _state["current_frame"] is None:
        raise HTTPException(status_code=400, detail=_error_detail("no_frame", "No frame loaded"))
    histogram = compute_histogram(_state["current_frame"])
    return JSONResponse(content=histogram)


@app.get("/api/packages")
async def list_packages():
    """List all effect packages with their recipes."""
    result = []
    for pkg_id, pkg in PACKAGES.items():
        recipes = []
        for recipe_id, recipe in pkg["recipes"].items():
            recipes.append({
                "id": recipe_id,
                "name": recipe["name"],
                "description": recipe["description"],
                "effects": recipe["effects"],
            })
        result.append({
            "id": pkg_id,
            "name": pkg["name"],
            "description": pkg["description"],
            "effects_used": pkg.get("effects_used", []),
            "recipes": recipes,
        })
    return result


@app.get("/api/categories")
async def list_categories():
    """List all effect categories."""
    return CATEGORIES


MAX_UPLOAD_SIZE = 2 * 1024 * 1024 * 1024  # 2GB limit

# File types we accept and how we handle them
FILE_TYPES = {
    # Native video — processed directly
    "video": {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.wmv', '.flv', '.ts', '.mts'},
    # Images — converted to single-frame "video" (still image effects)
    "image": {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp'},
    # GIF — extracted as frame sequence
    "gif": {'.gif'},
    # Creative interpretation — raw bytes visualized as pixel data
    "raw": {'.pdf', '.zip', '.txt', '.csv', '.json', '.xml', '.html', '.doc', '.docx',
            '.wav', '.mp3', '.aiff', '.flac', '.psd', '.ai', '.svg'},
}
ALL_ALLOWED_EXTENSIONS = set()
for exts in FILE_TYPES.values():
    ALL_ALLOWED_EXTENSIONS |= exts


def _detect_file_type(suffix: str) -> str:
    """Determine how to handle a file based on extension."""
    for ftype, exts in FILE_TYPES.items():
        if suffix in exts:
            return ftype
    return "unknown"


def _image_to_video(image_path: str) -> tuple[str, dict]:
    """Convert a still image to a 1-frame 'video' temp file. Returns (path, info)."""
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    frame = np.array(img)
    # Create a temp MP4 with 1 frame held for 5 seconds
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    tmp.close()
    fps = 1.0
    duration = 5.0
    cmd = [
        shutil.which("ffmpeg") or "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-c:v", "libx264", "-t", str(duration),
        "-pix_fmt", "yuv420p", "-vf", f"scale={w + w % 2}:{h + h % 2}",
        tmp.name,
    ]
    subprocess.run(cmd, capture_output=True, check=True, timeout=30)
    info = {
        "width": w, "height": h, "fps": fps, "duration": duration,
        "has_audio": False, "codec": "h264",
        "total_frames": int(duration * fps),
        "source_type": "image",
    }
    return tmp.name, info


def _gif_to_video(gif_path: str) -> tuple[str, dict]:
    """Convert a GIF to MP4. Returns (path, info)."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    tmp.close()
    cmd = [
        shutil.which("ffmpeg") or "ffmpeg", "-y",
        "-i", gif_path,
        "-movflags", "faststart",
        "-pix_fmt", "yuv420p",
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        tmp.name,
    ]
    subprocess.run(cmd, capture_output=True, check=True, timeout=60)
    info = probe_video(tmp.name)
    info["source_type"] = "gif"
    return tmp.name, info


def _raw_to_video(raw_path: str, original_name: str) -> tuple[str, dict]:
    """Interpret raw file bytes as pixel data — creative glitch interpretation.
    Reads bytes, reshapes into an image, creates a static video from it."""
    data = Path(raw_path).read_bytes()
    # Cap at 2MB of raw data to prevent memory issues
    data = data[:2 * 1024 * 1024]
    arr = np.frombuffer(data, dtype=np.uint8)

    # Find dimensions that fit — aim for roughly 16:9
    total = len(arr)
    # Make divisible by 3 for RGB
    total = (total // 3) * 3
    if total < 3:
        raise ValueError("File too small to interpret as image data")
    arr = arr[:total]

    pixels = total // 3
    # Find width/height close to 16:9
    w = int(np.sqrt(pixels * 16 / 9))
    w = max(16, min(w, 1920))
    w = w + (w % 2)  # even
    h = pixels // w
    h = max(16, min(h, 1080))
    h = h + (h % 2)  # even
    usable = w * h * 3

    if usable > total:
        # Tile the data to fill
        repeats = (usable // total) + 1
        arr = np.tile(arr, repeats)[:usable]
    else:
        arr = arr[:usable]

    frame = arr.reshape((h, w, 3))

    # Save as image, then convert to video
    img_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    Image.fromarray(frame).save(img_tmp.name)
    img_tmp.close()

    try:
        video_path, info = _image_to_video(img_tmp.name)
        info["source_type"] = "raw_interpretation"
        info["original_name"] = original_name
        return video_path, info
    finally:
        os.unlink(img_tmp.name)


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload a file for processing. Accepts video, images, GIFs, and creative raw files."""
    # Validate filename
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    suffix = Path(file.filename).suffix.lower()
    if not suffix:
        suffix = ".bin"
    file_type = _detect_file_type(suffix)
    if file_type == "unknown":
        all_exts = sorted(ALL_ALLOWED_EXTENSIONS)
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Accepted: {', '.join(all_exts)}"
        )

    # Stream to temp file with size limit
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    total_size = 0
    try:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            total_size += len(chunk)
            if total_size > MAX_UPLOAD_SIZE:
                tmp.close()
                os.unlink(tmp.name)
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size: {MAX_UPLOAD_SIZE // (1024*1024)}MB"
                )
            tmp.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        tmp.close()
        os.unlink(tmp.name)
        raise HTTPException(status_code=500, detail=_error_detail("upload_failed", f"Upload failed: {e}"))
    tmp.close()

    try:
        # Route by file type
        if file_type == "video":
            video_path = tmp.name
            info = probe_video(video_path)
            info["source_type"] = "video"
        elif file_type == "image":
            video_path, info = _image_to_video(tmp.name)
            os.unlink(tmp.name)  # Clean up original
        elif file_type == "gif":
            video_path, info = _gif_to_video(tmp.name)
            os.unlink(tmp.name)
        elif file_type == "raw":
            video_path, info = _raw_to_video(tmp.name, file.filename)
            os.unlink(tmp.name)
        else:
            os.unlink(tmp.name)
            raise HTTPException(status_code=400, detail="Could not process file")

        # Lock state mutations (prevents race if two uploads overlap)
        async with _state_lock:
            # Clean up previous temp file
            old_path = _state.get("video_path")
            if old_path and os.path.exists(old_path):
                os.unlink(old_path)

            _state["video_path"] = video_path
            _state["video_info"] = info

            # Extract first frame for preview
            frame = extract_single_frame(video_path, 0)
            _state["current_frame"] = frame

        return {
            "status": "ok",
            "info": info,
            "preview": _frame_to_data_url(frame),
        }
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        raise HTTPException(status_code=400, detail=str(e))


MAX_CHAIN_LENGTH = 20  # Prevent CPU exhaustion from oversized chains


def _filter_video_level_effects(effects: list[dict]) -> tuple[list[dict], list[str]]:
    """Remove video-level effects from chain and return (filtered_effects, skipped_names).

    Video-level effects like realdatamosh operate on full videos and can't preview as single frames.
    """
    filtered = []
    skipped = []
    for effect in effects:
        if is_video_level(effect["name"]):
            skipped.append(effect["name"])
        else:
            filtered.append(effect)
    return filtered, skipped


@app.post("/api/preview")
async def preview_effect(chain: EffectChain):
    """Apply effect chain to a single frame and return preview."""
    if _state["video_path"] is None:
        raise HTTPException(status_code=400, detail=_error_detail("no_video", "No video loaded"))
    if len(chain.effects) > MAX_CHAIN_LENGTH:
        raise HTTPException(status_code=400, detail=_error_detail("too_many_effects", f"Too many effects (max {MAX_CHAIN_LENGTH})"))

    try:
        frame = extract_single_frame(_state["video_path"], chain.frame_number)

        # Cap resolution before applying effects to prevent CPU spikes
        MAX_PREVIEW_PIXELS = 1920 * 1080
        h, w = frame.shape[:2]
        if h * w > MAX_PREVIEW_PIXELS:
            scale = (MAX_PREVIEW_PIXELS / (h * w)) ** 0.5
            new_h, new_w = int(h * scale), int(w * scale)
            frame = np.array(Image.fromarray(frame).resize((new_w, new_h)))

        warning = None
        if chain.effects:
            # Filter out video-level effects that can't preview as single frames
            filtered_effects, skipped = _filter_video_level_effects(chain.effects)

            if skipped:
                warning = f"Skipped video-level effects (require full render): {', '.join(skipped)}"

            if filtered_effects:
                original = frame.copy() if chain.mix < 1.0 else None
                frame = apply_chain(frame, filtered_effects,
                                    frame_index=chain.frame_number,
                                    total_frames=_state["video_info"].get("total_frames", 1),
                                    watermark=False)
                # Wet/dry mix
                if original is not None:
                    mix = max(0.0, min(1.0, chain.mix))
                    frame = np.clip(
                        original.astype(float) * (1 - mix) + frame.astype(float) * mix,
                        0, 255
                    ).astype(np.uint8)

        result = {"preview": _frame_to_data_url(frame)}
        if warning:
            result["warning"] = warning
        return result
    except Exception as e:
        import logging
        logging.exception("Preview failed")
        raise HTTPException(status_code=500, detail=_error_detail("processing_failed", "Effect processing failed"))


class TimelinePreviewRequest(BaseModel):
    frame_number: int
    regions: list[dict]  # [{start, end, effects, muted, mask}]
    mix: float = 1.0


@app.post("/api/preview/timeline")
async def preview_timeline(req: TimelinePreviewRequest):
    """Preview a frame with timeline-aware region effects and optional spatial masks."""
    if _state["video_path"] is None:
        raise HTTPException(status_code=400, detail=_error_detail("no_video", "No video loaded"))

    try:
        frame = extract_single_frame(_state["video_path"], req.frame_number)

        # Cap resolution
        MAX_PREVIEW_PIXELS = 1920 * 1080
        h, w = frame.shape[:2]
        if h * w > MAX_PREVIEW_PIXELS:
            scale_factor = (MAX_PREVIEW_PIXELS / (h * w)) ** 0.5
            new_h, new_w = int(h * scale_factor), int(w * scale_factor)
            frame = np.array(Image.fromarray(frame).resize((new_w, new_h)))
            h, w = new_h, new_w

        original = frame.copy()
        processed = frame.copy()
        all_skipped = []

        # Apply each region that contains this frame
        for region in req.regions:
            if region.get("muted"):
                continue
            start = region.get("start", 0)
            end = region.get("end", 0)
            if start <= req.frame_number <= end:
                effects = region.get("effects", [])
                if not effects:
                    continue

                # Filter out video-level effects
                filtered_effects, skipped = _filter_video_level_effects(effects)
                all_skipped.extend(skipped)

                if not filtered_effects:
                    continue

                mask = region.get("mask")
                if mask and isinstance(mask, dict):
                    # Spatial mask: apply effects only to the masked rectangle
                    mx = max(0, int(mask.get("x", 0) * w))
                    my = max(0, int(mask.get("y", 0) * h))
                    mw = min(w - mx, int(mask.get("w", 1) * w))
                    mh = min(h - my, int(mask.get("h", 1) * h))
                    if mw > 0 and mh > 0:
                        # Extract sub-region, apply effects, composite back
                        sub_frame = processed[my:my+mh, mx:mx+mw].copy()
                        sub_frame = apply_chain(sub_frame, filtered_effects,
                                                frame_index=req.frame_number,
                                                total_frames=_state["video_info"].get("total_frames", 1),
                                                watermark=False)
                        processed[my:my+mh, mx:mx+mw] = sub_frame
                else:
                    # Full frame
                    processed = apply_chain(processed, filtered_effects,
                                            frame_index=req.frame_number,
                                            total_frames=_state["video_info"].get("total_frames", 1),
                                            watermark=False)

        # Wet/dry mix
        if req.mix < 1.0:
            mix = max(0.0, min(1.0, req.mix))
            processed = np.clip(
                original.astype(float) * (1 - mix) + processed.astype(float) * mix,
                0, 255
            ).astype(np.uint8)

        result = {"preview": _frame_to_data_url(processed)}
        if all_skipped:
            unique_skipped = list(dict.fromkeys(all_skipped))  # Remove duplicates, preserve order
            result["warning"] = f"Skipped video-level effects (require full render): {', '.join(unique_skipped)}"
        return result
    except Exception as e:
        import logging
        logging.exception("Timeline preview failed")
        raise HTTPException(status_code=500, detail="Timeline processing failed")


class FreezeRegionRequest(BaseModel):
    region_id: int
    start_frame: int
    end_frame: int
    effects: list[dict]
    automation: dict | None = None
    lfo_config: dict | None = None
    mix: float = 1.0


@app.post("/api/timeline/freeze")
async def freeze_region(req: FreezeRegionRequest):
    """Render a region's frames with all effects+automation baked.

    Returns path to the pre-rendered video file for frozen playback.
    """
    if _state["video_path"] is None:
        raise HTTPException(status_code=400, detail=_error_detail("no_video", "No video loaded"))

    from core.video_io import extract_frames, reassemble_video, load_frame, save_frame
    from core.automation import AutomationSession
    from core.modulation import LfoModulator
    import tempfile as tf

    info = _state["video_info"]

    auto_session = None
    if req.automation:
        auto_session = AutomationSession.from_dict(req.automation)

    lfo_mod = LfoModulator(req.lfo_config) if req.lfo_config else None

    with tf.TemporaryDirectory() as tmpdir:
        frames_dir = Path(tmpdir) / "frames"
        processed_dir = Path(tmpdir) / "processed"
        frames_dir.mkdir()
        processed_dir.mkdir()

        frame_files = extract_frames(_state["video_path"], str(frames_dir))
        total = len(frame_files)

        start = max(0, req.start_frame)
        end = min(total - 1, req.end_frame)

        for i in range(start, end + 1):
            if i >= len(frame_files):
                break
            frame = load_frame(frame_files[i])
            effects = req.effects

            if auto_session:
                effects = auto_session.apply_to_chain(effects, i)
            if lfo_mod:
                effects = lfo_mod.apply_to_chain(effects, i, info["fps"])

            if effects:
                original = frame.copy() if req.mix < 1.0 else None
                frame = apply_chain(frame, effects,
                                    frame_index=i,
                                    total_frames=total,
                                    watermark=False)
                if original is not None:
                    mix = max(0.0, min(1.0, req.mix))
                    frame = np.clip(
                        original.astype(float) * (1 - mix) + frame.astype(float) * mix,
                        0, 255
                    ).astype(np.uint8)

            save_frame(frame, str(processed_dir / f"frame_{i - start + 1:06d}.png"))

        # Reassemble frozen region
        freeze_name = f"freeze_region_{req.region_id}.mp4"
        freeze_path = EXPORT_DIR / "frozen" / freeze_name
        freeze_path.parent.mkdir(parents=True, exist_ok=True)

        reassemble_video(
            str(processed_dir), str(freeze_path), info["fps"],
            quality="hi"
        )

    size_mb = freeze_path.stat().st_size / (1024 * 1024)
    return {
        "status": "ok",
        "path": str(freeze_path),
        "region_id": req.region_id,
        "frames": end - start + 1,
        "size_mb": round(size_mb, 1),
    }


@app.delete("/api/timeline/freeze/{region_id}")
async def unfreeze_region(region_id: int):
    """Delete a frozen region's pre-rendered video."""
    freeze_path = EXPORT_DIR / "frozen" / f"freeze_region_{region_id}.mp4"
    if freeze_path.exists():
        freeze_path.unlink()
        return {"status": "ok", "region_id": region_id}
    return {"status": "not_found", "region_id": region_id}


class TimelineExportRequest(BaseModel):
    timeline_regions: list[dict]
    format: str = "mp4"
    mix: float = 1.0
    audio_mode: str = "copy"
    scale_algorithm: str = "lanczos"
    resolution_preset: str | None = None
    width: int | None = None
    height: int | None = None
    scale_factor: float | None = None
    fps_preset: str | None = None
    h264_crf: int = 23
    h264_preset: str = "medium"
    prores_profile: str = "422"
    gif_colors: int = 256
    webm_crf: int = 30
    effects: list[dict] = []  # Kept for compat but timeline uses region effects
    lfo_config: dict | None = None  # Optional LFO modulation for export


@app.post("/api/export/timeline")
async def export_timeline(req: TimelineExportRequest):
    """Export with timeline regions — each region applies its own effects with optional spatial masks."""
    if _state["video_path"] is None:
        raise HTTPException(status_code=400, detail=_error_detail("no_video", "No video loaded"))

    from core.video_io import extract_frames, load_frame, save_frame
    from core.modulation import LfoModulator
    import time as _time

    info = _state["video_info"]
    source_w, source_h = info["width"], info["height"]

    # Load LFO modulation if provided
    lfo_mod = LfoModulator(req.lfo_config) if req.lfo_config else None

    # Determine target dimensions
    target_w, target_h = source_w, source_h
    if req.resolution_preset and req.resolution_preset != "source":
        res_map = {
            "480p": (854, 480), "720p": (1280, 720), "1080p": (1920, 1080),
            "2k": (2560, 1440), "4k": (3840, 2160),
            "instagram_square": (1080, 1080), "instagram_story": (1080, 1920), "tiktok": (1080, 1920),
        }
        if req.resolution_preset in res_map:
            target_w, target_h = res_map[req.resolution_preset]
    if req.width and req.height:
        target_w, target_h = req.width, req.height
    if req.scale_factor:
        target_w = int(source_w * req.scale_factor)
        target_h = int(source_h * req.scale_factor)
    # Ensure even dimensions
    target_w = target_w + (target_w % 2)
    target_h = target_h + (target_h % 2)

    output_fps = float(req.fps_preset) if req.fps_preset else info["fps"]

    import tempfile as tf

    with tf.TemporaryDirectory() as tmpdir:
        frames_dir = Path(tmpdir) / "frames"
        processed_dir = Path(tmpdir) / "processed"
        frames_dir.mkdir()
        processed_dir.mkdir()

        extract_scale = min(1.0, target_w / source_w)
        frame_files = extract_frames(_state["video_path"], str(frames_dir), scale=extract_scale)
        if len(frame_files) > MAX_FRAMES_PER_RENDER:
            raise HTTPException(status_code=400, detail=_error_detail("video_too_long", f"Video too long ({len(frame_files)} frames, max {MAX_FRAMES_PER_RENDER})"))

        _render_progress["active"] = True
        _render_progress["total_frames"] = len(frame_files)
        _render_progress["phase"] = "processing"

        for i, fp in enumerate(frame_files):
            _render_progress["current_frame"] = i
            frame = load_frame(fp)
            h, w = frame.shape[:2]
            original = frame.copy()
            processed = frame.copy()

            # Apply timeline regions
            for region in req.timeline_regions:
                start = region.get("start", 0)
                end = region.get("end", 0)
                if start <= i <= end:
                    effects = region.get("effects", [])
                    if not effects:
                        continue
                    # Apply LFO modulation per frame
                    if lfo_mod:
                        effects = lfo_mod.apply_to_chain(effects, i, info["fps"])

                    mask = region.get("mask")
                    if mask and isinstance(mask, dict):
                        mx = max(0, int(mask.get("x", 0) * w))
                        my = max(0, int(mask.get("y", 0) * h))
                        mw = min(w - mx, int(mask.get("w", 1) * w))
                        mh = min(h - my, int(mask.get("h", 1) * h))
                        if mw > 0 and mh > 0:
                            sub_frame = processed[my:my+mh, mx:mx+mw].copy()
                            sub_frame = apply_chain(sub_frame, effects,
                                                    frame_index=i,
                                                    total_frames=len(frame_files),
                                                    watermark=True)
                            processed[my:my+mh, mx:mx+mw] = sub_frame
                    else:
                        processed = apply_chain(processed, effects,
                                                frame_index=i,
                                                total_frames=len(frame_files),
                                                watermark=True)

            # Wet/dry mix
            if req.mix < 1.0:
                mix_val = max(0.0, min(1.0, req.mix))
                processed = np.clip(
                    original.astype(float) * (1 - mix_val) + processed.astype(float) * mix_val,
                    0, 255
                ).astype(np.uint8)

            # Resize if needed
            ph, pw = processed.shape[:2]
            if (pw, ph) != (target_w, target_h):
                algo_map = {
                    "lanczos": Image.LANCZOS, "bilinear": Image.BILINEAR,
                    "bicubic": Image.BICUBIC, "nearest": Image.NEAREST,
                }
                algo = algo_map.get(req.scale_algorithm, Image.LANCZOS)
                processed = np.array(Image.fromarray(processed).resize((target_w, target_h), algo))

            save_frame(processed, str(processed_dir / f"frame_{i+1:06d}.png"))

        _render_progress["phase"] = "encoding"

        # Build output
        timestamp = int(_time.time())
        ext_map = {"mp4": ".mp4", "mov": ".mov", "gif": ".gif", "png_seq": "", "webm": ".webm"}
        ext = ext_map.get(req.format, ".mp4")
        output_name = f"entropic_{timestamp}{ext}"
        output_path = EXPORT_DIR / output_name

        if req.format == "mp4":
            cmd = [
                shutil.which("ffmpeg") or "ffmpeg", "-y",
                "-framerate", str(output_fps),
                "-i", str(processed_dir / "frame_%06d.png"),
                "-c:v", "libx264", "-crf", str(req.h264_crf),
                "-preset", req.h264_preset, "-pix_fmt", "yuv420p",
            ]
            if req.audio_mode != "strip" and info.get("has_audio"):
                if req.audio_mode == "copy":
                    cmd += ["-i", _state["video_path"], "-map", "0:v", "-map", "1:a?", "-c:a", "copy", "-shortest"]
                else:
                    cmd += ["-i", _state["video_path"], "-map", "0:v", "-map", "1:a?", "-c:a", "aac", "-b:a", "192k", "-shortest"]
            cmd.append(str(output_path))
            subprocess.run(cmd, capture_output=True, check=True, timeout=600)
        elif req.format == "mov":
            profile_map = {"proxy": "0", "lt": "1", "422": "2", "422hq": "3", "4444": "4"}
            profile_num = profile_map.get(req.prores_profile, "2")
            cmd = [
                shutil.which("ffmpeg") or "ffmpeg", "-y",
                "-framerate", str(output_fps),
                "-i", str(processed_dir / "frame_%06d.png"),
                "-c:v", "prores_ks", "-profile:v", profile_num,
                "-pix_fmt", "yuv422p10le" if profile_num != "4" else "yuva444p10le",
                str(output_path),
            ]
            subprocess.run(cmd, capture_output=True, check=True, timeout=600)
        elif req.format == "gif":
            cmd = [
                shutil.which("ffmpeg") or "ffmpeg", "-y",
                "-framerate", str(output_fps),
                "-i", str(processed_dir / "frame_%06d.png"),
                "-vf", f"fps=15,split[s0][s1];[s0]palettegen=max_colors={req.gif_colors}[p];[s1][p]paletteuse",
                "-loop", "0", str(output_path),
            ]
            subprocess.run(cmd, capture_output=True, check=True, timeout=300)
        elif req.format == "webm":
            cmd = [
                shutil.which("ffmpeg") or "ffmpeg", "-y",
                "-framerate", str(output_fps),
                "-i", str(processed_dir / "frame_%06d.png"),
                "-c:v", "libvpx-vp9", "-crf", str(req.webm_crf),
                "-b:v", "0", "-pix_fmt", "yuv420p", str(output_path),
            ]
            subprocess.run(cmd, capture_output=True, check=True, timeout=600)
        elif req.format == "png_seq":
            seq_dir = EXPORT_DIR / f"entropic_{timestamp}_seq"
            seq_dir.mkdir()
            for f in sorted(processed_dir.glob("*.png")):
                shutil.copy2(str(f), str(seq_dir / f.name))
            return {
                "status": "ok", "path": str(seq_dir),
                "frames": len(list(seq_dir.glob("*.png"))),
                "format": "png_seq", "dimensions": f"{target_w}x{target_h}",
            }

        _render_progress["active"] = False
        _render_progress["phase"] = "idle"

        size_mb = output_path.stat().st_size / (1024 * 1024)
        return {
            "status": "ok", "path": str(output_path),
            "size_mb": round(size_mb, 1), "format": req.format,
            "dimensions": f"{target_w}x{target_h}", "fps": output_fps,
        }


@app.get("/api/frame/{frame_number}")
async def get_frame(frame_number: int):
    """Get a raw frame without effects."""
    if _state["video_path"] is None:
        raise HTTPException(status_code=400, detail="No video loaded")
    frame = extract_single_frame(_state["video_path"], frame_number)
    return {"preview": _frame_to_data_url(frame)}


class ThumbnailRequest(BaseModel):
    effect_name: str
    frame_number: int = 0


@app.post("/api/preview/thumbnail")
async def preview_thumbnail(req: ThumbnailRequest):
    """Render a small thumbnail of a single effect for hover preview."""
    if _state["video_path"] is None:
        raise HTTPException(status_code=400, detail="No video loaded")
    try:
        frame = extract_single_frame(_state["video_path"], req.frame_number)
        # Downscale to 160px wide for speed
        h, w = frame.shape[:2]
        thumb_w = 160
        thumb_h = int(h * thumb_w / max(w, 1))
        frame = np.array(Image.fromarray(frame).resize((thumb_w, thumb_h)))

        frame = apply_chain(frame, [{"name": req.effect_name, "params": {}}],
                            frame_index=req.frame_number,
                            total_frames=_state["video_info"].get("total_frames", 1),
                            watermark=False)
        return {"preview": _frame_to_data_url(frame)}
    except Exception:
        raise HTTPException(status_code=400, detail="Thumbnail generation failed")


# ============ PROJECT SAVE/LOAD ============

PROJECTS_DIR = Path.home() / "Documents" / "Entropic Projects"


@app.post("/api/project/save")
async def save_project(project: dict):
    """Save project (timeline state) as JSON."""
    import json as _json
    import re
    import time as _time
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    name = project.get("name", f"project_{int(_time.time())}")
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', str(name).strip())
    if not safe_name:
        safe_name = f"project_{int(_time.time())}"
    filepath = PROJECTS_DIR / f"{safe_name}.entropic"
    filepath.write_text(_json.dumps(project, indent=2))
    return {"status": "ok", "path": str(filepath), "name": safe_name}


@app.post("/api/project/load")
async def load_project(body: dict):
    """Load project by path or list available projects."""
    import json as _json
    path = body.get("path")
    if path:
        filepath = Path(path)
        # Validate path is inside projects dir
        if not filepath.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        try:
            data = _json.loads(filepath.read_text())
            return {"status": "ok", "project": data}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid project file: {e}")
    else:
        # List available projects
        PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
        projects = []
        for f in sorted(PROJECTS_DIR.glob("*.entropic"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = _json.loads(f.read_text())
                projects.append({
                    "name": data.get("name", f.stem),
                    "path": str(f),
                    "modified": f.stat().st_mtime,
                })
            except Exception:
                continue
        return {"status": "ok", "projects": projects}


@app.get("/api/randomize")
async def randomize_chain():
    """Generate a random effect chain for experimentation."""
    import random
    count = random.randint(1, 3)
    chain_out = []
    for _ in range(count):
        name = random.choice(list(EFFECTS.keys()))
        params = {}
        for k, v in EFFECTS[name]["params"].items():
            if isinstance(v, float):
                params[k] = round(random.uniform(0, max(v * 2, 1.0)), 2)
            elif isinstance(v, int):
                params[k] = random.randint(0, max(v * 2, 10))
            elif isinstance(v, bool):
                params[k] = random.choice([True, False])
            elif isinstance(v, tuple):
                params[k] = [random.randint(-50, 50), random.randint(-50, 50)]
        chain_out.append({"name": name, "params": params})
    return {"effects": chain_out}


class PresetSave(BaseModel):
    name: str
    effects: list[dict]
    description: str = ""
    tags: list[str] = []


@app.get("/api/presets")
async def list_presets():
    """List all presets — built-in + user-saved."""
    import json as _json
    result = []

    # Built-in presets
    try:
        from presets import BUILT_IN_PRESETS
        for p in BUILT_IN_PRESETS:
            result.append({**p, "source": "built-in", "editable": False})
    except ImportError:
        pass

    # User presets
    for f in sorted(PRESETS_DIR.glob("*.json")):
        try:
            data = _json.loads(f.read_text())
            data["source"] = "user"
            data["editable"] = True
            data["id"] = f.stem
            result.append(data)
        except Exception:
            continue

    return {"presets": result}


@app.post("/api/presets")
async def save_preset(preset: PresetSave):
    """Save a user preset."""
    import json as _json
    import re
    # Sanitize name for filename
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', preset.name.strip().lower())
    if not safe_name:
        raise HTTPException(status_code=400, detail="Preset name required")
    filepath = PRESETS_DIR / f"{safe_name}.json"
    data = {
        "name": preset.name.strip(),
        "description": preset.description,
        "effects": preset.effects,
        "tags": preset.tags,
        "category": "User",
    }
    filepath.write_text(_json.dumps(data, indent=2))
    return {"status": "ok", "id": safe_name, "path": str(filepath)}


@app.delete("/api/presets/{preset_id}")
async def delete_preset(preset_id: str):
    """Delete a user preset."""
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', preset_id):
        raise HTTPException(status_code=400, detail="Invalid preset ID")
    filepath = PRESETS_DIR / f"{preset_id}.json"
    # Verify resolved path stays inside PRESETS_DIR
    if not filepath.resolve().parent == PRESETS_DIR.resolve():
        raise HTTPException(status_code=400, detail="Invalid preset path")
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Preset not found")
    filepath.unlink()
    return {"status": "ok"}


@app.get("/api/sample-frames")
async def sample_frames(count: int = 5):
    """Get evenly-spaced frames from the loaded video for overview."""
    if _state["video_path"] is None:
        raise HTTPException(status_code=400, detail="No video loaded")
    info = _state["video_info"]
    total = max(1, info.get("total_frames", 1))
    count = max(1, min(count, 10))  # Cap at 10 to prevent memory issues
    indices = [int(i * total / count) for i in range(count)]
    previews = []
    for idx in indices:
        frame = extract_single_frame(_state["video_path"], idx)
        previews.append({
            "frame": idx,
            "preview": _frame_to_data_url(frame),
        })
    return {"frames": previews}


@app.post("/api/render")
async def render_video(req: RenderRequest):
    """Render the loaded video with effects applied. Returns download path."""
    if _state["video_path"] is None:
        raise HTTPException(status_code=400, detail="No video loaded")

    from core.video_io import extract_frames, reassemble_video, load_frame, save_frame
    from core.automation import AutomationSession
    from core.modulation import LfoModulator
    import tempfile as tf

    info = _state["video_info"]
    quality = req.quality if req.quality in ("lo", "mid", "hi") else "mid"

    # Load automation if provided
    auto_session = None
    if req.automation:
        auto_session = AutomationSession.from_dict(req.automation)

    # Load LFO modulation if provided
    lfo_mod = LfoModulator(req.lfo_config) if req.lfo_config else None

    with tf.TemporaryDirectory() as tmpdir:
        frames_dir = Path(tmpdir) / "frames"
        processed_dir = Path(tmpdir) / "processed"
        frames_dir.mkdir()
        processed_dir.mkdir()

        # Extract frames
        scale = {"lo": 0.5, "mid": 0.75, "hi": 1.0}[quality]
        frame_files = extract_frames(_state["video_path"], str(frames_dir), scale=scale)
        if len(frame_files) > MAX_FRAMES_PER_RENDER:
            raise HTTPException(status_code=400, detail=f"Video too long ({len(frame_files)} frames, max {MAX_FRAMES_PER_RENDER})")

        # Disk space estimation: 2× frame PNGs (input + output) ~= 2× frames × resolution × 3 bytes
        w, h = int(info["width"] * scale), int(info["height"] * scale)
        est_png_bytes = w * h * 3  # Uncompressed; PNGs compress ~40-60%
        est_total_gb = (len(frame_files) * est_png_bytes * 2) / (1024 ** 3)
        try:
            disk_stat = os.statvfs(tmpdir)
            free_gb = (disk_stat.f_bavail * disk_stat.f_frsize) / (1024 ** 3)
            if est_total_gb > free_gb * 0.8:  # Leave 20% headroom
                raise HTTPException(status_code=400, detail=(
                    f"Render needs ~{est_total_gb:.1f}GB temp space but only {free_gb:.1f}GB free. "
                    f"Use lower quality or shorter clip."
                ))
        except OSError:
            pass  # Can't check — proceed with caution

        # Process each frame
        for i, fp in enumerate(frame_files):
            frame = load_frame(fp)
            if req.effects:
                # Apply automation overrides
                effects = auto_session.apply_to_chain(req.effects, i) if auto_session else req.effects
                # Apply LFO modulation per frame
                if lfo_mod:
                    effects = lfo_mod.apply_to_chain(effects, i, info["fps"])
                original = frame.copy() if req.mix < 1.0 else None
                frame = apply_chain(frame, effects,
                                    frame_index=i,
                                    total_frames=len(frame_files),
                                    watermark=True)
                if original is not None:
                    mix = max(0.0, min(1.0, req.mix))
                    # Normalize channels for blend (RGBA → strip alpha)
                    blend_frame = frame[:, :, :3] if frame.ndim == 3 and frame.shape[2] == 4 else frame
                    frame = np.clip(
                        original.astype(float) * (1 - mix) + blend_frame.astype(float) * mix,
                        0, 255
                    ).astype(np.uint8)
            # Ensure RGB for output (strip any RGBA alpha channel)
            if frame.ndim == 3 and frame.shape[2] == 4:
                frame = frame[:, :, :3]
            save_frame(frame, str(processed_dir / f"frame_{i+1:06d}.png"))

        # Reassemble
        output_name = f"entropic_render_{quality}.mp4"
        output_path = Path(tmpdir) / output_name
        audio_src = _state["video_path"] if info.get("has_audio") else None
        final = reassemble_video(
            str(processed_dir), str(output_path), info["fps"],
            audio_source=audio_src, quality=quality
        )

        # Copy to user-visible location
        dest = EXPORT_DIR / final.name
        shutil.copy2(str(final), str(dest))

    size_mb = dest.stat().st_size / (1024 * 1024)
    return {
        "status": "ok",
        "path": str(dest),
        "size_mb": round(size_mb, 1),
        "quality": quality,
    }


@app.get("/api/export-options")
async def get_export_options():
    """Return available export options for the UI."""
    from core.export_models import (
        ExportFormat, ScaleAlgorithm, H264Preset, ProResProfile,
        AudioMode, EXPORT_PRESETS, AspectMode,
    )
    return {
        "formats": [{"value": f.value, "label": {
            "mp4": "MP4 (H.264) — Web/Social",
            "mov": "MOV (ProRes) — Editing Pipeline",
            "gif": "GIF — Short Loops",
            "png_seq": "PNG Sequence — Compositing",
            "webm": "WebM (VP9) — Web Embed",
        }.get(f.value, f.value)} for f in ExportFormat],
        "resolutions": {
            "source": None,
            "480p": [854, 480], "720p": [1280, 720], "1080p": [1920, 1080],
            "1440p": [2560, 1440], "2160p": [3840, 2160],
        },
        "scale_algorithms": [a.value for a in ScaleAlgorithm],
        "aspect_modes": [m.value for m in AspectMode],
        "h264_presets": [p.value for p in H264Preset],
        "prores_profiles": [p.value for p in ProResProfile],
        "audio_modes": [m.value for m in AudioMode],
        "fps_presets": ["23.976", "24", "25", "29.97", "30", "50", "59.94", "60"],
        "export_presets": sorted(EXPORT_PRESETS.keys()),
    }


@app.post("/api/export")
async def export_video(export: ExportSettings):
    """Advanced export with full settings."""
    from core.export_models import ExportFormat
    from core.video_io import extract_frames, load_frame, save_frame
    from core.modulation import LfoModulator

    if _state["video_path"] is None:
        raise HTTPException(status_code=400, detail=_error_detail("no_video", "No video loaded"))

    info = _state["video_info"]
    source_w, source_h = info["width"], info["height"]
    target_w, target_h = export.get_target_dimensions(source_w, source_h)
    output_fps = export.get_output_fps(info["fps"])

    # Load LFO modulation if provided
    lfo_mod = LfoModulator(export.lfo_config) if export.lfo_config else None

    import tempfile as tf

    with tf.TemporaryDirectory() as tmpdir:
        frames_dir = Path(tmpdir) / "frames"
        processed_dir = Path(tmpdir) / "processed"
        frames_dir.mkdir()
        processed_dir.mkdir()

        # Calculate extraction scale (extract at target res when downscaling)
        extract_scale = min(1.0, target_w / source_w)
        frame_files = extract_frames(_state["video_path"], str(frames_dir), scale=extract_scale)
        if len(frame_files) > MAX_FRAMES_PER_RENDER:
            raise HTTPException(status_code=400, detail=_error_detail("video_too_long", f"Video too long ({len(frame_files)} frames, max {MAX_FRAMES_PER_RENDER})"))

        # Disk space estimation guard
        est_png_bytes = target_w * target_h * 3
        est_total_gb = (len(frame_files) * est_png_bytes * 2) / (1024 ** 3)
        try:
            disk_stat = os.statvfs(tmpdir)
            free_gb = (disk_stat.f_bavail * disk_stat.f_frsize) / (1024 ** 3)
            if est_total_gb > free_gb * 0.8:
                raise HTTPException(status_code=400, detail=_error_detail(
                    "disk_space", f"Export needs ~{est_total_gb:.1f}GB temp space but only {free_gb:.1f}GB free. "
                    f"Use lower resolution or shorter clip."
                ))
        except OSError:
            pass

        # Apply trim if specified
        start_idx = 0
        end_idx = len(frame_files)
        if export.frame_start is not None:
            start_idx = max(0, min(export.frame_start, len(frame_files) - 1))
        if export.frame_end is not None:
            end_idx = max(start_idx + 1, min(export.frame_end + 1, len(frame_files)))
        frame_files = frame_files[start_idx:end_idx]

        _render_progress["active"] = True
        _render_progress["total_frames"] = len(frame_files)
        _render_progress["phase"] = "processing"

        # Process each frame
        for i, fp in enumerate(frame_files):
            _render_progress["current_frame"] = i
            frame = load_frame(fp)

            # Apply effects with mix
            if export.effects:
                effects = export.effects
                # Apply LFO modulation per frame
                if lfo_mod:
                    effects = lfo_mod.apply_to_chain(effects, i, info["fps"])
                original = frame.copy() if export.mix < 1.0 else None
                frame = apply_chain(frame, effects,
                                    frame_index=i,
                                    total_frames=len(frame_files),
                                    watermark=True)
                if original is not None:
                    mix = max(0.0, min(1.0, export.mix))
                    # Normalize channels for blend (RGBA → strip alpha)
                    blend_frame = frame[:, :, :3] if frame.ndim == 3 and frame.shape[2] == 4 else frame
                    frame = np.clip(
                        original.astype(float) * (1 - mix) + blend_frame.astype(float) * mix,
                        0, 255
                    ).astype(np.uint8)

            # Ensure RGB for output (strip any RGBA alpha channel)
            if frame.ndim == 3 and frame.shape[2] == 4:
                frame = frame[:, :, :3]

            # Resize to target dimensions if different from extracted
            h_now, w_now = frame.shape[:2]
            if (w_now, h_now) != (target_w, target_h):
                img = Image.fromarray(frame)
                algo_map = {
                    "lanczos": Image.LANCZOS,
                    "bilinear": Image.BILINEAR,
                    "bicubic": Image.BICUBIC,
                    "nearest": Image.NEAREST,
                }
                algo = algo_map.get(export.scale_algorithm.value, Image.LANCZOS)
                img = img.resize((target_w, target_h), algo)
                frame = np.array(img)

            save_frame(frame, str(processed_dir / f"frame_{i+1:06d}.png"))

        # Build output filename
        ext = export.get_output_extension()
        import time
        timestamp = int(time.time())
        output_name = f"entropic_{timestamp}{ext}"

        if export.format == ExportFormat.PNG_SEQ:
            # Copy PNGs to renders dir
            seq_dir = EXPORT_DIR / f"entropic_{timestamp}_seq"
            seq_dir.mkdir()
            for f in sorted(processed_dir.glob("*.png")):
                shutil.copy2(str(f), str(seq_dir / f.name))
            return {
                "status": "ok",
                "path": str(seq_dir),
                "frames": len(list(seq_dir.glob("*.png"))),
                "format": "png_seq",
                "dimensions": f"{target_w}x{target_h}",
            }

        elif export.format == ExportFormat.GIF:
            output_path = EXPORT_DIR / output_name
            gif_fps = export.gif_fps or min(output_fps, 15)
            cmd = [
                shutil.which("ffmpeg") or "ffmpeg", "-y",
                "-framerate", str(output_fps),
                "-i", str(processed_dir / "frame_%06d.png"),
                "-vf", f"fps={gif_fps},split[s0][s1];[s0]palettegen=max_colors={export.gif_colors}[p];[s1][p]paletteuse" +
                       (":dither=floyd_steinberg" if export.gif_dithering else ":dither=none"),
                "-loop", str(export.gif_loop),
                str(output_path),
            ]
            subprocess.run(cmd, capture_output=True, check=True, timeout=300)

        elif export.format == ExportFormat.WEBM:
            output_path = EXPORT_DIR / output_name
            cmd = [
                shutil.which("ffmpeg") or "ffmpeg", "-y",
                "-framerate", str(output_fps),
                "-i", str(processed_dir / "frame_%06d.png"),
                "-c:v", "libvpx-vp9", "-crf", str(export.webm_crf),
                "-b:v", "0", "-pix_fmt", "yuv420p",
                str(output_path),
            ]
            if export.audio_mode != "strip" and info.get("has_audio"):
                cmd = cmd[:-1] + [
                    "-i", _state["video_path"], "-map", "0:v", "-map", "1:a?",
                    "-c:a", "libopus", "-shortest", str(output_path)
                ]
            subprocess.run(cmd, capture_output=True, check=True, timeout=600)

        elif export.format == ExportFormat.MOV:
            output_path = EXPORT_DIR / output_name
            profile_map = {
                "proxy": "0", "lt": "1", "422": "2", "422hq": "3", "4444": "4",
            }
            profile_num = profile_map.get(export.prores_profile.value, "2")
            cmd = [
                shutil.which("ffmpeg") or "ffmpeg", "-y",
                "-framerate", str(output_fps),
                "-i", str(processed_dir / "frame_%06d.png"),
                "-c:v", "prores_ks", "-profile:v", profile_num,
                "-pix_fmt", "yuv422p10le" if profile_num != "4" else "yuva444p10le",
            ]
            if export.audio_mode != "strip" and info.get("has_audio"):
                cmd += ["-i", _state["video_path"], "-map", "0:v", "-map", "1:a?",
                        "-c:a", "aac", "-b:a", export.audio_bitrate, "-shortest"]
            cmd.append(str(output_path))
            subprocess.run(cmd, capture_output=True, check=True, timeout=600)

        else:  # MP4 (H.264)
            output_path = EXPORT_DIR / output_name
            cmd = [
                shutil.which("ffmpeg") or "ffmpeg", "-y",
                "-framerate", str(output_fps),
                "-i", str(processed_dir / "frame_%06d.png"),
                "-c:v", "libx264",
                "-crf", str(export.h264_crf),
                "-preset", export.h264_preset.value,
                "-pix_fmt", "yuv420p",
            ]
            if export.audio_mode != "strip" and info.get("has_audio"):
                if export.audio_mode == "copy":
                    cmd += ["-i", _state["video_path"], "-map", "0:v", "-map", "1:a?",
                            "-c:a", "copy", "-shortest"]
                else:
                    cmd += ["-i", _state["video_path"], "-map", "0:v", "-map", "1:a?",
                            "-c:a", "aac", "-b:a", export.audio_bitrate, "-shortest"]
            cmd.append(str(output_path))
            subprocess.run(cmd, capture_output=True, check=True, timeout=600)

        _render_progress["active"] = False
        _render_progress["phase"] = "idle"

        size_mb = output_path.stat().st_size / (1024 * 1024)
        return {
            "status": "ok",
            "path": str(output_path),
            "size_mb": round(size_mb, 1),
            "format": export.format.value,
            "dimensions": f"{target_w}x{target_h}",
            "fps": output_fps,
        }


MAX_PREVIEW_DIMENSION = 1280  # Cap preview size to limit data URL bloat


def _frame_to_data_url(frame: np.ndarray) -> str:
    """Convert numpy frame to base64 data URL for <img> tag.
    Downscales large frames to keep data URLs under ~500KB."""
    # Strip alpha channel — JPEG doesn't support RGBA
    if frame.ndim == 3 and frame.shape[2] == 4:
        frame = frame[:, :, :3]
    img = Image.fromarray(frame)

    # Downscale if larger than preview limit
    w, h = img.size
    if max(w, h) > MAX_PREVIEW_DIMENSION:
        ratio = MAX_PREVIEW_DIMENSION / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=70)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/jpeg;base64,{b64}"


# ============ PERFORM MODE API ============

from core.layer import Layer, LayerStack, ADSR_PRESETS
from core.automation import PerformanceSession


class PerformInitRequest(BaseModel):
    layers: list[dict] | None = None  # Custom layer configs
    auto: bool = True                 # Auto-generate defaults


from typing import Literal
from pydantic import Field


_VALID_TRIGGER_MODES = ("toggle", "gate", "adsr", "one_shot", "always_on")
_VALID_EVENTS = ("on", "off", "opacity", "panic")
_MAX_EFFECTS_PER_LAYER = 20


class TriggerEvent(BaseModel):
    layer_id: int
    event: Literal["on", "off", "opacity", "panic"]
    value: float = Field(default=1.0, ge=0.0, le=1.0)


class PerformFrameRequest(BaseModel):
    frame_number: int = Field(ge=0)
    layer_states: list[dict] | None = None  # Legacy: [{layer_id, active, opacity}]
    trigger_events: list[TriggerEvent] | None = None


class PerformUpdateLayerRequest(BaseModel):
    layer_id: int
    trigger_mode: Literal["toggle", "gate", "adsr", "one_shot", "always_on"] | None = None
    adsr_preset: str | None = None
    blend_mode: str | None = None
    effects: list[dict] | None = None
    choke_group: int | None = -1  # -1 = don't change, None = remove, 0+ = set
    opacity: float | None = Field(default=None, ge=0.0, le=1.0)
    z_order: int | None = Field(default=None, ge=0, le=7)


class PerformSaveRequest(BaseModel):
    layers_config: list[dict]
    events: dict              # PerformanceSession dict
    duration_frames: int = Field(default=0, ge=0)


class PerformRenderRequest(BaseModel):
    layers_config: list[dict]
    events: dict
    duration_frames: int = Field(default=0, ge=0)
    fps: int = Field(default=30, ge=1, le=120)
    crf: int = Field(default=18, ge=0, le=51)


# Default layer presets for web perform mode (all use uploaded video)
_PERFORM_DEFAULTS = [
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
            {"name": "vhs", "params": {"tracking": 0.4, "noise_amount": 0.3}},
        ],
        "trigger_mode": "toggle",
        "adsr_preset": "sustain",
        "opacity": 0.8,
    },
    {
        "name": "PixelSort",
        "effects": [
            {"name": "pixelsort", "params": {"threshold": 0.5}},
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


@app.post("/api/perform/init")
async def perform_init(req: PerformInitRequest):
    """Initialize perform mode layers. Creates persistent LayerStack with ADSR envelopes."""
    if _state["video_path"] is None:
        raise HTTPException(status_code=400, detail="No video loaded. Upload a file first.")

    video_path = _state["video_path"]

    if req.layers:
        layer_dicts = req.layers
    else:
        # Build default 4 layers using uploaded video
        layer_dicts = []
        for i, preset in enumerate(_PERFORM_DEFAULTS):
            layer_dicts.append({
                "layer_id": i,
                "video_path": video_path,
                "z_order": i,
                "choke_group": None,
                "midi_note": None,
                "midi_cc_opacity": None,
                **preset,
            })

    # Create actual Layer objects with ADSR envelopes (persistent across frames)
    layers = [Layer.from_dict(ld) for ld in layer_dicts]
    stack = LayerStack(layers)
    async with _state_lock:
        _state["perf_stack"] = stack
        _state["perf_layers"] = layer_dicts
        _state["perf_frame_count"] = 0

    return {
        "status": "ok",
        "layers": layer_dicts,
        "adsr_presets": list(ADSR_PRESETS.keys()),
    }


@app.post("/api/perform/frame")
async def perform_frame(req: PerformFrameRequest):
    """Composite a perform-mode frame with stateful ADSR envelope processing.

    Accepts trigger events (on/off/opacity), advances all envelopes one frame,
    composites layers using computed ADSR opacity, and returns both the preview
    and current envelope states for client UI sync.
    """
    if _state["video_path"] is None:
        raise HTTPException(status_code=400, detail="No video loaded")

    stack: LayerStack | None = _state.get("perf_stack")
    if stack is None:
        raise HTTPException(status_code=400, detail="Perform mode not initialized. Call /api/perform/init first.")

    try:
        # --- 1. Process trigger events from client ---
        if req.trigger_events:
            for evt in req.trigger_events:
                layer = stack.get_layer(evt.layer_id)
                if layer is None:
                    continue
                if evt.event == "on":
                    stack.handle_choke(layer)
                    layer.trigger_on()
                elif evt.event == "off":
                    layer.trigger_off()
                elif evt.event == "opacity":
                    layer.set_opacity(evt.value)
                elif evt.event == "panic":
                    layer.reset()

        # Legacy fallback: if client sends layer_states instead of trigger_events,
        # apply raw active/opacity (no ADSR envelope)
        elif req.layer_states:
            for s in req.layer_states:
                layer = stack.get_layer(s.get("layer_id", -1))
                if layer is None:
                    continue
                layer.set_opacity(s.get("opacity", layer.opacity))

        # --- 2. Advance all ADSR envelopes one frame ---
        stack.advance_all()
        _state["perf_frame_count"] = _state.get("perf_frame_count", 0) + 1

        # --- 3. Extract base frame ---
        frame = extract_single_frame(_state["video_path"], req.frame_number)

        MAX_PREVIEW_PIXELS = 1920 * 1080
        h, w = frame.shape[:2]
        if h * w > MAX_PREVIEW_PIXELS:
            scale = (MAX_PREVIEW_PIXELS / (h * w)) ** 0.5
            new_h, new_w = int(h * scale), int(w * scale)
            frame = np.array(Image.fromarray(frame).resize((new_w, new_h)))

        # --- 4. Build per-layer frames (apply effects) ---
        frame_dict = {}
        for layer in stack.layers:
            if not layer.is_visible:
                continue
            layer_frame = frame.copy()
            if layer.effects:
                layer_frame = apply_chain(layer_frame, layer.effects,
                                          frame_index=_state.get("perf_frame_count", 0),
                                          total_frames=_state["video_info"].get("total_frames", 1),
                                          watermark=False)
            frame_dict[layer.layer_id] = layer_frame

        # --- 5. Composite using LayerStack (respects z-order + computed opacity) ---
        result = stack.composite(frame_dict)

        # --- 6. Build envelope state for client UI sync ---
        layer_info = []
        for layer in stack.layers:
            layer_info.append({
                "layer_id": layer.layer_id,
                "active": layer._active,
                "current_opacity": round(layer._current_opacity, 4),
                "phase": layer._adsr_envelope.phase,
                "envelope_level": round(layer._adsr_envelope.level, 4),
            })

        return {
            "preview": _frame_to_data_url(result),
            "layer_states": layer_info,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Frame processing error")


@app.post("/api/perform/update_layer")
async def perform_update_layer(req: PerformUpdateLayerRequest):
    """Update a layer's config on the persistent LayerStack (trigger mode, ADSR, effects, etc)."""
    stack: LayerStack | None = _state.get("perf_stack")
    if stack is None:
        raise HTTPException(status_code=400, detail="Perform mode not initialized.")

    layer = stack.get_layer(req.layer_id)
    if layer is None:
        raise HTTPException(status_code=404, detail=f"Layer {req.layer_id} not found")

    # Update trigger mode (resets envelope)
    if req.trigger_mode is not None:
        layer.trigger_mode = req.trigger_mode
        layer.reset()

    # Update ADSR preset (recreates envelope)
    if req.adsr_preset is not None:
        from core.layer import ADSR_PRESETS
        if req.adsr_preset not in ADSR_PRESETS:
            raise HTTPException(status_code=400, detail=f"Unknown ADSR preset: {req.adsr_preset}")
        layer.adsr_preset = req.adsr_preset
        layer._adsr_envelope = layer._create_envelope()

    # Update blend mode
    if req.blend_mode is not None:
        from core.layer import BLEND_MODES
        if req.blend_mode not in BLEND_MODES:
            raise HTTPException(status_code=400, detail=f"Unknown blend mode: {req.blend_mode}")
        layer.blend_mode = req.blend_mode

    # Update effects (capped at 20 to prevent CPU bombs)
    if req.effects is not None:
        if len(req.effects) > _MAX_EFFECTS_PER_LAYER:
            raise HTTPException(status_code=400, detail=f"Max {_MAX_EFFECTS_PER_LAYER} effects per layer")
        layer.effects = req.effects

    # Update choke group (-1 = don't change)
    if req.choke_group != -1:
        layer.choke_group = req.choke_group

    # Update base opacity
    if req.opacity is not None:
        layer.set_opacity(req.opacity)

    # Update z_order
    if req.z_order is not None:
        layer.z_order = req.z_order
        # Re-sort stack by z_order
        stack.layers.sort(key=lambda l: l.z_order)

    # Sync back to perf_layers config list
    for lc in _state.get("perf_layers", []):
        if lc["layer_id"] == req.layer_id:
            lc.update(layer.to_dict())
            break

    return {"status": "ok", "layer": layer.to_dict()}


@app.post("/api/perform/save")
async def perform_save(req: PerformSaveRequest):
    """Save a performance session (layers + automation events) to JSON."""
    import json as _json
    import time as _time

    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = int(_time.time())
    filename = f"performance_{timestamp}.json"
    filepath = PROJECTS_DIR / filename

    data = {
        "type": "performance",
        "layers_config": req.layers_config,
        "events": req.events,
        "duration_frames": req.duration_frames,
        "timestamp": timestamp,
    }
    filepath.write_text(_json.dumps(data, indent=2))

    return {"status": "ok", "path": str(filepath), "name": filename}


@app.post("/api/perform/render")
async def perform_render(req: PerformRenderRequest):
    """Render a recorded performance to full-quality video.

    Uses core/render.py render_performance() pipeline.
    """
    if _state["video_path"] is None:
        raise HTTPException(status_code=400, detail="No video loaded")

    import json as _json
    import time as _time
    import tempfile as tf

    # Save automation to temp file (render_performance expects a file path)
    with tf.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        _json.dump(req.events, tmp)
        automation_path = tmp.name

    # Ensure all layers have video_path set to current video
    layers_config = []
    for lc in req.layers_config:
        lc_copy = dict(lc)
        if not lc_copy.get("video_path"):
            lc_copy["video_path"] = _state["video_path"]
        layers_config.append(lc_copy)

    timestamp = int(_time.time())
    output_path = EXPORT_DIR / f"entropic_perform_{timestamp}.mp4"

    try:
        from core.render import render_performance
        info = _state["video_info"]
        audio_source = _state["video_path"] if info.get("has_audio") else None

        result_path = render_performance(
            layers_config=layers_config,
            automation_path=automation_path,
            output_path=str(output_path),
            fps=req.fps,
            duration=req.duration_frames / req.fps if req.duration_frames > 0 else None,
            audio_source=audio_source,
            crf=req.crf,
        )

        size_mb = Path(result_path).stat().st_size / (1024 * 1024)
        return {
            "status": "ok",
            "path": Path(result_path).name,  # Filename only, no full path leak
            "dir": str(EXPORT_DIR),
            "size_mb": round(size_mb, 1),
            "format": "mp4",
            "fps": req.fps,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Render failed")
    finally:
        # Clean up temp automation file
        if os.path.exists(automation_path):
            os.unlink(automation_path)


import atexit


def _cleanup_on_shutdown():
    """Remove temp video file on exit."""
    path = _state.get("video_path")
    if path and os.path.exists(path):
        os.unlink(path)


atexit.register(_cleanup_on_shutdown)


def start():
    import uvicorn
    print("Entropic — launching at http://127.0.0.1:7860")
    uvicorn.run(app, host="127.0.0.1", port=7860, log_level="warning")


if __name__ == "__main__":
    start()

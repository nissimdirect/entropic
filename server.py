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
import time
import threading
from pathlib import Path
from io import BytesIO

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
import numpy as np
from PIL import Image

from effects import EFFECTS, CATEGORIES, CATEGORY_ORDER, apply_chain, is_video_level
from effects.color import compute_histogram
from packages import PACKAGES
from core.video_io import probe_video, extract_single_frame, stream_frames, open_output_pipe
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


class NoCacheStaticMiddleware(BaseHTTPMiddleware):
    """Prevent browsers (especially Safari) from caching static files during development."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static") or request.url.path == "/":
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


app.add_middleware(NoCacheStaticMiddleware)

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

# Freeze cache: track_idx -> {frames: {frame_num: numpy_array}, lock: asyncio.Lock, last_access: float, flattened: bool}
_freeze_cache = {}
_freeze_cache_lock = asyncio.Lock()  # Global lock for cache eviction

# Cache limits
MAX_TRACKS = 8
FREEZE_CACHE_MAX_BYTES = 2 * 1024 * 1024 * 1024  # 2GB

# Render progress tracking (polled by frontend during export)
_render_progress = {
    "active": False,
    "current_frame": 0,
    "total_frames": 0,
    "phase": "idle",  # "extracting", "processing", "encoding", "idle"
    "cancel_requested": False,
}
_render_progress_lock = threading.Lock()


# Chunk preview progress tracking (polled by frontend during chunk playback)
_chunk_progress = {
    "active": False,
    "frame": 0,
    "total": 0,
    "ready": False,
    "cancel": False,
    "url": "",
    "error": "",
}
_chunk_progress_lock = threading.Lock()

# Temp dir for chunk files (cleaned up per-request)
_CHUNK_DIR = Path(tempfile.gettempdir()) / "entropic_chunks"
_CHUNK_DIR.mkdir(exist_ok=True)


def _set_chunk_progress(**kwargs):
    """Thread-safe update of chunk progress dict."""
    with _chunk_progress_lock:
        _chunk_progress.update(kwargs)


def _get_chunk_progress():
    """Thread-safe snapshot of chunk progress dict."""
    with _chunk_progress_lock:
        return dict(_chunk_progress)


def _set_progress(**kwargs):
    """SEC-1: Thread-safe update of render progress dict."""
    with _render_progress_lock:
        _render_progress.update(kwargs)


def _get_progress():
    """SEC-1: Thread-safe snapshot of render progress dict."""
    with _render_progress_lock:
        return dict(_render_progress)


class ExportCancelledError(Exception):
    """Raised when user cancels an in-progress export."""
    pass

# Safety guard: max frames per render to prevent CPU/memory exhaustion
MAX_FRAMES_PER_RENDER = 10000

# Per-frame processing timeout (seconds)
FRAME_TIMEOUT_SECONDS = 30
PREVIEW_TIMEOUT_SECONDS = 5  # Shorter timeout for preview (vs render)

# Playback preview resolution cap
PLAYBACK_MAX_PIXELS = 640 * 360

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
    "invalid_track": {"code": "INVALID_TRACK", "hint": "Track index out of bounds.", "action": None},
    "invalid_blend_mode": {"code": "INVALID_BLEND_MODE", "hint": "Use a valid blend mode (normal, multiply, screen, add, overlay, darken, lighten).", "action": None},
    "not_frozen": {"code": "NOT_FROZEN", "hint": "Freeze the track before flattening.", "action": "freeze"},
    "no_frames": {"code": "NO_FRAMES", "hint": "Track has no cached frames.", "action": "freeze"},
}


def _error_detail(key: str, message: str, effect_name: str = "") -> dict:
    """Build structured error detail dict for frontend handleApiError()."""
    recovery = ERROR_RECOVERY.get(key, {})
    result = {
        "detail": message,
        "code": recovery.get("code", "UNKNOWN"),
        "hint": recovery.get("hint", ""),
        "action": recovery.get("action"),
    }
    if effect_name:
        result["effect_name"] = effect_name
    return result


def _run_ffmpeg(cmd: list, timeout: int = 600) -> subprocess.CompletedProcess:
    """Run an FFmpeg command with detailed error surfacing on failure."""
    try:
        return subprocess.run(cmd, capture_output=True, check=True, timeout=timeout)
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or b"").decode("utf-8", errors="replace").strip()
        # Extract the most useful part of FFmpeg stderr (last 500 chars usually has the error)
        stderr_tail = stderr[-500:] if len(stderr) > 500 else stderr
        msg = f"FFmpeg encoding failed (exit code {e.returncode}): {stderr_tail}"
        _set_progress(active=False, phase="idle")
        detail = _error_detail("render_failed", msg)
        detail["ffmpeg_stderr"] = stderr_tail
        raise HTTPException(status_code=500, detail=detail)
    except subprocess.TimeoutExpired:
        _set_progress(active=False, phase="idle")
        raise HTTPException(status_code=500, detail=_error_detail(
            "render_failed", f"FFmpeg encoding timed out after {timeout}s. Try a shorter video or simpler codec."
        ))


def _validate_output(output_path: Path) -> None:
    """Validate that an exported video file is valid using ffprobe."""
    if not output_path.exists():
        raise HTTPException(status_code=500, detail=_error_detail(
            "render_failed", "Export produced no output file."
        ))
    if output_path.stat().st_size == 0:
        output_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=_error_detail(
            "render_failed", "Export produced an empty file (0 bytes)."
        ))
    # Probe with ffprobe for valid container
    ffprobe = shutil.which("ffprobe") or "ffprobe"
    try:
        probe_result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(output_path)],
            capture_output=True, timeout=30
        )
        duration_str = probe_result.stdout.decode("utf-8", errors="replace").strip()
        if probe_result.returncode != 0 or not duration_str:
            stderr = probe_result.stderr.decode("utf-8", errors="replace").strip()
            output_path.unlink(missing_ok=True)
            raise HTTPException(status_code=500, detail=_error_detail(
                "render_failed", f"Export produced an invalid file. ffprobe: {stderr[:200]}"
            ))
    except subprocess.TimeoutExpired:
        pass  # If ffprobe times out, file is probably fine — don't block


def _apply_chain_with_timeout(frame, effects, frame_index, total_frames, watermark=True, timeout=None):
    """Apply effect chain with per-frame timeout protection."""
    import concurrent.futures
    t = timeout or FRAME_TIMEOUT_SECONDS
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            apply_chain, frame, effects,
            frame_index=frame_index, total_frames=total_frames, watermark=watermark
        )
        try:
            return future.result(timeout=t)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(
                f"Frame {frame_index + 1} processing timed out after {t}s"
            )


def _apply_frame_cutout(original, processed, params):
    """Composite a clean center rectangle over a processed frame (or inverse).

    Creates a "picture frame" effect: border = processed/effected, center = clean original.
    With invert=True: center = effected, border = clean.

    Args:
        original: Clean frame (H, W, 3) uint8 numpy array.
        processed: Effected frame (H, W, 3) uint8 numpy array.
        params: Dict with center_x, center_y, width, height, feather, opacity, invert, shape.

    Returns:
        Composited frame (H, W, 3) uint8 numpy array.
    """
    h, w = original.shape[:2]

    cx = float(params.get('center_x', 0.5))
    cy = float(params.get('center_y', 0.5))
    rw = float(params.get('width', 0.6))
    rh = float(params.get('height', 0.6))
    feather = float(params.get('feather', 0.15))
    opacity = float(params.get('opacity', 1.0))
    invert = bool(params.get('invert', False))
    shape = params.get('shape', 'rectangle')

    # Clamp params
    opacity = max(0.0, min(1.0, opacity))
    feather = max(0.0, min(1.0, feather))

    # Build mask (1.0 = show original, 0.0 = show processed)
    mask = np.zeros((h, w), dtype=np.float32)

    if shape == 'ellipse':
        # Ellipse mask using distance from center
        yy, xx = np.mgrid[0:h, 0:w]
        # Normalize to 0-1
        nx = (xx / w - cx) / (rw / 2 + 1e-6)
        ny = (yy / h - cy) / (rh / 2 + 1e-6)
        dist = nx * nx + ny * ny
        mask = np.clip(1.0 - dist, 0.0, 1.0)
        # Sharpen if low feather
        if feather < 0.01:
            mask = (dist <= 1.0).astype(np.float32)
    else:
        # Rectangle mask
        x1 = int(max(0, (cx - rw / 2) * w))
        y1 = int(max(0, (cy - rh / 2) * h))
        x2 = int(min(w, (cx + rw / 2) * w))
        y2 = int(min(h, (cy + rh / 2) * h))
        if x2 > x1 and y2 > y1:
            mask[y1:y2, x1:x2] = 1.0

    # Feathering via gaussian blur
    if feather > 0.005:
        from scipy.ndimage import gaussian_filter
        sigma = feather * min(w, h) * 0.15
        sigma = max(1.0, sigma)
        mask = gaussian_filter(mask, sigma=sigma)

    if invert:
        mask = 1.0 - mask

    # Apply opacity
    mask = mask * opacity

    # Composite: result = original * mask + processed * (1 - mask)
    mask_3d = mask[:, :, np.newaxis]
    result = original.astype(np.float32) * mask_3d + processed.astype(np.float32) * (1.0 - mask_3d)
    return np.clip(result, 0, 255).astype(np.uint8)


class EffectChain(BaseModel):
    effects: list[dict]  # [{"name": "pixelsort", "params": {"threshold": 0.5}}, ...]
    frame_number: int = 0
    mix: float = 1.0  # Wet/dry blend: 0.0 = original, 1.0 = fully processed
    quality: str = 'full'  # 'full' or 'playback' (lower res for live playback)
    frame_cutout: dict | None = None  # {center_x, center_y, width, height, feather, opacity, invert, shape}


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
    return _get_progress()


@app.post("/api/export/cancel")
async def cancel_export():
    """Request cancellation of a running export."""
    progress = _get_progress()
    if not progress["active"]:
        return {"status": "no_export_running"}
    _set_progress(cancel_requested=True)
    return {"status": "cancel_requested"}


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
        max_pixels = PLAYBACK_MAX_PIXELS if chain.quality == 'playback' else 1920 * 1080
        h, w = frame.shape[:2]
        if h * w > max_pixels:
            scale = (max_pixels / (h * w)) ** 0.5
            new_h, new_w = int(h * scale), int(w * scale)
            frame = np.array(Image.fromarray(frame).resize((new_w, new_h)))

        warning = None
        # Preserve original for frame cutout compositing
        need_original = chain.mix < 1.0 or chain.frame_cutout
        original = frame.copy() if need_original else None

        if chain.effects:
            # Filter out video-level effects that can't preview as single frames
            filtered_effects, skipped = _filter_video_level_effects(chain.effects)

            if skipped:
                warning = f"Skipped video-level effects (require full render): {', '.join(skipped)}"

            if filtered_effects:
                frame = _apply_chain_with_timeout(frame, filtered_effects,
                                    frame_index=chain.frame_number,
                                    total_frames=_state["video_info"].get("total_frames", 1),
                                    watermark=False,
                                    timeout=PREVIEW_TIMEOUT_SECONDS)
                # Wet/dry mix
                if original is not None and chain.mix < 1.0:
                    mix = max(0.0, min(1.0, chain.mix))
                    frame = np.clip(
                        original.astype(float) * (1 - mix) + frame.astype(float) * mix,
                        0, 255
                    ).astype(np.uint8)

        # Frame cutout: composite clean center over processed frame
        if chain.frame_cutout and original is not None:
            frame = _apply_frame_cutout(original, frame, chain.frame_cutout)

        result = {"preview": _frame_to_data_url(frame)}
        if warning:
            result["warning"] = warning
        return result
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.exception("Preview failed")
        # Try to identify which effect caused the error
        effect_name = ""
        try:
            if filtered_effects:
                effect_name = filtered_effects[-1].get("name", "") if isinstance(filtered_effects[-1], dict) else ""
        except NameError:
            pass
        raise HTTPException(status_code=500, detail=_error_detail(
            "processing_failed", f"Effect processing failed: {str(e)[:100]}", effect_name=effect_name))


class MultiTrackPreviewRequest(BaseModel):
    frame_number: int
    tracks: list[dict]  # [{name, effects, opacity, blend_mode, muted, solo}]
    quality: str = 'full'


@app.post("/api/preview/multitrack")
async def preview_multitrack(req: MultiTrackPreviewRequest):
    """Preview a frame composited from multiple tracks with blend modes."""
    if _state["video_path"] is None:
        raise HTTPException(status_code=400, detail=_error_detail("no_video", "No video loaded"))

    # Blend mode whitelist (SEC-5)
    ALLOWED_BLEND_MODES = ["normal", "multiply", "screen", "add", "overlay", "darken", "lighten"]

    try:
        from core.layer import Layer, LayerStack

        # Validate blend modes
        for i, track in enumerate(req.tracks):
            blend_mode = track.get("blend_mode", "normal")
            if blend_mode not in ALLOWED_BLEND_MODES:
                raise HTTPException(
                    status_code=400,
                    detail=_error_detail(
                        "invalid_blend_mode",
                        f"Invalid blend mode '{blend_mode}' on track {i}. Allowed: {', '.join(ALLOWED_BLEND_MODES)}"
                    )
                )

        # Determine which tracks are audible (solo logic)
        any_solo = any(t.get("solo", False) for t in req.tracks)

        layers = []
        for i, track in enumerate(req.tracks):
            is_muted = track.get("muted", False)
            is_solo = track.get("solo", False)
            # If any track is soloed, only soloed tracks are visible
            if any_solo and not is_solo:
                continue
            if is_muted:
                continue

            layers.append(Layer(
                layer_id=i,
                name=track.get("name", f"Track {i + 1}"),
                video_path=_state["video_path"],
                effects=track.get("effects", []),
                opacity=max(0.0, min(1.0, track.get("opacity", 1.0))),
                z_order=i,
                blend_mode=track.get("blend_mode", "normal"),
                trigger_mode="always_on",
            ))

        if not layers:
            # All muted — return black frame
            frame = extract_single_frame(_state["video_path"], req.frame_number)
            black = np.zeros_like(frame)
            return {"preview": _frame_to_data_url(black)}

        stack = LayerStack(layers)

        # Load the source frame once and apply each track's effects
        raw_frame = extract_single_frame(_state["video_path"], req.frame_number)

        # Cap resolution (lower for playback)
        max_pixels = PLAYBACK_MAX_PIXELS if req.quality == 'playback' else 1920 * 1080
        h, w = raw_frame.shape[:2]
        if h * w > max_pixels:
            scale = (max_pixels / (h * w)) ** 0.5
            new_h, new_w = int(h * scale), int(w * scale)
            raw_frame = np.array(Image.fromarray(raw_frame).resize((new_w, new_h)))

        total_frames = _state["video_info"].get("total_frames", 1)

        frame_dict = {}
        for i, layer in enumerate(layers):
            # Check if this track is frozen — use cached frame if available
            track_data = req.tracks[i]
            if track_data.get("frozen", False) and i in _freeze_cache:
                track_cache = _freeze_cache[i]
                cached_frame = track_cache.get("frames", {}).get(req.frame_number)
                if cached_frame is not None:
                    # Update last access time
                    track_cache["last_access"] = time.time()
                    frame_dict[layer.layer_id] = cached_frame
                    continue

            # Not frozen or no cache — apply effects normally
            effects = layer.effects
            if effects:
                filtered, _ = _filter_video_level_effects(effects)
                if filtered:
                    processed = _apply_chain_with_timeout(
                        raw_frame.copy(), filtered,
                        frame_index=req.frame_number,
                        total_frames=total_frames,
                        watermark=False,
                        timeout=PREVIEW_TIMEOUT_SECONDS,
                    )
                else:
                    processed = raw_frame.copy()
            else:
                processed = raw_frame.copy()
            frame_dict[layer.layer_id] = processed

        composited = stack.composite(frame_dict)
        return {"preview": _frame_to_data_url(composited)}

    except HTTPException:
        raise  # Don't swallow validation errors (blend mode, bounds, etc.)
    except Exception as e:
        import logging
        logging.exception("Multitrack preview failed")
        raise HTTPException(status_code=500, detail=_error_detail("processing_failed", "Multi-track preview failed"))


def _get_cache_size_bytes() -> int:
    """Calculate total memory used by freeze cache."""
    total = 0
    for track_idx, track_cache in _freeze_cache.items():
        if "frames" in track_cache:
            for frame in track_cache["frames"].values():
                total += frame.nbytes
    return total


async def _evict_lru_cache(target_bytes: int):
    """Evict least-recently-used tracks until cache is under target size.

    Args:
        target_bytes: Target cache size to achieve after eviction.
    """
    async with _freeze_cache_lock:
        current_size = _get_cache_size_bytes()

        if current_size <= target_bytes:
            return  # Already under limit

        # Sort tracks by last_access (oldest first)
        sorted_tracks = sorted(
            _freeze_cache.items(),
            key=lambda x: x[1].get("last_access", 0)
        )

        # Evict oldest tracks until under limit
        for track_idx, _ in sorted_tracks:
            if _get_cache_size_bytes() <= target_bytes:
                break
            del _freeze_cache[track_idx]


class FreezeTrackRequest(BaseModel):
    track_index: int
    effects: list[dict]


@app.post("/api/track/freeze")
async def freeze_track(req: FreezeTrackRequest):
    """Render all frames with track effects and cache them server-side."""
    if req.track_index < 0 or req.track_index >= MAX_TRACKS:
        raise HTTPException(status_code=400, detail=_error_detail("invalid_track", f"Track index {req.track_index} out of bounds (0-{MAX_TRACKS-1})"))

    if _state["video_path"] is None:
        raise HTTPException(status_code=400, detail=_error_detail("no_video", "No video loaded"))

    total_frames = _state["video_info"].get("total_frames", 1)

    # Cap at 300 frames
    if total_frames > 300:
        raise HTTPException(
            status_code=400,
            detail=_error_detail(
                "video_too_long",
                f"Cannot freeze: video has {total_frames} frames (max 300)"
            )
        )

    # Initialize track cache entry if needed
    async with _freeze_cache_lock:
        if req.track_index not in _freeze_cache:
            _freeze_cache[req.track_index] = {
                "frames": {},
                "lock": asyncio.Lock(),
                "last_access": time.time(),
                "flattened": False,
            }

    track_cache = _freeze_cache[req.track_index]

    # Acquire per-track lock to prevent concurrent freezes
    async with track_cache["lock"]:
        try:
            # Estimate memory needed for new frames
            sample_frame = extract_single_frame(_state["video_path"], 0)
            bytes_per_frame = sample_frame.nbytes
            estimated_total = bytes_per_frame * total_frames

            # Evict LRU tracks if this would exceed 2GB
            if _get_cache_size_bytes() + estimated_total > FREEZE_CACHE_MAX_BYTES:
                await _evict_lru_cache(FREEZE_CACHE_MAX_BYTES - estimated_total)

            # Clear any existing frames for this track
            track_cache["frames"] = {}
            track_cache["last_access"] = time.time()

            # Render each frame
            for frame_num in range(total_frames):
                frame = extract_single_frame(_state["video_path"], frame_num)

                # Apply effects chain
                if req.effects:
                    frame = apply_chain(
                        frame,
                        req.effects,
                        frame_index=frame_num,
                        total_frames=total_frames,
                        watermark=False
                    )

                # Store as numpy array (much more efficient than data URL)
                track_cache["frames"][frame_num] = frame

            return {
                "frozen": True,
                "frames": total_frames
            }

        except HTTPException:
            raise
        except Exception as e:
            import logging
            logging.exception("Track freeze failed")
            raise HTTPException(status_code=500, detail=_error_detail("freeze_failed", "Track freeze failed"))


@app.post("/api/track/unfreeze")
async def unfreeze_track(track_index: int):
    """Clear freeze cache for a track."""
    if track_index < 0 or track_index >= MAX_TRACKS:
        raise HTTPException(status_code=400, detail=_error_detail("invalid_track", f"Track index {track_index} out of bounds (0-{MAX_TRACKS-1})"))

    async with _freeze_cache_lock:
        if track_index in _freeze_cache:
            del _freeze_cache[track_index]

    return {"frozen": False}


@app.post("/api/track/flatten")
async def flatten_track(track_index: int):
    """Commit frozen frames as the new source for this track.

    Marks the track as flattened. Frontend should clear its effect chain.
    """
    if track_index < 0 or track_index >= MAX_TRACKS:
        raise HTTPException(status_code=400, detail=_error_detail("invalid_track", f"Track index {track_index} out of bounds (0-{MAX_TRACKS-1})"))

    async with _freeze_cache_lock:
        if track_index not in _freeze_cache:
            raise HTTPException(status_code=400, detail=_error_detail("not_frozen", f"Track {track_index} is not frozen"))

        track_cache = _freeze_cache[track_index]
        if not track_cache.get("frames"):
            raise HTTPException(status_code=400, detail=_error_detail("no_frames", f"Track {track_index} has no cached frames"))

        # Mark as flattened
        track_cache["flattened"] = True
        track_cache["last_access"] = time.time()

    return {"flattened": True}


class TimelinePreviewRequest(BaseModel):
    frame_number: int
    regions: list[dict]  # [{start, end, effects, muted, mask}]
    mix: float = 1.0
    quality: str = 'full'
    frame_cutout: dict | None = None  # {center_x, center_y, width, height, feather, opacity, invert, shape}


@app.post("/api/preview/timeline")
async def preview_timeline(req: TimelinePreviewRequest):
    """Preview a frame with timeline-aware region effects and optional spatial masks."""
    if _state["video_path"] is None:
        raise HTTPException(status_code=400, detail=_error_detail("no_video", "No video loaded"))

    try:
        frame = extract_single_frame(_state["video_path"], req.frame_number)

        # Cap resolution (lower for playback)
        max_pixels = PLAYBACK_MAX_PIXELS if req.quality == 'playback' else 1920 * 1080
        h, w = frame.shape[:2]
        if h * w > max_pixels:
            scale_factor = (max_pixels / (h * w)) ** 0.5
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
                        sub_frame = _apply_chain_with_timeout(sub_frame, filtered_effects,
                                                frame_index=req.frame_number,
                                                total_frames=_state["video_info"].get("total_frames", 1),
                                                watermark=False,
                                                timeout=PREVIEW_TIMEOUT_SECONDS)
                        processed[my:my+mh, mx:mx+mw] = sub_frame
                else:
                    # Full frame
                    processed = _apply_chain_with_timeout(processed, filtered_effects,
                                            frame_index=req.frame_number,
                                            total_frames=_state["video_info"].get("total_frames", 1),
                                            watermark=False,
                                            timeout=PREVIEW_TIMEOUT_SECONDS)

        # Wet/dry mix
        if req.mix < 1.0:
            mix = max(0.0, min(1.0, req.mix))
            processed = np.clip(
                original.astype(float) * (1 - mix) + processed.astype(float) * mix,
                0, 255
            ).astype(np.uint8)

        # Frame cutout: composite clean center over processed frame
        if req.frame_cutout:
            processed = _apply_frame_cutout(original, processed, req.frame_cutout)

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
    if req.region_id < 0:
        raise HTTPException(status_code=400, detail=_error_detail("invalid_track", f"Region ID {req.region_id} must be >= 0"))

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
    if region_id < 0:
        raise HTTPException(status_code=400, detail=_error_detail("invalid_track", f"Region ID {region_id} must be >= 0"))
    freeze_path = (EXPORT_DIR / "frozen" / f"freeze_region_{region_id}.mp4").resolve()
    # SEC-3: Validate path is inside frozen dir (prevent path traversal via crafted region_id)
    frozen_dir = (EXPORT_DIR / "frozen").resolve()
    if not str(freeze_path).startswith(str(frozen_dir) + "/"):
        raise HTTPException(status_code=403, detail=_error_detail("invalid_track", "Invalid region ID"))
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

        _set_progress(active=True, total_frames=len(frame_files), phase="processing", cancel_requested=False, current_frame=0)

        for i, fp in enumerate(frame_files):
            # Check for cancellation
            if _get_progress().get("cancel_requested"):
                _set_progress(active=False, phase="idle", cancel_requested=False)
                raise HTTPException(status_code=499, detail=_error_detail(
                    "render_failed", f"Export cancelled by user at frame {i + 1}/{len(frame_files)}"
                ))

            _set_progress(current_frame=i)
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
                            sub_frame = _apply_chain_with_timeout(sub_frame, effects,
                                                    frame_index=i,
                                                    total_frames=len(frame_files),
                                                    watermark=True)
                            processed[my:my+mh, mx:mx+mw] = sub_frame
                    else:
                        processed = _apply_chain_with_timeout(processed, effects,
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

        _set_progress(phase="encoding")

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
            _run_ffmpeg(cmd, timeout=600)
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
            _run_ffmpeg(cmd, timeout=600)
        elif req.format == "gif":
            cmd = [
                shutil.which("ffmpeg") or "ffmpeg", "-y",
                "-framerate", str(output_fps),
                "-i", str(processed_dir / "frame_%06d.png"),
                "-vf", f"fps=15,split[s0][s1];[s0]palettegen=max_colors={req.gif_colors}[p];[s1][p]paletteuse",
                "-loop", "0", str(output_path),
            ]
            _run_ffmpeg(cmd, timeout=300)
        elif req.format == "webm":
            cmd = [
                shutil.which("ffmpeg") or "ffmpeg", "-y",
                "-framerate", str(output_fps),
                "-i", str(processed_dir / "frame_%06d.png"),
                "-c:v", "libvpx-vp9", "-crf", str(req.webm_crf),
                "-b:v", "0", "-pix_fmt", "yuv420p", str(output_path),
            ]
            _run_ffmpeg(cmd, timeout=600)
        elif req.format == "png_seq":
            seq_dir = EXPORT_DIR / f"entropic_{timestamp}_seq"
            seq_dir.mkdir()
            for f in sorted(processed_dir.glob("*.png")):
                shutil.copy2(str(f), str(seq_dir / f.name))
            _set_progress(active=False, phase="idle")
            return {
                "status": "ok", "path": str(seq_dir),
                "frames": len(list(seq_dir.glob("*.png"))),
                "format": "png_seq", "dimensions": f"{target_w}x{target_h}",
            }

        # Validate output file integrity
        _validate_output(output_path)

        _set_progress(active=False, phase="idle")

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
        filepath = Path(path).resolve()
        # SEC-2: Validate path is inside projects dir (prevent path traversal)
        projects_resolved = PROJECTS_DIR.resolve()
        if not str(filepath).startswith(str(projects_resolved) + "/") and filepath != projects_resolved:
            raise HTTPException(status_code=403, detail="Access denied: path outside projects directory")
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
    target_w, target_h = export.resolution.resolve_dimensions(source_w, source_h)
    output_fps = export.frame_rate.resolve_numeric(info["fps"])

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
        if export.trim.mode.value == "frames":
            start_idx = max(0, min(export.trim.start_frame, len(frame_files) - 1))
            if export.trim.end_frame is not None:
                end_idx = max(start_idx + 1, min(export.trim.end_frame + 1, len(frame_files)))
        elif export.trim.mode.value == "time":
            fps = info.get("fps", 30)
            start_idx = max(0, int(export.trim.start_time * fps))
            if export.trim.end_time is not None:
                end_idx = max(start_idx + 1, int(export.trim.end_time * fps) + 1)
            start_idx = min(start_idx, len(frame_files) - 1)
            end_idx = min(end_idx, len(frame_files))
        frame_files = frame_files[start_idx:end_idx]

        _set_progress(active=True, total_frames=len(frame_files), phase="processing", cancel_requested=False, current_frame=0)

        # Build multi-track layer stack if tracks provided
        use_multitrack = export.tracks and len(export.tracks) > 0
        mt_layers = None
        mt_stack = None
        if use_multitrack:
            from core.layer import Layer, LayerStack

            # Validate blend modes (SEC-5)
            ALLOWED_BLEND_MODES = ["normal", "multiply", "screen", "add", "overlay", "darken", "lighten"]
            for ti, track in enumerate(export.tracks):
                blend_mode = track.get("blend_mode", "normal")
                if blend_mode not in ALLOWED_BLEND_MODES:
                    raise HTTPException(
                        status_code=400,
                        detail=_error_detail(
                            "invalid_blend_mode",
                            f"Invalid blend mode '{blend_mode}' on track {ti}. Allowed: {', '.join(ALLOWED_BLEND_MODES)}"
                        )
                    )

            any_solo = any(t.get("solo", False) for t in export.tracks)
            mt_layers = []
            for ti, track in enumerate(export.tracks):
                is_muted = track.get("muted", False)
                is_solo = track.get("solo", False)
                if any_solo and not is_solo:
                    continue
                if is_muted:
                    continue
                mt_layers.append(Layer(
                    layer_id=ti,
                    name=track.get("name", f"Track {ti + 1}"),
                    video_path=_state["video_path"],
                    effects=track.get("effects", []),
                    opacity=max(0.0, min(1.0, track.get("opacity", 1.0))),
                    z_order=ti,
                    blend_mode=track.get("blend_mode", "normal"),
                    trigger_mode="always_on",
                ))
            mt_stack = LayerStack(mt_layers) if mt_layers else None

        # Process each frame
        last_successful_frame = -1
        current_effect_name = ""
        try:
            for i, fp in enumerate(frame_files):
                # Check for cancellation
                if _get_progress().get("cancel_requested"):
                    _set_progress(active=False, phase="idle", cancel_requested=False)
                    detail = _error_detail("render_failed", f"Export cancelled by user at frame {i + 1}/{len(frame_files)}")
                    detail["last_successful_frame"] = last_successful_frame
                    detail["total_frames"] = len(frame_files)
                    detail["cancelled"] = True
                    raise HTTPException(status_code=499, detail=detail)

                _set_progress(current_frame=i)
                frame = load_frame(fp)

                if use_multitrack and mt_stack:
                    frame_dict = {}
                    for layer in mt_layers:
                        if layer.effects:
                            filtered, _ = _filter_video_level_effects(layer.effects)
                            if filtered:
                                current_effect_name = f"track '{layer.name}' effects"
                                eff = lfo_mod.apply_to_chain(filtered, i, info["fps"]) if lfo_mod else filtered
                                processed = _apply_chain_with_timeout(
                                    frame.copy(), eff,
                                    frame_index=i,
                                    total_frames=len(frame_files),
                                    watermark=True,
                                )
                            else:
                                processed = frame.copy()
                        else:
                            processed = frame.copy()
                        frame_dict[layer.layer_id] = processed
                    current_effect_name = ""
                    frame = mt_stack.composite(frame_dict)
                elif use_multitrack and not mt_stack:
                    frame = np.zeros_like(frame)
                elif export.effects:
                    effects = export.effects
                    if lfo_mod:
                        effects = lfo_mod.apply_to_chain(effects, i, info["fps"])
                    current_effect_name = ", ".join(e.get("name", "?") for e in effects[:3])
                    if len(effects) > 3:
                        current_effect_name += f" (+{len(effects) - 3} more)"
                    original = frame.copy() if export.mix < 1.0 else None
                    frame = _apply_chain_with_timeout(frame, effects,
                                        frame_index=i,
                                        total_frames=len(frame_files),
                                        watermark=True)
                    current_effect_name = ""
                    if original is not None:
                        mix = max(0.0, min(1.0, export.mix))
                        blend_frame = frame[:, :, :3] if frame.ndim == 3 and frame.shape[2] == 4 else frame
                        frame = np.clip(
                            original.astype(float) * (1 - mix) + blend_frame.astype(float) * mix,
                            0, 255
                        ).astype(np.uint8)

                if frame.ndim == 3 and frame.shape[2] == 4:
                    frame = frame[:, :, :3]

                h_now, w_now = frame.shape[:2]
                if (w_now, h_now) != (target_w, target_h):
                    img = Image.fromarray(frame)
                    algo_map = {
                        "lanczos": Image.LANCZOS,
                        "bilinear": Image.BILINEAR,
                        "bicubic": Image.BICUBIC,
                        "nearest": Image.NEAREST,
                    }
                    algo = algo_map.get(export.resolution.get_scale_algorithm(source_w, source_h).value, Image.LANCZOS)
                    img = img.resize((target_w, target_h), algo)
                    frame = np.array(img)

                save_frame(frame, str(processed_dir / f"frame_{i+1:06d}.png"))
                last_successful_frame = i
        except HTTPException:
            raise  # Re-raise cancellation HTTPException
        except Exception as e:
            import logging
            logging.exception(f"Export failed at frame {i}")
            _set_progress(active=False, phase="idle")
            effect_info = f" (effect: {current_effect_name})" if current_effect_name else ""
            detail = _error_detail("render_failed", f"Export failed at frame {i + 1}/{len(frame_files)}{effect_info}: {str(e)[:200]}")
            detail["last_successful_frame"] = last_successful_frame
            detail["total_frames"] = len(frame_files)
            if current_effect_name:
                detail["failed_effect"] = current_effect_name
            raise HTTPException(status_code=500, detail=detail)

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
            gif_fps = export.gif.fps or min(output_fps, 15)
            dither_val = export.gif.dither.value
            cmd = [
                shutil.which("ffmpeg") or "ffmpeg", "-y",
                "-framerate", str(output_fps),
                "-i", str(processed_dir / "frame_%06d.png"),
                "-vf", f"fps={gif_fps},split[s0][s1];[s0]palettegen=max_colors={export.gif.max_colors}[p];[s1][p]paletteuse" +
                       (f":dither={dither_val}" if dither_val != "none" else ":dither=none"),
                "-loop", str(export.gif.loop_count),
                str(output_path),
            ]
            _set_progress(phase="encoding")
            _run_ffmpeg(cmd, timeout=300)

        elif export.format == ExportFormat.WEBM:
            output_path = EXPORT_DIR / output_name
            cmd = [
                shutil.which("ffmpeg") or "ffmpeg", "-y",
                "-framerate", str(output_fps),
                "-i", str(processed_dir / "frame_%06d.png"),
                "-c:v", "libvpx-vp9", "-crf", str(export.webm.crf),
                "-b:v", "0", "-pix_fmt", "yuv420p",
                str(output_path),
            ]
            if export.audio.mode.value != "strip" and info.get("has_audio"):
                cmd = cmd[:-1] + [
                    "-i", _state["video_path"], "-map", "0:v", "-map", "1:a?",
                    "-c:a", "libopus", "-shortest", str(output_path)
                ]
            _set_progress(phase="encoding")
            _run_ffmpeg(cmd, timeout=600)

        elif export.format == ExportFormat.MOV:
            output_path = EXPORT_DIR / output_name
            profile_map = {
                "proxy": "0", "lt": "1", "422": "2", "422hq": "3", "4444": "4",
            }
            profile_num = profile_map.get(str(export.prores.profile.value), "2")
            cmd = [
                shutil.which("ffmpeg") or "ffmpeg", "-y",
                "-framerate", str(output_fps),
                "-i", str(processed_dir / "frame_%06d.png"),
                "-c:v", "prores_ks", "-profile:v", profile_num,
                "-pix_fmt", "yuv422p10le" if profile_num != "4" else "yuva444p10le",
            ]
            if export.audio.mode.value != "strip" and info.get("has_audio"):
                cmd += ["-i", _state["video_path"], "-map", "0:v", "-map", "1:a?",
                        "-c:a", "aac", "-b:a", export.audio.bitrate, "-shortest"]
            cmd.append(str(output_path))
            _set_progress(phase="encoding")
            _run_ffmpeg(cmd, timeout=600)

        else:  # MP4 (H.264)
            output_path = EXPORT_DIR / output_name
            cmd = [
                shutil.which("ffmpeg") or "ffmpeg", "-y",
                "-framerate", str(output_fps),
                "-i", str(processed_dir / "frame_%06d.png"),
                "-c:v", "libx264",
                "-crf", str(export.h264.crf),
                "-preset", export.h264.preset.value,
                "-pix_fmt", "yuv420p",
            ]
            if export.audio.mode.value != "strip" and info.get("has_audio"):
                if export.audio.mode.value == "copy":
                    cmd += ["-i", _state["video_path"], "-map", "0:v", "-map", "1:a?",
                            "-c:a", "copy", "-shortest"]
                else:
                    cmd += ["-i", _state["video_path"], "-map", "0:v", "-map", "1:a?",
                            "-c:a", "aac", "-b:a", export.audio.bitrate, "-shortest"]
            cmd.append(str(output_path))
            _set_progress(phase="encoding")
            _run_ffmpeg(cmd, timeout=600)

        # Validate output file integrity
        _validate_output(output_path)

        _set_progress(active=False, phase="idle")

        size_mb = output_path.stat().st_size / (1024 * 1024)
        return {
            "status": "ok",
            "path": str(output_path),
            "size_mb": round(size_mb, 1),
            "format": export.format.value,
            "dimensions": f"{target_w}x{target_h}",
            "fps": output_fps,
        }


MAX_PREVIEW_DIMENSION = 1920  # Cap preview size to limit data URL bloat


def _frame_to_data_url(frame: np.ndarray) -> str:
    """Convert numpy frame to base64 data URL for img tag.
    RGBA frames get composited onto checkerboard and encoded as PNG.
    RGB frames get encoded as JPEG. Large frames are downscaled."""
    has_alpha = frame.ndim == 3 and frame.shape[2] == 4

    if has_alpha:
        # Composite RGBA onto checkerboard for preview
        h, w = frame.shape[:2]
        tile = 8
        rows = np.arange(h) // tile
        cols = np.arange(w) // tile
        pattern = ((rows[:, None] + cols[None, :]) % 2).astype(np.uint8)
        checker = np.where(pattern[:, :, None], np.uint8(255), np.uint8(200))
        alpha = frame[:, :, 3:4].astype(np.float32) / 255.0
        rgb = frame[:, :, :3].astype(np.float32)
        composited = (rgb * alpha + checker.astype(np.float32) * (1 - alpha))
        frame = np.clip(composited, 0, 255).astype(np.uint8)

    img = Image.fromarray(frame)
    w, h = img.size
    if max(w, h) > MAX_PREVIEW_DIMENSION:
        ratio = MAX_PREVIEW_DIMENSION / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    buf = BytesIO()
    if has_alpha:
        img.save(buf, format="PNG", optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/png;base64,{b64}"
    else:
        img.save(buf, format="JPEG", quality=70)
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/jpeg;base64,{b64}"


# ============ PERFORM MODE API ============

from core.layer import Layer, LayerStack, ADSR_PRESETS
from core.automation import PerformanceSession


class PerformInitRequest(BaseModel):
    layers: list[dict] | None = None  # Custom layer configs
    auto: bool = True                 # Auto-generate defaults
    master_effects: list[dict] = []   # Master bus effects (applied after composite)


from typing import Literal
from pydantic import Field


_VALID_TRIGGER_MODES = ("toggle", "gate", "adsr", "one_shot", "always_on")
_VALID_EVENTS = ("on", "off", "opacity", "panic")
_MAX_EFFECTS_PER_LAYER = 20


class TriggerEvent(BaseModel):
    layer_id: int = Field(ge=0, lt=MAX_TRACKS)
    event: Literal["on", "off", "opacity", "panic"]
    value: float = Field(default=1.0, ge=0.0, le=1.0)


class PerformFrameRequest(BaseModel):
    frame_number: int = Field(ge=0)
    layer_states: list[dict] | None = None  # Legacy: [{layer_id, active, opacity}]
    trigger_events: list[TriggerEvent] | None = None


class PerformUpdateLayerRequest(BaseModel):
    layer_id: int = Field(ge=0, lt=MAX_TRACKS)
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
        _state["perf_master_effects"] = req.master_effects

    return {
        "status": "ok",
        "layers": layer_dicts,
        "master_effects": req.master_effects,
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

        # --- 5b. Apply master bus effects (post-composite processing) ---
        master_fx = _state.get("perf_master_effects", [])
        if master_fx:
            result = apply_chain(result, master_fx,
                                 frame_index=_state.get("perf_frame_count", 0),
                                 total_frames=_state["video_info"].get("total_frames", 1),
                                 watermark=False)

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


class PerformMasterRequest(BaseModel):
    effects: list[dict] = []


@app.post("/api/perform/master")
async def perform_update_master(req: PerformMasterRequest):
    """Update the master bus effects chain (applied after layer composite)."""
    if _state.get("perf_stack") is None:
        raise HTTPException(status_code=400, detail="Perform mode not initialized.")
    if len(req.effects) > 10:
        raise HTTPException(status_code=400, detail="Max 10 master bus effects")
    _state["perf_master_effects"] = req.effects
    return {"status": "ok", "master_effects": req.effects}


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


# ============ CHUNK PREVIEW (Sprint 1: Hybrid Real-Time Preview) ============

# Chunk cleanup interval (seconds) — delete chunk files older than this
_CHUNK_TTL_SECONDS = 60


class ChunkRequest(BaseModel):
    start_frame: int = 0
    duration_frames: int = 90  # ~3 seconds at 30fps
    regions: list[dict] = []   # Same format as timeline preview
    tracks: list[dict] = []    # Same format as multitrack preview
    mix: float = 1.0
    mode: str = 'timeline'     # 'timeline' | 'multitrack' | 'flat'
    effects: list[dict] = []   # For flat mode
    quality: str = 'playback'  # 'playback' (640x360) | 'full'
    frame_cutout: dict | None = None  # {center_x, center_y, width, height, feather, opacity, invert, shape}


def _cleanup_old_chunks():
    """Delete chunk files older than TTL."""
    now = time.time()
    for f in _CHUNK_DIR.glob("chunk_*.mp4"):
        try:
            if now - f.stat().st_mtime > _CHUNK_TTL_SECONDS:
                f.unlink(missing_ok=True)
        except OSError:
            pass


def _render_chunk_sync(video_path, chunk_path, req: ChunkRequest, video_info: dict):
    """Render a preview chunk to disk (runs in thread pool).

    Decodes frames via stream_frames(), applies effect chain, encodes to H.264.
    """
    fps = video_info.get("fps", 30)
    total_video_frames = video_info.get("total_frames", 1)

    # Determine scale from quality
    max_pixels = PLAYBACK_MAX_PIXELS if req.quality == 'playback' else 1920 * 1080

    # Probe to get dimensions at scale
    orig_w = video_info.get("width", 640)
    orig_h = video_info.get("height", 360)
    if orig_w * orig_h > max_pixels:
        scale = (max_pixels / (orig_w * orig_h)) ** 0.5
    else:
        scale = 1.0

    # Cap duration to remaining frames
    remaining = max(0, total_video_frames - req.start_frame)
    num_frames = min(req.duration_frames, remaining)
    if num_frames <= 0:
        _set_chunk_progress(active=False, ready=False, error="No frames to render")
        return

    _set_chunk_progress(active=True, frame=0, total=num_frames, ready=False, cancel=False, error="")

    pipe_out = None
    frame_gen = None
    try:
        frame_gen = stream_frames(video_path, scale=scale, start_frame=req.start_frame)
        first_frame = True

        for i, raw_frame in enumerate(frame_gen):
            if i >= num_frames:
                break

            # Check for cancellation
            if _get_chunk_progress().get("cancel"):
                _set_chunk_progress(active=False, ready=False, error="Cancelled")
                break

            frame = raw_frame
            frame_index = req.start_frame + i

            # Apply effects based on mode
            if req.mode == 'timeline' and req.regions:
                for region in req.regions:
                    if region.get("muted"):
                        continue
                    start = region.get("start", 0)
                    end = region.get("end", 0)
                    if start <= frame_index <= end:
                        effects = region.get("effects", [])
                        if not effects:
                            continue
                        filtered, _ = _filter_video_level_effects(effects)
                        if filtered:
                            frame = _apply_chain_with_timeout(
                                frame, filtered,
                                frame_index=frame_index,
                                total_frames=total_video_frames,
                                watermark=False,
                                timeout=PREVIEW_TIMEOUT_SECONDS
                            )
            elif req.mode == 'flat' and req.effects:
                filtered, _ = _filter_video_level_effects(req.effects)
                if filtered:
                    frame = _apply_chain_with_timeout(
                        frame, filtered,
                        frame_index=frame_index,
                        total_frames=total_video_frames,
                        watermark=False,
                        timeout=PREVIEW_TIMEOUT_SECONDS
                    )

            # Wet/dry mix
            if req.mix < 1.0:
                mix = max(0.0, min(1.0, req.mix))
                frame = np.clip(
                    raw_frame.astype(float) * (1 - mix) + frame.astype(float) * mix,
                    0, 255
                ).astype(np.uint8)

            # Frame cutout: composite clean center over processed frame
            if req.frame_cutout:
                frame = _apply_frame_cutout(raw_frame, frame, req.frame_cutout)

            # Open output pipe on first frame (now we know dimensions)
            if first_frame:
                h, w = frame.shape[:2]
                pipe_out = open_output_pipe(str(chunk_path), w, h, fps=fps, crf=28)
                first_frame = False

            pipe_out.stdin.write(frame.tobytes())
            _set_chunk_progress(frame=i + 1)

        # Close encode pipe
        if pipe_out:
            pipe_out.stdin.close()
            pipe_out.wait(timeout=30)

        if _get_chunk_progress().get("cancel"):
            # Clean up cancelled chunk
            Path(chunk_path).unlink(missing_ok=True)
            return

        if Path(chunk_path).exists() and Path(chunk_path).stat().st_size > 0:
            _set_chunk_progress(active=False, ready=True, url=f"/api/preview/chunk/file/{Path(chunk_path).name}")
        else:
            _set_chunk_progress(active=False, ready=False, error="Chunk encoding produced no output")

    except Exception as e:
        import logging
        logging.exception("Chunk render failed")
        _set_chunk_progress(active=False, ready=False, error=str(e)[:200])
        if pipe_out:
            try:
                pipe_out.stdin.close()
                pipe_out.kill()
                pipe_out.wait(timeout=5)
            except Exception:
                pass
    finally:
        # P1-3: Explicitly close the generator to release FFmpeg subprocess immediately
        if frame_gen is not None:
            frame_gen.close()


@app.post("/api/preview/chunk")
async def preview_chunk(req: ChunkRequest):
    """Start rendering a preview chunk. Returns immediately; poll progress endpoint."""
    if _state["video_path"] is None:
        raise HTTPException(status_code=400, detail=_error_detail("no_video", "No video loaded"))

    # Clean up old chunks
    _cleanup_old_chunks()

    # Cancel any in-flight chunk render before starting a new one (P1-1: race condition guard)
    if _get_chunk_progress().get("active"):
        _set_chunk_progress(cancel=True)
        # Brief wait for the render thread to notice the cancel flag
        await asyncio.sleep(0.1)

    # If no effects, return source video path directly (no re-encode needed)
    has_effects = bool(req.regions) or bool(req.tracks) or bool(req.effects)
    if not has_effects:
        _set_chunk_progress(active=False, ready=True, frame=0, total=0, cancel=False, error="",
                           url="/api/preview/chunk/source")
        return {"status": "ready", "url": "/api/preview/chunk/source"}

    # P1-2: Reject unsupported multitrack mode (not implemented in chunk render)
    if req.mode == 'multitrack':
        raise HTTPException(status_code=400, detail="Multitrack chunk preview not yet supported. Use timeline mode.")

    # Generate unique chunk filename
    chunk_name = f"chunk_{int(time.time() * 1000)}.mp4"
    chunk_path = _CHUNK_DIR / chunk_name

    video_path = _state["video_path"]
    video_info = _state["video_info"]

    # Reset progress
    _set_chunk_progress(active=True, frame=0, total=req.duration_frames, ready=False, cancel=False, error="", url="")

    # Run chunk render in background thread
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _render_chunk_sync, video_path, chunk_path, req, video_info)

    return {"status": "rendering", "poll": "/api/preview/chunk/progress"}


@app.get("/api/preview/chunk/progress")
async def chunk_progress():
    """Poll chunk render progress."""
    return _get_chunk_progress()


@app.post("/api/preview/chunk/cancel")
async def chunk_cancel():
    """Cancel in-flight chunk rendering."""
    progress = _get_chunk_progress()
    if not progress["active"]:
        return {"status": "no_chunk_rendering"}
    _set_chunk_progress(cancel=True)
    return {"status": "cancel_requested"}


@app.get("/api/preview/chunk/file/{filename}")
async def chunk_file(filename: str):
    """Serve a rendered chunk file."""
    # SEC: sanitize filename to prevent path traversal
    safe_name = Path(filename).name
    chunk_path = _CHUNK_DIR / safe_name
    if not chunk_path.exists():
        raise HTTPException(status_code=404, detail="Chunk not found")
    return FileResponse(str(chunk_path), media_type="video/mp4")


@app.get("/api/preview/chunk/source")
async def chunk_source():
    """Serve the source video directly (for no-effects playback)."""
    if _state["video_path"] is None:
        raise HTTPException(status_code=400, detail=_error_detail("no_video", "No video loaded"))
    return FileResponse(str(_state["video_path"]), media_type="video/mp4")


import atexit


def _cleanup_on_shutdown():
    """Remove temp video file and chunk files on exit."""
    path = _state.get("video_path")
    if path and os.path.exists(path):
        os.unlink(path)
    # Clean up all chunk files
    for f in _CHUNK_DIR.glob("chunk_*.mp4"):
        try:
            f.unlink(missing_ok=True)
        except OSError:
            pass


atexit.register(_cleanup_on_shutdown)


def start():
    import uvicorn
    print("Entropic — launching at http://127.0.0.1:7860")
    uvicorn.run(app, host="127.0.0.1", port=7860, log_level="warning")


if __name__ == "__main__":
    start()

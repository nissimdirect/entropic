#!/usr/bin/env python3
"""
Entropic — FastAPI Backend
Serves the DAW-style UI and handles effect processing via API.
"""

import sys
import os
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

from effects import EFFECTS, apply_chain
from core.video_io import probe_video, extract_single_frame

app = FastAPI(title="Entropic")

# Serve static files (UI)
UI_DIR = Path(__file__).parent / "ui"
app.mount("/static", StaticFiles(directory=str(UI_DIR / "static")), name="static")

# In-memory state for current session
_state = {
    "video_path": None,
    "video_info": None,
    "current_frame": None,
}


class EffectChain(BaseModel):
    effects: list[dict]  # [{"name": "pixelsort", "params": {"threshold": 0.5}}, ...]
    frame_number: int = 0


@app.get("/")
async def index():
    return FileResponse(str(UI_DIR / "index.html"))


@app.get("/api/effects")
async def list_effects():
    """List all available effects with their parameters."""
    result = []
    for name, entry in EFFECTS.items():
        params = {}
        for k, v in entry["params"].items():
            if isinstance(v, bool):
                params[k] = {"type": "bool", "default": v}
            elif isinstance(v, int):
                params[k] = {"type": "int", "default": v, "min": 0, "max": max(v * 4, 10)}
            elif isinstance(v, float):
                params[k] = {"type": "float", "default": v, "min": 0.0, "max": max(v * 4, 2.0), "step": 0.01}
            elif isinstance(v, tuple):
                params[k] = {"type": "xy", "default": list(v), "min": -100, "max": 100}
            elif isinstance(v, str):
                params[k] = {"type": "string", "default": v}
        result.append({
            "name": name,
            "description": entry["description"],
            "params": params,
        })
    return result


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file for processing."""
    # Save to temp file
    suffix = Path(file.filename).suffix or ".mp4"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    content = await file.read()
    tmp.write(content)
    tmp.close()

    try:
        info = probe_video(tmp.name)
        _state["video_path"] = tmp.name
        _state["video_info"] = info

        # Extract first frame for preview
        frame = extract_single_frame(tmp.name, 0)
        _state["current_frame"] = frame

        return {
            "status": "ok",
            "info": info,
            "preview": _frame_to_data_url(frame),
        }
    except Exception as e:
        os.unlink(tmp.name)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/preview")
async def preview_effect(chain: EffectChain):
    """Apply effect chain to a single frame and return preview."""
    if _state["video_path"] is None:
        raise HTTPException(status_code=400, detail="No video loaded")

    try:
        frame = extract_single_frame(_state["video_path"], chain.frame_number)
        if chain.effects:
            frame = apply_chain(frame, chain.effects)
        return {"preview": _frame_to_data_url(frame)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/frame/{frame_number}")
async def get_frame(frame_number: int):
    """Get a raw frame without effects."""
    if _state["video_path"] is None:
        raise HTTPException(status_code=400, detail="No video loaded")
    frame = extract_single_frame(_state["video_path"], frame_number)
    return {"preview": _frame_to_data_url(frame)}


def _frame_to_data_url(frame: np.ndarray) -> str:
    """Convert numpy frame to base64 data URL for <img> tag."""
    img = Image.fromarray(frame)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/jpeg;base64,{b64}"


def start():
    import uvicorn
    print("Entropic — launching at http://127.0.0.1:7860")
    uvicorn.run(app, host="127.0.0.1", port=7860, log_level="warning")


if __name__ == "__main__":
    start()

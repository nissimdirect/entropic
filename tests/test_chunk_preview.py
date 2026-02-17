#!/usr/bin/env python3
"""
Entropic -- Chunk Preview Tests

Tests for the chunk preview endpoints in server.py:
- POST /api/preview/chunk (start chunk render)
- GET  /api/preview/chunk/progress (poll progress)
- POST /api/preview/chunk/cancel (cancel render)
- GET  /api/preview/chunk/file/{filename} (serve rendered file)
- GET  /api/preview/chunk/source (serve source video)
- ChunkRequest model defaults

Run with: pytest tests/test_chunk_preview.py -v
"""

import os
import sys
import time
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from starlette.testclient import TestClient
from server import (
    app, _state, _chunk_progress, _set_chunk_progress, _get_chunk_progress,
    ChunkRequest, _cleanup_old_chunks, _CHUNK_DIR, _CHUNK_TTL_SECONDS,
    _render_chunk_sync,
)
from conftest import MOCK_VIDEO_INFO, _make_test_frame


@pytest.fixture(autouse=True)
def setup_state():
    """Reset server state and chunk progress before each test."""
    _state["video_path"] = None
    _state["video_info"] = None
    _state["current_frame"] = None
    # Reset chunk progress to idle defaults
    _set_chunk_progress(
        active=False, frame=0, total=0,
        ready=False, cancel=False, url="", error=""
    )
    with patch("server.extract_single_frame", return_value=_make_test_frame()), \
         patch("server.probe_video", return_value=MOCK_VIDEO_INFO.copy()):
        yield
    _state["video_path"] = None
    _state["video_info"] = None
    _state["current_frame"] = None
    _set_chunk_progress(
        active=False, frame=0, total=0,
        ready=False, cancel=False, url="", error=""
    )


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def loaded_state():
    """Set up state as if a video is loaded."""
    _state["video_path"] = "/mock/test.mp4"
    _state["video_info"] = MOCK_VIDEO_INFO.copy()


# ===========================================================================
# 1. POST /api/preview/chunk — no video loaded
# ===========================================================================

def test_chunk_endpoint_no_video(client):
    """POST /api/preview/chunk with no video loaded returns 400."""
    resp = client.post("/api/preview/chunk", json={
        "start_frame": 0,
        "duration_frames": 30,
        "regions": [],
        "effects": [],
    })
    assert resp.status_code == 400
    data = resp.json()
    assert "detail" in data
    detail = data["detail"]
    # Structured error detail has a "code" key
    if isinstance(detail, dict):
        assert detail.get("code") == "NO_VIDEO"


# ===========================================================================
# 2. GET /api/preview/chunk/progress — idle state
# ===========================================================================

def test_chunk_progress_idle(client):
    """GET /api/preview/chunk/progress when nothing rendering returns inactive."""
    resp = client.get("/api/preview/chunk/progress")
    assert resp.status_code == 200
    data = resp.json()
    assert data["active"] is False
    assert data["ready"] is False


# ===========================================================================
# 3. POST /api/preview/chunk/cancel — nothing rendering
# ===========================================================================

def test_chunk_cancel_no_render(client):
    """POST /api/preview/chunk/cancel when nothing rendering returns appropriate status."""
    resp = client.post("/api/preview/chunk/cancel")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "no_chunk_rendering"


# ===========================================================================
# 4. POST /api/preview/chunk — empty effects returns source URL
# ===========================================================================

def test_chunk_no_effects_returns_source(client, loaded_state):
    """POST /api/preview/chunk with empty effects/regions returns source URL."""
    resp = client.post("/api/preview/chunk", json={
        "start_frame": 0,
        "duration_frames": 30,
        "regions": [],
        "effects": [],
        "tracks": [],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["url"] == "/api/preview/chunk/source"


# ===========================================================================
# 5. GET /api/preview/chunk/file — path traversal (security)
# ===========================================================================

def test_chunk_file_path_traversal(client):
    """GET /api/preview/chunk/file/../../etc/passwd returns 404 (security test)."""
    resp = client.get("/api/preview/chunk/file/../../etc/passwd")
    # FastAPI may normalize the path; if it reaches the handler, should be 404
    assert resp.status_code in (404, 400)


# ===========================================================================
# 6. GET /api/preview/chunk/file — nonexistent file
# ===========================================================================

def test_chunk_file_not_found(client):
    """GET /api/preview/chunk/file/nonexistent.mp4 returns 404."""
    resp = client.get("/api/preview/chunk/file/nonexistent.mp4")
    assert resp.status_code == 404
    data = resp.json()
    assert "detail" in data
    assert "not found" in str(data["detail"]).lower()


# ===========================================================================
# 7. GET /api/preview/chunk/source — no video loaded
# ===========================================================================

def test_chunk_source_no_video(client):
    """GET /api/preview/chunk/source with no video loaded returns 400."""
    resp = client.get("/api/preview/chunk/source")
    assert resp.status_code == 400
    data = resp.json()
    assert "detail" in data


# ===========================================================================
# 8. ChunkRequest model defaults
# ===========================================================================

def test_chunk_request_model_defaults():
    """Verify ChunkRequest model defaults match expected values."""
    req = ChunkRequest()
    assert req.start_frame == 0
    assert req.duration_frames == 90
    assert req.regions == []
    assert req.tracks == []
    assert req.mix == 1.0
    assert req.mode == "timeline"
    assert req.effects == []
    assert req.quality == "playback"
    assert req.frame_cutout is None


# ===========================================================================
# 9. _cleanup_old_chunks deletes old files
# ===========================================================================

def test_cleanup_old_chunks(tmp_path):
    """_cleanup_old_chunks deletes chunk files older than TTL."""
    # Create a fake old chunk file inside the real _CHUNK_DIR
    _CHUNK_DIR.mkdir(exist_ok=True)
    old_chunk = _CHUNK_DIR / "chunk_test_old_999.mp4"
    old_chunk.write_bytes(b"\x00" * 100)
    # Backdate mtime to be older than TTL
    old_mtime = time.time() - _CHUNK_TTL_SECONDS - 10
    os.utime(str(old_chunk), (old_mtime, old_mtime))

    # Create a recent chunk that should NOT be deleted
    recent_chunk = _CHUNK_DIR / "chunk_test_recent_999.mp4"
    recent_chunk.write_bytes(b"\x00" * 100)

    _cleanup_old_chunks()

    assert not old_chunk.exists(), "Old chunk file should be deleted"
    assert recent_chunk.exists(), "Recent chunk file should be kept"

    # Clean up test file
    recent_chunk.unlink(missing_ok=True)


# ===========================================================================
# 10. _render_chunk_sync respects cancel flag
# ===========================================================================

def test_render_chunk_sync_cancel():
    """Setting cancel flag stops chunk rendering early."""
    _CHUNK_DIR.mkdir(exist_ok=True)
    chunk_path = _CHUNK_DIR / "chunk_cancel_test.mp4"

    req = ChunkRequest(
        start_frame=0,
        duration_frames=10,
        mode="flat",
        effects=[{"name": "invert", "params": {}}],
    )
    video_info = MOCK_VIDEO_INFO.copy()

    # Create a frame generator that yields frames and sets cancel after 2
    frames_yielded = []

    def fake_stream_frames(path, scale=1.0, start_frame=0):
        for i in range(10):
            frame = np.zeros((240, 320, 3), dtype=np.uint8)
            frames_yielded.append(i)
            # Set cancel after yielding frame 2
            if i == 2:
                _set_chunk_progress(cancel=True)
            yield frame

    # Mock stream_frames and open_output_pipe
    mock_pipe = MagicMock()
    mock_pipe.stdin = MagicMock()
    mock_pipe.wait = MagicMock()

    with patch("server.stream_frames", side_effect=fake_stream_frames), \
         patch("server.open_output_pipe", return_value=mock_pipe):
        _render_chunk_sync("/mock/test.mp4", chunk_path, req, video_info)

    # Should have stopped early — not all 10 frames
    assert len(frames_yielded) < 10, (
        f"Cancel should stop rendering early, but {len(frames_yielded)} frames were yielded"
    )

    progress = _get_chunk_progress()
    assert progress["active"] is False
    assert "cancel" in progress.get("error", "").lower() or progress.get("cancel") is True

    # Clean up
    chunk_path.unlink(missing_ok=True)

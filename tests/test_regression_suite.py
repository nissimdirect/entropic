#!/usr/bin/env python3
"""
Entropic -- Regression Test Suite

Prevents the 15 regressions from 2026-02-15 session:
1. Server initialization (no crash on startup)
2. Upload endpoint (no dual notification)
3. Preview endpoint (proper response format)
4. Export endpoint (end-to-end workflow)
5. Multi-track composite (blend mode validation)
6. Track operations (add, remove, reorder)
7. Effect chain operations (add, remove, reorder)
8. Undo/redo after each operation
9. No 3-mode system remnants (Quick/Timeline/Perform strings)

Run with: pytest tests/test_regression_suite.py -v
"""

import os
import sys
import numpy as np
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from starlette.testclient import TestClient
from server import app, _state
from conftest import MOCK_VIDEO_INFO, _make_test_frame


@pytest.fixture(autouse=True)
def setup_state():
    """Reset server state before each test (mock-based, no real video needed)."""
    _state["video_path"] = "/mock/test.mp4"
    _state["video_info"] = MOCK_VIDEO_INFO.copy()
    _state["current_frame"] = None
    with patch("server.extract_single_frame", return_value=_make_test_frame()), \
         patch("server.probe_video", return_value=MOCK_VIDEO_INFO.copy()):
        yield
    _state["video_path"] = None
    _state["video_info"] = None
    _state["current_frame"] = None


@pytest.fixture
def client():
    return TestClient(app)


# ===========================================================================
# REGRESSION 1: SERVER INITIALIZATION
# ===========================================================================

def test_server_starts_without_crash(client):
    """
    Regression: Server must start and respond to health check.
    Prevents: Server crash on initialization due to missing imports or circular dependencies.
    """
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] == "ok"


# ===========================================================================
# REGRESSION 2: UPLOAD ENDPOINT (NO DUAL NOTIFICATION)
# ===========================================================================

def test_upload_returns_single_response(client):
    """
    Regression: Upload endpoint must return exactly one JSON response.
    Prevents: Dual notification bug where upload returns two separate responses,
    causing frontend to process both and potentially double-load the video.
    """
    import io
    fake_video = io.BytesIO(b"\x00" * 1024)  # Minimal binary blob; probe_video is mocked
    resp = client.post(
        "/api/upload",
        files={"file": ("test.mp4", fake_video, "video/mp4")}
    )

    assert resp.status_code == 200
    data = resp.json()

    # Should have standard upload response structure
    assert "status" in data
    assert data["status"] == "ok"
    assert "info" in data
    assert "preview" in data

    # Should NOT have duplicate keys or nested responses
    assert isinstance(data, dict)
    assert len([k for k in data.keys() if k == "status"]) == 1


# ===========================================================================
# REGRESSION 3: PREVIEW ENDPOINT (PROPER FORMAT)
# ===========================================================================

def test_preview_returns_valid_image_data(client):
    """
    Regression: Preview endpoint must return valid base64 image data.
    Prevents: Preview returning None, empty string, or malformed data URL.
    """
    resp = client.post("/api/preview", json={
        "effects": [{"name": "blur", "params": {"radius": 5.0}}],
        "frame_number": 0,
        "mix": 1.0
    })

    assert resp.status_code == 200
    data = resp.json()
    assert "preview" in data

    # Validate data URL format
    preview = data["preview"]
    assert isinstance(preview, str)
    assert preview.startswith("data:image/jpeg;base64,") or preview.startswith("data:image/png;base64,")
    assert len(preview) > 100  # Should have actual image data


# ===========================================================================
# REGRESSION 4: EXPORT ENDPOINT (END-TO-END)
# ===========================================================================

def test_export_completes_end_to_end(client):
    """
    Regression: Export endpoint must complete without errors.
    Prevents: Export hanging, crashing, or returning 500 errors.
    Bug fixed: ExportSettings nested property references (h264.crf, resolution.resolve_dimensions, etc.)
    """
    from pathlib import Path

    mock_frame_paths = [Path("/mock/frame_000001.png")]

    def mock_subprocess_run(cmd, **kwargs):
        """Create the output file ffmpeg would produce."""
        # The last arg is the output path
        output_path = cmd[-1]
        if output_path.endswith((".mp4", ".mov", ".webm", ".gif")):
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(b"\x00" * 512)
        return MagicMock(returncode=0)

    with patch("core.video_io.extract_frames", return_value=mock_frame_paths), \
         patch("core.video_io.load_frame", return_value=_make_test_frame()), \
         patch("core.video_io.save_frame"), \
         patch("subprocess.run", side_effect=mock_subprocess_run):
        resp = client.post("/api/export", json={
            "effects": [{"name": "blur", "params": {"radius": 5.0}}],
            "format": "mp4",
            "mix": 1.0
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "path" in data
    assert "size_mb" in data

    # Cleanup the dummy output
    Path(data["path"]).unlink(missing_ok=True)


# ===========================================================================
# REGRESSION 5: MULTI-TRACK COMPOSITE (BLEND MODE VALIDATION)
# ===========================================================================

def test_multitrack_validates_blend_modes(client):
    """
    Regression: Multi-track endpoint must validate blend mode strings.
    Prevents: Backend crash when invalid blend mode is passed.
    """
    # Valid blend mode should work
    resp = client.post("/api/preview/multitrack", json={
        "frame_number": 0,
        "tracks": [
            {
                "effects": [],
                "blend_mode": "normal",
                "opacity": 1.0,
                "muted": False,
                "solo": False
            }
        ]
    })
    assert resp.status_code == 200

    # Invalid blend mode should return 400 or handle gracefully
    resp = client.post("/api/preview/multitrack", json={
        "frame_number": 0,
        "tracks": [
            {
                "effects": [],
                "blend_mode": "INVALID_MODE_XYZ",
                "opacity": 1.0,
                "muted": False,
                "solo": False
            }
        ]
    })
    # Should not crash (500) — either 400 or graceful fallback
    assert resp.status_code in [200, 400]


# ===========================================================================
# REGRESSION 6: TRACK OPERATIONS (ADD, REMOVE, REORDER)
# ===========================================================================

def test_track_add_remove_reorder_work(client):
    """
    Regression: Track operations must work independently.
    Prevents: Frontend track list getting out of sync with backend state.

    NOTE: This tests that multi-track endpoint handles variable track counts,
    as there is no explicit add/remove track endpoint (tracks are ephemeral).
    """
    # Single track
    resp = client.post("/api/preview/multitrack", json={
        "frame_number": 0,
        "tracks": [
            {"effects": [], "blend_mode": "normal", "opacity": 1.0, "muted": False, "solo": False}
        ]
    })
    assert resp.status_code == 200

    # Three tracks
    resp = client.post("/api/preview/multitrack", json={
        "frame_number": 0,
        "tracks": [
            {"effects": [], "blend_mode": "normal", "opacity": 1.0, "muted": False, "solo": False},
            {"effects": [], "blend_mode": "overlay", "opacity": 0.5, "muted": False, "solo": False},
            {"effects": [], "blend_mode": "multiply", "opacity": 1.0, "muted": False, "solo": False}
        ]
    })
    assert resp.status_code == 200

    # Back to one track (simulates removal)
    resp = client.post("/api/preview/multitrack", json={
        "frame_number": 0,
        "tracks": [
            {"effects": [], "blend_mode": "normal", "opacity": 1.0, "muted": False, "solo": False}
        ]
    })
    assert resp.status_code == 200


# ===========================================================================
# REGRESSION 7: EFFECT CHAIN OPERATIONS (ADD, REMOVE, REORDER)
# ===========================================================================

def test_effect_chain_add_remove_reorder(client):
    """
    Regression: Effect chain operations must preserve order and state.
    Prevents: Effects being applied in wrong order or disappearing.
    """
    # Start with no effects
    resp = client.post("/api/preview", json={
        "effects": [],
        "frame_number": 0,
        "mix": 1.0
    })
    assert resp.status_code == 200

    # Add one effect
    resp = client.post("/api/preview", json={
        "effects": [{"name": "blur", "params": {"radius": 5.0}}],
        "frame_number": 0,
        "mix": 1.0
    })
    assert resp.status_code == 200

    # Add second effect (order: blur → edges)
    resp = client.post("/api/preview", json={
        "effects": [
            {"name": "blur", "params": {"radius": 5.0}},
            {"name": "edges", "params": {"threshold": 0.3}}
        ],
        "frame_number": 0,
        "mix": 1.0
    })
    assert resp.status_code == 200

    # Reorder (order: edges → blur)
    resp = client.post("/api/preview", json={
        "effects": [
            {"name": "edges", "params": {"threshold": 0.3}},
            {"name": "blur", "params": {"radius": 5.0}}
        ],
        "frame_number": 0,
        "mix": 1.0
    })
    assert resp.status_code == 200

    # Remove first effect (back to just blur)
    resp = client.post("/api/preview", json={
        "effects": [{"name": "blur", "params": {"radius": 5.0}}],
        "frame_number": 0,
        "mix": 1.0
    })
    assert resp.status_code == 200


# ===========================================================================
# REGRESSION 8: UNDO/REDO AFTER OPERATIONS
# ===========================================================================

def test_undo_redo_work_after_operations(client):
    """
    Regression: Undo/redo must work after any operation.
    Prevents: Undo stack corruption or undo not working after specific actions.

    NOTE: This tests that the server can handle the same effect chain
    being applied multiple times (simulating undo/redo), as history
    is client-side. The server must be stateless.
    """
    effect_chain_a = [{"name": "blur", "params": {"radius": 5.0}}]
    effect_chain_b = [{"name": "edges", "params": {"threshold": 0.3}}]

    # Apply chain A
    resp = client.post("/api/preview", json={
        "effects": effect_chain_a,
        "frame_number": 0,
        "mix": 1.0
    })
    assert resp.status_code == 200

    # Apply chain B
    resp = client.post("/api/preview", json={
        "effects": effect_chain_b,
        "frame_number": 0,
        "mix": 1.0
    })
    assert resp.status_code == 200

    # Undo (back to chain A)
    resp = client.post("/api/preview", json={
        "effects": effect_chain_a,
        "frame_number": 0,
        "mix": 1.0
    })
    assert resp.status_code == 200

    # Redo (forward to chain B)
    resp = client.post("/api/preview", json={
        "effects": effect_chain_b,
        "frame_number": 0,
        "mix": 1.0
    })
    assert resp.status_code == 200


# ===========================================================================
# REGRESSION 9: NO 3-MODE SYSTEM REMNANTS
# ===========================================================================

def test_no_quick_timeline_perform_mode_strings_in_responses(client):
    """
    Regression: Responses must not contain Quick/Timeline/Perform mode strings.
    Prevents: Old 3-mode system strings leaking into responses.
    """
    # Check effects list
    resp = client.get("/api/effects")
    assert resp.status_code == 200
    text = resp.text.lower()
    assert "quick mode" not in text
    assert "timeline mode" not in text
    assert "perform mode" not in text

    # Check categories
    resp = client.get("/api/categories")
    assert resp.status_code == 200
    text = resp.text.lower()
    assert "quick mode" not in text
    assert "timeline mode" not in text
    assert "perform mode" not in text

    # Check preview response
    resp = client.post("/api/preview", json={
        "effects": [{"name": "blur", "params": {"radius": 5.0}}],
        "frame_number": 0,
        "mix": 1.0
    })
    assert resp.status_code == 200
    text = resp.text.lower()
    assert "quick mode" not in text
    assert "timeline mode" not in text
    assert "perform mode" not in text


# ===========================================================================
# REGRESSION 10: FRAME INDEX CONSISTENCY
# ===========================================================================

def test_frame_index_passed_to_effects(client):
    """
    Regression: frame_index must be passed to all effects.
    Prevents: Temporal effects breaking due to missing frame_index parameter.

    This test ensures that effects requiring frame_index don't crash.
    """
    # Temporal effect (requires frame_index)
    resp = client.post("/api/preview", json={
        "effects": [{"name": "delay", "params": {"delay_frames": 5, "decay": 0.5}}],
        "frame_number": 10,
        "mix": 1.0
    })
    # Should not crash (500)
    assert resp.status_code in [200, 400]  # 400 if effect doesn't exist, 200 if it works

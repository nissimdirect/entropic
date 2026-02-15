"""
Entropic — Integration Tests for /api/preview endpoint
Tests the full web UI code path through the preview endpoint with stateful effects.

Run with: pytest tests/test_preview_integration.py -v
"""

import os
import sys
import base64

import pytest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from starlette.testclient import TestClient
from server import app, _state
from core.video_io import probe_video

TEST_VIDEO = os.path.join(os.path.dirname(__file__), "test_input.mp4")


@pytest.fixture(autouse=True)
def setup_state():
    """Load the test video into server state before each test."""
    info = probe_video(TEST_VIDEO)
    _state["video_path"] = TEST_VIDEO
    _state["video_info"] = info
    _state["current_frame"] = None
    yield
    _state["video_path"] = None
    _state["video_info"] = None
    _state["current_frame"] = None


@pytest.fixture
def client():
    return TestClient(app)


def _decode_preview(data_url: str) -> np.ndarray:
    """Decode a data:image/... URL back to a numpy array."""
    from PIL import Image
    from io import BytesIO

    header, encoded = data_url.split(",", 1)
    img_bytes = base64.b64decode(encoded)
    img = Image.open(BytesIO(img_bytes))
    return np.array(img)


# ---------------------------------------------------------------------------
# Basic preview endpoint tests
# ---------------------------------------------------------------------------

class TestPreviewEndpoint:

    def test_preview_no_effects(self, client):
        """Preview with empty chain returns the original frame."""
        resp = client.post("/api/preview", json={
            "effects": [],
            "frame_number": 0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "preview" in data
        assert data["preview"].startswith("data:image/")

    def test_preview_no_video_loaded(self, client):
        """Preview without a loaded video returns 400."""
        _state["video_path"] = None
        resp = client.post("/api/preview", json={
            "effects": [],
            "frame_number": 0,
        })
        assert resp.status_code == 400

    def test_preview_returns_valid_image(self, client):
        """Preview response decodes to a valid numpy array."""
        resp = client.post("/api/preview", json={
            "effects": [{"name": "hueshift", "params": {"degrees": 90}}],
            "frame_number": 0,
        })
        assert resp.status_code == 200
        frame = _decode_preview(resp.json()["preview"])
        assert frame.ndim == 3
        assert frame.shape[2] == 3
        assert frame.dtype == np.uint8


# ---------------------------------------------------------------------------
# Stateful effect tests (single frame)
# ---------------------------------------------------------------------------

class TestStatefulEffectsSingleFrame:

    def test_pixelgravity_single_frame(self, client):
        """pixel_gravity (physics) produces a transformed frame, not the original."""
        resp = client.post("/api/preview", json={
            "effects": [{"name": "pixelgravity", "params": {
                "num_attractors": 5,
                "gravity_strength": 8.0,
                "damping": 0.95,
                "attractor_radius": 0.3,
                "wander": 0.5,
                "seed": 42,
                "boundary": "black",
            }}],
            "frame_number": 0,
        })
        assert resp.status_code == 200
        frame = _decode_preview(resp.json()["preview"])
        assert frame.shape[2] == 3

        # Get original for comparison
        orig_resp = client.post("/api/preview", json={
            "effects": [],
            "frame_number": 0,
        })
        orig_frame = _decode_preview(orig_resp.json()["preview"])

        # The effect should have changed pixels
        assert not np.array_equal(frame, orig_frame), \
            "pixelgravity should transform the frame"

    def test_feedback_single_frame(self, client):
        """feedback (temporal) produces a valid response on first frame."""
        resp = client.post("/api/preview", json={
            "effects": [{"name": "feedback", "params": {"decay": 0.3}}],
            "frame_number": 0,
        })
        assert resp.status_code == 200
        frame = _decode_preview(resp.json()["preview"])
        assert frame.ndim == 3
        assert frame.dtype == np.uint8


# ---------------------------------------------------------------------------
# Stateful effect tests (multi-frame)
# ---------------------------------------------------------------------------

class TestStatefulEffectsMultiFrame:

    def test_pixelgravity_different_frames(self, client):
        """pixel_gravity produces valid output on different frame indices."""
        frames = []
        for frame_num in [0, 5, 10]:
            resp = client.post("/api/preview", json={
                "effects": [{"name": "pixelgravity", "params": {
                    "num_attractors": 3,
                    "gravity_strength": 8.0,
                    "damping": 0.95,
                    "attractor_radius": 0.3,
                    "wander": 0.5,
                    "seed": 42,
                    "boundary": "wrap",
                }}],
                "frame_number": frame_num,
            })
            assert resp.status_code == 200
            frame = _decode_preview(resp.json()["preview"])
            frames.append(frame)

        # All frames should be valid images
        for f in frames:
            assert f.ndim == 3
            assert f.dtype == np.uint8

    def test_feedback_different_frames(self, client):
        """feedback produces valid output across multiple frame requests."""
        for frame_num in [0, 3, 7]:
            resp = client.post("/api/preview", json={
                "effects": [{"name": "feedback", "params": {"decay": 0.5}}],
                "frame_number": frame_num,
            })
            assert resp.status_code == 200
            data = resp.json()
            assert "preview" in data
            frame = _decode_preview(data["preview"])
            assert frame.ndim == 3

    def test_chained_stateful_effects(self, client):
        """A chain with multiple stateful effects doesn't crash."""
        resp = client.post("/api/preview", json={
            "effects": [
                {"name": "feedback", "params": {"decay": 0.3}},
                {"name": "pixelgravity", "params": {
                    "num_attractors": 3,
                    "gravity_strength": 5.0,
                    "damping": 0.95,
                    "attractor_radius": 0.3,
                    "wander": 0.5,
                    "seed": 99,
                    "boundary": "clamp",
                }},
            ],
            "frame_number": 0,
        })
        assert resp.status_code == 200
        frame = _decode_preview(resp.json()["preview"])
        assert frame.ndim == 3


# ---------------------------------------------------------------------------
# Mix (wet/dry) with stateful effects
# ---------------------------------------------------------------------------

class TestMixWithStatefulEffects:

    def test_half_mix_differs_from_full(self, client):
        """50% mix should blend original and effected frame."""
        full_resp = client.post("/api/preview", json={
            "effects": [{"name": "pixelgravity", "params": {
                "num_attractors": 5,
                "gravity_strength": 8.0,
                "damping": 0.95,
                "attractor_radius": 0.3,
                "wander": 0.5,
                "seed": 42,
                "boundary": "black",
            }}],
            "frame_number": 0,
            "mix": 1.0,
        })
        half_resp = client.post("/api/preview", json={
            "effects": [{"name": "pixelgravity", "params": {
                "num_attractors": 5,
                "gravity_strength": 8.0,
                "damping": 0.95,
                "attractor_radius": 0.3,
                "wander": 0.5,
                "seed": 42,
                "boundary": "black",
            }}],
            "frame_number": 0,
            "mix": 0.5,
        })
        assert full_resp.status_code == 200
        assert half_resp.status_code == 200

        full_frame = _decode_preview(full_resp.json()["preview"])
        half_frame = _decode_preview(half_resp.json()["preview"])

        # They should differ (mix blends with original)
        assert not np.array_equal(full_frame, half_frame), \
            "50% mix should differ from 100% wet"

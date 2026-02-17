#!/usr/bin/env python3
"""
Entropic -- Frame Cutout Compositing Tests

Tests for the _apply_frame_cutout function in server.py which composites
a clean center region over a processed frame (or inverse).

Uses simple numpy test frames (all-black original, all-white processed)
to verify compositing math, shapes, feathering, opacity, and invert.

Run with: pytest tests/test_frame_cutout.py -v
"""

import os
import sys
import numpy as np
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from starlette.testclient import TestClient
from server import app, _state, _apply_frame_cutout
from conftest import MOCK_VIDEO_INFO, _make_test_frame


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def black_frame():
    """64x64 all-black frame (represents 'original' / clean)."""
    return np.zeros((64, 64, 3), dtype=np.uint8)


@pytest.fixture
def white_frame():
    """64x64 all-white frame (represents 'processed' / effected)."""
    return np.full((64, 64, 3), 255, dtype=np.uint8)


# ===========================================================================
# 1. Rectangle cutout — basic
# ===========================================================================

def test_cutout_rectangle_basic(black_frame, white_frame):
    """Rectangle cutout: center pixels should match original (black),
    border should match processed (white)."""
    params = {
        'center_x': 0.5, 'center_y': 0.5,
        'width': 0.5, 'height': 0.5,
        'feather': 0.0, 'opacity': 1.0,
        'invert': False, 'shape': 'rectangle',
    }
    result = _apply_frame_cutout(black_frame, white_frame, params)
    assert result.shape == black_frame.shape
    assert result.dtype == np.uint8

    # Dead center pixel should be original (black)
    cy, cx = 32, 32
    assert result[cy, cx, 0] == 0, "Center should be original (black)"

    # Corner (0,0) should be processed (white) — outside cutout region
    assert result[0, 0, 0] == 255, "Corner should be processed (white)"


# ===========================================================================
# 2. Ellipse cutout
# ===========================================================================

def test_cutout_ellipse(black_frame, white_frame):
    """Ellipse cutout: center should be more original-like (black)."""
    params = {
        'center_x': 0.5, 'center_y': 0.5,
        'width': 0.6, 'height': 0.6,
        'feather': 0.0, 'opacity': 1.0,
        'invert': False, 'shape': 'ellipse',
    }
    result = _apply_frame_cutout(black_frame, white_frame, params)

    # Center pixel should be original (black)
    cy, cx = 32, 32
    assert result[cy, cx, 0] < 30, "Center of ellipse should be near-original (black)"

    # Far corner should be processed (white)
    assert result[0, 0, 0] == 255, "Corner should be processed (white)"


# ===========================================================================
# 3. Feather produces smooth transition
# ===========================================================================

def test_cutout_feather_smooth(black_frame, white_frame):
    """With feather > 0, edge transition should be gradual (not hard)."""
    params = {
        'center_x': 0.5, 'center_y': 0.5,
        'width': 0.5, 'height': 0.5,
        'feather': 0.5, 'opacity': 1.0,
        'invert': False, 'shape': 'rectangle',
    }
    result = _apply_frame_cutout(black_frame, white_frame, params)

    # Sample a horizontal line through the middle (y=32)
    row = result[32, :, 0].astype(float)

    # With feather, there should be intermediate values (not just 0 and 255)
    unique_vals = np.unique(row)
    assert len(unique_vals) > 2, (
        f"Feathered cutout should produce gradual transition, got only {len(unique_vals)} unique values"
    )


# ===========================================================================
# 4. Opacity = 0.5 blends 50/50 in center area
# ===========================================================================

def test_cutout_opacity_half(black_frame, white_frame):
    """opacity=0.5 should blend 50/50 in center area."""
    params = {
        'center_x': 0.5, 'center_y': 0.5,
        'width': 0.5, 'height': 0.5,
        'feather': 0.0, 'opacity': 0.5,
        'invert': False, 'shape': 'rectangle',
    }
    result = _apply_frame_cutout(black_frame, white_frame, params)

    # Center pixel: mask=0.5, so result = black*0.5 + white*0.5 = 127.5
    cy, cx = 32, 32
    center_val = int(result[cy, cx, 0])
    assert 120 <= center_val <= 135, (
        f"Center should be ~128 (50/50 blend), got {center_val}"
    )

    # Corner: outside mask, so fully processed (white)
    assert result[0, 0, 0] == 255, "Corner should remain fully processed"


# ===========================================================================
# 5. Invert swaps clean/effected regions
# ===========================================================================

def test_cutout_invert(black_frame, white_frame):
    """invert=True should swap: center is effected (white), border is clean (black)."""
    params = {
        'center_x': 0.5, 'center_y': 0.5,
        'width': 0.5, 'height': 0.5,
        'feather': 0.0, 'opacity': 1.0,
        'invert': True, 'shape': 'rectangle',
    }
    result = _apply_frame_cutout(black_frame, white_frame, params)

    # Center should be processed (white) — inverted
    cy, cx = 32, 32
    assert result[cy, cx, 0] == 255, "Inverted center should be processed (white)"

    # Corner should be original (black) — inverted
    assert result[0, 0, 0] == 0, "Inverted corner should be original (black)"


# ===========================================================================
# 6. Full-width cutout (width=1.0, height=1.0) returns mostly original
# ===========================================================================

def test_cutout_full_width(black_frame, white_frame):
    """width=1.0, height=1.0 should return mostly original."""
    params = {
        'center_x': 0.5, 'center_y': 0.5,
        'width': 1.0, 'height': 1.0,
        'feather': 0.0, 'opacity': 1.0,
        'invert': False, 'shape': 'rectangle',
    }
    result = _apply_frame_cutout(black_frame, white_frame, params)

    # Almost all pixels should be original (black)
    black_pixels = np.sum(result == 0)
    total_pixels = result.size
    ratio = black_pixels / total_pixels
    assert ratio > 0.95, (
        f"Full-size cutout should be >95% original, got {ratio:.1%}"
    )


# ===========================================================================
# 7. Zero-size cutout returns processed frame
# ===========================================================================

def test_cutout_zero_size(black_frame, white_frame):
    """width=0.0, height=0.0 should return processed frame (no cutout area)."""
    params = {
        'center_x': 0.5, 'center_y': 0.5,
        'width': 0.0, 'height': 0.0,
        'feather': 0.0, 'opacity': 1.0,
        'invert': False, 'shape': 'rectangle',
    }
    result = _apply_frame_cutout(black_frame, white_frame, params)

    # All pixels should be processed (white) since mask is all zeros
    np.testing.assert_array_equal(result, white_frame)


# ===========================================================================
# 8. Off-center cutout shifts clean area right
# ===========================================================================

def test_cutout_off_center(black_frame, white_frame):
    """center_x=0.8 shifts clean area right."""
    params = {
        'center_x': 0.8, 'center_y': 0.5,
        'width': 0.3, 'height': 0.3,
        'feather': 0.0, 'opacity': 1.0,
        'invert': False, 'shape': 'rectangle',
    }
    result = _apply_frame_cutout(black_frame, white_frame, params)

    # Pixel at (32, 51) — 80% of 64 = 51.2 — should be inside cutout (black)
    assert result[32, 51, 0] == 0, "Off-center cutout at x=0.8 should be clean at pixel 51"

    # Pixel at (32, 10) — far left — should be processed (white)
    assert result[32, 10, 0] == 255, "Far left should remain processed (white)"


# ===========================================================================
# Integration test fixtures (mock video state for HTTP endpoint tests)
# ===========================================================================

@pytest.fixture
def loaded_state():
    """Set up mock video state and patch frame extraction."""
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


CUTOUT_PARAMS = {
    "center_x": 0.5, "center_y": 0.5,
    "width": 0.6, "height": 0.6,
    "feather": 0.1, "opacity": 1.0,
    "invert": False, "shape": "rectangle",
}


# ===========================================================================
# 9. Integration: POST /api/preview/timeline with frame_cutout
# ===========================================================================

def test_preview_timeline_with_cutout(client, loaded_state):
    """POST /api/preview/timeline with frame_cutout param returns valid preview."""
    resp = client.post("/api/preview/timeline", json={
        "frame_number": 0,
        "regions": [
            {
                "start": 0, "end": 10,
                "effects": [{"name": "invert", "params": {}}],
                "muted": False,
            }
        ],
        "mix": 1.0,
        "frame_cutout": CUTOUT_PARAMS,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "preview" in data
    assert data["preview"].startswith("data:image/")


# ===========================================================================
# 10. Integration: POST /api/preview with frame_cutout
# ===========================================================================

def test_preview_effect_with_cutout(client, loaded_state):
    """POST /api/preview with frame_cutout param returns valid preview."""
    resp = client.post("/api/preview", json={
        "effects": [{"name": "invert", "params": {}}],
        "frame_number": 0,
        "mix": 1.0,
        "frame_cutout": CUTOUT_PARAMS,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "preview" in data
    assert data["preview"].startswith("data:image/")

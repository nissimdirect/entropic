"""
Conftest: shared fixtures for all Entropic test modules.

1. Effect state reset (per-test) — prevents state leaks between tests
2. Mock video info + frame generator — eliminates ffmpeg dependency for HTTP tests
3. Real video generation — only for tests that need actual video processing
"""

import os
import subprocess
import numpy as np
import pytest
from unittest.mock import patch

TEST_VIDEO_PATH = os.path.join(os.path.dirname(__file__), "test_input.mp4")

# ---------------------------------------------------------------------------
# Mock video infrastructure — used by security, regression, and new_features
# tests that test HTTP behavior, not video processing.
# ---------------------------------------------------------------------------

MOCK_VIDEO_INFO = {
    "width": 320,
    "height": 240,
    "fps": 24.0,
    "duration": 1.0,
    "has_audio": False,
    "codec": "h264",
    "total_frames": 24,
}


def _make_test_frame(width=320, height=240):
    """Generate a synthetic test frame (gradient, not blank)."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:, :, 0] = np.linspace(0, 255, width, dtype=np.uint8)  # R gradient
    frame[:, :, 1] = 128  # constant G
    frame[:, :, 2] = np.linspace(255, 0, width, dtype=np.uint8)  # B inverse
    return frame


# ---------------------------------------------------------------------------
# Real video generation — for integration tests that need actual rendering
# ---------------------------------------------------------------------------

def _video_is_valid(path):
    """Check if test video exists AND is a valid media file."""
    if not os.path.exists(path) or os.path.getsize(path) < 1000:
        return False
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", path],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0 and '"codec_type"' in result.stdout
    except (subprocess.TimeoutExpired, OSError):
        return False


def _generate_test_video(path):
    """Generate a 1-second 320x240 H.264 MP4 with color gradients."""
    w, h, fps = 320, 240, 24
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
         "-s", f"{w}x{h}", "-pix_fmt", "rgb24", "-r", str(fps),
         "-i", "-", "-c:v", "libx264", "-preset", "ultrafast",
         "-pix_fmt", "yuv420p", path],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    for i in range(fps):
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:, :, 0] = int(255 * i / fps)
        frame[:, :, 1] = 128
        frame[:, :, 2] = 200
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    proc.communicate()
    return proc.returncode == 0


@pytest.fixture(scope="session", autouse=True)
def _ensure_test_video():
    """Best-effort: generate test video if possible. Not required for mock-based tests."""
    if _video_is_valid(TEST_VIDEO_PATH):
        return
    try:
        _generate_test_video(TEST_VIDEO_PATH)
    except Exception:
        pass  # Mock-based tests don't need this


# ---------------------------------------------------------------------------
# Effect state reset — prevents state leaks between tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_effect_state():
    """Clear all effect state dicts before each test."""
    from effects import physics, temporal, destruction, sidechain, dsp_filters

    physics._physics_state.clear()
    physics._physics_access_order.clear()
    temporal._temporal_state.clear()
    destruction._destruction_state.clear()
    sidechain._sidechain_state.clear()
    dsp_filters._phaser_state.clear()
    dsp_filters._feedback_phaser_state.clear()
    dsp_filters._spectral_freeze_state.clear()
    dsp_filters._reverb_state.clear()
    dsp_filters._freq_flanger_state.clear()

    yield

    physics._physics_state.clear()
    physics._physics_access_order.clear()
    temporal._temporal_state.clear()
    destruction._destruction_state.clear()
    sidechain._sidechain_state.clear()
    dsp_filters._phaser_state.clear()
    dsp_filters._feedback_phaser_state.clear()
    dsp_filters._spectral_freeze_state.clear()
    dsp_filters._reverb_state.clear()
    dsp_filters._freq_flanger_state.clear()

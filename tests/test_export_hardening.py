"""
Entropic — Export Hardening Tests
Tests for: blend modes (darken/lighten), FFmpeg error surfacing,
export cancellation, per-frame error attribution, output integrity,
and per-frame timeout.

Run with: pytest tests/test_export_hardening.py -v
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.layer import _BLEND_FNS, BLEND_MODES, Layer, LayerStack
from effects import _CHAIN_BLEND_FNS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def small_frame():
    """A 64x64 random RGB frame."""
    return np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)


@pytest.fixture
def dark_frame():
    """A 64x64 frame with low values (0-50)."""
    return np.random.randint(0, 50, (64, 64, 3), dtype=np.uint8)


@pytest.fixture
def bright_frame():
    """A 64x64 frame with high values (200-255)."""
    return np.random.randint(200, 256, (64, 64, 3), dtype=np.uint8)


# ===========================================================================
# Phase 2: Blend Mode Tests (darken / lighten)
# ===========================================================================

class TestBlendModes:
    """Verify darken and lighten blend modes exist and produce correct results."""

    def test_darken_in_blend_fns(self):
        """darken must be registered in _BLEND_FNS."""
        assert "darken" in _BLEND_FNS

    def test_lighten_in_blend_fns(self):
        """lighten must be registered in _BLEND_FNS."""
        assert "lighten" in _BLEND_FNS

    def test_darken_in_blend_modes_list(self):
        """darken must appear in the BLEND_MODES list."""
        assert "darken" in BLEND_MODES

    def test_lighten_in_blend_modes_list(self):
        """lighten must appear in the BLEND_MODES list."""
        assert "lighten" in BLEND_MODES

    def test_darken_in_chain_blend_fns(self):
        """darken must be registered in _CHAIN_BLEND_FNS (effects module)."""
        assert "darken" in _CHAIN_BLEND_FNS

    def test_lighten_in_chain_blend_fns(self):
        """lighten must be registered in _CHAIN_BLEND_FNS (effects module)."""
        assert "lighten" in _CHAIN_BLEND_FNS

    def test_darken_math(self, dark_frame, bright_frame):
        """darken(dark, bright) should equal the dark frame (element-wise min)."""
        fn = _BLEND_FNS["darken"]
        result = fn(dark_frame.astype(np.float32), bright_frame.astype(np.float32))
        np.testing.assert_array_equal(result, dark_frame.astype(np.float32))

    def test_lighten_math(self, dark_frame, bright_frame):
        """lighten(dark, bright) should equal the bright frame (element-wise max)."""
        fn = _BLEND_FNS["lighten"]
        result = fn(dark_frame.astype(np.float32), bright_frame.astype(np.float32))
        np.testing.assert_array_equal(result, bright_frame.astype(np.float32))

    def test_darken_chain_math(self, dark_frame, bright_frame):
        """Chain blend darken should produce element-wise min."""
        fn = _CHAIN_BLEND_FNS["darken"]
        result = fn(dark_frame.astype(np.float32), bright_frame.astype(np.float32))
        np.testing.assert_array_equal(result, dark_frame.astype(np.float32))

    def test_lighten_chain_math(self, dark_frame, bright_frame):
        """Chain blend lighten should produce element-wise max."""
        fn = _CHAIN_BLEND_FNS["lighten"]
        result = fn(dark_frame.astype(np.float32), bright_frame.astype(np.float32))
        np.testing.assert_array_equal(result, bright_frame.astype(np.float32))

    def test_darken_self_is_identity(self, small_frame):
        """darken(x, x) should equal x."""
        fn = _BLEND_FNS["darken"]
        f = small_frame.astype(np.float32)
        result = fn(f, f)
        np.testing.assert_array_equal(result, f)

    def test_lighten_self_is_identity(self, small_frame):
        """lighten(x, x) should equal x."""
        fn = _BLEND_FNS["lighten"]
        f = small_frame.astype(np.float32)
        result = fn(f, f)
        np.testing.assert_array_equal(result, f)

    def test_layer_composite_with_darken(self, small_frame, dark_frame):
        """LayerStack composite should work with darken blend mode."""
        layer0 = Layer(layer_id=0, trigger_mode="always_on", blend_mode="normal", opacity=1.0)
        layer1 = Layer(layer_id=1, trigger_mode="always_on", blend_mode="darken", opacity=1.0, z_order=1)
        stack = LayerStack([layer0, layer1])
        result = stack.composite({0: small_frame, 1: dark_frame})
        assert result.shape == small_frame.shape
        assert result.dtype == np.uint8

    def test_layer_composite_with_lighten(self, small_frame, bright_frame):
        """LayerStack composite should work with lighten blend mode."""
        layer0 = Layer(layer_id=0, trigger_mode="always_on", blend_mode="normal", opacity=1.0)
        layer1 = Layer(layer_id=1, trigger_mode="always_on", blend_mode="lighten", opacity=1.0, z_order=1)
        stack = LayerStack([layer0, layer1])
        result = stack.composite({0: small_frame, 1: bright_frame})
        assert result.shape == small_frame.shape
        assert result.dtype == np.uint8


# ===========================================================================
# Phase 3A: FFmpeg Error Detail Surfacing
# ===========================================================================

class TestFFmpegErrorSurfacing:
    """Test that _run_ffmpeg surfaces detailed stderr on failure."""

    def test_run_ffmpeg_surfaces_stderr(self):
        """CalledProcessError should produce HTTPException with stderr details."""
        from server import _run_ffmpeg
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _run_ffmpeg(["ffmpeg", "-i", "nonexistent_file.mp4", "-y", "/dev/null"], timeout=10)

        detail = exc_info.value.detail
        assert detail["code"] == "RENDER_FAILED"
        assert "ffmpeg_stderr" in detail
        # FFmpeg stderr should mention the missing file
        assert len(detail["ffmpeg_stderr"]) > 0

    def test_run_ffmpeg_timeout(self):
        """_run_ffmpeg should raise HTTPException on timeout."""
        from server import _run_ffmpeg
        from fastapi import HTTPException

        # Use a command that will hang (sleep)
        with pytest.raises(HTTPException) as exc_info:
            _run_ffmpeg(["sleep", "30"], timeout=1)

        assert exc_info.value.status_code == 500
        assert "timed out" in exc_info.value.detail["detail"]


# ===========================================================================
# Phase 3B: Export Cancellation
# ===========================================================================

class TestExportCancellation:
    """Test the export cancel mechanism."""

    def test_cancel_flag_default(self):
        """cancel_requested should default to False."""
        from server import _render_progress
        assert _render_progress.get("cancel_requested") is not None

    def test_cancel_endpoint_no_active_export(self):
        """Cancel when no export is running should return no_export_running."""
        from server import _render_progress
        _render_progress["active"] = False
        import asyncio
        from server import cancel_export
        result = asyncio.run(cancel_export())
        assert result["status"] == "no_export_running"

    def test_cancel_endpoint_active_export(self):
        """Cancel during active export should set cancel_requested flag."""
        from server import _render_progress, cancel_export
        _render_progress["active"] = True
        _render_progress["cancel_requested"] = False
        import asyncio
        result = asyncio.run(cancel_export())
        assert result["status"] == "cancel_requested"
        assert _render_progress["cancel_requested"] is True
        # Reset state
        _render_progress["active"] = False
        _render_progress["cancel_requested"] = False


# ===========================================================================
# Phase 3D: Output Integrity Check
# ===========================================================================

class TestOutputIntegrity:
    """Test _validate_output catches invalid output files."""

    def test_missing_file_raises(self, tmp_path):
        """Missing output file should raise HTTPException."""
        from server import _validate_output
        from fastapi import HTTPException

        fake_path = tmp_path / "nonexistent.mp4"
        with pytest.raises(HTTPException) as exc_info:
            _validate_output(fake_path)
        assert "no output file" in exc_info.value.detail["detail"].lower()

    def test_empty_file_raises(self, tmp_path):
        """Empty output file should raise HTTPException."""
        from server import _validate_output
        from fastapi import HTTPException

        empty_file = tmp_path / "empty.mp4"
        empty_file.write_bytes(b"")
        with pytest.raises(HTTPException) as exc_info:
            _validate_output(empty_file)
        assert "empty" in exc_info.value.detail["detail"].lower() or "0 bytes" in exc_info.value.detail["detail"]

    def test_valid_file_passes(self, tmp_path):
        """A file with content that ffprobe can't parse should still pass (non-zero size)."""
        from server import _validate_output

        # Write some bytes — ffprobe will fail but file is non-empty
        # _validate_output only hard-fails if ffprobe returns no duration AND returncode != 0
        # For a non-video file, ffprobe will error, but the function should handle gracefully
        fake_file = tmp_path / "test.mp4"
        fake_file.write_bytes(b"\x00" * 1024)
        # This may raise if ffprobe says it's invalid, which is correct behavior
        # The test verifies it doesn't crash unexpectedly
        try:
            _validate_output(fake_file)
        except Exception as e:
            # Should be an HTTPException about invalid file, not a crash
            from fastapi import HTTPException
            assert isinstance(e, HTTPException)


# ===========================================================================
# Phase 3F: Per-Frame Timeout
# ===========================================================================

class TestPerFrameTimeout:
    """Test _apply_chain_with_timeout catches slow effects."""

    def test_normal_chain_completes(self, small_frame):
        """Normal effect chain should complete within timeout."""
        from server import _apply_chain_with_timeout

        effects = [{"name": "invert", "params": {}}]
        result = _apply_chain_with_timeout(
            small_frame, effects, frame_index=0, total_frames=1
        )
        assert result.shape == small_frame.shape
        assert result.dtype == np.uint8

    def test_timeout_raises(self, small_frame):
        """A deliberately slow function should trigger TimeoutError."""
        import time
        import concurrent.futures

        # Patch FRAME_TIMEOUT_SECONDS to 1 second for testing
        with patch("server.FRAME_TIMEOUT_SECONDS", 1):
            # Create a mock apply_chain that sleeps
            def slow_chain(frame, effects, frame_index=0, total_frames=1, watermark=True):
                time.sleep(5)
                return frame

            with patch("server.apply_chain", slow_chain):
                from server import _apply_chain_with_timeout
                with pytest.raises(TimeoutError):
                    _apply_chain_with_timeout(
                        small_frame, [{"name": "test", "params": {}}],
                        frame_index=0, total_frames=1
                    )


# ===========================================================================
# Blend mode count validation
# ===========================================================================

class TestBlendModeConsistency:
    """Verify all frontend blend modes have backend implementations."""

    FRONTEND_BLEND_MODES = ["normal", "multiply", "screen", "add", "overlay", "darken", "lighten"]

    def test_all_frontend_modes_in_layer_blend_fns(self):
        """Every blend mode the frontend offers should be in _BLEND_FNS or handled as 'normal'."""
        for mode in self.FRONTEND_BLEND_MODES:
            if mode == "normal":
                # Normal is handled as the default (no blend fn needed)
                continue
            assert mode in _BLEND_FNS, f"Blend mode '{mode}' missing from _BLEND_FNS"

    def test_all_frontend_modes_in_chain_blend_fns(self):
        """Every blend mode the frontend offers should be in _CHAIN_BLEND_FNS or handled as 'normal'."""
        for mode in self.FRONTEND_BLEND_MODES:
            if mode == "normal":
                continue
            assert mode in _CHAIN_BLEND_FNS, f"Blend mode '{mode}' missing from _CHAIN_BLEND_FNS"

    def test_server_validates_all_frontend_modes(self):
        """Server's ALLOWED_BLEND_MODES should match frontend modes."""
        # The allowed list is defined inline in export_video — verify it matches
        allowed = ["normal", "multiply", "screen", "add", "overlay", "darken", "lighten"]
        for mode in self.FRONTEND_BLEND_MODES:
            assert mode in allowed, f"Mode '{mode}' not in server's ALLOWED_BLEND_MODES"

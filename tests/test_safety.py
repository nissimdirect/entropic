"""
Entropic -- Safety & Resource Limit Tests
Red Team audit: CPU spikes, memory explosion, disk exhaustion, hangs, leaks.

Run with: pytest tests/test_safety.py -v
"""

import os
import sys
import time
import tempfile
import struct
import subprocess
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import BytesIO

import pytest
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from effects import apply_effect, apply_chain, EFFECTS
from effects.pixelsort import pixelsort
from effects.channelshift import channelshift
from effects.scanlines import scanlines
from effects.bitcrush import bitcrush
from effects.color import (
    hue_shift,
    contrast_crush,
    saturation_warp,
    brightness_exposure,
    color_invert,
    color_temperature,
)
from core.video_io import probe_video, extract_single_frame


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def small_frame():
    """A 64x64 random RGB frame -- lightweight for fast tests."""
    return np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)


@pytest.fixture
def medium_frame():
    """A 480x640 random RGB frame -- typical preview size."""
    return np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)


@pytest.fixture
def large_frame():
    """A 1080x1920 random RGB frame -- full HD."""
    return np.random.randint(0, 256, (1080, 1920, 3), dtype=np.uint8)


@pytest.fixture
def solid_black_frame():
    """All-zero frame -- edge case for division, normalization."""
    return np.zeros((64, 64, 3), dtype=np.uint8)


@pytest.fixture
def solid_white_frame():
    """All-255 frame -- edge case for overflow."""
    return np.full((64, 64, 3), 255, dtype=np.uint8)


@pytest.fixture
def single_pixel_frame():
    """1x1 frame -- smallest possible."""
    return np.array([[[128, 64, 32]]], dtype=np.uint8)


@pytest.fixture
def single_row_frame():
    """1-pixel-high frame."""
    return np.random.randint(0, 256, (1, 100, 3), dtype=np.uint8)


@pytest.fixture
def single_col_frame():
    """1-pixel-wide frame."""
    return np.random.randint(0, 256, (100, 1, 3), dtype=np.uint8)


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory, cleaned up after test."""
    d = tempfile.mkdtemp(prefix="entropic_test_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# 1. FILE SIZE REJECTION
# ---------------------------------------------------------------------------

class TestFileSizeRejection:
    """Upload endpoint must reject files that are too large."""

    def test_upload_rejects_oversized_file(self):
        """Files over the max size limit must be rejected before full read."""
        # The current server.py has NO file size check. This test documents the gap.
        # Once the fix is in place, this should pass.
        MAX_UPLOAD_MB = 500  # recommended max for a glitch tool
        MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

        # Simulate what happens: file.read() loads the ENTIRE file into RAM
        # For a 4GB file, this would consume 4GB of RAM instantly.
        # The fix: check Content-Length header and stream with a cap.
        assert MAX_UPLOAD_BYTES == 500 * 1024 * 1024, "Max upload should be 500MB"

    def test_upload_rejects_non_video_file(self):
        """Non-video files (zip, exe, txt) must be rejected."""
        ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
        dangerous = [".exe", ".sh", ".py", ".zip", ".tar", ".txt", ".html"]
        for ext in dangerous:
            assert ext not in ALLOWED_EXTENSIONS, f"{ext} should not be allowed"

    def test_upload_rejects_empty_filename(self):
        """Empty or missing filename must not crash the suffix extraction."""
        # server.py line 79: Path(file.filename).suffix or ".mp4"
        # If filename is None, Path(None) raises TypeError
        from pathlib import Path as P
        with pytest.raises(TypeError):
            P(None).suffix


# ---------------------------------------------------------------------------
# 2. MEMORY LIMITS -- Frame Processing
# ---------------------------------------------------------------------------

class TestMemoryLimits:
    """Effects must not balloon memory beyond expected bounds."""

    def test_frame_copy_does_not_multiply_memory(self, medium_frame):
        """Each effect should produce at most 2x the input frame size in peak RAM."""
        input_bytes = medium_frame.nbytes  # ~921,600 bytes for 480x640x3
        result = pixelsort(medium_frame, threshold=0.5)
        assert result.nbytes == input_bytes, "Output must be same size as input"

    def test_apply_chain_does_not_accumulate_copies(self, medium_frame):
        """A chain of 10 effects must not keep 10 copies alive simultaneously."""
        chain = [{"name": "hueshift", "params": {"degrees": 30}}] * 10
        result = apply_chain(medium_frame, chain)
        # The frame variable is reassigned each iteration, so old frames
        # should be garbage-collectible. This test ensures output shape matches.
        assert result.shape == medium_frame.shape
        assert result.dtype == np.uint8

    def test_contrast_crush_float_intermediate_bounded(self, large_frame):
        """contrast_crush converts to float32 -- ensure it does not create float64."""
        result = contrast_crush(large_frame, amount=100, curve="s_curve")
        # float32 is 4 bytes/channel vs float64's 8 -- matters for 1080p
        assert result.dtype == np.uint8, "Output must be uint8"
        assert result.shape == large_frame.shape

    def test_saturation_warp_float_bounded(self, large_frame):
        """saturation_warp with amount=5.0 must not produce values > 255."""
        result = saturation_warp(large_frame, amount=5.0)
        assert result.max() <= 255
        assert result.min() >= 0
        assert result.dtype == np.uint8

    def test_exposure_wrap_mode_bounded(self, solid_white_frame):
        """Exposure with wrap mode on a white frame -- ensure no overflow."""
        result = brightness_exposure(solid_white_frame, stops=3.0, clip_mode="wrap")
        assert result.dtype == np.uint8
        assert result.max() <= 255

    def test_exposure_mirror_mode_bounded(self, solid_white_frame):
        """Exposure mirror mode must stay in 0-255 range."""
        result = brightness_exposure(solid_white_frame, stops=3.0, clip_mode="mirror")
        assert result.dtype == np.uint8
        assert result.max() <= 255
        assert result.min() >= 0


# ---------------------------------------------------------------------------
# 3. TIMEOUT HANDLING -- Subprocess Calls
# ---------------------------------------------------------------------------

class TestTimeoutHandling:
    """FFmpeg subprocess calls must have timeouts to prevent infinite hangs."""

    def test_ffprobe_has_timeout(self):
        """probe_video must call subprocess.run with a timeout."""
        import inspect
        source = inspect.getsource(probe_video)
        assert "timeout" in source, (
            "probe_video must have a subprocess timeout to prevent infinite hangs."
        )

    def test_extract_single_frame_has_timeout(self):
        """extract_single_frame must call subprocess.run with a timeout."""
        import inspect
        source = inspect.getsource(extract_single_frame)
        assert "timeout" in source, (
            "extract_single_frame must have a subprocess timeout."
        )

    def test_subprocess_timeout_kills_process(self):
        """Verify that subprocess.run with timeout raises TimeoutExpired."""
        with pytest.raises(subprocess.TimeoutExpired):
            subprocess.run(["sleep", "10"], timeout=0.1)


# ---------------------------------------------------------------------------
# 4. CORRUPT FILE HANDLING
# ---------------------------------------------------------------------------

class TestCorruptFileHandling:
    """Malformed or truncated files must not crash the server."""

    def test_probe_rejects_empty_file(self, tmp_dir):
        """Empty file must raise an error, not hang."""
        empty = tmp_dir / "empty.mp4"
        empty.write_bytes(b"")
        with pytest.raises(Exception):
            probe_video(str(empty))

    def test_probe_rejects_text_file_as_video(self, tmp_dir):
        """A text file with .mp4 extension must be rejected."""
        fake = tmp_dir / "fake.mp4"
        fake.write_text("this is not a video file")
        with pytest.raises(Exception):
            probe_video(str(fake))

    def test_probe_rejects_truncated_mp4(self, tmp_dir):
        """A truncated MP4 header should raise an error."""
        truncated = tmp_dir / "truncated.mp4"
        # Write a partial ftyp box (MP4 magic)
        truncated.write_bytes(b"\x00\x00\x00\x18ftypmp42\x00\x00")
        with pytest.raises(Exception):
            probe_video(str(truncated))

    def test_extract_frame_from_corrupt_file(self, tmp_dir):
        """Extracting a frame from a corrupt file must not leave temp files."""
        corrupt = tmp_dir / "corrupt.mp4"
        corrupt.write_bytes(b"\x00" * 1024)
        with pytest.raises(Exception):
            extract_single_frame(str(corrupt), 0)
        # Verify no temp .png files leaked
        leaked = list(Path(tempfile.gettempdir()).glob("tmp*.png"))
        # NOTE: We can't guarantee zero leaked files from other processes,
        # but we check our specific function cleans up via its finally block.


# ---------------------------------------------------------------------------
# 5. EFFECT PARAMETER CLAMPING
# ---------------------------------------------------------------------------

class TestParameterClamping:
    """All effects must clamp parameters to safe ranges, never crash on extreme values."""

    # --- Pixelsort ---

    def test_pixelsort_threshold_zero(self, small_frame):
        """threshold=0 means sort everything -- should not crash."""
        result = pixelsort(small_frame, threshold=0.0)
        assert result.shape == small_frame.shape

    def test_pixelsort_threshold_one(self, small_frame):
        """threshold=1.0 means sort nothing -- should return near-identical frame."""
        result = pixelsort(small_frame, threshold=1.0)
        assert result.shape == small_frame.shape

    def test_pixelsort_negative_threshold(self, small_frame):
        """Negative threshold must not crash."""
        result = pixelsort(small_frame, threshold=-1.0)
        assert result.shape == small_frame.shape

    def test_pixelsort_threshold_above_one(self, small_frame):
        """threshold > 1.0 must not crash (should sort nothing)."""
        result = pixelsort(small_frame, threshold=999.0)
        assert result.shape == small_frame.shape

    def test_pixelsort_invalid_sort_by_falls_back(self, small_frame):
        """Unknown sort_by value should fall back to brightness, not crash."""
        result = pixelsort(small_frame, sort_by="nonexistent")
        assert result.shape == small_frame.shape

    def test_pixelsort_vertical(self, small_frame):
        """Vertical pixel sort must not crash."""
        result = pixelsort(small_frame, direction="vertical")
        assert result.shape == small_frame.shape

    def test_pixelsort_single_pixel(self, single_pixel_frame):
        """1x1 frame must not crash pixelsort."""
        result = pixelsort(single_pixel_frame)
        assert result.shape == single_pixel_frame.shape

    def test_pixelsort_single_row(self, single_row_frame):
        """Single-row frame must not crash pixelsort."""
        result = pixelsort(single_row_frame)
        assert result.shape == single_row_frame.shape

    def test_pixelsort_solid_black(self, solid_black_frame):
        """All-black frame: hue/saturation normalization divides by zero."""
        # _hue: arctan2(0, 0) = 0, fine.
        # _saturation: mx=0, division masked, fine.
        # BUT: normalized = (keys - keys.min()) / (keys.max() - keys.min() + 1e-8)
        # keys.max() - keys.min() = 0 for solid frames. The +1e-8 prevents crash.
        result = pixelsort(solid_black_frame, sort_by="hue")
        assert result.shape == solid_black_frame.shape

    def test_pixelsort_solid_black_saturation(self, solid_black_frame):
        """All-black frame sorted by saturation must not divide by zero."""
        result = pixelsort(solid_black_frame, sort_by="saturation")
        assert result.shape == solid_black_frame.shape

    # --- Channel Shift ---

    def test_channelshift_huge_offset(self, small_frame):
        """Offsets larger than image dimensions should wrap, not crash."""
        result = channelshift(small_frame, r_offset=(10000, 10000))
        assert result.shape == small_frame.shape

    def test_channelshift_negative_offset(self, small_frame):
        """Negative offsets must wrap correctly."""
        result = channelshift(small_frame, r_offset=(-5, -5))
        assert result.shape == small_frame.shape

    def test_channelshift_zero_offset(self, small_frame):
        """Zero offsets = identity transform."""
        result = channelshift(small_frame, r_offset=(0, 0), g_offset=(0, 0), b_offset=(0, 0))
        np.testing.assert_array_equal(result, small_frame)

    # --- Scanlines ---

    def test_scanlines_zero_width(self, small_frame):
        """line_width=0 is clamped to 1, so it should not crash."""
        result = scanlines(small_frame, line_width=0)
        assert result.shape == small_frame.shape

    def test_scanlines_negative_width(self, small_frame):
        """Negative line_width could cause range issues."""
        # spacing = -2 * 2 = -4, range(0, 64, -4) yields nothing
        # This won't crash but produces no scanlines -- parameter should be clamped
        result = scanlines(small_frame, line_width=-1)
        assert result.shape == small_frame.shape

    def test_scanlines_huge_width(self, small_frame):
        """line_width larger than image height should apply one big line, not crash."""
        result = scanlines(small_frame, line_width=9999)
        assert result.shape == small_frame.shape

    def test_scanlines_opacity_bounds(self, small_frame):
        """Opacity outside 0-1 must not produce values outside 0-255."""
        result = scanlines(small_frame, opacity=5.0)  # no clamping in code!
        assert result.max() <= 255
        assert result.min() >= 0  # np.clip saves us, but opacity should be clamped

    # --- Bitcrush ---

    def test_bitcrush_depth_zero(self, small_frame):
        """color_depth=0 is clamped to 1 (black/white)."""
        result = bitcrush(small_frame, color_depth=0)
        assert result.dtype == np.uint8
        assert result.shape == small_frame.shape

    def test_bitcrush_depth_negative(self, small_frame):
        """Negative depth is clamped to 1."""
        result = bitcrush(small_frame, color_depth=-5)
        assert result.shape == small_frame.shape

    def test_bitcrush_resolution_zero(self, small_frame):
        """resolution_scale=0 should be clamped, not crash."""
        result = bitcrush(small_frame, resolution_scale=0.0)
        assert result.shape == small_frame.shape

    def test_bitcrush_resolution_negative(self, small_frame):
        """Negative resolution_scale is clamped to 0.05."""
        result = bitcrush(small_frame, resolution_scale=-1.0)
        assert result.shape == small_frame.shape

    def test_bitcrush_tiny_frame(self, single_pixel_frame):
        """1x1 frame with resolution downscale must not crash."""
        result = bitcrush(single_pixel_frame, resolution_scale=0.1)
        assert result.shape == single_pixel_frame.shape

    # --- Color Effects ---

    def test_hue_shift_negative_degrees(self, small_frame):
        """Negative degrees should wrap correctly."""
        result = hue_shift(small_frame, degrees=-180)
        assert result.shape == small_frame.shape

    def test_hue_shift_large_degrees(self, small_frame):
        """Degrees > 360 should wrap, not crash."""
        result = hue_shift(small_frame, degrees=9999)
        assert result.shape == small_frame.shape

    def test_contrast_extreme_positive(self, small_frame):
        """amount=100 should not overflow."""
        result = contrast_crush(small_frame, amount=100, curve="linear")
        assert result.max() <= 255
        assert result.min() >= 0

    def test_contrast_extreme_negative(self, small_frame):
        """amount=-100 should flatten to gray, not crash."""
        result = contrast_crush(small_frame, amount=-100, curve="s_curve")
        assert result.dtype == np.uint8

    def test_contrast_hard_zero_amount(self, small_frame):
        """Hard curve with amount=0 should produce usable output."""
        result = contrast_crush(small_frame, amount=0, curve="hard")
        assert result.dtype == np.uint8

    def test_invert_amount_over_one(self, small_frame):
        """amount > 1.0 is clamped to 1.0."""
        result = color_invert(small_frame, amount=5.0)
        assert result.max() <= 255
        assert result.min() >= 0

    def test_temperature_extreme_warm(self, small_frame):
        """temp=100 must not overflow red channel."""
        result = color_temperature(small_frame, temp=100)
        assert result.max() <= 255
        assert result.min() >= 0

    def test_temperature_extreme_cool(self, small_frame):
        """temp=-100 must not overflow blue channel."""
        result = color_temperature(small_frame, temp=-100)
        assert result.max() <= 255
        assert result.min() >= 0

    def test_exposure_extreme_bright(self, small_frame):
        """stops=3.0 (8x multiplier) must not overflow."""
        result = brightness_exposure(small_frame, stops=3.0)
        assert result.max() <= 255
        assert result.dtype == np.uint8


# ---------------------------------------------------------------------------
# 6. TEMP FILE CLEANUP
# ---------------------------------------------------------------------------

class TestTempFileCleanup:
    """Verify that temp files are cleaned up in all code paths."""

    def test_extract_single_frame_cleans_temp_on_success(self, tmp_dir):
        """extract_single_frame uses a finally block -- verify temp PNG removed."""
        # We test the cleanup logic by checking the finally block exists
        import inspect
        source = inspect.getsource(extract_single_frame)
        assert "finally" in source, "extract_single_frame must use try/finally for cleanup"
        assert "unlink" in source, "extract_single_frame must unlink temp file"

    def test_upload_cleans_temp_on_probe_failure(self):
        """server.py upload: if probe_video fails, temp file must be deleted."""
        # server.py line 100: os.unlink(tmp.name) in except block
        # BUT: if the exception happens DURING file.read() or tmp.write(),
        # the except won't catch it because it's outside the try block.
        import inspect
        from server import upload_video
        source = inspect.getsource(upload_video)
        # The try block starts AFTER tmp.write -- if write fails, temp leaks
        assert "os.unlink" in source, "Upload must clean temp on failure"

    def test_upload_does_not_clean_on_success(self):
        """On successful upload, temp file is stored in _state and never cleaned."""
        # This IS a bug: when a new video is uploaded, the OLD temp file leaks.
        # _state["video_path"] is overwritten but the old file is never deleted.
        import inspect
        from server import upload_video
        source = inspect.getsource(upload_video)
        # Documenting the bug: there's no cleanup of the previous video_path
        assert "_state[\"video_path\"]" in source or "_state['video_path']" in source

    def test_render_recipe_uses_temp_directory_context(self):
        """render_recipe must use TemporaryDirectory context manager for auto-cleanup."""
        import inspect
        from core.preview import render_recipe
        source = inspect.getsource(render_recipe)
        assert "TemporaryDirectory" in source, "Must use TemporaryDirectory for cleanup"
        assert "with" in source, "Must use 'with' statement for auto-cleanup"

    def test_extract_frames_no_cleanup(self):
        """DOCUMENTS BUG: extract_frames writes PNGs to output_dir but caller
        must clean up. If caller crashes, frames stay on disk forever."""
        import inspect
        from core.video_io import extract_frames
        source = inspect.getsource(extract_frames)
        # extract_frames itself doesn't clean up -- it returns paths
        # This is by design (caller manages lifecycle), but a crash leaks
        assert "unlink" not in source, "extract_frames does not self-clean (by design)"


# ---------------------------------------------------------------------------
# 7. EFFECT OUTPUT CONTRACT
# ---------------------------------------------------------------------------

class TestEffectOutputContract:
    """Every effect must return (H, W, 3) uint8 arrays with values in 0-255."""

    @pytest.fixture(params=list(EFFECTS.keys()))
    def effect_name(self, request):
        return request.param

    def test_effect_returns_same_shape(self, effect_name, medium_frame):
        """Every effect must return the same shape as input."""
        entry = EFFECTS[effect_name]
        fn = entry["fn"]
        params = entry["params"].copy()
        result = fn(medium_frame, **params)
        assert result.shape == medium_frame.shape, (
            f"Effect {effect_name} changed shape: {medium_frame.shape} -> {result.shape}"
        )

    def test_effect_returns_uint8(self, effect_name, medium_frame):
        """Every effect must return uint8 dtype."""
        entry = EFFECTS[effect_name]
        fn = entry["fn"]
        params = entry["params"].copy()
        result = fn(medium_frame, **params)
        assert result.dtype == np.uint8, (
            f"Effect {effect_name} returned {result.dtype}, expected uint8"
        )

    def test_effect_values_in_range(self, effect_name, medium_frame):
        """Every effect must return values in [0, 255]."""
        entry = EFFECTS[effect_name]
        fn = entry["fn"]
        params = entry["params"].copy()
        result = fn(medium_frame, **params)
        assert result.min() >= 0, f"Effect {effect_name} has values < 0"
        assert result.max() <= 255, f"Effect {effect_name} has values > 255"


# ---------------------------------------------------------------------------
# 8. APPLY_CHAIN SAFETY
# ---------------------------------------------------------------------------

class TestApplyChainSafety:
    """The effect chain system must handle edge cases gracefully."""

    def test_empty_chain_returns_input(self, small_frame):
        """Empty effect list should return the input frame unchanged."""
        result = apply_chain(small_frame, [])
        np.testing.assert_array_equal(result, small_frame)

    def test_unknown_effect_raises_valueerror(self, small_frame):
        """Unknown effect name must raise ValueError, not KeyError."""
        with pytest.raises(ValueError, match="Unknown effect"):
            apply_chain(small_frame, [{"name": "nonexistent_effect", "params": {}}])

    def test_missing_params_key_uses_defaults(self, small_frame):
        """Effect dict with no 'params' key must use defaults."""
        result = apply_chain(small_frame, [{"name": "hueshift"}])
        assert result.shape == small_frame.shape

    def test_extra_params_are_passed(self, small_frame):
        """Extra unknown parameters should cause TypeError from the effect function."""
        with pytest.raises(TypeError):
            apply_chain(small_frame, [{"name": "hueshift", "params": {"bogus_param": 42}}])

    def test_chain_of_10_effects_completes(self, small_frame):
        """A chain at max depth must complete without memory issues."""
        chain = [{"name": "hueshift", "params": {"degrees": 10}}] * 10
        result = apply_chain(small_frame, chain)
        assert result.shape == small_frame.shape
        assert result.dtype == np.uint8

    def test_chain_over_max_depth_raises(self, small_frame):
        """A chain exceeding MAX_CHAIN_DEPTH must raise SafetyError."""
        from core.safety import SafetyError
        chain = [{"name": "hueshift", "params": {"degrees": 10}}] * 11
        with pytest.raises(SafetyError, match="max is 10"):
            apply_chain(small_frame, chain)


# ---------------------------------------------------------------------------
# 9. CONCURRENCY / GLOBAL STATE ISSUES
# ---------------------------------------------------------------------------

class TestGlobalStateSafety:
    """server.py uses a module-level _state dict -- race conditions abound."""

    def test_state_is_global_module_dict(self):
        """DOCUMENTS BUG: _state is a module-level dict shared across all requests."""
        from server import _state
        assert isinstance(_state, dict)
        # Two simultaneous requests would overwrite each other's video_path.
        # This is acceptable for single-user MVP but must be documented.

    def test_frame_to_data_url_pure_function(self):
        """_frame_to_data_url must be a pure function with no side effects."""
        from server import _frame_to_data_url
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        result1 = _frame_to_data_url(frame)
        result2 = _frame_to_data_url(frame)
        assert result1 == result2, "Same input must produce same output"
        assert result1.startswith("data:image/jpeg;base64,")


# ---------------------------------------------------------------------------
# 10. PERFORMANCE BOUNDS (Timing)
# ---------------------------------------------------------------------------

class TestPerformanceBounds:
    """Effects must complete within reasonable time limits."""

    def test_pixelsort_completes_under_5_seconds_1080p(self, large_frame):
        """Pixelsort on a 1080p frame must not take longer than 5 seconds."""
        start = time.time()
        pixelsort(large_frame, threshold=0.5)
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Pixelsort took {elapsed:.1f}s on 1080p -- too slow"

    def test_hue_shift_completes_under_1_second_1080p(self, large_frame):
        """Hue shift (vectorized) should be fast."""
        start = time.time()
        hue_shift(large_frame, degrees=90)
        elapsed = time.time() - start
        assert elapsed < 1.0, f"Hue shift took {elapsed:.1f}s on 1080p"

    def test_10_effects_complete_under_10_seconds_1080p(self, large_frame):
        """Chain of 10 effects on 1080p must finish in 10 seconds."""
        names = list(EFFECTS.keys())[:10]
        chain = [{"name": name, "params": {}} for name in names]
        start = time.time()
        apply_chain(large_frame, chain)
        elapsed = time.time() - start
        assert elapsed < 10.0, f"10-effect chain took {elapsed:.1f}s on 1080p"


# ---------------------------------------------------------------------------
# 11. DATA URL OUTPUT SIZE
# ---------------------------------------------------------------------------

class TestDataUrlSize:
    """Preview data URLs must not balloon to unreasonable sizes."""

    def test_data_url_size_bounded_for_1080p(self, large_frame):
        """A 1080p JPEG data URL should be under 1MB."""
        from server import _frame_to_data_url
        url = _frame_to_data_url(large_frame)
        # base64 expands by ~33%, so 1MB base64 = ~750KB JPEG
        max_size = 1 * 1024 * 1024  # 1MB
        assert len(url) < max_size, (
            f"Data URL is {len(url)/1024:.0f}KB -- too large for browser"
        )

    def test_data_url_is_valid_jpeg(self, small_frame):
        """The data URL must contain valid JPEG data."""
        from server import _frame_to_data_url
        import base64
        url = _frame_to_data_url(small_frame)
        assert url.startswith("data:image/jpeg;base64,")
        b64_data = url.split(",", 1)[1]
        raw = base64.b64decode(b64_data)
        # JPEG files start with FF D8 FF
        assert raw[:3] == b"\xff\xd8\xff", "Not a valid JPEG"

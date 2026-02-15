"""Tests for RGBA pipeline: transparent layer rendering and preview compositing."""

import base64
import numpy as np
import pytest

from effects import apply_effect, EFFECTS


class TestFrameToDataUrl:
    """Tests for _frame_to_data_url in server.py."""

    def _get_fn(self):
        from server import _frame_to_data_url
        return _frame_to_data_url

    def test_frame_to_data_url_jpeg_for_rgb(self):
        """RGB frame produces a JPEG data URL."""
        fn = self._get_fn()
        frame = np.zeros((64, 64, 3), dtype=np.uint8)
        frame[:, :] = [100, 150, 200]
        result = fn(frame)
        assert result.startswith("data:image/jpeg;base64,")
        # Verify it's valid base64
        b64_part = result.split(",", 1)[1]
        decoded = base64.b64decode(b64_part)
        assert len(decoded) > 0

    def test_frame_to_data_url_png_for_rgba(self):
        """RGBA frame produces a PNG data URL."""
        fn = self._get_fn()
        frame = np.zeros((64, 64, 4), dtype=np.uint8)
        frame[:, :] = [100, 150, 200, 128]
        result = fn(frame)
        assert result.startswith("data:image/png;base64,")
        b64_part = result.split(",", 1)[1]
        decoded = base64.b64decode(b64_part)
        # PNG magic bytes
        assert decoded[:4] == b"\x89PNG"

    def test_checkerboard_composite_blends(self):
        """RGBA composited onto checkerboard produces intermediate pixel values."""
        fn = self._get_fn()
        # Semi-transparent red
        frame = np.zeros((16, 16, 4), dtype=np.uint8)
        frame[:, :] = [255, 0, 0, 128]  # 50% alpha red
        result = fn(frame)
        # Decode the PNG and check pixel values are blended (not pure red or pure checker)
        from PIL import Image
        from io import BytesIO
        b64_part = result.split(",", 1)[1]
        img = Image.open(BytesIO(base64.b64decode(b64_part)))
        pixels = np.array(img)
        # With 50% alpha, red channel should be between checker color and 255
        # Checker colors are 200 and 255, so blended red should be ~227 or ~255
        # The key check: green/blue channels should NOT be 0 (they'd pick up checker)
        assert pixels[:, :, 1].mean() > 0  # Green > 0 from checker bleed
        assert pixels[:, :, 2].mean() > 0  # Blue > 0 from checker bleed


class TestOutputAlphaFlag:
    """Tests for output_alpha flag on effect entries."""

    def test_chroma_key_has_output_alpha(self):
        assert EFFECTS["chroma_key"].get("output_alpha") is True

    def test_luma_key_has_output_alpha(self):
        assert EFFECTS["luma_key"].get("output_alpha") is True

    def test_emboss_has_output_alpha(self):
        assert EFFECTS["emboss"].get("output_alpha") is True


class TestChromaKeyAlphaOutput:
    """Tests that keying effects produce 4-channel RGBA output."""

    def test_chroma_key_output_has_alpha(self):
        """chroma_key with replace_color=transparent produces 4-channel output."""
        # Create a green frame
        frame = np.zeros((64, 64, 3), dtype=np.uint8)
        frame[:, :] = [0, 255, 0]  # Pure green
        result = apply_effect(frame, "chroma_key", hue=120.0, tolerance=30.0,
                              softness=10.0, replace_color="transparent")
        assert result.ndim == 3
        assert result.shape[2] == 4, f"Expected 4 channels (RGBA), got {result.shape[2]}"

    def test_luma_key_output_has_alpha(self):
        """luma_key with replace_color=transparent produces 4-channel output."""
        # Create a dark frame
        frame = np.zeros((64, 64, 3), dtype=np.uint8)
        frame[:, :] = [10, 10, 10]  # Very dark
        result = apply_effect(frame, "luma_key", threshold=0.3, mode="dark",
                              softness=10.0, replace_color="transparent")
        assert result.ndim == 3
        assert result.shape[2] == 4, f"Expected 4 channels (RGBA), got {result.shape[2]}"


class TestAlphaPreservation:
    """Tests that alpha channels are properly handled through the pipeline."""

    def test_apply_effect_preserves_alpha_for_output_alpha_effects(self):
        """apply_effect on chroma_key returns RGBA when input is RGB."""
        frame = np.zeros((64, 64, 3), dtype=np.uint8)
        frame[:, :] = [0, 200, 0]  # Green-ish
        result = apply_effect(frame, "chroma_key", replace_color="transparent")
        assert result.shape[2] == 4

    def test_rgb_effects_strip_and_reattach_alpha(self):
        """Non-alpha effect on RGBA frame preserves input alpha channel."""
        frame = np.zeros((64, 64, 4), dtype=np.uint8)
        frame[:, :] = [100, 150, 200, 180]  # RGBA with alpha=180
        # contrast is a standard RGB effect, not in output_alpha or physics sets
        result = apply_effect(frame, "contrast", amount=50)
        assert result.ndim == 3
        assert result.shape[2] == 4, f"Expected alpha preserved, got {result.shape[2]} channels"
        # The alpha channel should match the input alpha
        np.testing.assert_array_equal(result[:, :, 3], 180)

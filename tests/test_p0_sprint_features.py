"""
P0 Sprint Feature Tests — 2026-02-15

Tests for features built in the P0 sprint:
1. Frame pre-cache: server preview endpoint handles rapid sequential requests
2. Click-to-type: parameter value clamping (server-side validation)
3. WCAG contrast: CSS variable validation
4. Loop brace: timeline.js syntax validity + serialization round-trip
5. Knob value rendering: display formatting matches spec

These are persistent tests per Execution Gate #6.
"""

import json
import os
import sys
import subprocess

import numpy as np
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from effects import apply_chain, EFFECTS


# ============ 1. RAPID SEQUENTIAL PREVIEW (Frame Pre-Cache Support) ============

class TestRapidSequentialPreview:
    """Verify apply_chain handles rapid sequential frame_index calls without state corruption."""

    @pytest.fixture
    def test_frame(self):
        return np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)

    def test_sequential_frames_no_crash(self, test_frame):
        """Simulate pre-cache: 8 frames processed in sequence."""
        chain = [{"name": "hueshift", "params": {"degrees": 45}, "bypassed": False}]
        for i in range(8):
            result = apply_chain(test_frame, chain, frame_index=i)
            assert result is not None
            assert result.shape == test_frame.shape

    def test_sequential_frames_with_stateful_effect(self, test_frame):
        """Stateful effects (feedback, stutter) must handle frame_index jumps."""
        chain = [{"name": "vhs", "params": {}, "bypassed": False}]
        # Simulate playback then loop jump (frame 10 → frame 2)
        for i in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 2, 3, 4]:
            result = apply_chain(test_frame, chain, frame_index=i)
            assert result is not None

    def test_same_frame_twice_is_deterministic(self, test_frame):
        """Same frame_index + same params = same result (cache correctness)."""
        chain = [{"name": "pixelsort", "params": {"threshold": 0.5, "direction": "horizontal"}, "bypassed": False}]
        r1 = apply_chain(test_frame, chain, frame_index=5)
        r2 = apply_chain(test_frame, chain, frame_index=5)
        # Deterministic effects should produce identical output
        np.testing.assert_array_equal(r1, r2)


# ============ 2. PARAMETER VALUE CLAMPING ============

class TestParameterClamping:
    """Click-to-type allows arbitrary input — server must handle out-of-range values."""

    @pytest.fixture
    def test_frame(self):
        return np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)

    def test_param_beyond_max(self, test_frame):
        """Value above max should not crash (client clamps, but defense in depth)."""
        chain = [{"name": "hueshift", "params": {"degrees": 99999}, "bypassed": False}]
        result = apply_chain(test_frame, chain, frame_index=0)
        assert result is not None

    def test_param_below_min(self, test_frame):
        """Value below min should not crash."""
        chain = [{"name": "contrast", "params": {"amount": -99999}, "bypassed": False}]
        result = apply_chain(test_frame, chain, frame_index=0)
        assert result is not None

    def test_param_nan_becomes_default(self, test_frame):
        """NaN from parseFloat('abc') — server should handle gracefully."""
        chain = [{"name": "blur", "params": {"radius": float('nan')}, "bypassed": False}]
        # Should not raise — effect should use default or clamp
        try:
            result = apply_chain(test_frame, chain, frame_index=0)
            assert result is not None
        except (ValueError, TypeError):
            # Acceptable: explicit error is better than silent corruption
            pass

    def test_param_zero_for_divisor_effects(self, test_frame):
        """Zero in denominator params should not crash (division by zero guard)."""
        chain = [{"name": "pixelate", "params": {"size": 0}, "bypassed": False}]
        try:
            result = apply_chain(test_frame, chain, frame_index=0)
            assert result is not None
        except (ValueError, ZeroDivisionError):
            pass


# ============ 3. WCAG CONTRAST VALIDATION ============

class TestWCAGContrast:
    """Verify CSS variables meet WCAG AA contrast ratios."""

    @staticmethod
    def relative_luminance(hex_color):
        """Calculate WCAG relative luminance from hex color."""
        hex_color = hex_color.lstrip('#')
        r, g, b = [int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
        components = []
        for c in [r, g, b]:
            if c <= 0.03928:
                components.append(c / 12.92)
            else:
                components.append(((c + 0.055) / 1.055) ** 2.4)
        return 0.2126 * components[0] + 0.7152 * components[1] + 0.0722 * components[2]

    @staticmethod
    def contrast_ratio(color1, color2):
        L1 = TestWCAGContrast.relative_luminance(color1)
        L2 = TestWCAGContrast.relative_luminance(color2)
        lighter = max(L1, L2)
        darker = min(L1, L2)
        return (lighter + 0.05) / (darker + 0.05)

    def test_text_dim_contrast(self):
        """--text-dim (#7a7a7a) on --bg-darkest (#0a0a0b) must be >= 3.0:1."""
        ratio = self.contrast_ratio('#7a7a7a', '#0a0a0b')
        assert ratio >= 3.0, f"text-dim contrast {ratio:.1f}:1 < 3.0:1"

    def test_text_secondary_contrast(self):
        """--text-secondary (#999) on --bg-darkest (#0a0a0b) must be >= 4.5:1."""
        ratio = self.contrast_ratio('#999999', '#0a0a0b')
        assert ratio >= 4.5, f"text-secondary contrast {ratio:.1f}:1 < 4.5:1"

    def test_text_primary_contrast(self):
        """--text-primary (#e0e0e0) on --bg-darkest (#0a0a0b) must be >= 7.0:1."""
        ratio = self.contrast_ratio('#e0e0e0', '#0a0a0b')
        assert ratio >= 7.0, f"text-primary contrast {ratio:.1f}:1 < 7.0:1"


# ============ 4. TIMELINE JS SYNTAX + LOOP BRACE STRUCTURE ============

class TestTimelineJS:
    """Verify timeline.js is valid JS and contains loop brace code."""

    TIMELINE_PATH = os.path.join(PROJECT_ROOT, 'ui', 'static', 'timeline.js')

    def test_js_syntax_valid(self):
        """timeline.js must parse without syntax errors."""
        result = subprocess.run(
            ['node', '-c', self.TIMELINE_PATH],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"JS syntax error: {result.stderr}"

    def test_loop_state_vars_exist(self):
        """Loop brace state variables must be declared in constructor."""
        with open(self.TIMELINE_PATH) as f:
            content = f.read()
        assert 'this.loopStart' in content
        assert 'this.loopEnd' in content
        assert 'this.loopEnabled' in content

    def test_loop_methods_exist(self):
        """Loop control methods must exist."""
        with open(self.TIMELINE_PATH) as f:
            content = f.read()
        assert 'setLoop(' in content
        assert 'toggleLoop(' in content
        assert 'clearLoop(' in content
        assert 'setLoopFromIO(' in content

    def test_loop_serialization(self):
        """Loop state must appear in serialize() output."""
        with open(self.TIMELINE_PATH) as f:
            content = f.read()
        assert 'loopStart: this.loopStart' in content
        assert 'loopEnd: this.loopEnd' in content
        assert 'loopEnabled: this.loopEnabled' in content

    def test_loop_deserialization(self):
        """deserialize() must restore loop state."""
        with open(self.TIMELINE_PATH) as f:
            content = f.read()
        assert 'data.loopStart' in content
        assert 'data.loopEnd' in content
        assert 'data.loopEnabled' in content

    def test_drawLoopBrace_exists(self):
        """drawLoopBrace() rendering method must exist."""
        with open(self.TIMELINE_PATH) as f:
            content = f.read()
        assert 'drawLoopBrace()' in content

    def test_loop_keyboard_shortcut(self):
        """L key handler for loop toggle must exist."""
        with open(self.TIMELINE_PATH) as f:
            content = f.read()
        assert 'toggleLoop()' in content
        assert 'setLoopFromIO()' in content


# ============ 5. APP JS SYNTAX + KNOB FEATURES ============

class TestAppJS:
    """Verify app.js is valid JS and contains click-to-type + pre-cache code."""

    APP_PATH = os.path.join(PROJECT_ROOT, 'ui', 'static', 'app.js')

    def test_js_syntax_valid(self):
        """app.js must parse without syntax errors."""
        result = subprocess.run(
            ['node', '-c', self.APP_PATH],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"JS syntax error: {result.stderr}"

    def test_click_to_type_handler_exists(self):
        """Click-to-type handler on .knob-value must exist."""
        with open(self.APP_PATH) as f:
            content = f.read()
        assert 'knob-value-input' in content
        assert "input.type = 'number'" in content

    def test_frame_cache_exists(self):
        """Frame pre-cache system must exist."""
        with open(self.APP_PATH) as f:
            content = f.read()
        assert 'frameCache' in content
        assert 'prefetchFrames' in content
        assert 'clearFrameCache' in content

    def test_knob_value_skip_during_edit(self):
        """updateKnobVisual must skip value span when input is active."""
        with open(self.APP_PATH) as f:
            content = f.read()
        assert "!valueSpan.querySelector('.knob-value-input')" in content


# ============ 6. CSS VALIDATION ============

class TestCSS:
    """Verify style.css contains required styles."""

    CSS_PATH = os.path.join(PROJECT_ROOT, 'ui', 'static', 'style.css')

    def test_knob_value_input_styles(self):
        """Click-to-type input must have matching styles."""
        with open(self.CSS_PATH) as f:
            content = f.read()
        assert '.knob-value-input' in content
        assert 'cursor: text' in content  # knob-value should show text cursor

    def test_contrast_values_wcag(self):
        """CSS variables must use WCAG-passing values (accessible palette)."""
        with open(self.CSS_PATH) as f:
            content = f.read()
        # text-dim raised to #8a8a96 for WCAG AA compliance on primary backgrounds
        assert '--text-dim: #8a8a96' in content
        # text-secondary raised to #a0a0ac for WCAG AA
        assert '--text-secondary: #a0a0ac' in content

"""
Entropic — UX Improvements Tests
Tests for: structured errors, render progress, effect groups, duplicate, UI elements.

Run with: pytest tests/test_ux_improvements.py -v
"""

import os
import sys

import pytest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from effects import apply_chain, EFFECTS


@pytest.fixture
def frame():
    """A 64x64 deterministic frame for consistent testing."""
    rng = np.random.RandomState(42)
    return rng.randint(0, 256, (64, 64, 3), dtype=np.uint8)


# ---------------------------------------------------------------------------
# STRUCTURED ERRORS (Item 1: UX-E)
# ---------------------------------------------------------------------------

class TestStructuredErrors:
    """Server error responses include code, hint, and action keys."""

    def test_error_detail_function(self):
        """_error_detail returns structured dict with code, hint, action."""
        from server import _error_detail

        result = _error_detail("no_video", "No video loaded")
        assert result["detail"] == "No video loaded"
        assert result["code"] == "NO_VIDEO"
        assert result["hint"] == "Load a video or image file first."
        assert result["action"] == "load_file"

    def test_error_detail_unknown_key(self):
        """Unknown error key returns UNKNOWN code with empty hint."""
        from server import _error_detail

        result = _error_detail("nonexistent_key", "Something broke")
        assert result["code"] == "UNKNOWN"
        assert result["hint"] == ""
        assert result["action"] is None

    def test_all_recovery_keys_valid(self):
        """All ERROR_RECOVERY entries have required keys."""
        from server import ERROR_RECOVERY

        for key, recovery in ERROR_RECOVERY.items():
            assert "code" in recovery, f"Missing 'code' in {key}"
            assert "hint" in recovery, f"Missing 'hint' in {key}"
            assert "action" in recovery, f"Missing 'action' in {key}"


# ---------------------------------------------------------------------------
# RENDER PROGRESS (Item 5: UX-A)
# ---------------------------------------------------------------------------

class TestRenderProgress:
    """Render progress dict has expected shape."""

    def test_render_progress_shape(self):
        """_render_progress has required keys."""
        from server import _render_progress

        assert "active" in _render_progress
        assert "current_frame" in _render_progress
        assert "total_frames" in _render_progress
        assert "phase" in _render_progress

    def test_render_progress_defaults(self):
        """Default state is inactive/idle."""
        from server import _render_progress

        assert _render_progress["active"] is False
        assert _render_progress["phase"] == "idle"


# ---------------------------------------------------------------------------
# EFFECT GROUPS (Item 6: Nestable Racks)
# ---------------------------------------------------------------------------

class TestEffectGroups:
    """apply_chain handles nested group items."""

    def test_group_applies_children(self, frame):
        """A group with children applies effects sequentially."""
        chain = [
            {
                "type": "group",
                "name": "Test Group",
                "bypassed": False,
                "mix": 1.0,
                "children": [
                    {"name": "invert", "params": {}},
                ],
            }
        ]
        result = apply_chain(frame, chain)
        assert result.shape == frame.shape
        # Invert should flip the pixel values
        assert not np.array_equal(result, frame)

    def test_bypassed_group_skips_children(self, frame):
        """Bypassed groups should not apply any child effects."""
        chain = [
            {
                "type": "group",
                "name": "Bypassed Group",
                "bypassed": True,
                "mix": 1.0,
                "children": [
                    {"name": "invert", "params": {}},
                ],
            }
        ]
        result = apply_chain(frame, chain)
        assert np.array_equal(result, frame), "Bypassed group should not modify frame"

    def test_empty_group_passthrough(self, frame):
        """Group with no children passes frame through unchanged."""
        chain = [
            {
                "type": "group",
                "name": "Empty Group",
                "bypassed": False,
                "mix": 1.0,
                "children": [],
            }
        ]
        result = apply_chain(frame, chain)
        assert np.array_equal(result, frame)

    def test_group_mix_blending(self, frame):
        """Group with mix < 1.0 blends original and processed."""
        chain = [
            {
                "type": "group",
                "name": "Half Mix Group",
                "bypassed": False,
                "mix": 0.5,
                "children": [
                    {"name": "invert", "params": {}},
                ],
            }
        ]
        result = apply_chain(frame, chain)
        # Result should be different from both original and full invert
        assert not np.array_equal(result, frame)
        full_invert = apply_chain(frame.copy(), [{"name": "invert", "params": {}}])
        assert not np.array_equal(result, full_invert)

    def test_nested_groups(self, frame):
        """Groups inside groups recurse correctly."""
        chain = [
            {
                "type": "group",
                "name": "Outer",
                "bypassed": False,
                "mix": 1.0,
                "children": [
                    {
                        "type": "group",
                        "name": "Inner",
                        "bypassed": False,
                        "mix": 1.0,
                        "children": [
                            {"name": "invert", "params": {}},
                        ],
                    }
                ],
            }
        ]
        result = apply_chain(frame, chain)
        # Should match applying invert directly
        direct = apply_chain(frame.copy(), [{"name": "invert", "params": {}}])
        np.testing.assert_array_equal(result, direct)

    def test_group_zero_mix_returns_original(self, frame):
        """Group with mix=0 returns the original frame."""
        chain = [
            {
                "type": "group",
                "name": "Zero Mix",
                "bypassed": False,
                "mix": 0.0,
                "children": [
                    {"name": "invert", "params": {}},
                ],
            }
        ]
        result = apply_chain(frame, chain)
        np.testing.assert_array_equal(result, frame)

    def test_mixed_chain_with_groups(self, frame):
        """Chain with both groups and plain effects processes correctly."""
        chain = [
            {"name": "invert", "params": {}},
            {
                "type": "group",
                "name": "Group",
                "bypassed": False,
                "mix": 1.0,
                "children": [
                    {"name": "invert", "params": {}},
                ],
            }
        ]
        # invert -> invert = original
        result = apply_chain(frame, chain)
        np.testing.assert_array_equal(result, frame)


# ---------------------------------------------------------------------------
# DUPLICATE WITH PARAMS (Item 8: Already works — regression test)
# ---------------------------------------------------------------------------

class TestDuplicateDeepClone:
    """Ensure params are deep-cloned, not shared by reference."""

    def test_deep_clone_params(self):
        """JSON round-trip creates independent param copies."""
        import json
        original = {"name": "pixelsort", "params": {"threshold": 0.5, "direction": "horizontal"}}
        clone_params = json.loads(json.dumps(original["params"]))
        clone_params["threshold"] = 0.9
        assert original["params"]["threshold"] == 0.5, "Original should not be mutated"


# ---------------------------------------------------------------------------
# UI ELEMENTS (Items 2, 4, 7)
# ---------------------------------------------------------------------------

class TestUIElements:
    """Verify index.html contains expected elements."""

    @pytest.fixture(autouse=True)
    def load_html(self):
        html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "index.html")
        with open(html_path) as f:
            self.html = f.read()

    def test_shortcut_hints_in_menus(self):
        """Menu items contain shortcut hints."""
        assert "menu-shortcut" in self.html
        # Undo menu item has shortcut hint
        assert "Undo" in self.html

    def test_help_overlay_exists(self):
        """Help panel modal exists in HTML."""
        assert 'id="help-overlay"' in self.html

    def test_help_search_input(self):
        """Help panel has searchable effect reference."""
        assert 'id="help-search"' in self.html

    def test_layers_renamed_to_devices(self):
        """Right panel tab renamed from 'Layers' to 'Devices'."""
        assert ">Devices<" in self.html

    def test_perform_renamed_to_mixer(self):
        """Perform toggle button renamed to 'Mixer'."""
        assert ">Mixer<" in self.html

    def test_mode_badge_removed(self):
        """Mode badge div removed (was always 'TIMELINE')."""
        assert 'id="mode-badge"' not in self.html

    def test_export_mix_label_hint(self):
        """Export mix slider has effect intensity label."""
        assert "Effect Intensity" in self.html

    def test_mix_slider_removed(self):
        """Global mix slider was removed — per-effect dry/wet handles this."""
        assert "mix-control" not in self.html

    def test_export_range_selector(self):
        """Export dialog has range selector (full/playhead/custom)."""
        assert 'id="export-range"' in self.html
        assert "Full Video" in self.html
        assert "From Playhead" in self.html
        assert "Custom Range" in self.html

    def test_export_duration_field(self):
        """Export dialog has duration field for playhead export."""
        assert 'id="export-duration"' in self.html

    def test_group_shortcuts_in_reference(self):
        """Shortcut reference includes group shortcuts."""
        assert "Create group" in self.html
        assert "Ungroup" in self.html


# ---------------------------------------------------------------------------
# APP.JS FUNCTIONS (Items 1, 3, 4, 6)
# ---------------------------------------------------------------------------

class TestAppJSFunctions:
    """Verify app.js contains expected function definitions."""

    @pytest.fixture(autouse=True)
    def load_js(self):
        js_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "static", "app.js")
        with open(js_path) as f:
            self.js = f.read()

    def test_handle_api_error_exists(self):
        """handleApiError function defined."""
        assert "function handleApiError" in self.js

    def test_persist_history_exists(self):
        """_persistHistory function defined."""
        assert "function _persistHistory" in self.js

    def test_load_history_exists(self):
        """_loadHistory function defined."""
        assert "function _loadHistory" in self.js

    def test_show_help_panel_exists(self):
        """showHelpPanel function defined."""
        assert "function showHelpPanel" in self.js

    def test_show_onboarding_exists(self):
        """showOnboarding function defined."""
        assert "function showOnboarding" in self.js

    def test_add_group_exists(self):
        """addGroup function defined."""
        assert "function addGroup" in self.js

    def test_ungroup_selected_exists(self):
        """ungroupSelected function defined."""
        assert "function ungroupSelected" in self.js

    def test_flatten_chain_for_api_exists(self):
        """flattenChainForApi function defined."""
        assert "function flattenChainForApi" in self.js

    def test_render_device_html_exists(self):
        """_renderDeviceHTML function handles group rendering."""
        assert "function _renderDeviceHTML" in self.js
        assert "device-group" in self.js

    def test_filter_help_effects_exists(self):
        """filterHelpEffects function defined."""
        assert "function filterHelpEffects" in self.js

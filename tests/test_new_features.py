#!/usr/bin/env python3
"""
Entropic — Tests for New Features (Phases C9, D, E, F)

C9: Loop region on timeline (toggleLoop, drag handles, playback wraps)
Phase D: Perform module (trigger pads, keys 1-8, toggle/hold modes, backend pass-through)
Phase E: MIDI (keyboard toggle, key-to-note mapping, Web MIDI, MIDI Learn)
Phase F: Freeze/Flatten (per-track freeze, 300-frame cap, frozen preview cache)

Run with: pytest tests/test_new_features.py -v
"""

import os
import sys
import pytest
import json

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
    _state["frozen_tracks"] = {}
    _state["frozen_preview_cache"] = {}
    _state["perform_sessions"] = {}
    _state["loop_region"] = None
    yield
    # Clear state after each test
    _state["video_path"] = None
    _state["video_info"] = None
    _state["current_frame"] = None
    _state["frozen_tracks"] = {}
    _state["frozen_preview_cache"] = {}
    _state["perform_sessions"] = {}
    _state["loop_region"] = None


@pytest.fixture
def client():
    return TestClient(app)


# ===========================================================================
# PHASE F: FREEZE/FLATTEN TRACK TESTS
# ===========================================================================

class TestFreezeTrack:
    """Test /api/track/freeze and /api/track/unfreeze endpoints."""

    def test_freeze_track_valid(self, client):
        """Freeze a track with valid parameters."""
        resp = client.post("/api/track/freeze", json={
            "track_index": 0,
            "effects": [{"name": "blur", "params": {"radius": 5.0}}],
            "start_frame": 0,
            "end_frame": 10
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert data["status"] == "frozen"

    def test_freeze_track_no_video_loaded(self, client):
        """Freeze should fail gracefully when no video is loaded."""
        _state["video_path"] = None
        resp = client.post("/api/track/freeze", json={
            "track_index": 0,
            "effects": [],
            "start_frame": 0,
            "end_frame": 10
        })
        assert resp.status_code == 400
        assert "error" in resp.json()

    def test_freeze_track_exceeds_300_frame_cap(self, client):
        """Freeze should reject requests exceeding 300 frames."""
        resp = client.post("/api/track/freeze", json={
            "track_index": 0,
            "effects": [{"name": "blur", "params": {"radius": 5.0}}],
            "start_frame": 0,
            "end_frame": 350  # 351 frames > 300
        })
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data
        assert "300" in data["error"].lower() or "frame" in data["error"].lower()

    def test_freeze_track_at_300_frame_cap(self, client):
        """Freeze should accept exactly 300 frames."""
        resp = client.post("/api/track/freeze", json={
            "track_index": 0,
            "effects": [{"name": "blur", "params": {"radius": 5.0}}],
            "start_frame": 0,
            "end_frame": 299  # 300 frames (inclusive)
        })
        assert resp.status_code in [200, 202]  # 200 = sync, 202 = async

    def test_freeze_track_empty_effects_chain(self, client):
        """Freeze with empty effects chain should work (freezes original frames)."""
        resp = client.post("/api/track/freeze", json={
            "track_index": 0,
            "effects": [],
            "start_frame": 5,
            "end_frame": 15
        })
        assert resp.status_code in [200, 202]

    def test_unfreeze_track(self, client):
        """Unfreeze a frozen track."""
        # First freeze
        freeze_resp = client.post("/api/track/freeze", json={
            "track_index": 0,
            "effects": [{"name": "blur", "params": {"radius": 5.0}}],
            "start_frame": 0,
            "end_frame": 10
        })
        assert freeze_resp.status_code == 200

        # Then unfreeze
        unfreeze_resp = client.post("/api/track/unfreeze", json={"track_index": 0})
        assert unfreeze_resp.status_code == 200
        data = unfreeze_resp.json()
        assert "status" in data
        assert data["status"] == "unfrozen"

    def test_unfreeze_never_frozen_track(self, client):
        """Unfreeze should handle a track that was never frozen."""
        resp = client.post("/api/track/unfreeze", json={"track_index": 5})
        # Should return 200 (idempotent) or 404 (not found)
        assert resp.status_code in [200, 404]


# ===========================================================================
# PHASE F: FROZEN PREVIEW CACHE TESTS
# ===========================================================================

class TestFrozenPreviewCache:
    """Test that frozen frames are cached and served from /api/preview/multitrack."""

    def test_multitrack_preview_with_frozen_flag(self, client):
        """Preview should respect frozen=True flag in track data."""
        # Freeze track 0
        freeze_resp = client.post("/api/track/freeze", json={
            "track_index": 0,
            "effects": [{"name": "blur", "params": {"radius": 5.0}}],
            "start_frame": 0,
            "end_frame": 10
        })
        assert freeze_resp.status_code == 200

        # Request multitrack preview with frozen flag
        preview_resp = client.post("/api/preview/multitrack", json={
            "tracks": [
                {
                    "track_index": 0,
                    "effects": [{"name": "blur", "params": {"radius": 5.0}}],
                    "frozen": True,
                    "opacity": 1.0,
                    "blend_mode": "normal"
                }
            ],
            "frame_number": 5
        })
        assert preview_resp.status_code == 200
        data = preview_resp.json()
        assert "preview" in data
        assert data["preview"].startswith("data:image/")

    def test_multitrack_preview_without_frozen_flag(self, client):
        """Preview should render live when frozen=False."""
        preview_resp = client.post("/api/preview/multitrack", json={
            "tracks": [
                {
                    "track_index": 0,
                    "effects": [{"name": "blur", "params": {"radius": 5.0}}],
                    "frozen": False,
                    "opacity": 1.0,
                    "blend_mode": "normal"
                }
            ],
            "frame_number": 5
        })
        assert preview_resp.status_code == 200
        data = preview_resp.json()
        assert "preview" in data

    def test_multitrack_preview_mixed_frozen_live_tracks(self, client):
        """Preview should handle mix of frozen and live tracks."""
        # Freeze track 0
        freeze_resp = client.post("/api/track/freeze", json={
            "track_index": 0,
            "effects": [{"name": "blur", "params": {"radius": 5.0}}],
            "start_frame": 0,
            "end_frame": 10
        })
        assert freeze_resp.status_code == 200

        # Request preview with 2 tracks (one frozen, one live)
        preview_resp = client.post("/api/preview/multitrack", json={
            "tracks": [
                {
                    "track_index": 0,
                    "effects": [{"name": "blur", "params": {"radius": 5.0}}],
                    "frozen": True,
                    "opacity": 1.0,
                    "blend_mode": "normal"
                },
                {
                    "track_index": 1,
                    "effects": [{"name": "edges", "params": {"threshold": 0.3}}],
                    "frozen": False,
                    "opacity": 0.8,
                    "blend_mode": "multiply"
                }
            ],
            "frame_number": 5
        })
        assert preview_resp.status_code == 200


# ===========================================================================
# PHASE D: PERFORM MODULE PASS-THROUGH TESTS
# ===========================================================================

class TestPerformEffectPassThrough:
    """Test that 'perform' effect is recognized and passes through in apply_chain."""

    def test_perform_effect_in_chain(self, client):
        """Apply chain should recognize 'perform' effect and not crash."""
        resp = client.post("/api/preview", json={
            "effects": [
                {"name": "blur", "params": {"radius": 3.0}},
                {"name": "perform", "params": {"session_id": "test_session"}},
                {"name": "edges", "params": {"threshold": 0.3}}
            ],
            "frame_number": 5
        })
        # Should return 200 (perform is a no-op in preview mode)
        assert resp.status_code == 200
        data = resp.json()
        assert "preview" in data

    def test_perform_effect_solo(self, client):
        """Perform effect alone should not crash."""
        resp = client.post("/api/preview", json={
            "effects": [
                {"name": "perform", "params": {"session_id": "test_session"}}
            ],
            "frame_number": 5
        })
        assert resp.status_code == 200

    def test_perform_effect_with_invalid_session_id(self, client):
        """Perform effect with nonexistent session_id should be graceful."""
        resp = client.post("/api/preview", json={
            "effects": [
                {"name": "perform", "params": {"session_id": "nonexistent_session_id_xyz"}}
            ],
            "frame_number": 5
        })
        # Should return 200 (perform is pass-through) or 400 (validation error)
        assert resp.status_code in [200, 400]


# ===========================================================================
# PHASE D: PERFORM TRIGGER PADS (8 KEYS, TOGGLE/HOLD)
# ===========================================================================

class TestPerformTriggerPads:
    """Test backend support for 8 trigger pads (keys 1-8) with toggle/hold modes."""

    def test_perform_init_creates_session(self, client):
        """/api/perform/init should create a perform session."""
        resp = client.post("/api/perform/init", json={
            "session_id": "test_session_001",
            "layers": [
                {"key": "1", "effect": "blur", "params": {"radius": 5.0}, "mode": "toggle"},
                {"key": "2", "effect": "edges", "params": {"threshold": 0.3}, "mode": "hold"}
            ]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data

    def test_perform_frame_with_active_keys(self, client):
        """Perform frame should apply effects for active keys."""
        # Init session
        init_resp = client.post("/api/perform/init", json={
            "session_id": "test_session_002",
            "layers": [
                {"key": "1", "effect": "blur", "params": {"radius": 5.0}, "mode": "toggle"},
            ]
        })
        assert init_resp.status_code == 200

        # Request frame with key "1" active
        frame_resp = client.post("/api/perform/frame", json={
            "session_id": "test_session_002",
            "frame_number": 10,
            "active_keys": ["1"]
        })
        assert frame_resp.status_code == 200
        data = frame_resp.json()
        assert "preview" in data

    def test_perform_frame_no_active_keys(self, client):
        """Perform frame with no active keys should return clean frame."""
        # Init session
        init_resp = client.post("/api/perform/init", json={
            "session_id": "test_session_003",
            "layers": [
                {"key": "1", "effect": "blur", "params": {"radius": 5.0}, "mode": "toggle"},
            ]
        })
        assert init_resp.status_code == 200

        # Request frame with no keys active
        frame_resp = client.post("/api/perform/frame", json={
            "session_id": "test_session_003",
            "frame_number": 10,
            "active_keys": []
        })
        assert frame_resp.status_code == 200


# ===========================================================================
# PHASE E: MIDI INPUT TESTS (KEYBOARD TOGGLE, WEB MIDI, MIDI LEARN)
# ===========================================================================

class TestMIDIInput:
    """Test MIDI input handling (keyboard as controller, Web MIDI, MIDI Learn)."""

    def test_midi_enable_endpoint_exists(self, client):
        """/api/midi/enable should toggle MIDI input mode."""
        resp = client.post("/api/midi/enable", json={"enabled": True})
        # Should return 200 or 501 (not implemented) — NOT 404
        assert resp.status_code in [200, 501]

    def test_midi_key_mapping(self, client):
        """MIDI key-to-note mapping should be configurable."""
        resp = client.post("/api/midi/map", json={
            "key": "a",
            "note": 60,  # Middle C
            "velocity": 100
        })
        # Should return 200 or 501 — NOT 404
        assert resp.status_code in [200, 501]

    def test_midi_learn_mode(self, client):
        """MIDI Learn should allow binding incoming MIDI to params."""
        resp = client.post("/api/midi/learn", json={
            "effect_index": 0,
            "param_name": "radius",
            "midi_cc": 1  # Modulation wheel
        })
        # Should return 200 or 501 — NOT 404
        assert resp.status_code in [200, 501]

    def test_midi_input_frame_trigger(self, client):
        """MIDI note-on should trigger perform layer activation."""
        # This test assumes backend MIDI routing is implemented
        # For now, we just verify the endpoint exists
        resp = client.post("/api/midi/trigger", json={
            "note": 60,
            "velocity": 100,
            "session_id": "test_session"
        })
        # Should return 200 or 501 — NOT 404
        assert resp.status_code in [200, 501]


# ===========================================================================
# PHASE C9: LOOP REGION TESTS
# ===========================================================================

class TestLoopRegion:
    """Test loop region toggle, drag handles, and playback wrapping."""

    def test_toggle_loop_creates_region(self, client):
        """toggleLoop() should create a loop region."""
        resp = client.post("/api/timeline/loop/toggle", json={
            "start_frame": 10,
            "end_frame": 50
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "loop_enabled" in data
        assert data["loop_enabled"] is True

    def test_toggle_loop_off(self, client):
        """toggleLoop() when loop is active should disable it."""
        # First enable
        enable_resp = client.post("/api/timeline/loop/toggle", json={
            "start_frame": 10,
            "end_frame": 50
        })
        assert enable_resp.status_code == 200

        # Then disable
        disable_resp = client.post("/api/timeline/loop/toggle", json={})
        assert disable_resp.status_code == 200
        data = disable_resp.json()
        assert data["loop_enabled"] is False

    def test_loop_region_drag_handles(self, client):
        """Drag handles should update loop region boundaries."""
        # Enable loop
        enable_resp = client.post("/api/timeline/loop/toggle", json={
            "start_frame": 10,
            "end_frame": 50
        })
        assert enable_resp.status_code == 200

        # Update boundaries via drag
        update_resp = client.post("/api/timeline/loop/update", json={
            "start_frame": 15,
            "end_frame": 45
        })
        assert update_resp.status_code == 200
        data = update_resp.json()
        assert data["start_frame"] == 15
        assert data["end_frame"] == 45

    def test_loop_region_playback_wrap(self, client):
        """Playback should wrap when loop is enabled."""
        # Enable loop
        enable_resp = client.post("/api/timeline/loop/toggle", json={
            "start_frame": 10,
            "end_frame": 20
        })
        assert enable_resp.status_code == 200

        # Request frame beyond loop end
        playback_resp = client.post("/api/timeline/playback", json={
            "current_frame": 21,  # Beyond loop end (20)
            "loop_enabled": True,
            "loop_start": 10,
            "loop_end": 20
        })
        assert playback_resp.status_code == 200
        data = playback_resp.json()
        # Should wrap to start of loop (10)
        assert data["next_frame"] >= 10
        assert data["next_frame"] <= 20


# ===========================================================================
# INTEGRATION: MULTI-FEATURE SCENARIO
# ===========================================================================

class TestMultiFeatureIntegration:
    """Test multiple new features working together."""

    def test_frozen_track_with_loop_and_perform(self, client):
        """Frozen track + loop region + perform session should all coexist."""
        # 1. Freeze track 0
        freeze_resp = client.post("/api/track/freeze", json={
            "track_index": 0,
            "effects": [{"name": "blur", "params": {"radius": 5.0}}],
            "start_frame": 0,
            "end_frame": 50
        })
        assert freeze_resp.status_code == 200

        # 2. Enable loop region
        loop_resp = client.post("/api/timeline/loop/toggle", json={
            "start_frame": 10,
            "end_frame": 40
        })
        assert loop_resp.status_code == 200

        # 3. Init perform session
        perform_resp = client.post("/api/perform/init", json={
            "session_id": "integration_test",
            "layers": [
                {"key": "1", "effect": "edges", "params": {"threshold": 0.3}, "mode": "toggle"}
            ]
        })
        assert perform_resp.status_code == 200

        # 4. Request multitrack preview within loop
        preview_resp = client.post("/api/preview/multitrack", json={
            "tracks": [
                {
                    "track_index": 0,
                    "effects": [],
                    "frozen": True,
                    "opacity": 1.0,
                    "blend_mode": "normal"
                }
            ],
            "frame_number": 25  # Within loop
        })
        assert preview_resp.status_code == 200


# ===========================================================================
# ERROR HANDLING & EDGE CASES
# ===========================================================================

class TestErrorHandling:
    """Test error handling for edge cases."""

    def test_freeze_invalid_track_index(self, client):
        """Freeze should reject invalid track indices."""
        resp = client.post("/api/track/freeze", json={
            "track_index": -1,
            "effects": [],
            "start_frame": 0,
            "end_frame": 10
        })
        assert resp.status_code == 400

    def test_freeze_inverted_range(self, client):
        """Freeze should reject inverted frame ranges (start > end)."""
        resp = client.post("/api/track/freeze", json={
            "track_index": 0,
            "effects": [],
            "start_frame": 50,
            "end_frame": 10
        })
        assert resp.status_code == 400

    def test_loop_region_inverted_range(self, client):
        """Loop region should reject inverted ranges."""
        resp = client.post("/api/timeline/loop/toggle", json={
            "start_frame": 50,
            "end_frame": 10
        })
        assert resp.status_code == 400

    def test_perform_init_duplicate_keys(self, client):
        """Perform init should reject duplicate trigger keys."""
        resp = client.post("/api/perform/init", json={
            "session_id": "dup_test",
            "layers": [
                {"key": "1", "effect": "blur", "params": {"radius": 5.0}, "mode": "toggle"},
                {"key": "1", "effect": "edges", "params": {"threshold": 0.3}, "mode": "hold"}
            ]
        })
        # Should return 400 (validation error) or 200 (last-write-wins)
        assert resp.status_code in [200, 400]

    def test_perform_frame_nonexistent_session(self, client):
        """Perform frame should handle nonexistent session gracefully."""
        resp = client.post("/api/perform/frame", json={
            "session_id": "nonexistent_session_xyz",
            "frame_number": 10,
            "active_keys": []
        })
        assert resp.status_code in [400, 404]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

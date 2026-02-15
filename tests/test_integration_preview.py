#!/usr/bin/env python3
"""
Integration tests for the Entropic preview endpoint.

These tests start the ACTUAL server, upload a REAL video, and call /api/preview
with various effects — testing the exact code path users hit in the web UI.

This is what unit tests miss: the server.py → apply_chain → effect pipeline.
"""

import os
import sys
import time
import base64
import subprocess
import signal
import json
import requests

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

SERVER_URL = "http://127.0.0.1:7861"  # Use non-default port to avoid conflicts
TEST_VIDEO = os.path.join(PROJECT_ROOT, "test-videos", "clips", "synth_testcard_clip.mp4")
TIMEOUT = 10  # seconds per request

# Effects that were reported broken in UAT
BROKEN_EFFECTS_UAT = [
    # B3-B9: Physics effects (were broken due to frame_index, supposedly fixed)
    {"name": "pixelhaunt", "params": {}},
    {"name": "pixelliquify", "params": {}},
    {"name": "pixeltimewarp", "params": {}},
    # B10-B13: Other broken effects
    {"name": "bytecorrupt", "params": {"amount": 50}},
    {"name": "flowdistort", "params": {"strength": 3.0}},
    {"name": "autolevels", "params": {}},
    {"name": "histogrameq", "params": {}},
]

# Physics effects that need multi-frame accumulation — minimal change on single frame is EXPECTED
# These are NOT broken; they simply need many frames of state to produce visible results
ACCUMULATIVE_EFFECTS = [
    {"name": "pixelgravity", "params": {}},
    {"name": "pixelinkdrop", "params": {}},
    {"name": "pixelmelt", "params": {}},
    {"name": "pixelvortex", "params": {}},
]

# Effects that work well — use as control group
WORKING_EFFECTS = [
    {"name": "pixelsort", "params": {"threshold": 0.5}},
    {"name": "blur", "params": {"radius": 5.0}},
    {"name": "edges", "params": {"threshold": 0.3}},
    {"name": "noise", "params": {"amount": 0.3}},
    {"name": "asciiart", "params": {}},
]

# Parameter bug effects — test specific params
PARAM_BUG_EFFECTS = [
    # P2: Pixel magnetic — poles/damping/rotation should do something
    {"name": "pixelmagnetic", "params": {"poles": 1}},
    {"name": "pixelmagnetic", "params": {"poles": 5}},
    {"name": "pixelmagnetic", "params": {"damping": 0.1}},
    {"name": "pixelmagnetic", "params": {"damping": 0.9}},
    # P3: Pixel quantum — uncertainty/superposition should vary
    {"name": "pixelquantum", "params": {"uncertainty": 0.1}},
    {"name": "pixelquantum", "params": {"uncertainty": 0.9}},
    # P4: Pixel elastic — high mass should still work
    {"name": "pixelelastic", "params": {"mass": 0.1}},
    {"name": "pixelelastic", "params": {"mass": 5.0}},
    {"name": "pixelelastic", "params": {"mass": 50.0}},
]


def start_server():
    """Start the Entropic server on a test port."""
    env = os.environ.copy()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server:app",
         "--host", "127.0.0.1", "--port", "7861", "--log-level", "warning"],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait for server to be ready
    for _ in range(30):
        try:
            r = requests.get(f"{SERVER_URL}/api/effects", timeout=2)
            if r.status_code == 200:
                return proc
        except requests.ConnectionError:
            pass
        time.sleep(0.5)
    proc.kill()
    raise RuntimeError("Server failed to start within 15 seconds")


def stop_server(proc):
    """Gracefully stop the server."""
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def upload_video(video_path):
    """Upload a test video to the server."""
    with open(video_path, "rb") as f:
        r = requests.post(
            f"{SERVER_URL}/api/upload",
            files={"file": ("test.mp4", f, "video/mp4")},
            timeout=TIMEOUT,
        )
    assert r.status_code == 200, f"Upload failed: {r.status_code} {r.text}"
    return r.json()


def preview_effect(effects_list, frame_number=5):
    """Call the preview endpoint with an effect chain."""
    r = requests.post(
        f"{SERVER_URL}/api/preview",
        json={"effects": effects_list, "frame_number": frame_number, "mix": 1.0},
        timeout=TIMEOUT,
    )
    return r


def decode_preview(data_url):
    """Decode a data URL to raw image bytes and return dimensions."""
    # data:image/jpeg;base64,/9j/...
    header, b64data = data_url.split(",", 1)
    img_bytes = base64.b64decode(b64data)
    from PIL import Image
    from io import BytesIO
    img = Image.open(BytesIO(img_bytes))
    return img


def get_baseline_frame(frame_number=5):
    """Get a preview with no effects (original frame)."""
    r = preview_effect([], frame_number)
    assert r.status_code == 200
    return decode_preview(r.json()["preview"])


def images_differ(img1, img2, threshold=1.0):
    """Check if two images are meaningfully different."""
    import numpy as np
    arr1 = np.array(img1).astype(float)
    arr2 = np.array(img2).astype(float)
    # Handle size mismatch
    if arr1.shape != arr2.shape:
        return True  # Different sizes = different
    mean_diff = np.abs(arr1 - arr2).mean()
    return mean_diff > threshold, mean_diff


def params_differ(effect_name, params_a, params_b, frame_number=5):
    """Check if changing parameters actually changes the output."""
    r1 = preview_effect([{"name": effect_name, "params": params_a}], frame_number)
    r2 = preview_effect([{"name": effect_name, "params": params_b}], frame_number)
    if r1.status_code != 200 or r2.status_code != 200:
        return None, f"Request failed: {r1.status_code}, {r2.status_code}"
    img1 = decode_preview(r1.json()["preview"])
    img2 = decode_preview(r2.json()["preview"])
    differs, mean_diff = images_differ(img1, img2)
    return differs, mean_diff


def run_tests():
    """Run all integration tests."""
    results = {"passed": 0, "failed": 0, "errors": 0, "details": []}

    print(f"\n{'='*60}")
    print("ENTROPIC INTEGRATION TEST — Real Server, Real Video")
    print(f"{'='*60}\n")

    # Start server
    print("[SETUP] Starting server...")
    proc = start_server()
    print("[SETUP] Server started on port 7861")

    try:
        # Upload test video
        print(f"[SETUP] Uploading {os.path.basename(TEST_VIDEO)}...")
        info = upload_video(TEST_VIDEO)
        print(f"[SETUP] Video loaded: {info.get('total_frames', '?')} frames\n")

        # Get baseline (no effects)
        baseline = get_baseline_frame()
        print(f"[BASELINE] Original frame: {baseline.size}")

        # === TEST 1: Known-working effects (control group) ===
        print(f"\n--- Control Group (should all pass) ---")
        for effect in WORKING_EFFECTS:
            name = effect["name"]
            try:
                r = preview_effect([effect])
                if r.status_code != 200:
                    print(f"  FAIL  {name}: HTTP {r.status_code}")
                    results["failed"] += 1
                    results["details"].append({"effect": name, "status": "FAIL", "reason": f"HTTP {r.status_code}"})
                    continue
                img = decode_preview(r.json()["preview"])
                differs, mean_diff = images_differ(baseline, img)
                if differs:
                    print(f"  PASS  {name}: mean_diff={mean_diff:.1f}")
                    results["passed"] += 1
                    results["details"].append({"effect": name, "status": "PASS", "mean_diff": round(mean_diff, 1)})
                else:
                    print(f"  FAIL  {name}: No visible change (mean_diff={mean_diff:.1f})")
                    results["failed"] += 1
                    results["details"].append({"effect": name, "status": "FAIL", "reason": f"No change, diff={mean_diff:.1f}"})
            except Exception as e:
                print(f"  ERROR {name}: {e}")
                results["errors"] += 1
                results["details"].append({"effect": name, "status": "ERROR", "reason": str(e)})

        # === TEST 2: Previously broken effects ===
        print(f"\n--- Previously Broken (UAT bugs B3-B13) ---")
        for effect in BROKEN_EFFECTS_UAT:
            name = effect["name"]
            try:
                r = preview_effect([effect])
                if r.status_code != 200:
                    print(f"  FAIL  {name}: HTTP {r.status_code}")
                    results["failed"] += 1
                    results["details"].append({"effect": name, "status": "FAIL", "reason": f"HTTP {r.status_code}"})
                    continue
                img = decode_preview(r.json()["preview"])
                differs, mean_diff = images_differ(baseline, img)
                if differs:
                    print(f"  PASS  {name}: mean_diff={mean_diff:.1f}")
                    results["passed"] += 1
                    results["details"].append({"effect": name, "status": "PASS", "mean_diff": round(mean_diff, 1)})
                else:
                    print(f"  FAIL  {name}: No visible change (mean_diff={mean_diff:.1f})")
                    results["failed"] += 1
                    results["details"].append({"effect": name, "status": "FAIL", "reason": f"No change, diff={mean_diff:.1f}"})
            except Exception as e:
                print(f"  ERROR {name}: {e}")
                results["errors"] += 1
                results["details"].append({"effect": name, "status": "ERROR", "reason": str(e)})

        # === TEST 3: Parameter responsiveness ===
        print(f"\n--- Parameter Bug Tests (P2/P3/P4) ---")
        param_tests = [
            ("pixelmagnetic", {"poles": 1}, {"poles": 5}, "poles param"),
            ("pixelmagnetic", {"damping": 0.1}, {"damping": 0.9}, "damping param"),
            ("pixelquantum", {"uncertainty": 0.1}, {"uncertainty": 0.9}, "uncertainty param"),
            ("pixelelastic", {"mass": 0.1}, {"mass": 5.0}, "low vs mid mass"),
            ("pixelelastic", {"mass": 0.1}, {"mass": 50.0}, "low vs high mass"),
        ]
        for effect_name, params_a, params_b, desc in param_tests:
            try:
                differs, result = params_differ(effect_name, params_a, params_b)
                if differs is None:
                    print(f"  ERROR {effect_name} ({desc}): {result}")
                    results["errors"] += 1
                elif differs:
                    print(f"  PASS  {effect_name} ({desc}): params change output, diff={result:.1f}")
                    results["passed"] += 1
                else:
                    print(f"  FAIL  {effect_name} ({desc}): params have NO effect, diff={result:.1f}")
                    results["failed"] += 1
                    results["details"].append({"effect": effect_name, "status": "FAIL", "reason": f"{desc} dead, diff={result:.1f}"})
            except Exception as e:
                print(f"  ERROR {effect_name} ({desc}): {e}")
                results["errors"] += 1

        # === TEST 4: Accumulative physics effects (pass = no crash) ===
        print(f"\n--- Accumulative Effects (pass = HTTP 200, no crash) ---")
        for effect in ACCUMULATIVE_EFFECTS:
            name = effect["name"]
            try:
                r = preview_effect([effect])
                if r.status_code == 200:
                    img = decode_preview(r.json()["preview"])
                    _, mean_diff = images_differ(baseline, img)
                    print(f"  PASS  {name}: HTTP 200 (mean_diff={mean_diff:.1f}, low diff expected)")
                    results["passed"] += 1
                else:
                    print(f"  FAIL  {name}: HTTP {r.status_code}")
                    results["failed"] += 1
            except Exception as e:
                print(f"  ERROR {name}: {e}")
                results["errors"] += 1

        # === TEST 5: Effect chain (combo) ===
        print(f"\n--- Effect Chain Test ---")
        try:
            chain = [
                {"name": "blur", "params": {"radius": 3.0}},
                {"name": "pixelsort", "params": {"threshold": 0.5}},
            ]
            r = preview_effect(chain)
            if r.status_code == 200:
                img = decode_preview(r.json()["preview"])
                differs, mean_diff = images_differ(baseline, img)
                if differs:
                    print(f"  PASS  blur→pixelsort chain: mean_diff={mean_diff:.1f}")
                    results["passed"] += 1
                else:
                    print(f"  FAIL  chain produced no change")
                    results["failed"] += 1
            else:
                print(f"  FAIL  chain: HTTP {r.status_code}")
                results["failed"] += 1
        except Exception as e:
            print(f"  ERROR chain: {e}")
            results["errors"] += 1

        # === TEST 6: Automation lane engine (backend) ===
        print(f"\n--- Automation Lane Engine ---")
        try:
            from core.automation import AutomationLane, AutomationSession
            lane = AutomationLane(0, "intensity")
            lane.add_keyframe(0, 0.0)
            lane.add_keyframe(30, 1.0)
            lane.add_keyframe(60, 0.5)

            # Test interpolation at various points
            v0 = lane.get_value(0)
            v15 = lane.get_value(15)
            v30 = lane.get_value(30)
            v45 = lane.get_value(45)
            v60 = lane.get_value(60)

            assert v0 == 0.0, f"Frame 0 should be 0.0, got {v0}"
            assert 0.4 < v15 < 0.6, f"Frame 15 should be ~0.5, got {v15}"
            assert v30 == 1.0, f"Frame 30 should be 1.0, got {v30}"
            assert 0.7 < v45 < 0.8, f"Frame 45 should be ~0.75, got {v45}"
            assert v60 == 0.5, f"Frame 60 should be 0.5, got {v60}"
            print(f"  PASS  AutomationLane interpolation: 5/5 checkpoints correct")
            results["passed"] += 1

            # Test bezier curve
            lane_b = AutomationLane(0, "blur_radius")
            lane_b.add_keyframe(0, 0.0, curve="bezier", cp1=(0.42, 0.0), cp2=(0.58, 1.0))
            lane_b.add_keyframe(30, 1.0)
            v_mid = lane_b.get_value(15)
            assert 0.0 < v_mid < 1.0, f"Bezier midpoint should be between 0 and 1, got {v_mid}"
            print(f"  PASS  Bezier interpolation: midpoint={v_mid:.3f}")
            results["passed"] += 1

            # Test session apply_to_chain
            session = AutomationSession()
            s_lane = session.add_lane(0, "intensity")
            s_lane.add_keyframe(0, 0.0)
            s_lane.add_keyframe(30, 1.0)
            s_lane.add_keyframe(60, 0.5)
            test_chain = [{"name": "blur", "params": {"intensity": 0.0}}]
            applied = session.apply_to_chain(test_chain, 30)
            assert applied[0]["params"]["intensity"] == 1.0, f"apply_to_chain should set intensity to 1.0 at frame 30"
            print(f"  PASS  AutomationSession.apply_to_chain works")
            results["passed"] += 1

            # Test bake_lane
            baked = session.bake_lane(0, "intensity", 0, 10)
            assert len(baked) == 11, f"bake_lane should return 11 frames, got {len(baked)}"
            assert baked[0] == (0, 0.0)
            print(f"  PASS  bake_lane: {len(baked)} frames baked")
            results["passed"] += 1

            # Test to_dict/from_dict roundtrip
            d = lane.to_dict()
            lane2 = AutomationLane.from_dict(d)
            assert lane2.get_value(15) == lane.get_value(15), "Roundtrip serialization failed"
            print(f"  PASS  to_dict/from_dict roundtrip")
            results["passed"] += 1

        except Exception as e:
            print(f"  ERROR Automation engine: {e}")
            results["errors"] += 1

        # === TEST 7: Freeze endpoint ===
        print(f"\n--- Freeze Endpoint ---")
        try:
            # Test freeze endpoint exists and validates
            r = requests.post(
                f"{SERVER_URL}/api/timeline/freeze",
                json={"region_id": "test_nonexistent", "effects": [], "start_frame": 0, "end_frame": 10},
                timeout=TIMEOUT,
            )
            # Should return 200 (processes) or 422 (validation) — NOT 404
            assert r.status_code != 404, f"Freeze endpoint not found (404)"
            print(f"  PASS  Freeze endpoint exists: HTTP {r.status_code}")
            results["passed"] += 1

            # Test unfreeze endpoint
            r2 = requests.delete(
                f"{SERVER_URL}/api/timeline/freeze/test_nonexistent",
                timeout=TIMEOUT,
            )
            assert r2.status_code != 404, f"Unfreeze endpoint not found (404)"
            print(f"  PASS  Unfreeze endpoint exists: HTTP {r2.status_code}")
            results["passed"] += 1

        except Exception as e:
            print(f"  ERROR Freeze endpoint: {e}")
            results["errors"] += 1

        # === TEST 8: Control-map.json essential arrays ===
        print(f"\n--- Control Map (Parameter Accordion) ---")
        try:
            import json as jsonlib
            cmap_path = os.path.join(PROJECT_ROOT, "ui", "static", "control-map.json")
            with open(cmap_path) as f:
                cmap = jsonlib.load(f)
            effects = cmap.get("effects", {})
            total = len(effects)
            with_essential = sum(1 for e in effects.values() if "essential" in e)
            print(f"  INFO  {total} effects in control-map.json, {with_essential} have essential arrays")
            assert total >= 40, f"Expected 40+ effects, got {total}"
            assert with_essential >= 40, f"Expected 40+ with essential arrays, got {with_essential}"
            # Verify essential arrays are non-empty subsets of params
            for name, data in effects.items():
                ess = data.get("essential", [])
                assert isinstance(ess, list), f"{name}: essential is not a list"
                assert len(ess) > 0, f"{name}: essential array is empty"
            print(f"  PASS  All {with_essential} effects have valid essential arrays")
            results["passed"] += 1
        except Exception as e:
            print(f"  ERROR Control map: {e}")
            results["errors"] += 1

    finally:
        print(f"\n[TEARDOWN] Stopping server...")
        stop_server(proc)

    # Summary
    total = results["passed"] + results["failed"] + results["errors"]
    print(f"\n{'='*60}")
    print(f"RESULTS: {results['passed']}/{total} passed, "
          f"{results['failed']} failed, {results['errors']} errors")
    print(f"{'='*60}")

    # Write results to JSON for other tools to consume
    results_path = os.path.join(PROJECT_ROOT, "tests", "integration-results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results: {results_path}")

    return results["failed"] == 0 and results["errors"] == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

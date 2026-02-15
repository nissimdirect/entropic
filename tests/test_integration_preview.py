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
    {"name": "pixelgravity", "params": {}},
    {"name": "pixelhaunt", "params": {}},
    {"name": "pixelinkdrop", "params": {}},
    {"name": "pixelliquify", "params": {}},
    {"name": "pixelmelt", "params": {}},
    {"name": "pixeltimewarp", "params": {}},
    {"name": "pixelvortex", "params": {}},
    # B10-B13: Other broken effects
    {"name": "bytecorrupt", "params": {"intensity": 0.5}},
    {"name": "flowdistort", "params": {"intensity": 0.5}},
    {"name": "autolevels", "params": {}},
    {"name": "histogrameq", "params": {}},
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

        # === TEST 4: Effect chain (combo) ===
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

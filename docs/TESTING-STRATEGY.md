# Entropic Testing Strategy — Outcome-Based Visual Testing

> **Problem:** 652 unit tests all pass, but 14 effects are broken in the actual web UI. Tests validate CODE, not OUTCOMES.
> **Goal:** A testing suite that catches visual regressions, parameter dead zones, and UX failures — so the USER doesn't have to.
> **Key insight from user:** "I want you to really think about how we can implement a more comprehensive testing plan where these things are being checked so I don't have to all the time."

---

## Testing Pyramid for Visual Software

```
           /\
          /  \  Manual UAT
         /    \  (User clicks around — catches UX, feel, workflow)
        /──────\
       /        \  Visual Regression Tests
      /          \  (Automated screenshot comparison — catches rendering changes)
     /────────────\
    /              \  Integration Tests
   /                \  (API endpoint → full effect chain — catches pipeline bugs)
  /──────────────────\
 /                    \  Unit Tests (existing 652)
/______________________\  (Function → output — catches logic bugs)
```

**What we have:** Bottom layer only (unit tests).
**What we need:** All 4 layers.

---

## Layer 1: Visual Diff Testing (Image Comparison)

### Concept
For every effect, maintain a "golden" reference image. On every code change, re-render the effect and compare to the golden image. If the diff exceeds a threshold, the test fails.

This catches:
- Effects that stop working (diff = 100% because output = input)
- Parameter changes that alter output unexpectedly
- Regressions from refactoring

### Implementation

```python
# tests/test_visual.py

import numpy as np
import pytest
from pathlib import Path
from effects import apply_effect, EFFECTS
from PIL import Image

GOLDEN_DIR = Path("tests/golden")
REFERENCE_IMAGE = np.array(Image.open("tests/fixtures/reference_720p.jpg"))

# Effects that are stateful and need frame_index > 0 to show results
STATEFUL_EFFECTS = {
    "pixelliquify", "pixelgravity", "pixelvortex", "pixelexplode",
    "pixelelastic", "pixelmelt", "pixelblackhole", "pixelantigravity",
    "pixelmagnetic", "pixeltimewarp", "pixeldimensionfold", "pixelwormhole",
    "pixelquantum", "pixeldarkenergy", "pixelsuperfluid", "pixelbubbles",
    "pixelinkdrop", "pixelhaunt", "stutter", "feedback", "tapestop",
    "delay", "decimator", "samplehold", "granulator", "beatrepeat",
    "spectralfreeze", "visualreverb", "videoflanger", "videophaser",
    "spatialflanger", "channelphaser", "brightnessphaser", "hueflanger",
    "resonantfilter", "combfilter", "feedbackphaser", "freqflanger",
    "sidechainduck", "sidechainpump", "sidechaingate", "datamosh",
}

# Effects that need key_frame
KEY_FRAME_EFFECTS = {"sidechaincross", "sidechaincrossfeed", "sidechaininterference"}

# Video-level effects (skip)
SKIP_EFFECTS = {"realdatamosh"}


def compute_image_diff(a: np.ndarray, b: np.ndarray) -> float:
    """Compute normalized mean absolute difference between two frames.
    Returns 0.0 (identical) to 1.0 (completely different).
    """
    return float(np.mean(np.abs(a.astype(float) - b.astype(float))) / 255.0)


def compute_ssim_approx(a: np.ndarray, b: np.ndarray) -> float:
    """Approximate Structural Similarity Index. 1.0 = identical."""
    a_f = a.astype(float)
    b_f = b.astype(float)
    mu_a, mu_b = np.mean(a_f), np.mean(b_f)
    var_a, var_b = np.var(a_f), np.var(b_f)
    cov = np.mean((a_f - mu_a) * (b_f - mu_b))
    c1, c2 = 6.5025, 58.5225  # constants for 8-bit images
    ssim = ((2 * mu_a * mu_b + c1) * (2 * cov + c2)) / \
           ((mu_a**2 + mu_b**2 + c1) * (var_a + var_b + c2))
    return float(ssim)


class TestVisualEffects:
    """Visual regression tests — compare effect output to golden reference."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Ensure golden directory exists."""
        GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    @pytest.mark.parametrize("effect_name", sorted(EFFECTS.keys()))
    def test_effect_produces_visible_change(self, effect_name):
        """Every effect must produce a VISIBLE change from the input frame.

        This is the #1 test that would have caught the server.py:377 bug.
        If an effect returns the input frame unchanged, it's broken.
        """
        if effect_name in SKIP_EFFECTS:
            pytest.skip(f"{effect_name} is video-level")
        if effect_name in KEY_FRAME_EFFECTS:
            pytest.skip(f"{effect_name} needs key_frame")

        frame = REFERENCE_IMAGE.copy()

        if effect_name in STATEFUL_EFFECTS:
            # Stateful effects need multiple frames to build up state
            # Run 10 frames, check the last one
            for i in range(10):
                result = apply_effect(frame.copy(), effect_name,
                                      frame_index=i, total_frames=100)
            result = apply_effect(frame.copy(), effect_name,
                                  frame_index=10, total_frames=100)
        else:
            result = apply_effect(frame, effect_name,
                                  frame_index=5, total_frames=100)

        diff = compute_image_diff(frame, result)
        assert diff > 0.01, (
            f"Effect '{effect_name}' produced no visible change "
            f"(diff={diff:.4f}). Effect may be broken or parameters "
            f"may need adjustment."
        )

    @pytest.mark.parametrize("effect_name", sorted(EFFECTS.keys()))
    def test_effect_matches_golden(self, effect_name):
        """Compare effect output to golden reference. Fails if too different."""
        if effect_name in SKIP_EFFECTS:
            pytest.skip(f"{effect_name} is video-level")
        if effect_name in KEY_FRAME_EFFECTS:
            pytest.skip(f"{effect_name} needs key_frame")

        golden_path = GOLDEN_DIR / f"{effect_name}.npy"
        frame = REFERENCE_IMAGE.copy()

        if effect_name in STATEFUL_EFFECTS:
            for i in range(10):
                apply_effect(frame.copy(), effect_name,
                             frame_index=i, total_frames=100)
            result = apply_effect(frame.copy(), effect_name,
                                  frame_index=10, total_frames=100)
        else:
            result = apply_effect(frame, effect_name,
                                  frame_index=5, total_frames=100)

        if not golden_path.exists():
            # First run: save as golden reference
            np.save(golden_path, result)
            pytest.skip(f"Golden reference saved for {effect_name}")

        golden = np.load(golden_path)
        diff = compute_image_diff(golden, result)

        # Allow small differences (floating point, etc.)
        assert diff < 0.02, (
            f"Effect '{effect_name}' visual regression: diff={diff:.4f} "
            f"(threshold=0.02). Output has changed since golden was saved."
        )

    @pytest.mark.parametrize("effect_name", sorted(EFFECTS.keys()))
    def test_effect_preview_mode(self, effect_name):
        """Test effect in PREVIEW MODE (frame_index=0, total_frames=1).

        This simulates exactly what the web UI preview does.
        Stateful effects should still produce SOME change, not return
        the input frame unchanged. This is the test that catches
        the server.py:377 class of bugs.
        """
        if effect_name in SKIP_EFFECTS:
            pytest.skip(f"{effect_name} is video-level")
        if effect_name in KEY_FRAME_EFFECTS:
            pytest.skip(f"{effect_name} needs key_frame")

        frame = REFERENCE_IMAGE.copy()

        # This is EXACTLY what /api/preview does: frame_index=0, total_frames=1
        result = apply_effect(frame, effect_name,
                              frame_index=0, total_frames=1)

        diff = compute_image_diff(frame, result)

        if effect_name in STATEFUL_EFFECTS:
            # Stateful effects in preview mode should still show SOMETHING
            # (first frame of the effect, not the cleanup result)
            # Threshold is lower because first frame has less accumulated state
            assert diff > 0.001, (
                f"Stateful effect '{effect_name}' returned unchanged frame "
                f"in preview mode (diff={diff:.6f}). This means the cleanup "
                f"logic is nuking state on the first frame. CHECK: "
                f"'if frame_index >= total_frames - 1' should include "
                f"'and total_frames > 1'."
            )
        else:
            assert diff > 0.01, (
                f"Effect '{effect_name}' produced no change in preview mode."
            )
```

### Parameter Sensitivity Testing

```python
# tests/test_parameters.py

class TestParameterSensitivity:
    """Verify that changing parameters actually changes the output."""

    @pytest.mark.parametrize("effect_name", sorted(EFFECTS.keys()))
    def test_each_param_changes_output(self, effect_name):
        """For each parameter, verify that changing it changes the frame.

        This catches: dead seed params, non-functional sliders,
        parameters that are exposed but not wired to anything.
        """
        if effect_name in SKIP_EFFECTS:
            pytest.skip()

        entry = EFFECTS[effect_name]
        frame = REFERENCE_IMAGE.copy()
        base_params = entry["params"].copy()

        for param_name, default_value in base_params.items():
            if param_name in ("seed", "frame_index", "total_frames"):
                continue  # Test seeds separately
            if not isinstance(default_value, (int, float)):
                continue  # Skip non-numeric params

            # Render with default
            result_default = apply_effect(frame.copy(), effect_name,
                                          frame_index=5, total_frames=100,
                                          **base_params)

            # Render with modified param
            test_value = _get_test_value(default_value)
            modified_params = {**base_params, param_name: test_value}
            result_modified = apply_effect(frame.copy(), effect_name,
                                           frame_index=5, total_frames=100,
                                           **modified_params)

            diff = compute_image_diff(result_default, result_modified)

            # Every numeric parameter should produce at least SOME change
            assert diff > 0.001, (
                f"{effect_name}.{param_name}: changing from "
                f"{default_value} to {test_value} produced no visible "
                f"change (diff={diff:.6f}). Parameter may not be wired."
            )

    @pytest.mark.parametrize("effect_name", sorted(EFFECTS.keys()))
    def test_seed_changes_output(self, effect_name):
        """Verify that changing seed changes the output for effects that use it."""
        entry = EFFECTS[effect_name]
        if "seed" not in entry["params"]:
            pytest.skip(f"{effect_name} has no seed param")

        frame = REFERENCE_IMAGE.copy()
        params = entry["params"].copy()

        params["seed"] = 42
        result_a = apply_effect(frame.copy(), effect_name,
                                frame_index=5, total_frames=100, **params)

        params["seed"] = 999
        result_b = apply_effect(frame.copy(), effect_name,
                                frame_index=5, total_frames=100, **params)

        diff = compute_image_diff(result_a, result_b)

        assert diff > 0.001, (
            f"{effect_name}: changing seed from 42 to 999 produced "
            f"no visible change (diff={diff:.6f}). Seed param is dead."
        )


def _get_test_value(default_value):
    """Generate a meaningfully different test value."""
    if isinstance(default_value, float):
        if default_value == 0.0:
            return 0.5
        elif default_value >= 0.9:
            return default_value * 0.3
        else:
            return default_value * 2.0
    elif isinstance(default_value, int):
        if default_value == 0:
            return 5
        else:
            return max(1, default_value * 2)
    return default_value
```

---

## Layer 2: Integration Tests (API Endpoint Testing)

### What This Catches
- Effects that work in unit tests but fail through the server pipeline
- Missing parameter forwarding (the server.py:377 class of bugs)
- Response format issues, error handling gaps

```python
# tests/test_integration.py

import pytest
import httpx
from pathlib import Path

BASE_URL = "http://localhost:7860"


@pytest.fixture(scope="module")
def client():
    """HTTP client for the running Entropic server."""
    return httpx.Client(base_url=BASE_URL, timeout=30.0)


@pytest.fixture(scope="module")
def uploaded_video(client):
    """Upload a test video and return the video info."""
    video_path = Path("tests/fixtures/test_video_5s.mp4")
    if not video_path.exists():
        pytest.skip("Test video not found at tests/fixtures/test_video_5s.mp4")

    with open(video_path, "rb") as f:
        response = client.post("/api/upload", files={"file": f})

    assert response.status_code == 200, f"Upload failed: {response.text}"
    data = response.json()
    assert "total_frames" in data
    return data


class TestPreviewEndpoint:
    """Test /api/preview with various effects through the actual server."""

    def test_preview_stateless_effect(self, client, uploaded_video):
        """Stateless effect through preview endpoint should work."""
        response = client.post("/api/preview", json={
            "frame_number": 30,
            "effects": [{"name": "pixelsort", "params": {"threshold": 0.5}}],
            "mix": 1.0,
        })
        assert response.status_code == 200
        data = response.json()
        assert "preview" in data
        assert data["preview"].startswith("data:image/")

    def test_preview_stateful_effect(self, client, uploaded_video):
        """Stateful effect through preview endpoint must produce a change.

        THIS IS THE TEST THAT CATCHES THE server.py:377 BUG.
        """
        # Get unprocessed frame
        response_clean = client.post("/api/preview", json={
            "frame_number": 30,
            "effects": [],
            "mix": 1.0,
        })
        clean_data = response_clean.json()["preview"]

        # Get frame with stateful effect
        response_effect = client.post("/api/preview", json={
            "frame_number": 30,
            "effects": [{"name": "pixelliquify", "params": {
                "viscosity": 0.92, "turbulence": 3.0
            }}],
            "mix": 1.0,
        })
        effect_data = response_effect.json()["preview"]

        # The two should be DIFFERENT
        assert clean_data != effect_data, (
            "Stateful effect 'pixelliquify' returned same frame as "
            "no-effect preview. This means frame_index/total_frames "
            "are not being passed correctly to apply_chain()."
        )

    @pytest.mark.parametrize("effect_name", [
        "pixelliquify", "pixelgravity", "pixelvortex",
        "stutter", "feedback", "videoflanger",
    ])
    def test_preview_each_stateful_effect(self, client, uploaded_video, effect_name):
        """Each stateful effect must produce a visible change in preview."""
        response = client.post("/api/preview", json={
            "frame_number": 30,
            "effects": [{"name": effect_name, "params": {}}],
            "mix": 1.0,
        })
        assert response.status_code == 200
        # More rigorous: decode base64, compute diff against clean frame


class TestUploadEndpoint:
    """Test /api/upload error handling."""

    def test_upload_valid_video(self, client):
        """Valid video upload returns 200 with video info."""
        video_path = Path("tests/fixtures/test_video_5s.mp4")
        if not video_path.exists():
            pytest.skip()
        with open(video_path, "rb") as f:
            response = client.post("/api/upload", files={"file": f})
        assert response.status_code == 200

    def test_upload_invalid_file(self, client):
        """Invalid file upload returns error, not silent failure."""
        response = client.post("/api/upload",
                               files={"file": ("test.txt", b"not a video")})
        assert response.status_code != 200 or "error" in response.json()

    def test_upload_no_file(self, client):
        """Missing file returns 4xx, not 500."""
        response = client.post("/api/upload")
        assert 400 <= response.status_code < 500
```

---

## Layer 3: Visual Regression CI

### Concept
On every commit that touches `effects/` or `server.py`:
1. Run all visual diff tests
2. If any golden comparison fails, the commit is flagged
3. Developer reviews the diff images and either updates goldens or fixes the regression

### CI Script

```bash
#!/bin/bash
# tests/run_visual_tests.sh

echo "=== Entropic Visual Regression Tests ==="

# Start server in background
python server.py &
SERVER_PID=$!
sleep 3

# Run visual tests
pytest tests/test_visual.py tests/test_parameters.py -v --tb=short

# Run integration tests
pytest tests/test_integration.py -v --tb=short

# Cleanup
kill $SERVER_PID 2>/dev/null

echo "=== Done ==="
```

### Pre-Commit Hook

```bash
#!/bin/bash
# .githooks/pre-commit-visual

# Only run if effects code changed
CHANGED=$(git diff --cached --name-only | grep -E "^(effects/|server\.py|core/)")
if [ -z "$CHANGED" ]; then
    exit 0
fi

echo "Effects code changed — running visual regression tests..."
pytest tests/test_visual.py::TestVisualEffects::test_effect_produces_visible_change -x -q
if [ $? -ne 0 ]; then
    echo "VISUAL REGRESSION DETECTED. Fix the issue or update golden references."
    exit 1
fi
```

---

## The Image Diff on Parameter Changes (User's Idea)

User asked: "Have you thought about the image diff on parameters changing and being weighted against why a parameter changing would change the image?"

### Concept: Parameter Change Impact Score

For each parameter on each effect, compute a **change impact score** — how much does changing this parameter actually change the output?

```python
def compute_parameter_impact(effect_name: str, param_name: str,
                              frame: np.ndarray, steps: int = 11) -> dict:
    """
    Sweep a parameter through its range and measure visual impact at each step.

    Returns:
        {
            "param": "threshold",
            "impact_profile": [
                {"value": 0.0, "diff_from_prev": 0.0, "diff_from_base": 0.0},
                {"value": 0.1, "diff_from_prev": 0.02, "diff_from_base": 0.02},
                ...
            ],
            "dead_zones": [(0.0, 0.3)],      # ranges where diff < threshold
            "hot_zones": [(0.7, 0.9)],        # ranges where diff is highest
            "sweet_spot": (0.3, 0.7),          # recommended range
            "total_impact": 0.45,              # average diff across all steps
            "is_functional": True,             # does this param do ANYTHING?
        }
    """
```

### Weighting: Why Would a Parameter Change the Image?

The user's insight is profound: not all parameters SHOULD change the image by the same amount. A parameter change should be weighted against its EXPECTED impact:

| Parameter Type | Expected Impact | Example |
|---------------|----------------|---------|
| **Generator** | Creates the effect from scratch | `pixelsort.threshold` → changes which pixels sort |
| **Modulator** | Modifies an existing effect | `wave.amplitude` → changes wave height |
| **Seed** | Changes randomization | `noise.seed` → different noise pattern |
| **Mode selector** | Switches behavior entirely | `blur.blur_type` → box vs motion |
| **Compound dependency** | Only visible when combined | `sidechain.attack` → only visible during transitions |

```python
PARAM_TYPES = {
    "generator": {"min_expected_diff": 0.05, "description": "Creates/controls the core effect"},
    "modulator": {"min_expected_diff": 0.02, "description": "Modifies strength/character"},
    "seed": {"min_expected_diff": 0.01, "description": "Changes randomization pattern"},
    "mode": {"min_expected_diff": 0.03, "description": "Switches behavior mode"},
    "compound": {"min_expected_diff": 0.0, "description": "Only visible in combination"},
    "temporal": {"min_expected_diff": 0.0, "description": "Only visible across frames"},
}

# Tag each parameter with its type
PARAM_TYPE_MAP = {
    "pixelsort.threshold": "generator",
    "pixelsort.sort_by": "mode",
    "pixelsort.direction": "mode",
    "noise.amount": "generator",
    "noise.seed": "seed",
    "noise.noise_type": "mode",
    "wave.amplitude": "generator",
    "wave.frequency": "modulator",
    "sidechain_duck.attack": "compound",
    "sidechain_duck.release": "compound",
    "stutter.repeat": "temporal",
    # ... etc for all params
}


def test_parameter_impact_weighted(effect_name, param_name, frame):
    """Test that parameter impact matches its expected type."""
    param_type = PARAM_TYPE_MAP.get(f"{effect_name}.{param_name}", "generator")
    expected = PARAM_TYPES[param_type]["min_expected_diff"]

    impact = compute_parameter_impact(effect_name, param_name, frame)

    if param_type in ("compound", "temporal"):
        # These params may legitimately show no change on a single frame
        # Test them in multi-frame context instead
        return  # skip single-frame assertion

    assert impact["total_impact"] >= expected, (
        f"{effect_name}.{param_name} (type={param_type}): "
        f"expected diff >= {expected}, got {impact['total_impact']:.4f}. "
        f"Parameter may not be wired correctly."
    )
```

### Automated Parameter Audit Report

Run weekly or on every release:

```python
def generate_parameter_audit():
    """Generate a full parameter audit report across all effects.

    Outputs a markdown table showing:
    - Which params work (change output)
    - Which params are dead (no change)
    - Which params have dead zones (partial range functional)
    - Which seeds actually work
    """
    frame = load_reference_image()
    results = []

    for effect_name, entry in EFFECTS.items():
        if entry["fn"] is None:
            continue
        for param_name, default in entry["params"].items():
            if not isinstance(default, (int, float)):
                continue
            impact = compute_parameter_impact(effect_name, param_name, frame)
            results.append({
                "effect": effect_name,
                "param": param_name,
                "functional": impact["is_functional"],
                "dead_zones": impact["dead_zones"],
                "sweet_spot": impact["sweet_spot"],
                "total_impact": impact["total_impact"],
            })

    # Generate markdown report
    report = "# Parameter Audit Report\n\n"
    report += "| Effect | Parameter | Functional | Dead Zones | Sweet Spot | Impact |\n"
    report += "|--------|-----------|-----------|------------|------------|--------|\n"
    for r in results:
        status = "YES" if r["functional"] else "**NO**"
        report += f"| {r['effect']} | {r['param']} | {status} | {r['dead_zones']} | {r['sweet_spot']} | {r['total_impact']:.3f} |\n"

    Path("docs/PARAMETER-AUDIT.md").write_text(report)
```

---

## Testing Checklist for New Effects

When adding a new effect:

1. [ ] Unit test: effect produces visible change with default params
2. [ ] Unit test: each parameter changes output
3. [ ] Unit test: seed changes output (if seed param exists)
4. [ ] Unit test: boundary values (0, max, negative) don't crash
5. [ ] Integration test: effect works through /api/preview endpoint
6. [ ] Integration test: effect works in preview mode (frame_index=0, total_frames=1)
7. [ ] Visual regression: golden reference saved
8. [ ] Parameter audit: all params functional, dead zones documented
9. [ ] Manual test: open web UI, add effect, verify visually

**Rule:** No effect ships without all 9 checks passing.

---

## Implementation Order

1. **Create test fixtures** — reference_720p.jpg, test_video_5s.mp4
2. **Write test_visual.py** — `test_effect_produces_visible_change` for all 109 effects
3. **Run it** — identify which effects fail (this IS the automated seed/param audit)
4. **Write test_parameters.py** — parameter impact testing for all numeric params
5. **Write test_integration.py** — API endpoint tests with stateful effects
6. **Set up golden references** — save first-run outputs as goldens
7. **Add pre-commit hook** — visual tests on effects code changes
8. **Generate PARAMETER-AUDIT.md** — full audit report

**Estimated effort:** 1 session to build the framework, then it runs automatically forever.

---

*Testing strategy by Claude Code | Quality + Red Team + CTO perspectives | 2026-02-15*

"""
Entropic -- Parameter Automation Engine

Automates effect parameters over time (frame-by-frame).
Each automation lane controls one parameter of one effect in the chain.

Data model:
    AutomationLane: keyframes + curve type for a single parameter
    AutomationSession: collection of lanes for a full chain
    AutomationRecorder: records parameter changes during playback

Usage (in render loop):
    session = AutomationSession()
    session.add_lane(effect_idx=0, param="threshold", keyframes=[(0, 0.5), (30, 1.0)])

    for frame_idx in range(total_frames):
        overrides = session.get_values(frame_idx, total_frames)
        # overrides = {0: {"threshold": 0.72}, 2: {"intensity": 0.3}}
        # Apply overrides to chain before processing
"""

import math
import json
from pathlib import Path


# ─── Interpolation curves ───────────────────────────────────────────

def _lerp(a, b, t):
    """Linear interpolation."""
    return a + (b - a) * t


def _ease_in(a, b, t):
    """Quadratic ease-in."""
    return a + (b - a) * t * t


def _ease_out(a, b, t):
    """Quadratic ease-out."""
    return a + (b - a) * (1.0 - (1.0 - t) ** 2)


def _ease_in_out(a, b, t):
    """Quadratic ease-in-out."""
    if t < 0.5:
        return a + (b - a) * 2.0 * t * t
    return a + (b - a) * (1.0 - (-2.0 * t + 2.0) ** 2 / 2.0)


def _step(a, b, t):
    """Step (hold previous value until next keyframe)."""
    return a


def _sine(a, b, t):
    """Sinusoidal interpolation."""
    return a + (b - a) * (1.0 - math.cos(t * math.pi)) / 2.0


CURVES = {
    "linear": _lerp,
    "ease_in": _ease_in,
    "ease_out": _ease_out,
    "ease_in_out": _ease_in_out,
    "step": _step,
    "sine": _sine,
}


# ─── Automation Lane ────────────────────────────────────────────────

class AutomationLane:
    """A single parameter's automation: keyframes + interpolation curve.

    Keyframes: [(frame_index, value), ...]
    Frames are absolute (0 = first frame of video).
    """

    def __init__(self, effect_idx, param_name, keyframes=None, curve="linear"):
        self.effect_idx = effect_idx
        self.param_name = param_name
        self.keyframes = sorted(keyframes or [], key=lambda kf: kf[0])
        self.curve = curve

    def add_keyframe(self, frame, value):
        """Add or update a keyframe at the given frame."""
        # Remove existing keyframe at this frame
        self.keyframes = [kf for kf in self.keyframes if kf[0] != frame]
        self.keyframes.append((frame, value))
        self.keyframes.sort(key=lambda kf: kf[0])

    def remove_keyframe(self, frame):
        """Remove keyframe at exact frame."""
        self.keyframes = [kf for kf in self.keyframes if kf[0] != frame]

    def get_value(self, frame):
        """Get interpolated value at a frame. Returns None if no keyframes."""
        if not self.keyframes:
            return None

        # Before first keyframe: hold first value
        if frame <= self.keyframes[0][0]:
            return self.keyframes[0][1]

        # After last keyframe: hold last value
        if frame >= self.keyframes[-1][0]:
            return self.keyframes[-1][1]

        # Find surrounding keyframes
        for i in range(len(self.keyframes) - 1):
            f0, v0 = self.keyframes[i]
            f1, v1 = self.keyframes[i + 1]
            if f0 <= frame <= f1:
                if f1 == f0:
                    return v0
                t = (frame - f0) / (f1 - f0)
                interp = CURVES.get(self.curve, _lerp)
                return interp(v0, v1, t)

        return self.keyframes[-1][1]

    def to_dict(self):
        return {
            "effect_idx": self.effect_idx,
            "param": self.param_name,
            "keyframes": self.keyframes,
            "curve": self.curve,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            effect_idx=d["effect_idx"],
            param_name=d["param"],
            keyframes=[tuple(kf) for kf in d["keyframes"]],
            curve=d.get("curve", "linear"),
        )


# ─── Automation Session ─────────────────────────────────────────────

class AutomationSession:
    """Collection of automation lanes for a full effect chain."""

    def __init__(self):
        self.lanes = []

    def add_lane(self, effect_idx, param_name, keyframes=None, curve="linear"):
        """Add a new automation lane."""
        lane = AutomationLane(effect_idx, param_name, keyframes, curve)
        self.lanes.append(lane)
        return lane

    def get_lane(self, effect_idx, param_name):
        """Find a lane by effect index and parameter name."""
        for lane in self.lanes:
            if lane.effect_idx == effect_idx and lane.param_name == param_name:
                return lane
        return None

    def remove_lane(self, effect_idx, param_name):
        """Remove a lane."""
        self.lanes = [l for l in self.lanes
                      if not (l.effect_idx == effect_idx and l.param_name == param_name)]

    def get_values(self, frame):
        """Get all automated parameter values at a frame.

        Returns: {effect_idx: {param_name: value, ...}, ...}
        Only includes parameters that have automation at this frame.
        """
        overrides = {}
        for lane in self.lanes:
            val = lane.get_value(frame)
            if val is not None:
                if lane.effect_idx not in overrides:
                    overrides[lane.effect_idx] = {}
                overrides[lane.effect_idx][lane.param_name] = val
        return overrides

    def apply_to_chain(self, effects_list, frame):
        """Return a modified effects list with automated values applied.

        Does NOT mutate the original list — returns a new list.
        """
        overrides = self.get_values(frame)
        if not overrides:
            return effects_list

        result = []
        for i, effect in enumerate(effects_list):
            if i in overrides:
                new_params = {**effect.get("params", {}), **overrides[i]}
                result.append({**effect, "params": new_params})
            else:
                result.append(effect)
        return result

    def to_dict(self):
        return {"lanes": [l.to_dict() for l in self.lanes]}

    @classmethod
    def from_dict(cls, d):
        session = cls()
        for lane_data in d.get("lanes", []):
            session.lanes.append(AutomationLane.from_dict(lane_data))
        return session

    def save(self, path):
        """Save automation to JSON file."""
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path):
        """Load automation from JSON file."""
        data = json.loads(Path(path).read_text())
        return cls.from_dict(data)


# ─── Automation Recorder ────────────────────────────────────────────

class AutomationRecorder:
    """Records parameter changes during playback for later automation.

    Usage:
        recorder = AutomationRecorder()
        recorder.start()

        # During playback, when user moves a knob:
        recorder.record(frame_index=15, effect_idx=0, param="threshold", value=0.8)

        recorder.stop()
        session = recorder.to_session(simplify=True)
    """

    def __init__(self):
        self.recording = False
        self.events = []  # [(frame, effect_idx, param, value), ...]

    def start(self):
        self.recording = True
        self.events = []

    def stop(self):
        self.recording = False

    def record(self, frame, effect_idx, param, value):
        """Record a parameter value at a frame."""
        if not self.recording:
            return
        self.events.append((frame, effect_idx, param, value))

    def to_session(self, simplify=True, tolerance=0.01):
        """Convert recorded events to an AutomationSession.

        If simplify=True, removes redundant keyframes where the value
        didn't change significantly (within tolerance).
        """
        session = AutomationSession()

        # Group events by (effect_idx, param)
        groups = {}
        for frame, eidx, param, value in self.events:
            key = (eidx, param)
            if key not in groups:
                groups[key] = []
            groups[key].append((frame, value))

        for (eidx, param), keyframes in groups.items():
            # Sort by frame
            keyframes.sort(key=lambda kf: kf[0])

            if simplify and len(keyframes) > 2:
                keyframes = _simplify_keyframes(keyframes, tolerance)

            session.add_lane(eidx, param, keyframes)

        return session


def _simplify_keyframes(keyframes, tolerance=0.01):
    """Remove redundant keyframes using Ramer-Douglas-Peucker simplification.

    Keeps first and last, removes points that are within tolerance of
    the line between their neighbors.
    """
    if len(keyframes) <= 2:
        return keyframes

    # Find the point with maximum distance from the line between first and last
    first = keyframes[0]
    last = keyframes[-1]

    max_dist = 0
    max_idx = 0

    for i in range(1, len(keyframes) - 1):
        frame, value = keyframes[i]
        # Interpolate what the value would be on the line from first to last
        if last[0] == first[0]:
            t = 0
        else:
            t = (frame - first[0]) / (last[0] - first[0])
        expected = first[1] + t * (last[1] - first[1])
        dist = abs(value - expected)

        if dist > max_dist:
            max_dist = dist
            max_idx = i

    if max_dist > tolerance:
        # Recurse on both halves
        left = _simplify_keyframes(keyframes[:max_idx + 1], tolerance)
        right = _simplify_keyframes(keyframes[max_idx:], tolerance)
        return left[:-1] + right
    else:
        # All intermediate points are within tolerance — keep only endpoints
        return [first, last]

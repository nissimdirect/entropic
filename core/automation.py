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


def _bezier(a, b, t, cp1=None, cp2=None):
    """Cubic bezier interpolation with optional control points.

    cp1, cp2 are (x, y) tuples in normalized 0-1 space.
    If not provided, defaults to ease_in_out-like curve.
    """
    if cp1 is None:
        cp1 = (0.42, 0.0)
    if cp2 is None:
        cp2 = (0.58, 1.0)

    # Solve cubic bezier: P(t) = (1-t)^3*P0 + 3(1-t)^2*t*P1 + 3(1-t)*t^2*P2 + t^3*P3
    # For value axis only (P0.y=0, P3.y=1, map to a→b)
    # First solve for the bezier parameter u that gives us x=t
    # Using Newton's method to find u where B_x(u) = t
    u = t  # initial guess
    for _ in range(8):
        # Bezier x(u) with P0=(0,0), P1=cp1, P2=cp2, P3=(1,1)
        x_u = (3.0 * (1 - u) ** 2 * u * cp1[0] +
               3.0 * (1 - u) * u ** 2 * cp2[0] +
               u ** 3)
        # Derivative of x with respect to u
        dx = (3.0 * (1 - u) ** 2 * cp1[0] +
              6.0 * (1 - u) * u * (cp2[0] - cp1[0]) +
              3.0 * u ** 2 * (1 - cp2[0]))
        if abs(dx) < 1e-10:
            break
        u = u - (x_u - t) / dx
        u = max(0.0, min(1.0, u))

    # Now evaluate bezier y(u)
    y = (3.0 * (1 - u) ** 2 * u * cp1[1] +
         3.0 * (1 - u) * u ** 2 * cp2[1] +
         u ** 3)

    return a + (b - a) * y


CURVES = {
    "linear": _lerp,
    "ease_in": _ease_in,
    "ease_out": _ease_out,
    "ease_in_out": _ease_in_out,
    "step": _step,
    "sine": _sine,
    "bezier": _bezier,
}


# ─── Automation Lane ────────────────────────────────────────────────

class AutomationLane:
    """A single parameter's automation: keyframes + interpolation curve.

    Keyframes: [(frame_index, value), ...] or extended format
        [(frame, value, curve_type, cp1, cp2), ...]
    where curve_type/cp1/cp2 are optional per-segment overrides.
    Frames are absolute (0 = first frame of video).
    """

    def __init__(self, effect_idx, param_name, keyframes=None, curve="linear"):
        self.effect_idx = effect_idx
        self.param_name = param_name
        self.keyframes = sorted(keyframes or [], key=lambda kf: kf[0])
        self.curve = curve  # default curve for segments without override

    def add_keyframe(self, frame, value, curve=None, cp1=None, cp2=None):
        """Add or update a keyframe at the given frame.

        Args:
            frame: Frame index.
            value: Parameter value (0-1 normalized for UI lanes).
            curve: Optional per-segment curve override (applied to segment AFTER this kf).
            cp1, cp2: Optional bezier control points [(x,y)] for 'bezier' curve.
        """
        # Remove existing keyframe at this frame
        self.keyframes = [kf for kf in self.keyframes if kf[0] != frame]
        if curve or cp1 or cp2:
            self.keyframes.append((frame, value, curve, cp1, cp2))
        else:
            self.keyframes.append((frame, value))
        self.keyframes.sort(key=lambda kf: kf[0])

    def remove_keyframe(self, frame):
        """Remove keyframe at exact frame."""
        self.keyframes = [kf for kf in self.keyframes if kf[0] != frame]

    @staticmethod
    def _kf_frame(kf):
        return kf[0]

    @staticmethod
    def _kf_value(kf):
        return kf[1]

    @staticmethod
    def _kf_curve(kf):
        return kf[2] if len(kf) > 2 and kf[2] else None

    @staticmethod
    def _kf_cp1(kf):
        return kf[3] if len(kf) > 3 and kf[3] else None

    @staticmethod
    def _kf_cp2(kf):
        return kf[4] if len(kf) > 4 and kf[4] else None

    def get_value(self, frame):
        """Get interpolated value at a frame. Returns None if no keyframes."""
        if not self.keyframes:
            return None

        # Before first keyframe: hold first value
        if frame <= self._kf_frame(self.keyframes[0]):
            return self._kf_value(self.keyframes[0])

        # After last keyframe: hold last value
        if frame >= self._kf_frame(self.keyframes[-1]):
            return self._kf_value(self.keyframes[-1])

        # Find surrounding keyframes
        for i in range(len(self.keyframes) - 1):
            kf0 = self.keyframes[i]
            kf1 = self.keyframes[i + 1]
            f0, v0 = self._kf_frame(kf0), self._kf_value(kf0)
            f1, v1 = self._kf_frame(kf1), self._kf_value(kf1)

            if f0 <= frame <= f1:
                if f1 == f0:
                    return v0
                t = (frame - f0) / (f1 - f0)

                # Per-segment curve override (stored on the starting keyframe)
                seg_curve = self._kf_curve(kf0) or self.curve
                interp = CURVES.get(seg_curve, _lerp)

                if seg_curve == "bezier":
                    cp1 = self._kf_cp1(kf0)
                    cp2 = self._kf_cp2(kf0)
                    return _bezier(v0, v1, t, cp1, cp2)
                return interp(v0, v1, t)

        return self._kf_value(self.keyframes[-1])

    def to_dict(self):
        # Serialize keyframes with optional extended data
        kfs_out = []
        for kf in self.keyframes:
            if len(kf) > 2 and (kf[2] or kf[3] or kf[4]):
                kfs_out.append({
                    "frame": kf[0],
                    "value": kf[1],
                    "curve": kf[2],
                    "cp1": kf[3],
                    "cp2": kf[4],
                })
            else:
                kfs_out.append([kf[0], kf[1]])
        return {
            "effect_idx": self.effect_idx,
            "param": self.param_name,
            "keyframes": kfs_out,
            "curve": self.curve,
        }

    @classmethod
    def from_dict(cls, d):
        # Deserialize keyframes (support both [frame, val] and {frame, value, curve, cp1, cp2})
        keyframes = []
        for kf in d.get("keyframes", []):
            if isinstance(kf, dict):
                keyframes.append((
                    kf["frame"], kf["value"],
                    kf.get("curve"), kf.get("cp1"), kf.get("cp2"),
                ))
            else:
                keyframes.append(tuple(kf))
        return cls(
            effect_idx=d["effect_idx"],
            param_name=d["param"],
            keyframes=keyframes,
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

    def bake_lane(self, effect_idx, param_name, start_frame, end_frame):
        """Convert a lane's automation to per-frame static values.

        Returns list of (frame, value) tuples — one per frame.
        Useful for Freeze/Flatten: bake automation into static params.
        """
        lane = self.get_lane(effect_idx, param_name)
        if not lane:
            return []
        return [(f, lane.get_value(f)) for f in range(start_frame, end_frame + 1)]

    def bake_all(self, effects_list, start_frame, end_frame):
        """Bake all automation into per-frame effect lists.

        Returns: {frame: effects_list_with_overrides, ...}
        """
        result = {}
        for f in range(start_frame, end_frame + 1):
            result[f] = self.apply_to_chain(effects_list, f)
        return result

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


class MidiEventLane(AutomationLane):
    """Step-function automation lane for MIDI events.

    Unlike AutomationLane (which interpolates between keyframes),
    MidiEventLane holds the last value until the next event — like
    a sample-and-hold. Used for note on/off and CC fader recording.
    """

    def __init__(self, layer_id, param_name, keyframes=None):
        # effect_idx is repurposed as layer_id for performance mode
        super().__init__(
            effect_idx=layer_id,
            param_name=param_name,
            keyframes=keyframes or [],
            curve="step",
        )
        self.layer_id = layer_id

    def get_value(self, frame):
        """Step interpolation: hold last value until next keyframe."""
        if not self.keyframes:
            return None

        # Before first keyframe: return None (no data yet)
        if frame < self.keyframes[0][0]:
            return None

        # Find the last keyframe at or before this frame
        value = self.keyframes[0][1]
        for kf_frame, kf_value in self.keyframes:
            if kf_frame <= frame:
                value = kf_value
            else:
                break
        return value

    def to_dict(self):
        d = super().to_dict()
        d["type"] = "midi_event"
        d["layer_id"] = self.layer_id
        return d

    @classmethod
    def from_dict(cls, d):
        lane = cls(
            layer_id=d.get("layer_id", d.get("effect_idx", 0)),
            param_name=d["param"],
            keyframes=[tuple(kf) for kf in d["keyframes"]],
        )
        return lane


class PerformanceSession(AutomationSession):
    """Automation session extended for layer-based performance recording.

    Adds MIDI event lanes and per-layer value lookup.
    """

    def record_midi_event(self, frame, layer_id, param, value):
        """Record a MIDI event (note on/off or CC) at a frame.

        Args:
            frame: Frame index when event occurred.
            layer_id: Layer this event targets.
            param: Parameter name ("active", "opacity", "trigger_on", "trigger_off").
            value: Value (1/0 for triggers, 0-1 for opacity).
        """
        # Find or create lane for this layer+param
        lane = None
        for l in self.lanes:
            if (isinstance(l, MidiEventLane) and
                    l.layer_id == layer_id and l.param_name == param):
                lane = l
                break

        if lane is None:
            lane = MidiEventLane(layer_id, param)
            self.lanes.append(lane)

        lane.add_keyframe(frame, value)

    def get_layer_values(self, frame):
        """Get all layer parameter values at a frame.

        Returns: {layer_id: {param: value, ...}, ...}
        """
        result = {}
        for lane in self.lanes:
            lid = getattr(lane, 'layer_id', lane.effect_idx)
            val = lane.get_value(frame)
            if val is not None:
                if lid not in result:
                    result[lid] = {}
                result[lid][lane.param_name] = val
        return result

    def to_dict(self):
        return {
            "type": "performance",
            "lanes": [l.to_dict() for l in self.lanes],
        }

    @classmethod
    def from_dict(cls, d):
        session = cls()
        for lane_data in d.get("lanes", []):
            if lane_data.get("type") == "midi_event":
                session.lanes.append(MidiEventLane.from_dict(lane_data))
            else:
                session.lanes.append(AutomationLane.from_dict(lane_data))
        return session

    def save(self, path):
        """Save performance automation to JSON file."""
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path):
        """Load performance automation from JSON file."""
        data = json.loads(Path(path).read_text())
        if data.get("type") == "performance":
            return cls.from_dict(data)
        # Fall back to base class for non-performance files
        return AutomationSession.from_dict(data)


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

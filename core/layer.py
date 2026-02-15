"""
Entropic — Layer Compositor for Live Performance

Manages video layers with MIDI-triggered activation, ADSR envelopes,
choke groups, and alpha compositing.

Each layer has:
- A video source (streaming frames from FFmpeg)
- An effect chain (same format as apply_chain)
- Trigger mode: toggle, gate, adsr, always_on
- ADSR envelope for opacity modulation
- Choke group (mutually exclusive layers)
- MIDI note/CC mapping
"""

from dataclasses import dataclass, field

import numpy as np

from effects.adsr import ADSREnvelope


# ADSR presets (values in frames at 30fps)
ADSR_PRESETS = {
    "pluck":   {"attack": 0.3,  "decay": 1.5,  "sustain": 0.8, "release": 6},
    "sustain": {"attack": 15,   "decay": 6,    "sustain": 1.0, "release": 60},
    "stab":    {"attack": 0.15, "decay": 0.3,  "sustain": 0.0, "release": 3},
    "pad":     {"attack": 60,   "decay": 30,   "sustain": 1.0, "release": 150},
}


@dataclass
class Layer:
    """A single video layer with trigger/effect state.

    Configuration (serializable):
        layer_id: Unique integer ID (0-7).
        name: Display name.
        video_path: Path to source video.
        effects: Effect chain (list of dicts, same as apply_chain format).
        opacity: Base opacity (0-1). Modulated by ADSR and CC.
        z_order: Stacking order (lower = bottom/back).
        trigger_mode: "toggle" | "gate" | "adsr" | "always_on"
        adsr_preset: Name from ADSR_PRESETS or custom dict.
        choke_group: Optional int. Layers in same group are mutually exclusive.
        midi_note: MIDI note number that triggers this layer.
        midi_cc_opacity: CC number for opacity fader control.

    Runtime state (not serialized):
        _active: Whether layer is currently visible.
        _adsr_envelope: ADSREnvelope instance.
        _current_opacity: Computed opacity (base * envelope).
    """
    layer_id: int = 0
    name: str = ""
    video_path: str = ""
    effects: list = field(default_factory=list)
    opacity: float = 1.0
    z_order: int = 0
    trigger_mode: str = "toggle"  # "toggle" | "gate" | "adsr" | "one_shot" | "always_on"
    adsr_preset: str = "sustain"
    blend_mode: str = "normal"  # "normal"|"multiply"|"screen"|"overlay"|"add"|"difference"|"soft_light"
    choke_group: int | None = None
    midi_note: int | None = None
    midi_cc_opacity: int | None = None

    def __post_init__(self):
        self._active = self.trigger_mode == "always_on"
        self._adsr_envelope = self._create_envelope()
        self._current_opacity = self.opacity if self._active else 0.0

    def _create_envelope(self):
        """Create ADSR envelope from preset name or custom dict."""
        if isinstance(self.adsr_preset, dict):
            params = self.adsr_preset
        else:
            params = ADSR_PRESETS.get(self.adsr_preset, ADSR_PRESETS["sustain"])
        return ADSREnvelope(**params)

    def trigger_on(self):
        """Activate this layer (note on / toggle on)."""
        if self.trigger_mode == "toggle":
            self._active = not self._active
            if self._active:
                self._adsr_envelope.trigger_on()
            else:
                self._adsr_envelope.trigger_off()
        elif self.trigger_mode in ("gate", "adsr"):
            self._active = True
            self._adsr_envelope.trigger_on()
        elif self.trigger_mode == "one_shot":
            # One-shot: always retrigger from attack, like an Ableton sample
            self._active = True
            self._adsr_envelope.reset()
            self._adsr_envelope.trigger_on()
        # always_on: no-op

    def trigger_off(self):
        """Deactivate this layer (note off)."""
        if self.trigger_mode == "gate":
            self._active = False
            self._adsr_envelope.trigger_off()
        elif self.trigger_mode == "adsr":
            # ADSR mode: note off starts release, but layer stays "active"
            # until envelope reaches 0
            self._adsr_envelope.trigger_off()
        # one_shot: no-op on note off — envelope plays through automatically
        # toggle: no-op on note off (toggle only responds to note on)
        # always_on: no-op

    def force_off(self):
        """Force layer off (used by choke groups)."""
        self._active = False
        self._adsr_envelope.trigger_off()
        self._current_opacity = 0.0

    def set_opacity(self, value):
        """Set base opacity from CC fader (0-1)."""
        self.opacity = max(0.0, min(1.0, value))

    def advance(self):
        """Step ADSR envelope one frame and compute current opacity.

        Returns:
            float: Current effective opacity (0-1).
        """
        if self.trigger_mode == "always_on":
            self._current_opacity = self.opacity
            return self._current_opacity

        # One-shot: when envelope reaches sustain phase, immediately start release
        # This makes it play through A→D→R automatically like a sample trigger
        if self.trigger_mode == "one_shot" and self._adsr_envelope.phase == "sustain":
            self._adsr_envelope.trigger_off()

        env_level = self._adsr_envelope.advance()

        # For ADSR/one_shot mode, check if envelope finished release
        if self.trigger_mode in ("adsr", "one_shot") and env_level <= 0 and not self._adsr_envelope.was_triggered:
            self._active = False

        self._current_opacity = self.opacity * env_level
        return self._current_opacity

    @property
    def is_visible(self):
        """Whether this layer should be composited (active with opacity > 0)."""
        if self.trigger_mode == "always_on":
            return self.opacity > 0
        return self._active or self._current_opacity > 0.001

    def reset(self):
        """Panic reset — force to initial state."""
        self._active = self.trigger_mode == "always_on"
        self._adsr_envelope.reset()
        self._current_opacity = self.opacity if self._active else 0.0

    def to_dict(self):
        return {
            "layer_id": self.layer_id,
            "name": self.name,
            "video_path": self.video_path,
            "effects": self.effects,
            "opacity": self.opacity,
            "z_order": self.z_order,
            "trigger_mode": self.trigger_mode,
            "adsr_preset": self.adsr_preset,
            "blend_mode": self.blend_mode,
            "choke_group": self.choke_group,
            "midi_note": self.midi_note,
            "midi_cc_opacity": self.midi_cc_opacity,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: v for k, v in d.items() if not k.startswith("_")})


# ─── Blend Mode Functions (Photoshop-compatible) ───
# All operate on float32 arrays normalized to 0-255.

BLEND_MODES = [
    "normal", "multiply", "screen", "overlay",
    "add", "difference", "soft_light",
]


def _blend_multiply(bottom, top):
    return bottom * top / 255.0


def _blend_screen(bottom, top):
    return 255.0 - (255.0 - bottom) * (255.0 - top) / 255.0


def _blend_overlay(bottom, top):
    """Overlay = Multiply where bottom is dark, Screen where bottom is light."""
    mask = bottom < 128.0
    result = np.where(
        mask,
        2.0 * bottom * top / 255.0,
        255.0 - 2.0 * (255.0 - bottom) * (255.0 - top) / 255.0,
    )
    return result


def _blend_add(bottom, top):
    return np.minimum(255.0, bottom + top)


def _blend_difference(bottom, top):
    return np.abs(bottom - top)


def _blend_soft_light(bottom, top):
    """Pegtop soft light formula (continuous, no branch)."""
    t = top / 255.0
    return (1.0 - 2.0 * t) * (bottom ** 2 / 255.0) + 2.0 * t * bottom


_BLEND_FNS = {
    "multiply": _blend_multiply,
    "screen": _blend_screen,
    "overlay": _blend_overlay,
    "add": _blend_add,
    "difference": _blend_difference,
    "soft_light": _blend_soft_light,
}


class LayerStack:
    """Manages multiple layers and composites them together.

    Layers are sorted by z_order (lowest = bottom) and blended
    from bottom to top. Each layer can use a different blend mode.
    """

    def __init__(self, layers=None):
        self.layers = sorted(layers or [], key=lambda l: l.z_order)
        self._layers_by_id = {l.layer_id: l for l in self.layers}
        self._layers_by_note = {}
        self._layers_by_cc = {}
        self._build_lookup()

    def _build_lookup(self):
        """Build MIDI note/CC -> layer lookup tables."""
        self._layers_by_note = {}
        self._layers_by_cc = {}
        for layer in self.layers:
            if layer.midi_note is not None:
                self._layers_by_note[layer.midi_note] = layer
            if layer.midi_cc_opacity is not None:
                self._layers_by_cc[layer.midi_cc_opacity] = layer

    def get_layer(self, layer_id):
        """Get layer by ID."""
        return self._layers_by_id.get(layer_id)

    def get_layer_by_note(self, note):
        """Get layer mapped to a MIDI note."""
        return self._layers_by_note.get(note)

    def get_layer_by_cc(self, cc):
        """Get layer mapped to a CC number."""
        return self._layers_by_cc.get(cc)

    def handle_choke(self, triggered_layer):
        """Enforce choke groups: when a layer triggers, silence others in same group."""
        if triggered_layer.choke_group is None:
            return
        for layer in self.layers:
            if (layer is not triggered_layer and
                    layer.choke_group == triggered_layer.choke_group and
                    layer._active):
                layer.force_off()

    def advance_all(self):
        """Step all layer ADSR envelopes one frame."""
        for layer in self.layers:
            layer.advance()

    def composite(self, frame_dict):
        """Blend all visible layers from bottom to top with blend modes.

        Args:
            frame_dict: {layer_id: numpy_frame} — pre-processed frames
                        for each layer (after effects applied).

        Returns:
            numpy.ndarray: Composited frame (H, W, 3) uint8.
        """
        result = None

        for layer in self.layers:
            if not layer.is_visible:
                continue

            frame = frame_dict.get(layer.layer_id)
            if frame is None:
                continue

            alpha = layer._current_opacity

            # Handle RGBA frames: extract per-pixel alpha from 4th channel
            pixel_alpha = None
            if frame.ndim == 3 and frame.shape[2] == 4:
                pixel_alpha = frame[:, :, 3].astype(np.float32) / 255.0
                frame = frame[:, :, :3]

            if result is None:
                # First visible layer becomes the base
                if pixel_alpha is not None:
                    pa = (pixel_alpha * alpha)[:, :, np.newaxis]
                    result = np.clip(frame.astype(np.float32) * pa, 0, 255).astype(np.uint8)
                elif alpha >= 1.0:
                    result = frame.copy()
                else:
                    result = np.clip(frame.astype(np.float32) * alpha, 0, 255).astype(np.uint8)
                continue

            # Ensure same size (resize if needed)
            if result.shape[:2] != frame.shape[:2]:
                from PIL import Image
                h, w = result.shape[:2]
                img = Image.fromarray(frame)
                frame = np.array(img.resize((w, h), Image.LANCZOS))
                if pixel_alpha is not None:
                    pa_img = Image.fromarray((pixel_alpha * 255).astype(np.uint8))
                    pixel_alpha = np.array(pa_img.resize((w, h), Image.LANCZOS)).astype(np.float32) / 255.0

            if alpha <= 0:
                continue

            # Compute effective alpha (layer opacity * per-pixel alpha)
            if pixel_alpha is not None:
                eff_alpha = (pixel_alpha * alpha)[:, :, np.newaxis]
            else:
                eff_alpha = alpha

            # Get blend function
            blend_fn = _BLEND_FNS.get(layer.blend_mode)

            if blend_fn is None:
                # Normal blend: result = bottom * (1-a) + top * a
                r = result.astype(np.float32)
                f = frame.astype(np.float32)
                result = np.clip(r * (1.0 - eff_alpha) + f * eff_alpha, 0, 255).astype(np.uint8)
            else:
                # Non-normal blend mode:
                # 1. Compute blended = blend_fn(bottom, top)
                # 2. Mix with alpha: result = bottom * (1-a) + blended * a
                r = result.astype(np.float32)
                f = frame.astype(np.float32)
                blended = blend_fn(r, f)
                result = np.clip(r * (1.0 - eff_alpha) + blended * eff_alpha, 0, 255).astype(np.uint8)

        # If no layers visible, return black frame
        if result is None:
            for frame in frame_dict.values():
                if frame is not None:
                    return np.zeros_like(frame)
            return np.zeros((540, 960, 3), dtype=np.uint8)

        return result

    def panic(self):
        """Reset all layers to initial state."""
        for layer in self.layers:
            layer.reset()

    def to_dict(self):
        return {"layers": [l.to_dict() for l in self.layers]}

    @classmethod
    def from_dict(cls, d):
        layers = [Layer.from_dict(ld) for ld in d.get("layers", [])]
        return cls(layers)

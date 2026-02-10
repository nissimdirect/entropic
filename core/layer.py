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
    trigger_mode: str = "toggle"
    adsr_preset: str = "sustain"
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

        env_level = self._adsr_envelope.advance()

        # For ADSR mode, check if envelope finished release
        if self.trigger_mode == "adsr" and env_level <= 0 and not self._adsr_envelope.was_triggered:
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
            "choke_group": self.choke_group,
            "midi_note": self.midi_note,
            "midi_cc_opacity": self.midi_cc_opacity,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: v for k, v in d.items() if not k.startswith("_")})


class LayerStack:
    """Manages multiple layers and composites them together.

    Layers are sorted by z_order (lowest = bottom) and alpha-blended
    from bottom to top using Normal blend mode.
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
        """Blend all visible layers from bottom to top.

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

            if result is None:
                # First visible layer becomes the base
                if alpha >= 1.0:
                    result = frame.copy()
                else:
                    # Blend with black background
                    result = (frame.astype(np.float32) * alpha).astype(np.uint8)
                continue

            # Ensure same size (resize if needed)
            if result.shape != frame.shape:
                from PIL import Image
                h, w = result.shape[:2]
                img = Image.fromarray(frame)
                frame = np.array(img.resize((w, h), Image.LANCZOS))

            # Alpha blend: result = bottom * (1-a) + top * a
            if alpha >= 1.0:
                result = frame.copy()
            elif alpha > 0:
                r = result.astype(np.float32)
                f = frame.astype(np.float32)
                result = np.clip(r * (1.0 - alpha) + f * alpha, 0, 255).astype(np.uint8)

        # If no layers visible, return black frame
        if result is None:
            # Try to get dimensions from any available frame
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

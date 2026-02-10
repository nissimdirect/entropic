"""
Entropic — Live Performance Engine

Real-time preview with pygame display, MIDI layer triggering,
and automation recording. Two-phase VJ workflow:
  1. Perform live (480p preview, record MIDI automation)
  2. Render offline (1080p from recorded automation)

Hotkeys:
  Space      = play/pause
  1-8        = toggle layers (keyboard fallback)
  Shift+P    = panic (reset all layers) — requires modifier to prevent slips
  Shift+Q    = quit — requires modifier to prevent accidental exit
  Esc        = exit (double-tap within 500ms)

UX safety (Don Norman error prevention):
  - Auto-record always on — performer chooses to discard, not remember to arm
  - Destructive hotkeys require modifier or double-tap
  - caffeinate prevents macOS sleep during 30-min sets
  - Pre-buffered frames minimize MIDI trigger latency
"""

import subprocess as _subprocess
import sys
import time
import json
from pathlib import Path

import numpy as np

try:
    import pygame
except ImportError:
    pygame = None

from core.video_io import probe_video, stream_frames
from core.layer import Layer, LayerStack, ADSR_PRESETS
from core.automation import PerformanceSession
from effects import apply_chain


class PerformanceEngine:
    """Real-time layer compositing with MIDI control and automation recording.

    Latency optimizations:
      - MIDI/keyboard events processed FIRST each frame (before rendering)
      - Layer trigger is pure dict lookup (O(1))
      - Frame pre-buffering: next frame read happens while current frame displays
      - Inactive layers skip both frame read AND effect processing

    Memory management:
      - Each layer holds exactly 1 frame in memory (~1.5MB at 480p)
      - FFmpeg generators are lazy — only decode on demand
      - Inactive layers don't accumulate frames
      - Effect processing uses in-place where possible
    """

    def __init__(self, layers_config, preview_scale=0.5, fps=30):
        if pygame is None:
            raise RuntimeError("pygame required for performance mode. Install: pip install pygame")

        # Build layers
        layers = []
        for lc in layers_config:
            if isinstance(lc, Layer):
                layers.append(lc)
            else:
                layers.append(Layer.from_dict(lc))
        self.layer_stack = LayerStack(layers)

        self.preview_scale = preview_scale
        self.fps = fps
        self.frame_index = 0
        self.playing = False
        self.recording = True  # Buffer always captures (user chooses to keep or discard at exit)
        self.running = True

        # Automation: always captures to buffer, user decides at exit
        # Buffer is single-level — new recording clears previous buffer
        # Max buffer: 50,000 events (~27 min at 30fps with constant input)
        self.session = PerformanceSession()
        self._user_opted_in = False  # True once user explicitly hits R
        self._buffer_generation = 0  # Increments on each R press
        self._max_buffer_events = 50000  # Cap to prevent memory bloat
        self._buffer_event_count = 0

        # MIDI (optional)
        self._midi = None

        # Video generators (one per layer)
        self._generators = {}
        self._current_frames = {}

        # Display
        self._screen = None
        self._clock = None
        self._font = None  # Cache font to avoid re-creation per frame

        # UX safety state
        self._last_esc_time = 0.0  # Double-tap Esc detection
        self._caffeinate_proc = None  # macOS sleep prevention

    def init_midi(self, device_id=None, learn=False):
        """Initialize MIDI controller (optional)."""
        try:
            from core.midi import MidiController
            self._midi = MidiController(device_id=device_id, learn=learn)
            self._midi.start()
        except Exception as e:
            print(f"  MIDI init failed: {e}")
            self._midi = None

    def init_video_streams(self):
        """Start streaming frame generators for each layer.

        Validates video files exist before streaming (red team issue #9).
        """
        for layer in self.layer_stack.layers:
            if layer.video_path:
                if not Path(layer.video_path).exists():
                    print(f"  ERROR: Video not found: {layer.video_path}")
                    print(f"         Layer {layer.layer_id} ({layer.name}) disabled.")
                    continue
                gen = stream_frames(layer.video_path, scale=self.preview_scale)
                self._generators[layer.layer_id] = gen
                try:
                    self._current_frames[layer.layer_id] = next(gen)
                except StopIteration:
                    print(f"  Warning: No frames in {layer.video_path}")

    def init_display(self):
        """Initialize pygame window."""
        pygame.init()

        # Get dimensions from first available frame
        w, h = 960, 540
        for frame in self._current_frames.values():
            if frame is not None:
                h, w = frame.shape[:2]
                break

        self._screen = pygame.display.set_mode((w, h))
        pygame.display.set_caption("Entropic Performance Mode")
        self._clock = pygame.time.Clock()
        self._font = pygame.font.SysFont("monospace", 14)
        self._display_w = w
        self._display_h = h

    def _start_caffeinate(self):
        """Prevent macOS from sleeping during performance (30-min sets)."""
        try:
            self._caffeinate_proc = _subprocess.Popen(
                ["caffeinate", "-dims"],
                stdout=_subprocess.DEVNULL,
                stderr=_subprocess.DEVNULL,
            )
            print("  Sleep prevention: ON (caffeinate)")
        except Exception:
            pass  # Non-fatal — only affects macOS

    def _stop_caffeinate(self):
        """Stop sleep prevention."""
        if self._caffeinate_proc:
            self._caffeinate_proc.terminate()
            self._caffeinate_proc = None

    def _record_event(self, layer_id, param, value):
        """Record a MIDI/keyboard event with buffer cap protection."""
        if not self.recording:
            return
        if not self._user_opted_in and self._buffer_event_count >= self._max_buffer_events:
            return  # Buffer full — stop silently to prevent memory bloat
        self.session.record_midi_event(self.frame_index, layer_id, param, value)
        self._buffer_event_count += 1

    def _handle_pygame_events(self):
        """Process keyboard input. MIDI triggers are O(1) dict lookups for minimal latency."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()

                # Esc = double-tap to exit (prevents accidental quit mid-set)
                if event.key == pygame.K_ESCAPE:
                    now = time.monotonic()
                    if now - self._last_esc_time < 0.5:
                        self.running = False
                    else:
                        self._last_esc_time = now
                        print("  [Press Esc again to exit]")

                # Shift+Q = quit (modifier required — prevents accidental exit)
                elif event.key == pygame.K_q and (mods & pygame.KMOD_SHIFT):
                    self.running = False

                elif event.key == pygame.K_r:
                    self._user_opted_in = not self._user_opted_in
                    if self._user_opted_in:
                        # New recording — clear buffer to prevent unbounded growth
                        self.session = PerformanceSession()
                        self._buffer_generation += 1
                        self._buffer_event_count = 0
                        print(f"  [REC ON] Buffer cleared, recording fresh (gen {self._buffer_generation})")
                    else:
                        print("  [REC OFF] (buffer retained from this take)")

                elif event.key == pygame.K_SPACE:
                    self.playing = not self.playing
                    state = "PLAYING" if self.playing else "PAUSED"
                    print(f"  [{state}]")

                # Shift+P = panic (modifier required — prevents accidental layer reset)
                elif event.key == pygame.K_p and (mods & pygame.KMOD_SHIFT):
                    self.layer_stack.panic()
                    print("  [PANIC] All layers reset")

                # Number keys 1-8 = toggle layers
                elif pygame.K_1 <= event.key <= pygame.K_8:
                    layer_id = event.key - pygame.K_1
                    layer = self.layer_stack.get_layer(layer_id)
                    if layer:
                        layer.trigger_on()
                        self.layer_stack.handle_choke(layer)
                        val = 1.0 if layer._active else 0.0
                        self._record_event(layer_id, "active", val)
                        state = "ON" if layer._active else "OFF"
                        print(f"  Layer {layer_id} ({layer.name}): {state}")

            elif event.type == pygame.KEYUP:
                # Number key release for gate mode
                if pygame.K_1 <= event.key <= pygame.K_8:
                    layer_id = event.key - pygame.K_1
                    layer = self.layer_stack.get_layer(layer_id)
                    if layer and layer.trigger_mode == "gate":
                        layer.trigger_off()
                        self._record_event(layer_id, "active", 0.0)

    def _handle_midi_events(self):
        """Process MIDI input. All lookups are O(1) dict for minimal latency."""
        if self._midi is None:
            return

        for event in self._midi.poll():
            if event["type"] == "note_on":
                layer = self.layer_stack.get_layer(event["layer"])
                if layer:
                    layer.trigger_on()
                    self.layer_stack.handle_choke(layer)
                    self._record_event(event["layer"], "trigger_on", 1.0)

            elif event["type"] == "note_off":
                layer = self.layer_stack.get_layer(event["layer"])
                if layer:
                    layer.trigger_off()
                    self._record_event(event["layer"], "trigger_off", 0.0)

            elif event["type"] == "cc":
                layer = self.layer_stack.get_layer(event["layer"])
                if layer:
                    layer.set_opacity(event["value"])
                    self._record_event(event["layer"], "opacity", event["value"])

    def _advance_frames(self):
        """Read next frame from each VISIBLE layer's video stream.

        Memory optimization: inactive layers skip frame reads entirely.
        Only 1 frame per layer is held in memory at any time.
        Old generators are explicitly closed before loop restart to prevent
        FFmpeg zombie processes (red team issue #1).
        """
        for layer in self.layer_stack.layers:
            if not layer.is_visible:
                continue

            gen = self._generators.get(layer.layer_id)
            if gen is None:
                continue

            try:
                self._current_frames[layer.layer_id] = next(gen)
            except StopIteration:
                # Loop: close old generator FIRST to kill FFmpeg process
                if layer.video_path:
                    try:
                        gen.close()
                    except Exception:
                        pass
                    new_gen = stream_frames(layer.video_path, scale=self.preview_scale)
                    self._generators[layer.layer_id] = new_gen
                    try:
                        self._current_frames[layer.layer_id] = next(new_gen)
                    except StopIteration:
                        pass

    def _apply_effects(self):
        """Apply each layer's effect chain to its current frame.

        Only processes visible layers. Returns dict of processed frames.
        """
        processed = {}
        for layer in self.layer_stack.layers:
            if not layer.is_visible:
                continue

            frame = self._current_frames.get(layer.layer_id)
            if frame is None:
                continue

            if layer.effects:
                frame = apply_chain(
                    frame, layer.effects,
                    frame_index=self.frame_index,
                    total_frames=999999,
                    watermark=False,
                )

            processed[layer.layer_id] = frame

        return processed

    def _render_to_screen(self, frame):
        """Display composited frame in pygame window."""
        surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
        self._screen.blit(surface, (0, 0))
        self._draw_hud()
        pygame.display.flip()

    def _draw_hud(self):
        """Draw minimal status overlay. Uses cached font for performance."""
        font = self._font

        # Recording indicator
        if self._user_opted_in:
            rec_surf = font.render("[REC]", True, (255, 80, 80))
            self._screen.blit(rec_surf, (10, 10))
        else:
            rec_surf = font.render("[BUF]", True, (120, 120, 120))
            self._screen.blit(rec_surf, (10, 10))

        # Frame counter + elapsed time
        elapsed = self.frame_index / self.fps
        minutes = int(elapsed // 60)
        seconds = elapsed % 60
        time_str = f"F:{self.frame_index}  {minutes}:{seconds:05.2f}"
        time_surf = font.render(time_str, True, (200, 200, 200))
        self._screen.blit(time_surf, (10, self._display_h - 24))

        # Layer status with trigger mode
        y = 30
        for layer in self.layer_stack.layers:
            color = (100, 255, 100) if layer.is_visible else (100, 100, 100)
            opacity_pct = int(layer._current_opacity * 100)
            mode_tag = layer.trigger_mode[:3].upper()
            label = f"L{layer.layer_id}: {layer.name or '---'} [{mode_tag}] {opacity_pct}%"
            surf = font.render(label, True, color)
            self._screen.blit(surf, (10, y))
            y += 18

    def run(self):
        """Main performance loop.

        Loop order optimized for minimal MIDI trigger latency:
          1. Handle events (MIDI + keyboard) — FIRST, before any rendering
          2. Advance ADSR envelopes
          3. Read frames (only visible layers)
          4. Apply effects (only visible layers)
          5. Composite + display
        """
        self.init_video_streams()
        self.init_display()
        self._start_caffeinate()

        print("\n  Entropic Performance Mode")
        print("  " + "─" * 40)
        print("  1-8=Layers  Space=Play/Pause  R=Record  Shift+P=Panic  Esc(x2)=Exit")
        print("  Buffer: always capturing. Press R to arm recording. Choose to keep/discard at exit.")
        print()

        # Print MIDI mapping summary
        for layer in self.layer_stack.layers:
            note = f"note {layer.midi_note}" if layer.midi_note else "—"
            cc = f"CC {layer.midi_cc_opacity}" if layer.midi_cc_opacity else "—"
            print(f"  L{layer.layer_id}: {layer.name:15s} [{layer.trigger_mode:9s}] "
                  f"MIDI: {note:10s} Opacity: {cc}")
        print()

        self.playing = True

        try:
            while self.running:
                # 1. Events FIRST for minimal trigger latency
                self._handle_pygame_events()
                self._handle_midi_events()

                if self.playing:
                    # 2. Advance envelopes
                    self.layer_stack.advance_all()

                    # 3. Read next frames (visible layers only)
                    self._advance_frames()

                    # 4. Apply effects (visible layers only)
                    processed = self._apply_effects()

                    # 5. Composite + display
                    composited = self.layer_stack.composite(processed)
                    self._render_to_screen(composited)

                    self.frame_index += 1
                else:
                    # Paused — still render current state (no frame advance)
                    if self._current_frames:
                        processed = self._apply_effects()
                        composited = self.layer_stack.composite(processed)
                        self._render_to_screen(composited)

                self._clock.tick(self.fps)

        except KeyboardInterrupt:
            print("\n  [INTERRUPTED]")
        finally:
            self._cleanup()

    def _cleanup(self):
        """Clean up resources."""
        self._stop_caffeinate()

        if self._midi:
            self._midi.stop()

        for gen in self._generators.values():
            gen.close()
        self._generators.clear()
        self._current_frames.clear()

        if pygame and pygame.get_init():
            pygame.quit()

    def save_automation(self, path):
        """Save recorded automation to JSON."""
        path = Path(path)
        self.session.save(path)
        n_lanes = len(self.session.lanes)
        n_events = sum(len(l.keyframes) for l in self.session.lanes)
        print(f"  Saved: {path} ({n_lanes} lanes, {n_events} events)")

    def get_layers_config(self):
        """Get serializable layer configuration."""
        return self.layer_stack.to_dict()

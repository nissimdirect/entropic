"""
Entropic — MIDI Controller Input for Live Performance

Maps MIDI notes to layer triggers and CC faders to layer opacity.
Ported from Chaos Visualizer's core/midi.py, adapted for layer-based
compositing instead of parameter control.

Default mapping:
  Notes 36-43 (Launchpad pads) -> Layer triggers 0-7
  Notes 1-8   (keyboard zone)  -> Layer triggers 0-7
  CC 16-23    (Akai MIDI Mix)  -> Layer 0-7 opacity

Use --midi-learn to see what your controller sends, then edit
the NOTE_MAP and CC_MAP dicts to customize.
"""

import rtmidi


# Note number -> layer_id (Launchpad pads start at 36)
NOTE_MAP = {
    # Launchpad grid (bottom row)
    36: 0, 37: 1, 38: 2, 39: 3,
    40: 4, 41: 5, 42: 6, 43: 7,
    # Keyboard fallback (low notes)
    1: 0, 2: 1, 3: 2, 4: 3,
    5: 4, 6: 5, 7: 6, 8: 7,
}

# CC number -> layer_id for opacity (Akai MIDI Mix faders)
CC_MAP = {
    16: 0, 17: 1, 18: 2, 19: 3,
    20: 4, 21: 5, 22: 6, 23: 7,
}


class MidiController:
    """Reads MIDI input for layer triggering and opacity control.

    Returns structured events with note_on/note_off distinction
    (unlike Chaos Visualizer version which only tracks note_on).
    """

    def __init__(self, device_id=None, learn=False):
        self.device_id = device_id
        self.learn = learn
        self._midi_in = None
        self._available = False

    def start(self):
        """Open MIDI input port."""
        self._midi_in = rtmidi.MidiIn()
        ports = self._midi_in.get_ports()

        if not ports:
            if self.device_id is not None:
                print("  MIDI: No devices found")
            return

        if self.device_id is not None:
            if self.device_id >= len(ports):
                print(f"  MIDI: Device {self.device_id} not found (max: {len(ports) - 1})")
                return
            self._midi_in.open_port(self.device_id)
            print(f"  MIDI: Opened [{self.device_id}] {ports[self.device_id]}")
        else:
            # Auto-detect: open first available port
            self._midi_in.open_port(0)
            print(f"  MIDI: Auto-detected [0] {ports[0]}")
            self.device_id = 0

        self._available = True

    def stop(self):
        """Close MIDI input."""
        if self._midi_in:
            self._midi_in.close_port()
            del self._midi_in
            self._midi_in = None
        self._available = False

    def poll(self):
        """Read all pending MIDI events. Returns list of event dicts.

        Event types:
            {"type": "note_on",  "layer": int, "velocity": int, "note": int}
            {"type": "note_off", "layer": int, "note": int}
            {"type": "cc",       "layer": int, "value": float (0-1), "cc": int}

        Note off is detected as: status 0x80 OR status 0x90 with velocity 0.
        """
        if not self._available or not self._midi_in:
            return []

        events = []

        while True:
            msg = self._midi_in.get_message()
            if msg is None:
                break

            data, delta_time = msg
            if len(data) < 2:
                continue

            status = data[0] & 0xF0
            d1 = data[1]
            d2 = data[2] if len(data) > 2 else 0

            if self.learn:
                status_name = {
                    0x80: "NoteOff", 0x90: "NoteOn", 0xB0: "CC",
                    0xC0: "PgmChg", 0xE0: "PitchBend",
                }.get(status, f"0x{status:02X}")
                channel = data[0] & 0x0F
                print(f"  MIDI-LEARN: {status_name} ch={channel} "
                      f"d1={d1} d2={d2}")

            # Note On (velocity > 0)
            if status == 0x90 and d2 > 0:
                if d1 in NOTE_MAP:
                    events.append({
                        "type": "note_on",
                        "layer": NOTE_MAP[d1],
                        "velocity": d2,
                        "note": d1,
                    })

            # Note Off (0x80 or 0x90 with velocity 0)
            elif status == 0x80 or (status == 0x90 and d2 == 0):
                if d1 in NOTE_MAP:
                    events.append({
                        "type": "note_off",
                        "layer": NOTE_MAP[d1],
                        "note": d1,
                    })

            # CC (Control Change) -> layer opacity
            elif status == 0xB0:
                if d1 in CC_MAP:
                    events.append({
                        "type": "cc",
                        "layer": CC_MAP[d1],
                        "value": d2 / 127.0,
                        "cc": d1,
                    })

        return events

    @staticmethod
    def list_devices():
        """Print available MIDI input devices."""
        midi_in = rtmidi.MidiIn()
        ports = midi_in.get_ports()
        if not ports:
            print("\n  No MIDI input devices found.")
            del midi_in
            return

        print("\nMIDI Input Devices:")
        print("-" * 60)
        for i, name in enumerate(ports):
            print(f"  [{i}] {name}")
        print()
        del midi_in

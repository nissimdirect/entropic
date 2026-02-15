# Modulation & DSP Filter Guide

> How Entropic's audio-inspired effects actually work, and how they differ.

---

## The 5 Types

### Flanger
**What it does:** Mixes the signal with a delayed copy. The delay time oscillates via LFO, creating a sweeping comb filter.

**Audio equivalent:** Jet engine whoosh, metallic sweep.

**Visual result:** Evenly-spaced interference bands that move up/down or side-to-side.

```
Input ──┬──────────────────> Mix ──> Output
        │                    ^
        └── Delay (LFO) ────┘
             └── Feedback ──┘
```

**Key params:** `rate` (sweep speed), `depth` (delay range), `feedback` (resonance)

**Entropic flangers:**
| Effect | Domain | What varies |
|--------|--------|-------------|
| `videoflanger` | Temporal (frame delay) | Blends current + past frame at oscillating offset |
| `spatialflanger` | Spatial (pixel shift) | Per-row horizontal displacement with LFO |
| `hueflanger` | Color (hue rotation) | Blends frame with hue-rotated copy, angle oscillates |
| `freqflanger` | Frequency (FFT) | Blends FFT magnitude+phase with delayed frame |

---

### Phaser
**What it does:** Passes signal through a cascade of allpass filters, creating notches at harmonically-unrelated frequencies. Sounds smoother than flanging.

**Audio equivalent:** Swooshing, underwater, vocal coloring.

**Visual result:** Soft color-shifting waves, gentler than flanger's sharp bands.

```
Input ──┬──> Allpass 1 ──> Allpass 2 ──> ... ──> Allpass N ──> Mix ──> Output
        │                                                       ^
        └───────────────────────────────────────────────────────┘
```

**Key params:** `stages` (number of notches), `rate` (sweep speed), `feedback` (resonance)

**Entropic phasers:**
| Effect | Domain | What varies |
|--------|--------|-------------|
| `videophaser` | Frequency (FFT notches) | Classic sweeping allpass cascade |
| `channelphaser` | Per-channel (R/G/B) | Each color channel sweeps at different rate |
| `brightnessphaser` | Brightness bands | Inverts brightness in sweeping zones |
| `feedbackphaser` | Self-feeding FFT | Escalates feedback over time toward self-oscillation |

---

### Filter
**What it does:** Emphasizes or cuts specific frequency ranges in the spatial domain.

**Audio equivalent:** Synth filter sweep, wah pedal, EQ.

**Visual result:** Brightness banding, detail emphasis/removal at specific scales.

```
Input ──> FFT ──> Multiply by frequency mask ──> IFFT ──> Output
                       ^
                       └── LFO sweeps mask position
```

**Key params:** `frequency`/`q` (center + width), `gain` (boost), `rate` (sweep speed)

**Entropic filters:**
| Effect | Type | What it does |
|--------|------|-------------|
| `resonantfilter` | Bandpass | High-Q notch sweeps through spatial frequencies |
| `combfilter` | Comb | Multiple evenly-spaced teeth create interference |

---

### Modulator
**What it does:** Multiplies the signal by a carrier waveform, creating sum and difference frequencies (sidebands).

**Audio equivalent:** Ring mod, AM radio, robot voice.

**Visual result:** Striped patterns, color splitting, carrier frequency visible in output.

```
Input ──> Multiply ──> Output
              ^
              └── Carrier (sine/square/tri/saw)
```

**Key params:** `frequency` (carrier pitch), `depth` (mod amount), `mode` (am/fm/phase/multi)

**Entropic modulators:**
| Effect | What it does |
|--------|-------------|
| `ringmod` | 4 modes of carrier x signal multiplication |
| `gate` | Binary on/off based on threshold (like noise gate) |
| `wavefold` | Brightness reflects at threshold (harmonic distortion) |

---

### Reverb / Freeze
**What it does:** Accumulates echoes or freezes spectral content, creating persistence and trails.

**Audio equivalent:** Room reverb, convolution reverb, spectral freeze.

**Visual result:** Ghostly trails, persistence, frozen textures imposed on motion.

```
Input ──> Convolve with IR ──> Accumulate ──> Output
               ^
               └── Past frame as impulse response
```

**Entropic reverbs:**
| Effect | What it does |
|--------|-------------|
| `visualreverb` | Convolves with past frame as impulse response |
| `spectralfreeze` | Captures FFT magnitude and imposes on later frames |

---

## Quick Reference: All 16 Effects

| Effect | Type | Category | Sweeps? | Temporal? |
|--------|------|----------|---------|-----------|
| videoflanger | Flanger | modulation | Yes | Yes (frame buffer) |
| spatialflanger | Flanger | modulation | Yes | No (per-frame) |
| hueflanger | Flanger | modulation | Yes | No (per-frame) |
| freqflanger | Flanger | modulation | Yes | Yes (frame buffer) |
| videophaser | Phaser | modulation | Yes | No (per-frame) |
| channelphaser | Phaser | modulation | Yes | No (per-frame) |
| brightnessphaser | Phaser | modulation | Yes | No (per-frame) |
| feedbackphaser | Phaser | modulation | Yes | Yes (state accumulates) |
| resonantfilter | Filter | modulation | Yes | No (per-frame) |
| combfilter | Filter | modulation | Yes | No (per-frame) |
| ringmod | Modulator | modulation | Animates | No (per-frame) |
| gate | Modulator | modulation | No | No (per-frame) |
| wavefold | Modulator | modulation | No | No (per-frame) |
| spectralfreeze | Freeze | temporal | No | Yes (captures) |
| visualreverb | Reverb | temporal | No | Yes (convolves) |
| lfo | Operator | operators | Yes | No (modulates params) |

---

## How to Choose

| I want... | Use |
|-----------|-----|
| Metallic sweep, jet engine | `videoflanger` or `freqflanger` |
| Gentle color waves | `videophaser` or `channelphaser` |
| Psychedelic inversion | `brightnessphaser` |
| Synth filter sweep | `resonantfilter` |
| Striped carrier pattern | `ringmod` |
| Signal gating | `gate` |
| Harmonic distortion | `wavefold` |
| Ghost trails | `visualreverb` or `feedback` (temporal) |
| Frozen texture | `spectralfreeze` |
| Animate any parameter | `lfo` (operator) |
| Self-oscillation buildup | `feedbackphaser` |

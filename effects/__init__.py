"""
Entropic — Effects Registry
Auto-discovers effects and provides a uniform interface.
Every effect is a function: (frame: np.ndarray, **params) -> np.ndarray
"""

import numpy as np

from effects.pixelsort import pixelsort
from effects.channelshift import channelshift
from effects.scanlines import scanlines
from effects.bitcrush import bitcrush
from effects.color import (
    hue_shift,
    contrast_crush,
    saturation_warp,
    brightness_exposure,
    color_invert,
    color_temperature,
    tape_saturation,
    cyanotype,
    infrared,
    color_filter,
    chroma_key,
    luma_key,
    levels,
    curves,
    hsl_adjust,
    color_balance,
    compute_histogram,
)
from effects.distortion import (
    wave_distort,
    displacement,
    mirror,
    chromatic_aberration,
    pencil_sketch,
    cumulative_smear,
)
from effects.texture import (
    vhs,
    noise,
    posterize,
    edge_detect,
    blur,
    sharpen,
    tv_static,
    contour_lines,
)
from effects.temporal import stutter, frame_drop, time_stretch, feedback, tape_stop, tremolo, delay, decimator, sample_and_hold, granulator, beat_repeat, strobe, lfo
from effects.modulation import ring_mod, gate, wavefold
from effects.enhance import solarize, duotone, emboss, auto_levels, median_filter, false_color, histogram_eq, clahe, parallel_compression
from effects.destruction import (
    datamosh, byte_corrupt, block_corrupt, row_shift,
    jpeg_artifacts, invert_bands, data_bend, flow_distort,
    film_grain, glitch_repeat, xor_glitch,
    frame_smash, channel_destroy,
)
from effects.ascii import ascii_art, braille_art
from effects.sidechain import (
    sidechain_duck, sidechain_pump, sidechain_gate,
    sidechain_cross, sidechain_crossfeed, sidechain_interference,
    sidechain_operator,
)
from effects.dsp_filters import (
    video_flanger, video_phaser, spatial_flanger, channel_phaser,
    brightness_phaser, hue_flanger, resonant_filter, comb_filter,
    feedback_phaser, spectral_freeze, visual_reverb, freq_flanger,
)
from effects.adsr import adsr_wrap, ADSREnvelope
from effects.whimsy import (
    kaleidoscope, soft_bloom, shape_overlay, lens_flare,
    watercolor, rainbow_shift, sparkle, film_grain_warm,
)
from effects.physics import (
    pixel_liquify, pixel_gravity, pixel_vortex,
    pixel_explode, pixel_elastic, pixel_melt,
    pixel_blackhole, pixel_antigravity, pixel_magnetic,
    pixel_timewarp, pixel_dimensionfold,
    pixel_wormhole, pixel_quantum, pixel_darkenergy, pixel_superfluid,
    pixel_bubbles, pixel_inkdrop, pixel_haunt,
    pixel_xerox, pixel_fax, pixel_risograph,
    pixel_dynamics, pixel_cosmos, pixel_organic, pixel_decay,
)

# Real datamosh is video-level (not per-frame), but we register a marker
# so it appears in effect listings and can be referenced by recipes.
# Actual execution goes through entropic_datamosh.py or gradio_datamosh.py.
_REAL_DATAMOSH_REGISTERED = True

# Master registry: name -> (function, default_params, description)
EFFECTS = {
    # === GLITCH ===
    "pixelsort": {
        "fn": pixelsort,
        "category": "glitch",
        "params": {"threshold": 0.5, "sort_by": "brightness", "direction": "horizontal"},
        "description": "Sort pixels by brightness, hue, or saturation",
    },
    "channelshift": {
        "fn": channelshift,
        "category": "glitch",
        "params": {"r_offset": (10, 0), "g_offset": (0, 0), "b_offset": (-10, 0)},
        "description": "Offset RGB channels independently",
    },
    "displacement": {
        "fn": displacement,
        "category": "glitch",
        "params": {"block_size": 16, "intensity": 10.0, "seed": 42},
        "description": "Randomly displace image blocks",
    },
    "bitcrush": {
        "fn": bitcrush,
        "category": "glitch",
        "params": {"color_depth": 4, "resolution_scale": 1.0},
        "description": "Reduce color depth and/or resolution",
    },

    # === DISTORTION ===
    "pencilsketch": {
        "fn": pencil_sketch,
        "category": "distortion",
        "params": {"sigma_s": 60.0, "sigma_r": 0.07, "shade": 0.05},
        "description": "Pencil sketch drawing effect (OpenCV pencilSketch)",
    },
    "smear": {
        "fn": cumulative_smear,
        "category": "distortion",
        "params": {"direction": "horizontal", "decay": 0.95, "animate": False},
        "description": "Cumulative paint-smear / light-trail streaks (horizontal/vertical/diagonal_left/diagonal_right, animated rotation)",
    },
    "wave": {
        "fn": wave_distort,
        "category": "distortion",
        "params": {"amplitude": 10.0, "frequency": 0.05, "direction": "horizontal"},
        "description": "Sine wave displacement (horizontal/vertical/diagonal/circular)",
    },
    "mirror": {
        "fn": mirror,
        "category": "distortion",
        "params": {"axis": "vertical", "position": 0.5},
        "description": "Mirror one half onto the other",
    },
    "chromatic": {
        "fn": chromatic_aberration,
        "category": "distortion",
        "params": {"offset": 5, "direction": "horizontal"},
        "description": "RGB channel split (lens aberration)",
    },

    # === TEXTURE ===
    "tvstatic": {
        "fn": tv_static,
        "category": "texture",
        "params": {"intensity": 0.8, "sync_drift": 0.3, "seed": 42, "concentrate_x": 0.5, "concentrate_y": 0.5, "concentrate_radius": 0.0, "animate_displacement": False},
        "description": "TV static with horizontal sync drift (spatial concentration + animated displacement)",
    },
    "contours": {
        "fn": contour_lines,
        "category": "texture",
        "params": {"levels": 8, "outline_only": False},
        "description": "Topographic contour lines from luminance bands (outline_only=True overlays on original)",
    },
    "scanlines": {
        "fn": scanlines,
        "category": "texture",
        "params": {"line_width": 2, "opacity": 0.3, "flicker": False, "color": (0, 0, 0), "seed": 42},
        "description": "CRT/VHS scan line overlay",
    },
    "vhs": {
        "fn": vhs,
        "category": "texture",
        "params": {"tracking": 0.5, "noise_amount": 0.2, "color_bleed": 3, "seed": 42},
        "description": "VHS tape degradation simulation",
    },
    "noise": {
        "fn": noise,
        "category": "texture",
        "params": {"amount": 0.3, "noise_type": "gaussian", "seed": 42, "animate": False},
        "description": "Add grain/noise overlay (animate=True for motion noise)",
    },
    "blur": {
        "fn": blur,
        "category": "texture",
        "params": {"radius": 3, "blur_type": "box"},
        "description": "Blur (box/gaussian/motion/radial/median/lens)",
    },
    "sharpen": {
        "fn": sharpen,
        "category": "texture",
        "params": {"amount": 1.0},
        "description": "Sharpen/enhance edges",
    },
    "edges": {
        "fn": edge_detect,
        "category": "texture",
        "params": {"threshold": 0.3, "mode": "overlay", "edge_color": (255, 255, 255)},
        "param_ranges": {"threshold": {"min": 0.01, "max": 1.0}},
        "description": "Edge detection (overlay/neon/edges-only, colorizable edges, non-linear threshold)",
    },
    "posterize": {
        "fn": posterize,
        "category": "texture",
        "params": {"levels": 4},
        "description": "Reduce to N color levels per channel",
    },
    "asciiart": {
        "fn": ascii_art,
        "category": "texture",
        "params": {"charset": "basic", "width": 80, "invert": False, "color_mode": "mono", "edge_mix": 0.0},
        "description": "ASCII art (25 charsets incl. matrix/code/virus/daemon/hex/octal/base64/currency/katakana/runic, 5 colors: mono/green/amber/original/rainbow)",
    },
    "brailleart": {
        "fn": braille_art,
        "category": "texture",
        "params": {"width": 80, "threshold": 128, "invert": False, "dither": True, "color_mode": "mono"},
        "description": "Convert frame to braille unicode art (2×4 dot grid, 4× resolution, Floyd-Steinberg dither)",
    },

    # === COLOR ===
    "tapesaturation": {
        "fn": tape_saturation,
        "category": "color",
        "params": {"drive": 1.5, "warmth": 0.3, "mode": "vintage", "output_level": 0.85},
        "param_ranges": {"drive": {"min": 0.5, "max": 5.0}, "warmth": {"min": 0.0, "max": 1.0}, "output_level": {"min": 0.5, "max": 1.5}},
        "description": "Tape saturation — midpoint-preserving dynamics compression (vintage/hot/lo-fi)",
    },
    "colorfilter": {
        "fn": color_filter,
        "category": "color",
        "params": {"preset": "cyanotype", "intensity": 1.0},
        "description": "Color filter presets (cyanotype, infrared, sepia, cool, warm)",
    },
    "chroma_key": {
        "fn": chroma_key,
        "category": "color",
        "params": {"hue": 120.0, "tolerance": 30.0, "softness": 10.0, "replace_color": "transparent"},
        "param_ranges": {"hue": {"min": 0.0, "max": 360.0}, "tolerance": {"min": 5.0, "max": 90.0}, "softness": {"min": 0.0, "max": 50.0}},
        "description": "Green screen — key out a color range for transparency",
    },
    "luma_key": {
        "fn": luma_key,
        "category": "color",
        "params": {"threshold": 0.3, "mode": "dark", "softness": 10.0, "replace_color": "transparent"},
        "param_ranges": {"threshold": {"min": 0.0, "max": 1.0}, "softness": {"min": 0.0, "max": 50.0}},
        "description": "Luminance key — key out dark or bright areas for transparency",
    },
    "hueshift": {
        "fn": hue_shift,
        "category": "color",
        "params": {"degrees": 180},
        "description": "Rotate the hue wheel",
    },
    "contrast": {
        "fn": contrast_crush,
        "category": "color",
        "params": {"amount": 50, "curve": "linear"},
        "param_ranges": {"amount": {"min": 0, "max": 150}},
        "description": "Extreme contrast manipulation",
    },
    "saturation": {
        "fn": saturation_warp,
        "category": "color",
        "params": {"amount": 1.5, "channel": "all"},
        "param_ranges": {"amount": {"min": 0.0, "max": 4.0}},
        "description": "Boost or kill saturation",
    },
    "exposure": {
        "fn": brightness_exposure,
        "category": "color",
        "params": {"stops": 1.0, "clip_mode": "clip"},
        "param_ranges": {"stops": {"min": -3.0, "max": 3.0}},
        "description": "Push exposure up or down",
    },
    "invert": {
        "fn": color_invert,
        "category": "color",
        "params": {"channel": "all", "amount": 1.0},
        "description": "Full or partial color inversion",
    },
    "temperature": {
        "fn": color_temperature,
        "category": "color",
        "params": {"temp": 30},
        "description": "Warm/cool color temperature shift",
    },
    "levels": {
        "fn": levels,
        "category": "tools",
        "params": {"input_black": 0, "input_white": 255, "gamma": 1.0, "output_black": 0, "output_white": 255, "channel": "master"},
        "description": "Levels — remap black/white points with gamma curve (per-channel or master)",
    },
    "curves": {
        "fn": curves,
        "category": "tools",
        "params": {"points": [[0, 0], [64, 64], [128, 128], [192, 192], [255, 255]], "channel": "master", "interpolation": "cubic"},
        "description": "Curves — spline-based tonal adjustment via control points (per-channel or master)",
    },
    "hsladjust": {
        "fn": hsl_adjust,
        "category": "tools",
        "params": {"target_hue": "all", "hue_shift": 0, "saturation": 0, "lightness": 0},
        "description": "HSL Adjust — per-hue-range hue/saturation/lightness control (reds, greens, blues, etc.)",
    },
    "colorbalance": {
        "fn": color_balance,
        "category": "tools",
        "params": {"shadows_r": 0, "shadows_g": 0, "shadows_b": 0, "midtones_r": 0, "midtones_g": 0, "midtones_b": 0, "highlights_r": 0, "highlights_g": 0, "highlights_b": 0, "preserve_luminosity": True},
        "description": "Color Balance — shift RGB in shadows, midtones, and highlights independently",
    },

    # === TEMPORAL ===
    "stutter": {
        "fn": stutter,
        "category": "temporal",
        "params": {"repeat": 3, "interval": 8},
        "description": "Freeze-stutter: hold frames at intervals (skipping record)",
    },
    "dropout": {
        "fn": frame_drop,
        "category": "temporal",
        "params": {"drop_rate": 0.3, "seed": 42},
        "description": "Random frame drops to black (signal loss)",
    },
    "timestretch": {
        "fn": time_stretch,
        "category": "temporal",
        "params": {"speed": 0.5},
        "description": "Speed change with visual artifacts",
    },
    "feedback": {
        "fn": feedback,
        "category": "temporal",
        "params": {"decay": 0.3},
        "description": "Ghost trails from previous frames (video echo)",
    },
    "tapestop": {
        "fn": tape_stop,
        "category": "temporal",
        "params": {"trigger": 0.7, "ramp_frames": 15},
        "description": "Freeze and fade to black like a tape machine stopping",
    },
    "tremolo": {
        "fn": tremolo,
        "category": "temporal",
        "params": {"rate": 2.0, "depth": 0.5},
        "description": "Brightness oscillation over time (LFO on brightness)",
    },
    "delay": {
        "fn": delay,
        "category": "temporal",
        "params": {"delay_frames": 5, "decay": 0.4},
        "description": "Ghost echo from N frames ago (video delay line)",
    },
    "decimator": {
        "fn": decimator,
        "category": "temporal",
        "params": {"factor": 3},
        "description": "Reduce effective framerate (choppy lo-fi motion)",
    },
    "samplehold": {
        "fn": sample_and_hold,
        "category": "temporal",
        "params": {"hold_min": 4, "hold_max": 15, "seed": 42},
        "description": "Freeze at random intervals (sample & hold)",
    },
    "granulator": {
        "fn": granulator,
        "category": "temporal",
        "params": {
            "position": 0.5, "grain_size": 4, "spray": 0.0,
            "density": 1, "scan_speed": 0.0, "reverse_prob": 0.0, "seed": 42,
        },
        "description": "Video granular synthesis — rearrange slices by position, spray, grain size, density. Inspired by Ableton Granulator II.",
    },
    "beatrepeat": {
        "fn": beat_repeat,
        "category": "temporal",
        "params": {
            "interval": 16, "offset": 0, "gate": 8, "grid": 4,
            "variation": 0.0, "chance": 1.0, "decay": 0.0, "pitch_decay": 0.0, "seed": 42,
        },
        "description": "Triggered frame repetition — captures buffer on trigger and repeats with grid subdivision, decay, pitch decay. Inspired by Ableton Beat Repeat.",
    },
    "strobe": {
        "fn": strobe,
        "category": "temporal",
        "params": {
            "rate": 4.0, "color": "white", "shape": "full",
            "opacity": 1.0, "duty": 0.5, "seed": 42,
        },
        "description": "Video strobe — flash color/shape/invert at regular intervals. Colors: white, black, red, blue, green, invert, random. Shapes: full, circle, bars_h, bars_v, grid.",
    },
    "lfo": {
        "fn": lfo,
        "category": "temporal",
        "params": {
            "rate": 2.0, "depth": 0.5, "target": "brightness",
            "waveform": "sine", "seed": 42,
        },
        "param_descriptions": {"rate": "Oscillation speed in Hz", "depth": "Modulation amount (0=none, 1=full)", "target": "What gets modulated", "waveform": "Shape of oscillation"},
        "description": "LFO — controller that oscillates any parameter over time (not an effect itself). Targets: brightness, displacement, channelshift, blur, moire, glitch, invert, posterize. Waveforms: sine, square, saw, triangle, random.",
    },

    # === MODULATION ===
    "wavefold": {
        "fn": wavefold,
        "category": "modulation",
        "params": {"threshold": 0.7, "folds": 3, "brightness": 1.0},
        "description": "Audio wavefolding — pixel brightness folds at threshold (brightness compensation)",
    },
    "ringmod": {
        "fn": ring_mod,
        "category": "modulation",
        "params": {"frequency": 4.0, "direction": "horizontal", "mode": "am", "depth": 1.0, "source": "internal"},
        "param_descriptions": {"frequency": "Carrier cycles across frame", "direction": "Band orientation", "mode": "am=bands, fm=brightness-driven, phase=luminance shift, multi=per-RGB harmonics", "depth": "0=bypass, 1=full modulation", "source": "internal=sine wave, luminance=self-modulation"},
        "description": "Ring mod — 4 modes: am (classic bands), fm (brightness modulates freq), phase (luminance shifts phase), multi (3 harmonic carriers per RGB)",
    },
    "gate": {
        "fn": gate,
        "category": "modulation",
        "params": {"threshold": 0.3, "mode": "brightness"},
        "description": "Black out pixels below brightness threshold (noise gate)",
    },

    # === ENHANCE ===
    "histogrameq": {
        "fn": histogram_eq,
        "category": "enhance",
        "params": {"strength": 1.0},
        "description": "Per-channel histogram equalization (reveal hidden detail)",
    },
    "clahe": {
        "fn": clahe,
        "category": "enhance",
        "params": {"clip_limit": 2.0, "grid_size": 8},
        "description": "CLAHE — adaptive local contrast enhancement (night vision)",
    },
    "parallelcompress": {
        "fn": parallel_compression,
        "category": "enhance",
        "params": {"crush": 0.5, "blend": 0.5, "mode": "luminance"},
        "description": "Parallel compression (luminance/per_channel/saturation modes)",
    },
    "solarize": {
        "fn": solarize,
        "category": "enhance",
        "params": {"threshold": 128, "brightness": 1.0, "target": "all"},
        "description": "Partial inversion (Sabattier/Man Ray — target: all/shadows/midtones/highlights)",
    },
    "duotone": {
        "fn": duotone,
        "category": "enhance",
        "params": {"shadow_color": (0, 0, 80), "highlight_color": (255, 200, 100)},
        "description": "Two-color gradient mapping (graphic design aesthetic)",
    },
    "emboss": {
        "fn": emboss,
        "category": "enhance",
        "params": {"amount": 1.0, "transparent_bg": False},
        "description": "3D raised/carved texture effect (transparent_bg=True makes gray background black for overlay)",
    },
    "autolevels": {
        "fn": auto_levels,
        "category": "enhance",
        "params": {"cutoff": 5.0, "strength": 1.0},
        "description": "Auto-contrast histogram stretch (professional color correction)",
    },
    "median": {
        "fn": median_filter,
        "category": "enhance",
        "params": {"size": 5},
        "description": "Median filter (watercolor / noise reduction)",
    },
    "falsecolor": {
        "fn": false_color,
        "category": "enhance",
        "params": {"colormap": "jet"},
        "description": "Map luminance to false-color palette (thermal vision)",
    },

    # === DESTRUCTION ===
    "xorglitch": {
        "fn": xor_glitch,
        "category": "destruction",
        "params": {"pattern": 128, "mode": "fixed", "seed": 42},
        "description": "Bitwise XOR corruption (fixed/random/gradient/shift_self/invert_self/prev_frame)",
    },
    "datamosh": {
        "fn": datamosh,
        "category": "destruction",
        "params": {
            "intensity": 1.0, "accumulate": True, "decay": 0.95,
            "mode": "melt", "seed": 42, "motion_threshold": 0.0,
            "macroblock_size": 16, "donor_offset": 10, "blend_mode": "normal",
        },
        "param_descriptions": {"intensity": "Effect strength (higher=more destruction)", "accumulate": "Stack motion vectors across frames", "decay": "How fast accumulated motion fades", "mode": "melt/bloom/rip/replace/annihilate/freeze_through/pframe_extend/donor", "motion_threshold": "Ignore motion below this level", "macroblock_size": "Block size for motion estimation (8-64)", "donor_offset": "Frame offset for donor mode", "blend_mode": "How moshed pixels combine"},
        "description": "Datamosh (optical flow) — 8 modes: melt, bloom, rip, replace, annihilate, freeze_through (authentic I-frame removal), pframe_extend (P-frame duplication/bloom-glide), donor (cross-clip pixel feeding). Blend modes: normal, multiply, average, swap.",
    },
    "bytecorrupt": {
        "fn": byte_corrupt,
        "category": "destruction",
        "params": {"amount": 100, "jpeg_quality": 40, "seed": 42},
        "description": "JPEG data bending — corrupt compressed bytes for authentic glitch",
    },
    "blockcorrupt": {
        "fn": block_corrupt,
        "category": "destruction",
        "params": {"num_blocks": 15, "block_size": 32, "mode": "random", "placement": "random", "seed": 42},
        "description": "Corrupt macroblocks (shift/noise/repeat/invert/zero, placement: random/sequential/radial/edge_detected)",
    },
    "rowshift": {
        "fn": row_shift,
        "category": "destruction",
        "params": {"max_shift": 30, "density": 0.3, "direction": "horizontal", "seed": 42},
        "description": "Scanline tearing — rows/columns displaced (horizontal/vertical/both)",
    },
    "jpegdamage": {
        "fn": jpeg_artifacts,
        "category": "destruction",
        "params": {"quality": 5, "block_damage": 20, "seed": 42},
        "description": "Extreme JPEG compression + block corruption artifacts",
    },
    "invertbands": {
        "fn": invert_bands,
        "category": "destruction",
        "params": {"band_height": 10, "offset": 0, "direction": "horizontal"},
        "description": "Alternating inverted bands (horizontal/vertical, CRT damage)",
    },
    "databend": {
        "fn": data_bend,
        "category": "destruction",
        "params": {"effect": "echo", "intensity": 0.5, "seed": 42},
        "description": "Audio DSP on pixel data — echo, distort, bitcrush, reverse, feedback, tremolo, ringmod",
    },
    "flowdistort": {
        "fn": flow_distort,
        "category": "destruction",
        "params": {"strength": 3.0, "direction": "forward"},
        "description": "Warp frame using optical flow as displacement map",
    },
    "filmgrain": {
        "fn": film_grain,
        "category": "destruction",
        "params": {"intensity": 0.4, "grain_size": 2, "seed": 42, "animate": True},
        "description": "Realistic film grain (brightness-responsive, chunky texture, animate=True for moving grain)",
    },
    "glitchrepeat": {
        "fn": glitch_repeat,
        "category": "destruction",
        "params": {"num_slices": 8, "max_height": 20, "shift": True, "flicker": False, "seed": 42},
        "description": "Repeat and shift random horizontal slices (buffer overflow, flicker=True alternates glitched/clean)",
    },
    "framesmash": {
        "fn": frame_smash,
        "category": "destruction",
        "params": {"aggression": 0.5, "color_affect": True, "seed": 42},
        "description": "One-stop apocalypse — rows, blocks, channels, XOR, dissolve (color_affect=False for geometry-only)",
    },
    "channeldestroy": {
        "fn": channel_destroy,
        "category": "destruction",
        "params": {"mode": "separate", "intensity": 0.5, "seed": 42},
        "description": "Rip color channels apart — separate, swap, crush, eliminate, invert, XOR",
    },

    # === SIDECHAIN ===
    "sidechainduck": {
        "fn": sidechain_duck,
        "category": "sidechain",
        "params": {"source": "brightness", "threshold": 0.5, "ratio": 4.0, "attack": 0.3, "release": 0.7, "mode": "brightness", "invert": False, "seed": 42},
        "description": "Sidechain duck — key signal ducks brightness/saturation/blur/invert/displace",
        "alias_of": "sidechainoperator",
    },
    "sidechainpump": {
        "fn": sidechain_pump,
        "category": "sidechain",
        "params": {"rate": 2.0, "depth": 0.7, "curve": "exponential", "mode": "brightness", "seed": 42},
        "description": "Rhythmic sidechain pump — 4-on-the-floor ducking at fixed BPM",
        "alias_of": "sidechainoperator",
    },
    "sidechaingate": {
        "fn": sidechain_gate,
        "category": "sidechain",
        "params": {"source": "brightness", "threshold": 0.4, "mode": "freeze", "hold_frames": 5},
        "description": "Sidechain gate — video only passes when signal exceeds threshold",
        "alias_of": "sidechainoperator",
    },
    "sidechaincross": {
        "fn": sidechain_cross,
        "category": "sidechain",
        "params": {"source": "brightness", "threshold": 0.3, "softness": 0.3, "mode": "blend",
                   "strength": 0.8, "invert": False, "pre_a": "none", "pre_b": "none",
                   "attack": 0.0, "decay": 0.0, "sustain": 1.0, "release": 0.0,
                   "lookahead": 0},
        "param_descriptions": {"source": "What drives the sidechain (brightness/motion/edges)", "threshold": "Activation level (0=always on, 1=only peaks)", "softness": "Crossover smoothness", "mode": "How videos combine (blend/reveal/mask)", "strength": "Overall effect amount", "invert": "Flip which video shows", "pre_a": "Pre-process main video", "pre_b": "Pre-process sidechain video", "attack": "Envelope attack time", "decay": "Envelope decay time", "sustain": "Sustain level", "release": "Release time", "lookahead": "Frame lookahead for timing"},
        "description": "Cross-video sidechain — one video busts through another with ADSR envelope and pre-processing",
        "alias_of": "sidechainoperator",
    },
    "sidechaincrossfeed": {
        "fn": sidechain_crossfeed,
        "category": "sidechain",
        "params": {"channel_map": "rgb_shift", "strength": 0.7},
        "param_ranges": {"strength": {"min": 0.0, "max": 1.0}},
        "param_options": {"channel_map": ["rgb_shift", "blend", "multiply", "screen", "difference", "color_steal", "luminance_steal", "displace", "spectral_split", "phase", "beat"]},
        "param_descriptions": {"channel_map": "How channels cross-feed between videos", "strength": "Effect intensity"},
        "description": "Cross-channel feed — mix color channels between two videos (self-interference when solo)",
        "alias_of": "sidechainoperator",
    },
    "sidechaininterference": {
        "fn": sidechain_interference,
        "category": "sidechain",
        "params": {"mode": "phase", "strength": 0.7},
        "param_ranges": {"strength": {"min": 0.0, "max": 1.0}},
        "param_options": {"mode": ["phase", "beat", "spectral_split", "difference"]},
        "param_descriptions": {"mode": "Interference type (phase=FFT ghosting, beat=additive)", "strength": "Effect intensity"},
        "description": "Signal interference — FFT phase blending, beat patterns, spectral splits between videos",
        "alias_of": "sidechainoperator",
    },
    "sidechainoperator": {
        "fn": sidechain_operator,
        "category": "sidechain",
        "params": {"mode": "duck", "source": "brightness", "threshold": 0.5, "seed": 42},
        "description": "Sidechain Operator — 4 modes: duck, pump, gate, cross",
    },

    # === PIXEL PHYSICS ===
    "pixelliquify": {
        "fn": pixel_liquify,
        "category": "physics",
        "params": {"viscosity": 0.92, "turbulence": 3.0, "flow_scale": 40.0, "speed": 1.0, "seed": 42, "boundary": "wrap"},
        "param_ranges": {"viscosity": {"min": 0.8, "max": 0.99}, "turbulence": {"min": 0.5, "max": 10.0}, "flow_scale": {"min": 10.0, "max": 100.0}, "speed": {"min": 0.1, "max": 3.0}},
        "description": "Liquify — pixels become fluid and wash around in turbulent flow",
        "alias_of": "pixeldynamics",
    },
    "pixelgravity": {
        "fn": pixel_gravity,
        "category": "physics",
        "params": {"num_attractors": 5, "gravity_strength": 8.0, "damping": 0.95, "attractor_radius": 0.3, "wander": 0.5, "seed": 42, "boundary": "black"},
        "param_ranges": {"num_attractors": {"min": 1, "max": 20}, "gravity_strength": {"min": 1.0, "max": 30.0}, "damping": {"min": 0.8, "max": 0.99}, "attractor_radius": {"min": 0.1, "max": 1.0}, "wander": {"min": 0.0, "max": 2.0}},
        "description": "Gravity attractors — pixels get pulled toward random wandering points",
        "alias_of": "pixeldynamics",
    },
    "pixelvortex": {
        "fn": pixel_vortex,
        "category": "physics",
        "params": {"num_vortices": 3, "spin_strength": 5.0, "pull_strength": 2.0, "radius": 0.25, "damping": 0.93, "seed": 42, "boundary": "wrap"},
        "param_ranges": {"num_vortices": {"min": 1, "max": 10}, "spin_strength": {"min": 1.0, "max": 20.0}, "pull_strength": {"min": 0.0, "max": 10.0}, "radius": {"min": 0.1, "max": 1.0}, "damping": {"min": 0.8, "max": 0.99}},
        "description": "Vortex — swirling whirlpools pull pixels into spirals",
        "alias_of": "pixeldynamics",
    },
    "pixelexplode": {
        "fn": pixel_explode,
        "category": "physics",
        "params": {"origin": "center", "force": 10.0, "damping": 0.96, "gravity": 0.0, "scatter": 0.0, "seed": 42, "boundary": "black"},
        "param_ranges": {"force": {"min": 1.0, "max": 30.0}, "damping": {"min": 0.8, "max": 0.99}, "gravity": {"min": 0.0, "max": 5.0}, "scatter": {"min": 0.0, "max": 5.0}},
        "description": "Explode — pixels blast outward from a point with optional gravity",
        "alias_of": "pixeldynamics",
    },
    "pixelelastic": {
        "fn": pixel_elastic,
        "category": "physics",
        "params": {"stiffness": 0.3, "mass": 1.0, "force_type": "turbulence", "force_strength": 5.0, "damping": 0.9, "concentrate_x": 0.5, "concentrate_y": 0.5, "concentrate_radius": 0.0, "seed": 42, "boundary": "mirror"},
        "param_ranges": {"stiffness": {"min": 0.05, "max": 0.8}, "mass": {"min": 0.1, "max": 5.0}, "force_strength": {"min": 1.0, "max": 20.0}, "damping": {"min": 0.8, "max": 0.99}},
        "param_descriptions": {"stiffness": "Spring return force (high=snappy, low=loose)", "mass": "Pixel inertia (high=slow heavy movement)", "force_type": "turbulence/brightness/edges/radial/vortex/wave", "force_strength": "How hard the force pushes", "damping": "Velocity decay (high=more damped)", "concentrate_x": "Focus point X (0-1)", "concentrate_y": "Focus point Y (0-1)", "concentrate_radius": "Focus area size (0=everywhere)"},
        "description": "Elastic — springs + 6 forces (turbulence/brightness/edges/radial/vortex/wave) + spatial concentration",
        "alias_of": "pixeldynamics",
    },
    "pixelmelt": {
        "fn": pixel_melt,
        "category": "physics",
        "params": {"heat": 3.0, "gravity": 2.0, "viscosity": 0.95, "melt_source": "top", "seed": 42, "boundary": "black"},
        "param_ranges": {"heat": {"min": 0.0, "max": 10.0}, "gravity": {"min": 0.5, "max": 10.0}, "viscosity": {"min": 0.85, "max": 0.99}},
        "description": "Melt — pixels drip and flow downward like melting wax",
        "alias_of": "pixeldynamics",
    },

    # === IMPOSSIBLE PHYSICS ===
    "pixelblackhole": {
        "fn": pixel_blackhole,
        "category": "physics",
        "params": {"mass": 10.0, "spin": 3.0, "event_horizon": 0.08, "spaghettify": 5.0, "accretion_glow": 0.8, "hawking": 0.0, "position": "center", "seed": 42, "boundary": "black"},
        "param_ranges": {"mass": {"min": 1.0, "max": 30.0}, "spin": {"min": 0.0, "max": 10.0}, "event_horizon": {"min": 0.02, "max": 0.3}, "spaghettify": {"min": 0.0, "max": 15.0}, "accretion_glow": {"min": 0.0, "max": 2.0}, "hawking": {"min": 0.0, "max": 3.0}},
        "description": "Black hole — singularity with event horizon, spaghettification, and accretion glow",
        "alias_of": "pixelcosmos",
    },
    "pixelantigravity": {
        "fn": pixel_antigravity,
        "category": "physics",
        "params": {"repulsion": 8.0, "num_zones": 4, "zone_radius": 0.2, "oscillate": 1.0, "damping": 0.93, "seed": 42, "boundary": "wrap"},
        "param_ranges": {"repulsion": {"min": 1.0, "max": 20.0}, "num_zones": {"min": 1, "max": 10}, "zone_radius": {"min": 0.1, "max": 0.8}, "oscillate": {"min": 0.0, "max": 3.0}, "damping": {"min": 0.8, "max": 0.99}},
        "description": "Anti-gravity — repulsion zones push pixels outward with oscillating direction",
        "alias_of": "pixelcosmos",
    },
    "pixelmagnetic": {
        "fn": pixel_magnetic,
        "category": "physics",
        "params": {"field_type": "dipole", "strength": 6.0, "poles": 2, "rotation_speed": 0.5, "damping": 0.92, "seed": 42, "boundary": "wrap"},
        "param_ranges": {"strength": {"min": 1.0, "max": 20.0}, "poles": {"min": 2, "max": 8}, "rotation_speed": {"min": 0.0, "max": 2.0}, "damping": {"min": 0.8, "max": 0.99}},
        "param_visibility": {"poles": {"hidden_when": {"field_type": "chaotic"}}},
        "param_descriptions": {"field_type": "dipole/quadrupole/toroidal/chaotic", "strength": "Field intensity", "poles": "Number of magnetic poles (quad/toroidal only)", "rotation_speed": "Field rotation over time", "damping": "Velocity decay"},
        "description": "Magnetic fields — pixels curve along dipole/quadrupole/toroidal field lines",
        "alias_of": "pixelcosmos",
    },
    "pixeltimewarp": {
        "fn": pixel_timewarp,
        "category": "physics",
        "params": {"warp_speed": 2.0, "echo_count": 3, "echo_decay": 0.6, "reverse_probability": 0.3, "damping": 0.9, "seed": 42, "boundary": "wrap"},
        "param_ranges": {"warp_speed": {"min": 0.5, "max": 10.0, "ui_min": 0.5, "ui_max": 6.0}, "echo_count": {"min": 1, "max": 8, "ui_min": 1, "ui_max": 5}, "echo_decay": {"min": 0.1, "max": 1.0}, "reverse_probability": {"min": 0.0, "max": 1.0}, "damping": {"min": 0.5, "max": 1.0}},
        "description": "Time warp — displacement reverses with ghosting echoes",
        "alias_of": "pixelcosmos",
    },
    "pixeldimensionfold": {
        "fn": pixel_dimensionfold,
        "category": "physics",
        "params": {"num_folds": 3, "fold_depth": 8.0, "fold_width": 0.15, "rotation_speed": 0.3, "mirror_folds": True, "seed": 42, "boundary": "wrap"},
        "param_ranges": {"num_folds": {"min": 1, "max": 8, "ui_min": 1, "ui_max": 5}, "fold_depth": {"min": 1.0, "max": 20.0, "ui_min": 2.0, "ui_max": 12.0}, "fold_width": {"min": 0.02, "max": 0.5, "ui_min": 0.05, "ui_max": 0.3}, "rotation_speed": {"min": 0.0, "max": 2.0}},
        "description": "Dimension fold — space folds over itself along rotating axes",
        "alias_of": "pixelcosmos",
    },
    "pixelwormhole": {
        "fn": pixel_wormhole,
        "category": "physics",
        "params": {"portal_radius": 0.1, "tunnel_strength": 8.0, "spin": 2.0, "distortion_ring": 1.5, "wander": 0.3, "center_x": 0.5, "center_y": 0.5, "damping": 0.9, "seed": 42, "boundary": "black"},
        "param_ranges": {"portal_radius": {"min": 0.02, "max": 0.4, "ui_min": 0.05, "ui_max": 0.25}, "tunnel_strength": {"min": 1.0, "max": 20.0, "ui_min": 2.0, "ui_max": 12.0}, "spin": {"min": 0.0, "max": 8.0, "ui_min": 0.0, "ui_max": 4.0}, "distortion_ring": {"min": 0.5, "max": 5.0}, "wander": {"min": 0.0, "max": 1.0}, "center_x": {"min": 0.0, "max": 1.0}, "center_y": {"min": 0.0, "max": 1.0}, "damping": {"min": 0.5, "max": 1.0}},
        "description": "Wormhole — paired portals with position control (center_x/center_y)",
        "alias_of": "pixelcosmos",
    },
    "pixelquantum": {
        "fn": pixel_quantum,
        "category": "physics",
        "params": {"tunnel_prob": 0.3, "barrier_count": 4, "barrier_width": 0.05, "uncertainty": 5.0, "superposition": 0.4, "decoherence": 0.02, "seed": 42, "boundary": "wrap"},
        "param_ranges": {"tunnel_prob": {"min": 0.0, "max": 1.0}, "barrier_count": {"min": 2, "max": 10}, "barrier_width": {"min": 0.01, "max": 0.15}, "uncertainty": {"min": 0.0, "max": 15.0}, "superposition": {"min": 0.0, "max": 1.0}, "decoherence": {"min": 0.0, "max": 0.1}},
        "param_descriptions": {"tunnel_prob": "Chance pixels teleport through barriers", "barrier_count": "Number of quantum barriers", "barrier_width": "Width of each barrier zone", "uncertainty": "Heisenberg displacement randomness", "superposition": "Ghost intensity (0=no ghosts)", "decoherence": "How fast ghosts fade per frame"},
        "description": "Quantum — pixels tunnel through barriers and split into superposition ghosts",
        "alias_of": "pixelcosmos",
    },
    "pixeldarkenergy": {
        "fn": pixel_darkenergy,
        "category": "physics",
        "params": {"expansion_rate": 3.0, "acceleration": 0.05, "void_color": [5, 0, 15], "structure": 0.5, "hubble_zones": 6, "seed": 42, "boundary": "black"},
        "param_ranges": {"expansion_rate": {"min": 0.5, "max": 10.0, "ui_min": 1.0, "ui_max": 6.0}, "acceleration": {"min": 0.0, "max": 0.2, "ui_min": 0.01, "ui_max": 0.1}, "structure": {"min": 0.0, "max": 1.0}, "hubble_zones": {"min": 2, "max": 12, "ui_min": 3, "ui_max": 8}},
        "description": "Dark energy — accelerating Hubble expansion tears pixels apart, reveals void",
        "alias_of": "pixelcosmos",
    },
    "pixelsuperfluid": {
        "fn": pixel_superfluid,
        "category": "physics",
        "params": {"flow_speed": 6.0, "quantized_vortices": 5, "vortex_strength": 4.0, "climb_force": 2.0, "viscosity": 0.0, "thermal_noise": 0.5, "seed": 42, "boundary": "wrap"},
        "param_ranges": {"flow_speed": {"min": 1.0, "max": 15.0, "ui_min": 2.0, "ui_max": 10.0}, "quantized_vortices": {"min": 1, "max": 12, "ui_min": 2, "ui_max": 8}, "vortex_strength": {"min": 0.5, "max": 10.0, "ui_min": 1.0, "ui_max": 6.0}, "climb_force": {"min": 0.0, "max": 8.0, "ui_min": 0.5, "ui_max": 4.0}, "viscosity": {"min": 0.0, "max": 1.0}, "thermal_noise": {"min": 0.0, "max": 2.0}},
        "description": "Superfluid — zero-friction flow with quantized vortices that climb edges",
        "alias_of": "pixelcosmos",
    },
    "pixelbubbles": {
        "fn": pixel_bubbles,
        "category": "physics",
        "params": {"num_portals": 6, "min_radius": 0.03, "max_radius": 0.12, "pull_strength": 6.0, "spin": 1.5, "void_mode": "black", "wander": 0.4, "damping": 0.91, "seed": 42, "boundary": "black"},
        "param_ranges": {"num_portals": {"min": 1, "max": 15, "ui_min": 2, "ui_max": 10}, "min_radius": {"min": 0.01, "max": 0.2}, "max_radius": {"min": 0.05, "max": 0.4, "ui_min": 0.05, "ui_max": 0.25}, "pull_strength": {"min": 1.0, "max": 15.0, "ui_min": 2.0, "ui_max": 10.0}, "spin": {"min": 0.0, "max": 5.0}, "wander": {"min": 0.0, "max": 1.0}, "damping": {"min": 0.5, "max": 1.0}},
        "description": "Bubbles — multiple portals of random size with negative space void inside",
        "alias_of": "pixelorganic",
    },
    "pixelinkdrop": {
        "fn": pixel_inkdrop,
        "category": "physics",
        "params": {"num_drops": 4, "diffusion_rate": 3.0, "surface_tension": 0.6, "marangoni": 2.0, "tendrils": 8, "drop_interval": 0.3, "color_shift": 0.5, "seed": 42, "boundary": "wrap"},
        "param_ranges": {"num_drops": {"min": 1, "max": 10, "ui_min": 1, "ui_max": 6}, "diffusion_rate": {"min": 0.5, "max": 8.0, "ui_min": 1.0, "ui_max": 5.0}, "surface_tension": {"min": 0.0, "max": 1.0}, "marangoni": {"min": 0.0, "max": 6.0, "ui_min": 0.5, "ui_max": 4.0}, "tendrils": {"min": 2, "max": 16, "ui_min": 4, "ui_max": 12}, "drop_interval": {"min": 0.1, "max": 1.0}, "color_shift": {"min": 0.0, "max": 1.0}},
        "description": "Ink drop — paint in water with diffusion, surface tension, and Marangoni tendrils",
        "alias_of": "pixelorganic",
    },
    "pixelhaunt": {
        "fn": pixel_haunt,
        "category": "physics",
        "params": {"force_type": "turbulence", "force_strength": 4.0, "ghost_persistence": 0.95, "ghost_opacity": 0.4, "crackle": 0.3, "damping": 0.9, "seed": 42, "boundary": "wrap"},
        "param_ranges": {"force_strength": {"min": 0.5, "max": 10.0, "ui_min": 1.0, "ui_max": 6.0}, "ghost_persistence": {"min": 0.5, "max": 1.0, "ui_min": 0.7, "ui_max": 0.99}, "ghost_opacity": {"min": 0.0, "max": 1.0}, "crackle": {"min": 0.0, "max": 1.0}, "damping": {"min": 0.5, "max": 1.0}},
        "description": "Haunt — ghostly afterimages linger where pixels used to be (hauntology)",
        "alias_of": "pixelorganic",
    },

    # === PRINT DEGRADATION ===
    "pixelxerox": {
        "fn": pixel_xerox,
        "category": "destruction",
        "params": {"generations": 8, "contrast_gain": 1.15, "noise_amount": 0.06, "halftone_size": 4, "edge_fuzz": 1.5, "toner_skip": 0.05, "style": "copy", "seed": 42, "boundary": "clamp"},
        "description": "Xerox — generational copy loss (styles: copy/faded/harsh/zine)",
        "alias_of": "pixeldecay",
    },
    "pixelfax": {
        "fn": pixel_fax,
        "category": "destruction",
        "params": {"scan_noise": 0.3, "toner_bleed": 2.0, "paper_texture": 0.4, "compression_bands": 8, "thermal_fade": 0.2, "dither": True, "seed": 42, "boundary": "clamp"},
        "description": "Fax — thermal printing artifacts, scan noise, toner bleed, paper texture",
        "alias_of": "pixeldecay",
    },
    "pixelrisograph": {
        "fn": pixel_risograph,
        "category": "destruction",
        "params": {"ink_bleed": 2.5, "registration_offset": 3, "paper_grain": 0.3, "ink_coverage": 0.85, "num_colors": 2, "palette": "classic", "color_a": [0, 90, 180], "color_b": [220, 50, 50], "seed": 42, "boundary": "clamp"},
        "description": "Risograph — palettes: classic/zine/punk/ocean/sunset/custom (color_a/color_b for custom)",
        "alias_of": "pixeldecay",
    },

    # === DSP FILTERS ===
    "videoflanger": {
        "fn": video_flanger,
        "category": "modulation",
        "params": {"rate": 0.5, "depth": 10, "feedback": 0.4, "wet": 0.5},
        "param_descriptions": {"rate": "Sweep speed in Hz", "depth": "Max delay offset in frames", "feedback": "Recirculated signal (0=clean, 0.9=resonant)", "wet": "Effect mix amount"},
        "description": "Flanger — sharp, evenly-spaced interference bands that sweep up and down (comb filter from oscillating frame delay)",
    },
    "videophaser": {
        "fn": video_phaser,
        "category": "modulation",
        "params": {"rate": 0.3, "stages": 4, "depth": 1.0, "feedback": 0.3},
        "param_descriptions": {"rate": "Sweep speed in Hz", "stages": "Number of allpass notches (more = richer)", "depth": "How far notches sweep", "feedback": "Resonance at notch frequencies"},
        "description": "Phaser — gentle color-shifting waves from sweeping allpass notch filters (smoother than flanger)",
    },
    "spatialflanger": {
        "fn": spatial_flanger,
        "category": "modulation",
        "params": {"rate": 0.8, "depth": 20, "feedback": 0.3},
        "description": "Per-row horizontal shift with LFO — diagonal sweep flanging",
    },
    "channelphaser": {
        "fn": channel_phaser,
        "category": "modulation",
        "params": {"r_rate": 0.05, "g_rate": 0.3, "b_rate": 1.2, "stages": 5, "depth": 1.5, "wet": 0.8},
        "description": "Per-channel FFT phase sweep at different rates — color fringing and tearing",
    },
    "brightnessphaser": {
        "fn": brightness_phaser,
        "category": "modulation",
        "params": {"rate": 0.25, "bands": 6, "depth": 0.3, "strength": 0.8},
        "description": "Sweeping brightness inversion bands — psychedelic solarization sweep",
    },
    "hueflanger": {
        "fn": hue_flanger,
        "category": "color",
        "params": {"rate": 0.3, "depth": 60.0, "sat_depth": 0.0},
        "description": "Blend with hue-rotated copy, rotation oscillates — color interference",
    },
    "resonantfilter": {
        "fn": resonant_filter,
        "category": "modulation",
        "params": {"rate": 0.2, "q": 50.0, "gain": 3.0, "wet": 0.7},
        "description": "High-Q bandpass sweep through spatial frequencies — synth filter on video",
    },
    "combfilter": {
        "fn": comb_filter,
        "category": "modulation",
        "params": {"teeth": 7, "spacing": 8, "rate": 0.3, "depth": 3.0, "wet": 0.7},
        "description": "Multi-tooth spatial comb filter — offset copies create interference patterns",
    },
    "feedbackphaser": {
        "fn": feedback_phaser,
        "category": "modulation",
        "params": {"rate": 0.3, "stages": 6, "feedback": 0.5, "escalation": 0.01},
        "description": "Self-feeding 2D FFT phaser that escalates over time — builds to self-oscillation",
    },
    "spectralfreeze": {
        "fn": spectral_freeze,
        "category": "temporal",
        "params": {"interval": 30, "blend_peak": 0.7, "envelope_frames": 25},
        "description": "Freeze frequency magnitude at intervals, impose on later frames — spectral imprint",
    },
    "visualreverb": {
        "fn": visual_reverb,
        "category": "temporal",
        "params": {"rate": 0.15, "depth": 0.5, "ir_interval": 30},
        "description": "Convolve frame with past frame as impulse response — visual echo/room",
    },
    "freqflanger": {
        "fn": freq_flanger,
        "category": "modulation",
        "params": {"rate": 0.5, "depth": 10, "mag_blend": 0.4, "phase_blend": 0.15},
        "description": "2D FFT magnitude+phase blend with delayed frame — spectral ghosting",
    },

    # === MEGA-EFFECTS (unified wrappers) ===
    "pixeldynamics": {
        "fn": pixel_dynamics,
        "category": "physics",
        "params": {"mode": "liquify", "viscosity": 0.92, "turbulence": 3.0, "speed": 1.0, "seed": 42, "boundary": "wrap"},
        "description": "Pixel Dynamics — 6 modes: liquify, gravity, vortex, explode, elastic, melt",
    },
    "pixelcosmos": {
        "fn": pixel_cosmos,
        "category": "physics",
        "params": {"mode": "blackhole", "mass": 10.0, "spin": 3.0, "seed": 42, "boundary": "black"},
        "description": "Pixel Cosmos — 9 modes: blackhole, antigravity, magnetic, timewarp, dimensionfold, wormhole, quantum, darkenergy, superfluid",
    },
    "pixelorganic": {
        "fn": pixel_organic,
        "category": "physics",
        "params": {"mode": "bubbles", "num_portals": 6, "pull_strength": 6.0, "seed": 42, "boundary": "black"},
        "description": "Pixel Organic — 3 modes: bubbles, inkdrop, haunt",
    },
    "pixeldecay": {
        "fn": pixel_decay,
        "category": "destruction",
        "params": {"mode": "xerox", "generations": 8, "seed": 42, "boundary": "clamp"},
        "description": "Pixel Decay — 3 modes: xerox, fax, risograph",
    },

    # === WHIMSY ===
    "kaleidoscope": {
        "fn": kaleidoscope,
        "category": "whimsy",
        "params": {"segments": 6, "rotation": 0.0, "center_x": 0.5, "center_y": 0.5, "zoom": 1.0, "mood": "classic"},
        "param_ranges": {"segments": {"min": 2, "max": 16}, "rotation": {"min": 0, "max": 360}, "zoom": {"min": 0.5, "max": 3.0}},
        "description": "Kaleidoscope — mirror segments radiating from center (classic/psychedelic/soft moods)",
    },
    "softbloom": {
        "fn": soft_bloom,
        "category": "whimsy",
        "params": {"radius": 15, "intensity": 0.6, "threshold": 180, "tint_r": 255, "tint_g": 240, "tint_b": 220, "mood": "dreamy"},
        "param_ranges": {"radius": {"min": 3, "max": 50}, "intensity": {"min": 0.0, "max": 2.0}, "threshold": {"min": 50, "max": 250}},
        "description": "Soft bloom — dreamy glow where bright areas bleed soft light (dreamy/neon/ethereal moods)",
    },
    "shapeoverlay": {
        "fn": shape_overlay,
        "category": "whimsy",
        "params": {"shape": "circle", "count": 5, "size": 0.1, "opacity": 0.4, "color_r": 255, "color_g": 100, "color_b": 100, "filled": True, "animate": True, "speed": 1.0, "orientation": "random", "mood": "playful", "seed": 42},
        "param_ranges": {"count": {"min": 1, "max": 30}, "size": {"min": 0.02, "max": 0.5}, "opacity": {"min": 0.0, "max": 1.0}, "speed": {"min": 0.0, "max": 5.0}},
        "description": "Floating shapes — circles, triangles, stars, hearts overlaid (playful/minimal/chaos, grid/spiral/cascade/random placement)",
    },
    "lensflare": {
        "fn": lens_flare,
        "category": "whimsy",
        "params": {"position_x": 0.3, "position_y": 0.3, "intensity": 0.7, "size": 0.15, "color_r": 255, "color_g": 200, "color_b": 100, "streaks": 6, "animate": True, "drift_speed": 0.5, "mood": "cinematic"},
        "param_ranges": {"intensity": {"min": 0.0, "max": 2.0}, "size": {"min": 0.02, "max": 0.5}, "streaks": {"min": 0, "max": 12}, "drift_speed": {"min": 0.0, "max": 3.0}},
        "description": "Lens flare — animated with streaks, ghost orbs, and position drift (cinematic/retro/sci_fi moods)",
    },
    "watercolor": {
        "fn": watercolor,
        "category": "whimsy",
        "params": {"edge_strength": 0.5, "blur_radius": 7, "paper_texture": 0.3, "saturation_boost": 1.2, "mood": "classic", "seed": 42},
        "param_ranges": {"edge_strength": {"min": 0.0, "max": 1.0}, "blur_radius": {"min": 1, "max": 20}, "paper_texture": {"min": 0.0, "max": 1.0}, "saturation_boost": {"min": 0.5, "max": 2.5}},
        "description": "Watercolor paint — soft bleeding edges on paper texture (classic/vibrant/faded moods)",
    },
    "rainbowshift": {
        "fn": rainbow_shift,
        "category": "whimsy",
        "params": {"speed": 1.0, "direction": "horizontal", "opacity": 0.4, "wave": True, "mood": "smooth"},
        "param_ranges": {"speed": {"min": 0.0, "max": 5.0}, "opacity": {"min": 0.0, "max": 1.0}},
        "description": "Rainbow shift — animated gradient sweep (smooth/bands/prismatic, horizontal/vertical/diagonal/radial)",
    },
    "sparkle": {
        "fn": sparkle,
        "category": "whimsy",
        "params": {"density": 0.002, "size": 3, "brightness": 1.0, "color_r": 255, "color_g": 255, "color_b": 255, "animate": True, "twinkle_speed": 2.0, "spread": "random", "mood": "glitter", "seed": 42},
        "param_ranges": {"density": {"min": 0.0005, "max": 0.01}, "size": {"min": 1, "max": 10}, "brightness": {"min": 0.0, "max": 2.0}, "twinkle_speed": {"min": 0.0, "max": 5.0}},
        "description": "Sparkle/glitter — animated twinkle overlay (glitter/fairy/frost, random/highlights/edges spread)",
    },
    "filmgrainwarm": {
        "fn": film_grain_warm,
        "category": "whimsy",
        "params": {"amount": 0.15, "size": 1.0, "warmth": 0.3, "flicker": True, "mood": "vintage", "seed": 42},
        "param_ranges": {"amount": {"min": 0.01, "max": 0.5}, "size": {"min": 0.5, "max": 4.0}, "warmth": {"min": 0.0, "max": 1.0}},
        "description": "Warm film grain — organic texture with color warmth (vintage/kodak/expired moods)",
    },

    # === REAL DATAMOSH (video-level, not per-frame) ===
    "realdatamosh": {
        "fn": None,  # Video-level effect — use entropic_datamosh.py or gradio_datamosh.py
        "category": "destruction",
        "params": {
            "mode": "splice",
            "switch_frame": 30,
            "interval": 15,
            "rotation": 0.0,
            "x_offset": 0,
            "y_offset": 0,
            "motion_pattern": "static",
        },
        "description": "REAL H.264 P-frame datamosh (not simulation). Modes: splice, interleave, replace, multi, strategic. Requires two input videos. Use 'entropic_datamosh.py' CLI or 'python gradio_datamosh.py' for browser UI.",
        "video_level": True,  # Flag: this effect operates on full video, not single frames
    },
}

# Category display order and labels
CATEGORIES = {
    "physics": "PHYSICS",
    "glitch": "GLITCH",
    "distortion": "DISTORTION",
    "color": "COLOR",
    "tools": "TOOLS",
    "texture": "TEXTURE",
    "temporal": "TEMPORAL",
    "modulation": "MODULATION",
    "sidechain": "SIDECHAIN",
    "enhance": "ENHANCE",
    "destruction": "DESTRUCTION",
    "whimsy": "WHIMSY",
}

# Ordered list for UI folder rendering
CATEGORY_ORDER = list(CATEGORIES.keys())


def get_effect(name: str):
    """Get an effect by name. Returns (fn, default_params).

    Raises ValueError if effect doesn't exist or is video-level only
    (video-level effects like realdatamosh operate on full videos, not single frames).
    """
    if name not in EFFECTS:
        available = ", ".join(sorted(EFFECTS.keys()))
        raise ValueError(f"Unknown effect: {name}. Available: {available}")
    entry = EFFECTS[name]
    if entry["fn"] is None:
        raise ValueError(
            f"'{name}' is a video-level effect (operates on full videos, not single frames). "
            f"Use entropic_datamosh.py CLI or 'python entropic.py datamosh' instead."
        )
    return entry["fn"], entry["params"].copy()


def is_video_level(name: str) -> bool:
    """Check if an effect is video-level (not per-frame)."""
    return EFFECTS.get(name, {}).get("video_level", False)


def list_effects(category: str = None) -> list[dict]:
    """List all available effects with descriptions.

    Args:
        category: Optional filter — only return effects in this category.
    """
    results = []
    for name, entry in EFFECTS.items():
        if category and entry.get("category") != category:
            continue
        results.append({
            "name": name,
            "description": entry["description"],
            "params": entry["params"],
            "category": entry.get("category", "other"),
        })
    return results


def list_categories() -> list[str]:
    """Return ordered list of category keys."""
    return list(CATEGORIES.keys())


def search_effects(query: str, max_query_len: int = 200) -> list[dict]:
    """Search effects by name or description substring."""
    if len(query) > max_query_len:
        raise ValueError(f"Search query too long (max {max_query_len} chars)")
    query_lower = query.lower()
    results = []
    for name, entry in EFFECTS.items():
        if query_lower in name or query_lower in entry["description"].lower():
            results.append({
                "name": name,
                "description": entry["description"],
                "params": entry["params"],
                "category": entry.get("category", "other"),
            })
    return results


def apply_effect(frame, effect_name: str, frame_index: int = 0, total_frames: int = 1, **params):
    """Apply a named effect to a frame with given params.

    Special params:
        mix (0.0-1.0): Dry/wet blend. 1.0 = fully processed (default).
        region: Region spec — "x,y,w,h", preset name, or dict. None = full frame.
        feather (int): Edge feather radius for region blending (0 = hard edge).
    """
    # Extract special params before passing to effect function
    mix = float(params.pop("mix", 1.0))
    mix = max(0.0, min(1.0, mix))
    blend_mode = params.pop("blend_mode", "normal")
    region = params.pop("region", None)
    feather = int(params.pop("feather", 0))
    # Spatial concentration params (generic — works with any effect)
    conc_x = params.pop("concentrate_x", None)
    conc_y = params.pop("concentrate_y", None)
    conc_radius = float(params.pop("concentrate_radius", 0.0))
    conc_strength = float(params.pop("concentrate_strength", 1.0))

    fn, defaults = get_effect(effect_name)
    merged = {**defaults, **params}

    # RGBA normalization gate: strip alpha before most effects, preserve for reattach.
    # EXCEPTION: Physics effects use _remap_frame (cv2.remap) which handles any channel
    # count, so we pass RGBA through so alpha drifts with the displaced pixels.
    _PHYSICS_EFFECTS = {
        "pixelliquify", "pixelgravity", "pixelvortex", "pixelexplode", "pixelelastic",
        "pixelmelt", "pixelblackhole", "pixelantigravity", "pixelmagnetic",
        "pixeltimewarp", "pixeldimensionfold", "pixelwormhole", "pixelquantum",
        "pixeldarkenergy", "pixelsuperfluid", "pixelbubbles", "pixelinkdrop",
        "pixelhaunt", "pixelannihilate", "pixeldynamics", "pixelcosmos",
        "pixelorganic", "pixeldecay",
    }
    _input_alpha = None
    _pass_rgba_through = effect_name in _PHYSICS_EFFECTS
    if frame.ndim == 3 and frame.shape[2] == 4:
        if _pass_rgba_through:
            # Physics: keep RGBA intact — displacement will move alpha with pixels
            _input_alpha = None  # Don't reattach separately; physics handles it
        else:
            _input_alpha = frame[:, :, 3].copy()
            frame = frame[:, :, :3].copy()

    # Inject temporal context for effects that need it
    import inspect
    sig = inspect.signature(fn)
    if "frame_index" in sig.parameters:
        merged["frame_index"] = frame_index
    if "total_frames" in sig.parameters:
        merged["total_frames"] = total_frames

    # Warn about temporal effects + region (experimental interaction)
    _TEMPORAL_EFFECTS = {"stutter", "dropout", "feedback", "tapestop", "tremolo",
                         "delay", "decimator", "samplehold"}
    if region is not None and effect_name in _TEMPORAL_EFFECTS:
        import warnings
        warnings.warn(
            f"Region + temporal effect '{effect_name}' is experimental. "
            f"Temporal state is shared globally and may produce unexpected results "
            f"when combined with region masking.",
            stacklevel=2
        )

    # Apply with region masking if specified
    if region is not None:
        from core.region import apply_to_region
        wet = apply_to_region(frame, fn, region, feather=feather, **merged)
    else:
        wet = fn(frame, **merged)

    # RGBA output handling: if effect produced RGBA, extract its alpha
    # If effect produced RGB but input had alpha, reattach the input alpha
    # Physics effects that passed RGBA through already have displaced alpha in wet
    _output_alpha = None
    if wet.ndim == 3 and wet.shape[2] == 4:
        _output_alpha = wet[:, :, 3]
        wet = wet[:, :, :3]
    elif _input_alpha is not None:
        _output_alpha = _input_alpha

    # For concentration and mix blending, ensure frame is also RGB
    if frame.ndim == 3 and frame.shape[2] == 4:
        frame = frame[:, :, :3]

    # Spatial concentration: Gaussian falloff mask around a point
    if conc_x is not None and conc_y is not None and conc_radius > 0:
        h, w = frame.shape[:2]
        cx = float(conc_x) * w
        cy = float(conc_y) * h
        rad_px = conc_radius * max(h, w)
        ys = np.arange(h, dtype=np.float32).reshape(-1, 1)
        xs = np.arange(w, dtype=np.float32).reshape(1, -1)
        dist_sq = (xs - cx) ** 2 + (ys - cy) ** 2
        sigma = rad_px / 2.0
        gauss = np.exp(-dist_sq / (2 * sigma * sigma))
        gauss = gauss * conc_strength
        gauss = np.clip(gauss, 0, 1)[:, :, np.newaxis]
        wet = np.clip(
            frame.astype(np.float32) * (1.0 - gauss) + wet.astype(np.float32) * gauss,
            0, 255
        ).astype(np.uint8)
        if mix < 1.0:
            wet = np.clip(
                frame.astype(np.float32) * (1.0 - mix) + wet.astype(np.float32) * mix,
                0, 255
            ).astype(np.uint8)
    elif mix < 1.0 or blend_mode != "normal":
        # Dry/wet blend with optional blend mode
        if mix <= 0.0:
            wet = frame.copy()
            # If input was RGB, don't inject effect's output alpha onto dry signal
            if _input_alpha is None and not _pass_rgba_through:
                _output_alpha = None
        else:
            wet = _blend_mix(frame, wet, mix, blend_mode)

    # Reattach alpha channel if present (RGBA normalization gate exit)
    if _output_alpha is not None:
        return np.dstack([wet, _output_alpha])
    return wet


# --- License / Watermark ---

_LICENSE_PATH = None  # Set by desktop.py or checked at import time


def _check_license():
    """Check if user has a valid license (any amount paid on Gumroad).
    Returns True if licensed (no watermark), False if free tier."""
    import os
    from pathlib import Path
    # Check local license file
    license_file = Path.home() / ".entropic_license"
    if license_file.exists():
        try:
            key = license_file.read_text().strip()
            # Basic format check: Gumroad keys are typically 35 chars
            if len(key) >= 8:
                return True
        except Exception:
            pass
    return False


def _burn_watermark(frame):
    """Burn 'Made with PopChaos Glitch' into frame pixel data.
    Semi-transparent diagonal text in bottom-right corner."""
    from PIL import Image, ImageDraw, ImageFont
    h, w = frame.shape[:2]

    # Create overlay with transparency
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    text = "Made with PopChaos Glitch"
    font_size = max(12, min(w // 30, 28))

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", font_size)
    except Exception:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except Exception:
            font = ImageFont.load_default()

    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    # Position: bottom-right corner with padding
    padding = max(10, w // 50)
    x = w - tw - padding
    y = h - th - padding

    # Draw with semi-transparency (burned into pixel data)
    alpha = int(255 * 0.3)  # 30% opacity
    draw.text((x, y), text, fill=(255, 255, 255, alpha), font=font)

    # Composite onto frame
    base = Image.fromarray(frame).convert("RGBA")
    composited = Image.alpha_composite(base, overlay)
    return np.array(composited.convert("RGB"))


# Blend mode functions (shared with core/layer.py — same formulas)
_CHAIN_BLEND_FNS = {
    "multiply": lambda b, t: b * t / 255.0,
    "screen": lambda b, t: 255.0 - (255.0 - b) * (255.0 - t) / 255.0,
    "overlay": lambda b, t: np.where(b < 128.0, 2.0 * b * t / 255.0,
                                      255.0 - 2.0 * (255.0 - b) * (255.0 - t) / 255.0),
    "add": lambda b, t: np.minimum(255.0, b + t),
    "difference": lambda b, t: np.abs(b - t),
    "soft_light": lambda b, t: (1.0 - 2.0 * t / 255.0) * (b ** 2 / 255.0) + 2.0 * t / 255.0 * b,
}


def _blend_mix(original, wet, mix, blend_mode="normal"):
    """Apply blend mode + mix between original and wet frames.

    Handles RGBA channel normalization. Returns uint8 RGB.
    """
    # Normalize channels (RGBA → strip alpha for blending)
    b = original[:, :, :3] if original.ndim == 3 and original.shape[2] == 4 else original
    t = wet[:, :, :3] if wet.ndim == 3 and wet.shape[2] == 4 else wet

    b_f = b.astype(np.float32)
    t_f = t.astype(np.float32)

    blend_fn = _CHAIN_BLEND_FNS.get(blend_mode)
    if blend_fn is not None:
        # Non-normal blend: compute blended result, then mix with original
        blended = blend_fn(b_f, t_f)
        result = b_f * (1.0 - mix) + blended * mix
    else:
        # Normal blend: linear interpolation
        result = b_f * (1.0 - mix) + t_f * mix

    return np.clip(result, 0, 255).astype(np.uint8)


def apply_chain(frame, effects_list: list[dict], frame_index: int = 0, total_frames: int = 1,
                watermark: bool = False):
    """Apply a chain of effects sequentially.

    effects_list: [{"name": "pixelsort", "params": {"threshold": 0.6}}, ...]

    Any effect can include an optional "envelope" key for ADSR modulation:
        {"name": "vhs", "params": {...}, "envelope": {
            "attack": 3, "decay": 0, "sustain": 1.0, "release": 8,
            "trigger": "lfo", "rate": 1.0
        }}

    Envelope params:
        attack: Frames to ramp to full effect (0=instant).
        decay: Frames from peak to sustain level (0=instant).
        sustain: Steady-state level (0-1). 1.0 = full effect when on.
        release: Frames to fade out when trigger drops (0=instant).
        trigger: What drives the envelope ("lfo", "time", "brightness",
                 "edges", "motion", "contrast", "saturation").
        rate: For LFO trigger, frequency in Hz. For time trigger,
              pulses per second. For content triggers, threshold (0-1).

    Args:
        watermark: If True (default), burns watermark on free tier exports.
                   Set False for preview (no watermark on previews).
    """
    from core.safety import validate_chain_depth
    validate_chain_depth(effects_list)

    for effect in effects_list:
        # Handle nested group items (Ableton-style racks)
        if effect.get("type") == "group":
            if effect.get("bypassed", False):
                continue  # Skip bypassed groups entirely
            children = effect.get("children", [])
            if not children:
                continue
            group_mix = float(effect.get("mix", 1.0))
            group_mix = max(0.0, min(1.0, group_mix))
            group_blend = effect.get("blend_mode", "normal")
            original = frame.copy() if group_mix < 1.0 or group_blend != "normal" else None
            frame = apply_chain(frame, children, frame_index=frame_index,
                                total_frames=total_frames, watermark=False)
            if original is not None:
                if group_mix <= 0.0:
                    frame = original
                else:
                    frame = _blend_mix(original, frame, group_mix, group_blend)
            continue

        name = effect["name"]
        params = effect.get("params", {})
        envelope = effect.get("envelope")

        # Extract per-effect mix and blend mode
        mix = float(params.pop("mix", 1.0))
        mix = max(0.0, min(1.0, mix))
        blend_mode = params.pop("blend_mode", "normal")

        if envelope is not None:
            # Wrap effect with ADSR envelope
            fn, defaults = get_effect(name)
            merged_params = {**defaults, **params}
            original = frame.copy() if mix < 1.0 or blend_mode != "normal" else None
            frame = adsr_wrap(
                frame, fn, merged_params,
                attack=envelope.get("attack", 0),
                decay=envelope.get("decay", 0),
                sustain=envelope.get("sustain", 1.0),
                release=envelope.get("release", 0),
                trigger_source=envelope.get("trigger", "lfo"),
                trigger_threshold=envelope.get("rate", 1.0),
                seed=merged_params.get("seed", 42),
                frame_index=frame_index,
                total_frames=total_frames,
            )
            # Apply per-effect dry/wet blend with optional blend mode
            if original is not None:
                if mix <= 0.0:
                    frame = original
                else:
                    frame = _blend_mix(original, frame, mix, blend_mode)
        else:
            frame = apply_effect(frame, name, frame_index=frame_index, total_frames=total_frames,
                                mix=mix, blend_mode=blend_mode, **params)

    # Burn watermark on free tier (only for exports, not previews)
    if watermark and not _check_license():
        frame = _burn_watermark(frame)

    return frame

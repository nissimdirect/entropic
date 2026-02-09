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
from effects.modulation import ring_mod, gate, wavefold, am_radio
from effects.enhance import solarize, duotone, emboss, auto_levels, median_filter, false_color, histogram_eq, clahe, parallel_compression
from effects.destruction import (
    datamosh, byte_corrupt, block_corrupt, row_shift,
    jpeg_artifacts, invert_bands, data_bend, flow_distort,
    film_grain, glitch_repeat, xor_glitch,
    pixel_annihilate, frame_smash, channel_destroy,
)
from effects.ascii import ascii_art, braille_art
from effects.sidechain import (
    sidechain_duck, sidechain_pump, sidechain_gate,
    sidechain_cross, sidechain_crossfeed, sidechain_interference,
)
from effects.dsp_filters import (
    video_flanger, video_phaser, spatial_flanger, channel_phaser,
    brightness_phaser, hue_flanger, resonant_filter, comb_filter,
    feedback_phaser, spectral_freeze, visual_reverb, freq_flanger,
)
from effects.adsr import adsr_wrap, ADSREnvelope
from effects.physics import (
    pixel_liquify, pixel_gravity, pixel_vortex,
    pixel_explode, pixel_elastic, pixel_melt,
    pixel_blackhole, pixel_antigravity, pixel_magnetic,
    pixel_timewarp, pixel_dimensionfold,
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
        "params": {"direction": "horizontal", "decay": 0.95},
        "description": "Cumulative paint-smear / light-trail streaks",
    },
    "wave": {
        "fn": wave_distort,
        "category": "distortion",
        "params": {"amplitude": 10.0, "frequency": 0.05, "direction": "horizontal"},
        "description": "Sine wave displacement distortion",
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
        "params": {"intensity": 0.8, "sync_drift": 0.3, "seed": 42},
        "description": "TV static with horizontal sync drift (between-channels)",
    },
    "contours": {
        "fn": contour_lines,
        "category": "texture",
        "params": {"levels": 8},
        "description": "Topographic contour lines from luminance bands",
    },
    "scanlines": {
        "fn": scanlines,
        "category": "texture",
        "params": {"line_width": 2, "opacity": 0.3, "flicker": False, "color": (0, 0, 0)},
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
        "params": {"amount": 0.3, "noise_type": "gaussian", "seed": 42},
        "description": "Add grain/noise overlay",
    },
    "blur": {
        "fn": blur,
        "category": "texture",
        "params": {"radius": 3, "blur_type": "box"},
        "description": "Box or motion blur",
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
        "params": {"threshold": 0.3, "mode": "overlay"},
        "description": "Edge detection (overlay, neon, or edges-only)",
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
        "params": {"charset": "basic", "width": 80, "invert": False, "color_mode": "mono", "edge_mix": 0.0, "seed": 42},
        "description": "Convert frame to ASCII art (basic/dense/block charset, mono/green/amber/original color)",
    },
    "brailleart": {
        "fn": braille_art,
        "category": "texture",
        "params": {"width": 80, "threshold": 128, "invert": False, "dither": True, "color_mode": "mono", "seed": 42},
        "description": "Convert frame to braille unicode art (2×4 dot grid, 4× resolution, Floyd-Steinberg dither)",
    },

    # === COLOR ===
    "tapesaturation": {
        "fn": tape_saturation,
        "category": "color",
        "params": {"drive": 1.5, "warmth": 0.3},
        "description": "Analog tape saturation curve (tanh soft-clip + warmth)",
    },
    "cyanotype": {
        "fn": cyanotype,
        "category": "color",
        "params": {"intensity": 1.0},
        "description": "Prussian blue cyanotype photographic print simulation",
    },
    "infrared": {
        "fn": infrared,
        "category": "color",
        "params": {"vegetation_glow": 1.0},
        "description": "Infrared film simulation (vegetation glows, sky darkens)",
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
        "description": "Extreme contrast manipulation",
    },
    "saturation": {
        "fn": saturation_warp,
        "category": "color",
        "params": {"amount": 1.5, "channel": "all"},
        "description": "Boost or kill saturation",
    },
    "exposure": {
        "fn": brightness_exposure,
        "category": "color",
        "params": {"stops": 1.0, "clip_mode": "clip"},
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
        "description": "Multi-target LFO — oscillate brightness, displacement, channelshift, blur, moire, glitch, invert, or posterize. Waveforms: sine, square, saw, triangle, random.",
    },

    # === MODULATION ===
    "wavefold": {
        "fn": wavefold,
        "category": "modulation",
        "params": {"threshold": 0.7, "folds": 3},
        "description": "Audio wavefolding — pixel brightness folds at threshold",
    },
    "amradio": {
        "fn": am_radio,
        "category": "modulation",
        "params": {"carrier_freq": 10.0, "depth": 0.8},
        "description": "AM radio interference bands (sine carrier on rows)",
    },
    "ringmod": {
        "fn": ring_mod,
        "category": "modulation",
        "params": {"frequency": 4.0, "direction": "horizontal"},
        "description": "Sine wave carrier modulation (alternating bands)",
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
        "params": {},
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
        "params": {"crush": 0.5, "blend": 0.5},
        "description": "Parallel compression (NY compression for video)",
    },
    "solarize": {
        "fn": solarize,
        "category": "enhance",
        "params": {"threshold": 128},
        "description": "Partial inversion above threshold (Sabattier/Man Ray effect)",
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
        "params": {"amount": 1.0},
        "description": "3D raised/carved texture effect",
    },
    "autolevels": {
        "fn": auto_levels,
        "category": "enhance",
        "params": {"cutoff": 2.0},
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
        "description": "Bitwise XOR corruption (fixed, random, or gradient pattern)",
    },
    "datamosh": {
        "fn": datamosh,
        "category": "destruction",
        "params": {
            "intensity": 1.0, "accumulate": True, "decay": 0.95,
            "mode": "melt", "seed": 42, "motion_threshold": 0.0,
            "macroblock_size": 16, "donor_offset": 10, "blend_mode": "normal",
        },
        "description": "Datamosh (optical flow) — 8 modes: melt, bloom, rip, replace, annihilate, freeze_through (authentic I-frame removal), pframe_extend (P-frame duplication/bloom-glide), donor (cross-clip pixel feeding). Blend modes: normal, multiply, average, swap.",
    },
    "bytecorrupt": {
        "fn": byte_corrupt,
        "category": "destruction",
        "params": {"amount": 20, "jpeg_quality": 75, "seed": 42},
        "description": "JPEG data bending — corrupt compressed bytes for authentic glitch",
    },
    "blockcorrupt": {
        "fn": block_corrupt,
        "category": "destruction",
        "params": {"num_blocks": 15, "block_size": 32, "mode": "random", "seed": 42},
        "description": "Corrupt random macroblocks (shift, noise, repeat, invert, zero)",
    },
    "rowshift": {
        "fn": row_shift,
        "category": "destruction",
        "params": {"max_shift": 30, "density": 0.3, "seed": 42},
        "description": "Horizontal scanline tearing — rows displaced randomly",
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
        "params": {"band_height": 10, "offset": 0},
        "description": "Alternating inverted horizontal bands (CRT damage)",
    },
    "databend": {
        "fn": data_bend,
        "category": "destruction",
        "params": {"effect": "echo", "intensity": 0.5, "seed": 42},
        "description": "Audio DSP on pixel data — echo, distort, bitcrush, reverse",
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
        "params": {"intensity": 0.4, "grain_size": 2, "seed": 42},
        "description": "Realistic film grain (brightness-responsive, chunky texture)",
    },
    "glitchrepeat": {
        "fn": glitch_repeat,
        "category": "destruction",
        "params": {"num_slices": 8, "max_height": 20, "shift": True, "seed": 42},
        "description": "Repeat and shift random horizontal slices (buffer overflow)",
    },
    "pixelannihilate": {
        "fn": pixel_annihilate,
        "category": "destruction",
        "params": {"threshold": 0.5, "mode": "dissolve", "replacement": "black", "seed": 42},
        "description": "Kill pixels by dissolve, threshold, edge-kill, or channel-rip",
    },
    "framesmash": {
        "fn": frame_smash,
        "category": "destruction",
        "params": {"aggression": 0.5, "seed": 42},
        "description": "One-stop apocalypse — rows, blocks, channels, XOR, dissolve combined",
    },
    "channeldestroy": {
        "fn": channel_destroy,
        "category": "destruction",
        "params": {"mode": "separate", "intensity": 0.5, "seed": 42},
        "description": "Rip color channels apart — separate, swap, crush, eliminate, XOR",
    },

    # === SIDECHAIN ===
    "sidechainduck": {
        "fn": sidechain_duck,
        "category": "modulation",
        "params": {"source": "brightness", "threshold": 0.5, "ratio": 4.0, "attack": 0.3, "release": 0.7, "mode": "brightness", "invert": False, "seed": 42},
        "description": "Sidechain duck — key signal ducks brightness/saturation/blur/invert/displace",
    },
    "sidechainpump": {
        "fn": sidechain_pump,
        "category": "modulation",
        "params": {"rate": 2.0, "depth": 0.7, "curve": "exponential", "mode": "brightness", "seed": 42},
        "description": "Rhythmic sidechain pump — 4-on-the-floor ducking at fixed BPM",
    },
    "sidechaingate": {
        "fn": sidechain_gate,
        "category": "modulation",
        "params": {"source": "brightness", "threshold": 0.4, "mode": "freeze", "hold_frames": 5, "seed": 42},
        "description": "Sidechain gate — video only passes when signal exceeds threshold",
    },
    "sidechaincross": {
        "fn": sidechain_cross,
        "category": "modulation",
        "params": {"source": "brightness", "threshold": 0.3, "softness": 0.3, "mode": "blend",
                   "strength": 0.8, "invert": False, "pre_a": "none", "pre_b": "none",
                   "attack": 0.0, "decay": 0.0, "sustain": 1.0, "release": 0.0,
                   "lookahead": 0, "seed": 42},
        "description": "Cross-video sidechain — one video busts through another with ADSR envelope and pre-processing",
    },
    "sidechaincrossfeed": {
        "fn": sidechain_crossfeed,
        "category": "color",
        "params": {"channel_map": "rgb_shift", "strength": 0.7, "seed": 42},
        "description": "Cross-video channel feed — mix color channels between two videos",
    },
    "sidechaininterference": {
        "fn": sidechain_interference,
        "category": "modulation",
        "params": {"mode": "phase", "strength": 0.7, "seed": 42},
        "description": "Cross-video interference — treat two videos as waves, create phase/amplitude interference",
    },

    # === PIXEL PHYSICS ===
    "pixelliquify": {
        "fn": pixel_liquify,
        "category": "distortion",
        "params": {"viscosity": 0.92, "turbulence": 3.0, "flow_scale": 40.0, "speed": 1.0, "seed": 42},
        "description": "Liquify — pixels become fluid and wash around in turbulent flow",
    },
    "pixelgravity": {
        "fn": pixel_gravity,
        "category": "distortion",
        "params": {"num_attractors": 5, "gravity_strength": 8.0, "damping": 0.95, "attractor_radius": 0.3, "wander": 0.5, "seed": 42},
        "description": "Gravity attractors — pixels get pulled toward random wandering points",
    },
    "pixelvortex": {
        "fn": pixel_vortex,
        "category": "distortion",
        "params": {"num_vortices": 3, "spin_strength": 5.0, "pull_strength": 2.0, "radius": 0.25, "damping": 0.93, "seed": 42},
        "description": "Vortex — swirling whirlpools pull pixels into spirals",
    },
    "pixelexplode": {
        "fn": pixel_explode,
        "category": "distortion",
        "params": {"origin": "center", "force": 10.0, "damping": 0.96, "gravity": 0.0, "scatter": 0.0, "seed": 42},
        "description": "Explode — pixels blast outward from a point with optional gravity",
    },
    "pixelelastic": {
        "fn": pixel_elastic,
        "category": "distortion",
        "params": {"stiffness": 0.3, "mass": 1.0, "force_type": "turbulence", "force_strength": 5.0, "damping": 0.9, "seed": 42},
        "description": "Elastic — pixels on springs that stretch, bounce, and snap back",
    },
    "pixelmelt": {
        "fn": pixel_melt,
        "category": "distortion",
        "params": {"heat": 3.0, "gravity": 2.0, "viscosity": 0.95, "melt_source": "top", "seed": 42},
        "description": "Melt — pixels drip and flow downward like melting wax",
    },

    # === IMPOSSIBLE PHYSICS ===
    "pixelblackhole": {
        "fn": pixel_blackhole,
        "category": "distortion",
        "params": {"mass": 10.0, "spin": 3.0, "event_horizon": 0.08, "spaghettify": 5.0, "accretion_glow": 0.8, "hawking": 0.0, "position": "center", "seed": 42},
        "description": "Black hole — singularity with event horizon, spaghettification, and accretion glow",
    },
    "pixelantigravity": {
        "fn": pixel_antigravity,
        "category": "distortion",
        "params": {"repulsion": 8.0, "num_zones": 4, "zone_radius": 0.2, "oscillate": 1.0, "damping": 0.93, "seed": 42},
        "description": "Anti-gravity — repulsion zones push pixels outward with oscillating direction",
    },
    "pixelmagnetic": {
        "fn": pixel_magnetic,
        "category": "distortion",
        "params": {"field_type": "dipole", "strength": 6.0, "poles": 2, "rotation_speed": 0.5, "damping": 0.92, "seed": 42},
        "description": "Magnetic fields — pixels curve along dipole/quadrupole/toroidal field lines",
    },
    "pixeltimewarp": {
        "fn": pixel_timewarp,
        "category": "distortion",
        "params": {"warp_speed": 2.0, "echo_count": 3, "echo_decay": 0.6, "reverse_probability": 0.3, "damping": 0.9, "seed": 42},
        "description": "Time warp — displacement reverses with ghosting echoes",
    },
    "pixeldimensionfold": {
        "fn": pixel_dimensionfold,
        "category": "distortion",
        "params": {"num_folds": 3, "fold_depth": 8.0, "fold_width": 0.15, "rotation_speed": 0.3, "mirror_folds": True, "seed": 42},
        "description": "Dimension fold — space folds over itself along rotating axes",
    },

    # === DSP FILTERS ===
    "videoflanger": {
        "fn": video_flanger,
        "category": "modulation",
        "params": {"rate": 0.5, "depth": 10, "feedback": 0.4, "wet": 0.5, "seed": 42},
        "description": "Temporal flanger — blend with oscillating-delay past frame (comb-filter interference)",
    },
    "videophaser": {
        "fn": video_phaser,
        "category": "modulation",
        "params": {"rate": 0.3, "stages": 4, "depth": 1.0, "feedback": 0.3, "seed": 42},
        "description": "Spatial phaser — FFT phase sweep creates sweeping notch interference",
    },
    "spatialflanger": {
        "fn": spatial_flanger,
        "category": "modulation",
        "params": {"rate": 0.8, "depth": 20, "feedback": 0.3, "seed": 42},
        "description": "Per-row horizontal shift with LFO — diagonal sweep flanging",
    },
    "channelphaser": {
        "fn": channel_phaser,
        "category": "modulation",
        "params": {"r_rate": 0.05, "g_rate": 0.3, "b_rate": 1.2, "stages": 5, "depth": 1.5, "wet": 0.8, "seed": 42},
        "description": "Per-channel FFT phase sweep at different rates — color fringing and tearing",
    },
    "brightnessphaser": {
        "fn": brightness_phaser,
        "category": "modulation",
        "params": {"rate": 0.25, "bands": 6, "depth": 0.3, "strength": 0.8, "seed": 42},
        "description": "Sweeping brightness inversion bands — psychedelic solarization sweep",
    },
    "hueflanger": {
        "fn": hue_flanger,
        "category": "color",
        "params": {"rate": 0.3, "depth": 60.0, "sat_depth": 0.0, "seed": 42},
        "description": "Blend with hue-rotated copy, rotation oscillates — color interference",
    },
    "resonantfilter": {
        "fn": resonant_filter,
        "category": "modulation",
        "params": {"rate": 0.2, "q": 50.0, "gain": 3.0, "wet": 0.7, "seed": 42},
        "description": "High-Q bandpass sweep through spatial frequencies — synth filter on video",
    },
    "combfilter": {
        "fn": comb_filter,
        "category": "modulation",
        "params": {"teeth": 7, "spacing": 8, "rate": 0.3, "depth": 3.0, "wet": 0.7, "seed": 42},
        "description": "Multi-tooth spatial comb filter — offset copies create interference patterns",
    },
    "feedbackphaser": {
        "fn": feedback_phaser,
        "category": "modulation",
        "params": {"rate": 0.3, "stages": 6, "feedback": 0.5, "escalation": 0.01, "seed": 42},
        "description": "Self-feeding 2D FFT phaser that escalates over time — builds to self-oscillation",
    },
    "spectralfreeze": {
        "fn": spectral_freeze,
        "category": "temporal",
        "params": {"interval": 30, "blend_peak": 0.7, "envelope_frames": 25, "seed": 42},
        "description": "Freeze frequency magnitude at intervals, impose on later frames — spectral imprint",
    },
    "visualreverb": {
        "fn": visual_reverb,
        "category": "temporal",
        "params": {"rate": 0.15, "depth": 0.5, "ir_interval": 30, "seed": 42},
        "description": "Convolve frame with past frame as impulse response — visual echo/room",
    },
    "freqflanger": {
        "fn": freq_flanger,
        "category": "modulation",
        "params": {"rate": 0.5, "depth": 10, "mag_blend": 0.4, "phase_blend": 0.15, "seed": 42},
        "description": "2D FFT magnitude+phase blend with delayed frame — spectral ghosting",
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
    "glitch": "GLITCH",
    "distortion": "DISTORTION",
    "texture": "TEXTURE",
    "color": "COLOR",
    "temporal": "TEMPORAL",
    "modulation": "MODULATION",
    "enhance": "ENHANCE",
    "destruction": "DESTRUCTION",
}


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
    region = params.pop("region", None)
    feather = int(params.pop("feather", 0))

    fn, defaults = get_effect(effect_name)
    merged = {**defaults, **params}

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

    # Dry/wet blend (parallel processing)
    if mix >= 1.0:
        return wet
    if mix <= 0.0:
        return frame.copy()

    # Linear blend: output = dry * (1 - mix) + wet * mix
    blended = (frame.astype(np.float32) * (1.0 - mix) + wet.astype(np.float32) * mix)
    return np.clip(blended, 0, 255).astype(np.uint8)


def apply_chain(frame, effects_list: list[dict], frame_index: int = 0, total_frames: int = 1):
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
    """
    from core.safety import validate_chain_depth
    validate_chain_depth(effects_list)

    for effect in effects_list:
        name = effect["name"]
        params = effect.get("params", {})
        envelope = effect.get("envelope")

        if envelope is not None:
            # Wrap effect with ADSR envelope
            fn, defaults = get_effect(name)
            merged_params = {**defaults, **params}
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
        else:
            frame = apply_effect(frame, name, frame_index=frame_index, total_frames=total_frames, **params)
    return frame

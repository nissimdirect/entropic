"""
Entropic — Packages System (Challenger Prototype)

Instead of individual effects, packages group pre-configured effect chains
by USE CASE. Each package contains named recipes at different intensity levels.

Benefits for UAT:
  - "Package X, Recipe Y is broken" → immediately debuggable
  - Each recipe has KNOWN expected output
  - No blind parameter guessing
  - Clear test matrix: packages × recipes × test videos

Usage:
    python entropic_packages.py list
    python entropic_packages.py explore <package>
    python entropic_packages.py apply <project> --package <name> --recipe <recipe>
    python entropic_packages.py batch <project> --package <name>  (renders ALL recipes in package)
"""

# Each package: name, description, available effects, and pre-configured recipes
PACKAGES = {
    # =========================================================================
    # 1. ANALOG DECAY — VHS, film, tape degradation
    # =========================================================================
    "analog-decay": {
        "name": "Analog Decay",
        "description": "VHS tapes, film reels, broadcast signals breaking down. "
                       "Everything warm, noisy, and beautifully broken.",
        "effects_used": ["vhs", "scanlines", "noise", "chromatic", "temperature",
                         "saturation", "blur", "contrast"],
        "recipes": {
            "light-wear": {
                "name": "Light Wear",
                "description": "Barely degraded. Like a well-stored VHS played once.",
                "effects": [
                    {"name": "vhs", "params": {"tracking": 0.2, "noise_amount": 0.1, "color_bleed": 2, "seed": 42}},
                    {"name": "noise", "params": {"amount": 0.05, "noise_type": "gaussian", "seed": 7}},
                    {"name": "temperature", "params": {"temp": 8}},
                ],
            },
            "worn-tape": {
                "name": "Worn Tape",
                "description": "Played a hundred times. Tracking wobbles, color bleeds.",
                "effects": [
                    {"name": "vhs", "params": {"tracking": 0.5, "noise_amount": 0.25, "color_bleed": 5, "seed": 42}},
                    {"name": "scanlines", "params": {"line_width": 2, "opacity": 0.2, "flicker": True, "color": [0, 0, 0]}},
                    {"name": "chromatic", "params": {"offset": 3, "direction": "horizontal"}},
                    {"name": "noise", "params": {"amount": 0.12, "noise_type": "gaussian", "seed": 33}},
                    {"name": "temperature", "params": {"temp": 15}},
                ],
            },
            "destroyed-tape": {
                "name": "Destroyed Tape",
                "description": "Left in a hot car for a decade. Barely watchable.",
                "effects": [
                    {"name": "vhs", "params": {"tracking": 0.9, "noise_amount": 0.5, "color_bleed": 12, "seed": 42}},
                    {"name": "scanlines", "params": {"line_width": 3, "opacity": 0.5, "flicker": True, "color": [0, 0, 0]}},
                    {"name": "chromatic", "params": {"offset": 8, "direction": "horizontal"}},
                    {"name": "noise", "params": {"amount": 0.35, "noise_type": "uniform", "seed": 99}},
                    {"name": "blur", "params": {"radius": 2, "blur_type": "box"}},
                    {"name": "saturation", "params": {"amount": 0.6, "channel": "all"}},
                    {"name": "temperature", "params": {"temp": 30}},
                ],
            },
            "broadcast-signal": {
                "name": "Broadcast Signal",
                "description": "Bad antenna reception. Horizontal tears and static.",
                "effects": [
                    {"name": "scanlines", "params": {"line_width": 2, "opacity": 0.35, "flicker": True, "color": [0, 0, 0]}},
                    {"name": "noise", "params": {"amount": 0.2, "noise_type": "salt_pepper", "seed": 55}},
                    {"name": "chromatic", "params": {"offset": 4, "direction": "horizontal"}},
                    {"name": "contrast", "params": {"amount": 25, "curve": "linear"}},
                    {"name": "saturation", "params": {"amount": 0.75, "channel": "all"}},
                ],
            },
            "nuclear-analog": {
                "name": "Nuclear Analog",
                "description": "VHS left in a bonfire. Maximum tracking, noise, bleed, tears.",
                "effects": [
                    {"name": "vhs", "params": {"tracking": 1.0, "noise_amount": 0.8, "color_bleed": 15, "seed": 42}},
                    {"name": "scanlines", "params": {"line_width": 4, "opacity": 0.7, "flicker": True, "color": [0, 0, 0]}},
                    {"name": "chromatic", "params": {"offset": 15, "direction": "horizontal"}},
                    {"name": "noise", "params": {"amount": 0.6, "noise_type": "uniform", "seed": 99}},
                    {"name": "rowshift", "params": {"max_shift": 80, "density": 0.3, "seed": 42}},
                    {"name": "filmgrain", "params": {"intensity": 1.5, "grain_size": 4, "seed": 42}},
                    {"name": "channeldestroy", "params": {"mode": "separate", "intensity": 0.3, "seed": 42}},
                ],
            },
        },
    },

    # =========================================================================
    # 2. DIGITAL CORRUPTION — Glitch blocks, bitcrush, pixel chaos
    # =========================================================================
    "digital-corruption": {
        "name": "Digital Corruption",
        "description": "Data rot, compression artifacts, block displacement. "
                       "The file is corrupted and it looks amazing.",
        "effects_used": ["displacement", "bitcrush", "channelshift", "posterize",
                         "pixelsort", "noise", "contrast", "sharpen"],
        "recipes": {
            "minor-glitch": {
                "name": "Minor Glitch",
                "description": "Small block displacement. Like a streaming buffer hiccup.",
                "effects": [
                    {"name": "displacement", "params": {"block_size": 16, "intensity": 5.0, "seed": 42}},
                    {"name": "channelshift", "params": {"r_offset": [3, 0], "g_offset": [0, 0], "b_offset": [-3, 0]}},
                ],
            },
            "data-rot": {
                "name": "Data Rot",
                "description": "Bitcrushed with posterized colors. Digital decay.",
                "effects": [
                    {"name": "bitcrush", "params": {"color_depth": 4, "resolution_scale": 0.7}},
                    {"name": "posterize", "params": {"levels": 6}},
                    {"name": "sharpen", "params": {"amount": 2.0}},
                    {"name": "channelshift", "params": {"r_offset": [5, 0], "g_offset": [0, 2], "b_offset": [-5, -2]}},
                ],
            },
            "full-corruption": {
                "name": "Full Corruption",
                "description": "Maximum data destruction. Blocks everywhere, colors gone.",
                "effects": [
                    {"name": "displacement", "params": {"block_size": 8, "intensity": 35.0, "seed": 666}},
                    {"name": "bitcrush", "params": {"color_depth": 2, "resolution_scale": 0.4}},
                    {"name": "channelshift", "params": {"r_offset": [30, 10], "g_offset": [-15, -5], "b_offset": [10, 20]}},
                    {"name": "posterize", "params": {"levels": 3}},
                    {"name": "noise", "params": {"amount": 0.4, "noise_type": "uniform", "seed": 13}},
                    {"name": "contrast", "params": {"amount": 70, "curve": "linear"}},
                ],
            },
            "pixel-sort": {
                "name": "Pixel Sort",
                "description": "Clean pixel sorting. The signature glitch art look.",
                "effects": [
                    {"name": "pixelsort", "params": {"threshold": 0.4, "sort_by": "brightness", "direction": "vertical"}},
                    {"name": "contrast", "params": {"amount": 15, "curve": "linear"}},
                ],
            },
            "nuclear-digital": {
                "name": "Nuclear Digital",
                "description": "Maximum displacement, 1-bit color, massive channel shift, XOR corruption.",
                "effects": [
                    {"name": "displacement", "params": {"block_size": 4, "intensity": 50.0, "seed": 666}},
                    {"name": "bitcrush", "params": {"color_depth": 2, "resolution_scale": 0.25}},
                    {"name": "channelshift", "params": {"r_offset": [50, 20], "g_offset": [-30, -15], "b_offset": [20, 40]}},
                    {"name": "xorglitch", "params": {"pattern": 200, "mode": "random", "seed": 42}},
                    {"name": "framesmash", "params": {"aggression": 0.6, "seed": 42}},
                ],
            },
        },
    },

    # =========================================================================
    # 3. COLOR LAB — Color grading, manipulation, artistic color
    # =========================================================================
    "color-lab": {
        "name": "Color Lab",
        "description": "Hue shifts, temperature changes, saturation warps, inversions. "
                       "Everything about changing the color palette.",
        "effects_used": ["hueshift", "saturation", "temperature", "exposure",
                         "contrast", "invert", "duotone", "falsecolor"],
        "recipes": {
            "warm-grade": {
                "name": "Warm Grade",
                "description": "Golden warmth. Sunset vibes.",
                "effects": [
                    {"name": "temperature", "params": {"temp": 40}},
                    {"name": "exposure", "params": {"stops": 0.2, "clip_mode": "clip"}},
                    {"name": "saturation", "params": {"amount": 1.3, "channel": "all"}},
                    {"name": "contrast", "params": {"amount": 10, "curve": "linear"}},
                ],
            },
            "cold-grade": {
                "name": "Cold Grade",
                "description": "Ice blue. Clinical, detached.",
                "effects": [
                    {"name": "temperature", "params": {"temp": -45}},
                    {"name": "saturation", "params": {"amount": 0.8, "channel": "all"}},
                    {"name": "contrast", "params": {"amount": 20, "curve": "linear"}},
                    {"name": "exposure", "params": {"stops": -0.2, "clip_mode": "clip"}},
                ],
            },
            "psychedelic": {
                "name": "Psychedelic",
                "description": "Cranked hue shift with max saturation. Acid trip.",
                "effects": [
                    {"name": "hueshift", "params": {"degrees": 120}},
                    {"name": "saturation", "params": {"amount": 3.0, "channel": "all"}},
                    {"name": "contrast", "params": {"amount": 40, "curve": "linear"}},
                    {"name": "invert", "params": {"channel": "g", "amount": 0.5}},
                ],
            },
            "duotone-poster": {
                "name": "Duotone Poster",
                "description": "Two-color graphic design look. Bold and flat.",
                "effects": [
                    {"name": "duotone", "params": {"shadow_color": [10, 10, 60], "highlight_color": [255, 180, 80]}},
                    {"name": "contrast", "params": {"amount": 30, "curve": "linear"}},
                ],
            },
            "thermal-map": {
                "name": "Thermal Map",
                "description": "False color heat vision. Predator mode.",
                "effects": [
                    {"name": "falsecolor", "params": {"colormap": "jet"}},
                    {"name": "contrast", "params": {"amount": 20, "curve": "linear"}},
                ],
            },
        },
    },

    # =========================================================================
    # 4. TEMPORAL CHAOS — Frame manipulation, stutter, feedback
    # =========================================================================
    "temporal-chaos": {
        "name": "Temporal Chaos",
        "description": "Time manipulation. Frames stutter, echo, drop out, speed up, slow down. "
                       "These effects only make sense on VIDEO (not single frames).",
        "effects_used": ["stutter", "dropout", "feedback", "delay", "decimator",
                         "samplehold", "tremolo", "tapestop", "timestretch"],
        "recipes": {
            "subtle-stutter": {
                "name": "Subtle Stutter",
                "description": "Light frame holding. Like a tiny buffer glitch.",
                "effects": [
                    {"name": "stutter", "params": {"repeat": 2, "interval": 12}},
                ],
            },
            "echo-trail": {
                "name": "Echo Trail",
                "description": "Ghost trails from previous frames. Dreamy movement.",
                "effects": [
                    {"name": "feedback", "params": {"decay": 0.4}},
                    {"name": "delay", "params": {"delay_frames": 3, "decay": 0.3}},
                ],
            },
            "choppy-lofi": {
                "name": "Choppy Lo-Fi",
                "description": "Reduced framerate with random freezes. Surveillance cam feel.",
                "effects": [
                    {"name": "decimator", "params": {"factor": 4}},
                    {"name": "samplehold", "params": {"hold_min": 3, "hold_max": 8, "seed": 42}},
                ],
            },
            "signal-loss": {
                "name": "Signal Loss",
                "description": "Random frames drop to black. Lost transmission.",
                "effects": [
                    {"name": "dropout", "params": {"drop_rate": 0.2, "seed": 42}},
                    {"name": "stutter", "params": {"repeat": 3, "interval": 10}},
                    {"name": "tremolo", "params": {"rate": 1.5, "depth": 0.3}},
                ],
            },
            "tape-death": {
                "name": "Tape Death",
                "description": "Tape machine slowing to a stop. Everything fades.",
                "effects": [
                    {"name": "tapestop", "params": {"trigger": 0.6, "ramp_frames": 20}},
                    {"name": "feedback", "params": {"decay": 0.5}},
                ],
            },
            "nuclear-temporal": {
                "name": "Nuclear Temporal",
                "description": "Maximum stutter, dropout, decimation, and sample hold. Time is broken.",
                "effects": [
                    {"name": "stutter", "params": {"repeat": 8, "interval": 3}},
                    {"name": "dropout", "params": {"drop_rate": 0.5, "seed": 42}},
                    {"name": "decimator", "params": {"factor": 6}},
                    {"name": "feedback", "params": {"decay": 0.7}},
                    {"name": "tremolo", "params": {"rate": 15.0, "depth": 0.9}},
                ],
            },
        },
    },

    # =========================================================================
    # 5. DISTORTION ENGINE — Wave, mirror, spatial warping
    # =========================================================================
    "distortion-engine": {
        "name": "Distortion Engine",
        "description": "Spatial warping. Waves, mirrors, displacement. "
                       "The image bends, stretches, and folds.",
        "effects_used": ["wave", "mirror", "displacement", "chromatic",
                         "pixelsort", "blur"],
        "recipes": {
            "gentle-wave": {
                "name": "Gentle Wave",
                "description": "Slight undulation. Underwater feeling.",
                "effects": [
                    {"name": "wave", "params": {"amplitude": 4.0, "frequency": 0.02, "direction": "horizontal"}},
                    {"name": "chromatic", "params": {"offset": 2, "direction": "radial"}},
                ],
            },
            "mirror-world": {
                "name": "Mirror World",
                "description": "Vertical symmetry. Rorschach test.",
                "effects": [
                    {"name": "mirror", "params": {"axis": "vertical", "position": 0.5}},
                    {"name": "chromatic", "params": {"offset": 3, "direction": "radial"}},
                ],
            },
            "earthquake": {
                "name": "Earthquake",
                "description": "Massive displacement in both directions. Nothing stays put.",
                "effects": [
                    {"name": "wave", "params": {"amplitude": 20.0, "frequency": 0.05, "direction": "horizontal"}},
                    {"name": "wave", "params": {"amplitude": 12.0, "frequency": 0.03, "direction": "vertical"}},
                    {"name": "displacement", "params": {"block_size": 16, "intensity": 20.0, "seed": 911}},
                    {"name": "blur", "params": {"radius": 3, "blur_type": "motion"}},
                ],
            },
            "melt": {
                "name": "Melt",
                "description": "Pixel sort + vertical wave. The image melts upward.",
                "effects": [
                    {"name": "pixelsort", "params": {"threshold": 0.3, "sort_by": "brightness", "direction": "vertical"}},
                    {"name": "wave", "params": {"amplitude": 8.0, "frequency": 0.04, "direction": "vertical"}},
                    {"name": "blur", "params": {"radius": 1, "blur_type": "motion"}},
                ],
            },
            "nuclear-distortion": {
                "name": "Nuclear Distortion",
                "description": "Maximum wave + displacement + channel rip. Geometry destroyed.",
                "effects": [
                    {"name": "wave", "params": {"amplitude": 40.0, "frequency": 0.1, "direction": "horizontal"}},
                    {"name": "wave", "params": {"amplitude": 30.0, "frequency": 0.08, "direction": "vertical"}},
                    {"name": "displacement", "params": {"block_size": 8, "intensity": 50.0, "seed": 911}},
                    {"name": "channeldestroy", "params": {"mode": "separate", "intensity": 0.5, "seed": 42}},
                    {"name": "pixelsort", "params": {"threshold": 0.2, "sort_by": "hue", "direction": "vertical"}},
                ],
            },
        },
    },

    # =========================================================================
    # 6. ENHANCEMENT SUITE — Artistic filters, edge detection, texture
    # =========================================================================
    "enhancement-suite": {
        "name": "Enhancement Suite",
        "description": "Artistic filters that enhance or transform the image. "
                       "Solarize, emboss, edge detect, median paint.",
        "effects_used": ["solarize", "emboss", "autolevels", "median",
                         "edges", "sharpen", "falsecolor"],
        "recipes": {
            "auto-correct": {
                "name": "Auto Correct",
                "description": "Auto-levels + sharpen. Clean up any footage.",
                "effects": [
                    {"name": "autolevels", "params": {"cutoff": 2.0}},
                    {"name": "sharpen", "params": {"amount": 1.2}},
                ],
            },
            "neon-edges": {
                "name": "Neon Edges",
                "description": "Edge detection in neon overlay mode. Tron vibes.",
                "effects": [
                    {"name": "edges", "params": {"threshold": 0.3, "mode": "neon"}},
                    {"name": "contrast", "params": {"amount": 30, "curve": "linear"}},
                ],
            },
            "watercolor": {
                "name": "Watercolor",
                "description": "Heavy median filter. Painterly, soft.",
                "effects": [
                    {"name": "median", "params": {"size": 9}},
                    {"name": "saturation", "params": {"amount": 1.4, "channel": "all"}},
                    {"name": "contrast", "params": {"amount": 15, "curve": "linear"}},
                ],
            },
            "sabattier": {
                "name": "Sabattier",
                "description": "Solarization. Man Ray darkroom technique.",
                "effects": [
                    {"name": "solarize", "params": {"threshold": 128}},
                    {"name": "contrast", "params": {"amount": 20, "curve": "linear"}},
                    {"name": "saturation", "params": {"amount": 1.5, "channel": "all"}},
                ],
            },
            "embossed-metal": {
                "name": "Embossed Metal",
                "description": "3D emboss with sharpening. Carved in stone.",
                "effects": [
                    {"name": "emboss", "params": {"amount": 1.5}},
                    {"name": "sharpen", "params": {"amount": 2.0}},
                    {"name": "contrast", "params": {"amount": 40, "curve": "linear"}},
                ],
            },
        },
    },

    # =========================================================================
    # 7. SIGNAL PROCESSING — Modulation, gating, oscillation
    # =========================================================================
    "signal-processing": {
        "name": "Signal Processing",
        "description": "Audio-inspired effects applied to video. Ring modulation, "
                       "noise gates, tremolo. The image becomes a waveform.",
        "effects_used": ["ringmod", "gate", "tremolo", "tapestop",
                         "scanlines", "contrast"],
        "recipes": {
            "ring-mod": {
                "name": "Ring Mod",
                "description": "Sine wave bands across the image. AM radio for video.",
                "effects": [
                    {"name": "ringmod", "params": {"frequency": 4.0, "direction": "horizontal"}},
                ],
            },
            "noise-gate": {
                "name": "Noise Gate",
                "description": "Dark pixels go to black. High contrast cutoff.",
                "effects": [
                    {"name": "gate", "params": {"threshold": 0.4, "mode": "brightness"}},
                    {"name": "contrast", "params": {"amount": 20, "curve": "linear"}},
                ],
            },
            "strobe": {
                "name": "Strobe",
                "description": "Fast brightness oscillation. Club strobe effect.",
                "effects": [
                    {"name": "tremolo", "params": {"rate": 8.0, "depth": 0.8}},
                    {"name": "contrast", "params": {"amount": 30, "curve": "linear"}},
                ],
            },
            "full-signal-chain": {
                "name": "Full Signal Chain",
                "description": "Ring mod → gate → scanlines. Full signal processing path.",
                "effects": [
                    {"name": "ringmod", "params": {"frequency": 3.0, "direction": "vertical"}},
                    {"name": "gate", "params": {"threshold": 0.3, "mode": "brightness"}},
                    {"name": "scanlines", "params": {"line_width": 2, "opacity": 0.3, "flicker": True, "color": [0, 0, 0]}},
                    {"name": "contrast", "params": {"amount": 25, "curve": "linear"}},
                ],
            },
            "nuclear-signal": {
                "name": "Nuclear Signal",
                "description": "Max ring mod + hard gate + max strobe + data bend. Signal annihilated.",
                "effects": [
                    {"name": "ringmod", "params": {"frequency": 20.0, "direction": "vertical"}},
                    {"name": "gate", "params": {"threshold": 0.6, "mode": "brightness"}},
                    {"name": "tremolo", "params": {"rate": 20.0, "depth": 1.0}},
                    {"name": "databend", "params": {"effect": "distort", "intensity": 0.8, "seed": 42}},
                    {"name": "xorglitch", "params": {"pattern": 128, "mode": "gradient", "seed": 42}},
                ],
            },
        },
    },

    # =========================================================================
    # 8. TOTAL DESTRUCTION — Datamosh, byte corrupt, data bending
    # =========================================================================
    "total-destruction": {
        "name": "Total Destruction",
        "description": "Maximum violence to your video. Datamoshing, byte corruption, "
                       "data bending, block damage. The file fights back.",
        "effects_used": ["datamosh", "bytecorrupt", "blockcorrupt", "rowshift",
                         "jpegdamage", "databend", "flowdistort", "glitchrepeat",
                         "filmgrain", "invertbands", "xorglitch", "pixelannihilate",
                         "framesmash", "channeldestroy"],
        "recipes": {
            "light-datamosh": {
                "name": "Light Datamosh",
                "description": "Gentle optical flow warping. Motion trails start to bleed.",
                "effects": [
                    {"name": "datamosh", "params": {"intensity": 0.5, "accumulate": True, "decay": 0.8, "mode": "melt", "seed": 42}},
                ],
            },
            "heavy-datamosh": {
                "name": "Heavy Datamosh",
                "description": "Full melt. Pixels flow like liquid along motion vectors.",
                "effects": [
                    {"name": "datamosh", "params": {"intensity": 5.0, "accumulate": True, "decay": 0.98, "mode": "melt", "seed": 42}},
                    {"name": "rowshift", "params": {"max_shift": 20, "density": 0.15, "seed": 42}},
                ],
            },
            "datamosh-rip": {
                "name": "Datamosh Rip",
                "description": "Motion vectors amplified with noise injection. Pixels fly apart.",
                "effects": [
                    {"name": "datamosh", "params": {"intensity": 15.0, "accumulate": True, "decay": 0.99, "mode": "rip", "seed": 42}},
                ],
            },
            "datamosh-annihilate": {
                "name": "Datamosh Annihilate",
                "description": "All datamosh modes combined. Warp + blocks + rows + channels.",
                "effects": [
                    {"name": "datamosh", "params": {"intensity": 30.0, "accumulate": True, "decay": 0.999, "mode": "annihilate", "seed": 42}},
                ],
            },
            "data-bent": {
                "name": "Data Bent",
                "description": "JPEG bytes corrupted. Authentic glitch art from file damage.",
                "effects": [
                    {"name": "bytecorrupt", "params": {"amount": 80, "jpeg_quality": 15, "seed": 42}},
                    {"name": "jpegdamage", "params": {"quality": 3, "block_damage": 40, "seed": 42}},
                ],
            },
            "block-massacre": {
                "name": "Block Massacre",
                "description": "Random macroblocks destroyed. Like a corrupted MPEG stream.",
                "effects": [
                    {"name": "blockcorrupt", "params": {"num_blocks": 60, "block_size": 48, "mode": "random", "seed": 42}},
                    {"name": "rowshift", "params": {"max_shift": 80, "density": 0.3, "seed": 42}},
                    {"name": "glitchrepeat", "params": {"num_slices": 20, "max_height": 50, "shift": True, "seed": 42}},
                ],
            },
            "audio-on-video": {
                "name": "Audio on Video",
                "description": "Audio DSP applied to pixel data. Feedback echo + distortion.",
                "effects": [
                    {"name": "databend", "params": {"effect": "feedback", "intensity": 0.8, "seed": 42}},
                    {"name": "databend", "params": {"effect": "distort", "intensity": 0.7, "seed": 42}},
                ],
            },
            "everything-breaks": {
                "name": "Everything Breaks",
                "description": "ALL destruction effects at once. Maximum chaos.",
                "effects": [
                    {"name": "datamosh", "params": {"intensity": 10.0, "accumulate": True, "decay": 0.99, "mode": "melt", "seed": 42}},
                    {"name": "blockcorrupt", "params": {"num_blocks": 40, "block_size": 32, "mode": "random", "seed": 42}},
                    {"name": "rowshift", "params": {"max_shift": 60, "density": 0.25, "seed": 42}},
                    {"name": "bytecorrupt", "params": {"amount": 50, "jpeg_quality": 20, "seed": 42}},
                    {"name": "glitchrepeat", "params": {"num_slices": 15, "max_height": 30, "shift": True, "seed": 42}},
                    {"name": "channeldestroy", "params": {"mode": "separate", "intensity": 0.4, "seed": 42}},
                ],
            },
            # --- NEW: Transcript-learned techniques ---
            "freeze-through": {
                "name": "Freeze Through (Authentic Datamosh)",
                "description": "Real I-frame removal look. Previous frame frozen, only moving "
                               "pixels update in macroblock-sized chunks. The ACTUAL datamosh aesthetic.",
                "effects": [
                    {"name": "datamosh", "params": {
                        "intensity": 3.0, "mode": "freeze_through",
                        "motion_threshold": 1.5, "macroblock_size": 16, "seed": 42,
                    }},
                ],
            },
            "freeze-through-fine": {
                "name": "Freeze Through Fine Detail",
                "description": "Authentic datamosh with small 8px macroblocks. Like raw footage "
                               "with less compression — finer detail in the mosh.",
                "effects": [
                    {"name": "datamosh", "params": {
                        "intensity": 2.0, "mode": "freeze_through",
                        "motion_threshold": 0.8, "macroblock_size": 8, "seed": 42,
                    }},
                ],
            },
            "bloom-glide": {
                "name": "Bloom / Glide (P-Frame Extend)",
                "description": "Classic datamosh bloom where pixels stretch along their motion path. "
                               "Simulates P-frame duplication — the iconic 'glide' effect.",
                "effects": [
                    {"name": "datamosh", "params": {
                        "intensity": 5.0, "accumulate": True, "decay": 0.98,
                        "mode": "pframe_extend", "seed": 42,
                    }},
                ],
            },
            "bloom-glide-nuclear": {
                "name": "Nuclear Bloom Glide",
                "description": "Extreme P-frame extension. Pixels stretch infinitely, decay near zero.",
                "effects": [
                    {"name": "datamosh", "params": {
                        "intensity": 30.0, "accumulate": True, "decay": 0.999,
                        "mode": "pframe_extend", "seed": 42,
                    }},
                    {"name": "channeldestroy", "params": {"mode": "separate", "intensity": 0.3, "seed": 42}},
                ],
            },
            "donor-mosh": {
                "name": "Donor Mosh",
                "description": "Current motion applied to pixels from 10 frames ago. "
                               "Creates surreal temporal displacement.",
                "effects": [
                    {"name": "datamosh", "params": {
                        "intensity": 3.0, "mode": "donor",
                        "donor_offset": 10, "seed": 42,
                    }},
                ],
            },
            "multiply-mosh": {
                "name": "Multiply Mosh",
                "description": "Datamosh with multiply blend. Darkens and creates "
                               "rich, layered pixel smearing.",
                "effects": [
                    {"name": "datamosh", "params": {
                        "intensity": 5.0, "mode": "melt", "decay": 0.95,
                        "blend_mode": "multiply", "seed": 42,
                    }},
                ],
            },
            "swap-mosh": {
                "name": "Swap Mosh",
                "description": "Motion-based pixel swap between moshed and original. "
                               "Moving areas get moshed, static areas stay clean.",
                "effects": [
                    {"name": "datamosh", "params": {
                        "intensity": 8.0, "mode": "melt", "decay": 0.97,
                        "blend_mode": "swap", "seed": 42,
                    }},
                ],
            },
        },
    },

    # =========================================================================
    # 9. MOTION WARP — Flow-based effects (only work on video with motion)
    # =========================================================================
    "motion-warp": {
        "name": "Motion Warp",
        "description": "Optical flow effects that react to motion in the video. "
                       "More motion = more effect. Dead still video = no effect.",
        "effects_used": ["datamosh", "flowdistort", "feedback", "delay", "stutter"],
        "recipes": {
            "flow-push": {
                "name": "Flow Push",
                "description": "Pixels pushed forward along motion. Creates stretching.",
                "effects": [
                    {"name": "flowdistort", "params": {"strength": 8.0, "direction": "forward"}},
                ],
            },
            "flow-pull": {
                "name": "Flow Pull",
                "description": "Pixels pulled backward against motion. Ghostly resistance.",
                "effects": [
                    {"name": "flowdistort", "params": {"strength": 8.0, "direction": "backward"}},
                    {"name": "feedback", "params": {"decay": 0.5}},
                ],
            },
            "melt-cascade": {
                "name": "Melt Cascade",
                "description": "Accumulating datamosh with echo. Everything melts and echoes.",
                "effects": [
                    {"name": "datamosh", "params": {"intensity": 8.0, "accumulate": True, "decay": 0.98, "mode": "melt", "seed": 42}},
                    {"name": "delay", "params": {"delay_frames": 3, "decay": 0.5}},
                ],
            },
            "motion-stutter": {
                "name": "Motion Stutter",
                "description": "Flow distortion combined with frame stuttering. Jerky and warped.",
                "effects": [
                    {"name": "flowdistort", "params": {"strength": 15.0, "direction": "forward"}},
                    {"name": "stutter", "params": {"repeat": 4, "interval": 5}},
                ],
            },
            "nuclear-flow": {
                "name": "Nuclear Flow",
                "description": "Maximum flow distortion. Pixels rip across the entire frame.",
                "effects": [
                    {"name": "flowdistort", "params": {"strength": 40.0, "direction": "forward"}},
                    {"name": "channeldestroy", "params": {"mode": "separate", "intensity": 0.6, "seed": 42}},
                ],
            },
        },
    },

    # =========================================================================
    # 10. NUCLEAR — Maximum destruction from EVERY category
    # =========================================================================
    "nuclear": {
        "name": "NUCLEAR",
        "description": "The most extreme settings for every effect. Nothing subtle. "
                       "This is where video goes to die.",
        "effects_used": ["datamosh", "framesmash", "channeldestroy", "pixelannihilate",
                         "xorglitch", "databend", "blockcorrupt", "rowshift",
                         "bytecorrupt", "jpegdamage", "glitchrepeat", "vhs",
                         "displacement", "wave", "bitcrush"],
        "recipes": {
            "nuclear-datamosh": {
                "name": "Nuclear Datamosh",
                "description": "Datamosh annihilate mode at max intensity. Reality ceases.",
                "effects": [
                    {"name": "datamosh", "params": {"intensity": 50.0, "accumulate": True, "decay": 0.999, "mode": "annihilate", "seed": 42}},
                ],
            },
            "nuclear-smash": {
                "name": "Nuclear Smash",
                "description": "Frame smash at full aggression. Every pixel is violated.",
                "effects": [
                    {"name": "framesmash", "params": {"aggression": 1.0, "seed": 42}},
                ],
            },
            "nuclear-corrupt": {
                "name": "Nuclear Corrupt",
                "description": "Maximum byte + block + JPEG corruption stacked.",
                "effects": [
                    {"name": "bytecorrupt", "params": {"amount": 300, "jpeg_quality": 1, "seed": 42}},
                    {"name": "blockcorrupt", "params": {"num_blocks": 150, "block_size": 64, "mode": "random", "seed": 42}},
                    {"name": "jpegdamage", "params": {"quality": 1, "block_damage": 150, "seed": 42}},
                ],
            },
            "nuclear-channel": {
                "name": "Nuclear Channel",
                "description": "Channels ripped apart + XOR + pixel annihilation.",
                "effects": [
                    {"name": "channeldestroy", "params": {"mode": "separate", "intensity": 1.0, "seed": 42}},
                    {"name": "xorglitch", "params": {"pattern": 170, "mode": "random", "seed": 42}},
                    {"name": "pixelannihilate", "params": {"threshold": 0.5, "mode": "dissolve", "replacement": "noise", "seed": 42}},
                ],
            },
            "nuclear-databend": {
                "name": "Nuclear Databend",
                "description": "Audio feedback loop on pixel data. Total signal destruction.",
                "effects": [
                    {"name": "databend", "params": {"effect": "feedback", "intensity": 1.0, "seed": 42}},
                    {"name": "databend", "params": {"effect": "distort", "intensity": 0.9, "seed": 42}},
                    {"name": "databend", "params": {"effect": "reverse", "intensity": 1.0, "seed": 42}},
                ],
            },
            "nuclear-teardown": {
                "name": "Nuclear Teardown",
                "description": "Row shift + glitch repeat + invert bands at maximum. Torn apart.",
                "effects": [
                    {"name": "rowshift", "params": {"max_shift": 200, "density": 0.8, "seed": 42}},
                    {"name": "glitchrepeat", "params": {"num_slices": 50, "max_height": 100, "shift": True, "seed": 42}},
                    {"name": "invertbands", "params": {"band_height": 5, "offset": 0}},
                ],
            },
            "nuclear-everything": {
                "name": "Nuclear Everything",
                "description": "Every destruction technique at maximum. The final boss.",
                "effects": [
                    {"name": "datamosh", "params": {"intensity": 30.0, "accumulate": True, "decay": 0.999, "mode": "annihilate", "seed": 42}},
                    {"name": "framesmash", "params": {"aggression": 0.8, "seed": 42}},
                    {"name": "channeldestroy", "params": {"mode": "xor_channels", "intensity": 0.8, "seed": 42}},
                    {"name": "rowshift", "params": {"max_shift": 100, "density": 0.5, "seed": 42}},
                    {"name": "bytecorrupt", "params": {"amount": 100, "jpeg_quality": 5, "seed": 42}},
                    {"name": "pixelannihilate", "params": {"threshold": 0.3, "mode": "dissolve", "replacement": "noise", "seed": 42}},
                ],
            },
            "nuclear-analog": {
                "name": "Nuclear Analog",
                "description": "VHS at max + displacement + bitcrush + wave distort. Analog apocalypse.",
                "effects": [
                    {"name": "vhs", "params": {"tracking": 1.0, "noise_amount": 0.8, "color_bleed": 15, "seed": 42}},
                    {"name": "displacement", "params": {"block_size": 8, "intensity": 50.0, "seed": 42}},
                    {"name": "bitcrush", "params": {"color_depth": 2, "resolution_scale": 0.3}},
                    {"name": "wave", "params": {"amplitude": 30.0, "frequency": 0.1, "direction": "horizontal"}},
                    {"name": "filmgrain", "params": {"intensity": 1.5, "grain_size": 5, "seed": 42}},
                ],
            },
        },
    },

    # =========================================================================
    # 11. DATAMOSH COMBOS — Real datamosh + Entropic effect chains
    # =========================================================================
    "datamosh-combos": {
        "name": "Datamosh Combos",
        "description": "Combine REAL datamosh (H.264 P-frame manipulation via "
                       "entropic_datamosh.py) with Entropic's per-frame effects. "
                       "Run datamosh first, then apply these effect chains to the output.",
        "effects_used": ["datamosh", "pixelsort", "bytecorrupt", "channeldestroy",
                         "flowdistort", "databend", "filmgrain", "chromatic",
                         "hueshift", "feedback", "scanlines", "vhs"],
        "recipes": {
            "mosh-then-sort": {
                "name": "Mosh Then Sort",
                "description": "Real datamosh → pixel sort. Melting pixels get sorted into streaks.",
                "effects": [
                    {"name": "pixelsort", "params": {"threshold": 0.3, "sort_by": "brightness", "direction": "vertical"}},
                    {"name": "chromatic", "params": {"offset": 4, "direction": "horizontal"}},
                ],
                "note": "Run entropic_datamosh.py splice first, then apply this chain.",
            },
            "mosh-then-corrupt": {
                "name": "Mosh Then Corrupt",
                "description": "Real datamosh → byte corruption. Double destruction — codec + data level.",
                "effects": [
                    {"name": "bytecorrupt", "params": {"amount": 40, "jpeg_quality": 20, "seed": 42}},
                    {"name": "rowshift", "params": {"max_shift": 30, "density": 0.2, "seed": 42}},
                ],
                "note": "Run entropic_datamosh.py splice first, then apply this chain.",
            },
            "mosh-then-vhs": {
                "name": "Mosh Then VHS",
                "description": "Real datamosh → VHS degradation. Codec melt + tape damage.",
                "effects": [
                    {"name": "vhs", "params": {"tracking": 0.6, "noise_amount": 0.3, "color_bleed": 8, "seed": 42}},
                    {"name": "scanlines", "params": {"line_width": 2, "opacity": 0.3, "flicker": True, "color": [0, 0, 0]}},
                    {"name": "filmgrain", "params": {"intensity": 0.6, "grain_size": 3, "seed": 42}},
                ],
                "note": "Run entropic_datamosh.py splice first, then apply this chain.",
            },
            "mosh-then-channel-rip": {
                "name": "Mosh Then Channel Rip",
                "description": "Real datamosh → channel destruction. Melted pixels with separated RGB.",
                "effects": [
                    {"name": "channeldestroy", "params": {"mode": "separate", "intensity": 0.5, "seed": 42}},
                    {"name": "hueshift", "params": {"degrees": 60}},
                ],
                "note": "Run entropic_datamosh.py splice first, then apply this chain.",
            },
            "mosh-then-databend": {
                "name": "Mosh Then Databend",
                "description": "Real datamosh → audio DSP on pixels. Cross-modal double destruction.",
                "effects": [
                    {"name": "databend", "params": {"effect": "echo", "intensity": 0.6, "seed": 42}},
                    {"name": "databend", "params": {"effect": "distort", "intensity": 0.4, "seed": 42}},
                ],
                "note": "Run entropic_datamosh.py splice first, then apply this chain.",
            },
            "mosh-nuclear-combo": {
                "name": "Mosh Nuclear Combo",
                "description": "Real datamosh → simulated datamosh → byte corrupt → channel rip. "
                               "The ultimate double-datamosh apocalypse.",
                "effects": [
                    {"name": "datamosh", "params": {"intensity": 10.0, "accumulate": True, "decay": 0.98, "mode": "melt", "seed": 42}},
                    {"name": "bytecorrupt", "params": {"amount": 60, "jpeg_quality": 10, "seed": 42}},
                    {"name": "channeldestroy", "params": {"mode": "xor_channels", "intensity": 0.6, "seed": 42}},
                    {"name": "filmgrain", "params": {"intensity": 1.0, "grain_size": 4, "seed": 42}},
                ],
                "note": "DOUBLE datamosh: real P-frame + simulated optical flow. Maximum melt.",
            },
        },
    },
    # =========================================================================
    # 12. ASCII ART — Text and braille rendering effects
    # =========================================================================
    "ascii-art": {
        "name": "ASCII Art",
        "description": "Convert video frames to ASCII and braille unicode art. "
                       "Clean text rendering, retro terminal aesthetics, high-res braille dots.",
        "effects_used": ["asciiart", "brailleart", "scanlines", "noise", "contrast"],
        "recipes": {
            "terminal-mono": {
                "name": "Terminal Mono",
                "description": "Classic white-on-black ASCII art. Clean and readable.",
                "effects": [
                    {"name": "asciiart", "params": {"charset": "basic", "width": 100, "color_mode": "mono", "seed": 42}},
                ],
            },
            "matrix-rain": {
                "name": "Matrix Rain",
                "description": "Green phosphor terminal. Dense charset for maximum detail.",
                "effects": [
                    {"name": "asciiart", "params": {"charset": "dense", "width": 120, "color_mode": "green", "seed": 42}},
                    {"name": "scanlines", "params": {"line_width": 2, "opacity": 0.15, "flicker": True, "color": [0, 0, 0]}},
                ],
            },
            "amber-crt": {
                "name": "Amber CRT",
                "description": "Retro amber terminal with block characters and scanlines.",
                "effects": [
                    {"name": "asciiart", "params": {"charset": "block", "width": 80, "color_mode": "amber", "seed": 42}},
                    {"name": "scanlines", "params": {"line_width": 2, "opacity": 0.25, "flicker": False, "color": [0, 0, 0]}},
                    {"name": "noise", "params": {"amount": 0.08, "noise_type": "gaussian", "seed": 42}},
                ],
            },
            "braille-hires": {
                "name": "Braille Hi-Res",
                "description": "Braille unicode art. 4× the resolution of regular ASCII.",
                "effects": [
                    {"name": "brailleart", "params": {"width": 120, "threshold": 128, "dither": True, "color_mode": "mono", "seed": 42}},
                ],
            },
            "edge-ascii": {
                "name": "Edge ASCII",
                "description": "Edge-detected ASCII art. Outlines pop, details emerge.",
                "effects": [
                    {"name": "asciiart", "params": {"charset": "dense", "width": 100, "color_mode": "mono", "edge_mix": 0.8, "seed": 42}},
                    {"name": "contrast", "params": {"amount": 20, "curve": "linear"}},
                ],
            },
            "nuclear-ascii": {
                "name": "Nuclear ASCII",
                "description": "Maximum effect: inverted braille with scanlines and noise. Unreadable but beautiful.",
                "effects": [
                    {"name": "brailleart", "params": {"width": 100, "threshold": 100, "invert": True, "dither": True, "color_mode": "green", "seed": 42}},
                    {"name": "scanlines", "params": {"line_width": 3, "opacity": 0.3, "flicker": True, "color": [0, 0, 0]}},
                    {"name": "noise", "params": {"amount": 0.2, "noise_type": "salt_pepper", "seed": 42}},
                ],
            },
        },
    },

    # =========================================================================
    # 13. DSP FILTERS — Audio DSP concepts applied to video
    # =========================================================================
    "dsp-filters": {
        "name": "DSP Filters",
        "description": "Audio DSP applied to video: phasers, flangers, comb filters, "
                       "resonant sweeps, spectral freezing, visual reverb.",
        "effects_used": ["videoflanger", "videophaser", "spatialflanger", "channelphaser",
                         "brightnessphaser", "hueflanger", "resonantfilter", "combfilter",
                         "feedbackphaser", "spectralfreeze", "visualreverb", "freqflanger"],
        "recipes": {
            # === Flanger family ===
            "flanger-gentle": {
                "name": "Gentle Flanger",
                "description": "Slow temporal flanger — ghostly frame echoes.",
                "effects": [
                    {"name": "videoflanger", "params": {"rate": 0.3, "depth": 8, "feedback": 0.3, "wet": 0.5, "seed": 42}},
                ],
            },
            "flanger-heavy": {
                "name": "Heavy Flanger",
                "description": "Fast flanger with high feedback — dense temporal comb.",
                "effects": [
                    {"name": "videoflanger", "params": {"rate": 1.5, "depth": 15, "feedback": 0.6, "wet": 0.7, "seed": 42}},
                ],
            },
            "flanger-extreme": {
                "name": "Extreme Flanger",
                "description": "Max depth + feedback — heavy ghosting and self-reinforcement.",
                "effects": [
                    {"name": "videoflanger", "params": {"rate": 2.0, "depth": 25, "feedback": 0.85, "wet": 0.9, "seed": 42}},
                ],
            },
            "freq-flanger-slow": {
                "name": "Freq Flanger (Slow)",
                "description": "2D FFT spectral blend with slow sweep — massive phase ghosting.",
                "effects": [
                    {"name": "freqflanger", "params": {"rate": 0.15, "depth": 20, "mag_blend": 0.6, "phase_blend": 0.5, "seed": 42}},
                ],
            },
            "spatial-flanger": {
                "name": "Spatial Flanger",
                "description": "Per-row horizontal shift with diagonal sweep.",
                "effects": [
                    {"name": "spatialflanger", "params": {"rate": 0.8, "depth": 20, "feedback": 0.3, "seed": 42}},
                ],
            },
            "spatial-flanger-extreme": {
                "name": "Spatial Flanger (Extreme)",
                "description": "Wide shift + high feedback — heavy horizontal interference.",
                "effects": [
                    {"name": "spatialflanger", "params": {"rate": 2.0, "depth": 50, "feedback": 0.7, "seed": 42}},
                ],
            },
            # === Phaser family ===
            "phaser-subtle": {
                "name": "Subtle Phaser",
                "description": "3-stage row phase sweep — gentle notch movement.",
                "effects": [
                    {"name": "videophaser", "params": {"rate": 0.2, "stages": 3, "depth": 0.5, "feedback": 0.2, "seed": 42}},
                ],
            },
            "phaser-deep": {
                "name": "Deep Phaser",
                "description": "6-stage deep notch sweep with feedback.",
                "effects": [
                    {"name": "videophaser", "params": {"rate": 0.5, "stages": 6, "depth": 1.5, "feedback": 0.5, "seed": 42}},
                ],
            },
            "channel-phaser": {
                "name": "Channel Phaser",
                "description": "R/G/B sweep at different rates — color tearing.",
                "effects": [
                    {"name": "channelphaser", "params": {"r_rate": 0.05, "g_rate": 0.3, "b_rate": 1.2, "stages": 5, "depth": 1.5, "wet": 0.8, "seed": 42}},
                ],
            },
            "channel-phaser-torn": {
                "name": "Channel Phaser (Torn)",
                "description": "Extreme per-channel separation — 8 stages, 3x depth.",
                "effects": [
                    {"name": "channelphaser", "params": {"r_rate": 0.05, "g_rate": 0.3, "b_rate": 1.2, "stages": 8, "depth": 3.0, "wet": 0.8, "seed": 42}},
                ],
            },
            "brightness-phaser": {
                "name": "Brightness Phaser",
                "description": "6-band brightness inversion sweep — solarization that moves.",
                "effects": [
                    {"name": "brightnessphaser", "params": {"rate": 0.25, "bands": 6, "depth": 0.3, "strength": 0.8, "seed": 42}},
                ],
            },
            "brightness-phaser-extreme": {
                "name": "Brightness Phaser (Extreme)",
                "description": "12-band full inversion, slow sweep — maximum solarization.",
                "effects": [
                    {"name": "brightnessphaser", "params": {"rate": 0.12, "bands": 12, "depth": 0.5, "strength": 1.0, "seed": 42}},
                ],
            },
            "feedback-phaser": {
                "name": "Feedback Phaser",
                "description": "Self-feeding 2D phaser that escalates over time.",
                "effects": [
                    {"name": "feedbackphaser", "params": {"rate": 0.3, "stages": 6, "feedback": 0.5, "escalation": 0.01, "seed": 42}},
                ],
            },
            "feedback-phaser-runaway": {
                "name": "Feedback Phaser (Runaway)",
                "description": "80% feedback, fast escalation — self-oscillation territory.",
                "effects": [
                    {"name": "feedbackphaser", "params": {"rate": 0.2, "stages": 8, "feedback": 0.8, "escalation": 0.03, "seed": 42}},
                ],
            },
            # === Filter family ===
            "resonant-filter": {
                "name": "Resonant Filter",
                "description": "Sweeping bandpass — synth filter on video.",
                "effects": [
                    {"name": "resonantfilter", "params": {"rate": 0.2, "q": 50.0, "gain": 3.0, "wet": 0.7, "seed": 42}},
                ],
            },
            "resonant-filter-extreme": {
                "name": "Resonant Filter (Extreme)",
                "description": "Q=200, gain=8x — razor-thin resonant peak, slow sweep.",
                "effects": [
                    {"name": "resonantfilter", "params": {"rate": 0.1, "q": 200.0, "gain": 8.0, "wet": 0.85, "seed": 42}},
                ],
            },
            "comb-filter": {
                "name": "Comb Filter",
                "description": "7-tooth rotating spatial comb — interference patterns.",
                "effects": [
                    {"name": "combfilter", "params": {"teeth": 7, "spacing": 8, "rate": 0.3, "depth": 3.0, "wet": 0.7, "seed": 42}},
                ],
            },
            "comb-filter-deep": {
                "name": "Comb Filter (Deep)",
                "description": "15 teeth, wide spacing, 80% wet — dense interference.",
                "effects": [
                    {"name": "combfilter", "params": {"teeth": 15, "spacing": 10, "rate": 0.15, "depth": 6.0, "wet": 0.8, "seed": 42}},
                ],
            },
            # === Color domain ===
            "hue-flanger": {
                "name": "Hue Flanger",
                "description": "Oscillating hue rotation blend — color interference.",
                "effects": [
                    {"name": "hueflanger", "params": {"rate": 0.3, "depth": 60.0, "sat_depth": 0.0, "seed": 42}},
                ],
            },
            "hue-flanger-massive": {
                "name": "Hue Flanger (Massive)",
                "description": "±90 degree hue sweep + saturation modulation, very slow.",
                "effects": [
                    {"name": "hueflanger", "params": {"rate": 0.1, "depth": 90.0, "sat_depth": 80.0, "seed": 42}},
                ],
            },
            # === Temporal spectral ===
            "spectral-freeze": {
                "name": "Spectral Freeze",
                "description": "Capture spectrum at intervals, impose on later frames.",
                "effects": [
                    {"name": "spectralfreeze", "params": {"interval": 30, "blend_peak": 0.7, "envelope_frames": 25, "seed": 42}},
                ],
            },
            "visual-reverb": {
                "name": "Visual Reverb",
                "description": "Convolve with past frame — spatial echo of previous content.",
                "effects": [
                    {"name": "visualreverb", "params": {"rate": 0.15, "depth": 0.5, "ir_interval": 30, "seed": 42}},
                ],
            },
            # === Combos ===
            "freq-brightness-smash": {
                "name": "Freq + Brightness Smash",
                "description": "2D freq flanger → 12-band brightness phaser. Spectral + solarization.",
                "effects": [
                    {"name": "freqflanger", "params": {"rate": 0.12, "depth": 20, "mag_blend": 0.6, "phase_blend": 0.5, "seed": 42}},
                    {"name": "brightnessphaser", "params": {"rate": 0.1, "bands": 12, "depth": 0.5, "strength": 1.0, "seed": 42}},
                ],
            },
            "total-dsp-smash": {
                "name": "Total DSP Smash",
                "description": "Freq flanger → brightness phaser → resonant boost → feedback. Everything.",
                "effects": [
                    {"name": "freqflanger", "params": {"rate": 0.12, "depth": 20, "mag_blend": 0.6, "phase_blend": 0.5, "seed": 42}},
                    {"name": "brightnessphaser", "params": {"rate": 0.1, "bands": 12, "depth": 0.5, "strength": 1.0, "seed": 42}},
                    {"name": "resonantfilter", "params": {"rate": 0.08, "q": 100.0, "gain": 5.0, "wet": 0.7, "seed": 42}},
                ],
            },
            "nuclear-dsp": {
                "name": "Nuclear DSP",
                "description": "Feedback phaser (runaway) + resonant filter + freq flanger. Maximum DSP destruction.",
                "effects": [
                    {"name": "feedbackphaser", "params": {"rate": 0.2, "stages": 8, "feedback": 0.8, "escalation": 0.03, "seed": 42}},
                    {"name": "resonantfilter", "params": {"rate": 0.1, "q": 200.0, "gain": 8.0, "wet": 0.85, "seed": 42}},
                    {"name": "freqflanger", "params": {"rate": 0.15, "depth": 20, "mag_blend": 0.7, "phase_blend": 0.5, "seed": 42}},
                ],
            },
        },
    },

    # =========================================================================
    # 14. SIDECHAIN — Video ducking, pumping, gating
    # =========================================================================
    "sidechain": {
        "name": "Sidechain",
        "description": "Audio sidechain concepts on video: ducking, pumping, gating. "
                       "One signal modulates another.",
        "effects_used": ["sidechainduck", "sidechainpump", "sidechaingate"],
        "recipes": {
            "pump-120bpm": {
                "name": "Pump 120 BPM",
                "description": "Classic sidechain pump at 120 BPM — brightness ducks on the beat.",
                "effects": [
                    {"name": "sidechainpump", "params": {"rate": 2.0, "depth": 0.7, "curve": "exponential", "mode": "brightness", "seed": 42}},
                ],
            },
            "pump-140bpm-sat": {
                "name": "Pump 140 BPM (Saturation)",
                "description": "Fast pump — saturation ducks on the beat.",
                "effects": [
                    {"name": "sidechainpump", "params": {"rate": 2.33, "depth": 0.8, "curve": "exponential", "mode": "saturation", "seed": 42}},
                ],
            },
            "pump-blur": {
                "name": "Pump Blur",
                "description": "Focus pulses in and out at 90 BPM.",
                "effects": [
                    {"name": "sidechainpump", "params": {"rate": 1.5, "depth": 0.9, "curve": "linear", "mode": "blur", "seed": 42}},
                ],
            },
            "pump-scale": {
                "name": "Pump Scale",
                "description": "Video zooms in/out with the beat — breathing effect.",
                "effects": [
                    {"name": "sidechainpump", "params": {"rate": 2.0, "depth": 0.6, "curve": "exponential", "mode": "scale", "seed": 42}},
                ],
            },
            "pump-displace": {
                "name": "Pump Displace",
                "description": "Pixels scatter on the beat, reform between hits.",
                "effects": [
                    {"name": "sidechainpump", "params": {"rate": 2.0, "depth": 0.8, "curve": "exponential", "mode": "displace", "seed": 42}},
                ],
            },
            "duck-brightness": {
                "name": "Duck Brightness",
                "description": "Bright areas duck dark — self-sidechain compression.",
                "effects": [
                    {"name": "sidechainduck", "params": {"source": "brightness", "threshold": 0.5, "ratio": 6.0, "attack": 0.2, "release": 0.6, "mode": "brightness", "seed": 42}},
                ],
            },
            "duck-edges-invert": {
                "name": "Duck Edges → Invert",
                "description": "High-edge areas get inverted — detail triggers corruption.",
                "effects": [
                    {"name": "sidechainduck", "params": {"source": "edges", "threshold": 0.3, "ratio": 8.0, "attack": 0.1, "release": 0.5, "mode": "invert", "seed": 42}},
                ],
            },
            "duck-motion-displace": {
                "name": "Duck Motion → Displace",
                "description": "Moving areas get displaced — motion triggers pixel scatter.",
                "effects": [
                    {"name": "sidechainduck", "params": {"source": "motion", "threshold": 0.3, "ratio": 10.0, "attack": 0.1, "release": 0.4, "mode": "displace", "seed": 42}},
                ],
            },
            "gate-brightness-freeze": {
                "name": "Gate: Brightness → Freeze",
                "description": "Video freezes when dark, plays when bright.",
                "effects": [
                    {"name": "sidechaingate", "params": {"source": "brightness", "threshold": 0.4, "mode": "freeze", "hold_frames": 5, "seed": 42}},
                ],
            },
            "gate-motion-black": {
                "name": "Gate: Motion → Black",
                "description": "Video drops to black when still, shows when moving.",
                "effects": [
                    {"name": "sidechaingate", "params": {"source": "motion", "threshold": 0.3, "mode": "black", "hold_frames": 8, "seed": 42}},
                ],
            },
            "nuclear-sidechain": {
                "name": "Nuclear Sidechain",
                "description": "Fast pump + edge duck + brightness gate. Maximum rhythmic destruction.",
                "effects": [
                    {"name": "sidechainpump", "params": {"rate": 3.0, "depth": 0.9, "curve": "exponential", "mode": "displace", "seed": 42}},
                    {"name": "sidechainduck", "params": {"source": "edges", "threshold": 0.2, "ratio": 12.0, "attack": 0.05, "release": 0.3, "mode": "invert", "seed": 42}},
                ],
            },
        },
    },

    # =========================================================================
    # 15. ENVELOPES — ADSR on any effect. LFO/time-triggered rhythmic modulation.
    # =========================================================================
    "envelopes": {
        "name": "Envelopes",
        "description": "ADSR envelopes on effects — pluck, pad, pulse, swell. "
                       "LFO and time triggers make effects breathe rhythmically.",
        "effects_used": ["vhs", "wave", "invert", "scanlines", "noise",
                         "bitcrush", "posterize", "edges", "chromatic",
                         "blur", "pixelsort", "freqflanger"],
        "recipes": {
            # --- Plucks (percussive: instant attack, no sustain, fast release) ---
            "pluck-invert": {
                "name": "Pluck: Invert",
                "description": "Percussive negative flash at 3Hz.",
                "effects": [
                    {"name": "invert", "params": {"channel": "all", "amount": 1.0},
                     "envelope": {"attack": 1, "decay": 1, "sustain": 1.0, "release": 3, "trigger": "lfo", "rate": 3.0}},
                ],
            },
            "pluck-scanlines": {
                "name": "Pluck: Scanlines",
                "description": "Scanline strobe at 2Hz.",
                "effects": [
                    {"name": "scanlines", "params": {"line_width": 5, "opacity": 1.0, "flicker": True, "color": [0, 0, 0]},
                     "envelope": {"attack": 1, "decay": 0, "sustain": 1.0, "release": 3, "trigger": "lfo", "rate": 2.0}},
                ],
            },
            "pluck-noise": {
                "name": "Pluck: Noise Burst",
                "description": "Grain burst at 2Hz — film damage percussive.",
                "effects": [
                    {"name": "noise", "params": {"amount": 0.9, "noise_type": "gaussian", "seed": 42},
                     "envelope": {"attack": 1, "decay": 1, "sustain": 1.0, "release": 4, "trigger": "lfo", "rate": 2.0}},
                ],
            },
            "pluck-wave": {
                "name": "Pluck: Wave Hit",
                "description": "Warp pops in and vanishes at 1.5Hz.",
                "effects": [
                    {"name": "wave", "params": {"amplitude": 40.0, "frequency": 0.04, "direction": "both"},
                     "envelope": {"attack": 1, "decay": 2, "sustain": 1.0, "release": 4, "trigger": "lfo", "rate": 1.5}},
                ],
            },
            # --- Pads (slow bloom, long sustain, long release) ---
            "pad-blur": {
                "name": "Pad: Blur Bloom",
                "description": "Focus slowly drifts out and back at 0.5Hz.",
                "effects": [
                    {"name": "blur", "params": {"radius": 25, "blur_type": "gaussian"},
                     "envelope": {"attack": 12, "decay": 0, "sustain": 1.0, "release": 18, "trigger": "lfo", "rate": 0.5}},
                ],
            },
            "pad-chromatic": {
                "name": "Pad: Chromatic Bloom",
                "description": "Color fringing slowly blooms at 0.4Hz.",
                "effects": [
                    {"name": "chromatic", "params": {"offset": 35, "direction": "horizontal"},
                     "envelope": {"attack": 15, "decay": 0, "sustain": 1.0, "release": 20, "trigger": "lfo", "rate": 0.4}},
                ],
            },
            "pad-bitcrush": {
                "name": "Pad: Bitcrush Decay",
                "description": "Quality slowly degrades and recovers at 0.3Hz.",
                "effects": [
                    {"name": "bitcrush", "params": {"color_depth": 1, "resolution_scale": 0.15},
                     "envelope": {"attack": 15, "decay": 0, "sustain": 1.0, "release": 20, "trigger": "lfo", "rate": 0.3}},
                ],
            },
            "pad-edges": {
                "name": "Pad: Edge Reveal",
                "description": "Line drawing slowly appears over image at 0.4Hz.",
                "effects": [
                    {"name": "edges", "params": {"threshold": 0.2, "mode": "overlay"},
                     "envelope": {"attack": 18, "decay": 0, "sustain": 1.0, "release": 22, "trigger": "lfo", "rate": 0.4}},
                ],
            },
            # --- Pulses (time-triggered rhythmic bursts) ---
            "pulse-posterize": {
                "name": "Pulse: Posterize",
                "description": "Color reduction in timed bursts.",
                "effects": [
                    {"name": "posterize", "params": {"levels": 2},
                     "envelope": {"attack": 2, "decay": 0, "sustain": 1.0, "release": 8, "trigger": "time", "rate": 0.5}},
                ],
            },
            "pulse-vhs": {
                "name": "Pulse: VHS Damage",
                "description": "VHS tracking errors in timed bursts.",
                "effects": [
                    {"name": "vhs", "params": {"tracking": 1.0, "noise_amount": 0.8, "color_bleed": 10, "seed": 42},
                     "envelope": {"attack": 2, "decay": 0, "sustain": 1.0, "release": 6, "trigger": "time", "rate": 0.5}},
                ],
            },
            # --- Swells (slow rise, no plateau, slow fall) ---
            "swell-freqflanger": {
                "name": "Swell: Spectral Ghost",
                "description": "Spectral smear swells and recedes at 0.5Hz.",
                "effects": [
                    {"name": "freqflanger", "params": {"rate": 0.15, "depth": 25, "mag_blend": 0.8, "phase_blend": 0.6, "seed": 42},
                     "envelope": {"attack": 15, "decay": 15, "sustain": 0.0, "release": 0, "trigger": "lfo", "rate": 0.5}},
                ],
            },
            "swell-wave": {
                "name": "Swell: Wave Breathe",
                "description": "Warp swells up and down at 0.6Hz — video breathes.",
                "effects": [
                    {"name": "wave", "params": {"amplitude": 50.0, "frequency": 0.03, "direction": "both"},
                     "envelope": {"attack": 12, "decay": 12, "sustain": 0.0, "release": 0, "trigger": "lfo", "rate": 0.6}},
                ],
            },
            # --- Multi-effect chains with mixed envelopes ---
            "rhythmic-destruction": {
                "name": "Rhythmic Destruction",
                "description": "VHS + scanlines + noise all pulsing at different rates.",
                "effects": [
                    {"name": "vhs", "params": {"tracking": 1.0, "noise_amount": 0.7, "color_bleed": 8, "seed": 42},
                     "envelope": {"attack": 2, "decay": 0, "sustain": 1.0, "release": 5, "trigger": "lfo", "rate": 1.0}},
                    {"name": "scanlines", "params": {"line_width": 4, "opacity": 1.0, "flicker": True, "color": [0, 0, 0]},
                     "envelope": {"attack": 1, "decay": 0, "sustain": 1.0, "release": 2, "trigger": "lfo", "rate": 2.0}},
                    {"name": "noise", "params": {"amount": 0.8, "noise_type": "gaussian", "seed": 42},
                     "envelope": {"attack": 1, "decay": 0, "sustain": 1.0, "release": 3, "trigger": "lfo", "rate": 1.5}},
                ],
            },
            "breathing-glitch": {
                "name": "Breathing Glitch",
                "description": "Wave + chromatic + blur all slowly swelling at different rates.",
                "effects": [
                    {"name": "wave", "params": {"amplitude": 35.0, "frequency": 0.04, "direction": "both"},
                     "envelope": {"attack": 10, "decay": 10, "sustain": 0.0, "release": 0, "trigger": "lfo", "rate": 0.5}},
                    {"name": "chromatic", "params": {"offset": 30, "direction": "horizontal"},
                     "envelope": {"attack": 15, "decay": 15, "sustain": 0.0, "release": 0, "trigger": "lfo", "rate": 0.3}},
                    {"name": "blur", "params": {"radius": 20, "blur_type": "gaussian"},
                     "envelope": {"attack": 8, "decay": 8, "sustain": 0.0, "release": 0, "trigger": "lfo", "rate": 0.7}},
                ],
            },
            "nuclear-envelope": {
                "name": "Nuclear Envelope",
                "description": "Everything at once — invert plucks + VHS pulse + wave swell + noise burst.",
                "effects": [
                    {"name": "invert", "params": {"channel": "all", "amount": 1.0},
                     "envelope": {"attack": 1, "decay": 0, "sustain": 1.0, "release": 2, "trigger": "lfo", "rate": 4.0}},
                    {"name": "vhs", "params": {"tracking": 1.0, "noise_amount": 0.9, "color_bleed": 12, "seed": 42},
                     "envelope": {"attack": 2, "decay": 0, "sustain": 1.0, "release": 5, "trigger": "lfo", "rate": 1.0}},
                    {"name": "wave", "params": {"amplitude": 50.0, "frequency": 0.03, "direction": "both"},
                     "envelope": {"attack": 8, "decay": 8, "sustain": 0.0, "release": 0, "trigger": "lfo", "rate": 0.6}},
                    {"name": "noise", "params": {"amount": 1.0, "noise_type": "gaussian", "seed": 42},
                     "envelope": {"attack": 1, "decay": 0, "sustain": 1.0, "release": 3, "trigger": "lfo", "rate": 2.0}},
                ],
            },
        },
    },

    # =========================================================================
    # WHIMSY — Retro, fantastical, soft, playful
    # =========================================================================
    "whimsy": {
        "name": "Whimsy",
        "description": "Retro, fantastical, and soft effects. Shapes floating, "
                       "flares drifting, watercolor washes — less hard edges, more magic.",
        "effects_used": ["kaleidoscope", "softbloom", "shapeoverlay", "lensflare",
                         "watercolor", "rainbowshift", "sparkle", "filmgrainwarm"],
        "recipes": {
            "fairy-tale": {
                "name": "Fairy Tale",
                "description": "Soft bloom + sparkle + warm grain. Ethereal storybook look.",
                "effects": [
                    {"name": "softbloom", "params": {"radius": 20, "intensity": 0.5, "threshold": 160, "mood": "dreamy"}},
                    {"name": "sparkle", "params": {"density": 0.003, "size": 4, "mood": "fairy", "spread": "highlights", "seed": 42}},
                    {"name": "filmgrainwarm", "params": {"amount": 0.1, "warmth": 0.4, "mood": "vintage", "seed": 42}},
                ],
            },
            "retro-prism": {
                "name": "Retro Prism",
                "description": "Rainbow shift + lens flare + film grain. 70s psychedelic.",
                "effects": [
                    {"name": "rainbowshift", "params": {"speed": 0.8, "direction": "diagonal", "opacity": 0.3, "mood": "prismatic"}},
                    {"name": "lensflare", "params": {"position_x": 0.2, "position_y": 0.25, "intensity": 0.5, "mood": "retro", "streaks": 8}},
                    {"name": "filmgrainwarm", "params": {"amount": 0.2, "size": 2.0, "warmth": 0.5, "mood": "kodak", "seed": 42}},
                ],
            },
            "shape-dance": {
                "name": "Shape Dance",
                "description": "Animated shapes + kaleidoscope + sparkle. Playful motion graphics.",
                "effects": [
                    {"name": "shapeoverlay", "params": {"shape": "triangle", "count": 8, "size": 0.08, "opacity": 0.3, "orientation": "spiral", "mood": "playful", "seed": 42}},
                    {"name": "kaleidoscope", "params": {"segments": 4, "rotation": 15, "mood": "soft"}},
                    {"name": "sparkle", "params": {"density": 0.001, "size": 2, "mood": "glitter", "seed": 42}},
                ],
            },
            "watercolor-dream": {
                "name": "Watercolor Dream",
                "description": "Watercolor paint + soft bloom + warm grain. Fine art feel.",
                "effects": [
                    {"name": "watercolor", "params": {"edge_strength": 0.6, "blur_radius": 5, "paper_texture": 0.4, "mood": "vibrant", "seed": 42}},
                    {"name": "softbloom", "params": {"radius": 10, "intensity": 0.3, "threshold": 200, "mood": "ethereal"}},
                    {"name": "filmgrainwarm", "params": {"amount": 0.08, "warmth": 0.2, "mood": "vintage", "seed": 42}},
                ],
            },
            "cosmic-frost": {
                "name": "Cosmic Frost",
                "description": "Frost sparkle + lens flare + rainbow. Sci-fi winter wonderland.",
                "effects": [
                    {"name": "sparkle", "params": {"density": 0.005, "size": 5, "mood": "frost", "spread": "edges", "seed": 42}},
                    {"name": "lensflare", "params": {"position_x": 0.5, "position_y": 0.2, "intensity": 0.8, "mood": "sci_fi", "streaks": 4, "size": 0.2}},
                    {"name": "rainbowshift", "params": {"speed": 0.3, "direction": "radial", "opacity": 0.15, "mood": "smooth"}},
                ],
            },
            "expired-memory": {
                "name": "Expired Memory",
                "description": "Expired film + watercolor + soft bloom. Faded nostalgic dream.",
                "effects": [
                    {"name": "filmgrainwarm", "params": {"amount": 0.25, "size": 2.5, "warmth": 0.6, "mood": "expired", "seed": 42}},
                    {"name": "watercolor", "params": {"edge_strength": 0.3, "blur_radius": 10, "paper_texture": 0.2, "mood": "faded", "seed": 42}},
                    {"name": "softbloom", "params": {"radius": 25, "intensity": 0.4, "threshold": 150, "mood": "dreamy"}},
                ],
            },
        },
    },
}


def list_packages() -> list[dict]:
    """List all packages with their recipe counts."""
    result = []
    for key, pkg in PACKAGES.items():
        result.append({
            "key": key,
            "name": pkg["name"],
            "description": pkg["description"],
            "recipe_count": len(pkg["recipes"]),
            "effects_used": pkg["effects_used"],
        })
    return result


def get_package(key: str) -> dict | None:
    """Get a package by key."""
    return PACKAGES.get(key)


def get_recipe(package_key: str, recipe_key: str) -> dict | None:
    """Get a specific recipe from a package."""
    pkg = PACKAGES.get(package_key)
    if not pkg:
        return None
    return pkg["recipes"].get(recipe_key)


def list_package_recipes(package_key: str) -> list[dict]:
    """List all recipes in a package."""
    pkg = PACKAGES.get(package_key)
    if not pkg:
        return []
    result = []
    for key, recipe in pkg["recipes"].items():
        result.append({
            "key": key,
            "name": recipe["name"],
            "description": recipe["description"],
            "effect_count": len(recipe["effects"]),
            "effects": recipe["effects"],
        })
    return result

"""
Entropic -- Built-in Presets
Curated effect chains designed by the Mad Scientist.

Each preset is a recipe: a named chain of effects with tuned parameters
that produce a specific aesthetic when applied in sequence.

Categories:
    Classic     -- Nostalgic analog looks (VHS, CRT, surveillance)
    Cinematic   -- Film-grade moods (noir, dream, cyberpunk)
    Experimental-- Wild combinations, unexpected textures
    Extreme     -- Maximum destruction, datamosh-adjacent chaos
    Subtle      -- Gentle touches, film grain, soft color grades
"""

BUILT_IN_PRESETS = [
    # =========================================================================
    # CLASSIC (6 presets)
    # =========================================================================
    {
        "name": "VHS Nostalgia",
        "description": "Degraded VHS tape pulled from a cardboard box in your parents' garage. "
                       "Tracking errors, color bleed, and analog noise. Best on home video footage.",
        "category": "Classic",
        "effects": [
            {"name": "vhs", "params": {"tracking": 0.7, "noise_amount": 0.35, "color_bleed": 8, "seed": 77}},
            {"name": "scanlines", "params": {"line_width": 2, "opacity": 0.25, "flicker": True, "color": [0, 0, 0]}},
            {"name": "chromatic", "params": {"offset": 3, "direction": "horizontal"}},
            {"name": "saturation", "params": {"amount": 0.8, "channel": "all"}},
            {"name": "temperature", "params": {"temp": 15}},
            {"name": "noise", "params": {"amount": 0.1, "noise_type": "gaussian", "seed": 33}},
        ],
        "tags": ["retro", "analog", "tape", "90s", "lo-fi", "warm"],
    },
    {
        "name": "CRT Monitor",
        "description": "Late-night terminal glow. Green-tinted phosphor scanlines with subtle "
                       "barrel distortion feel. Works on anything you want to look like a hacker movie.",
        "category": "Classic",
        "effects": [
            {"name": "scanlines", "params": {"line_width": 3, "opacity": 0.5, "flicker": True, "color": [0, 20, 0]}},
            {"name": "chromatic", "params": {"offset": 2, "direction": "radial"}},
            {"name": "contrast", "params": {"amount": 30, "curve": "linear"}},
            {"name": "saturation", "params": {"amount": 0.6, "channel": "all"}},
            {"name": "temperature", "params": {"temp": -20}},
            {"name": "sharpen", "params": {"amount": 1.5}},
        ],
        "tags": ["monitor", "screen", "terminal", "phosphor", "green", "tech"],
    },
    {
        "name": "Surveillance Cam",
        "description": "Grainy black-and-white security footage. Low resolution, high contrast, "
                       "salt-and-pepper noise. The feeling of being watched.",
        "category": "Classic",
        "effects": [
            {"name": "saturation", "params": {"amount": 0.0, "channel": "all"}},
            {"name": "contrast", "params": {"amount": 60, "curve": "linear"}},
            {"name": "noise", "params": {"amount": 0.4, "noise_type": "salt_pepper", "seed": 99}},
            {"name": "bitcrush", "params": {"color_depth": 6, "resolution_scale": 0.6}},
            {"name": "scanlines", "params": {"line_width": 1, "opacity": 0.15, "flicker": False, "color": [0, 0, 0]}},
            {"name": "sharpen", "params": {"amount": 2.0}},
        ],
        "tags": ["security", "cctv", "grainy", "monochrome", "dark", "gritty"],
    },
    {
        "name": "Old Film Reel",
        "description": "Faded 8mm home movie look. Desaturated warm tones, soft edges, dust-like "
                       "noise. Smells like a projector bulb.",
        "category": "Classic",
        "effects": [
            {"name": "saturation", "params": {"amount": 0.5, "channel": "all"}},
            {"name": "temperature", "params": {"temp": 35}},
            {"name": "exposure", "params": {"stops": 0.3, "clip_mode": "clip"}},
            {"name": "contrast", "params": {"amount": 20, "curve": "linear"}},
            {"name": "noise", "params": {"amount": 0.25, "noise_type": "gaussian", "seed": 12}},
            {"name": "blur", "params": {"radius": 1, "blur_type": "box"}},
            {"name": "vhs", "params": {"tracking": 0.15, "noise_amount": 0.1, "color_bleed": 2, "seed": 44}},
        ],
        "tags": ["film", "vintage", "8mm", "projector", "warm", "faded"],
    },
    {
        "name": "Analog Broadcast",
        "description": "Broadcast TV signal breaking up. Horizontal displacement glitches, "
                       "color fringing, and scan lines from a bad antenna connection.",
        "category": "Classic",
        "effects": [
            {"name": "displacement", "params": {"block_size": 8, "intensity": 12.0, "seed": 55}},
            {"name": "channelshift", "params": {"r_offset": [4, 0], "g_offset": [0, 0], "b_offset": [-4, 1]}},
            {"name": "scanlines", "params": {"line_width": 2, "opacity": 0.35, "flicker": True, "color": [0, 0, 0]}},
            {"name": "vhs", "params": {"tracking": 0.4, "noise_amount": 0.15, "color_bleed": 5, "seed": 88}},
            {"name": "noise", "params": {"amount": 0.15, "noise_type": "uniform", "seed": 21}},
        ],
        "tags": ["tv", "broadcast", "signal", "static", "antenna", "glitch"],
    },
    {
        "name": "Polaroid Memory",
        "description": "Overexposed instant photo with washed-out highlights and shifted hues. "
                       "The way your memory actually looks, not the way it happened.",
        "category": "Classic",
        "effects": [
            {"name": "exposure", "params": {"stops": 0.6, "clip_mode": "clip"}},
            {"name": "contrast", "params": {"amount": -15, "curve": "linear"}},
            {"name": "saturation", "params": {"amount": 0.65, "channel": "all"}},
            {"name": "temperature", "params": {"temp": 25}},
            {"name": "hueshift", "params": {"degrees": 8}},
            {"name": "blur", "params": {"radius": 1, "blur_type": "box"}},
            {"name": "noise", "params": {"amount": 0.08, "noise_type": "gaussian", "seed": 7}},
        ],
        "tags": ["polaroid", "instant", "washed", "memory", "warm", "soft"],
    },

    # =========================================================================
    # CINEMATIC (6 presets)
    # =========================================================================
    {
        "name": "Dream Sequence",
        "description": "Soft focus haze with shifted hues and gentle wave distortion. "
                       "The world seen through half-closed eyes at 4am. For transitions and intros.",
        "category": "Cinematic",
        "effects": [
            {"name": "blur", "params": {"radius": 4, "blur_type": "box"}},
            {"name": "exposure", "params": {"stops": 0.5, "clip_mode": "clip"}},
            {"name": "saturation", "params": {"amount": 1.4, "channel": "all"}},
            {"name": "hueshift", "params": {"degrees": 15}},
            {"name": "wave", "params": {"amplitude": 3.0, "frequency": 0.01, "direction": "horizontal"}},
            {"name": "chromatic", "params": {"offset": 4, "direction": "radial"}},
            {"name": "contrast", "params": {"amount": -10, "curve": "linear"}},
        ],
        "tags": ["dream", "ethereal", "haze", "soft", "surreal", "psychedelic"],
    },
    {
        "name": "Cyberpunk Night",
        "description": "Neon-drenched urban darkness. Cranked saturation, cold temperature, "
                       "chromatic aberration like cheap optics catching city light.",
        "category": "Cinematic",
        "effects": [
            {"name": "exposure", "params": {"stops": -0.4, "clip_mode": "clip"}},
            {"name": "contrast", "params": {"amount": 45, "curve": "linear"}},
            {"name": "saturation", "params": {"amount": 2.5, "channel": "all"}},
            {"name": "temperature", "params": {"temp": -40}},
            {"name": "chromatic", "params": {"offset": 6, "direction": "radial"}},
            {"name": "edges", "params": {"threshold": 0.6, "mode": "neon"}},
            {"name": "scanlines", "params": {"line_width": 1, "opacity": 0.1, "flicker": False, "color": [0, 0, 30]}},
        ],
        "tags": ["cyberpunk", "neon", "night", "urban", "cold", "futuristic"],
    },
    {
        "name": "Noir",
        "description": "Black and white with crushed blacks and blown highlights. "
                       "Hard shadows, no mercy. For when the story is heavier than color can hold.",
        "category": "Cinematic",
        "effects": [
            {"name": "saturation", "params": {"amount": 0.0, "channel": "all"}},
            {"name": "contrast", "params": {"amount": 70, "curve": "linear"}},
            {"name": "exposure", "params": {"stops": -0.3, "clip_mode": "clip"}},
            {"name": "sharpen", "params": {"amount": 1.8}},
            {"name": "noise", "params": {"amount": 0.12, "noise_type": "gaussian", "seed": 42}},
        ],
        "tags": ["noir", "bw", "monochrome", "dark", "contrast", "dramatic"],
    },
    {
        "name": "Film Burn",
        "description": "Overexposed film gate with warm color bleeding and blown-out highlights. "
                       "The projector jammed and the celluloid started to melt.",
        "category": "Cinematic",
        "effects": [
            {"name": "exposure", "params": {"stops": 1.2, "clip_mode": "clip"}},
            {"name": "temperature", "params": {"temp": 60}},
            {"name": "saturation", "params": {"amount": 1.8, "channel": "r"}},
            {"name": "contrast", "params": {"amount": -20, "curve": "linear"}},
            {"name": "channelshift", "params": {"r_offset": [8, 3], "g_offset": [0, 0], "b_offset": [-3, -1]}},
            {"name": "blur", "params": {"radius": 2, "blur_type": "box"}},
            {"name": "noise", "params": {"amount": 0.15, "noise_type": "gaussian", "seed": 66}},
        ],
        "tags": ["burn", "overexposed", "warm", "film", "damaged", "hot"],
    },
    {
        "name": "Underwater",
        "description": "Cool blue-green wash with soft caustic wave distortion. "
                       "Sound is muffled. Light bends. Everything moves slowly.",
        "category": "Cinematic",
        "effects": [
            {"name": "temperature", "params": {"temp": -55}},
            {"name": "saturation", "params": {"amount": 0.7, "channel": "r"}},
            {"name": "saturation", "params": {"amount": 1.3, "channel": "b"}},
            {"name": "wave", "params": {"amplitude": 6.0, "frequency": 0.02, "direction": "vertical"}},
            {"name": "wave", "params": {"amplitude": 4.0, "frequency": 0.015, "direction": "horizontal"}},
            {"name": "blur", "params": {"radius": 2, "blur_type": "box"}},
            {"name": "contrast", "params": {"amount": -15, "curve": "linear"}},
            {"name": "exposure", "params": {"stops": -0.2, "clip_mode": "clip"}},
        ],
        "tags": ["underwater", "aquatic", "blue", "cool", "fluid", "dreamy"],
    },
    {
        "name": "Golden Hour",
        "description": "Late afternoon warmth with lifted shadows and soft saturation. "
                       "Everything looks better when the sun is low and the world is amber.",
        "category": "Cinematic",
        "effects": [
            {"name": "temperature", "params": {"temp": 45}},
            {"name": "exposure", "params": {"stops": 0.3, "clip_mode": "clip"}},
            {"name": "contrast", "params": {"amount": 15, "curve": "linear"}},
            {"name": "saturation", "params": {"amount": 1.3, "channel": "all"}},
            {"name": "hueshift", "params": {"degrees": 5}},
            {"name": "blur", "params": {"radius": 1, "blur_type": "box"}},
        ],
        "tags": ["golden", "warm", "sunset", "amber", "soft", "natural"],
    },

    # =========================================================================
    # EXPERIMENTAL (6 presets)
    # =========================================================================
    {
        "name": "Phantom Limb",
        "description": "Each color channel lives in a different timezone. Red remembers the past, "
                       "blue predicts the future, green stays present. Disembodied RGB halos "
                       "trail every moving object like afterimages from a fever.",
        "category": "Experimental",
        "effects": [
            {"name": "channelshift", "params": {"r_offset": [25, 8], "g_offset": [0, 0], "b_offset": [-25, -8]}},
            {"name": "chromatic", "params": {"offset": 12, "direction": "radial"}},
            {"name": "wave", "params": {"amplitude": 5.0, "frequency": 0.03, "direction": "horizontal"}},
            {"name": "saturation", "params": {"amount": 2.2, "channel": "all"}},
            {"name": "contrast", "params": {"amount": 35, "curve": "linear"}},
        ],
        "tags": ["rgb", "split", "trippy", "afterimage", "psychedelic", "color"],
    },
    {
        "name": "Rorschach",
        "description": "Vertical mirror meets edge detection. Your footage becomes an inkblot test. "
                       "What you see says more about you than the video.",
        "category": "Experimental",
        "effects": [
            {"name": "mirror", "params": {"axis": "vertical", "position": 0.5}},
            {"name": "edges", "params": {"threshold": 0.25, "mode": "neon"}},
            {"name": "invert", "params": {"channel": "all", "amount": 0.5}},
            {"name": "contrast", "params": {"amount": 50, "curve": "linear"}},
            {"name": "saturation", "params": {"amount": 3.0, "channel": "all"}},
            {"name": "hueshift", "params": {"degrees": 90}},
        ],
        "tags": ["mirror", "symmetry", "neon", "inkblot", "abstract", "weird"],
    },
    {
        "name": "Signal from Nowhere",
        "description": "Intercepted transmission from an unknown source. Heavy displacement "
                       "tears the image apart while posterization reduces it to pure data. "
                       "Something is trying to communicate.",
        "category": "Experimental",
        "effects": [
            {"name": "displacement", "params": {"block_size": 12, "intensity": 25.0, "seed": 137}},
            {"name": "posterize", "params": {"levels": 5}},
            {"name": "channelshift", "params": {"r_offset": [15, 0], "g_offset": [0, 5], "b_offset": [-10, -5]}},
            {"name": "scanlines", "params": {"line_width": 4, "opacity": 0.6, "flicker": True, "color": [0, 40, 0]}},
            {"name": "noise", "params": {"amount": 0.3, "noise_type": "uniform", "seed": 42}},
            {"name": "contrast", "params": {"amount": 40, "curve": "linear"}},
        ],
        "tags": ["transmission", "data", "signal", "alien", "glitch", "blocks"],
    },
    {
        "name": "Dissolving Ego",
        "description": "Pixel sorting meets wave distortion meets inverted channels. "
                       "The image melts upward like smoke. Identity becomes pattern. "
                       "Pattern becomes noise. Noise becomes silence.",
        "category": "Experimental",
        "effects": [
            {"name": "pixelsort", "params": {"threshold": 0.35, "sort_by": "brightness", "direction": "vertical"}},
            {"name": "wave", "params": {"amplitude": 12.0, "frequency": 0.04, "direction": "vertical"}},
            {"name": "invert", "params": {"channel": "g", "amount": 0.7}},
            {"name": "hueshift", "params": {"degrees": 180}},
            {"name": "saturation", "params": {"amount": 1.8, "channel": "all"}},
            {"name": "blur", "params": {"radius": 2, "blur_type": "motion"}},
        ],
        "tags": ["melt", "sort", "psychedelic", "abstract", "spiritual", "dissolve"],
    },
    {
        "name": "Hologram",
        "description": "Translucent projection flickering into existence. Scanlines, chromatic "
                       "fringe, blue-shifted and slightly transparent. Like a message from the future "
                       "rendered on insufficient hardware.",
        "category": "Experimental",
        "effects": [
            {"name": "temperature", "params": {"temp": -60}},
            {"name": "saturation", "params": {"amount": 0.4, "channel": "r"}},
            {"name": "saturation", "params": {"amount": 2.0, "channel": "b"}},
            {"name": "scanlines", "params": {"line_width": 2, "opacity": 0.5, "flicker": True, "color": [0, 80, 120]}},
            {"name": "chromatic", "params": {"offset": 8, "direction": "horizontal"}},
            {"name": "exposure", "params": {"stops": 0.8, "clip_mode": "clip"}},
            {"name": "contrast", "params": {"amount": 25, "curve": "linear"}},
            {"name": "edges", "params": {"threshold": 0.5, "mode": "overlay"}},
        ],
        "tags": ["hologram", "projection", "sci-fi", "blue", "futuristic", "flicker"],
    },
    {
        "name": "Thermal Vision",
        "description": "False-color thermal imaging. Posterized into heat bands with inverted "
                       "luminance and shifted hues. Cold things glow purple, hot things scream yellow.",
        "category": "Experimental",
        "effects": [
            {"name": "saturation", "params": {"amount": 0.0, "channel": "all"}},
            {"name": "invert", "params": {"channel": "all", "amount": 1.0}},
            {"name": "posterize", "params": {"levels": 8}},
            {"name": "hueshift", "params": {"degrees": 240}},
            {"name": "saturation", "params": {"amount": 3.5, "channel": "all"}},
            {"name": "contrast", "params": {"amount": 35, "curve": "linear"}},
            {"name": "temperature", "params": {"temp": 30}},
        ],
        "tags": ["thermal", "infrared", "false-color", "military", "heat", "vision"],
    },

    # =========================================================================
    # EXTREME (4 presets)
    # =========================================================================
    {
        "name": "Total Collapse",
        "description": "Every destructive effect at once. The image is barely recognizable. "
                       "Blocks scatter, pixels sort, channels explode, resolution crumbles. "
                       "This is what data sounds like when it screams.",
        "category": "Extreme",
        "effects": [
            {"name": "displacement", "params": {"block_size": 8, "intensity": 40.0, "seed": 666}},
            {"name": "pixelsort", "params": {"threshold": 0.2, "sort_by": "hue", "direction": "horizontal"}},
            {"name": "channelshift", "params": {"r_offset": [40, 15], "g_offset": [-20, -10], "b_offset": [10, 30]}},
            {"name": "bitcrush", "params": {"color_depth": 2, "resolution_scale": 0.4}},
            {"name": "wave", "params": {"amplitude": 30.0, "frequency": 0.08, "direction": "horizontal"}},
            {"name": "noise", "params": {"amount": 0.5, "noise_type": "uniform", "seed": 13}},
            {"name": "contrast", "params": {"amount": 80, "curve": "linear"}},
            {"name": "saturation", "params": {"amount": 3.5, "channel": "all"}},
        ],
        "tags": ["destroy", "chaos", "maximum", "datamosh", "broken", "harsh"],
    },
    {
        "name": "Bit Rot",
        "description": "Digital decay at the byte level. Extreme bitcrushing with color depth "
                       "stripped to almost nothing, resolution halved, then sharpened to make "
                       "every artifact razor-edged. Files don't die -- they corrode.",
        "category": "Extreme",
        "effects": [
            {"name": "bitcrush", "params": {"color_depth": 2, "resolution_scale": 0.3}},
            {"name": "posterize", "params": {"levels": 3}},
            {"name": "sharpen", "params": {"amount": 3.0}},
            {"name": "channelshift", "params": {"r_offset": [6, 0], "g_offset": [0, 3], "b_offset": [-6, -3]}},
            {"name": "displacement", "params": {"block_size": 4, "intensity": 15.0, "seed": 404}},
            {"name": "contrast", "params": {"amount": 90, "curve": "linear"}},
            {"name": "noise", "params": {"amount": 0.3, "noise_type": "salt_pepper", "seed": 808}},
        ],
        "tags": ["bitrot", "corruption", "digital", "decay", "lo-fi", "destroyed"],
    },
    {
        "name": "Earthquake",
        "description": "The ground shakes and the image shatters. Massive block displacement, "
                       "aggressive wave distortion in both directions, motion blur streaks. "
                       "Nothing stays where it should be.",
        "category": "Extreme",
        "effects": [
            {"name": "displacement", "params": {"block_size": 16, "intensity": 45.0, "seed": 911}},
            {"name": "wave", "params": {"amplitude": 25.0, "frequency": 0.06, "direction": "horizontal"}},
            {"name": "wave", "params": {"amplitude": 15.0, "frequency": 0.04, "direction": "vertical"}},
            {"name": "blur", "params": {"radius": 5, "blur_type": "motion"}},
            {"name": "channelshift", "params": {"r_offset": [12, 5], "g_offset": [-8, -3], "b_offset": [5, -7]}},
            {"name": "noise", "params": {"amount": 0.25, "noise_type": "gaussian", "seed": 777}},
            {"name": "contrast", "params": {"amount": 30, "curve": "linear"}},
        ],
        "tags": ["shake", "destruction", "displacement", "violent", "motion", "chaos"],
    },
    {
        "name": "Black Hole",
        "description": "Reality inverts and collapses. Full color inversion, crushed to near-black, "
                       "then edges ripped out in neon. Like staring into the event horizon "
                       "of a monitor that's consuming itself.",
        "category": "Extreme",
        "effects": [
            {"name": "invert", "params": {"channel": "all", "amount": 1.0}},
            {"name": "exposure", "params": {"stops": -2.0, "clip_mode": "clip"}},
            {"name": "edges", "params": {"threshold": 0.15, "mode": "neon"}},
            {"name": "contrast", "params": {"amount": 95, "curve": "linear"}},
            {"name": "saturation", "params": {"amount": 4.0, "channel": "all"}},
            {"name": "chromatic", "params": {"offset": 15, "direction": "radial"}},
            {"name": "pixelsort", "params": {"threshold": 0.4, "sort_by": "saturation", "direction": "vertical"}},
            {"name": "hueshift", "params": {"degrees": 120}},
        ],
        "tags": ["void", "invert", "neon", "dark", "cosmic", "destruction"],
    },

    # =========================================================================
    # SUBTLE (5 presets)
    # =========================================================================
    {
        "name": "Film Grain",
        "description": "Barely-there organic grain that adds texture without changing the image. "
                       "Like shooting on 35mm but keeping it clean. The camera loved you.",
        "category": "Subtle",
        "effects": [
            {"name": "noise", "params": {"amount": 0.08, "noise_type": "gaussian", "seed": 42}},
            {"name": "contrast", "params": {"amount": 5, "curve": "linear"}},
            {"name": "saturation", "params": {"amount": 0.95, "channel": "all"}},
        ],
        "tags": ["grain", "film", "texture", "organic", "clean", "minimal"],
    },
    {
        "name": "Soft Glow",
        "description": "Gentle bloom on highlights with a whisper of warmth. "
                       "Skin looks perfect, lights look magical, everything feels kind.",
        "category": "Subtle",
        "effects": [
            {"name": "blur", "params": {"radius": 2, "blur_type": "box"}},
            {"name": "exposure", "params": {"stops": 0.15, "clip_mode": "clip"}},
            {"name": "contrast", "params": {"amount": -8, "curve": "linear"}},
            {"name": "temperature", "params": {"temp": 10}},
            {"name": "saturation", "params": {"amount": 1.1, "channel": "all"}},
        ],
        "tags": ["glow", "soft", "bloom", "warm", "flattering", "beauty"],
    },
    {
        "name": "Faded Denim",
        "description": "Cool desaturated tones like a favorite pair of worn-in jeans. "
                       "Slightly lifted blacks, muted colors, effortlessly cool.",
        "category": "Subtle",
        "effects": [
            {"name": "saturation", "params": {"amount": 0.6, "channel": "all"}},
            {"name": "temperature", "params": {"temp": -12}},
            {"name": "contrast", "params": {"amount": 10, "curve": "linear"}},
            {"name": "exposure", "params": {"stops": 0.1, "clip_mode": "clip"}},
        ],
        "tags": ["cool", "muted", "desaturated", "casual", "modern", "clean"],
    },
    {
        "name": "Whisper",
        "description": "Almost invisible chromatic aberration and the faintest hint of scanlines. "
                       "You can't quite tell what's different but something feels cinematic.",
        "category": "Subtle",
        "effects": [
            {"name": "chromatic", "params": {"offset": 1, "direction": "radial"}},
            {"name": "scanlines", "params": {"line_width": 1, "opacity": 0.05, "flicker": False, "color": [0, 0, 0]}},
            {"name": "noise", "params": {"amount": 0.04, "noise_type": "gaussian", "seed": 7}},
            {"name": "contrast", "params": {"amount": 8, "curve": "linear"}},
        ],
        "tags": ["subtle", "cinematic", "barely-there", "texture", "polish", "professional"],
    },
    {
        "name": "Morning Light",
        "description": "Gentle overexposure with warm tones and slightly reduced contrast. "
                       "The way the room looks when you first open the curtains.",
        "category": "Subtle",
        "effects": [
            {"name": "exposure", "params": {"stops": 0.25, "clip_mode": "clip"}},
            {"name": "temperature", "params": {"temp": 18}},
            {"name": "contrast", "params": {"amount": -5, "curve": "linear"}},
            {"name": "saturation", "params": {"amount": 1.15, "channel": "all"}},
            {"name": "noise", "params": {"amount": 0.03, "noise_type": "gaussian", "seed": 5}},
        ],
        "tags": ["warm", "morning", "light", "gentle", "natural", "peaceful"],
    },
]


def get_preset(name: str) -> dict | None:
    """Look up a preset by name (case-insensitive)."""
    name_lower = name.lower()
    for preset in BUILT_IN_PRESETS:
        if preset["name"].lower() == name_lower:
            return preset
    return None


def get_presets_by_category(category: str) -> list[dict]:
    """Get all presets in a category."""
    return [p for p in BUILT_IN_PRESETS if p["category"].lower() == category.lower()]


def get_presets_by_tag(tag: str) -> list[dict]:
    """Get all presets that have a given tag."""
    tag_lower = tag.lower()
    return [p for p in BUILT_IN_PRESETS if tag_lower in [t.lower() for t in p["tags"]]]


def list_preset_names() -> list[str]:
    """Return all preset names."""
    return [p["name"] for p in BUILT_IN_PRESETS]


def list_categories() -> list[str]:
    """Return unique categories."""
    return sorted(set(p["category"] for p in BUILT_IN_PRESETS))

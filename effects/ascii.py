"""
Entropic — ASCII Art Effects
Convert video frames to ASCII art rendered back as images.

Techniques from: ascii-image-converter (braille), video-to-ascii (luminance/color),
gradscii-art (optimization), pic2ascii (edge detection).
"""

import numpy as np

# Character sets ordered by visual density (lightest → darkest)
CHARSETS = {
    "dense": " .'`^\",:;Il!i><~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
    "basic": " .:-=+*#%@",
    "block": " ░▒▓█",
    "digits": " .123456789",
    "symbols": " ·•◦○◎●◉⬤",
    "binary": "01",
    "katakana": " ｦｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ",
    "box": " ╴╵╶╷┌─┐│└┘├┤┬┴┼╔═╗║╚╝█",
    "runic": " ᛫ᛁᛚᛉᛏᛒᛗᛞᚨᚲᚺᛊᛈᛟᛜᛠ",
    "shade": " ░▒▓▄▀▌▐▖▗▘▝▚▞█",
    "gothic": " ·†‡§¶‖║╬█",
    "currency": " ¢·°€£¥₹₩₿$",
    "math": " ·+−×÷≈∑∏∫∞",
    "arrows": " ·→↗↑↙↓↘↔↕⇒⇔",
    "stars": " ·⋆✧☆★✦✶✸⬤",
    "chess": " ·♙♟♘♞♗♝♖♜♕♛",
    "dots": " ⠁⠂⠃⠄⠅⠆⠇⡀⡁⣀⣁⣂⣃⣄⣅⣆⣇⣏⣟⣿",
    "emoji": " ·○◐◑●◉⦿⊕⊗⬤",
    "matrix": " .:0ｦ1ｱ2ｲ3ｳ4ｴ5ｵ6ｶ7ｷ8ｸ9ｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ*#",
    "code": " .-:;=+/|()[]<>{}*&#%@!",
    "virus": " ·░¿¡×÷±≠▒§¶†‡▓█",
    "daemon": " ·†‡¤§¶‖║╫╬▓█",
    "hex": " 1C7FE32A54D6908B",
    "octal": " 17352460",
    "base64": " /+1lijtfcr7IvnuxzJLCTYEFUVS32e5sAkPaq469dXbhZpwoy8gGKNDQRHBWMm0O",
}

# Braille dot bit positions: 2-wide × 4-tall grid per character
BRAILLE_DOTS = [
    [0x01, 0x08],
    [0x02, 0x10],
    [0x04, 0x20],
    [0x40, 0x80],
]


def _render_text_to_frame(lines, width, height, font_scale=1.0, color=(255, 255, 255), bg_color=(0, 0, 0)):
    """Render list of ASCII text lines back into an image frame using OpenCV putText.

    Note: OpenCV putText only supports ASCII. For Unicode (braille, block chars),
    use _render_text_pillow() instead.

    Returns (H, W, 3) uint8 BGR array matching original dimensions.
    """
    import cv2

    # Create background
    canvas = np.full((height, width, 3), bg_color, dtype=np.uint8)

    if not lines:
        return canvas

    # Calculate font size to fit all lines
    num_lines = len(lines)
    max_line_len = max(len(line) for line in lines) if lines else 1

    # Font: FONT_HERSHEY_SIMPLEX for clean monospace-like rendering
    font = cv2.FONT_HERSHEY_SIMPLEX

    # Calculate scale: fit widest line and all rows
    # getTextSize returns ((width, height), baseline)
    test_size = cv2.getTextSize("X", font, 1.0, 1)
    char_w = test_size[0][0]
    char_h = test_size[0][1] + test_size[1]

    scale_x = (width * 0.98) / (max_line_len * char_w) if max_line_len > 0 else 1.0
    scale_y = (height * 0.95) / (num_lines * char_h) if num_lines > 0 else 1.0
    scale = min(scale_x, scale_y) * font_scale
    scale = max(0.15, min(scale, 3.0))

    thickness = max(1, int(scale * 1.2))

    # Recalculate char dimensions at final scale
    test_size = cv2.getTextSize("X", font, scale, thickness)
    final_char_h = test_size[0][1] + test_size[1]
    line_spacing = int(final_char_h * 1.15)

    # Starting Y position (center vertically)
    total_text_h = num_lines * line_spacing
    y_start = max(final_char_h, (height - total_text_h) // 2 + final_char_h)

    for i, line in enumerate(lines):
        y = y_start + i * line_spacing
        if y > height:
            break
        cv2.putText(canvas, line, (2, y), font, scale, color, thickness, cv2.LINE_AA)

    return canvas


def _render_text_pillow(lines, width, height, font_scale=1.0, color=(255, 255, 255), bg_color=(0, 0, 0)):
    """Render Unicode text lines into an image frame using Pillow.

    Pillow supports Unicode (braille U+2800-U+28FF, block elements, etc.)
    unlike OpenCV's putText which only handles ASCII.

    Returns (H, W, 3) uint8 RGB array matching original dimensions.
    """
    from PIL import Image, ImageDraw, ImageFont

    bg_rgb = (int(bg_color[0]), int(bg_color[1]), int(bg_color[2]))
    canvas = Image.new("RGB", (width, height), bg_rgb)

    if not lines:
        return np.array(canvas)

    draw = ImageDraw.Draw(canvas)
    num_lines = len(lines)
    max_line_len = max(len(line) for line in lines) if lines else 1

    # Calculate font size to fit all lines and width
    font_size = max(6, int(height / num_lines * 0.85 * font_scale))
    width_font_size = max(6, int(width / max_line_len * 1.8 * font_scale))
    font_size = min(font_size, width_font_size)

    # Try monospace fonts that support braille Unicode (U+2800-U+28FF)
    # macOS: Menlo has braille, Courier New has braille, Apple Symbols as fallback
    # Linux: DejaVu and Liberation have braille
    font = None
    mono_fonts = [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Supplemental/Courier New.ttf",
        "/System/Library/Fonts/Supplemental/Andale Mono.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Apple Symbols.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    ]
    for font_path in mono_fonts:
        try:
            font = ImageFont.truetype(font_path, font_size)
            break
        except (OSError, IOError):
            continue
    if font is None:
        font = ImageFont.load_default()

    text_color = (int(color[0]), int(color[1]), int(color[2]))

    bbox = draw.textbbox((0, 0), "X", font=font)
    char_h = bbox[3] - bbox[1]
    line_spacing = int(char_h * 1.15)

    total_text_h = num_lines * line_spacing
    y_start = max(0, (height - total_text_h) // 2)

    for i, line in enumerate(lines):
        y = y_start + i * line_spacing
        if y > height:
            break
        draw.text((2, y), line, fill=text_color, font=font)

    return np.array(canvas)


def _render_ascii_colored(lines, small_frame, out_w, out_h, ascii_h, ascii_w):
    """Render ASCII with per-character color sampled from the source image."""
    from PIL import Image, ImageDraw, ImageFont

    canvas = Image.new("RGB", (out_w, out_h), (0, 0, 0))
    if not lines:
        return np.array(canvas)

    draw = ImageDraw.Draw(canvas)
    num_lines = len(lines)
    max_line_len = max(len(line) for line in lines) if lines else 1

    font_size = max(6, min(int(out_h / num_lines * 0.85), int(out_w / max_line_len * 1.8)))
    font = None
    for fp in ["/System/Library/Fonts/Menlo.ttc",
               "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]:
        try:
            font = ImageFont.truetype(fp, font_size)
            break
        except (OSError, IOError):
            continue
    if font is None:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), "X", font=font)
    char_w = max(1, bbox[2] - bbox[0])
    char_h = max(1, bbox[3] - bbox[1])
    line_spacing = int(char_h * 1.15)
    y_start = max(0, (out_h - num_lines * line_spacing) // 2)

    for row_idx, line in enumerate(lines):
        y = y_start + row_idx * line_spacing
        if y > out_h:
            break
        for col_idx, ch in enumerate(line):
            if ch == ' ':
                continue
            # Sample color from source
            src_y = min(row_idx, small_frame.shape[0] - 1)
            src_x = min(col_idx, small_frame.shape[1] - 1)
            color = tuple(int(c) for c in small_frame[src_y, src_x])
            x = 2 + col_idx * char_w
            if x < out_w:
                draw.text((x, y), ch, fill=color, font=font)

    return np.array(canvas)


def ascii_art(frame: np.ndarray, charset: str = "basic", width: int = 80,
              invert: bool = False, color_mode: str = "mono", edge_mix: float = 0.0,
              seed: int = 42, **kwargs) -> np.ndarray:
    """Convert frame to ASCII art rendered back as an image.

    Args:
        frame: (H, W, 3) uint8 BGR array.
        charset: Character set — "basic", "dense", "block", "digits",
                 "symbols", "binary", "katakana".
        width: ASCII width in characters (controls detail level).
        invert: Invert brightness mapping (swap light/dark chars).
        color_mode: "mono" (white on black), "green" (matrix), "amber" (retro),
                    "original" (per-cell color from source), "rainbow" (hue gradient).
        edge_mix: Blend in edge detection (0.0 = none, 1.0 = full).
        seed: Random seed (unused but kept for interface consistency).

    Returns:
        ASCII-art-styled frame (H, W, 3) uint8 BGR.
    """
    h, w = frame.shape[:2]
    width = max(10, min(width, 500))
    chars = CHARSETS.get(charset, CHARSETS["basic"])
    if invert:
        chars = chars[::-1]

    # Compute target height preserving aspect ratio
    # Terminal chars are ~2x taller than wide, but we're rendering back to image
    # so use 0.55 correction factor
    ascii_height = max(1, int(width * (h / w) * 0.55))

    # Downscale frame to ASCII resolution
    import cv2
    small = cv2.resize(frame, (width, ascii_height), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32)

    # Optional edge detection overlay (Sobel)
    if edge_mix > 0:
        sobelx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        edges = np.sqrt(sobelx ** 2 + sobely ** 2)
        edges = np.clip(edges / edges.max() * 255 if edges.max() > 0 else edges, 0, 255)
        # Edges darken the image (make outlines more visible in ASCII)
        gray = gray * (1.0 - edge_mix * edges / 255 * 0.7)
        gray = np.clip(gray, 0, 255)

    # Map pixels to ASCII characters
    num_chars = len(chars)
    lines = []
    for y in range(ascii_height):
        row = ""
        for x in range(width):
            brightness = gray[y, x]
            idx = int(brightness / 256 * num_chars)
            idx = min(idx, num_chars - 1)
            row += chars[idx]
        lines.append(row)

    # Determine text color
    color_map = {
        "mono": (255, 255, 255),
        "green": (0, 255, 0),
        "amber": (0, 191, 255),  # BGR for amber
    }

    if color_mode == "original":
        # Per-cell color from source image — render with Pillow for color per character
        return _render_ascii_colored(lines, small, w, h, ascii_height, width)
    elif color_mode == "rainbow":
        # Rainbow hue gradient across the frame
        import colorsys
        hue = (kwargs.get("frame_index", 0) * 0.02) % 1.0
        r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        text_color = (int(r * 255), int(g * 255), int(b * 255))
        bg = (0, 0, 0)
    else:
        text_color = color_map.get(color_mode, (255, 255, 255))
        bg = (0, 0, 0)

    return _render_text_to_frame(lines, w, h, color=text_color, bg_color=bg)


def braille_art(frame: np.ndarray, width: int = 80, threshold: int = 128,
                invert: bool = False, dither: bool = True,
                color_mode: str = "mono", seed: int = 42, **kwargs) -> np.ndarray:
    """Convert frame to braille unicode art rendered back as an image.

    Each braille character encodes a 2×4 pixel grid (256 patterns).
    This gives ~4× the resolution of standard ASCII art.

    Args:
        frame: (H, W, 3) uint8 BGR array.
        width: Braille width in characters.
        threshold: Brightness threshold for dot on/off (0-255).
        invert: Invert dot pattern.
        dither: Apply Floyd-Steinberg dithering (better detail).
        color_mode: "mono" (white on black), "green" (matrix), "amber" (retro).
        seed: Random seed (unused).

    Returns:
        Braille-art-styled frame (H, W, 3) uint8 BGR.
    """
    import cv2

    h, w = frame.shape[:2]
    width = max(10, min(width, 500))
    threshold = max(0, min(threshold, 255))

    # Each braille char = 2 pixels wide × 4 pixels tall
    char_cols = width
    img_width = char_cols * 2
    aspect_ratio = h / w
    img_height_pixels = int(img_width * aspect_ratio)
    char_rows = max(1, (img_height_pixels + 3) // 4)
    img_height = char_rows * 4

    # Downscale and convert to grayscale
    small = cv2.resize(frame, (img_width, img_height), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32)

    # Floyd-Steinberg dithering
    if dither:
        for y in range(img_height):
            for x in range(img_width):
                old_val = gray[y, x]
                new_val = 255.0 if old_val > threshold else 0.0
                error = old_val - new_val
                gray[y, x] = new_val
                if x + 1 < img_width:
                    gray[y, x + 1] = max(0, min(255, gray[y, x + 1] + error * 7 / 16))
                if y + 1 < img_height:
                    if x - 1 >= 0:
                        gray[y + 1, x - 1] = max(0, min(255, gray[y + 1, x - 1] + error * 3 / 16))
                    gray[y + 1, x] = max(0, min(255, gray[y + 1, x] + error * 5 / 16))
                    if x + 1 < img_width:
                        gray[y + 1, x + 1] = max(0, min(255, gray[y + 1, x + 1] + error * 1 / 16))

    # Convert to braille characters
    lines = []
    for row in range(char_rows):
        line = ""
        for col in range(char_cols):
            bits = 0
            for dy in range(4):
                for dx in range(2):
                    py = row * 4 + dy
                    px = col * 2 + dx
                    if py < img_height and px < img_width:
                        pixel_on = gray[py, px] > threshold
                        if invert:
                            pixel_on = not pixel_on
                        if pixel_on:
                            bits |= BRAILLE_DOTS[dy][dx]
            line += chr(0x2800 + bits)
        lines.append(line)

    # Determine text color
    color_map = {
        "mono": (255, 255, 255),
        "green": (0, 255, 0),
        "amber": (0, 191, 255),
    }
    text_color = color_map.get(color_mode, (255, 255, 255))

    # Use Pillow renderer — braille characters are Unicode (U+2800-U+28FF)
    # and OpenCV's putText only supports ASCII
    return _render_text_pillow(lines, w, h, color=text_color, bg_color=(0, 0, 0))

"""
Entropic — Destruction Effects
Radical glitch effects that corrupt, tear, mosh, and destroy video at the data level.
These are the AGGRESSIVE effects — not color grading, not gentle filters.
NUCLEAR MODE: Every effect has been pushed to maximum possible destruction.
"""

import numpy as np
import io


# ============================================================================
# 1. DATAMOSH — Optical flow warping (simulates I-frame removal)
# ============================================================================

# Seed-keyed state dict for all destruction effects (prevents cross-chain corruption)
_destruction_state = {}


def _get_destruction_state(key: str, default_factory):
    """Lazy-init state for a destruction effect, keyed by seed."""
    if key not in _destruction_state:
        _destruction_state[key] = default_factory()
    return _destruction_state[key]


def _cleanup_destruction_if_done(key: str, frame_index: int, total_frames: int):
    """Remove state at end of render to prevent memory leaks."""
    if total_frames > 1 and frame_index >= total_frames - 1:
        _destruction_state.pop(key, None)


def datamosh(
    frame: np.ndarray,
    intensity: float = 1.0,
    accumulate: bool = True,
    decay: float = 0.95,
    mode: str = "melt",
    frame_index: int = 0,
    total_frames: int = 1,
    seed: int = 42,
    motion_threshold: float = 0.0,
    macroblock_size: int = 16,
    donor_offset: int = 10,
    blend_mode: str = "normal",
) -> np.ndarray:
    """Simulated datamosh — pixels rip apart and bleed across frames.

    Modes:
        melt: Classic datamosh — old frame warped by new motion. Compounds every
              frame so pixels progressively detach from reality and smear into oblivion.
        bloom: Old frame preserved and smeared outward. Nothing new enters. Ever.
        rip: Motion vectors amplified 10x with random noise injected. Pixels tear
             apart violently. Chunks of image fly across the frame.
        replace: Blocks of old frame randomly stamped over current. I-frame skip sim.
        annihilate: ALL of the above combined. Warped prev frame + random block
                    replacement + row displacement + channel separation. Total war.
        freeze_through: Authentic I-frame removal. Previous frame frozen — only pixels
                        where motion exceeds threshold update with new data. This is
                        what REAL datamosh looks like.
        pframe_extend: P-frame duplication sim. Amplifies and repeats motion vectors
                       from a single moment, extending pixel movement over time.
                       Creates the classic bloom/glide look.
        donor: Motion from current frame, pixel data from a different temporal
               position (donor_offset frames back). Simulates the AE donor layer.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        intensity: How extreme. 1.0=visible, 5.0=insane, 20.0=apocalyptic, 100.0=nuclear.
        accumulate: If True, flow compounds over time (true datamosh behavior).
        decay: How fast old flow fades (0.999 = almost never fades = maximum melt).
        mode: 'melt', 'bloom', 'rip', 'replace', 'annihilate', 'freeze_through',
              'pframe_extend', or 'donor'.
        seed: Random seed.
        motion_threshold: Minimum motion magnitude for pixels to update (0.0-50.0).
                          Higher = only fast-moving pixels break through. Used by
                          freeze_through mode but applicable to all.
        macroblock_size: Block size for codec-authentic effects (8, 16, or 32).
        donor_offset: For donor mode, how many frames back to pull pixel data from.
        blend_mode: How to mix mosh result with current frame.
                    'normal', 'multiply', 'average', 'swap'.

    Returns:
        Datamoshed frame.
    """
    import cv2

    state_key = f"datamosh_{seed}"
    h, w = frame.shape[:2]
    intensity = max(0.1, min(100.0, float(intensity)))
    decay = max(0.0, min(0.9999, float(decay)))
    motion_threshold = max(0.0, min(50.0, float(motion_threshold)))
    macroblock_size = max(8, min(32, int(macroblock_size)))
    donor_offset = max(1, min(120, int(donor_offset)))

    st = _get_destruction_state(state_key, lambda: {
        "prev_frame": None, "flow_accum": None,
        "donor_buffer": [], "frozen_frame": None, "pframe_flow": None,
    })

    # Reset on first frame or if prev_frame is uninitialized/wrong size
    if frame_index == 0 or st["prev_frame"] is None or st["prev_frame"].shape != frame.shape:
        st["prev_frame"] = frame.copy()
        st["flow_accum"] = np.zeros((h, w, 2), dtype=np.float32)
        st["donor_buffer"] = [frame.copy()]
        st["frozen_frame"] = frame.copy()
        st["pframe_flow"] = None
        _cleanup_destruction_if_done(state_key, frame_index, total_frames)
        return frame.copy()

    # Maintain donor buffer (ring buffer of recent frames)
    st["donor_buffer"].append(frame.copy())
    if len(st["donor_buffer"]) > donor_offset + 5:
        st["donor_buffer"] = st["donor_buffer"][-(donor_offset + 5):]

    # Convert to grayscale for flow calculation
    prev_gray = cv2.cvtColor(st["prev_frame"], cv2.COLOR_RGB2GRAY)
    curr_gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

    # Calculate dense optical flow — more pyramid levels at high intensity
    levels = min(5, 3 + int(intensity / 10))
    flow = cv2.calcOpticalFlowFarneback(
        prev_gray, curr_gray, None,
        pyr_scale=0.5, levels=levels, winsize=15,
        iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
    )

    rng = np.random.RandomState(seed + frame_index)

    if mode in ("rip", "annihilate"):
        # VIOLENT flow amplification + random vectors injected
        noise_scale = intensity * 5.0
        noise = rng.normal(0, noise_scale, flow.shape).astype(np.float32)
        # Random explosive bursts in random regions
        num_bursts = max(1, int(intensity))
        for _ in range(num_bursts):
            cy, cx = rng.randint(0, h), rng.randint(0, w)
            radius = rng.randint(10, max(11, min(h, w) // 4))
            yy, xx = np.ogrid[-cy:h-cy, -cx:w-cx]
            mask = (xx*xx + yy*yy) < radius*radius
            burst_strength = intensity * 10.0
            noise[mask, 0] += rng.normal(0, burst_strength)
            noise[mask, 1] += rng.normal(0, burst_strength)
        flow = flow * intensity * 5 + noise

    # Accumulate flow — this is what makes datamosh compound
    if accumulate:
        st["flow_accum"] = st["flow_accum"] * decay + flow * intensity
    else:
        st["flow_accum"] = flow * intensity

    # Create remap coordinates
    map_y, map_x = np.mgrid[0:h, 0:w].astype(np.float32)
    map_x += st["flow_accum"][:, :, 0]
    map_y += st["flow_accum"][:, :, 1]

    if mode == "melt":
        # REAL datamosh: warp the PREVIOUS frame by current motion
        # Old pixels move with new motion — progressively detaches from reality
        result = cv2.remap(
            st["prev_frame"], map_x, map_y,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_WRAP,
        )
        # Compound: prev = warped result, so next frame warps the warp
        st["prev_frame"] = result.copy()

    elif mode == "bloom":
        # Smear previous frame outward — nothing from current frame enters
        result = cv2.remap(
            st["prev_frame"], map_x, map_y,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_WRAP,
        )
        # Channel separation for extra chaos at high intensity
        if intensity > 3.0:
            shift = int(intensity * 2)
            result[:, :, 0] = np.roll(result[:, :, 0], shift, axis=1)
            result[:, :, 2] = np.roll(result[:, :, 2], -shift, axis=1)
        st["prev_frame"] = result.copy()

    elif mode == "replace":
        # I-frame skip: blocks of previous frame stamped over current
        result = frame.copy()
        block_size = max(8, 32 - int(intensity))
        replace_prob = min(0.95, intensity * 0.2)
        for by in range(0, h, block_size):
            for bx in range(0, w, block_size):
                if rng.random() < replace_prob:
                    bh = min(block_size, h - by)
                    bw = min(block_size, w - bx)
                    # Sometimes grab from random position (more chaos)
                    if rng.random() < 0.3 and intensity > 2.0:
                        src_y = rng.randint(0, max(1, h - bh))
                        src_x = rng.randint(0, max(1, w - bw))
                        result[by:by+bh, bx:bx+bw] = st["prev_frame"][src_y:src_y+bh, src_x:src_x+bw]
                    else:
                        result[by:by+bh, bx:bx+bw] = st["prev_frame"][by:by+bh, bx:bx+bw]
        st["prev_frame"] = frame.copy()

    elif mode == "annihilate":
        # EVERYTHING AT ONCE: warp prev + block replace + row tear + channel split
        # 1. Warp previous frame
        warped = cv2.remap(
            st["prev_frame"], map_x, map_y,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_WRAP,
        )
        # 2. Block-replace chunks of current frame with warped prev
        result = frame.copy()
        block_size = max(8, 24 - int(intensity / 2))
        for by in range(0, h, block_size):
            for bx in range(0, w, block_size):
                choice = rng.random()
                bh = min(block_size, h - by)
                bw = min(block_size, w - bx)
                if choice < 0.4:
                    result[by:by+bh, bx:bx+bw] = warped[by:by+bh, bx:bx+bw]
                elif choice < 0.55:
                    sy = rng.randint(0, max(1, h - bh))
                    sx = rng.randint(0, max(1, w - bw))
                    result[by:by+bh, bx:bx+bw] = warped[sy:sy+bh, sx:sx+bw]
                elif choice < 0.65:
                    result[by:by+bh, bx:bx+bw] = 255 - result[by:by+bh, bx:bx+bw]
        # 3. Row displacement — violent horizontal tearing
        num_tears = max(5, int(intensity * 3))
        for _ in range(num_tears):
            y = rng.randint(0, h)
            band = rng.randint(1, max(2, min(h // 5, int(intensity * 5))))
            shift = rng.randint(-int(w * 0.4), int(w * 0.4) + 1)
            end_y = min(y + band, h)
            result[y:end_y] = np.roll(result[y:end_y], shift, axis=1)
        # 4. Channel separation
        ch_shift = max(3, int(intensity * 3))
        result[:, :, 0] = np.roll(result[:, :, 0], ch_shift, axis=1)
        result[:, :, 2] = np.roll(result[:, :, 2], -ch_shift, axis=1)
        result[:, :, 1] = np.roll(result[:, :, 1], ch_shift // 2, axis=0)
        st["prev_frame"] = warped.copy()

    elif mode == "freeze_through":
        # AUTHENTIC I-FRAME REMOVAL: Previous frame stays frozen.
        # Only pixels where motion exceeds threshold get updated with new data.
        # This is what real datamosh looks like — old image persists, new movement
        # "breaks through" in macroblock-sized chunks.
        flow_mag = np.sqrt(flow[:, :, 0]**2 + flow[:, :, 1]**2)

        # Use macroblock-sized regions for codec-authentic look
        mb = macroblock_size
        thresh = max(0.5, motion_threshold if motion_threshold > 0 else intensity * 0.5)

        result = st["frozen_frame"].copy()
        for by in range(0, h, mb):
            for bx in range(0, w, mb):
                bh = min(mb, h - by)
                bw = min(mb, w - bx)
                block_motion = flow_mag[by:by+bh, bx:bx+bw].mean()
                if block_motion > thresh:
                    # This block has enough motion — new pixels break through
                    result[by:by+bh, bx:bx+bw] = frame[by:by+bh, bx:bx+bw]
                    # Update the frozen frame for this block too
                    st["frozen_frame"][by:by+bh, bx:bx+bw] = frame[by:by+bh, bx:bx+bw]

        st["prev_frame"] = frame.copy()

    elif mode == "pframe_extend":
        # P-FRAME DUPLICATION: Capture motion vectors from one moment,
        # then keep applying them repeatedly to extend the motion trail.
        # This creates the "bloom/glide" look where pixels stretch along motion paths.

        # Capture flow on the first non-reset frame, or when motion is strong
        flow_mag = np.sqrt(flow[:, :, 0]**2 + flow[:, :, 1]**2).mean()
        if st["pframe_flow"] is None or flow_mag > intensity * 2.0:
            st["pframe_flow"] = flow.copy()

        # Amplify the captured flow and apply it cumulatively
        extend_flow = st["pframe_flow"] * intensity * 2.0
        if accumulate:
            st["flow_accum"] = st["flow_accum"] * decay + extend_flow
        else:
            st["flow_accum"] = extend_flow

        ext_map_y, ext_map_x = np.mgrid[0:h, 0:w].astype(np.float32)
        ext_map_x += st["flow_accum"][:, :, 0]
        ext_map_y += st["flow_accum"][:, :, 1]

        result = cv2.remap(
            st["prev_frame"], ext_map_x, ext_map_y,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_WRAP,
        )
        st["prev_frame"] = result.copy()

    elif mode == "donor":
        # DONOR-BASED MOSH: Motion vectors from current frame, but pixel data
        # pulled from a different temporal position (donor_offset frames back).
        # Simulates the After Effects "donor layer" technique.
        buf_idx = max(0, len(st["donor_buffer"]) - 1 - donor_offset)
        donor_frame = st["donor_buffer"][buf_idx]

        # Warp the donor frame using current motion
        result = cv2.remap(
            donor_frame, map_x, map_y,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_WRAP,
        )
        st["prev_frame"] = frame.copy()

    else:  # "rip" (flow already amplified above)
        result = cv2.remap(
            frame, map_x, map_y,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_WRAP,
        )
        # Inject dead pixel clusters
        if intensity > 3.0:
            num_dead = int(intensity * 50)
            for _ in range(num_dead):
                y, x = rng.randint(0, h), rng.randint(0, w)
                sz = rng.randint(1, max(2, int(intensity)))
                ey, ex = min(y + sz, h), min(x + sz, w)
                result[y:ey, x:ex] = 0 if rng.random() < 0.5 else 255
        st["prev_frame"] = frame.copy()

    # Apply blend mode (from transcript learnings — multiply, average, swap)
    if blend_mode == "multiply":
        result = (result.astype(np.float32) * frame.astype(np.float32) / 255.0)
        result = np.clip(result, 0, 255).astype(np.uint8)
    elif blend_mode == "average":
        result = ((result.astype(np.float32) + frame.astype(np.float32)) / 2.0)
        result = np.clip(result, 0, 255).astype(np.uint8)
    elif blend_mode == "swap":
        # Swap: use motion magnitude to decide which pixels come from which source
        flow_mag = np.sqrt(
            st["flow_accum"][:, :, 0]**2 + st["flow_accum"][:, :, 1]**2
        )
        if flow_mag.max() > 0:
            swap_mask = (flow_mag / flow_mag.max()) > 0.5
            swap_3d = swap_mask[:, :, np.newaxis]
            result = np.where(swap_3d, result, frame)

    # Apply motion threshold gating (applicable to all modes)
    if motion_threshold > 0.0 and mode not in ("freeze_through",):
        flow_mag = np.sqrt(flow[:, :, 0]**2 + flow[:, :, 1]**2)
        static_mask = flow_mag < motion_threshold
        static_3d = static_mask[:, :, np.newaxis]
        result = np.where(static_3d, frame, result)

    _cleanup_destruction_if_done(state_key, frame_index, total_frames)
    return result


# ============================================================================
# 2. BYTE CORRUPT — JPEG data bending
# ============================================================================

def byte_corrupt(
    frame: np.ndarray,
    amount: int = 20,
    jpeg_quality: int = 75,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Corrupt JPEG data bytes to create authentic glitch artifacts.

    Saves frame as JPEG in memory, corrupts random bytes in the data region,
    then reloads. Creates unpredictable, authentic codec-level corruption.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        amount: Number of bytes to corrupt (1-500).
        jpeg_quality: JPEG quality for intermediate encoding (lower = more artifacts).
        seed: Random seed.

    Returns:
        Corrupted frame (original if corruption breaks the file entirely).
    """
    from PIL import Image

    amount = max(1, min(500, int(amount)))
    jpeg_quality = max(1, min(95, int(jpeg_quality)))
    rng = np.random.RandomState(seed + frame_index)

    img = Image.fromarray(frame)

    # Save to memory buffer as JPEG
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=jpeg_quality)
    data = bytearray(buf.getvalue())

    if len(data) < 100:
        return frame.copy()

    # Always get the JPEG-compressed version first (this alone adds artifacts)
    buf_clean = io.BytesIO(bytes(data))
    jpeg_frame = np.array(Image.open(buf_clean).convert("RGB"))

    # Find the SOS marker (0xFF 0xDA) — corruption after this affects image data
    sos_pos = bytes(data).find(b'\xff\xda')
    safe_start = max(20, sos_pos + 12) if sos_pos > 0 else 20
    safe_end = len(data) - 2

    # Try byte corruption with multiple attempts
    for attempt in range(3):
        corrupted_data = bytearray(data)
        corrupt_amount = amount * (attempt + 1)  # More aggressive each attempt

        for _ in range(corrupt_amount):
            pos = rng.randint(safe_start, safe_end)
            strategy = rng.randint(0, 5)
            if strategy == 0:
                corrupted_data[pos] = rng.randint(0, 256)
            elif strategy == 1:
                corrupted_data[pos] = corrupted_data[pos] ^ 0xFF
            elif strategy == 2:
                corrupted_data[pos] = 0
            elif strategy == 3:
                corrupted_data[pos] = 255
            else:
                # Byte swap with neighbor
                if pos + 1 < safe_end:
                    corrupted_data[pos], corrupted_data[pos+1] = corrupted_data[pos+1], corrupted_data[pos]

        try:
            buf2 = io.BytesIO(bytes(corrupted_data))
            corrupted = Image.open(buf2)
            corrupted.load()
            result = np.array(corrupted.convert("RGB"))
            if result.shape == frame.shape:
                return result
        except Exception:
            continue

    if jpeg_frame.shape == frame.shape:
        return jpeg_frame
    return frame.copy()


# ============================================================================
# 3. BLOCK CORRUPT — Macroblock displacement
# ============================================================================

def block_corrupt(
    frame: np.ndarray,
    num_blocks: int = 15,
    block_size: int = 32,
    mode: str = "shift",
    placement: str = "random",
    seed: int = 42,
) -> np.ndarray:
    """Corrupt random rectangular blocks — simulates codec macroblock errors.

    Corruption modes:
        shift: Copy block from random offset position
        noise: Fill block with random noise
        repeat: Fill block by repeating its first row
        invert: Invert all colors in block
        zero: Black out the block
        smear: Stretch a single pixel column across the block

    Placement modes:
        random: Place blocks randomly (default)
        sequential: Place blocks left-to-right, top-to-bottom
        radial: Place blocks radiating from center
        edge_detected: Place blocks near detected edges

    Args:
        frame: (H, W, 3) uint8 RGB array.
        num_blocks: Number of blocks to corrupt (1-200).
        block_size: Size of each block in pixels (4-256).
        mode: Corruption mode ('shift', 'noise', 'repeat', 'invert', 'zero', 'smear', 'random').
        placement: Placement strategy ('random', 'sequential', 'radial', 'edge_detected').
        seed: Random seed.

    Returns:
        Block-corrupted frame.
    """
    import cv2

    num_blocks = max(1, min(200, int(num_blocks)))
    block_size = max(4, min(256, int(block_size)))
    corruption_modes = ["shift", "noise", "repeat", "invert", "zero", "smear"]
    rng = np.random.RandomState(seed)

    h, w = frame.shape[:2]
    result = frame.copy()

    # Generate block positions based on placement strategy
    if placement == "sequential":
        # Left-to-right, top-to-bottom grid
        positions = []
        for y in range(0, h, block_size):
            for x in range(0, w, block_size):
                positions.append((y, x))
        # Take first num_blocks positions
        positions = positions[:num_blocks]
    elif placement == "radial":
        # Radiate from center outward
        cx, cy = w // 2, h // 2
        positions = []
        for _ in range(num_blocks):
            angle = rng.uniform(0, 2 * np.pi)
            distance = rng.uniform(0, min(cx, cy))
            x = int(cx + distance * np.cos(angle))
            y = int(cy + distance * np.sin(angle))
            x = max(0, min(w - block_size, x))
            y = max(0, min(h - block_size, y))
            positions.append((y, x))
    elif placement == "edge_detected":
        # Detect edges, place blocks near them
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_coords = np.argwhere(edges > 0)
        if len(edge_coords) == 0:
            # Fallback to random if no edges
            positions = [(rng.randint(0, max(1, h - block_size)),
                          rng.randint(0, max(1, w - block_size)))
                         for _ in range(num_blocks)]
        else:
            positions = []
            for _ in range(num_blocks):
                edge_pt = edge_coords[rng.randint(0, len(edge_coords))]
                y, x = edge_pt[0], edge_pt[1]
                y = max(0, min(h - block_size, y))
                x = max(0, min(w - block_size, x))
                positions.append((y, x))
    else:  # random
        positions = [(rng.randint(0, max(1, h - block_size)),
                      rng.randint(0, max(1, w - block_size)))
                     for _ in range(num_blocks)]

    for y, x in positions:
        bh = min(block_size, h - y)
        bw = min(block_size, w - x)

        m = mode if mode != "random" else corruption_modes[rng.randint(0, len(corruption_modes))]

        if m == "shift":
            sy = rng.randint(0, max(1, h - bh))
            sx = rng.randint(0, max(1, w - bw))
            result[y:y+bh, x:x+bw] = frame[sy:sy+bh, sx:sx+bw]
        elif m == "noise":
            result[y:y+bh, x:x+bw] = rng.randint(0, 256, (bh, bw, 3), dtype=np.uint8)
        elif m == "repeat":
            row = result[y, x:x+bw].copy()
            result[y:y+bh, x:x+bw] = row[np.newaxis, :, :]
        elif m == "invert":
            result[y:y+bh, x:x+bw] = 255 - result[y:y+bh, x:x+bw]
        elif m == "zero":
            result[y:y+bh, x:x+bw] = 0
        elif m == "smear":
            col_idx = rng.randint(x, max(x + 1, x + bw))
            col = result[y:y+bh, col_idx:col_idx+1, :].copy()
            result[y:y+bh, x:x+bw] = col

    return result


# ============================================================================
# 4. ROW SHIFT — Scanline displacement / horizontal tearing
# ============================================================================

def row_shift(
    frame: np.ndarray,
    max_shift: int = 30,
    density: float = 0.3,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Horizontally shift random rows — creates torn/signal interference look.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        max_shift: Maximum pixel shift per row (-max to +max). Up to full frame width.
        density: Fraction of rows to shift (0.0-1.0).
        seed: Random seed.

    Returns:
        Row-shifted frame.
    """
    h, w = frame.shape[:2]
    max_shift = max(1, min(w, int(max_shift)))
    density = max(0.0, min(1.0, float(density)))

    rng = np.random.RandomState(seed + frame_index)
    result = frame.copy()

    for y in range(h):
        if rng.random() < density:
            shift = rng.randint(-max_shift, max_shift + 1)
            result[y] = np.roll(result[y], shift, axis=0)

    return result


# ============================================================================
# 5. JPEG ARTIFACTS — Synthetic codec compression damage
# ============================================================================

def jpeg_artifacts(
    frame: np.ndarray,
    quality: int = 5,
    block_damage: int = 20,
    seed: int = 42,
) -> np.ndarray:
    """Simulate heavy JPEG compression artifacts.

    Double-compresses at extremely low quality, then optionally corrupts
    random 8x8 blocks to simulate codec errors.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        quality: JPEG quality (1-30, lower = more artifacts).
        block_damage: Number of 8x8 blocks to corrupt additionally (0-200).
        seed: Random seed.

    Returns:
        JPEG-damaged frame.
    """
    from PIL import Image

    quality = max(1, min(30, int(quality)))
    block_damage = max(0, min(200, int(block_damage)))
    rng = np.random.RandomState(seed)

    img = Image.fromarray(frame)

    # Triple-compress at very low quality for maximum artifacts
    for _ in range(3):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        buf.seek(0)
        img = Image.open(buf)
    result = np.array(img.convert("RGB"))

    # Additional 8x8 block corruption
    if block_damage > 0:
        h, w = result.shape[:2]
        for _ in range(block_damage):
            by = rng.randint(0, max(1, h - 8)) & ~7
            bx = rng.randint(0, max(1, w - 8)) & ~7
            block = result[by:by+8, bx:bx+8].copy()
            mean_val = block.mean(axis=(0, 1)).astype(np.uint8)
            bright = (block.mean(axis=2) > block.mean(axis=2).mean())
            result[by:by+8, bx:bx+8][bright] = np.minimum(mean_val + 60, 255)
            result[by:by+8, bx:bx+8][~bright] = np.maximum(mean_val - 60, 0)

    return result


# ============================================================================
# 6. INVERT BANDS — Alternating row inversion
# ============================================================================

def invert_bands(
    frame: np.ndarray,
    band_height: int = 10,
    offset: int = 0,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Invert alternating horizontal bands — CRT/VHS damage simulation.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        band_height: Height of each band in pixels (2-100).
        offset: Vertical offset for band position animation.

    Returns:
        Band-inverted frame.
    """
    band_height = max(2, min(100, int(band_height)))

    result = frame.copy()
    h = frame.shape[0]

    anim_offset = (offset + frame_index * 2) % (band_height * 2)

    for y in range(0, h, band_height * 2):
        start = (y + anim_offset) % h
        end = min(start + band_height, h)
        result[start:end] = 255 - result[start:end]

    return result


# ============================================================================
# 7. DATA BEND — Treat frame bytes as audio waveform, apply DSP
# ============================================================================

def data_bend(
    frame: np.ndarray,
    effect: str = "echo",
    intensity: float = 0.5,
    seed: int = 42,
) -> np.ndarray:
    """Treat pixel data as an audio signal and apply DSP effects.

    This is the cross-modal experiment: audio processing on video data.

    Effects:
        echo: Repeat signal with decay (ghosting)
        distort: Hard clip the signal (posterization on steroids)
        bitcrush_audio: Reduce sample resolution (extreme quantization)
        reverse: Reverse chunks of pixel data (data scramble)
        feedback: Multiple echo taps that feed into each other (catastrophic)

    Args:
        frame: (H, W, 3) uint8 RGB array.
        effect: DSP effect to apply.
        intensity: Effect strength (0.0-1.0).
        seed: Random seed.

    Returns:
        Data-bent frame.
    """
    intensity = max(0.0, min(1.0, float(intensity)))

    # Flatten frame to 1D "audio signal"
    flat = frame.flatten().astype(np.float32) / 255.0

    if effect == "echo":
        delay = int(frame.shape[1] * 3 * intensity * 10)
        delay = max(1, min(len(flat) // 2, delay))
        echo_signal = np.zeros_like(flat)
        echo_signal[delay:] = flat[:-delay] * intensity * 0.7
        flat = flat + echo_signal

    elif effect == "distort":
        threshold = max(0.05, 1.0 - intensity * 0.95)
        flat = np.clip(flat / threshold, 0.0, 1.0)

    elif effect == "bitcrush_audio":
        levels = max(2, int(256 * (1.0 - intensity * 0.98)))
        flat = np.round(flat * levels) / levels

    elif effect == "reverse":
        rng = np.random.RandomState(seed)
        chunk_size = max(100, int(len(flat) * intensity * 0.1))
        num_chunks = max(1, int(intensity * 40))
        for _ in range(num_chunks):
            start = rng.randint(0, max(1, len(flat) - chunk_size))
            flat[start:start + chunk_size] = flat[start:start + chunk_size][::-1]

    elif effect == "feedback":
        # Multiple echo taps feeding into each other — catastrophic accumulation
        rng = np.random.RandomState(seed)
        num_taps = max(3, int(intensity * 8))
        for _ in range(num_taps):
            delay = rng.randint(100, max(101, int(len(flat) * 0.1)))
            gain = 0.3 + intensity * 0.6
            echo = np.zeros_like(flat)
            echo[delay:] = flat[:-delay] * gain
            flat = flat + echo

    # Reshape back to frame
    result = np.clip(flat * 255.0, 0, 255).astype(np.uint8)
    return result.reshape(frame.shape)


# ============================================================================
# 8. FLOW DISTORT — Motion-based warping (optical flow as displacement map)
# ============================================================================

def flow_distort(
    frame: np.ndarray,
    strength: float = 3.0,
    direction: str = "forward",
    frame_index: int = 0,
    total_frames: int = 1,
    seed: int = 42,
) -> np.ndarray:
    """Warp frame using optical flow as displacement map.

    Unlike datamosh (which accumulates), this applies single-frame flow
    as a displacement effect. Areas of high motion get distorted.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        strength: Displacement multiplier (0.5-50.0).
        direction: 'forward' (push) or 'backward' (pull).
        seed: Random seed for state keying.

    Returns:
        Flow-distorted frame.
    """
    import cv2

    state_key = f"flow_distort_{seed}"
    h, w = frame.shape[:2]
    strength = max(0.5, min(50.0, float(strength)))

    st = _get_destruction_state(state_key, lambda: {"prev": None})

    if frame_index == 0 or st["prev"] is None or st["prev"].shape != frame.shape:
        st["prev"] = frame.copy()
        _cleanup_destruction_if_done(state_key, frame_index, total_frames)
        return frame.copy()

    prev_gray = cv2.cvtColor(st["prev"], cv2.COLOR_RGB2GRAY)
    curr_gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

    flow = cv2.calcOpticalFlowFarneback(
        prev_gray, curr_gray, None,
        pyr_scale=0.5, levels=3, winsize=15,
        iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
    )

    sign = 1.0 if direction == "forward" else -1.0
    map_y, map_x = np.mgrid[0:h, 0:w].astype(np.float32)
    map_x += flow[:, :, 0] * strength * sign
    map_y += flow[:, :, 1] * strength * sign

    result = cv2.remap(
        frame, map_x, map_y,
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_WRAP,
    )

    st["prev"] = frame.copy()
    _cleanup_destruction_if_done(state_key, frame_index, total_frames)
    return result


# ============================================================================
# 9. GRAIN — Film grain / sensor noise (not Gaussian — actual grain texture)
# ============================================================================

def film_grain(
    frame: np.ndarray,
    intensity: float = 0.4,
    grain_size: int = 2,
    seed: int = 42,
    animate: bool = True,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Realistic film grain — not uniform noise, actual grain texture.

    Creates grain that responds to image brightness (more grain in midtones,
    less in deep shadows and bright highlights, like real film stock).

    Args:
        frame: (H, W, 3) uint8 RGB array.
        intensity: Grain strength (0.0-2.0). Above 1.0 = extreme grain.
        grain_size: Grain particle size in pixels (1-8).
        seed: Random seed (base seed when animate=False).
        animate: If True, grain moves frame-to-frame (default True for realism).

    Returns:
        Grainy frame.
    """
    intensity = max(0.0, min(2.0, float(intensity)))
    grain_size = max(1, min(8, int(grain_size)))
    effective_seed = seed + frame_index if animate else seed
    rng = np.random.RandomState(effective_seed)

    h, w = frame.shape[:2]
    f = frame.astype(np.float32)

    gh, gw = max(1, h // grain_size), max(1, w // grain_size)
    grain = rng.normal(0, 1, (gh, gw)).astype(np.float32)

    if grain_size > 1:
        grain = np.repeat(np.repeat(grain, grain_size, axis=0), grain_size, axis=1)
        grain = grain[:h, :w]

    luminance = np.mean(f, axis=2) / 255.0
    midtone_mask = 1.0 - 4.0 * (luminance - 0.5) ** 2
    midtone_mask = np.clip(midtone_mask, 0.2, 1.0)

    grain_scaled = grain * intensity * 120.0 * midtone_mask
    for c in range(3):
        f[:, :, c] += grain_scaled

    return np.clip(f, 0, 255).astype(np.uint8)


# ============================================================================
# 10. GLITCH REPEAT — Repeat random horizontal slices (data buffer overflow)
# ============================================================================

def glitch_repeat(
    frame: np.ndarray,
    num_slices: int = 8,
    max_height: int = 20,
    shift: bool = True,
    flicker: bool = False,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Repeat random horizontal slices and optionally shift them.

    Creates the "buffer overflow" glitch look where random horizontal bands
    get duplicated and smeared across the image.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        num_slices: Number of slices to repeat (1-60).
        max_height: Maximum height of each slice (3-200).
        shift: Also horizontally shift repeated slices.
        flicker: If True, alternates between glitched and clean frames.
        seed: Random seed.

    Returns:
        Glitch-repeated frame.
    """
    # Flicker mode: every other frame is clean
    if flicker and frame_index % 2 == 0:
        return frame.copy()

    num_slices = max(1, min(60, int(num_slices)))
    max_height = max(3, min(200, int(max_height)))
    rng = np.random.RandomState(seed + frame_index)

    h, w = frame.shape[:2]
    result = frame.copy()

    for _ in range(num_slices):
        slice_h = rng.randint(3, max(4, max_height + 1))
        src_y = rng.randint(0, max(1, h - slice_h))
        source_slice = frame[src_y:src_y + slice_h].copy()

        dst_y = rng.randint(0, max(1, h - slice_h))

        if shift:
            shift_px = rng.randint(-w // 2, w // 2)
            source_slice = np.roll(source_slice, shift_px, axis=1)

        result[dst_y:dst_y + slice_h] = source_slice

    return result


# ============================================================================
# 11. XOR GLITCH — Bitwise XOR corruption
# ============================================================================

def xor_glitch(
    frame: np.ndarray,
    pattern: int = 128,
    mode: str = "fixed",
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Bitwise XOR pixels with a pattern — digital-only aesthetic.

    Modes:
        fixed: XOR all pixels with a single byte value.
        random: XOR with random bytes per pixel (noise).
        gradient: XOR with a horizontal gradient (column index as byte).
        shift_self: XOR frame with horizontally shifted copy of itself.
        invert_self: XOR frame with its own inversion.
        prev_frame: XOR with previous frame (temporal glitch).

    Args:
        frame: (H, W, 3) uint8 RGB array.
        pattern: XOR byte value for fixed mode (0-255). For shift_self, shift amount (pixels).
        mode: 'fixed', 'random', 'gradient', 'shift_self', 'invert_self', or 'prev_frame'.
        seed: Random seed for random mode.
        frame_index: Current frame number for prev_frame mode.
        total_frames: Total frames for prev_frame mode.

    Returns:
        XOR-glitched frame.
    """
    pattern = max(0, min(255, int(pattern)))

    if mode == "random":
        rng = np.random.RandomState(seed)
        mask = rng.randint(0, 256, frame.shape, dtype=np.uint8)
        return np.bitwise_xor(frame, mask)
    elif mode == "gradient":
        h, w = frame.shape[:2]
        gradient = np.tile(np.arange(w, dtype=np.uint8), (h, 1))
        gradient = np.stack([gradient] * 3, axis=2)
        return np.bitwise_xor(frame, gradient)
    elif mode == "shift_self":
        # XOR with shifted copy — creates interference patterns
        shift = max(1, min(frame.shape[1] // 2, pattern))
        shifted = np.roll(frame, shift, axis=1)
        return np.bitwise_xor(frame, shifted)
    elif mode == "invert_self":
        # XOR with inverted self — produces specific color artifacts
        inverted = 255 - frame
        return np.bitwise_xor(frame, inverted)
    elif mode == "prev_frame":
        # XOR with previous frame — temporal glitch (requires state)
        state_key = f"xor_prev_{seed}"
        st = _get_destruction_state(state_key, lambda: {"prev": None})
        if frame_index == 0 or st["prev"] is None or st["prev"].shape != frame.shape:
            st["prev"] = frame.copy()
            _cleanup_destruction_if_done(state_key, frame_index, total_frames)
            return frame.copy()
        result = np.bitwise_xor(frame, st["prev"])
        st["prev"] = frame.copy()
        _cleanup_destruction_if_done(state_key, frame_index, total_frames)
        return result
    else:  # fixed
        return np.bitwise_xor(frame, np.uint8(pattern))


# ============================================================================
# 12. PIXEL ANNIHILATE — Destroy pixels based on various criteria
# ============================================================================

def pixel_annihilate(
    frame: np.ndarray,
    threshold: float = 0.5,
    mode: str = "dissolve",
    replacement: str = "black",
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Kill pixels. Dissolve them. Replace them with noise. Erase the image.

    Modes:
        dissolve: Random pixels are killed (transparency sim, replaced).
        threshold: Kill pixels above/below brightness threshold.
        edge_kill: Kill all edge pixels (remove structure, leave flat).
        channel_rip: Kill one random channel per pixel block.

    Replacements:
        black: Dead pixels go black.
        white: Dead pixels go white.
        noise: Dead pixels become random noise.
        invert: Dead pixels become their inverse.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        threshold: Kill probability or brightness cutoff (0.0-1.0).
        mode: Kill mode.
        replacement: What replaces dead pixels.
        seed: Random seed.

    Returns:
        Annihilated frame.
    """
    threshold = max(0.0, min(1.0, float(threshold)))
    rng = np.random.RandomState(seed + frame_index)

    h, w = frame.shape[:2]
    result = frame.copy()

    if mode == "dissolve":
        # Random pixel death
        kill_mask = rng.random((h, w)) < threshold
    elif mode == "threshold":
        # Kill by brightness
        gray = np.mean(frame.astype(np.float32), axis=2) / 255.0
        kill_mask = gray > threshold
    elif mode == "edge_kill":
        # Kill edge pixels — destroy structure
        gray = np.mean(frame.astype(np.float32), axis=2)
        gx = np.zeros_like(gray)
        gy = np.zeros_like(gray)
        gx[:, 1:-1] = np.abs(gray[:, 2:] - gray[:, :-2])
        gy[1:-1, :] = np.abs(gray[2:, :] - gray[:-2, :])
        edges = np.sqrt(gx**2 + gy**2)
        if edges.max() > 0:
            edges = edges / edges.max()
        kill_mask = edges > (1.0 - threshold)
    elif mode == "channel_rip":
        # Kill one channel per block region
        block = max(4, int(32 * (1.0 - threshold)))
        for by in range(0, h, block):
            for bx in range(0, w, block):
                ch = rng.randint(0, 3)
                bh = min(block, h - by)
                bw = min(block, w - bx)
                result[by:by+bh, bx:bx+bw, ch] = 0
        return result
    else:
        kill_mask = rng.random((h, w)) < threshold

    # Apply replacement
    kill_3d = kill_mask[:, :, np.newaxis]
    if replacement == "white":
        fill = np.full_like(frame, 255)
    elif replacement == "noise":
        fill = rng.randint(0, 256, frame.shape, dtype=np.uint8)
    elif replacement == "invert":
        fill = 255 - frame
    else:  # black
        fill = np.zeros_like(frame)

    result = np.where(kill_3d, fill, frame)
    return result


# ============================================================================
# 13. FRAME SMASH — Combine multiple corruptions in one pass
# ============================================================================

def frame_smash(
    frame: np.ndarray,
    aggression: float = 0.5,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Apply multiple destruction techniques simultaneously. One-stop apocalypse.

    This is NOT a chain — it applies everything in parallel and composites.
    Higher aggression = more techniques stacked, higher intensity each.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        aggression: How much destruction (0.0 = mild, 1.0 = total apocalypse).
        seed: Random seed.

    Returns:
        Smashed frame.
    """
    aggression = max(0.0, min(1.0, float(aggression)))
    rng = np.random.RandomState(seed + frame_index)

    h, w = frame.shape[:2]
    result = frame.astype(np.float32)

    # 1. Row displacement (always)
    if aggression > 0.1:
        density = aggression * 0.8
        max_shift = int(w * aggression * 0.5)
        for y in range(h):
            if rng.random() < density:
                shift = rng.randint(-max_shift, max(1, max_shift + 1))
                result[y] = np.roll(result[y], shift, axis=0)

    # 2. Block corruption
    if aggression > 0.2:
        num = int(aggression * 60)
        bs = max(8, int(64 * (1.0 - aggression * 0.5)))
        for _ in range(num):
            by = rng.randint(0, max(1, h - bs))
            bx = rng.randint(0, max(1, w - bs))
            bh = min(bs, h - by)
            bw = min(bs, w - bx)
            action = rng.randint(0, 4)
            if action == 0:
                # Random source block
                sy = rng.randint(0, max(1, h - bh))
                sx = rng.randint(0, max(1, w - bw))
                result[by:by+bh, bx:bx+bw] = result[sy:sy+bh, sx:sx+bw]
            elif action == 1:
                result[by:by+bh, bx:bx+bw] = rng.uniform(0, 255, (bh, bw, 3))
            elif action == 2:
                result[by:by+bh, bx:bx+bw] = 255 - result[by:by+bh, bx:bx+bw]
            else:
                result[by:by+bh, bx:bx+bw] = 0

    # 3. Channel separation
    if aggression > 0.3:
        ch_shift = int(w * aggression * 0.15)
        r = np.roll(result[:, :, 0], ch_shift, axis=1)
        b = np.roll(result[:, :, 2], -ch_shift, axis=1)
        g = np.roll(result[:, :, 1], int(ch_shift * 0.5), axis=0)
        result = np.stack([r, g, b], axis=2)

    # 4. Data bend (echo on raw pixels)
    if aggression > 0.5:
        flat = result.flatten()
        delay = int(w * 3 * aggression * 5)
        delay = max(1, min(len(flat) // 2, delay))
        echo = np.zeros_like(flat)
        echo[delay:] = flat[:-delay] * aggression * 0.5
        flat = flat + echo
        result = flat.reshape(result.shape)

    # 5. XOR corruption
    if aggression > 0.7:
        xor_val = rng.randint(64, 255)
        mask = rng.random((h, w)) < aggression * 0.4
        for c in range(3):
            result[:, :, c] = np.where(
                mask, np.bitwise_xor(np.clip(result[:, :, c], 0, 255).astype(np.uint8), xor_val),
                result[:, :, c]
            )

    # 6. Pixel dissolution
    if aggression > 0.8:
        dissolve = rng.random((h, w)) < (aggression - 0.8) * 3
        result[dissolve] = rng.uniform(0, 255, (np.sum(dissolve), 3))

    return np.clip(result, 0, 255).astype(np.uint8)


# ============================================================================
# 14. CHANNEL DESTROY — Rip color channels apart
# ============================================================================

def channel_destroy(
    frame: np.ndarray,
    mode: str = "separate",
    intensity: float = 0.5,
    seed: int = 42,
    frame_index: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """Violently separate, swap, crush, or eliminate color channels.

    Modes:
        separate: Offset each channel by huge amounts in different directions.
        swap: Randomly reassign channels to wrong channels.
        crush: Reduce one or more channels to 1-bit.
        eliminate: Kill one or more channels entirely.
        invert: Invert one or more channels.
        xor_channels: XOR channels against each other.

    Args:
        frame: (H, W, 3) uint8 RGB array.
        mode: Destruction mode.
        intensity: How extreme (0.0-1.0).
        seed: Random seed.

    Returns:
        Channel-destroyed frame.
    """
    intensity = max(0.0, min(1.0, float(intensity)))
    rng = np.random.RandomState(seed + frame_index)

    h, w = frame.shape[:2]
    result = frame.copy()

    if mode == "separate":
        # Massive channel offsets
        shift_x = int(w * intensity * 0.3)
        shift_y = int(h * intensity * 0.3)
        result[:, :, 0] = np.roll(np.roll(frame[:, :, 0], shift_x, axis=1), shift_y, axis=0)
        result[:, :, 1] = np.roll(np.roll(frame[:, :, 1], -shift_x, axis=1), -shift_y // 2, axis=0)
        result[:, :, 2] = np.roll(np.roll(frame[:, :, 2], shift_x // 2, axis=1), -shift_y, axis=0)

    elif mode == "swap":
        channels = [0, 1, 2]
        rng.shuffle(channels)
        result[:, :, 0] = frame[:, :, channels[0]]
        result[:, :, 1] = frame[:, :, channels[1]]
        result[:, :, 2] = frame[:, :, channels[2]]
        # At high intensity, also offset after swap
        if intensity > 0.5:
            shift = int(w * (intensity - 0.5) * 0.4)
            result[:, :, 0] = np.roll(result[:, :, 0], shift, axis=1)

    elif mode == "crush":
        # Reduce channels to 1-bit (black or white per channel)
        num_crush = max(1, int(intensity * 3))
        for _ in range(num_crush):
            ch = rng.randint(0, 3)
            threshold = rng.randint(64, 192)
            result[:, :, ch] = np.where(result[:, :, ch] > threshold, 255, 0).astype(np.uint8)

    elif mode == "eliminate":
        # Kill channels (set to zero)
        num_kill = max(1, min(2, int(intensity * 2.5)))
        channels = list(range(3))
        rng.shuffle(channels)
        for i in range(num_kill):
            result[:, :, channels[i]] = 0

    elif mode == "invert":
        # Invert one or more channels
        num_invert = max(1, min(3, int(intensity * 3)))
        channels = list(range(3))
        rng.shuffle(channels)
        for i in range(num_invert):
            result[:, :, channels[i]] = 255 - result[:, :, channels[i]]

    elif mode == "xor_channels":
        # XOR channels against each other
        result[:, :, 0] = np.bitwise_xor(frame[:, :, 0], frame[:, :, 1])
        result[:, :, 1] = np.bitwise_xor(frame[:, :, 1], frame[:, :, 2])
        result[:, :, 2] = np.bitwise_xor(frame[:, :, 2], frame[:, :, 0])
        if intensity > 0.5:
            # Double XOR for more chaos
            result[:, :, 0] = np.bitwise_xor(result[:, :, 0], frame[:, :, 2])

    return result

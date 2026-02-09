"""
Entropic — Safety & Resource Guards
Centralized preflight checks run before any file processing.
Prevents runaway disk usage, path traversal, and resource exhaustion.
"""

import os
import signal
from pathlib import Path

# --- Configurable Limits ---
MAX_FILE_MB = 500          # Maximum input file size
TIMEOUT_SEC = 300          # 5 minute processing timeout
MIN_DISK_GB = 1.0          # Minimum free disk space
MAX_CHAIN_DEPTH = 10       # Maximum effects in a chain
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".gif", ".png", ".jpg", ".jpeg"}


class SafetyError(Exception):
    """Raised when a preflight check fails."""
    pass


def preflight(input_path: str, output_dir: str | None = None) -> dict:
    """Run all safety checks before processing a file.

    Args:
        input_path: Path to the input file.
        output_dir: Directory where output will be written (optional).

    Returns:
        dict with file metadata (size_mb, extension, etc.)

    Raises:
        SafetyError: If any check fails.
        FileNotFoundError: If input doesn't exist.
    """
    input_path = str(input_path)
    real_path = os.path.realpath(input_path)

    # 1. File exists
    if not os.path.isfile(real_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # 2. Path traversal check — must be under home directory
    home = os.path.expanduser("~")
    if not real_path.startswith(home):
        raise SafetyError(
            f"Path outside home directory: {real_path}. "
            f"Entropic only processes files under {home}"
        )

    # 3. File size check
    size_bytes = os.path.getsize(real_path)
    size_mb = size_bytes / (1024 * 1024)
    if size_mb > MAX_FILE_MB:
        raise SafetyError(
            f"Input file is {size_mb:.0f}MB, exceeds {MAX_FILE_MB}MB limit. "
            f"Use a shorter clip or lower resolution."
        )

    # 4. File extension check
    ext = Path(real_path).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise SafetyError(
            f"File type '{ext}' not allowed. "
            f"Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # 5. Disk space check (if output dir specified)
    if output_dir:
        output_dir = str(output_dir)
        check_dir = output_dir if os.path.isdir(output_dir) else os.path.dirname(output_dir) or "."
        try:
            stat = os.statvfs(check_dir)
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
            if free_gb < MIN_DISK_GB:
                raise SafetyError(
                    f"Only {free_gb:.1f}GB free disk space, need {MIN_DISK_GB}GB minimum."
                )
        except OSError:
            pass  # Can't check disk space — proceed with caution

    return {
        "path": real_path,
        "size_mb": size_mb,
        "extension": ext,
    }


def validate_chain_depth(effects_list: list) -> None:
    """Check that effect chain isn't too deep.

    Raises:
        SafetyError: If chain exceeds MAX_CHAIN_DEPTH.
    """
    if len(effects_list) > MAX_CHAIN_DEPTH:
        raise SafetyError(
            f"Effect chain has {len(effects_list)} effects, max is {MAX_CHAIN_DEPTH}. "
            f"Split into multiple passes."
        )


def validate_region(region_spec, frame_width: int = None, frame_height: int = None) -> None:
    """Validate a region specification without applying it.

    Raises:
        SafetyError: If the spec is malformed or clearly invalid.
    """
    if region_spec is None:
        return

    from core.region import RegionError

    # String validation
    if isinstance(region_spec, str):
        # Check length
        if len(region_spec) > 200:
            raise SafetyError(f"Region string too long ({len(region_spec)} chars, max 200)")
        # Preset names are always valid
        from core.region import REGION_PRESETS
        if region_spec in REGION_PRESETS:
            return
        # Must be x,y,w,h format
        parts = region_spec.replace(" ", "").split(",")
        if len(parts) != 4:
            raise SafetyError(
                f"Region must be 'x,y,w,h' or a preset. Got: '{region_spec}'. "
                f"Presets: {', '.join(sorted(REGION_PRESETS.keys()))}"
            )
        for p in parts:
            try:
                v = float(p)
                if v != v or v == float('inf') or v == float('-inf'):
                    raise SafetyError(f"NaN/Inf not allowed in region: {region_spec}")
            except ValueError:
                raise SafetyError(f"Non-numeric value in region: '{p}'")

    elif isinstance(region_spec, dict):
        for key in ("x", "y", "w", "h"):
            if key in region_spec:
                try:
                    float(region_spec[key])
                except (TypeError, ValueError):
                    raise SafetyError(f"Invalid region value for '{key}': {region_spec[key]}")

    elif isinstance(region_spec, (tuple, list)):
        if len(region_spec) != 4:
            raise SafetyError(f"Region must have 4 values (x,y,w,h). Got {len(region_spec)}")

    # If we have frame dimensions, do a full parse test
    if frame_width and frame_height:
        try:
            from core.region import parse_region
            parse_region(region_spec, frame_height, frame_width)
        except RegionError as e:
            raise SafetyError(str(e))


def set_processing_timeout(seconds: int = TIMEOUT_SEC) -> None:
    """Set an alarm-based timeout for processing. Unix only.

    Call this before starting a long operation.
    The alarm will raise TimeoutError if processing exceeds the limit.
    """
    if not hasattr(signal, "SIGALRM"):
        return  # Windows — no SIGALRM support

    def _timeout_handler(signum, frame):
        raise TimeoutError(
            f"Processing exceeded {seconds}s timeout. "
            f"Try a shorter clip or simpler effect chain."
        )

    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(seconds)


def clear_processing_timeout() -> None:
    """Clear a previously set processing timeout."""
    if hasattr(signal, "SIGALRM"):
        signal.alarm(0)

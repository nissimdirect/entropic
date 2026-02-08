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

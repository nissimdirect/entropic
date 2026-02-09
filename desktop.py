#!/usr/bin/env python3
"""
Entropic — Native Desktop App (PyWebView)
No browser. No Terminal. No URL bar.

Usage:
    python3 desktop.py
"""

import sys
import os
import shutil
import signal
import threading
import atexit
import subprocess

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# --- Configuration ---
APP_TITLE = "ENTROPIC"
DEFAULT_PORT = 7860
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
MIN_WIDTH = 1000
MIN_HEIGHT = 700
BG_VOID = "#050506"


def check_ffmpeg():
    """Check if FFmpeg is installed. Returns True if found."""
    return shutil.which("ffmpeg") is not None


def show_ffmpeg_dialog():
    """Show a native macOS dialog about missing FFmpeg."""
    try:
        # Use osascript for a native dialog — no tkinter dependency
        script = '''
        display dialog "Entropic needs FFmpeg for video processing.\\n\\nInstall with Homebrew:\\n    brew install ffmpeg\\n\\nOr download from ffmpeg.org" ¬
            buttons {"I'll install later", "Open Terminal"} ¬
            default button "Open Terminal" ¬
            with title "FFmpeg Required" ¬
            with icon caution
        '''
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=30
        )
        if "Open Terminal" in result.stdout:
            subprocess.Popen([
                "osascript", "-e",
                'tell application "Terminal" to do script "brew install ffmpeg"'
            ])
    except Exception:
        pass  # Dialog failed — app still opens, export just won't work


def find_free_port(start=DEFAULT_PORT):
    """Find a free port starting from start."""
    import socket
    for port in range(start, start + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    return start  # Fall back


def start_server(port, ready_event):
    """Start the FastAPI server in a background thread."""
    import uvicorn
    from server import app

    # Signal that server is ready once uvicorn starts
    class ReadyServer(uvicorn.Server):
        def startup(self, sockets=None):
            result = super().startup(sockets)
            ready_event.set()
            return result

    config = uvicorn.Config(
        app, host="127.0.0.1", port=port,
        log_level="warning", access_log=False,
    )
    server_instance = ReadyServer(config)
    server_instance.run()


# Track server thread and child processes for cleanup
_server_thread = None
_server_port = None


def cleanup():
    """Kill server thread and any orphan FFmpeg processes."""
    # Kill any FFmpeg child processes we spawned
    try:
        # Find ffmpeg processes that are children of this process
        pid = os.getpid()
        result = subprocess.run(
            ["pgrep", "-P", str(pid), "ffmpeg"],
            capture_output=True, text=True, timeout=3
        )
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                try:
                    os.kill(int(line.strip()), signal.SIGTERM)
                except (ProcessLookupError, ValueError):
                    pass
    except Exception:
        pass


atexit.register(cleanup)


def main():
    global _server_thread, _server_port

    # 1. Check FFmpeg (non-blocking — app opens regardless)
    has_ffmpeg = check_ffmpeg()
    if not has_ffmpeg:
        show_ffmpeg_dialog()

    # 2. Find a free port
    _server_port = find_free_port()

    # 3. Start server in background thread
    ready_event = threading.Event()
    _server_thread = threading.Thread(
        target=start_server,
        args=(_server_port, ready_event),
        daemon=True,
    )
    _server_thread.start()

    # 4. Wait for server to be ready (max 10 seconds)
    ready_event.wait(timeout=10)

    # 5. Launch PyWebView window
    import webview

    url = f"http://127.0.0.1:{_server_port}"

    # Expose Python functions to JavaScript via pywebview JS API
    def reveal_in_finder(path):
        """Open Finder and highlight the file."""
        if path and os.path.exists(path):
            subprocess.run(["open", "-R", path])

    window = webview.create_window(
        APP_TITLE,
        url=url,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        min_size=(MIN_WIDTH, MIN_HEIGHT),
        background_color=BG_VOID,
        text_select=False,
        js_api=None,
    )

    window.expose(reveal_in_finder)

    # Start the webview event loop (blocks until window closes)
    webview.start(debug=False)

    # Window closed — clean up
    cleanup()
    os._exit(0)  # Force exit to kill server thread


if __name__ == "__main__":
    main()

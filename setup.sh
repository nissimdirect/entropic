#!/bin/bash
# Entropic — Setup Script for New Machine
# Run this on ANY macOS computer to get Entropic running.
# Usage: bash setup.sh

set -e

echo "=== Entropic Setup ==="
echo ""

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Install from python.org or: brew install python3"
    exit 1
fi

# Check FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "ERROR: FFmpeg not found. Install with: brew install ffmpeg"
    exit 1
fi

PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
FFMPEG_VER=$(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')
echo "Python: $PYTHON_VER"
echo "FFmpeg: $FFMPEG_VER"

# Create venv
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Verify imports
echo "Verifying imports..."
python3 -c "
import numpy
import PIL
import cv2
print('All dependencies OK')
"

# Create desktop launcher
echo "Creating desktop launcher..."
APP_DIR="$HOME/Desktop/Entropic.app"
mkdir -p "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Resources"

cat > "$APP_DIR/Contents/MacOS/launch" << 'LAUNCHER'
#!/bin/bash
PROJECT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$PROJECT_DIR"
if [ -f "$PROJECT_DIR/venv/bin/python3" ]; then
    exec "$PROJECT_DIR/venv/bin/python3" "$PROJECT_DIR/server.py" "$@"
else
    exec python3 "$PROJECT_DIR/server.py" "$@"
fi
LAUNCHER
chmod +x "$APP_DIR/Contents/MacOS/launch"

cat > "$APP_DIR/Contents/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleExecutable</key>
	<string>launch</string>
	<key>CFBundleIdentifier</key>
	<string>com.popchaoslabs.entropic</string>
	<key>CFBundleName</key>
	<string>Entropic</string>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
</dict>
</plist>
PLIST

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To run:"
echo "  Double-click 'Entropic' on your Desktop (opens web UI)"
echo "  OR: source venv/bin/activate && python3 entropic.py --help"
echo ""
echo "CLI examples:"
echo "  python3 entropic.py list-effects"
echo "  python3 entropic.py clip video.mp4 --start 10 --duration 5"
echo "  python3 entropic.py new myproject --source video.mp4"

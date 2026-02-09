"""
Entropic — DMG Build Settings
Build with: dmgbuild -s dmg_settings.py "Entropic" Entropic.dmg
Install: pip install dmgbuild
"""

import os

# Application name
application = defines.get('app', 'dist/Entropic.app')
appname = os.path.basename(application)

# Volume name
volume_name = "Entropic"

# DMG format (UDBZ = bzip2 compressed)
format = defines.get('format', 'UDBZ')

# DMG size (auto-calculated, but set minimum)
size = None

# Files to include
files = [application]
symlinks = {'Applications': '/Applications'}

# Window appearance
background_color = '#050506'
window_rect = ((200, 120), (660, 400))
icon_size = 80
icon_locations = {
    appname: (140, 160),
    'Applications': (500, 160),
}

# Text size
text_size = 12

# PyInstaller hook for opencv-python-headless
# Collect all cv2 submodules, data files (config.py etc), and dynamic libs
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs

hiddenimports = collect_submodules('cv2')
datas = collect_data_files('cv2', include_py_files=True)
binaries = collect_dynamic_libs('cv2')

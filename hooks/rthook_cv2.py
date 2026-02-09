# Runtime hook: Fix cv2 bootstrap recursion in PyInstaller
# Problem: cv2/__init__.py's bootstrap() does importlib.import_module("cv2")
# which re-enters __init__.py in frozen builds instead of loading cv2.abi3.so.
# Fix: Monkey-patch importlib.import_module to handle this specific case.
import sys
import os

if getattr(sys, 'frozen', False):
    import importlib
    _original_import_module = importlib.import_module

    def _patched_import_module(name, package=None):
        # When cv2 bootstrap pops itself from sys.modules and re-imports "cv2",
        # intercept and load the native binary extension directly
        if name == 'cv2' and hasattr(sys, 'OpenCV_LOADER'):
            base_dir = sys._MEIPASS
            cv2_dir = os.path.join(base_dir, 'cv2')
            # Find the native .so file
            for f in os.listdir(cv2_dir):
                if f.startswith('cv2') and f.endswith('.so'):
                    spec = importlib.util.spec_from_file_location(
                        'cv2', os.path.join(cv2_dir, f),
                        submodule_search_locations=[]
                    )
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        return mod
        return _original_import_module(name, package)

    importlib.import_module = _patched_import_module

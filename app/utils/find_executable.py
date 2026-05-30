import os
import shutil
from typing import Optional

def find_executable(app_name: str, custom_paths: Optional[list] = None) -> Optional[str]:
    """
    Attempts to find the full path to an executable in a safe, cross-platform way.
    - Checks custom_paths first (if provided)
    - Checks system PATH
    - Checks common install locations for Windows
    Returns the full path if found, else None.
    """
    # 1. Check custom paths
    if custom_paths:
        for path in custom_paths:
            exe_path = os.path.expandvars(os.path.expanduser(path))
            if os.path.isfile(exe_path):
                return exe_path

    # 2. Use shutil.which (searches PATH)
    exe_path = shutil.which(app_name)
    if exe_path:
        return exe_path

    # 3. Check common Windows locations
    if os.name == "nt":
        common_dirs = [
            os.path.join(os.environ.get("ProgramFiles", r"C:\\Program Files"), app_name + ".exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\\Program Files (x86)"), app_name + ".exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", r"C:\\Users\\%USERNAME%\\AppData\\Local"), app_name, app_name + ".exe"),
        ]
        for exe_path in common_dirs:
            exe_path = os.path.expandvars(exe_path)
            if os.path.isfile(exe_path):
                return exe_path

    return None

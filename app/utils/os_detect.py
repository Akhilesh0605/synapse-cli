import platform
from typing import Literal

OsContext = Literal["windows", "linux", "macos"]


def detect_os_context() -> OsContext:
    system = platform.system().lower()

    if system == "windows":
        return "windows"
    elif system == "darwin":
        return "macos"
    elif system == "linux":
        return "linux"
    else:
        return "linux"  # safe default
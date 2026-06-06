import ctypes
import time
from dataclasses import dataclass


VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
KEYEVENTF_KEYUP = 0x0002


@dataclass(frozen=True)
class VolumeActionResult:
    success: bool
    message: str


def _press_key(virtual_key_code: int) -> None:
    ctypes.windll.user32.keybd_event(virtual_key_code, 0, 0, 0)
    ctypes.windll.user32.keybd_event(virtual_key_code, 0, KEYEVENTF_KEYUP, 0)


def apply_windows_volume_intent(intent_name: str, percent: int) -> VolumeActionResult:
    intent_name = intent_name.lower()

    if intent_name == "mute_volume":
        _press_key(VK_VOLUME_MUTE)
        return VolumeActionResult(success=True, message="Muted system volume.")

    steps = max(1, abs(int(percent)))
    virtual_key_code = VK_VOLUME_UP if intent_name == "increase_volume" else VK_VOLUME_DOWN

    for _ in range(steps):
        _press_key(virtual_key_code)
        time.sleep(0.02)

    direction = "increased" if virtual_key_code == VK_VOLUME_UP else "decreased"
    return VolumeActionResult(
        success=True,
        message=f"{direction.capitalize()} system volume by {steps}% using media keys.",
    )
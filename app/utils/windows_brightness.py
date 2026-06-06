import subprocess
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class BrightnessActionResult:
    success: bool
    message: str


def _build_powershell_script(target_brightness: int) -> str:
    return f"""
$current = (Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness | Select-Object -First 1 -ExpandProperty CurrentBrightness)
if ($null -eq $current) {{ throw 'Could not read current brightness.' }}
$target = [Math]::Max(0, [Math]::Min(100, [int]{target_brightness}))
$methods = Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods | Select-Object -First 1
if ($null -eq $methods) {{ throw 'Brightness control not supported on this device.' }}
$methods | Invoke-CimMethod -MethodName WmiSetBrightness -Arguments @{{ Timeout = 1; Brightness = $target }} | Out-Null
"""


def apply_windows_brightness_intent(intent_name: str, level: int) -> BrightnessActionResult:
    intent_name = intent_name.lower()
    level = max(1, abs(int(level)))

    current_result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness | Select-Object -First 1 -ExpandProperty CurrentBrightness)",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        encoding="utf-8",
        errors="replace",
    )

    if current_result.returncode != 0:
        return BrightnessActionResult(
            success=False,
            message=(current_result.stderr.strip() or "Could not read current brightness."),
        )

    try:
        current_brightness = int(current_result.stdout.strip())
    except ValueError:
        return BrightnessActionResult(
            success=False,
            message="Could not parse current brightness.",
        )

    if intent_name in {"decrease_screen_brightness", "lower_screen_brightness"}:
        target_brightness = current_brightness - level
    elif intent_name in {"set_screen_brightness", "adjust_screen_brightness"}:
        target_brightness = level
    else:
        target_brightness = current_brightness + level

    target_brightness = max(0, min(100, target_brightness))
    script = _build_powershell_script(target_brightness)

    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        timeout=15,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        return BrightnessActionResult(
            success=False,
            message=(result.stderr.strip() or result.stdout.strip() or "Brightness adjustment failed."),
        )

    direction = "increased" if target_brightness >= current_brightness else "decreased"
    time.sleep(0.02)
    return BrightnessActionResult(
        success=True,
        message=f"{direction.capitalize()} screen brightness to {target_brightness}%.",
    )
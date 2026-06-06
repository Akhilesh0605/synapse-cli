from app.schemas.command_schema import ShellCommandSchema
from app.schemas.intent_schema import IntentSchema
from app.semantic.semantic_validator import SemanticValidator


def test_open_settings_accepts_start_alias():
    intent = IntentSchema(
        action_type="system_command",
        intent="open_settings",
        requires_shell=True,
        shell_type="powershell",
        parameters={},
        risk_level="LOW",
        confidence="HIGH",
        explanation="User wants to open Windows settings.",
    )

    command = ShellCommandSchema(
        shell_type="powershell",
        command="start ms-settings:",
        explanation="Opens Windows Settings from PowerShell.",
        expected_risk="LOW",
        requires_confirmation=False,
        requires_sudo=False,
        confidence="HIGH",
        retry_attempt=0,
        error_context=None,
    )

    result = SemanticValidator.validate(intent, command)

    assert result.safe is True
    assert result.base_command == "start-process"
    assert result.capability == "system.launch"


def test_increase_volume_accepts_volume_cmdlets():
    intent = IntentSchema(
        action_type="system_command",
        intent="increase_volume",
        requires_shell=True,
        shell_type="powershell",
        parameters={"percent": 3},
        risk_level="LOW",
        confidence="HIGH",
        explanation="User wants to increase audio volume.",
    )

    command = ShellCommandSchema(
        shell_type="powershell",
        command="Get-Volume | Set-Volume -Level (-3)",
        explanation="Adjusts volume by the requested amount.",
        expected_risk="LOW",
        requires_confirmation=False,
        requires_sudo=False,
        confidence="HIGH",
        retry_attempt=0,
        error_context=None,
    )

    result = SemanticValidator.validate(intent, command)

    assert result.safe is True
    assert result.base_command == "get-volume"
    assert result.capability == "system.media"


def test_increase_screen_brightness_accepts_powercfg():
    intent = IntentSchema(
        action_type="system_command",
        intent="increase_screen_brightness",
        requires_shell=True,
        shell_type="powershell",
        parameters={"level": 3},
        risk_level="LOW",
        confidence="HIGH",
        explanation="User wants to increase screen brightness.",
    )

    command = ShellCommandSchema(
        shell_type="powershell",
        command="powercfg -setdcvalueindex EXE 1C04F4A5-6EA2-4c9d-a8e7-Cb0f4A5B3D65 18 3",
        explanation="Adjusts screen brightness on battery power.",
        expected_risk="LOW",
        requires_confirmation=False,
        requires_sudo=False,
        confidence="HIGH",
        retry_attempt=0,
        error_context=None,
    )

    result = SemanticValidator.validate(intent, command)

    assert result.safe is True
    assert result.base_command == "powercfg"
    assert result.capability == "system.display"


def test_open_youtube_accepts_start_process_url():
    intent = IntentSchema(
        action_type="system_command",
        intent="open_youtube",
        requires_shell=True,
        shell_type="powershell",
        parameters={"url": "https://www.youtube.com"},
        risk_level="LOW",
        confidence="HIGH",
        explanation="User wants to open YouTube.",
    )

    command = ShellCommandSchema(
        shell_type="powershell",
        command="Start-Process 'https://www.youtube.com'",
        explanation="Opens YouTube in the default browser.",
        expected_risk="LOW",
        requires_confirmation=False,
        requires_sudo=False,
        confidence="HIGH",
        retry_attempt=0,
        error_context=None,
    )

    result = SemanticValidator.validate(intent, command)

    assert result.safe is True
    assert result.base_command == "start-process"
    assert result.capability == "system.launch"
# semantic_validator.py
from pathlib import Path

from app.semantic.intent_command_map import INTENT_ALLOWED_COMMANDS
from app.semantic.capability_map import COMMAND_CAPABILITIES
from app.semantic.semantic_result import SemanticValidationResult, SemanticViolation
from app.schemas.intent_schema import IntentSchema
from app.schemas.command_schema import ShellCommandSchema


class SemanticValidator:

    @classmethod
    def validate(
        cls,
        intent:  IntentSchema,
        command: ShellCommandSchema,
    ) -> SemanticValidationResult:

        violations   = []

        # ── Normalize base command ───────────────────────
        base_command = (
            Path(command.command.strip().split()[0])
            .stem
            .lower()
        )

        # ── Check 1: intent has a known mapping ──────────
        allowed_commands = INTENT_ALLOWED_COMMANDS.get(intent.intent)

        if allowed_commands is None:
            # unknown intent — no mapping exists at all
            violations.append(SemanticViolation(
                rule   = "UNKNOWN_INTENT_MAPPING",
                reason = (
                    f"Intent '{intent.intent}' has no entry in "
                    f"INTENT_ALLOWED_COMMANDS. Cannot verify command is appropriate."
                ),
            ))
        elif base_command not in allowed_commands:
            # intent known but command not in its allowed set
            violations.append(SemanticViolation(
                rule   = "INTENT_COMMAND_MISMATCH",
                reason = (
                    f"Intent '{intent.intent}' does not permit "
                    f"'{base_command}'. "
                    f"Allowed: {sorted(allowed_commands)}"
                ),
            ))

        # ── Check 2: command has a capability mapping ────
        capability = COMMAND_CAPABILITIES.get(base_command)

        if capability is None:
            violations.append(SemanticViolation(
                rule   = "UNKNOWN_COMMAND_CAPABILITY",
                reason = (
                    f"'{base_command}' has no capability mapping. "
                    f"Add it to COMMAND_CAPABILITIES before allowing execution."
                ),
            ))

        return SemanticValidationResult(
            safe         = len(violations) == 0,
            violations   = violations,
            base_command = base_command,
            capability   = capability,
        )
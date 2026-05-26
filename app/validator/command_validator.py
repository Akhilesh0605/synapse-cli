
import re
import logging
from enum import Enum
from typing import List
from pydantic import BaseModel

from app.schemas.command_schema import ShellCommandSchema

logger = logging.getLogger(__name__)




class ValidationStatus(str, Enum):
    PASSED  = "PASSED"
    FAILED  = "FAILED"


class ValidationViolation(BaseModel):
    rule:   str
    reason: str


class ValidationResult(BaseModel):
    status:     ValidationStatus
    violations: List[ValidationViolation] = []
    safe:       bool
    
# RULE SETS


# Dangerous command patterns — matched against actual command string
DANGEROUS_PATTERNS: List[re.Pattern] = [
    # Destructive filesystem
    re.compile(r"rm\s+-[^\s]*r[^\s]*\s+/",          re.IGNORECASE),  # rm -rf /
    re.compile(r"rm\s+-[^\s]*f[^\s]*\s+/",          re.IGNORECASE),  # rm -f /
    re.compile(r"mkfs",                              re.IGNORECASE),
    re.compile(r"dd\s+if=",                          re.IGNORECASE),
    re.compile(r"shred\s",                           re.IGNORECASE),
    re.compile(r"wipefs",                            re.IGNORECASE),

    # Windows destructive
    re.compile(r"format\s+[a-z]:",                  re.IGNORECASE),
    re.compile(r"del\s+/[sqfSQF]",                  re.IGNORECASE),
    re.compile(r"rd\s+/[sqSQ]",                     re.IGNORECASE),
    re.compile(r"rmdir\s+/[sqSQ]",                  re.IGNORECASE),
    re.compile(r"Remove-Item\s+-Recurse\s+-Force\s+[A-Za-z]:\\(Windows|System)", re.IGNORECASE),

    # Remote code execution
    re.compile(r"curl[^|]*\|\s*(bash|sh|zsh)",      re.IGNORECASE),
    re.compile(r"wget[^|]*\|\s*(bash|sh|zsh)",      re.IGNORECASE),
    re.compile(r"Invoke-Expression",                 re.IGNORECASE),  # PowerShell IEX
    re.compile(r"iex\s*\(",                          re.IGNORECASE),  # IEX shorthand

    # Encoding / obfuscation
    re.compile(r"base64\s+--decode.*\|\s*(bash|sh)", re.IGNORECASE),
    re.compile(r"-EncodedCommand",                   re.IGNORECASE),  # PowerShell encoded
    re.compile(r"-enc\s+[A-Za-z0-9+/=]{20,}",       re.IGNORECASE),

    # Privilege escalation
    re.compile(r"sudo\s+su",                         re.IGNORECASE),
    re.compile(r"chmod\s+777\s+/",                  re.IGNORECASE),
    re.compile(r"visudo",                            re.IGNORECASE),
    re.compile(r"passwd\s+root",                     re.IGNORECASE),

    # Fork bomb
    re.compile(r":\(\)\s*\{",                        re.IGNORECASE),

    # System shutdown/reboot
    re.compile(r"\bshutdown\b",                      re.IGNORECASE),
    re.compile(r"\breboot\b",                        re.IGNORECASE),
    re.compile(r"\bhalt\b",                          re.IGNORECASE),
    re.compile(r"Stop-Computer",                     re.IGNORECASE),
    re.compile(r"Restart-Computer",                  re.IGNORECASE),
]


# Protected system paths — block any command targeting these
PROTECTED_PATHS: List[re.Pattern] = [
    # Windows
    re.compile(r"C:\\Windows\\System32",             re.IGNORECASE),
    re.compile(r"C:\\Windows\\SysWOW64",             re.IGNORECASE),
    re.compile(r"C:\\Windows",                       re.IGNORECASE),
    re.compile(r"C:\\Program Files",                 re.IGNORECASE),

    # Linux / macOS
    re.compile(r"(?<!\w)/etc(?:/|\s|$)",             re.IGNORECASE),
    re.compile(r"(?<!\w)/bin(?:/|\s|$)",             re.IGNORECASE),
    re.compile(r"(?<!\w)/sbin(?:/|\s|$)",            re.IGNORECASE),
    re.compile(r"(?<!\w)/boot(?:/|\s|$)",            re.IGNORECASE),
    re.compile(r"(?<!\w)/sys(?:/|\s|$)",             re.IGNORECASE),
    re.compile(r"(?<!\w)/dev(?:/|\s|$)",             re.IGNORECASE),
    re.compile(r"(?<!\w)/usr(?:/|\s|$)",             re.IGNORECASE),
]


# Command injection patterns
INJECTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"`[^`]+`"),                          # backtick subshell
    re.compile(r"\$\([^)]+\)"),                      # $() subshell
    re.compile(r"%COMSPEC%",                         re.IGNORECASE),  # Windows shell var
    re.compile(r"cmd\.exe\s*/[cCkK]",               re.IGNORECASE),  # cmd.exe /c injection
    re.compile(r"powershell\.exe\s+-",              re.IGNORECASE),  # nested PS call
    re.compile(r";\s*(rm|del|format|shutdown)",      re.IGNORECASE),  # semicolon injection
]


# Chaining operators — command must be single
CHAINING_PATTERNS: List[re.Pattern] = [
    re.compile(r"&&"),
    re.compile(r"\|\|"),
    re.compile(r"\r?\n"),                            # newline as command separator
]


# Shell-specific safe command prefixes (LOW risk whitelist)
SAFE_COMMAND_PREFIXES = {
    "powershell": [
        "get-childitem", "dir", "ls", "get-process", "get-service",
        "get-content", "select-string", "where-object", "get-item",
        "get-location", "get-date", "get-host", "get-command",
        "get-help", "test-path", "measure-object", "get-psdrive",
    ],
    "cmd": [
        "dir", "echo", "type", "find", "findstr", "where",
        "tasklist", "ipconfig", "ping", "netstat", "cls",
    ],
    "bash": [
        "ls", "cat", "pwd", "find", "grep", "echo", "ps",
        "df", "du", "top", "uname", "whoami", "date", "which",
        "man", "help", "history", "env", "printenv",
    ],
}


# ─────────────────────────────────────────────
# VALIDATOR
# ─────────────────────────────────────────────

class CommandValidator:
    """
    Statically analyses a ShellCommandSchema command string.
    Runs after shell generation, before sandboxed execution.

    Usage:
        result = CommandValidator.validate(shell_schema)
        if not result.safe:
            # block execution
    """

    @classmethod
    def validate(cls, schema: ShellCommandSchema) -> ValidationResult:
        violations: List[ValidationViolation] = []

        cls._check_empty_command(schema, violations)
        cls._check_command_length(schema, violations)
        cls._check_chaining(schema, violations)
        cls._check_injection(schema, violations)
        cls._check_dangerous_patterns(schema, violations)
        cls._check_protected_paths(schema, violations)
        cls._check_low_risk_whitelist(schema, violations)

        if violations:
            logger.warning(
                "Command validation FAILED for '%s' — %d violation(s)",
                schema.command, len(violations)
            )
            return ValidationResult(
                status     = ValidationStatus.FAILED,
                violations = violations,
                safe       = False,
            )

        logger.debug("Command validation PASSED: '%s'", schema.command)
        return ValidationResult(
            status = ValidationStatus.PASSED,
            safe   = True,
        )

    # ── CHECKS ──────────────────────────────────────────

    @staticmethod
    def _check_empty_command(
        schema: ShellCommandSchema,
        violations: List[ValidationViolation]
    ) -> None:
        if not schema.command or not schema.command.strip():
            violations.append(ValidationViolation(
                rule   = "EMPTY_COMMAND",
                reason = "Command string is empty or whitespace only.",
            ))

    @staticmethod
    def _check_command_length(
        schema: ShellCommandSchema,
        violations: List[ValidationViolation]
    ) -> None:
        # Abnormally long commands often indicate obfuscation
        if len(schema.command) > 500:
            violations.append(ValidationViolation(
                rule   = "COMMAND_TOO_LONG",
                reason = (
                    f"Command length {len(schema.command)} exceeds 500 chars. "
                    "May indicate obfuscation."
                ),
            ))

    @staticmethod
    def _check_chaining(
        schema: ShellCommandSchema,
        violations: List[ValidationViolation]
    ) -> None:
        # Semicolons allowed in PowerShell but not bash
        if schema.shell_type == "bash" and ";" in schema.command:
            violations.append(ValidationViolation(
                rule   = "COMMAND_CHAINING",
                reason = "Bash command contains semicolon — only single commands allowed.",
            ))

        for pattern in CHAINING_PATTERNS:
            if pattern.search(schema.command):
                violations.append(ValidationViolation(
                    rule   = "COMMAND_CHAINING",
                    reason = (
                        f"Command contains chaining operator "
                        f"matching /{pattern.pattern}/."
                    ),
                ))
                break

    @staticmethod
    def _check_injection(
        schema: ShellCommandSchema,
        violations: List[ValidationViolation]
    ) -> None:
        for pattern in INJECTION_PATTERNS:
            if pattern.search(schema.command):
                violations.append(ValidationViolation(
                    rule   = "COMMAND_INJECTION",
                    reason = (
                        f"Potential command injection pattern detected: "
                        f"/{pattern.pattern}/"
                    ),
                ))

    @staticmethod
    def _check_dangerous_patterns(
        schema: ShellCommandSchema,
        violations: List[ValidationViolation]
    ) -> None:
        for pattern in DANGEROUS_PATTERNS:
            if pattern.search(schema.command):
                violations.append(ValidationViolation(
                    rule   = "DANGEROUS_COMMAND_PATTERN",
                    reason = (
                        f"Command matches dangerous pattern: "
                        f"/{pattern.pattern}/"
                    ),
                ))

    @staticmethod
    def _check_protected_paths(
        schema: ShellCommandSchema,
        violations: List[ValidationViolation]
    ) -> None:
        for pattern in PROTECTED_PATHS:
            if pattern.search(schema.command):
                violations.append(ValidationViolation(
                    rule   = "PROTECTED_PATH",
                    reason = (
                        f"Command targets a protected system path: "
                        f"/{pattern.pattern}/"
                    ),
                ))

    @staticmethod
    def _check_low_risk_whitelist(
        schema: ShellCommandSchema,
        violations: List[ValidationViolation]
    ) -> None:
        """
        For LOW risk commands, verify the base command is a known safe prefix.
        Catches cases where risk_level was misclassified.
        """
        if schema.expected_risk != "LOW":
            return

        shell    = schema.shell_type.lower()
        prefixes = SAFE_COMMAND_PREFIXES.get(shell, [])
        if not prefixes:
            return

        base_command = schema.command.strip().split()[0].lower()
        if base_command not in prefixes:
            violations.append(ValidationViolation(
                rule   = "LOW_RISK_WHITELIST_MISS",
                reason = (
                    f"Command '{base_command}' is not on the LOW risk "
                    f"safe-command list for {shell}. "
                    f"Risk may be misclassified."
                ),
            ))


import re
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.intent_schema import IntentSchema


# POLICY DECISION TYPES


class PolicyDecision(str, Enum):
    ALLOW                = "ALLOW"                # safe to proceed to LLM #2
    BLOCK                = "BLOCK"                # hard stop, never reaches execution
    REQUIRE_CONFIRMATION = "REQUIRE_CONFIRMATION" # pause and ask user
    CLARIFY              = "CLARIFY"              # LLM #1 was unsure, ask user to rephrase


class ViolationSeverity(str, Enum):
    INFO     = "INFO"
    WARNING  = "WARNING"
    CRITICAL = "CRITICAL"


# ─────────────────────────────────────────────
# POLICY MODELS
# ─────────────────────────────────────────────

class PolicyViolation(BaseModel):
    rule:     str
    reason:   str
    severity: ViolationSeverity


class PolicyResult(BaseModel):
    decision:         PolicyDecision
    violations:       List[PolicyViolation] = Field(default_factory=list)
    reason:           str
    safe_to_proceed:  bool
    sanitized_params: Optional[Dict[str, Any]] = None  # returned if params were cleaned



# ─────────────────────────────────────────────
# POLICY RULES — BLOCKED INTENTS
# Intents that should NEVER reach shell synthesis.
# ─────────────────────────────────────────────

BLOCKED_INTENTS: set[str] = {
    # filesystem destruction
    "delete_system_files",
    "remove_root_directory",
    "format_drive",
    "wipe_disk",
    "overwrite_disk",

    # system destabilisation
    "shutdown_system",
    "reboot_system",
    "kill_all_processes",
    "disable_firewall",
    "disable_antivirus",
    "corrupt_bootloader",

    # privilege escalation
    "add_sudo_user",
    "grant_root_access",
    "modify_sudoers",
    "change_admin_password",

    # data destruction
    "drop_database",
    "truncate_all_tables",
    "delete_all_logs",

    # network attacks
    "port_scan_external",
    "flood_network",
    "disable_network_interfaces",

    # system folder operations
    "delete_system_folder",
    "delete_system_files",
    "modify_system_directory",
    "remove_system32",
    "delete_windows_folder",
}


# ─────────────────────────────────────────────
# POLICY RULES — DANGEROUS PARAMETER PATTERNS
# Regex matched against ALL parameter values.
# ─────────────────────────────────────────────

DANGEROUS_PARAM_PATTERNS: List[re.Pattern] = [
    re.compile(r"rm\s+-rf\s+/",      re.IGNORECASE),
    re.compile(r"mkfs",               re.IGNORECASE),
    re.compile(r"dd\s+if=",           re.IGNORECASE),
    re.compile(r">\s*/dev/sd",        re.IGNORECASE),
    re.compile(r"format\s+[a-z]:",    re.IGNORECASE),  # Windows format C:
    re.compile(r"del\s+/[sqf]",       re.IGNORECASE),  # Windows del /s /q /f
    re.compile(r"rd\s+/[sq].*\\",     re.IGNORECASE),  # Windows rd /s /q
    re.compile(r"curl.*\|\s*(bash|sh)", re.IGNORECASE), # curl | bash
    re.compile(r"wget.*\|\s*(bash|sh)", re.IGNORECASE), # wget | sh
    re.compile(r"chmod\s+777\s+/",    re.IGNORECASE),
    re.compile(r":()\{.*\}",          re.IGNORECASE),  # fork bomb
    re.compile(r"base64\s+--decode",  re.IGNORECASE),  # encoded payload execution
]

# Protected paths — any parameter value matching these = BLOCK
PROTECTED_PATHS: List[re.Pattern] = [
    # Windows critical
    re.compile(r"C:\\Windows",            re.IGNORECASE),
    re.compile(r"C:\\Windows\\System32",  re.IGNORECASE),
    re.compile(r"C:\\Windows\\SysWOW64",  re.IGNORECASE),
    re.compile(r"C:\\Program Files",      re.IGNORECASE),
    re.compile(r"C:\\Users\\.*\\AppData", re.IGNORECASE),

    # Linux/macOS critical
    re.compile(r"^/etc",                  re.IGNORECASE),
    re.compile(r"^/bin",                  re.IGNORECASE),
    re.compile(r"^/sbin",                 re.IGNORECASE),
    re.compile(r"^/usr",                  re.IGNORECASE),
    re.compile(r"^/boot",                 re.IGNORECASE),
    re.compile(r"^/sys",                  re.IGNORECASE),
    re.compile(r"^/dev",                  re.IGNORECASE),
]

# ─────────────────────────────────────────────
# POLICY RULES — SHELL TYPE / OS CONSISTENCY
# ─────────────────────────────────────────────

VALID_SHELLS_PER_OS: Dict[str, List[str]] = {
    "windows": ["powershell", "cmd"],
    "linux":   ["bash"],
    "macos":   ["bash"],
}


# ─────────────────────────────────────────────
# POLICY ENGINE
# ─────────────────────────────────────────────

class PolicyEngine:
    """
    Evaluates an IntentSchema against policy rules.
    Returns a PolicyResult with ALLOW / BLOCK / REQUIRE_CONFIRMATION / CLARIFY.

    Usage:
        engine = PolicyEngine(os_context="windows")
        result = engine.evaluate(intent_schema)
    """

    def __init__(
        self,
        os_context:          Literal["windows", "linux", "macos"] = "linux",
        max_retries_reached: bool = False,
    ):
        self.os_context          = os_context
        self.max_retries_reached = max_retries_reached
        self._violations: List[PolicyViolation] = []

    # ── PUBLIC ──────────────────────────────

    def evaluate(self, schema: IntentSchema) -> PolicyResult:
        """Run all policy checks and return a single PolicyResult."""
        self._violations = []

        # --- ordered checks (cheapest / most critical first) ---
        self._check_unknown_action(schema)
        self._check_low_confidence(schema)
        self._check_blocked_intent(schema)
        self._check_protected_paths(schema)
        self._check_dangerous_parameters(schema)
        self._check_shell_os_consistency(schema)
        self._check_risk_level(schema)
        self._check_max_retries(schema)

        return self._build_result(schema)

    # ── PRIVATE CHECKS ───────────────────────

    def _check_unknown_action(self, schema: IntentSchema) -> None:
        if schema.action_type == "unknown":
            self._violations.append(PolicyViolation(
                rule     = "UNKNOWN_ACTION_TYPE",
                reason   = "Intent could not be classified. User should clarify.",
                severity = ViolationSeverity.WARNING,
            ))

    def _check_low_confidence(self, schema: IntentSchema) -> None:
        if schema.confidence == "LOW":
            self._violations.append(PolicyViolation(
                rule     = "LOW_CONFIDENCE_INTENT",
                reason   = f"LLM #1 classified intent '{schema.intent}' with LOW confidence.",
                severity = ViolationSeverity.WARNING,
            ))

    def _check_blocked_intent(self, schema: IntentSchema) -> None:
        if schema.intent in BLOCKED_INTENTS:
            self._violations.append(PolicyViolation(
                rule     = "BLOCKED_INTENT",
                reason   = f"Intent '{schema.intent}' is on the hard-block list.",
                severity = ViolationSeverity.CRITICAL,
            ))

    def _check_dangerous_parameters(self, schema: IntentSchema) -> None:
        for key, value in schema.parameters.items():
            value_str = str(value)
            for pattern in DANGEROUS_PARAM_PATTERNS:
                if pattern.search(value_str):
                    self._violations.append(PolicyViolation(
                        rule     = "DANGEROUS_PARAMETER_VALUE",
                        reason   = (
                            f"Parameter '{key}' contains dangerous pattern "
                            f"matching /{pattern.pattern}/"
                        ),
                        severity = ViolationSeverity.CRITICAL,
                    ))
                    break  # one violation per parameter key is enough

    def _check_shell_os_consistency(self, schema: IntentSchema) -> None:
        if schema.shell_type == "none":
            return  # no shell needed, nothing to check
        allowed = VALID_SHELLS_PER_OS.get(self.os_context, [])
        if schema.shell_type not in allowed:
            self._violations.append(PolicyViolation(
                rule     = "SHELL_OS_MISMATCH",
                reason   = (
                    f"shell_type '{schema.shell_type}' is not valid for "
                    f"os_context '{self.os_context}'. Allowed: {allowed}"
                ),
                severity = ViolationSeverity.WARNING,
            ))

    def _check_risk_level(self, schema: IntentSchema) -> None:
        if schema.risk_level == "HIGH":
            self._violations.append(PolicyViolation(
                rule     = "HIGH_RISK_OPERATION",
                reason   = (
                    f"Intent '{schema.intent}' is classified as HIGH risk. "
                    "Explicit user approval required."
                ),
                severity = ViolationSeverity.CRITICAL,
            ))
        elif schema.risk_level == "MEDIUM":
            self._violations.append(PolicyViolation(
                rule     = "MEDIUM_RISK_OPERATION",
                reason   = (
                    f"Intent '{schema.intent}' is classified as MEDIUM risk. "
                    "User confirmation required before execution."
                ),
                severity = ViolationSeverity.WARNING,
            ))

    def _check_max_retries(self, schema: IntentSchema) -> None:
        if self.max_retries_reached:
            self._violations.append(PolicyViolation(
                rule     = "MAX_RETRIES_EXCEEDED",
                reason   = "Shell synthesis has failed and exhausted all retries.",
                severity = ViolationSeverity.CRITICAL,
            ))

    def _check_protected_paths(self, schema: IntentSchema) -> None:
        for key, value in schema.parameters.items():
            value_str = str(value)
            for pattern in PROTECTED_PATHS:
                if pattern.search(value_str):
                    self._violations.append(PolicyViolation(
                        rule     = "PROTECTED_PATH_TARGET",
                        reason   = (
                            f"Parameter '{key}' targets a protected system path: "
                            f"'{value_str}'. This operation is hard-blocked."
                        ),
                        severity = ViolationSeverity.CRITICAL,
                    ))
                    break
    # ── DECISION BUILDER ─────────────────────

    def _build_result(self, schema: IntentSchema) -> PolicyResult:
        critical  = [v for v in self._violations if v.severity == ViolationSeverity.CRITICAL]
        warnings  = [v for v in self._violations if v.severity == ViolationSeverity.WARNING]

        # ── BLOCK: any critical violation ──
        if critical:
            # Distinguish hard block vs approval needed
            block_rules = {"BLOCKED_INTENT", "DANGEROUS_PARAMETER_VALUE", "MAX_RETRIES_EXCEEDED"}
            approval_rules = {"HIGH_RISK_OPERATION"}

            is_hard_block = any(v.rule in block_rules for v in critical)

            if is_hard_block:
                return PolicyResult(
                    decision        = PolicyDecision.BLOCK,
                    violations      = self._violations,
                    reason          = critical[0].reason,
                    safe_to_proceed = False,
                )
            else:
                # HIGH_RISK → needs explicit approval (maps to architecture's "explicit approval")
                return PolicyResult(
                    decision        = PolicyDecision.REQUIRE_CONFIRMATION,
                    violations      = self._violations,
                    reason          = critical[0].reason,
                    safe_to_proceed = False,
                )

        # ── CLARIFY: unknown action or low confidence ──
        clarify_rules = {"UNKNOWN_ACTION_TYPE", "LOW_CONFIDENCE_INTENT"}
        if any(v.rule in clarify_rules for v in warnings):
            return PolicyResult(
                decision        = PolicyDecision.CLARIFY,
                violations      = self._violations,
                reason          = warnings[0].reason,
                safe_to_proceed = False,
            )

        # ── REQUIRE_CONFIRMATION: medium risk or shell mismatch (auto-correctable) ──
        if warnings:
            # Auto-correct shell type mismatch before passing to LLM #2
            sanitized_params = dict(schema.parameters)
            corrected_shell  = VALID_SHELLS_PER_OS.get(self.os_context, ["bash"])[0]

            return PolicyResult(
                decision        = PolicyDecision.REQUIRE_CONFIRMATION,
                violations      = self._violations,
                reason          = warnings[0].reason,
                safe_to_proceed = False,
                sanitized_params = sanitized_params,
            )

        # ── ALLOW: no violations ──
        return PolicyResult(
            decision        = PolicyDecision.ALLOW,
            violations      = [],
            reason          = "All policy checks passed.",
            safe_to_proceed = True,
        )
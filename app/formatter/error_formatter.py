"""
SynapseCLI — Error Formatter
Formats all failure states into human-readable messages.
"""

from rich.console import Console

console = Console()

# Maps internal status to human-readable titles
STATUS_TITLES = {
    "blocked":             ("✗", "red",    "Request Blocked"),
    "execution_failed":    ("✗", "red",    "Execution Failed"),
    "error":               ("✗", "red",    "Something Went Wrong"),
    "clarify":             ("?", "yellow", "Could Not Understand"),
    "require_confirmation":("!", "yellow", "Confirmation Required"),
}

# Maps violation rule names to plain English
RULE_MESSAGES = {
    "BLOCKED_INTENT":            "This operation is not permitted.",
    "DANGEROUS_PARAMETER_VALUE": "A parameter contains a dangerous value.",
    "PROTECTED_PATH":            "This path is protected and cannot be modified.",
    "PROTECTED_PATH_TARGET":     "This targets a protected system path.",
    "HIGH_RISK_OPERATION":       "This is a high-risk operation requiring approval.",
    "MEDIUM_RISK_OPERATION":     "This operation requires confirmation.",
    "SHELL_OS_MISMATCH":         "The shell type doesn't match your OS.",
    "DANGEROUS_COMMAND_PATTERN": "The command contains a dangerous pattern.",
    "COMMAND_CHAINING":          "Command chaining is not allowed.",
    "COMMAND_INJECTION":         "Potential command injection detected.",
    "COMMAND_TOO_LONG":          "Command is unusually long — possible obfuscation.",
    "LOW_RISK_WHITELIST_MISS":   "Command not recognized as safe for this operation.",
    "UNKNOWN_INTENT_MAPPING":    "This operation type is not yet supported.",
    "UNKNOWN_COMMAND_CAPABILITY":"This command is not in the allowed list.",
    "INTENT_COMMAND_MISMATCH":   "The generated command doesn't match the request.",
    "LOW_CONFIDENCE_INTENT":     "Request was too ambiguous to process safely.",
    "UNKNOWN_ACTION_TYPE":       "Could not determine what you want to do.",
    "MAX_RETRIES_EXCEEDED":      "Command failed after multiple attempts.",
    "POLICY_VIOLATION":          "Execution policy does not permit this operation.",
}


def format_error(response: dict) -> None:
    """Format and display any failure or blocked response."""

    status  = response.get("status", "error")
    icon, color, title = STATUS_TITLES.get(status, ("✗", "red", "Failed"))

    console.print()
    console.print(f"  [bold {color}]{icon} {title}[/bold {color}]")
    console.print()

    # ── Primary reason ────────────────────────────────────
    reason = response.get("reason") or response.get("message", "")
    if reason:
        console.print(f"  [dim]Reason:[/dim]")
        console.print(f"  {_clean_reason(reason)}")
        console.print()

    # ── Violations list ───────────────────────────────────
    violations = _collect_violations(response)
    if violations:
        console.print(f"  [dim]Issues:[/dim]")
        for v in violations:
            rule    = v.get("rule", "")
            message = RULE_MESSAGES.get(rule, v.get("reason", rule))
            console.print(f"  [dim]•[/dim] {message}")
        console.print()

    # ── Failed command (if exists) ────────────────────────
    command = response.get("command", {})
    cmd_str = command.get("command") if isinstance(command, dict) else None
    if cmd_str:
        console.print(f"  [dim]Command:[/dim]")
        console.print(f"  [dim]  {cmd_str}[/dim]")
        console.print()

    # ── Execution stderr (if execution failed) ────────────
    execution = response.get("execution", {})
    if isinstance(execution, dict):
        stderr = execution.get("stderr", "").strip()
        if stderr and status == "execution_failed":
            # Show first 3 lines of stderr only
            lines = stderr.splitlines()[:3]
            console.print(f"  [dim]Error detail:[/dim]")
            for line in lines:
                console.print(f"  [dim]  {line}[/dim]")
            console.print()

    # ── Clarify hint ──────────────────────────────────────
    if status == "clarify":
        console.print(f"  [dim]Try being more specific about what you want to do.[/dim]")
        console.print()


def format_confirmation(response: dict) -> None:
    """Format a require_confirmation prompt."""

    intent  = response.get("intent", {})
    command = response.get("command", {})

    console.print()
    console.print("  [bold yellow]! Confirmation Required[/bold yellow]")
    console.print()

    intent_str = intent.get("intent", "unknown").replace("_", " ").title()
    risk       = intent.get("risk_level", "MEDIUM")
    cmd_str    = command.get("command", "") if isinstance(command, dict) else ""

    console.print(f"  [dim]Action:[/dim]  {intent_str}")
    console.print(f"  [dim]Risk:[/dim]    [yellow]{risk}[/yellow]")

    if cmd_str:
        console.print(f"  [dim]Command:[/dim]")
        console.print(f"  [bold]  {cmd_str}[/bold]")

    reason = response.get("reason", "")
    if reason:
        console.print()
        console.print(f"  [dim]{_clean_reason(reason)}[/dim]")

    console.print()


# ── Helpers ───────────────────────────────────────────────

def _collect_violations(response: dict) -> list:
    """Pull violations from policy, semantic, or validation results."""
    violations = []

    policy = response.get("policy", {})
    if isinstance(policy, dict):
        violations.extend(policy.get("violations", []))

    semantic = response.get("semantic", {})
    if isinstance(semantic, dict):
        violations.extend(semantic.get("violations", []))

    direct = response.get("violations", [])
    if direct:
        violations.extend(direct)

    return violations


def _clean_reason(reason: str) -> str:
    """Strip internal rule names from user-facing reason strings."""
    for rule, message in RULE_MESSAGES.items():
        if rule in reason:
            return message
    # Truncate overly long reasons
    if len(reason) > 120:
        return reason[:120] + "..."
    return reason
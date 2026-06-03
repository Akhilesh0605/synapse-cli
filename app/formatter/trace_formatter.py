"""
SynapseCLI — Trace Formatter
Developer/debug mode — shows pipeline stage timings and status.
"""

from rich.console import Console

console = Console()

STAGE_LABELS = {
    "intent_generation":  "Intent Classification",
    "policy_evaluation":  "Policy Evaluation",
    "shell_generation":   "Shell Synthesis",
    "command_validation": "Command Validation",
    "semantic_validation":"Semantic Validation",
    "execution_policy":   "Execution Policy",
    "execution":          "Execution",
}


def format_trace(response: dict) -> None:
    """Format and display pipeline trace in developer mode."""

    trace = response.get("trace", {})
    if not trace:
        return

    stages      = trace.get("stages", [])
    total_ms    = trace.get("total_ms", 0)
    failed      = trace.get("failed_stage")

    console.print()
    console.print("  [dim]── Pipeline Trace ──────────────────────[/dim]")
    console.print()

    for stage in stages:
        name       = stage.get("stage_name", "")
        latency    = stage.get("latency_ms", 0)
        success    = stage.get("success", True)
        error_msg  = stage.get("error_message")
        label      = STAGE_LABELS.get(name, name.replace("_", " ").title())

        if success:
            icon  = "[green]✓[/green]"
            color = "white"
        else:
            icon  = "[red]✗[/red]"
            color = "red"

        # Right-align latency at column 42
        label_padded = label.ljust(26)
        ms_str       = f"{latency}ms".rjust(8)

        console.print(f"  {icon} [{color}]{label_padded}[/{color}] [dim]{ms_str}[/dim]")

        if not success and error_msg:
            short = error_msg[:80] + "..." if len(error_msg) > 80 else error_msg
            console.print(f"     [dim red]  {short}[/dim red]")

    console.print()
    console.print(f"  [dim]Total: {total_ms}ms across {len(stages)} stages[/dim]")

    if failed:
        label = STAGE_LABELS.get(failed, failed)
        console.print(f"  [dim red]Failed at: {label}[/dim red]")

    console.print()
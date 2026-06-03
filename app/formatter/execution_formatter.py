"""
SynapseCLI — Execution Formatter
Formats successful command execution results for display.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text

console = Console()


def format_execution(response: dict) -> None:
    """Format and display a successful execution result."""

    intent  = response.get("intent", {})
    command = response.get("command", {})
    execution = response.get("execution", {})

    # ── Header ───────────────────────────────────────────
    console.print()
    console.print("  [bold green]✓ Command executed successfully[/bold green]")
    console.print()

    # ── Intent summary ────────────────────────────────────
    intent_str = intent.get("intent", "unknown").replace("_", " ").title()
    console.print(f"  [dim]Action:[/dim]  {intent_str}")
    console.print()

    # ── Command ───────────────────────────────────────────
    cmd_str = command.get("command", "")
    if cmd_str:
        console.print("  [dim]Command:[/dim]")
        console.print(f"  [bold cyan]  {cmd_str}[/bold cyan]")
        console.print()

    # ── stdout output ─────────────────────────────────────
    stdout = execution.get("stdout", "").strip()
    if stdout:
        console.print("  [dim]Output:[/dim]")
        console.print()

        lines = stdout.splitlines()

        # Truncate if too long
        MAX_LINES = 40
        truncated = len(lines) > MAX_LINES
        display_lines = lines[:MAX_LINES]

        for line in display_lines:
            console.print(f"  {line}")

        if truncated:
            remaining = len(lines) - MAX_LINES
            console.print(f"  [dim]... {remaining} more lines[/dim]")

        console.print()

    # ── No output case ────────────────────────────────────
    elif not stdout:
        action = intent.get("intent", "")
        if "create" in action or "write" in action or "move" in action:
            path = intent.get("parameters", {}).get("target_path", "")
            if path:
                console.print(f"  [dim]Location:[/dim]")
                console.print(f"  [cyan]  {path}[/cyan]")
                console.print()

    # ── Execution time ────────────────────────────────────
    exec_ms = execution.get("execution_time_ms", 0)
    console.print(f"  [dim]Time:[/dim]  {exec_ms}ms")
    console.print()
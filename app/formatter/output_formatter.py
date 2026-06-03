"""
SynapseCLI — Output Formatter
Main entry point. Routes response to the correct formatter.
"""

from rich.console import Console

from app.formatter.execution_formatter import format_execution
from app.formatter.error_formatter import (
    format_error,
    format_confirmation,
)
from app.formatter.trace_formatter import format_trace

console = Console()

# Statuses that are errors or blocks
ERROR_STATUSES = {
    "blocked",
    "execution_failed",
    "error",
    "clarify",
}


def format_response(response: dict, debug: bool = False) -> None:
    """
    Main formatter entry point.

    Args:
        response : full pipeline response dict from process_query()
        debug    : if True, also print pipeline trace
    """

    status = response.get("status", "error")

    # ── Route to correct formatter ────────────────────────
    if status == "success":
        format_execution(response)

    elif status == "require_confirmation":
        format_confirmation(response)

    elif status == "ai_response":
        _format_ai_response(response)

    elif status == "web_navigation":
        _format_web_navigation(response)

    elif status == "web_search":
        _format_web_search(response)

    elif status in ERROR_STATUSES:
        format_error(response)

    else:
        # Fallback — unknown status
        format_error(response)

    # ── Debug trace (always last) ─────────────────────────
    if debug:
        format_trace(response)


# ── Non-shell response formatters ─────────────────────────

def _format_ai_response(response: dict) -> None:
    answer = response.get("answer", "")
    intent = response.get("intent", {})

    console.print()
    console.print("  [bold cyan]◆ SynapseCLI[/bold cyan]")
    console.print()

    if answer:
        # Word-wrap at 72 chars
        for line in answer.splitlines():
            if line.strip():
                console.print(f"  {line}")
            else:
                console.print()
    else:
        topic = intent.get("intent", "").replace("_", " ")
        console.print(f"  [dim]No answer available for: {topic}[/dim]")

    console.print()


def _format_web_navigation(response: dict) -> None:
    url    = response.get("url", "")
    intent = response.get("intent", {})
    action = intent.get("intent", "").replace("_", " ").title()

    console.print()
    console.print("  [bold cyan]◆ Opening browser[/bold cyan]")
    console.print()
    console.print(f"  [dim]Action:[/dim]  {action}")
    if url:
        console.print(f"  [dim]URL:[/dim]     [cyan]{url}[/cyan]")
    console.print()


def _format_web_search(response: dict) -> None:
    message = response.get("message", "")

    console.print()
    console.print("  [bold cyan]◆ Opening web search[/bold cyan]")
    console.print()
    if message:
        console.print(f"  {message}")
    console.print()
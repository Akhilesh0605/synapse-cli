import typer
import webbrowser
from rich.prompt import Confirm
from app.ui.console import console
from app.core.orchestrator import process_query
from app.formatter.output_formatter import format_response
from app.database.connection import create_tables

# Initialize database on app startup
create_tables()

app = typer.Typer()

@app.command()
def run(
    query: str,
    debug: bool = typer.Option(False, "--debug", "-d", help="Show pipeline trace")
):
    console.print(f"[bold cyan]Received Query[/bold cyan] : {query}")

    result = process_query(query)

    # Handle confirmation before formatting
    if result.get("status") == "require_confirmation":
        format_response(result, debug=debug)
        proceed = Confirm.ask("Proceed?", default=False)
        if not proceed:
            console.print("\n  [dim]Cancelled.[/dim]\n")
            return
        result = process_query(query, force_confirm=True)

    # Handle web navigation
    if result.get("status") == "web_navigation":
        url = result.get("url")
        if url:
            webbrowser.open(url)

    # Final formatted output
    format_response(result, debug=debug)
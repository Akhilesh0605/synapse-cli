import typer
import webbrowser
from rich.prompt import Confirm
from app.ui.console import console
from app.core.orchestrator import process_query

app=typer.Typer()

@app.command()

def run(query:str):
    console.print(f"[boldcyan]Recieved Query [/boldcyan] : {query}")
    result=process_query(query)
    if result.get("status") == "require_confirmation":
        proceed = Confirm.ask("This action requires confirmation. Proceed?", default=False)
        if proceed:
            result = process_query(query, force_confirm=True)
    if result.get("status") == "web_navigation":
        url = result.get("url")
        if url:
            webbrowser.open(url)

    console.print(f"\n[bold green] Generated Response:[/bold green]")
    console.print(result)

if __name__=="__main__":
    app()
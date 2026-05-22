import typer
from app.ui.console import console
from app.core.orchestrator import process_query

app=typer.Typer()

@app.command()

def run(query:str):
    console.print(f"[boldcyan]Recieved Query [/boldcyan] : {query}")
    result=process_query(query)
    console.print(f"\n[bold green] Generated Response:[/bold green]")
    console.print(result)

if __name__=="__main__":
    app()
import typer
from app.ui.console import console
from app.llm.client import generate_command

app=typer.Typer()

@app.command()

def run(query:str):
    console.print(f"[cyan]Recieved Query [/cyan] : {query}")
    result=generate_command(query)
    console.print(f"\n[bold green] Generated Response:[/bold green]")
    console.print(result)

if __name__=="__main__":
    app()
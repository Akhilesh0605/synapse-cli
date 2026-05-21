import typer
from app.ui.console import console

app=typer.Typer()

@app.command()

def run(query:str):
    console.print(f"[cyan]Recieved Query [/cyan] : {query}")

if __name__=="__main__":
    app()
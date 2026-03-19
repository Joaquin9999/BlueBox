import typer

app = typer.Typer(
    no_args_is_help=True,
    help="BlueBox CLI",
)


@app.callback()
def main() -> None:
    """BlueBox CLI."""


@app.command()
def version() -> None:
    """Show BlueBox version."""
    typer.echo("bluebox 0.1.0")


if __name__ == "__main__":
    app()

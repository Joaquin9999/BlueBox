import typer

app = typer.Typer(
    no_args_is_help=True,
    help="BlueHunt CLI",
)


@app.callback()
def main() -> None:
    """BlueHunt CLI."""


@app.command()
def version() -> None:
    """Show BlueHunt version."""
    typer.echo("bluehunt 0.1.0")


if __name__ == "__main__":
    app()

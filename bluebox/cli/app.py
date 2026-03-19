from pathlib import Path

import typer
from rich.console import Console

from bluebox.core import initialize_case_from_artifacts

app = typer.Typer(
    no_args_is_help=True,
    help="BlueBox CLI",
)
console = Console()


@app.callback()
def main() -> None:
    """BlueBox CLI."""


@app.command()
def version() -> None:
    """Show BlueBox version."""
    typer.echo("bluebox 0.1.0")


@app.command()
def init(
    challenge_name: str = typer.Argument(..., help="Raw challenge name."),
    artifacts: Path = typer.Option(..., "--artifacts", help="Artifacts path (file or directory)."),
    title: str = typer.Option(..., "--title", help="Human-readable challenge title."),
    context: str = typer.Option("", "--context", help="Initial case context."),
    base_path: Path = typer.Option(Path("."), "--base-path", help="Directory where the case folder will be created."),
) -> None:
    """Initialize a complete case workspace from artifacts."""
    try:
        case_root = initialize_case_from_artifacts(
            base_path=base_path.resolve(),
            challenge_name=challenge_name,
            artifacts_path=artifacts.resolve(),
            title=title,
            context=context,
        )
    except (FileNotFoundError, FileExistsError) as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    console.print(f"[green]Initialized case:[/green] {case_root}")


if __name__ == "__main__":
    app()

from pathlib import Path

import typer
from rich.console import Console

from bluebox.core import initialize_case_from_artifacts, validate_case_structure

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


@app.command()
def validate(case_path: Path = typer.Argument(..., help="Path to case workspace.")) -> None:
    """Validate case workspace structure and metadata."""
    report = validate_case_structure(case_path.resolve())

    if report.is_valid:
        console.print(f"[green]Validation passed:[/green] {report.case_path}")
    else:
        console.print(f"[red]Validation failed:[/red] {report.case_path}")

    for warning in report.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")

    for error in report.errors:
        console.print(f"[red]Error:[/red] {error}")

    if not report.is_valid:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()

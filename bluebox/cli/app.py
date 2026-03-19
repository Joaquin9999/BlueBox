import json
from pathlib import Path

import typer
from rich.console import Console

from bluebox.core import (
    build_doctor_report,
    check_profile,
    classify_case,
    finalize_case,
    get_case_status,
    initialize_case_from_artifacts,
    install_profile,
    list_profiles,
    prepare_and_launch_solve,
    validate_case_structure,
)

app = typer.Typer(
    no_args_is_help=True,
    help="BlueBox CLI",
)
console = Console()
tools_app = typer.Typer(help="Manage optional Blue Team/DFIR tool profiles.")
app.add_typer(tools_app, name="tools")


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


@app.command()
def classify(case_path: Path = typer.Argument(..., help="Path to case workspace.")) -> None:
    """Classify a case and propose initial analysis direction."""
    try:
        outcome = classify_case(case_path.resolve())
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    console.print(f"[green]Classified:[/green] {outcome.case_path}")
    console.print(f"[cyan]Category:[/cyan] {outcome.category}")
    console.print(
        "[cyan]Subcategories:[/cyan] "
        + (", ".join(outcome.subcategories) if outcome.subcategories else "none")
    )


@app.command()
def solve(
    case_path: Path = typer.Argument(..., help="Path to case workspace."),
    no_launch: bool = typer.Option(False, "--no-launch", help="Prepare solve context without launching Codex CLI."),
) -> None:
    """Prepare and launch Codex CLI for case solving."""
    try:
        outcome = prepare_and_launch_solve(
            case_path.resolve(),
            launch_codex=not no_launch,
        )
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    console.print(f"[green]Prepared solve context:[/green] {outcome.context_path}")
    console.print(f"[green]Prepared solve prompt:[/green] {outcome.prompt_path}")

    if no_launch:
        console.print("[yellow]Codex launch skipped (--no-launch).[/yellow]")
    elif outcome.codex_return_code is not None:
        console.print(f"[cyan]Codex exit code:[/cyan] {outcome.codex_return_code}")


@app.command()
def status(case_path: Path = typer.Argument(..., help="Path to case workspace.")) -> None:
    """Show a concise operational status for a case."""
    try:
        snapshot = get_case_status(case_path.resolve())
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    console.print(f"[bold]Case:[/bold] {snapshot.case_name}")
    console.print(f"[bold]Title:[/bold] {snapshot.title}")
    console.print(f"[bold]Status:[/bold] {snapshot.status}")
    console.print(f"[bold]Category:[/bold] {snapshot.category or 'unclassified'}")
    console.print(f"[bold]Artifacts:[/bold] {snapshot.artifact_count}")
    console.print(f"[bold]Active hypotheses:[/bold] {snapshot.active_hypotheses_count}")
    console.print(f"[bold]Latest update:[/bold] {snapshot.latest_update or 'none'}")


@app.command()
def doctor() -> None:
    """Run environment diagnostics for BlueBox operators."""
    report = build_doctor_report()

    console.print(f"[bold]Python:[/bold] {report.python_version}")
    console.print(f"[bold]Platform:[/bold] {report.platform_info}")

    for check in report.checks:
        status_text = "OK" if check.available else "MISSING"
        color = "green" if check.available else "red"
        console.print(f"[bold]{check.name}:[/bold] [{color}]{status_text}[/{color}] - {check.detail}")


@app.command()
def finalize(
    case_path: Path = typer.Argument(..., help="Path to case workspace."),
    allow_incomplete: bool = typer.Option(
        False,
        "--allow-incomplete",
        help="Generate a clearly marked incomplete final writeup when case is not solved.",
    ),
) -> None:
    """Generate final writeup from accumulated case documentation."""
    try:
        outcome = finalize_case(case_path.resolve(), allow_incomplete=allow_incomplete)
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    if outcome.generated_incomplete:
        console.print(f"[yellow]Generated incomplete final writeup:[/yellow] {outcome.output_path}")
    else:
        console.print(f"[green]Generated final writeup:[/green] {outcome.output_path}")


@tools_app.command("list")
def tools_list() -> None:
    """List available tool profiles and tools."""
    profiles = list_profiles()
    for profile_name, specs in profiles.items():
        console.print(f"[bold]{profile_name}[/bold]")
        for spec in specs:
            console.print(f"  - {spec.name}: {spec.description}")


@tools_app.command("check")
def tools_check(profile: str = typer.Argument(..., help="Profile to check.")) -> None:
    """Check whether tools in a profile are available."""
    try:
        statuses = check_profile(profile)
    except ValueError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    missing = 0
    for status in statuses:
        label = "OK" if status.available else "MISSING"
        color = "green" if status.available else "red"
        console.print(f"- {status.name}: [{color}]{label}[/{color}] ({status.detail})")
        if not status.available and status.install_hint:
            console.print(f"    hint: {status.install_hint}")
        if not status.available:
            missing += 1

    if missing > 0:
        raise typer.Exit(code=1)


@tools_app.command("install")
def tools_install(
    profile: str = typer.Argument(..., help="Profile to install."),
    apply: bool = typer.Option(False, "--apply", help="Execute install commands instead of dry-run."),
) -> None:
    """Install missing tools for a profile (dry-run by default)."""
    try:
        results = install_profile(profile, apply=apply)
    except ValueError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    failures = 0
    for result in results:
        if result.success:
            console.print(f"- {result.name}: [green]OK[/green] ({result.message})")
            continue

        failures += 1
        console.print(f"- {result.name}: [yellow]PENDING[/yellow] ({result.message})")
        if result.command:
            console.print(f"    command: {result.command}")

    if failures > 0:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()

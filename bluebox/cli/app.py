import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.panel import Panel

from bluebox.core import (
    build_doctor_report,
    check_profile,
    classify_case,
    finalize_case,
    get_case_status,
    initialize_case_from_artifacts,
    install_all_profiles,
    install_profile,
    install_tool,
    list_tool_names,
    list_profiles,
    prepare_and_launch_solve,
    validate_case_structure,
)

app = typer.Typer(
    no_args_is_help=True,
    help="BlueBox CLI",
)
console = Console()
ACTIVE_PROJECT_FILE = Path(".bluebox") / "active_case.txt"
PROJECT_HISTORY_FILE = Path(".bluebox") / "projects_history.txt"
RECENT_CASES_FILE = Path(".bluebox") / "recent_cases.json"
SETTINGS_FILE = Path(".bluebox") / "settings.yaml"
project_app = typer.Typer(
    no_args_is_help=True,
    help="Manage active BlueBox project context.",
)
cases_app = typer.Typer(
    no_args_is_help=True,
    help="Manage case context with vNext-style commands.",
)
tools_app = typer.Typer(
    no_args_is_help=False,
    help="Manage optional Blue Team/DFIR tool profiles.",
)
app.add_typer(project_app, name="project")
app.add_typer(cases_app, name="cases")
app.add_typer(tools_app, name="tools")


@tools_app.callback(invoke_without_command=True)
def tools_main(ctx: typer.Context) -> None:
    """Manage optional Blue Team/DFIR tool profiles."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        console.print("\n[bold]Note:[/bold] Use [cyan]tools install <profile>[/cyan] for dry-run suggestions.")
        console.print("[bold]Note:[/bold] Use [cyan]tools install <profile> --apply[/cyan] to execute install commands.")
        raise typer.Exit(code=0)


def _active_project_file() -> Path:
    return Path.cwd() / ACTIVE_PROJECT_FILE


def _project_history_file() -> Path:
    return Path.cwd() / PROJECT_HISTORY_FILE


def _recent_cases_file() -> Path:
    return Path.cwd() / RECENT_CASES_FILE


def _settings_file() -> Path:
    return Path.cwd() / SETTINGS_FILE


def _ensure_settings_file() -> None:
    settings_file = _settings_file()
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    if settings_file.is_file():
        return

    defaults = {
        "default_profile": "minimal",
        "default_evidence_mode": "reference-only",
        "default_launcher": "no-launch",
    }
    settings_file.write_text(yaml.safe_dump(defaults, sort_keys=False), encoding="utf-8")


def _read_recent_cases() -> list[dict[str, str]]:
    recent_file = _recent_cases_file()
    if not recent_file.is_file():
        return []

    try:
        payload = json.loads(recent_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    if not isinstance(payload, list):
        return []

    recent_cases: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        path_value = item.get("path")
        if not isinstance(path_value, str) or not path_value.strip():
            continue

        name_value = item.get("name")
        if not isinstance(name_value, str) or not name_value.strip():
            name_value = Path(path_value).name

        used_at = item.get("used_at")
        if not isinstance(used_at, str) or not used_at.strip():
            used_at = ""

        recent_cases.append(
            {
                "name": name_value.strip(),
                "path": str(Path(path_value).expanduser().resolve()),
                "used_at": used_at,
            }
        )

    return recent_cases


def _write_recent_cases(recent_cases: list[dict[str, str]]) -> None:
    recent_file = _recent_cases_file()
    recent_file.parent.mkdir(parents=True, exist_ok=True)
    recent_file.write_text(json.dumps(recent_cases[:20], indent=2), encoding="utf-8")


def _touch_recent_case(case_root: Path) -> None:
    normalized_path = str(case_root.resolve())
    case_name = case_root.name
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    entries = _read_recent_cases()
    updated = [
        {
            "name": case_name,
            "path": normalized_path,
            "used_at": timestamp,
        }
    ]
    for entry in entries:
        if entry["path"] == normalized_path:
            continue
        updated.append(entry)

    _write_recent_cases(updated)


def _resolve_case_reference(case_ref: str) -> Path:
    candidate = Path(case_ref).expanduser()
    candidate_with_cwd = (Path.cwd() / candidate).resolve()
    if _is_case_workspace(candidate_with_cwd):
        return candidate_with_cwd

    direct_candidate = candidate.resolve()
    if _is_case_workspace(direct_candidate):
        return direct_candidate

    named_candidate = (Path.cwd() / "cases" / case_ref).resolve()
    if _is_case_workspace(named_candidate):
        return named_candidate

    recent_case_match = None
    for entry in _read_recent_cases():
        if entry["name"] == case_ref:
            recent_case_match = Path(entry["path"]).expanduser().resolve()
            break

    if recent_case_match is not None and _is_case_workspace(recent_case_match):
        return recent_case_match

    raise ValueError(f"Case not found: {case_ref}")


def _save_active_case(case_root: Path) -> None:
    active_file = _active_project_file()
    active_file.parent.mkdir(parents=True, exist_ok=True)
    resolved_case_root = case_root.resolve()
    active_file.write_text(str(resolved_case_root), encoding="utf-8")
    _append_project_history(resolved_case_root)
    _touch_recent_case(resolved_case_root)
    _ensure_settings_file()


def _append_project_history(case_root: Path) -> None:
    history_file = _project_history_file()
    history_file.parent.mkdir(parents=True, exist_ok=True)

    existing: list[str] = []
    if history_file.is_file():
        existing = [line.strip() for line in history_file.read_text(encoding="utf-8").splitlines() if line.strip()]

    normalized = str(case_root.resolve())
    updated = [normalized] + [entry for entry in existing if entry != normalized]
    history_file.write_text("\n".join(updated[:50]) + "\n", encoding="utf-8")


def _read_project_history() -> list[Path]:
    history_file = _project_history_file()
    if not history_file.is_file():
        return []

    entries = [line.strip() for line in history_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [Path(entry).expanduser().resolve() for entry in entries]


def _write_project_history(projects: list[Path]) -> None:
    history_file = _project_history_file()
    history_file.parent.mkdir(parents=True, exist_ok=True)
    normalized = [str(project.resolve()) for project in projects]
    if not normalized:
        history_file.write_text("", encoding="utf-8")
        return
    history_file.write_text("\n".join(normalized[:50]) + "\n", encoding="utf-8")


def _is_case_workspace(case_path: Path) -> bool:
    return (case_path / "meta" / "solution_state.json").is_file()


def _read_active_case() -> Path | None:
    active_file = _active_project_file()
    if not active_file.is_file():
        return None

    stored_path = active_file.read_text(encoding="utf-8").strip()
    if not stored_path:
        return None

    return Path(stored_path).expanduser().resolve()


def _resolve_case_path(case_path: Path | None, command_name: str) -> Path:
    if case_path is not None:
        return case_path.resolve()

    cwd = Path.cwd()
    if (cwd / "meta" / "solution_state.json").is_file():
        return cwd.resolve()

    candidate = _read_active_case()
    if candidate is not None and candidate.exists():
        return candidate

    console.print(
        "[red]Error:[/red] No active case found. Run [cyan]bluebox init[/cyan] first "
        "or provide <case-path>."
    )
    console.print(f"Hint: [cyan]bluebox {command_name} <case-path>[/cyan]")
    raise typer.Exit(code=1)


@app.callback()
def main() -> None:
    """BlueBox CLI."""


@app.command()
def version() -> None:
    """Show BlueBox version."""
    typer.echo("bluebox 0.1.0")


@app.command()
def start() -> None:
    """Show onboarding guide, commands, and recommended workflow."""
    message = """[bold]BlueBox Quick Start[/bold]

[bold]0) Setup inicial de herramientas[/bold]
- Opción 1: [cyan]bluebox setup --mode all[/cyan]
- Opción 2: [cyan]bluebox setup --mode tool --tool <name>[/cyan]
- Ejecuta instalación real con [cyan]--apply[/cyan]

[bold]1) Inicializa un caso[/bold]
- Interactivo: [cyan]bluebox init[/cyan]
- Script/CI: [cyan]bluebox init --name \"My Case\" --artifacts ./artifacts --title \"My Case\"[/cyan]

[bold]2) Flujo recomendado por proyecto[/bold]
- Después de [cyan]bluebox init[/cyan], BlueBox guarda el proyecto activo en [cyan].bluebox/active_case.txt[/cyan]
- BlueBox también registra recientes en [cyan].bluebox/recent_cases.json[/cyan] y defaults en [cyan].bluebox/settings.yaml[/cyan]
- Puedes ejecutar sin ruta: [cyan]bluebox classify[/cyan], [cyan]validate[/cyan], [cyan]solve[/cyan], [cyan]status[/cyan], [cyan]finalize[/cyan]
- También puedes pasar ruta explícita: [cyan]bluebox classify <case-path>[/cyan]

[bold]3) Comandos principales[/bold]
- [cyan]doctor[/cyan]: diagnóstico de entorno
- [cyan]project show/set/list/clear[/cyan]: ver, cambiar, listar y limpiar proyecto activo
- [cyan]cases list/current/use/open/clear[/cyan]: comandos vNext para sesión de casos
- [cyan]tools list/check/install[/cyan]: perfiles DFIR/Blue Team opcionales
- [cyan]version[/cyan]: versión instalada

[bold]4) Compatibilidad base[/bold]
- BlueBox es Python puro y se ejecuta en macOS, Linux y Windows con Python 3.12+.
- Verifica tu entorno con [cyan]bluebox doctor[/cyan].

[bold]5) Sobre entorno virtual y tools[/bold]
- BlueBox puede ejecutarse dentro o fuera de un entorno virtual.
- [cyan]tools install --apply[/cyan] ejecuta comandos del sistema (ej. brew/apt), no solo del venv.
- En dry-run (sin [cyan]--apply[/cyan]) solo muestra lo que instalaría.

[bold]Tip[/bold]: Usa [cyan]bluebox --help[/cyan] y [cyan]bluebox <comando> --help[/cyan] para ver opciones detalladas.
"""
    console.print(Panel.fit(message, title="bluebox start", border_style="cyan"))


@app.command()
def setup(
    mode: str | None = typer.Option(
        None,
        "--mode",
        help="Setup mode: 'all' (all profiles) or 'tool' (single tool).",
    ),
    tool: str | None = typer.Option(
        None,
        "--tool",
        help="Tool name when mode is 'tool'.",
    ),
    apply: bool = typer.Option(False, "--apply", help="Execute install commands instead of dry-run."),
) -> None:
    """Run initial setup: install all tool profiles or one specific tool."""
    selected_mode = (mode or "").strip().lower()
    if not selected_mode:
        console.print("[bold]Setup options:[/bold]")
        console.print("1) Install all profiles")
        console.print("2) Install one specific tool")
        option = typer.prompt("Choose option", default="1")
        selected_mode = "all" if option.strip() == "1" else "tool"

    if selected_mode not in {"all", "tool"}:
        console.print("[red]Error:[/red] Invalid mode. Use --mode all or --mode tool.")
        raise typer.Exit(code=1)

    if selected_mode == "all":
        console.print("[bold]Setup mode:[/bold] install all profiles")
        if not apply:
            console.print("[cyan]Dry-run mode:[/cyan] no install commands are executed.")
        else:
            console.print("[yellow]Applying system install commands for missing tools...[/yellow]")

        all_results = install_all_profiles(apply=apply)
        failures = 0
        pending = 0
        for profile_name, profile_results in all_results.items():
            console.print(f"\n[bold]{profile_name}[/bold]")
            for result in profile_results:
                if result.success:
                    console.print(f"- {result.name}: [green]OK[/green] ({result.message})")
                    continue

                if apply:
                    failures += 1
                else:
                    pending += 1
                console.print(f"- {result.name}: [yellow]PENDING[/yellow] ({result.message})")
                if result.command:
                    console.print(f"    command: {result.command}")

        if apply and failures > 0:
            raise typer.Exit(code=1)
        if not apply and pending > 0:
            console.print("\n[bold]Tip:[/bold] Run with [cyan]--apply[/cyan] to execute commands.")
        return

    selected_tool = (tool or "").strip()
    if not selected_tool:
        available_tools = ", ".join(list_tool_names())
        console.print(f"[bold]Available tools:[/bold] {available_tools}")
        selected_tool = typer.prompt("Tool name")

    if not apply:
        console.print("[cyan]Dry-run mode:[/cyan] no install commands are executed.")
    else:
        console.print("[yellow]Applying system install command for selected tool...[/yellow]")

    try:
        result = install_tool(selected_tool, apply=apply)
    except ValueError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    if result.success:
        console.print(f"- {result.name}: [green]OK[/green] ({result.message})")
        return

    console.print(f"- {result.name}: [yellow]PENDING[/yellow] ({result.message})")
    if result.command:
        console.print(f"    command: {result.command}")

    if apply:
        raise typer.Exit(code=1)


@project_app.command("show")
def project_show() -> None:
    """Show currently active project path."""
    active_case = _read_active_case()
    if active_case is None:
        console.print("[red]Error:[/red] No active project set in current workspace.")
        console.print("Hint: run [cyan]bluebox init[/cyan] or [cyan]bluebox project set <case-path>[/cyan].")
        raise typer.Exit(code=1)

    if not active_case.exists():
        console.print(f"[yellow]Warning:[/yellow] Active project path no longer exists: {active_case}")
        raise typer.Exit(code=1)

    console.print(f"[green]Active project:[/green] {active_case}")


@project_app.command("set")
def project_set(case_path: Path = typer.Argument(..., help="Path to case workspace.")) -> None:
    """Set active project path for pathless command usage."""
    resolved_case_path = case_path.expanduser().resolve()
    if not _is_case_workspace(resolved_case_path):
        console.print(f"[red]Error:[/red] Not a valid BlueBox case path: {resolved_case_path}")
        console.print("Hint: expected file [cyan]meta/solution_state.json[/cyan].")
        raise typer.Exit(code=1)

    _save_active_case(resolved_case_path)
    console.print(f"[green]Set active project:[/green] {resolved_case_path}")


@project_app.command("clear")
def project_clear() -> None:
    """Clear active project pointer in current workspace."""
    active_file = _active_project_file()
    if not active_file.is_file():
        console.print("[yellow]No active project to clear.[/yellow]")
        return

    active_file.unlink()
    console.print("[green]Cleared active project.[/green]")


@project_app.command("list")
def project_list(
    existing_only: bool = typer.Option(
        False,
        "--existing-only",
        help="Show only projects that currently exist on disk.",
    ),
    compact: bool = typer.Option(
        False,
        "--compact",
        help="Show compact output (one plain path per line, no status labels).",
    ),
) -> None:
    """List known projects from workspace history."""
    projects = _read_project_history()
    if not projects:
        console.print("[yellow]No projects in history yet.[/yellow]")
        console.print("Hint: run [cyan]bluebox init[/cyan] or [cyan]bluebox project set <case-path>[/cyan].")
        return

    active_case = _read_active_case()
    if existing_only:
        projects = [project_path for project_path in projects if project_path.exists()]

    if not projects:
        console.print("[yellow]No existing projects found in history.[/yellow]")
        return

    if compact:
        for project_path in projects:
            console.print(project_path)
        return

    console.print("[bold]Known projects:[/bold]")
    for project_path in projects:
        is_active = active_case is not None and project_path == active_case
        exists = project_path.exists()
        status = "active" if is_active else "known"
        color = "green" if exists else "yellow"
        if not exists:
            status = f"{status}, missing"
        console.print(f"- [{color}]{project_path}[/{color}] ({status})")


@project_app.command("prune-missing")
def project_prune_missing() -> None:
    """Remove non-existing project paths from workspace history."""
    projects = _read_project_history()
    if not projects:
        console.print("[yellow]No projects in history yet.[/yellow]")
        return

    existing_projects = [project_path for project_path in projects if project_path.exists()]
    removed_count = len(projects) - len(existing_projects)
    _write_project_history(existing_projects)

    console.print(
        f"[green]History pruned.[/green] removed={removed_count}, kept={len(existing_projects)}"
    )


@cases_app.command("list")
def cases_list(existing_only: bool = typer.Option(False, "--existing-only", help="List only existing case paths.")) -> None:
    """List recently used cases in this workspace."""
    recent_cases = _read_recent_cases()
    if existing_only:
        recent_cases = [entry for entry in recent_cases if Path(entry["path"]).exists()]

    if not recent_cases:
        console.print("[yellow]No recent cases found.[/yellow]")
        console.print("Hint: run [cyan]bluebox new[/cyan] or [cyan]bluebox cases use <case>[/cyan].")
        return

    active_case = _read_active_case()
    console.print("[bold]Recent cases:[/bold]")
    for entry in recent_cases:
        path = Path(entry["path"]).expanduser().resolve()
        is_active = active_case is not None and path == active_case
        marker = "active" if is_active else "recent"
        exists = "exists" if path.exists() else "missing"
        console.print(f"- {entry['name']}: {path} ({marker}, {exists})")


@cases_app.command("current")
def cases_current() -> None:
    """Show active case path."""
    active_case = _read_active_case()
    if active_case is None:
        console.print("[red]Error:[/red] No active case set.")
        raise typer.Exit(code=1)

    if not active_case.exists():
        console.print(f"[yellow]Warning:[/yellow] Active case path no longer exists: {active_case}")
        raise typer.Exit(code=1)

    console.print(f"[green]Current case:[/green] {active_case}")


@cases_app.command("use")
def cases_use(case_ref: str = typer.Argument(..., help="Case name or path.")) -> None:
    """Set active case by name or path."""
    try:
        resolved_case = _resolve_case_reference(case_ref)
    except ValueError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    _save_active_case(resolved_case)
    console.print(f"[green]Active case set:[/green] {resolved_case}")


@cases_app.command("open")
def cases_open(case_ref: str | None = typer.Argument(None, help="Optional case name or path.")) -> None:
    """Open case directory in file browser."""
    try:
        case_path = _resolve_case_reference(case_ref) if case_ref else _resolve_case_path(None, "cases open")
    except ValueError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    typer.launch(str(case_path), locate=False)
    console.print(f"[green]Opened case:[/green] {case_path}")


@cases_app.command("clear")
def cases_clear() -> None:
    """Clear active case pointer."""
    project_clear()


@cases_app.command("archive")
def cases_archive(
    case_ref: str = typer.Argument(..., help="Case name or path."),
    destination: Path | None = typer.Option(None, "--to", help="Archive destination directory."),
) -> None:
    """Archive a case directory into exports."""
    try:
        case_path = _resolve_case_reference(case_ref)
    except ValueError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    if destination is None:
        destination = Path.cwd() / "exports"

    destination = destination.expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    target_path = destination / case_path.name

    if target_path.exists():
        console.print(f"[red]Error:[/red] Archive target already exists: {target_path}")
        raise typer.Exit(code=1)

    shutil.move(str(case_path), str(target_path))

    active_case = _read_active_case()
    if active_case is not None and active_case == case_path:
        active_file = _active_project_file()
        if active_file.is_file():
            active_file.unlink()

    console.print(f"[green]Archived case:[/green] {target_path}")


@cases_app.command("clone")
def cases_clone(
    case_ref: str = typer.Argument(..., help="Source case name or path."),
    new_name: str = typer.Argument(..., help="New case folder name."),
) -> None:
    """Clone a case into the same parent directory with a new name."""
    try:
        source_case = _resolve_case_reference(case_ref)
    except ValueError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    target_case = source_case.parent / new_name
    if target_case.exists():
        console.print(f"[red]Error:[/red] Target already exists: {target_case}")
        raise typer.Exit(code=1)

    shutil.copytree(source_case, target_case)
    _save_active_case(target_case)
    console.print(f"[green]Cloned case:[/green] {target_case}")


@app.command("current")
def current_alias() -> None:
    """Alias for `cases current`."""
    cases_current()


@app.command("use")
def use_alias(case_ref: str = typer.Argument(..., help="Case name or path.")) -> None:
    """Alias for `cases use`."""
    cases_use(case_ref)


@app.command("open")
def open_alias(case_ref: str | None = typer.Argument(None, help="Optional case name or path.")) -> None:
    """Alias for `cases open`."""
    cases_open(case_ref)


@app.command()
def init(
    challenge_name: str | None = typer.Option(None, "--name", "-n", help="Raw challenge name."),
    artifacts: Path | None = typer.Option(None, "--artifacts", help="Artifacts path (file or directory)."),
    title: str | None = typer.Option(None, "--title", help="Human-readable challenge title."),
    context: str | None = typer.Option(None, "--context", help="Initial case context."),
    base_path: Path | None = typer.Option(
        None,
        "--base-path",
        help="Directory where the case folder will be created.",
    ),
) -> None:
    """Initialize a complete case workspace from artifacts."""
    interactive_mode = challenge_name is None or artifacts is None or title is None

    if challenge_name is None or not challenge_name.strip():
        challenge_name = typer.prompt("Challenge name")

    if artifacts is None:
        artifacts = Path(typer.prompt("Artifacts path (file or directory)")).expanduser()

    if title is None:
        title = typer.prompt("Case title")

    if context is None:
        if interactive_mode:
            context = typer.prompt("Initial case context (optional)", default="", show_default=False)
        else:
            context = ""

    if base_path is None:
        if interactive_mode:
            base_path = Path(typer.prompt("Base path", default=".", show_default=True)).expanduser()
        else:
            base_path = Path(".")

    try:
        case_root = initialize_case_from_artifacts(
            base_path=base_path.resolve(),
            challenge_name=challenge_name,
            artifacts_path=artifacts.resolve(),
            title=title,
            context=context,
            evidence_mode="legacy-copy",
        )
    except (FileNotFoundError, FileExistsError, ValueError) as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    console.print(f"[green]Initialized case:[/green] {case_root}")
    _save_active_case(case_root)
    console.print(f"[cyan]Active project:[/cyan] {case_root}")


@app.command("new")
def new_case(
    challenge_name: str | None = typer.Option(None, "--name", "-n", help="Raw challenge name."),
    artifacts: Path | None = typer.Option(None, "--artifacts", help="Artifacts path (file or directory)."),
    title: str | None = typer.Option(None, "--title", help="Human-readable challenge title."),
    context: str | None = typer.Option(None, "--context", help="Initial case context."),
    base_path: Path | None = typer.Option(None, "--base-path", help="Workspace root directory."),
    evidence_mode: str | None = typer.Option(
        None,
        "--evidence-mode",
        help="reference-only | lightweight-copy | full-copy",
    ),
) -> None:
    """Create a new case with safer defaults and evidence-mode options."""
    interactive_mode = challenge_name is None or artifacts is None or title is None

    if challenge_name is None or not challenge_name.strip():
        challenge_name = typer.prompt("Challenge name")

    if artifacts is None:
        artifacts = Path(typer.prompt("Artifacts path (file or directory)")).expanduser()

    if title is None:
        title = typer.prompt("Case title")

    if context is None:
        if interactive_mode:
            context = typer.prompt("Initial case context (optional)", default="", show_default=False)
        else:
            context = ""

    if base_path is None:
        if interactive_mode:
            base_path = Path(typer.prompt("Workspace base path", default=".", show_default=True)).expanduser()
        else:
            base_path = Path(".")

    selected_mode = (evidence_mode or "").strip().lower()
    if not selected_mode:
        if interactive_mode:
            console.print("Evidence mode options: reference-only, lightweight-copy, full-copy")
            selected_mode = typer.prompt("Evidence mode", default="reference-only").strip().lower()
        else:
            selected_mode = "reference-only"

    if selected_mode not in {"reference-only", "lightweight-copy", "full-copy"}:
        console.print("[red]Error:[/red] Invalid evidence mode. Use reference-only, lightweight-copy, or full-copy.")
        raise typer.Exit(code=1)

    if selected_mode == "full-copy" and artifacts.is_dir():
        file_count = len([path for path in artifacts.rglob("*") if path.is_file()])
        if file_count > 1000:
            console.print("[yellow]Warning:[/yellow] Full copy requested for a large directory.")

    try:
        case_root = initialize_case_from_artifacts(
            base_path=base_path.resolve(),
            challenge_name=challenge_name,
            artifacts_path=artifacts.resolve(),
            title=title,
            context=context,
            evidence_mode=selected_mode,
        )
    except (FileNotFoundError, FileExistsError, ValueError) as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    console.print(f"[green]Created case:[/green] {case_root}")
    console.print(f"[cyan]Evidence mode:[/cyan] {selected_mode}")
    _save_active_case(case_root)
    console.print(f"[cyan]Active project:[/cyan] {case_root}")


@app.command("check")
def check_case(
    case_path: Path | None = typer.Argument(None, help="Path to case workspace (optional if project is active)."),
) -> None:
    """Product alias for `validate`."""
    validate(case_path)


@app.command("inspect")
def inspect_case(
    case_path: Path | None = typer.Argument(None, help="Path to case workspace (optional if project is active)."),
) -> None:
    """Product alias for `classify`."""
    classify(case_path)


@app.command("run")
def run_case(
    case_path: Path | None = typer.Argument(None, help="Path to case workspace (optional if project is active)."),
    no_launch: bool = typer.Option(False, "--no-launch", help="Prepare context without launching Codex CLI."),
) -> None:
    """Product alias for `solve`."""
    solve(case_path, no_launch=no_launch)


@app.command("info")
def info_case(
    case_path: Path | None = typer.Argument(None, help="Path to case workspace (optional if project is active)."),
) -> None:
    """Product alias for `status`."""
    status(case_path)


@app.command("report")
def report_case(
    case_path: Path | None = typer.Argument(None, help="Path to case workspace (optional if project is active)."),
    allow_incomplete: bool = typer.Option(
        False,
        "--allow-incomplete",
        help="Generate a clearly marked incomplete final writeup when case is not solved.",
    ),
) -> None:
    """Product alias for `finalize`."""
    finalize(case_path, allow_incomplete=allow_incomplete)


@app.command()
def validate(
    case_path: Path | None = typer.Argument(None, help="Path to case workspace (optional if project is active)."),
) -> None:
    """Validate case workspace structure and metadata."""
    resolved_case_path = _resolve_case_path(case_path, "validate")
    report = validate_case_structure(resolved_case_path)

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
def classify(
    case_path: Path | None = typer.Argument(None, help="Path to case workspace (optional if project is active)."),
) -> None:
    """Classify a case and propose initial analysis direction."""
    resolved_case_path = _resolve_case_path(case_path, "classify")
    try:
        outcome = classify_case(resolved_case_path)
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
    case_path: Path | None = typer.Argument(None, help="Path to case workspace (optional if project is active)."),
    no_launch: bool = typer.Option(False, "--no-launch", help="Prepare solve context without launching Codex CLI."),
) -> None:
    """Prepare and launch Codex CLI for case solving."""
    resolved_case_path = _resolve_case_path(case_path, "solve")
    try:
        outcome = prepare_and_launch_solve(
            resolved_case_path,
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
def status(
    case_path: Path | None = typer.Argument(None, help="Path to case workspace (optional if project is active)."),
) -> None:
    """Show a concise operational status for a case."""
    resolved_case_path = _resolve_case_path(case_path, "status")
    try:
        snapshot = get_case_status(resolved_case_path)
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
    case_path: Path | None = typer.Argument(None, help="Path to case workspace (optional if project is active)."),
    allow_incomplete: bool = typer.Option(
        False,
        "--allow-incomplete",
        help="Generate a clearly marked incomplete final writeup when case is not solved.",
    ),
) -> None:
    """Generate final writeup from accumulated case documentation."""
    resolved_case_path = _resolve_case_path(case_path, "finalize")
    try:
        outcome = finalize_case(resolved_case_path, allow_incomplete=allow_incomplete)
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
    if apply:
        console.print("[yellow]Applying system install commands for missing tools...[/yellow]")
    else:
        console.print("[cyan]Dry-run mode:[/cyan] no install commands are executed.")

    try:
        results = install_profile(profile, apply=apply)
    except ValueError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    failures = 0
    pending = 0
    for result in results:
        if result.success:
            console.print(f"- {result.name}: [green]OK[/green] ({result.message})")
            continue

        if apply:
            failures += 1
        else:
            pending += 1
        console.print(f"- {result.name}: [yellow]PENDING[/yellow] ({result.message})")
        if result.command:
            console.print(f"    command: {result.command}")

    if apply and failures > 0:
        raise typer.Exit(code=1)
    if not apply and pending > 0:
        console.print("[bold]Tip:[/bold] Run again with [cyan]--apply[/cyan] to execute suggested commands.")


if __name__ == "__main__":
    app()

import json
import os
import shutil
import sys
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
console = Console(width=200) if os.getenv("GITHUB_ACTIONS") else Console()
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
recipe_app = typer.Typer(
    no_args_is_help=True,
    help="Run compact analysis recipes that generate report files.",
)
app.add_typer(project_app, name="project")
app.add_typer(cases_app, name="cases")
app.add_typer(tools_app, name="tools")
app.add_typer(recipe_app, name="recipe")


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


def _is_nonempty_file(path: Path) -> bool:
    return path.is_file() and bool(path.read_text(encoding="utf-8").strip())


def _read_settings() -> dict[str, str]:
    settings_file = _settings_file()
    if not settings_file.is_file():
        return {}

    try:
        payload = yaml.safe_load(settings_file.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return {}

    if not isinstance(payload, dict):
        return {}

    output: dict[str, str] = {}
    for key, value in payload.items():
        if isinstance(key, str) and isinstance(value, str):
            output[key] = value
    return output


def _compute_progress(case_path: Path) -> tuple[int, list[str], list[str]]:
    checks: list[tuple[str, bool]] = []
    checks.append(("case created", case_path.is_dir()))

    active_case = _read_active_case()
    checks.append(("active case registered", active_case is not None and active_case == case_path.resolve()))
    checks.append(("manifest generated", (case_path / "challenge" / "manifest.json").is_file()))
    checks.append(("hashes generated", (case_path / "challenge" / "hashes.json").is_file()))

    profile_selected = False
    case_yaml = case_path / "case.yaml"
    if case_yaml.is_file():
        try:
            case_payload = yaml.safe_load(case_yaml.read_text(encoding="utf-8"))
            profile_value = case_payload.get("profile") if isinstance(case_payload, dict) else None
            profile_selected = isinstance(profile_value, str) and bool(profile_value.strip())
        except yaml.YAMLError:
            profile_selected = False
    checks.append(("profile selected", profile_selected))

    commands_log = case_path / "meta" / "commands.log"
    tool_profile_checked = False
    if commands_log.is_file():
        text = commands_log.read_text(encoding="utf-8").lower()
        tool_profile_checked = "tools check" in text or "setup" in text
    checks.append(("tool profile checked", tool_profile_checked))

    checks.append(("compact context generated", _is_nonempty_file(case_path / "agent" / "context.md")))

    reports_dir = case_path / "work" / "reports"
    has_report = reports_dir.is_dir() and any(path.is_file() for path in reports_dir.rglob("*"))
    checks.append(("at least one report generated", has_report))

    checks.append(("log updated", _is_nonempty_file(case_path / "memory" / "log.md")))
    checks.append(("candidate flag found", _is_nonempty_file(case_path / "output" / "final_flag.txt")))
    checks.append(("writeup generated", _is_nonempty_file(case_path / "output" / "writeup.md")))
    checks.append(("writeup_final generated", _is_nonempty_file(case_path / "output" / "writeup_final.md")))

    completed = [label for label, passed in checks if passed]
    pending = [label for label, passed in checks if not passed]
    score = int(round((len(completed) / len(checks)) * 100)) if checks else 0
    return score, completed, pending


def _compute_next_action(case_path: Path) -> str:
    state_path = case_path / "meta" / "solution_state.json"
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            status = (state.get("status") or "").strip().lower()
        except json.JSONDecodeError:
            status = ""
    else:
        status = ""

    if status in {"initialized", "new"}:
        return "Case initialized. Run [cyan]bluebox inspect[/cyan] next."
    if status == "classified":
        return "Case classified. Run [cyan]bluebox run --no-launch[/cyan] to prepare solving context."
    if status == "solving":
        return "Solving in progress. Run [cyan]bluebox info[/cyan] and keep [cyan]memory/log.md[/cyan] updated."
    if status == "solved":
        return "Flag candidate found. Run [cyan]bluebox report[/cyan] to generate final writeup."
    if status == "finalized":
        return "Case already finalized. Review [cyan]output/writeup_final.md[/cyan] and export if needed."

    if not (case_path / "challenge" / "manifest.json").is_file():
        return "Missing challenge manifest. Recreate case or re-run [cyan]bluebox new[/cyan]."
    if not (case_path / "challenge" / "hashes.json").is_file():
        return "Missing hashes. Recreate evidence metadata before analysis."
    if not _is_nonempty_file(case_path / "agent" / "context.md"):
        return "Context is empty. Run [cyan]bluebox inspect[/cyan] to seed investigation direction."
    if not any((case_path / "work" / "reports").glob("*.md")):
        return "No reports yet. Run analysis and summarize outputs into [cyan]work/reports/[/cyan]."
    if not _is_nonempty_file(case_path / "output" / "final_flag.txt"):
        return "No flag candidate yet. Continue investigation and update [cyan]output/final_flag.txt[/cyan]."
    if not _is_nonempty_file(case_path / "output" / "writeup_final.md"):
        return "Generate polished output with [cyan]bluebox report[/cyan]."

    return "Workflow looks complete. Run [cyan]bluebox info[/cyan] for a final operational check."


def _reports_count(case_path: Path) -> int:
    reports_dir = case_path / "work" / "reports"
    if not reports_dir.is_dir():
        return 0
    return len([path for path in reports_dir.rglob("*") if path.is_file()])


def _read_memory_tail(case_path: Path, max_lines: int = 8) -> list[str]:
    memory_log = case_path / "memory" / "log.md"
    if not memory_log.is_file():
        return []

    lines = [line.rstrip() for line in memory_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    return lines[-max_lines:]


def _build_case_summary_text(case_path: Path) -> str:
    snapshot = get_case_status(case_path)
    score, completed, pending = _compute_progress(case_path)
    recommendation = _compute_next_action(case_path)
    reports_count = _reports_count(case_path)
    memory_tail = _read_memory_tail(case_path, max_lines=6)

    sections = [
        f"Case: {snapshot.case_name}",
        f"Title: {snapshot.title}",
        f"Status: {snapshot.status}",
        f"Category: {snapshot.category or 'unclassified'}",
        f"Artifacts: {snapshot.artifact_count}",
        f"Reports: {reports_count}",
        f"Progress: {score}%",
        f"Completed: {', '.join(completed[:6]) if completed else 'none'}",
        f"Pending: {', '.join(pending[:6]) if pending else 'none'}",
        f"Next: {recommendation}",
    ]

    if memory_tail:
        sections.append("Recent log:")
        sections.extend(f"- {line}" for line in memory_tail)

    return "\n".join(sections)


def _write_tooling_status_report(
    profile: str,
    results: list,
    *,
    apply: bool,
) -> Path | None:
    active_case = _read_active_case()
    if active_case is None or not _is_case_workspace(active_case):
        return None

    available: list[str] = []
    missing: list[str] = []
    for result in results:
        if result.success:
            available.append(result.name)
        else:
            missing.append(result.name)

    lines = [
        f"# Tooling Status - {profile}",
        "",
        f"- Mode: {'apply' if apply else 'dry-run'}",
        f"- Generated at: {datetime.now(UTC).isoformat().replace('+00:00', 'Z')}",
        "",
        "## Available",
    ]
    lines.extend([f"- {name}" for name in available] or ["- none"])
    lines.append("")
    lines.append("## Missing")
    lines.extend([f"- {name}" for name in missing] or ["- none"])

    report_path = active_case / "work" / "reports" / "tooling_status.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def _iter_case_artifact_files(case_path: Path) -> list[Path]:
    manifest_path = case_path / "challenge" / "manifest.json"
    if not manifest_path.is_file():
        return []

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    source_root_value = payload.get("source_path")
    artifacts = payload.get("artifacts", [])
    if not isinstance(source_root_value, str) or not isinstance(artifacts, list):
        return []

    source_root = Path(source_root_value).expanduser()
    files: list[Path] = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        rel_path = artifact.get("path")
        if not isinstance(rel_path, str) or not rel_path:
            continue

        candidate = (source_root / rel_path).resolve()
        if candidate.is_file():
            files.append(candidate)
            continue

        fallback = (case_path / "original" / rel_path).resolve()
        if fallback.is_file():
            files.append(fallback)

    return files


def _write_recipe_report(case_path: Path, file_name: str, content: str) -> Path:
    reports_dir = case_path / "work" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / file_name
    report_path.write_text(content if content.endswith("\n") else f"{content}\n", encoding="utf-8")
    return report_path


def _render_recipe_report(
    *,
    recipe_name: str,
    case_path: Path,
    title: str,
    selected_files: list[Path],
    notes: list[str],
) -> str:
    lines = [
        f"# {title}",
        "",
        f"- Recipe: `{recipe_name}`",
        f"- Case: `{case_path.name}`",
        f"- Generated at: `{datetime.now(UTC).isoformat().replace('+00:00', 'Z')}`",
        "",
        "## Candidate artifacts",
    ]
    if selected_files:
        lines.extend([f"- `{path}`" for path in selected_files[:50]])
    else:
        lines.append("- none detected")

    lines.append("")
    lines.append("## Notes")
    lines.extend([f"- {note}" for note in notes] if notes else ["- No additional notes."])
    lines.append("")
    lines.append("## Next action")
    lines.append(f"- {_compute_next_action(case_path)}")
    return "\n".join(lines)


def _run_recipe(case_path: Path, recipe_name: str) -> Path:
    artifacts = _iter_case_artifact_files(case_path)
    lower_name = recipe_name.strip().lower()

    if lower_name == "pcap-overview":
        selected = [path for path in artifacts if path.suffix.lower() in {".pcap", ".pcapng"}]
        content = _render_recipe_report(
            recipe_name=lower_name,
            case_path=case_path,
            title="PCAP Overview",
            selected_files=selected,
            notes=[
                "Focus on DNS, HTTP, and unusual beaconing intervals.",
                "If `tshark` is installed, add protocol and endpoint counts.",
            ],
        )
        return _write_recipe_report(case_path, "pcap_summary.md", content)

    if lower_name == "evtx-overview":
        selected = [path for path in artifacts if path.suffix.lower() == ".evtx"]
        content = _render_recipe_report(
            recipe_name=lower_name,
            case_path=case_path,
            title="EVTX Overview",
            selected_files=selected,
            notes=[
                "Prioritize security, Sysmon, and PowerShell-related channels.",
                "If Chainsaw/Hayabusa is available, record top suspicious detections.",
            ],
        )
        return _write_recipe_report(case_path, "evtx_summary.md", content)

    if lower_name == "metadata-scan":
        selected = artifacts
        content = _render_recipe_report(
            recipe_name=lower_name,
            case_path=case_path,
            title="Metadata Scan",
            selected_files=selected,
            notes=[
                "Extract high-signal metadata first (timestamps, authors, tooling hints).",
                "Use compact findings and avoid raw-dump style notes.",
            ],
        )
        return _write_recipe_report(case_path, "metadata_summary.md", content)

    if lower_name == "strings-triage":
        selected = [
            path
            for path in artifacts
            if path.suffix.lower() in {".bin", ".exe", ".dll", ".dat", ".elf", ".so", ".txt", ".log"}
        ]
        content = _render_recipe_report(
            recipe_name=lower_name,
            case_path=case_path,
            title="Strings Triage",
            selected_files=selected,
            notes=[
                "Search for URLs, domains, file paths, and command fragments.",
                "Promote only confirmed high-signal hits into agent/context.md.",
            ],
        )
        return _write_recipe_report(case_path, "strings_hotspots.md", content)

    if lower_name == "quick-yara-scan":
        selected = artifacts
        content = _render_recipe_report(
            recipe_name=lower_name,
            case_path=case_path,
            title="Quick YARA Scan",
            selected_files=selected,
            notes=[
                "Run only curated rule sets to keep output manageable.",
                "Store noisy raw output outside context and summarize key matches only.",
            ],
        )
        return _write_recipe_report(case_path, "yara_quick_scan.md", content)

    raise ValueError(f"Unknown recipe: {recipe_name}")


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
def wizard(
    base_path: Path = typer.Option(Path("."), "--base-path", help="Workspace root for folder bootstrap."),
    create_case: bool = typer.Option(False, "--create-case", help="Create a case during wizard flow."),
    import_source: Path | None = typer.Option(None, "--import-source", help="Optional challenge file/dir to import into inbox."),
    import_name: str | None = typer.Option(None, "--import-name", help="Optional inbox folder/file name for imported challenge."),
    challenge_name: str | None = typer.Option(None, "--name", help="Challenge name when --create-case is used."),
    artifacts: Path | None = typer.Option(None, "--artifacts", help="Artifacts path when --create-case is used."),
    title: str | None = typer.Option(None, "--title", help="Case title when --create-case is used."),
    context: str | None = typer.Option(None, "--context", help="Initial case context."),
    evidence_mode: str = typer.Option("reference-only", "--evidence-mode", help="reference-only | lightweight-copy | full-copy"),
) -> None:
    """Run onboarding wizard: verify environment, bootstrap folders, and optionally create a case."""
    resolved_base = base_path.expanduser().resolve()
    resolved_base.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold]Wizard[/bold] workspace: {resolved_base}")
    console.print(f"- Python: {sys.version.split()[0]}")

    package_manager = "none"
    for candidate in ("brew", "apt", "winget", "choco"):
        if shutil.which(candidate):
            package_manager = candidate
            break
    console.print(f"- Package manager: {package_manager}")

    for folder_name in (".bluebox", "inbox", "cases", "exports", "profiles"):
        folder_path = resolved_base / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)
        console.print(f"- ensured: {folder_path}")

    imported_artifacts: Path | None = None
    if import_source is not None:
        resolved_import_source = import_source.expanduser().resolve()
        if not resolved_import_source.exists():
            console.print(f"[red]Error:[/red] Import source not found: {resolved_import_source}")
            raise typer.Exit(code=1)

        inbox_dir = resolved_base / "inbox"
        target_name = (import_name or resolved_import_source.name).strip()
        if not target_name:
            target_name = "challenge-import"
        destination = inbox_dir / target_name

        if destination.exists():
            console.print(f"[red]Error:[/red] Import target already exists: {destination}")
            raise typer.Exit(code=1)

        if resolved_import_source.is_dir():
            shutil.copytree(resolved_import_source, destination)
        else:
            shutil.copy2(resolved_import_source, destination)
        imported_artifacts = destination
        console.print(f"- imported challenge to: {destination}")

    current_dir = Path.cwd()
    try:
        os_changed = False
        if current_dir != resolved_base:
            os_changed = True
            import os

            os.chdir(resolved_base)
        _ensure_settings_file()
        if os_changed:
            os.chdir(current_dir)
    except Exception:
        if Path.cwd() != current_dir:
            import os

            os.chdir(current_dir)
        raise

    if create_case:
        selected_name = challenge_name or typer.prompt("Challenge name")
        selected_artifacts = artifacts
        if selected_artifacts is None and imported_artifacts is not None:
            selected_artifacts = imported_artifacts
        if selected_artifacts is None:
            selected_artifacts = Path(typer.prompt("Artifacts path (file or directory)")).expanduser()
        selected_title = title or typer.prompt("Case title")
        selected_context = context if context is not None else typer.prompt(
            "Initial case context (optional)", default="", show_default=False
        )

        try:
            case_root = initialize_case_from_artifacts(
                base_path=resolved_base,
                challenge_name=selected_name,
                artifacts_path=selected_artifacts.expanduser().resolve(),
                title=selected_title,
                context=selected_context,
                evidence_mode=evidence_mode,
            )
        except (FileNotFoundError, FileExistsError, ValueError) as error:
            console.print(f"[red]Error:[/red] {error}")
            raise typer.Exit(code=1) from error

        previous_cwd = Path.cwd()
        try:
            import os

            os.chdir(resolved_base)
            _save_active_case(case_root)
        finally:
            import os

            os.chdir(previous_cwd)

        console.print(f"\n[green]Case created successfully:[/green] {case_root}")
    else:
        console.print("\n[yellow]No case created.[/yellow] Re-run with [cyan]--create-case[/cyan] to create one now.")

    console.print("\n[bold]Recommended next steps:[/bold]")
    console.print("1. [cyan]bluebox info[/cyan]")
    console.print("2. [cyan]bluebox inspect[/cyan]")
    console.print("3. [cyan]bluebox run --no-launch[/cyan]")
    console.print("4. [cyan]bluebox next[/cyan]")


@app.command("next")
def next_action(
    case_path: Path | None = typer.Argument(None, help="Path to case workspace (optional if project is active)."),
) -> None:
    """Suggest the next best action based on current case state."""
    if case_path is None:
        candidate = _read_active_case()
        if candidate is None:
            console.print("[yellow]No active case detected.[/yellow]")
            console.print("Next step: run [cyan]bluebox new[/cyan] or [cyan]bluebox wizard --create-case[/cyan].")
            return
        resolved_case = candidate
    else:
        resolved_case = case_path.expanduser().resolve()

    if not _is_case_workspace(resolved_case):
        console.print(f"[red]Error:[/red] Not a valid case workspace: {resolved_case}")
        raise typer.Exit(code=1)

    recommendation = _compute_next_action(resolved_case)
    console.print(f"[bold]Case:[/bold] {resolved_case}")
    console.print(f"[bold]Next:[/bold] {recommendation}")


@app.command()
def setup(
    mode: str | None = typer.Option(
        None,
        "--mode",
        help="Setup mode: 'all' (all profiles), 'profile' (one profile), or 'tool' (single tool).",
    ),
    tool: str | None = typer.Option(
        None,
        "--tool",
        help="Tool name when mode is 'tool'.",
    ),
    profile: str | None = typer.Option(
        None,
        "--profile",
        help="Profile name shortcut (equivalent to --mode all for 'all', otherwise installs one profile).",
    ),
    apply: bool = typer.Option(False, "--apply", help="Execute install commands instead of dry-run."),
) -> None:
    """Run initial setup: install all tool profiles or one specific tool."""
    selected_mode = (mode or "").strip().lower()
    selected_profile = (profile or "").strip().lower()

    if not selected_mode and selected_profile:
        selected_mode = "all" if selected_profile == "all" else "profile"

    if not selected_mode:
        console.print("[bold]Setup options:[/bold]")
        console.print("1) Install all profiles")
        console.print("2) Install one specific profile")
        console.print("3) Install one specific tool")
        option = typer.prompt("Choose option", default="1")
        normalized_option = option.strip()
        if normalized_option == "1":
            selected_mode = "all"
        elif normalized_option == "2":
            selected_mode = "profile"
        else:
            selected_mode = "tool"

    if selected_mode not in {"all", "profile", "tool"}:
        console.print("[red]Error:[/red] Invalid mode. Use --mode all, --mode profile, or --mode tool.")
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

    if selected_mode == "profile":
        if not selected_profile:
            selected_profile = typer.prompt("Profile name").strip().lower()
        console.print(f"[bold]Setup mode:[/bold] install profile [cyan]{selected_profile}[/cyan]")
        try:
            results = install_profile(selected_profile, apply=apply)
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

        report_path = _write_tooling_status_report(selected_profile, results, apply=apply)
        if report_path is not None:
            console.print(f"[cyan]Tooling report saved:[/cyan] {report_path}")

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
    no_launch: bool = typer.Option(False, "--no-launch", help="Prepare context without launching Agent CLI."),
) -> None:
    """Product alias for `solve`."""
    solve(case_path, no_launch=no_launch)


@app.command("info")
def info_case(
    case_path: Path | None = typer.Argument(None, help="Path to case workspace (optional if project is active)."),
) -> None:
    """Show enriched operational status and progress score."""
    resolved_case_path = _resolve_case_path(case_path, "info")
    try:
        snapshot = get_case_status(resolved_case_path)
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    score, completed, pending = _compute_progress(resolved_case_path)
    recommendation = _compute_next_action(resolved_case_path)
    settings = _read_settings()
    reports_count = _reports_count(resolved_case_path)

    console.print(f"[bold]Case:[/bold] {snapshot.case_name}")
    console.print(f"[bold]Title:[/bold] {snapshot.title}")
    console.print(f"[bold]Status:[/bold] {snapshot.status}")
    console.print(f"[bold]Category:[/bold] {snapshot.category or 'unclassified'}")
    console.print(f"[bold]Reports:[/bold] {reports_count}")
    console.print(f"[bold]Artifacts:[/bold] {snapshot.artifact_count}")
    console.print(f"[bold]Active hypotheses:[/bold] {snapshot.active_hypotheses_count}")
    console.print(f"[bold]Latest update:[/bold] {snapshot.latest_update or 'none'}")
    console.print(f"[bold]Progress:[/bold] {score}%")
    console.print(f"[bold]Completed:[/bold] {', '.join(completed[:5]) if completed else 'none'}")
    console.print(f"[bold]Pending:[/bold] {', '.join(pending[:5]) if pending else 'none'}")
    if settings:
        console.print(f"[bold]Active tool profile:[/bold] {settings.get('default_profile', 'n/a')}")
    console.print(f"[bold]Next action:[/bold] {recommendation}")


@app.command()
def home() -> None:
    """Show a compact dashboard for active case and workspace state."""
    active_case = _read_active_case()
    recent_cases = _read_recent_cases()[:5]
    settings = _read_settings()
    report = build_doctor_report()
    missing_tools = [check.name for check in report.checks if not check.available]

    console.print("[bold]BlueBox Home[/bold]")
    if active_case is None:
        console.print("[bold]Active case:[/bold] none")
        console.print("[bold]Suggested next:[/bold] [cyan]bluebox new[/cyan]")
    else:
        console.print(f"[bold]Active case:[/bold] {active_case}")
        if _is_case_workspace(active_case):
            score, _, _ = _compute_progress(active_case)
            console.print(f"[bold]Progress:[/bold] {score}%")
            console.print(f"[bold]Suggested next:[/bold] {_compute_next_action(active_case)}")

    if recent_cases:
        console.print("[bold]Recent cases:[/bold]")
        for entry in recent_cases:
            console.print(f"- {entry['name']} ({entry['used_at'] or 'unknown'})")
    else:
        console.print("[bold]Recent cases:[/bold] none")

    console.print(f"[bold]Current profile:[/bold] {settings.get('default_profile', 'minimal') if settings else 'minimal'}")
    if missing_tools:
        console.print(f"[bold]Tool health:[/bold] missing {', '.join(missing_tools)}")
    else:
        console.print("[bold]Tool health:[/bold] all core checks available")


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
def handoff(
    case_path: Path | None = typer.Argument(None, help="Path to case workspace (optional if project is active)."),
    write: bool = typer.Option(True, "--write/--no-write", help="Write summary into agent/handoff.md."),
) -> None:
    """Generate concise handoff summary for the current case."""
    resolved_case_path = _resolve_case_path(case_path, "handoff")
    if not _is_case_workspace(resolved_case_path):
        console.print(f"[red]Error:[/red] Not a valid case workspace: {resolved_case_path}")
        raise typer.Exit(code=1)

    summary_text = _build_case_summary_text(resolved_case_path)
    console.print(summary_text)

    if write:
        handoff_path = resolved_case_path / "agent" / "handoff.md"
        handoff_path.parent.mkdir(parents=True, exist_ok=True)
        content = f"# Handoff\n\n{summary_text}\n"
        handoff_path.write_text(content, encoding="utf-8")
        console.print(f"[green]Updated handoff:[/green] {handoff_path}")


@app.command("summary")
def summary_command(
    case_path: Path | None = typer.Argument(None, help="Path to case workspace (optional if project is active)."),
) -> None:
    """Produce compact human-readable case summary."""
    resolved_case_path = _resolve_case_path(case_path, "summary")
    if not _is_case_workspace(resolved_case_path):
        console.print(f"[red]Error:[/red] Not a valid case workspace: {resolved_case_path}")
        raise typer.Exit(code=1)

    console.print(_build_case_summary_text(resolved_case_path))


@app.command()
def summarize(
    source_path: Path = typer.Argument(..., help="Large file to summarize into a compact report."),
    case_path: Path | None = typer.Option(
        None,
        "--case-path",
        help="Case workspace (optional if project is active).",
    ),
    output_name: str | None = typer.Option(None, "--output-name", help="Custom output filename under work/reports."),
) -> None:
    """Turn large outputs into compact reports under work/reports/."""
    resolved_case_path = _resolve_case_path(case_path, "summarize")
    if not _is_case_workspace(resolved_case_path):
        console.print(f"[red]Error:[/red] Not a valid case workspace: {resolved_case_path}")
        raise typer.Exit(code=1)

    resolved_source = source_path.expanduser().resolve()
    if not resolved_source.is_file():
        console.print(f"[red]Error:[/red] Source file not found: {resolved_source}")
        raise typer.Exit(code=1)

    try:
        raw = resolved_source.read_bytes()
    except OSError as error:
        console.print(f"[red]Error:[/red] Unable to read source file: {error}")
        raise typer.Exit(code=1) from error

    report_name = output_name or f"{resolved_source.stem}_summary.md"
    if not report_name.lower().endswith(".md"):
        report_name = f"{report_name}.md"

    reports_dir = resolved_case_path / "work" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / report_name

    is_text = True
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        is_text = False
        text = ""

    lines = text.splitlines() if is_text else []
    head_lines = lines[:20]
    tail_lines = lines[-20:] if len(lines) > 20 else []

    report_content = [
        f"# Summary for `{resolved_source.name}`",
        "",
        f"- Source path: `{resolved_source}`",
        f"- Size bytes: `{len(raw)}`",
        f"- Text file: `{is_text}`",
        f"- Line count: `{len(lines) if is_text else 'n/a'}`",
        "",
    ]

    if is_text:
        report_content.append("## First lines")
        report_content.append("```")
        report_content.extend(head_lines if head_lines else ["(empty file)"])
        report_content.append("```")
        if tail_lines:
            report_content.append("")
            report_content.append("## Last lines")
            report_content.append("```")
            report_content.extend(tail_lines)
            report_content.append("```")
    else:
        report_content.append("Binary or non-UTF8 content. Use specialized tools and keep findings in this report.")

    report_path.write_text("\n".join(report_content) + "\n", encoding="utf-8")
    console.print(f"[green]Summary report created:[/green] {report_path}")


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
    no_launch: bool = typer.Option(False, "--no-launch", help="Prepare solve context without launching Agent CLI."),
) -> None:
    """Prepare and launch Agent CLI for case solving."""
    resolved_case_path = _resolve_case_path(case_path, "solve")
    try:
        outcome = prepare_and_launch_solve(
            resolved_case_path,
            launch_agent=not no_launch,
        )
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    console.print(f"[green]Prepared solve context:[/green] {outcome.context_path}")
    console.print(f"[green]Prepared solve prompt:[/green] {outcome.prompt_path}")

    if no_launch:
        console.print("[yellow]Agent launch skipped (--no-launch).[/yellow]")
    elif outcome.agent_return_code is not None:
        console.print(f"[cyan]Agent exit code:[/cyan] {outcome.agent_return_code}")


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


@tools_app.command("profiles")
def tools_profiles() -> None:
    """List profile names only (product-style quick view)."""
    for profile_name in list_profiles().keys():
        console.print(profile_name)


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
    available_tools: list[str] = []
    missing_tools: list[str] = []
    for result in results:
        if result.success:
            console.print(f"- {result.name}: [green]OK[/green] ({result.message})")
            available_tools.append(result.name)
            continue

        if apply:
            failures += 1
        else:
            pending += 1
        missing_tools.append(result.name)
        console.print(f"- {result.name}: [yellow]PENDING[/yellow] ({result.message})")
        if result.command:
            console.print(f"    command: {result.command}")

    console.print(f"\n[bold]Installed profile:[/bold] {profile}")
    console.print(f"[bold]Available:[/bold] {', '.join(available_tools) if available_tools else 'none'}")
    console.print(f"[bold]Missing:[/bold] {', '.join(missing_tools) if missing_tools else 'none'}")

    report_path = _write_tooling_status_report(profile, results, apply=apply)
    if report_path is not None:
        console.print(f"[bold]Report saved to:[/bold] {report_path}")

    if apply and failures > 0:
        raise typer.Exit(code=1)
    if not apply and pending > 0:
        console.print("[bold]Tip:[/bold] Run again with [cyan]--apply[/cyan] to execute suggested commands.")


@recipe_app.command("run")
def recipe_run(
    recipe_name: str = typer.Argument(..., help="Recipe name (pcap-overview, evtx-overview, metadata-scan, strings-triage, quick-yara-scan)."),
    case_path: Path | None = typer.Option(None, "--case-path", help="Case workspace (optional if project is active)."),
) -> None:
    """Run a compact recipe and write report output to work/reports/."""
    resolved_case = _resolve_case_path(case_path, "recipe run")
    if not _is_case_workspace(resolved_case):
        console.print(f"[red]Error:[/red] Not a valid case workspace: {resolved_case}")
        raise typer.Exit(code=1)

    try:
        report_path = _run_recipe(resolved_case, recipe_name)
    except ValueError as error:
        console.print(f"[red]Error:[/red] {error}")
        console.print("Hint: use one of pcap-overview, evtx-overview, metadata-scan, strings-triage, quick-yara-scan")
        raise typer.Exit(code=1) from error

    console.print(f"[green]Recipe report generated:[/green] {report_path}")


if __name__ == "__main__":
    app()

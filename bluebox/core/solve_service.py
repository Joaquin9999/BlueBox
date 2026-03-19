from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from .validation import validate_case_structure


@dataclass
class SolveOutcome:
    case_path: Path
    context_path: Path
    prompt_path: Path
    command_log_path: Path
    codex_return_code: int | None


def _utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _load_json_dict(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _extract_active_hypotheses(hypotheses_path: Path) -> list[str]:
    if not hypotheses_path.exists():
        return []

    active: list[str] = []
    in_active_section = False

    for raw_line in hypotheses_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            in_active_section = line.lower().startswith("## active")
            continue
        if in_active_section and line.startswith("- "):
            item = line[2:].strip()
            if item and item.lower() != "none yet.":
                active.append(item)

    return active


def _summarize_artifacts(inventory: dict[str, Any], limit: int = 15) -> list[str]:
    artifacts = inventory.get("artifacts", [])
    if not isinstance(artifacts, list):
        return []

    summary: list[str] = []
    for item in artifacts[:limit]:
        if isinstance(item, dict):
            path = str(item.get("path", "unknown"))
            size = item.get("size")
            if isinstance(size, int):
                summary.append(f"{path} ({size} bytes)")
            else:
                summary.append(path)
        elif isinstance(item, str):
            summary.append(item)

    return summary


def _repo_prompt_path() -> Path:
    package_prompt = Path(__file__).resolve().parents[1] / "prompts" / "codex_solver_prompt.txt"
    if package_prompt.exists():
        return package_prompt

    fallback_prompt = Path(__file__).resolve().parents[2] / "prompts" / "codex_solver_prompt.txt"
    if fallback_prompt.exists():
        return fallback_prompt

    raise FileNotFoundError("Solver prompt template not found.")


def _build_context_markdown(
    *,
    title: str,
    initial_context: str,
    category: str | None,
    subcategories: list[str],
    artifact_summary: list[str],
    active_hypotheses: list[str],
    current_state: str,
    timestamp: str,
) -> str:
    lines = [
        "# BlueBox Codex Context",
        "",
        f"- Generated at: {timestamp}",
        f"- Title: {title}",
        f"- Current state: {current_state}",
        f"- Category: {category or 'unclassified'}",
        f"- Subcategories: {', '.join(subcategories) if subcategories else 'none'}",
        "",
        "## Initial Context",
        initial_context or "No initial context provided.",
        "",
        "## Artifact Inventory Summary",
    ]

    if artifact_summary:
        lines.extend([f"- {item}" for item in artifact_summary])
    else:
        lines.append("- No artifacts listed in inventory.")

    lines.extend(["", "## Active Hypotheses"])
    if active_hypotheses:
        lines.extend([f"- {item}" for item in active_hypotheses])
    else:
        lines.append("- None currently listed.")

    return "\n".join(lines).rstrip() + "\n"


def _run_codex_cli(case_path: Path) -> int:
    if shutil.which("codex") is None:
        raise FileNotFoundError("Codex CLI not found in PATH.")

    process = subprocess.run(["codex"], cwd=case_path, check=False)
    return process.returncode


def prepare_and_launch_solve(
    case_path: Path,
    *,
    launch_codex: bool = True,
    codex_runner: Callable[[Path], int] | None = None,
) -> SolveOutcome:
    validation = validate_case_structure(case_path)
    if not validation.is_valid:
        joined_errors = "\n".join(validation.errors)
        raise ValueError(f"Case validation failed before solve:\n{joined_errors}")

    timestamp = _utc_timestamp()

    solution_state_path = case_path / "meta" / "solution_state.json"
    inventory_path = case_path / "meta" / "artifacts_inventory.json"
    hypotheses_path = case_path / "notes" / "hypotheses.md"

    solution_state = _load_json_dict(solution_state_path)
    inventory = _load_json_dict(inventory_path)

    title = str(solution_state.get("title", case_path.name))
    initial_context = str(solution_state.get("context", ""))
    category_value = solution_state.get("category")
    category = category_value if isinstance(category_value, str) else None

    raw_subcategories = solution_state.get("subcategories", [])
    subcategories = [item for item in raw_subcategories if isinstance(item, str)] if isinstance(raw_subcategories, list) else []

    current_state = str(solution_state.get("status", "initialized"))
    artifact_summary = _summarize_artifacts(inventory)
    active_hypotheses = _extract_active_hypotheses(hypotheses_path)

    context_markdown = _build_context_markdown(
        title=title,
        initial_context=initial_context,
        category=category,
        subcategories=subcategories,
        artifact_summary=artifact_summary,
        active_hypotheses=active_hypotheses,
        current_state=current_state,
        timestamp=timestamp,
    )

    codex_dir = case_path / ".codex"
    codex_dir.mkdir(parents=True, exist_ok=True)

    context_path = codex_dir / "context.md"
    context_path.write_text(context_markdown, encoding="utf-8")

    prompt_path = codex_dir / "prompt.txt"
    prompt_template_path = _repo_prompt_path()
    prompt_path.write_text(prompt_template_path.read_text(encoding="utf-8"), encoding="utf-8")

    solution_state["status"] = "solving"
    solution_state["updated_at"] = timestamp
    solution_state_path.write_text(json.dumps(solution_state, indent=2) + "\n", encoding="utf-8")

    command_log_path = case_path / "meta" / "commands.log"
    command_log_path.parent.mkdir(parents=True, exist_ok=True)
    command_log_path.write_text(
        command_log_path.read_text(encoding="utf-8") if command_log_path.exists() else "",
        encoding="utf-8",
    )
    with command_log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{timestamp} | solve | prepared codex context and prompt\n")

    codex_return_code: int | None = None
    if launch_codex:
        runner = codex_runner or _run_codex_cli
        codex_return_code = runner(case_path)
        with command_log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(f"{_utc_timestamp()} | solve | launched codex (exit={codex_return_code})\n")

    return SolveOutcome(
        case_path=case_path,
        context_path=context_path,
        prompt_path=prompt_path,
        command_log_path=command_log_path,
        codex_return_code=codex_return_code,
    )

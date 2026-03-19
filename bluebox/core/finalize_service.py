from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .validation import validate_case_structure

SOLVED_STATUSES = {"solved", "finalized"}


@dataclass
class FinalizeOutcome:
    case_path: Path
    output_path: Path
    generated_incomplete: bool


def _utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _load_json_dict(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").rstrip()


def _json_summary_lines(evidence_summary: dict[str, Any]) -> list[str]:
    summary = evidence_summary.get("summary", [])
    if isinstance(summary, list):
        output: list[str] = []
        for item in summary:
            if isinstance(item, str):
                output.append(item)
            elif isinstance(item, dict):
                output.append(json.dumps(item, ensure_ascii=False))
        return output
    return []


def _build_final_markdown(
    *,
    case_name: str,
    title: str,
    status: str,
    category: str | None,
    generated_at: str,
    writeup: str,
    findings: str,
    changelog: str,
    hypotheses: str,
    evidence_summary_lines: list[str],
    incomplete: bool,
) -> str:
    lines: list[str] = [
        f"# Final Writeup — {case_name}",
        "",
        f"- Generated at: {generated_at}",
        f"- Title: {title}",
        f"- Status at generation: {status}",
        f"- Category: {category or 'unclassified'}",
    ]

    if incomplete:
        lines.extend(
            [
                "",
                "> Incomplete final writeup: case status is not solved/finalized.",
            ]
        )

    lines.extend(["", "## Evidence Summary"])
    if evidence_summary_lines:
        lines.extend([f"- {entry}" for entry in evidence_summary_lines])
    else:
        lines.append("- No evidence summary entries documented.")

    lines.extend(["", "## Live Writeup (Source)", writeup or "(empty)"])
    lines.extend(["", "## Findings (Source)", findings or "(empty)"])
    lines.extend(["", "## Hypotheses (Source)", hypotheses or "(empty)"])
    lines.extend(["", "## Changelog (Source)", changelog or "(empty)"])

    return "\n".join(lines).rstrip() + "\n"


def finalize_case(case_path: Path, *, allow_incomplete: bool = False) -> FinalizeOutcome:
    validation = validate_case_structure(case_path)
    if not validation.is_valid:
        joined_errors = "\n".join(validation.errors)
        raise ValueError(f"Case validation failed before finalize:\n{joined_errors}")

    solution_state_path = case_path / "meta" / "solution_state.json"
    writeup_path = case_path / "notes" / "writeup.md"
    findings_path = case_path / "notes" / "findings.md"
    changelog_path = case_path / "notes" / "changelog.md"
    hypotheses_path = case_path / "notes" / "hypotheses.md"
    evidence_summary_path = case_path / "meta" / "evidence_summary.json"
    writeup_final_path = case_path / "notes" / "writeup_final.md"

    solution_state = _load_json_dict(solution_state_path)
    evidence_summary = _load_json_dict(evidence_summary_path)

    status = str(solution_state.get("status", "unknown"))
    is_solved = status in SOLVED_STATUSES

    if not is_solved and not allow_incomplete:
        raise ValueError(
            "Case is not solved. Refusing to finalize. "
            "Use --allow-incomplete to generate a clearly marked incomplete final writeup."
        )

    generated_at = _utc_timestamp()
    case_name = str(solution_state.get("case_name", case_path.name))
    title = str(solution_state.get("title", case_name))
    category = solution_state.get("category") if isinstance(solution_state.get("category"), str) else None

    final_markdown = _build_final_markdown(
        case_name=case_name,
        title=title,
        status=status,
        category=category,
        generated_at=generated_at,
        writeup=_read_text(writeup_path),
        findings=_read_text(findings_path),
        changelog=_read_text(changelog_path),
        hypotheses=_read_text(hypotheses_path),
        evidence_summary_lines=_json_summary_lines(evidence_summary),
        incomplete=not is_solved,
    )
    writeup_final_path.write_text(final_markdown, encoding="utf-8")

    if is_solved:
        solution_state["status"] = "finalized"
    solution_state["updated_at"] = generated_at
    solution_state_path.write_text(json.dumps(solution_state, indent=2) + "\n", encoding="utf-8")

    with changelog_path.open("a", encoding="utf-8") as changelog_file:
        if not changelog_path.read_text(encoding="utf-8").endswith("\n"):
            changelog_file.write("\n")
        if is_solved:
            changelog_file.write(f"- {generated_at}: Final writeup generated and case moved to 'finalized'.\n")
        else:
            changelog_file.write(f"- {generated_at}: Incomplete final writeup generated (case not solved).\n")

    return FinalizeOutcome(
        case_path=case_path,
        output_path=writeup_final_path,
        generated_incomplete=not is_solved,
    )

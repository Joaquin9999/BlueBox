from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .case_model import REQUIRED_CASE_DIRECTORIES, REQUIRED_CASE_FILES

ALLOWED_SOLUTION_STATUS: set[str] = {
    "initialized",
    "classified",
    "solving",
    "solved",
    "finalized",
}

REQUIRED_JSON_FILES: tuple[str, ...] = (
    "meta/solution_state.json",
    "meta/artifacts_inventory.json",
    "meta/hashes.json",
    "meta/evidence_summary.json",
)


@dataclass
class ValidationReport:
    case_path: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def _load_json(file_path: Path) -> dict[str, Any] | None:
    try:
        content = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return content if isinstance(content, dict) else None


def validate_case_structure(case_path: Path) -> ValidationReport:
    report = ValidationReport(case_path=case_path)

    if not case_path.exists():
        report.errors.append(f"Case path does not exist: {case_path}")
        return report

    if not case_path.is_dir():
        report.errors.append(f"Case path is not a directory: {case_path}")
        return report

    for relative_dir in REQUIRED_CASE_DIRECTORIES:
        target = case_path / relative_dir
        if not target.is_dir():
            report.errors.append(f"Missing required directory: {relative_dir}")

    for relative_file in REQUIRED_CASE_FILES:
        target = case_path / relative_file
        if not target.is_file():
            report.errors.append(f"Missing required file: {relative_file}")

    parsed_json: dict[str, dict[str, Any]] = {}
    for relative_json in REQUIRED_JSON_FILES:
        json_path = case_path / relative_json
        if not json_path.exists():
            continue

        parsed_content = _load_json(json_path)
        if parsed_content is None:
            report.errors.append(f"Invalid JSON file: {relative_json}")
            continue

        parsed_json[relative_json] = parsed_content

    solution_state = parsed_json.get("meta/solution_state.json")
    if solution_state is not None:
        status_value = solution_state.get("status")
        if status_value not in ALLOWED_SOLUTION_STATUS:
            report.errors.append(
                "Invalid solution status in meta/solution_state.json: "
                f"{status_value!r}. Allowed: {sorted(ALLOWED_SOLUTION_STATUS)}"
            )

    notes_path = case_path / "notes"
    if notes_path.exists() and not any(notes_path.iterdir()):
        report.warnings.append("Notes directory is empty.")

    return report

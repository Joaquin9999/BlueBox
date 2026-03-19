from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .validation import validate_case_structure


@dataclass
class CaseStatusSnapshot:
    case_name: str
    title: str
    status: str
    category: str | None
    artifact_count: int
    active_hypotheses_count: int
    latest_update: str | None


def _load_json_dict(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _count_active_hypotheses(hypotheses_path: Path) -> int:
    if not hypotheses_path.exists():
        return 0

    count = 0
    in_active = False

    for raw_line in hypotheses_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            in_active = line.lower().startswith("## active")
            continue
        if in_active and line.startswith("- "):
            value = line[2:].strip().lower()
            if value and value not in {"none", "none yet.", "none yet"}:
                count += 1

    return count


def _latest_update_from_changelog(changelog_path: Path) -> str | None:
    if not changelog_path.exists():
        return None

    entries = [line.strip() for line in changelog_path.read_text(encoding="utf-8").splitlines() if line.strip().startswith("-")]
    if not entries:
        return None
    return entries[-1][1:].strip()


def get_case_status(case_path: Path) -> CaseStatusSnapshot:
    validation = validate_case_structure(case_path)
    if not validation.is_valid:
        joined = "\n".join(validation.errors)
        raise ValueError(f"Case validation failed before status:\n{joined}")

    state = _load_json_dict(case_path / "meta" / "solution_state.json")
    inventory = _load_json_dict(case_path / "meta" / "artifacts_inventory.json")

    artifacts = inventory.get("artifacts", [])
    artifact_count = len(artifacts) if isinstance(artifacts, list) else 0

    return CaseStatusSnapshot(
        case_name=str(state.get("case_name", case_path.name)),
        title=str(state.get("title", case_path.name)),
        status=str(state.get("status", "unknown")),
        category=state.get("category") if isinstance(state.get("category"), str) else None,
        artifact_count=artifact_count,
        active_hypotheses_count=_count_active_hypotheses(case_path / "notes" / "hypotheses.md"),
        latest_update=_latest_update_from_changelog(case_path / "notes" / "changelog.md"),
    )

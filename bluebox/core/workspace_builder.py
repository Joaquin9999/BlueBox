from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from .case_model import CaseWorkspaceSpec, ensure_case_structure
from .template_renderer import render_case_templates


def ensure_workspace_layout(base_path: Path) -> None:
    for directory in (".bluebox", "inbox", "cases", "exports", "profiles", "tools"):
        (base_path / directory).mkdir(parents=True, exist_ok=True)


def create_case_workspace(base_path: Path, spec: CaseWorkspaceSpec) -> Path:
    ensure_workspace_layout(base_path)
    case_root = base_path / "cases" / spec.case_name
    ensure_case_structure(case_root)

    context = {
        "case_name": spec.case_name,
        "title": spec.title,
        "context": spec.context,
        "source_ref": "",
        "evidence_mode": "legacy-copy",
        "timestamp": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    render_case_templates(case_root=case_root, context=context)

    return case_root

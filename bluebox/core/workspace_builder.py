from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from .case_model import CaseWorkspaceSpec, ensure_case_structure
from .template_renderer import render_case_templates


def create_case_workspace(base_path: Path, spec: CaseWorkspaceSpec) -> Path:
    case_root = base_path / spec.case_name
    ensure_case_structure(case_root)

    context = {
        "case_name": spec.case_name,
        "title": spec.title,
        "context": spec.context,
        "timestamp": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    render_case_templates(case_root=case_root, context=context)

    return case_root

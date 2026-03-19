from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .case_model import REQUIRED_CASE_FILES


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def templates_root() -> Path:
    package_templates = Path(__file__).resolve().parents[1] / "templates" / "case"
    if package_templates.exists():
        return package_templates

    repository_templates = _repo_root() / "templates" / "case"
    if repository_templates.exists():
        return repository_templates

    raise FileNotFoundError("Could not locate case templates directory.")


def build_template_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(templates_root())),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_case_templates(case_root: Path, context: dict[str, Any]) -> None:
    environment = build_template_environment()
    for relative_path in REQUIRED_CASE_FILES:
        template = environment.get_template(relative_path)
        destination = case_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(template.render(**context).rstrip() + "\n", encoding="utf-8")

import json
from pathlib import Path

from typer.testing import CliRunner

from bluebox.cli.app import app
from bluebox.core import CaseWorkspaceSpec, create_case_workspace


runner = CliRunner()


def _build_case(tmp_path: Path) -> Path:
    spec = CaseWorkspaceSpec(
        raw_name="Validation Case",
        title="Validation Case",
        context="Validation",
    )
    case_root = create_case_workspace(tmp_path, spec)

    (case_root / "meta" / "solution_state.json").write_text(
        json.dumps(
            {
                "case_name": "validation-case",
                "title": "Validation Case",
                "status": "initialized",
                "category": None,
                "subcategories": [],
                "created_at": "2026-03-18T00:00:00+00:00",
                "updated_at": "2026-03-18T00:00:00+00:00",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return case_root


def test_validate_command_passes_for_valid_case(tmp_path: Path) -> None:
    case_root = _build_case(tmp_path)

    result = runner.invoke(app, ["validate", str(case_root)])

    assert result.exit_code == 0
    assert "Validation passed" in result.stdout


def test_validate_command_fails_for_missing_file(tmp_path: Path) -> None:
    case_root = _build_case(tmp_path)
    (case_root / "notes" / "findings.md").unlink()

    result = runner.invoke(app, ["validate", str(case_root)])

    assert result.exit_code == 1
    assert "Missing required file: notes/findings.md" in result.stdout


def test_validate_command_fails_for_invalid_json(tmp_path: Path) -> None:
    case_root = _build_case(tmp_path)
    (case_root / "meta" / "hashes.json").write_text("{invalid", encoding="utf-8")

    result = runner.invoke(app, ["validate", str(case_root)])

    assert result.exit_code == 1
    assert "Invalid JSON file: meta/hashes.json" in result.stdout


def test_validate_command_fails_for_invalid_status(tmp_path: Path) -> None:
    case_root = _build_case(tmp_path)
    invalid_state = {
        "case_name": "validation-case",
        "title": "Validation Case",
        "status": "unknown-state",
        "category": None,
        "subcategories": [],
        "created_at": "2026-03-18T00:00:00+00:00",
        "updated_at": "2026-03-18T00:00:00+00:00",
    }
    (case_root / "meta" / "solution_state.json").write_text(
        json.dumps(invalid_state, indent=2) + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["validate", str(case_root)])

    assert result.exit_code == 1
    assert "Invalid solution status" in result.stdout

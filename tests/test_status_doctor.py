from pathlib import Path

from typer.testing import CliRunner

from bluebox.cli.app import app


runner = CliRunner()


def _build_case_for_status(tmp_path: Path) -> Path:
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "events.log").write_text("event", encoding="utf-8")

    init_result = runner.invoke(
        app,
        [
            "init",
            "--name",
            "Status Case",
            "--artifacts",
            str(artifacts_dir),
            "--title",
            "Status Case",
            "--context",
            "Status context",
            "--base-path",
            str(tmp_path),
        ],
    )
    assert init_result.exit_code == 0

    case_root = tmp_path / "cases" / "status-case"

    classify_result = runner.invoke(app, ["classify", str(case_root)])
    assert classify_result.exit_code == 0

    return case_root


def test_status_command_outputs_expected_fields(tmp_path: Path) -> None:
    case_root = _build_case_for_status(tmp_path)

    result = runner.invoke(app, ["status", str(case_root)])

    assert result.exit_code == 0
    assert "Case:" in result.stdout
    assert "Title:" in result.stdout
    assert "Status:" in result.stdout
    assert "Category:" in result.stdout
    assert "Artifacts:" in result.stdout
    assert "Active hypotheses:" in result.stdout


def test_status_command_fails_for_invalid_case(tmp_path: Path) -> None:
    broken_case = tmp_path / "broken"
    broken_case.mkdir(parents=True, exist_ok=True)

    result = runner.invoke(app, ["status", str(broken_case)])

    assert result.exit_code == 1
    assert "Case validation failed before status" in result.stdout


def test_doctor_command_outputs_environment_checks() -> None:
    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "Python:" in result.stdout
    assert "Platform:" in result.stdout
    assert "uv:" in result.stdout
    assert "agent:" in result.stdout
    assert "git:" in result.stdout

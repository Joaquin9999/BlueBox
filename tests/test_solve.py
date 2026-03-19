import json
from pathlib import Path

from typer.testing import CliRunner

from bluebox.cli.app import app
from bluebox.core.solve_service import prepare_and_launch_solve


runner = CliRunner()


def _init_and_classify_case(tmp_path: Path) -> Path:
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "traffic.pcap").write_bytes(b"pcap")
    (artifacts_dir / "dns.log").write_text("dns", encoding="utf-8")

    init_result = runner.invoke(
        app,
        [
            "init",
            "--name",
            "Solve Case",
            "--artifacts",
            str(artifacts_dir),
            "--title",
            "Solve Case",
            "--context",
            "Initial solve context",
            "--base-path",
            str(tmp_path),
        ],
    )
    assert init_result.exit_code == 0

    case_root = tmp_path / "solve-case"

    classify_result = runner.invoke(app, ["classify", str(case_root)])
    assert classify_result.exit_code == 0

    return case_root


def test_solve_prepare_only_updates_files_and_state(tmp_path: Path) -> None:
    case_root = _init_and_classify_case(tmp_path)

    solve_result = runner.invoke(app, ["solve", str(case_root), "--no-launch"])

    assert solve_result.exit_code == 0
    assert "Prepared solve context" in solve_result.stdout

    context_path = case_root / ".codex" / "context.md"
    prompt_path = case_root / ".codex" / "prompt.txt"
    commands_log = case_root / "meta" / "commands.log"

    assert context_path.is_file()
    assert prompt_path.is_file()
    assert commands_log.is_file()

    context_content = context_path.read_text(encoding="utf-8")
    assert "BlueBox Codex Context" in context_content
    assert "Current state" in context_content

    state = json.loads((case_root / "meta" / "solution_state.json").read_text(encoding="utf-8"))
    assert state["status"] == "solving"


def test_solve_launch_uses_runner_hook(tmp_path: Path) -> None:
    case_root = _init_and_classify_case(tmp_path)

    outcome = prepare_and_launch_solve(
        case_root,
        launch_codex=True,
        codex_runner=lambda _: 0,
    )

    assert outcome.codex_return_code == 0

    commands_log = (case_root / "meta" / "commands.log").read_text(encoding="utf-8")
    assert "launched codex (exit=0)" in commands_log


def test_solve_fails_for_invalid_case(tmp_path: Path) -> None:
    broken_case = tmp_path / "broken-case"
    broken_case.mkdir(parents=True, exist_ok=True)

    result = runner.invoke(app, ["solve", str(broken_case), "--no-launch"])

    assert result.exit_code == 1
    assert "Case validation failed before solve" in result.stdout

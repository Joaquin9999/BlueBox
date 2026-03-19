import json
from pathlib import Path

from typer.testing import CliRunner

from bluebox.cli.app import app


runner = CliRunner()


def _init_case(tmp_path: Path, name: str = "Finalize Case") -> Path:
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "evidence.log").write_text("evidence", encoding="utf-8")

    init_result = runner.invoke(
        app,
        [
            "init",
            name,
            "--artifacts",
            str(artifacts_dir),
            "--title",
            name,
            "--context",
            "Finalize context",
            "--base-path",
            str(tmp_path),
        ],
    )
    assert init_result.exit_code == 0

    case_root = tmp_path / name.lower().replace(" ", "-")
    evidence_summary = {
        "case_name": case_root.name,
        "generated_at": "2026-03-18T00:00:00+00:00",
        "summary": ["Observed suspicious log entry."],
    }
    (case_root / "meta" / "evidence_summary.json").write_text(
        json.dumps(evidence_summary, indent=2) + "\n",
        encoding="utf-8",
    )
    return case_root


def test_finalize_fails_when_case_not_solved(tmp_path: Path) -> None:
    case_root = _init_case(tmp_path)

    result = runner.invoke(app, ["finalize", str(case_root)])

    assert result.exit_code == 1
    assert "Case is not solved" in result.stdout


def test_finalize_allows_incomplete_when_flag_enabled(tmp_path: Path) -> None:
    case_root = _init_case(tmp_path, name="Incomplete Final")

    result = runner.invoke(app, ["finalize", str(case_root), "--allow-incomplete"])

    assert result.exit_code == 0
    assert "Generated incomplete final writeup" in result.stdout

    final_text = (case_root / "notes" / "writeup_final.md").read_text(encoding="utf-8")
    assert "Incomplete final writeup" in final_text


def test_finalize_generates_final_for_solved_case(tmp_path: Path) -> None:
    case_root = _init_case(tmp_path, name="Solved Final")

    solution_state_path = case_root / "meta" / "solution_state.json"
    state = json.loads(solution_state_path.read_text(encoding="utf-8"))
    state["status"] = "solved"
    solution_state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    result = runner.invoke(app, ["finalize", str(case_root)])

    assert result.exit_code == 0
    assert "Generated final writeup" in result.stdout

    new_state = json.loads(solution_state_path.read_text(encoding="utf-8"))
    assert new_state["status"] == "finalized"

    final_text = (case_root / "notes" / "writeup_final.md").read_text(encoding="utf-8")
    assert "Final Writeup" in final_text
    assert "Observed suspicious log entry." in final_text

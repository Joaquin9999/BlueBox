import json
from pathlib import Path

from typer.testing import CliRunner

from bluebox.cli.app import app


runner = CliRunner()


def _init_case(tmp_path: Path, challenge_name: str, artifacts_dir: Path) -> Path:
    result = runner.invoke(
        app,
        [
            "init",
            "--name",
            challenge_name,
            "--artifacts",
            str(artifacts_dir),
            "--title",
            challenge_name,
            "--base-path",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    return tmp_path / challenge_name.lower().replace(" ", "-")


def test_classify_updates_case_state_and_notes(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "traffic.pcap").write_bytes(b"pcap")
    (artifacts_dir / "dns.log").write_text("query", encoding="utf-8")

    case_root = _init_case(tmp_path, "Suspicious Beaconing", artifacts_dir)

    classify_result = runner.invoke(app, ["classify", str(case_root)])
    assert classify_result.exit_code == 0
    assert "Classified:" in classify_result.stdout

    state = json.loads((case_root / "meta" / "solution_state.json").read_text(encoding="utf-8"))
    assert state["status"] == "classified"
    assert state["category"] == "pcap/network forensics"
    assert isinstance(state["subcategories"], list)

    hypotheses = (case_root / "notes" / "hypotheses.md").read_text(encoding="utf-8")
    writeup = (case_root / "notes" / "writeup.md").read_text(encoding="utf-8")
    changelog = (case_root / "notes" / "changelog.md").read_text(encoding="utf-8")

    assert "Classification Update" in hypotheses
    assert "Classification Summary" in writeup
    assert "status 'classified'" in changelog


def test_classify_fails_for_invalid_case(tmp_path: Path) -> None:
    bad_case = tmp_path / "broken-case"
    bad_case.mkdir(parents=True, exist_ok=True)

    result = runner.invoke(app, ["classify", str(bad_case)])

    assert result.exit_code == 1
    assert "Case validation failed before classify" in result.stdout

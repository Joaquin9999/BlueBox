import json
from pathlib import Path

from typer.testing import CliRunner

from bluebox.cli.app import app


runner = CliRunner()


def test_integration_init_classify_validate(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "capture.pcap").write_bytes(b"pcap")
    (artifacts_dir / "dns.log").write_text("query", encoding="utf-8")

    init_result = runner.invoke(
        app,
        [
            "init",
            "Integration Case",
            "--artifacts",
            str(artifacts_dir),
            "--title",
            "Integration Case",
            "--context",
            "integration test",
            "--base-path",
            str(tmp_path),
        ],
    )
    assert init_result.exit_code == 0

    case_root = tmp_path / "integration-case"

    classify_result = runner.invoke(app, ["classify", str(case_root)])
    assert classify_result.exit_code == 0

    validate_result = runner.invoke(app, ["validate", str(case_root)])
    assert validate_result.exit_code == 0

    solution_state = json.loads((case_root / "meta" / "solution_state.json").read_text(encoding="utf-8"))
    assert solution_state["status"] == "classified"
    assert solution_state["category"] in {
        "pcap/network forensics",
        "mixed blue team",
        "log analysis",
    }

    inventory = json.loads((case_root / "meta" / "artifacts_inventory.json").read_text(encoding="utf-8"))
    assert inventory["artifact_count"] == 2

    hashes = json.loads((case_root / "meta" / "hashes.json").read_text(encoding="utf-8"))
    assert len(hashes["files"]) == 2

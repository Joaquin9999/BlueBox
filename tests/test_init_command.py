import hashlib
import json
from pathlib import Path

from typer.testing import CliRunner

from bluebox.cli.app import app


runner = CliRunner()


def _sha256(content: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(content)
    return digest.hexdigest()


def test_init_command_creates_case_workspace(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    file_a = artifacts_dir / "log.txt"
    file_b = artifacts_dir / "nested" / "evidence.bin"
    file_b.parent.mkdir(parents=True, exist_ok=True)

    file_a_content = b"suspicious beaconing"
    file_b_content = b"\x00\x01\x02\x03"
    file_a.write_bytes(file_a_content)
    file_b.write_bytes(file_b_content)

    result = runner.invoke(
        app,
        [
            "init",
            "--name",
            "Suspicious Beaconing",
            "--artifacts",
            str(artifacts_dir),
            "--title",
            "Suspicious Beaconing",
            "--context",
            "Initial context",
            "--base-path",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0

    case_root = tmp_path / "cases" / "suspicious-beaconing"
    assert case_root.is_dir()

    original_a = case_root / "original" / "log.txt"
    original_b = case_root / "original" / "nested" / "evidence.bin"
    working_a = case_root / "working" / "log.txt"
    working_b = case_root / "working" / "nested" / "evidence.bin"

    assert original_a.read_bytes() == file_a_content
    assert original_b.read_bytes() == file_b_content
    assert working_a.read_bytes() == file_a_content
    assert working_b.read_bytes() == file_b_content

    hashes = json.loads((case_root / "meta" / "hashes.json").read_text(encoding="utf-8"))
    hashes_by_path = {entry["path"]: entry["sha256"] for entry in hashes["files"]}

    assert hashes["algorithm"] == "sha256"
    assert hashes_by_path["log.txt"] == _sha256(file_a_content)
    assert hashes_by_path["nested/evidence.bin"] == _sha256(file_b_content)

    inventory = json.loads((case_root / "meta" / "artifacts_inventory.json").read_text(encoding="utf-8"))
    assert inventory["artifact_count"] == 2

    solution_state = json.loads((case_root / "meta" / "solution_state.json").read_text(encoding="utf-8"))
    assert solution_state["status"] == "initialized"
    assert solution_state["artifact_count"] == 2

    changelog = (case_root / "notes" / "changelog.md").read_text(encoding="utf-8")
    assert "Case initialized from artifacts" in changelog


def test_init_fails_when_case_already_exists(tmp_path: Path) -> None:
    artifacts_file = tmp_path / "artifact.txt"
    artifacts_file.write_text("abc", encoding="utf-8")

    first = runner.invoke(
        app,
        [
            "init",
            "--name",
            "Repeat Case",
            "--artifacts",
            str(artifacts_file),
            "--title",
            "Repeat Case",
            "--base-path",
            str(tmp_path),
        ],
    )
    second = runner.invoke(
        app,
        [
            "init",
            "--name",
            "Repeat Case",
            "--artifacts",
            str(artifacts_file),
            "--title",
            "Repeat Case",
            "--base-path",
            str(tmp_path),
        ],
    )

    assert first.exit_code == 0, first.stdout
    assert second.exit_code == 1, second.stdout
    assert "Case directory already exists" in second.stdout


def test_init_sets_active_project_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    artifacts_file = tmp_path / "artifact.txt"
    artifacts_file.write_text("abc", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "init",
            "--name",
            "Active Case",
            "--artifacts",
            str(artifacts_file),
            "--title",
            "Active Case",
            "--base-path",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    active_file = tmp_path / ".bluebox" / "active_case.txt"
    assert active_file.is_file()
    assert active_file.read_text(encoding="utf-8").strip().endswith("active-case")


def test_classify_uses_active_project_when_path_is_omitted(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "network.log").write_text("demo", encoding="utf-8")

    init_result = runner.invoke(
        app,
        [
            "init",
            "--name",
            "Project Flow",
            "--artifacts",
            str(artifacts_dir),
            "--title",
            "Project Flow",
            "--base-path",
            str(tmp_path),
        ],
    )

    assert init_result.exit_code == 0

    classify_result = runner.invoke(app, ["classify"])
    assert classify_result.exit_code == 0
    assert "Classified:" in classify_result.stdout


def test_new_command_defaults_to_reference_only(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "sample.log").write_text("demo", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "new",
            "--name",
            "Reference Case",
            "--artifacts",
            str(artifacts_dir),
            "--title",
            "Reference Case",
            "--base-path",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    case_root = tmp_path / "cases" / "reference-case"
    assert case_root.is_dir()

    manifest = json.loads((case_root / "challenge" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["evidence_mode"] == "reference-only"


def test_new_command_rejects_artifacts_equal_base_path(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "new",
            "--name",
            "Invalid Paths",
            "--artifacts",
            str(tmp_path),
            "--title",
            "Invalid Paths",
            "--base-path",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "Artifacts path must be different from base path" in result.stdout


def test_new_generates_default_agent_prompt_content(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "sample.log").write_text("demo", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "new",
            "--name",
            "Prompt Case",
            "--artifacts",
            str(artifacts_dir),
            "--title",
            "Prompt Case",
            "--base-path",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    prompt_text = (tmp_path / "cases" / "prompt-case" / "agent" / "prompt.md").read_text(encoding="utf-8")
    assert "most wanted hacker" in prompt_text
    assert "writeups" in prompt_text



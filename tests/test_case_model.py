from pathlib import Path

from bluebox.core.case_model import REQUIRED_CASE_FILES, CaseWorkspaceSpec, sanitize_case_name
from bluebox.core.workspace_builder import create_case_workspace


def test_sanitize_case_name() -> None:
    assert sanitize_case_name("Suspicious Beaconing") == "suspicious-beaconing"
    assert sanitize_case_name("  ### Windows DFIR 101 ###  ") == "windows-dfir-101"
    assert sanitize_case_name("---") == "case"


def test_create_case_workspace_generates_structure_and_files(tmp_path: Path) -> None:
    spec = CaseWorkspaceSpec(
        raw_name="Suspicious Beaconing",
        title="Suspicious Beaconing",
        context="Initial context",
    )

    case_root = create_case_workspace(tmp_path, spec)

    assert case_root.name == "suspicious-beaconing"
    assert (case_root / "original").is_dir()
    assert (case_root / "working").is_dir()
    assert (case_root / "derived" / "extracted").is_dir()
    assert (case_root / ".codex").is_dir()

    for required_file in REQUIRED_CASE_FILES:
        assert (case_root / required_file).is_file(), f"Missing: {required_file}"

    writeup_content = (case_root / "notes" / "writeup.md").read_text(encoding="utf-8")
    assert "Suspicious Beaconing" in writeup_content

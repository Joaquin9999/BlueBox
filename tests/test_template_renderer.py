from pathlib import Path

from bluebox.core.case_model import REQUIRED_CASE_FILES, ensure_case_structure
from bluebox.core.template_renderer import render_case_templates


def test_render_case_templates_writes_required_files(tmp_path: Path) -> None:
    case_root = tmp_path / "render-case"
    ensure_case_structure(case_root)

    render_case_templates(
        case_root,
        {
            "case_name": "render-case",
            "title": "Render Case",
            "context": "Renderer context",
            "timestamp": "2026-03-18T00:00:00+00:00",
        },
    )

    for relative_file in REQUIRED_CASE_FILES:
        assert (case_root / relative_file).is_file(), f"Missing rendered file: {relative_file}"

    writeup = (case_root / "notes" / "writeup.md").read_text(encoding="utf-8")
    assert "Render Case" in writeup
    assert "Renderer context" in writeup

    state = (case_root / "meta" / "solution_state.json").read_text(encoding="utf-8")
    assert '"status": "initialized"' in state

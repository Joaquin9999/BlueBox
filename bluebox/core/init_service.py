from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .case_model import CaseWorkspaceSpec
from .workspace_builder import create_case_workspace

EVIDENCE_MODES = {"reference-only", "lightweight-copy", "full-copy", "legacy-copy"}


def _utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _iter_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


def _sha256_file(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for block in iter(lambda: handle.read(8192), b""):
            digest.update(block)
    return digest.hexdigest()


def _copy_artifacts(artifacts_path: Path, destination_root: Path) -> int:
    if artifacts_path.is_file():
        destination_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(artifacts_path, destination_root / artifacts_path.name)
        return 1

    if not artifacts_path.is_dir():
        raise FileNotFoundError(f"Artifacts path does not exist: {artifacts_path}")

    copied_count = 0
    for source_file in _iter_files(artifacts_path):
        relative_file = source_file.relative_to(artifacts_path)
        target_file = destination_root / relative_file
        target_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, target_file)
        copied_count += 1
    return copied_count


def _contains_bluebox_workspace(root: Path) -> bool:
    if not root.is_dir():
        return False

    if (root / ".bluebox").exists():
        return True

    for marker in root.rglob("meta/solution_state.json"):
        if marker.is_file():
            return True
    return False


def _build_entries_for_source(source_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    hashes_entries: list[dict[str, Any]] = []
    inventory_entries: list[dict[str, Any]] = []
    for file_path in _iter_files(source_root):
        relative_path = file_path.relative_to(source_root).as_posix()
        sha256_value = _sha256_file(file_path)
        file_size = file_path.stat().st_size

        hashes_entries.append(
            {
                "path": relative_path,
                "sha256": sha256_value,
            }
        )
        inventory_entries.append(
            {
                "path": relative_path,
                "size": file_size,
                "source": "reference" if source_root.name != "original" else "original",
            }
        )
    return hashes_entries, inventory_entries


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def initialize_case_from_artifacts(
    *,
    base_path: Path,
    challenge_name: str,
    artifacts_path: Path,
    title: str,
    context: str,
    evidence_mode: str = "reference-only",
) -> Path:
    if evidence_mode not in EVIDENCE_MODES:
        raise ValueError(f"Unsupported evidence mode: {evidence_mode}")

    artifacts_path = artifacts_path.resolve()
    base_path = base_path.resolve()

    spec = CaseWorkspaceSpec(raw_name=challenge_name, title=title, context=context)
    safe_title = spec.title.replace('"', '\\"')
    safe_context = spec.context.replace('"', '\\"')
    planned_case_root = base_path / "cases" / spec.case_name

    if artifacts_path == base_path:
        raise ValueError("Artifacts path must be different from base path.")

    if planned_case_root == artifacts_path or planned_case_root.is_relative_to(artifacts_path):
        raise ValueError("Case path cannot be inside artifacts path.")

    if _contains_bluebox_workspace(artifacts_path):
        raise ValueError("Artifacts path already contains a BlueBox workspace.")

    if planned_case_root.exists():
        raise FileExistsError(f"Case directory already exists: {planned_case_root}")

    case_root = create_case_workspace(base_path=base_path, spec=spec)

    if not artifacts_path.exists():
        raise FileNotFoundError(f"Artifacts path does not exist: {artifacts_path}")

    copied_original = 0
    source_root_for_index = artifacts_path
    if evidence_mode in {"legacy-copy", "full-copy"}:
        copied_original = _copy_artifacts(artifacts_path, case_root / "original")
        _copy_artifacts(artifacts_path, case_root / "working")
        source_root_for_index = case_root / "original"
    elif evidence_mode == "lightweight-copy":
        copied_original = _copy_artifacts(artifacts_path, case_root / "original")
        source_root_for_index = case_root / "original"

    timestamp = _utc_timestamp()
    hashes_entries, inventory_entries = _build_entries_for_source(source_root_for_index)

    _write_json(
        case_root / "challenge" / "hashes.json",
        {
            "case_name": spec.case_name,
            "generated_at": timestamp,
            "algorithm": "sha256",
            "files": hashes_entries,
        },
    )

    _write_json(
        case_root / "challenge" / "manifest.json",
        {
            "case_name": spec.case_name,
            "generated_at": timestamp,
            "source_path": str(artifacts_path),
            "evidence_mode": evidence_mode,
            "artifact_count": len(inventory_entries),
            "artifacts": inventory_entries,
        },
    )

    (case_root / "challenge" / "source_ref.txt").write_text(
        f"source_path={artifacts_path}\nmode={evidence_mode}\ncreated_at={timestamp}\n",
        encoding="utf-8",
    )

    (case_root / "case.yaml").write_text(
        "\n".join(
            [
                f'case_name: "{spec.case_name}"',
                f'title: "{safe_title}"',
                'status: "initialized"',
                "profile: null",
                f'copy_mode: "{evidence_mode}"',
                f'created_at: "{timestamp}"',
                f'updated_at: "{timestamp}"',
                f'context: "{safe_context}"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return case_root

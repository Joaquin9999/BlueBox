from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .case_model import CaseWorkspaceSpec
from .workspace_builder import create_case_workspace


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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def initialize_case_from_artifacts(
    *,
    base_path: Path,
    challenge_name: str,
    artifacts_path: Path,
    title: str,
    context: str,
) -> Path:
    spec = CaseWorkspaceSpec(raw_name=challenge_name, title=title, context=context)
    case_root = create_case_workspace(base_path=base_path, spec=spec)

    if not artifacts_path.exists():
        raise FileNotFoundError(f"Artifacts path does not exist: {artifacts_path}")

    copied_original = _copy_artifacts(artifacts_path, case_root / "original")
    _copy_artifacts(artifacts_path, case_root / "working")

    timestamp = _utc_timestamp()
    original_root = case_root / "original"

    hashes_entries: list[dict[str, Any]] = []
    inventory_entries: list[dict[str, Any]] = []

    for file_path in _iter_files(original_root):
        relative_path = file_path.relative_to(original_root).as_posix()
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
                "source": "original",
            }
        )

    _write_json(
        case_root / "meta" / "hashes.json",
        {
            "case_name": spec.case_name,
            "generated_at": timestamp,
            "algorithm": "sha256",
            "files": hashes_entries,
        },
    )

    _write_json(
        case_root / "meta" / "artifacts_inventory.json",
        {
            "case_name": spec.case_name,
            "generated_at": timestamp,
            "artifact_count": len(inventory_entries),
            "artifacts": inventory_entries,
        },
    )

    _write_json(
        case_root / "meta" / "solution_state.json",
        {
            "case_name": spec.case_name,
            "title": spec.title,
            "status": "initialized",
            "category": None,
            "subcategories": [],
            "context": spec.context,
            "artifact_count": len(inventory_entries),
            "created_at": timestamp,
            "updated_at": timestamp,
        },
    )

    (case_root / "notes" / "changelog.md").write_text(
        "\n".join(
            [
                f"# Changelog — {spec.case_name}",
                "",
                f"- {timestamp}: Case initialized from artifacts (`{copied_original}` files copied).",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return case_root

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field


REQUIRED_CASE_DIRECTORIES: tuple[str, ...] = (
    "challenge",
    "work/reports",
    "work/extracted",
    "work/parsed",
    "work/scratch",
    "agent",
    "memory",
    "output",
)

REQUIRED_CASE_FILES: tuple[str, ...] = (
    "case.yaml",
    "challenge/source_ref.txt",
    "challenge/manifest.json",
    "challenge/hashes.json",
    "agent/context.md",
    "agent/prompt.md",
    "agent/handoff.md",
    "memory/log.md",
    "output/writeup.md",
    "output/writeup_final.md",
    "output/final_flag.txt",
)


class CaseWorkspaceSpec(BaseModel):
    raw_name: str = Field(min_length=1)
    title: str = Field(min_length=1)
    context: str = ""

    @property
    def case_name(self) -> str:
        return sanitize_case_name(self.raw_name)


def sanitize_case_name(name: str) -> str:
    normalized = name.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized)
    return normalized.strip("-") or "case"


def ensure_case_structure(case_root: Path) -> None:
    for relative_dir in REQUIRED_CASE_DIRECTORIES:
        (case_root / relative_dir).mkdir(parents=True, exist_ok=True)

from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class ToolCheck:
    name: str
    available: bool
    detail: str


@dataclass
class DoctorReport:
    python_version: str
    platform_info: str
    checks: list[ToolCheck]


def _run_version_command(command: list[str]) -> str:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as error:
        return f"error: {error}"

    output = (completed.stdout or completed.stderr).strip()
    return output.splitlines()[0] if output else "available"


def build_doctor_report() -> DoctorReport:
    checks: list[ToolCheck] = []

    uv_path = shutil.which("uv")
    checks.append(
        ToolCheck(
            name="uv",
            available=uv_path is not None,
            detail=_run_version_command(["uv", "--version"]) if uv_path else "not found in PATH",
        )
    )

    agent_path = shutil.which("agent")
    checks.append(
        ToolCheck(
            name="agent",
            available=agent_path is not None,
            detail=_run_version_command(["agent", "--version"]) if agent_path else "not found in PATH",
        )
    )

    git_path = shutil.which("git")
    checks.append(
        ToolCheck(
            name="git",
            available=git_path is not None,
            detail=_run_version_command(["git", "--version"]) if git_path else "not found in PATH",
        )
    )

    return DoctorReport(
        python_version=platform.python_version(),
        platform_info=f"{platform.system()} {platform.release()}",
        checks=checks,
    )

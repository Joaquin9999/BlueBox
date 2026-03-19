from __future__ import annotations

import platform
import shlex
import shutil
import subprocess
from dataclasses import dataclass

from .tools_catalog import INSTALL_HINTS, TOOLS_BY_PROFILE, ToolSpec


@dataclass
class ToolStatus:
    name: str
    available: bool
    detail: str
    install_hint: str | None


@dataclass
class ToolInstallResult:
    name: str
    attempted: bool
    success: bool
    command: str | None
    message: str


def list_profiles() -> dict[str, list[ToolSpec]]:
    return TOOLS_BY_PROFILE


def list_tool_names() -> list[str]:
    names: set[str] = set()
    for specs in TOOLS_BY_PROFILE.values():
        for spec in specs:
            names.add(spec.name)
    return sorted(names)


def _os_family() -> str:
    system = platform.system().lower()
    if "darwin" in system:
        return "darwin"
    if "linux" in system:
        return "linux"
    return "other"


def _check_tool(spec: ToolSpec) -> bool:
    command = shlex.split(spec.check_command)
    executable = command[0]
    if shutil.which(executable) is None:
        return False

    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return completed.returncode == 0


def check_profile(profile: str) -> list[ToolStatus]:
    if profile not in TOOLS_BY_PROFILE:
        raise ValueError(f"Unknown profile: {profile}")

    family = _os_family()
    hints = INSTALL_HINTS.get(family, {})

    statuses: list[ToolStatus] = []
    for spec in TOOLS_BY_PROFILE[profile]:
        available = _check_tool(spec)
        statuses.append(
            ToolStatus(
                name=spec.name,
                available=available,
                detail=spec.description,
                install_hint=hints.get(spec.name),
            )
        )
    return statuses


def _find_tool_spec(tool_name: str) -> ToolSpec | None:
    target = tool_name.strip().lower()
    for specs in TOOLS_BY_PROFILE.values():
        for spec in specs:
            if spec.name.lower() == target:
                return spec
    return None


def install_tool(tool_name: str, *, apply: bool = False) -> ToolInstallResult:
    spec = _find_tool_spec(tool_name)
    if spec is None:
        raise ValueError(f"Unknown tool: {tool_name}")

    family = _os_family()
    hints = INSTALL_HINTS.get(family, {})
    available = _check_tool(spec)
    if available:
        return ToolInstallResult(
            name=spec.name,
            attempted=False,
            success=True,
            command=None,
            message="already available",
        )

    command = hints.get(spec.name)
    if command is None:
        return ToolInstallResult(
            name=spec.name,
            attempted=False,
            success=False,
            command=None,
            message="no install hint for this OS",
        )

    if not apply:
        return ToolInstallResult(
            name=spec.name,
            attempted=False,
            success=False,
            command=command,
            message="dry-run (use --apply to execute)",
        )

    completed = subprocess.run(command, shell=True, check=False)
    return ToolInstallResult(
        name=spec.name,
        attempted=True,
        success=completed.returncode == 0,
        command=command,
        message="installed" if completed.returncode == 0 else f"failed ({completed.returncode})",
    )


def install_profile(profile: str, *, apply: bool = False) -> list[ToolInstallResult]:
    statuses = check_profile(profile)
    family = _os_family()
    hints = INSTALL_HINTS.get(family, {})

    results: list[ToolInstallResult] = []
    for status in statuses:
        if status.available:
            results.append(
                ToolInstallResult(
                    name=status.name,
                    attempted=False,
                    success=True,
                    command=None,
                    message="already available",
                )
            )
            continue

        command = hints.get(status.name)
        if command is None:
            results.append(
                ToolInstallResult(
                    name=status.name,
                    attempted=False,
                    success=False,
                    command=None,
                    message="no install hint for this OS",
                )
            )
            continue

        if not apply:
            results.append(
                ToolInstallResult(
                    name=status.name,
                    attempted=False,
                    success=False,
                    command=command,
                    message="dry-run (use --apply to execute)",
                )
            )
            continue

        completed = subprocess.run(command, shell=True, check=False)
        results.append(
            ToolInstallResult(
                name=status.name,
                attempted=True,
                success=completed.returncode == 0,
                command=command,
                message="installed" if completed.returncode == 0 else f"failed ({completed.returncode})",
            )
        )

    return results


def install_all_profiles(*, apply: bool = False) -> dict[str, list[ToolInstallResult]]:
    results: dict[str, list[ToolInstallResult]] = {}
    for profile in TOOLS_BY_PROFILE:
        results[profile] = install_profile(profile, apply=apply)
    return results

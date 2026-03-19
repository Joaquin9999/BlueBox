from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .validation import validate_case_structure


@dataclass
class ClassificationOutcome:
    case_path: Path
    category: str
    subcategories: list[str]
    artifact_count: int
    analysis_path: list[str]
    hypotheses: list[str]


def _utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _load_json_dict(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _extract_artifact_paths(artifacts_inventory: dict[str, Any]) -> list[str]:
    raw_artifacts = artifacts_inventory.get("artifacts", [])
    if not isinstance(raw_artifacts, list):
        raise ValueError("meta/artifacts_inventory.json: 'artifacts' must be a list")

    paths: list[str] = []
    for item in raw_artifacts:
        if isinstance(item, dict) and isinstance(item.get("path"), str):
            paths.append(item["path"])
        elif isinstance(item, str):
            paths.append(item)
    return paths


def _infer_category(artifact_paths: list[str]) -> tuple[str, list[str]]:
    scores: dict[str, int] = {
        "log analysis": 0,
        "pcap/network forensics": 0,
        "windows dfir": 0,
        "linux dfir": 0,
        "phishing": 0,
        "malware triage": 0,
    }
    subcategories: set[str] = set()

    for artifact in artifact_paths:
        value = artifact.lower()

        if value.endswith((".pcap", ".pcapng", ".cap")):
            scores["pcap/network forensics"] += 3
            subcategories.update({"pcap", "network-traffic"})
        if any(token in value for token in ["dns", "http", "proxy", "netflow"]):
            scores["pcap/network forensics"] += 1
            subcategories.add("network-logs")

        if value.endswith((".evtx", ".etl", ".pf")) or any(
            token in value for token in ["sysmon", "powershell", "registry", "windows"]
        ):
            scores["windows dfir"] += 2
            subcategories.add("windows-artifacts")

        if any(token in value for token in ["/var/log", "auth.log", "syslog", "linux", "journal"]):
            scores["linux dfir"] += 2
            subcategories.add("linux-logs")

        if value.endswith((".eml", ".msg")) or any(
            token in value for token in ["mail", "phish", "smtp", "imap"]
        ):
            scores["phishing"] += 2
            subcategories.add("email-artifacts")

        if value.endswith((".exe", ".dll", ".ps1", ".vbs", ".js", ".jar", ".apk")) or any(
            token in value for token in ["malware", "payload", "sample"]
        ):
            scores["malware triage"] += 2
            subcategories.add("suspicious-binaries")

        if value.endswith((".log", ".txt", ".json", ".csv")):
            scores["log analysis"] += 1
            subcategories.add("structured-logs")

    ranked = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
    non_zero = [item for item in ranked if item[1] > 0]

    if len(non_zero) >= 2 and non_zero[0][1] == non_zero[1][1]:
        return "mixed blue team", sorted(subcategories)

    if non_zero:
        return non_zero[0][0], sorted(subcategories)

    return "mixed blue team", []


def _analysis_path_for_category(category: str) -> list[str]:
    mapping: dict[str, list[str]] = {
        "pcap/network forensics": [
            "Enumerate protocols, endpoints and top talkers.",
            "Build a communication timeline and isolate suspicious sessions.",
            "Correlate network indicators with host artifacts and logs.",
        ],
        "windows dfir": [
            "Prioritize event logs, process execution traces and persistence artifacts.",
            "Build host timeline around anomalous process/user activity.",
            "Cross-check indicators against network and file evidence.",
        ],
        "linux dfir": [
            "Review auth/system logs and service activity for anomalies.",
            "Build timeline of user actions, process launches and remote access.",
            "Correlate suspicious events with binaries/scripts and network traces.",
        ],
        "phishing": [
            "Extract sender/recipient, headers and delivery path details.",
            "Analyze links/attachments and identify initial infection vector.",
            "Correlate email indicators with endpoint/network events.",
        ],
        "malware triage": [
            "Inventory suspicious files, hashes and execution artifacts.",
            "Prioritize static triage (strings/imports/metadata) before dynamic steps.",
            "Map observable behavior to host/network evidence.",
        ],
        "log analysis": [
            "Normalize key logs and identify high-signal fields.",
            "Build timeline and isolate unusual authentication/process/network events.",
            "Validate candidate findings with cross-source corroboration.",
        ],
        "mixed blue team": [
            "Start with inventory-driven scoping and evidence triage.",
            "Build a unified timeline across host, network and email artifacts.",
            "Prioritize hypotheses that can be verified with available evidence.",
        ],
    }
    return mapping.get(category, mapping["mixed blue team"])


def _initial_hypotheses(category: str) -> list[str]:
    category_hypotheses: dict[str, list[str]] = {
        "pcap/network forensics": [
            "Observed suspicious communications indicate potential C2 or beaconing behavior.",
            "One or more endpoints likely initiated anomalous outbound traffic patterns.",
        ],
        "windows dfir": [
            "A suspicious process chain may indicate execution/persistence activity.",
            "At least one user or service context likely performed anomalous actions.",
        ],
        "linux dfir": [
            "Anomalous authentication or privilege activity may have occurred.",
            "Suspicious script/binary execution may explain observed timeline anomalies.",
        ],
        "phishing": [
            "A malicious email artifact may represent the initial access vector.",
            "Attachment or URL interaction likely triggered follow-on activity.",
        ],
        "malware triage": [
            "One or more binaries/scripts may exhibit malicious indicators.",
            "File-level indicators likely correlate with host/network anomalies.",
        ],
        "log analysis": [
            "Timeline anomalies in logs likely reveal the main attack sequence.",
            "Correlated log events should identify the most suspicious entities.",
        ],
        "mixed blue team": [
            "Multiple evidence sources likely need correlation to identify root activity.",
            "Initial anomalies should be validated through timeline-based triage.",
        ],
    }
    return category_hypotheses.get(category, category_hypotheses["mixed blue team"])


def _append_markdown_section(path: Path, heading: str, lines: list[str]) -> None:
    current = path.read_text(encoding="utf-8").rstrip()
    section = "\n".join(["", heading, *[f"- {line}" for line in lines]])
    path.write_text(current + "\n" + section + "\n", encoding="utf-8")


def classify_case(case_path: Path) -> ClassificationOutcome:
    validation = validate_case_structure(case_path)
    if not validation.is_valid:
        joined_errors = "\n".join(validation.errors)
        raise ValueError(f"Case validation failed before classify:\n{joined_errors}")

    artifacts_inventory_path = case_path / "meta" / "artifacts_inventory.json"
    solution_state_path = case_path / "meta" / "solution_state.json"

    inventory = _load_json_dict(artifacts_inventory_path)
    solution_state = _load_json_dict(solution_state_path)

    artifact_paths = _extract_artifact_paths(inventory)
    category, subcategories = _infer_category(artifact_paths)
    analysis_path = _analysis_path_for_category(category)
    hypotheses = _initial_hypotheses(category)
    timestamp = _utc_timestamp()

    solution_state["status"] = "classified"
    solution_state["category"] = category
    solution_state["subcategories"] = subcategories
    solution_state["updated_at"] = timestamp
    (case_path / "meta" / "solution_state.json").write_text(
        json.dumps(solution_state, indent=2) + "\n",
        encoding="utf-8",
    )

    _append_markdown_section(
        case_path / "notes" / "hypotheses.md",
        f"## Classification Update — {timestamp}",
        [f"Category inferred: {category}", *hypotheses],
    )

    _append_markdown_section(
        case_path / "notes" / "writeup.md",
        f"## Classification Summary — {timestamp}",
        [
            f"Inferred category: {category}",
            f"Subcategories: {', '.join(subcategories) if subcategories else 'none'}",
            "Initial analysis path:",
            *analysis_path,
        ],
    )

    _append_markdown_section(
        case_path / "notes" / "changelog.md",
        "## Updates",
        [f"{timestamp}: Case moved to status 'classified' with category '{category}'."],
    )

    return ClassificationOutcome(
        case_path=case_path,
        category=category,
        subcategories=subcategories,
        artifact_count=len(artifact_paths),
        analysis_path=analysis_path,
        hypotheses=hypotheses,
    )

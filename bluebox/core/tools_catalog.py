from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolSpec:
    name: str
    check_command: str
    description: str


TOOLS_BY_PROFILE: dict[str, list[ToolSpec]] = {
    "base": [
        ToolSpec("git", "git --version", "Version control"),
        ToolSpec("jq", "jq --version", "JSON processor"),
        ToolSpec("ripgrep", "rg --version", "Fast text search"),
    ],
    "network": [
        ToolSpec("tshark", "tshark --version", "Packet analysis CLI"),
        ToolSpec("tcpdump", "tcpdump --version", "Packet capture"),
        ToolSpec("zeek", "zeek --version", "Network security monitoring"),
    ],
    "windows-dfir": [
        ToolSpec("chainsaw", "chainsaw --help", "Windows event log hunting"),
        ToolSpec("evtx_dump", "evtx_dump --help", "EVTX extraction"),
    ],
    "linux-dfir": [
        ToolSpec("log2timeline", "log2timeline.py --version", "Timeline generation"),
        ToolSpec("plaso", "psort.py --version", "Timeline processing"),
    ],
    "malware": [
        ToolSpec("yara", "yara --version", "YARA matching engine"),
        ToolSpec("upx", "upx --version", "Binary unpacker/packer"),
        ToolSpec("ssdeep", "ssdeep -V", "Fuzzy hashing"),
    ],
}


INSTALL_HINTS: dict[str, dict[str, str]] = {
    "darwin": {
        "git": "brew install git",
        "jq": "brew install jq",
        "ripgrep": "brew install ripgrep",
        "tshark": "brew install wireshark",
        "tcpdump": "brew install tcpdump",
        "zeek": "brew install zeek",
        "chainsaw": "brew install chainsaw",
        "evtx_dump": "pip install python-evtx",
        "log2timeline": "brew install plaso",
        "plaso": "brew install plaso",
        "yara": "brew install yara",
        "upx": "brew install upx",
        "ssdeep": "brew install ssdeep",
    },
    "linux": {
        "git": "sudo apt-get install -y git",
        "jq": "sudo apt-get install -y jq",
        "ripgrep": "sudo apt-get install -y ripgrep",
        "tshark": "sudo apt-get install -y tshark",
        "tcpdump": "sudo apt-get install -y tcpdump",
        "zeek": "sudo apt-get install -y zeek",
        "chainsaw": "echo 'Install Chainsaw binary from official release'",
        "evtx_dump": "pip install python-evtx",
        "log2timeline": "sudo apt-get install -y plaso-tools",
        "plaso": "sudo apt-get install -y plaso-tools",
        "yara": "sudo apt-get install -y yara",
        "upx": "sudo apt-get install -y upx-ucl",
        "ssdeep": "sudo apt-get install -y ssdeep",
    },
}

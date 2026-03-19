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
        ToolSpec("yq", "yq --version", "YAML processor"),
        ToolSpec("ripgrep", "rg --version", "Fast text search"),
        ToolSpec("fd", "fd --version", "Fast file finder"),
        ToolSpec("file", "file --version", "File type identification"),
        ToolSpec("strings", "strings --version", "Printable strings extraction"),
        ToolSpec("xxd", "xxd -h", "Hex dump utility"),
        ToolSpec("binwalk", "binwalk --help", "Firmware/binary analysis"),
        ToolSpec("curl", "curl --version", "HTTP transfer tool"),
        ToolSpec("7z", "7z", "Archive extraction utility"),
        ToolSpec("unzip", "unzip -v", "ZIP extraction utility"),
    ],
    "forensics-core": [
        ToolSpec("exiftool", "exiftool -ver", "Metadata extractor"),
        ToolSpec("yara", "yara --version", "YARA matching engine"),
        ToolSpec("ssdeep", "ssdeep -V", "Fuzzy hashing"),
        ToolSpec("bulk_extractor", "bulk_extractor -h", "Bulk artifact extraction"),
        ToolSpec("fls", "fls -V", "Sleuthkit file listing"),
        ToolSpec("foremost", "foremost -V", "File carving"),
        ToolSpec("testdisk", "testdisk /version", "Partition/data recovery"),
        ToolSpec("hashdeep", "hashdeep -h", "Recursive hashing"),
    ],
    "pcap": [
        ToolSpec("tshark", "tshark --version", "Packet analysis CLI"),
        ToolSpec("tcpdump", "tcpdump --version", "Packet capture"),
        ToolSpec("zeek", "zeek --version", "Network security monitoring"),
        ToolSpec("ngrep", "ngrep -V", "Network grep"),
        ToolSpec("capinfos", "capinfos -h", "PCAP metadata"),
        ToolSpec("mergecap", "mergecap -h", "PCAP merge"),
        ToolSpec("editcap", "editcap -h", "PCAP editing"),
    ],
    "windows-dfir": [
        ToolSpec("chainsaw", "chainsaw --help", "Windows event log hunting"),
        ToolSpec("hayabusa", "hayabusa --help", "Windows timeline hunting"),
        ToolSpec("evtx_dump", "evtx_dump --help", "EVTX extraction"),
        ToolSpec("yara", "yara --version", "YARA matching engine"),
        ToolSpec("jq", "jq --version", "JSON processor"),
    ],
    "memory": [
        ToolSpec("volatility3", "vol --help", "Memory forensics framework"),
        ToolSpec("yara", "yara --version", "YARA matching engine"),
        ToolSpec("strings", "strings --version", "Printable strings extraction"),
    ],
    "malware": [
        ToolSpec("yara", "yara --version", "YARA matching engine"),
        ToolSpec("upx", "upx --version", "Binary unpacker/packer"),
        ToolSpec("ssdeep", "ssdeep -V", "Fuzzy hashing"),
        ToolSpec("radare2", "r2 -v", "Reverse engineering framework"),
        ToolSpec("binwalk", "binwalk --help", "Firmware/binary analysis"),
        ToolSpec("file", "file --version", "File type identification"),
        ToolSpec("strings", "strings --version", "Printable strings extraction"),
    ],
    "ctf-blue": [
        ToolSpec("jq", "jq --version", "JSON processor"),
        ToolSpec("yq", "yq --version", "YAML processor"),
        ToolSpec("ripgrep", "rg --version", "Fast text search"),
        ToolSpec("file", "file --version", "File type identification"),
        ToolSpec("strings", "strings --version", "Printable strings extraction"),
        ToolSpec("binwalk", "binwalk --help", "Firmware/binary analysis"),
        ToolSpec("exiftool", "exiftool -ver", "Metadata extractor"),
        ToolSpec("yara", "yara --version", "YARA matching engine"),
        ToolSpec("tshark", "tshark --version", "Packet analysis CLI"),
        ToolSpec("zeek", "zeek --version", "Network security monitoring"),
        ToolSpec("chainsaw", "chainsaw --help", "Windows event log hunting"),
    ],
    "network": [
        ToolSpec("tshark", "tshark --version", "Packet analysis CLI"),
        ToolSpec("tcpdump", "tcpdump --version", "Packet capture"),
        ToolSpec("zeek", "zeek --version", "Network security monitoring"),
    ],
    "linux-dfir": [
        ToolSpec("log2timeline", "log2timeline.py --version", "Timeline generation"),
        ToolSpec("plaso", "psort.py --version", "Timeline processing"),
    ],
}


def _build_all_profile() -> list[ToolSpec]:
    names_seen: set[str] = set()
    merged: list[ToolSpec] = []
    for profile_name, specs in TOOLS_BY_PROFILE.items():
        if profile_name == "all":
            continue
        for spec in specs:
            key = spec.name.lower()
            if key in names_seen:
                continue
            names_seen.add(key)
            merged.append(spec)
    return merged


TOOLS_BY_PROFILE["all"] = _build_all_profile()


INSTALL_HINTS: dict[str, dict[str, str]] = {
    "darwin": {
        "git": "brew install git",
        "jq": "brew install jq",
        "yq": "brew install yq",
        "ripgrep": "brew install ripgrep",
        "fd": "brew install fd",
        "file": "brew install file-formula",
        "strings": "brew install binutils",
        "xxd": "brew install xxd",
        "binwalk": "brew install binwalk",
        "curl": "brew install curl",
        "7z": "brew install p7zip",
        "unzip": "brew install unzip",
        "exiftool": "brew install exiftool",
        "bulk_extractor": "brew install bulk_extractor",
        "fls": "brew install sleuthkit",
        "foremost": "brew install foremost",
        "testdisk": "brew install testdisk",
        "hashdeep": "brew install md5deep",
        "tshark": "brew install wireshark",
        "tcpdump": "brew install tcpdump",
        "zeek": "brew install zeek",
        "ngrep": "brew install ngrep",
        "capinfos": "brew install wireshark",
        "mergecap": "brew install wireshark",
        "editcap": "brew install wireshark",
        "chainsaw": "brew install chainsaw",
        "hayabusa": "echo 'Install Hayabusa binary from official release'",
        "evtx_dump": "pip install python-evtx",
        "log2timeline": "brew install plaso",
        "plaso": "brew install plaso",
        "volatility3": "pip install volatility3",
        "yara": "brew install yara",
        "upx": "brew install upx",
        "ssdeep": "brew install ssdeep",
        "radare2": "brew install radare2",
    },
    "linux": {
        "git": "sudo apt-get install -y git",
        "jq": "sudo apt-get install -y jq",
        "yq": "sudo snap install yq",
        "ripgrep": "sudo apt-get install -y ripgrep",
        "fd": "sudo apt-get install -y fd-find",
        "file": "sudo apt-get install -y file",
        "strings": "sudo apt-get install -y binutils",
        "xxd": "sudo apt-get install -y xxd",
        "binwalk": "sudo apt-get install -y binwalk",
        "curl": "sudo apt-get install -y curl",
        "7z": "sudo apt-get install -y p7zip-full",
        "unzip": "sudo apt-get install -y unzip",
        "exiftool": "sudo apt-get install -y libimage-exiftool-perl",
        "bulk_extractor": "sudo apt-get install -y bulk-extractor",
        "fls": "sudo apt-get install -y sleuthkit",
        "foremost": "sudo apt-get install -y foremost",
        "testdisk": "sudo apt-get install -y testdisk",
        "hashdeep": "sudo apt-get install -y hashdeep",
        "tshark": "sudo apt-get install -y tshark",
        "tcpdump": "sudo apt-get install -y tcpdump",
        "zeek": "sudo apt-get install -y zeek",
        "ngrep": "sudo apt-get install -y ngrep",
        "capinfos": "sudo apt-get install -y wireshark-common",
        "mergecap": "sudo apt-get install -y wireshark-common",
        "editcap": "sudo apt-get install -y wireshark-common",
        "chainsaw": "echo 'Install Chainsaw binary from official release'",
        "hayabusa": "echo 'Install Hayabusa binary from official release'",
        "evtx_dump": "pip install python-evtx",
        "log2timeline": "sudo apt-get install -y plaso-tools",
        "plaso": "sudo apt-get install -y plaso-tools",
        "volatility3": "pip install volatility3",
        "yara": "sudo apt-get install -y yara",
        "upx": "sudo apt-get install -y upx-ucl",
        "ssdeep": "sudo apt-get install -y ssdeep",
        "radare2": "sudo apt-get install -y radare2",
    },
}

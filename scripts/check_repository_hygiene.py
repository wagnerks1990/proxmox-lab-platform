#!/usr/bin/env python3
"""Reject tracked secrets, private key material, and private runtime endpoints."""

from __future__ import annotations

import ipaddress
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOTS = (Path("backend/app"), Path("frontend/src"), Path("deploy"))
FORBIDDEN_SUFFIXES = {".db", ".dump", ".key", ".pem", ".pfx", ".sqlite", ".sqlite3"}
SECRET_PATTERNS = {
    "private key material": re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
}
CREDENTIAL_URL_RE = re.compile(r"https?://[^\s/:]+:[^\s/@]+@")
IPV4_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
PRIVATE_NETWORKS = tuple(
    ipaddress.ip_network(value)
    for value in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    )
    return [Path(raw.decode()) for raw in result.stdout.split(b"\0") if raw]


def is_runtime_file(path: Path) -> bool:
    return path.name.startswith("docker-compose") or any(
        path.is_relative_to(root) for root in RUNTIME_ROOTS
    )


def main() -> int:
    failures: list[str] = []
    for relative in tracked_files():
        if relative.name != ".env.example" and (
            relative.name == ".env" or relative.suffix.lower() in FORBIDDEN_SUFFIXES
        ):
            failures.append(f"{relative}: forbidden tracked secret/data file type")
        path = ROOT / relative
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                failures.append(f"{relative}:{line}: possible {label}")
        if is_runtime_file(relative):
            for match in CREDENTIAL_URL_RE.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                failures.append(f"{relative}:{line}: possible credential-bearing URL")
            for match in IPV4_RE.finditer(text):
                try:
                    address = ipaddress.ip_address(match.group())
                except ValueError:
                    continue
                if any(address in network for network in PRIVATE_NETWORKS):
                    line = text.count("\n", 0, match.start()) + 1
                    failures.append(
                        f"{relative}:{line}: private infrastructure address {address}"
                    )
    if failures:
        print("Repository hygiene check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Repository hygiene check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

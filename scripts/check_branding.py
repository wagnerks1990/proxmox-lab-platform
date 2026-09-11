#!/usr/bin/env python3
"""Reject retired LabGoblin predecessor identifiers in application-owned code.

The current GitHub repository URL is intentionally permitted until the repository
slug itself is renamed. Proxmox VE integration terminology is also legitimate;
this check targets only application-owned predecessor identifiers.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "node_modules", "site", "dist", "build", ".venv", "venv", "__pycache__"}
TEXT_SUFFIXES = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".yml", ".yaml", ".md",
    ".sh", ".ini", ".toml", ".txt", ".service", ".css", ".html", ".env",
}

# These are application-owned predecessor identifiers. Generic Proxmox terms,
# PROXMOX_* integration settings, and Proxmox model/API names are intentionally
# not included.
DISALLOWED = (
    "/opt/proxmox-lab-platform",
    "/var/lib/proxmox-lab-platform",
    "proxmox_lab",
    "plp_session",
    "proxmox-lab-updater",
    "proxmox-lab-runner",
    "proxmox-lab-asset-server",
    "proxmox-lab-iso-server",
    "proxmox-lab-ct-template-server",
    "proxmox-lab-frontend",
    "token_id:'proxmox-lab-platform'",
    'token_id:"proxmox-lab-platform"',
    'TOKEN_ID_DEFAULT = "proxmox-lab-platform"',
)

# Documentation defining the policy must be allowed to name examples of what is
# forbidden. The repository slug also necessarily contains the predecessor name
# until GitHub repository administration renames it.
POLICY_FILES = {Path("docs/brand.md"), Path("AI_CONTEXT.md"), Path("AGENTS.md")}
ALLOWED_REPO_URL = "github.com/wagnerks1990/proxmox-lab-platform"


def iter_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in {"Dockerfile", "Makefile"}:
            yield path, rel


def main() -> int:
    failures: list[tuple[Path, int, str]] = []
    for path, rel in iter_files():
        if rel in POLICY_FILES:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, 1):
            check = line
            if ALLOWED_REPO_URL in check:
                check = check.replace(ALLOWED_REPO_URL, "<CURRENT_REPOSITORY>")
            for retired in DISALLOWED:
                if retired in check:
                    failures.append((rel, number, retired))
    if failures:
        print("Retired LabGoblin predecessor identifiers found:")
        for rel, number, retired in failures:
            print(f"- {rel}:{number}: {retired}")
        return 1
    print("LabGoblin branding identifier check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

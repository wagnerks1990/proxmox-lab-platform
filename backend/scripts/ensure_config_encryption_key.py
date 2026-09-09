#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import secrets
from pathlib import Path


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        values[k.strip()] = v.strip().strip('"').strip("'")
    return values


def main() -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Ensure CONFIG_ENCRYPTION_KEY exists in backend .env"
    )
    parser.add_argument("--env-file", default=str(backend_dir / ".env"))
    parser.add_argument(
        "--create", action="store_true", help="Create env file when missing"
    )
    args = parser.parse_args()

    env_path = Path(args.env_file)
    if not env_path.exists():
        if not args.create:
            print(
                f"ERROR: {env_path} does not exist. Re-run with --create to create it."
            )
            return 1
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text("")

    env_values = parse_env(env_path)
    existing = env_values.get("CONFIG_ENCRYPTION_KEY", "").strip()
    if existing:
        print("CONFIG_ENCRYPTION_KEY already exists. No changes made.")
        return 0

    if env_values.get("APP_SECRET_KEY", "").strip():
        print(
            "APP_SECRET_KEY exists; generating dedicated CONFIG_ENCRYPTION_KEY for Proxmox token encryption."
        )

    generated = secrets.token_urlsafe(48)
    with env_path.open("a", encoding="utf-8") as f:
        if env_path.stat().st_size > 0:
            f.write("\n")
        f.write(f"CONFIG_ENCRYPTION_KEY={generated}\n")

    try:
        os.chmod(env_path, 0o600)
    except Exception:
        print("WARN: Could not set file permissions to 600 on this platform.")

    print("Generated CONFIG_ENCRYPTION_KEY and wrote it to env file.")
    print("Key value is not displayed for safety.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env bash
set -euo pipefail
python3 "$(dirname "$0")/ensure_config_encryption_key.py" "$@"

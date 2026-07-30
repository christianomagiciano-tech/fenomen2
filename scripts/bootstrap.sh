#!/usr/bin/env bash
# Sets up a local development environment for Fenomen 2.
set -euo pipefail

cd "$(dirname "$0")/.."

python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"

echo "Environment ready. Activate with: source .venv/bin/activate"

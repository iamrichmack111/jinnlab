#!/usr/bin/env bash
set -euo pipefail
PREFIX="${HOME}/.local/share/jinnlab"
VENV="${PREFIX}/venv"

# Axelrod is most dependable on mainstream supported Python releases.
if command -v python3.12 >/dev/null 2>&1; then
  PYTHON=python3.12
elif [ -x /opt/homebrew/bin/python3.12 ]; then
  PYTHON=/opt/homebrew/bin/python3.12
else
  PYTHON=python3
fi

echo "Using: $($PYTHON --version)"
rm -rf "$VENV"
"$PYTHON" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/pip" install "$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HOME/.local/bin"
ln -sf "$VENV/bin/jinnlab" "$HOME/.local/bin/jinnlab"
printf '\nInstalled JinnLab 3. Run: jinnlab\n'

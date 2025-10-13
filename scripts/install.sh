#!/usr/bin/env bash
set -euo pipefail

REPO_OWNER=supermarsx
REPO_NAME=writetofillet
FORMULA_URL="https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/refs/heads/main/Formula/${REPO_NAME}.rb"

echo "Installing ${REPO_NAME}..."
if command -v brew >/dev/null 2>&1; then
  echo "Detected Homebrew. Installing via brew formula..."
  brew install "${FORMULA_URL}"
  exit $?
fi

if command -v pipx >/dev/null 2>&1; then
  echo "Detected pipx. Installing from current repo..."
  pipx install .
  exit $?
fi

echo "Falling back to pip editable install from current repo..."
python -m pip install -e .
echo "Installed ${REPO_NAME}. Use 'writetofillet --help' to get started."


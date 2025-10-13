#!/usr/bin/env bash
set -euo pipefail
echo "Updating writetofillet..."
if command -v brew >/dev/null 2>&1; then
  brew upgrade writetofillet || brew install writetofillet
  exit $?
fi
if command -v scoop >/dev/null 2>&1; then
  scoop update
  scoop update writetofillet || scoop install writetofillet
  exit $?
fi
if command -v pipx >/dev/null 2>&1; then
  pipx upgrade writetofillet || true
fi
echo "Checking for latest rolling release:"
writetofillet --check-updates || true


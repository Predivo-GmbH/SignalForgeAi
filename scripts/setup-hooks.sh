#!/bin/bash
# Installs git hooks from scripts/ into .git/hooks/
# Run once after cloning: bash scripts/setup-hooks.sh

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK_SRC="$REPO_ROOT/scripts/pre-commit"
HOOK_DST="$REPO_ROOT/.git/hooks/pre-commit"

cp "$HOOK_SRC" "$HOOK_DST"
echo "Installed pre-commit hook."

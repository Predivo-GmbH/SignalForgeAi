#!/bin/bash
# Run frontend tests on native Linux filesystem for WSL2 performance.
# Usage: bash test-wsl.sh
# The /mnt/c/ filesystem is 10-20x slower than native Linux FS,
# causing vitest worker spawn timeouts. This script copies the
# project to /tmp, installs Linux-native deps, and runs tests there.

set -e

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="/tmp/sf-frontend-test"

echo "==> Syncing to native Linux filesystem..."
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"

# Copy source files (excluding node_modules — we'll install fresh)
rsync -a --exclude node_modules --exclude dist --exclude .vite "$SRC_DIR/" "$WORK_DIR/"

cd "$WORK_DIR"

echo "==> Installing dependencies (Linux-native)..."
npm install --prefer-offline 2>&1 | tail -3

echo "==> Running tests..."
npx vitest run --reporter=verbose "$@"

#!/usr/bin/env bash
# =============================================================================
# SignalForge — Database Backup Script
# Runs daily via cron (set up by deploy.sh)
#
# Creates compressed PostgreSQL dumps and keeps the last 14 days.
# =============================================================================
set -euo pipefail

APP_DIR="/opt/signalforge"
BACKUP_DIR="/opt/signalforge/backups"
RETENTION_DAYS=14
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[BACKUP]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"; }
warn()  { echo -e "${YELLOW}[BACKUP WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"; }
error() { echo -e "${RED}[BACKUP ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"; }

# Create backup directory
mkdir -p "$BACKUP_DIR"

# --- 1. PostgreSQL dump -------------------------------------------------------
info "Starting PostgreSQL backup..."

DUMP_FILE="$BACKUP_DIR/signalforge_${TIMESTAMP}.sql.gz"

docker compose -f "$APP_DIR/docker-compose.prod.yml" exec -T timescaledb \
  pg_dump -U signalforge signalforge | gzip > "$DUMP_FILE"

if [ -s "$DUMP_FILE" ]; then
  DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
  info "PostgreSQL dump: $DUMP_FILE ($DUMP_SIZE)"
else
  error "PostgreSQL dump is empty! Check if the database is running."
  rm -f "$DUMP_FILE"
  exit 1
fi

# --- 1b. Verify backup integrity ---------------------------------------------
info "Verifying backup integrity..."

# Check gzip archive is valid
if ! gunzip -t "$DUMP_FILE" 2>/dev/null; then
  error "Backup file failed gzip integrity check! Archive may be corrupt: $DUMP_FILE"
  exit 1
fi
info "Gzip integrity check: OK"

# Warn if backup is suspiciously small (< 1KB)
DUMP_SIZE_BYTES=$(stat --format="%s" "$DUMP_FILE" 2>/dev/null || stat -
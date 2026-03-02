#!/usr/bin/env bash
# =============================================================================
# SignalForge — Deployment Script
# Run as the 'deploy' user on the Hetzner server.
#
# Usage:
#   First deploy:  bash deploy.sh setup
#   Update/redeploy: bash deploy.sh update
#   Rollback:      bash deploy.sh rollback
# =============================================================================
set -euo pipefail

APP_DIR="/opt/signalforge"
REPO_URL=""  # Set your Git repo URL here (e.g. git@github.com:youruser/day-trading.git)
BRANCH="main"

# Images that are built locally (not pulled from registry)
BUILD_IMAGES=("signalforge-api" "signalforge-worker" "signalforge-beat")

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# --- Helpers ------------------------------------------------------------------

check_env_file() {
  if [ ! -f "$APP_DIR/backend/.env.prod" ]; then
    error "backend/.env.prod not found!\n  Copy the template:\n  cp $APP_DIR/deploy/.env.prod.template $APP_DIR/backend/.env.prod\n  Then edit it with your secrets."
  fi

  # Check for unfilled placeholders
  if grep -q "CHANGE-ME" "$APP_DIR/backend/.env.prod"; then
    error "backend/.env.prod still contains CHANGE-ME placeholders.\n  Edit the file and replace all CHANGE-ME values with real secrets."
  fi
}

generate_secrets_hint() {
  echo ""
  info "Generate your secrets with these commands:"
  echo "  DB password:      openssl rand -base64 24"
  echo "  JWT secret:       python3 -c \"import secrets; print(secrets.token_urlsafe(64))\""
  echo "  Fernet key:       python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
  echo ""
}

tag_current_images_as_previous() {
  info "Tagging current images as :previous for rollback..."
  for img in "${BUILD_IMAGES[@]}"; do
    if docker image inspect "${img}:latest" &>/dev/null; then
      docker tag "${img}:latest" "${img}:previous"
      info "  Tagged ${img}:latest -> ${img}:previous"
    else
      warn "  ${img}:latest not found, skipping tag"
    fi
  done
}

# --- Commands -----------------------------------------------------------------

setup() {
  echo "============================================"
  echo "  SignalForge — First-Time Setup"
  echo "============================================"

  # Step 1: Clone or copy repo
  if [ -n "$REPO_URL" ]; then
    info "Cloning repository..."
    if [ -d "$APP_DIR/.git" ]; then
      info "Repo already cloned, pulling latest..."
      cd "$APP_DIR" && git pull origin "$BRANCH"
    else
      git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
    fi
  else
    if [ ! -f "$APP_DIR/docker-compose.prod.yml" ]; then
      error "No REPO_URL set and no files found in $APP_DIR.\n  Either:\n  a) Set REPO_URL in this script, or\n  b) Manually copy the project to $APP_DIR"
    fi
    info "Using existing files in $APP_DIR (no git repo configured)."
  fi

  cd "$APP_DIR"

  # Step 2: Create .env.prod from template if missing
  if [ ! -f "$APP_DIR/backend/.env.prod" ]; then
    warn "No backend/.env.prod found. Creating from template..."
    cp "$APP_DIR/deploy/.env.prod.template" "$APP_DIR/backend/.env.prod"
    generate_secrets_hint
    error "Edit backend/.env.prod with your secrets, then run this script again."
  fi

  check_env_file

  # Step 3: Build frontend
  info "Building frontend..."
  if command -v node &>/dev/null; then
    cd "$APP_DIR/frontend"
    npm ci --production=false
    npm run build
    cd "$APP_DIR"
  else
    # Use Docker to build frontend if Node not installed
    info "Node.js not found, building frontend via Docker..."
    docker run --rm \
      -v "$APP_DIR/frontend:/app" \
      -w /app \
      node:20-slim \
      sh -c "npm ci && npm run build"
  fi

  # Step 4: Set up Caddy
  info "Configuring Caddy reverse proxy..."
  sudo mkdir -p /var/log/caddy
  sudo cp "$APP_DIR/deploy/Caddyfile" /etc/caddy/Caddyfile
  sudo systemctl restart caddy
  sudo systemctl enable caddy

  # Step 5: Build and start Docker services
  info "Building Docker images (this may take a few minutes on first run)..."
  docker compose -f docker-compose.prod.yml build

  info "Starting services..."
  docker compose -f docker-compose.prod.yml up -d

  # Step 6: Wait for DB to be healthy, then run migrations
  info "Waiting for database to be ready..."
  sleep 10

  info "Running database migrations..."
  docker compose -f docker-compose.prod.yml exec api \
    python -m alembic upgrade head

  # Step 7: Set up backup cron
  info "Setting up daily backup cron job..."
  setup_backup_cron

  # Step 8: Verify
  verify

  echo ""
  echo "============================================"
  echo "  Setup complete!"
  echo "============================================"
  echo ""
  echo "  Your app is running at: http://$(curl -s ifconfig.me)"
  echo ""
  echo "  Useful commands:"
  echo "    View logs:     cd $APP_DIR && docker compose -f docker-compose.prod.yml logs -f"
  echo "    View API logs: cd $APP_DIR && docker compose -f docker-compose.prod.yml logs -f api"
  echo "    Stop all:      cd $APP_DIR && docker compose -f docker-compose.prod.yml down"
  echo "    Redeploy:      bash $APP_DIR/deploy/deploy.sh update"
  echo "    Rollback:      bash $APP_DIR/deploy/deploy.sh rollback"
  echo ""
}

update() {
  echo "============================================"
  echo "  SignalForge — Update Deployment"
  echo "============================================"

  cd "$APP_DIR"
  check_env_file

  # Pull latest code if git is configured
  if [ -d "$APP_DIR/.git" ] && [ -n "$REPO_URL" ]; then
    info "Pulling latest code..."
    git pull origin "$BRANCH"
  fi

  # Rebuild frontend
  info "Rebuilding frontend..."
  if command -v node &>/dev/null; then
    cd "$APP_DIR/frontend" && npm ci && npm run build && cd "$APP_DIR"
  else
    docker run --rm -v "$APP_DIR/frontend:/app" -w /app node:20-slim sh -c "npm ci && npm run build"
  fi

  # Tag current images as :previous before rebuilding
  tag_current_images_as_previous

  # Rebuild and restart Docker services
  info "Rebuilding Docker images..."
  docker compose -f docker-compose.prod.yml build

  info "Restarting services (zero-downtime rolling restart)..."
  docker compose -f docker-compose.prod.yml up -d

  # Run any new migrations
  info "Running database migrations..."
  sleep 5
  docker compose -f docker-compose.prod.yml exec api \
    python -m alembic upgrade head

  # Update Caddy config if changed
  sudo cp "$APP_DIR/deploy/Caddyfile" /etc/caddy/Caddyfile
  sudo systemctl reload caddy

  verify

  echo ""
  info "Update complete!"
}

rollback() {
  echo "============================================"
  echo "  SignalForge — Rollback to Previous Version"
  echo "============================================"

  cd "$APP_DIR"

  # Verify :previous images exist
  local missing=false
  for img in "${BUILD_IMAGES[@]}"; do
    if ! docker image inspect "${img}:previous" &>/dev/null; then
      error "No :previous image found for ${img}. Cannot rollback."
    fi
  done

  # Tag :previous images back to :latest
  info "Restoring previous images..."
  for img in "${BUILD_IMAGES[@]}"; do
    docker tag "${img}:previous" "${img}:latest"
    info "  Restored ${img}:previous -> ${img}:latest"
  done

  # Restart containers with the restored images
  info "Restarting services with previous images..."
  docker compose -f docker-compose.prod.yml up -d

  # Verify health
  verify

  echo ""
  info "Rollback complete! Services are running the previous version."
  warn "If you need to rollback database migrations, do so manually:"
  echo "  docker compose -f docker-compose.prod.yml exec api python -m alembic downgrade -1"
}

verify() {
  echo ""
  info "Verifying services..."

  # Check all containers are running
  local services=("timescaledb" "redis" "api" "worker" "beat")
  local all_ok=true

  for svc in "${services[@]}"; do
    local status
    status=$(docker compose -f docker-compose.prod.yml ps --format '{{.State}}' "$svc" 2>/dev/null || echo "not found")
    if [ "$status" = "running" ]; then
      echo "  $svc: running"
    else
      echo "  $svc: $status"
      all_ok=false
    fi
  done

  # Health check
  sleep 3
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "  API health check: OK"
  else
    warn "API health check failed — it may still be starting up. Check logs:"
    echo "    docker compose -f docker-compose.prod.yml logs api"
    all_ok=false
  fi

  if [ "$all_ok" = true ]; then
    info "All services healthy!"
  else
    warn "Some services may need attention. Check logs above."
  fi
}

setup_backup_cron() {
  local cron_line="0 3 * * * bash $APP_DIR/deploy/backup.sh >> /var/log/signalforge-backup.log 2>&1"

  # Add cron job if not already present
  (crontab -l 2>/dev/null | grep -v "signalforge.*backup" ; echo "$cron_line") | crontab -
  info "Backup cron installed: daily at 03:00 UTC"
}

# --- Entrypoint ---------------------------------------------------------------

case "${1:-help}" in
  setup)    setup ;;
  update)   update ;;
  rollback) rollback ;;
  verify)   verify ;;
  *)
    echo "Usage: bash deploy.sh <command>"
    echo ""
    echo "Commands:"
    echo "  setup    — First-time deployment (clone, build, start, migrate)"
    echo "  update   — Pull latest code, rebuild, restart, migrate"
    echo "  rollback — Revert to previously deployed images"
    echo "  verify   — Check all services are running"
    ;;
esac

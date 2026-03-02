# SignalForge — Hetzner Deployment Guide

Deploy SignalForge to a Hetzner CX33 cloud server running Ubuntu 24.04.

## Prerequisites

- A Hetzner Cloud account → [console.hetzner.com](https://console.hetzner.com)
- An SSH key pair on your local machine (`ssh-keygen -t ed25519` if you don't have one)

---

## Step 1: Order the Server

1. Log into [Hetzner Cloud Console](https://console.hetzner.com)
2. **New Project** → name it "SignalForge"
3. **Add Server** with these settings:

| Setting | Value |
|---------|-------|
| Location | Falkenstein or Nuremberg |
| Image | Ubuntu 24.04 |
| Type | Shared vCPU → **CX33** (4 vCPU, 8 GB, 80 GB) |
| SSH Key | Add your public key (`~/.ssh/id_ed25519.pub`) |
| Name | `signalforge` |

4. Click **Create & Buy Now** (~€5.49/mo)
5. Note the **IP address** shown after creation

---

## Step 2: Initialize the Server

Upload and run the server init script:

```bash
# From your local machine (in the day-trading project directory)
scp deploy/server-init.sh root@YOUR_SERVER_IP:/root/
ssh root@YOUR_SERVER_IP "bash /root/server-init.sh"
```

This script:
- Creates a `deploy` user with your SSH key
- Disables root SSH login and password authentication
- Configures UFW firewall (ports 22, 80, 443 only)
- Installs Docker, Docker Compose, and Caddy
- Enables Fail2Ban and automatic security updates
- Creates `/opt/signalforge/` directory

**After it finishes, root login is disabled.** Use the deploy user from now on:

```bash
ssh deploy@YOUR_SERVER_IP
```

---

## Step 3: Upload the Project

Since you don't have a Git remote set up yet, copy the files manually:

```bash
# From your local machine, in the day-trading project directory
rsync -avz --exclude 'node_modules' --exclude '.venv' --exclude '__pycache__' \
  --exclude '.git' --exclude 'dist' --exclude '.pytest_cache' \
  ./ deploy@YOUR_SERVER_IP:/opt/signalforge/
```

Or if you set up a Git repo later, edit `REPO_URL` in `deploy/deploy.sh` and it will clone automatically.

---

## Step 4: Configure Environment Variables

SSH into the server and create the production environment file:

```bash
ssh deploy@YOUR_SERVER_IP
cd /opt/signalforge

# Copy the template
cp deploy/.env.prod.template backend/.env.prod

# Generate secrets
echo "DB password:"
openssl rand -base64 24

echo "JWT secret:"
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# Note: Fernet key generation requires the cryptography package.
# You can generate it after Docker is running, or use this alternative:
echo "Fernet key:"
python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"

# Edit the file — replace all CHANGE-ME values
nano backend/.env.prod
```

**Required changes in `.env.prod`:**

| Variable | What to set |
|----------|-------------|
| `SF_DATABASE_URL` | Replace `CHANGE-ME-DB-PASSWORD` with your generated DB password |
| `SF_DB_PASSWORD` | Same DB password (used by docker-compose for PostgreSQL) |
| `SF_JWT_SECRET` | Your generated JWT secret |
| `SF_ENCRYPTION_KEY` | Your generated Fernet key |
| `SF_CORS_ORIGINS` | `["http://YOUR_SERVER_IP"]` |

Optional (add later when ready):
- `SF_ANTHROPIC_API_KEY` — for AI advisor + self-learning loop
- `SF_RESEND_API_KEY` — for email alerts

---

## Step 5: Deploy

```bash
bash /opt/signalforge/deploy/deploy.sh setup
```

This will:
1. Build the frontend (via Docker if Node.js isn't installed)
2. Configure Caddy as the reverse proxy
3. Build all Docker images (first build takes ~5 minutes for ta-lib compilation)
4. Start all 5 services (TimescaleDB, Redis, API, Worker, Beat)
5. Run database migrations
6. Set up the daily backup cron job
7. Verify everything is healthy

**When it's done, open your browser:**
```
http://YOUR_SERVER_IP
```

- Frontend password gate: `signalforge`
- Login: `roger@signalforge.dev` / `SignalForge2026` (or register a new account)

---

## Step 6: Verify Everything Works

```bash
# Check all containers are running
cd /opt/signalforge
docker compose -f docker-compose.prod.yml ps

# Expected: 5 services, all "running"
# - timescaledb
# - redis
# - api
# - worker
# - beat

# API health check
curl http://localhost:8000/health

# View real-time logs
docker compose -f docker-compose.prod.yml logs -f

# View specific service logs
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f worker
```

---

## Day-to-Day Operations

### Redeploy after code changes

```bash
# Upload new code (from local machine)
rsync -avz --exclude 'node_modules' --exclude '.venv' --exclude '__pycache__' \
  --exclude '.git' --exclude 'dist' --exclude '.pytest_cache' \
  ./ deploy@YOUR_SERVER_IP:/opt/signalforge/

# SSH in and redeploy
ssh deploy@YOUR_SERVER_IP
bash /opt/signalforge/deploy/deploy.sh update
```

### View logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f api --tail 100
docker compose -f docker-compose.prod.yml logs -f worker --tail 100
```

### Restart a service

```bash
cd /opt/signalforge
docker compose -f docker-compose.prod.yml restart api
docker compose -f docker-compose.prod.yml restart worker
```

### Stop everything

```bash
cd /opt/signalforge
docker compose -f docker-compose.prod.yml down
```

### Start everything

```bash
cd /opt/signalforge
docker compose -f docker-compose.prod.yml up -d
```

### Manual backup

```bash
bash /opt/signalforge/deploy/backup.sh
```

Backups are stored in `/opt/signalforge/backups/` and automatically cleaned after 14 days.

### Restore from backup

```bash
# Stop the API and workers first
cd /opt/signalforge
docker compose -f docker-compose.prod.yml stop api worker beat

# Restore
gunzip -c backups/signalforge_2026-03-15_030000.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T timescaledb \
  psql -U signalforge signalforge

# Restart
docker compose -f docker-compose.prod.yml up -d
```

---

## Adding a Domain Later

When you have a domain (e.g., `signalforge.example.com`):

1. Point your domain's DNS A record to your server IP
2. Edit the Caddyfile:

```bash
sudo nano /etc/caddy/Caddyfile
```

Replace `:80 {` with `signalforge.example.com {` — Caddy will auto-provision Let's Encrypt SSL.

3. Update CORS origins in `backend/.env.prod`:

```
SF_CORS_ORIGINS=["https://signalforge.example.com"]
```

4. Restart:

```bash
sudo systemctl reload caddy
cd /opt/signalforge && docker compose -f docker-compose.prod.yml restart api
```

---

## Architecture on the Server

```
Internet
   │
   ▼
┌──────────────────────────────────┐
│  Caddy (port 80/443)            │
│  - SSL termination              │
│  - /api/* → localhost:8000      │
│  - /ws/*  → localhost:8000      │
│  - /*     → frontend/dist/      │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│  Docker Compose (5 containers)  │
│                                  │
│  ┌─────────┐  ┌──────────────┐  │
│  │  API    │  │  Celery      │  │
│  │ :8000   │  │  Worker (×4) │  │
│  └────┬────┘  └──────┬───────┘  │
│       │              │           │
│       │    ┌─────────┘           │
│       │    │  ┌──────────────┐  │
│       │    │  │  Celery Beat │  │
│       │    │  └──────┬───────┘  │
│       ▼    ▼         ▼           │
│  ┌───────────┐  ┌────────────┐  │
│  │TimescaleDB│  │   Redis    │  │
│  │  :5432    │  │   :6379    │  │
│  └───────────┘  └────────────┘  │
│                                  │
│  (DB ports NOT exposed to host) │
└──────────────────────────────────┘
```

---

## Troubleshooting

### Container won't start
```bash
docker compose -f docker-compose.prod.yml logs <service_name>
```

### API returns 502
- Check if the API container is running: `docker compose -f docker-compose.prod.yml ps api`
- Check API logs: `docker compose -f docker-compose.prod.yml logs api`
- Verify health: `curl http://localhost:8000/health`

### Database connection error
- Check TimescaleDB is healthy: `docker compose -f docker-compose.prod.yml ps timescaledb`
- Verify the password in `.env.prod` matches `SF_DB_PASSWORD`

### Disk space running low
```bash
# Check disk usage
df -h

# Clean Docker build cache
docker system prune -f

# Check backup size
du -sh /opt/signalforge/backups/
```

### Server resource usage
```bash
# Overview
htop

# Docker stats (live CPU/RAM per container)
docker stats
```

---

## Security Checklist

- [x] Root SSH disabled
- [x] Password authentication disabled
- [x] UFW firewall (only 22, 80, 443)
- [x] Fail2Ban on SSH
- [x] Automatic security updates
- [x] Non-root Docker user (appuser in container)
- [x] Database not exposed to internet
- [x] Redis not exposed to internet
- [x] API behind reverse proxy
- [ ] Domain + HTTPS (when you add a domain)
- [ ] Offsite backups (optional — rsync to another server or S3)

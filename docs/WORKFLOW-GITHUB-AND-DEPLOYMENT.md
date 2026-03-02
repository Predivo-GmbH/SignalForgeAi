# SignalForge — GitHub & Deployment Workflow

Step-by-step workflow for publishing to GitHub and later deploying to Hetzner.

---

## Part 1: Push to GitHub

### 1.1 Install and authenticate GitHub CLI

```bash
# Install gh (on Windows, use winget or download from https://cli.github.com)
winget install --id GitHub.cli

# Authenticate
gh auth login
# → Choose: GitHub.com → HTTPS → Login with browser
```

### 1.2 Create the GitHub repository

```bash
cd "/mnt/c/Business/Internal Projects/day-trading"

# Create a private repo on GitHub and set it as origin
gh repo create signalforge --private --source=. --remote=origin

# Verify
git remote -v
# Should show: origin  https://github.com/YOUR_USERNAME/signalforge.git
```

### 1.3 Commit all outstanding changes

```bash
# Review what's changed
git status

# Stage everything (gitignore will exclude secrets and temp files)
git add -A

# Verify nothing sensitive is staged
git diff --cached --name-only | grep -i "env\|secret\|key"
# Should show NO .env.prod files, only .env.example and .env.prod.template

# Commit
git commit -m "feat: add deployment infrastructure, risk management, and UI improvements"

# Push
git push -u origin main
```

### 1.4 Verify on GitHub

```bash
gh repo view --web
# Opens your repo in the browser — verify files look correct
```

### 1.5 Security check

After pushing, verify these files are **NOT** in the repo:
- `backend/.env` (local secrets)
- `backend/.env.prod` (production secrets)
- `.claude/settings.json` (Claude config)
- `celerybeat-schedule*` (runtime files)

These files **SHOULD** be in the repo (safe templates):
- `backend/.env.example` (no real values)
- `deploy/.env.prod.template` (CHANGE-ME placeholders)

---

## Part 2: Deploy to Hetzner (When Ready)

Follow these steps when the application is finished and you're ready to go live.

### 2.1 Prerequisites

- [ ] Application is feature-complete and tested locally
- [ ] All code is committed and pushed to GitHub
- [ ] You have a Hetzner Cloud account
- [ ] You have an SSH key pair (`ssh-keygen -t ed25519`)

### 2.2 Order the server

1. Log into [console.hetzner.com](https://console.hetzner.com)
2. Create project "SignalForge"
3. Add Server:
   - **Location:** Falkenstein or Nuremberg
   - **Image:** Ubuntu 24.04
   - **Type:** Shared vCPU → **CX33** (4 vCPU, 8 GB RAM, 80 GB NVMe) — ~€5.49/mo
   - **SSH Key:** Add your public key
   - **Name:** `signalforge`
4. Note the IP address

### 2.3 Initialize the server

```bash
# Upload and run the init script
scp deploy/server-init.sh root@YOUR_SERVER_IP:/root/
ssh root@YOUR_SERVER_IP "bash /root/server-init.sh"
```

After this, root login is disabled. Use `deploy` user:
```bash
ssh deploy@YOUR_SERVER_IP
```

### 2.4 Deploy the application

**Option A: From GitHub (recommended)**

Edit `deploy/deploy.sh` — set `REPO_URL` to your GitHub repo:
```bash
REPO_URL="git@github.com:YOUR_USERNAME/signalforge.git"
```

Then on the server:
```bash
bash /opt/signalforge/deploy/deploy.sh setup
```

**Option B: Manual rsync (no GitHub needed)**

```bash
# From your local machine
rsync -avz --exclude 'node_modules' --exclude '.venv' --exclude '__pycache__' \
  --exclude '.git' --exclude 'dist' --exclude '.pytest_cache' \
  ./ deploy@YOUR_SERVER_IP:/opt/signalforge/
```

Then on the server:
```bash
bash /opt/signalforge/deploy/deploy.sh setup
```

### 2.5 Configure secrets

```bash
ssh deploy@YOUR_SERVER_IP
cp /opt/signalforge/deploy/.env.prod.template /opt/signalforge/backend/.env.prod
nano /opt/signalforge/backend/.env.prod
# Fill in all CHANGE-ME values (see DEPLOYMENT-GUIDE.md for details)
```

### 2.6 Verify

```bash
# On the server
bash /opt/signalforge/deploy/deploy.sh verify

# From your browser
http://YOUR_SERVER_IP
```

### 2.7 Add domain + SSL (optional, when ready)

1. Point DNS A record → server IP
2. Edit `/etc/caddy/Caddyfile`: replace `:80` with `yourdomain.com`
3. Update `SF_CORS_ORIGINS` in `.env.prod`
4. `sudo systemctl reload caddy`

---

## Part 3: Ongoing Workflow

### Making changes

```
Local development → git commit → git push → ssh in → deploy.sh update
```

### Monitoring

```bash
# Live logs
ssh deploy@YOUR_SERVER_IP
cd /opt/signalforge
docker compose -f docker-compose.prod.yml logs -f

# Resource usage
docker stats
```

### Backups

- Automatic: daily at 03:00 UTC (cron), kept for 14 days
- Manual: `bash /opt/signalforge/deploy/backup.sh`
- Stored in: `/opt/signalforge/backups/`

---

## File Reference

| File | Purpose |
|------|---------|
| `deploy/server-init.sh` | One-time server hardening + Docker + Caddy install |
| `deploy/deploy.sh` | Deploy (`setup`) and update (`update`) commands |
| `deploy/backup.sh` | PostgreSQL backup with 14-day retention |
| `deploy/.env.prod.template` | Production env vars template (safe to commit) |
| `deploy/Caddyfile` | Reverse proxy config (IP-only, domain-ready) |
| `docker-compose.prod.yml` | Production Docker services (5 containers) |
| `docs/DEPLOYMENT-GUIDE.md` | Detailed deployment walkthrough |

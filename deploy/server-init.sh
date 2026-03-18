#!/usr/bin/env bash
# =============================================================================
# SignalForgeAI — Server Initialization Script
# Run this ONCE on a fresh Hetzner CX33 (Ubuntu 24.04)
#
# Usage:
#   1. SSH in as root:  ssh root@<YOUR_SERVER_IP>
#   2. Upload this file: scp deploy/server-init.sh root@<IP>:/root/
#   3. Run it:           bash /root/server-init.sh
# =============================================================================
set -euo pipefail

# --- Configuration -----------------------------------------------------------
DEPLOY_USER="deploy"
SSH_PORT=22  # Change to a non-standard port if desired (e.g. 2222)

echo "============================================"
echo "  SignalForgeAI — Server Init"
echo "============================================"

# --- 1. System updates -------------------------------------------------------
echo "[1/7] Updating system packages..."
apt-get update -qq && apt-get upgrade -y -qq
apt-get install -y -qq \
  curl wget git ufw fail2ban unattended-upgrades \
  apt-transport-https ca-certificates gnupg lsb-release

# --- 2. Create deploy user ---------------------------------------------------
echo "[2/7] Creating deploy user..."
if id "$DEPLOY_USER" &>/dev/null; then
  echo "  User '$DEPLOY_USER' already exists, skipping."
else
  adduser --disabled-password --gecos "" "$DEPLOY_USER"
  usermod -aG sudo "$DEPLOY_USER"
  # Allow sudo without password for deploy user
  echo "$DEPLOY_USER ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$DEPLOY_USER

  # Copy root's SSH keys to deploy user
  mkdir -p /home/$DEPLOY_USER/.ssh
  cp /root/.ssh/authorized_keys /home/$DEPLOY_USER/.ssh/
  chown -R $DEPLOY_USER:$DEPLOY_USER /home/$DEPLOY_USER/.ssh
  chmod 700 /home/$DEPLOY_USER/.ssh
  chmod 600 /home/$DEPLOY_USER/.ssh/authorized_keys
  echo "  User '$DEPLOY_USER' created with SSH key from root."
fi

# --- 3. SSH hardening --------------------------------------------------------
echo "[3/7] Hardening SSH..."
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#\?ChallengeResponseAuthentication.*/ChallengeResponseAuthentication no/' /etc/ssh/sshd_config
sed -i "s/^#\?Port.*/Port $SSH_PORT/" /etc/ssh/sshd_config
systemctl restart sshd
echo "  SSH: root login disabled, password auth disabled, port=$SSH_PORT"

# --- 4. Firewall (UFW) -------------------------------------------------------
echo "[4/7] Configuring firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow $SSH_PORT/tcp comment "SSH"
ufw allow 80/tcp comment "HTTP"
ufw allow 443/tcp comment "HTTPS"
ufw --force enable
echo "  Firewall: only SSH($SSH_PORT), HTTP(80), HTTPS(443) open"

# --- 5. Fail2Ban -------------------------------------------------------------
echo "[5/7] Configuring Fail2Ban..."
cat > /etc/fail2ban/jail.local << 'JAIL'
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 5
bantime = 3600
findtime = 600
JAIL
systemctl enable fail2ban
systemctl restart fail2ban

# --- 6. Install Docker -------------------------------------------------------
echo "[6/7] Installing Docker..."
if command -v docker &>/dev/null; then
  echo "  Docker already installed: $(docker --version)"
else
  curl -fsSL https://get.docker.com | sh
  usermod -aG docker $DEPLOY_USER
  systemctl enable docker
  echo "  Docker installed: $(docker --version)"
fi

# Verify Docker Compose plugin
if docker compose version &>/dev/null; then
  echo "  Docker Compose: $(docker compose version)"
else
  echo "  WARNING: Docker Compose plugin not found. Install it manually."
fi

# --- 7. Install Caddy (reverse proxy) ----------------------------------------
echo "[7/7] Installing Caddy..."
if command -v caddy &>/dev/null; then
  echo "  Caddy already installed: $(caddy version)"
else
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
    gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
    tee /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -qq
  apt-get install -y -qq caddy
  echo "  Caddy installed: $(caddy version)"
fi

# --- 8. Enable automatic security updates ------------------------------------
echo "[+] Enabling automatic security updates..."
cat > /etc/apt/apt.conf.d/20auto-upgrades << 'AUTOUPGRADE'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
AUTOUPGRADE

# --- 9. Create app directory --------------------------------------------------
echo "[+] Creating application directory..."
mkdir -p /opt/signalforge
chown $DEPLOY_USER:$DEPLOY_USER /opt/signalforge

# --- Done --------------------------------------------------------------------
echo ""
echo "============================================"
echo "  Server init complete!"
echo "============================================"
echo ""
echo "  Next steps:"
echo "  1. Log out:    exit"
echo "  2. Log back in as deploy user:"
echo "     ssh deploy@<YOUR_SERVER_IP> -p $SSH_PORT"
echo "  3. Run the deploy script:"
echo "     bash /opt/signalforge/deploy/deploy.sh"
echo ""
echo "  IMPORTANT: Root SSH is now DISABLED."
echo "  Use 'deploy' user for all future access."
echo ""

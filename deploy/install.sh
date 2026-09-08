#!/bin/sh
set -eu

REPOSITORY=${UPDATER_REPOSITORY:-https://github.com/wagnerks1990/proxmox-lab-platform.git}
BRANCH=${PLATFORM_BRANCH:-main}
INSTALL_ROOT=/opt/proxmox-lab-platform
ALLOW_PVE=false

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repository) REPOSITORY=$2; shift 2 ;;
    --branch) BRANCH=$2; shift 2 ;;
    --allow-proxmox-host) ALLOW_PVE=true; shift ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this installer as root." >&2
  exit 1
fi

if command -v pveversion >/dev/null 2>&1 && [ "$ALLOW_PVE" != true ]; then
  echo "A Proxmox VE host was detected. A dedicated Debian/Ubuntu VM is recommended." >&2
  echo "Re-run with --allow-proxmox-host only if you accept installing Docker on the hypervisor." >&2
  exit 1
fi

. /etc/os-release
case "${ID:-}" in
  debian|ubuntu) ;;
  *) echo "Only current Debian and Ubuntu hosts are supported." >&2; exit 1 ;;
esac

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl git openssl docker.io
if ! DEBIAN_FRONTEND=noninteractive apt-get install -y docker-compose-v2; then
  DEBIAN_FRONTEND=noninteractive apt-get install -y docker-compose-plugin
fi
systemctl enable --now docker

if ! getent group proxmox-lab-updater >/dev/null; then
  groupadd --system proxmox-lab-updater
fi
UPDATER_GID=$(getent group proxmox-lab-updater | cut -d: -f3)
mkdir -p "$INSTALL_ROOT" /var/lib/proxmox-lab-platform/backups /run/proxmox-lab-updater
chown root:proxmox-lab-updater /run/proxmox-lab-updater
chmod 0750 /run/proxmox-lab-updater
if [ ! -d "$INSTALL_ROOT/app/.git" ]; then
  git clone --branch "$BRANCH" --single-branch "$REPOSITORY" "$INSTALL_ROOT/app"
else
  echo "Existing deployment found; use the updater instead of reinstalling." >&2
  exit 1
fi

cd "$INSTALL_ROOT/app"
umask 077
POSTGRES_PASSWORD=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 48)
CONFIG_ENCRYPTION_KEY=$(openssl rand -hex 48)
UPDATER_TOKEN=$(openssl rand -hex 48)
BOOTSTRAP_ADMIN_TOKEN=$(openssl rand -hex 32)
cat > .env <<EOF
POSTGRES_DB=proxmox_lab
POSTGRES_USER=proxmox_lab
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
JWT_SECRET_KEY=$JWT_SECRET_KEY
CONFIG_ENCRYPTION_KEY=$CONFIG_ENCRYPTION_KEY
UPDATER_TOKEN=$UPDATER_TOKEN
BOOTSTRAP_ADMIN_TOKEN=$BOOTSTRAP_ADMIN_TOKEN
UPDATER_REPOSITORY=$REPOSITORY
UPDATER_GID=$UPDATER_GID
HTTP_PORT=8080
PROXMOX_VERIFY_SSL=true
AUTH_COOKIE_SECURE=false
CORS_ALLOWED_ORIGINS=
UPDATER_ALLOW_AUTOMATIC=false
UPDATER_REQUIRE_SIGNED_COMMITS=false
EOF
chmod 0600 .env

install -m 0755 deploy/updater_agent.py /usr/local/lib/proxmox-lab-updater.py
install -m 0644 deploy/proxmox-lab-updater.service /etc/systemd/system/proxmox-lab-updater.service
systemctl daemon-reload
systemctl enable --now proxmox-lab-updater.service
docker compose --env-file .env up -d --build

attempt=0
until curl -fsS http://127.0.0.1:8080/api/ready >/dev/null; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 60 ]; then
    docker compose --env-file .env ps
    echo "Installation started but the health gate failed." >&2
    exit 1
  fi
  sleep 3
done

echo "Proxmox Lab Platform is available at http://$(hostname -I | awk '{print $1}'):8080"
echo "Open the site and create the first administrator with this one-time bootstrap token:"
echo "$BOOTSTRAP_ADMIN_TOKEN"
echo "The token is also stored in $INSTALL_ROOT/app/.env (mode 0600). Remove it after enrollment."
echo "Then configure Proxmox credentials in the web administration interface."

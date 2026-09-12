#!/bin/sh
set -eu

# Configure a remotely managed, named Cloudflare Tunnel without putting its
# token in the command line, Compose environment, database, or application.
#
# Enable:
#   sudo deploy/configure-cloudflare.sh enable \
#     --hostname lab.example.edu \
#     --team-domain school.cloudflareaccess.com \
#     --audience 0123456789abcdef0123456789abcdef \
#     --token-file /root/cloudflare-tunnel-token
#
# Disable while retaining the protected token for an easy re-enable:
#   sudo deploy/configure-cloudflare.sh disable
# Add --remove-token to delete the installed token during disable.
# `status` reports configuration booleans but never prints the token.

APP_DIR=${LABGOBLIN_APP_DIR:-/opt/labgoblin/app}
TOKEN_DEST=${LABGOBLIN_CLOUDFLARE_TOKEN_FILE:-/etc/labgoblin/cloudflare-tunnel-token}
CLOUDFLARE_GROUP=labgoblin-cloudflared
JWKS_TTL=3600
MODE=${1:-}
[ "$#" -gt 0 ] && shift

usage() {
  echo "Usage:" >&2
  echo "  $0 enable --hostname HOST --team-domain TEAM.cloudflareaccess.com --audience AUD --token-file PATH [--jwks-ttl-seconds SECONDS] [--app-dir DIR]" >&2
  echo "  $0 disable [--remove-token] [--app-dir DIR]" >&2
  echo "  $0 status [--app-dir DIR]" >&2
  exit 2
}

HOSTNAME_VALUE=
TEAM_DOMAIN=
AUDIENCE=
TOKEN_SOURCE=
REMOVE_TOKEN=false

while [ "$#" -gt 0 ]; do
  case "$1" in
    --hostname) HOSTNAME_VALUE=${2:-}; shift 2 ;;
    --team-domain) TEAM_DOMAIN=${2:-}; shift 2 ;;
    --audience) AUDIENCE=${2:-}; shift 2 ;;
    --token-file) TOKEN_SOURCE=${2:-}; shift 2 ;;
    --jwks-ttl-seconds) JWKS_TTL=${2:-}; shift 2 ;;
    --app-dir) APP_DIR=${2:-}; shift 2 ;;
    --remove-token) REMOVE_TOKEN=true; shift ;;
    *) usage ;;
  esac
done

[ "$(id -u)" -eq 0 ] || { echo "Run this command as root." >&2; exit 1; }
case "$MODE" in enable|disable|status) ;; *) usage ;; esac

ENV_FILE=$APP_DIR/.env
[ -f "$ENV_FILE" ] || { echo "Missing LabGoblin environment file: $ENV_FILE" >&2; exit 1; }
[ -f "$APP_DIR/docker-compose.yml" ] || { echo "Missing docker-compose.yml under $APP_DIR" >&2; exit 1; }

BEGIN_MARKER='# BEGIN LABGOBLIN CLOUDFLARE (managed by configure-cloudflare.sh)'
END_MARKER='# END LABGOBLIN CLOUDFLARE'

managed_block_count() {
  awk -v begin="$BEGIN_MARKER" -v end="$END_MARKER" '
    $0 == begin { begins += 1 }
    $0 == end { ends += 1 }
    END { print begins + 0, ends + 0 }
  ' "$ENV_FILE"
}

remove_managed_block() {
  source_file=$1
  destination=$2
  awk -v begin="$BEGIN_MARKER" -v end="$END_MARKER" '
    $0 == begin { skipping = 1; next }
    $0 == end { skipping = 0; next }
    !skipping { print }
  ' "$source_file" > "$destination"
}

validate_existing_block() {
  counts=$(managed_block_count)
  [ "$counts" = "0 0" ] || [ "$counts" = "1 1" ] || {
    echo "Refusing to edit malformed or duplicate managed Cloudflare block in $ENV_FILE" >&2
    exit 1
  }
}

status() {
  enabled=false
  access_required=false
  public_hostname=
  while IFS='=' read -r key value; do
    case "$key" in
      CLOUDFLARE_TUNNEL_ENABLED) enabled=$value ;;
      CLOUDFLARE_ACCESS_REQUIRED) access_required=$value ;;
      CLOUDFLARE_PUBLIC_HOSTNAME) public_hostname=$value ;;
    esac
  done < "$ENV_FILE"
  echo "Tunnel enabled: $enabled"
  echo "Access required: $access_required"
  echo "Public hostname: ${public_hostname:-not configured}"
  if [ -f "$TOKEN_DEST" ]; then
    echo "Tunnel token file: installed"
  else
    echo "Tunnel token file: not installed"
  fi
}

if [ "$MODE" = status ]; then
  status
  exit 0
fi

validate_existing_block
umask 077
ENV_NEXT=$(mktemp "$APP_DIR/.env.cloudflare.XXXXXX")
ENV_BACKUP=$(mktemp "$APP_DIR/.env.cloudflare-backup.XXXXXX")
TOKEN_BACKUP=
TOKEN_STAGE=
cleanup() {
  rm -f "$ENV_NEXT" "$ENV_BACKUP"
  [ -z "$TOKEN_BACKUP" ] || rm -f "$TOKEN_BACKUP"
  [ -z "$TOKEN_STAGE" ] || rm -f "$TOKEN_STAGE"
}
trap cleanup EXIT HUP INT TERM
cp -p "$ENV_FILE" "$ENV_BACKUP"
remove_managed_block "$ENV_FILE" "$ENV_NEXT"

if [ "$MODE" = enable ]; then
  printf '%s' "$HOSTNAME_VALUE" | grep -Eq '^[A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z][A-Za-z0-9-]*$' || {
    echo "--hostname must be a valid fully qualified DNS hostname." >&2; exit 1;
  }
  printf '%s' "$TEAM_DOMAIN" | grep -Eq '^[A-Za-z0-9][A-Za-z0-9-]{0,62}\.cloudflareaccess\.com$' || {
    echo "--team-domain must be a <team>.cloudflareaccess.com hostname." >&2; exit 1;
  }
  printf '%s' "$AUDIENCE" | grep -Eq '^[A-Za-z0-9_-]{8,128}$' || {
    echo "--audience is not a valid Cloudflare Access application audience." >&2; exit 1;
  }
  printf '%s' "$JWKS_TTL" | grep -Eq '^[0-9]+$' || {
    echo "--jwks-ttl-seconds must be an integer." >&2; exit 1;
  }
  [ "$JWKS_TTL" -ge 60 ] && [ "$JWKS_TTL" -le 86400 ] || {
    echo "--jwks-ttl-seconds must be between 60 and 86400." >&2; exit 1;
  }
  [ -f "$TOKEN_SOURCE" ] || { echo "--token-file must name a readable regular file." >&2; exit 1; }
  token=$(tr -d '\r\n' < "$TOKEN_SOURCE")
  [ -n "$token" ] && [ "$(wc -c < "$TOKEN_SOURCE")" -le 8192 ] || {
    echo "Tunnel token file is empty or unexpectedly large." >&2; exit 1;
  }
  printf '%s' "$token" | grep -Eq '^[A-Za-z0-9._-]+$' || {
    echo "Tunnel token file contains invalid characters." >&2; exit 1;
  }
  {
    printf '\n%s\n' "$BEGIN_MARKER"
    echo 'CLOUDFLARE_TUNNEL_ENABLED=true'
    echo "CLOUDFLARE_TUNNEL_TOKEN_FILE=$TOKEN_DEST"
    echo "CLOUDFLARE_PUBLIC_HOSTNAME=$HOSTNAME_VALUE"
    echo 'HTTP_BIND_ADDRESS=127.0.0.1'
    echo 'AUTH_COOKIE_SECURE=true'
    echo 'CORS_ALLOWED_ORIGINS='
    echo "BROWSER_TRUSTED_ORIGINS=https://$HOSTNAME_VALUE"
    echo 'CLOUDFLARE_ACCESS_REQUIRED=true'
    echo "CLOUDFLARE_ACCESS_TEAM_DOMAIN=$TEAM_DOMAIN"
    echo "CLOUDFLARE_ACCESS_AUDIENCE=$AUDIENCE"
    echo "CLOUDFLARE_ACCESS_JWKS_TTL_SECONDS=$JWKS_TTL"
    echo "$END_MARKER"
  } >> "$ENV_NEXT"
  docker compose --env-file "$ENV_NEXT" --project-directory "$APP_DIR" --profile cloudflare config --quiet
  install -d -o root -g root -m 0700 "$(dirname "$TOKEN_DEST")"
  if ! getent group "$CLOUDFLARE_GROUP" >/dev/null; then
    groupadd --system "$CLOUDFLARE_GROUP"
  fi
  CLOUDFLARE_GID=$(getent group "$CLOUDFLARE_GROUP" | cut -d: -f3)
  printf '%s' "$CLOUDFLARE_GID" | grep -Eq '^[0-9]+$' || {
    echo "Unable to resolve the $CLOUDFLARE_GROUP system group." >&2; exit 1;
  }
  if [ -f "$TOKEN_DEST" ]; then
    TOKEN_BACKUP=$(mktemp "$(dirname "$TOKEN_DEST")/.cloudflare-token.XXXXXX")
    cp -p "$TOKEN_DEST" "$TOKEN_BACKUP"
  fi
  TOKEN_STAGE=$(mktemp "$(dirname "$TOKEN_DEST")/.cloudflare-token-stage.XXXXXX")
  install -o root -g "$CLOUDFLARE_GID" -m 0440 "$TOKEN_SOURCE" "$TOKEN_STAGE"
  mv "$TOKEN_STAGE" "$TOKEN_DEST"
  TOKEN_STAGE=
  unset token
  sed -i "/^$END_MARKER$/i CLOUDFLARE_TUNNEL_GID=$CLOUDFLARE_GID" "$ENV_NEXT"
  chmod 0600 "$ENV_NEXT"
  mv "$ENV_NEXT" "$ENV_FILE"
  if ! docker compose --env-file "$ENV_FILE" --project-directory "$APP_DIR" --profile cloudflare up -d --force-recreate api web cloudflared; then
    cp -p "$ENV_BACKUP" "$ENV_FILE"
    if [ -n "$TOKEN_BACKUP" ]; then
      cp -p "$TOKEN_BACKUP" "$TOKEN_DEST"
    else
      rm -f "$TOKEN_DEST"
    fi
    docker compose --env-file "$ENV_FILE" --project-directory "$APP_DIR" up -d --force-recreate api web || true
    echo "Cloudflare startup failed; the previous environment was restored." >&2
    exit 1
  fi
  echo "Cloudflare Tunnel is enabled for https://$HOSTNAME_VALUE."
  echo "The origin is bound to loopback; keep Cloudflare Access enabled at the edge."
else
  docker compose --env-file "$ENV_FILE" --project-directory "$APP_DIR" --profile cloudflare stop cloudflared >/dev/null 2>&1 || true
  chmod 0600 "$ENV_NEXT"
  mv "$ENV_NEXT" "$ENV_FILE"
  if ! docker compose --env-file "$ENV_FILE" --project-directory "$APP_DIR" up -d --force-recreate api web; then
    cp -p "$ENV_BACKUP" "$ENV_FILE"
    docker compose --env-file "$ENV_FILE" --project-directory "$APP_DIR" --profile cloudflare up -d --force-recreate api web cloudflared || true
    echo "Cloudflare disable failed; the enabled environment was restored." >&2
    exit 1
  fi
  docker compose --env-file "$ENV_FILE" --project-directory "$APP_DIR" --profile cloudflare rm -f cloudflared >/dev/null 2>&1 || true
  if [ "$REMOVE_TOKEN" = true ]; then
    rm -f "$TOKEN_DEST"
    echo "Cloudflare Tunnel is disabled and its installed token was removed."
  else
    echo "Cloudflare Tunnel is disabled. Its protected token was retained."
  fi
fi

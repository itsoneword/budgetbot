#!/bin/bash
# BudgetBot deploy wrapper (dv-6caa). Encodes the prod compose incantation so
# nobody has to remember the overlay/env-file flags.
#
#   ./deploy.sh           prod deploy: overlay, secrets file, no exposed DB port
#   ./deploy.sh --dev     dev deploy: base compose only (Postgres on 127.0.0.1:5432)
#   ./deploy.sh --config  print the merged prod compose config and exit
set -euo pipefail
cd "$(dirname "$0")"

SECRETS=/home/cleversol/.claude/service-secrets/budgetbot.env
PROD_ARGS=(--env-file "$SECRETS" -f docker-compose.yml -f docker-compose.prod.yml)

case "${1:-}" in
  --dev)
    docker compose up -d --build
    exit 0
    ;;
  --config)
    docker compose "${PROD_ARGS[@]}" config
    exit 0
    ;;
  "") ;;
  *)
    echo "Usage: ./deploy.sh [--dev|--config]" >&2
    exit 1
    ;;
esac

# Preflight: secrets file must exist and be private.
if [ ! -f "$SECRETS" ]; then
  echo "ERROR: $SECRETS missing. Create it with API_KEY, POSTGRES_PASSWORD, ADMIN_USER_ID (chmod 600)." >&2
  exit 1
fi
if [ "$(stat -c '%a' "$SECRETS")" != "600" ]; then
  echo "ERROR: $SECRETS must be chmod 600 (is $(stat -c '%a' "$SECRETS"))." >&2
  exit 1
fi

docker compose "${PROD_ARGS[@]}" up -d --build

# Wait for the bot healthcheck (heartbeat file, start_period 180s covers
# alembic upgrade + slow first boot).
echo "Waiting for budgetbot-container to become healthy..."
for _ in $(seq 1 40); do
  status=$(docker inspect --format '{{.State.Health.Status}}' budgetbot-container 2>/dev/null || echo starting)
  if [ "$status" = "healthy" ]; then
    echo "budgetbot-container is healthy."
    docker logs --tail 20 budgetbot-container
    exit 0
  fi
  sleep 10
done
echo "ERROR: container did not become healthy in time (status: $status). Recent logs:" >&2
docker logs --tail 50 budgetbot-container >&2
exit 1

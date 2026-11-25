#!/usr/bin/env bash
# Build the image (runs the full data pipeline and tests), start the
# dashboard, wait for the health check, then stream logs. Ctrl+C stops it.
#
# Settings come from .env if present, or the environment:
#   PORT       host port for the dashboard   (default 8000)
#   PGA_YEARS  seasons to download            (default 2022-2025)
set -euo pipefail

cd "$(dirname "$0")"

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

PORT="${PORT:-8000}"
PGA_YEARS="${PGA_YEARS:-2022-2025}"
IMAGE="pga-tour-stats-pipeline"
CONTAINER="pga-tour-stats-pipeline"
HEALTH_TIMEOUT=30  # seconds

if lsof -tiTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port ${PORT} is already in use. Free it, or pick another: PORT=8001 ./run.sh" >&2
  exit 1
fi

# Remove a container left over from a previous run of this script.
docker rm -f "${CONTAINER}" >/dev/null 2>&1 || true

echo "Building image (seasons: ${PGA_YEARS})..."
docker build --build-arg PGA_YEARS="${PGA_YEARS}" -t "${IMAGE}" .

echo "Starting container on port ${PORT}..."
docker run -d --rm --name "${CONTAINER}" -p "${PORT}:8000" "${IMAGE}" >/dev/null
trap 'docker stop "${CONTAINER}" >/dev/null 2>&1 || true' EXIT

echo -n "Waiting for health check"
for ((i = 0; i < HEALTH_TIMEOUT; i++)); do
  if curl -sf "http://localhost:${PORT}/health" >/dev/null; then
    echo " ok"
    echo
    echo "Dashboard running at http://localhost:${PORT}  (Ctrl+C to stop)"
    echo
    docker logs -f "${CONTAINER}"
    exit 0
  fi
  echo -n "."
  sleep 1
done

echo
echo "Health check failed after ${HEALTH_TIMEOUT}s. Container logs:" >&2
docker logs "${CONTAINER}" >&2
exit 1

#!/bin/sh
set -eu

# Require explicit token outside local dev (compose sets a default there only).
TOKEN="${JUPYTER_TOKEN:-}"
if [ -z "$TOKEN" ]; then
  echo "jupyter: JUPYTER_TOKEN must be set" >&2
  exit 1
fi

exec jupyter lab \
  --ip=0.0.0.0 \
  --port=8888 \
  --no-browser \
  --allow-root \
  --ServerApp.token="$TOKEN" \
  --ServerApp.allow_origin='*'

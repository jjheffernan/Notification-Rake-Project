#!/usr/bin/env bash
# Post-deploy smoke checks (bash + curl only). Usage: smoke_deploy.sh [BASE_URL]

set -uo pipefail

BASE_URL="${1:-http://127.0.0.1:8000}"
BASE_URL="${BASE_URL%/}"

FAIL=0

check() {
  local name="$1"
  local path="$2"
  local code
  code=$(curl -sS -o /dev/null -w "%{http_code}" "${BASE_URL}${path}" 2>/dev/null) || code="000"
  if [[ "$code" == "200" ]]; then
    echo "PASS  $name (HTTP $code)"
  else
    echo "FAIL  $name (HTTP $code)"
    FAIL=$((FAIL + 1))
  fi
}

check "GET /health" "/health"
check "GET /" "/"

echo
if [[ "$FAIL" -eq 0 ]]; then
  echo "Smoke: all checks passed"
  exit 0
fi

echo "Smoke: $FAIL check(s) failed"
exit 1

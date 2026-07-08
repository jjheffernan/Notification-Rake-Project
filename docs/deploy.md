# Deployment

Wiki: [Deployment](wiki/Deployment.md). Setup: [Setup-and-Quick-Start](wiki/Setup-and-Quick-Start.md).

## Local

```bash
cp .env.example .env
docker compose up -d
docker compose --profile dev-tools up -d jupyter
```

## Coolify on Proxmox

```text
Proxmox → LXC with Coolify → deploy/coolify/docker-compose.yml
```

1. Install [Coolify](https://coolify.io/docs) on LXC/VM.
2. Docker Compose resource → `deploy/coolify/docker-compose.yml`.
3. Set secrets in Coolify UI — [`SECURITY.md`](../SECURITY.md).
4. Traefik: Hasura + Gotify only. No public DB or Jupyter.
5. Optional: `COOLIFY_WEBHOOK` GitHub secret for auto-redeploy on `main`.

## Hasura bootstrap

Track `vehicle_listing`, `vehicle_make`, `vehicle_model` in console after first deploy.

## Post-deploy smoke

After deploy (or local `docker compose up`):

```bash
./scripts/ops/smoke_deploy.sh                    # default http://127.0.0.1:8000
./scripts/ops/smoke_deploy.sh https://staging.example
```

Checks `GET /health` and `GET /`; exits non-zero on failure.

## CI/CD

`.github/workflows/ci.yml` — lint, pytest, Docker build on PR/push; webhook deploy on `main`.

## Scale path (later)

MVP → add Redis/worker → OpenSearch → OpenStack. Not in repo yet.

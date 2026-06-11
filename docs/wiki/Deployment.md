# Deployment

## Local / dev

See [Setup-and-Quick-Start](Setup-and-Quick-Start).

Always tear down when finished:

```bash
make down
```

## Production considerations

- Change all `change-me` secrets in `.env`
- Do not expose Postgres, Adminer, Jupyter, or Prometheus publicly
- Hasura: restrict admin secret; use allowlists if exposing GraphQL
- Dashboard: strong `DASHBOARD_SECRET_KEY` and admin password
- Review [SECURITY.md](https://github.com/jjheffernan/Notification-Rake-Project/blob/main/SECURITY.md) in repo root

## Coolify on Proxmox

```text
Proxmox → LXC with Coolify → deploy/coolify/docker-compose.yml
```

1. Install [Coolify](https://coolify.io/docs) on LXC/VM.
2. Create Docker Compose resource pointing at `deploy/coolify/docker-compose.yml`.
3. Set secrets in Coolify UI.
4. Traefik: expose Hasura + Gotify only; keep DB and Jupyter internal.
5. Optional: `COOLIFY_WEBHOOK` GitHub secret for auto-redeploy on `main`.

## Hasura bootstrap

After first deploy, track tables in Hasura console or run:

```bash
make run CMD=hasura_track
```

## CI/CD

`.github/workflows/ci.yml`:

- Lint (ruff)
- pytest
- Docker build on PR/push
- Webhook deploy on `main` (if configured)

## Scale path (future)

Redis/worker queue → OpenSearch → dedicated ingest workers. Not in MVP repo.

## Dashboard process

Production container command:

```text
gunicorn notification_rake.web:app --bind 0.0.0.0:8000 --workers 2
```

Defined in `docker/Dockerfile` dashboard target.

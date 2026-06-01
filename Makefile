# Synced with pyproject.toml [tool.notification-rake] and docker-compose.yml
COMPOSE := docker compose
COMPOSE_FILE := docker-compose.yml
CORE_SERVICES := db hasura gotify meilisearch dashboard
DEV_PROFILE := dev-tools
DEFAULT_CMD := health

.PHONY: install-skills up down stop jupyter test lint check docker-build docker-check run scripts reset-gotify reset-db

install-skills:
	.agent/scripts/install.sh

up:
	$(COMPOSE) up -d $(CORE_SERVICES)

down stop:
	$(COMPOSE) --profile $(DEV_PROFILE) down --remove-orphans

jupyter:
	$(COMPOSE) --profile $(DEV_PROFILE) up -d jupyter

test:
	@test -d .venv || python3 -m venv .venv
	.venv/bin/pip install -q ".[dev]"
	.venv/bin/pytest -q --tb=short

lint:
	@test -d .venv || python3 -m venv .venv
	.venv/bin/pip install -q ".[dev]"
	.venv/bin/ruff check src tests

check: lint test docker-build

docker-build:
	$(COMPOSE) build app dashboard jupyter

# Ephemeral stack: start core services, run one command, tear everything down
docker-check:
	$(COMPOSE) up -d $(CORE_SERVICES)
	$(COMPOSE) run --rm app $(or $(CMD),$(DEFAULT_CMD))
	$(COMPOSE) --profile $(DEV_PROFILE) down --remove-orphans

run:
	$(COMPOSE) up -d $(CORE_SERVICES)
	$(COMPOSE) run --rm app $(or $(CMD),$(DEFAULT_CMD))

scripts:
	@.venv/bin/python -m notification_rake help 2>/dev/null || python3 -m notification_rake help

reset-gotify:
	$(COMPOSE) rm -sf gotify
	docker volume rm -f notification-rake-project_gotify_data
	$(COMPOSE) up -d gotify
	@echo "Gotify reset — login: admin / password from GOTIFY_ADMIN_PASS in .env"

reset-db:
	$(COMPOSE) rm -sf db hasura
	docker volume rm -f notification-rake-project_pgdata
	$(COMPOSE) up -d db hasura
	@echo "Postgres reset — credentials from POSTGRES_* in .env"

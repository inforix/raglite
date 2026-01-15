SHELL := /bin/sh

DOCKER_COMPOSE ?= docker compose
DEV_COMPOSE := $(DOCKER_COMPOSE) -f docker-compose.dev.yml
PROD_COMPOSE := $(DOCKER_COMPOSE) -f docker-compose.yml

UI_BUILD := ui/dist/index.html
UI_SRC := $(shell find ui/src -type f)

.PHONY: dev build stop clean ui-build

dev: $(UI_BUILD)
	$(DEV_COMPOSE) up -d --build

build: $(UI_BUILD)
	$(PROD_COMPOSE) build

stop:
	$(DEV_COMPOSE) down --remove-orphans || true
	$(PROD_COMPOSE) down --remove-orphans || true

clean: stop
	$(DEV_COMPOSE) down -v --remove-orphans || true
	$(PROD_COMPOSE) down -v --remove-orphans || true
	rm -rf data raglite.db
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -type f \( -name "*.pyc" -o -name "*.pyo" -o -name ".coverage" \) -delete
	rm -rf .pytest_cache ui/dist ui/node_modules

ui-build: $(UI_BUILD)

$(UI_BUILD): $(UI_SRC) ui/bun.lock ui/package.json ui/vite.config.ts
	cd ui && bun install --frozen-lockfile --save-text-lockfile && bun run build

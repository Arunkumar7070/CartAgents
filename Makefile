.PHONY: build up down logs migrate index test lint format clean eval web

build:
	docker compose build

up:
	docker compose up

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	docker compose run --rm migrate

# Embeds the catalog into Postgres. Re-run whenever data/products.json or the embedding model changes.
index:
	docker compose run --rm api python -m embedding.index

test:
	docker compose up -d --wait db
	uv run pytest tests/ -v

lint:
	uv run ruff check app/ embedding/ evaluation/ tests/
	uv run ruff format --check app/ embedding/ evaluation/ tests/

format:
	uv run ruff format app/ embedding/ evaluation/ tests/

eval:
	uv run python -m evaluation.skill_router_eval

web:
	cd frontend && npm run dev

clean:
	docker compose down -v

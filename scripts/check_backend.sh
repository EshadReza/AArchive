#!/usr/bin/env bash
# Run from any directory. A disposable PostgreSQL TEST_DATABASE_URL is required.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${TEST_DATABASE_URL:?Set TEST_DATABASE_URL to a disposable PostgreSQL database}"
export DJANGO_SETTINGS_MODULE=config.settings.test
uv sync --locked
uv run --locked ruff check backend
uv run --locked ruff format --check backend
uv run --locked python backend/manage.py check --settings=config.settings.test --database default
uv run --locked python backend/manage.py makemigrations --check --dry-run --settings=config.settings.test
uv run --locked pytest
uv run --locked python scripts/sprint_context.py --check

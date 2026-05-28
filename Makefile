.PHONY: help install test lint format check security build serve docker-build docker-up docker-down clean

help:
	@echo "Release Sentinel Development Tasks"
	@echo "===================================="
	@echo "  make install        Install dependencies"
	@echo "  make test           Run test suite"
	@echo "  make lint           Run linting checks"
	@echo "  make format         Format code with black"
	@echo "  make check          Run all checks (lint + test + security)"
	@echo "  make security       Run security scanning"
	@echo "  make build          Build Python distribution"
	@echo "  make serve          Start development server"
	@echo "  make docker-build   Build Docker image"
	@echo "  make docker-up      Start Docker container"
	@echo "  make docker-down    Stop Docker container"
	@echo "  make clean          Remove build artifacts"

install:
	python -m pip install -e ".[dev]"

test:
	export PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest -v

lint:
	python -m ruff check src tests
	python -m black --check src tests

format:
	python -m black src tests
	python -m ruff check --fix src tests

check: lint test security

security:
	python -m bandit -r src -ll

build:
	python -m build

serve:
	python -m releasesentinel serve --port 8000

docker-build:
	docker build -t release-sentinel:latest .

docker-up:
	docker-compose up

docker-down:
	docker-compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache

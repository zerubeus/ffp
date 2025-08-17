.DEFAULT_GOAL := all

.PHONY: .uv
.uv: ## Check that uv is installed
	@uv --version || echo 'Please install uv: https://docs.astral.sh/uv/getting-started/installation/'

.PHONY: .pre-commit
.pre-commit: ## Check that pre-commit is installed
	@pre-commit -V || echo 'Please install pre-commit: https://pre-commit.com/'

.PHONY: setup
setup: ## Initial setup - install UV and create environment
	@echo "🚀 Setting up Coding for Freedom bridge..."
	@command -v uv >/dev/null 2>&1 || { echo "Installing UV..."; curl -LsSf https://astral.sh/uv/install.sh | sh; }
	@echo "🐍 Initializing UV project..."
	@uv venv
	@echo "📚 Installing dependencies..."
	@uv sync
	@[ -f .env ] || { echo "⚙️  Creating .env file..."; cp .env.example .env; echo "⚠️  Please edit .env with your API credentials"; }
	@echo "✅ Setup complete! Run 'source .venv/bin/activate' then 'make run'"

.PHONY: install
install: .uv ## Install the package and dependencies for local development
	uv sync

.PHONY: dev
dev: .uv ## Install with development dependencies
	uv sync --all-extras

.PHONY: format
format: ## Format the code
	uv run ruff format ffp/
	uv run ruff check --fix --fix-only ffp/

.PHONY: lint
lint: ## Lint the code
	uv run ruff format --check ffp/
	uv run ruff check ffp/

.PHONY: typecheck
typecheck: ## Run type checking
	@# PYRIGHT_PYTHON_IGNORE_WARNINGS avoids the overhead of making a request to github on every invocation
	PYRIGHT_PYTHON_IGNORE_WARNINGS=1 uv run pyright

.PHONY: test
test: ## Run tests
	uv run pytest tests/

.PHONY: run
run: ## Run the application
	uv run python -m ffp.main

.PHONY: clean
clean: ## Clean build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .venv/
	rm -rf build/ dist/ *.egg-info/

.PHONY: build
build: clean ## Build the package distribution
	uv build

.PHONY: get-latest-version
get-latest-version: ## Get the latest version from git tags
	@LATEST_TAG=$$(git tag -l "v[0-9]*.[0-9]*.[0-9]*" | sort -V | tail -n1); \
	if [ -z "$$LATEST_TAG" ]; then \
		echo "0.0.0"; \
	else \
		echo "$${LATEST_TAG#v}"; \
	fi

.PHONY: release
release: all build ## Create a new release on GitHub (requires VERSION env var or auto-increments patch)
	@if [ -z "$$VERSION" ]; then \
		CURRENT_VERSION=$$(make -s get-latest-version); \
		MAJOR=$$(echo $$CURRENT_VERSION | cut -d. -f1); \
		MINOR=$$(echo $$CURRENT_VERSION | cut -d. -f2); \
		PATCH=$$(echo $$CURRENT_VERSION | cut -d. -f3); \
		NEW_PATCH=$$((PATCH + 1)); \
		VERSION="$$MAJOR.$$MINOR.$$NEW_PATCH"; \
		echo "No VERSION specified, auto-incrementing to $$VERSION"; \
	fi; \
	echo "Creating release v$$VERSION..."; \
	if ! echo "$$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$$'; then \
		echo "ERROR: Version $$VERSION must be in format X.Y.Z (e.g. 1.0.0)"; \
		exit 1; \
	fi; \
	if git rev-parse "v$$VERSION" >/dev/null 2>&1; then \
		echo "ERROR: Tag v$$VERSION already exists"; \
		exit 1; \
	fi; \
	git tag -a "v$$VERSION" -m "Release v$$VERSION"; \
	git push origin "v$$VERSION"; \
	echo "Successfully created and pushed tag v$$VERSION"

.PHONY: publish
publish: all build ## Publish the package to PyPI
	@if [ ! -f .env ]; then \
		echo "ERROR: Missing .env file with PYPI_TOKEN"; \
		exit 1; \
	fi
	@echo "Publishing to PyPI..."
	@. .env && uv publish --token $$PYPI_TOKEN
	@echo "Successfully published to PyPI"

.PHONY: all
all: format lint typecheck ## Run code formatting, linting, static type checks

.PHONY: help
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Docker commands
.PHONY: docker-up
docker-up: ## Start the application with Docker Compose
	docker-compose up -d
	@echo "Application is running in Docker"

.PHONY: docker-down
docker-down: ## Stop all Docker services
	docker-compose down

.PHONY: docker-clean
docker-clean: ## Stop and remove all Docker containers and volumes
	docker-compose down -v

.PHONY: docker-logs
docker-logs: ## View application logs
	docker-compose logs -f app

.PHONY: docker-run
docker-run: ## Build and run the application with Docker
	docker-compose up --build

.PHONY: errors
errors: ## Display database errors from the last 24 hours
	@uv run python -m ffp.show_errors

.PHONY: errors-all
errors-all: ## Display all database errors from the last 7 days
	@uv run python -m ffp.show_errors --hours 168 --limit 100
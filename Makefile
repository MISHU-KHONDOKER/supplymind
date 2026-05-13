# ==============================================================================
# SupplyMind Makefile
# ==============================================================================
# Convenience commands for development, testing, and deployment.
# Run `make help` to see all available commands.
# ==============================================================================

# Use bash for all shell commands (more features than sh)
SHELL := /bin/bash

# Default goal when running `make` with no arguments
.DEFAULT_GOAL := help

# Phony targets — not real files, just command names
.PHONY: help run stop restart logs clean install test test-cov lint format \
        type-check eval benchmark build deploy health docker-build docker-push

# ------------------------------------------------------------------------------
# Project Variables
# ------------------------------------------------------------------------------

PROJECT_NAME := supplymind
BACKEND_DIR  := backend
FRONTEND_DIR := frontend
INFRA_DIR    := infra
COMPOSE_FILE := $(INFRA_DIR)/docker-compose.yml
ENV_FILE     := .env

# ------------------------------------------------------------------------------
# Help
# ------------------------------------------------------------------------------

help: ## Show this help message
	@echo ""
	@echo "SupplyMind — Development Commands"
	@echo "================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""		

# ------------------------------------------------------------------------------
# Application Lifecycle
# ------------------------------------------------------------------------------

run: ## Start the full stack (Docker Compose)
	@echo "🚀 Starting SupplyMind..."
	docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) up -d --build
	@echo ""
	@echo "✓ Stack is running:"
	@echo "  Frontend:   http://localhost:3000"
	@echo "  Backend:    http://localhost:8000"
	@echo "  API docs:   http://localhost:8000/docs"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana:    http://localhost:3001 (admin/admin)"
	@echo ""

stop: ## Stop all services
	@echo "🛑 Stopping SupplyMind..."
	docker compose -f $(COMPOSE_FILE) down

restart: stop run ## Restart the full stack

logs: ## Tail logs from all services
	docker compose -f $(COMPOSE_FILE) logs -f --tail=100

logs-backend: ## Tail logs from backend only
	docker compose -f $(COMPOSE_FILE) logs -f --tail=100 backend

clean: ## Remove containers, volumes, and build artifacts
	@echo "🧹 Cleaning up..."
	docker compose -f $(COMPOSE_FILE) down -v --rmi local --remove-orphans
	@echo "✓ Cleanup complete"

health: ## Run smoke tests against all services
	@echo "🏥 Checking service health..."
	@curl -sf http://localhost:8000/health > /dev/null && echo "✓ Backend healthy" || echo "✗ Backend unreachable"
	@curl -sf http://localhost:9090/-/healthy > /dev/null && echo "✓ Prometheus healthy" || echo "✗ Prometheus unreachable"
	@curl -sf http://localhost:3001/api/health > /dev/null && echo "✓ Grafana healthy" || echo "✗ Grafana unreachable"
	@curl -sf http://localhost:3000 > /dev/null && echo "✓ Frontend reachable" || echo "✗ Frontend unreachable"


# ------------------------------------------------------------------------------
# Local Development (without Docker)
# ------------------------------------------------------------------------------

install: ## Install backend dependencies into a local virtualenv
	@echo "📦 Installing backend dependencies..."
	cd $(BACKEND_DIR) && python -m venv venv
	cd $(BACKEND_DIR) && venv/Scripts/activate && pip install --upgrade pip
	cd $(BACKEND_DIR) && venv/Scripts/activate && pip install -r requirements.txt
	@echo "✓ Backend dependencies installed"

install-frontend: ## Install frontend dependencies
	@echo "📦 Installing frontend dependencies..."
	cd $(FRONTEND_DIR) && npm install
	@echo "✓ Frontend dependencies installed"

# ------------------------------------------------------------------------------
# Testing
# ------------------------------------------------------------------------------

test: ## Run the full test suite
	@echo "🧪 Running tests..."
	cd $(BACKEND_DIR) && pytest tests/ -v

test-cov: ## Run tests with coverage report
	@echo "🧪 Running tests with coverage..."
	cd $(BACKEND_DIR) && pytest tests/ -v \
		--cov=app \
		--cov-report=term-missing \
		--cov-report=html:coverage_html \
		--cov-fail-under=70

test-unit: ## Run unit tests only (fast)
	cd $(BACKEND_DIR) && pytest tests/unit/ -v

test-integration: ## Run integration tests (slower, requires services)
	cd $(BACKEND_DIR) && pytest tests/integration/ -v

# ------------------------------------------------------------------------------
# Code Quality
# ------------------------------------------------------------------------------

lint: ## Lint code with Ruff
	@echo "🔍 Linting backend..."
	cd $(BACKEND_DIR) && ruff check app/ tests/
	@echo "✓ Linting passed"

format: ## Auto-format code with Black and isort
	@echo "✨ Formatting code..."
	cd $(BACKEND_DIR) && black app/ tests/
	cd $(BACKEND_DIR) && isort app/ tests/
	cd $(BACKEND_DIR) && ruff check --fix app/ tests/
	@echo "✓ Code formatted"

type-check: ## Run static type checking with mypy
	@echo "🔬 Type-checking backend..."
	cd $(BACKEND_DIR) && mypy app/ --strict
	@echo "✓ Type-check passed"

check: lint type-check test ## Run all quality checks (lint + types + tests)
	@echo "✓ All checks passed"


# ------------------------------------------------------------------------------
# Evaluation and Benchmarks
# ------------------------------------------------------------------------------

eval: ## Run the evaluation harness against the golden test set
	@echo "📊 Running evaluation suite..."
	cd $(BACKEND_DIR) && python -m app.evaluation.runner \
		--golden tests/eval/golden_set.json \
		--output eval_outputs/run_$(shell date +%Y%m%d_%H%M%S).json
	@echo "✓ Evaluation complete"

eval-quick: ## Run a quick subset of the eval suite (for development)
	cd $(BACKEND_DIR) && python -m app.evaluation.runner --quick

benchmark: ## Run performance benchmarks (100 pipeline runs)
	@echo "⏱️  Running benchmarks..."
	cd $(BACKEND_DIR) && python -m app.benchmark.runner \
		--iterations 100 \
		--output benchmarks/results_$(shell date +%Y%m%d_%H%M%S).json
	@echo "✓ Benchmark complete"

# ------------------------------------------------------------------------------
# Data Generation
# ------------------------------------------------------------------------------

generate-data: ## Generate synthetic supply chain dataset
	@echo "🔬 Generating synthetic data..."
	cd $(BACKEND_DIR) && python -m app.data.synthetic.generator \
		--suppliers 50 \
		--products 200 \
		--days 90 \
		--seed 42
	@echo "✓ Synthetic data generated"

# ------------------------------------------------------------------------------
# Docker Build and Deploy
# ------------------------------------------------------------------------------

docker-build: ## Build production Docker images
	@echo "🏗️  Building Docker images..."
	docker build -t $(PROJECT_NAME)-backend:latest -f $(BACKEND_DIR)/Dockerfile $(BACKEND_DIR)
	docker build -t $(PROJECT_NAME)-frontend:latest -f $(FRONTEND_DIR)/Dockerfile $(FRONTEND_DIR)
	@echo "✓ Images built"

docker-push: docker-build ## Build and push images to registry
	@echo "📤 Pushing Docker images..."
	docker push $(PROJECT_NAME)-backend:latest
	docker push $(PROJECT_NAME)-frontend:latest
	@echo "✓ Images pushed"

deploy: ## Deploy to staging environment
	@echo "🚀 Deploying to staging..."
	@echo "TODO: implement Kubernetes manifest application"

# ------------------------------------------------------------------------------
# Kubernetes (Minikube)
# ------------------------------------------------------------------------------

k8s-start: ## Start local Kubernetes cluster (Minikube)
	minikube start --cpus=4 --memory=8192

k8s-stop: ## Stop the Minikube cluster
	minikube stop

k8s-deploy: ## Deploy to Minikube
	kubectl apply -f $(INFRA_DIR)/k8s/
	@echo "✓ Deployed to Minikube"

k8s-status: ## Show Kubernetes pod status
	kubectl get pods,services,deployments

# ------------------------------------------------------------------------------
# Development Utilities
# ------------------------------------------------------------------------------

shell: ## Open an interactive Python shell inside the backend container
	docker compose -f $(COMPOSE_FILE) exec backend ipython

db-shell: ## Open a ChromaDB inspection shell
	docker compose -f $(COMPOSE_FILE) exec backend python -m app.tools.chroma_shell

version: ## Print version information for all components
	@echo "SupplyMind Version Info"
	@echo "======================="
	@echo "Project:  $(PROJECT_NAME)"
	@echo "Python:   $$(python --version 2>&1)"
	@echo "Node:     $$(node --version 2>&1)"
	@echo "Docker:   $$(docker --version 2>&1)"
	@echo "Git SHA:  $$(git rev-parse --short HEAD 2>/dev/null || echo 'no git')"

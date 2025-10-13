# BTC Watcher Makefile
# 简化常用命令

.PHONY: help install dev up down logs test verify clean

# Default target
help:
	@echo "BTC Watcher - Available Commands"
	@echo "================================="
	@echo ""
	@echo "Development:"
	@echo "  make install     - Install dependencies"
	@echo "  make dev         - Start development environment"
	@echo ""
	@echo "Deployment:"
	@echo "  make verify      - Verify deployment environment"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo ""
	@echo "Monitoring:"
	@echo "  make logs        - Show all logs"
	@echo "  make logs-api    - Show backend API logs"
	@echo "  make logs-web    - Show frontend logs"
	@echo "  make logs-db     - Show database logs"
	@echo "  make ps          - Show running containers"
	@echo ""
	@echo "Testing:"
	@echo "  make test        - Run API integration tests"
	@echo "  make test-unit   - Run unit tests"
	@echo "  make test-verify - Run runtime verification"
	@echo "  make test-dynamic - Run dynamic tests"
	@echo "  make test-all    - Run all tests"
	@echo "  make smoke       - Run smoke tests"
	@echo "  make coverage    - Generate coverage report"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean       - Stop and remove containers"
	@echo "  make clean-all   - Stop, remove containers and volumes (DANGER!)"
	@echo "  make rebuild     - Rebuild all containers"
	@echo ""

# Install dependencies
install:
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Installing test dependencies..."
	cd backend && pip install -r requirements-test.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

# Development mode
dev:
	@echo "Starting development environment..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Verify deployment environment
verify:
	@echo "Verifying deployment environment..."
	./verify_deployment.sh

# Start services
up:
	@echo "Starting all services..."
	./scripts/start.sh

# Stop services
down:
	@echo "Stopping all services..."
	./scripts/stop.sh

# Restart services
restart:
	@echo "Restarting all services..."
	docker-compose restart

# Show logs
logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f backend

logs-web:
	docker-compose logs -f frontend

logs-db:
	docker-compose logs -f db

logs-redis:
	docker-compose logs -f redis

# Show running containers
ps:
	docker-compose ps

# Run API integration tests
test:
	@echo "Running API integration tests..."
	cd backend && python tests/test_api.py

# Run unit tests
test-unit:
	@echo "Running unit tests..."
	./scripts/run_unit_tests.sh

# Run runtime verification
test-verify:
	@echo "Running runtime verification..."
	./scripts/verify_runtime.sh

# Run dynamic tests
test-dynamic:
	@echo "Running dynamic tests..."
	./scripts/dynamic_test.sh

# Run all tests
test-all:
	@echo "Running all tests..."
	@echo "\n=== 1. Unit Tests ==="
	./scripts/run_unit_tests.sh
	@echo "\n=== 2. Integration Tests ==="
	cd backend && python tests/test_api.py
	@echo "\n=== 3. Dynamic Tests ==="
	./scripts/dynamic_test.sh

# Run smoke tests
smoke:
	@echo "Running smoke tests..."
	@curl -s http://localhost:8000/api/v1/system/health && echo "✅ Backend health check passed" || echo "❌ Backend health check failed"
	@curl -s http://localhost > /dev/null && echo "✅ Frontend accessible" || echo "❌ Frontend not accessible"
	@curl -s http://localhost:8000/docs > /dev/null && echo "✅ API docs accessible" || echo "❌ API docs not accessible"

# Generate coverage report
coverage:
	@echo "Generating coverage report..."
	cd backend && pytest tests/unit/ --cov=. --cov-report=html --cov-report=term-missing
	@echo "✅ Coverage report generated at backend/htmlcov/index.html"

# Clean up
clean:
	@echo "Stopping and removing containers..."
	docker-compose down

clean-all:
	@echo "⚠️  WARNING: This will remove all containers and volumes!"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	docker-compose down -v
	@echo "✅ Cleanup complete"

# Rebuild containers
rebuild:
	@echo "Rebuilding all containers..."
	docker-compose build --no-cache
	docker-compose up -d

# Database operations
db-shell:
	@echo "Connecting to database..."
	docker exec -it btc-watcher-db psql -U btc_watcher

db-backup:
	@echo "Backing up database..."
	docker exec btc-watcher-db pg_dump -U btc_watcher btc_watcher > backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Database backup created"

db-restore:
	@echo "⚠️  WARNING: This will restore the database from backup!"
	@read -p "Enter backup file path: " file && docker exec -i btc-watcher-db psql -U btc_watcher < $$file
	@echo "✅ Database restored"

# Redis operations
redis-shell:
	@echo "Connecting to Redis..."
	docker exec -it btc-watcher-redis redis-cli

redis-flush:
	@echo "⚠️  WARNING: This will flush all Redis data!"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	docker exec btc-watcher-redis redis-cli FLUSHALL
	@echo "✅ Redis flushed"

# Code quality
lint-backend:
	@echo "Running backend linters..."
	cd backend && flake8 . || true
	cd backend && pylint **/*.py || true

format-backend:
	@echo "Formatting backend code..."
	cd backend && black .
	cd backend && isort .

lint-frontend:
	@echo "Running frontend linters..."
	cd frontend && npm run lint

format-frontend:
	@echo "Formatting frontend code..."
	cd frontend && npm run format

# Docker operations
docker-prune:
	@echo "Pruning unused Docker resources..."
	docker system prune -f
	@echo "✅ Docker cleanup complete"

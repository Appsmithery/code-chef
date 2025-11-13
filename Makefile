.PHONY: up down rebuild logs clean backup restore help

# Default target
.DEFAULT_GOAL := help

## up: Start all services
up:
	@echo "Starting Dev-Tools services..."
	@./scripts/up.sh

## down: Stop all services
down:
	@echo "Stopping Dev-Tools services..."
	@./scripts/down.sh

## rebuild: Rebuild and restart all services
rebuild:
	@echo "Rebuilding Dev-Tools services..."
	@./scripts/rebuild.sh

## logs: View logs from all services
logs:
	@cd compose && docker-compose logs -f

## logs-agent: View logs from specific agent (usage: make logs-agent AGENT=orchestrator)
logs-agent:
	@cd compose && docker-compose logs -f $(AGENT)

## ps: Show running services
ps:
	@cd compose && docker-compose ps

## backup: Backup all volumes
backup:
	@echo "Creating backup..."
	@./scripts/backup_volumes.sh

## restore: Restore volumes from backup (usage: make restore BACKUP=./backups/20250112_140000)
restore:
	@echo "Restoring from backup: $(BACKUP)"
	@./scripts/restore_volumes.sh $(BACKUP)

## clean: Remove all containers, volumes, and images
clean:
	@echo "Cleaning up Dev-Tools resources..."
	@cd compose && docker-compose down -v
	@docker system prune -f

## health: Check health of all services
health:
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health || echo "MCP Gateway: DOWN"
	@curl -s http://localhost:8001/health || echo "Orchestrator: DOWN"

## shell: Open shell in specific service (usage: make shell SERVICE=orchestrator)
shell:
	@cd compose && docker-compose exec $(SERVICE) /bin/sh

## help: Show this help message
help:
	@echo "Dev-Tools Makefile Commands:"
	@echo ""
	@sed -n 's/^##//p' ${MAKEFILE_LIST} | column -t -s ':' | sed -e 's/^/ /'
	@echo ""
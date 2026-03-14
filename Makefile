# Dataverse Ansible Makefile
#
# Usage:
#   make status ENV=tim        # Show environment status
#   make deploy ENV=tim        # Full deploy (terraform + ansible)
#   make test ENV=tim          # Run integration tests
#   make rebuild ENV=tim       # Destroy, rebuild, restore DB, deploy, test
#   make destroy ENV=tim       # Tear down everything
#
# Environments: tim (dev), jamie (test)
#
# Prerequisites:
#   - terraform-dataverse repo cloned as sibling directory
#   - AWS credentials configured
#   - SSH keys in place

SHELL := /bin/bash
.PHONY: help status deploy provision ansible test destroy clean rebuild restore-db

# Default environment
ENV ?= tim

# Paths - terraform-dataverse should be sibling to dataverse-ansible
TERRAFORM_BASE := ../terraform-dataverse
TERRAFORM_DIR := $(TERRAFORM_BASE)/environments/$(ENV)

ifeq ($(ENV),tim)
    GROUP_VARS := dev
    INVENTORY := inventory-dev.yml
    HOSTNAME := staging.ucladataverse.dev
else ifeq ($(ENV),jamie)
    GROUP_VARS := test
    INVENTORY := inventory-test.yml
    HOSTNAME := test.ucladataverse.dev
else
    GROUP_VARS := $(ENV)
    INVENTORY := inventory-$(ENV).yml
    HOSTNAME := $(ENV).ucladataverse.dev
endif

INVENTORY_PATH := $(TERRAFORM_DIR)/$(INVENTORY)

# Colors
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
CYAN := \033[0;36m
NC := \033[0m

help: ## Show this help
	@echo "$(CYAN)Dataverse Infrastructure Management$(NC)"
	@echo ""
	@echo "Usage: make <target> ENV=<environment>"
	@echo ""
	@echo "$(YELLOW)Environments:$(NC)"
	@echo "  tim    - Dev environment (staging.ucladataverse.dev)"
	@echo "  jamie  - Test environment (test.ucladataverse.dev)"
	@echo ""
	@echo "$(YELLOW)Targets:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-18s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make rebuild ENV=tim              # Full destroy + rebuild + test"
	@echo "  make test-smoke ENV=tim           # Quick smoke tests"
	@echo "  make ssh ENV=tim                  # SSH to instance"

# =============================================================================
# BOOTSTRAP & DEPENDENCIES
# =============================================================================

bootstrap: ## Install Ansible collections and Python dependencies
	@echo "$(GREEN)Installing Ansible collections...$(NC)"
	ansible-galaxy collection install -r collections/requirements.yml -p ./collections --force
	@echo "$(GREEN)Installing Python dependencies...$(NC)"
	uv sync
	@echo "$(GREEN)Bootstrap complete!$(NC)"

# =============================================================================
# STATUS & INFO
# =============================================================================

status: ## Show environment status
	@echo "$(CYAN)Environment: $(ENV)$(NC)"
	@echo "$(CYAN)Hostname: $(HOSTNAME)$(NC)"
	@echo ""
	@echo "$(YELLOW)Terraform State:$(NC)"
	@cd $(TERRAFORM_DIR) 2>/dev/null && terraform output 2>/dev/null || echo "  Not provisioned"
	@echo ""
	@echo "$(YELLOW)Service Check:$(NC)"
	@curl -s --max-time 5 https://$(HOSTNAME)/api/info/version 2>/dev/null | jq -r '.data.version // "Not responding"' || echo "  Not responding"

# =============================================================================
# INFRASTRUCTURE (TERRAFORM)
# =============================================================================

provision: ## Provision AWS infrastructure with Terraform
	@echo "$(GREEN)Provisioning infrastructure for $(ENV)...$(NC)"
	@if [ ! -d "$(TERRAFORM_DIR)" ]; then \
		echo "$(RED)ERROR: Terraform directory not found at $(TERRAFORM_DIR)$(NC)"; \
		echo "Ensure terraform-dataverse is cloned as a sibling directory"; \
		exit 1; \
	fi
	cd $(TERRAFORM_DIR) && terraform init
	cd $(TERRAFORM_DIR) && terraform apply
	@echo ""
	@echo "$(YELLOW)NEXT STEPS:$(NC)"
	@echo "1. Create/verify DNS A record for $(HOSTNAME)"
	@echo "2. Update group_vars/$(GROUP_VARS).yml with RDS endpoint and S3 bucket"
	@echo "3. Run 'make ansible ENV=$(ENV)'"

destroy: ## Destroy all infrastructure (DANGER!)
	@echo "$(RED)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(RED)║  WARNING: This will PERMANENTLY DELETE all resources!      ║$(NC)"
	@echo "$(RED)║  - EC2 instance                                            ║$(NC)"
	@echo "$(RED)║  - RDS database (ALL DATA LOST)                            ║$(NC)"
	@echo "$(RED)║  - S3 bucket (ALL FILES LOST)                              ║$(NC)"
	@echo "$(RED)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@read -p "Type '$(ENV)' to confirm destruction: " confirm; \
	if [ "$$confirm" = "$(ENV)" ]; then \
		cd $(TERRAFORM_DIR) && terraform destroy; \
	else \
		echo "Aborted."; \
	fi

# =============================================================================
# DEPLOYMENT (ANSIBLE)
# =============================================================================

ansible: ## Run Ansible playbook
	@echo "$(GREEN)Running Ansible for $(ENV)...$(NC)"
	@if [ ! -f "$(INVENTORY_PATH)" ]; then \
		echo "$(RED)ERROR: Inventory not found at $(INVENTORY_PATH)$(NC)"; \
		echo "Run 'make provision ENV=$(ENV)' first, then create inventory"; \
		exit 1; \
	fi
	ansible-playbook -i $(INVENTORY_PATH) site.yml

ansible-migration: ## Run only migration tasks (JPA tables + logos)
	@echo "$(GREEN)Running migration tasks for $(ENV)...$(NC)"
	ansible-playbook -i $(INVENTORY_PATH) site.yml --tags migration

ansible-branding: ## Run only branding tasks (logos)
	@echo "$(GREEN)Running branding tasks for $(ENV)...$(NC)"
	ansible-playbook -i $(INVENTORY_PATH) site.yml --tags logos

deploy: provision ## Full deployment (provision + ansible)
	@echo ""
	@echo "$(YELLOW)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(YELLOW)Infrastructure provisioned. Before continuing:$(NC)"
	@echo "$(YELLOW)1. Verify/create DNS A record for $(HOSTNAME)$(NC)"
	@echo "$(YELLOW)2. Update group_vars/$(GROUP_VARS).yml with terraform outputs$(NC)"
	@echo "$(YELLOW)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@read -p "Press Enter when ready to run Ansible (or Ctrl+C to abort)..."
	$(MAKE) ansible ENV=$(ENV)

# =============================================================================
# DATABASE MIGRATION
# =============================================================================

# Local path to production DB dump (download once, reuse)
DB_DUMP ?= /tmp/dvndb_prod.dump

dump-db: ## Show how to create DB dump from production
	@echo "$(YELLOW)Run these commands to get production DB dump:$(NC)"
	@echo ""
	@echo "  # On production server:"
	@echo "  pg_dump -U postgres -Fc dvndb > /tmp/dvndb_prod.dump"
	@echo ""
	@echo "  # Copy to your local machine:"
	@echo "  scp ec2-user@production:/tmp/dvndb_prod.dump /tmp/"
	@echo ""
	@echo "  # Then restore with:"
	@echo "  make restore-db ENV=$(ENV) DB_HOST=<rds-endpoint> DB_PASS=<password>"
	@echo ""
	@echo "$(CYAN)Tip: Keep the dump at $(DB_DUMP) - it can be reused for rebuilds$(NC)"

restore-db: ## Restore DB from local dump file (requires DB_HOST, DB_PASS, optionally DB_DUMP)
	@if [ -z "$(DB_HOST)" ] || [ -z "$(DB_PASS)" ]; then \
		echo "$(RED)ERROR: DB_HOST and DB_PASS are required$(NC)"; \
		echo "Usage: make restore-db ENV=$(ENV) DB_HOST=<rds-endpoint> DB_PASS=<password> [DB_DUMP=/path/to/file]"; \
		exit 1; \
	fi
	@if [ ! -f "$(DB_DUMP)" ]; then \
		echo "$(RED)ERROR: DB dump not found at $(DB_DUMP)$(NC)"; \
		echo "Run 'make dump-db' for instructions, or set DB_DUMP=/path/to/dump"; \
		exit 1; \
	fi
	@echo "$(GREEN)Restoring $(DB_DUMP) to $(DB_HOST)...$(NC)"
	PGPASSWORD=$(DB_PASS) pg_restore -h $(DB_HOST) -U postgres -d dvndb -v $(DB_DUMP) || true
	@echo "$(GREEN)Database restored!$(NC)"

# =============================================================================
# FULL REBUILD WORKFLOW
# =============================================================================

rebuild: ## FULL REBUILD: destroy, provision, restore DB, deploy, test (requires DB_HOST, DB_PASS)
	@if [ -z "$(DB_HOST)" ] || [ -z "$(DB_PASS)" ]; then \
		echo "$(RED)ERROR: DB_HOST and DB_PASS are required$(NC)"; \
		echo "Usage: make rebuild ENV=$(ENV) DB_HOST=<rds-endpoint> DB_PASS=<password> [DB_DUMP=/path/to/file]"; \
		exit 1; \
	fi
	@echo "$(CYAN)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(CYAN)║           FULL ENVIRONMENT REBUILD                         ║$(NC)"
	@echo "$(CYAN)║  destroy → provision → ansible → restore DB → test         ║$(NC)"
	@echo "$(CYAN)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)Prerequisites:$(NC)"
	@echo "  - DB_HOST: $(DB_HOST)"
	@echo "  - DB_DUMP: $(DB_DUMP)"
	@echo "  - DNS configured for $(HOSTNAME)"
	@echo ""
	@if [ ! -f "$(DB_DUMP)" ]; then \
		echo "$(RED)WARNING: DB dump not found at $(DB_DUMP)$(NC)"; \
		echo "Set DB_DUMP=/path/to/dump or run 'make dump-db' first"; \
		echo ""; \
	fi
	@read -p "Type 'rebuild $(ENV)' to confirm: " confirm; \
	if [ "$$confirm" = "rebuild $(ENV)" ]; then \
		$(MAKE) destroy ENV=$(ENV) && \
		$(MAKE) provision ENV=$(ENV) && \
		$(MAKE) ansible ENV=$(ENV) && \
		$(MAKE) restore-db ENV=$(ENV) DB_HOST=$(DB_HOST) DB_PASS=$(DB_PASS) DB_DUMP=$(DB_DUMP) && \
		$(MAKE) ansible-migration ENV=$(ENV) && \
		$(MAKE) test-smoke ENV=$(ENV); \
	else \
		echo "Aborted."; \
	fi

# =============================================================================
# TESTING
# =============================================================================

test: ## Run all integration tests
	@echo "$(GREEN)Running all tests for $(ENV)...$(NC)"
	uv run pytest tests/integration -v --dataverse-url=https://$(HOSTNAME)

test-smoke: ## Run smoke tests only
	@echo "$(GREEN)Running smoke tests for $(ENV)...$(NC)"
	uv run pytest tests/integration/test_smoke.py -v --dataverse-url=https://$(HOSTNAME)

test-migration: ## Run migration tests (requires DB_HOST, DB_PASS)
	@echo "$(GREEN)Running migration tests for $(ENV)...$(NC)"
	@if [ -z "$(DB_HOST)" ]; then \
		echo "$(YELLOW)Usage: make test-migration ENV=$(ENV) DB_HOST=<rds-endpoint> DB_PASS=<password>$(NC)"; \
		exit 1; \
	fi
	uv run pytest tests/integration/test_migration.py -v \
		--dataverse-url=https://$(HOSTNAME) \
		--db-host=$(DB_HOST) \
		--db-user=postgres \
		--db-password=$(DB_PASS)

# =============================================================================
# UTILITIES
# =============================================================================

ssh: ## SSH to EC2 instance
	@IP=$$(cd $(TERRAFORM_DIR) && terraform output -json instance_public_ips 2>/dev/null | jq -r 'to_entries[0].value' 2>/dev/null); \
	if [ -n "$$IP" ] && [ "$$IP" != "null" ]; then \
		echo "$(GREEN)Connecting to $$IP...$(NC)"; \
		ssh -o StrictHostKeyChecking=no rocky@$$IP; \
	else \
		echo "$(RED)No instance found. Run 'make provision ENV=$(ENV)' first$(NC)"; \
	fi

logs: ## Tail Payara logs on EC2
	@IP=$$(cd $(TERRAFORM_DIR) && terraform output -json instance_public_ips 2>/dev/null | jq -r 'to_entries[0].value' 2>/dev/null); \
	if [ -n "$$IP" ] && [ "$$IP" != "null" ]; then \
		ssh -o StrictHostKeyChecking=no rocky@$$IP 'sudo tail -f /usr/local/payara6/glassfish/domains/domain1/logs/server.log'; \
	else \
		echo "$(RED)No instance found$(NC)"; \
	fi

reindex: ## Trigger Solr reindex
	@echo "$(GREEN)Triggering Solr reindex...$(NC)"
	curl -X DELETE "https://$(HOSTNAME)/api/admin/index"
	curl -X GET "https://$(HOSTNAME)/api/admin/index"

clean: ## Clean up local caches
	@echo "$(GREEN)Cleaning up...$(NC)"
	rm -rf __pycache__ tests/__pycache__ .pytest_cache
	find . -name "*.pyc" -delete

# Makefile for The Grand Locus project
UV := uv

# --- Configuration ---
# These variables can be modified if the project details change.
PROJECT_ID := thegrandlocus-2
REGION     := europe-west1
# Two Cloud Run services in the same project: staging (test releases) and production (live).
SERVICE_NAME_PRODUCTION := thegrandlocus
SERVICE_NAME_STAGING    := thegrandlocus-staging
# Default for logs / undeploy when no override is given
LOG_SERVICE ?= $(SERVICE_NAME_PRODUCTION)

# Load secrets from .env file
GOOGLE_CLIENT_ID := $(shell awk -F= '/^GOOGLE_CLIENT_ID/{print $$2}' .env)
GOOGLE_CLIENT_SECRET := $(shell awk -F= '/^GOOGLE_CLIENT_SECRET/{print $$2}' .env)
SECRET_KEY := $(shell awk -F= '/^SECRET_KEY/{print $$2}' .env)


# --- Rules ---

# The .PHONY directive tells make that these are not files.
.PHONY: help install install-dev run deploy deploy-prod deploy-staging cloudrun-deploy logs logs-staging \
	undeploy undeploy-staging pre-commit check-env check-gcloud check-gcloud-auth check-gcloud-adc \
	check-uv requirements export-requirements

# Default target when running `make` without arguments.
default: help

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@echo "  install    Create/update the uv environment (see pyproject.toml / uv.lock)"
	@echo "  requirements  Regenerate requirements.txt from uv.lock (for Docker)"
	@echo "  run        Run the FastAPI application locally for development"
	@echo "  deploy       Same as deploy-prod (live site)"
	@echo "  deploy-prod  Build and deploy to production Cloud Run ($(SERVICE_NAME_PRODUCTION))"
	@echo "  deploy-staging  Build and deploy to staging Cloud Run ($(SERVICE_NAME_STAGING))"
	@echo "  logs         Latest logs for production (override: make logs LOG_SERVICE=...)"
	@echo "  logs-staging Latest logs for staging"
	@echo "  undeploy        Delete the production Cloud Run service (destructive)"
	@echo "  undeploy-staging  Delete the staging Cloud Run service"
	@echo "  backup     Backup all the posts from the production database"
	@echo "  index      Update the Datastore indexes"

install: check-uv
	$(UV) sync

install-dev: install
	$(UV) run pre-commit install

# Regenerate requirements.txt from the lockfile (used by Dockerfile / non-uv deploys).
export-requirements requirements: check-uv
	$(UV) export --no-dev --frozen -o requirements.txt

clean:
	rm -rf .venv
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete

run: install check-env check-gcloud check-gcloud-adc
	$(UV) run python run.py

backup: install check-gcloud-adc
	$(UV) run python scripts/backup_posts.py

index: check-gcloud-adc
	gcloud datastore indexes create index.yaml

# Staging vs production: same git branch (e.g. master), two services. Test with deploy-staging;
# when satisfied, deploy-prod promotes the app to the live URL.
deploy deploy-prod: DEPLOY_SERVICE := $(SERVICE_NAME_PRODUCTION)
deploy deploy-prod: DEPLOY_ENV := production
deploy deploy-prod: cloudrun-deploy

deploy-staging: DEPLOY_SERVICE := $(SERVICE_NAME_STAGING)
deploy-staging: DEPLOY_ENV := staging
deploy-staging: cloudrun-deploy

cloudrun-deploy: install check-env check-gcloud check-gcloud-auth
	@test -n "$(DEPLOY_SERVICE)" || (echo "Use make deploy-prod or make deploy-staging"; exit 1)
	@echo "Deploying service '$(DEPLOY_SERVICE)' (ENVIRONMENT=$(DEPLOY_ENV)) to project '$(PROJECT_ID)' in region '$(REGION)'..."
	gcloud run deploy $(DEPLOY_SERVICE) \
		--source . \
		--project=$(PROJECT_ID) \
		--region=$(REGION) \
		--allow-unauthenticated \
		--set-env-vars="GOOGLE_CLIENT_ID=$(GOOGLE_CLIENT_ID),GOOGLE_CLIENT_SECRET=$(GOOGLE_CLIENT_SECRET),SECRET_KEY=$(SECRET_KEY),ENVIRONMENT=$(DEPLOY_ENV)" \
		-q
	@echo "Deployment complete."

undeploy: check-gcloud check-gcloud-auth
	gcloud run services delete $(SERVICE_NAME_PRODUCTION) --region=$(REGION) --project=$(PROJECT_ID)

undeploy-staging: check-gcloud check-gcloud-auth
	gcloud run services delete $(SERVICE_NAME_STAGING) --region=$(REGION) --project=$(PROJECT_ID)

logs: check-gcloud check-gcloud-auth
	@LATEST_REVISION=$$(gcloud run revisions list --service=$(LOG_SERVICE) --project=$(PROJECT_ID) --region=$(REGION) --format="value(revision.name)" --limit=1); \
	echo "Fetching logs for service $(LOG_SERVICE), revision: $$LATEST_REVISION..."; \
	gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.revision_name=\"$$LATEST_REVISION\"" --project=$(PROJECT_ID) --limit=50 --format=json | cat

logs-staging:
	@$(MAKE) logs LOG_SERVICE=$(SERVICE_NAME_STAGING)

test: install-dev
	$(UV) run pytest

pre-commit: install-dev
	$(UV) run pre-commit run --color=always --all-files

# Check for .env file and required variables
check-env:
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Please create one with GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and SECRET_KEY."; \
		exit 1; \
	fi
	@for var in GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET SECRET_KEY; do \
		if ! grep -q "^$$var=" .env; then \
			echo "Error: Required variable '$$var' is not set in the .env file."; \
			exit 1; \
		fi \
	done

# Check if uv is installed (https://docs.astral.sh/uv/getting-started/installation/)
check-uv:
	@if ! command -v uv >/dev/null 2>&1; then \
		echo "Error: uv is not installed. Install with:"; \
		echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"; \
		echo "or: pip install --user uv"; \
		exit 1; \
	fi

# Check if gcloud is installed
check-gcloud:
	@if ! command -v gcloud >/dev/null 2>&1; then \
		echo "Error: gcloud is not installed. Please install it first:"; \
		echo "$$GCLOUD_INSTALL_INSTRUCTIONS"; \
		exit 1; \
	fi

# Check if user is logged into gcloud
check-gcloud-auth:
	@if [ -z "$$(gcloud auth list --filter=status:ACTIVE --format='value(account)')" ]; then \
		echo "Error: You are not logged into gcloud. Please run 'gcloud auth login' and try again."; \
		exit 1; \
	fi

# Check for gcloud application default credentials
check-gcloud-adc:
	@if [ ! -f "$$HOME/.config/gcloud/application_default_credentials.json" ]; then \
		echo "Error: Google Cloud Application Default Credentials not found."; \
		echo "Please run 'gcloud auth application-default login' to configure them."; \
		exit 1; \
	fi

define GCLOUD_INSTALL_INSTRUCTIONS
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash

# Reload your shell
source ~/.bashrc

# Initialize gcloud
gcloud init
endef
export GCLOUD_INSTALL_INSTRUCTIONS

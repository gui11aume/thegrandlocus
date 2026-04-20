# Makefile for The Grand Locus project
PYTHON_VERSION := 3.12.8

POETRY := PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring poetry
POE := $(POETRY) run poe

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
.PHONY: help install run deploy deploy-prod deploy-staging cloudrun-deploy logs logs-staging \
	undeploy undeploy-staging pre-commit check-env check-gcloud check-gcloud-auth check-gcloud-adc

# Default target when running `make` without arguments.
default: help

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@echo "  install    Install/update Python dependencies from requirements.txt"
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

install: check-pyenv check-poetry
	pyenv install -s $(PYTHON_VERSION)
	pyenv local $(PYTHON_VERSION)
	$(POETRY) env use $$(pyenv which python)
	$(POETRY) install --only main

install-dev: install
	$(POETRY) install --only dev
	$(POETRY) run pre-commit install

clean: check-poetry
	$(POETRY) env remove --all
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete

run: install check-env check-gcloud check-gcloud-adc
	$(POETRY) run python run.py

backup: install check-gcloud-adc
	$(POETRY) run python scripts/backup_posts.py

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
	$(POETRY) run pytest

pre-commit: install-dev
	$(POETRY) run pre-commit run --color=always --all-files

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

# Check if pyenv is installed
check-pyenv:
	@if ! command -v pyenv >/dev/null 2>&1; then \
		echo "Error: pyenv is not installed. Please install it first:"; \
		echo "$$PYENV_INSTALL_INSTRUCTIONS"; \
		exit 1; \
	fi

# Check if poetry is installed
check-poetry:
	@if ! command -v poetry >/dev/null 2>&1; then \
		echo "Error: poetry is not installed. Please install it first:"; \
		echo "$$POETRY_INSTALL_INSTRUCTIONS"; \
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

# Installation instructions
define PYENV_INSTALL_INSTRUCTIONS
# Install pyenv dependencies
sudo apt-get update
sudo apt-get install -y make build-essential libssl-dev zlib1g-dev \
libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev \
libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python3-openssl git

# Install pyenv
curl https://pyenv.run | bash

# Add pyenv to PATH (add these lines to your ~/.bashrc or ~/.zshrc)
export PYENV_ROOT="$$HOME/.pyenv"
export PATH="$$PYENV_ROOT/bin:$$PATH"
eval "$$(pyenv init --path)"

# Reload your shell
source ~/.bashrc
endef
export PYENV_INSTALL_INSTRUCTIONS

define POETRY_INSTALL_INSTRUCTIONS
# Option 1: Install poetry using apt
sudo apt-get install -y python3-poetry

# Option 2: Install poetry using curl
curl -sSL https://install.python-poetry.org | python3 -

# Option 3: Install poetry using pip
pip install poetry
endef
export POETRY_INSTALL_INSTRUCTIONS

define GCLOUD_INSTALL_INSTRUCTIONS
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash

# Reload your shell
source ~/.bashrc

# Initialize gcloud
gcloud init
endef
export GCLOUD_INSTALL_INSTRUCTIONS

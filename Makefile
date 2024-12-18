# Configuration variables
PROJECT_ID := $(shell gcloud config get-value project)
LOCATION := us-central1
BUILDER_NAME := github-ops-builder
BUILDER_TAG ?= latest  # Can be overridden by environment variable
BUILDER_IMAGE_LATEST := $(LOCATION)-docker.pkg.dev/$(PROJECT_ID)/docker/$(BUILDER_NAME):latest

# Test configuration
TEST_REPO_OWNER := test-owner
TEST_REPO_NAME := test-repo
TEST_PARENT_REPO := test-parent-repo
TEST_SUBMODULE_PATH := modules/test-module

# Directory structure setup
.PHONY: setup
setup:
	@mkdir -p builders/github-ops

# Install Python dependencies locally
.PHONY: install
install:
	@pip install -r requirements.txt

# Test the Docker image
.PHONY: test
test:
	@echo "Testing Docker image..."
	@docker run --rm $(BUILDER_IMAGE_LATEST) --help
	@echo "Basic test passed: Image can execute and show help message"

# Copy files to builder directory
.PHONY: copy-files
copy-files: setup
	@cp github_ops.py builders/github-ops/
	@cp cli.py builders/github-ops/
	@cp Dockerfile builders/github-ops/
	@cp requirements.txt builders/github-ops/

.PHONY: build
build: copy-files
	@echo "Building Docker image..."
	@cd builders/github-ops && docker build -t $(BUILDER_IMAGE_LATEST) .
	@if [ "$(BUILDER_TAG)" != "latest" ] && [ -n "$(BUILDER_TAG)" ]; then \
		echo "Tagging version $(BUILDER_TAG)..."; \
		docker tag $(BUILDER_IMAGE_LATEST) $(LOCATION)-docker.pkg.dev/$(PROJECT_ID)/docker/$(BUILDER_NAME):$(BUILDER_TAG); \
	fi

# Test commands
.PHONY: test-get-version
test-get-version:
	@echo "Testing get-version command..."
	@docker run --rm \
		-e GITHUB_TOKEN=${GITHUB_TOKEN} \
		$(BUILDER_IMAGE_LATEST) \
		--action get-version \
		--repo-owner $(TEST_REPO_OWNER) \
		--repo-name $(TEST_REPO_NAME)

# Push image(s)
.PHONY: push
push:
	@echo "Pushing latest tag..."
	@docker push $(BUILDER_IMAGE_LATEST)
	@if [ "$(BUILDER_TAG)" != "latest" ]; then \
		echo "Pushing version $(BUILDER_TAG)..."; \
		docker push $(LOCATION)-docker.pkg.dev/$(PROJECT_ID)/docker/$(BUILDER_NAME):$(BUILDER_TAG); \
	fi

# Refresh Docker credentials
.PHONY: refresh
refresh:
	@echo "Refreshing credentials..."
	@docker logout https://$(LOCATION)-docker.pkg.dev
	@gcloud auth print-access-token | docker login -u oauth2accesstoken --password-stdin https://$(LOCATION)-docker.pkg.dev

# Configure Docker authentication
.PHONY: configure-docker
configure-docker:
	@echo "Configuring Docker authentication..."
	@gcloud auth configure-docker $(LOCATION)-docker.pkg.dev

# All-in-one command to build and push
.PHONY: deploy
deploy: configure-docker build test push
	@if [ "$(BUILDER_TAG)" != "latest" ]; then \
		echo "Successfully built and pushed images:"; \
		echo "  - $(LOCATION)-docker.pkg.dev/$(PROJECT_ID)/docker/$(BUILDER_NAME):$(BUILDER_TAG)"; \
		echo "  - $(BUILDER_IMAGE_LATEST)"; \
	else \
		echo "Successfully built and pushed image:"; \
		echo "  - $(BUILDER_IMAGE_LATEST)"; \
	fi

# Clean up build artifacts and images
.PHONY: clean
clean:
	@echo "Cleaning up..."
	@rm -rf builders
	@rm -f current_version.txt new_version.txt
	@docker rmi $(BUILDER_IMAGE_LATEST) || true
	@if [ "$(BUILDER_TAG)" != "latest" ]; then \
		docker rmi $(LOCATION)-docker.pkg.dev/$(PROJECT_ID)/docker/$(BUILDER_NAME):$(BUILDER_TAG) || true; \
	fi


# List all versions of the image
.PHONY: list-versions
list-versions:
	@echo "Listing all versions of $(BUILDER_NAME)..."
	@gcloud artifacts docker tags list $(LOCATION)-docker.pkg.dev/$(PROJECT_ID)/docker/$(BUILDER_NAME) \
		--sort-by=~CREATE_TIME \
		--format="table[box](tag,version,metadata.create_time)"

# Show detailed information about a specific version
.PHONY: describe-version
describe-version:
	@if [ -z "$(VERSION)" ]; then \
		echo "Usage: make describe-version VERSION=<tag>"; \
		exit 1; \
	fi
	@echo "Showing details for version $(VERSION)..."
	@gcloud artifacts docker images describe $(LOCATION)-docker.pkg.dev/$(PROJECT_ID)/docker/$(BUILDER_NAME):$(VERSION) \
		--format="yaml"

# Delete a specific version
.PHONY: delete-version
delete-version:
	@if [ -z "$(VERSION)" ]; then \
		echo "Usage: make delete-version VERSION=<tag>"; \
		exit 1; \
	fi
	@if [ "$(VERSION)" = "latest" ]; then \
		echo "Error: Cannot delete 'latest' tag as it's required for the build process"; \
		exit 1; \
	fi
	@echo "WARNING: About to delete version $(VERSION) of $(BUILDER_NAME)"
	@echo "Are you sure? [y/N] " && read ans && [ $${ans:-N} = y ]
	@gcloud artifacts docker tags delete $(LOCATION)-docker.pkg.dev/$(PROJECT_ID)/docker/$(BUILDER_NAME):$(VERSION) --quiet
	@echo "Version $(VERSION) deleted successfully"

# Display help information
.PHONY: help
help:
	@echo "Available commands:"
	@echo "  make install        - Install Python dependencies locally"
	@echo "  make setup          - Create necessary directories"
	@echo "  make build          - Build the Docker image"
	@echo "  make test          - Test the Docker image"
	@echo "  make test-local    - Run CLI tests locally"
	@echo "  make test-all      - Run all Docker-based tests"
	@echo "  make push          - Push image(s) to Docker repository"
	@echo "  make deploy        - Configure Docker, build, test, and push"
	@echo "  make clean         - Clean up build artifacts and remove Docker images"
	@echo "  make list-versions - List the 10 most recent versions of the image"
	@echo "  make help          - Display this help message"
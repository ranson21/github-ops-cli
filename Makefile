# Configuration variables
PROJECT_ID := $(shell gcloud config get-value project)
LOCATION := us-central1
BUILDER_NAME := github-ops-builder
BUILDER_TAG := latest
BUILDER_IMAGE := $(LOCATION)-docker.pkg.dev/$(PROJECT_ID)/docker/$(BUILDER_NAME):$(BUILDER_TAG)

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

# Copy files to builder directory
.PHONY: copy-files
copy-files: setup
	@cp github_ops.py builders/github-ops/
	@cp cli.py builders/github-ops/
	@cp Dockerfile builders/github-ops/
	@cp requirements.txt builders/github-ops/

# Build the Docker image
.PHONY: build
build: copy-files
	@echo "Building $(BUILDER_IMAGE)..."
	@cd builders/github-ops && docker build -t $(BUILDER_IMAGE) .

# Test commands for each CLI action
.PHONY: test-get-version
test-get-version:
	@echo "Testing get-version command..."
	@docker run --rm \
		-e GITHUB_TOKEN=${GITHUB_TOKEN} \
		$(BUILDER_IMAGE) \
		--action get-version \
		--repo-owner $(TEST_REPO_OWNER) \
		--repo-name $(TEST_REPO_NAME)

.PHONY: test-bump-version
test-bump-version:
	@echo "Testing bump-version command..."
	@echo "v1.0.0" > current_version.txt
	@docker run --rm \
		-v $(PWD)/current_version.txt:/current_version.txt \
		-e GITHUB_TOKEN=${GITHUB_TOKEN} \
		$(BUILDER_IMAGE) \
		--action bump-version \
		--repo-owner $(TEST_REPO_OWNER) \
		--repo-name $(TEST_REPO_NAME) \
		--current-version v1.0.0 \
		--version-type patch \
		--pr-number 123

.PHONY: test-create-release
test-create-release:
	@echo "Testing create-release command..."
	@echo "v1.0.1" > new_version.txt
	@docker run --rm \
		-v $(PWD)/new_version.txt:/new_version.txt \
		-e GITHUB_TOKEN=${GITHUB_TOKEN} \
		$(BUILDER_IMAGE) \
		--action create-release \
		--repo-owner $(TEST_REPO_OWNER) \
		--repo-name $(TEST_REPO_NAME) \
		--current-version v1.0.1

.PHONY: test-update-submodule
test-update-submodule:
	@echo "Testing update-submodule command..."
	@echo "v1.0.1" > new_version.txt
	@docker run --rm \
		-v $(PWD)/new_version.txt:/new_version.txt \
		-e GITHUB_TOKEN=${GITHUB_TOKEN} \
		$(BUILDER_IMAGE) \
		--action update-submodule \
		--repo-owner $(TEST_REPO_OWNER) \
		--repo-name $(TEST_REPO_NAME) \
		--parent-repo $(TEST_PARENT_REPO) \
		--submodule-path $(TEST_SUBMODULE_PATH) \
		--is-merge true

# Run all tests
.PHONY: test-all
test-all: test-get-version test-bump-version test-create-release test-update-submodule

# Local development testing
.PHONY: test-local
test-local: install
	@echo "Running local CLI tests..."
	@python cli.py --help

# Test the Docker image
.PHONY: test
test: build
	@echo "Testing $(BUILDER_IMAGE)..."
	@docker run --rm $(BUILDER_IMAGE) --help

# Push the image to Docker Repository
.PHONY: push
push: build
	@echo "Pushing $(BUILDER_IMAGE)..."
	@docker push $(BUILDER_IMAGE)

# Refresh Docker credentials
.PHONY: refresh
refresh:
	@echo "Refreshing credentials..."
	@docker logout https://us-central1-docker.pkg.dev
	@gcloud auth print-access-token | docker login -u oauth2accesstoken --password-stdin https://us-central1-docker.pkg.dev

# Configure Docker authentication
.PHONY: configure-docker
configure-docker:
	@echo "Configuring Docker authentication..."
	@gcloud auth configure-docker $(LOCATION)-docker.pkg.dev

# All-in-one command to build and push
.PHONY: deploy
deploy: configure-docker build test push
	@echo "Successfully built and pushed $(BUILDER_IMAGE)"

# Clean up build artifacts
.PHONY: clean
clean:
	@echo "Cleaning up..."
	@rm -rf builders
	@rm -f current_version.txt new_version.txt
	@docker rmi $(BUILDER_IMAGE) || true

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
	@echo "  make push          - Push the image to Docker repository"
	@echo "  make deploy        - Configure Docker, build, test, and push"
	@echo "  make clean         - Clean up build artifacts"
	@echo "  make help          - Display this help message"
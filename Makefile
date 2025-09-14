SHELL := /bin/bash

.PHONY: help build run deploy

help:
	@echo "Usage:"
	@echo "  make build    - Build Docker image (local+remote)"
	@echo "  make run      - Run locally (uses last built image)"
	@echo "  make deploy   - Deploy to Cloud Run (uses last built image)"

# Always run through bash, no need for +x permission
build:
	bash ./scripts/build.sh

run: build
	bash ./scripts/run_local.sh

deploy: build
	bash ./scripts/deploy.sh

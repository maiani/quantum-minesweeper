SHELL := /bin/bash

.PHONY: help build run deploy browser browser-serve

help:
	@echo "Usage:"
	@echo "  make build         - Build Docker image (local+remote)"
	@echo "  make run           - Run locally (uses last built image)"
	@echo "  make deploy        - Deploy to Cloud Run (uses last built image)"
	@echo "  make browser       - Build the static browser-only bundle into dist/"
	@echo "  make browser-serve - Build it and serve at http://127.0.0.1:8000"

# Always run through bash, no need for +x permission
build:
	bash ./scripts/build.sh

# Static browser-only build (no server): Pyodide runs the game in the page.
browser:
	python scripts/build_browser.py

browser-serve: browser
	python -m http.server -d dist 8000

run: build
	bash ./scripts/run_local.sh

deploy: build
	bash ./scripts/deploy.sh

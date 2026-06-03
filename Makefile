SHELL := /bin/bash
PORT ?= 8000

.PHONY: help build run deploy icons browser browser-serve check

help:
	@echo "Usage:"
	@echo "  make build             - Build Docker image (local+remote)"
	@echo "  make run               - Run locally (uses last built image)"
	@echo "  make deploy            - Deploy to Cloud Run (uses last built image)"
	@echo "  make icons             - Regenerate PWA PNG icons from static/icons/icon.svg"
	@echo "  make browser           - Build the static browser-only bundle into dist/"
	@echo "  make browser-serve     - Build it and serve at http://127.0.0.1:$(PORT)"
	@echo "  make check             - Run focused release/build checks"

# Always run through bash, no need for +x permission
build:
	bash ./scripts/build.sh

icons:
	python scripts/make_icons.py

# Static browser-only build (no server): Pyodide runs the game in the page.
browser: icons
	python scripts/build_browser.py

browser-serve: browser
	python -m http.server -d dist $(PORT)

check:
	python -m ruff check qminesweeper tests scripts
	pytest -q
	node --check qminesweeper/static/scripts/pyodide-engine.js
	node --check qminesweeper/static/scripts/browser-main.js

run: build
	bash ./scripts/run_local.sh

deploy: build
	bash ./scripts/deploy.sh

set shell := ["bash", "-euo", "pipefail", "-c"]

# List available project commands.
default:
    @just --list

# Run Python lint checks.
lint:
    python -m ruff check qminesweeper tests scripts

# Run the Python test suite.
test:
    pytest

# Check JavaScript entry-point syntax.
js-check:
    node --check qminesweeper/static/scripts/pyodide-engine.js
    node --check qminesweeper/static/scripts/browser-main.js

# Run the fast development checks.
check: lint test js-check

# Build the wheel and source distribution away from the browser dist directory.
package:
    python -m build --outdir build/packages

# Regenerate PWA PNG icons from the SVG source.
icons:
    python scripts/make_icons.py

# Build the static browser-only PWA into dist using the tracked icons.
browser:
    python scripts/build_browser.py

# Build and serve the browser-only PWA locally.
browser-serve port="8000": browser
    python -m http.server -d dist "{{port}}"

# Build the local Docker image.
docker-build:
    bash ./scripts/build.sh

# Build and run the local Docker image.
docker-run: docker-build
    bash ./scripts/run_local.sh

# Build distributions and run all non-Docker release checks.
release-check: check package browser

# Build, push, and deploy the configured image to Cloud Run.
deploy:
    bash ./scripts/deploy.sh

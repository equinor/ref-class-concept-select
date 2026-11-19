.PHONY: setup check manifest manifest-verify sodir facts facts-validate test lint format

# Install the environment with every domain's dependencies.
setup:
	uv sync --all-groups

# Everything that must hold before work is handed off or committed.
check: manifest-verify facts-validate test lint

# Rewrite data/manifest.csv from the raw data (after adding a source).
manifest:
	uv run python -m syskit.manifest create

manifest-verify:
	uv run python -m syskit.manifest verify

# Download a new dated snapshot of the Sodir tables.
sodir:
	uv run python -m syskit.sodir snapshot

# Rewrite data/facts/sodir.csv from the latest snapshot.
facts:
	uv run python -m syskit.sodir facts

facts-validate:
	uv run python -m syskit.facts validate

test:
	uv run pytest -q

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

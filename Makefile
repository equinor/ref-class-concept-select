.PHONY: setup check manifest manifest-verify sodir facts facts-validate test lint format \
	flow-deck flow-run flow-compare public doc-volve

VOLVE_DATA ?= ../volve_data
FLOW_DECK_DIR = $(VOLVE_DATA)/eclipse_model/sim_model_PPA-eclipse
FLOW_RUN_DIR = $(CURDIR)/agents/sim/work/volve_2016_flow/run
FLOW_PROCESSES ?= 8

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

# Write the OPM Flow version of the Volve deck beside the original (four _FLOW files).
flow-deck:
	uv run python -m simkit.flow_deck build

# Run it. Output goes to agents/sim/work/, never into the data directory.
flow-run:
	mkdir -p $(FLOW_RUN_DIR)
	cd $(FLOW_DECK_DIR) && mpirun -np $(FLOW_PROCESSES) flow VOLVE_2016_FLOW.DATA \
		--output-dir=$(FLOW_RUN_DIR) > $(FLOW_RUN_DIR)/flow.log 2>&1

# Compare the Flow run with the shipped Eclipse results.
flow-compare:
	uv run python -m simkit.compare init $(FLOW_RUN_DIR)
	uv run python -m simkit.compare summary $(FLOW_RUN_DIR)
	uv run python -m simkit.compare balance $(FLOW_RUN_DIR)

# Download new dated snapshots of the public price series (CPI, Brent).
public:
	uv run python -m syskit.public snapshot

# Rebuild what the doc domain generates from data: plot data, facts, redrawn charts, report.
doc-volve:
	uv run python -m dockit.pud_plots extract
	uv run python -m dockit.pud_facts write
	uv run python -m dockit.disc_facts write
	uv run python -m dockit.pud_redraw draw
	uv run python -m dockit.pud_report build

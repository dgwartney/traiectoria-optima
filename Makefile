# This directory is for raw data fetched from external sources
RAW_DATA_DIR=data/raw

# This directory is the output of our processed data
PROCESSED_DATA_DIR=data/processed

# This directory is intermediate processing of data
INTERMEDIATE_DATA_DIR=data/intermediate

# This file represents the sqlite database with the flight data cleaned and ready to use
FLIGHT_DATA_DB=flight_data.db

# Build the full path to the sqlite database
FLIGHT_DATA_DB_PATH=$(PROCESSED_DATA_DIR)/$(FLIGHT_DATA_DB)

# Configure our source and data directories
SRC_DIR=src
SRC_DATA_DIR=$(SRC_DIR)/data

# Specific python file to process the flight data
SRC_FLIGHT_DATA_DB=$(SRC_DATA_DIR)/flight_data.py

# Builds the processed network (airports + routes) from the raw sources
SRC_FLIGHT_NETWORK=$(SRC_DATA_DIR)/flight_network.py

# Where immutable, checksummed slices of the processed network are frozen
SNAPSHOT_DIR=data/snapshots

# Where experiments live: a directory each, pinning a snapshot.
EXPERIMENT_DIR=experiments

# Creates and slices snapshots, and scaffolds experiments. These know the
# repository's layout, which is why they are scripts rather than package code.
SCRIPTS_DIR=scripts
SRC_NEW_SNAPSHOT=$(SCRIPTS_DIR)/new_snapshot.py
SRC_NEW_EXPERIMENT=$(SCRIPTS_DIR)/new_experiment.py

# The narrowing that reproduces the dataset published before the pipeline went
# global: United, US large airports, both endpoints. Kept as a snapshot rather
# than as the pipeline's output.
LEGACY_SNAPSHOT_FILTERS=--airline UA --airport-type large_airport --country US

# SQL script that derives the United Airlines tables from the SQLite database
# and spools them out as the two processed CSV files
SRC_SQL_DIR=$(SRC_DIR)/sql
FLIGHT_DATA_SQL=$(SRC_SQL_DIR)/flight_data.sql
AIRPORTS_CSV=$(PROCESSED_DATA_DIR)/airports.csv
ROUTES_CSV=$(PROCESSED_DATA_DIR)/routes.csv

# Raw source data files loaded into the sqlite database by flight_data.py
OPEN_FLIGHTS_DIR=$(RAW_DATA_DIR)/open_flights
OUR_AIRPORTS_DIR=$(RAW_DATA_DIR)/our_airports
OPEN_FLIGHTS_AIRPORTS=$(OPEN_FLIGHTS_DIR)/airports.dat
OPEN_FLIGHTS_ROUTES=$(OPEN_FLIGHTS_DIR)/routes.dat
OUR_AIRPORTS_AIRPORTS=$(OUR_AIRPORTS_DIR)/airports.csv

#
# Definitions for the markdown to PDF generation with mermaid or .svg files
DOCS_DIR       = docs
DOCS_TEMPLATES = $(DOCS_DIR)/templates
DOCS_MERMAID   = $(DOCS_DIR)/mermaid
DOC_HEADER     = $(DOCS_TEMPLATES)/doc-header.tex
SVG_FILTER     = $(DOCS_DIR)/svg-to-png.lua

BUILD_DIR = build
PDF_DIR   = $(BUILD_DIR)/pdf
SVG_DIR   = $(BUILD_DIR)/svg
PNG_DIR   = $(BUILD_DIR)/png

MD_SRCS  := $(wildcard $(DOCS_DIR)/*.md)
MMD_SRCS := $(wildcard $(DOCS_MERMAID)/*.mmd)
PDFS     := $(MD_SRCS:$(DOCS_DIR)/%.md=$(PDF_DIR)/%.pdf)
SVGS     := $(MMD_SRCS:$(DOCS_MERMAID)/%.mmd=$(SVG_DIR)/%.svg)
PNGS     := $(MMD_SRCS:$(DOCS_MERMAID)/%.mmd=$(PNG_DIR)/%.png)

# Arguments we require for pandoc
PANDOC_FLAGS := \
	--pdf-engine=xelatex \
	--resource-path=$(DOCS_DIR) \
	--lua-filter=$(SVG_FILTER) \
	--include-in-header=$(DOC_HEADER)

# Quality gates below record success as a stamp file here rather than an
# output artifact, since pytest and ruff don't produce one.
STAMP_DIR = .make

# Every Python file the test and lint gates should re-run for
PY_SRC   := $(shell find $(SRC_DIR) -name '*.py' -not -path '*/__pycache__/*')
PY_TESTS := $(shell find tests -name '*.py' -not -path '*/__pycache__/*')

.PHONY: all help notebook flight_data flight_network snapshot legacy_snapshot experiment united_airlines_tables international_airports verify_iata_codes test lint check docs clean

.DEFAULT_GOAL := help

all: check 

help: ## Show this list of targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

#
# Start a jupyter lab session from the install virtual
# environment setup by `uv`
notebook: ## Start a Jupyter Lab session
	uv sync --group notebooks
	uv run jupyter lab

# Build all project docs (project_plan.md, report.md, ...) to PDF
docs: $(PDFS)

$(SVG_DIR)/%.svg: $(DOCS_MERMAID)/%.mmd | $(SVG_DIR)
	mmdc -i $< -o $@

$(PNG_DIR)/%.png: $(SVG_DIR)/%.svg | $(PNG_DIR)
	rsvg-convert -f png $< -o $@

$(PDF_DIR)/%.pdf: $(DOCS_DIR)/%.md $(SVG_FILTER) $(DOC_HEADER) | $(PNGS) $(PDF_DIR)
	pandoc $< -o $@ $(PANDOC_FLAGS)

$(PDF_DIR) $(SVG_DIR) $(PNG_DIR):
	mkdir -p $@

check-deps:
	@for cmd in pandoc xelatex mmdc rsvg-convert; do \
	  command -v $$cmd >/dev/null 2>&1 && echo "✓ $$cmd" || echo "✗ $$cmd MISSING"; \
	done

clean: ## Remove generated data, build output, and make stamp files
	$(RM) $(FLIGHT_DATA_DB_PATH) $(AIRPORTS_RAW_JSON) $(INTERNATIONAL_AIRPORTS_CSV)
	$(RM) $(AIRPORTS_CSV) $(ROUTES_CSV)
	$(RM) -r $(STAMP_DIR)
	$(RM) -r $(BUILD_DIR)

.PHONY: notebook flight_data docs check-deps clean

#
# --- Data pipeline ----------------------------------------------------
# Real file target: only regenerates the DB when flight_data.py (or the
# raw inputs it reads) is newer than the existing DB file.
#

SRC_GENERATE_AIRPORTS_RAW=$(SRC_DATA_DIR)/generate_airports_raw.py
SRC_INTERNATIONAL_AIRPORTS=$(SRC_DATA_DIR)/international_airports.py
SRC_VERIFY_IATA_CODES=$(SRC_DATA_DIR)/verify_iata_codes.py
IATA_CODE_OVERRIDES=data/reference/iata_code_overrides.csv
AIRPORTS_RAW_JSON=data/raw/wikipedia/airports_raw.json
INTERNATIONAL_AIRPORTS_CSV=$(PROCESSED_DATA_DIR)/international_airports.csv

#
# Step 1: scrape the raw Wikipedia airport list (network + Playwright).
#
$(AIRPORTS_RAW_JSON): $(SRC_GENERATE_AIRPORTS_RAW)
	uv run python $(SRC_GENERATE_AIRPORTS_RAW) $(AIRPORTS_RAW_JSON)

#
# Step 2: attach coordinates to the scraped airports from the OurAirports
# data we already vendor, patching the ten codes that do not join through
# $(IATA_CODE_OVERRIDES). No network access.
#
# The prerequisites are order-only (after the `|`) so this step is skipped
# entirely whenever the CSV already exists. The step is cheap now, but the CSV
# is committed output -- a rebuild should be deliberate rather than triggered
# by a newer scrape or script. Delete the CSV (or `make clean`) to force one.
#
$(INTERNATIONAL_AIRPORTS_CSV): | $(AIRPORTS_RAW_JSON) $(SRC_INTERNATIONAL_AIRPORTS) $(IATA_CODE_OVERRIDES)
	uv run python $(SRC_INTERNATIONAL_AIRPORTS) \
		$(AIRPORTS_RAW_JSON) \
		$(OUR_AIRPORTS_AIRPORTS) \
		$(IATA_CODE_OVERRIDES) \
		$(INTERNATIONAL_AIRPORTS_CSV)

#
# Audit tool, not a data target: re-checks $(IATA_CODE_OVERRIDES) against
# IATA's live registry. Run by hand when the table is suspected stale.
#
verify_iata_codes: ## Re-check the IATA code overrides against iata.org
	uv run python $(SRC_VERIFY_IATA_CODES) $(IATA_CODE_OVERRIDES)

#
# The loader appends to whatever tables already exist, so remove any stale
# database first -- otherwise a rebuild doubles up every row.
#
$(FLIGHT_DATA_DB_PATH): $(SRC_FLIGHT_DATA_DB) $(INTERNATIONAL_AIRPORTS_CSV) \
		$(OPEN_FLIGHTS_AIRPORTS) $(OPEN_FLIGHTS_ROUTES) $(OUR_AIRPORTS_AIRPORTS)
	$(RM) $(FLIGHT_DATA_DB_PATH)
	uv run python $(SRC_FLIGHT_DATA_DB) \
		$(OPEN_FLIGHTS_AIRPORTS) \
		$(OPEN_FLIGHTS_ROUTES) \
		$(OUR_AIRPORTS_AIRPORTS) \
		$(INTERNATIONAL_AIRPORTS_CSV) \
		$(FLIGHT_DATA_DB_PATH)

flight_data: $(FLIGHT_DATA_DB_PATH) ## Load source data into data/processed/flight_data.db

#
# Step 4: derive the processed network from the raw sources.
#
# One invocation writes both $(AIRPORTS_CSV) and $(ROUTES_CSV), so a
# stamp file stands in as the target -- the same idiom the test/lint gates
# below use. (GNU Make 3.81 ships on macOS and has no grouped `&:` targets.)
#
# Note this no longer depends on $(FLIGHT_DATA_DB_PATH): the network is built
# straight from the raw files with pandas, so a clone without the sqlite3
# binary can still produce the dataset.
#
$(STAMP_DIR)/flight_network: $(SRC_FLIGHT_NETWORK) $(OUR_AIRPORTS_AIRPORTS) \
		$(OPEN_FLIGHTS_ROUTES) $(INTERNATIONAL_AIRPORTS_CSV) | $(STAMP_DIR)
	uv run python $(SRC_FLIGHT_NETWORK) \
		$(OUR_AIRPORTS_AIRPORTS) \
		$(OPEN_FLIGHTS_ROUTES) \
		$(AIRPORTS_CSV) \
		$(ROUTES_CSV) \
		--international $(INTERNATIONAL_AIRPORTS_CSV) \
		--database $(FLIGHT_DATA_DB_PATH)
	touch $@

flight_network: $(STAMP_DIR)/flight_network ## Rebuild data/processed/{airports,routes}.csv and the DB tables

#
# Freeze the processed network, whole or sliced. Experiments pin a snapshot
# rather than the processed files, which keep moving as the pipeline changes.
#
# Narrowing goes through the same `Catalog` an experiment uses, so a
# snapshot's criteria mean what they mean in a notebook, and the manifest
# records the chain step by step. Pass narrowings through SNAPSHOT_FILTERS:
#
#   make snapshot
#   make snapshot SNAPSHOT_FILTERS="--airline UA --airport-type large"
#
# Identical data always lands on the same id, so re-freezing is a no-op
# rather than a duplicate.
#
snapshot: $(AIRPORTS_CSV) ## Freeze data/processed as an immutable snapshot (SNAPSHOT_FILTERS=...)
	uv run python $(SRC_NEW_SNAPSHOT) \
		--airports-csv $(AIRPORTS_CSV) \
		--routes-csv $(ROUTES_CSV) \
		--root $(SNAPSHOT_DIR) \
		$(SNAPSHOT_FILTERS)

legacy_snapshot: ## Freeze the United/US-large slice as an immutable snapshot
	$(MAKE) snapshot SNAPSHOT_FILTERS="$(LEGACY_SNAPSHOT_FILTERS)"

#
# Scaffold an experiment: a directory pinning a snapshot, plus a starter
# notebook that runs end to end as written. Defaults to the most recently
# frozen snapshot; name another with SNAPSHOT=<id>.
#
#   make experiment SLUG=astar-heuristics
#   make experiment SLUG=astar-heuristics SNAPSHOT=2026-09-11-1528c4
#
experiment: ## Scaffold an experiment (SLUG=required, SNAPSHOT=optional)
	@test -n "$(SLUG)" || { echo "usage: make experiment SLUG=<name> [SNAPSHOT=<id>]" >&2; exit 1; }
	uv run python $(SRC_NEW_EXPERIMENT) $(SLUG) \
		--root $(EXPERIMENT_DIR) \
		--snapshot-root $(SNAPSHOT_DIR) \
		$(if $(SNAPSHOT),--snapshot $(SNAPSHOT),) \
		$(if $(DESCRIPTION),--description "$(DESCRIPTION)",)

#
# The exploratory SQL derivation. Not part of the CSV build -- it creates the
# United subset tables inside the database for ad-hoc querying, and is the one
# target that still needs the sqlite3 CLI.
#
united_airlines_tables: $(FLIGHT_DATA_SQL) $(FLIGHT_DATA_DB_PATH) ## Derive the United subset tables in the SQLite DB for exploration
	sqlite3 $(FLIGHT_DATA_DB_PATH) < $(FLIGHT_DATA_SQL)

# --- Quality gates ------------------------------------------------------
# pytest/ruff don't produce an output file to key off of, so each writes a
# stamp file on success; the stamp's mtime is what make compares against
# the source files to decide whether a re-run is required.

$(STAMP_DIR):
	mkdir -p $(STAMP_DIR)

$(STAMP_DIR)/test: $(PY_SRC) $(PY_TESTS) pyproject.toml | $(STAMP_DIR)
	uv run pytest
	touch $@

test: $(STAMP_DIR)/test ## Run the pytest suite

$(STAMP_DIR)/lint: $(PY_SRC) pyproject.toml | $(STAMP_DIR)
	uv run ruff check
	touch $@

lint: $(STAMP_DIR)/lint ## Run ruff checks

check: lint test ## Run lint and test


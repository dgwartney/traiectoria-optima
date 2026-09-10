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


.PHONY: all help notebook flight_data international_airports test lint check docs clean

.DEFAULT_GOAL := help

all: check 

help: ## Show this list of targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

#
# Start a jupyter lab session from the install virtual
# environment setup by `uv`
notebook: ## Start a Jupyter Lab session
	uv run jupyter lab

# Build all project docs (project_plan.md, report.md, ...) to PDF
docs: $(PDFS)

$(SVG_DIR)/%.svg: $(DOCS_MERMAID)/%.mmd | $(SVG_DIR)
	mmdc -i $< -o $@

$(PNG_DIR)/%.png: $(SVG_DIR)/%.svg | $(PNG_DIR)
	rsvg-convert -f png $< -o $@

# reference.md uses mkdocstrings' "::: identifier" autodoc syntax, which
# collides with pandoc's fenced_divs extension (each "::: name" implicitly
# closes the previous one, warning about unclosed divs). Disable that
# extension here since mkdocstrings-only content isn't renderable by pandoc
# anyway.
$(PDF_DIR)/reference.pdf: $(DOCS_DIR)/reference.md $(SVG_FILTER) $(DOC_HEADER) | $(PNGS) $(PDF_DIR)
	pandoc $< -o $@ --from=markdown-fenced_divs $(PANDOC_FLAGS)

$(PDF_DIR)/%.pdf: $(DOCS_DIR)/%.md $(SVG_FILTER) $(DOC_HEADER) | $(PNGS) $(PDF_DIR)
	pandoc $< -o $@ $(PANDOC_FLAGS)

$(PDF_DIR) $(SVG_DIR) $(PNG_DIR):
	mkdir -p $@

check-deps:
	@for cmd in pandoc xelatex mmdc rsvg-convert; do \
	  command -v $$cmd >/dev/null 2>&1 && echo "✓ $$cmd" || echo "✗ $$cmd MISSING"; \
	done

clean: ## Remove generated data, docs site, and make stamp files
	$(RM) $(FLIGHT_DATA_DB_PATH) $(AIRPORTS_RAW_JSON) $(INTERNATIONAL_AIRPORTS_CSV)
	$(RM) -r $(SITE_DIR) $(STAMP_DIR)
	$(RM) -r $(BUILD_DIR)

.PHONY: notebook flight_data docs check-deps clean

#
# --- Data pipeline ----------------------------------------------------
# Real file target: only regenerates the DB when flight_data.py (or the
# raw inputs it reads) is newer than the existing DB file.
#

SRC_GENERATE_AIRPORTS_RAW=$(SRC_DATA_DIR)/generate_airports_raw.py
SRC_FETCH_AIRPORT_COORDS=$(SRC_DATA_DIR)/fetch_airport_coords_api.py
AIRPORTS_RAW_JSON=data/raw/wikipedia/airports_raw.json
INTERNATIONAL_AIRPORTS_CSV=$(PROCESSED_DATA_DIR)/international_airports.csv

#
# Step 1: scrape the raw Wikipedia airport list (network + Playwright).
#
$(AIRPORTS_RAW_JSON): $(SRC_GENERATE_AIRPORTS_RAW)
	uv run python $(SRC_GENERATE_AIRPORTS_RAW)

#
# Step 2: resolve batch coordinates from the Wikipedia API into the CSV.
#
# The prerequisites are order-only (after the `|`) so this step is skipped
# entirely whenever the CSV already exists -- geocoding hits the network for
# every airport, so we don't want a newer scrape or script to trigger a
# re-run. Delete the CSV (or `make clean`) to force a rebuild.
#
$(INTERNATIONAL_AIRPORTS_CSV): | $(AIRPORTS_RAW_JSON) $(SRC_FETCH_AIRPORT_COORDS)
	uv run python $(SRC_FETCH_AIRPORT_COORDS) $(AIRPORTS_RAW_JSON) $(INTERNATIONAL_AIRPORTS_CSV)

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


# This directory is the output of our processed data
PROCESSED_DATA_DIR=data/processed
# This file represents the sqlite database with the flight data cleaned and ready to use
FLIGHT_DATA_DB=flight_data.db
# Build the full path to the sqlite database
FLIGHT_DATA_DB_PATH=$(PROCESSED_DATA_DIR)/$(FLIGHT_DATA_DB)

# Configure our source and data directories
SRC_DIR=src
SRC_DATA_DIR=$(SRC_DIR)/data

# Specific python file to process the flight data
SRC_FLIGHT_DATA_DB=$(SRC_DATA_DIR)/flight_data.py

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

PANDOC_FLAGS := \
	--pdf-engine=xelatex \
	--resource-path=$(DOCS_DIR) \
	--lua-filter=$(SVG_FILTER) \
	--include-in-header=$(DOC_HEADER)
=======
# Configure directories for mkdocs (see https://www.mkdocs.org/)
SITE_DIR=site
STAMP_DIR=.make

PY_SRC=$(shell find $(SRC_DIR) -name '*.py')
PY_TESTS=$(shell find tests -name '*.py')
DOCS_SRC=$(shell find docs -type f) mkdocs.yml

.PHONY: all help notebook flight_data test lint check docs docs-serve clean

.DEFAULT_GOAL := help

all: check docs ## Run all quality gates and build the docs site

help: ## Show this list of targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'
>>>>>>> 859af7c (Add complete Makefile ; mkdocs building of site, full documentation of existing code)

# Start a jupyter lab session from the install virtual
# environment setup by `uv`
notebook: ## Start a Jupyter Lab session
	uv run jupyter lab

<<<<<<< HEAD
flight_data:
	uv run python $(SRC_FLIGHT_DATA_DB)

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

clean:
	$(RM) $(PROCESSED_DATA_DIR)/$(FLIGHT_DATA_DB)
	$(RM) -r $(BUILD_DIR)

.PHONY: notebook flight_data docs check-deps clean
=======
# --- Data pipeline ----------------------------------------------------
# Real file target: only regenerates the DB when flight_data.py (or the
# raw inputs it reads) is newer than the existing DB file.

$(FLIGHT_DATA_DB_PATH): $(SRC_FLIGHT_DATA_DB)
	uv run python $(SRC_FLIGHT_DATA_DB)

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

# --- Documentation --------------------------------------------------------
# Real file target: mkdocs only rebuilds when docs/, mkdocs.yml, or the
# documented source files have changed since the last build.

$(SITE_DIR)/index.html: $(DOCS_SRC) $(PY_SRC) mkdocs.yml
	uv run mkdocs build

docs: $(SITE_DIR)/index.html ## Build the mkdocs site into site/

docs-serve: ## Serve the docs site locally with live reload
	uv run mkdocs serve

clean: ## Remove generated data, docs site, and make stamp files
	$(RM) $(FLIGHT_DATA_DB_PATH)
	$(RM) -r $(SITE_DIR) $(STAMP_DIR)

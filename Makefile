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
DOCS_IMAGES    = $(DOCS_DIR)/images
MERMAID_DIR    = mermaid
DOC_HEADER     = $(DOCS_TEMPLATES)/doc-header.tex
SVG_FILTER     = $(DOCS_DIR)/svg-to-png.lua

# Slide blocks live inside the report chapters, so exactly one of these two
# filters runs on every build: the report drops them, the deck keeps only them.
# One source, two deliverables, no drift.
DROP_SLIDES_FILTER = $(DOCS_DIR)/drop-slides.lua
DECK_SLIDES_FILTER = $(DOCS_DIR)/deck-slides.lua

BUILD_DIR = build
PDF_DIR   = $(BUILD_DIR)/pdf
PNG_DIR   = $(BUILD_DIR)/png
HTML_DIR  = $(BUILD_DIR)/html

# One markdown file per slide, extracted from the chapters. Build output, not
# a source directory -- edit the chapter, not the extracted file.
DECK_SLIDES_DIR = $(BUILD_DIR)/deck
DECK_DIR        = $(DOCS_DIR)/deck
DECK_MANIFEST   = $(DECK_DIR)/manifest.txt
DECK_CSS        = $(DOCS_TEMPLATES)/deck.css
DECK_HTML       = $(HTML_DIR)/deck.html
DECK_PDF        = $(PDF_DIR)/deck.pdf
SRC_BUILD_DECK  = $(SCRIPTS_DIR)/build_deck.py
SRC_EXPORT_DECK = $(SCRIPTS_DIR)/export_deck_pdf.py

# reveal.js is fetched rather than committed: vendored JavaScript in a
# repository whose point is from-scratch algorithms invites the wrong question.
# The cost is one networked fetch per clone.
REVEAL_VERSION = 5.1.0
REVEAL_DIR     = vendor/reveal.js
REVEAL_TARBALL = https://github.com/hakimel/reveal.js/archive/refs/tags/$(REVEAL_VERSION).tar.gz

# The deck-only slides -- title, agenda, questions -- have no chapter home.
DECK_ONLY_SRCS := $(wildcard $(DECK_DIR)/*.md)

# Width of generated diagram PNGs, in pixels. Large enough to stay sharp when
# scaled to the 6.5in text column.
DIAGRAM_WIDTH = 1600

# The final report is one file per chapter under $(REPORT_DIR), assembled into a
# single PDF by the `report` target. Chapters are listed rather than globbed:
# the order is the document's order, and it is not the order `ls` gives once a
# chapter is renamed or inserted.
REPORT_DIR = $(DOCS_DIR)/report
REPORT_PDF = $(PDF_DIR)/report.pdf

REPORT_FRONTMATTER = $(REPORT_DIR)/00-frontmatter.md

REPORT_CHAPTERS = \
	$(REPORT_DIR)/01-introduction.md \
	$(REPORT_DIR)/02-dataset.md \
	$(REPORT_DIR)/03-graph-construction.md \
	$(REPORT_DIR)/04-algorithms.md \
	$(REPORT_DIR)/05-correctness-testing.md \
	$(REPORT_DIR)/06-complexity-analysis.md \
	$(REPORT_DIR)/07-empirical-evaluation.md \
	$(REPORT_DIR)/08-visualization.md \
	$(REPORT_DIR)/09-challenges-and-lessons-learned.md \
	$(REPORT_DIR)/10-conclusion.md \
	$(REPORT_DIR)/11-references.md \
	$(REPORT_DIR)/12-appendix.md

# A file holding nothing but a bare \newpage. Interleaving it between the
# chapters is what starts each one on a fresh page. It is a separate file
# because GitHub renders each chapter on its own page, where an inline
# \newpage would show as literal text; passed to pandoc as its own input, it
# reaches the PDF and appears in no rendered chapter.
REPORT_NEWPAGE = $(REPORT_DIR)/newpage.md

# Frontmatter, the first chapter, then every later chapter with a page break in
# front of it. The break goes before the *second* chapter onward so that the
# report's H1 shares a page with the introduction rather than sitting alone.
REPORT_SRCS = $(REPORT_FRONTMATTER) $(firstword $(REPORT_CHAPTERS)) \
	$(foreach chapter,$(wordlist 2,$(words $(REPORT_CHAPTERS)),$(REPORT_CHAPTERS)),\
		$(REPORT_NEWPAGE) $(chapter))

MD_SRCS  := $(wildcard $(DOCS_DIR)/*.md)
MMD_SRCS := $(wildcard $(MERMAID_DIR)/*.mmd)
PDFS     := $(MD_SRCS:$(DOCS_DIR)/%.md=$(PDF_DIR)/%.pdf)

# Two outputs per mermaid source, with different lifetimes:
#   .svg -> docs/images/, COMMITTED. What the markdown references, so the docs
#           render in a fresh clone and on GitHub, neither of which builds.
#   .png -> build/, generated. Only the PDF needs it; svg-to-png.lua rewrites
#           every .svg reference to the matching build/png file.
DIAGRAM_SVGS := $(MMD_SRCS:$(MERMAID_DIR)/%.mmd=$(DOCS_IMAGES)/%.svg)
PNGS         := $(MMD_SRCS:$(MERMAID_DIR)/%.mmd=$(PNG_DIR)/%.png)

# Arguments we require for pandoc
PANDOC_FLAGS := \
	--pdf-engine=xelatex \
	--resource-path=$(DOCS_DIR):$(DOCS_DIR)/report \
	--lua-filter=$(SVG_FILTER) \
	--lua-filter=$(DROP_SLIDES_FILTER) \
	--include-in-header=$(DOC_HEADER)

# Quality gates below record success as a stamp file here rather than an
# output artifact, since pytest and ruff don't produce one.
STAMP_DIR = .make

# Every Python file the test and lint gates should re-run for
PY_SRC   := $(shell find $(SRC_DIR) -name '*.py' -not -path '*/__pycache__/*')
PY_TESTS := $(shell find tests -name '*.py' -not -path '*/__pycache__/*')

.PHONY: all help notebook flight_data flight_network snapshot legacy_snapshot experiment united_airlines_tables international_airports verify_iata_codes test lint check docs report deck deck-pdf vendor-reveal diagrams clean

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

# Build all project docs (project_plan.md, status.md, ...) to PDF, the
# assembled final report included.
docs: $(PDFS) $(REPORT_PDF)

report: $(REPORT_PDF) ## Build the final report from docs/report/*.md into build/pdf/report.pdf

# Only the report gets a table of contents. The other docs are single-topic and
# short enough that one would be noise. Depth counts from `#`, which is a
# chapter: 2 reaches the `##` subsections (4.1, 6.3, ...), the deepest level
# the report uses today, and 3 leaves room for one level below them without a
# Makefile edit.
REPORT_TOC_FLAGS = --toc --toc-depth=3

# One pandoc invocation over every chapter in order. Pandoc concatenates its
# inputs before parsing, so cross-chapter section references resolve, the
# frontmatter's YAML governs the whole document, and the table of contents is
# built from every chapter rather than one at a time.
$(REPORT_PDF): $(REPORT_SRCS) $(SVG_FILTER) $(DROP_SLIDES_FILTER) $(DOC_HEADER) $(PNGS) | $(PDF_DIR)
	pandoc $(REPORT_SRCS) -o $@ $(PANDOC_FLAGS) $(REPORT_TOC_FLAGS)

#
# --- Deck -------------------------------------------------------------
# The deck has no sources of its own beyond the three deck-only slides. Its
# content is the `deck-slide` blocks inside the report chapters, which is why
# it depends on $(REPORT_CHAPTERS): edit a chapter and the deck rebuilds.
#

deck: $(DECK_HTML) ## Build the reveal.js deck from the report chapters

deck-pdf: $(DECK_PDF) ## Export the deck to build/pdf/deck.pdf

$(DECK_HTML): $(REPORT_CHAPTERS) $(DECK_ONLY_SRCS) $(DECK_MANIFEST) $(DECK_CSS) $(DECK_SLIDES_FILTER) $(SRC_BUILD_DECK) | $(REVEAL_DIR)
	uv run python $(SRC_BUILD_DECK) $(REPORT_CHAPTERS) \
	  --manifest $(DECK_MANIFEST) --slides-dir $(DECK_SLIDES_DIR) \
	  --out $@ --reveal $(REVEAL_DIR)

# Printed through reveal's own `?print-pdf` mode, so the PDF has one page per
# slide at the deck's own aspect ratio rather than a screenshot of a scroll.
$(DECK_PDF): $(DECK_HTML) $(SRC_EXPORT_DECK) | $(PDF_DIR)
	uv run python $(SRC_EXPORT_DECK) $(DECK_HTML) $@

vendor-reveal: $(REVEAL_DIR) ## Fetch reveal.js into vendor/ (gitignored; needed once per clone)

# Only `dist/` and `plugin/` are unpacked; the rest of the tarball is the
# project's own source, tests and demos, which we do not ship a copy of.
$(REVEAL_DIR):
	@mkdir -p $(dir $(REVEAL_DIR))
	curl -fsSL -o $(dir $(REVEAL_DIR))reveal.tgz $(REVEAL_TARBALL)
	tar xzf $(dir $(REVEAL_DIR))reveal.tgz -C $(dir $(REVEAL_DIR)) \
	  'reveal.js-$(REVEAL_VERSION)/dist' 'reveal.js-$(REVEAL_VERSION)/plugin'
	mv $(dir $(REVEAL_DIR))reveal.js-$(REVEAL_VERSION) $(REVEAL_DIR)
	$(RM) $(dir $(REVEAL_DIR))reveal.tgz

# Regenerate every diagram from its mermaid source.
diagrams: $(DIAGRAM_SVGS) $(PNGS) ## Rebuild diagrams from mermaid/*.mmd

# Rendered straight from .mmd by mmdc. Do not route this through
# rsvg-convert: it silently drops all text from a mermaid SVG.
$(DOCS_IMAGES)/%.svg: $(MERMAID_DIR)/%.mmd
	mmdc -i $< -o $@

$(PNG_DIR)/%.png: $(MERMAID_DIR)/%.mmd | $(PNG_DIR)
	mmdc -i $< -o $@ -w $(DIAGRAM_WIDTH)

# $(PNGS) is a real prerequisite, not order-only, so editing a diagram
# rebuilds the PDFs that embed it.
$(PDF_DIR)/%.pdf: $(DOCS_DIR)/%.md $(SVG_FILTER) $(DROP_SLIDES_FILTER) $(DOC_HEADER) $(PNGS) | $(PDF_DIR)
	pandoc $< -o $@ $(PANDOC_FLAGS)

$(PDF_DIR) $(PNG_DIR) $(HTML_DIR):
	mkdir -p $@

check-deps:
	@for cmd in pandoc xelatex mmdc rsvg-convert; do \
	  command -v $$cmd >/dev/null 2>&1 && echo "✓ $$cmd" || echo "✗ $$cmd MISSING"; \
	done

clean: ## Remove generated data, build output, and make stamp files
	$(RM) -r $(STAMP_DIR)
	$(RM) -r $(BUILD_DIR)

.PHONY: notebook flight_data docs report deck deck-pdf vendor-reveal diagrams check-deps clean

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
# Scaffold an experiment: a directory pinning a snapshot, plus starter code
# that runs end to end as written. Defaults to the most recently frozen
# snapshot; name another with SNAPSHOT=<id>.
#
# CODE= names the file holding the experiment's code. A name ending in .py
# gets a starter script, anything else a starter notebook.
#
#   make experiment SLUG=astar-heuristics
#   make experiment SLUG=astar-heuristics SNAPSHOT=2026-09-11-1528c4
#   make experiment SLUG=astar-heuristics CODE=run.py
#
# FORCE=1 regenerates experiment.toml for an experiment that already exists.
# It never touches code files: those are the experimenter's work.
#
experiment: ## Scaffold an experiment (SLUG=required, SNAPSHOT/CODE/FORCE=optional)
	@test -n "$(SLUG)" || { echo "usage: make experiment SLUG=<name> [SNAPSHOT=<id>] [CODE=<file>] [FORCE=1]" >&2; exit 1; }
	uv run python $(SRC_NEW_EXPERIMENT) $(SLUG) \
		--root $(EXPERIMENT_DIR) \
		--snapshot-root $(SNAPSHOT_DIR) \
		$(if $(SNAPSHOT),--snapshot $(SNAPSHOT),) \
		$(if $(CODE),--notebook $(CODE),) \
		$(if $(FORCE),--force,) \
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


PROCESSED_DATA_DIR=data/processed
FLIGHT_DATA_DB=flight_data.db

SRC_DIR=src
SRC_DATA_DIR=$(SRC_DIR)/data
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

# Start a jupyter lab session from the install virtual
# environment setup by `uv`
notebook:
	uv run jupyter lab

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

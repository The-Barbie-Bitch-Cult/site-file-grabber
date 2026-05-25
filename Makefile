.PHONY: install-local test help

PYTHON ?= python3
BIN_DIR ?= $(HOME)/.local/bin
VENV ?= $(PWD)/.venv

help:
	@echo "Targets:"
	@echo "  make install-local  Install site-file-grabber to ~/.local/bin"
	@echo "  make test           Run unit tests"

install-local:
	$(PYTHON) -m venv "$(VENV)"
	"$(VENV)/bin/python" -m pip install --upgrade pip
	"$(VENV)/bin/python" -m pip install -e .
	@mkdir -p "$(BIN_DIR)"
	@printf '%s\n' '#!/usr/bin/env sh' 'exec "$(VENV)/bin/python" -m site_file_grabber.cli "$$@"' > "$(BIN_DIR)/site-file-grabber"
	@chmod +x "$(BIN_DIR)/site-file-grabber"
	@echo "Installed $(BIN_DIR)/site-file-grabber"

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

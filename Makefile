# Makefile for PXOS development

# Default Python interpreter
PYTHON = python3

# Virtual environment directory
VENV = venv

.PHONY: all install run test clean help

all: install

# Create virtual environment and install dependencies
install: $(VENV)/bin/activate
$(VENV)/bin/activate: requirements.txt
	test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	. $(VENV)/bin/activate; pip install -r requirements.txt
	@echo "Installation complete. Run 'source $(VENV)/bin/activate' to use the venv."

# Run the main PXOS application
run:
	@$(PYTHON) main.py

# Run tests (placeholder)
test:
	@echo "Running tests..."
	@# Replace with your actual test command, e.g., pytest
	@echo "No tests configured yet."

# Clean up build artifacts and pycache
clean:
	@find . -type f -name '*.pyc' -delete
	@find . -type d -name '__pycache__' -delete
	@echo "Cleaned up Python cache files."

# Display help information
help:
	@echo "PXOS Makefile"
	@echo "------------------"
	@echo "Commands:"
	@echo "  make install  - Creates a virtual environment and installs dependencies."
	@echo "  make run      - Runs the main PXOS application."
	@echo "  make test     - Runs the test suite (placeholder)."
	@echo "  make clean    - Removes Python cache files."

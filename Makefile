.PHONY: install run dry-run test preview preview-all serve

install:
	pip install -r requirements.txt

run:
	python3 -m src.main

dry-run:
	python3 -m src.main --dry-run

test:
	python3 -m pytest tests/ -v

# Generate a single scenario preview (default: mixed).
# Override with: make preview SCENARIO=high-noon-game
preview:
	python3 scripts/preview.py --scenario $(or $(SCENARIO),mixed)

# Generate all scenarios to docs/preview-<name>.html
preview-all:
	python3 scripts/preview.py --all

# List available scenarios
scenarios:
	python3 scripts/preview.py --list

# Serve docs/ on http://localhost:8080 for local browser testing
serve:
	python3 -m http.server 8080 --directory docs/

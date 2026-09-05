.PHONY: install run dry-run test

install:
	pip install -r requirements.txt

run:
	python -m src.main

dry-run:
	python -m src.main --dry-run

test:
	pytest tests/ -v

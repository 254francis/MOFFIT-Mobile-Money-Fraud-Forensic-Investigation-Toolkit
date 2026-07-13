.PHONY: install test lint run

install:
	pip install -e .

test:
	pytest

lint:
	flake8 .
	black --check .

run:
	moffit --help

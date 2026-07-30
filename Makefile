.PHONY: install test lint clean

install:
	python -m pip install --upgrade pip
	pip install -e . pytest pytest-cov ruff mypy

test:
	python -m pytest tests/ -v --cov=src/git_sensei --cov-fail-under=65

lint:
	ruff check --select E,F,W --ignore E501,E722,F401,F841,W293 src/git_sensei/ tests/
	mypy src/git_sensei/ --ignore-missing-imports

clean:
	rm -rf .pytest_cache
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

.PHONY: install test lint clean

install:
	python -m pip install --upgrade pip
	pip install -e . pytest pytest-cov

test:
	python -m pytest tests/ -v --cov=src/git_sensei --cov-fail-under=65

lint:
	python -m py_compile src/git_sensei/*.py

clean:
	rm -rf .pytest_cache
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

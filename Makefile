.PHONY: setup run eval test clean help

export PATH := $(CURDIR)/.venv/bin:$(PATH)

setup:
	uv sync

run:
	uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

eval:
	uv run python -m eval.evaluate

test:
	pytest -q

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache

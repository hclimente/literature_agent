# Tests

This directory contains unit tests for the papers_please bin scripts.

## Setup

Tests use pytest and are configured in `pyproject.toml`. To install test dependencies:

```bash
uv sync --dev
```

Or if using pip:

```bash
pip install -e ".[dev]"
```

## Running Tests

Run all tests:
```bash
uv run pytest tests/
```

Run specific test file:
```bash
uv run pytest tests/test_utils.py
```

Run with verbose output:
```bash
uv run pytest tests/ -v
```

Run with coverage:
```bash
uv run pytest tests/ --cov=common --cov-report=term-missing
```

## Test Coverage

### `test_utils.py`
Tests for `common/utils.py` - **100% coverage**
- `get_env_variable()` function:
  - Retrieves existing environment variables
  - Handles missing environment variables
  - Raises errors when `raise_error=True`
  - Logs errors appropriately
  - Handles edge cases (empty strings, special characters, multiline values, etc.)

## Test Structure

Tests are organized by module:
- `test_utils.py` - Tests for `common/utils.py`

Each test file contains test classes that group related tests together.

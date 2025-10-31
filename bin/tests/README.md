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

### `test_utils.py` - **100% coverage** ✅
Tests for `common/utils.py` (24 tests):
- `get_env_variable()` function:
  - Retrieves existing environment variables
  - Handles missing environment variables
  - Raises errors when `raise_error=True`
  - Logs errors appropriately
  - Handles edge cases (empty strings, special characters, multiline values, etc.)
- `get_common_variations()` function:
  - Generates case variations (lower, upper, capitalize, title)
  - Adds quote variations (single and double quotes)
  - Adds punctuation variations (periods)
  - Returns mapping for case-insensitive lookups

### `test_validation.py` - **100% coverage** ✅
Tests for `common/validation.py` (41 tests):
- `validate_json_response()` function:
  - Validates JSON lists
  - Handles code block formats (```json, ```, `)
  - Validates nested objects
  - Raises appropriate errors for invalid inputs
- `handle_error()` function:
  - Logs warnings when `allow_errors=True`
  - Raises ValidationError when `allow_errors=False`
- `ValidationError` class:
  - Properly logs error messages
  - Inherits from Exception
- `split_by_qc()` function:
  - Splits articles into pass/fail lists
  - Handles KeyError and ValidationError exceptions
  - Supports custom merge keys
- `validate_llm_response()` function:
  - Validates metadata, screening, and priority responses
  - Handles invalid items gracefully
  - Supports multiple items
- `save_validated_responses()` function:
  - Saves pass and fail lists to JSON files
  - Handles empty lists
  - Creates appropriate output files

### Overall Coverage: 78%
- `common/utils.py`: **100%** ✅
- `common/validation.py`: **100%** ✅
- `common/models.py`: 93%
- `common/llm.py`: 0% (not tested)
- `common/parsers.py`: 0% (not tested)

## Test Structure

Tests are organized by module:
- `test_utils.py` - Tests for `common/utils.py` (24 tests)
- `test_validation.py` - Tests for `common/validation.py` (41 tests)

**Total: 65 tests, all passing** ✅

Each test file contains test classes that group related tests together.

## Refactoring Notes

The circular import between `common/models.py` and `common/validation.py` was resolved by moving the `get_common_variations()` function from `validation.py` to `utils.py`, where it logically belongs as a utility function with no dependencies. This allows both modules to import from `utils.py` without creating a circular dependency.

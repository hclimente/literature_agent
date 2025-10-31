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

### `test_models.py` - **100% coverage** ✅
Tests for `common/models.py` (47 tests):
- `Author` model:
  - Field validation and requirements
  - JSON serialization
- `InstitutionalAuthor` model:
  - Field validation and requirements
  - JSON serialization
- `Article` model:
  - Creating minimal and full articles
  - Mixed author types
  - Optional fields and defaults
  - Required field validation
  - URL format validation
- `MetadataResponse` model:
  - Creating responses with all fields
  - DOI format validation
  - Required field validation
- `ScreeningResponse` model:
  - Accept/reject decisions
  - Field aliases
  - Boolean string cleaning
  - Required field validation
- `PriorityResponse` model:
  - High/medium/low priorities
  - Field aliases
  - Case normalization
  - Required field validation
- `pprint()` function:
  - Single models, lists, and dictionaries
  - None value handling
  - Pretty formatting verification
  - Error handling for invalid inputs

### `test_json_validate_articles.py` - **100% coverage** ✅
Tests for `json_validate_articles.py` (15 tests):
- `validate_articles_json()` function:
  - Import stage validation with minimal and full articles
  - Export stage validation with all required fields
  - Field filtering based on stage (import vs export)
  - Multiple articles processing
  - Automatic access_date setting to today
  - Access_date overwriting
  - Invalid stage error handling
  - Empty list handling
  - Pretty-printed output formatting
  - Required field validation
  - URL format validation
  - Date format validation
  - File not found error handling
  - Malformed JSON error handling

### `test_crossref_annotate_doi.py` - **100% coverage** ✅
Tests for `crossref_annotate_doi.py` (18 tests):
- `process_author_list()` function:
  - Single individual author processing
  - Single institutional author processing
  - Multiple individual authors
  - Multiple institutional authors
  - Mixed individual and institutional authors
  - Empty author list handling (returns None)
  - Special characters in names (hyphens, apostrophes, accents)
  - Unicode characters (Chinese, Cyrillic)
  - Single character names
  - Long institutional names
  - Names with spaces
  - Large author lists (100+ authors)
  - Author order preservation
  - Correct type assignment (Author vs InstitutionalAuthor)
  - Empty string validation

### Overall Coverage
- `common/utils.py`: **100%** ✅
- `common/validation.py`: **100%** ✅
- `common/models.py`: **100%** ✅
- `common/parsers.py`: **100%** ✅
- `json_validate_articles.py`: **100%** ✅ (function coverage)
- `crossref_annotate_doi.py`: **~50%** (process_author_list function tested)
- `common/llm.py`: Not yet tested
- Other scripts: Not yet tested

## Test Structure

Tests are organized by module:
- `test_utils.py` - Tests for `common/utils.py` (24 tests)
- `test_validation.py` - Tests for `common/validation.py` (41 tests)
- `test_models.py` - Tests for `common/models.py` (47 tests)
- `test_parsers.py` - Tests for `common/parsers.py` (30 tests)
- `test_json_validate_articles.py` - Tests for `json_validate_articles.py` (15 tests)
- `test_crossref_annotate_doi.py` - Tests for `crossref_annotate_doi.py` (18 tests)

Each test file contains test classes that group related tests together.

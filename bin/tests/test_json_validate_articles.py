#!/usr/bin/env python
"""Tests for json_validate_articles.py"""

import pytest
from datetime import date
import json
import tempfile
import pathlib
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from json_validate_articles import validate_articles_json


class TestValidateArticlesJson:
    """Test suite for validate_articles_json function"""

    @pytest.fixture
    def minimal_article_data(self):
        """Fixture for minimal article data"""
        return {
            "url": "https://example.com/article1",
            "journal_name": "Nature",
            "date": "2024-01-15",
            "raw_contents": "Article content",
        }

    @pytest.fixture
    def full_article_data(self):
        """Fixture for full article data with all fields"""
        return {
            "url": "https://example.com/article1",
            "journal_name": "Nature",
            "date": "2024-01-15",
            "raw_contents": "Article content",
            "title": "Test Article",
            "doi": "10.1234/test",
            "summary": "Article summary",
            "authors": [{"first_name": "John", "last_name": "Doe"}],
            "journal_short_name": "Nat.",
            "volume": 123,
            "issue": 4,
            "language": "en",
            "screening_decision": True,
            "screening_reasoning": "Relevant",
            "priority_decision": "high",
            "priority_reasoning": "Important",
            "zotero_key": "ABC123",
        }

    def test_validate_import_stage_minimal_article(self, minimal_article_data):
        """Test validation at import stage with minimal article"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create input JSON file
            input_file = pathlib.Path(tmpdir) / "input.json"
            input_file.write_text(json.dumps([minimal_article_data]))

            # Create output file path
            output_file = pathlib.Path(tmpdir) / "output.json"

            # Run validation
            validate_articles_json(
                str(input_file),
                "import",
                str(output_file),
            )

            # Read and parse output
            output_content = output_file.read_text()
            result = json.loads(output_content)

            # Assertions
            assert len(result) == 1
            assert result[0]["url"] == "https://example.com/article1"
            assert result[0]["journal_name"] == "Nature"
            assert result[0]["date"] == "2024-01-15"
            assert result[0]["raw_contents"] == "Article content"
            assert result[0]["access_date"] == date.today().isoformat()

            # Import stage should only keep core fields
            assert "title" not in result[0]
            assert "doi" not in result[0]
            assert "summary" not in result[0]

    def test_validate_import_stage_with_extra_fields(self, full_article_data):
        """Test that import stage strips extra fields"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create input JSON file with all fields
            input_file = pathlib.Path(tmpdir) / "input.json"
            input_file.write_text(json.dumps([full_article_data]))

            # Create output file path
            output_file = pathlib.Path(tmpdir) / "output.json"

            # Run validation
            validate_articles_json(
                str(input_file),
                "import",
                str(output_file),
            )

            # Read and parse output
            output_content = output_file.read_text()
            result = json.loads(output_content)

            # Assertions - only core fields should remain
            assert len(result) == 1
            assert "url" in result[0]
            assert "journal_name" in result[0]
            assert "date" in result[0]
            assert "access_date" in result[0]
            assert "raw_contents" in result[0]

            # All other fields should be removed
            assert "title" not in result[0]
            assert "doi" not in result[0]
            assert "summary" not in result[0]
            assert "authors" not in result[0]
            assert "journal_short_name" not in result[0]
            assert "volume" not in result[0]
            assert "issue" not in result[0]
            assert "language" not in result[0]
            assert "screening_decision" not in result[0]
            assert "screening_reasoning" not in result[0]
            assert "priority_decision" not in result[0]
            assert "priority_reasoning" not in result[0]
            assert "zotero_key" not in result[0]

    def test_validate_export_stage_full_article(self, full_article_data):
        """Test validation at export stage with full article"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create input JSON file
            input_file = pathlib.Path(tmpdir) / "input.json"
            input_file.write_text(json.dumps([full_article_data]))

            # Create output file path
            output_file = pathlib.Path(tmpdir) / "output.json"

            # Run validation
            validate_articles_json(
                str(input_file),
                "export",
                str(output_file),
            )

            # Read and parse output
            output_content = output_file.read_text()
            result = json.loads(output_content)

            # Assertions - export stage should keep more fields
            assert len(result) == 1
            assert result[0]["url"] == "https://example.com/article1"
            assert result[0]["journal_name"] == "Nature"
            assert result[0]["date"] == "2024-01-15"
            assert result[0]["raw_contents"] == "Article content"
            assert result[0]["access_date"] == date.today().isoformat()
            assert result[0]["title"] == "Test Article"
            assert result[0]["doi"] == "10.1234/test"
            assert result[0]["summary"] == "Article summary"
            assert result[0]["screening_decision"] is True
            assert result[0]["screening_reasoning"] == "Relevant"
            assert result[0]["priority_decision"] == "high"
            assert result[0]["priority_reasoning"] == "Important"

            # Fields not required for export should be removed
            assert "authors" not in result[0]
            assert "journal_short_name" not in result[0]
            assert "volume" not in result[0]
            assert "issue" not in result[0]
            assert "language" not in result[0]
            assert "zotero_key" not in result[0]

    def test_validate_export_stage_strips_optional_fields(self, full_article_data):
        """Test that export stage strips fields not in required list"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create input JSON file
            input_file = pathlib.Path(tmpdir) / "input.json"
            input_file.write_text(json.dumps([full_article_data]))

            # Create output file path
            output_file = pathlib.Path(tmpdir) / "output.json"

            # Run validation
            validate_articles_json(
                str(input_file),
                "export",
                str(output_file),
            )

            # Read and parse output
            output_content = output_file.read_text()
            result = json.loads(output_content)

            # Verify optional fields are not present
            assert "authors" not in result[0]
            assert "volume" not in result[0]
            assert "issue" not in result[0]
            assert "zotero_key" not in result[0]

    def test_validate_multiple_articles(self, minimal_article_data):
        """Test validation with multiple articles"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create second article
            article2 = minimal_article_data.copy()
            article2["url"] = "https://example.com/article2"
            article2["journal_name"] = "Science"

            # Create input JSON file with multiple articles
            input_file = pathlib.Path(tmpdir) / "input.json"
            input_file.write_text(json.dumps([minimal_article_data, article2]))

            # Create output file path
            output_file = pathlib.Path(tmpdir) / "output.json"

            # Run validation
            validate_articles_json(
                str(input_file),
                "import",
                str(output_file),
            )

            # Read and parse output
            output_content = output_file.read_text()
            result = json.loads(output_content)

            # Assertions
            assert len(result) == 2
            assert result[0]["url"] == "https://example.com/article1"
            assert result[0]["journal_name"] == "Nature"
            assert result[1]["url"] == "https://example.com/article2"
            assert result[1]["journal_name"] == "Science"

    def test_validate_sets_access_date_to_today(self, minimal_article_data):
        """Test that access_date is set to today's date"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create input JSON file without access_date
            input_file = pathlib.Path(tmpdir) / "input.json"
            input_file.write_text(json.dumps([minimal_article_data]))

            # Create output file path
            output_file = pathlib.Path(tmpdir) / "output.json"

            # Run validation
            validate_articles_json(
                str(input_file),
                "import",
                str(output_file),
            )

            # Read and parse output
            output_content = output_file.read_text()
            result = json.loads(output_content)

            # Verify access_date is today
            assert result[0]["access_date"] == date.today().isoformat()

    def test_validate_overwrites_access_date(self, minimal_article_data):
        """Test that existing access_date is overwritten with today's date"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Add an old access_date
            article_with_date = minimal_article_data.copy()
            article_with_date["access_date"] = "2020-01-01"

            # Create input JSON file
            input_file = pathlib.Path(tmpdir) / "input.json"
            input_file.write_text(json.dumps([article_with_date]))

            # Create output file path
            output_file = pathlib.Path(tmpdir) / "output.json"

            # Run validation
            validate_articles_json(
                str(input_file),
                "import",
                str(output_file),
            )

            # Read and parse output
            output_content = output_file.read_text()
            result = json.loads(output_content)

            # Verify access_date is updated to today, not the old date
            assert result[0]["access_date"] == date.today().isoformat()
            assert result[0]["access_date"] != "2020-01-01"

    def test_validate_invalid_stage_raises_error(self, minimal_article_data):
        """Test that invalid stage raises ValueError"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create input JSON file
            input_file = pathlib.Path(tmpdir) / "input.json"
            input_file.write_text(json.dumps([minimal_article_data]))

            # Create output file path
            output_file = pathlib.Path(tmpdir) / "output.json"

            # Test invalid stage
            with pytest.raises(ValueError) as exc_info:
                validate_articles_json(
                    str(input_file),
                    "invalid_stage",
                    str(output_file),
                )
            assert "Unknown stage: invalid_stage" in str(exc_info.value)

    def test_validate_empty_list(self):
        """Test validation with empty article list"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create input JSON file with empty list
            input_file = pathlib.Path(tmpdir) / "input.json"
            input_file.write_text("[]")

            # Create output file path
            output_file = pathlib.Path(tmpdir) / "output.json"

            # Run validation
            validate_articles_json(
                str(input_file),
                "import",
                str(output_file),
            )

            # Read and parse output
            output_content = output_file.read_text()
            result = json.loads(output_content)

            # Assertions
            assert len(result) == 0
            assert result == []

    def test_validate_output_is_pretty_printed(self, minimal_article_data):
        """Test that output is formatted with pretty printing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create input JSON file
            input_file = pathlib.Path(tmpdir) / "input.json"
            input_file.write_text(json.dumps([minimal_article_data]))

            # Create output file path
            output_file = pathlib.Path(tmpdir) / "output.json"

            # Run validation
            validate_articles_json(
                str(input_file),
                "import",
                str(output_file),
            )

            # Read output
            output_content = output_file.read_text()

            # Verify pretty printing
            assert "\n" in output_content  # Has newlines
            assert "  " in output_content or "\t" in output_content  # Has indentation
            lines = output_content.split("\n")
            assert len(lines) > 2  # Multiple lines

    def test_validate_missing_required_field_raises_error(self):
        """Test that missing required fields raise validation error"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create article missing required field
            invalid_article = {
                "url": "https://example.com/article1",
                # Missing journal_name
                "date": "2024-01-15",
                "raw_contents": "Content",
            }

            # Create input JSON file
            input_file = pathlib.Path(tmpdir) / "input.json"
            input_file.write_text(json.dumps([invalid_article]))

            # Create output file path
            output_file = pathlib.Path(tmpdir) / "output.json"

            # Should raise validation error
            with pytest.raises(Exception):  # Pydantic will raise ValidationError
                validate_articles_json(
                    str(input_file),
                    "import",
                    str(output_file),
                )

    def test_validate_invalid_url_raises_error(self):
        """Test that invalid URL format raises validation error"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create article with invalid URL
            invalid_article = {
                "url": "not-a-valid-url",
                "journal_name": "Nature",
                "date": "2024-01-15",
                "raw_contents": "Content",
            }

            # Create input JSON file
            input_file = pathlib.Path(tmpdir) / "input.json"
            input_file.write_text(json.dumps([invalid_article]))

            # Create output file path
            output_file = pathlib.Path(tmpdir) / "output.json"

            # Should raise validation error
            with pytest.raises(Exception):  # Pydantic will raise ValidationError
                validate_articles_json(
                    str(input_file),
                    "import",
                    str(output_file),
                )

    def test_validate_invalid_date_format_raises_error(self):
        """Test that invalid date format raises validation error"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create article with invalid date
            invalid_article = {
                "url": "https://example.com/article1",
                "journal_name": "Nature",
                "date": "not-a-date",
                "raw_contents": "Content",
            }

            # Create input JSON file
            input_file = pathlib.Path(tmpdir) / "input.json"
            input_file.write_text(json.dumps([invalid_article]))

            # Create output file path
            output_file = pathlib.Path(tmpdir) / "output.json"

            # Should raise validation error
            with pytest.raises(Exception):  # Pydantic will raise ValidationError
                validate_articles_json(
                    str(input_file),
                    "import",
                    str(output_file),
                )

    def test_validate_nonexistent_input_file_raises_error(self):
        """Test that nonexistent input file raises error"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create paths for nonexistent input file
            input_file = pathlib.Path(tmpdir) / "nonexistent.json"
            output_file = pathlib.Path(tmpdir) / "output.json"

            # Should raise FileNotFoundError
            with pytest.raises(FileNotFoundError):
                validate_articles_json(
                    str(input_file),
                    "import",
                    str(output_file),
                )

    def test_validate_malformed_json_raises_error(self, minimal_article_data):
        """Test that malformed JSON raises error"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create input file with malformed JSON
            input_file = pathlib.Path(tmpdir) / "input.json"
            input_file.write_text("{this is not valid json}")

            # Create output file path
            output_file = pathlib.Path(tmpdir) / "output.json"

            # Should raise JSONDecodeError
            with pytest.raises(json.JSONDecodeError):
                validate_articles_json(
                    str(input_file),
                    "import",
                    str(output_file),
                )

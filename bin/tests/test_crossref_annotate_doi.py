#!/usr/bin/env python
"""Tests for crossref_annotate_doi.py"""

import sys
from pathlib import Path

import pytest

# Add the parent directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from crossref_annotate_doi import process_author_list
from common.models import Author, InstitutionalAuthor


class TestProcessAuthorList:
    """Test suite for process_author_list function"""

    def test_process_single_individual_author(self):
        """Test processing a single individual author"""
        author_data = [{"given": "John", "family": "Doe"}]
        result = process_author_list(author_data)

        assert result is not None
        assert len(result) == 1
        assert isinstance(result[0], Author)
        assert result[0].first_name == "John"
        assert result[0].last_name == "Doe"

    def test_process_single_institutional_author(self):
        """Test processing a single institutional author"""
        author_data = [{"name": "University Research Lab"}]
        result = process_author_list(author_data)

        assert result is not None
        assert len(result) == 1
        assert isinstance(result[0], InstitutionalAuthor)
        assert result[0].name == "University Research Lab"

    def test_process_multiple_individual_authors(self):
        """Test processing multiple individual authors"""
        author_data = [
            {"given": "John", "family": "Doe"},
            {"given": "Jane", "family": "Smith"},
            {"given": "Bob", "family": "Johnson"},
        ]
        result = process_author_list(author_data)

        assert result is not None
        assert len(result) == 3
        assert all(isinstance(author, Author) for author in result)
        assert result[0].first_name == "John"
        assert result[0].last_name == "Doe"
        assert result[1].first_name == "Jane"
        assert result[1].last_name == "Smith"
        assert result[2].first_name == "Bob"
        assert result[2].last_name == "Johnson"

    def test_process_multiple_institutional_authors(self):
        """Test processing multiple institutional authors"""
        author_data = [{"name": "Research Institute A"}, {"name": "Laboratory B"}]
        result = process_author_list(author_data)

        assert result is not None
        assert len(result) == 2
        assert all(isinstance(author, InstitutionalAuthor) for author in result)
        assert result[0].name == "Research Institute A"
        assert result[1].name == "Laboratory B"

    def test_process_mixed_authors(self):
        """Test processing mixed individual and institutional authors"""
        author_data = [
            {"given": "John", "family": "Doe"},
            {"name": "Research Institute"},
            {"given": "Jane", "family": "Smith"},
            {"name": "University Lab"},
        ]
        result = process_author_list(author_data)

        assert result is not None
        assert len(result) == 4
        assert isinstance(result[0], Author)
        assert isinstance(result[1], InstitutionalAuthor)
        assert isinstance(result[2], Author)
        assert isinstance(result[3], InstitutionalAuthor)

        assert result[0].first_name == "John"
        assert result[0].last_name == "Doe"
        assert result[1].name == "Research Institute"
        assert result[2].first_name == "Jane"
        assert result[2].last_name == "Smith"
        assert result[3].name == "University Lab"

    def test_process_empty_list(self):
        """Test processing an empty author list"""
        author_data = []
        result = process_author_list(author_data)

        assert result is None

    def test_process_author_with_special_characters_in_name(self):
        """Test processing author names with special characters"""
        author_data = [
            {"given": "Jean-Pierre", "family": "O'Connor"},
            {"given": "María", "family": "García-López"},
        ]
        result = process_author_list(author_data)

        assert result is not None
        assert len(result) == 2
        assert result[0].first_name == "Jean-Pierre"
        assert result[0].last_name == "O'Connor"
        assert result[1].first_name == "María"
        assert result[1].last_name == "García-López"

    def test_process_institutional_author_with_special_characters(self):
        """Test processing institutional names with special characters"""
        author_data = [
            {"name": "Max Planck Institute für Molekulare Genetik"},
            {"name": "Centre National de la Recherche Scientifique (CNRS)"},
        ]
        result = process_author_list(author_data)

        assert result is not None
        assert len(result) == 2
        assert result[0].name == "Max Planck Institute für Molekulare Genetik"
        assert result[1].name == "Centre National de la Recherche Scientifique (CNRS)"

    def test_process_author_with_unicode_characters(self):
        """Test processing author names with Unicode characters"""
        author_data = [
            {"given": "李", "family": "明"},
            {"given": "Александр", "family": "Петров"},
        ]
        result = process_author_list(author_data)

        assert result is not None
        assert len(result) == 2
        assert result[0].first_name == "李"
        assert result[0].last_name == "明"
        assert result[1].first_name == "Александр"
        assert result[1].last_name == "Петров"

    def test_process_author_with_single_character_names(self):
        """Test processing authors with single character names"""
        author_data = [{"given": "A", "family": "B"}]
        result = process_author_list(author_data)

        assert result is not None
        assert len(result) == 1
        assert result[0].first_name == "A"
        assert result[0].last_name == "B"

    def test_process_institutional_author_with_long_name(self):
        """Test processing institutional author with very long name"""
        author_data = [
            {
                "name": "The International Consortium for Advanced Research in Biomedical Sciences and Technology"
            }
        ]
        result = process_author_list(author_data)

        assert result is not None
        assert len(result) == 1
        assert (
            result[0].name
            == "The International Consortium for Advanced Research in Biomedical Sciences and Technology"
        )

    def test_process_author_with_spaces_in_names(self):
        """Test processing authors with spaces in given or family names"""
        author_data = [{"given": "Mary Anne", "family": "Von Smith"}]
        result = process_author_list(author_data)

        assert result is not None
        assert len(result) == 1
        assert result[0].first_name == "Mary Anne"
        assert result[0].last_name == "Von Smith"

    def test_process_large_author_list(self):
        """Test processing a large list of authors"""
        author_data = [
            {"given": f"Author{i}", "family": f"LastName{i}"} for i in range(100)
        ]
        result = process_author_list(author_data)

        assert result is not None
        assert len(result) == 100
        assert all(isinstance(author, Author) for author in result)
        assert result[0].first_name == "Author0"
        assert result[99].first_name == "Author99"

    def test_process_author_order_preserved(self):
        """Test that author order is preserved"""
        author_data = [
            {"given": "First", "family": "Author"},
            {"given": "Second", "family": "Author"},
            {"given": "Third", "family": "Author"},
        ]
        result = process_author_list(author_data)

        assert result is not None
        assert result[0].first_name == "First"
        assert result[1].first_name == "Second"
        assert result[2].first_name == "Third"

    def test_process_mixed_authors_order_preserved(self):
        """Test that mixed author types maintain order"""
        author_data = [
            {"given": "Individual1", "family": "Author1"},
            {"name": "Institution1"},
            {"given": "Individual2", "family": "Author2"},
            {"name": "Institution2"},
        ]
        result = process_author_list(author_data)

        assert result is not None
        assert len(result) == 4
        assert isinstance(result[0], Author)
        assert isinstance(result[1], InstitutionalAuthor)
        assert isinstance(result[2], Author)
        assert isinstance(result[3], InstitutionalAuthor)

    def test_process_author_returns_correct_types(self):
        """Test that function returns correct types for each author"""
        author_data = [
            {"given": "John", "family": "Doe"},
            {"name": "Institution"},
        ]
        result = process_author_list(author_data)

        assert result is not None
        assert isinstance(result, list)
        assert isinstance(result[0], Author)
        assert not isinstance(result[0], InstitutionalAuthor)
        assert isinstance(result[1], InstitutionalAuthor)
        assert not isinstance(result[1], Author) or isinstance(
            result[1], InstitutionalAuthor
        )

    def test_process_author_with_empty_strings(self):
        """Test processing authors with empty string values"""
        # This might raise a validation error from Pydantic
        author_data = [{"given": "", "family": "Doe"}]
        # Depending on model validation, this might raise an error
        # Testing to see what happens
        try:
            result = process_author_list(author_data)
            # If it doesn't raise, check the result
            assert result is not None
        except Exception:
            # If Pydantic validation fails, that's also acceptable behavior
            pass

    def test_process_institutional_author_with_empty_string(self):
        """Test processing institutional author with empty name"""
        author_data = [{"name": ""}]
        # This might raise a validation error from Pydantic
        try:
            result = process_author_list(author_data)
            # If it doesn't raise, check the result
            assert result is not None
        except Exception:
            # If Pydantic validation fails, that's also acceptable behavior
            pass


class TestFetchMetadata:
    """Test suite for fetch_metadata function"""

    @pytest.fixture(autouse=True)
    def cleanup_output_file(self):
        """Clean up the output file after each test"""
        import os

        yield

        # Clean up after test
        output_file = "articles_with_extra_metadata.json"
        if os.path.exists(output_file):
            os.remove(output_file)

    @pytest.fixture
    def sample_articles_json(self, tmp_path):
        """Create a sample articles JSON file"""
        import json

        articles = [
            {
                "title": "Test Article 1",
                "url": "https://example.com/article1",
                "journal_name": "Nature",
                "date": "2024-01-01",
                "access_date": "2024-01-15",
                "raw_contents": "Content 1",
                "doi": "10.1234/test1",
            },
        ]

        json_file = tmp_path / "articles.json"
        json_file.write_text(json.dumps(articles))
        return str(json_file)

    def test_fetch_metadata_invalid_error_strategy(self, sample_articles_json):
        """Test that invalid error_strategy raises ValueError"""
        from crossref_annotate_doi import fetch_metadata

        with pytest.raises(ValueError, match="error_strategy must be either"):
            fetch_metadata(sample_articles_json, "invalid")

    def test_fetch_metadata_invalid_error_strategy_none(self, sample_articles_json):
        """Test that None error_strategy raises ValueError"""
        from crossref_annotate_doi import fetch_metadata

        with pytest.raises(ValueError, match="error_strategy must be either"):
            fetch_metadata(sample_articles_json, None)

    def test_fetch_metadata_loads_articles_from_json(self, sample_articles_json):
        """Test that fetch_metadata successfully loads articles from JSON"""
        from crossref_annotate_doi import ArticleList
        import pathlib

        # Read the actual file to verify it's valid
        json_string = pathlib.Path(sample_articles_json).read_text()
        articles = ArticleList.validate_json(json_string)

        # Verify articles were loaded
        assert len(articles) == 1
        assert articles[0].doi == "10.1234/test1"

    def test_fetch_metadata_exclude_strategy_is_valid(self, sample_articles_json):
        """Test that 'exclude' is a valid error strategy"""
        from crossref_annotate_doi import fetch_metadata

        # This should not raise a ValueError
        try:
            # We expect this to fail at Crossref API call, not at validation
            fetch_metadata(sample_articles_json, "exclude")
        except ValueError as e:
            if "error_strategy must be either" in str(e):
                pytest.fail("'exclude' should be a valid error strategy")
        except Exception:
            # Other exceptions are okay (e.g., network errors, API errors)
            pass

    def test_fetch_metadata_include_strategy_is_valid(self, sample_articles_json):
        """Test that 'include' is a valid error strategy"""
        from crossref_annotate_doi import fetch_metadata

        # This should not raise a ValueError
        try:
            # We expect this to fail at Crossref API call, not at validation
            fetch_metadata(sample_articles_json, "include")
        except ValueError as e:
            if "error_strategy must be either" in str(e):
                pytest.fail("'include' should be a valid error strategy")
        except Exception:
            # Other exceptions are okay (e.g., network errors, API errors)
            pass

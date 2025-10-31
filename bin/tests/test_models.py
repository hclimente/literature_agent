#!/usr/bin/env python
"""Tests for common/models.py"""

import pytest
from datetime import date
from pydantic import ValidationError
import sys
from pathlib import Path
import json

# Add the parent directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.models import (
    Author,
    InstitutionalAuthor,
    Article,
    MetadataResponse,
    ScreeningResponse,
    PriorityResponse,
    pprint,
)


class TestAuthor:
    """Test suite for Author model"""

    def test_create_author(self):
        """Test creating a valid Author"""
        author = Author(first_name="John", last_name="Doe")
        assert author.first_name == "John"
        assert author.last_name == "Doe"

    def test_author_requires_first_name(self):
        """Test that Author requires first_name"""
        with pytest.raises(ValidationError) as exc_info:
            Author(last_name="Doe")
        assert "first_name" in str(exc_info.value).lower()
        assert (
            "field required" in str(exc_info.value).lower()
            or "missing" in str(exc_info.value).lower()
        )

    def test_author_requires_last_name(self):
        """Test that Author requires last_name"""
        with pytest.raises(ValidationError) as exc_info:
            Author(first_name="John")
        assert "last_name" in str(exc_info.value).lower()
        assert (
            "field required" in str(exc_info.value).lower()
            or "missing" in str(exc_info.value).lower()
        )

    def test_author_json_serialization(self):
        """Test Author JSON serialization"""
        author = Author(first_name="Jane", last_name="Smith")
        json_str = author.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["first_name"] == "Jane"
        assert parsed["last_name"] == "Smith"


class TestInstitutionalAuthor:
    """Test suite for InstitutionalAuthor model"""

    def test_create_institutional_author(self):
        """Test creating a valid InstitutionalAuthor"""
        author = InstitutionalAuthor(name="University Research Lab")
        assert author.name == "University Research Lab"

    def test_institutional_author_requires_name(self):
        """Test that InstitutionalAuthor requires name"""
        with pytest.raises(ValidationError) as exc_info:
            InstitutionalAuthor()
        assert "name" in str(exc_info.value).lower()
        assert (
            "field required" in str(exc_info.value).lower()
            or "missing" in str(exc_info.value).lower()
        )

    def test_institutional_author_json_serialization(self):
        """Test InstitutionalAuthor JSON serialization"""
        author = InstitutionalAuthor(name="Research Institute")
        json_str = author.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["name"] == "Research Institute"


class TestArticle:
    """Test suite for Article model"""

    def test_create_minimal_article(self):
        """Test creating an Article with minimal required fields"""
        article = Article(
            url="https://example.com/article",
            journal_name="Nature",
            date=date(2024, 1, 15),
            access_date=date(2024, 1, 20),
            raw_contents="Article text content",
        )
        assert str(article.url) == "https://example.com/article"
        assert article.journal_name == "Nature"
        assert article.date == date(2024, 1, 15)
        assert article.access_date == date(2024, 1, 20)
        assert article.raw_contents == "Article text content"

    def test_create_full_article(self):
        """Test creating an Article with all fields"""
        authors = [
            Author(first_name="John", last_name="Doe"),
            Author(first_name="Jane", last_name="Smith"),
        ]
        article = Article(
            title="Test Article",
            authors=authors,
            summary="Article summary",
            doi="10.1234/test",
            url="https://example.com/article",
            journal_name="Nature",
            journal_short_name="Nat.",
            volume=123,
            issue=4,
            date=date(2024, 1, 15),
            language="en",
            screening_decision=True,
            screening_reasoning="Relevant to research",
            priority_decision="high",
            priority_reasoning="Important findings",
            access_date=date(2024, 1, 20),
            raw_contents="Full article content",
            zotero_key="ABC123",
        )
        assert article.title == "Test Article"
        assert len(article.authors) == 2
        assert article.summary == "Article summary"
        assert article.doi == "10.1234/test"
        assert article.volume == 123
        assert article.issue == 4
        assert article.language == "en"
        assert article.screening_decision is True
        assert article.priority_decision == "high"
        assert article.zotero_key == "ABC123"

    def test_article_with_mixed_authors(self):
        """Test Article with both individual and institutional authors"""
        authors = [
            Author(first_name="John", last_name="Doe"),
            InstitutionalAuthor(name="Research Institute"),
        ]
        article = Article(
            url="https://example.com/article",
            authors=authors,
            journal_name="Science",
            date=date(2024, 1, 15),
            access_date=date(2024, 1, 20),
            raw_contents="Content",
        )
        assert len(article.authors) == 2
        assert isinstance(article.authors[0], Author)
        assert isinstance(article.authors[1], InstitutionalAuthor)

    def test_article_optional_fields_default_to_none(self):
        """Test that optional fields default to None"""
        article = Article(
            url="https://example.com/article",
            journal_name="Journal",
            date=date(2024, 1, 15),
            access_date=date(2024, 1, 20),
            raw_contents="Content",
        )
        assert article.title is None
        assert article.authors is None
        assert article.summary is None
        assert article.doi is None
        assert article.journal_short_name is None
        assert article.volume is None
        assert article.issue is None
        assert article.language is None
        assert article.screening_decision is None
        assert article.screening_reasoning is None
        assert article.priority_decision is None
        assert article.priority_reasoning is None
        assert article.zotero_key is None

    def test_article_requires_url(self):
        """Test that Article requires url"""
        with pytest.raises(ValidationError) as exc_info:
            Article(
                journal_name="Journal",
                date=date(2024, 1, 15),
                access_date=date(2024, 1, 20),
                raw_contents="Content",
            )
        assert "url" in str(exc_info.value).lower()

    def test_article_requires_journal_name(self):
        """Test that Article requires journal_name"""
        with pytest.raises(ValidationError) as exc_info:
            Article(
                url="https://example.com/article",
                date=date(2024, 1, 15),
                access_date=date(2024, 1, 20),
                raw_contents="Content",
            )
        assert "journal_name" in str(exc_info.value).lower()

    def test_article_requires_date(self):
        """Test that Article requires date"""
        with pytest.raises(ValidationError) as exc_info:
            Article(
                url="https://example.com/article",
                journal_name="Journal",
                access_date=date(2024, 1, 20),
                raw_contents="Content",
            )
        assert "date" in str(exc_info.value).lower()

    def test_article_requires_access_date(self):
        """Test that Article requires access_date"""
        with pytest.raises(ValidationError) as exc_info:
            Article(
                url="https://example.com/article",
                journal_name="Journal",
                date=date(2024, 1, 15),
                raw_contents="Content",
            )
        assert "access_date" in str(exc_info.value).lower()

    def test_article_requires_raw_contents(self):
        """Test that Article requires raw_contents"""
        with pytest.raises(ValidationError) as exc_info:
            Article(
                url="https://example.com/article",
                journal_name="Journal",
                date=date(2024, 1, 15),
                access_date=date(2024, 1, 20),
            )
        assert "raw_contents" in str(exc_info.value).lower()

    def test_article_validates_url_format(self):
        """Test that Article validates URL format"""
        with pytest.raises(ValidationError) as exc_info:
            Article(
                url="not-a-valid-url",
                journal_name="Journal",
                date=date(2024, 1, 15),
                access_date=date(2024, 1, 20),
                raw_contents="Content",
            )
        error_msg = str(exc_info.value).lower()
        assert "url" in error_msg


class TestMetadataResponse:
    """Test suite for MetadataResponse model"""

    def test_create_metadata_response(self):
        """Test creating a valid MetadataResponse"""
        response = MetadataResponse(
            title="Test Article",
            summary="Article summary",
            url="https://example.com/article",
            doi="10.1234/test",
        )
        assert response.title == "Test Article"
        assert response.summary == "Article summary"
        assert str(response.url) == "https://example.com/article"
        assert response.doi == "10.1234/test"

    def test_metadata_response_validates_doi_format(self):
        """Test that MetadataResponse validates DOI format"""
        with pytest.raises(ValidationError) as exc_info:
            MetadataResponse(
                title="Test",
                summary="Summary",
                url="https://example.com/article",
                doi="invalid-doi",
            )
        error_msg = str(exc_info.value).lower()
        assert "doi" in error_msg

    def test_metadata_response_requires_all_fields(self):
        """Test that MetadataResponse requires all fields"""
        with pytest.raises(ValidationError) as exc_info:
            MetadataResponse(
                title="Test",
                summary="Summary",
                url="https://example.com/article",
            )
        assert "doi" in str(exc_info.value).lower()

    def test_metadata_response_valid_doi_formats(self):
        """Test various valid DOI formats"""
        valid_dois = [
            "10.1234/test",
            "10.1000/xyz123",
            "10.12345/journal.2024.01.001",
            "10.1234/test-article-2024",
        ]
        for doi in valid_dois:
            response = MetadataResponse(
                title="Test",
                summary="Summary",
                url="https://example.com/article",
                doi=doi,
            )
            assert response.doi == doi

    def test_metadata_response_invalid_doi_formats(self):
        """Test various invalid DOI formats"""
        invalid_dois = [
            "doi:10.1234/test",  # Has prefix
            "10.123/test",  # Too few digits before slash
            "11.1234/test",  # Must start with 10
            "10.1234",  # Missing slash and suffix
            "10.1234/",  # Missing suffix
        ]
        for doi in invalid_dois:
            with pytest.raises(ValidationError) as exc_info:
                MetadataResponse(
                    title="Test",
                    summary="Summary",
                    url="https://example.com/article",
                    doi=doi,
                )
            assert "doi" in str(exc_info.value).lower()


class TestScreeningResponse:
    """Test suite for ScreeningResponse model"""

    def test_create_screening_response_accept(self):
        """Test creating a ScreeningResponse with accept decision"""
        response = ScreeningResponse(
            doi="10.1234/test", decision=True, reasoning="Relevant article"
        )
        assert response.doi == "10.1234/test"
        assert response.screening_decision is True
        assert response.screening_reasoning == "Relevant article"

    def test_create_screening_response_reject(self):
        """Test creating a ScreeningResponse with reject decision"""
        response = ScreeningResponse(
            doi="10.1234/test", decision=False, reasoning="Not relevant"
        )
        assert response.doi == "10.1234/test"
        assert response.screening_decision is False
        assert response.screening_reasoning == "Not relevant"

    def test_screening_response_field_alias(self):
        """Test that screening_decision uses 'decision' alias"""
        data = {"doi": "10.1234/test", "decision": True, "reasoning": "Relevant"}
        response = ScreeningResponse.model_validate(data)
        assert response.screening_decision is True
        assert response.screening_reasoning == "Relevant"

    def test_screening_response_cleans_boolean_strings(self):
        """Test that screening_decision cleans string boolean values"""
        # Test various string representations of booleans
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
        ]
        for input_val, expected in test_cases:
            response = ScreeningResponse(
                doi="10.1234/test", decision=input_val, reasoning="Test"
            )
            assert response.screening_decision == expected

    def test_screening_response_accepts_boolean(self):
        """Test that screening_decision accepts actual boolean values"""
        response_true = ScreeningResponse(
            doi="10.1234/test", decision=True, reasoning="Test"
        )
        assert response_true.screening_decision is True

        response_false = ScreeningResponse(
            doi="10.1234/test", decision=False, reasoning="Test"
        )
        assert response_false.screening_decision is False

    def test_screening_response_requires_all_fields(self):
        """Test that ScreeningResponse requires all fields"""
        with pytest.raises(ValidationError) as exc_info:
            ScreeningResponse(doi="10.1234/test", decision=True)
        assert "reasoning" in str(exc_info.value).lower()

        with pytest.raises(ValidationError) as exc_info:
            ScreeningResponse(doi="10.1234/test", reasoning="Test")
        assert "decision" in str(exc_info.value).lower()

        with pytest.raises(ValidationError) as exc_info:
            ScreeningResponse(decision=True, reasoning="Test")
        assert "doi" in str(exc_info.value).lower()


class TestPriorityResponse:
    """Test suite for PriorityResponse model"""

    def test_create_priority_response_high(self):
        """Test creating a PriorityResponse with high priority"""
        response = PriorityResponse(
            doi="10.1234/test", decision="high", reasoning="Important findings"
        )
        assert response.doi == "10.1234/test"
        assert response.priority_decision == "high"
        assert response.priority_reasoning == "Important findings"

    def test_create_priority_response_medium(self):
        """Test creating a PriorityResponse with medium priority"""
        response = PriorityResponse(
            doi="10.1234/test", decision="medium", reasoning="Moderately relevant"
        )
        assert response.priority_decision == "medium"

    def test_create_priority_response_low(self):
        """Test creating a PriorityResponse with low priority"""
        response = PriorityResponse(
            doi="10.1234/test", decision="low", reasoning="Less urgent"
        )
        assert response.priority_decision == "low"

    def test_priority_response_field_alias(self):
        """Test that priority_decision uses 'decision' alias"""
        data = {"doi": "10.1234/test", "decision": "high", "reasoning": "Important"}
        response = PriorityResponse.model_validate(data)
        assert response.priority_decision == "high"
        assert response.priority_reasoning == "Important"

    def test_priority_response_cleans_case_variations(self):
        """Test that priority_decision normalizes case variations"""
        test_cases = [
            ("high", "high"),
            ("High", "high"),
            ("HIGH", "high"),
            ("medium", "medium"),
            ("Medium", "medium"),
            ("MEDIUM", "medium"),
            ("low", "low"),
            ("Low", "low"),
            ("LOW", "low"),
        ]
        for input_val, expected in test_cases:
            response = PriorityResponse(
                doi="10.1234/test", decision=input_val, reasoning="Test"
            )
            assert response.priority_decision == expected

    def test_priority_response_requires_all_fields(self):
        """Test that PriorityResponse requires all fields"""
        with pytest.raises(ValidationError) as exc_info:
            PriorityResponse(doi="10.1234/test", decision="high")
        assert "reasoning" in str(exc_info.value).lower()

        with pytest.raises(ValidationError) as exc_info:
            PriorityResponse(doi="10.1234/test", reasoning="Test")
        assert "decision" in str(exc_info.value).lower()

        with pytest.raises(ValidationError) as exc_info:
            PriorityResponse(decision="high", reasoning="Test")
        assert "doi" in str(exc_info.value).lower()


class TestPprint:
    """Test suite for pprint function"""

    def test_pprint_single_author(self):
        """Test pprint with a single Author model"""
        author = Author(first_name="John", last_name="Doe")
        result = pprint(author)
        parsed = json.loads(result)
        assert parsed["first_name"] == "John"
        assert parsed["last_name"] == "Doe"
        assert isinstance(result, str)
        # Verify pretty formatting
        assert "\n" in result
        assert "  " in result or "\t" in result  # Check for indentation

    def test_pprint_list_of_authors(self):
        """Test pprint with a list of models"""
        authors = [
            Author(first_name="John", last_name="Doe"),
            Author(first_name="Jane", last_name="Smith"),
        ]
        result = pprint(authors)
        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed[0]["first_name"] == "John"
        assert parsed[1]["first_name"] == "Jane"
        assert result.startswith("[")
        assert result.endswith("]")
        # Verify pretty formatting
        assert "\n" in result
        assert "  " in result or "\t" in result

    def test_pprint_dict_of_models(self):
        """Test pprint with a dict of models"""
        authors = {
            "author1": Author(first_name="John", last_name="Doe"),
            "author2": Author(first_name="Jane", last_name="Smith"),
        }
        result = pprint(authors)
        parsed = json.loads(result)
        assert "author1" in parsed
        assert "author2" in parsed
        assert parsed["author1"]["first_name"] == "John"
        assert parsed["author2"]["first_name"] == "Jane"
        assert result.startswith("{")
        assert result.endswith("}")
        # Verify pretty formatting
        assert "\n" in result
        assert "  " in result or "\t" in result

    def test_pprint_article_with_none_values(self):
        """Test pprint excludes None values by default"""
        article = Article(
            url="https://example.com/article",
            journal_name="Journal",
            date=date(2024, 1, 15),
            access_date=date(2024, 1, 20),
            raw_contents="Content",
        )
        result = pprint(article)
        parsed = json.loads(result)
        # None fields should not appear in output
        assert "title" not in parsed
        assert "summary" not in parsed
        assert "doi" not in parsed

    def test_pprint_article_include_none_values(self):
        """Test pprint includes None values when exclude_none=False"""
        article = Article(
            url="https://example.com/article",
            journal_name="Journal",
            date=date(2024, 1, 15),
            access_date=date(2024, 1, 20),
            raw_contents="Content",
        )
        result = pprint(article, exclude_none=False)
        parsed = json.loads(result)
        # None fields should appear in output as null
        assert "title" in parsed
        assert parsed["title"] is None

    def test_pprint_metadata_response(self):
        """Test pprint with MetadataResponse"""
        response = MetadataResponse(
            title="Test Article",
            summary="Summary",
            url="https://example.com/article",
            doi="10.1234/test",
        )
        result = pprint(response)
        parsed = json.loads(result)
        assert parsed["title"] == "Test Article"
        assert parsed["doi"] == "10.1234/test"

    def test_pprint_screening_response(self):
        """Test pprint with ScreeningResponse"""
        response = ScreeningResponse(
            doi="10.1234/test", decision=True, reasoning="Relevant"
        )
        result = pprint(response)
        parsed = json.loads(result)
        assert parsed["doi"] == "10.1234/test"
        assert parsed["screening_decision"] is True
        assert parsed["screening_reasoning"] == "Relevant"

    def test_pprint_priority_response(self):
        """Test pprint with PriorityResponse"""
        response = PriorityResponse(
            doi="10.1234/test", decision="high", reasoning="Important"
        )
        result = pprint(response)
        parsed = json.loads(result)
        assert parsed["doi"] == "10.1234/test"
        assert parsed["priority_decision"] == "high"
        assert parsed["priority_reasoning"] == "Important"

    def test_pprint_empty_list(self):
        """Test pprint with empty list"""
        result = pprint([])
        parsed = json.loads(result)
        assert parsed == []
        assert result.startswith("[")
        assert result.endswith("]")

    def test_pprint_empty_dict(self):
        """Test pprint with empty dict"""
        result = pprint({})
        parsed = json.loads(result)
        assert parsed == {}
        assert result.startswith("{")
        assert result.endswith("}")

    def test_pprint_list_has_proper_formatting(self):
        """Test that pprint formats list with proper indentation and commas"""
        authors = [
            Author(first_name="John", last_name="Doe"),
            Author(first_name="Jane", last_name="Smith"),
        ]
        result = pprint(authors)
        parsed = json.loads(result)
        assert len(parsed) == 2
        # Check for proper JSON list structure
        assert result.startswith("[")
        assert result.endswith("]")
        # Verify pretty formatting with newlines and indentation
        lines = result.split("\n")
        assert len(lines) > 2  # Should have multiple lines
        # Check that elements are indented
        assert any(
            line.startswith("  ") or line.startswith("\t") for line in lines[1:-1]
        )

    def test_pprint_dict_has_proper_formatting(self):
        """Test that pprint formats dict with proper structure"""
        authors = {
            "author1": Author(first_name="John", last_name="Doe"),
        }
        result = pprint(authors)
        parsed = json.loads(result)
        assert "author1" in parsed
        assert result.startswith("{")
        assert result.endswith("}")
        # Verify pretty formatting with newlines and indentation
        lines = result.split("\n")
        assert len(lines) > 2  # Should have multiple lines
        assert any(
            line.startswith("  ") or line.startswith("\t") for line in lines[1:-1]
        )

    def test_pprint_raises_error_for_invalid_input(self):
        """Test that pprint raises TypeError for invalid input"""
        with pytest.raises(TypeError, match="Input must be a Pydantic BaseModel"):
            pprint("not a model")

        with pytest.raises(TypeError, match="Input must be a Pydantic BaseModel"):
            pprint(123)

        with pytest.raises(TypeError, match="Input must be a Pydantic BaseModel"):
            pprint(None)

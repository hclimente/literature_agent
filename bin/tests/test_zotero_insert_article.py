#!/usr/bin/env python
"""Tests for zotero_insert_article.py"""

import pytest
from datetime import date
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add the parent directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from zotero_insert_article import (
    add_creators,
    create_zotero_article,
    create_zotero_note,
    validate_response,
    insert_batch,
    insert_article,
)
from common.models import Article, Author, InstitutionalAuthor


class TestAddCreators:
    """Test suite for add_creators function"""

    def test_add_creators_empty_list(self):
        """Test with empty list"""
        result = add_creators([])
        assert result == []

    def test_add_creators_none(self):
        """Test with None"""
        result = add_creators(None)
        assert result == []

    def test_add_creators_single_author(self):
        """Test with a single Author"""
        authors = [Author(first_name="John", last_name="Doe")]
        result = add_creators(authors)

        assert len(result) == 1
        assert result[0]["creatorType"] == "author"
        assert result[0]["firstName"] == "John"
        assert result[0]["lastName"] == "Doe"

    def test_add_creators_multiple_authors(self):
        """Test with multiple Authors"""
        authors = [
            Author(first_name="John", last_name="Doe"),
            Author(first_name="Jane", last_name="Smith"),
        ]
        result = add_creators(authors)

        assert len(result) == 2
        assert result[0]["firstName"] == "John"
        assert result[0]["lastName"] == "Doe"
        assert result[1]["firstName"] == "Jane"
        assert result[1]["lastName"] == "Smith"

    def test_add_creators_institutional_author(self):
        """Test with InstitutionalAuthor"""
        authors = [InstitutionalAuthor(name="MIT Research Group")]
        result = add_creators(authors)

        assert len(result) == 1
        assert result[0]["creatorType"] == "author"
        assert result[0]["name"] == "MIT Research Group"
        assert "firstName" not in result[0]
        assert "lastName" not in result[0]

    def test_add_creators_mixed_authors(self):
        """Test with mix of Author and InstitutionalAuthor"""
        authors = [
            Author(first_name="John", last_name="Doe"),
            InstitutionalAuthor(name="MIT Research Group"),
            Author(first_name="Jane", last_name="Smith"),
        ]
        result = add_creators(authors)

        assert len(result) == 3
        assert result[0]["firstName"] == "John"
        assert result[1]["name"] == "MIT Research Group"
        assert result[2]["firstName"] == "Jane"


class TestCreateZoteroArticle:
    """Test suite for create_zotero_article function"""

    @pytest.fixture
    def mock_zotero(self):
        """Create a mock Zotero client"""
        zot = Mock()
        zot.item_template.return_value = {
            "itemType": "journalArticle",
            "title": "",
            "creators": [],
            "abstractNote": "",
            "publicationTitle": "",
            "volume": "",
            "issue": "",
            "pages": "",
            "date": "",
            "series": "",
            "seriesTitle": "",
            "seriesText": "",
            "journalAbbreviation": "",
            "language": "",
            "DOI": "",
            "ISSN": "",
            "shortTitle": "",
            "url": "",
            "accessDate": "",
            "archive": "",
            "archiveLocation": "",
            "libraryCatalog": "",
            "callNumber": "",
            "rights": "",
            "extra": "",
            "tags": [],
            "collections": [],
            "relations": {},
        }
        return zot

    @pytest.fixture
    def minimal_article(self):
        """Create a minimal article for testing"""
        return Article(
            title="Test Article",
            url="https://example.com/article",
            journal_name="Nature",
            date=date(2025, 10, 15),
            access_date=date(2025, 10, 31),
            raw_contents="Raw content",
        )

    @pytest.fixture
    def full_article(self):
        """Create a full article with all fields"""
        return Article(
            title="Full Test Article",
            authors=[
                Author(first_name="John", last_name="Doe"),
                InstitutionalAuthor(name="MIT"),
            ],
            summary="This is a test summary",
            doi="10.1234/test",
            url="https://example.com/article",
            journal_name="Nature",
            journal_short_name="Nat.",
            volume=123,
            issue=4,
            date=date(2025, 10, 15),
            language="en",
            screening_decision=True,
            screening_reasoning="Relevant",
            priority_decision="high",
            priority_reasoning="Important",
            access_date=date(2025, 10, 31),
            raw_contents="Raw content",
        )

    def test_create_zotero_article_minimal(self, minimal_article, mock_zotero):
        """Test creating a Zotero article with minimal data"""
        collection_id = "TEST123"

        result = create_zotero_article(minimal_article, collection_id, mock_zotero)

        assert result["title"] == "Test Article"
        assert result["url"] == "https://example.com/article"
        assert result["publicationTitle"] == "Nature"
        assert result["date"] == "2025-10-15"
        assert result["accessDate"] == "2025-10-31"
        assert result["collections"] == [collection_id]
        assert result["creators"] == []
        # Note: The code adds a tag even when priority_decision is None
        assert len(result["tags"]) == 1
        assert result["tags"][0]["tag"] == "llm_priority-None"

    def test_create_zotero_article_full(self, full_article, mock_zotero):
        """Test creating a Zotero article with all fields"""
        collection_id = "TEST123"

        result = create_zotero_article(full_article, collection_id, mock_zotero)

        assert result["title"] == "Full Test Article"
        assert result["abstractNote"] == "This is a test summary"
        assert result["DOI"] == "10.1234/test"
        assert result["url"] == "https://example.com/article"
        assert result["publicationTitle"] == "Nature"
        assert result["journalAbbreviation"] == "Nat."
        assert result["volume"] == 123
        assert result["issue"] == 4
        assert result["date"] == "2025-10-15"
        assert result["language"] == "en"
        assert result["accessDate"] == "2025-10-31"
        assert result["collections"] == [collection_id]

        # Check creators
        assert len(result["creators"]) == 2
        assert result["creators"][0]["firstName"] == "John"
        assert result["creators"][1]["name"] == "MIT"

        # Check tags
        assert len(result["tags"]) == 1
        assert result["tags"][0]["tag"] == "llm_priority-high"
        assert result["tags"][0]["type"] == 0

    def test_create_zotero_article_no_priority(self, minimal_article, mock_zotero):
        """Test creating article without priority decision (still adds tag with None)"""
        collection_id = "TEST123"

        result = create_zotero_article(minimal_article, collection_id, mock_zotero)

        # The code adds a tag even when priority_decision is None
        assert len(result["tags"]) == 1
        assert result["tags"][0]["tag"] == "llm_priority-None"

    def test_create_zotero_article_calls_template(self, minimal_article, mock_zotero):
        """Test that item_template is called correctly"""
        collection_id = "TEST123"

        create_zotero_article(minimal_article, collection_id, mock_zotero)

        mock_zotero.item_template.assert_called_once_with("journalArticle")


class TestCreateZoteroNote:
    """Test suite for create_zotero_note function"""

    @pytest.fixture
    def mock_zotero(self):
        """Create a mock Zotero client"""
        zot = Mock()
        zot.item_template.return_value = {
            "itemType": "note",
            "note": "",
            "tags": [],
            "relations": {},
            "parentItem": "",
        }
        return zot

    @pytest.fixture
    def article_with_key(self):
        """Create an article with zotero_key and reasoning"""
        return Article(
            title="Test Article",
            url="https://example.com/article",
            journal_name="Nature",
            date=date(2025, 10, 15),
            access_date=date(2025, 10, 31),
            raw_contents="Raw content",
            zotero_key="ABC123",
            screening_reasoning="This is relevant to my research",
            priority_reasoning="High priority because of novel findings",
        )

    def test_create_zotero_note(self, article_with_key, mock_zotero):
        """Test creating a Zotero note"""
        result = create_zotero_note(article_with_key, mock_zotero)

        assert result["parentItem"] == "ABC123"
        assert "AI Screening reasoning:" in result["note"]
        assert "This is relevant to my research" in result["note"]
        assert "AI Priority reasoning:" in result["note"]
        assert "High priority because of novel findings" in result["note"]

    def test_create_zotero_note_calls_template(self, article_with_key, mock_zotero):
        """Test that item_template is called correctly"""
        create_zotero_note(article_with_key, mock_zotero)

        mock_zotero.item_template.assert_called_once_with("note")


class TestValidateResponse:
    """Test suite for validate_response function"""

    def test_validate_response_success(self):
        """Test validation with successful response"""
        items = [{"title": "Article 1"}, {"title": "Article 2"}]
        response = {
            "successful": {"0": {}, "1": {}},
            "failed": {},
        }

        assert validate_response(items, response) is True

    def test_validate_response_missing_successful_key(self):
        """Test validation fails when 'successful' key is missing"""
        items = [{"title": "Article 1"}]
        response = {"failed": {}}

        with pytest.raises(AssertionError, match="Response missing 'successful' key"):
            validate_response(items, response)

    def test_validate_response_missing_failed_key(self):
        """Test validation fails when 'failed' key is missing"""
        items = [{"title": "Article 1"}]
        response = {"successful": {"0": {}}}

        with pytest.raises(AssertionError, match="Response missing 'failed' key"):
            validate_response(items, response)

    def test_validate_response_wrong_number_successful(self):
        """Test validation fails when number of successful items doesn't match"""
        items = [{"title": "Article 1"}, {"title": "Article 2"}]
        response = {
            "successful": {"0": {}},  # Only 1 successful, expected 2
            "failed": {},
        }

        with pytest.raises(AssertionError, match="Expected 2 successful inserts"):
            validate_response(items, response)

    def test_validate_response_has_failures(self):
        """Test validation fails when there are failed items"""
        items = [{"title": "Article 1"}, {"title": "Article 2"}]
        response = {
            "successful": {"0": {}, "1": {}},
            "failed": {"2": {"message": "Some error"}},
        }

        with pytest.raises(AssertionError, match="Expected 0 failed inserts"):
            validate_response(items, response)

    def test_validate_response_empty_items(self):
        """Test validation with empty items list"""
        items = []
        response = {
            "successful": {},
            "failed": {},
        }

        assert validate_response(items, response) is True


class TestInsertBatch:
    """Test suite for insert_batch function"""

    @pytest.fixture
    def mock_zotero(self):
        """Create a mock Zotero client"""
        zot = Mock()
        return zot

    def test_insert_batch_success(self, mock_zotero):
        """Test successful batch insertion"""
        items = [
            {"title": "Article 1", "DOI": "10.1234/test1"},
            {"title": "Article 2", "DOI": "10.1234/test2"},
        ]

        mock_zotero.create_items.return_value = {
            "successful": {
                "0": {"data": {"DOI": "10.1234/test1", "key": "KEY1"}},
                "1": {"data": {"DOI": "10.1234/test2", "key": "KEY2"}},
            },
            "failed": {},
        }

        result = insert_batch(mock_zotero, items, return_keys=True)

        assert result == {"10.1234/test1": "KEY1", "10.1234/test2": "KEY2"}
        mock_zotero.create_items.assert_called_once_with(items)

    def test_insert_batch_no_return_keys(self, mock_zotero):
        """Test batch insertion without returning keys"""
        items = [{"title": "Article 1", "DOI": "10.1234/test1"}]

        mock_zotero.create_items.return_value = {
            "successful": {"0": {"data": {"DOI": "10.1234/test1", "key": "KEY1"}}},
            "failed": {},
        }

        result = insert_batch(mock_zotero, items, return_keys=False)

        assert result == {}

    def test_insert_batch_validation_failure(self, mock_zotero):
        """Test batch insertion with validation failure"""
        items = [{"title": "Article 1"}]

        mock_zotero.create_items.return_value = {
            "successful": {},
            "failed": {"0": {"message": "Error"}},
        }

        with pytest.raises(AssertionError):
            insert_batch(mock_zotero, items)

    def test_insert_batch_empty_items(self, mock_zotero):
        """Test batch insertion with empty items list"""
        items = []

        mock_zotero.create_items.return_value = {
            "successful": {},
            "failed": {},
        }

        result = insert_batch(mock_zotero, items, return_keys=True)

        assert result == {}


class TestInsertArticle:
    """Test suite for insert_article function"""

    @pytest.fixture
    def mock_zotero_client(self):
        """Create a mock Zotero client"""
        zot = Mock()
        zot.item_template = Mock(
            side_effect=lambda template_type: {
                "journalArticle": {
                    "itemType": "journalArticle",
                    "title": "",
                    "creators": [],
                    "tags": [],
                    "collections": [],
                },
                "note": {
                    "itemType": "note",
                    "note": "",
                    "parentItem": "",
                },
            }[template_type]
        )

        def create_items_side_effect(items):
            # Return response matching the number of items
            return {
                "successful": {
                    str(i): {
                        "data": {"DOI": f"10.1234/test{i + 1}", "key": f"KEY{i + 1}"}
                    }
                    for i in range(len(items))
                },
                "failed": {},
            }

        zot.create_items.side_effect = create_items_side_effect
        return zot

    @pytest.fixture
    def sample_articles_json(self, tmp_path):
        """Create a temporary JSON file with sample articles"""
        articles = [
            {
                "title": "Test Article 1",
                "url": "https://example.com/article1",
                "journal_name": "Nature",
                "date": "2025-10-15",
                "access_date": "2025-10-31",
                "raw_contents": "Content 1",
                "doi": "10.1234/test1",
                "screening_reasoning": "Relevant 1",
                "priority_reasoning": "High 1",
                "priority_decision": "high",
            },
            {
                "title": "Test Article 2",
                "url": "https://example.com/article2",
                "journal_name": "Science",
                "date": "2025-10-20",
                "access_date": "2025-10-31",
                "raw_contents": "Content 2",
                "doi": "10.1234/test2",
                "screening_reasoning": "Relevant 2",
                "priority_reasoning": "Medium 2",
                "priority_decision": "medium",
            },
        ]

        json_file = tmp_path / "articles.json"
        json_file.write_text(json.dumps(articles))
        return str(json_file)

    @patch("zotero_insert_article.zotero.Zotero")
    @patch("zotero_insert_article.get_env_variable")
    def test_insert_article_basic(
        self, mock_get_env, mock_zotero_class, sample_articles_json, mock_zotero_client
    ):
        """Test basic article insertion"""
        mock_get_env.return_value = "fake_api_key"
        mock_zotero_class.return_value = mock_zotero_client

        insert_article(
            articles_json=sample_articles_json,
            zotero_user_id="12345",
            zotero_library_type="user",
            zotero_collection_id="COLL123",
        )

        # Verify Zotero client was created correctly
        mock_zotero_class.assert_called_once_with("12345", "user", "fake_api_key")

        # Verify create_items was called twice: once for articles, once for notes
        assert mock_zotero_client.create_items.call_count == 2

    @patch("zotero_insert_article.zotero.Zotero")
    @patch("zotero_insert_article.get_env_variable")
    def test_insert_article_batch_size(
        self,
        mock_get_env,
        mock_zotero_class,
        tmp_path,
    ):
        """Test that articles are batched correctly (50 per batch)"""
        mock_get_env.return_value = "fake_api_key"

        # Create a fresh mock for this test
        mock_zot = Mock()
        mock_zot.item_template = Mock(
            side_effect=lambda template_type: {
                "journalArticle": {
                    "itemType": "journalArticle",
                    "title": "",
                    "creators": [],
                    "tags": [],
                    "collections": [],
                },
                "note": {
                    "itemType": "note",
                    "note": "",
                    "parentItem": "",
                },
            }[template_type]
        )

        # Track all items created to properly return DOIs
        call_count = [0]
        article_dois = []

        def create_items_side_effect(items):
            call_count[0] += 1

            # For article items (have DOI field), extract and store DOIs
            if items and "DOI" in items[0]:
                dois_in_batch = [item["DOI"] for item in items if item.get("DOI")]
                article_dois.extend(dois_in_batch)
                return {
                    "successful": {
                        str(i): {"data": {"DOI": doi, "key": f"KEY_{doi}"}}
                        for i, doi in enumerate(dois_in_batch)
                    },
                    "failed": {},
                }
            else:
                # For notes (no DOI)
                return {
                    "successful": {
                        str(i): {"data": {"key": f"NOTE_KEY_{i}"}}
                        for i in range(len(items))
                    },
                    "failed": {},
                }

        mock_zot.create_items.side_effect = create_items_side_effect
        mock_zotero_class.return_value = mock_zot

        # Create 75 articles (should result in 2 batches: 50 + 25)
        articles = []
        for i in range(75):
            articles.append(
                {
                    "title": f"Article {i}",
                    "url": f"https://example.com/article{i}",
                    "journal_name": "Nature",
                    "date": "2025-10-15",
                    "access_date": "2025-10-31",
                    "raw_contents": f"Content {i}",
                    "doi": f"10.1234/test{i}",
                    "screening_reasoning": f"Relevant {i}",
                    "priority_reasoning": f"Priority {i}",
                }
            )

        json_file = tmp_path / "many_articles.json"
        json_file.write_text(json.dumps(articles))

        insert_article(
            articles_json=str(json_file),
            zotero_user_id="12345",
            zotero_library_type="user",
            zotero_collection_id="COLL123",
        )

        # Should be called 4 times: 2 for articles (50+25), 2 for notes (50+25)
        assert mock_zot.create_items.call_count == 4

        # Check batch sizes
        calls = mock_zot.create_items.call_args_list
        # First article batch: 50 items
        assert len(calls[0][0][0]) == 50
        # Second article batch: 25 items
        assert len(calls[1][0][0]) == 25
        # First notes batch: 50 items
        assert len(calls[2][0][0]) == 50
        # Second notes batch: 25 items
        assert len(calls[3][0][0]) == 25

    @patch("zotero_insert_article.zotero.Zotero")
    @patch("zotero_insert_article.get_env_variable")
    def test_insert_article_empty_file(
        self, mock_get_env, mock_zotero_class, tmp_path, mock_zotero_client
    ):
        """Test handling of empty articles file"""
        mock_get_env.return_value = "fake_api_key"
        mock_zotero_class.return_value = mock_zotero_client

        json_file = tmp_path / "empty_articles.json"
        json_file.write_text("[]")

        insert_article(
            articles_json=str(json_file),
            zotero_user_id="12345",
            zotero_library_type="user",
            zotero_collection_id="COLL123",
        )

        # With empty articles, create_items should not be called at all
        assert mock_zotero_client.create_items.call_count == 0

    @patch("zotero_insert_article.zotero.Zotero")
    @patch("zotero_insert_article.get_env_variable")
    def test_insert_article_group_library(
        self, mock_get_env, mock_zotero_class, sample_articles_json, mock_zotero_client
    ):
        """Test insertion into group library"""
        mock_get_env.return_value = "fake_api_key"
        mock_zotero_class.return_value = mock_zotero_client

        insert_article(
            articles_json=sample_articles_json,
            zotero_user_id="67890",
            zotero_library_type="group",
            zotero_collection_id="COLL456",
        )

        # Verify Zotero client was created with group library type
        mock_zotero_class.assert_called_once_with("67890", "group", "fake_api_key")

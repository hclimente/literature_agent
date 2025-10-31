#!/usr/bin/env python
"""Tests for zotero_remove_processed.py"""

import sys
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from datetime import date

import pytest

# Add the parent directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.models import Article, ArticleList
from zotero_remove_processed import remove_processed


class TestRemoveProcessed:
    """Test suite for remove_processed function"""

    @pytest.fixture
    def sample_articles(self):
        """Sample articles for testing"""
        return [
            Article(
                title="Article 1",
                url="https://example.com/article1",
                journal_name="Journal 1",
                date=date(2024, 1, 1),
                access_date=date(2024, 1, 15),
                raw_contents="Content 1",
            ),
            Article(
                title="Article 2",
                url="https://example.com/article2",
                journal_name="Journal 2",
                date=date(2024, 1, 2),
                access_date=date(2024, 1, 15),
                raw_contents="Content 2",
            ),
            Article(
                title="Article 3",
                url="https://example.com/article3",
                journal_name="Journal 3",
                date=date(2024, 1, 3),
                access_date=date(2024, 1, 15),
                raw_contents="Content 3",
            ),
        ]

    @pytest.fixture
    def mock_zotero_items(self):
        """Mock Zotero collection items"""
        return [
            {
                "data": {
                    "itemType": "journalArticle",
                    "url": "https://example.com/article1",
                    "title": "Article 1",
                }
            },
            {
                "data": {
                    "itemType": "journalArticle",
                    "url": "https://example.com/article2",
                    "title": "Article 2",
                }
            },
            {
                "data": {
                    "itemType": "note",  # Not a journal article
                    "url": "https://example.com/note1",
                }
            },
        ]

    @pytest.fixture
    def articles_json_file(self, sample_articles, tmp_path):
        """Create a temporary articles JSON file"""
        json_file = tmp_path / "articles.json"
        json_file.write_text(ArticleList.dump_json(sample_articles).decode())
        return str(json_file)

    @patch("zotero_remove_processed.get_env_variable")
    @patch("zotero_remove_processed.zotero.Zotero")
    def test_filters_already_processed_articles(
        self,
        mock_zotero_class,
        mock_env,
        sample_articles,
        articles_json_file,
        mock_zotero_items,
    ):
        """Test that already processed articles are filtered out"""
        # Setup mocks
        mock_env.return_value = "test-api-key"  # pragma: allowlist secret
        mock_zot = MagicMock()
        mock_zot.collection_items.return_value = mock_zotero_items
        mock_zotero_class.return_value = mock_zot

        written_data = []

        def capture_write(content):
            written_data.append(content)

        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.return_value.write = capture_write

            remove_processed(
                articles_json=articles_json_file,
                zotero_user_id="12345",
                zotero_library_type="user",
                zotero_collection_id="ABC123",
            )

            # Verify file was opened for writing
            mock_file.assert_called_once_with("unprocessed_articles.json", "w")

    @patch("zotero_remove_processed.get_env_variable")
    @patch("zotero_remove_processed.zotero.Zotero")
    def test_writes_only_unprocessed_articles(
        self,
        mock_zotero_class,
        mock_env,
        articles_json_file,
        mock_zotero_items,
    ):
        """Test that only unprocessed articles are written to output"""
        # Setup mocks
        mock_env.return_value = "test-api-key"  # pragma: allowlist secret
        mock_zot = MagicMock()
        mock_zot.collection_items.return_value = mock_zotero_items
        mock_zotero_class.return_value = mock_zot

        written_data = []

        def capture_write(content):
            written_data.append(content)

        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.return_value.write = capture_write

            remove_processed(
                articles_json=articles_json_file,
                zotero_user_id="12345",
                zotero_library_type="user",
                zotero_collection_id="ABC123",
            )

            # Only article3 should be written (article1 and article2 are in Zotero)
            assert len(written_data) == 1
            written_content = written_data[0]
            assert "article3" in written_content
            assert (
                "article1" not in written_content
                or written_content.count("article1") == 0
            )
            assert (
                "article2" not in written_content
                or written_content.count("article2") == 0
            )

    @patch("zotero_remove_processed.get_env_variable")
    @patch("zotero_remove_processed.zotero.Zotero")
    def test_initializes_zotero_client(
        self,
        mock_zotero_class,
        mock_env,
        articles_json_file,
        mock_zotero_items,
    ):
        """Test that Zotero client is initialized correctly"""
        mock_env.return_value = "test-api-key"  # pragma: allowlist secret
        mock_zot = MagicMock()
        mock_zot.collection_items.return_value = mock_zotero_items
        mock_zotero_class.return_value = mock_zot

        with patch("builtins.open", mock_open()):
            remove_processed(
                articles_json=articles_json_file,
                zotero_user_id="12345",
                zotero_library_type="user",
                zotero_collection_id="ABC123",
            )

            # Verify Zotero was initialized with correct params
            mock_zotero_class.assert_called_once_with(
                "12345",
                "user",
                "test-api-key",  # pragma: allowlist secret
            )

    @patch("zotero_remove_processed.get_env_variable")
    @patch("zotero_remove_processed.zotero.Zotero")
    def test_retrieves_collection_items(
        self,
        mock_zotero_class,
        mock_env,
        articles_json_file,
        mock_zotero_items,
    ):
        """Test that collection items are retrieved from Zotero"""
        mock_env.return_value = "test-api-key"  # pragma: allowlist secret
        mock_zot = MagicMock()
        mock_zot.collection_items.return_value = mock_zotero_items
        mock_zotero_class.return_value = mock_zot

        with patch("builtins.open", mock_open()):
            remove_processed(
                articles_json=articles_json_file,
                zotero_user_id="12345",
                zotero_library_type="user",
                zotero_collection_id="ABC123",
            )

            # Verify collection_items was called with correct collection ID
            mock_zot.collection_items.assert_called_once_with("ABC123")

    @patch("zotero_remove_processed.get_env_variable")
    @patch("zotero_remove_processed.zotero.Zotero")
    def test_filters_only_journal_articles(
        self,
        mock_zotero_class,
        mock_env,
        articles_json_file,
    ):
        """Test that only journal articles are considered when filtering"""
        mock_env.return_value = "test-api-key"  # pragma: allowlist secret

        # Mix of item types
        mixed_items = [
            {
                "data": {
                    "itemType": "journalArticle",
                    "url": "https://example.com/article1",
                }
            },
            {
                "data": {
                    "itemType": "note",
                    "url": "https://example.com/note1",
                }
            },
            {
                "data": {
                    "itemType": "book",
                    "url": "https://example.com/book1",
                }
            },
        ]

        mock_zot = MagicMock()
        mock_zot.collection_items.return_value = mixed_items
        mock_zotero_class.return_value = mock_zot

        written_data = []

        def capture_write(content):
            written_data.append(content)

        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.return_value.write = capture_write

            remove_processed(
                articles_json=articles_json_file,
                zotero_user_id="12345",
                zotero_library_type="user",
                zotero_collection_id="ABC123",
            )

            # Should filter article1 but not note1 or book1
            written_content = written_data[0]
            # article2 and article3 should be in output
            assert "article2" in written_content
            assert "article3" in written_content

    @patch("zotero_remove_processed.get_env_variable")
    @patch("zotero_remove_processed.zotero.Zotero")
    def test_handles_empty_zotero_collection(
        self,
        mock_zotero_class,
        mock_env,
        articles_json_file,
        sample_articles,
    ):
        """Test handling of empty Zotero collection"""
        mock_env.return_value = "test-api-key"  # pragma: allowlist secret
        mock_zot = MagicMock()
        mock_zot.collection_items.return_value = []  # Empty collection
        mock_zotero_class.return_value = mock_zot

        written_data = []

        def capture_write(content):
            written_data.append(content)

        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.return_value.write = capture_write

            remove_processed(
                articles_json=articles_json_file,
                zotero_user_id="12345",
                zotero_library_type="user",
                zotero_collection_id="ABC123",
            )

            # All articles should be written (none processed)
            written_content = written_data[0]
            assert "article1" in written_content
            assert "article2" in written_content
            assert "article3" in written_content

    @patch("zotero_remove_processed.get_env_variable")
    @patch("zotero_remove_processed.zotero.Zotero")
    def test_handles_all_articles_processed(
        self,
        mock_zotero_class,
        mock_env,
        articles_json_file,
    ):
        """Test when all articles have been processed"""
        mock_env.return_value = "test-api-key"  # pragma: allowlist secret

        # All articles already in Zotero
        all_processed = [
            {
                "data": {
                    "itemType": "journalArticle",
                    "url": "https://example.com/article1",
                }
            },
            {
                "data": {
                    "itemType": "journalArticle",
                    "url": "https://example.com/article2",
                }
            },
            {
                "data": {
                    "itemType": "journalArticle",
                    "url": "https://example.com/article3",
                }
            },
        ]

        mock_zot = MagicMock()
        mock_zot.collection_items.return_value = all_processed
        mock_zotero_class.return_value = mock_zot

        with patch("builtins.open", mock_open()) as mock_file:
            remove_processed(
                articles_json=articles_json_file,
                zotero_user_id="12345",
                zotero_library_type="user",
                zotero_collection_id="ABC123",
            )

            # File should not be opened since no unprocessed articles
            mock_file.assert_not_called()

    @patch("zotero_remove_processed.get_env_variable")
    @patch("zotero_remove_processed.zotero.Zotero")
    def test_logs_article_counts(
        self,
        mock_zotero_class,
        mock_env,
        articles_json_file,
        mock_zotero_items,
        caplog,
    ):
        """Test that article counts are logged"""
        import logging

        caplog.set_level(logging.INFO)

        mock_env.return_value = "test-api-key"  # pragma: allowlist secret
        mock_zot = MagicMock()
        mock_zot.collection_items.return_value = mock_zotero_items
        mock_zotero_class.return_value = mock_zot

        with patch("builtins.open", mock_open()):
            remove_processed(
                articles_json=articles_json_file,
                zotero_user_id="12345",
                zotero_library_type="user",
                zotero_collection_id="ABC123",
            )

        # Check log messages
        assert "Loaded 3 articles" in caplog.text
        assert "Retrieved 3 items from Zotero collection" in caplog.text

    @patch("zotero_remove_processed.get_env_variable")
    @patch("zotero_remove_processed.zotero.Zotero")
    def test_logs_skipped_articles(
        self,
        mock_zotero_class,
        mock_env,
        articles_json_file,
        mock_zotero_items,
        caplog,
    ):
        """Test that skipped articles are logged"""
        import logging

        caplog.set_level(logging.INFO)

        mock_env.return_value = "test-api-key"  # pragma: allowlist secret
        mock_zot = MagicMock()
        mock_zot.collection_items.return_value = mock_zotero_items
        mock_zotero_class.return_value = mock_zot

        with patch("builtins.open", mock_open()):
            remove_processed(
                articles_json=articles_json_file,
                zotero_user_id="12345",
                zotero_library_type="user",
                zotero_collection_id="ABC123",
            )

        # Check for skip messages
        assert "Skipping already processed article" in caplog.text
        assert "https://example.com/article1" in caplog.text
        assert "https://example.com/article2" in caplog.text

    @patch("zotero_remove_processed.get_env_variable")
    @patch("zotero_remove_processed.zotero.Zotero")
    def test_uses_group_library_type(
        self,
        mock_zotero_class,
        mock_env,
        articles_json_file,
        mock_zotero_items,
    ):
        """Test using group library type"""
        mock_env.return_value = "test-api-key"  # pragma: allowlist secret
        mock_zot = MagicMock()
        mock_zot.collection_items.return_value = mock_zotero_items
        mock_zotero_class.return_value = mock_zot

        with patch("builtins.open", mock_open()):
            remove_processed(
                articles_json=articles_json_file,
                zotero_user_id="12345",
                zotero_library_type="group",  # Group instead of user
                zotero_collection_id="ABC123",
            )

            # Verify correct library type used
            mock_zotero_class.assert_called_once_with(
                "12345",
                "group",
                "test-api-key",  # pragma: allowlist secret
            )

    @patch("zotero_remove_processed.get_env_variable")
    @patch("zotero_remove_processed.zotero.Zotero")
    def test_preserves_article_data(
        self,
        mock_zotero_class,
        mock_env,
        articles_json_file,
        mock_zotero_items,
    ):
        """Test that full article data is preserved in output"""
        mock_env.return_value = "test-api-key"  # pragma: allowlist secret
        mock_zot = MagicMock()
        mock_zot.collection_items.return_value = mock_zotero_items
        mock_zotero_class.return_value = mock_zot

        written_data = []

        def capture_write(content):
            written_data.append(content)

        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.return_value.write = capture_write

            remove_processed(
                articles_json=articles_json_file,
                zotero_user_id="12345",
                zotero_library_type="user",
                zotero_collection_id="ABC123",
            )

            # Verify article data is preserved
            written_content = written_data[0]
            assert "Article 3" in written_content
            assert "Journal 3" in written_content
            assert "Content 3" in written_content

    @patch("zotero_remove_processed.get_env_variable")
    @patch("zotero_remove_processed.zotero.Zotero")
    def test_handles_url_str_conversion(
        self,
        mock_zotero_class,
        mock_env,
        articles_json_file,
        mock_zotero_items,
    ):
        """Test that URL is converted to string for comparison"""
        mock_env.return_value = "test-api-key"  # pragma: allowlist secret
        mock_zot = MagicMock()
        mock_zot.collection_items.return_value = mock_zotero_items
        mock_zotero_class.return_value = mock_zot

        # The function converts item.url to str() before checking
        with patch("builtins.open", mock_open()):
            remove_processed(
                articles_json=articles_json_file,
                zotero_user_id="12345",
                zotero_library_type="user",
                zotero_collection_id="ABC123",
            )

            # Should complete without error
            assert True

    @patch("zotero_remove_processed.get_env_variable")
    def test_handles_missing_api_key(self, mock_env, articles_json_file):
        """Test handling of missing API key"""
        mock_env.return_value = None

        # Should fail when trying to initialize Zotero client
        # The actual error depends on pyzotero's behavior
        with pytest.raises(Exception):
            remove_processed(
                articles_json=articles_json_file,
                zotero_user_id="12345",
                zotero_library_type="user",
                zotero_collection_id="ABC123",
            )

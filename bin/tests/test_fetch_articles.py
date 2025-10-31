#!/usr/bin/env python
"""Tests for fetch_articles.py"""

import pytest
from datetime import date
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch
import time

# Add the parent directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from fetch_articles import fetch_rss_feed
from common.models import Article


class TestFetchRssFeed:
    """Test suite for fetch_rss_feed function"""

    @pytest.fixture
    def bbc_feed_url(self):
        """BBC News RSS feed URL for testing"""
        return "http://feeds.bbci.co.uk/news/rss.xml"

    @pytest.fixture
    def mock_feed_entry(self):
        """Create a mock RSS feed entry"""
        entry = Mock()
        entry.link = "https://www.bbc.com/news/test-article-123"
        entry.title = "Test Article Title"
        entry.summary = "This is a test summary"

        # Set published_parsed as time.struct_time
        entry.published_parsed = time.strptime(
            "2025-10-25 10:30:00", "%Y-%m-%d %H:%M:%S"
        )
        entry.updated_parsed = None
        entry.created_parsed = None

        # Also set string versions
        entry.published = "Thu, 25 Oct 2025 10:30:00 GMT"
        entry.updated = None
        entry.created = None

        return entry

    @pytest.fixture
    def mock_old_feed_entry(self):
        """Create a mock RSS feed entry with an old date"""
        entry = Mock()
        entry.link = "https://www.bbc.com/news/old-article-456"
        entry.title = "Old Article Title"
        entry.summary = "This is an old test summary"

        # Set published_parsed as time.struct_time (before cutoff)
        entry.published_parsed = time.strptime(
            "2025-10-10 10:30:00", "%Y-%m-%d %H:%M:%S"
        )
        entry.updated_parsed = None
        entry.created_parsed = None

        # Also set string versions
        entry.published = "Thu, 10 Oct 2025 10:30:00 GMT"
        entry.updated = None
        entry.created = None

        return entry

    @pytest.fixture
    def mock_feed_entry_no_date(self):
        """Create a mock RSS feed entry without date information"""
        entry = Mock()
        entry.link = "https://www.bbc.com/news/no-date-article-789"
        entry.title = "No Date Article"
        entry.summary = "Article without date"

        # No date fields
        entry.published_parsed = None
        entry.updated_parsed = None
        entry.created_parsed = None
        entry.published = None
        entry.updated = None
        entry.created = None

        return entry

    @pytest.fixture
    def mock_feed(self, mock_feed_entry, mock_old_feed_entry, mock_feed_entry_no_date):
        """Create a mock RSS feed with multiple entries"""
        feed = Mock()
        feed.bozo = 0
        feed.entries = [mock_feed_entry, mock_old_feed_entry, mock_feed_entry_no_date]
        # Make feed support 'in' operator
        feed.__contains__ = Mock(side_effect=lambda key: key in ["bozo", "entries"])
        return feed

    def test_fetch_rss_feed_basic(
        self, mock_feed, mock_feed_entry, tmp_path, monkeypatch
    ):
        """Test basic RSS feed fetching with valid entries"""
        # Change to temp directory to avoid writing to actual project
        monkeypatch.chdir(tmp_path)

        with patch("fetch_articles.feedparser.parse", return_value=mock_feed):
            articles = fetch_rss_feed(
                journal_name="BBC News",
                url="http://feeds.bbci.co.uk/news/rss.xml",
                cutoff_date="2025-10-20",
                max_items=5,
            )

        # Should return 1 article (one is too old, one has no date)
        assert len(articles) == 1
        assert isinstance(articles[0], Article)
        assert articles[0].journal_name == "BBC News"
        assert str(articles[0].url) == mock_feed_entry.link
        assert articles[0].date == date(2025, 10, 25)

        # Check that articles.json was created
        articles_file = tmp_path / "articles.json"
        assert articles_file.exists()

    def test_fetch_rss_feed_filters_old_articles(
        self, mock_feed, tmp_path, monkeypatch
    ):
        """Test that articles before cutoff date are filtered"""
        monkeypatch.chdir(tmp_path)

        with patch("fetch_articles.feedparser.parse", return_value=mock_feed):
            articles = fetch_rss_feed(
                journal_name="BBC News",
                url="http://feeds.bbci.co.uk/news/rss.xml",
                cutoff_date="2025-10-20",
                max_items=5,
            )

        # Should only return the recent article
        assert len(articles) == 1
        assert articles[0].date == date(2025, 10, 25)

    def test_fetch_rss_feed_respects_max_items(self, tmp_path, monkeypatch):
        """Test that max_items parameter is respected"""
        monkeypatch.chdir(tmp_path)

        # Create feed with many entries
        feed = Mock()
        feed.bozo = 0
        feed.entries = []
        feed.__contains__ = Mock(side_effect=lambda key: key in ["bozo", "entries"])

        for i in range(10):
            entry = Mock()
            entry.link = f"https://www.bbc.com/news/article-{i}"
            entry.title = f"Article {i}"
            entry.summary = f"Summary {i}"
            entry.published_parsed = time.strptime(
                "2025-10-25 10:30:00", "%Y-%m-%d %H:%M:%S"
            )
            entry.updated_parsed = None
            entry.created_parsed = None
            entry.published = "Thu, 25 Oct 2025 10:30:00 GMT"
            entry.updated = None
            entry.created = None
            feed.entries.append(entry)

        with patch("fetch_articles.feedparser.parse", return_value=feed):
            articles = fetch_rss_feed(
                journal_name="BBC News",
                url="http://feeds.bbci.co.uk/news/rss.xml",
                cutoff_date="2025-10-20",
                max_items=3,
            )

        # Should only return 3 articles due to max_items
        assert len(articles) == 3

    def test_fetch_rss_feed_skips_entries_without_date(
        self, mock_feed, tmp_path, monkeypatch
    ):
        """Test that entries without parseable dates are skipped"""
        monkeypatch.chdir(tmp_path)

        with patch("fetch_articles.feedparser.parse", return_value=mock_feed):
            articles = fetch_rss_feed(
                journal_name="BBC News",
                url="http://feeds.bbci.co.uk/news/rss.xml",
                cutoff_date="2025-10-20",
                max_items=5,
            )

        # Should not include the entry without date
        assert len(articles) == 1
        assert all(article.date is not None for article in articles)

    def test_fetch_rss_feed_handles_malformed_feed(self, tmp_path, monkeypatch):
        """Test handling of malformed RSS feeds"""
        monkeypatch.chdir(tmp_path)

        # Create a malformed feed
        feed = Mock()
        feed.bozo = 1  # Indicates malformed feed
        feed.entries = []
        feed.__contains__ = Mock(side_effect=lambda key: key in ["bozo", "entries"])

        with patch("fetch_articles.feedparser.parse", return_value=feed):
            articles = fetch_rss_feed(
                journal_name="BBC News",
                url="http://feeds.bbci.co.uk/news/rss.xml",
                cutoff_date="2025-10-20",
                max_items=5,
            )

        # Should return empty list
        assert len(articles) == 0

    def test_fetch_rss_feed_uses_alternative_date_fields(self, tmp_path, monkeypatch):
        """Test that function uses alternative date fields when published is not available"""
        monkeypatch.chdir(tmp_path)

        # Create entry with only updated field
        entry = Mock()
        entry.link = "https://www.bbc.com/news/updated-article-123"
        entry.title = "Updated Article"
        entry.summary = "Article with updated date"
        entry.published_parsed = None
        entry.updated_parsed = time.strptime("2025-10-25 15:00:00", "%Y-%m-%d %H:%M:%S")
        entry.created_parsed = None
        entry.published = None
        entry.updated = "Thu, 25 Oct 2025 15:00:00 GMT"
        entry.created = None

        feed = Mock()
        feed.bozo = 0
        feed.entries = [entry]
        feed.__contains__ = Mock(side_effect=lambda key: key in ["bozo", "entries"])

        with patch("fetch_articles.feedparser.parse", return_value=feed):
            articles = fetch_rss_feed(
                journal_name="BBC News",
                url="http://feeds.bbci.co.uk/news/rss.xml",
                cutoff_date="2025-10-20",
                max_items=5,
            )

        assert len(articles) == 1
        assert articles[0].date == date(2025, 10, 25)

    def test_fetch_rss_feed_uses_string_date_fallback(self, tmp_path, monkeypatch):
        """Test that function falls back to string date fields when parsed fields are not available"""
        monkeypatch.chdir(tmp_path)

        # Create entry with only string date fields
        entry = Mock()
        entry.link = "https://www.bbc.com/news/string-date-article-123"
        entry.title = "String Date Article"
        entry.summary = "Article with string date"
        entry.published_parsed = None
        entry.updated_parsed = None
        entry.created_parsed = None
        entry.published = "2025-10-25T10:30:00Z"
        entry.updated = None
        entry.created = None

        feed = Mock()
        feed.bozo = 0
        feed.entries = [entry]
        feed.__contains__ = Mock(side_effect=lambda key: key in ["bozo", "entries"])

        with patch("fetch_articles.feedparser.parse", return_value=feed):
            articles = fetch_rss_feed(
                journal_name="BBC News",
                url="http://feeds.bbci.co.uk/news/rss.xml",
                cutoff_date="2025-10-20",
                max_items=5,
            )

        assert len(articles) == 1
        assert articles[0].date == date(2025, 10, 25)

    def test_fetch_rss_feed_article_structure(self, mock_feed, tmp_path, monkeypatch):
        """Test that returned articles have correct structure"""
        monkeypatch.chdir(tmp_path)

        with patch("fetch_articles.feedparser.parse", return_value=mock_feed):
            articles = fetch_rss_feed(
                journal_name="BBC News",
                url="http://feeds.bbci.co.uk/news/rss.xml",
                cutoff_date="2025-10-20",
                max_items=5,
            )

        assert len(articles) == 1
        article = articles[0]

        # Check required fields
        assert isinstance(article, Article)
        assert article.journal_name == "BBC News"
        assert article.url is not None
        assert article.date is not None
        assert hasattr(article, "raw_contents")
        assert hasattr(article, "access_date")

    def test_fetch_rss_feed_empty_feed(self, tmp_path, monkeypatch):
        """Test handling of empty RSS feeds"""
        monkeypatch.chdir(tmp_path)

        feed = Mock()
        feed.bozo = 0
        feed.entries = []
        feed.__contains__ = Mock(side_effect=lambda key: key in ["bozo", "entries"])

        with patch("fetch_articles.feedparser.parse", return_value=feed):
            articles = fetch_rss_feed(
                journal_name="BBC News",
                url="http://feeds.bbci.co.uk/news/rss.xml",
                cutoff_date="2025-10-20",
                max_items=5,
            )

        assert len(articles) == 0

        # Check that no articles.json is created for empty results
        articles_file = tmp_path / "articles.json"
        assert not articles_file.exists()

    def test_fetch_rss_feed_cutoff_date_formats(self, tmp_path, monkeypatch):
        """Test that different cutoff date formats are handled correctly"""
        monkeypatch.chdir(tmp_path)

        entry = Mock()
        entry.link = "https://www.bbc.com/news/test-article-123"
        entry.title = "Test Article"
        entry.summary = "Test summary"
        entry.published_parsed = time.strptime(
            "2025-10-25 10:30:00", "%Y-%m-%d %H:%M:%S"
        )
        entry.updated_parsed = None
        entry.created_parsed = None
        entry.published = "Thu, 25 Oct 2025 10:30:00 GMT"
        entry.updated = None
        entry.created = None

        feed = Mock()
        feed.bozo = 0
        feed.entries = [entry]
        feed.__contains__ = Mock(side_effect=lambda key: key in ["bozo", "entries"])

        # Test ISO 8601 format
        with patch("fetch_articles.feedparser.parse", return_value=feed):
            articles = fetch_rss_feed(
                journal_name="BBC News",
                url="http://feeds.bbci.co.uk/news/rss.xml",
                cutoff_date="2025-10-20",
                max_items=5,
            )

        assert len(articles) == 1

    def test_fetch_rss_feed_writes_json_file(self, mock_feed, tmp_path, monkeypatch):
        """Test that articles are written to JSON file"""
        monkeypatch.chdir(tmp_path)

        with patch("fetch_articles.feedparser.parse", return_value=mock_feed):
            _ = fetch_rss_feed(
                journal_name="BBC News",
                url="http://feeds.bbci.co.uk/news/rss.xml",
                cutoff_date="2025-10-20",
                max_items=5,
            )

        articles_file = tmp_path / "articles.json"
        assert articles_file.exists()

        # Check that JSON is valid
        with open(articles_file, "r") as f:
            json_content = f.read()
            json_data = json.loads(json_content)

        # Should be a list with one article
        assert isinstance(json_data, list)
        assert len(json_data) == 1

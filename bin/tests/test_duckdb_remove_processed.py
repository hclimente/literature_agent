#!/usr/bin/env python
"""Tests for duckdb_remove_processed.py"""

import json
import os
import sys
from pathlib import Path

import pytest
import duckdb

# Add the parent directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from duckdb_remove_processed import remove_unprocessed_articles


class TestRemoveUnprocessedArticles:
    """Test suite for remove_unprocessed_articles function"""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create a temporary database with processed articles"""
        db_path = tmp_path / "test.duckdb"

        with duckdb.connect(str(db_path)) as con:
            # Create articles table
            con.execute("""
                CREATE TABLE articles (
                    url TEXT,
                    title TEXT
                )
            """)

            # Add some processed articles
            con.execute("""
                INSERT INTO articles (url, title)
                VALUES
                    ('http://example.com/1', 'Article 1'),
                    ('http://example.com/2', 'Article 2')
            """)

        return str(db_path)

    @pytest.fixture
    def sample_articles_json(self, tmp_path):
        """Create a temporary JSON file with sample articles"""
        articles = [
            {
                "url": "http://example.com/1",
                "title": "Article 1",
                "summary": "Summary 1",
            },
            {
                "url": "http://example.com/2",
                "title": "Article 2",
                "summary": "Summary 2",
            },
            {
                "url": "http://example.com/3",
                "title": "Article 3",
                "summary": "Summary 3",
            },
        ]

        json_path = tmp_path / "articles.json"
        with open(json_path, "w") as f:
            json.dump(articles, f)

        return str(json_path)

    @pytest.fixture(autouse=True)
    def cleanup_output_file(self):
        """Cleanup the hard-coded output file after each test"""
        yield
        # Cleanup after test
        if os.path.exists("unprocessed_articles.json"):
            os.remove("unprocessed_articles.json")

    def test_removes_processed_articles(self, temp_db, sample_articles_json, tmp_path):
        """Test that processed articles are removed"""
        output_json = tmp_path / "output.json"

        remove_unprocessed_articles(
            db_path=temp_db,
            articles_json=sample_articles_json,
            output_json=str(output_json),
        )

        # Check that output file was created (note: function hard-codes filename)
        assert os.path.exists("unprocessed_articles.json")

        # Check content
        with open("unprocessed_articles.json", "r") as f:
            result = json.load(f)

        # Only article 3 should be present (articles 1 and 2 are in DB)
        assert len(result) == 1
        assert result[0]["url"] == "http://example.com/3"

    def test_all_articles_processed(self, temp_db, tmp_path):
        """Test when all articles have been processed"""
        # Create JSON with only processed articles
        articles = [
            {"url": "http://example.com/1", "title": "Article 1"},
            {"url": "http://example.com/2", "title": "Article 2"},
        ]

        json_file = tmp_path / "articles.json"
        with open(json_file, "w") as f:
            json.dump(articles, f)

        output_json = tmp_path / "output.json"

        remove_unprocessed_articles(
            db_path=temp_db,
            articles_json=str(json_file),
            output_json=str(output_json),
        )

        # File should not be created since no unprocessed articles
        assert not os.path.exists("unprocessed_articles.json")

    def test_all_articles_unprocessed(self, temp_db, tmp_path):
        """Test when no articles have been processed"""
        # Create JSON with only unprocessed articles
        articles = [
            {"url": "http://example.com/3", "title": "Article 3"},
            {"url": "http://example.com/4", "title": "Article 4"},
        ]

        json_file = tmp_path / "articles.json"
        with open(json_file, "w") as f:
            json.dump(articles, f)

        output_json = tmp_path / "output.json"

        remove_unprocessed_articles(
            db_path=temp_db,
            articles_json=str(json_file),
            output_json=str(output_json),
        )

        # Check that all articles are in output
        assert os.path.exists("unprocessed_articles.json")

        with open("unprocessed_articles.json", "r") as f:
            result = json.load(f)

        assert len(result) == 2
        urls = [a["url"] for a in result]
        assert "http://example.com/3" in urls
        assert "http://example.com/4" in urls

    def test_empty_input(self, temp_db, tmp_path):
        """Test with empty input JSON"""
        articles = []

        json_file = tmp_path / "articles.json"
        with open(json_file, "w") as f:
            json.dump(articles, f)

        output_json = tmp_path / "output.json"

        remove_unprocessed_articles(
            db_path=temp_db,
            articles_json=str(json_file),
            output_json=str(output_json),
        )

        # No file should be created for empty input
        assert not os.path.exists("unprocessed_articles.json")

    def test_preserves_article_data(self, temp_db, tmp_path):
        """Test that article data is preserved in output"""
        articles = [
            {
                "url": "http://example.com/3",
                "title": "Article 3",
                "summary": "Summary 3",
                "author": "Author 3",
                "date": "2024-01-01",
            }
        ]

        json_file = tmp_path / "articles.json"
        with open(json_file, "w") as f:
            json.dump(articles, f)

        output_json = tmp_path / "output.json"

        remove_unprocessed_articles(
            db_path=temp_db,
            articles_json=str(json_file),
            output_json=str(output_json),
        )

        # Check that all data is preserved
        with open("unprocessed_articles.json", "r") as f:
            result = json.load(f)

        assert len(result) == 1
        article = result[0]
        assert article["url"] == "http://example.com/3"
        assert article["title"] == "Article 3"
        assert article["summary"] == "Summary 3"
        assert article["author"] == "Author 3"
        assert article["date"] == "2024-01-01"

    def test_handles_special_characters_in_urls(self, temp_db, tmp_path):
        """Test handling of special characters in URLs"""
        articles = [
            {
                "url": "http://example.com/article?param=value&other=123",
                "title": "Article with query params",
            },
            {
                "url": "http://example.com/article#section",
                "title": "Article with fragment",
            },
        ]

        json_file = tmp_path / "articles.json"
        with open(json_file, "w") as f:
            json.dump(articles, f)

        output_json = tmp_path / "output.json"

        remove_unprocessed_articles(
            db_path=temp_db,
            articles_json=str(json_file),
            output_json=str(output_json),
        )

        # Both articles should be in output (not in DB)
        with open("unprocessed_articles.json", "r") as f:
            result = json.load(f)

        assert len(result) == 2
        urls = [a["url"] for a in result]
        assert "http://example.com/article?param=value&other=123" in urls
        assert "http://example.com/article#section" in urls

    def test_empty_database(self, tmp_path):
        """Test with an empty database"""
        # Create empty database
        db_path = tmp_path / "empty.duckdb"
        with duckdb.connect(str(db_path)) as con:
            con.execute("""
                CREATE TABLE articles (
                    url TEXT,
                    title TEXT
                )
            """)

        articles = [
            {"url": "http://example.com/1", "title": "Article 1"},
            {"url": "http://example.com/2", "title": "Article 2"},
        ]

        json_file = tmp_path / "articles.json"
        with open(json_file, "w") as f:
            json.dump(articles, f)

        output_json = tmp_path / "output.json"

        remove_unprocessed_articles(
            db_path=str(db_path),
            articles_json=str(json_file),
            output_json=str(output_json),
        )

        # All articles should be in output (none in DB)
        with open("unprocessed_articles.json", "r") as f:
            result = json.load(f)

        assert len(result) == 2

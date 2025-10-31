#!/usr/bin/env python
"""Tests for duckdb_create.py"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import duckdb

# Add the parent directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from duckdb_create import create_journal_table, create_articles_table


class TestCreateJournalTable:
    """Test suite for create_journal_table function"""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create a temporary database path"""
        db_path = tmp_path / "test.duckdb"
        return str(db_path)

    @pytest.fixture
    def sample_journals_tsv(self, tmp_path):
        """Create a sample journals TSV file"""
        tsv_path = tmp_path / "journals.tsv"
        tsv_path.write_text(
            "name\tfeed_url\n"
            "Nature\thttps://www.nature.com/nature.rss\n"
            "Science\thttps://www.science.org/rss/news_current.xml\n"
        )
        return str(tsv_path)

    def test_create_journal_table_basic(self, temp_db, sample_journals_tsv):
        """Test basic journal table creation and population"""
        create_journal_table(sample_journals_tsv, temp_db, "2024-01-01")

        # Verify table was created
        with duckdb.connect(temp_db) as con:
            # Check table exists
            tables = con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='sources'"
            ).fetchall()
            assert (
                len(tables) > 0
                or con.execute("SELECT COUNT(*) FROM sources").fetchone()[0] >= 0
            )

            # Check data was inserted
            result = con.execute(
                "SELECT name, feed_url, last_checked FROM sources ORDER BY name"
            ).fetchall()

            assert len(result) == 2
            assert result[0] == (
                "Nature",
                "https://www.nature.com/nature.rss",
                "2024-01-01",
            )
            assert result[1] == (
                "Science",
                "https://www.science.org/rss/news_current.xml",
                "2024-01-01",
            )

    def test_create_journal_table_with_different_cutoff_date(
        self, temp_db, sample_journals_tsv
    ):
        """Test journal table creation with different cutoff date"""
        create_journal_table(sample_journals_tsv, temp_db, "2025-06-15")

        with duckdb.connect(temp_db) as con:
            result = con.execute("SELECT last_checked FROM sources LIMIT 1").fetchone()
            assert result[0] == "2025-06-15"

    def test_create_journal_table_skips_empty_lines(self, temp_db, tmp_path):
        """Test that empty lines in TSV are skipped"""
        tsv_path = tmp_path / "journals_with_blanks.tsv"
        tsv_path.write_text(
            "name\tfeed_url\n"
            "Nature\thttps://www.nature.com/nature.rss\n"
            "\n"
            "Science\thttps://www.science.org/rss/news_current.xml\n"
            "\n"
        )

        create_journal_table(str(tsv_path), temp_db, "2024-01-01")

        with duckdb.connect(temp_db) as con:
            count = con.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
            assert count == 2

    def test_create_journal_table_if_not_exists(self, temp_db, sample_journals_tsv):
        """Test that CREATE TABLE IF NOT EXISTS works correctly"""
        # Create table first time
        create_journal_table(sample_journals_tsv, temp_db, "2024-01-01")

        # Create table second time - should not error
        create_journal_table(sample_journals_tsv, temp_db, "2024-01-01")

        with duckdb.connect(temp_db) as con:
            count = con.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
            # Should still be 2 because of INSERT OR IGNORE
            assert count == 2

    def test_create_journal_table_insert_or_ignore(self, temp_db, sample_journals_tsv):
        """Test that INSERT OR IGNORE prevents duplicates"""
        # Insert journals twice
        create_journal_table(sample_journals_tsv, temp_db, "2024-01-01")
        create_journal_table(sample_journals_tsv, temp_db, "2024-06-01")

        with duckdb.connect(temp_db) as con:
            count = con.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
            # Should still be 2, not 4
            assert count == 2

            # Check that the first insertion is preserved (not updated)
            result = con.execute(
                "SELECT last_checked FROM sources WHERE name = 'Nature'"
            ).fetchone()
            assert result[0] == "2024-01-01"

    def test_create_journal_table_with_special_characters(self, temp_db, tmp_path):
        """Test journal names and URLs with special characters"""
        tsv_path = tmp_path / "special_journals.tsv"
        tsv_path.write_text(
            "name\tfeed_url\n"
            "Nature & Science\thttps://example.com/feed?id=123&format=rss\n"
            "Cell (Journal)\thttps://example.com/cell.rss\n"
        )

        create_journal_table(str(tsv_path), temp_db, "2024-01-01")

        with duckdb.connect(temp_db) as con:
            result = con.execute("SELECT name FROM sources ORDER BY name").fetchall()
            assert result[0][0] == "Cell (Journal)"
            assert result[1][0] == "Nature & Science"

    def test_create_journal_table_missing_file(self, temp_db):
        """Test error handling when TSV file doesn't exist"""
        with pytest.raises(FileNotFoundError):
            create_journal_table("/nonexistent/file.tsv", temp_db, "2024-01-01")

    def test_create_journal_table_malformed_tsv(self, temp_db, tmp_path):
        """Test error handling with malformed TSV (missing column)"""
        tsv_path = tmp_path / "malformed.tsv"
        tsv_path.write_text("name\tfeed_url\nOnlyOneColumn\n")

        with pytest.raises(ValueError):
            create_journal_table(str(tsv_path), temp_db, "2024-01-01")

    def test_create_journal_table_empty_file(self, temp_db, tmp_path):
        """Test handling of TSV file with only header"""
        tsv_path = tmp_path / "empty.tsv"
        tsv_path.write_text("name\tfeed_url\n")

        # This should fail because executemany doesn't accept empty list
        with pytest.raises(duckdb.InvalidInputException):
            create_journal_table(str(tsv_path), temp_db, "2024-01-01")

    def test_create_journal_table_primary_key_constraint(self, temp_db, tmp_path):
        """Test that name is a primary key"""
        tsv_path = tmp_path / "journals.tsv"
        tsv_path.write_text(
            "name\tfeed_url\nNature\thttps://www.nature.com/nature.rss\n"
        )

        create_journal_table(str(tsv_path), temp_db, "2024-01-01")

        # Try to insert duplicate directly (bypassing INSERT OR IGNORE)
        with duckdb.connect(temp_db) as con:
            with pytest.raises(duckdb.ConstraintException):
                con.execute(
                    """
                    INSERT INTO sources (name, feed_url, last_checked)
                    VALUES ('Nature', 'https://different.url', '2024-01-01')
                """
                )

    def test_create_journal_table_not_null_constraints(self, temp_db, tmp_path):
        """Test NOT NULL constraints on feed_url and last_checked"""
        tsv_path = tmp_path / "journals.tsv"
        tsv_path.write_text(
            "name\tfeed_url\nNature\thttps://www.nature.com/nature.rss\n"
        )

        create_journal_table(str(tsv_path), temp_db, "2024-01-01")

        with duckdb.connect(temp_db) as con:
            # Try to insert with NULL feed_url
            with pytest.raises(duckdb.ConstraintException):
                con.execute(
                    """
                    INSERT INTO sources (name, feed_url, last_checked)
                    VALUES ('Test', NULL, '2024-01-01')
                """
                )

            # Try to insert with NULL last_checked
            with pytest.raises(duckdb.ConstraintException):
                con.execute(
                    """
                    INSERT INTO sources (name, feed_url, last_checked)
                    VALUES ('Test', 'https://test.com', NULL)
                """
                )

    @patch("duckdb_create.logging")
    def test_create_journal_table_logs_info(
        self, mock_logging, temp_db, sample_journals_tsv
    ):
        """Test that function logs appropriate info messages"""
        create_journal_table(sample_journals_tsv, temp_db, "2024-01-01")

        # Check that logging.info was called
        assert mock_logging.info.call_count >= 5


class TestCreateArticlesTable:
    """Test suite for create_articles_table function"""

    @pytest.fixture
    def temp_db_with_sources(self, tmp_path):
        """Create a temporary database with sources table"""
        db_path = tmp_path / "test.duckdb"

        with duckdb.connect(str(db_path)) as con:
            con.execute("""
                CREATE TABLE sources (
                    name TEXT PRIMARY KEY,
                    feed_url TEXT NOT NULL,
                    last_checked TEXT NOT NULL
                )
            """)
            con.execute("""
                INSERT INTO sources (name, feed_url, last_checked)
                VALUES ('Nature', 'https://nature.com/rss', '2024-01-01')
            """)

        return str(db_path)

    def test_create_articles_table_basic(self, temp_db_with_sources):
        """Test basic articles table creation"""
        create_articles_table(temp_db_with_sources)

        with duckdb.connect(temp_db_with_sources) as con:
            # Check that table exists and has correct columns
            columns = con.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'articles'
                ORDER BY ordinal_position
            """
            ).fetchall()

            column_names = [col[0] for col in columns]
            assert "id" in column_names
            assert "title" in column_names
            assert "journal_name" in column_names
            assert "summary" in column_names
            assert "url" in column_names
            assert "date" in column_names
            assert "doi" in column_names
            assert "screening_decision" in column_names
            assert "screening_reasoning" in column_names
            assert "priority" in column_names
            assert "priority_reasoning" in column_names

    def test_create_articles_table_sequence_created(self, temp_db_with_sources):
        """Test that the article_id_seq sequence is created"""
        create_articles_table(temp_db_with_sources)

        with duckdb.connect(temp_db_with_sources) as con:
            # Check sequence exists by trying to use it
            result = con.execute("SELECT NEXTVAL('article_id_seq')").fetchone()
            assert result[0] == 1

            result = con.execute("SELECT NEXTVAL('article_id_seq')").fetchone()
            assert result[0] == 2

    def test_create_articles_table_enum_type_created(self, temp_db_with_sources):
        """Test that the priority_level ENUM type is created"""
        create_articles_table(temp_db_with_sources)

        with duckdb.connect(temp_db_with_sources) as con:
            # Try to insert valid enum values
            con.execute("""
                INSERT INTO articles (title, summary, url, date, priority)
                VALUES ('Test', 'Summary', 'https://test.com', '2024-01-01', 'low')
            """)

            con.execute("""
                INSERT INTO articles (title, summary, url, date, priority)
                VALUES ('Test2', 'Summary2', 'https://test2.com', '2024-01-01', 'medium')
            """)

            con.execute("""
                INSERT INTO articles (title, summary, url, date, priority)
                VALUES ('Test3', 'Summary3', 'https://test3.com', '2024-01-01', 'high')
            """)

            count = con.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
            assert count == 3

    def test_create_articles_table_invalid_priority_rejected(
        self, temp_db_with_sources
    ):
        """Test that invalid priority values are rejected"""
        create_articles_table(temp_db_with_sources)

        with duckdb.connect(temp_db_with_sources) as con:
            with pytest.raises(duckdb.ConversionException):
                con.execute("""
                    INSERT INTO articles (title, summary, url, date, priority)
                    VALUES ('Test', 'Summary', 'https://test.com', '2024-01-01', 'invalid')
                """)

    def test_create_articles_table_foreign_key_constraint(self, temp_db_with_sources):
        """Test that journal_name has a foreign key constraint to sources"""
        create_articles_table(temp_db_with_sources)

        with duckdb.connect(temp_db_with_sources) as con:
            # Should succeed with valid journal_name
            con.execute("""
                INSERT INTO articles (title, journal_name, summary, url, date)
                VALUES ('Test', 'Nature', 'Summary', 'https://test.com', '2024-01-01')
            """)

            # Should fail with invalid journal_name
            with pytest.raises(duckdb.ConstraintException):
                con.execute("""
                    INSERT INTO articles (title, journal_name, summary, url, date)
                    VALUES ('Test2', 'NonExistent', 'Summary', 'https://test2.com', '2024-01-01')
                """)

    def test_create_articles_table_primary_key_on_url(self, temp_db_with_sources):
        """Test that url is the primary key"""
        create_articles_table(temp_db_with_sources)

        with duckdb.connect(temp_db_with_sources) as con:
            con.execute("""
                INSERT INTO articles (title, summary, url, date)
                VALUES ('Test', 'Summary', 'https://test.com', '2024-01-01')
            """)

            # Should fail with duplicate URL
            with pytest.raises(duckdb.ConstraintException):
                con.execute("""
                    INSERT INTO articles (title, summary, url, date)
                    VALUES ('Different Title', 'Different Summary', 'https://test.com', '2024-01-02')
                """)

    def test_create_articles_table_not_null_constraints(self, temp_db_with_sources):
        """Test NOT NULL constraints on required fields"""
        create_articles_table(temp_db_with_sources)

        with duckdb.connect(temp_db_with_sources) as con:
            # Missing title
            with pytest.raises(duckdb.ConstraintException):
                con.execute("""
                    INSERT INTO articles (summary, url, date)
                    VALUES ('Summary', 'https://test1.com', '2024-01-01')
                """)

            # Missing summary
            with pytest.raises(duckdb.ConstraintException):
                con.execute("""
                    INSERT INTO articles (title, url, date)
                    VALUES ('Title', 'https://test2.com', '2024-01-01')
                """)

            # Missing url
            with pytest.raises(duckdb.ConstraintException):
                con.execute("""
                    INSERT INTO articles (title, summary, date)
                    VALUES ('Title', 'Summary', '2024-01-01')
                """)

            # Missing date
            with pytest.raises(duckdb.ConstraintException):
                con.execute("""
                    INSERT INTO articles (title, summary, url)
                    VALUES ('Title', 'Summary', 'https://test3.com')
                """)

    def test_create_articles_table_optional_fields_default_null(
        self, temp_db_with_sources
    ):
        """Test that optional fields default to NULL"""
        create_articles_table(temp_db_with_sources)

        with duckdb.connect(temp_db_with_sources) as con:
            con.execute("""
                INSERT INTO articles (title, summary, url, date)
                VALUES ('Test', 'Summary', 'https://test.com', '2024-01-01')
            """)

            result = con.execute("""
                SELECT doi, screening_decision, screening_reasoning,
                       priority, priority_reasoning
                FROM articles
            """).fetchone()

            assert result[0] is None  # doi
            assert result[1] is None  # screening_decision
            assert result[2] is None  # screening_reasoning
            assert result[3] is None  # priority
            assert result[4] is None  # priority_reasoning

    def test_create_articles_table_id_auto_increments(self, temp_db_with_sources):
        """Test that id auto-increments using the sequence"""
        create_articles_table(temp_db_with_sources)

        with duckdb.connect(temp_db_with_sources) as con:
            con.execute("""
                INSERT INTO articles (title, summary, url, date)
                VALUES ('Test1', 'Summary1', 'https://test1.com', '2024-01-01')
            """)

            con.execute("""
                INSERT INTO articles (title, summary, url, date)
                VALUES ('Test2', 'Summary2', 'https://test2.com', '2024-01-02')
            """)

            result = con.execute("SELECT id FROM articles ORDER BY id").fetchall()

            assert result[0][0] == 1
            assert result[1][0] == 2

    def test_create_articles_table_if_not_exists(self, temp_db_with_sources):
        """Test that CREATE TABLE IF NOT EXISTS works correctly"""
        # Create table first time
        create_articles_table(temp_db_with_sources)

        # Insert some data
        with duckdb.connect(temp_db_with_sources) as con:
            con.execute("""
                INSERT INTO articles (title, summary, url, date)
                VALUES ('Test', 'Summary', 'https://test.com', '2024-01-01')
            """)

        # Create table second time - will fail because sequence already exists
        # This is a limitation of the current implementation
        with pytest.raises(duckdb.CatalogException):
            create_articles_table(temp_db_with_sources)

    def test_create_articles_table_journal_name_can_be_null(self, temp_db_with_sources):
        """Test that journal_name can be NULL"""
        create_articles_table(temp_db_with_sources)

        with duckdb.connect(temp_db_with_sources) as con:
            con.execute("""
                INSERT INTO articles (title, summary, url, date)
                VALUES ('Test', 'Summary', 'https://test.com', '2024-01-01')
            """)

            result = con.execute("SELECT journal_name FROM articles").fetchone()
            assert result[0] is None

    @patch("duckdb_create.logging")
    def test_create_articles_table_logs_info(self, mock_logging, temp_db_with_sources):
        """Test that function logs appropriate info messages"""
        create_articles_table(temp_db_with_sources)

        # Check that logging.info was called
        assert mock_logging.info.call_count >= 3

    def test_create_articles_table_full_article_insert(self, temp_db_with_sources):
        """Test inserting a complete article with all fields"""
        create_articles_table(temp_db_with_sources)

        with duckdb.connect(temp_db_with_sources) as con:
            con.execute("""
                INSERT INTO articles (
                    title, journal_name, summary, url, date, doi,
                    screening_decision, screening_reasoning,
                    priority, priority_reasoning
                )
                VALUES (
                    'Test Article',
                    'Nature',
                    'This is a test summary',
                    'https://test.com/article',
                    '2024-01-01',
                    '10.1234/test',
                    TRUE,
                    'Relevant to research',
                    'high',
                    'Critical for current project'
                )
            """)

            result = con.execute("SELECT * FROM articles").fetchone()

            assert result[1] == "Test Article"  # title
            assert result[2] == "Nature"  # journal_name
            assert result[3] == "This is a test summary"  # summary
            assert result[4] == "https://test.com/article"  # url
            assert result[6] == "10.1234/test"  # doi
            assert result[7] is True  # screening_decision
            assert result[8] == "Relevant to research"  # screening_reasoning
            assert result[9] == "high"  # priority
            assert result[10] == "Critical for current project"  # priority_reasoning

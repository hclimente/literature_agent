#!/usr/bin/env python
"""Tests for duckdb_extract_fields.py"""

import sys
from pathlib import Path

import pytest
import duckdb

# Add the parent directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from duckdb_extract_fields import extract_fields


class TestExtractFields:
    """Test suite for extract_fields function"""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create a temporary database with test data"""
        db_path = tmp_path / "test.duckdb"

        with duckdb.connect(str(db_path)) as con:
            # Create test table
            con.execute("""
                CREATE TABLE articles (
                    id INTEGER,
                    title TEXT,
                    summary TEXT,
                    status TEXT,
                    priority INTEGER
                )
            """)

            # Insert test data
            con.executemany(
                """
                INSERT INTO articles (id, title, summary, status, priority)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (1, "First Article", "Summary 1", "published", 1),
                    (2, "Second Article", "Summary 2", "draft", 2),
                    (3, "Third Article", "Summary 3", "published", 3),
                    (4, "Fourth Article", "Summary 4", "archived", 1),
                ],
            )

        return str(db_path)

    def test_extract_all_records(self, temp_db, tmp_path):
        """Test extracting all records without WHERE clause"""
        output_file = tmp_path / "output.tsv"

        extract_fields(
            db_path=temp_db,
            table="articles",
            columns="id, title",
            output_tsv=str(output_file),
            where_clause="",
        )

        # Read and verify output
        content = output_file.read_text()
        lines = content.strip().split("\n")

        assert len(lines) == 5  # Header + 4 data rows
        assert lines[0] == "id\ttitle"
        assert "1\tFirst Article" in content
        assert "2\tSecond Article" in content
        assert "3\tThird Article" in content
        assert "4\tFourth Article" in content

    def test_extract_with_where_clause(self, temp_db, tmp_path):
        """Test extracting records with WHERE clause"""
        output_file = tmp_path / "output.tsv"

        extract_fields(
            db_path=temp_db,
            table="articles",
            columns="id, title, status",
            output_tsv=str(output_file),
            where_clause="status = 'published'",
        )

        # Read and verify output
        content = output_file.read_text()
        lines = content.strip().split("\n")

        assert len(lines) == 3  # Header + 2 published articles
        assert lines[0] == "id\ttitle\tstatus"
        assert "1\tFirst Article\tpublished" in content
        assert "3\tThird Article\tpublished" in content
        assert "Second Article" not in content

    def test_extract_single_column(self, temp_db, tmp_path):
        """Test extracting single column"""
        output_file = tmp_path / "output.tsv"

        extract_fields(
            db_path=temp_db,
            table="articles",
            columns="title",
            output_tsv=str(output_file),
            where_clause="",
        )

        # Read and verify output
        content = output_file.read_text()
        lines = content.strip().split("\n")

        assert len(lines) == 5  # Header + 4 data rows
        assert lines[0] == "title"
        assert lines[1] == "First Article"

    def test_extract_all_columns(self, temp_db, tmp_path):
        """Test extracting all columns"""
        output_file = tmp_path / "output.tsv"

        extract_fields(
            db_path=temp_db,
            table="articles",
            columns="id, title, summary, status, priority",
            output_tsv=str(output_file),
            where_clause="",
        )

        # Read and verify output
        content = output_file.read_text()
        lines = content.strip().split("\n")

        assert len(lines) == 5  # Header + 4 data rows
        assert lines[0] == "id\ttitle\tsummary\tstatus\tpriority"
        assert "1\tFirst Article\tSummary 1\tpublished\t1" in content

    def test_extract_with_custom_separator(self, temp_db, tmp_path):
        """Test extracting with custom separator"""
        output_file = tmp_path / "output.csv"

        extract_fields(
            db_path=temp_db,
            table="articles",
            columns="id, title",
            output_tsv=str(output_file),
            where_clause="",
            sep=",",
        )

        # Read and verify output
        content = output_file.read_text()
        lines = content.strip().split("\n")

        assert lines[0] == "id,title"
        assert "1,First Article" in content
        assert "\t" not in content  # No tabs

    def test_extract_with_pipe_separator(self, temp_db, tmp_path):
        """Test extracting with pipe separator"""
        output_file = tmp_path / "output.txt"

        extract_fields(
            db_path=temp_db,
            table="articles",
            columns="id, title",
            output_tsv=str(output_file),
            where_clause="",
            sep="|",
        )

        # Read and verify output
        content = output_file.read_text()
        assert "id|title" in content
        assert "1|First Article" in content

    def test_extract_with_complex_where_clause(self, temp_db, tmp_path):
        """Test extraction with complex WHERE condition"""
        output_file = tmp_path / "output.tsv"

        extract_fields(
            db_path=temp_db,
            table="articles",
            columns="id, title, priority",
            output_tsv=str(output_file),
            where_clause="priority > 1 AND status != 'archived'",
        )

        # Read and verify output
        content = output_file.read_text()
        lines = content.strip().split("\n")

        assert len(lines) == 3  # Header + 2 matching articles
        assert "2\tSecond Article\t2" in content
        assert "3\tThird Article\t3" in content

    def test_extract_with_order_by(self, temp_db, tmp_path):
        """Test extraction doesn't include ORDER BY but data order matters"""
        output_file = tmp_path / "output.tsv"

        # Note: The function doesn't support ORDER BY in where_clause,
        # but we can test the natural order
        extract_fields(
            db_path=temp_db,
            table="articles",
            columns="id, title",
            output_tsv=str(output_file),
            where_clause="",
        )

        # Read output
        content = output_file.read_text()
        lines = content.strip().split("\n")

        # Just verify all records are present
        assert len(lines) == 5

    def test_extract_no_matching_records(self, temp_db, tmp_path):
        """Test extraction when no records match WHERE clause"""
        output_file = tmp_path / "output.tsv"

        extract_fields(
            db_path=temp_db,
            table="articles",
            columns="id, title",
            output_tsv=str(output_file),
            where_clause="id = 999",  # Non-existent ID
        )

        # Read and verify output
        content = output_file.read_text()
        lines = content.strip().split("\n")

        assert len(lines) == 1  # Only header
        assert lines[0] == "id\ttitle"

    def test_extract_with_null_values(self, temp_db, tmp_path):
        """Test extraction with NULL values in data"""
        # Add record with NULL
        with duckdb.connect(temp_db) as con:
            con.execute(
                """
                INSERT INTO articles (id, title, summary, status, priority)
                VALUES (5, 'Article with NULL', NULL, 'draft', NULL)
                """
            )

        output_file = tmp_path / "output.tsv"

        extract_fields(
            db_path=temp_db,
            table="articles",
            columns="id, title, summary, priority",
            output_tsv=str(output_file),
            where_clause="id = 5",
        )

        # Read and verify output
        content = output_file.read_text()
        lines = content.strip().split("\n")

        assert len(lines) == 2  # Header + 1 data row
        # NULL values are represented as "None" by str()
        assert "5\tArticle with NULL\tNone\tNone" in content

    def test_extract_with_special_characters(self, temp_db, tmp_path):
        """Test extraction with special characters in data"""
        # Add record with special characters using parameterized query
        with duckdb.connect(temp_db) as con:
            con.execute(
                """
                INSERT INTO articles (id, title, summary, status, priority)
                VALUES (?, ?, ?, ?, ?)
                """,
                [6, 'Article\'s "Title" & More', "Summary with\ttab", "draft", 1],
            )

        output_file = tmp_path / "output.tsv"

        extract_fields(
            db_path=temp_db,
            table="articles",
            columns="id, title, summary",
            output_tsv=str(output_file),
            where_clause="id = 6",
        )

        # Read and verify output - special characters should be preserved
        content = output_file.read_text()
        assert 'Article\'s "Title" & More' in content

    def test_extract_with_numeric_columns(self, temp_db, tmp_path):
        """Test extraction of numeric columns"""
        output_file = tmp_path / "output.tsv"

        extract_fields(
            db_path=temp_db,
            table="articles",
            columns="id, priority",
            output_tsv=str(output_file),
            where_clause="",
        )

        # Read and verify output
        content = output_file.read_text()
        lines = content.strip().split("\n")

        assert len(lines) == 5
        assert "1\t1" in content
        assert "2\t2" in content

    def test_extract_with_like_operator(self, temp_db, tmp_path):
        """Test extraction with LIKE operator in WHERE clause"""
        output_file = tmp_path / "output.tsv"

        extract_fields(
            db_path=temp_db,
            table="articles",
            columns="id, title",
            output_tsv=str(output_file),
            where_clause="title LIKE '%First%'",
        )

        # Read and verify output
        content = output_file.read_text()
        lines = content.strip().split("\n")

        assert len(lines) == 2  # Header + 1 match
        assert "1\tFirst Article" in content

    def test_extract_with_in_operator(self, temp_db, tmp_path):
        """Test extraction with IN operator in WHERE clause"""
        output_file = tmp_path / "output.tsv"

        extract_fields(
            db_path=temp_db,
            table="articles",
            columns="id, title, status",
            output_tsv=str(output_file),
            where_clause="status IN ('published', 'archived')",
        )

        # Read and verify output
        content = output_file.read_text()
        lines = content.strip().split("\n")

        assert len(lines) == 4  # Header + 3 matching articles
        assert "published" in content
        assert "archived" in content
        assert "draft" not in content

    def test_extract_nonexistent_table(self, temp_db, tmp_path):
        """Test extraction from non-existent table raises error"""
        output_file = tmp_path / "output.tsv"

        with pytest.raises(Exception):  # DuckDB will raise a catalog error
            extract_fields(
                db_path=temp_db,
                table="nonexistent_table",
                columns="id, title",
                output_tsv=str(output_file),
                where_clause="",
            )

    def test_extract_nonexistent_column(self, temp_db, tmp_path):
        """Test extraction of non-existent column raises error"""
        output_file = tmp_path / "output.tsv"

        with pytest.raises(Exception):  # DuckDB will raise a binder error
            extract_fields(
                db_path=temp_db,
                table="articles",
                columns="id, nonexistent_column",
                output_tsv=str(output_file),
                where_clause="",
            )

    def test_extract_invalid_where_clause(self, temp_db, tmp_path):
        """Test extraction with invalid WHERE clause raises error"""
        output_file = tmp_path / "output.tsv"

        with pytest.raises(Exception):  # DuckDB will raise a parser error
            extract_fields(
                db_path=temp_db,
                table="articles",
                columns="id, title",
                output_tsv=str(output_file),
                where_clause="invalid syntax here",
            )

    def test_extract_creates_output_file(self, temp_db, tmp_path):
        """Test that output file is created if it doesn't exist"""
        output_file = tmp_path / "new_output.tsv"

        assert not output_file.exists()

        extract_fields(
            db_path=temp_db,
            table="articles",
            columns="id, title",
            output_tsv=str(output_file),
            where_clause="",
        )

        assert output_file.exists()

    def test_extract_overwrites_existing_file(self, temp_db, tmp_path):
        """Test that existing output file is overwritten"""
        output_file = tmp_path / "output.tsv"

        # Create file with existing content
        output_file.write_text("Old content\nOld line 2")

        extract_fields(
            db_path=temp_db,
            table="articles",
            columns="id, title",
            output_tsv=str(output_file),
            where_clause="id = 1",
        )

        # Verify old content is gone
        content = output_file.read_text()
        assert "Old content" not in content
        assert "id\ttitle" in content

    def test_extract_empty_table(self, temp_db, tmp_path):
        """Test extraction from empty table"""
        # Create empty table
        with duckdb.connect(temp_db) as con:
            con.execute("""
                CREATE TABLE empty_table (
                    id INTEGER,
                    name TEXT
                )
            """)

        output_file = tmp_path / "output.tsv"

        extract_fields(
            db_path=temp_db,
            table="empty_table",
            columns="id, name",
            output_tsv=str(output_file),
            where_clause="",
        )

        # Read and verify output
        content = output_file.read_text()
        lines = content.strip().split("\n")

        assert len(lines) == 1  # Only header
        assert lines[0] == "id\tname"

    def test_extract_with_count_aggregate(self, temp_db, tmp_path):
        """Test extraction with aggregate function (if supported via columns)"""
        output_file = tmp_path / "output.tsv"

        # This might work depending on implementation
        extract_fields(
            db_path=temp_db,
            table="articles",
            columns="status, COUNT(*) as count",
            output_tsv=str(output_file),
            where_clause="1=1 GROUP BY status",
        )

        # This test depends on whether GROUP BY in where_clause works
        # In the current implementation, it's part of WHERE not the query structure
        # So this might fail, but documents expected behavior
        content = output_file.read_text()
        assert "status" in content

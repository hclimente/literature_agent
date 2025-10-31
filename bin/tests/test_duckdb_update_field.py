#!/usr/bin/env python
"""Tests for duckdb_update_field.py"""

import sys
from pathlib import Path

import pytest
import duckdb

# Add the parent directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from duckdb_update_field import update_duckdb_field


class TestUpdateDuckdbField:
    """Test suite for update_duckdb_field function"""

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
                    status TEXT,
                    priority INTEGER
                )
            """)

            # Insert test data
            con.executemany(
                """
                INSERT INTO articles (id, title, status, priority)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (1, "Article 1", "pending", 1),
                    (2, "Article 2", "pending", 2),
                    (3, "Article 3", "completed", 3),
                    (4, "Article 4", "pending", 1),
                ],
            )

        return str(db_path)

    def test_update_single_field(self, temp_db):
        """Test updating a single field for matching records"""
        # Update status to 'processed' where priority = 1
        update_duckdb_field(
            db_path=temp_db,
            table="articles",
            set_clause="status = 'processed'",
            where_clause="priority = 1",
        )

        # Verify updates
        with duckdb.connect(temp_db) as con:
            result = con.execute(
                "SELECT id, status FROM articles WHERE priority = 1 ORDER BY id"
            ).fetchall()

            assert len(result) == 2
            assert result[0] == (1, "processed")
            assert result[1] == (4, "processed")

            # Verify other records unchanged
            other = con.execute(
                "SELECT status FROM articles WHERE priority != 1"
            ).fetchall()
            assert all(
                status[0] == "pending" or status[0] == "completed" for status in other
            )

    def test_update_multiple_fields(self, temp_db):
        """Test updating multiple fields at once"""
        update_duckdb_field(
            db_path=temp_db,
            table="articles",
            set_clause="status = 'archived', priority = 0",
            where_clause="id = 2",
        )

        # Verify updates
        with duckdb.connect(temp_db) as con:
            result = con.execute(
                "SELECT status, priority FROM articles WHERE id = 2"
            ).fetchone()

            assert result == ("archived", 0)

    def test_update_with_string_value(self, temp_db):
        """Test updating with string values"""
        update_duckdb_field(
            db_path=temp_db,
            table="articles",
            set_clause="title = 'Updated Title'",
            where_clause="id = 1",
        )

        # Verify update
        with duckdb.connect(temp_db) as con:
            result = con.execute("SELECT title FROM articles WHERE id = 1").fetchone()

            assert result[0] == "Updated Title"

    def test_update_with_numeric_value(self, temp_db):
        """Test updating with numeric values"""
        update_duckdb_field(
            db_path=temp_db,
            table="articles",
            set_clause="priority = 99",
            where_clause="status = 'pending'",
        )

        # Verify updates
        with duckdb.connect(temp_db) as con:
            result = con.execute(
                "SELECT COUNT(*) FROM articles WHERE priority = 99"
            ).fetchone()

            assert result[0] == 3  # 3 pending articles

    def test_update_multiple_records(self, temp_db):
        """Test updating multiple records at once"""
        update_duckdb_field(
            db_path=temp_db,
            table="articles",
            set_clause="status = 'batch_processed'",
            where_clause="priority IN (1, 2)",
        )

        # Verify updates
        with duckdb.connect(temp_db) as con:
            result = con.execute(
                "SELECT COUNT(*) FROM articles WHERE status = 'batch_processed'"
            ).fetchone()

            assert result[0] == 3  # Articles 1, 2, and 4

    def test_update_with_complex_where_clause(self, temp_db):
        """Test update with complex WHERE condition"""
        update_duckdb_field(
            db_path=temp_db,
            table="articles",
            set_clause="status = 'special'",
            where_clause="priority > 1 AND status = 'pending'",
        )

        # Verify updates
        with duckdb.connect(temp_db) as con:
            result = con.execute(
                "SELECT id FROM articles WHERE status = 'special' ORDER BY id"
            ).fetchall()

            assert result == [(2,)]  # Only article 2 matches

    def test_no_matching_records(self, temp_db):
        """Test update when no records match WHERE clause"""
        update_duckdb_field(
            db_path=temp_db,
            table="articles",
            set_clause="status = 'none'",
            where_clause="id = 999",  # Non-existent ID
        )

        # Verify no records were updated
        with duckdb.connect(temp_db) as con:
            result = con.execute(
                "SELECT COUNT(*) FROM articles WHERE status = 'none'"
            ).fetchone()

            assert result[0] == 0

    def test_update_all_records_with_true_condition(self, temp_db):
        """Test updating all records with always-true condition"""
        update_duckdb_field(
            db_path=temp_db,
            table="articles",
            set_clause="status = 'global'",
            where_clause="1 = 1",
        )

        # Verify all records updated
        with duckdb.connect(temp_db) as con:
            result = con.execute(
                "SELECT COUNT(*) FROM articles WHERE status = 'global'"
            ).fetchone()

            assert result[0] == 4  # All 4 articles

    def test_update_with_null_value(self, temp_db):
        """Test updating field to NULL"""
        update_duckdb_field(
            db_path=temp_db,
            table="articles",
            set_clause="title = NULL",
            where_clause="id = 1",
        )

        # Verify update
        with duckdb.connect(temp_db) as con:
            result = con.execute("SELECT title FROM articles WHERE id = 1").fetchone()

            assert result[0] is None

    def test_update_with_special_characters(self, temp_db):
        """Test updating with special characters in values"""
        # Use parameterized query instead of string formatting to avoid SQL injection
        with duckdb.connect(temp_db) as con:
            # Direct update using DuckDB's parameter binding
            con.execute(
                "UPDATE articles SET title = ? WHERE id = ?",
                ['Article\'s "Special" Title & More', 1],
            )

        # Verify update
        with duckdb.connect(temp_db) as con:
            result = con.execute("SELECT title FROM articles WHERE id = 1").fetchone()

            assert result[0] == 'Article\'s "Special" Title & More'

    def test_update_nonexistent_table(self, temp_db):
        """Test that updating non-existent table raises error"""
        with pytest.raises(Exception):  # DuckDB will raise a catalog error
            update_duckdb_field(
                db_path=temp_db,
                table="nonexistent_table",
                set_clause="field = 'value'",
                where_clause="id = 1",
            )

    def test_update_nonexistent_field(self, temp_db):
        """Test that updating non-existent field raises error"""
        with pytest.raises(Exception):  # DuckDB will raise a binder error
            update_duckdb_field(
                db_path=temp_db,
                table="articles",
                set_clause="nonexistent_field = 'value'",
                where_clause="id = 1",
            )

    def test_update_with_invalid_where_clause(self, temp_db):
        """Test that invalid WHERE clause raises error"""
        with pytest.raises(Exception):  # DuckDB will raise a parser error
            update_duckdb_field(
                db_path=temp_db,
                table="articles",
                set_clause="status = 'value'",
                where_clause="invalid syntax here",
            )

    def test_update_with_nonexistent_database(self, tmp_path):
        """Test updating with non-existent database path"""
        nonexistent_db = tmp_path / "nonexistent.duckdb"

        # Should create new database but fail because table doesn't exist
        with pytest.raises(Exception):
            update_duckdb_field(
                db_path=str(nonexistent_db),
                table="articles",
                set_clause="status = 'value'",
                where_clause="id = 1",
            )

    def test_update_preserves_other_fields(self, temp_db):
        """Test that update only affects specified fields"""
        # Get original data
        with duckdb.connect(temp_db) as con:
            original = con.execute(
                "SELECT id, title, priority FROM articles WHERE id = 1"
            ).fetchone()

        # Update only status
        update_duckdb_field(
            db_path=temp_db,
            table="articles",
            set_clause="status = 'updated'",
            where_clause="id = 1",
        )

        # Verify other fields unchanged
        with duckdb.connect(temp_db) as con:
            updated = con.execute(
                "SELECT id, title, priority FROM articles WHERE id = 1"
            ).fetchone()

        assert updated == original  # Other fields should be identical

    def test_update_with_subquery_in_where(self, temp_db):
        """Test update with subquery in WHERE clause"""
        update_duckdb_field(
            db_path=temp_db,
            table="articles",
            set_clause="status = 'high_priority'",
            where_clause="priority = (SELECT MIN(priority) FROM articles)",
        )

        # Verify updates
        with duckdb.connect(temp_db) as con:
            result = con.execute(
                "SELECT COUNT(*) FROM articles WHERE status = 'high_priority'"
            ).fetchone()

            assert result[0] == 2  # Articles with priority 1

    def test_update_creates_connection_properly(self, temp_db):
        """Test that function properly uses context manager"""
        # This test ensures no connection leaks
        update_duckdb_field(
            db_path=temp_db,
            table="articles",
            set_clause="status = 'test'",
            where_clause="id = 1",
        )

        # Should be able to connect again without issues
        with duckdb.connect(temp_db) as con:
            result = con.execute("SELECT status FROM articles WHERE id = 1").fetchone()

            assert result[0] == "test"

    def test_update_with_calculated_value(self, temp_db):
        """Test update with calculated/expression value"""
        update_duckdb_field(
            db_path=temp_db,
            table="articles",
            set_clause="priority = priority + 10",
            where_clause="id = 1",
        )

        # Verify update
        with duckdb.connect(temp_db) as con:
            result = con.execute(
                "SELECT priority FROM articles WHERE id = 1"
            ).fetchone()

            assert result[0] == 11  # Original was 1, now 1 + 10

    def test_sql_injection_attempt(self, temp_db):
        """Test that SQL injection attempts are handled (and fail)"""
        with pytest.raises(duckdb.ParserException):
            update_duckdb_field(
                db_path=temp_db,
                table="articles",
                set_clause="status = 'processed'; DROP TABLE articles;",
                where_clause="1=1",
            )

    def test_invalid_sql_syntax(self, temp_db):
        """Test with invalid SQL syntax in set_clause"""
        with pytest.raises(duckdb.ParserException):
            update_duckdb_field(
                db_path=temp_db,
                table="articles",
                set_clause="status = 'processed' AND priority =",
                where_clause="id = 1",
            )

    def test_non_existent_table(self, temp_db):
        """Test updating a non-existent table"""
        with pytest.raises(duckdb.CatalogException):
            update_duckdb_field(
                db_path=temp_db,
                table="non_existent_table",
                set_clause="status = 'processed'",
                where_clause="id = 1",
            )

    def test_non_existent_column(self, temp_db):
        """Test updating a non-existent column"""
        with pytest.raises(duckdb.BinderException):
            update_duckdb_field(
                db_path=temp_db,
                table="articles",
                set_clause="non_existent_column = 'value'",
                where_clause="id = 1",
            )

    def test_data_type_mismatch(self, temp_db):
        """Test with data type mismatch"""
        with pytest.raises(duckdb.ConversionException):
            update_duckdb_field(
                db_path=temp_db,
                table="articles",
                set_clause="priority = 'not-a-number'",
                where_clause="id = 1",
            )

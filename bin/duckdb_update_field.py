#!/usr/bin/env python
import argparse

import duckdb


def update_duckdb_field(db_path: str, table: str, set_clause: str, where_clause: str):
    """
    Update a specific field in a DuckDB table for multiple records.

    Args:
        db_path (str): Path to the DuckDB database file.
        table (str): Name of the table to update.
        set_clause (str): Clause specifying the update (e.g., "field_name = 'value'").
        where_clause (str): Clause specifying the condition for the update (e.g., "id_field = 'value'").

    Returns:
        None
    """
    with duckdb.connect(db_path) as con:
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        con.execute(query)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update a specific field in a DuckDB table for multiple records."
    )
    parser.add_argument(
        "--db_path",
        type=str,
        default="papers_please.duckdb",
        help="Path to the DuckDB database file.",
    )
    parser.add_argument(
        "--table",
        type=str,
        required=True,
        help="Name of the table to update.",
    )
    parser.add_argument(
        "--where_clause",
        type=str,
        required=True,
        help="Clause specifying the condition for the update (e.g., `id_field = 'value'`).",
    )
    parser.add_argument(
        "--set_clause",
        type=str,
        required=True,
        help="Clause specifying the update (e.g., `field_name = 'value'`).",
    )

    args = parser.parse_args()

    update_duckdb_field(args.db_path, args.table, args.set_clause, args.where_clause)

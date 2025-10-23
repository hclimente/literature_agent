#!/usr/bin/env python
import argparse

import duckdb


def extract_fields(
    db_path: str,
    table: str,
    columns: str,
    output_tsv: str,
    where_clause: str = "",
    sep: str = "\t",
) -> None:
    """
    Extract specific fields from a DuckDB table based on a condition.

    Args:
        db_path (str): Path to the DuckDB database file.
        table (str): Name of the table to update.
        columns (str): Columns to select (e.g., "id, title, summary").
        output_tsv (str): Path to the output TSV file.
        where_clause (str): Clause specifying the condition for the update (e.g., "id_field = 'value'").
        sep (str): Separator for the output TSV file. Defaults to tab character.

    Returns:
        None
    """
    if where_clause:
        where_clause = f"WHERE {where_clause} "

    with duckdb.connect(db_path) as con:
        query = f"SELECT {columns} FROM {table} {where_clause}"
        result = con.execute(query).fetchall()

    with open(output_tsv, "w") as f:
        header = columns.split(", ")
        f.write(f"{sep.join(header)}\n")
        for row in result:
            f.write(f"{sep.join(map(str, row))}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract specific fields from a DuckDB table based on a condition."
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
        "--columns",
        type=str,
        required=True,
        help="Clause specifying the columns to select (e.g., `id, title, summary`).",
    )
    parser.add_argument(
        "--where_clause",
        type=str,
        help="Clause specifying the condition for the update (e.g., `id_field = 'value'`).",
    )
    parser.add_argument(
        "--output_tsv",
        type=str,
        default="output.tsv",
        help="Path to the output TSV file.",
    )

    args = parser.parse_args()

    extract_fields(
        args.db_path, args.table, args.columns, args.output_tsv, args.where_clause
    )

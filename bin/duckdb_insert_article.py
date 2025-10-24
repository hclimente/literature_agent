#!/usr/bin/env python
import argparse
import json
import logging

import duckdb

from common.parsers import (
    add_articles_json_argument,
    add_duckdb_arguments,
)


def insert_article(
    db_path: str,
    articles_json: str,
) -> None:
    """
    Update a specific field in a DuckDB table for multiple records.

    Args:
        db_path (str): Path to the DuckDB database file.
        articles_json (str): Path to the JSON file containing articles.

    Returns:
        None
    """

    articles = json.load(open(articles_json, "r"))
    logging.info(f"Loaded {len(articles)} articles from {articles_json}.")

    for a in articles:
        a["metadata_doi"] = a["metadata_doi"] if a["metadata_doi"] != "NULL" else None

        logging.info(f"Inserting article: {a['metadata_title'][:50]}...")

        with duckdb.connect(db_path) as con:
            try:
                con.execute(
                    """
                    INSERT INTO articles (title, summary, link, journal_name, date, doi, screening_decision, screening_reasoning, priority, priority_reasoning)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        a["metadata_title"],
                        a["metadata_summary"],
                        a["link"],
                        a["journal_name"],
                        a["date"],
                        a["metadata_doi"],
                        a.get("screening_decision", None),
                        a.get("screening_reasoning", None),
                        a.get("priority_decision", None),
                        a.get("priority_reasoning", None),
                    ),
                )
                logging.info("✅ Article inserted successfully")
            except Exception as e:
                logging.error(f"❌ Failed to insert article: {e}")
                raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Insert articles from a TSV file into a DuckDB database."
    )

    parser = add_articles_json_argument(parser)
    parser = add_duckdb_arguments(parser)

    args = parser.parse_args()

    insert_article(
        args.db_path,
        args.articles_json,
    )

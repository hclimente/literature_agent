#!/usr/bin/env python
import argparse
import json
import logging

import duckdb


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
        a["doi"] = a["doi"] if a["doi"] != "NULL" else None
        a["screen_decision"] = (
            a["screen_decision"] if a["screen_decision"] != "NULL" else None
        )
        a["priority_decision"] = (
            a["priority_decision"] if a["priority_decision"] != "NULL" else None
        )

        logging.info(f"Inserting article: {a['title'][:50]}...")

        with duckdb.connect(db_path) as con:
            try:
                con.execute(
                    """
                    INSERT OR IGNORE INTO articles (title, summary, link, journal_name, date, doi, screened, priority)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        a["title"],
                        a["summary"],
                        a["link"],
                        a["journal_name"],
                        a["date"],
                        a["doi"],
                        a["screen_decision"],
                        a["priority_decision"],
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
    parser.add_argument(
        "--db_path",
        type=str,
        required=True,
        help="Path to the DuckDB database file.",
    )
    parser.add_argument(
        "--articles_json",
        type=str,
        required=True,
        help="Path to the JSON file containing articles.",
    )

    args = parser.parse_args()

    insert_article(
        args.db_path,
        args.articles_json,
    )

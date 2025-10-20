#!/usr/bin/env python
import argparse
import logging

import duckdb


def insert_article(
    db_path: str,
    title: str,
    summary: str,
    link: str,
    journal_name: str,
    date: str,
    doi: str,
    screening_decision: str,
    priority: str,
) -> None:
    """
    Update a specific field in a DuckDB table for multiple records.

    Args:
        db_path (str): Path to the DuckDB database file.
        title (str): Title of the article.
        summary (str): Summary of the article.
        link (str): Link to the article.
        journal_name (str): Name of the journal.
        date (str): Date of the article.
        doi (str): DOI of the article.
        screening_decision (str): Screening decision for the article.
        priority (str): Priority of the article.

    Returns:
        None
    """

    # Convert "NULL" strings to actual NULL values
    doi = doi if doi != "NULL" else None

    # Convert screening decision string to boolean or NULL
    if screening_decision == "NULL":
        screened_bool = None
    elif screening_decision == "true":
        screened_bool = True
    elif screening_decision == "false":
        screened_bool = False
    else:
        logging.error(f"❌ Unexpected screening_decision value: {screening_decision}.")
        raise ValueError(f"Unexpected screening_decision value: {screening_decision}.")

    # Convert priority string to enum value or NULL
    priority_value = priority if priority != "NULL" else None
    if priority_value and priority_value not in ["low", "medium", "high"]:
        logging.error(f"❌ Invalid priority value: {priority_value}.")
        raise ValueError(f"Invalid priority value: {priority_value}.")

    logging.info(f"Inserting article: {title[:50]}...")

    with duckdb.connect(db_path) as con:
        try:
            con.execute(
                """
                INSERT OR IGNORE INTO articles (title, summary, link, journal_name, date, doi, screened, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    summary,
                    link,
                    journal_name,
                    date,
                    doi,
                    screened_bool,
                    priority_value,
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
        "--title",
        type=str,
        required=True,
        help="Title of the article.",
    )
    parser.add_argument(
        "--summary",
        type=str,
        required=True,
        help="Summary of the article.",
    )
    parser.add_argument(
        "--link",
        type=str,
        required=True,
        help="Link to the article.",
    )
    parser.add_argument(
        "--journal_name",
        type=str,
        required=True,
        help="Name of the journal.",
    )
    parser.add_argument(
        "--date",
        type=str,
        required=True,
        help="Date of the article.",
    )
    parser.add_argument(
        "--doi",
        type=str,
        required=True,
        help="DOI of the article.",
    )
    parser.add_argument(
        "--screening_decision",
        type=str,
        required=True,
        help="Screening decision for the article.",
    )
    parser.add_argument(
        "--priority",
        type=str,
        required=True,
        help="Priority of the article.",
    )

    args = parser.parse_args()

    insert_article(
        args.db_path,
        args.title,
        args.summary,
        args.link,
        args.journal_name,
        args.date,
        args.doi,
        args.screening_decision,
        args.priority,
    )

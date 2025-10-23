#!/usr/bin/env python
import argparse
import json
import logging

import duckdb

from common.parsers import (
    add_articles_json_argument,
    add_duckdb_arguments,
)


def remove_unprocessed_articles(
    db_path: str,
    articles_json: str,
    output_json: str,
) -> None:
    """
    Remove articles that have already been processed from a JSON file using a DuckDB database.

    Args:
        db_path (str): Path to the DuckDB database file.
        articles_json (str): Path to the JSON file containing articles.
        output_json (str): Path to the output JSON file containing unprocessed articles.

    Returns:
        None
    """

    logging.info("-" * 20)
    logging.info(f"db_path       : {db_path}")
    logging.info(f"articles_json : {articles_json}")
    logging.info(f"output_json   : {output_json}")
    logging.info("-" * 20)

    articles = json.load(open(articles_json, "r"))
    logging.info(f"Loaded {len(articles)} articles from {articles_json}.")

    links = [a["link"] for a in articles]

    with duckdb.connect(db_path) as con:
        con.execute("""
            CREATE TEMPORARY TABLE tmp_articles (
                link TEXT,
            );
        """)

        con.executemany(
            """
            INSERT INTO tmp_articles (link)
            VALUES (?);
        """,
            [(link,) for link in links],
        )

        result = con.execute("""
            SELECT a.link
            FROM tmp_articles a
            LEFT JOIN articles p
            ON a.link = p.link
            WHERE p.title IS NULL;
        """).fetchall()
        logging.info(f"Found {len(result)} unprocessed articles.")

    unprocessed_articles = [a for a in articles if (a["link"],) in result]

    if unprocessed_articles:
        json.dump(
            unprocessed_articles, open("unprocessed_articles.json", "w"), indent=2
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Remove articles that have already been processed from a TSV file using a DuckDB database."
    )

    parser = add_articles_json_argument(parser)
    parser = add_duckdb_arguments(parser)
    parser.add_argument(
        "--output_json",
        type=str,
        required=True,
        help="Path to the output TSV file.",
    )

    args = parser.parse_args()

    remove_unprocessed_articles(
        args.db_path,
        args.articles_json,
        args.output_json,
    )

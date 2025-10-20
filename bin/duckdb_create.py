#!/usr/bin/env python
import argparse
import logging
import time

import duckdb


def create_journal_table(journals_tsv: str, db_path: str, global_cutoff_date: str):
    logging.info("-" * 20)
    logging.info("Called create_journal_table with the following arguments:")
    logging.info(f"journals_tsv       : {journals_tsv}")
    logging.info(f"db_path            : {db_path}")
    logging.info(f"global_cutoff_date : {global_cutoff_date}")
    logging.info("-" * 20)

    with duckdb.connect(db_path) as con:
        logging.info("⌛ Began creating sources table...")
        con.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                name TEXT PRIMARY KEY,
                feed_url TEXT NOT NULL,
                last_checked TEXT NOT NULL
            )
        """)
        logging.info("✅ Done creating sources table")

        with open(journals_tsv, "r") as f:
            sources = []
            for line in f:
                if line.strip() == "":
                    continue
                name, feed_url = line.strip().split("\t")
                sources.append((name, feed_url, global_cutoff_date))

        logging.info("⌛ Began inserting journal sources...")
        con.executemany(
            """
            INSERT OR IGNORE INTO sources (name, feed_url, last_checked)
            VALUES (?, ?, ?)
        """,
            sources,
        )
        logging.info("✅ Done inserting journal sources")


def create_articles_table(db_path: str):
    logging.info("-" * 20)
    logging.info("Called create_articles_table with the following arguments:")
    logging.info(f"db_path : {db_path}")
    logging.info("-" * 20)

    with duckdb.connect(db_path) as con:
        logging.info("⌛ Began creating articles table...")
        con.execute("CREATE SEQUENCE article_id_seq START 1;")
        con.execute("CREATE TYPE priority_level AS ENUM ('low', 'medium', 'high');")

        # create table to store articles
        con.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER DEFAULT NEXTVAL('article_id_seq'),
                title TEXT NOT NULL,
                journal_name TEXT,
                summary TEXT NOT NULL,
                link TEXT NOT NULL,
                date DATE NOT NULL,
                doi TEXT DEFAULT NULL,
                screened BOOLEAN DEFAULT NULL,
                priority priority_level DEFAULT NULL,
                FOREIGN KEY (journal_name) REFERENCES sources(name),
                PRIMARY KEY (link)
            )
            """)
        logging.info("✅ Done creating articles table")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Fetch articles from RSS feeds and store them in a database."
    )
    parser.add_argument(
        "--db_path",
        type=str,
        default="literature_agent.duckdb",
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--journals_tsv",
        type=str,
        required=True,
        help="Path to the TSV file containing journal names and RSS feed URLs.",
    )

    args = parser.parse_args()

    global_cutoff_date = time.strftime("%Y-%m-%d")
    create_journal_table(args.journals_tsv, args.db_path, global_cutoff_date)
    create_articles_table(args.db_path)

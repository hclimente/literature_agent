import argparse
import logging
import time

import duckdb


def create_journal_table(db_path: str, global_cutoff_date: str):
    logging.info("-" * 20)
    logging.info("Called create_journal_table with the following arguments:")
    logging.info(f"db_path            : {db_path}")
    logging.info(f"global_cutoff_date : {global_cutoff_date}")
    logging.info("-" * 20)

    with duckdb.connect(db_path) as con:
        logging.info("⌛ Began creating sources table...")
        con.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                name TEXT PRIMARY KEY,
                feed_url TEXT NOT NULL,
                last_checked DATE
            )
        """)
        logging.info("✅ Done creating sources table")

        # add entries
        sources = [
            ("Nature Genetics", "https://www.nature.com/ng.rss", global_cutoff_date),
            (
                "Nature Reviews Drug Discovery",
                "https://www.nature.com/nrd.rss",
                global_cutoff_date,
            ),
        ]

        logging.info("⌛ Began inserting journal sources...")
        con.executemany(
            """
            INSERT INTO sources (name, feed_url, last_checked)
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

        # create table to store articles
        con.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY DEFAULT NEXTVAL('article_id_seq'),
                journal_name TEXT,
                title TEXT NOT NULL,
                link TEXT NOT NULL,
                date DATE NOT NULL,
                reviewed BOOLEAN DEFAULT 0,
                priority INTEGER DEFAULT 0,
                FOREIGN KEY (journal_name) REFERENCES sources(name)
            )
            """)
        logging.info("✅ Done creating articles table")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Fetch articles from RSS feeds and store them in a database."
    )

    args = parser.parse_args()

    global_cutoff_date = time.strftime("%Y-%m-%d")
    create_journal_table(global_cutoff_date)
    create_articles_table()

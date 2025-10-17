import duckdb

DB_PATH = "rss_sources.db"


def create_journal_table():
    with duckdb.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                name TEXT PRIMARY KEY,
                feed_url TEXT NOT NULL,
                last_checked DATE
            )
        """)

        # add entries
        sources = [
            ("Nature Genetics", "https://www.nature.com/ng.rss", "2025-10-05"),
        ]
        con.executemany(
            """
            INSERT INTO sources (name, feed_url, last_checked)
            VALUES (?, ?, ?)
        """,
            sources,
        )


def create_articles_table():
    with duckdb.connect(DB_PATH) as con:
        # create table to store articles
        con.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY,
                journal_name TEXT,
                title TEXT NOT NULL,
                link TEXT NOT NULL,
                summary TEXT,
                date DATE NOT NULL,
                reviewed BOOLEAN DEFAULT 0,
                priority INTEGER DEFAULT 0,
                FOREIGN KEY (journal_name) REFERENCES sources(name)
            )
            """)


if __name__ == "__main__":
    create_journal_table()
    create_articles_table()

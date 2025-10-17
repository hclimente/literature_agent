#!/usr/bin/env python
import argparse
from time import strptime

import feedparser


def fetch_rss_feed(
    journal_name: str,
    url: str,
    cuttoff_date: str = "2025-10-05",
    max_items: int = 3,
):
    """
    Fetch the latest news articles from an RSS feed and provide concise summaries.
    Args:
        journal_name (str): The name of the journal to fetch articles from.
        url (str): The URL of the RSS feed to fetch.
        cuttoff_date (str): The cutoff date for articles in ISO 8601 format (YYYY-MM-DD). Articles published after this date will be included. Defaults to "2025-10-12".
        max_items (int): The maximum number of items to return. Defaults to 3.
    Returns:
        list: A list of dictionaries, each containing 'title', 'link', 'summary', and 'date' of an article.
    """

    cuttoff_date = strptime(cuttoff_date, "%Y-%m-%d")

    feed = feedparser.parse(url)

    # Check if the feed and entries were parsed correctly.
    if "bozo" in feed and feed.bozo == 1:
        print(f"Warning: The feed at {url} may be malformed.")
        # You might still get data, but it's good to know.

    with open("articles.tsv", "w") as f:
        for item in feed.entries[:max_items]:
            item_date = strptime(item.updated, "%Y-%m-%d")
            if item_date < cuttoff_date:
                break

            f.write(
                f"{item.title}\t{journal_name}\t{item.link}\t{item.summary}\t{item.updated}\n"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch articles from RSS feeds and store them in a database."
    )
    parser.add_argument(
        "--journal_name",
        type=str,
        required=True,
        help="The name of the journal to fetch articles from.",
    )
    parser.add_argument(
        "--feed_url", type=str, required=True, help="The URL of the RSS feed to fetch."
    )
    parser.add_argument(
        "--cutoff_date",
        type=str,
        required=True,
        help="Cutoff date for articles in ISO 8601 format (YYYY-MM-DD). Articles published after this date will be included.",
    )
    parser.add_argument(
        "--max_items",
        type=int,
        default=3,
        help="The maximum number of items to return.",
    )

    args = parser.parse_args()

    fetch_rss_feed(
        journal_name=args.journal_name,
        url=args.feed_url,
        cuttoff_date=args.cutoff_date,
        max_items=args.max_items,
    )

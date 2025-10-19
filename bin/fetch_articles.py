#!/usr/bin/env python
import argparse
import logging

from dateutil.parser import parse
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

    logging.info("-" * 20)
    logging.info("fetch_rss_feed called with the following arguments:")
    logging.info(f"journal_name : {journal_name}")
    logging.info(f"url          : {url}")
    logging.info(f"cuttoff_date : {cuttoff_date}")
    logging.info(f"max_items    : {max_items}")
    logging.info("-" * 20)

    cuttoff_date = parse(cuttoff_date, tzinfos={"UTC": 0})

    logging.info("⌛ Began fetching RSS feed...")
    feed = feedparser.parse(url)

    # Check if the feed and entries were parsed correctly.
    if "bozo" in feed and feed.bozo == 1:
        logging.warning(f"⚠️ The feed at {url} may be malformed.")
        # You might still get data, but it's good to know.
    logging.info("✅ Done fetching RSS feed")

    logging.info("⌛ Began writing articles to TSV...")

    for i, item in enumerate(feed.entries[:max_items]):
        with open(f"article_{i}.txt", "w") as f:
            f.write(f"Journal: {journal_name}\n{item}")
            # if item_date < cuttoff_date:
            #     break

            # item_date = item_date.strftime('%Y-%m-%d')
            # title = sanitize_text(item.title)

            # try:
            #     summary = sanitize_text(item.summary)
            # except AttributeError:
            #     summary = sanitize_text(item.content)

            # f.write(
            #     f"{title}\t{journal_name}\t{item.link}\t{summary}\t{item_date}\n"
            # )
    logging.info("✅ Done writing articles to TSV")


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

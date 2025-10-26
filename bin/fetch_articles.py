#!/usr/bin/env python
import argparse
import logging
import time

from dateutil.parser import parse
import feedparser

from common.models import Article, pprint


def fetch_rss_feed(
    journal_name: str,
    url: str,
    cutoff_date: str,
    max_items: int,
):
    """
    Fetch the latest news articles from an RSS feed and store them in a JSON file.

    Args:
        journal_name (str): The name of the journal to fetch articles from.
        url (str): The URL of the RSS feed to fetch.
        cutoff_date (str): The cutoff date for articles in ISO 8601 format (YYYY-MM-DD). Articles published after this date will be included. Defaults to "2025-10-12".
        max_items (int): The maximum number of items to return. Defaults to 3.
    Returns:
        list: A list of dictionaries, each containing 'title', 'url', 'date', and 'raw_contents' of an article.
    """

    logging.info("-" * 20)
    logging.info("fetch_rss_feed called with the following arguments:")
    logging.info(f"journal_name : {journal_name}")
    logging.info(f"url          : {url}")
    logging.info(f"cutoff_date  : {cutoff_date}")
    logging.info(f"max_items    : {max_items}")
    logging.info("-" * 20)

    # Parse cutoff date to naive datetime for comparison
    cutoff_date = parse(cutoff_date, tzinfos={"UTC": 0})
    cutoff_date = cutoff_date.replace(tzinfo=None)

    logging.info("⌛ Began fetching RSS feed...")
    feed = feedparser.parse(url)

    # Check if the feed and entries were parsed correctly.
    if "bozo" in feed and feed.bozo == 1:
        logging.warning(f"⚠️ The feed at {url} may be malformed.")
        # You might still get data, but it's good to know.

    logging.info(f"Found {len(feed.entries)} entries in the feed.")
    logging.info("✅ Done fetching RSS feed")

    logging.info("⌛ Began writing articles to TSV...")

    articles = []
    for i, item in enumerate(feed.entries[:max_items]):
        logging.info(f"⌛ Began processing item {i + 1}...")
        logging.info(item)

        # Extract publication date from various possible fields
        item_date = None
        for date_field in ["published_parsed", "updated_parsed", "created_parsed"]:
            if hasattr(item, date_field) and getattr(item, date_field):
                # Convert time.struct_time to datetime
                item_date = parse(
                    time.strftime("%Y-%m-%d %H:%M:%S", getattr(item, date_field))
                )
                break

        # Fallback to string date fields
        if not item_date:
            for date_field in ["published", "updated", "created"]:
                if hasattr(item, date_field) and getattr(item, date_field):
                    try:
                        item_date = parse(getattr(item, date_field), tzinfos={"UTC": 0})
                        break
                    except (ValueError, TypeError):
                        continue

        # Skip if we can't parse the date
        if not item_date:
            logging.warning("⚠️ Skipping: could not parse date.")
            continue

        # Convert to naive datetime for comparison (removes timezone info)
        item_date_naive = item_date.replace(tzinfo=None)

        # Filter by date
        if item_date_naive < cutoff_date:
            logging.warning(
                f"⚠️ Skipping: article published before cutoff date ({item_date_naive})."
            )
            continue

        article_data = {
            "journal_name": journal_name,
            "url": item.link,
            "raw_contents": str(item),
            "date": item_date_naive.date().isoformat(),
            "access_date": time.strftime("%Y-%m-%d"),
        }
        article = Article.model_validate(article_data)
        articles.append(article)

        logging.info(f"✅ Done processing item {i + 1}.")

    if articles:
        with open("articles.json", "w") as f:
            f.write(pprint(articles))

    logging.info("✅ Done writing articles to JSON.")

    return articles


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch articles from RSS feeds and store them in a JSON file."
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
        cutoff_date=args.cutoff_date,
        max_items=args.max_items,
    )

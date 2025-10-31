#!/usr/bin/env python
import argparse
import logging
import pathlib

from pyzotero import zotero

from common.models import (
    ArticleList,
    pprint,
)
from common.parsers import (
    add_input_articles_json_argument,
    add_debug_argument,
)
from common.utils import get_env_variable


def remove_processed(
    articles_json: str,
    zotero_user_id: str,
    zotero_library_type: str,
    zotero_collection_id: str,
) -> None:
    """
    Insert articles from a JSON file into Zotero.

    Args:
        articles_json (str): Path to the JSON file containing articles.
        zotero_user_id (str): Zotero user ID.
        zotero_library_type (str): Zotero library type ('user' or 'group').
        zotero_collection_id (str): Zotero collection ID to add articles to.

    Returns:
        None
    """
    logging.info("-" * 20)
    logging.info(f"articles_json        : {articles_json}")
    logging.info(f"zotero_user_id       : {zotero_user_id}")
    logging.info(f"zotero_library_type  : {zotero_library_type}")
    logging.info(f"zotero_collection_id : {zotero_collection_id}")
    logging.info("-" * 20)

    zot = zotero.Zotero(
        zotero_user_id, zotero_library_type, get_env_variable("ZOTERO_API_KEY")
    )

    json_string = pathlib.Path(articles_json).read_text()
    articles = ArticleList.validate_json(json_string)
    logging.info(f"Loaded {len(articles)} articles from {articles_json}.")

    items = zot.collection_items(zotero_collection_id)
    logging.info(f"Retrieved {len(items)} items from Zotero collection.")

    urls = {
        i["data"]["url"] for i in items if i["data"]["itemType"] == "journalArticle"
    }

    articles_to_process = []

    for item in articles:
        item_url = str(item.url)
        if item_url in urls:
            logging.info(f"Skipping already processed article: {item_url}")
            continue

        articles_to_process.append(item)

    if articles_to_process:
        with open("unprocessed_articles.json", "w") as f:
            f.write(pprint(articles))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Insert articles from a TSV file into a DuckDB database."
    )

    parser = add_input_articles_json_argument(parser)
    parser = add_debug_argument(parser)
    parser.add_argument(
        "--zotero_user_id",
        type=str,
        required=True,
        help="Zotero user ID.",
    )
    parser.add_argument(
        "--zotero_library_type",
        type=str,
        required=True,
        help="Zotero library type ('user' or 'group').",
    )
    parser.add_argument(
        "--zotero_collection_id",
        type=str,
        required=True,
        help="Zotero collection ID.",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(message)s",
    )

    remove_processed(
        args.articles_json,
        args.zotero_user_id,
        args.zotero_library_type,
        args.zotero_collection_id,
    )

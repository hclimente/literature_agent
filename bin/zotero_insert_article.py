#!/usr/bin/env python
import argparse
import json
import logging
import os

from pyzotero import zotero

from common.models import (
    Article,
)
from common.parsers import (
    add_articles_json_argument,
)


def create_zotero_article(
    item: Article, zotero_collection_id, zot: zotero.Zotero
) -> zotero.Item:
    # Get a template for a journal article
    zotero_article = zot.item_template("journalArticle")

    # Core metadata fields
    zotero_article["title"] = item.title
    zotero_article["abstractNote"] = item.summary
    zotero_article["publicationTitle"] = item.journal_name
    zotero_article["date"] = item.date.isoformat()
    zotero_article["DOI"] = item.doi
    zotero_article["url"] = item.url

    # Optional fields - populate if available
    # zotero_article['volume'] = metadata["volume"]
    # zotero_article['issue'] = metadata["issue"]
    # zotero_article['pages'] = metadata["pages"]
    # zotero_article['journalAbbreviation'] = metadata["journal_abbreviation"]
    # zotero_article['language'] = metadata["language"]
    # zotero_article['ISSN'] = metadata["issn"]
    # zotero_article['shortTitle'] = metadata["short_title"]
    # zotero_article['accessDate'] = metadata["access_date"]
    # zotero_article['series'] = metadata["series"]
    # zotero_article['seriesTitle'] = metadata["series_title"]
    # zotero_article['seriesText'] = metadata["series_text"]
    # zotero_article['archive'] = metadata["archive"]
    # zotero_article['archiveLocation'] = metadata["archive_location"]
    # zotero_article['libraryCatalog'] = metadata["library_catalog"]
    # zotero_article['callNumber'] = metadata["call_number"]
    # zotero_article['rights'] = metadata["rights"]

    # Add creators/authors if available
    zotero_article["creators"] = []
    for author in item.authors:
        if "firstName" in author and "lastName" in author:
            zotero_article["creators"].append(
                {
                    "creatorType": "author",
                    "firstName": author["firstName"],
                    "lastName": author["lastName"],
                }
            )
        elif "name" in author:
            zotero_article["creators"].append(
                {"creatorType": "author", "name": author["name"]}
            )

    # Add tags based on screening/priority
    zotero_article["tags"] = []

    try:
        zotero_article["tags"].append(
            {"tag": f"llm_priority-{item.priority_decision}", "type": 0}
        )
    except KeyError:
        pass

    # Add to collections if specified
    zotero_article["collections"] = [zotero_collection_id]
    # zotero_article["relations"] = metadata["relations"]

    return zotero_article


def create_zotero_note(item: Article, zot: zotero.Zotero) -> zotero.Item:
    note = zot.item_template("note")

    note["parentItem"] = item.zotero_key
    note["note"] = f"""
**AI Screening reasoning:** {item.screening_reasoning}

**AI Priority reasoning:** {item.priority_reasoning}
"""

    return note


def validate_response(items, response: dict) -> bool:
    """
    Validate the response from Zotero API.

    Args:
        response (dict): The response dictionary from Zotero API.

    Returns:
        bool: True if the response is valid, False otherwise.
    """
    assert "successful" in response, "Response missing 'successful' key."
    assert len(response["successful"]) == len(items), (
        f"Expected {len(items)} successful inserts, got {len(response['successful'])}."
    )
    assert "failed" in response, "Response missing 'failed' key."
    assert len(response["failed"]) == 0, (
        f"Expected 0 failed inserts, got {len(response['failed'])}."
    )
    return True


def insert_batch(zot: zotero.Zotero, items: list, return_keys: bool = True) -> list:
    resp = zot.create_items(items)

    logging.debug(f"Zotero response: {resp}")

    validate_response(items, resp)

    logging.info("✅ Batch of articles inserted successfully.")

    if not return_keys:
        return {}
    else:
        return {d["data"]["DOI"]: d["data"]["key"] for d in resp["successful"].values()}


def insert_article(
    articles_json: str,
    zotero_user_id: str,
    zotero_library_type: str,
    zotero_collection_id: str,
) -> None:
    """
    Insert articles from a JSON file into a DuckDB database.

    Args:
        articles_json (str): Path to the JSON file containing articles.
        zotero_user_id (str): Zotero user ID.
        zotero_library_type (str): Zotero library type ('user' or 'group')

    Returns:
        None
    """

    zot = zotero.Zotero(
        zotero_user_id, zotero_library_type, os.environ.get("ZOTERO_API_KEY")
    )

    articles = json.load(open(articles_json, "r"))
    logging.info(f"Loaded {len(articles)} articles from {articles_json}.")

    articles_to_insert = []
    zotero_keys = {}
    counter = 0

    for i, item in enumerate(articles):
        logging.info(f"Processing article: {item['metadata_title'][:50]}...")

        item = Article.model_validate(item)

        zotero_item = create_zotero_article(item, zotero_collection_id, zot)

        articles_to_insert.append(zotero_item)

        counter += 1

        if articles_to_insert and (counter == 50 or i == len(articles) - 1):
            batch_keys = insert_batch(zot, articles_to_insert)
            zotero_keys.update(batch_keys)
            articles_to_insert = []
            counter = 0

    notes_to_insert = []

    for i, item in enumerate(articles):
        logging.info(f"Processing notes: {item['metadata_title'][:50]}...")

        setattr(item, "zotero_key", zotero_keys[item.doi])
        note = create_zotero_note(item, zot)
        notes_to_insert.append(note)

        counter += 1

        if notes_to_insert and (counter == 50 or i == len(articles) - 1):
            insert_batch(zot, notes_to_insert, False)
            notes_to_insert = []
            counter = 0

    insert_batch(zot, notes_to_insert, False)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(
        description="Insert articles from a TSV file into a DuckDB database."
    )

    parser = add_articles_json_argument(parser)
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

    insert_article(
        args.articles_json,
        args.zotero_user_id,
        args.zotero_library_type,
        args.zotero_collection_id,
    )

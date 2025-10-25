#!/usr/bin/env python
import argparse
import json
import logging
import os

from pyzotero import zotero

from common.parsers import (
    add_articles_json_argument,
)


def create_zotero_article(
    metadata: dict, zotero_collection_id, zot: zotero.Zotero
) -> zotero.Item:
    # Get a template for a journal article
    article = zot.item_template("journalArticle")

    # Core metadata fields
    article["title"] = metadata["metadata_title"]
    article["abstractNote"] = metadata["metadata_summary"]
    article["publicationTitle"] = metadata["journal_name"]
    article["date"] = metadata["date"]
    article["DOI"] = (
        metadata["metadata_doi"]
        if metadata["metadata_doi"] and metadata["metadata_doi"] != "NULL"
        else ""
    )
    article["url"] = metadata["link"]

    # Optional fields - populate if available
    # article['volume'] = metadata["volume"]
    # article['issue'] = metadata["issue"]
    # article['pages'] = metadata["pages"]
    # article['journalAbbreviation'] = metadata["journal_abbreviation"]
    # article['language'] = metadata["language"]
    # article['ISSN'] = metadata["issn"]
    # article['shortTitle'] = metadata["short_title"]
    # article['accessDate'] = metadata["access_date"]
    # article['series'] = metadata["series"]
    # article['seriesTitle'] = metadata["series_title"]
    # article['seriesText'] = metadata["series_text"]
    # article['archive'] = metadata["archive"]
    # article['archiveLocation'] = metadata["archive_location"]
    # article['libraryCatalog'] = metadata["library_catalog"]
    # article['callNumber'] = metadata["call_number"]
    # article['rights'] = metadata["rights"]

    # Add creators/authors if available
    article["creators"] = []
    for author in metadata["authors"]:
        if "firstName" in author and "lastName" in author:
            article["creators"].append(
                {
                    "creatorType": "author",
                    "firstName": author["firstName"],
                    "lastName": author["lastName"],
                }
            )
        elif "name" in author:
            article["creators"].append(
                {"creatorType": "author", "name": author["name"]}
            )

    # Add tags based on screening/priority
    article["tags"] = []

    try:
        article["tags"].append(
            {"tag": f"llm_priority-{metadata['priority_decision']}", "type": 0}
        )
    except KeyError:
        pass

    # Add to collections if specified
    article["collections"] = [zotero_collection_id]
    # article["relations"] = metadata["relations"]

    return article


def create_zotero_note(key: str, metadata: dict, zot: zotero.Zotero) -> zotero.Item:
    note = zot.item_template("note")

    note["parentItem"] = key
    note["note"] = f"""
**AI Screening reasoning:** {metadata["screening_reasoning"]}

**AI Priority reasoning:** {metadata["priority_reasoning"]}
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
    zotero_user_id: str = "1508765",
    zotero_library_type: str = "user",
    zotero_collection_id: str = "U3T98NSQ",
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

    for i, a in enumerate(articles):
        logging.info(f"Processing article: {a['metadata_title'][:50]}...")

        article = create_zotero_article(a, zotero_collection_id, zot)

        articles_to_insert.append(article)

        counter += 1

        if articles_to_insert and (counter == 50 or i == len(articles) - 1):
            batch_keys = insert_batch(zot, articles_to_insert)
            zotero_keys.update(batch_keys)
            articles_to_insert = []
            counter = 0

    notes_to_insert = []

    for i, a in enumerate(articles):
        logging.info(f"Processing notes: {a['metadata_title'][:50]}...")

        note = create_zotero_note(zotero_keys[a["metadata_doi"]], a, zot)
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
    # parser.add_argument(
    #     "--zotero_user_id",
    #     type=str,
    #     required=True,
    #     help="Zotero user ID.",
    # )
    # parser.add_argument(
    #     "--zotero_library_type",
    #     type=str,
    #     required=True,
    #     help="Zotero library type ('user' or 'group').",
    # )
    # parser.add_argument(
    #     "--zotero_collection_id",
    #     type=str,
    #     required=True,
    #     help="Zotero collection ID.",
    # )

    args = parser.parse_args()

    insert_article(
        args.articles_json,
        # args.zotero_user_id,
        # args.zotero_library_type,
        # args.zotero_collection_id,
    )

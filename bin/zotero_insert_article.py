#!/usr/bin/env python
import argparse
import logging
import pathlib

from pyzotero import zotero

from common.models import (
    Article,
    ArticleList,
    Author,
    InstitutionalAuthor,
)
from common.parsers import (
    add_input_articles_json_argument,
    add_debug_argument,
)
from common.utils import get_env_variable


def add_creators(authors: list | None) -> list:
    """
    Convert a list of Author or InstitutionalAuthor objects into Zotero creator format.
    Args:
        authors (list | None): List of Author or InstitutionalAuthor objects.
        Returns:
        list: List of creators in Zotero format.
    """

    if not authors:
        return []

    creators = []
    for author in authors:
        if isinstance(author, InstitutionalAuthor):
            creators.append(
                {
                    "creatorType": "author",
                    "name": author.name,
                }
            )
        elif isinstance(author, Author):
            creators.append(
                {
                    "creatorType": "author",
                    "firstName": author.first_name,
                    "lastName": author.last_name,
                }
            )
    return creators


def create_zotero_article(
    item: Article, zotero_collection_id, zot: zotero.Zotero
) -> dict:
    """
    Create a Zotero journal article item from an Article object.

    Args:
        item (Article): The article to convert.
        zotero_collection_id: The Zotero collection ID to add the article to.
        zot (zotero.Zotero): The Zotero client instance.

    Returns:
        dict: The created Zotero article item.
    """
    # Get a template for a journal article
    zotero_article = zot.item_template("journalArticle")

    # Core metadata fields
    zotero_article["title"] = item.title
    zotero_article["abstractNote"] = item.summary
    zotero_article["publicationTitle"] = item.journal_name
    zotero_article["date"] = item.date.isoformat()
    zotero_article["DOI"] = item.doi
    zotero_article["url"] = str(item.url)

    # Optional fields - populate if available
    zotero_article["volume"] = item.volume
    zotero_article["issue"] = item.issue
    # zotero_article['pages'] = metadata["pages"]
    zotero_article["journalAbbreviation"] = item.journal_short_name
    zotero_article["language"] = item.language
    # zotero_article['ISSN'] = metadata["issn"]
    # zotero_article['shortTitle'] = metadata["short_title"]
    zotero_article["accessDate"] = item.access_date.isoformat()
    # zotero_article['series'] = metadata["series"]
    # zotero_article['seriesTitle'] = metadata["series_title"]
    # zotero_article['seriesText'] = metadata["series_text"]
    # zotero_article['archive'] = metadata["archive"]
    # zotero_article['archiveLocation'] = metadata["archive_location"]
    # zotero_article['libraryCatalog'] = metadata["library_catalog"]
    # zotero_article['callNumber'] = metadata["call_number"]
    # zotero_article['rights'] = metadata["rights"]

    # Add creators/authors if available
    zotero_article["creators"] = add_creators(item.authors)

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


def create_zotero_note(item: Article, zot: zotero.Zotero) -> dict:
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
        items: The items that were attempted to be inserted.
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
    """
    Insert a batch of items into Zotero.

    Args:
        zot (zotero.Zotero): The Zotero client instance.
        items (list): List of items to insert.
        return_keys (bool): Whether to return the created item keys.

    Returns:
        list: Dictionary mapping DOIs to Zotero keys if return_keys=True, else empty dict.
    """
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

    articles_to_insert = []
    zotero_keys = {}
    counter = 0

    for i, item in enumerate(articles):
        logging.info(f"Processing '{item.title[:50]}...'")

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
        logging.info(f"Processing notes for '{item.title[:50]}...'")

        item.zotero_key = zotero_keys[item.doi]
        note = create_zotero_note(item, zot)
        notes_to_insert.append(note)

        counter += 1

        if notes_to_insert and (counter == 50 or i == len(articles) - 1):
            insert_batch(zot, notes_to_insert, False)
            notes_to_insert = []
            counter = 0

    # Only insert remaining notes if there are any
    if notes_to_insert:
        insert_batch(zot, notes_to_insert, False)


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

    insert_article(
        args.articles_json,
        args.zotero_user_id,
        args.zotero_library_type,
        args.zotero_collection_id,
    )

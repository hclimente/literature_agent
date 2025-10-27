#!/usr/bin/env python
import argparse
import logging
import os
import pathlib

from habanero import Crossref, WorksContainer
from httpx import HTTPStatusError

from common.models import (
    ArticleList,
    Author,
    pprint,
)
from common.parsers import (
    add_input_articles_json_argument,
    add_debug_argument,
)


def process_author_list(author_data: list) -> list[Author]:
    """
    Convert raw author data from Crossref into a list of Author objects.

    Args:
        author_data (list): List of author data dictionaries from Crossref.

    Returns:
        list[Author]: List of Author objects.
    """
    authors = []
    for author in author_data:
        first_name = author["given"]
        last_name = author["family"]
        authors.append(Author(first_name=first_name, last_name=last_name))
    return authors


def fetch_metadata(articles_json: str, error_strategy: str) -> None:
    """
    Fetch metadata for a given DOI using the Crossref API.

    Args:
        articles_json (str): Path to the JSON file containing articles.
        error_strategy (str): Strategy to handle items that fail to fetch metadata.
                              Options are "exclude" (remove failed items) or "include"
                              (keep failed items with reduced metadata).
    Returns:
        None
    """
    if error_strategy not in ["exclude", "include"]:
        raise ValueError("error_strategy must be either 'exclude' or 'include'.")

    json_string = pathlib.Path(articles_json).read_text()
    articles = ArticleList.validate_json(json_string)
    logging.info(f"Loaded {len(articles)} articles from {articles_json}.")
    logging.debug(f"Articles: {pprint(articles)}")

    try:
        # set a mailto address to get into the "polite pool"
        cr = Crossref(mailto=os.environ["USER_EMAIL"])
    except KeyError:
        cr = Crossref()
    logging.info("Initialized Crossref client.")

    for i, article in enumerate(articles):
        logging.debug(f"Processing article {i + 1}/{len(articles)}: {article.doi}")

        try:
            metadata = cr.works(ids=article.doi)
        except HTTPStatusError:
            if error_strategy == "exclude":
                continue
            elif error_strategy == "include":
                logging.warning(f"Failed to fetch metadata for DOI: {article.doi}")
                continue

        metadata = WorksContainer(metadata)
        logging.debug(f"Fetched metadata for DOIs: {article.doi}")
        logging.debug(f"Metadata response: {metadata.works}")

        author_list = getattr(metadata, "author", [[]])[0]
        article.authors = process_author_list(author_list)
        journal_short_name = getattr(metadata, "short_container_title", [[None]])[0]

        if journal_short_name:
            article.journal_short_name = journal_short_name[0][0]

        article.volume = getattr(metadata, "volume", [None])[0]
        article.issue = getattr(metadata, "issue", [None])[0]

    with open("articles_with_extra_metadata.json", "w") as f:
        f.write(pprint(articles))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch metadata for articles using Crossref API."
    )
    parser = add_input_articles_json_argument(parser)
    parser = add_debug_argument(parser)
    parser.add_argument(
        "--error_strategy",
        type=str,
        choices=["exclude", "include"],
        help=(
            "Strategy to handle items that fail to fetch metadata: "
            "'exclude' to remove them, 'include' to keep them with reduced metadata."
        ),
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(message)s",
    )

    fetch_metadata(args.articles_json, args.error_strategy)

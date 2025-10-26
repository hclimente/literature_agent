#!/usr/bin/env python
import argparse
import logging
import os
import pathlib

from habanero import Crossref, WorksContainer

from common.models import (
    ArticleList,
    Author,
    pprint,
)
from common.parsers import add_articles_json_argument


def get_author_list(author_data: list) -> list[Author]:
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


def fetch_metadata(articles_json: str) -> dict:
    """
    Fetch metadata for a given DOI using the Crossref API.

    Args:
        articles_json (str): Path to the JSON file containing articles.
    """
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

        metadata = cr.works(ids=article.doi)
        x = WorksContainer(metadata)
        logging.debug(f"Fetched metadata for DOIs: {article.doi}")
        logging.debug(f"Metadata response: {x.works}")

        article.authors = get_author_list(x.author[0])
        journal_short_name = getattr(x, "short_container_title", [[None]])[0]

        if journal_short_name:
            article.journal_short_name = journal_short_name[0][0]

        article.volume = getattr(x, "volume", [None])[0]
        article.issue = getattr(x, "issue", [None])[0]

    with open("articles_with_extra_metadata.json", "w") as f:
        f.write(pprint(articles))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Fetch metadata for articles using Crossref API."
    )
    parser = add_articles_json_argument(parser)

    args = parser.parse_args()

    fetch_metadata(args.articles_json)

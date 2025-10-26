#!/usr/bin/env python
import argparse
from datetime import date
import logging
import pathlib

from common.models import ArticleList, pprint
from common.parsers import (
    add_input_articles_json_argument,
    add_debug_argument,
    add_output_argument,
)


def validate_articles_json(
    articles_json: str,
    stage: str,
    out: str,
) -> None:
    """
    Validate articles from a JSON file at different processing stages.

    Args:
        articles_json (str): Path to the JSON file containing articles.
        stage (str): Validation stage ("import" or "export").
        out (str): Path to the output file.

    Returns:
        None
    """

    logging.info(f"⌛ Began validating articles JSON to {stage}...")

    json_string = pathlib.Path(articles_json).read_text()
    articles = ArticleList.validate_json(json_string)

    # Keep only required fields based on the stage
    core_fields = [
        "url",
        "journal_name",
        "date",
        "raw_contents",
    ]
    if stage == "import":
        required_fields = core_fields
    elif stage == "export":
        required_fields = core_fields + [
            "title",
            "doi",
            "summary",
            "screening_decision",
            "screening_reasoning",
            "priority_decision",
            "priority_reasoning",
        ]
    else:
        raise ValueError(f"Unknown stage: {stage}")

    for article in articles:
        for f in article.model_fields:
            if f not in required_fields:
                setattr(article, f, None)

        # Always set access_date to today
        article.access_date = date.today().isoformat()

    # Save the validated articles to the output file
    with open(f"{out}", "w") as f:
        f.write(pprint(articles))

    logging.info("✅ Validation completed successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Validate articles from a JSON file at different processing stages."
    )
    parser = add_input_articles_json_argument(parser)
    parser = add_output_argument(parser)
    parser.add_argument(
        "--stage",
        type=str,
        required=True,
        choices=["import", "export"],
        help="Validation stage: 'import' (basic structure) or 'export' (with processing results).",
    )
    parser = add_debug_argument(parser)

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(message)s",
    )

    validate_articles_json(
        args.articles_json,
        args.stage,
        args.out,
    )

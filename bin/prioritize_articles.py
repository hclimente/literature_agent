#!/usr/bin/env python
import argparse
import json
import logging
import os

from common.llm import llm_query
from common.parsers import (
    add_articles_json_argument,
    add_llm_arguments,
)
from common.validation import (
    get_common_variations,
    validate_decision_response,
    validate_llm_response,
)
from tools.metadata_tools import get_abstract_from_doi, springer_get_abstract_from_doi

STAGE = "priority"


def validate_priority_response(response: str, allow_errors: bool) -> str:
    """
    Validate AI prioritization response. It raises an error if validation fails.

    Args:
        response_text (str): The AI response for priority decision
        allow_errors (bool): Whether to allow errors without failing the process.

    Returns:
        tuple: (articles_pass, articles_fail)
    """

    priority_mappings = get_common_variations(["low", "medium", "high"])
    return validate_decision_response(response, allow_errors, STAGE, priority_mappings)


def prioritize_articles(
    articles_json: str,
    system_prompt_path: str,
    research_interests_path: str,
    model: str,
    allow_qc_errors: bool,
):
    """
    Prioritizes articles based on user research interests.

    Args:
        articles_json (str):
        system_prompt_path (str): The path to the system prompt file.
        research_interests_path (str): The path to a text file containing the user's research interests.
        model (str): The model to use for screening. One of 'gemini-1.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.5-pro'.
        allow_qc_errors (bool): Whether to allow QC errors without failing the process.
    Returns:
        None. Writes the screening decision to 'decision.txt'.
    """
    logging.info("-" * 20)
    logging.info("screen_article called with the following arguments:")
    logging.info(f"articles_json           : {articles_json}")
    logging.info(f"system_prompt_path      : {system_prompt_path}")
    logging.info(f"research_interests_path : {research_interests_path}")
    logging.info(f"model                   : {model}")
    logging.info("-" * 20)

    articles = json.load(open(articles_json, "r"))
    logging.info(f"Loaded {len(articles)} articles.")
    logging.debug(f"articles: {articles}")

    logging.info("Began removing articles with no doi or screened out...")
    articles = [
        a for a in articles if a["metadata_doi"] != "NULL" and a["screening_decision"]
    ]
    logging.info("Done removing articles with no doi.")

    response_text = llm_query(
        articles=articles,
        system_prompt_path=system_prompt_path,
        model=model,
        api_key=os.environ.get("GOOGLE_API_KEY"),
        research_interests_path=research_interests_path,
        llm_tools=[get_abstract_from_doi, springer_get_abstract_from_doi],
    )

    validate_llm_response(
        articles, response_text, allow_qc_errors, validate_priority_response, STAGE
    )

    logging.info("✅ Done prioritizing articles.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Prioritize articles based on user research interests."
    )

    parser = add_articles_json_argument(parser)
    parser = add_llm_arguments(parser, include_research_interests=True)

    args = parser.parse_args()

    prioritize_articles(
        args.articles_json,
        args.system_prompt_path,
        args.research_interests_path,
        args.model,
        args.allow_qc_errors,
    )

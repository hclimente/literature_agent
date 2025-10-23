#!/usr/bin/env python
import argparse
import json
import logging
import os

from tools.metadata_tools import get_abstract_from_doi, springer_get_abstract_from_doi
from utils import (
    llm_query,
    validate_decision_response,
    validate_llm_response,
)

STAGE = "screening"


def validate_screening_response(response: str, allow_errors: bool) -> str:
    """
    Validate AI screening response. It raises an error if validation fails.

    Args:
        response (str): The parsed AI response for screening decision
        allow_errors (bool): Whether to allow errors without failing the process.

    Returns:
        tuple: (articles_pass, articles_fail)
    """

    screening_mappings = {
        "true": "true",
        "true.": "true",
        '"true"': "true",
        "'true'": "true",
        "false": "false",
        "false.": "false",
        '"false"': "false",
        "'false'": "false",
    }

    return validate_decision_response(response, allow_errors, STAGE, screening_mappings)


def screen_articles(
    articles_json: str,
    system_prompt_path: str,
    research_interests_path: str,
    model: str,
    allow_qc_errors: bool,
):
    """
    Screens articles based on user research interests.

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
    logging.info("screen_articles called with the following arguments:")
    logging.info(f"articles_json           : {articles_json}")
    logging.info(f"system_prompt_path      : {system_prompt_path}")
    logging.info(f"research_interests_path : {research_interests_path}")
    logging.info(f"model                   : {model}")
    logging.info(f"allow_qc_errors         : {allow_qc_errors}")
    logging.info("-" * 20)

    articles = json.load(open(articles_json, "r"))
    logging.info(f"Loaded {len(articles)} articles.")
    logging.debug(f"articles: {articles}")

    logging.info("Began removing articles with no doi...")
    articles = [a for a in articles if a["metadata_doi"] != "NULL"]
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
        articles, response_text, allow_qc_errors, validate_screening_response, STAGE
    )

    logging.info("✅ Done screening articles.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Screen articles based on user research interests."
    )
    parser.add_argument(
        "--articles_json",
        type=str,
        required=True,
        help="The path to the JSON files containing the articles to process.",
    )
    parser.add_argument(
        "--system_prompt_path",
        type=str,
        required=True,
        help="The path to the system prompt file.",
    )
    parser.add_argument(
        "--research_interests_path",
        type=str,
        required=True,
        help="The path to a text file containing the user's research interests.",
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="The model to use for screening. One of 'gemini-1.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.5-pro'.",
    )
    parser.add_argument(
        "--allow_qc_errors",
        type=bool,
        required=True,
        help="Whether to allow QC errors without failing the process.",
    )

    args = parser.parse_args()

    screen_articles(
        args.articles_json,
        args.system_prompt_path,
        args.research_interests_path,
        args.model,
        args.allow_qc_errors,
    )

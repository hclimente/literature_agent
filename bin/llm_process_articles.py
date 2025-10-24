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
    save_validated_responses,
    validate_llm_response,
)
from tools.metadata_tools import get_abstract_from_doi, springer_get_abstract_from_doi


def llm_process_articles(
    stage: str,
    articles_json: str,
    system_prompt_path: str,
    research_interests_path: str,
    model: str,
    allow_qc_errors: bool,
):
    """
    Process articles based on the provided prompt.

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
    logging.info("llm_process_articles called with the following arguments:")
    logging.info(f"articles_json           : {articles_json}")
    logging.info(f"system_prompt_path      : {system_prompt_path}")
    logging.info(f"research_interests_path : {research_interests_path}")
    logging.info(f"model                   : {model}")
    logging.info(f"allow_qc_errors         : {allow_qc_errors}")
    logging.info("-" * 20)

    articles = json.load(open(articles_json, "r"))
    logging.info(f"Loaded {len(articles)} articles.")
    logging.debug(f"articles: {articles}")

    response_text = llm_query(
        articles=articles,
        system_prompt_path=system_prompt_path,
        model=model,
        api_key=os.environ.get("GOOGLE_API_KEY"),
        research_interests_path=research_interests_path,
        llm_tools=[get_abstract_from_doi, springer_get_abstract_from_doi],
    )

    response_pass, response_fail = validate_llm_response(
        stage, response_text, allow_qc_errors
    )

    if stage == "metadata":
        kwargs = {
            "merge_key": "link",
            "expected_fields": ["title", "summary", "doi"],
        }
    else:
        kwargs = {
            "merge_key": "metadata_doi",
            "expected_fields": ["decision", "reasoning"],
        }

    save_validated_responses(
        articles,
        response_pass,
        response_fail,
        allow_qc_errors,
        stage,
        **kwargs,
    )

    logging.info(f"✅ Done {stage} articles.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(
        description="Process articles based on the provided prompt."
    )
    parser = add_articles_json_argument(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    metadata_parser = subparsers.add_parser("metadata")
    metadata_parser = add_llm_arguments(
        metadata_parser, include_research_interests=False
    )
    screening_parser = subparsers.add_parser("screening")
    screening_parser = add_llm_arguments(
        screening_parser, include_research_interests=True
    )
    priority_parser = subparsers.add_parser("priority")
    priority_parser = add_llm_arguments(
        priority_parser, include_research_interests=True
    )

    args = parser.parse_args()
    try:
        research_interests_path = args.research_interests_path
    except AttributeError:
        research_interests_path = None

    llm_process_articles(
        args.command,
        args.articles_json,
        args.system_prompt_path,
        research_interests_path,
        args.model,
        args.allow_qc_errors,
    )

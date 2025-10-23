#!/usr/bin/env python
import argparse
import json
import logging
import os
import re

from google.genai import types

from common.llm import llm_query
from common.parsers import (
    add_articles_json_argument,
    add_llm_arguments,
)
from common.validation import (
    handle_error,
    save_validated_responses,
    validate_llm_response,
)

STAGE = "metadata"


def sanitize_text(text: str) -> str:
    """
    Sanitize text by escaping special characters.

    Args:
        text (str): The text to sanitize.
    Returns:
        str: The sanitized text.
    """
    special_characters = ["\\", '"', "'", "$"]
    for char in special_characters:
        text = text.strip().replace(char, f"\\{char}")

    return text


def validate_metadata_response(
    metadata: str, allow_errors: bool = False
) -> tuple[str, str, str]:
    """
    Validate and parse AI metadata response. It raises an error if validation fails.

    Args:
        metadata (str): The AI response in JSON format.

    Returns:
        tuple[dict, dict]: A tuple containing two dictionaries:
            - articles_pass: Articles that passed validation.
            - articles_fail: Articles that failed validation with error messages.
    """

    articles_pass = {}
    articles_fail = {}

    for k, d in metadata.items():
        if not d or not isinstance(d, dict):
            articles_fail[k] = handle_error(
                d, "Empty or non-dict response.", "metadata", allow_errors
            )
            continue

        if not all(k in d for k in ["title", "summary", "doi"]):
            articles_fail[k] = handle_error(
                d, "Missing keys (title, summary, doi).", "metadata", allow_errors
            )
            continue

        # Validate individual fields
        if not d["title"]:
            articles_fail[k] = handle_error(
                d, "Title cannot be empty.", "metadata", allow_errors
            )
            continue
        else:
            d["title"] = sanitize_text(d["title"].strip())

        if not d["summary"]:
            articles_fail[k] = handle_error(
                d, "Summary cannot be empty.", "metadata", allow_errors
            )
            continue
        else:
            d["summary"] = d["summary"].strip()

        if not d["doi"]:
            articles_fail[k] = handle_error(
                d, "DOI cannot be empty.", "metadata", allow_errors
            )
            continue

        elif d["doi"] != "NULL":
            if not re.match(r"^10\.\d{4,}/[^\s]+$", d["doi"]):
                articles_fail[k] = handle_error(
                    d, d["metadata_error"], "metadata", allow_errors
                )
                continue
            d["doi"] = d["doi"].strip()

        articles_pass[k] = d

    return articles_pass, articles_fail


def extract_metadata(
    articles_json: str,
    system_prompt_path: str = None,
    model: str = None,
    allow_qc_errors: bool = False,
):
    """
    Extract metadata from an article using Google Gemini.

    Args:
        articles_json (str): The path to the JSON files containing the articles to process.
        system_prompt_path (str, optional): The path to the system prompt file.
        model (str, optional): The model to use for metadata extraction. One of 'gemini-1.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.5-pro'.
        allow_qc_errors (bool, optional): Whether to allow QC errors without failing the process.
    Returns:
        None.
    """
    logging.info("-" * 20)
    logging.info("extract_metadata called with the following arguments:")
    logging.info(f"articles_json      : {articles_json}")
    logging.info(f"system_prompt_path : {system_prompt_path}")
    logging.info(f"model              : {model}")
    logging.info(f"allow_qc_errors    : {allow_qc_errors}")
    logging.info("-" * 20)

    logging.info("⌛ Began extracting metadata")

    articles = json.load(open(articles_json, "r"))
    logging.info(f"Loaded {len(articles)} articles.")
    logging.debug(f"articles: {articles}")

    raw_metadata = {a["link"]: a["raw_contents"] for a in articles}
    logging.debug(f"raw_metadata: {raw_metadata}")

    response_text = llm_query(
        articles=raw_metadata,
        system_prompt_path=system_prompt_path,
        model=model,
        api_key=os.environ.get("GOOGLE_API_KEY"),
        llm_tools=[types.Tool(google_search=types.GoogleSearch())],
    )

    response_pass, response_fail = validate_llm_response(
        articles,
        response_text,
        allow_qc_errors,
        validate_metadata_response,
        STAGE,
    )

    save_validated_responses(
        articles,
        response_pass,
        response_fail,
        allow_qc_errors,
        STAGE,
        merge_key="link",
        expected_fields=["title", "summary", "doi"],
    )

    logging.info("✅ Done extracting metadata")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Extract DOIs from articles using Google Gemini. Outputs a TSV file with title and DOI."
    )

    parser = add_articles_json_argument(parser)
    parser = add_llm_arguments(parser)

    args = parser.parse_args()

    extract_metadata(
        args.articles_json, args.system_prompt_path, args.model, args.allow_qc_errors
    )

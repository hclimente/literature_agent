#!/usr/bin/env python
import argparse
import json
import logging
import os
import re

from google import genai
from google.genai import types

from utils import validate_json_response, handle_error

API_KEY = os.environ.get("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY environment variable not found. "
        "Did you remember to `nextflow secrets set GOOGLE_API_KEY '<YOUR-KEY'`?"
    )

client = genai.Client(api_key=API_KEY)


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


def split_by_qc(articles, metadata_pass, metadata_fail):
    """
    Split articles into those that passed and failed metadata QC.
    Args:
        articles (list): List of articles.
        metadata_pass (dict): Metadata that passed validation.
        metadata_fail (dict): Metadata that failed validation.
    Returns:
        tuple: (articles_pass, articles_fail)
    """
    articles_pass = []
    articles_fail = []

    for a in articles:
        url = a["link"]

        if url in metadata_fail:
            articles_fail.append(a)
        else:
            a["title"] = metadata_pass[url]["title"]
            a["summary"] = metadata_pass[url]["summary"]
            a["doi"] = metadata_pass[url]["doi"]
            articles_pass.append(a)

    return articles_pass, articles_fail


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
            if not re.match(r"^10\.\d{4,}/[-._;()/:\w\[\]]+$", d["doi"]):
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

    with open(system_prompt_path, "r") as f:
        system_instruction = f.read()

    response_text = client.models.generate_content(
        model=model,
        contents=f"These are the articles to extract the metadata from:\n{raw_metadata}",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            thinking_config=types.ThinkingConfig(include_thoughts=False),
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )

    response_text = response_text.text.strip()
    logging.info(f"Extracted Metadata: {response_text}")

    response = validate_json_response(
        response_text, "metadata_extraction", [a["link"] for a in articles]
    )
    response_pass, response_fail = validate_metadata_response(response, allow_qc_errors)
    logging.info(f"Validated Metadata for {len(response_pass)} articles.")
    logging.debug(f"Screening Pass: {response_pass}")
    logging.info(f"Invalid Metadata for {len(response_fail)} articles.")
    logging.debug(f"Screening Fail: {response_fail}")

    articles_pass, articles_fail = split_by_qc(articles, response_pass, response_fail)

    json.dump(articles_pass, open("pass_articles.json", "w"), indent=2)
    json.dump(articles_fail, open("failed_articles.json", "w"), indent=2)
    logging.info("✅ Done extracting metadata")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Extract DOIs from articles using Google Gemini. Outputs a TSV file with title and DOI."
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
        required=False,
        help="The path to the system prompt file.",
    )
    parser.add_argument(
        "--model",
        type=str,
        required=False,
        help="The model to use for metadata extraction. One of 'gemini-1.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.5-pro'.",
    )
    parser.add_argument(
        "--allow_qc_errors",
        type=bool,
        required=True,
        help="Whether to allow QC errors without failing the process.",
    )

    args = parser.parse_args()

    extract_metadata(
        args.articles_json, args.system_prompt_path, args.model, args.allow_qc_errors
    )

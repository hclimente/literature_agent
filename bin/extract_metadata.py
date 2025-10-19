#!/usr/bin/env python
import argparse
import logging
import os
from time import strptime

from google import genai
from google.genai import types

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
        text = text.replace(char, f"\\{char}")

    return text


def validate_date(date_string, format_string="%Y-%m-%d"):
    """
    Checks if a string adheres to the specified date format.

    Args:
        date_string (str): The date string to check.
        format_string (str): The expected date format (default is "%Y-%m-%d").
    Returns:
        None.
    """
    if not isinstance(date_string, str):
        raise TypeError(f"Expected string, got {type(date_string).__name__}.")
    try:
        strptime(date_string, format_string)
    except ValueError as e:
        raise ValueError(
            f"Date validation failed for string '{date_string}'. Reason: {e}"
        )


def extract_metadata(
    article_file: str, system_prompt_path: str = None, model: str = None
):
    """
    Extract metadata from an article using Google Gemini.

    Args:
        article_file (str): The path to the article file to process.
        system_prompt_path (str, optional): The path to the system prompt file.
        model (str, optional): The model to use for metadata extraction. One of 'gemini-1.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.5-pro'.
    Returns:
        None.
    """
    logging.info("-" * 20)
    logging.info("extract_metadata called with the following arguments:")
    logging.info(f"article_file       : {article_file}")
    logging.info(f"system_prompt_path : {system_prompt_path}")
    logging.info(f"model              : {model}")
    logging.info("-" * 20)

    logging.info("⌛ Began extracting metadata")

    with open(article_file, "r") as f:
        lines = f.readlines()

    logging.info(f"Article content read:\n{lines}")

    with open(system_prompt_path, "r") as f:
        system_instruction = f.read()

    response = client.models.generate_content(
        model=model,
        contents=f"This is the article to extract the metadata from:\n{lines}",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            thinking_config=types.ThinkingConfig(include_thoughts=False),
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )

    metadata = response.text.strip()
    logging.info(f"Extracted Metadata: {metadata}")

    title, journal_name, summary, link, date, doi = metadata.split("|")
    title = sanitize_text(title)
    summary = sanitize_text(summary)
    validate_date(date)

    with open("metadata.tsv", "w") as f:
        f.write(f"{title}\t{summary}\t{link}\t{journal_name}\t{date}\t{doi}\n")

    logging.info("✅ Done extracting metadata")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Extract DOIs from articles using Google Gemini. Outputs a TSV file with title and DOI."
    )
    parser.add_argument(
        "--article_file",
        type=str,
        required=True,
        help="The path to the article file to process.",
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

    args = parser.parse_args()

    extract_metadata(args.article_file, args.system_prompt_path, args.model)

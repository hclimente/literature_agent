#!/usr/bin/env python
import argparse
import logging
import os
import re

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


def validate_metadata_response(metadata: str) -> tuple[str, str, str]:
    """
    Validate and parse AI metadata response. It raises an error if validation fails.

    Args:
        metadata (str): The AI response containing pipe-separated metadata

    Returns:
        tuple[str, str, str]: (title, summary, doi)
    """
    if not metadata or not isinstance(metadata, str):
        logging.error("❌ AI returned empty or non-string response")
        raise

    parts = metadata.strip().split("|")
    if len(parts) != 3:
        logging.error(f"Expected 3 parts separated by |, got {len(parts)}: {metadata}")
        raise

    title, summary, doi = parts
    title, summary, doi = title.strip(), summary.strip(), doi.strip()

    # Validate individual fields
    if not title:
        logging.error("❌ Title cannot be empty")
        raise

    if not summary:
        logging.error("❌ Summary cannot be empty")
        raise

    # Validate DOI format if not NULL
    if doi != "NULL":
        # Basic DOI format: 10.xxxx/yyyyy
        if not re.match(r"^10\.\d+/.+", doi):
            logging.warning(f"⚠️ Invalid DOI format: '{doi}', setting to NULL")
            doi = "NULL"

    return title, summary, doi


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
        raw_metadata = f.read()

    lines = raw_metadata.strip().split("\n")
    journal_name = ""
    link = ""
    date = ""

    for line in lines:
        if line.startswith("Journal: "):
            journal_name = line.replace("Journal: ", "").strip()
        elif line.startswith("URL: "):
            link = line.replace("URL: ", "").strip()
        elif line.startswith("Date: "):
            date = line.replace("Date: ", "").strip()

    logging.info(f"Article raw medatada:\n{raw_metadata}")
    logging.info(f"Extracted - Journal: {journal_name}, URL: {link}, Date: {date}")

    with open(system_prompt_path, "r") as f:
        system_instruction = f.read()

    response = client.models.generate_content(
        model=model,
        contents=f"This is the article to extract the metadata from:\n{raw_metadata}",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            thinking_config=types.ThinkingConfig(include_thoughts=False),
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )

    metadata = response.text.strip()
    logging.info(f"Extracted Metadata: {metadata}")

    title, summary, doi = validate_metadata_response(metadata)
    title = sanitize_text(title)
    summary = sanitize_text(summary)

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

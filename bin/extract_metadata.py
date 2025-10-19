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


def extract_metadata(article_file: str):
    """
    Extract metadata from an article using Google Gemini.

    Args:
        article_file (str): The path to the article file to process.
    Returns:
        None.
    """
    logging.info("-" * 20)
    logging.info("extract_metadata called with the following arguments:")
    logging.info(f"article_file : {article_file}")
    logging.info("-" * 20)

    logging.info("⌛ Began extracting metadata")

    with open(article_file, "r") as f:
        lines = f.readlines()

    logging.info(f"Article content read:\n{lines}")

    system_instruction = """
You are a helpful assistant for that extracts metadata from academic articles.

Your task is to extract the following information:
- Title
- Journal Name
- Abstract/Summary
- Date of publication, in YYYY-MM-DD format. If the day is not available, use "01" as the day.
- URL, if possible within the journal's website
- DOI (Digital Object Identifier). In some cases, the DOI will be available in the summary or the URL of the article. In others, you may
need to look it up on Google Search or other academic databases.

Put the metadata in a single-line, pipe-separated (PSV) string. Use the following field order:

title|journal_name|summary|link|date|doi.

Do not include field names or delimiters other than the single pipe |. When a field is not available, use "NULL" as the value.

Example Output Format: From reference to reality: identifying noncanonical peptides|Trends in Genetics|The translation of genome...|https://www.cell.com/...|2025-08-04|10.1016/j.tig.2025.07.011
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
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
    date = strptime(date, "%Y-%m-%d")

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

    args = parser.parse_args()

    extract_metadata(args.article_file)

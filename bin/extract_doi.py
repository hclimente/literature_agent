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


def extract_doi(title: str, summary: str, link: str, journal_name: str):
    """
    Screens articles based on user research interests.

    Args:
        in_articles_tsv (str): Path to the input TSV file containing articles to screen.
        out_articles_tsv (str): Path to the output TSV file to store the screened articles
    Returns:
        None.
    """
    logging.info("-" * 20)
    logging.info("extract_doi called with the following arguments:")
    logging.info(f"title        : {title}")
    logging.info(f"summary      : {summary}")
    logging.info(f"link         : {link}")
    logging.info(f"journal_name : {journal_name}")
    logging.info("-" * 20)

    logging.info(f"⌛ Began extracting doi for article '{title}' from {journal_name}")

    system_instruction = """
You are a helpful assistant for that extracts DOIs from academic articles.

In some cases, the DOI will be available in the summary or the URL of the article. In others, you may
need to look it up on Google Search or other academic databases.

Respond only with the DOI of the article, or "none" if you cannot find it.
"""

    prompt = (
        f"Title: {title}\nJournal: {journal_name}\nSummary: {summary}\nURL: {link}\n"
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=f"This is the article to extract the DOI from:\n{prompt}",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            thinking_config=types.ThinkingConfig(include_thoughts=True),
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )

    doi = response.text.strip().lower()
    logging.info(f"doi: {doi}")

    with open("doi.txt", "w") as f:
        regex_match = re.match(r"^10.\d{4,9}/[-._;()/:A-Z0-9]+$", doi, re.IGNORECASE)
        if doi == "none" or regex_match is None:
            logging.error("❌ Unexpected doi")
            f.write("NULL")
        else:
            f.write(doi)

    for part in response.candidates[0].content.parts:
        if not part.text:
            continue
        if part.thought:
            logging.info(f"Thought: {part.text}")

    logging.info(f"✅ Done extracting doi for article '{title}' from {journal_name}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Extract DOIs from articles using Google Gemini. Outputs a TSV file with title and DOI."
    )
    parser.add_argument(
        "--title",
        type=str,
        required=True,
        help="The path to the input TSV file containing the articles to screen.",
    )
    parser.add_argument(
        "--summary",
        type=str,
        required=True,
        help="The path to the output TSV file to store the screened articles.",
    )
    parser.add_argument(
        "--link",
        type=str,
        required=True,
        help="The path to the output TSV file to store the screened articles.",
    )
    parser.add_argument(
        "--journal_name",
        type=str,
        required=True,
        help="The path to the input TSV file containing the articles to screen.",
    )

    args = parser.parse_args()

    extract_doi(args.title, args.summary, args.link, args.journal_name)

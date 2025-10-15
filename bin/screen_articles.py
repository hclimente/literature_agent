#!/usr/bin/env python
import argparse
import os

from google import genai
from google.adk.agents.llm_agent import Agent

API_KEY = os.environ.get("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY environment variable not found. "
        "Did you remember to `nextflow secrets set GOOGLE_API_KEY '<YOUR-KEY'`?"
    )

genai.Client(api_key=API_KEY)
root_agent = Agent(
    model="gemini-2.5-flash",
    name="root_agent",
    description="A helpful assistant for getting scientific articles.",
    instruction="Fetch the latest scientific articles from an RSS feed and provide concise summaries.",
    tools=[],
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch articles from RSS feeds and store them in a database."
    )
    parser.add_argument(
        "--in_articles_tsv",
        type=str,
        required=True,
        help="The path to the input TSV file containing the articles to screen.",
    )
    parser.add_argument(
        "--out_articles_tsv",
        type=str,
        required=True,
        help="The path to the output TSV file to store the screened articles.",
    )

    args = parser.parse_args()

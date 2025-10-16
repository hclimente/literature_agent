#!/usr/bin/env python
import argparse
import os
import requests

from google import genai
from google.adk.agents.llm_agent import Agent

API_KEY = os.environ.get("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY environment variable not found. "
        "Did you remember to `nextflow secrets set GOOGLE_API_KEY '<YOUR-KEY'`?"
    )

genai.Client(api_key=API_KEY)


# Tools
def get_abstract_from_doi(doi: str) -> str:
    """
    Fetches the abstract for a given DOI using the Crossref API.

    Args:
        doi: The DOI string (e.g., '10.1016/j.cell.2020.10.015').

    Returns:
        The abstract text as a string, or an informative message if not found.
    """
    # Crossref API endpoint for a single work (article)
    url = f"https://api.crossref.org/works/{doi}"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)

        data = response.json()

        # Crossref's JSON response structure
        message = data.get("message", {})

        # The abstract is typically stored under the 'abstract' key
        abstract = message.get("abstract")

        if abstract:
            # Abstracts often contain XML tags (e.g., <jats:p>).
            # We need to strip these out for clean text.
            import re

            clean_abstract = re.sub(r"<[^>]*>", "", abstract)
            return clean_abstract.strip()
        else:
            return f"Abstract not found for DOI: {doi}. (Data available but abstract field missing.)"

    except requests.exceptions.RequestException as e:
        # Handles connection issues, timeouts, or bad HTTP status codes
        return f"Error fetching data for DOI {doi}: {e}"


agent = Agent(
    model="gemini-2.5-flash",
    name="root_agent",
    description="A helpful assistant for getting scientific articles.",
    instruction=(
        "You are a helpful assistant for screening scientific articles. "
        "Your ONLY job is to determine if the provided article is worth reading, using as little information as possible."
        "You must answer ONLY 'yes' or 'no'. No other text, punctuation, or explanation is permitted.",
    ),
    tools=[get_abstract_from_doi],
)


def screen_articles(in_articles_tsv: str, out_articles_tsv: str):
    with open(in_articles_tsv, "r") as F_IN, open(out_articles_tsv, "w") as F_OUT:
        for line in F_IN:
            title, link, summary, date = line.strip().split("\t")
            prompt = f"Title: {title}\nSummary: {summary}\n"
            response = agent.chat(prompt)

            if response.text.strip().lower() == "yes":
                F_OUT.write(f"{title}\t{link}\t{response.text}\t{date}\n")
            if response.text.strip().lower() not in ["yes", "no"]:
                print(
                    f"Warning: Unexpected response from agent for article '{title}': {response.text}"
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

    screen_articles(args.in_articles_tsv, args.out_articles_tsv)

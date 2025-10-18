#!/usr/bin/env python
import argparse
import logging
import os

from google import genai
from google.genai import types

from tools.metadata_tools import get_abstract_from_doi, springer_get_abstract_from_doi

API_KEY = os.environ.get("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY environment variable not found. "
        "Did you remember to `nextflow secrets set GOOGLE_API_KEY '<YOUR-KEY'`?"
    )

client = genai.Client(api_key=API_KEY)


def prioritize_articles(
    title: str, journal_name: str, summary: str, doi: str, research_interests_path: str
):
    """
    Prioritizes articles based on user research interests.

    Args:
        title (str): The title of the article to screen.
        journal_name (str): The journal name of the article to screen.
        summary (str): The summary of the article to screen.
        doi (str): The DOI of the article to screen.
        research_interests_path (str): The path to a text file containing the user's research interests.
    Returns:
        None. Writes the screening decision to 'decision.txt'.
    """
    logging.info("-" * 20)
    logging.info("screen_article called with the following arguments:")
    logging.info(f"title                   : {title}")
    logging.info(f"journal_name            : {journal_name}")
    logging.info(f"summary                 : {summary}")
    logging.info(f"doi                     : {doi}")
    logging.info(f"research_interests_path : {research_interests_path}")
    logging.info("-" * 20)

    logging.info(f"⌛ Began prioritizing article '{title}' from {journal_name}")

    with open(research_interests_path, "r") as F:
        research_interests = F.read().strip()

    system_instruction = f"""
You are a helpful assistant for prioritizing scientific articles. Your job is to score which articles
are worth reading by the user using a 5-point scale, where 0 means low priority and 5 means high priority.

Note that the articles have already been screened for relevance. An article receiving a 0 might still be worth
reading given infinite time; 3 is quite generous; 5 is a must-read, urgently.

Use as much information as you need from the article; retrieving additional information when needed.

Here is a description of the user's interests:\n{research_interests}\n

You must answer ONLY an integer between 0 and 5. No other text, punctuation, or explanation.

Here is the article to prioritize:
    """
    prompt = (
        f"Title: {title}\nJournal: {journal_name}\nSummary: {summary}\ndoi: {doi}\n"
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=f"Here is the article to screen:{prompt}",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            thinking_config=types.ThinkingConfig(include_thoughts=True),
            tools=[get_abstract_from_doi, springer_get_abstract_from_doi],
        ),
    )

    decision = response.text.strip().lower()
    logging.info(f"Decision: {decision}")

    with open("priority.txt", "w") as f:
        if decision not in [str(x) for x in range(0, 6)]:
            logging.error("❌ Unexpected decision")
            f.write("NULL")
        else:
            f.write(decision)

    for part in response.candidates[0].content.parts:
        if not part.text:
            continue
        if part.thought:
            logging.info(f"Thought: {part.text}")

    logging.info(f"✅ Done prioritizing article '{title}' from {journal_name}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Prioritize articles based on user research interests."
    )
    parser.add_argument(
        "--title",
        type=str,
        required=True,
        help="The title of the article to screen.",
    )
    parser.add_argument(
        "--journal_name",
        type=str,
        required=True,
        help="The journal name of the article to screen.",
    )
    parser.add_argument(
        "--summary",
        type=str,
        required=True,
        help="The summary of the article to screen.",
    )
    parser.add_argument(
        "--doi",
        type=str,
        required=True,
        help="The DOI of the article to screen.",
    )
    parser.add_argument(
        "--research_interests_path",
        type=str,
        required=True,
        help="The path to a text file containing the user's research interests.",
    )

    args = parser.parse_args()

    prioritize_articles(
        args.title,
        args.journal_name,
        args.summary,
        args.doi,
        args.research_interests_path,
    )

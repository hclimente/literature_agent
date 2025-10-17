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
    in_articles_tsv: str, user_prompt_path: str, out_articles_tsv: str
):
    """
    Screens articles based on user research interests.

    Args:
        in_articles_tsv (str): Path to the input TSV file containing articles to screen.
        user_prompt_path (str): Path to the text file containing the user's research interests.
        out_articles_tsv (str): Path to the output TSV file to store the screened articles
    Returns:
        None
    """
    logging.info("-" * 20)
    logging.info("prioritize_articles called with the following arguments:")
    logging.info(f"in_articles_tsv  : {in_articles_tsv}")
    logging.info(f"user_prompt_path : {user_prompt_path}")
    logging.info(f"out_articles_tsv : {out_articles_tsv}")
    logging.info("-" * 20)

    with open(user_prompt_path, "r") as F:
        user_prompt = F.read().strip()

    with open(in_articles_tsv, "r") as F_IN, open(out_articles_tsv, "w") as F_OUT:
        F_IN.readline()  # skip header
        F_OUT.write("title\tjournal_name\tlink\tdate\n")

        for line in F_IN:
            line = line.strip()

            if not line:
                continue

            title, journal_name, link, _ = line.split("\t")

            logging.info(f"⌛ Began prioritizing article '{title}' from {journal_name}")

            prompt = f"Title: {title}\nJournal: {journal_name}\nURL: {link}\n"
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"""
You are a helpful assistant for prioritizing scientific articles. Your job is to score which articles
are worth reading by the user using a 5-point scale, where 0 means low priority and 5 means high priority.

Note that the articles have already been screened for relevance. An article receiving a 0 might still be worth
reading given infinite time; 3 is quite generous; 5 is a must-read, urgently.

Use as much information as you need from the article; retrieving additional information when needed.

Here is a description of the user's interests:\n{user_prompt}\n

You must answer ONLY an integer between 0 and 5. No other text, punctuation, or explanation.

Here is the article to prioritize:\n{prompt}"
                """,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(include_thoughts=True),
                    tools=[get_abstract_from_doi, springer_get_abstract_from_doi],
                ),
            )

            decision = response.text.strip().lower()
            logging.info(f"Decision: {decision}")

            if decision not in [str(x) for x in range(0, 6)]:
                logging.error("❌ Unexpected decision")
            else:
                F_OUT.write(f"{title}\t{journal_name}\t{decision}\n")

            for part in response.candidates[0].content.parts:
                if not part.text:
                    continue
                if part.thought:
                    logging.info(f"Thought: {part.text}")

            logging.info(f"✅ Done prioritizing article '{title}' from {journal_name}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Fetch articles from RSS feeds and store them in a database."
    )
    parser.add_argument(
        "--in_articles_tsv",
        type=str,
        required=True,
        help="The path to the input TSV file containing the articles to prioritize.",
    )
    parser.add_argument(
        "--research_interests_path",
        type=str,
        required=True,
        help="The path to a text file containing the user's research interests.",
    )
    parser.add_argument(
        "--out_articles_tsv",
        type=str,
        required=True,
        help="The path to the output TSV file to store the article priorities.",
    )

    args = parser.parse_args()

    prioritize_articles(
        args.in_articles_tsv, args.research_interests_path, args.out_articles_tsv
    )

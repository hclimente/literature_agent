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


def screen_articles(in_articles_tsv: str, user_prompt_path: str, out_articles_tsv: str):
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
    logging.info("screen_articles called with the following arguments:")
    logging.info(f"in_articles_tsv  : {in_articles_tsv}")
    logging.info(f"user_prompt_path : {user_prompt_path}")
    logging.info(f"out_articles_tsv : {out_articles_tsv}")
    logging.info("-" * 20)

    with open(user_prompt_path, "r") as F:
        user_prompt = F.read().strip()

    with open(in_articles_tsv, "r") as F_IN, open(out_articles_tsv, "w") as F_OUT:
        F_OUT.write("title\tjournal_name\tlink\tdate\n")

        for line in F_IN:
            title, journal_name, link, summary, date = line.strip().split("\t")

            logging.info(f"⌛ Began screening article '{title}' from {journal_name}")

            prompt = f"Title: {title}\nJournal: {journal_name}\nSummary: {summary}\n"
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=(
                    "You are a helpful assistant for screening scientific articles. Your ONLY job is to "
                    "screen which articles could be worth reading by the user. Since using tools incurs "
                    "in costly API calls, they should be used only when absolutely necessary. "
                    f"Here is a description of the user's interests:\n{user_prompt}\n"
                    "You must answer ONLY 'yes' or 'no'. No other text, punctuation, or explanation is "
                    f"permitted. Here is the article to screen:\n{prompt}"
                ),
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(include_thoughts=True),
                    tools=[get_abstract_from_doi, springer_get_abstract_from_doi],
                ),
            )

            decision = response.text.strip().lower()
            logging.info(f"Decision: {decision}")

            if decision not in ["yes", "no"]:
                logging.error("❌ Unexpected decision")
            elif decision == "yes":
                F_OUT.write(f"{title}\t{journal_name}\t{link}\t{date}\n")

            for part in response.candidates[0].content.parts:
                if not part.text:
                    continue
                if part.thought:
                    logging.info(f"Thought: {part.text}")

            logging.info(f"✅ Done screening article '{title}' from {journal_name}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

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
        "--research_interests_path",
        type=str,
        required=True,
        help="The path to a text file containing the user's research interests.",
    )
    parser.add_argument(
        "--out_articles_tsv",
        type=str,
        required=True,
        help="The path to the output TSV file to store the screened articles.",
    )

    args = parser.parse_args()

    screen_articles(
        args.in_articles_tsv, args.research_interests_path, args.out_articles_tsv
    )

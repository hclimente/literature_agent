#!/usr/bin/env python
import argparse
import logging
import os

from google import genai
from google.genai import types

from tools.metadata_tools import get_abstract_from_doi, springer_get_abstract_from_doi
from utils import ValidationError

API_KEY = os.environ.get("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY environment variable not found. "
        "Did you remember to `nextflow secrets set GOOGLE_API_KEY '<YOUR-KEY'`?"
    )

client = genai.Client(api_key=API_KEY)


def validate_screening_response(response_text: str) -> str:
    """
    Validate AI screening response. It raises an error if validation fails.

    Args:
        response_text (str): The AI response for screening decision

    Returns:
        str: "true" or "false"
    """
    if not response_text or not isinstance(response_text, str):
        raise ValidationError(
            "screening", response_text, "Empty or non-string response."
        )

    # allow for some common variations
    decision_mappings = {
        "true": "true",
        "true.": "true",
        '"true"': "true",
        "'true'": "true",
        "false": "false",
        "false.": "false",
        '"false"': "false",
        "'false'": "false",
    }

    decision = response_text.strip().lower()

    try:
        return decision_mappings[decision]
    except KeyError:
        raise ValidationError(
            "screening",
            decision,
            "Invalid screening value. Expected 'true' or 'false'.",
        )


def screen_article(
    title: str,
    journal_name: str,
    summary: str,
    doi: str,
    system_prompt_path: str,
    research_interests_path: str,
    model: str,
):
    """
    Screens articles based on user research interests.

    Args:
        title (str): The title of the article to screen.
        journal_name (str): The journal name of the article to screen.
        summary (str): The summary of the article to screen.
        doi (str): The DOI of the article to screen.
        system_prompt_path (str): The path to the system prompt file.
        research_interests_path (str): The path to a text file containing the user's research interests.
        model (str): The model to use for screening. One of 'gemini-1.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.5-pro'.
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

    logging.info(f"⌛ Began screening article '{title}' from {journal_name}")

    logging.info("Began reading system prompt...")
    with open(system_prompt_path, "r") as f:
        system_instruction = f.read().strip()
    logging.info("Done reading system prompt.")

    logging.info("Began reading research interests...")
    with open(research_interests_path, "r") as F:
        research_interests = F.read().strip()
    logging.info("Done reading research interests.")

    system_instruction = system_instruction.format(
        research_interests=research_interests
    )
    logging.info(f"System prompt: {system_instruction}")

    prompt = f"""
Here is the article to screen:
    Title: {title}
    Journal: {journal_name}
    Summary: {summary}
    doi: {doi}
"""
    logging.info(f"User prompt: {prompt}")

    response = client.models.generate_content(
        model=model,
        contents=f"Here is the article to screen:{prompt}",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            thinking_config=types.ThinkingConfig(include_thoughts=True),
            tools=[get_abstract_from_doi, springer_get_abstract_from_doi],
        ),
    )

    decision = validate_screening_response(response.text)
    logging.info(f"Decision: {decision}")

    with open("decision.txt", "w") as f:
        f.write(decision)

    for part in response.candidates[0].content.parts:
        if not part.text:
            continue
        if part.thought:
            logging.info(f"Thought: {part.text}")

    logging.info(f"✅ Done screening article '{title}' from {journal_name}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Screen articles based on user research interests."
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
        "--system_prompt_path",
        type=str,
        required=True,
        help="The path to the system prompt file.",
    )
    parser.add_argument(
        "--research_interests_path",
        type=str,
        required=True,
        help="The path to a text file containing the user's research interests.",
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="The model to use for screening. One of 'gemini-1.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.5-pro'.",
    )

    args = parser.parse_args()

    screen_article(
        args.title,
        args.journal_name,
        args.summary,
        args.doi,
        args.system_prompt_path,
        args.research_interests_path,
        args.model,
    )

#!/usr/bin/env python
import argparse
import json
import logging
import os

from google import genai
from google.genai import types

from tools.metadata_tools import get_abstract_from_doi, springer_get_abstract_from_doi
from utils import validate_json_response, ValidationError

API_KEY = os.environ.get("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY environment variable not found. "
        "Did you remember to `nextflow secrets set GOOGLE_API_KEY '<YOUR-KEY'`?"
    )

client = genai.Client(api_key=API_KEY)


def validate_screening_response(response: str) -> str:
    """
    Validate AI screening response. It raises an error if validation fails.

    Args:
        response (str): The parsed AI response for screening decision

    Returns:
        str: "true" or "false"
    """
    for d in response.values():
        if not d or not isinstance(d, dict):
            raise ValidationError("screening", d, "Empty or non-dict response.")

        if not all(k in d for k in ["decision", "reasoning"]):
            raise ValidationError(
                "screening",
                d,
                "Missing keys (decision and/or reasoning).",
            )

        decision = d["decision"]

        if isinstance(decision, bool):
            decision = "true" if decision else "false"
        else:
            if not isinstance(decision, str):
                raise ValidationError(
                    "screening",
                    decision,
                    "Screening decision should be a string.",
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

            decision = decision.strip().lower()

            try:
                decision = decision_mappings[decision]
            except KeyError:
                raise ValidationError(
                    "screening",
                    decision,
                    "Invalid screening value. Expected 'true' or 'false'.",
                )

    return response


def screen_articles(
    articles_json: str,
    system_prompt_path: str,
    research_interests_path: str,
    model: str,
):
    """
    Screens articles based on user research interests.

    Args:
        articles_json (str):
        system_prompt_path (str): The path to the system prompt file.
        research_interests_path (str): The path to a text file containing the user's research interests.
        model (str): The model to use for screening. One of 'gemini-1.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.5-pro'.
    Returns:
        None. Writes the screening decision to 'decision.txt'.
    """
    logging.info("-" * 20)
    logging.info("screen_articles called with the following arguments:")
    logging.info(f"articles_json           : {articles_json}")
    logging.info(f"system_prompt_path      : {system_prompt_path}")
    logging.info(f"research_interests_path : {research_interests_path}")
    logging.info(f"model                   : {model}")
    logging.info("-" * 20)

    articles = json.load(open(articles_json, "r"))
    logging.info(f"Loaded {len(articles)} articles.")
    logging.debug(f"articles: {articles}")

    logging.info("Began removing articles with no doi...")
    articles = [a for a in articles if a["doi"] != "NULL"]
    logging.info("Done removing articles with no doi.")

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
    logging.debug(f"System prompt: {system_instruction}")

    prompt = f"Here are the articles to screen: {articles}"
    logging.debug(f"User prompt: {prompt}")

    response_text = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            thinking_config=types.ThinkingConfig(include_thoughts=False),
            tools=[get_abstract_from_doi, springer_get_abstract_from_doi],
        ),
    )

    response_text = response_text.text.strip()
    response = validate_json_response(
        response_text, "screening", [a["doi"] for a in articles]
    )
    decisions = validate_screening_response(response)
    for a in articles:
        doi = a["doi"]
        a["screen_decision"] = decisions[doi]["decision"]
        a["screen_reasoning"] = decisions[doi]["reasoning"]

    json.dump(articles, open("screened_articles.json", "w"), indent=2)

    logging.info("✅ Done screening articles.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Screen articles based on user research interests."
    )
    parser.add_argument(
        "--articles_json",
        type=str,
        required=True,
        help="The path to the JSON files containing the articles to process.",
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

    screen_articles(
        args.articles_json,
        args.system_prompt_path,
        args.research_interests_path,
        args.model,
    )

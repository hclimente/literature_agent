#!/usr/bin/env python
import argparse
import json
import logging
import os

from google import genai
from google.genai import types

from tools.metadata_tools import get_abstract_from_doi, springer_get_abstract_from_doi
from utils import validate_json_response

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
        tuple: (articles_pass, articles_fail)
    """

    articles_pass = {}
    articles_fail = {}

    for k, d in response.items():
        if not d or not isinstance(d, dict):
            d["screening_error"] = "Empty or non-dict response."
            articles_fail[k] = d
            continue

        if not all(k in d for k in ["decision", "reasoning"]):
            d["screening_error"] = "Missing keys (decision and/or reasoning)."
            articles_fail[k] = d
            continue

        decision = d["decision"]

        if isinstance(decision, bool):
            decision = "true" if decision else "false"
        else:
            if not isinstance(decision, str):
                d["screening_error"] = "Screening decision should be a string."
                articles_fail[k] = d
                continue

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
                d["screening_error"] = (
                    "Invalid screening value. Expected 'true' or 'false'."
                )
                articles_fail[k] = d
                continue

        d["decision"] = decision
        articles_pass[k] = d

    return articles_pass, articles_fail


def split_by_qc(articles, qc_pass, qc_fail):
    """
    Split articles into those that passed and failed screening QC.
    Args:
        articles (list): List of articles.
        qc_pass (dict): Metadata that passed validation.
        qc_faill (dict): Metadata that failed validation.
    Returns:
        tuple: (articles_pass, articles_fail)
    """
    articles_pass = []
    articles_fail = []

    for a in articles:
        doi = a["doi"]

        if doi in qc_fail:
            articles_fail.append(a)
        else:
            a["screening_decision"] = qc_pass[doi]["decision"]
            a["screening_reasoning"] = qc_pass[doi]["reasoning"]
            articles_pass.append(a)

    return articles_pass, articles_fail


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
    response_pass, response_fail = validate_screening_response(response)
    logging.info(f"Validated Screening for {len(response_pass)} articles.")
    logging.debug(f"Screening Pass: {response_pass}")
    logging.info(f"Invalid Screening for {len(response_fail)} articles.")
    logging.debug(f"Screening Fail: {response_fail}")

    articles_pass, articles_fail = split_by_qc(articles, response_pass, response_fail)
    json.dump(articles_pass, open("pass_articles.json", "w"), indent=2)
    json.dump(articles_fail, open("failed_articles.json", "w"), indent=2)
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

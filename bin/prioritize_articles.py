#!/usr/bin/env python
import argparse
import json
import logging
import os

from google import genai
from google.genai import types

from tools.metadata_tools import get_abstract_from_doi, springer_get_abstract_from_doi
from utils import validate_json_response, handle_error

API_KEY = os.environ.get("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY environment variable not found. "
        "Did you remember to `nextflow secrets set GOOGLE_API_KEY '<YOUR-KEY'`?"
    )

client = genai.Client(api_key=API_KEY)


def validate_priority_response(response: str, allow_errors: bool) -> str:
    """
    Validate AI prioritization response. It raises an error if validation fails.

    Args:
        response_text (str): The AI response for priority decision
        allow_errors (bool): Whether to allow errors without failing the process.

    Returns:
        tuple: (articles_pass, articles_fail)
    """

    articles_pass = {}
    articles_fail = {}

    for k, d in response.items():
        if not d or not isinstance(d, dict):
            articles_fail[k] = handle_error(
                d, "Empty or non-dict response.", "priority", allow_errors
            )
            continue

        if not all(k in d for k in ["decision", "reasoning"]):
            articles_fail[k] = handle_error(
                d,
                "Missing keys (decision and/or reasoning).",
                "priority",
                allow_errors,
            )
            continue

        priority = d["decision"]

        if not priority or not isinstance(priority, str):
            articles_fail[k] = handle_error(
                d, "Empty or non-string response.", "priority", allow_errors
            )
            continue

        # allow for some common variations
        priority_mappings = {
            "low": "low",
            "low.": "low",
            '"low"': "low",
            "'low'": "low",
            "medium": "medium",
            "medium.": "medium",
            '"medium"': "medium",
            "'medium'": "medium",
            "high": "high",
            "high.": "high",
            '"high"': "high",
            "'high'": "high",
        }

        priority = priority.strip().lower()

        try:
            priority = priority_mappings[priority]
        except KeyError:
            articles_fail[k] = handle_error(
                d,
                "Invalid priority value. Expected 'low', 'medium', or 'high'.",
                "priority",
                allow_errors,
            )
            continue

        d["decision"] = priority
        articles_pass[k] = d

    return articles_pass, articles_fail


def split_by_qc(articles, qc_pass, qc_fail):
    """
    Split articles into those that passed and failed priotization QC.
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

        if doi in qc_pass:
            a["priority_decision"] = qc_pass[doi]["decision"]
            a["priority_reasoning"] = qc_pass[doi]["reasoning"]
            articles_pass.append(a)
        else:
            articles_fail.append(a)

    return articles_pass, articles_fail


def prioritize_articles(
    articles_json: str,
    system_prompt_path: str,
    research_interests_path: str,
    model: str,
    allow_qc_errors: bool,
):
    """
    Prioritizes articles based on user research interests.

    Args:
        articles_json (str):
        system_prompt_path (str): The path to the system prompt file.
        research_interests_path (str): The path to a text file containing the user's research interests.
        model (str): The model to use for screening. One of 'gemini-1.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.5-pro'.
        allow_qc_errors (bool): Whether to allow QC errors without failing the process.
    Returns:
        None. Writes the screening decision to 'decision.txt'.
    """
    logging.info("-" * 20)
    logging.info("screen_article called with the following arguments:")
    logging.info(f"articles_json           : {articles_json}")
    logging.info(f"system_prompt_path      : {system_prompt_path}")
    logging.info(f"research_interests_path : {research_interests_path}")
    logging.info(f"model                   : {model}")
    logging.info("-" * 20)

    articles = json.load(open(articles_json, "r"))
    logging.info(f"Loaded {len(articles)} articles.")
    logging.debug(f"articles: {articles}")

    logging.info("Began removing articles with no doi or screened out...")
    articles = [a for a in articles if a["doi"] != "NULL" and a["screening_decision"]]
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

    prompt = f"Here are the articles to prioritize:{articles}"
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
    logging.debug(f"Response: {response_text}")
    response = validate_json_response(
        response_text, "prioritization", [a["doi"] for a in articles]
    )
    response_pass, response_fail = validate_priority_response(response, allow_qc_errors)
    logging.info(f"Validated Priority for {len(response_pass)} articles.")
    logging.debug(f"Priority Pass: {response_pass}")
    logging.info(f"Invalid Priority for {len(response_fail)} articles.")
    logging.debug(f"Priority Fail: {response_fail}")

    articles_pass, articles_fail = split_by_qc(articles, response_pass, response_fail)
    json.dump(articles_pass, open("priority_pass.json", "w"), indent=2)
    json.dump(articles_fail, open("priority_fail.json", "w"), indent=2)
    logging.info("✅ Done prioritizing articles.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Prioritize articles based on user research interests."
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
        help="The model to use for prioritization. One of 'gemini-1.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.5-pro'.",
    )
    parser.add_argument(
        "--allow_qc_errors",
        type=bool,
        required=True,
        help="Whether to allow QC errors without failing the process.",
    )

    args = parser.parse_args()

    prioritize_articles(
        args.articles_json,
        args.system_prompt_path,
        args.research_interests_path,
        args.model,
        args.allow_qc_errors,
    )

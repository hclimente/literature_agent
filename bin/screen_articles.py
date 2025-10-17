#!/usr/bin/env python
import argparse
import logging
import os
import requests
import xml.etree.ElementTree as ET

from google import genai
from google.genai import types

API_KEY = os.environ.get("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY environment variable not found. "
        "Did you remember to `nextflow secrets set GOOGLE_API_KEY '<YOUR-KEY'`?"
    )

client = genai.Client(api_key=API_KEY)


# Tools
def get_abstract_from_doi(doi: str, email: str = os.environ.get("USER_EMAIL")) -> str:
    """
    Retrieves the abstract of a publication from its DOI.

    Args:
        doi (str): The Digital Object Identifier (DOI) of the article.
        email: Your email address, required by NCBI's API usage policy. Defaults to the USER_EMAIL
        environment variable.

    Returns:
        The abstract text as a string, or an error message if retrieval fails.
    """
    logging.info("-" * 20)
    logging.info("get_abstract_from_doi called with the following arguments:")
    logging.info(f"doi   : {doi}")
    logging.info(f"email : {email[0:3]}****@{email.split('@')[-1]}")
    logging.info("-" * 20)

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    # --- 1. ESearch: Convert DOI to PMID (Uses XML) ---
    esearch_url = (
        f"{BASE_URL}esearch.fcgi?db=pubmed&term={doi}[doi]&retmode=xml&email={email}"
    )

    try:
        logging.info("⌛ Began retrieving PMID from DOI...")
        esearch_response = requests.get(esearch_url, timeout=10)
        esearch_response.raise_for_status()

        # Parse ESearch XML
        root_esearch = ET.fromstring(esearch_response.content)
        id_element = root_esearch.find("./IdList/Id")

        if id_element is None or not id_element.text:
            return f"Error: No PMID found for DOI: {doi}."

        pmid = id_element.text
        logging.info(f"Retrieved PMID: {pmid}")
        logging.info("✅ Done retrieving PMID from DOI")

        logging.info("⌛ Began retrieving abstract from PMID...")
        # --- 2. EFetch: Retrieve Full Record as XML (Per your request) ---
        efetch_url = f"{BASE_URL}efetch.fcgi?db=pubmed&id={pmid}&retmode=xml&rettype=abstract&email={email}"

        efetch_response = requests.get(efetch_url, timeout=10)
        efetch_response.raise_for_status()

        # --- 3. Parse EFetch XML to extract Abstract Text ---
        # The PubMed XML structure is hierarchical. Abstract text is typically in
        # //MedlineCitation/Article/Abstract/AbstractText
        root_efetch = ET.fromstring(efetch_response.content)

        # Note: The 'AbstractText' tag can be a list of elements (e.g., background, methods, results)
        abstract_parts = root_efetch.findall(".//AbstractText")

        if not abstract_parts:
            error_message = f"PMID {pmid} found, but no AbstractText tags present."
            logging.error(f"❌ {error_message}")
            return error_message

        # Concatenate multiple parts if present (common for structured abstracts)
        abstract_text = "\n\n".join(
            "".join(part.itertext()).strip() for part in abstract_parts
        )

        # A common issue is a missing <Abstract> tag, in which case the text will be empty.
        if not abstract_text:
            error_message = (
                f"PMID {pmid} found, but the abstract text was empty after parsing."
            )
            logging.error(f"❌ {error_message}")
            return error_message

        logging.info(f"Retrieved Abstract: {abstract_text[:60]}...")
        logging.info("✅ Done retrieving abstract from PMID")

        return abstract_text

    except requests.exceptions.RequestException as e:
        return f"Network or API Error: {e}"
    except ET.ParseError as e:
        return f"Parsing Error: Failed to parse XML response. {e}"


def springer_get_abstract_from_doi(
    doi: str, api_key: str = os.environ.get("SPRINGER_META_API_KEY")
) -> str | None:
    """
    Retrieves the abstract for an article from a Springer journal using its DOI.

    Args:
        doi (str): The Digital Object Identifier (DOI) of the article.
        api_key (str): Your Springer Meta API key.

    Returns:
        The abstract text as a string, or an error message if retrieval fails.
    """
    logging.info("-" * 20)
    logging.info("springer_get_abstract_from_doi called with the following arguments:")
    logging.info(f"doi     : {doi}")
    logging.info(f"api_key : {api_key[0:3]}****")
    logging.info("-" * 20)

    base_url = "https://api.springernature.com/meta/v2/json"

    params = {"q": f"doi:{doi}", "api_key": api_key}

    try:
        logging.info("⌛ Began retrieving abstract from Springer API...")
        response = requests.get(base_url, params=params, timeout=10)
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()

        data = response.json()

        # Check if any records were returned
        if not data.get("records"):
            warn_message = f"No records found for DOI: {doi}"
            logging.warning(f"⚠️ {warn_message}")
            return warn_message

        # Extract the abstract from the first record
        # The abstract can contain HTML tags like <p>, <i>, etc.
        abstract = data["records"][0].get("abstract")
        if not abstract:
            warn_message = f"No abstract found for DOI: {doi}"
            logging.warning(f"⚠️ {warn_message}")
            return warn_message

        logging.info(f"Retrieved Abstract: {abstract[:60]}...")
        logging.info("✅ Done retrieving abstract from Springer API")

        return abstract

    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error occurred: {http_err}"
        logging.error(f"❌ {error_message}")
        return error_message
    except requests.exceptions.RequestException as req_err:
        error_message = f"Request error occurred: {req_err}"
        logging.error(f"❌ {error_message}")
        return error_message
    except (KeyError, IndexError) as json_err:
        error_message = f"Error parsing JSON response: {json_err}"
        logging.error(f"❌ {error_message}")
        return error_message


# Main screening function
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

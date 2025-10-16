#!/usr/bin/env python
import argparse
import os
import requests
import xml.etree.ElementTree as ET

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
def get_abstract_from_doi(doi: str, email: str = os.environ.get("USER_EMAIL")) -> str:
    """
    Retrieves the abstract of a publication from its DOI.

    Args:
        doi: The Digital Object Identifier (e.g., "10.1038/nature1718043").
        email: Your email address, required by NCBI's API usage policy. Defaults to the USER_EMAIL
        environment variable.

    Returns:
        The abstract text as a string, or an error message if retrieval fails.
    """
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    # --- 1. ESearch: Convert DOI to PMID (Uses XML) ---
    esearch_url = (
        f"{BASE_URL}esearch.fcgi?db=pubmed&term={doi}[doi]&retmode=xml&email={email}"
    )

    try:
        esearch_response = requests.get(esearch_url, timeout=10)
        esearch_response.raise_for_status()

        # Parse ESearch XML
        root_esearch = ET.fromstring(esearch_response.content)
        id_element = root_esearch.find("./IdList/Id")

        if id_element is None or not id_element.text:
            return f"Error: No PMID found for DOI: {doi}."

        pmid = id_element.text

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
            return f"PMID {pmid} found, but could not locate AbstractText tag in XML."

        # Concatenate multiple parts if present (common for structured abstracts)
        abstract_text = "\n\n".join(
            "".join(part.itertext()).strip() for part in abstract_parts
        )

        # A common issue is a missing <Abstract> tag, in which case the text will be empty.
        if not abstract_text:
            return f"PMID {pmid} found, but the abstract text was empty after parsing."

        return abstract_text

    except requests.exceptions.RequestException as e:
        return f"Network or API Error: {e}"
    except ET.ParseError as e:
        return f"Parsing Error: Failed to parse XML response. {e}"


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
        # required=True,
        help="The path to the input TSV file containing the articles to screen.",
    )
    parser.add_argument(
        "--out_articles_tsv",
        type=str,
        # required=True,
        help="The path to the output TSV file to store the screened articles.",
    )

    args = parser.parse_args()

    screen_articles(args.in_articles_tsv, args.out_articles_tsv)

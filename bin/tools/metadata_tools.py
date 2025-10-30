import logging
import requests
import xml.etree.ElementTree as ET

from common.utils import get_env_variable


def get_doi_for_arxiv_url(arxiv_url: str) -> str | None:
    """
    Retrieves the DOI for a given arXiv URL using the arXiv API.

    Args:
        arxiv_url (str): The URL of the arXiv article.
    Returns:
        The DOI as a string, or None if not found.
    """
    logging.info("-" * 20)
    logging.info("get_doi_for_arxiv_url called with the following arguments:")
    logging.info(f"arxiv_url : {arxiv_url}")
    logging.info("-" * 20)

    base_url = "10.48550/arXiv."
    arxiv_id = arxiv_url.rstrip("/").split("/")[-1]
    doi = f"{base_url}{arxiv_id}"
    logging.info(f"Constructed DOI: {doi}")

    return doi


def get_abstract_from_doi(doi: str, email: str = get_env_variable("USER_EMAIL")) -> str:
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
    research_url = (
        f"{BASE_URL}esearch.fcgi?db=pubmed&term={doi}[doi]&retmode=xml&email={email}"
    )

    try:
        logging.info("⌛ Began retrieving PMID from DOI...")
        research_response = requests.get(research_url, timeout=10)
        research_response.raise_for_status()

        # Parse ESearch XML
        root_esearch = ET.fromstring(research_response.content)
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
    doi: str, api_key: str = get_env_variable("SPRINGER_META_API_KEY")
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

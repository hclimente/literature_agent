import json
import logging

from .models import (
    MetadataResponse,
    PriorityResponse,
    ScreeningResponse,
    pprint,
)


def validate_json_response(response_text: str) -> dict:
    """
    Validate that the response is valid JSON.

    Args:
        response_text (str): The AI response text.

    Returns:
        dict: The parsed JSON object.
    """
    if not response_text or not isinstance(response_text, str):
        raise ValidationError(response_text, "Empty or non-string response.")

    # remove ``` at the start and end if present
    if response_text.startswith("```json") and response_text.endswith("```"):
        response_text = response_text[7:-3].strip()
    elif response_text.startswith("```") and response_text.endswith("```"):
        response_text = response_text[3:-3].strip()
    elif response_text.startswith("`") and response_text.endswith("`"):
        response_text = response_text[1:-1].strip()

    # parse as json
    try:
        response = json.loads(response_text)
    except json.JSONDecodeError:
        raise ValidationError(response_text, "Response is not valid JSON.")

    if not isinstance(response, list):
        raise ValidationError(response, "Response should be a list.")

    for item in response:
        if not isinstance(item, dict):
            raise ValidationError(
                response,
                "Each item in the response list should be a dictionary.",
            )

    return response


def split_by_qc(
    articles,
    response_pass,
    allow_errors,
    merge_key="metadata_doi",
):
    """
    Split articles into those that passed and failed QC.

    Args:
        articles (list): List of articles.
        response_pass (dict): Articles that passed validation.
        allow_errors (bool): Whether to allow errors without raising exceptions.
        merge_key (str): The key to use for merging articles with QC results.

    Returns:
        tuple: (articles_pass, articles_fail)
    """
    articles_pass = []
    articles_fail = []

    for item in articles:
        k = getattr(item, merge_key)

        if k in response_pass:
            for new_field in response_pass[k].model_fields:
                try:
                    setattr(item, new_field, getattr(response_pass[k], new_field))
                except KeyError:
                    error_msg = (
                        f"Expected field '{new_field}' not found in QC pass data."
                    )
                    handle_error(item, error_msg, allow_errors)
                    articles_fail.append(item)
                    continue
                except ValidationError:
                    error_msg = (
                        f"Validation error for field '{new_field}' in QC pass data."
                    )
                    handle_error(item, error_msg, allow_errors)
                    articles_fail.append(item)
                    continue

            articles_pass.append(item)
        else:
            error_msg = (
                f"Key {merge_key} '{k}' not found among passing {response_pass.keys()}."
            )
            handle_error(item, error_msg, allow_errors)
            articles_fail.append(item)

    return articles_pass, articles_fail


def handle_error(item: dict, error_msg: str, allow_errors: bool = False) -> dict:
    """
    Handle error messages during validation.

    Args:
        item (dict): The dictionary containing the article data.
        error_msg (str): The error message to handle.
        allow_errors (bool): Whether to allow errors without raising exceptions.

    Returns:
        dict: The modified dictionary with error field added (if allow_errors=True).
    """
    if allow_errors:
        logging.warning(f"⚠️ {error_msg}")
        logging.warning(f"⚠️ Article data: {item}")
    else:
        raise ValidationError(item, error_msg)


class ValidationError(Exception):
    """Exception raised for validation errors during article processing."""

    def __init__(self, item, error_msg):
        logging.error(f"❌ {error_msg}")
        logging.error(f"❌ Article data: {item}")
        super().__init__(error_msg)


def validate_llm_response(
    stage: str,
    response_text: str,
    merge_key: str,
    allow_qc_errors: bool,
) -> tuple:
    """
    Validate LLM response for a given processing stage.

    Args:
        stage (str): The processing stage (e.g., "metadata", "screening", "priority").
        response_text (str): The AI response text.
        merge_key (str): The key to use for merging articles with QC results.
        allow_qc_errors (bool): Whether to allow errors without failing the process.

    Returns:
        dict: Articles that passed validation, keyed by merge_key.
    """
    logging.info(f"Began validating {stage} response...")
    response = validate_json_response(response_text)

    response_pass = {}

    models = {
        "metadata": MetadataResponse,
        "priority": PriorityResponse,
        "screening": ScreeningResponse,
    }

    for item in response:
        try:
            article = models[stage].model_validate(item)
            key = getattr(article, merge_key)
            response_pass[key] = article
        except Exception as e:
            error_msg = f"Validation failed for item: {pprint(item)}\n{e}"
            handle_error(item, error_msg, allow_qc_errors)

    logging.info(f"Valid response for {len(response_pass)} articles.")
    logging.debug(f"Valid items: {pprint(response_pass)}")

    return response_pass


def save_validated_responses(
    articles: list,
    response_pass: dict,
    allow_qc_errors: bool,
    stage: str,
    **kwargs,
) -> None:
    """
    Save validated responses to JSON files.

    Args:
        articles (list): List of articles to validate.
        response_pass (dict): Articles that passed validation.
        allow_qc_errors (bool): Whether to allow errors without failing the process.
        stage (str): The processing stage (e.g., "screening", "priority").
        **kwargs: Additional keyword arguments passed to split_by_qc.
    """

    logging.info("Began saving validating responses...")

    articles_pass, articles_fail = split_by_qc(
        articles, response_pass, allow_qc_errors, **kwargs
    )
    logging.debug(f"Articles Pass: {pprint(articles_pass)}")
    logging.debug(f"Articles Fail: {pprint(articles_fail)}")
    if articles_pass:
        with open(f"{stage}_pass.json", "w") as f:
            f.write(pprint(articles_pass))
    if articles_fail:
        with open(f"{stage}_fail.json", "w") as f:
            f.write(pprint(articles_fail))

    logging.info("✅ Done validating responses.")


def get_common_variations(expected_values: list) -> dict:
    """
    Generate common variations of expected values (case, quotes, punctuation).

    Args:
        expected_values (list): List of expected values.

    Returns:
        dict: Mapping of variations to normalized values.
    """
    d = {}

    for v in expected_values:
        d[v] = v
        d[v.lower()] = v
        d[v.upper()] = v
        d[v.capitalize()] = v
        d[v.title()] = v

    update = {}
    for k, v in d.items():
        update[f"'{k}'"] = v
        update[f'"{k}"'] = v
        update[f"{k}."] = v

    d.update(update)
    return d

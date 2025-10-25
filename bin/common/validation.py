import json
import logging

from .models import (
    MetadataResponse,
    pprint,
)


def validate_json_response(response_text: str, stage: str) -> dict:
    """
    Validate that the response is valid JSON.

    Args:
        response_text (str): The AI response text.
        stage (str): The processing stage (e.g., "metadata", "screening", "priority").

    Returns:
        dict: The parsed JSON object.
    """
    if not response_text or not isinstance(response_text, str):
        raise ValidationError(stage, response_text, "Empty or non-string response.")

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
        raise ValidationError(stage, response_text, "Response is not valid JSON.")

    if not isinstance(response, list):
        raise ValidationError(
            stage,
            response,
            "Response should be a list.",
        )

    for item in response:
        if not isinstance(item, dict):
            raise ValidationError(
                stage,
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
        qc_pass (dict): Articles that passed validation.
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
                f"Article with {merge_key} '{k}' not found among passing articles."
            )
            handle_error(item, error_msg, allow_errors)
            articles_fail.append(item)

    return articles_pass, articles_fail


def handle_error(item: dict, error_msg: str, allow_errors: bool = False) -> dict:
    """
    Handle error messages.

    Args:
        d (dict): The dictionary containing the article data.
        error_msg (str): The error message to handle.
        stage (str): The processing stage (e.g., "screening", "priority").
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
        allow_qc_errors (bool): Whether to allow errors without failing the process.

    Returns:
        tuple: (response_pass, response_fail)
    """
    logging.info(f"Began validating {stage} response...")
    response = validate_json_response(response_text, stage)

    response_pass = {}

    models = {
        "metadata": MetadataResponse,
    }

    for item in response:
        try:
            article = models[stage].model_validate(item)
            key = str(getattr(article, merge_key))
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
        response_fail (dict): Articles that failed validation.
        allow_qc_errors (bool): Whether to allow errors without failing the process.
        stage (str): The processing stage (e.g., "screening", "priority").
    """
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

    logging.info("✅ Done validating screening response.")


def validate_decision_response(
    decisions: dict, allow_errors: bool, stage: str, decision_mappings: dict
) -> tuple:
    """
    Validate decision responses and normalize decision values.

    Args:
        decisions (dict): Dictionary of article decisions.
        allow_errors (bool): Whether to allow errors without failing the process.
        stage (str): The processing stage (e.g., "screening", "priority").
        decision_mappings (dict): Mapping of decision variations to normalized values.

    Returns:
        tuple: (articles_pass, articles_fail)
    """
    articles_pass = {}
    articles_fail = {}

    for k, d in decisions.items():
        if not d or not isinstance(d, dict):
            articles_fail[k] = handle_error(
                d, "Empty or non-dict response.", stage, allow_errors
            )
            continue

        if not all(k in d for k in ["decision", "reasoning"]):
            articles_fail[k] = handle_error(
                d,
                "Missing keys (decision and/or reasoning).",
                stage,
                allow_errors,
            )
            continue

        decision = str(d["decision"])

        if not decision or not isinstance(decision, str):
            articles_fail[k] = handle_error(
                d, "Empty or non-string response.", stage, allow_errors
            )
            continue

        decision = decision.strip().lower()

        try:
            decision = decision_mappings[decision]
        except KeyError:
            articles_fail[k] = handle_error(
                d,
                f"Invalid priority value. Expected {set(decision_mappings.values())}.",
                stage,
                allow_errors,
            )
            continue

        d["decision"] = decision
        articles_pass[k] = d

    return articles_pass, articles_fail


def get_common_variations(expected_values: list):
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


def validate_screening_response(
    stage: str, response: dict, allow_errors: bool
) -> tuple:
    """
    Validate AI screening response.

    Args:
        stage (str): The processing stage.
        response (dict): The parsed AI response for screening decision.
        allow_errors (bool): Whether to allow errors without failing the process.

    Returns:
        tuple: (articles_pass, articles_fail)
    """

    screening_mappings = get_common_variations(["true", "false"])
    return validate_decision_response(response, allow_errors, stage, screening_mappings)


def validate_priority_response(stage: str, response: dict, allow_errors: bool) -> tuple:
    """
    Validate AI prioritization response.

    Args:
        stage (str): The processing stage.
        response (dict): The AI response for priority decision.
        allow_errors (bool): Whether to allow errors without failing the process.

    Returns:
        tuple: (articles_pass, articles_fail)
    """

    priority_mappings = get_common_variations(["low", "medium", "high"])
    return validate_decision_response(response, allow_errors, stage, priority_mappings)


def sanitize_text(text: str) -> str:
    """
    Sanitize text by escaping special characters.

    Args:
        text (str): The text to sanitize.
    Returns:
        str: The sanitized text.
    """
    special_characters = ["\\", '"', "'", "$"]
    for char in special_characters:
        text = text.strip().replace(char, f"\\{char}")

    return text

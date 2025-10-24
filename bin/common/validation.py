import json
import logging
import re


def validate_json_response(response_text: str, stage: str) -> dict:
    """
    Validate that the response is valid JSON.

    Args:
        response_text (str): The AI response text.

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

    if not isinstance(response, dict):
        raise ValidationError(
            stage,
            response,
            "Response should be a dictionary.",
        )

    return response


def handle_error(
    d: dict, error_msg: str, stage: str, allow_errors: bool = False
) -> str:
    """
    Handle error messages.

    Args:
        d (dict): The dictionary containing the article data.
        error_msg (str): The error message to handle.
        stage (str): The processing stage (e.g., "screening", "priority").
        allow_errors (bool): Whether to allow errors without raising exceptions.
    Returns:
        str: The handled error message.
    """
    if allow_errors:
        logging.warning(f"⚠️ {error_msg}")
        d[f"{stage}_error"] = error_msg
        return d
    else:
        raise ValidationError(stage, d, error_msg)


def split_by_qc(
    articles,
    qc_pass,
    qc_fail,
    stage,
    allow_errors,
    merge_key="metadata_doi",
    expected_fields=["decision", "reasoning"],
):
    """
    Split articles into those that passed and failed screening QC.
    Args:
        articles (list): List of articles.
        qc_pass (dict): Articles that passed validation.
        qc_faill (dict): Articles that failed validation.
    Returns:
        tuple: (articles_pass, articles_fail)
    """
    articles_pass = []
    articles_fail = []

    for a in articles:
        k = a[merge_key]

        if k in qc_pass:
            for f in expected_fields:
                try:
                    a[f"{stage}_{f}"] = qc_pass[k][f]
                except KeyError:
                    error_msg = f"Expected field '{f}' not found in QC pass data."
                    a = handle_error(a, error_msg, stage, allow_errors)
                    articles_fail.append(a)
                    continue

            articles_pass.append(a)
        elif k in qc_fail:
            articles_fail.append(a)
        else:
            error_msg = f"Article {merge_key} not found in LLM output."
            a = handle_error(a, error_msg, stage, allow_errors)
            articles_fail.append(a)

    return articles_pass, articles_fail


class ValidationError(Exception):
    def __init__(self, field, value, reason):
        error_msg = f"Validation failed for {field} with value '{value}': {reason}"

        logging.error(f"❌ {error_msg}")
        super().__init__(error_msg)


def validate_llm_response(
    stage: str,
    response_text: str,
    allow_qc_errors: bool,
) -> None:
    logging.info(f"Began validating {stage} response...")
    response = validate_json_response(response_text, stage)

    if stage == "metadata":
        response_pass, response_fail = validate_metadata_response(
            stage, response, allow_qc_errors
        )
    elif stage == "screening":
        response_pass, response_fail = validate_screening_response(
            stage, response, allow_qc_errors
        )
    elif stage == "priority":
        response_pass, response_fail = validate_priority_response(
            stage, response, allow_qc_errors
        )
    else:
        raise

    logging.info(f"Validated Screening for {len(response_pass)} articles.")
    logging.debug(f"Screening Pass: {response_pass}")
    logging.info(f"Invalid Screening for {len(response_fail)} articles.")
    logging.debug(f"Screening Fail: {response_fail}")

    return response_pass, response_fail


def save_validated_responses(
    articles: list,
    response_pass: dict,
    response_fail: dict,
    allow_qc_errors: bool,
    stage: str,
    **kwargs,
) -> None:
    articles_pass, articles_fail = split_by_qc(
        articles, response_pass, response_fail, stage, allow_qc_errors, **kwargs
    )
    logging.debug(f"Articles Pass: {articles_pass}")
    logging.debug(f"Articles Fail: {articles_fail}")
    if articles_pass:
        json.dump(articles_pass, open(f"{stage}_pass.json", "w"), indent=2)
    if articles_fail:
        json.dump(articles_fail, open(f"{stage}_fail.json", "w"), indent=2)
    logging.info("✅ Done validating screening response.")


def validate_decision_response(
    decisions: str, allow_errors: bool, stage: str, decision_mappings: dict
) -> str:
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


def validate_metadata_response(
    stage: str, metadata: str, allow_errors: bool = False
) -> tuple[str, str, str]:
    """
    Validate and parse AI metadata response. It raises an error if validation fails.

    Args:
        metadata (str): The AI response in JSON format.

    Returns:
        tuple[dict, dict]: A tuple containing two dictionaries:
            - articles_pass: Articles that passed validation.
            - articles_fail: Articles that failed validation with error messages.
    """

    articles_pass = {}
    articles_fail = {}

    for k, d in metadata.items():
        if not d or not isinstance(d, dict):
            articles_fail[k] = handle_error(
                d, "Empty or non-dict response.", stage, allow_errors
            )
            continue

        if not all(k in d for k in ["title", "summary", "doi"]):
            articles_fail[k] = handle_error(
                d, "Missing keys (title, summary, doi).", stage, allow_errors
            )
            continue

        # Validate individual fields
        if not d["title"]:
            articles_fail[k] = handle_error(
                d, "Title cannot be empty.", stage, allow_errors
            )
            continue
        else:
            d["title"] = sanitize_text(d["title"].strip())

        if not d["summary"]:
            articles_fail[k] = handle_error(
                d, "Summary cannot be empty.", stage, allow_errors
            )
            continue
        else:
            d["summary"] = d["summary"].strip()

        if not d["doi"]:
            articles_fail[k] = handle_error(
                d, "DOI cannot be empty.", stage, allow_errors
            )
            continue

        elif d["doi"] != "NULL":
            if not re.match(r"^10\.\d{4,}/[^\s]+$", d["doi"]):
                articles_fail[k] = handle_error(
                    d, d["metadata_error"], stage, allow_errors
                )
                continue
            d["doi"] = d["doi"].strip()

        articles_pass[k] = d

    return articles_pass, articles_fail


def validate_screening_response(stage: str, response: str, allow_errors: bool) -> str:
    """
    Validate AI screening response. It raises an error if validation fails.

    Args:
        response (str): The parsed AI response for screening decision
        allow_errors (bool): Whether to allow errors without failing the process.

    Returns:
        tuple: (articles_pass, articles_fail)
    """

    screening_mappings = get_common_variations(["true", "false"])
    return validate_decision_response(response, allow_errors, stage, screening_mappings)


def validate_priority_response(stage: str, response: str, allow_errors: bool) -> str:
    """
    Validate AI prioritization response. It raises an error if validation fails.

    Args:
        response_text (str): The AI response for priority decision
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

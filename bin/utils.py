import json
import logging


def validate_json_response(
    response_text: str, stage: str, expected_fields: list = []
) -> dict:
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

    expected_fields = set(expected_fields)
    actual_fields = set(response.keys())
    if actual_fields != expected_fields:
        diff = actual_fields.symmetric_difference(expected_fields)
        raise ValidationError(
            stage,
            response,
            f"Response fields do not match expected fields. Symmetric diff: {diff}.",
        )

    return response


def handle_error(
    d: dict, error_msg: str, stage: str, allow_errors: bool = False
) -> str:
    """
    Handle error messages.

    Args:
        error_msg (str): The error message to handle.
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


class ValidationError(Exception):
    def __init__(self, field, value, reason):
        error_msg = f"Validation failed for {field} with value '{value}': {reason}"

        logging.error(f"❌ {error_msg}")
        super().__init__(error_msg)

import logging


class ValidationError(Exception):
    def __init__(self, field, value, reason):
        error_msg = f"Validation failed for {field} with value '{value}': {reason}"

        logging.error(f"❌ {error_msg}")
        super().__init__(error_msg)

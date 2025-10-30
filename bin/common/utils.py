import logging
import os


def get_env_variable(var_name: str) -> str:
    """
    Retrieve the value of an environment variable.

    Args:
        var_name (str): The name of the environment variable.

    Returns:
        str: The value of the environment variable.

    Raises:
        ValueError: If the environment variable is not found.
    """
    value = os.environ.get(var_name)

    if not value:
        error_msg = f"{var_name} environment variable not found."
        logging.error(f"❌ {error_msg}")
        raise ValueError(error_msg)
    return value

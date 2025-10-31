import logging
import os


def get_env_variable(var_name: str, raise_error: bool = False) -> str:
    """
    Retrieve the value of an environment variable.

    Args:
        var_name (str): The name of the environment variable.
        raise_error (bool): Whether to raise an error if the variable is not found.

    Returns:
        str: The value of the environment variable.

    Raises:
        ValueError: If the environment variable is not found and raise_error is True.
    """
    value = os.environ.get(var_name)

    if not value:
        error_msg = f"{var_name} environment variable not found."
        logging.error(f"❌ {error_msg}")
        if raise_error:
            raise ValueError(error_msg)
    return value

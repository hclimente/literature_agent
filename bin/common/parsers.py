import argparse


def add_input_articles_json_argument(parser: argparse.ArgumentParser):
    """
    Add articles JSON argument to an argument parser.

    Args:
        parser (argparse.ArgumentParser): The argument parser to add arguments to.

    Returns:
        argparse.ArgumentParser: The modified parser.
    """
    parser.add_argument(
        "--articles_json",
        type=str,
        required=True,
        help="The path to the JSON file containing the articles to process.",
    )

    return parser


def add_output_argument(parser: argparse.ArgumentParser):
    """
    Add output file argument to an argument parser.

    Args:
        parser (argparse.ArgumentParser): The argument parser to add arguments to.

    Returns:
        argparse.ArgumentParser: The modified parser.
    """
    parser.add_argument(
        "--out",
        type=str,
        required=True,
        help="The path to the output file.",
    )

    return parser


def add_debug_argument(parser: argparse.ArgumentParser):
    """
    Add debug argument to an argument parser.

    Args:
        parser (argparse.ArgumentParser): The argument parser to add arguments to.

    Returns:
        argparse.ArgumentParser: The modified parser.
    """
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with verbose logging.",
    )

    return parser


def add_duckdb_arguments(parser: argparse.ArgumentParser):
    """
    Add DuckDB database path argument to an argument parser.

    Args:
        parser (argparse.ArgumentParser): The argument parser to add arguments to.

    Returns:
        argparse.ArgumentParser: The modified parser.
    """
    parser.add_argument(
        "--db_path",
        type=str,
        default="papers_please.duckdb",
        help="Path to the DuckDB database file.",
    )

    return parser


def add_llm_arguments(
    parser: argparse.ArgumentParser, include_research_interests: bool = False
):
    """
    Add LLM processing arguments to an argument parser.

    Args:
        parser (argparse.ArgumentParser): The argument parser to add arguments to.
        include_research_interests (bool): Whether to include the research interests argument.

    Returns:
        argparse.ArgumentParser: The modified parser.
    """
    parser.add_argument(
        "--system_prompt_path",
        type=str,
        required=False,
        help="The path to the system prompt file.",
    )
    parser.add_argument(
        "--model",
        type=str,
        required=False,
        help="The model to use for metadata extraction. One of 'gemini-1.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.5-pro'.",
    )
    parser.add_argument(
        "--allow_qc_errors",
        type=bool,
        required=True,
        help="Whether to allow QC errors without failing the process.",
    )

    if include_research_interests:
        parser.add_argument(
            "--research_interests_path",
            type=str,
            required=True,
            help="The path to a text file containing the user's research interests.",
        )

    return parser

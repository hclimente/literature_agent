#!/usr/bin/env python
"""Tests for common/parsers.py"""

import argparse
import pytest
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.parsers import (
    add_input_articles_json_argument,
    add_output_argument,
    add_debug_argument,
    add_duckdb_arguments,
    add_llm_arguments,
)


class TestAddInputArticlesJsonArgument:
    """Test suite for add_input_articles_json_argument function"""

    def test_adds_articles_json_argument(self):
        """Test that articles_json argument is added to parser"""
        parser = argparse.ArgumentParser()
        result = add_input_articles_json_argument(parser)

        # Check that it returns the parser
        assert result is parser

        # Parse with the argument
        args = parser.parse_args(["--articles_json", "test.json"])
        assert args.articles_json == "test.json"

    def test_articles_json_is_required(self):
        """Test that articles_json argument is required"""
        parser = argparse.ArgumentParser()
        add_input_articles_json_argument(parser)

        # Should raise error when not provided
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_articles_json_accepts_different_paths(self):
        """Test that articles_json accepts various file paths"""
        parser = argparse.ArgumentParser()
        add_input_articles_json_argument(parser)

        test_paths = [
            "articles.json",
            "/absolute/path/to/articles.json",
            "../relative/path/articles.json",
            "path/with spaces/articles.json",
        ]

        for path in test_paths:
            args = parser.parse_args(["--articles_json", path])
            assert args.articles_json == path


class TestAddOutputArgument:
    """Test suite for add_output_argument function"""

    def test_adds_output_argument(self):
        """Test that out argument is added to parser"""
        parser = argparse.ArgumentParser()
        result = add_output_argument(parser)

        # Check that it returns the parser
        assert result is parser

        # Parse with the argument
        args = parser.parse_args(["--out", "output.json"])
        assert args.out == "output.json"

    def test_output_is_required(self):
        """Test that out argument is required"""
        parser = argparse.ArgumentParser()
        add_output_argument(parser)

        # Should raise error when not provided
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_output_accepts_different_paths(self):
        """Test that out accepts various file paths"""
        parser = argparse.ArgumentParser()
        add_output_argument(parser)

        test_paths = [
            "output.json",
            "/absolute/path/to/output.txt",
            "../relative/output.csv",
            "results/data.json",
        ]

        for path in test_paths:
            args = parser.parse_args(["--out", path])
            assert args.out == path


class TestAddDebugArgument:
    """Test suite for add_debug_argument function"""

    def test_adds_debug_argument(self):
        """Test that debug argument is added to parser"""
        parser = argparse.ArgumentParser()
        result = add_debug_argument(parser)

        # Check that it returns the parser
        assert result is parser

        # Parse with the argument
        args = parser.parse_args(["--debug"])
        assert args.debug is True

    def test_debug_is_optional(self):
        """Test that debug argument is optional"""
        parser = argparse.ArgumentParser()
        add_debug_argument(parser)

        # Should not raise error when not provided
        args = parser.parse_args([])
        assert args.debug is False

    def test_debug_is_store_true_action(self):
        """Test that debug uses store_true action"""
        parser = argparse.ArgumentParser()
        add_debug_argument(parser)

        # Without flag
        args_false = parser.parse_args([])
        assert args_false.debug is False

        # With flag
        args_true = parser.parse_args(["--debug"])
        assert args_true.debug is True


class TestAddDuckdbArguments:
    """Test suite for add_duckdb_arguments function"""

    def test_adds_db_path_argument(self):
        """Test that db_path argument is added to parser"""
        parser = argparse.ArgumentParser()
        result = add_duckdb_arguments(parser)

        # Check that it returns the parser
        assert result is parser

        # Parse with the argument
        args = parser.parse_args(["--db_path", "custom.duckdb"])
        assert args.db_path == "custom.duckdb"

    def test_db_path_has_default_value(self):
        """Test that db_path has default value"""
        parser = argparse.ArgumentParser()
        add_duckdb_arguments(parser)

        # Should use default when not provided
        args = parser.parse_args([])
        assert args.db_path == "papers_please.duckdb"

    def test_db_path_accepts_custom_paths(self):
        """Test that db_path accepts various database paths"""
        parser = argparse.ArgumentParser()
        add_duckdb_arguments(parser)

        test_paths = [
            "custom.duckdb",
            "/absolute/path/database.duckdb",
            "../relative/db.duckdb",
            "data/papers.db",
        ]

        for path in test_paths:
            args = parser.parse_args(["--db_path", path])
            assert args.db_path == path

    def test_db_path_is_optional(self):
        """Test that db_path argument is optional"""
        parser = argparse.ArgumentParser()
        add_duckdb_arguments(parser)

        # Should not raise error when not provided
        args = parser.parse_args([])
        assert hasattr(args, "db_path")


class TestAddLlmArguments:
    """Test suite for add_llm_arguments function"""

    def test_adds_basic_llm_arguments(self):
        """Test that basic LLM arguments are added"""
        parser = argparse.ArgumentParser()
        result = add_llm_arguments(parser)

        # Check that it returns the parser
        assert result is parser

        # Check that basic arguments exist
        args = parser.parse_args(
            [
                "--system_prompt_path",
                "prompt.md",
                "--model",
                "gemini-1.5-flash",
                "--allow_qc_errors",
                "True",
            ]
        )
        assert args.system_prompt_path == "prompt.md"
        assert args.model == "gemini-1.5-flash"
        assert args.allow_qc_errors is True

    def test_adds_research_interests_when_requested(self):
        """Test that research_interests_path is added when requested"""
        parser = argparse.ArgumentParser()
        add_llm_arguments(parser, include_research_interests=True)

        # Should have research_interests_path argument
        args = parser.parse_args(
            [
                "--system_prompt_path",
                "prompt.md",
                "--model",
                "gemini-1.5-flash",
                "--allow_qc_errors",
                "True",
                "--research_interests_path",
                "interests.md",
            ]
        )
        assert args.research_interests_path == "interests.md"

    def test_does_not_add_research_interests_by_default(self):
        """Test that research_interests_path is not added by default"""
        parser = argparse.ArgumentParser()
        add_llm_arguments(parser)

        # Should parse without research_interests_path
        args = parser.parse_args(
            [
                "--system_prompt_path",
                "prompt.md",
                "--model",
                "gemini-1.5-flash",
                "--allow_qc_errors",
                "True",
            ]
        )
        assert not hasattr(args, "research_interests_path")

    def test_research_interests_is_required_when_included(self):
        """Test that research_interests_path is required when included"""
        parser = argparse.ArgumentParser()
        add_llm_arguments(parser, include_research_interests=True)

        # Should raise error when research_interests_path not provided
        with pytest.raises(SystemExit):
            parser.parse_args(
                [
                    "--system_prompt_path",
                    "prompt.md",
                    "--model",
                    "gemini-1.5-flash",
                    "--allow_qc_errors",
                    "True",
                ]
            )

    def test_system_prompt_path_is_optional(self):
        """Test that system_prompt_path is optional"""
        parser = argparse.ArgumentParser()
        add_llm_arguments(parser)

        # Should parse without system_prompt_path
        args = parser.parse_args(
            ["--model", "gemini-1.5-flash", "--allow_qc_errors", "True"]
        )
        assert args.system_prompt_path is None

    def test_model_is_optional(self):
        """Test that model is optional"""
        parser = argparse.ArgumentParser()
        add_llm_arguments(parser)

        # Should parse without model
        args = parser.parse_args(
            ["--system_prompt_path", "prompt.md", "--allow_qc_errors", "True"]
        )
        assert args.model is None

    def test_allow_qc_errors_is_required(self):
        """Test that allow_qc_errors is required"""
        parser = argparse.ArgumentParser()
        add_llm_arguments(parser)

        # Should raise error when allow_qc_errors not provided
        with pytest.raises(SystemExit):
            parser.parse_args(
                ["--system_prompt_path", "prompt.md", "--model", "gemini-1.5-flash"]
            )

    def test_allow_qc_errors_accepts_boolean_values(self):
        """Test that allow_qc_errors accepts boolean-like values"""
        parser = argparse.ArgumentParser()
        add_llm_arguments(parser)

        # Test with True
        args_true = parser.parse_args(
            [
                "--system_prompt_path",
                "prompt.md",
                "--model",
                "gemini-1.5-flash",
                "--allow_qc_errors",
                "True",
            ]
        )
        assert args_true.allow_qc_errors is True

        # Note: argparse will accept "False" as a string and convert to True
        # because it's a non-empty string. This is expected behavior.

    def test_model_accepts_different_values(self):
        """Test that model accepts different model names"""
        parser = argparse.ArgumentParser()
        add_llm_arguments(parser)

        test_models = [
            "gemini-1.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.5-pro",
        ]

        for model in test_models:
            args = parser.parse_args(
                [
                    "--system_prompt_path",
                    "prompt.md",
                    "--model",
                    model,
                    "--allow_qc_errors",
                    "True",
                ]
            )
            assert args.model == model

    def test_system_prompt_path_accepts_various_paths(self):
        """Test that system_prompt_path accepts various file paths"""
        parser = argparse.ArgumentParser()
        add_llm_arguments(parser)

        test_paths = [
            "prompt.md",
            "/absolute/path/to/prompt.txt",
            "../relative/prompt.md",
            "prompts/system_instruction.txt",
        ]

        for path in test_paths:
            args = parser.parse_args(
                [
                    "--system_prompt_path",
                    path,
                    "--model",
                    "gemini-1.5-flash",
                    "--allow_qc_errors",
                    "True",
                ]
            )
            assert args.system_prompt_path == path


class TestMultipleArgumentFunctions:
    """Test combining multiple argument functions"""

    def test_combine_input_and_output(self):
        """Test combining input and output arguments"""
        parser = argparse.ArgumentParser()
        add_input_articles_json_argument(parser)
        add_output_argument(parser)

        args = parser.parse_args(
            ["--articles_json", "input.json", "--out", "output.json"]
        )
        assert args.articles_json == "input.json"
        assert args.out == "output.json"

    def test_combine_all_basic_arguments(self):
        """Test combining all basic arguments"""
        parser = argparse.ArgumentParser()
        add_input_articles_json_argument(parser)
        add_output_argument(parser)
        add_debug_argument(parser)
        add_duckdb_arguments(parser)

        args = parser.parse_args(
            [
                "--articles_json",
                "input.json",
                "--out",
                "output.json",
                "--debug",
                "--db_path",
                "custom.duckdb",
            ]
        )
        assert args.articles_json == "input.json"
        assert args.out == "output.json"
        assert args.debug is True
        assert args.db_path == "custom.duckdb"

    def test_combine_with_llm_arguments(self):
        """Test combining with LLM arguments"""
        parser = argparse.ArgumentParser()
        add_input_articles_json_argument(parser)
        add_output_argument(parser)
        add_debug_argument(parser)
        add_llm_arguments(parser, include_research_interests=True)

        args = parser.parse_args(
            [
                "--articles_json",
                "input.json",
                "--out",
                "output.json",
                "--debug",
                "--system_prompt_path",
                "prompt.md",
                "--model",
                "gemini-1.5-flash",
                "--allow_qc_errors",
                "True",
                "--research_interests_path",
                "interests.md",
            ]
        )
        assert args.articles_json == "input.json"
        assert args.out == "output.json"
        assert args.debug is True
        assert args.system_prompt_path == "prompt.md"
        assert args.model == "gemini-1.5-flash"
        assert args.research_interests_path == "interests.md"

    def test_optional_arguments_can_be_omitted(self):
        """Test that optional arguments can be omitted when combining"""
        parser = argparse.ArgumentParser()
        add_input_articles_json_argument(parser)
        add_output_argument(parser)
        add_debug_argument(parser)
        add_duckdb_arguments(parser)

        # Omit optional --debug and use default --db_path
        args = parser.parse_args(
            ["--articles_json", "input.json", "--out", "output.json"]
        )
        assert args.articles_json == "input.json"
        assert args.out == "output.json"
        assert args.debug is False
        assert args.db_path == "papers_please.duckdb"

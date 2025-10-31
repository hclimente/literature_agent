#!/usr/bin/env python
"""Tests for common/utils.py"""

import os
import pytest
from unittest.mock import patch
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils import get_env_variable


class TestGetEnvVariable:
    """Test suite for get_env_variable function"""

    def test_get_existing_env_variable(self):
        """Test retrieving an existing environment variable"""
        # Set a test environment variable
        test_var = "TEST_VAR_12345"
        test_value = "test_value"
        os.environ[test_var] = test_value

        try:
            result = get_env_variable(test_var)
            assert result == test_value
        finally:
            # Clean up
            del os.environ[test_var]

    def test_get_existing_env_variable_with_raise_error_false(self):
        """Test retrieving an existing variable with raise_error=False"""
        test_var = "TEST_VAR_67890"
        test_value = "another_value"
        os.environ[test_var] = test_value

        try:
            result = get_env_variable(test_var, raise_error=False)
            assert result == test_value
        finally:
            del os.environ[test_var]

    def test_get_existing_env_variable_with_raise_error_true(self):
        """Test retrieving an existing variable with raise_error=True"""
        test_var = "TEST_VAR_RAISE"
        test_value = "value_with_raise"
        os.environ[test_var] = test_value

        try:
            result = get_env_variable(test_var, raise_error=True)
            assert result == test_value
        finally:
            del os.environ[test_var]

    def test_get_missing_env_variable_default_behavior(self):
        """Test retrieving a missing variable with default behavior (raise_error=False)"""
        test_var = "NONEXISTENT_VAR_12345"
        # Ensure it doesn't exist
        if test_var in os.environ:
            del os.environ[test_var]

        result = get_env_variable(test_var)
        assert result is None

    def test_get_missing_env_variable_with_raise_error_false(self):
        """Test retrieving a missing variable with raise_error=False"""
        test_var = "NONEXISTENT_VAR_67890"
        # Ensure it doesn't exist
        if test_var in os.environ:
            del os.environ[test_var]

        result = get_env_variable(test_var, raise_error=False)
        assert result is None

    def test_get_missing_env_variable_with_raise_error_true(self):
        """Test that missing variable raises ValueError when raise_error=True"""
        test_var = "NONEXISTENT_VAR_ERROR"
        # Ensure it doesn't exist
        if test_var in os.environ:
            del os.environ[test_var]

        with pytest.raises(
            ValueError, match=f"{test_var} environment variable not found"
        ):
            get_env_variable(test_var, raise_error=True)

    def test_get_empty_string_env_variable(self):
        """Test retrieving an environment variable set to empty string"""
        test_var = "EMPTY_VAR_12345"
        os.environ[test_var] = ""

        try:
            # Empty string is falsy, function logs error but still returns empty string
            result = get_env_variable(test_var)
            assert result == ""
        finally:
            del os.environ[test_var]

    def test_get_empty_string_env_variable_with_raise_error_true(self):
        """Test that empty string raises ValueError when raise_error=True"""
        test_var = "EMPTY_VAR_ERROR"
        os.environ[test_var] = ""

        try:
            with pytest.raises(
                ValueError, match=f"{test_var} environment variable not found"
            ):
                get_env_variable(test_var, raise_error=True)
        finally:
            del os.environ[test_var]

    def test_get_env_variable_with_special_characters(self):
        """Test retrieving an environment variable with special characters in value"""
        test_var = "SPECIAL_CHAR_VAR"
        test_value = "value with spaces and !@#$%"
        os.environ[test_var] = test_value

        try:
            result = get_env_variable(test_var)
            assert result == test_value
        finally:
            del os.environ[test_var]

    def test_get_env_variable_with_multiline_value(self):
        """Test retrieving an environment variable with multiline value"""
        test_var = "MULTILINE_VAR"
        test_value = "line1\nline2\nline3"
        os.environ[test_var] = test_value

        try:
            result = get_env_variable(test_var)
            assert result == test_value
            assert "\n" in result
        finally:
            del os.environ[test_var]

    def test_get_env_variable_with_numeric_value(self):
        """Test retrieving an environment variable with numeric value (stored as string)"""
        test_var = "NUMERIC_VAR"
        test_value = "12345"
        os.environ[test_var] = test_value

        try:
            result = get_env_variable(test_var)
            assert result == test_value
            assert isinstance(result, str)
        finally:
            del os.environ[test_var]

    @patch("common.utils.logging.error")
    def test_get_missing_env_variable_logs_error(self, mock_logging_error):
        """Test that missing variable logs an error message"""
        test_var = "LOGGING_TEST_VAR"
        # Ensure it doesn't exist
        if test_var in os.environ:
            del os.environ[test_var]

        get_env_variable(test_var, raise_error=False)

        # Check that logging.error was called
        mock_logging_error.assert_called_once()
        call_args = mock_logging_error.call_args[0][0]
        assert test_var in call_args
        assert "not found" in call_args

    @patch("common.utils.logging.error")
    def test_get_empty_env_variable_logs_error(self, mock_logging_error):
        """Test that empty variable logs an error message"""
        test_var = "EMPTY_LOGGING_TEST_VAR"
        os.environ[test_var] = ""

        try:
            get_env_variable(test_var, raise_error=False)

            # Check that logging.error was called
            mock_logging_error.assert_called_once()
            call_args = mock_logging_error.call_args[0][0]
            assert test_var in call_args
            assert "not found" in call_args
        finally:
            del os.environ[test_var]

    def test_get_env_variable_case_sensitive(self):
        """Test that environment variable names are case-sensitive"""
        test_var_lower = "test_case_var"
        test_var_upper = "TEST_CASE_VAR"
        test_value = "case_test_value"

        os.environ[test_var_lower] = test_value

        try:
            # Should find the lowercase version
            result_lower = get_env_variable(test_var_lower)
            assert result_lower == test_value

            # Should not find the uppercase version (if not set)
            if test_var_upper not in os.environ:
                result_upper = get_env_variable(test_var_upper)
                assert result_upper is None
        finally:
            if test_var_lower in os.environ:
                del os.environ[test_var_lower]

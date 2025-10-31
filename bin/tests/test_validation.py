#!/usr/bin/env python
"""Tests for common/validation.py"""

import json
import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.validation import (
    validate_json_response,
    handle_error,
    ValidationError,
    split_by_qc,
    validate_llm_response,
    save_validated_responses,
)


class TestValidateJsonResponse:
    """Test suite for validate_json_response function"""

    def test_validate_simple_json_list(self):
        """Test validating a simple JSON list"""
        response_text = '[{"key": "value"}, {"key2": "value2"}]'
        result = validate_json_response(response_text)
        assert result == [{"key": "value"}, {"key2": "value2"}]

    def test_validate_json_with_code_blocks(self):
        """Test validating JSON wrapped in code blocks"""
        response_text = '```json\n[{"key": "value"}]\n```'
        result = validate_json_response(response_text)
        assert result == [{"key": "value"}]

    def test_validate_json_with_text_before_code_block(self):
        """Test validating JSON with text before ```json"""
        response_text = 'Here is the result:\n```json\n[{"key": "value"}]\n```'
        result = validate_json_response(response_text)
        assert result == [{"key": "value"}]

    def test_validate_json_with_triple_backticks(self):
        """Test validating JSON wrapped in triple backticks without json marker"""
        response_text = '```\n[{"key": "value"}]\n```'
        result = validate_json_response(response_text)
        assert result == [{"key": "value"}]

    def test_validate_json_with_single_backticks(self):
        """Test validating JSON wrapped in single backticks"""
        response_text = '`[{"key": "value"}]`'
        result = validate_json_response(response_text)
        assert result == [{"key": "value"}]

    def test_validate_empty_list(self):
        """Test validating an empty list"""
        response_text = "[]"
        result = validate_json_response(response_text)
        assert result == []

    def test_validate_nested_objects(self):
        """Test validating nested JSON objects"""
        response_text = '[{"outer": {"inner": "value"}}]'
        result = validate_json_response(response_text)
        assert result == [{"outer": {"inner": "value"}}]

    def test_validate_json_with_special_characters(self):
        """Test validating JSON with special characters"""
        response_text = '[{"key": "value with spaces and !@#$%"}]'
        result = validate_json_response(response_text)
        assert result == [{"key": "value with spaces and !@#$%"}]

    def test_validate_empty_string_raises_error(self):
        """Test that empty string raises ValidationError"""
        with pytest.raises(ValidationError, match="Empty or non-string response"):
            validate_json_response("")

    def test_validate_none_raises_error(self):
        """Test that None raises ValidationError"""
        with pytest.raises(ValidationError, match="Empty or non-string response"):
            validate_json_response(None)

    def test_validate_non_string_raises_error(self):
        """Test that non-string input raises ValidationError"""
        with pytest.raises(ValidationError, match="Empty or non-string response"):
            validate_json_response(123)

    def test_validate_invalid_json_raises_error(self):
        """Test that invalid JSON raises ValidationError"""
        response_text = '{"invalid": json}'
        with pytest.raises(ValidationError, match="Response is not valid JSON"):
            validate_json_response(response_text)

    def test_validate_non_list_raises_error(self):
        """Test that non-list JSON raises ValidationError"""
        response_text = '{"key": "value"}'
        with pytest.raises(ValidationError, match="Response should be a list"):
            validate_json_response(response_text)

    def test_validate_list_with_non_dict_raises_error(self):
        """Test that list with non-dict items raises ValidationError"""
        response_text = '["string", "items"]'
        with pytest.raises(
            ValidationError,
            match="Each item in the response list should be a dictionary",
        ):
            validate_json_response(response_text)

    def test_validate_mixed_list_raises_error(self):
        """Test that list with mixed types raises ValidationError"""
        response_text = '[{"key": "value"}, "string"]'
        with pytest.raises(
            ValidationError,
            match="Each item in the response list should be a dictionary",
        ):
            validate_json_response(response_text)

    def test_validate_json_with_whitespace(self):
        """Test validating JSON with extra whitespace"""
        response_text = '  [  {"key": "value"}  ]  '
        result = validate_json_response(response_text)
        assert result == [{"key": "value"}]

    def test_validate_json_with_newlines(self):
        """Test validating JSON with newlines"""
        response_text = '[\n  {"key": "value"},\n  {"key2": "value2"}\n]'
        result = validate_json_response(response_text)
        assert result == [{"key": "value"}, {"key2": "value2"}]


class TestHandleError:
    """Test suite for handle_error function"""

    @patch("common.validation.logging.warning")
    def test_handle_error_with_allow_errors_true(self, mock_warning):
        """Test handle_error with allow_errors=True logs warnings"""
        item = {"test": "data"}
        error_msg = "Test error message"

        # Should not raise exception
        handle_error(item, error_msg, allow_errors=True)

        # Should log warnings
        assert mock_warning.call_count == 2
        call_args_list = [call[0][0] for call in mock_warning.call_args_list]
        assert any(error_msg in arg for arg in call_args_list)
        assert any("test" in arg for arg in call_args_list)

    def test_handle_error_with_allow_errors_false(self):
        """Test handle_error with allow_errors=False raises exception"""
        item = {"test": "data"}
        error_msg = "Test error message"

        with pytest.raises(ValidationError, match="Test error message"):
            handle_error(item, error_msg, allow_errors=False)

    def test_handle_error_default_behavior(self):
        """Test handle_error with default behavior (allow_errors=False)"""
        item = {"test": "data"}
        error_msg = "Test error message"

        with pytest.raises(ValidationError):
            handle_error(item, error_msg)

    @patch("common.validation.logging.warning")
    def test_handle_error_with_complex_item(self, mock_warning):
        """Test handle_error with complex item structure"""
        item = {"nested": {"data": "value"}, "list": [1, 2, 3], "string": "test"}
        error_msg = "Complex error"

        handle_error(item, error_msg, allow_errors=True)
        assert mock_warning.called


class TestValidationError:
    """Test suite for ValidationError class"""

    @patch("common.validation.logging.error")
    def test_validation_error_logs_message(self, mock_error):
        """Test that ValidationError logs error message"""
        item = {"test": "data"}
        error_msg = "Test validation error"

        with pytest.raises(ValidationError):
            raise ValidationError(item, error_msg)

        # Should log errors
        assert mock_error.call_count == 2
        call_args_list = [call[0][0] for call in mock_error.call_args_list]
        assert any(error_msg in arg for arg in call_args_list)

    def test_validation_error_message(self):
        """Test that ValidationError contains correct message"""
        item = {"test": "data"}
        error_msg = "Test validation error"

        try:
            raise ValidationError(item, error_msg)
        except ValidationError as e:
            assert str(e) == error_msg

    @patch("common.validation.logging.error")
    def test_validation_error_with_none_item(self, mock_error):
        """Test ValidationError with None as item"""
        with pytest.raises(ValidationError):
            raise ValidationError(None, "Error with None item")

        assert mock_error.called

    @patch("common.validation.logging.error")
    def test_validation_error_inheritance(self, mock_error):
        """Test that ValidationError is an Exception"""
        assert issubclass(ValidationError, Exception)

        try:
            raise ValidationError({"data": "test"}, "Test")
        except Exception as e:
            assert isinstance(e, ValidationError)


class TestSplitByQC:
    """Test suite for split_by_qc function"""

    def test_split_all_pass(self):
        """Test split when all articles pass QC"""
        # Create mock articles
        article1 = MagicMock()
        article1.doi = "10.1234/test1"
        article2 = MagicMock()
        article2.doi = "10.1234/test2"
        articles = [article1, article2]

        # Create mock response_pass with matching DOIs
        response1 = MagicMock()
        response1.model_fields = ["title", "summary"]
        response1.title = "Title 1"
        response1.summary = "Summary 1"

        response2 = MagicMock()
        response2.model_fields = ["title", "summary"]
        response2.title = "Title 2"
        response2.summary = "Summary 2"

        response_pass = {
            "10.1234/test1": response1,
            "10.1234/test2": response2,
        }

        articles_pass, articles_fail = split_by_qc(
            articles, response_pass, allow_errors=False, merge_key="doi"
        )

        assert len(articles_pass) == 2
        assert len(articles_fail) == 0
        assert article1 in articles_pass
        assert article2 in articles_pass

    def test_split_all_fail(self):
        """Test split when all articles fail QC (not in response_pass)"""
        article1 = MagicMock()
        article1.doi = "10.1234/test1"
        article2 = MagicMock()
        article2.doi = "10.1234/test2"
        articles = [article1, article2]

        # Empty response_pass
        response_pass = {}

        articles_pass, articles_fail = split_by_qc(
            articles, response_pass, allow_errors=True, merge_key="doi"
        )

        assert len(articles_pass) == 0
        assert len(articles_fail) == 2
        assert article1 in articles_fail
        assert article2 in articles_fail

    def test_split_mixed(self):
        """Test split with some passing and some failing"""
        article1 = MagicMock()
        article1.doi = "10.1234/pass"
        article2 = MagicMock()
        article2.doi = "10.1234/fail"
        articles = [article1, article2]

        response1 = MagicMock()
        response1.model_fields = ["title"]
        response1.title = "Title 1"

        response_pass = {"10.1234/pass": response1}

        articles_pass, articles_fail = split_by_qc(
            articles, response_pass, allow_errors=True, merge_key="doi"
        )

        assert len(articles_pass) == 1
        assert len(articles_fail) == 1
        assert article1 in articles_pass
        assert article2 in articles_fail

    def test_split_with_key_error_in_getattr(self):
        """Test split handles KeyError when getting field from response"""
        article = MagicMock()
        article.doi = "10.1234/test"
        articles = [article]

        # Create a custom response class that raises KeyError
        class ResponseWithKeyError:
            model_fields = ["title"]

            def __getattr__(self, name):
                if name == "title":
                    raise KeyError("Field not found")
                raise AttributeError(
                    f"'{type(self).__name__}' object has no attribute '{name}'"
                )

        response = ResponseWithKeyError()
        response_pass = {"10.1234/test": response}

        articles_pass, articles_fail = split_by_qc(
            articles, response_pass, allow_errors=True, merge_key="doi"
        )

        # Article should be in fail list due to KeyError
        assert len(articles_fail) >= 1
        assert article in articles_fail

    def test_split_with_exception_during_setattr(self):
        """Test split handles exceptions during attribute setting"""

        # Create a custom class that raises an exception on setattr
        class ProblematicArticle:
            def __init__(self):
                object.__setattr__(self, "doi", "10.1234/test")

            def __setattr__(self, name, value):
                if name == "title":
                    raise ValidationError(self, "Cannot set title")
                object.__setattr__(self, name, value)

        article = ProblematicArticle()
        articles = [article]

        response = MagicMock()
        response.model_fields = ["title"]
        response.title = "Title"

        response_pass = {"10.1234/test": response}

        articles_pass, articles_fail = split_by_qc(
            articles, response_pass, allow_errors=True, merge_key="doi"
        )

        # Article should only be in fail list when exception occurs during setattr
        assert len(articles_fail) == 1
        assert article in articles_fail
        assert len(articles_pass) == 0
        assert article not in articles_pass

    def test_split_with_custom_merge_key(self):
        """Test split with custom merge key"""
        article = MagicMock()
        article.custom_id = "custom123"
        articles = [article]

        response = MagicMock()
        response.model_fields = ["title"]
        response.title = "Title"

        response_pass = {"custom123": response}

        articles_pass, articles_fail = split_by_qc(
            articles, response_pass, allow_errors=False, merge_key="custom_id"
        )

        assert len(articles_pass) == 1
        assert len(articles_fail) == 0


class TestValidateLlmResponse:
    """Test suite for validate_llm_response function"""

    @patch("common.validation.logging.info")
    @patch("common.validation.logging.debug")
    def test_validate_metadata_response(self, mock_debug, mock_info):
        """Test validating metadata stage response"""
        response_text = json.dumps(
            [
                {
                    "title": "Test Article",
                    "summary": "Test summary",
                    "url": "https://example.com/article",
                    "doi": "10.1234/test",
                }
            ]
        )

        result = validate_llm_response(
            stage="metadata",
            response_text=response_text,
            merge_key="doi",
            allow_qc_errors=False,
        )

        assert "10.1234/test" in result
        assert mock_info.called

    @patch("common.validation.logging.info")
    def test_validate_screening_response(self, mock_info):
        """Test validating screening stage response"""
        response_text = json.dumps(
            [{"doi": "10.1234/test", "decision": True, "reasoning": "Relevant article"}]
        )

        result = validate_llm_response(
            stage="screening",
            response_text=response_text,
            merge_key="doi",
            allow_qc_errors=False,
        )

        assert "10.1234/test" in result
        assert result["10.1234/test"].screening_decision is True

    @patch("common.validation.logging.info")
    def test_validate_priority_response(self, mock_info):
        """Test validating priority stage response"""
        response_text = json.dumps(
            [
                {
                    "doi": "10.1234/test",
                    "decision": "high",
                    "reasoning": "Important findings",
                }
            ]
        )

        result = validate_llm_response(
            stage="priority",
            response_text=response_text,
            merge_key="doi",
            allow_qc_errors=False,
        )

        assert "10.1234/test" in result
        assert result["10.1234/test"].priority_decision == "high"

    @patch("common.validation.logging.info")
    def test_validate_response_with_invalid_item(self, mock_info):
        """Test validation with invalid item (allow errors)"""
        response_text = json.dumps(
            [
                {"doi": "10.1234/valid", "decision": "high", "reasoning": "Good"},
                {"doi": "10.1234/invalid"},  # Missing required fields
            ]
        )

        result = validate_llm_response(
            stage="priority",
            response_text=response_text,
            merge_key="doi",
            allow_qc_errors=True,
        )

        # Only valid item should be in result
        assert "10.1234/valid" in result
        assert "10.1234/invalid" not in result

    @patch("common.validation.logging.info")
    def test_validate_response_pprint_fails(self, mock_info):
        """Test validation when pprint fails on error item"""
        # Create an object that will cause pprint to fail
        response_text = json.dumps([{"invalid": "data"}])

        result = validate_llm_response(
            stage="metadata",
            response_text=response_text,
            merge_key="doi",
            allow_qc_errors=True,
        )

        # Should handle the exception and return empty result
        assert len(result) == 0

    @patch("common.validation.logging.info")
    @patch("common.validation.logging.debug")
    def test_validate_response_multiple_items(self, mock_debug, mock_info):
        """Test validation with multiple valid items"""
        response_text = json.dumps(
            [
                {"doi": "10.1234/test1", "decision": True, "reasoning": "Relevant"},
                {
                    "doi": "10.1234/test2",
                    "decision": False,
                    "reasoning": "Not relevant",
                },
            ]
        )

        result = validate_llm_response(
            stage="screening",
            response_text=response_text,
            merge_key="doi",
            allow_qc_errors=False,
        )

        assert len(result) == 2
        assert "10.1234/test1" in result
        assert "10.1234/test2" in result


class TestSaveValidatedResponses:
    """Test suite for save_validated_responses function"""

    @patch("common.validation.logging.info")
    @patch("common.validation.logging.debug")
    @patch("builtins.open", create=True)
    def test_save_with_pass_and_fail(self, mock_open_func, mock_debug, mock_info):
        """Test saving when there are both passing and failing articles"""
        # Create mock articles
        article_pass = MagicMock()
        article_pass.doi = "10.1234/pass"
        article_fail = MagicMock()
        article_fail.doi = "10.1234/fail"
        articles = [article_pass, article_fail]

        # Create response_pass
        response = MagicMock()
        response.model_fields = ["title"]
        response.title = "Title"
        response_pass = {"10.1234/pass": response}

        # Mock file operations
        mock_file = MagicMock()
        mock_open_func.return_value.__enter__.return_value = mock_file

        save_validated_responses(
            articles=articles,
            response_pass=response_pass,
            allow_qc_errors=True,
            stage="screening",
            merge_key="doi",
        )

        # Should open two files (pass and fail)
        assert mock_open_func.call_count == 2
        assert mock_info.called

    @patch("common.validation.logging.info")
    @patch("common.validation.logging.debug")
    @patch("builtins.open", create=True)
    def test_save_only_pass(self, mock_open_func, mock_debug, mock_info):
        """Test saving when all articles pass"""
        article = MagicMock()
        article.doi = "10.1234/pass"
        articles = [article]

        response = MagicMock()
        response.model_fields = ["title"]
        response.title = "Title"
        response_pass = {"10.1234/pass": response}

        mock_file = MagicMock()
        mock_open_func.return_value.__enter__.return_value = mock_file

        save_validated_responses(
            articles=articles,
            response_pass=response_pass,
            allow_qc_errors=False,
            stage="priority",
            merge_key="doi",
        )

        # Should only open pass file
        assert mock_open_func.call_count == 1
        mock_open_func.assert_called_with("priority_pass.json", "w")

    @patch("common.validation.logging.info")
    @patch("common.validation.logging.debug")
    @patch("builtins.open", create=True)
    def test_save_only_fail(self, mock_open_func, mock_debug, mock_info):
        """Test saving when all articles fail"""
        article = MagicMock()
        article.doi = "10.1234/fail"
        articles = [article]

        response_pass = {}  # Empty, so article will fail

        mock_file = MagicMock()
        mock_open_func.return_value.__enter__.return_value = mock_file

        save_validated_responses(
            articles=articles,
            response_pass=response_pass,
            allow_qc_errors=True,
            stage="metadata",
            merge_key="doi",
        )

        # Should only open fail file
        assert mock_open_func.call_count == 1
        mock_open_func.assert_called_with("metadata_fail.json", "w")

    @patch("common.validation.logging.info")
    @patch("common.validation.logging.debug")
    def test_save_empty_lists(self, mock_debug, mock_info):
        """Test saving when there are no articles"""
        articles = []
        response_pass = {}

        save_validated_responses(
            articles=articles,
            response_pass=response_pass,
            allow_qc_errors=True,
            stage="screening",
            merge_key="doi",
        )

        # Should complete without error
        assert mock_info.called

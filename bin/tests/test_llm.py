#!/usr/bin/env python
"""Tests for common/llm.py"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add the parent directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.llm import llm_query
from common.models import Article


class TestLlmQuery:
    """Test suite for llm_query function"""

    @pytest.fixture
    def sample_articles(self):
        """Sample articles for testing"""
        from datetime import date

        return [
            Article(
                title="Test Article 1",
                url="https://example.com/article1",
                journal_name="Test Journal",
                date=date(2024, 1, 1),
                access_date=date(2024, 1, 15),
                raw_contents="Content 1",
            ),
            Article(
                title="Test Article 2",
                url="https://example.com/article2",
                journal_name="Test Journal",
                date=date(2024, 1, 2),
                access_date=date(2024, 1, 15),
                raw_contents="Content 2",
            ),
        ]

    @pytest.fixture
    def mock_system_prompt(self, tmp_path):
        """Create a mock system prompt file"""
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("System prompt for testing")
        return str(prompt_file)

    @pytest.fixture
    def mock_research_interests(self, tmp_path):
        """Create a mock research interests file"""
        interests_file = tmp_path / "interests.md"
        interests_file.write_text("AI and machine learning")
        return str(interests_file)

    def test_llm_query_raises_error_without_api_key(
        self, sample_articles, mock_system_prompt
    ):
        """Test that llm_query raises ValueError when API key is missing"""
        with pytest.raises(
            ValueError, match="GOOGLE_API_KEY environment variable not found"
        ):
            llm_query(
                articles=sample_articles,
                system_prompt_path=mock_system_prompt,
                model="gemini-1.5-flash",
                api_key="",
                research_interests_path=None,
                tools=[],
            )

    def test_llm_query_raises_error_with_none_api_key(
        self, sample_articles, mock_system_prompt
    ):
        """Test that llm_query raises ValueError when API key is None"""
        with pytest.raises(
            ValueError, match="GOOGLE_API_KEY environment variable not found"
        ):
            llm_query(
                articles=sample_articles,
                system_prompt_path=mock_system_prompt,
                model="gemini-1.5-flash",
                api_key=None,
                research_interests_path=None,
                tools=[],
            )

    @patch("common.llm.genai.Client")
    def test_llm_query_basic_success(
        self, mock_client_class, sample_articles, mock_system_prompt
    ):
        """Test successful basic LLM query without research interests"""
        # Setup mock client and response
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.text = '{"articles": []}'
        mock_client.models.generate_content.return_value = mock_response

        # Execute
        result = llm_query(
            articles=sample_articles,
            system_prompt_path=mock_system_prompt,
            model="gemini-1.5-flash",
            api_key="test-api-key",  # pragma: allowlist secret
            research_interests_path=None,
            tools=[],
        )

        # Verify
        assert result == '{"articles": []}'
        mock_client_class.assert_called_once_with(
            api_key="test-api-key"  # noqa: S106  # pragma: allowlist secret
        )
        mock_client.models.generate_content.assert_called_once()

        # Check that the call included the correct model
        call_kwargs = mock_client.models.generate_content.call_args[1]
        assert call_kwargs["model"] == "gemini-1.5-flash"

    @patch("common.llm.genai.Client")
    def test_llm_query_with_research_interests(
        self,
        mock_client_class,
        sample_articles,
        mock_system_prompt,
        mock_research_interests,
    ):
        """Test LLM query with research interests file"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.text = '{"articles": []}'
        mock_client.models.generate_content.return_value = mock_response

        # Execute
        result = llm_query(
            articles=sample_articles,
            system_prompt_path=mock_system_prompt,
            model="gemini-2.5-flash-lite",
            api_key="test-api-key",  # pragma: allowlist secret
            research_interests_path=mock_research_interests,
            tools=[],
        )

        # Verify
        assert result == '{"articles": []}'
        mock_client.models.generate_content.assert_called_once()

    @patch("common.llm.genai.Client")
    def test_llm_query_with_tools(
        self, mock_client_class, sample_articles, mock_system_prompt
    ):
        """Test LLM query with tools"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.text = "LLM response with tool usage"
        mock_client.models.generate_content.return_value = mock_response

        # Create mock tools
        def mock_tool_1():
            pass

        def mock_tool_2():
            pass

        tools = [mock_tool_1, mock_tool_2]

        # Execute
        result = llm_query(
            articles=sample_articles,
            system_prompt_path=mock_system_prompt,
            model="gemini-1.5-flash",
            api_key="test-api-key",  # pragma: allowlist secret
            research_interests_path=None,
            tools=tools,
        )

        # Verify
        assert result == "LLM response with tool usage"

        # Check that tools were passed in the config
        call_kwargs = mock_client.models.generate_content.call_args[1]
        assert call_kwargs["config"].tools == tools

    @patch("common.llm.genai.Client")
    def test_llm_query_different_models(
        self, mock_client_class, sample_articles, mock_system_prompt
    ):
        """Test LLM query with different model names"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.text = "Response"
        mock_client.models.generate_content.return_value = mock_response

        models = ["gemini-1.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"]

        for model in models:
            # Execute
            llm_query(
                articles=sample_articles,
                system_prompt_path=mock_system_prompt,
                model=model,
                api_key="test-api-key",  # pragma: allowlist secret
                research_interests_path=None,
                tools=[],
            )

            # Verify correct model was used
            call_kwargs = mock_client.models.generate_content.call_args[1]
            assert call_kwargs["model"] == model

    @patch("common.llm.genai.Client")
    def test_llm_query_strips_response_text(
        self, mock_client_class, sample_articles, mock_system_prompt
    ):
        """Test that LLM response text is stripped of whitespace"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.text = "  \n  Response with whitespace  \n  "
        mock_client.models.generate_content.return_value = mock_response

        # Execute
        result = llm_query(
            articles=sample_articles,
            system_prompt_path=mock_system_prompt,
            model="gemini-1.5-flash",
            api_key="test-api-key",  # pragma: allowlist secret
            research_interests_path=None,
            tools=[],
        )

        # Verify whitespace was stripped
        assert result == "Response with whitespace"

    @patch("common.llm.genai.Client")
    def test_llm_query_builds_correct_context(
        self, mock_client_class, sample_articles, mock_system_prompt
    ):
        """Test that the context is built correctly for the LLM"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.text = "Response"
        mock_client.models.generate_content.return_value = mock_response

        # Execute
        llm_query(
            articles=sample_articles,
            system_prompt_path=mock_system_prompt,
            model="gemini-1.5-flash",
            api_key="test-api-key",  # pragma: allowlist secret
            research_interests_path=None,
            tools=[],
        )

        # Verify context structure
        call_kwargs = mock_client.models.generate_content.call_args[1]
        contents = call_kwargs["contents"]

        # Should have 3 parts: user prompt, model acknowledgment, user articles
        assert len(contents) == 3
        assert contents[0].role == "user"
        assert contents[1].role == "model"
        assert contents[2].role == "user"

    @patch("common.llm.genai.Client")
    def test_llm_query_thinking_config_disabled(
        self, mock_client_class, sample_articles, mock_system_prompt
    ):
        """Test that thinking is disabled in the config"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.text = "Response"
        mock_client.models.generate_content.return_value = mock_response

        # Execute
        llm_query(
            articles=sample_articles,
            system_prompt_path=mock_system_prompt,
            model="gemini-1.5-flash",
            api_key="test-api-key",  # pragma: allowlist secret
            research_interests_path=None,
            tools=[],
        )

        # Verify thinking is disabled
        call_kwargs = mock_client.models.generate_content.call_args[1]
        assert call_kwargs["config"].thinking_config.include_thoughts is False

    @patch("common.llm.genai.Client")
    def test_llm_query_with_empty_articles_list(
        self, mock_client_class, mock_system_prompt
    ):
        """Test LLM query with empty articles list"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.text = '{"articles": []}'
        mock_client.models.generate_content.return_value = mock_response

        # Execute with empty list
        result = llm_query(
            articles=[],
            system_prompt_path=mock_system_prompt,
            model="gemini-1.5-flash",
            api_key="test-api-key",  # pragma: allowlist secret
            research_interests_path=None,
            tools=[],
        )

        # Verify it completes successfully
        assert result == '{"articles": []}'
        mock_client.models.generate_content.assert_called_once()

    @patch("common.llm.genai.Client")
    def test_llm_query_reads_system_prompt_file(
        self, mock_client_class, sample_articles, tmp_path
    ):
        """Test that system prompt is correctly read from file"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.text = "Response"
        mock_client.models.generate_content.return_value = mock_response

        # Create prompt file with specific content
        prompt_file = tmp_path / "custom_prompt.md"
        custom_prompt = "Custom system instruction for testing"
        prompt_file.write_text(custom_prompt)

        # Execute
        llm_query(
            articles=sample_articles,
            system_prompt_path=str(prompt_file),
            model="gemini-1.5-flash",
            api_key="test-api-key",  # pragma: allowlist secret
            research_interests_path=None,
            tools=[],
        )

        # Verify system prompt was included in context
        call_kwargs = mock_client.models.generate_content.call_args[1]
        contents = call_kwargs["contents"]
        assert custom_prompt in contents[0].parts[0].text

    @patch("common.llm.genai.Client")
    def test_llm_query_formats_research_interests_into_prompt(
        self, mock_client_class, sample_articles, tmp_path
    ):
        """Test that research interests are formatted into system prompt"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.text = "Response"
        mock_client.models.generate_content.return_value = mock_response

        # Create prompt with placeholder
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("Research interests: {research_interests}")

        # Create research interests file
        interests_file = tmp_path / "interests.md"
        interests_file.write_text("AI and machine learning")

        # Execute
        llm_query(
            articles=sample_articles,
            system_prompt_path=str(prompt_file),
            model="gemini-1.5-flash",
            api_key="test-api-key",  # pragma: allowlist secret
            research_interests_path=str(interests_file),
            tools=[],
        )

        # Verify research interests were inserted
        call_kwargs = mock_client.models.generate_content.call_args[1]
        contents = call_kwargs["contents"]
        assert "AI and machine learning" in contents[0].parts[0].text

    @patch("common.llm.genai.Client")
    def test_llm_query_includes_articles_in_prompt(
        self, mock_client_class, sample_articles, mock_system_prompt
    ):
        """Test that articles are included in the user prompt"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.text = "Response"
        mock_client.models.generate_content.return_value = mock_response

        # Execute
        llm_query(
            articles=sample_articles,
            system_prompt_path=mock_system_prompt,
            model="gemini-1.5-flash",
            api_key="test-api-key",  # pragma: allowlist secret
            research_interests_path=None,
            tools=[],
        )

        # Verify articles are in the prompt
        call_kwargs = mock_client.models.generate_content.call_args[1]
        contents = call_kwargs["contents"]
        articles_prompt = contents[2].parts[0].text

        assert "Here are the articles:" in articles_prompt
        assert "Test Article 1" in articles_prompt
        assert "Test Article 2" in articles_prompt

    @patch("common.llm.genai.Client")
    def test_llm_query_with_whitespace_in_prompt_file(
        self, mock_client_class, sample_articles, tmp_path
    ):
        """Test that whitespace is stripped from prompt file"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.text = "Response"
        mock_client.models.generate_content.return_value = mock_response

        # Create prompt file with whitespace
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("  \n  System prompt  \n  ")

        # Execute
        llm_query(
            articles=sample_articles,
            system_prompt_path=str(prompt_file),
            model="gemini-1.5-flash",
            api_key="test-api-key",  # pragma: allowlist secret
            research_interests_path=None,
            tools=[],
        )

        # Verify whitespace was stripped
        call_kwargs = mock_client.models.generate_content.call_args[1]
        contents = call_kwargs["contents"]
        assert contents[0].parts[0].text == "System prompt"

    @patch("common.llm.genai.Client")
    def test_llm_query_with_whitespace_in_research_interests(
        self, mock_client_class, sample_articles, tmp_path
    ):
        """Test that whitespace is stripped from research interests file"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.text = "Response"
        mock_client.models.generate_content.return_value = mock_response

        # Create files
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("Interests: {research_interests}")

        interests_file = tmp_path / "interests.md"
        interests_file.write_text("  \n  AI research  \n  ")

        # Execute
        llm_query(
            articles=sample_articles,
            system_prompt_path=str(prompt_file),
            model="gemini-1.5-flash",
            api_key="test-api-key",  # pragma: allowlist secret
            research_interests_path=str(interests_file),
            tools=[],
        )

        # Verify whitespace was stripped
        call_kwargs = mock_client.models.generate_content.call_args[1]
        contents = call_kwargs["contents"]
        assert "AI research" in contents[0].parts[0].text
        assert "  \n  " not in contents[0].parts[0].text

    @patch("common.llm.genai.Client")
    def test_llm_query_model_acknowledgment_message(
        self, mock_client_class, sample_articles, mock_system_prompt
    ):
        """Test that the model acknowledgment message is correct"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.text = "Response"
        mock_client.models.generate_content.return_value = mock_response

        # Execute
        llm_query(
            articles=sample_articles,
            system_prompt_path=mock_system_prompt,
            model="gemini-1.5-flash",
            api_key="test-api-key",  # pragma: allowlist secret
            research_interests_path=None,
            tools=[],
        )

        # Verify model acknowledgment
        call_kwargs = mock_client.models.generate_content.call_args[1]
        contents = call_kwargs["contents"]
        acknowledgment = contents[1].parts[0].text

        assert "Understood" in acknowledgment
        assert "analyze the articles" in acknowledgment
        assert "Please provide the articles" in acknowledgment

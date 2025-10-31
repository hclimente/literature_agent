#!/usr/bin/env python
"""Tests for tools/metadata_tools.py"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch
import requests

# Add the parent directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.metadata_tools import (
    get_doi_for_arxiv_url,
    get_abstract_from_doi,
    springer_get_abstract_from_doi,
)


class TestGetDoiForArxivUrl:
    """Test suite for get_doi_for_arxiv_url function"""

    def test_get_doi_for_arxiv_url_basic(self):
        """Test basic arXiv URL to DOI conversion"""
        arxiv_url = "https://arxiv.org/abs/2301.12345"
        result = get_doi_for_arxiv_url(arxiv_url)

        assert result == "10.48550/arXiv.2301.12345"

    def test_get_doi_for_arxiv_url_with_trailing_slash(self):
        """Test arXiv URL with trailing slash"""
        arxiv_url = "https://arxiv.org/abs/2301.12345/"
        result = get_doi_for_arxiv_url(arxiv_url)

        assert result == "10.48550/arXiv.2301.12345"

    def test_get_doi_for_arxiv_url_different_versions(self):
        """Test arXiv URL with version number"""
        arxiv_url = "https://arxiv.org/abs/2301.12345v2"
        result = get_doi_for_arxiv_url(arxiv_url)

        assert result == "10.48550/arXiv.2301.12345v2"

    def test_get_doi_for_arxiv_url_old_format(self):
        """Test arXiv URL with old identifier format (only extracts last part)"""
        arxiv_url = "https://arxiv.org/abs/math/0601001"
        result = get_doi_for_arxiv_url(arxiv_url)

        # Note: The function only extracts the last part after the final '/'
        assert result == "10.48550/arXiv.0601001"

    def test_get_doi_for_arxiv_url_pdf_link(self):
        """Test arXiv PDF URL"""
        arxiv_url = "https://arxiv.org/pdf/2301.12345.pdf"
        result = get_doi_for_arxiv_url(arxiv_url)

        assert result == "10.48550/arXiv.2301.12345.pdf"


class TestGetAbstractFromDoi:
    """Test suite for get_abstract_from_doi function"""

    @pytest.fixture
    def mock_esearch_response(self):
        """Create a mock ESearch response XML"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <eSearchResult>
            <IdList>
                <Id>12345678</Id>
            </IdList>
        </eSearchResult>
        """
        return xml_content

    @pytest.fixture
    def mock_efetch_response(self):
        """Create a mock EFetch response XML"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <Article>
                        <Abstract>
                            <AbstractText>This is a test abstract from PubMed.</AbstractText>
                        </Abstract>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        return xml_content

    @pytest.fixture
    def mock_efetch_structured_abstract(self):
        """Create a mock EFetch response with structured abstract"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <Article>
                        <Abstract>
                            <AbstractText Label="BACKGROUND">Background information here.</AbstractText>
                            <AbstractText Label="METHODS">Methods used in the study.</AbstractText>
                            <AbstractText Label="RESULTS">Results of the study.</AbstractText>
                        </Abstract>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        return xml_content

    @pytest.fixture
    def mock_esearch_no_pmid(self):
        """Create a mock ESearch response with no PMID"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <eSearchResult>
            <IdList>
            </IdList>
        </eSearchResult>
        """
        return xml_content

    @pytest.fixture
    def mock_efetch_no_abstract(self):
        """Create a mock EFetch response without abstract"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <Article>
                        <ArticleTitle>Test Article</ArticleTitle>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        return xml_content

    @patch("tools.metadata_tools.get_env_variable")
    @patch("tools.metadata_tools.requests.get")
    def test_get_abstract_from_doi_success(
        self, mock_get, mock_env, mock_esearch_response, mock_efetch_response
    ):
        """Test successful abstract retrieval"""
        mock_env.return_value = "test@example.com"

        # Mock the two API calls
        mock_esearch = Mock()
        mock_esearch.content = mock_esearch_response.encode()
        mock_esearch.raise_for_status = Mock()

        mock_efetch = Mock()
        mock_efetch.content = mock_efetch_response.encode()
        mock_efetch.raise_for_status = Mock()

        mock_get.side_effect = [mock_esearch, mock_efetch]

        result = get_abstract_from_doi("10.1234/test")

        assert result == "This is a test abstract from PubMed."
        assert mock_get.call_count == 2

    @patch("tools.metadata_tools.get_env_variable")
    @patch("tools.metadata_tools.requests.get")
    def test_get_abstract_from_doi_structured_abstract(
        self, mock_get, mock_env, mock_esearch_response, mock_efetch_structured_abstract
    ):
        """Test retrieval of structured abstract"""
        mock_env.return_value = "test@example.com"

        mock_esearch = Mock()
        mock_esearch.content = mock_esearch_response.encode()
        mock_esearch.raise_for_status = Mock()

        mock_efetch = Mock()
        mock_efetch.content = mock_efetch_structured_abstract.encode()
        mock_efetch.raise_for_status = Mock()

        mock_get.side_effect = [mock_esearch, mock_efetch]

        result = get_abstract_from_doi("10.1234/test")

        assert "Background information here." in result
        assert "Methods used in the study." in result
        assert "Results of the study." in result
        # Check that parts are separated by double newlines
        assert "\n\n" in result

    @patch("tools.metadata_tools.get_env_variable")
    @patch("tools.metadata_tools.requests.get")
    def test_get_abstract_from_doi_no_pmid_found(
        self, mock_get, mock_env, mock_esearch_no_pmid
    ):
        """Test handling when no PMID is found for DOI"""
        mock_env.return_value = "test@example.com"

        mock_esearch = Mock()
        mock_esearch.content = mock_esearch_no_pmid.encode()
        mock_esearch.raise_for_status = Mock()

        mock_get.return_value = mock_esearch

        result = get_abstract_from_doi("10.1234/nonexistent")

        assert result is None

    @patch("tools.metadata_tools.get_env_variable")
    @patch("tools.metadata_tools.requests.get")
    def test_get_abstract_from_doi_no_abstract_found(
        self, mock_get, mock_env, mock_esearch_response, mock_efetch_no_abstract
    ):
        """Test handling when PMID exists but no abstract is available"""
        mock_env.return_value = "test@example.com"

        mock_esearch = Mock()
        mock_esearch.content = mock_esearch_response.encode()
        mock_esearch.raise_for_status = Mock()

        mock_efetch = Mock()
        mock_efetch.content = mock_efetch_no_abstract.encode()
        mock_efetch.raise_for_status = Mock()

        mock_get.side_effect = [mock_esearch, mock_efetch]

        result = get_abstract_from_doi("10.1234/test")

        assert result is None

    @patch("tools.metadata_tools.get_env_variable")
    @patch("tools.metadata_tools.requests.get")
    def test_get_abstract_from_doi_network_error(self, mock_get, mock_env):
        """Test handling of network errors"""
        mock_env.return_value = "test@example.com"
        mock_get.side_effect = requests.exceptions.RequestException("Connection failed")

        result = get_abstract_from_doi("10.1234/test")

        assert "Network or API Error" in result

    @patch("tools.metadata_tools.get_env_variable")
    @patch("tools.metadata_tools.requests.get")
    def test_get_abstract_from_doi_parsing_error(self, mock_get, mock_env):
        """Test handling of XML parsing errors"""
        mock_env.return_value = "test@example.com"

        mock_response = Mock()
        mock_response.content = b"Invalid XML <>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = get_abstract_from_doi("10.1234/test")

        assert "Parsing Error" in result

    @patch("tools.metadata_tools.get_env_variable")
    @patch("tools.metadata_tools.requests.get")
    def test_get_abstract_from_doi_http_error(self, mock_get, mock_env):
        """Test handling of HTTP errors"""
        mock_env.return_value = "test@example.com"

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found"
        )
        mock_get.return_value = mock_response

        result = get_abstract_from_doi("10.1234/test")

        assert "Network or API Error" in result


class TestSpringerGetAbstractFromDoi:
    """Test suite for springer_get_abstract_from_doi function"""

    @pytest.fixture
    def mock_springer_response(self):
        """Create a mock Springer API response"""
        return {
            "records": [
                {
                    "abstract": "This is a test abstract from Springer Nature.",
                    "title": "Test Article",
                    "doi": "10.1234/test",
                }
            ]
        }

    @pytest.fixture
    def mock_springer_response_html_abstract(self):
        """Create a mock Springer API response with HTML in abstract"""
        return {
            "records": [
                {
                    "abstract": "<p>This is a test abstract with <i>italic</i> text.</p>",
                    "title": "Test Article",
                }
            ]
        }

    @pytest.fixture
    def mock_springer_no_records(self):
        """Create a mock Springer API response with no records"""
        return {"records": []}

    @pytest.fixture
    def mock_springer_no_abstract(self):
        """Create a mock Springer API response without abstract"""
        return {"records": [{"title": "Test Article", "doi": "10.1234/test"}]}

    @patch("tools.metadata_tools.get_env_variable")
    @patch("tools.metadata_tools.requests.get")
    def test_springer_get_abstract_success(
        self, mock_get, mock_env, mock_springer_response
    ):
        """Test successful abstract retrieval from Springer"""
        mock_env.return_value = "fake_api_key"

        mock_response = Mock()
        mock_response.json.return_value = mock_springer_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = springer_get_abstract_from_doi("10.1234/test")

        assert result == "This is a test abstract from Springer Nature."
        mock_get.assert_called_once()

    @patch("tools.metadata_tools.get_env_variable")
    @patch("tools.metadata_tools.requests.get")
    def test_springer_get_abstract_with_html(
        self, mock_get, mock_env, mock_springer_response_html_abstract
    ):
        """Test abstract retrieval with HTML tags"""
        mock_env.return_value = "fake_api_key"

        mock_response = Mock()
        mock_response.json.return_value = mock_springer_response_html_abstract
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = springer_get_abstract_from_doi("10.1234/test")

        assert result == "<p>This is a test abstract with <i>italic</i> text.</p>"

    @patch("tools.metadata_tools.get_env_variable")
    @patch("tools.metadata_tools.requests.get")
    def test_springer_get_abstract_no_records(
        self, mock_get, mock_env, mock_springer_no_records
    ):
        """Test handling when no records are found"""
        mock_env.return_value = "fake_api_key"

        mock_response = Mock()
        mock_response.json.return_value = mock_springer_no_records
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = springer_get_abstract_from_doi("10.1234/nonexistent")

        assert result is None

    @patch("tools.metadata_tools.get_env_variable")
    @patch("tools.metadata_tools.requests.get")
    def test_springer_get_abstract_no_abstract_field(
        self, mock_get, mock_env, mock_springer_no_abstract
    ):
        """Test handling when record exists but has no abstract"""
        mock_env.return_value = "fake_api_key"

        mock_response = Mock()
        mock_response.json.return_value = mock_springer_no_abstract
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = springer_get_abstract_from_doi("10.1234/test")

        assert result is None

    @patch("tools.metadata_tools.get_env_variable")
    @patch("tools.metadata_tools.requests.get")
    def test_springer_get_abstract_http_error(self, mock_get, mock_env):
        """Test handling of HTTP errors"""
        mock_env.return_value = "fake_api_key"

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "401 Unauthorized"
        )
        mock_get.return_value = mock_response

        result = springer_get_abstract_from_doi("10.1234/test")

        assert "HTTP error occurred" in result

    @patch("tools.metadata_tools.get_env_variable")
    @patch("tools.metadata_tools.requests.get")
    def test_springer_get_abstract_request_error(self, mock_get, mock_env):
        """Test handling of request errors"""
        mock_env.return_value = "fake_api_key"
        mock_get.side_effect = requests.exceptions.RequestException(
            "Connection timeout"
        )

        result = springer_get_abstract_from_doi("10.1234/test")

        assert "Request error occurred" in result

    @patch("tools.metadata_tools.get_env_variable")
    @patch("tools.metadata_tools.requests.get")
    def test_springer_get_abstract_json_parsing_error(self, mock_get, mock_env):
        """Test handling of JSON parsing errors"""
        mock_env.return_value = "fake_api_key"

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        # Simulate malformed JSON response that causes KeyError
        mock_response.json.return_value = {"unexpected_key": "value"}
        mock_get.return_value = mock_response

        result = springer_get_abstract_from_doi("10.1234/test")

        # Should return None when 'records' key is missing
        assert result is None

    @patch("tools.metadata_tools.get_env_variable")
    @patch("tools.metadata_tools.requests.get")
    def test_springer_get_abstract_api_key_usage(self, mock_get, mock_env):
        """Test that API key is properly used in request"""
        mock_env.return_value = "test_api_key_12345"

        mock_response = Mock()
        mock_response.json.return_value = {"records": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        springer_get_abstract_from_doi("10.1234/test")

        # Verify the API key was used in the request
        call_args = mock_get.call_args
        # fmt: off
        assert call_args[1]["params"]["api_key"] == "test_api_key_12345"  # pragma: allowlist secret
        # fmt: on
        assert call_args[1]["params"]["q"] == "doi:10.1234/test"

    @patch("tools.metadata_tools.get_env_variable")
    @patch("tools.metadata_tools.requests.get")
    def test_springer_get_abstract_timeout(self, mock_get, mock_env):
        """Test that timeout is set in request"""
        mock_env.return_value = "fake_api_key"

        mock_response = Mock()
        mock_response.json.return_value = {"records": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        springer_get_abstract_from_doi("10.1234/test")

        # Verify timeout was set
        call_args = mock_get.call_args
        assert call_args[1]["timeout"] == 10

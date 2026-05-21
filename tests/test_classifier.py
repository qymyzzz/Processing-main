"""Tests for the classifier module."""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os

from app.classifier import classify_rule_based, classify_gemini
import app.classifier as classifier


class TestClassifyRuleBased:
    """Tests for rule-based classification."""

    def test_classify_integration_keywords(self):
        """Test classification of integration-related issues."""
        text = "Our webhook integration is not working"
        result = classify_rule_based(text)
        assert result == "Интеграции"

    def test_classify_incident_keywords(self):
        """Test classification of incident-related issues."""
        text = "The system is not working and shows error 500"
        result = classify_rule_based(text)
        assert result == "Инциденты"

    def test_classify_operational_keywords(self):
        """Test classification of operational issues."""
        text = "I need access to the reporting system"
        result = classify_rule_based(text)
        assert result == "Операционная работа"

    def test_classify_case_insensitive(self):
        """Test that classification is case-insensitive."""
        text = "API problem"
        result = classify_rule_based(text)
        assert result == "Интеграции"

    def test_classify_multiple_keywords(self):
        """Test classification with multiple relevant keywords."""
        text = "API error and webhook integration is down"
        result = classify_rule_based(text)
        # Should have higher score for integration category
        assert result in ["Интеграции", "Инциденты"]

    def test_classify_no_keywords_defaults(self):
        """Test that unknown text defaults to operational."""
        text = "asdfghjkl random text with no keywords"
        result = classify_rule_based(text)
        assert result == "Операционная работа"

    def test_classify_empty_string(self):
        """Test classification of empty string."""
        result = classify_rule_based("")
        assert result == "Операционная работа"


class TestClassifyGemini:
    """Tests for Gemini-based classification."""

    @patch("app.classifier.gemini_client")
    def test_classify_gemini_success(self, mock_client):
        """Test successful Gemini classification."""
        mock_response = MagicMock()
        mock_response.text = "Инциденты"
        mock_client.models.generate_content.return_value = mock_response

        result = classify_gemini("System is down")
        assert result == "Инциденты"

    @patch("app.classifier.gemini_client")
    def test_classify_gemini_partial_match(self, mock_client):
        """Test Gemini classification with partial category match."""
        mock_response = MagicMock()
        mock_response.text = "The issue is related to Инциденты"
        mock_client.models.generate_content.return_value = mock_response

        result = classify_gemini("Something broke")
        assert result == "Инциденты"

    @patch("app.classifier.gemini_client")
    def test_classify_gemini_invalid_response(self, mock_client):
        """Test Gemini classification with invalid response."""
        mock_response = MagicMock()
        mock_response.text = "Unknown category"
        mock_client.models.generate_content.return_value = mock_response

        result = classify_gemini("Some issue")
        assert result == ""

    @patch("app.classifier.gemini_client")
    def test_classify_gemini_api_error(self, mock_client):
        """Test Gemini classification with API error."""
        mock_client.models.generate_content.side_effect = Exception("API Error")

        result = classify_gemini("Some issue")
        assert result == ""

    @patch("app.classifier.gemini_client")
    def test_classify_gemini_whitespace_stripping(self, mock_client):
        """Test that Gemini response whitespace is stripped."""
        mock_response = MagicMock()
        mock_response.text = "  Интеграции  \n"
        mock_client.models.generate_content.return_value = mock_response

        result = classify_gemini("API integration issue")
        assert result == "Интеграции"

    @patch("app.classifier.sanitize")
    @patch("app.classifier.gemini_client")
    def test_classify_gemini_sanitizes_input(self, mock_client, mock_sanitize):
        """Test that text is sanitized before sending to Gemini."""
        mock_sanitize.return_value = "Sanitized text"
        mock_response = MagicMock()
        mock_response.text = "Операционная работа"
        mock_client.models.generate_content.return_value = mock_response

        result = classify_gemini("Original text")

        mock_sanitize.assert_called_once_with("Original text")
        assert result == "Операционная работа"

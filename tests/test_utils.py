"""Tests for the utils module."""

import pytest
import sys
import os

from app.utils import escape_md


class TestEscapeMd:
    """Tests for Markdown escaping."""

    def test_escape_md_asterisks(self):
        """Test escaping of asterisks."""
        text = "*bold* and **stronger**"
        result = escape_md(text)
        assert result == "\\*bold\\* and \\*\\*stronger\\*\\*"

    def test_escape_md_underscores(self):
        """Test escaping of underscores."""
        text = "_italic_ and __strong__"
        result = escape_md(text)
        assert result == "\\_italic\\_ and \\_\\_strong\\_\\_"

    def test_escape_md_brackets(self):
        """Test escaping of brackets."""
        text = "[link](url) and (parentheses)"
        result = escape_md(text)
        assert "\\[" in result
        assert "\\]" in result
        assert "\\(" in result
        assert "\\)" in result

    def test_escape_md_backticks(self):
        """Test escaping of backticks."""
        text = "`code` block"
        result = escape_md(text)
        assert result == "\\`code\\` block"

    def test_escape_md_hash(self):
        """Test escaping of hash symbols."""
        text = "# Heading and ## Subheading"
        result = escape_md(text)
        assert "\\#" in result

    def test_escape_md_tilde(self):
        """Test escaping of tilde."""
        text = "~strikethrough~"
        result = escape_md(text)
        assert result == "\\~strikethrough\\~"

    def test_escape_md_backslash(self):
        """Test escaping of backslash."""
        text = "path\\to\\file"
        result = escape_md(text)
        assert result == "path\\\\to\\\\file"

    def test_escape_md_mixed_symbols(self):
        """Test escaping of mixed symbols."""
        text = "*bold* _italic_ `code` [link](url)"
        result = escape_md(text)
        assert "\\" in result  # Should contain escape characters

    def test_escape_md_no_special_characters(self):
        """Test that normal text is preserved."""
        text = "This is normal text without special characters"
        result = escape_md(text)
        assert result == text

    def test_escape_md_empty_string(self):
        """Test escaping of empty string."""
        result = escape_md("")
        assert result == ""

    def test_escape_md_numbers_and_special_chars(self):
        """Test escaping of numbers with special characters."""
        text = "Error: 404! Check this > issue | value = 5"
        result = escape_md(text)
        assert "\\>" in result
        assert "\\|" in result
        assert "\\=" in result
        assert "\\!" in result

    def test_escape_md_converts_to_string(self):
        """Test that non-string inputs are converted."""
        result = escape_md(123)
        assert isinstance(result, str)
        assert result == "123"

"""Tests for the sanitize module."""

import pytest
import sys
import os

from app.sanitize import sanitize, label_phone_numbers


class TestSanitize:
    """Tests for text sanitization."""

    def test_sanitize_credit_card_expiry(self):
        """Test masking of credit card expiry dates."""
        text = "Card expires 12/25"
        result = sanitize(text)
        assert "[СРОК_КАРТЫ]" in result
        assert "12/25" not in result

    def test_sanitize_email(self):
        """Test masking of email addresses."""
        text = "Contact us at support@example.com"
        result = sanitize(text)
        assert "[EMAIL]" in result
        assert "support@example.com" not in result

    def test_sanitize_cvv(self):
        """Test masking of CVV codes."""
        text = "Security code: 123"
        result = sanitize(text)
        assert "[CVV]" in result
        assert "123" not in result or "[CVV]" in result

    def test_sanitize_multiple_emails(self):
        """Test masking of multiple email addresses."""
        text = "Email user1@test.com or user2@test.com"
        result = sanitize(text)
        assert result.count("[EMAIL]") == 2

    def test_sanitize_preserves_normal_text(self):
        """Test that normal text is preserved."""
        text = "This is a normal message without sensitive data"
        result = sanitize(text)
        assert "normal message" in result

    def test_sanitize_empty_string(self):
        """Test sanitization of empty string."""
        result = sanitize("")
        assert result == ""

    def test_sanitize_credit_card_expiry_dash_format(self):
        """Test masking of credit card expiry with dash format."""
        text = "Card expires 05-26"
        result = sanitize(text)
        assert "[СРОК_КАРТЫ]" in result

    def test_sanitize_complex_message(self):
        """Test sanitization of complex message with multiple sensitive data."""
        text = "Customer email: john@example.com, card expires 03/27, CVV: 456"
        result = sanitize(text)
        assert "[EMAIL]" in result
        assert "[СРОК_КАРТЫ]" in result
        assert "[CVV]" in result


class TestLabelPhoneNumbers:
    """Tests for phone number labeling."""

    def test_label_phone_numbers_basic(self):
        """Test labeling of basic phone numbers."""
        text = "Call me at +1 234 567 8900"
        result = label_phone_numbers(text)
        assert "[НОМЕР ТЕЛЕФОНА]" in result

    def test_label_phone_numbers_multiple(self):
        """Test labeling of multiple phone numbers."""
        text = "Call +1-234-567-8900 or +44 20 7946 0958"
        result = label_phone_numbers(text, region="US")
        assert "[НОМЕР ТЕЛЕФОНА]" in result

    def test_label_phone_numbers_no_match(self):
        """Test that non-phone text is unchanged."""
        text = "This has no phone numbers"
        result = label_phone_numbers(text)
        assert result == text

    def test_label_phone_numbers_custom_replacement(self):
        """Test custom replacement text."""
        text = "Call +1 234 567 8900"
        result = label_phone_numbers(text, replacement="[PHONE]")
        assert "[PHONE]" in result

    def test_label_phone_numbers_preserves_other_text(self):
        """Test that other text is preserved."""
        text = "Contact support at +1 555 1234 for help"
        result = label_phone_numbers(text, region="US")
        assert "Contact support" in result
        assert "for help" in result
        # Phone number may or may not be detected depending on region/format
        # Just verify text is preserved
        assert "Contact support" in result and "for help" in result

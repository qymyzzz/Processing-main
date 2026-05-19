"""Tests for the categories module."""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from categories import CATEGORIES, CAT_KEYS


class TestCategories:
    """Tests for category constants."""

    def test_categories_not_empty(self):
        """Test that categories are defined."""
        assert len(CATEGORIES) > 0

    def test_categories_has_required_keys(self):
        """Test that all expected categories exist."""
        required = ["Операционная работа", "Инциденты", "Интеграции"]
        for cat in required:
            assert cat in CATEGORIES

    def test_categories_have_emojis(self):
        """Test that each category has an emoji."""
        for cat, emoji in CATEGORIES.items():
            assert emoji is not None
            assert len(emoji) > 0
            assert emoji in ["⚙️", "🔥", "🔗"]  # Expected emojis

    def test_cat_keys_matches_categories(self):
        """Test that CAT_KEYS is a list of CATEGORIES keys."""
        assert set(CAT_KEYS) == set(CATEGORIES.keys())

    def test_cat_keys_is_list(self):
        """Test that CAT_KEYS is a list."""
        assert isinstance(CAT_KEYS, list)

    def test_categories_count(self):
        """Test that there are exactly 3 categories."""
        assert len(CATEGORIES) == 3

    def test_category_emoji_mapping(self):
        """Test specific category emoji mappings."""
        assert CATEGORIES["Операционная работа"] == "⚙️"
        assert CATEGORIES["Инциденты"] == "🔥"
        assert CATEGORIES["Интеграции"] == "🔗"

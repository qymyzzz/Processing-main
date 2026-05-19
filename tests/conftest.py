"""Shared pytest fixtures and configuration."""

import os
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables for all tests."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")
    monkeypatch.setenv("BUCKET_URL", "https://example.s3.amazonaws.com")
    monkeypatch.setenv("S3_KEY", "tickets.xlsx")
    monkeypatch.setenv("TICKETS_META", "tickets_meta.json")
    monkeypatch.setenv("BOT_TOKEN", "test-token")
    monkeypatch.setenv("SUPPORT_IDS", "123,456,789")


@pytest.fixture
def sample_timestamp():
    """Sample timestamp for testing."""
    return datetime.now(timezone.utc)


@pytest.fixture
def sample_ticket():
    """Sample ticket data."""
    return {
        "ticket_id": "TICKET-001",
        "message_id": "msg-123",
        "chat_id": 1001,
        "chat_title": "Support Group",
        "sender": "John Doe",
        "text": "I have a problem with the API",
        "timestamp": "2024-01-15 10:30:00",
        "rule_cat": "Интеграции",
        "ai_cat": "Интеграции",
        "final_cat": "Интеграции",
        "created_at": "2024-01-15 10:30:00",
        "reply_to": None,
        "resolved": False,
        "assignee": None,
    }


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API response."""
    mock = MagicMock()
    mock.text = "Интеграции"
    return mock

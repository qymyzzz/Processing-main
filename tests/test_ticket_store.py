"""Tests for the ticket_store module."""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime, timezone, timedelta
import json

import app.ticket_system.ticket_store as ticket_store


class TestTicketStore:
    """Tests for ticket storage operations."""

    @pytest.fixture(autouse=True)
    def reset_tickets(self):
        """Reset the global tickets list before each test."""
        ticket_store._tickets = []
        yield
        ticket_store._tickets = []

    def test_add_ticket_basic(self):
        """Test adding a basic ticket."""
        with patch("app.ticket_system.ticket_store.pd.read_excel"), patch(
            "app.ticket_system.ticket_store.pd.concat"
        ), patch.object(ticket_store.pd.DataFrame, "to_excel"):

            ticket = ticket_store.add_ticket(
                chat_id=123,
                chat_title="Support",
                sender="John",
                text="Help needed",
                timestamp="2024-01-15 10:00:00",
                rule_cat="Инциденты",
                ai_cat="Инциденты",
                final_cat="Инциденты",
            )

            assert ticket["ticket_id"] == 1
            assert ticket["sender"] == "John"
            assert ticket["resolved"] is False
            assert ticket["assignee"] == []

    def test_add_ticket_increments_id(self):
        """Test that ticket IDs increment."""
        with patch("app.ticket_system.ticket_store.pd.read_excel"), patch(
            "app.ticket_system.ticket_store.pd.concat"
        ), patch.object(ticket_store.pd.DataFrame, "to_excel"):

            ticket1 = ticket_store.add_ticket(
                chat_id=123,
                chat_title="Support",
                sender="John",
                text="First ticket",
                timestamp="2024-01-15 10:00:00",
                rule_cat="Инциденты",
                ai_cat="Инциденты",
                final_cat="Инциденты",
            )

            ticket2 = ticket_store.add_ticket(
                chat_id=123,
                chat_title="Support",
                sender="Jane",
                text="Second ticket",
                timestamp="2024-01-15 11:00:00",
                rule_cat="Операционная работа",
                ai_cat="Операционная работа",
                final_cat="Операционная работа",
            )

            assert ticket1["ticket_id"] == 1
            assert ticket2["ticket_id"] == 2

    def test_get_tickets_all(self):
        """Test retrieving all tickets."""
        with patch("app.ticket_system.ticket_store.pd.read_excel"), patch(
            "app.ticket_system.ticket_store.pd.concat"
        ), patch.object(ticket_store.pd.DataFrame, "to_excel"):

            ticket_store.add_ticket(
                chat_id=123,
                chat_title="Support",
                sender="John",
                text="Ticket 1",
                timestamp="2024-01-15 10:00:00",
                rule_cat="Инциденты",
                ai_cat="Инциденты",
                final_cat="Инциденты",
            )

            ticket_store.add_ticket(
                chat_id=456,
                chat_title="Other",
                sender="Jane",
                text="Ticket 2",
                timestamp="2024-01-15 11:00:00",
                rule_cat="Операционная работа",
                ai_cat="Операционная работа",
                final_cat="Операционная работа",
            )

            all_tickets = ticket_store.get_tickets()
            assert len(all_tickets) == 2

    def test_get_tickets_by_chat_id(self):
        """Test filtering tickets by chat ID."""
        with patch("app.ticket_system.ticket_store.pd.read_excel"), patch(
            "app.ticket_system.ticket_store.pd.concat"
        ), patch.object(ticket_store.pd.DataFrame, "to_excel"):

            ticket_store.add_ticket(
                chat_id=123,
                chat_title="Support",
                sender="John",
                text="Ticket 1",
                timestamp="2024-01-15 10:00:00",
                rule_cat="Инциденты",
                ai_cat="Инциденты",
                final_cat="Инциденты",
            )

            ticket_store.add_ticket(
                chat_id=456,
                chat_title="Other",
                sender="Jane",
                text="Ticket 2",
                timestamp="2024-01-15 11:00:00",
                rule_cat="Операционная работа",
                ai_cat="Операционная работа",
                final_cat="Операционная работа",
            )

            tickets_123 = ticket_store.get_tickets(chat_id=123)
            assert len(tickets_123) == 1
            assert tickets_123[0]["chat_id"] == 123

    def test_get_tickets_by_sender(self):
        """Test filtering tickets by sender."""
        with patch("app.ticket_system.ticket_store.pd.read_excel"), patch(
            "app.ticket_system.ticket_store.pd.concat"
        ), patch.object(ticket_store.pd.DataFrame, "to_excel"):

            ticket_store.add_ticket(
                chat_id=123,
                chat_title="Support",
                sender="John",
                text="John's ticket",
                timestamp="2024-01-15 10:00:00",
                rule_cat="Инциденты",
                ai_cat="Инциденты",
                final_cat="Инциденты",
            )

            ticket_store.add_ticket(
                chat_id=123,
                chat_title="Support",
                sender="Jane",
                text="Jane's ticket",
                timestamp="2024-01-15 11:00:00",
                rule_cat="Операционная работа",
                ai_cat="Операционная работа",
                final_cat="Операционная работа",
            )

            john_tickets = ticket_store.get_tickets(sender="John")
            assert len(john_tickets) == 1
            assert john_tickets[0]["sender"] == "John"

    def test_get_tickets_by_resolved_status(self):
        """Test filtering tickets by resolved status."""
        with patch("app.ticket_system.ticket_store.pd.read_excel"), patch(
            "app.ticket_system.ticket_store.pd.concat"
        ), patch.object(ticket_store.pd.DataFrame, "to_excel"):

            ticket = ticket_store.add_ticket(
                chat_id=123,
                chat_title="Support",
                sender="John",
                text="Issue",
                timestamp="2024-01-15 10:00:00",
                rule_cat="Инциденты",
                ai_cat="Инциденты",
                final_cat="Инциденты",
            )

            # Resolve the ticket
            ticket_store.resolve_ticket(ticket["ticket_id"])

            unresolved = ticket_store.get_tickets(resolved=False)
            resolved = ticket_store.get_tickets(resolved=True)

            assert len(unresolved) == 0
            assert len(resolved) == 1

    def test_get_ticket_single(self):
        """Test retrieving a single ticket by ID."""
        with patch("app.ticket_system.ticket_store.pd.read_excel"), patch(
            "app.ticket_system.ticket_store.pd.concat"
        ), patch.object(ticket_store.pd.DataFrame, "to_excel"):

            added_ticket = ticket_store.add_ticket(
                chat_id=123,
                chat_title="Support",
                sender="John",
                text="Issue",
                timestamp="2024-01-15 10:00:00",
                rule_cat="Инциденты",
                ai_cat="Инциденты",
                final_cat="Инциденты",
            )

            retrieved = ticket_store.get_ticket(added_ticket["ticket_id"])

            assert retrieved is not None
            assert retrieved["ticket_id"] == added_ticket["ticket_id"]
            assert retrieved["sender"] == "John"

    def test_get_ticket_not_found(self):
        """Test retrieving a non-existent ticket."""
        result = ticket_store.get_ticket(999)
        assert result is None

    def test_resolve_ticket(self):
        """Test resolving a ticket."""
        with patch("app.ticket_system.ticket_store.pd.read_excel"), patch(
            "app.ticket_system.ticket_store.pd.concat"
        ), patch.object(ticket_store.pd.DataFrame, "to_excel"):

            ticket = ticket_store.add_ticket(
                chat_id=123,
                chat_title="Support",
                sender="John",
                text="Issue",
                timestamp="2024-01-15 10:00:00",
                rule_cat="Инциденты",
                ai_cat="Инциденты",
                final_cat="Инциденты",
            )

            result = ticket_store.resolve_ticket(ticket["ticket_id"])
            assert result is True

            resolved_ticket = ticket_store.get_ticket(ticket["ticket_id"])
            assert resolved_ticket["resolved"] is True

    def test_resolve_ticket_not_found(self):
        """Test resolving a non-existent ticket."""
        with patch("app.ticket_system.ticket_store.pd.read_excel"), patch.object(
            ticket_store.pd.DataFrame, "to_excel"
        ):
            result = ticket_store.resolve_ticket(999)
            assert result is False

    def test_unresolve_ticket(self):
        """Test unresolving a ticket."""
        with patch("app.ticket_system.ticket_store.pd.read_excel"), patch(
            "app.ticket_system.ticket_store.pd.concat"
        ), patch.object(ticket_store.pd.DataFrame, "to_excel"):

            ticket = ticket_store.add_ticket(
                chat_id=123,
                chat_title="Support",
                sender="John",
                text="Issue",
                timestamp="2024-01-15 10:00:00",
                rule_cat="Инциденты",
                ai_cat="Инциденты",
                final_cat="Инциденты",
            )

            ticket_store.resolve_ticket(ticket["ticket_id"])
            result = ticket_store.unresolve_ticket(ticket["ticket_id"])
            assert result is True

            ticket_data = ticket_store.get_ticket(ticket["ticket_id"])
            assert ticket_data["resolved"] is False

    def test_add_assignee(self):
        """Test adding an assignee to a ticket."""
        with patch("app.ticket_system.ticket_store.pd.read_excel"), patch(
            "app.ticket_system.ticket_store.pd.concat"
        ), patch.object(ticket_store.pd.DataFrame, "to_excel"):

            ticket = ticket_store.add_ticket(
                chat_id=123,
                chat_title="Support",
                sender="John",
                text="Issue",
                timestamp="2024-01-15 10:00:00",
                rule_cat="Инциденты",
                ai_cat="Инциденты",
                final_cat="Инциденты",
            )

            result = ticket_store.add_assignee(ticket["ticket_id"], "Alice")
            assert result is True

            updated = ticket_store.get_ticket(ticket["ticket_id"])
            assert "Alice" in updated["assignee"]

    def test_add_assignee_multiple(self):
        """Test adding multiple assignees to a ticket."""
        with patch("app.ticket_system.ticket_store.pd.read_excel"), patch(
            "app.ticket_system.ticket_store.pd.concat"
        ), patch.object(ticket_store.pd.DataFrame, "to_excel"):

            ticket = ticket_store.add_ticket(
                chat_id=123,
                chat_title="Support",
                sender="John",
                text="Issue",
                timestamp="2024-01-15 10:00:00",
                rule_cat="Инциденты",
                ai_cat="Инциденты",
                final_cat="Инциденты",
            )

            ticket_store.add_assignee(ticket["ticket_id"], "Alice")
            ticket_store.add_assignee(ticket["ticket_id"], "Bob")

            updated = ticket_store.get_ticket(ticket["ticket_id"])
            assert "Alice" in updated["assignee"]
            assert "Bob" in updated["assignee"]
            assert len(updated["assignee"]) == 2

    def test_get_tickets_by_assignee(self):
        """Test filtering tickets by assignee."""
        with patch("app.ticket_system.ticket_store.pd.read_excel"), patch(
            "app.ticket_system.ticket_store.pd.concat"
        ), patch.object(ticket_store.pd.DataFrame, "to_excel"):

            ticket1 = ticket_store.add_ticket(
                chat_id=123,
                chat_title="Support",
                sender="John",
                text="Ticket 1",
                timestamp="2024-01-15 10:00:00",
                rule_cat="Инциденты",
                ai_cat="Инциденты",
                final_cat="Инциденты",
            )

            ticket2 = ticket_store.add_ticket(
                chat_id=123,
                chat_title="Support",
                sender="Jane",
                text="Ticket 2",
                timestamp="2024-01-15 11:00:00",
                rule_cat="Операционная работа",
                ai_cat="Операционная работа",
                final_cat="Операционная работа",
            )

            ticket_store.add_assignee(ticket1["ticket_id"], "Alice")
            ticket_store.add_assignee(ticket2["ticket_id"], "Bob")

            alice_tickets = ticket_store.get_tickets(assignee="Alice")
            assert len(alice_tickets) == 1
            assert alice_tickets[0]["ticket_id"] == ticket1["ticket_id"]

import threading
from datetime import datetime

# List of new tickets detected by the AI classifier
# Each ticket is a dict with all message fields + metadata
_tickets: list[dict] = []
_lock = threading.Lock()


def add_ticket(
    chat_id: int,
    chat_title: str,
    sender: str,
    text: str,
    timestamp,
    rule_cat: str,
    ai_cat: str | None,
    final_cat: str | None,
    message_id: int | None = None,
) -> dict:
    """Add a new ticket and return it."""
    ticket = {
        "ticket_id": len(_tickets) + 1,  # simple incrementing ID
        "message_id": message_id,
        "chat_id": chat_id,
        "chat_title": chat_title,
        "sender": sender,
        "text": text,
        "timestamp": timestamp,
        "rule_cat": rule_cat,
        "ai_cat": ai_cat,
        "final_cat": final_cat,
        "created_at": datetime.now(),
        "resolved": False,
    }
    with _lock:
        _tickets.append(ticket)
    return ticket


def get_tickets(chat_id: int | None = None, resolved: bool | None = None) -> list[dict]:
    """
    Return a snapshot of tickets.
    - chat_id:  filter by chat, or None for all chats
    - resolved: filter by resolved status, or None for all
    """
    with _lock:
        result = list(_tickets)

    if chat_id is not None:
        result = [t for t in result if t["chat_id"] == chat_id]
    if resolved is not None:
        result = [t for t in result if t["resolved"] == resolved]
    return result


def resolve_ticket(ticket_id: int) -> bool:
    """Mark a ticket as resolved. Returns True if found, False otherwise."""
    with _lock:
        for ticket in _tickets:
            if ticket["ticket_id"] == ticket_id:
                ticket["resolved"] = True
                return True
    return False


def unresolve_ticket(ticket_id: int) -> bool:
    """Unmark a ticket as resolved. Returns False if found, True otherwise."""
    with _lock:
        for ticket in _tickets:
            if ticket["ticket_id"] == ticket_id:
                ticket["resolved"] = False
                return True
    return False


def get_ticket(ticket_id: int) -> dict | None:
    """Return a single ticket by ID, or None if not found."""
    with _lock:
        for ticket in _tickets:
            if ticket["ticket_id"] == ticket_id:
                return dict(ticket)
    return None

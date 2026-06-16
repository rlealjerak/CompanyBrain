from pathlib import Path

from app.connectors.base import BaseConnector, Document
from app.connectors.json_connector import (
    EmailConnector,
    ReferenceConnector,
    SlackConnector,
    TicketConnector,
)
from app.connectors.markdown_connector import MarkdownConnector

__all__ = [
    "BaseConnector",
    "Document",
    "EmailConnector",
    "MarkdownConnector",
    "ReferenceConnector",
    "SlackConnector",
    "TicketConnector",
    "get_connector",
]


def get_connector(path: Path) -> BaseConnector:
    """Return the right connector for a file based on its location and extension."""
    parts = {p.lower() for p in path.parts}

    if path.suffix == ".md":
        return MarkdownConnector()
    if "slack" in parts:
        return SlackConnector()
    if "emails" in parts:
        return EmailConnector()
    if "tickets" in parts:
        return TicketConnector()
    if "reference" in parts:
        return ReferenceConnector()

    raise ValueError(f"No connector registered for path: {path}")

"""Unit tests for file connectors (no database required).

Each connector test writes a minimal fixture file to tmp_path and verifies
that the connector returns well-formed Document objects.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.connectors import (
    EmailConnector,
    MarkdownConnector,
    ReferenceConnector,
    SlackConnector,
    TicketConnector,
    get_connector,
)
from app.connectors.base import Document


# ──────────────────────────────────────────────────────── MarkdownConnector


def test_markdown_connector_returns_one_document(tmp_path):
    f = tmp_path / "test_policy.md"
    f.write_text("# Test Policy\n\nSome content here.\n")
    docs = MarkdownConnector().load(f)
    assert len(docs) == 1


def test_markdown_connector_source_id_format(tmp_path):
    f = tmp_path / "refund_policy.md"
    f.write_text("# Refund Policy\n\nContent.\n")
    doc = MarkdownConnector().load(f)[0]
    assert doc.source_id == "policy:refund_policy"


def test_markdown_connector_content_type(tmp_path):
    f = tmp_path / "any.md"
    f.write_text("# Doc\n\nContent.\n")
    doc = MarkdownConnector().load(f)[0]
    assert doc.content_type == "policy"


def test_markdown_connector_extracts_title_from_h1(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("# My Custom Title\n\nContent.\n")
    doc = MarkdownConnector().load(f)[0]
    assert doc.source_name == "My Custom Title"


def test_markdown_connector_timestamp_is_set(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("# Doc\n\nContent.\n")
    doc = MarkdownConnector().load(f)[0]
    assert isinstance(doc.timestamp, datetime)
    assert doc.timestamp.tzinfo is not None


def test_markdown_connector_raw_content_not_empty(tmp_path):
    content = "# Doc\n\nSome policy content.\n"
    f = tmp_path / "doc.md"
    f.write_text(content)
    doc = MarkdownConnector().load(f)[0]
    assert doc.raw_content == content


# ──────────────────────────────────────────────────────── SlackConnector


@pytest.fixture
def slack_file(tmp_path):
    data = {
        "thread_ts": "1700000000.123456",
        "channel": "general",
        "topic": "Refund policy update",
        "messages": [
            {"display_name": "Alice", "text": "We updated the policy.", "is_reply": False},
            {"display_name": "Bob", "text": "Got it.", "is_reply": True},
        ],
    }
    f = tmp_path / "thread.json"
    f.write_text(json.dumps(data))
    return f


def test_slack_connector_source_id_format(slack_file):
    doc = SlackConnector().load(slack_file)[0]
    assert doc.source_id.startswith("slack:")


def test_slack_connector_content_type(slack_file):
    doc = SlackConnector().load(slack_file)[0]
    assert doc.content_type == "slack"


def test_slack_connector_raw_content_includes_messages(slack_file):
    doc = SlackConnector().load(slack_file)[0]
    assert "Alice" in doc.raw_content
    assert "We updated the policy." in doc.raw_content


def test_slack_connector_timestamp_from_thread_ts(slack_file):
    doc = SlackConnector().load(slack_file)[0]
    assert isinstance(doc.timestamp, datetime)
    assert doc.timestamp.tzinfo is not None


# ──────────────────────────────────────────────────────── EmailConnector


@pytest.fixture
def email_file(tmp_path):
    data = {
        "message_id": "msg-001",
        "subject": "Enterprise Follow-up",
        "messages": [
            {
                "from": "sales@acme.com",
                "date": "2024-01-15T10:00:00Z",
                "body": "Following up on your account.",
            }
        ],
    }
    f = tmp_path / "email.json"
    f.write_text(json.dumps(data))
    return f


def test_email_connector_source_id_format(email_file):
    doc = EmailConnector().load(email_file)[0]
    assert doc.source_id == "email:msg-001"


def test_email_connector_content_type(email_file):
    doc = EmailConnector().load(email_file)[0]
    assert doc.content_type == "email"


def test_email_connector_timestamp_from_first_message(email_file):
    doc = EmailConnector().load(email_file)[0]
    assert doc.timestamp == datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)


# ──────────────────────────────────────────────────────── TicketConnector


@pytest.fixture
def tickets_file(tmp_path):
    data = [
        {
            "ticket_id": "TKT-001",
            "subject": "Refund request",
            "body": "I want a refund.",
            "customer_name": "Jane Doe",
            "status": "open",
            "priority": "high",
            "category": "billing",
            "created_at": "2024-02-01T09:00:00Z",
        },
        {
            "ticket_id": "TKT-002",
            "subject": "Shipping delay",
            "body": "My order is late.",
            "customer_name": "John Smith",
            "status": "closed",
            "priority": "medium",
            "category": "shipping",
            "created_at": "2024-02-02T09:00:00Z",
        },
    ]
    f = tmp_path / "tickets.json"
    f.write_text(json.dumps(data))
    return f


def test_ticket_connector_returns_one_doc_per_ticket(tickets_file):
    docs = TicketConnector().load(tickets_file)
    assert len(docs) == 2


def test_ticket_connector_source_id_format(tickets_file):
    docs = TicketConnector().load(tickets_file)
    assert docs[0].source_id == "ticket:TKT-001"
    assert docs[1].source_id == "ticket:TKT-002"


def test_ticket_connector_content_type(tickets_file):
    docs = TicketConnector().load(tickets_file)
    for doc in docs:
        assert doc.content_type == "ticket"


def test_ticket_connector_raw_content_includes_body(tickets_file):
    docs = TicketConnector().load(tickets_file)
    assert "I want a refund." in docs[0].raw_content


# ──────────────────────────────────────────────────────── ReferenceConnector


def test_reference_connector_source_id_format(tmp_path):
    f = tmp_path / "team_directory.json"
    f.write_text(json.dumps({"teams": []}))
    doc = ReferenceConnector().load(f)[0]
    assert doc.source_id == "reference:team_directory"


def test_reference_connector_content_type(tmp_path):
    f = tmp_path / "pricing_table.json"
    f.write_text(json.dumps({"tiers": []}))
    doc = ReferenceConnector().load(f)[0]
    assert doc.content_type == "reference"


# ──────────────────────────────────────────────────────── get_connector routing


def test_get_connector_returns_markdown_for_md_files(tmp_path):
    f = tmp_path / "policy.md"
    assert isinstance(get_connector(f), MarkdownConnector)


def test_get_connector_returns_slack_for_slack_path(tmp_path):
    f = tmp_path / "slack" / "thread.json"
    assert isinstance(get_connector(f), SlackConnector)


def test_get_connector_returns_email_for_emails_path(tmp_path):
    f = tmp_path / "emails" / "chain.json"
    assert isinstance(get_connector(f), EmailConnector)


def test_get_connector_returns_ticket_for_tickets_path(tmp_path):
    f = tmp_path / "tickets" / "support_tickets.json"
    assert isinstance(get_connector(f), TicketConnector)


def test_get_connector_returns_reference_for_reference_path(tmp_path):
    f = tmp_path / "reference" / "team_directory.json"
    assert isinstance(get_connector(f), ReferenceConnector)


def test_get_connector_raises_for_unknown_path(tmp_path):
    f = tmp_path / "unknown" / "file.json"
    with pytest.raises(ValueError, match="No connector registered"):
        get_connector(f)


# ──────────────────────────────────────────────────── Document validation


def test_document_raises_on_empty_source_id():
    with pytest.raises(ValueError, match="source_id"):
        Document(
            raw_content="content",
            source_id="",
            source_name="name",
            author="author",
            timestamp=datetime.now(tz=timezone.utc),
            content_type="policy",
        )


def test_document_raises_on_empty_raw_content():
    with pytest.raises(ValueError, match="raw_content"):
        Document(
            raw_content="",
            source_id="policy:test",
            source_name="name",
            author="author",
            timestamp=datetime.now(tz=timezone.utc),
            content_type="policy",
        )


def test_document_raises_on_none_timestamp():
    with pytest.raises((ValueError, TypeError)):
        Document(
            raw_content="content",
            source_id="policy:test",
            source_name="name",
            author="author",
            timestamp=None,  # type: ignore[arg-type]
            content_type="policy",
        )

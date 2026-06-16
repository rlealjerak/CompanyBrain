import json
from datetime import datetime, timezone
from pathlib import Path

from app.connectors.base import BaseConnector, Document


def _parse_dt(s: str) -> datetime:
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _from_unix(ts: str | float) -> datetime:
    return datetime.fromtimestamp(float(ts), tz=timezone.utc)


class SlackConnector(BaseConnector):
    """Reads a Slack thread JSON file — one Document per file."""

    def load(self, path: Path) -> list[Document]:
        data = json.loads(path.read_text(encoding="utf-8"))

        thread_ts = data.get("thread_ts", path.stem)
        channel = data.get("channel", "unknown")
        topic = data.get("topic", path.stem)
        messages = data.get("messages", [])

        lines = [f"Channel: {channel}", f"Topic: {topic}", ""]
        for msg in messages:
            display = msg.get("display_name", msg.get("user", "unknown"))
            lines.append(f"[{display}]: {msg.get('text', '')}")

        author = "unknown"
        for msg in messages:
            if not msg.get("is_reply", True):
                author = msg.get("display_name", msg.get("user", "unknown"))
                break

        return [
            Document(
                raw_content="\n".join(lines),
                source_id=f"slack:{thread_ts}",
                source_name=topic,
                author=author,
                timestamp=_from_unix(thread_ts),
                content_type="slack",
                metadata={
                    "channel": channel,
                    "thread_ts": thread_ts,
                    "message_count": len(messages),
                },
            )
        ]


class EmailConnector(BaseConnector):
    """Reads an email chain JSON file — one Document per file."""

    def load(self, path: Path) -> list[Document]:
        data = json.loads(path.read_text(encoding="utf-8"))

        message_id = data.get("message_id", path.stem)
        subject = data.get("subject", path.stem)
        messages = data.get("messages", [])

        lines = [f"Subject: {subject}", ""]
        for msg in messages:
            lines.append(f"From: {msg.get('from', 'unknown')}")
            lines.append(f"Date: {msg.get('date', '')}")
            lines.append(msg.get("body", ""))
            lines.append("")

        timestamp = datetime.now(tz=timezone.utc)
        if messages and messages[0].get("date"):
            timestamp = _parse_dt(messages[0]["date"])

        author = messages[0].get("from", "unknown") if messages else "unknown"

        return [
            Document(
                raw_content="\n".join(lines),
                source_id=f"email:{message_id}",
                source_name=subject,
                author=author,
                timestamp=timestamp,
                content_type="email",
                metadata={"message_id": message_id, "message_count": len(messages)},
            )
        ]


class TicketConnector(BaseConnector):
    """Reads a support_tickets.json file — one Document per ticket."""

    def load(self, path: Path) -> list[Document]:
        tickets = json.loads(path.read_text(encoding="utf-8"))
        documents = []

        for ticket in tickets:
            ticket_id = ticket.get("ticket_id", "unknown")
            subject = ticket.get("subject", ticket_id)
            body = ticket.get("body", "")
            resolution = ticket.get("resolution_notes", "")
            customer = ticket.get("customer_name", "unknown")
            status = ticket.get("status", "unknown")
            priority = ticket.get("priority", "medium")
            category = ticket.get("category", "general")
            created_at = ticket.get("created_at", "")

            lines = [
                f"Ticket: {ticket_id}",
                f"Subject: {subject}",
                f"Customer: {customer}",
                f"Status: {status} | Priority: {priority} | Category: {category}",
                "",
                body,
            ]
            if resolution:
                lines += ["", f"Resolution: {resolution}"]

            timestamp = datetime.now(tz=timezone.utc)
            if created_at:
                timestamp = _parse_dt(created_at)

            documents.append(
                Document(
                    raw_content="\n".join(lines),
                    source_id=f"ticket:{ticket_id}",
                    source_name=subject,
                    author=customer,
                    timestamp=timestamp,
                    content_type="ticket",
                    metadata={
                        "ticket_id": ticket_id,
                        "status": status,
                        "priority": priority,
                        "category": category,
                    },
                )
            )

        return documents


class ReferenceConnector(BaseConnector):
    """Reads a reference JSON file (team_directory, pricing_table, etc.)."""

    def load(self, path: Path) -> list[Document]:
        data = json.loads(path.read_text(encoding="utf-8"))
        raw_content = json.dumps(data, indent=2)
        source_name = path.stem.replace("_", " ").title()

        mtime = path.stat().st_mtime
        timestamp = datetime.fromtimestamp(mtime, tz=timezone.utc)

        return [
            Document(
                raw_content=raw_content,
                source_id=f"reference:{path.stem}",
                source_name=source_name,
                author="company",
                timestamp=timestamp,
                content_type="reference",
                metadata={"filename": path.name},
            )
        ]

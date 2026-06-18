"""Claude-based task extraction for the Personal Intelligence Layer.

Sends a document to Claude Haiku and returns structured action items for a
specific user. Each item includes urgency signals that the scorer will combine
into a final score.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import anthropic

from app.connectors.base import Document
from app.core.config import settings

log = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=60.0)
    return _client


def extract_tasks(doc: Document, user_name: str, user_role: str) -> list[dict[str, Any]]:
    """Extract personal action items from *doc* for *user_name*.

    Returns a list of task dicts.  Keys guaranteed to be present:
      description, action_type, raw_urgency_score, deadline_str,
      explicitly_named, sender_is_manager, source_reference, task_fingerprint
    """
    prompt = (
        f"You are analyzing a {doc.content_type} message thread to extract personal "
        f"action items for {user_name} ({user_role}).\n\n"
        f"CONTENT:\n{doc.raw_content}\n\n"
        f"Extract all tasks that {user_name} is responsible for — either explicitly "
        f"assigned by name or implied by their role in the conversation.\n\n"
        "Return ONLY a JSON array. Each element must have exactly these fields:\n"
        '- "description": concise description of the action required (string)\n'
        '- "action_type": one of "follow-up", "respond", "review", "complete", "escalate"\n'
        '- "raw_urgency_score": integer 1-10 based on urgency signals in the text\n'
        '- "deadline_str": ISO 8601 datetime string if a deadline is mentioned, else null\n'
        f'- "explicitly_named": true if {user_name} is @mentioned or directly addressed by name\n'
        '- "sender_is_manager": true if the message sender appears to be in a management or '
        "leadership role based on context (manager, director, VP, team lead, etc.)\n"
        '- "sender": display name of the person who sent or assigned this task\n\n'
        f"If there are no action items for {user_name}, return an empty array [].\n\n"
        "Return ONLY the JSON array, no explanation or other text."
    )

    client = _get_client()
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    tasks_raw = _parse_json_array(raw)

    result = []
    for task in tasks_raw:
        if not isinstance(task, dict) or not task.get("description"):
            continue

        # source_reference is the document's source_id (already namespaced)
        source_ref = doc.source_id

        norm_desc = task["description"].strip().lower()
        fingerprint = hashlib.sha256(f"{source_ref}{norm_desc}".encode()).hexdigest()

        result.append(
            {
                "description": task.get("description", ""),
                "action_type": task.get("action_type", "follow-up"),
                "raw_urgency_score": float(task.get("raw_urgency_score", 5)),
                "deadline_str": task.get("deadline_str"),
                "explicitly_named": bool(task.get("explicitly_named", False)),
                "sender_is_manager": bool(task.get("sender_is_manager", False)),
                "sender": task.get("sender", doc.author),
                "source_reference": source_ref,
                "task_fingerprint": fingerprint,
            }
        )

    log.info(
        "Extracted %d task(s) from %s for %s",
        len(result),
        doc.source_id,
        user_name,
    )
    return result


def _parse_json_array(text: str) -> list:
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    log.warning("Could not parse task extraction JSON: %s", text[:200])
    return []

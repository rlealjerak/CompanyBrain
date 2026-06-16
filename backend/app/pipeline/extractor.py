from __future__ import annotations

import json

import anthropic

from app.core.config import settings

_MODEL = "claude-haiku-4-5-20251001"
_MAX_INPUT_CHARS = 8_000

_PROMPT = """\
Extract structured knowledge from this {content_type} document. Return a JSON object with exactly these keys:
- "key_facts": list of up to 10 important factual statements (strings)
- "entities": list of named entities, each as {{"name": str, "type": "person|policy|product|company|date"}}
- "action_items": list of tasks or commitments mentioned (empty list if none)
- "policy_rules": list of rules, conditions, or exceptions (empty list if not applicable)
- "summary": one sentence summarising the document

Document:
{content}

Return only valid JSON. No preamble, no code fences."""


def extract_knowledge(content: str, content_type: str) -> dict:
    """Call Claude to extract structured facts from a document.

    Returns a dict with key_facts, entities, action_items, policy_rules, summary.
    Falls back to an empty structure on parse failure so the pipeline never
    hard-fails due to a malformed model response.
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=60.0)

    truncated = content[:_MAX_INPUT_CHARS]
    prompt = _PROMPT.format(content_type=content_type, content=truncated)

    response = client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "key_facts": [],
            "entities": [],
            "action_items": [],
            "policy_rules": [],
            "summary": raw[:200],
        }

"""Context bundler for PIL tasks.

Calls the Company Brain search API over HTTP to fetch relevant knowledge chunks
and stores them on the task record. HTTP is required (not a direct DB call) so
future query pipeline improvements automatically benefit the PIL.
"""

from __future__ import annotations

import logging

import httpx

from app.core.auth import create_access_token
from app.core.config import settings

log = logging.getLogger(__name__)

_TIMEOUT = 30.0


def bundle_context(task_description: str, user_id: str) -> list[dict]:
    """Search Company Brain for chunks relevant to *task_description*.

    Uses a short-lived JWT for the task's owner so the search endpoint's auth
    is satisfied without storing a long-lived service credential.

    Returns the search result list (may be empty on any failure).
    """
    token = create_access_token(user_id)
    url = f"{settings.brain_api_url}/v1/query/search"

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(
                url,
                json={"query": task_description, "top_k": 5},
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            return resp.json().get("results", [])
    except Exception as exc:
        log.error(
            "Context bundling failed for '%s': %s",
            task_description[:80],
            exc,
        )
        return []

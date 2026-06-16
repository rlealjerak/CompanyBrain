from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import decode_token, get_current_user
from app.core.database import get_db
from app.pipeline.query import chat, search, stream_chat

router = APIRouter(prefix="/v1/query", tags=["query"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class ChatRequest(BaseModel):
    query: str


@router.post("/search")
def query_search(
    body: SearchRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(get_current_user)],
):
    results = search(body.query, db, top_k=body.top_k)
    return {"results": results, "count": len(results)}


@router.post("/chat")
def query_chat(
    body: ChatRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(get_current_user)],
):
    return chat(body.query, db)


@router.websocket("/chat/stream")
async def chat_stream(websocket: WebSocket, db: Annotated[Session, Depends(get_db)]):
    """Streaming chat over WebSocket.

    Auth is handled via the first message payload (not URL query params, which
    appear in access logs and browser history — a security risk for bearer tokens).

    First client message: {"token": "<jwt>", "query": "<question>"}
    Server responses:     {"type": "token", "content": "<fragment>"}
                          {"type": "done",  "sources": [...]}
                          {"type": "error", "content": "<message>"}
    """
    await websocket.accept()
    try:
        raw = await websocket.receive_text()
        msg = json.loads(raw)
        token = msg.get("token", "")
        query = msg.get("query", "").strip()

        try:
            decode_token(token)
        except Exception:
            await websocket.send_text(json.dumps({"type": "error", "content": "Unauthorized"}))
            await websocket.close(code=4001)
            return

        if not query:
            await websocket.send_text(json.dumps({"type": "error", "content": "query is required"}))
            await websocket.close(code=4000)
            return

        for event in stream_chat(query, db):
            await websocket.send_text(event)

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_text(json.dumps({"type": "error", "content": str(exc)}))
        except Exception:
            pass

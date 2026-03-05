"""Coffee Table chat endpoint — SSE streaming RAG chat."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from wellbegun.database import get_db
from wellbegun.services import llm_service, rag_service
from wellbegun.services.llm_service import OllamaUnavailableError
from wellbegun.system_prompts import DATA_MODEL_CONTEXT

log = logging.getLogger(__name__)

router = APIRouter(prefix="/coffee", tags=["coffee"])

COFFEE_SYSTEM_PROMPT = DATA_MODEL_CONTEXT + """\

## Your Role

You are Coffee Table, an AI assistant embedded in the WellBegun knowledge \
base. You act as three things:

1. **Planning assistant** — help the user think through goals, break work \
into steps, design plans, prioritise activities, and reason about what to \
do next. You can suggest plans, activities, timelines, and dependencies. \
When the user is stuck or overwhelmed, help them structure their thinking.

2. **Editor** — help the user write and refine content for their entities. \
Improve note text, draft project descriptions, sharpen log entries, \
summarise sources, and suggest titles. When asked, rewrite or expand \
content while preserving the user's voice and intent.

3. **Curator** — help the user organise and maintain their knowledge base. \
Suggest tags, flag missing fields, propose connections between entities, \
identify stale or orphaned items, and recommend how to structure reading \
lists and plans. Proactively notice when entities could be better linked \
or categorised.

## How to use context

The prompt may include sections with the user's actual data:
- "Currently Active Entities" — what the user is working on right now.
- "Relevant Knowledge Base Entries" — entities matching the query.
- "Knowledge Graph Relationships" — connections between entities.

Use this data to ground your suggestions in what the user actually has. \
When referencing KB entities, use the [entity_type#id] format \
(e.g. [project#3], [note#12]) so the UI can link to them.

## Guidelines

1. **Be proactive.** Don't just answer — suggest next steps, surface \
related entities, and offer to help organise. If you see a plan with no \
activities, offer to help populate it. If a note has no tags, suggest some.
2. **Use your own knowledge freely.** You are not limited to KB content. \
If the user asks about a topic, methodology, or technique, draw on your \
general knowledge to help them plan and write.
3. **When editing, show your work.** Present the revised text clearly so \
the user can compare and accept changes.
4. **When planning, think step by step.** Break goals into concrete \
activities, suggest realistic ordering, and flag dependencies.
5. **When curating, be specific.** Don't say "you should add tags" — \
suggest which tags and why.
6. **Do not fabricate KB data.** If referencing entities, only use those \
present in the provided context. If no matching entities are found and \
the user was asking about their data, say so.
7. Be concise. Use markdown for readability.
"""


# ---------------------------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class CoffeeChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


def _format_sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@router.post("/chat")
async def chat(body: CoffeeChatRequest, db: Session = Depends(get_db)):
    """SSE streaming RAG chat."""
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Try structured query first (no LLM needed)
    structured = rag_service.execute_structured_query(db, body.message)
    if structured is not None:
        async def structured_stream():
            if structured.entity_refs:
                yield _format_sse({"type": "entities", "items": structured.entity_refs})
            yield _format_sse({"type": "token", "content": structured.answer_text})
            if structured.curation:
                yield _format_sse({"type": "curation", "suggestions": structured.curation})
            yield _format_sse({"type": "done"})

        return StreamingResponse(
            structured_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # Fall through to LLM pipeline
    context = rag_service.retrieve_context(db, body.message)
    prompt = rag_service.build_rag_prompt(body.message, context)

    # Append conversation history (last 6 messages)
    history_lines: list[str] = []
    for msg in body.history[-6:]:
        prefix = "User" if msg.role == "user" else "Assistant"
        history_lines.append(f"{prefix}: {msg.content}")

    if history_lines:
        prompt = "## Conversation History\n" + "\n".join(history_lines) + "\n\n" + prompt

    async def event_stream():
        # 1. Send entity metadata first
        if context["entity_refs"]:
            yield _format_sse({
                "type": "entities",
                "items": context["entity_refs"],
            })

        # 2. Stream tokens
        try:
            async for token in llm_service.stream_generate(
                prompt=prompt,
                system=COFFEE_SYSTEM_PROMPT,
            ):
                yield _format_sse({"type": "token", "content": token})
        except OllamaUnavailableError:
            yield _format_sse({
                "type": "error",
                "message": "Ollama is not available. Please ensure it is running.",
            })
            yield _format_sse({"type": "done"})
            return

        # 3. Curation suggestions
        suggestions = rag_service.check_curation(db, context["entity_refs"])
        if suggestions:
            yield _format_sse({"type": "curation", "suggestions": suggestions})

        # 4. Done
        yield _format_sse({"type": "done"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )



# ---------------------------------------------------------------------------
# Model management
# ---------------------------------------------------------------------------

@router.get("/models")
async def get_models():
    """List available Ollama models and the currently active one."""
    try:
        models = await llm_service.list_models()
    except Exception:
        raise HTTPException(status_code=502, detail="Could not reach Ollama")
    return {"models": models, "current": llm_service.get_active_model()}


class ModelSwitchRequest(BaseModel):
    model: str


@router.post("/model")
async def switch_model(body: ModelSwitchRequest):
    """Switch the active LLM model."""
    try:
        models = await llm_service.list_models()
    except Exception:
        raise HTTPException(status_code=502, detail="Could not reach Ollama")
    available_names = {m["name"] for m in models}
    if body.model not in available_names:
        raise HTTPException(status_code=400, detail=f"Model '{body.model}' not available")
    llm_service.set_active_model(body.model)
    return {"current": body.model}

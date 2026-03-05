"""Journal extraction endpoint — freeform text to entity blocks via LLM."""

import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from wellbegun.services import llm_service
from wellbegun.services.llm_service import OllamaUnavailableError
from wellbegun.system_prompts import DATA_MODEL_CONTEXT

router = APIRouter(prefix="/journal", tags=["journal"])

EXTRACTION_SYSTEM_PROMPT = DATA_MODEL_CONTEXT + """\

## Your Role

You are an entity extraction assistant for this knowledge base.
Given freeform journal text, extract structured entities using the @entity_type syntax.

Available entity types and their fields:

@note
First line = title
Remaining lines = content
Optional fields: tags: comma,separated

@project
First line = title
Remaining lines = description
Optional fields: status: planned|in_progress|done|on_hold|cancelled, start_date: YYYY-MM-DD, tags: comma,separated

@log
First line = title
Remaining lines = content
Optional fields: location: text, mood: emoji, weather: emoji, day_theme: emoji, tags: comma,separated

@activity
First line = title
Remaining lines = description
Optional fields: duration: minutes, status: todo|in_progress|done|on_hold|cancelled, tags: comma,separated

@source
First line = title
Remaining lines = description
Optional fields: author: text, source_type: book|article|video|podcast|website, content_url: url, status: to_read|reading|reviewed, tags: comma,separated

@actor
First line = full_name (use full_name, NOT title)
Remaining lines = notes
Optional fields: role: text, affiliation: text, expertise: text, email: text, url: url, tags: comma,separated

@plan
First line = title
Remaining lines = description
Optional fields: motivation: text, outcome: text, start_date: YYYY-MM-DD, end_date: YYYY-MM-DD, status: planned|in_progress|done|on_hold|cancelled, tags: comma,separated
Plan items as: - activity title (one per line after fields)

SECTION HEADINGS:
- The user may use markdown headings (# Heading) to hint at the entity type for the text that follows
- Heading mappings (case-insensitive):
  # ToDo or # To Do       → extract items as @activity, each tagged: ToDo
  # Log                    → extract as @log
  # Notes or # Note        → extract as @note
  # Projects or # Project  → extract as @project
  # Sources or # Source    → extract as @source
  # Reading                → extract as @source, tagged: Reading
  # People or # Actors     → extract as @actor
  # Ideas or # Idea        → extract as @note, tagged: Idea
  # Meeting or # Meetings  → extract as @log, tagged: Meeting
  # Plan or # Plans        → extract as @plan
  # Questions or # Question → extract as @note, tagged: Question
- Under a heading, each bullet point (- item) or distinct paragraph becomes a separate entity of that type
- Headings are hints — still use judgement to pick the best entity type if the content clearly suggests otherwise
- Text without any heading should be extracted normally based on content

RULES:
- Output ONLY raw @entity_type blocks, one after another
- Do NOT wrap output in markdown code fences
- Do NOT add explanations or commentary
- Each block starts with @type on its own line
- Put the title/name on the next line
- Put optional key: value fields on separate lines
- Put the body text (content/description/notes) after the fields
- Separate blocks with a blank line
- Extract as many entities as you can identify from the text
- Use appropriate entity types based on the content

TAGS:
- Add a tags: field to every entity where applicable
- Infer tags from context using these common tags: Meeting, Idea, Research, Decision, Question, Follow-up, Reading
- Examples: meetings/discussions → tags: Meeting; ideas/brainstorms → tags: Idea; research topics → tags: Research; decisions made → tags: Decision; open questions → tags: Question; follow-up items → tags: Follow-up; books/articles/reading → tags: Reading
- You may combine multiple tags: tags: Meeting, Decision
- Only add tags that are clearly supported by the text
- Do NOT use status tags (ToDo, InProgress, Done, etc.) — status is a dedicated field on Activity, Project, Plan, and Source

CONNECTIONS:
- After all entity blocks, if there are clear relationships between entities, add a connections section
- Start the section with a line containing only: ---connections---
- Each connection is on its own line in the format: Source Entity Title -> predicate -> Target Entity Title
- Use entity titles exactly as they appear in your extracted blocks
- Available predicates: participated_in, mentioned_by, related_to, references, suggested_by, authored_by, assigned_to, documents, created_by, contributes_to
- Only include connections that are clearly implied by the text
- If no connections are evident, omit the ---connections--- section entirely
"""


KNOWN_PREDICATES = {
    "participated_in", "mentioned_by", "related_to", "references",
    "suggested_by", "authored_by", "assigned_to", "documents",
    "created_by", "contributes_to",
}


def _extract_entity_titles(notepad_text: str) -> list[str]:
    """Scan @type headers and grab the next non-empty line as the title."""
    titles: list[str] = []
    lines = notepad_text.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("@") and len(stripped.split()) == 1:
            # Next non-empty line is the title
            for j in range(i + 1, len(lines)):
                candidate = lines[j].strip()
                if candidate:
                    titles.append(candidate)
                    break
    return titles


def _match_label_to_index(label: str, titles: list[str]) -> int | None:
    """Case-insensitive exact match, then substring containment fallback."""
    label_lower = label.lower().strip()
    # Exact match first
    for idx, title in enumerate(titles):
        if title.lower().strip() == label_lower:
            return idx
    # Substring containment fallback
    for idx, title in enumerate(titles):
        if label_lower in title.lower().strip() or title.lower().strip() in label_lower:
            return idx
    return None


def _parse_connections(
    raw_connections: str, titles: list[str]
) -> list[dict]:
    """Parse 'src -> pred -> tgt' lines, resolve to indices."""
    connections: list[dict] = []
    for line in raw_connections.split("\n"):
        line = line.strip()
        if not line or line.startswith("---"):
            continue
        parts = [p.strip() for p in line.split("->")]
        if len(parts) != 3:
            continue
        src_label, predicate, tgt_label = parts
        src_idx = _match_label_to_index(src_label, titles)
        tgt_idx = _match_label_to_index(tgt_label, titles)
        if src_idx is None or tgt_idx is None or src_idx == tgt_idx:
            continue
        # Validate predicate, fallback to related_to
        predicate = predicate.strip().lower().replace(" ", "_")
        if predicate not in KNOWN_PREDICATES:
            predicate = "related_to"
        connections.append({
            "source_index": src_idx,
            "target_index": tgt_idx,
            "predicate": predicate,
        })
    return connections


class JournalExtractRequest(BaseModel):
    text: str


class ExtractedConnection(BaseModel):
    source_index: int
    target_index: int
    predicate: str


class JournalExtractResponse(BaseModel):
    notepad_text: str
    connections: list[ExtractedConnection] = []


def _clean_single_result(raw: str) -> JournalExtractResponse:
    """Clean a single LLM result into notepad_text + connections."""
    cleaned = re.sub(r"^```\w*\n?", "", raw.strip())
    cleaned = re.sub(r"\n?```$", "", cleaned)

    separator = "---connections---"
    if separator in cleaned.lower():
        idx = cleaned.lower().index(separator)
        notepad_text = cleaned[:idx].strip()
        raw_connections = cleaned[idx + len(separator):]
    else:
        notepad_text = cleaned.strip()
        raw_connections = ""

    connections: list[ExtractedConnection] = []
    if raw_connections.strip():
        titles = _extract_entity_titles(notepad_text)
        for conn in _parse_connections(raw_connections, titles):
            connections.append(ExtractedConnection(**conn))

    return JournalExtractResponse(notepad_text=notepad_text, connections=connections)


@router.post("/extract", response_model=JournalExtractResponse)
async def extract_entities(body: JournalExtractRequest):
    """Extract structured entities from freeform journal text."""
    if not body.text.strip():
        return JournalExtractResponse(notepad_text="")

    try:
        result = await llm_service.generate(
            prompt=body.text,
            system=EXTRACTION_SYSTEM_PROMPT,
        )
    except OllamaUnavailableError:
        raise HTTPException(status_code=503, detail="Ollama is not available")

    return _clean_single_result(result)

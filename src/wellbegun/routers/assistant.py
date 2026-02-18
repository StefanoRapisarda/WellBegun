"""
AI Assistant router for chat-based UI control and natural language queries.
"""

import os
import json
import re
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_

from wellbegun.database import get_db
from wellbegun.models import Log, Activity, Note, Project, Source, Actor, Tag, EntityTag

router = APIRouter(prefix="/assistant", tags=["assistant"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    context: dict
    history: list[ChatMessage] = []


class ActionCall(BaseModel):
    name: str
    args: dict = {}


class ChatResponse(BaseModel):
    response: str
    actions: list[ActionCall] = []


class QueryResult(BaseModel):
    entity_type: str
    id: int
    title: str
    subtitle: str | None = None
    date: str | None = None


class NLQueryRequest(BaseModel):
    question: str


class TagSuggestion(BaseModel):
    action: str  # 'create_and_tag' or 'tag_existing'
    tag_name: str
    tag_category: str
    entity_type: str
    entity_ids: list[int]
    message: str


class NLQueryResponse(BaseModel):
    answer: str
    results: list[QueryResult] = []
    ui_actions: list[dict] = []
    suggestions: list[TagSuggestion] = []


# Date parsing helpers
def parse_date_reference(text: str) -> tuple[datetime | None, datetime | None]:
    """Parse natural language date references."""
    text = text.lower()
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if 'today' in text:
        return today, today + timedelta(days=1)
    elif 'yesterday' in text:
        return today - timedelta(days=1), today
    elif 'this week' in text:
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=7)
    elif 'last week' in text:
        start = today - timedelta(days=today.weekday() + 7)
        return start, start + timedelta(days=7)
    elif 'this month' in text:
        start = today.replace(day=1)
        if today.month == 12:
            end = today.replace(year=today.year + 1, month=1, day=1)
        else:
            end = today.replace(month=today.month + 1, day=1)
        return start, end

    return None, None


def extract_entity_type_intent(text: str) -> list[str]:
    """Extract what entity types the user is asking about."""
    text = text.lower()
    types = []

    if any(w in text for w in ['meeting', 'meetings']):
        types.append('meeting')  # log_type
    if any(w in text for w in ['log', 'logs', 'diary', 'diaries', 'entry', 'entries']):
        types.append('log')
    if any(w in text for w in ['note', 'notes']):
        types.append('note')
    if any(w in text for w in ['activity', 'activities', 'task', 'tasks']):
        types.append('activity')
    if any(w in text for w in ['project', 'projects']):
        types.append('project')
    if any(w in text for w in ['source', 'sources', 'reference', 'references']):
        types.append('source')
    if any(w in text for w in ['actor', 'actors', 'person', 'people', 'contact', 'contacts']):
        types.append('actor')

    return types


def extract_keywords(text: str) -> list[str]:
    """Extract potential search keywords from text."""
    # Remove common question words and stopwords
    stopwords = {'did', 'do', 'does', 'have', 'has', 'had', 'i', 'my', 'me', 'the', 'a', 'an',
                 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'what', 'when', 'where',
                 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am', 'any',
                 'about', 'with', 'from', 'for', 'on', 'at', 'to', 'of', 'in', 'there',
                 'today', 'yesterday', 'week', 'month', 'year', 'last', 'next', 'show',
                 'find', 'search', 'get', 'list', 'all', 'some', 'how', 'many', 'much'}

    words = re.findall(r'\b\w+\b', text.lower())
    keywords = [w for w in words if w not in stopwords and len(w) > 2]
    return keywords


@router.post("/query", response_model=NLQueryResponse)
async def natural_language_query(request: NLQueryRequest, db: Session = Depends(get_db)):
    """
    Process natural language questions and query the database.
    Returns structured results and UI action suggestions.
    """
    question = request.question.lower()

    # Parse date range
    start_date, end_date = parse_date_reference(question)

    # Detect entity types
    entity_types = extract_entity_type_intent(question)

    # Extract search keywords
    keywords = extract_keywords(question)

    results: list[QueryResult] = []
    ui_actions: list[dict] = []

    suggestions: list[TagSuggestion] = []

    # Query based on detected intent

    # Meetings query - search logs with type=meeting AND activities with "meeting" in title
    if 'meeting' in entity_types or (not entity_types and 'meeting' in question):
        # 1. Search logs with log_type='meeting'
        log_query = db.query(Log).filter(Log.log_type == 'meeting', Log.is_archived == False)
        if start_date and end_date:
            log_query = log_query.filter(Log.created_at >= start_date, Log.created_at < end_date)

        meetings_logs = log_query.order_by(Log.created_at.desc()).limit(20).all()
        for m in meetings_logs:
            results.append(QueryResult(
                entity_type='log',
                id=m.id,
                title=f"[Log] {m.title}",
                subtitle=m.content[:100] if m.content else None,
                date=m.created_at.isoformat() if m.created_at else None
            ))

        # 2. Search activities with "meeting" in title or description
        activity_query = db.query(Activity).filter(
            Activity.is_archived == False,
            or_(
                Activity.title.ilike('%meeting%'),
                Activity.description.ilike('%meeting%')
            )
        )
        if start_date and end_date:
            activity_query = activity_query.filter(
                Activity.created_at >= start_date,
                Activity.created_at < end_date
            )

        meeting_activities = activity_query.order_by(Activity.created_at.desc()).limit(20).all()

        # Check which activities have a "meeting" tag
        meeting_tag = db.query(Tag).filter(
            Tag.name.ilike('meeting'),
            Tag.entity_type.is_(None)  # Wild tag, not entity-linked
        ).first()

        untagged_activities = []
        for a in meeting_activities:
            results.append(QueryResult(
                entity_type='activity',
                id=a.id,
                title=f"[Activity] {a.title}",
                subtitle=a.description[:100] if a.description else None,
                date=a.created_at.isoformat() if a.created_at else None
            ))

            # Check if this activity has a meeting tag
            if meeting_tag:
                has_tag = db.query(EntityTag).filter(
                    EntityTag.tag_id == meeting_tag.id,
                    EntityTag.target_type == 'activity',
                    EntityTag.target_id == a.id
                ).first()
                if not has_tag:
                    untagged_activities.append(a)
            else:
                untagged_activities.append(a)

        # Generate suggestion if we found untagged meeting activities
        if untagged_activities:
            if meeting_tag:
                suggestions.append(TagSuggestion(
                    action='tag_existing',
                    tag_name='meeting',
                    tag_category=meeting_tag.category,
                    entity_type='activity',
                    entity_ids=[a.id for a in untagged_activities],
                    message=f"Found {len(untagged_activities)} activity(ies) with 'meeting' in the title but not tagged. Would you like me to tag them?"
                ))
            else:
                suggestions.append(TagSuggestion(
                    action='create_and_tag',
                    tag_name='meeting',
                    tag_category='default',
                    entity_type='activity',
                    entity_ids=[a.id for a in untagged_activities],
                    message=f"Found {len(untagged_activities)} activity(ies) with 'meeting' in the title. There's no 'meeting' tag yet. Would you like me to create it and tag these activities?"
                ))

        if meetings_logs:
            ui_actions.append({
                'type': 'highlight',
                'target': 'log',
                'ids': [m.id for m in meetings_logs],
                'duration': 2000
            })
            ui_actions.append({
                'type': 'show_panel',
                'panel': 'log'
            })

        if meeting_activities:
            ui_actions.append({
                'type': 'highlight',
                'target': 'activity',
                'ids': [a.id for a in meeting_activities],
                'duration': 2000
            })
            ui_actions.append({
                'type': 'show_panel',
                'panel': 'activity'
            })

    # Logs query (general)
    if 'log' in entity_types:
        query = db.query(Log).filter(Log.is_archived == False)
        if start_date and end_date:
            query = query.filter(Log.created_at >= start_date, Log.created_at < end_date)
        if keywords:
            keyword_filters = [or_(
                Log.title.ilike(f'%{kw}%'),
                Log.content.ilike(f'%{kw}%')
            ) for kw in keywords]
            query = query.filter(or_(*keyword_filters))

        logs = query.order_by(Log.created_at.desc()).limit(20).all()
        for log in logs:
            results.append(QueryResult(
                entity_type='log',
                id=log.id,
                title=f"[{log.log_type}] {log.title}",
                subtitle=log.content[:100] if log.content else None,
                date=log.created_at.isoformat() if log.created_at else None
            ))

        if logs:
            ui_actions.append({
                'type': 'highlight',
                'target': 'log',
                'ids': [log.id for log in logs],
                'duration': 2000
            })

    # Notes query
    if 'note' in entity_types:
        query = db.query(Note).filter(Note.is_archived == False)
        if start_date and end_date:
            query = query.filter(Note.created_at >= start_date, Note.created_at < end_date)
        if keywords:
            keyword_filters = [or_(
                Note.title.ilike(f'%{kw}%'),
                Note.content.ilike(f'%{kw}%')
            ) for kw in keywords]
            query = query.filter(or_(*keyword_filters))

        notes = query.order_by(Note.created_at.desc()).limit(20).all()
        for note in notes:
            results.append(QueryResult(
                entity_type='note',
                id=note.id,
                title=note.title or note.content[:50] if note.content else 'Untitled',
                subtitle=note.content[:100] if note.content else None,
                date=note.created_at.isoformat() if note.created_at else None
            ))

        if notes:
            ui_actions.append({
                'type': 'highlight',
                'target': 'note',
                'ids': [n.id for n in notes],
                'duration': 2000
            })

    # Activities query
    if 'activity' in entity_types:
        query = db.query(Activity).filter(Activity.is_archived == False)
        if start_date and end_date:
            query = query.filter(Activity.created_at >= start_date, Activity.created_at < end_date)
        if keywords:
            keyword_filters = [or_(
                Activity.title.ilike(f'%{kw}%'),
                Activity.description.ilike(f'%{kw}%')
            ) for kw in keywords]
            query = query.filter(or_(*keyword_filters))

        activities = query.order_by(Activity.created_at.desc()).limit(20).all()
        for a in activities:
            results.append(QueryResult(
                entity_type='activity',
                id=a.id,
                title=f"[{a.status}] {a.title}",
                subtitle=a.description[:100] if a.description else None,
                date=a.created_at.isoformat() if a.created_at else None
            ))

        if activities:
            ui_actions.append({
                'type': 'highlight',
                'target': 'activity',
                'ids': [a.id for a in activities],
                'duration': 2000
            })

    # Projects query
    if 'project' in entity_types:
        query = db.query(Project).filter(Project.is_archived == False)
        if keywords:
            keyword_filters = [or_(
                Project.title.ilike(f'%{kw}%'),
                Project.description.ilike(f'%{kw}%')
            ) for kw in keywords]
            query = query.filter(or_(*keyword_filters))

        projects = query.order_by(Project.created_at.desc()).limit(20).all()
        for p in projects:
            results.append(QueryResult(
                entity_type='project',
                id=p.id,
                title=f"[{p.status}] {p.title}",
                subtitle=p.description[:100] if p.description else None,
                date=p.created_at.isoformat() if p.created_at else None
            ))

        if projects:
            ui_actions.append({
                'type': 'highlight',
                'target': 'project',
                'ids': [p.id for p in projects],
                'duration': 2000
            })

    # Generate natural language answer
    if not entity_types and not results:
        # Try a general search if no specific intent was detected
        # Search across all entity types for keywords
        if keywords:
            # Search logs
            logs = db.query(Log).filter(
                Log.is_archived == False,
                or_(Log.title.ilike(f'%{keywords[0]}%'), Log.content.ilike(f'%{keywords[0]}%'))
            ).limit(5).all()
            for log in logs:
                results.append(QueryResult(
                    entity_type='log',
                    id=log.id,
                    title=f"[{log.log_type}] {log.title}",
                    subtitle=log.content[:100] if log.content else None,
                    date=log.created_at.isoformat() if log.created_at else None
                ))

            # Search notes
            notes = db.query(Note).filter(
                Note.is_archived == False,
                or_(Note.title.ilike(f'%{keywords[0]}%'), Note.content.ilike(f'%{keywords[0]}%'))
            ).limit(5).all()
            for note in notes:
                results.append(QueryResult(
                    entity_type='note',
                    id=note.id,
                    title=note.title or 'Untitled',
                    subtitle=note.content[:100] if note.content else None,
                    date=note.created_at.isoformat() if note.created_at else None
                ))

    # Format answer
    if results:
        count = len(results)
        entity_word = entity_types[0] if entity_types else 'item'
        if entity_word == 'meeting':
            entity_word = 'meeting'

        time_phrase = ""
        if 'today' in question:
            time_phrase = " today"
        elif 'yesterday' in question:
            time_phrase = " yesterday"
        elif 'this week' in question:
            time_phrase = " this week"
        elif 'last week' in question:
            time_phrase = " last week"

        if count == 1:
            answer = f"Yes, you have 1 {entity_word}{time_phrase}: \"{results[0].title}\""
            if results[0].subtitle:
                answer += f" - {results[0].subtitle[:50]}..."
        else:
            answer = f"Yes, you have {count} {entity_word}s{time_phrase}:\n"
            for i, r in enumerate(results[:5]):
                answer += f"• {r.title}\n"
            if count > 5:
                answer += f"...and {count - 5} more."

        # Add suggestion message if any
        if suggestions:
            answer += f"\n\n💡 {suggestions[0].message}"
    else:
        time_phrase = ""
        if 'today' in question:
            time_phrase = " today"
        elif 'yesterday' in question:
            time_phrase = " yesterday"

        entity_word = entity_types[0] if entity_types else 'matching item'
        answer = f"No {entity_word}s found{time_phrase}."

    return NLQueryResponse(
        answer=answer,
        results=results,
        ui_actions=ui_actions,
        suggestions=suggestions
    )


class ExecuteSuggestionRequest(BaseModel):
    action: str
    tag_name: str
    tag_category: str
    entity_type: str
    entity_ids: list[int]


class ExecuteSuggestionResponse(BaseModel):
    success: bool
    message: str
    tag_id: int | None = None


@router.post("/execute-suggestion", response_model=ExecuteSuggestionResponse)
async def execute_suggestion(request: ExecuteSuggestionRequest, db: Session = Depends(get_db)):
    """
    Execute a tagging suggestion - create tag if needed and attach to entities.
    """
    try:
        tag = None

        if request.action == 'create_and_tag':
            # Check if tag already exists
            tag = db.query(Tag).filter(
                Tag.name.ilike(request.tag_name),
                Tag.category == request.tag_category,
                Tag.entity_type.is_(None)
            ).first()

            if not tag:
                # Create the tag with full_tag in format "category:name"
                full_tag = f"{request.tag_category}:{request.tag_name}"
                tag = Tag(
                    name=request.tag_name,
                    category=request.tag_category,
                    full_tag=full_tag,
                    entity_type=None,
                    entity_id=None
                )
                db.add(tag)
                db.commit()
                db.refresh(tag)

        elif request.action == 'tag_existing':
            # Find existing tag
            tag = db.query(Tag).filter(
                Tag.name.ilike(request.tag_name),
                Tag.entity_type.is_(None)
            ).first()

            if not tag:
                return ExecuteSuggestionResponse(
                    success=False,
                    message=f"Tag '{request.tag_name}' not found"
                )

        if tag:
            # Attach tag to all specified entities
            tagged_count = 0
            for entity_id in request.entity_ids:
                # Check if already tagged
                existing = db.query(EntityTag).filter(
                    EntityTag.tag_id == tag.id,
                    EntityTag.target_type == request.entity_type,
                    EntityTag.target_id == entity_id
                ).first()

                if not existing:
                    entity_tag = EntityTag(
                        tag_id=tag.id,
                        target_type=request.entity_type,
                        target_id=entity_id
                    )
                    db.add(entity_tag)
                    tagged_count += 1

            db.commit()

            return ExecuteSuggestionResponse(
                success=True,
                message=f"Tagged {tagged_count} {request.entity_type}(s) with '{request.tag_name}'",
                tag_id=tag.id
            )

        return ExecuteSuggestionResponse(
            success=False,
            message="Failed to process suggestion"
        )

    except Exception as e:
        db.rollback()
        return ExecuteSuggestionResponse(
            success=False,
            message=f"Error: {str(e)}"
        )


# --- Original chat endpoint for LLM-based responses ---

TOOLS = [
    {
        "name": "switch_panel",
        "description": "Show or hide a specific panel",
        "input_schema": {
            "type": "object",
            "properties": {
                "panel_id": {"type": "string"},
                "visible": {"type": "boolean"}
            },
            "required": ["panel_id", "visible"]
        }
    },
    {
        "name": "activate_project",
        "description": "Set a project as active",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_name": {"type": "string"}
            },
            "required": ["project_name"]
        }
    },
    {
        "name": "show_panels_for_focus",
        "description": "Configure panels for a focus mode",
        "input_schema": {
            "type": "object",
            "properties": {
                "mode": {"type": "string"}
            },
            "required": ["mode"]
        }
    }
]

SYSTEM_PROMPT = """You are an AI assistant for a note-taking app. Help users manage projects, activities, notes, and logs."""


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process a chat message. Falls back to empty response for frontend handling."""

    # Try Anthropic API if available
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            import anthropic
            client = anthropic.Anthropic()

            messages = [{"role": m.role, "content": m.content} for m in request.history]
            messages.append({
                "role": "user",
                "content": f"Context: {json.dumps(request.context)}\n\nUser: {request.message}"
            })

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages
            )

            text_response = ""
            actions = []
            for block in response.content:
                if block.type == "text":
                    text_response += block.text
                elif block.type == "tool_use":
                    actions.append(ActionCall(name=block.name, args=block.input))

            return ChatResponse(response=text_response, actions=actions)
        except Exception as e:
            print(f"Anthropic API error: {e}")

    # Return empty to trigger frontend local handling
    return ChatResponse(response="", actions=[])

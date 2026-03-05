"""RAG retrieval, prompt building, and curation heuristics."""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from wellbegun.models.tag import Tag, EntityTag
from wellbegun.services import search_service, knowledge_service, active_context_service


# ---------------------------------------------------------------------------
# Structured query types
# ---------------------------------------------------------------------------

@dataclass
class StructuredResult:
    answer_text: str
    entity_refs: list[dict] = field(default_factory=list)
    curation: list[dict] = field(default_factory=list)


# Canonical entity type synonyms
_ENTITY_SYNONYMS: dict[str, list[str]] = {
    "note": ["note", "notes"],
    "log": ["log", "logs", "diary", "entry", "entries"],
    "project": ["project", "projects"],
    "activity": ["activity", "activities", "task", "tasks"],
    "source": ["source", "sources", "reference", "references"],
    "actor": ["actor", "actors", "person", "people", "contact", "contacts"],
    "plan": ["plan", "plans"],
}

# All entity synonym words (for stripping from keywords)
_ENTITY_WORDS: set[str] = set()
for _syns in _ENTITY_SYNONYMS.values():
    for _s in _syns:
        _ENTITY_WORDS.update(_s.split())

# Models that support is_active
_ACTIVE_TYPES = {"project", "log", "activity", "source", "actor", "plan", "note"}

# Status vocabulary: maps tokens (including natural-language aliases) to
# canonical DB values, scoped per entity type.
_STATUS_VALUES: dict[str, dict[str, str]] = {
    "activity": {
        "todo": "todo", "in_progress": "in_progress", "done": "done",
        "on_hold": "on_hold", "cancelled": "cancelled",
    },
    "project": {
        "in_progress": "in_progress", "completed": "completed",
        "on_hold": "on_hold", "cancelled": "cancelled",
    },
    "plan": {
        "planned": "planned", "active": "active",
        "completed": "completed", "cancelled": "cancelled",
    },
    "source": {
        "to_read": "to_read", "reading": "reading", "read": "read",
    },
}

# Flat set of all recognised status tokens (for keyword stripping)
_ALL_STATUS_TOKENS: set[str] = set()
for _sv in _STATUS_VALUES.values():
    _ALL_STATUS_TOKENS.update(_sv.keys())


def _extract_status_values(query: str, entity_types: list[str] | None = None) -> list[str]:
    """Extract canonical status values from the query text.

    If entity_types are provided, only return statuses valid for those types.
    Otherwise match across all entity types.
    """
    lower = query.lower()
    words = set(re.findall(r"[a-z_]+", lower))
    types_to_check = entity_types if entity_types else list(_STATUS_VALUES.keys())
    matched: list[str] = []
    seen: set[str] = set()
    for etype in types_to_check:
        mapping = _STATUS_VALUES.get(etype, {})
        for token, canonical in mapping.items():
            if token in words and canonical not in seen:
                matched.append(canonical)
                seen.add(canonical)
    return matched


def _detect_entity_types(query: str) -> list[str]:
    """Map synonyms in the query to canonical entity types."""
    lower = query.lower()
    found: list[str] = []
    for canonical, synonyms in _ENTITY_SYNONYMS.items():
        for syn in synonyms:
            if syn in lower:
                if canonical not in found:
                    found.append(canonical)
                break
    return found


def classify_intent(query: str) -> tuple[str, list[str]]:
    """Return (intent_name, entity_types) for the query."""
    lower = query.lower()
    entity_types = _detect_entity_types(query)

    # 1. count
    if entity_types and re.search(r"how many|count|number of", lower):
        return "count", entity_types

    # 1b. status_filter — e.g. "todo activities", "completed projects", "any done tasks"
    status_vals = _extract_status_values(query, entity_types or None)
    if status_vals:
        # Default to all entity types that have status fields when none specified
        types = entity_types if entity_types else list(_STATUS_VALUES.keys())
        return "status_filter", types

    # 2. list_active
    if entity_types and re.search(r"active|current|ongoing", lower):
        return "list_active", entity_types

    # 3. curation
    if re.search(r"need tags|missing|incomplete|without tags|short content", lower):
        return "curation", entity_types or search_service.ALL_TYPES

    # 4. date_list
    start, end = _extract_date_range(query)
    if start or end:
        return "date_list", entity_types or search_service.ALL_TYPES

    # 5. tag_search — deferred (needs DB), checked in execute_structured_query
    if re.search(r"tagged|about|related to", lower):
        return "tag_search", entity_types or search_service.ALL_TYPES

    # 6. recent
    if re.search(r"recently|recent|latest", lower):
        return "recent", entity_types or search_service.ALL_TYPES

    # 7. list_all — "find all X", "show X", "list X", "get X"
    #    Only when there are NO qualifying keywords beyond entity type names.
    #    E.g. "find all projects" → list_all, but "find all work projects" → general (search).
    if entity_types and re.search(r"find|show|list|get|what|display", lower):
        keywords = _extract_keywords(query)
        # Collect all words that are entity-type synonyms
        entity_words: set[str] = set()
        for etype in entity_types:
            for syn in _ENTITY_SYNONYMS.get(etype, []):
                for w in syn.split():
                    entity_words.add(w)
        qualifiers = [kw for kw in keywords if kw not in entity_words]
        if not qualifiers:
            return "list_all", entity_types

    # 8. general → fallthrough to LLM
    return "general", entity_types


def _format_entity_list(results: list[dict], header: str) -> StructuredResult:
    """Format search results as markdown bullets with entity refs."""
    if not results:
        return StructuredResult(answer_text=f"{header}\n\nNo matching entities found.")

    lines = [header, ""]
    entity_refs: list[dict] = []
    for r in results:
        title = r.get("title") or "(untitled)"
        created = r.get("created_at")
        date_str = ""
        if created:
            date_str = f" ({created.strftime('%Y-%m-%d') if hasattr(created, 'strftime') else str(created)[:10]})"
        lines.append(f"- [{r['type']}#{r['id']}] **{title}**{date_str}")
        entity_refs.append({"type": r["type"], "id": r["id"], "title": title})

    return StructuredResult(answer_text="\n".join(lines), entity_refs=entity_refs)


def execute_structured_query(db: Session, query: str) -> StructuredResult | None:
    """Try to answer the query with direct SQL. Returns None to fall through to LLM."""
    intent, entity_types = classify_intent(query)

    if intent == "general":
        return None

    if intent == "count":
        parts: list[str] = []
        for etype in entity_types:
            config = search_service.MODEL_CONFIG.get(etype)
            if not config:
                continue
            model = config["model"]
            q = db.query(func.count(model.id))
            if etype in search_service.ARCHIVABLE_TYPES:
                q = q.filter(model.is_archived == False)  # noqa: E712
            count = q.scalar()
            label = etype.replace("_", " ")
            parts.append(f"- **{label}s**: {count}")
        text = "Here are the counts:\n\n" + "\n".join(parts) if parts else "No entity types matched your query."
        return StructuredResult(answer_text=text)

    if intent == "status_filter":
        status_vals = _extract_status_values(query, entity_types)
        # Only search entity types that have status fields
        filterable = [t for t in entity_types if t in _STATUS_VALUES]
        results = search_service.search(
            db, entity_types=filterable, status_values=status_vals, limit=30,
        )
        status_label = ", ".join(status_vals)
        type_label = ", ".join(t.replace("_", " ") + "s" for t in filterable)
        return _format_entity_list(results, f"{type_label.title()} with status [{status_label}]:")

    if intent == "list_active":
        all_results: list[dict] = []
        for etype in entity_types:
            if etype not in _ACTIVE_TYPES:
                continue
            config = search_service.MODEL_CONFIG.get(etype)
            if not config:
                continue
            model = config["model"]
            items = (
                db.query(model)
                .filter(model.is_active == True, model.is_archived == False)  # noqa: E712
                .order_by(model.updated_at.desc())
                .all()
            )
            for item in items:
                all_results.append({
                    "type": etype,
                    "id": item.id,
                    "title": getattr(item, config["title_field"], ""),
                    "created_at": item.created_at,
                })
        return _format_entity_list(all_results, f"Active {', '.join(t.replace('_', ' ') + 's' for t in entity_types)}:")

    if intent == "date_list":
        start_date, end_date = _extract_date_range(query)
        results = search_service.search(
            db, entity_types=entity_types,
            start_date=start_date, end_date=end_date, limit=30,
        )
        return _format_entity_list(results, "Entities matching your date range:")

    if intent == "tag_search":
        tag_ids = _find_tag_ids_by_query(db, query)
        if not tag_ids:
            return None  # no tags matched, fall through to LLM
        results = search_service.search(
            db, tag_ids=tag_ids, tag_mode="or",
            entity_types=entity_types, limit=30,
        )
        return _format_entity_list(results, "Entities matching those tags:")

    if intent == "curation":
        suggestions: list[dict] = []
        summary_parts: list[str] = ["Here's a curation summary:", ""]
        types_to_check = entity_types if entity_types else search_service.ALL_TYPES
        for etype in types_to_check:
            config = search_service.MODEL_CONFIG.get(etype)
            if not config:
                continue
            model = config["model"]
            # Count entities with 0 tags
            all_ids = [r[0] for r in db.query(model.id).all()]
            if not all_ids:
                continue
            tagged_ids = {
                r[0] for r in db.query(EntityTag.target_id)
                .filter(EntityTag.target_type == etype, EntityTag.target_id.in_(all_ids))
                .all()
            }
            untagged = [eid for eid in all_ids if eid not in tagged_ids]
            # Short content
            desc_field_name = config["desc_field"]
            title_field_name = config["title_field"]
            short_items = (
                db.query(model)
                .filter(func.length(getattr(model, desc_field_name)) < 20)
                .all()
            )
            label = etype.replace("_", " ")
            if untagged or short_items:
                summary_parts.append(f"**{label}s**:")
            if untagged:
                summary_parts.append(f"  - {len(untagged)} without tags")
                for eid in untagged[:5]:
                    entity = db.query(model).get(eid)
                    if entity:
                        title = getattr(entity, title_field_name, "")
                        suggestions.append({
                            "type": "missing_tags",
                            "entity_type": etype,
                            "entity_id": eid,
                            "title": title,
                            "message": f"{label.title()} \"{title}\" has no tags",
                            "action": "Add Tags",
                        })
            if short_items:
                summary_parts.append(f"  - {len(short_items)} with very short content")
                for item in short_items[:5]:
                    title = getattr(item, title_field_name, "")
                    suggestions.append({
                        "type": "short_content",
                        "entity_type": etype,
                        "entity_id": item.id,
                        "title": title,
                        "message": f"{label.title()} \"{title}\" has very little content",
                        "action": "Edit",
                    })

        if len(summary_parts) == 2:
            return StructuredResult(answer_text="All entities look well-curated!")
        return StructuredResult(answer_text="\n".join(summary_parts), curation=suggestions)

    if intent == "recent":
        results = search_service.search(db, entity_types=entity_types, limit=15)
        return _format_entity_list(results, "Recently updated entities:")

    if intent == "list_all":
        all_results: list[dict] = []
        for etype in entity_types:
            config = search_service.MODEL_CONFIG.get(etype)
            if not config:
                continue
            model = config["model"]
            q = db.query(model)
            if etype in search_service.ARCHIVABLE_TYPES:
                q = q.filter(model.is_archived == False)  # noqa: E712
            items = q.order_by(model.updated_at.desc()).all()
            for item in items:
                all_results.append({
                    "type": etype,
                    "id": item.id,
                    "title": getattr(item, config["title_field"], ""),
                    "created_at": item.created_at,
                })
        label = ", ".join(t.replace("_", " ") + "s" for t in entity_types)
        return _format_entity_list(all_results, f"All {label}:")


# Words to strip when extracting search keywords from natural language
_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could",
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "it",
    "they", "them", "their", "this", "that", "these", "those",
    "what", "which", "who", "whom", "how", "where", "when", "why",
    "and", "or", "but", "not", "no", "if", "then", "so", "because",
    "of", "in", "on", "at", "to", "for", "with", "by", "from", "about",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "under", "over",
    "all", "any", "some", "each", "every", "both", "few", "more", "most",
    "other", "such", "than", "too", "very", "just", "also",
    # Domain-specific noise words for our queries
    "check", "find", "show", "list", "get", "give", "tell", "search",
    "look", "display", "retrieve", "fetch", "query", "see",
    "entity", "entities", "item", "items", "entry", "entries",
    "created", "related", "tagged", "called", "named",
    "please", "me", "there",
})

# Relative date patterns: maps regex -> (days_back_start, days_back_end)
_DATE_PATTERNS: list[tuple[str, int, int]] = [
    (r"\byesterday\b", 1, 1),
    (r"\btoday\b", 0, 0),
    (r"\blast\s+week\b", 7, 1),
    (r"\bthis\s+week\b", 6, 0),  # last 7 days including today
    (r"\blast\s+month\b", 30, 1),
    (r"\bthis\s+month\b", 29, 0),
    (r"\blast\s+(\d+)\s+days?\b", -1, 0),  # special: group(1) is the number
]


def _extract_date_range(query: str) -> tuple[str | None, str | None]:
    """Extract start_date and end_date from natural language date expressions."""
    lower = query.lower()
    today = datetime.utcnow().date()

    for pattern, days_start, days_end in _DATE_PATTERNS:
        m = re.search(pattern, lower)
        if m:
            if days_start == -1:
                # "last N days" pattern
                n = int(m.group(1))
                start = today - timedelta(days=n)
                end = today
            else:
                start = today - timedelta(days=days_start)
                end = today - timedelta(days=days_end)
            return start.isoformat(), end.isoformat()

    return None, None


def _singularize(word: str) -> str | None:
    """Basic English plural → singular. Returns None if no rule applies."""
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith(("ses", "xes", "zes", "ches", "shes")):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return None


def _extract_keywords(query: str) -> list[str]:
    """Extract meaningful keywords from a natural language query.

    Produces both original and singular forms so that e.g.
    "meetings" also matches the title "Meeting on AI".
    """
    # Remove date expressions so they don't become keywords
    cleaned = query.lower()
    for pattern, _, _ in _DATE_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned)

    words = re.findall(r"[a-z0-9]+(?:'[a-z]+)?", cleaned)
    # Strip entity-type synonyms and status tokens — they describe the query
    # shape, not the content to search for.
    noise = _STOP_WORDS | _ENTITY_WORDS | _ALL_STATUS_TOKENS | {
        "status", "type", "kind", "category", "entity", "entities", "item", "items",
    }
    raw = [w for w in words if w not in noise and len(w) > 1]

    # Expand with singular forms for better ILIKE recall
    expanded: list[str] = []
    seen: set[str] = set()
    for kw in raw:
        if kw not in seen:
            expanded.append(kw)
            seen.add(kw)
        singular = _singularize(kw)
        if singular and singular not in seen and singular not in _STOP_WORDS:
            expanded.append(singular)
            seen.add(singular)
    return expanded


def _find_tag_ids_by_query(db: Session, query: str) -> list[int]:
    """Find tag IDs whose name appears within the query (case-insensitive).

    Checks each tag to see if its name is a substring of the query,
    so "check any entity on creative writing" matches tag "Creative writing".
    """
    lower_query = query.lower()
    if not lower_query.strip():
        return []
    all_tags = db.query(Tag.id, Tag.name).all()
    return [t_id for t_id, t_name in all_tags if t_name.lower() in lower_query]


def retrieve_context(db: Session, query: str) -> dict:
    """Combine search results + tag-based results + graph neighbors + active context."""
    # Extract keywords for text search and date range for date filtering
    keywords = _extract_keywords(query)
    start_date, end_date = _extract_date_range(query)
    # Detect entity types mentioned in the query to scope the search
    detected_types = _detect_entity_types(query) or None
    # Detect status keywords so search can filter by status field
    status_vals = _extract_status_values(query, detected_types) or None

    search_results: list[dict] = []
    seen_keys: set[tuple[str, int]] = set()

    def _merge(results: list[dict]) -> None:
        for r in results:
            key = (r["type"], r["id"])
            if key not in seen_keys:
                search_results.append(r)
                seen_keys.add(key)

    # 0. Status-only search (e.g. "todo activities" with no other keywords)
    if status_vals and not keywords:
        _merge(search_service.search(
            db, entity_types=detected_types, status_values=status_vals,
            start_date=start_date, end_date=end_date, limit=20,
        ))

    # 1. Keyword-based text search: try multi-word phrases first, then individual words
    if keywords:
        # Try the full keyword phrase
        phrase = " ".join(keywords)
        _merge(search_service.search(
            db, query=phrase, entity_types=detected_types,
            start_date=start_date, end_date=end_date,
            status_values=status_vals, limit=10,
        ))
        # Also try individual keywords if phrase didn't yield enough
        if len(search_results) < 10 and len(keywords) > 1:
            for kw in keywords:
                _merge(search_service.search(
                    db, query=kw, entity_types=detected_types,
                    start_date=start_date, end_date=end_date,
                    status_values=status_vals, limit=5,
                ))
    elif start_date or end_date:
        # Date-only query (e.g. "entities created yesterday")
        _merge(search_service.search(
            db, entity_types=detected_types,
            start_date=start_date, end_date=end_date, limit=20
        ))

    # 2. Tag-based search: find tags whose names appear in the query
    tag_ids = _find_tag_ids_by_query(db, query)
    if tag_ids:
        _merge(search_service.search(
            db, tag_ids=tag_ids, tag_mode="or", entity_types=detected_types,
            start_date=start_date, end_date=end_date, limit=10
        ))

    # Summarize each entity
    entity_summaries: list[str] = []
    entity_refs: list[dict] = []
    seen = set()

    for item in search_results:
        key = (item["type"], item["id"])
        if key in seen:
            continue
        seen.add(key)
        desc = item.get("description") or ""
        summary = f"[{item['type']}#{item['id']}] {item['title']}"
        if desc:
            summary += f" — {desc[:200]}"
        # Include tags so the LLM can reason about tag-based queries
        item_tags = item.get("tags") or []
        if item_tags:
            tag_names = ", ".join(t.name for t in item_tags)
            summary += f" [tags: {tag_names}]"
        # Include creation date for date-based queries
        created = item.get("created_at")
        if created:
            summary += f" (created: {created.strftime('%Y-%m-%d') if hasattr(created, 'strftime') else str(created)[:10]})"
        entity_summaries.append(summary)
        entity_refs.append({
            "type": item["type"],
            "id": item["id"],
            "title": item["title"],
        })

    # Graph neighbors for top 5 search hits
    graph_lines: list[str] = []
    allowed_types = set(detected_types) if detected_types else None
    for item in search_results[:5]:
        triples = knowledge_service.get_triples_for_entity(
            db, item["type"], item["id"]
        )
        for triple in triples[:3]:
            line = (
                f"[{triple.subject_type}#{triple.subject_id}] "
                f"—{triple.predicate}→ "
                f"[{triple.object_type}#{triple.object_id}]"
            )
            graph_lines.append(line)
            # Add referenced entities to refs if not already present
            # When entity types were detected, only add neighbors of those types
            for etype, eid in [
                (triple.subject_type, triple.subject_id),
                (triple.object_type, triple.object_id),
            ]:
                if allowed_types and etype not in allowed_types:
                    continue
                ref_key = (etype, eid)
                if ref_key not in seen:
                    seen.add(ref_key)
                    entity_refs.append({"type": etype, "id": eid, "title": ""})

    # Active context
    active = active_context_service.get_active_context(db)
    active_lines: list[str] = []
    for key, items in active.items():
        entity_type = key.rstrip("s")  # "projects" -> "project"
        for item in items:
            title = getattr(item, "title", None) or getattr(item, "full_name", "")
            active_lines.append(f"[{entity_type}#{item.id}] {title} (ACTIVE)")

    return {
        "entity_summaries": entity_summaries,
        "graph_neighbors": graph_lines,
        "active_context_text": "\n".join(active_lines) if active_lines else "",
        "entity_refs": entity_refs,
    }


def build_rag_prompt(query: str, context: dict) -> str:
    """Format retrieved context into an LLM prompt."""
    parts = [f"User question: {query}\n"]

    if context["active_context_text"]:
        parts.append("## Currently Active Entities")
        parts.append(context["active_context_text"])
        parts.append("")

    if context["entity_summaries"]:
        parts.append("## Relevant Knowledge Base Entries")
        parts.append("\n".join(context["entity_summaries"]))
        parts.append("")

    if context["graph_neighbors"]:
        parts.append("## Knowledge Graph Relationships")
        parts.append("\n".join(context["graph_neighbors"]))
        parts.append("")

    if not context["entity_summaries"] and not context["active_context_text"] and not context["graph_neighbors"]:
        parts.append("## No matching entities found in the knowledge base.")
        parts.append("If the user was asking about their data, let them know no matching entries were found.")
        parts.append("If the user was asking a general question, answer it using your own knowledge.")
        parts.append("")

    return "\n".join(parts)


def retrieve_feedback_examples(db: Session, query: str, limit: int = 3) -> list[dict]:
    """Retrieve relevant past feedback as few-shot examples for the LLM prompt.

    Scores stored coffee_feedback rows by keyword overlap with the incoming
    query and returns the top *limit* as {question, answer} dicts.
    """
    from wellbegun.models.coffee_feedback import CoffeeFeedback

    rows = (
        db.query(CoffeeFeedback)
        .filter(
            (CoffeeFeedback.ideal_answer.isnot(None))
            | (CoffeeFeedback.chosen_option.isnot(None))
        )
        .all()
    )
    if not rows:
        return []

    query_keywords = set(_extract_keywords(query))
    if not query_keywords:
        return []

    scored: list[tuple[float, dict]] = []
    for row in rows:
        row_keywords = set(_extract_keywords(row.original_message))
        if not row_keywords:
            continue
        overlap = len(query_keywords & row_keywords)
        if overlap == 0:
            continue

        # Determine the answer text
        if row.ideal_answer:
            answer = row.ideal_answer
        elif row.chosen_option is not None:
            # chosen_option is 0-indexed; option columns are option_1, option_2, option_3
            answer = getattr(row, f"option_{row.chosen_option + 1}", None)
            if not answer:
                continue
        else:
            continue

        scored.append((overlap, {"question": row.original_message, "answer": answer}))

    scored.sort(key=lambda t: t[0], reverse=True)
    return [item for _, item in scored[:limit]]


def check_curation(db: Session, entity_refs: list[dict]) -> list[dict]:
    """Run heuristic checks on referenced entities."""
    from wellbegun.models.tag import EntityTag
    from wellbegun.services.search_service import MODEL_CONFIG

    suggestions: list[dict] = []
    now = datetime.utcnow()
    stale_threshold = now - timedelta(days=30)

    for ref in entity_refs:
        etype = ref["type"]
        eid = ref["id"]
        config = MODEL_CONFIG.get(etype)
        if not config:
            continue

        model = config["model"]
        entity = db.query(model).filter(model.id == eid).first()
        if not entity:
            continue

        title = getattr(entity, config["title_field"], "")

        # Check: no tags
        tag_count = (
            db.query(EntityTag)
            .filter(EntityTag.target_type == etype, EntityTag.target_id == eid)
            .count()
        )
        if tag_count == 0:
            suggestions.append({
                "type": "missing_tags",
                "entity_type": etype,
                "entity_id": eid,
                "title": title,
                "message": f"{etype.replace('_', ' ').title()} \"{title}\" has no tags",
                "action": "Add Tags",
            })

        # Check: very short content
        desc_field = config["desc_field"]
        desc_value = getattr(entity, desc_field, None) or ""
        if len(desc_value) < 20:
            suggestions.append({
                "type": "short_content",
                "entity_type": etype,
                "entity_id": eid,
                "title": title,
                "message": f"{etype.replace('_', ' ').title()} \"{title}\" has very little content",
                "action": "Edit",
            })

        # Check: active but stale
        is_active = getattr(entity, "is_active", False)
        updated_at = getattr(entity, "updated_at", None)
        if is_active and updated_at and updated_at < stale_threshold:
            suggestions.append({
                "type": "stale",
                "entity_type": etype,
                "entity_id": eid,
                "title": title,
                "message": f"{etype.replace('_', ' ').title()} \"{title}\" is active but hasn't been updated in 30+ days",
                "action": "Archive",
            })

    return suggestions

# RAG (Retrieval-Augmented Generation)

> **Category**: concept | **Difficulty**: beginner | **Time**: ~15 min
> **Prerequisites**: REST APIs & HTTP Fundamentals

## Overview

If you've ever built a search engine or recommendation system, RAG follows the same pipeline: retrieve relevant data first, then use it to generate a response. Instead of training a model on your data (expensive, slow), you retrieve context at query time and give it to a pre-trained LLM as input.

Think of it like an open-book exam. The LLM is the student. Instead of memorizing your entire database (fine-tuning), you hand it the relevant pages (retrieved context) right before it answers the question.

**Key takeaways:**
- RAG = Retrieve relevant context + Augment the prompt + Generate with an LLM
- It avoids the need to fine-tune or retrain models on your data
- WellBegun uses a multi-source retrieval strategy: text search, tag matching, and graph traversal
- Intent classification routes queries to either direct SQL answers or LLM-powered responses

---

## Core Concepts

### 1. The RAG Pipeline

The RAG pipeline in WellBegun follows three steps:

1. **Classify the user's intent** — Is this a structured question (e.g., "how many projects?") that can be answered with SQL, or a general question that needs an LLM?
2. **Retrieve relevant context** — Search the knowledge base using multiple strategies (text, tags, graph) to find entities related to the query.
3. **Build the prompt and generate** — Format the retrieved context into a structured prompt and send it to a local LLM via Ollama.

This is the same retrieve-then-generate pattern you'd see in any search-based QA system, but instead of returning a ranked list of documents, you feed them to an LLM that synthesizes a natural language answer.

### 2. Intent Classification

Before doing any retrieval, WellBegun classifies the user's query to decide whether it even needs an LLM. Many questions can be answered directly with SQL.

```python
# From src/wellbegun/services/rag_service.py:104-157
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
```

The function uses regex patterns to categorize queries into structured intents (`count`, `list_active`, `status_filter`, `curation`, `tag_search`, `recent`, `list_all`) versus `general`. Structured intents get answered with direct SQL -- no LLM call needed. Only `general` queries flow through the full RAG pipeline.

Notice the two companion functions that power intent classification:

```python
# From src/wellbegun/services/rag_service.py:91-101
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
```

This maps natural language terms like "tasks", "entries", "people" to canonical entity types (`activity`, `log`, `actor`), using the synonym dictionary defined at the module level:

```python
# From src/wellbegun/services/rag_service.py:26-34
_ENTITY_SYNONYMS: dict[str, list[str]] = {
    "note": ["note", "notes"],
    "log": ["log", "logs", "diary", "entry", "entries"],
    "project": ["project", "projects"],
    "activity": ["activity", "activities", "task", "tasks"],
    "source": ["source", "sources", "reference", "references"],
    "actor": ["actor", "actors", "person", "people", "contact", "contacts"],
    "plan": ["plan", "plans"],
}
```

### 3. Structured Query Execution

When the intent is structured (e.g., "how many projects?"), the system answers directly with SQL -- no LLM needed. This is faster, cheaper, and deterministic.

```python
# From src/wellbegun/services/rag_service.py:179-200 (count intent shown)
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
```

The function handles seven structured intents (`count`, `status_filter`, `list_active`, `date_list`, `tag_search`, `curation`, `recent`, `list_all`), each executing targeted SQLAlchemy queries. When the intent is `general`, it returns `None`, signaling the caller to proceed with the full RAG pipeline. The result is wrapped in a `StructuredResult` dataclass:

```python
# From src/wellbegun/services/rag_service.py:18-22
@dataclass
class StructuredResult:
    answer_text: str
    entity_refs: list[dict] = field(default_factory=list)
    curation: list[dict] = field(default_factory=list)
```

### 4. Context Retrieval (The "R" in RAG)

When a query falls through to `general`, the system retrieves context from multiple sources. This multi-source strategy is the core of WellBegun's RAG implementation.

```python
# From src/wellbegun/services/rag_service.py:454-584
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

    # ... (status-only, keyword, and date searches merged here) ...

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
    # ... (format summaries with title, description, tags, dates) ...

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
```

The retrieval strategy has four layers, each adding context the others might miss:

1. **Keyword text search** -- Extracts meaningful keywords from the query (stripping stop words and entity-type synonyms), then runs ILIKE searches against entity titles and descriptions.
2. **Tag-based search** -- Finds tags whose names appear in the query text, then retrieves all entities tagged with those tags.
3. **Graph neighbor traversal** -- For the top 5 search hits, fetches knowledge graph triples (subject-predicate-object relationships) to surface connected entities.
4. **Active context** -- Adds currently active entities (the user's current working context) so the LLM knows what the user is focused on.

The keyword extraction itself uses NLP-like techniques:

```python
# From src/wellbegun/services/rag_service.py:408-438
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
```

### 5. Prompt Building (The "A" in RAG)

Once context is retrieved, it needs to be formatted into a prompt the LLM can reason over. This is the "Augment" step -- you're augmenting the user's question with retrieved knowledge.

```python
# From src/wellbegun/services/rag_service.py:587-612
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
```

The prompt is organized into clearly labeled sections (active entities, knowledge base entries, graph relationships) so the LLM can distinguish between different types of context. When no context is found, the prompt includes explicit fallback instructions telling the LLM to either say "no results" or answer from its own knowledge.

### 6. The LLM Service (The "G" in RAG)

WellBegun uses Ollama for local LLM inference -- no API keys, no cloud costs. The LLM service provides two generation modes:

```python
# From src/wellbegun/services/llm_service.py:52-72
async def generate(prompt: str, system: str = "", temperature: float | None = None) -> str:
    """Single-shot generation. Returns full response text."""
    payload: dict = {
        "model": get_active_model(),
        "prompt": prompt,
        "stream": False,
    }
    if system:
        payload["system"] = system
    if temperature is not None:
        payload["options"] = {"temperature": temperature}
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{settings.llm_base_url}/api/generate",
                json=payload,
            )
            r.raise_for_status()
            return r.json()["response"]
    except httpx.HTTPError as exc:
        raise OllamaUnavailableError(f"Ollama request failed: {exc}") from exc
```

The `generate` function sends a single-shot request to Ollama's `/api/generate` endpoint and waits for the complete response. For interactive use, there's also a streaming variant:

```python
# From src/wellbegun/services/llm_service.py:75-102
async def stream_generate(prompt: str, system: str = "") -> AsyncIterator[str]:
    """Streaming generation. Yields tokens as they arrive."""
    payload: dict = {
        "model": get_active_model(),
        "prompt": prompt,
        "stream": True,
    }
    if system:
        payload["system"] = system
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                "POST",
                f"{settings.llm_base_url}/api/generate",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
    except httpx.HTTPError as exc:
        raise OllamaUnavailableError(f"Ollama stream failed: {exc}") from exc
```

The streaming version uses `httpx.AsyncClient.stream()` and yields tokens as they arrive, enabling real-time display in the UI. Both functions communicate with Ollama via the REST API you learned about in the prerequisites course.

### 7. Graph Neighbor Retrieval

The knowledge graph adds a dimension that keyword search alone misses. When the RAG service finds relevant entities, it looks up their relationships in the knowledge graph:

```python
# From src/wellbegun/services/knowledge_service.py:18-33
def get_triples_for_entity(
    db: Session, entity_type: str, entity_id: int
) -> list[KnowledgeTriple]:
    return (
        db.query(KnowledgeTriple)
        .filter(
            or_(
                (KnowledgeTriple.subject_type == entity_type)
                & (KnowledgeTriple.subject_id == entity_id),
                (KnowledgeTriple.object_type == entity_type)
                & (KnowledgeTriple.object_id == entity_id),
            )
        )
        .order_by(KnowledgeTriple.created_at.desc())
        .all()
    )
```

This returns all triples where the entity appears as either subject or object. For example, if you search for "machine learning" and find a project, the graph might reveal that the project is connected to a source (a paper) and an actor (a collaborator) -- context that keyword search alone would miss.

---

## In This Project

The RAG system powers WellBegun's "Coffee Table" assistant feature. The architecture follows this flow:

```
user query
    |
    v
classify_intent()
    |
    +--> structured intent (count, list_active, curation, ...)
    |        |
    |        v
    |    execute_structured_query() --> direct SQL answer
    |
    +--> general intent
         |
         v
     retrieve_context()
         |  (keyword search + tag search + graph traversal + active context)
         v
     build_rag_prompt()
         |  (formats context into structured sections)
         v
     llm_service.generate() --> LLM response
```

Key files:
- `src/wellbegun/services/rag_service.py` -- Intent classification, structured query execution, context retrieval, and prompt building (730 lines)
- `src/wellbegun/services/llm_service.py` -- Ollama LLM wrapper for generation and streaming (103 lines)
- `src/wellbegun/services/knowledge_service.py` -- Knowledge graph triple retrieval used by the RAG context retrieval

The system also includes two supplementary features:
- **Feedback-based few-shot examples** (`retrieve_feedback_examples`, lines 615-661) -- retrieves past Q&A pairs scored by keyword overlap to provide few-shot examples in the prompt.
- **Curation checks** (`check_curation`, lines 664-729) -- heuristic quality checks (missing tags, short content, stale entities) that surface data hygiene suggestions alongside answers.

---

## Guided Examples

### Example 1: Structured Query -- "How many projects?"

Let's trace a structured query through the system:

1. **Intent classification**: `classify_intent("how many projects?")` detects the entity type `project` (from the synonym map) and matches the regex `r"how many|count|number of"`. Returns `("count", ["project"])`.

2. **Structured execution**: `execute_structured_query()` sees the `count` intent, looks up the `Project` model from `search_service.MODEL_CONFIG`, runs `db.query(func.count(Project.id))`, and returns a `StructuredResult` like:
   ```
   StructuredResult(answer_text="Here are the counts:\n\n- **projects**: 12")
   ```

3. **No LLM call needed** -- the answer is returned directly. This is fast, deterministic, and costs zero compute.

### Example 2: General Query -- "What do I know about machine learning?"

Now let's trace a general query through the full RAG pipeline:

1. **Intent classification**: `classify_intent("what do I know about machine learning?")` doesn't match any structured patterns. Returns `("general", [])`.

2. **Structured execution**: `execute_structured_query()` sees `general`, returns `None` -- signaling the caller to use RAG.

3. **Context retrieval**: `retrieve_context()` kicks in:
   - `_extract_keywords()` strips stop words, producing `["machine", "learning"]`
   - **Text search**: Searches entity titles and descriptions for "machine learning" and individually for "machine" and "learning"
   - **Tag search**: Checks if any tag names contain "machine learning"
   - **Graph traversal**: For the top 5 hits, fetches knowledge triples to find connected entities (e.g., a project linked to a source paper)
   - **Active context**: Adds currently active entities for awareness

4. **Prompt building**: `build_rag_prompt()` formats everything into sections:
   ```
   User question: What do I know about machine learning?

   ## Currently Active Entities
   [project#3] ML Research (ACTIVE)

   ## Relevant Knowledge Base Entries
   [note#42] Neural Network Notes — Overview of backpropagation... [tags: Machine Learning]
   [source#7] Deep Learning Book — Goodfellow et al. textbook...

   ## Knowledge Graph Relationships
   [project#3] —references→ [source#7]
   [note#42] —belongs_to→ [project#3]
   ```

5. **LLM generation**: `llm_service.generate(prompt)` sends the augmented prompt to Ollama, which synthesizes a natural language answer grounded in the retrieved context.

---

## Exercises

### Exercise 1: Add a New Structured Intent

**Task**: Look at `classify_intent()` in `src/wellbegun/services/rag_service.py:104-157`. Imagine you want to add a new intent called `"oldest"` that matches queries like "what's my oldest project?" or "show me the oldest notes". Where in the function would you add it? What regex pattern would you use? What would the corresponding handler in `execute_structured_query()` look like?

<details>
<summary>Hint</summary>
You'd add it near the `recent` intent (line 138) since they're both date-based. The regex might be `r"oldest|first|earliest"`. The handler would query with `.order_by(model.created_at.asc()).limit(5)` instead of `.desc()`.
</details>

### Exercise 2: Trace the Context Sources

**Task**: Open `src/wellbegun/services/rag_service.py` and find the four data sources in `retrieve_context()` (lines 454-584). For each source, identify: (a) what function or service it calls, (b) what kind of information it adds, and (c) under what conditions it activates.

<details>
<summary>Hint</summary>
The four sources are: (1) keyword text search via `search_service.search()` -- activates when `_extract_keywords()` returns non-empty results; (2) tag-based search via `_find_tag_ids_by_query()` + `search_service.search()` -- activates when tag names are found in the query; (3) graph neighbors via `knowledge_service.get_triples_for_entity()` -- always runs for the top 5 search hits; (4) active context via `active_context_service.get_active_context()` -- always runs.
</details>

---

## Knowledge Check

**Q1**: What is the main advantage of RAG over fine-tuning a model on your data?
- A) RAG produces more creative responses
- B) RAG retrieves context at query time, avoiding expensive retraining when data changes
- C) RAG doesn't need any data at all
- D) RAG always produces deterministic answers

<details>
<summary>Answer</summary>
**B) RAG retrieves context at query time, avoiding expensive retraining when data changes** -- Fine-tuning requires retraining the model every time your data changes. RAG retrieves the latest data on every query, so your knowledge base is always up to date without any model retraining.
</details>

**Q2**: In WellBegun, when does the system skip the LLM entirely?
- A) When the query is too short
- B) When Ollama is unavailable
- C) When `classify_intent()` returns a structured intent like `count` or `list_active`
- D) When there are no entities in the database

<details>
<summary>Answer</summary>
**C) When `classify_intent()` returns a structured intent like `count` or `list_active`** -- Structured intents are handled by `execute_structured_query()` which answers directly with SQL. This is faster and deterministic. See `src/wellbegun/services/rag_service.py:179-340`.
</details>

**Q3**: Why does `retrieve_context()` use multiple retrieval strategies instead of just keyword search?
- A) To make the code more complex
- B) Because keyword search is unreliable
- C) Each strategy captures different types of relevance -- text similarity, categorical tags, structural relationships, and current focus
- D) Because the database requires multiple queries

<details>
<summary>Answer</summary>
**C) Each strategy captures different types of relevance** -- Keyword search finds textual matches, tag search finds categorical relationships, graph traversal finds structural connections (e.g., a project linked to a source), and active context adds awareness of the user's current focus. Together, they provide richer context than any single strategy alone.
</details>

**Q4**: What role does `build_rag_prompt()` play in the pipeline?
- A) It sends the query to the LLM
- B) It formats retrieved context into labeled sections so the LLM can distinguish between different types of information
- C) It classifies the user's intent
- D) It stores the response in the database

<details>
<summary>Answer</summary>
**B) It formats retrieved context into labeled sections so the LLM can distinguish between different types of information** -- The prompt is organized into sections like "Currently Active Entities", "Relevant Knowledge Base Entries", and "Knowledge Graph Relationships". This structure helps the LLM understand the provenance and type of each piece of context. See `src/wellbegun/services/rag_service.py:587-612`.
</details>

---

## Further Reading
- [What is Retrieval-Augmented Generation (RAG)?](https://research.ibm.com/blog/retrieval-augmented-generation-RAG) -- article
- [LangChain RAG Tutorial](https://python.langchain.com/docs/tutorials/rag/) -- tutorial
- [Ollama Documentation](https://ollama.com/) -- official-docs
- [Building RAG Applications (Hugging Face)](https://huggingface.co/learn/cookbook/en/rag_with_hugging_face_gemma_elasticsearch) -- tutorial

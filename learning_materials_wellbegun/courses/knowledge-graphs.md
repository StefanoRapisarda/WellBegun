# Knowledge Graphs & Semantic Triples

> **Category**: concept | **Difficulty**: beginner | **Time**: ~15 min
> **Prerequisites**: SQLAlchemy ORM

## Overview
If you've worked with pandas DataFrames, you think in tables and rows. Knowledge graphs think in relationships: Subject -> Predicate -> Object. It's like a DataFrame with exactly three columns -- but those relationships form a web of connected knowledge, not flat rows.

In WellBegun, the knowledge graph connects every entity (projects, activities, logs, notes, sources, actors, plans, collections) through meaningful relationships, enabling the app to answer questions like "what is connected to this project?" and to provide rich context to the AI assistant.

**Key takeaways:**
- A knowledge graph stores facts as triples: (subject, predicate, object) -- e.g., (project#1, "contains", activity#5)
- Triples are more flexible than foreign keys -- any entity can relate to any other
- The predicate (verb) gives the relationship meaning: "contains", "cites", "belongs to"
- Graphs enable traversal: "find everything connected to project X"

---

## Core Concepts

### 1. The Triple (Subject, Predicate, Object)

The fundamental unit of a knowledge graph is the **triple** -- a three-part fact statement. In a sentence: "Project#1 *contains* Activity#5". The subject acts, the predicate describes the relationship, and the object receives the action.

WellBegun stores triples in the `knowledge_triples` table, modeled with SQLAlchemy:

```python
# From src/wellbegun/models/knowledge_triple.py:9-27
class KnowledgeTriple(Base):
    __tablename__ = "knowledge_triples"
    __table_args__ = (
        UniqueConstraint(
            "subject_type", "subject_id", "object_type", "object_id",
            name="uq_knowledge_triple",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(20), nullable=False)
    subject_id: Mapped[int] = mapped_column(Integer, nullable=False)
    predicate: Mapped[str] = mapped_column(String(100), nullable=False)
    object_type: Mapped[str] = mapped_column(String(20), nullable=False)
    object_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
```

The frontend mirrors this with a TypeScript interface:

```typescript
// From frontend/src/lib/types.ts:159-167
export interface KnowledgeTriple {
    id: number;
    subject_type: string;
    subject_id: number;
    predicate: string;
    object_type: string;
    object_id: number;
    created_at: string;
}
```

Notice the **polymorphic identity** pattern: instead of a foreign key to one specific table, the triple uses `subject_type` + `subject_id` (and `object_type` + `object_id`) to reference *any* entity in the system. This is what makes knowledge graphs more flexible than traditional relational foreign keys.

The `UniqueConstraint` on `(subject_type, subject_id, object_type, object_id)` ensures there is at most one triple between any two specific entities. If the predicate changes, the existing triple is updated rather than duplicated.

### 2. Entity Types and Polymorphism

WellBegun defines eight entity types that can participate in the graph:

```python
# From src/wellbegun/services/structural_relations.py:6-15
ENTITY_TYPES = [
    "project",
    "activity",
    "note",
    "log",
    "source",
    "actor",
    "plan",
    "collection",
]
```

Any entity can be the subject or object of a triple. A `note` can cite a `source`, an `actor` can contribute to a `project`, a `collection` can contain a `log`. This polymorphic approach means you do not need a separate relationship table for each pair of entity types -- one `knowledge_triples` table handles them all.

If you are coming from pandas, think of it this way: instead of having separate DataFrames for "project-activity relationships", "project-note relationships", and "note-source relationships", you have one DataFrame where each row is `[subject_type, subject_id, predicate, object_type, object_id]`. The types tell you what kind of entities are involved.

### 3. Structural vs Semantic Predicates

WellBegun distinguishes two categories of predicates:

**Structural predicates** are auto-generated from the application's data model. When you add a note to a collection, the system automatically creates a triple with the predicate "contains". These are defined in a lookup table:

```python
# From src/wellbegun/services/structural_relations.py:22-87 (selected entries)
STRUCTURAL_PREDICATES: dict[tuple[str, str], str] = {
    ("project", "activity"): "contains",
    ("project", "note"): "contains",
    ("project", "source"): "references",
    ("project", "actor"): "involves",
    ("activity", "source"): "consults",
    ("activity", "actor"): "assigned to",
    ("note", "source"): "cites",
    ("note", "actor"): "mentions",
    ("actor", "project"): "contributes to",
    ("collection", "note"): "contains",
    # ... many more pairs
}
```

The lookup function falls back to "related to" for unlisted pairs:

```python
# From src/wellbegun/services/structural_relations.py:134-136
def get_structural_predicate(source_type: str, target_type: str) -> str:
    """Return the default structural predicate for a (source, target) type pair."""
    return STRUCTURAL_PREDICATES.get((source_type, target_type), "related to")
```

**Semantic predicates** are user-created relationships that carry meaning beyond the application's structure. These are organized by category:

```python
# From src/wellbegun/services/structural_relations.py:89-131 (selected entries)
SEMANTIC_RELATIONS: dict[str, list[dict[str, str]]] = {
    "Meaning": [
        {"key": "defines", "forward": "defines", "reverse": "defined by"},
        {"key": "contrasts with", "forward": "contrasts with", "reverse": "contrasts with"},
    ],
    "Reasoning": [
        {"key": "supports", "forward": "supports", "reverse": "supported by"},
        {"key": "contradicts", "forward": "contradicts", "reverse": "contradicted by"},
    ],
    "Causality": [
        {"key": "causes", "forward": "causes", "reverse": "caused by"},
        {"key": "depends on", "forward": "depends on", "reverse": "depended on by"},
    ],
    # ... Process, Planning, Evaluation, Participation categories
}
```

Notice that semantic predicates have both a forward and reverse form. If note#3 "supports" note#7, then note#7 is "supported by" note#3. The `swap_triple_direction` function in the knowledge service uses this to flip relationships.

### 4. Graph Traversal

Retrieving all connections for an entity is the most fundamental graph operation -- a **one-hop traversal**. The `get_triples_for_entity` function finds every triple where the entity appears as either subject or object:

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

The key insight is the `or_` clause: the entity might be the subject ("project#1 contains note#3") or the object ("note#3 belongs to project#1"). To find all neighbors, you must check both positions.

If you are familiar with SQL, this translates to:
```sql
SELECT * FROM knowledge_triples
WHERE (subject_type = 'project' AND subject_id = 1)
   OR (object_type = 'project' AND object_id = 1)
ORDER BY created_at DESC;
```

### 5. Graph Population

WellBegun builds its knowledge graph by scanning existing data relationships. The `populate_from_focus` function (159-332 in knowledge_service.py) is the main entry point. It works in stages:

1. **Find entity tags** for the selected projects/activities
2. **Discover tagged entities** -- other entities connected through the tagging system
3. **Create board nodes** for visualization (with automatic column-based layout)
4. **Create triples** from tag relationships (using `create_triple`'s upsert pattern)
5. **Create triples from FK relationships** -- e.g., if an Activity has a `source_id` foreign key, create an "activity consults source" triple

The `create_triple` function implements an **upsert pattern** -- it checks for an existing triple between the same two entities and updates the predicate if needed, rather than creating a duplicate:

```python
# From src/wellbegun/services/knowledge_service.py:36-74
def create_triple(
    db: Session,
    subject_type: str,
    subject_id: int,
    predicate: str,
    object_type: str,
    object_id: int,
) -> KnowledgeTriple:
    """Create or return existing triple (upsert by unique constraint).

    Matches on (subject_type, subject_id, object_type, object_id).
    If a triple exists with a different predicate, updates it.
    """
    existing = (
        db.query(KnowledgeTriple)
        .filter(
            KnowledgeTriple.subject_type == subject_type,
            KnowledgeTriple.subject_id == subject_id,
            KnowledgeTriple.object_type == object_type,
            KnowledgeTriple.object_id == object_id,
        )
        .first()
    )
    if existing:
        if existing.predicate != predicate:
            existing.predicate = predicate
            db.flush()
        return existing
    triple = KnowledgeTriple(
        subject_type=subject_type,
        subject_id=subject_id,
        predicate=predicate,
        object_type=object_type,
        object_id=object_id,
    )
    db.add(triple)
    db.commit()
    db.refresh(triple)
    return triple
```

---

## In This Project

The knowledge graph system in WellBegun spans three layers:

**Data layer**: The `KnowledgeTriple` SQLAlchemy model (`src/wellbegun/models/knowledge_triple.py`) stores triples in the database with a unique constraint ensuring one triple per entity pair.

**Service layer**: `src/wellbegun/services/knowledge_service.py` provides CRUD operations (`create_triple`, `delete_triple`, `update_triple_predicate`), traversal (`get_triples_for_entity`, `get_all_triples`), relationship management (`swap_triple_direction`), and graph building (`populate_from_focus`, `populate_all`).

**Predicate definitions**: `src/wellbegun/services/structural_relations.py` defines the vocabulary of structural and semantic predicates as pure constants, safely importable from anywhere without circular dependencies.

**AI integration**: The RAG service (`src/wellbegun/services/rag_service.py`) uses graph traversal to provide relationship context to the AI assistant, formatting triples as human-readable lines like `[project#1] --contains--> [note#3]`.

**Visualization**: The `KnowledgeGraph.svelte` component (`frontend/src/lib/components/graph/KnowledgeGraph.svelte`) renders the graph as an interactive board with draggable entity cards and visible relationship edges.

**Graph-keeping side effects**: Other services create triples as side effects. For example, the collection service creates a "contains" triple whenever an item is added to a collection.

---

## Guided Examples

### Example 1: How Adding an Item to a Collection Creates a Triple

When you add an item to a collection, the collection service does not just insert a `CollectionItem` row -- it also creates a knowledge triple to keep the graph in sync:

```python
# From src/wellbegun/services/collection_service.py:166-176
    # Create "contains" knowledge triple to keep graph in sync
    from wellbegun.services import knowledge_service
    predicate = get_structural_predicate("collection", member_entity_type)
    knowledge_service.create_triple(
        db,
        subject_type="collection",
        subject_id=collection_id,
        predicate=predicate,
        object_type=member_entity_type,
        object_id=member_entity_id,
    )
```

Here is what happens step by step:

1. `get_structural_predicate("collection", member_entity_type)` looks up the default verb. For most entity types added to a collection, this returns `"contains"`.
2. `knowledge_service.create_triple(...)` either creates a new triple or finds the existing one (upsert behavior).
3. The result: `(collection#7, "contains", note#12)` is now a fact in the knowledge graph.

This pattern -- creating triples as a side effect of domain operations -- ensures the graph stays consistent with the application state without requiring users to manually manage relationships.

### Example 2: How the RAG Service Traverses the Graph for Context

When the AI assistant answers a question, it uses graph neighbors to provide richer context. For the top 5 search results, it fetches up to 3 triples each:

```python
# From src/wellbegun/services/rag_service.py:543-568
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
                f"---{triple.predicate}---> "
                f"[{triple.object_type}#{triple.object_id}]"
            )
            graph_lines.append(line)
```

This produces lines like:
```
[project#1] --contains--> [activity#5]
[activity#5] --consults--> [source#2]
[source#2] --mentioned by--> [actor#3]
```

The AI assistant receives these lines as context, allowing it to understand not just the individual entities but how they relate to each other. For a data scientist, this is analogous to enriching your feature set: instead of passing isolated records to a model, you pass the entity *and its neighborhood*.

---

## Exercises

### Exercise 1: Trace a Triple's Lifecycle

**Task**: Open `src/wellbegun/services/knowledge_service.py` and trace what happens when `create_triple` is called with a subject/object pair that already exists but with a different predicate. What SQL queries does it run? What happens to the existing row?

<details>
<summary>Hint</summary>
Look at lines 49-63. The function first queries for an existing triple matching on (subject_type, subject_id, object_type, object_id). If found with a different predicate, it updates the predicate in place and calls db.flush() rather than db.commit(). The unique constraint ensures only one triple per entity pair.
</details>

### Exercise 2: Extend the Graph Traversal

**Task**: The current `get_triples_for_entity` (lines 18-33) does a one-hop traversal. How would you modify it to do a two-hop traversal -- finding entities connected to the entity's neighbors? Sketch the approach in pseudocode.

<details>
<summary>Hint</summary>
Call get_triples_for_entity to get the first hop. For each triple returned, extract the "other" entity (the one that is not the starting entity). Then call get_triples_for_entity again for each neighbor. Collect all triples from both hops, deduplicating by triple ID.
</details>

---

## Knowledge Check

**Q1**: What are the three components of a knowledge triple?
- A) Table, Row, Column
- B) Subject, Predicate, Object
- C) Entity, Attribute, Value
- D) Key, Value, Type

<details>
<summary>Answer</summary>
**B) Subject, Predicate, Object** -- A triple represents a fact as (subject, predicate, object), such as (project#1, "contains", activity#5). The subject is the actor, the predicate is the verb describing the relationship, and the object is what the relationship points to.
</details>

**Q2**: Why does WellBegun use `subject_type` + `subject_id` instead of a single foreign key?
- A) It is faster for database lookups
- B) SQLAlchemy does not support foreign keys
- C) It allows any entity type to be the subject or object of a triple
- D) It reduces the number of database tables needed

<details>
<summary>Answer</summary>
**C) It allows any entity type to be the subject or object of a triple** -- This polymorphic identity pattern means a single knowledge_triples table can store relationships between any combination of entity types (project, note, source, actor, etc.) without needing a separate join table for each pair.
</details>

**Q3**: What is the purpose of the `or_` clause in `get_triples_for_entity`?
- A) It combines two different database queries for performance
- B) It finds triples where the entity is either the subject or the object
- C) It handles the case where the entity does not exist
- D) It sorts results by creation date

<details>
<summary>Answer</summary>
**B) It finds triples where the entity is either the subject or the object** -- An entity can appear on either side of a relationship. Project#1 might be the subject in "project#1 contains note#3" and the object in "actor#2 contributes to project#1". The or_ clause ensures both directions are captured.
</details>

**Q4**: What is the difference between a structural predicate and a semantic predicate?
- A) Structural predicates are stored in the database; semantic predicates are not
- B) Structural predicates are auto-generated from data relationships; semantic predicates are user-chosen meanings
- C) Structural predicates connect entities; semantic predicates connect triples
- D) There is no difference -- they are interchangeable terms

<details>
<summary>Answer</summary>
**B) Structural predicates are auto-generated from data relationships; semantic predicates are user-chosen meanings** -- Structural predicates like "contains" are assigned automatically when entities are related through the app's data model (e.g., adding an item to a collection). Semantic predicates like "supports", "contradicts", or "causes" are chosen by the user to express richer, domain-specific meaning.
</details>

---

## Further Reading
- [Knowledge Graphs - Introduction (Stanford CS520)](https://web.stanford.edu/class/cs520/) -- course
- [RDF (Resource Description Framework) Primer](https://www.w3.org/TR/rdf11-primer/) -- official-docs
- [NetworkX: Python Graph Library](https://networkx.org/documentation/stable/tutorial.html) -- tutorial
- [Knowledge Graphs: Fundamentals, Techniques, and Applications (Hogan et al.)](https://kgbook.org/) -- book

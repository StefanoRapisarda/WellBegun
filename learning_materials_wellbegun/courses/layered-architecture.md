# Layered Architecture

> **Category**: pattern | **Difficulty**: beginner | **Time**: ~20 min
> **Prerequisites**: client-server-architecture

## Overview

Layered architecture is a design pattern that organizes code into horizontal layers, each with a distinct responsibility. Each layer only talks to the layer directly below it, creating a clear chain of delegation. When you modify one layer (e.g., switching databases), the layers above it remain unaffected -- as long as the interface between them stays the same.

Think of it like a well-organized kitchen: the front-of-house (waiter) takes the order, passes it to the kitchen (chef), who fetches ingredients from the pantry (storage). The waiter never goes into the pantry, and the pantry does not know what dish is being made. Each role has a clear boundary.

In WellBegun, this pattern appears on both the backend (Python/FastAPI) and the frontend (Svelte/TypeScript), and understanding it will help you know exactly where to put new code.

**Key takeaways:**
- Code is organized into layers: presentation (routers), business logic (services), data access (models/ORM)
- Each layer only depends on the layer directly below it
- Changes in one layer do not ripple through the others (as long as interfaces are preserved)
- Both the backend and frontend follow this pattern independently

---

## Core Concepts

### The Three Backend Layers

WellBegun's backend has three distinct layers:

```
HTTP Request
    |
    v
[Presentation Layer]  --  Routers (src/wellbegun/routers/)
    |                     Handles HTTP: parsing requests, returning responses,
    |                     status codes, error translation
    v
[Business Logic Layer]  --  Services (src/wellbegun/services/)
    |                       Contains the rules: what happens when you create,
    |                       update, delete. Orchestrates operations.
    v
[Data Access Layer]  --  Models + Database (src/wellbegun/models/, database.py)
                         Knows how to store and retrieve data.
                         Defines the schema (table structure).
```

### Layer Responsibilities

**Presentation Layer (Routers)**
- Receives HTTP requests and extracts parameters
- Validates input using Pydantic schemas
- Calls the appropriate service function
- Translates errors into HTTP status codes (e.g., `None` from service becomes 404)
- Shapes the response using `response_model`

**Business Logic Layer (Services)**
- Contains the actual logic: creating entities, managing tags, cleaning up related data
- Does NOT know about HTTP, status codes, or JSON
- Receives plain Python arguments and returns Python objects
- Orchestrates multiple operations (e.g., create note + create tag in one transaction)

**Data Access Layer (Models + ORM)**
- Defines the database schema as Python classes
- Provides the session mechanism for transactions
- The ORM translates Python operations into SQL

### Why Separate Layers?

The key benefit is that each layer can change independently:

- Want to add a CLI interface alongside the web API? Write a new presentation layer that calls the same services.
- Want to add validation logic when creating notes? Modify the service layer. The router and model stay the same.
- Want to switch from SQLite to PostgreSQL? Change the database configuration. Services and routers are unaffected.

### Dependency Direction

Upper layers depend on lower layers, never the reverse:

- Routers import services: `from wellbegun.services import note_service`
- Services import models: `from wellbegun.models.note import Note`
- Models do NOT import services or routers
- Services do NOT import routers

This one-way dependency chain is what keeps the layers decoupled.

### The Frontend Layers

The frontend follows an analogous pattern:

```
User Interaction
    |
    v
[Components]  --  Svelte components (frontend/src/lib/components/)
    |              Handle UI: rendering, event handling, user input
    v
[Stores]  --  Svelte stores (frontend/src/lib/stores/)
    |          Manage state: hold data in memory, notify components of changes
    v
[API Client]  --  API functions (frontend/src/lib/api/)
                   Communicate with the backend: fetch, POST, PUT, DELETE
```

Components call store functions. Stores call API functions. API functions call the backend. This mirrors the backend's router -> service -> model chain.

---

## In This Project

### Backend: The Note Creation Flow

Here is the complete path a "create note" request takes through all backend layers:

**Layer 1 -- Router** (`src/wellbegun/routers/notes.py`):
```python
@router.post("/", response_model=NoteOut, status_code=201)
def create_note(data: NoteCreate, db: Session = Depends(get_db)):
    return note_service.create(db, title=data.title, content=data.content)
```
The router's job: receive the HTTP POST, validate the body as `NoteCreate`, call the service, return 201.

**Layer 2 -- Service** (`src/wellbegun/services/note_service.py`):
```python
def create(db: Session, title: str, content: str | None = None) -> Note:
    note = Note(title=title, content=content)
    db.add(note)
    db.flush()
    create_entity_tag(db, title, "note", "note", note.id)
    db.commit()
    db.refresh(note)
    return note
```
The service's job: create the Note object, stage it in the session, also create an entity tag (business logic!), commit everything. Notice it knows nothing about HTTP.

**Layer 3 -- Model** (`src/wellbegun/models/note.py`):
```python
class Note(Base):
    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # ... other columns
```
The model's job: define the database schema. It does not know how it is being used.

**Layer 3 -- Database** (`src/wellbegun/database.py`):
```python
def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```
The database module provides sessions. It does not know what queries will be run.

### Frontend: The Note Loading Flow

**Layer 1 -- Component** (a Svelte component calls):
```typescript
import { loadNotes } from '$lib/stores/notes';
onMount(() => loadNotes());
```

**Layer 2 -- Store** (`frontend/src/lib/stores/notes.ts`):
```typescript
export const notes = writable<Note[]>([]);

export async function loadNotes() {
    try {
        notes.set(await getNotes());
    } catch (e) {
        console.warn('Failed to load notes:', e);
    }
}
```

**Layer 3 -- API Client** (`frontend/src/lib/api/notes.ts`):
```typescript
export async function getNotes(): Promise<Note[]> {
    const res = await fetch(`${BASE}/`);
    return res.json();
}
```

The component does not call `fetch` directly. The store does not construct URLs. Each layer has a single responsibility.

---

## Guided Examples

### Example: Tracing a Create-Note Request Through All Layers

Let us follow a "create note" request from the user's browser all the way to the database and back:

**Step 1 -- Frontend Component**: The user types a title and clicks "Create." The component calls the API client:
```typescript
const newNote = await createNote({ title: "My Idea", content: "Some thoughts" });
```

**Step 2 -- Frontend API Client**: `createNote` sends an HTTP POST:
```typescript
const res = await fetch('/api/notes/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: "My Idea", content: "Some thoughts" })
});
return res.json();
```

**Step 3 -- Backend Router**: FastAPI receives the POST, validates the body as `NoteCreate`, and calls:
```python
note_service.create(db, title=data.title, content=data.content)
```

**Step 4 -- Backend Service**: Creates a `Note` object, adds it to the session, creates an entity tag, commits:
```python
note = Note(title="My Idea", content="Some thoughts")
db.add(note)
db.flush()  # INSERT INTO notes ... → id = 42
create_entity_tag(db, "My Idea", "note", "note", 42)
db.commit()
db.refresh(note)
return note  # Note object with id=42
```

**Step 5 -- Backend Router**: The returned `Note` object is serialized through `NoteOut` and sent as JSON with status 201:
```json
{
    "id": 42,
    "title": "My Idea",
    "content": "Some thoughts",
    "is_active": false,
    "is_archived": false,
    "created_at": "2026-03-05T10:30:00",
    "updated_at": "2026-03-05T10:30:00"
}
```

**Step 6 -- Frontend API Client**: Parses the JSON response and returns a typed `Note` object.

**Step 7 -- Frontend Component**: Receives the new note and can update the UI.

Notice how data transforms at each layer boundary: JSON in the frontend, Pydantic schema at the router, plain Python arguments in the service, ORM objects at the data layer, SQL in the database.

---

## Exercises

### Exercise 1: Identify the Layer

**Task**: For each code snippet below, identify which layer it belongs to (presentation/router, business logic/service, or data access/model):

1. `raise HTTPException(status_code=404, detail="Note not found")`
2. `db.query(Note).filter(Note.id == note_id).first()`
3. `__tablename__ = "notes"`
4. `note.is_active = True; db.commit()`
5. `response_model=list[NoteOut]`

<details>
<summary>Hint</summary>
1) Presentation -- HTTPException is an HTTP concept. 2) Service -- this is a query within business logic. 3) Data access/model -- schema definition. 4) Service -- modifying state and committing. 5) Presentation -- response shaping is the router's job.
</details>

### Exercise 2: Where Does New Logic Go?

**Task**: For each requirement below, identify which layer should change and why:

1. "When deleting a note, also delete all related knowledge triples" (already implemented -- look at `note_service.delete()`)
2. "Return a 403 Forbidden status when a user tries to delete someone else's note"
3. "Add a `word_count` column to the notes table"
4. "When creating a note, auto-generate a summary using an LLM"

<details>
<summary>Hint</summary>
1) Service layer -- orchestrating deletion of related data is business logic. 2) Presentation layer -- translating authorization checks into HTTP status codes. 3) Data access/model layer -- schema change. 4) Service layer -- calling an LLM is business logic, not HTTP handling or schema definition.
</details>

---

## Knowledge Check

**Q1**: In WellBegun's backend, which layer is responsible for returning HTTP 404 when a note is not found?
- A) The model layer (Note class)
- B) The service layer (note_service.py)
- C) The presentation layer (router in notes.py)
- D) The database layer (database.py)

<details>
<summary>Answer</summary>
**C) The presentation layer (router)** -- The service returns `None` when a note is not found. The router translates this into `HTTPException(status_code=404)`. The service should not know about HTTP status codes.
</details>

**Q2**: Why does the service layer accept plain Python arguments (title: str) rather than Pydantic schemas (NoteCreate)?
- A) Pydantic is too slow for the service layer
- B) So the service can be called from any context (API, CLI, tests) without requiring HTTP-specific types
- C) Services cannot import Pydantic
- D) There is no particular reason

<details>
<summary>Answer</summary>
**B) So the service can be called from any context** -- If the service accepted `NoteCreate`, it would be coupled to the API layer. By accepting plain arguments, the same service function can be called from a CLI tool, a test, or a background job without constructing Pydantic objects.
</details>

**Q3**: In the frontend, why does the store call the API client instead of using fetch directly?
- A) Svelte does not support fetch
- B) Separation of concerns: the store manages state, the API client handles HTTP communication
- C) The API client is faster than fetch
- D) fetch only works in components, not stores

<details>
<summary>Answer</summary>
**B) Separation of concerns** -- The store's job is to hold state and notify subscribers of changes. The API client's job is to construct HTTP requests and parse responses. If the API URL structure changes, only the API client needs to change -- stores and components are unaffected.
</details>

**Q4**: Which direction do dependencies flow in a layered architecture?
- A) Lower layers depend on upper layers
- B) Upper layers depend on lower layers
- C) All layers depend on each other
- D) Dependencies flow in both directions

<details>
<summary>Answer</summary>
**B) Upper layers depend on lower layers** -- Routers import services, services import models. Models never import services or routers. This one-way dependency chain keeps layers decoupled and independently replaceable.
</details>

---

## Further Reading
- [Layered Architecture Pattern (Mark Richards)](https://www.oreilly.com/library/view/software-architecture-patterns/9781491971437/ch01.html) -- book-chapter
- [FastAPI Project Structure Best Practices](https://fastapi.tiangolo.com/tutorial/bigger-applications/) -- official-docs
- [Separation of Concerns (Wikipedia)](https://en.wikipedia.org/wiki/Separation_of_concerns) -- reference
- [Clean Architecture (Robert C. Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html) -- article

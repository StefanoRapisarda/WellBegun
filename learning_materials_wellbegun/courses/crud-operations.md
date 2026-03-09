# CRUD Operations

> **Category**: concept | **Difficulty**: beginner | **Time**: ~15 min
> **Prerequisites**: None

## Overview
CRUD stands for **Create, Read, Update, Delete** -- the four fundamental operations you can perform on any piece of stored data. If you have ever inserted a row into a pandas DataFrame, queried it, changed a value, and dropped it, you have performed CRUD operations.

In WellBegun, every entity type (Note, Project, Source, Actor, Activity, Plan, Collection, Log) supports the same four operations. The pattern repeats so consistently that once you understand CRUD for Notes, you understand it for all eight entity types.

CRUD is universal because it maps directly to:
- **HTTP methods**: POST, GET, PUT, DELETE
- **SQL statements**: INSERT, SELECT, UPDATE, DELETE
- **User intentions**: "save this", "show me that", "change this", "remove that"

**Key takeaways:**
- CRUD is the universal pattern for data manipulation in any application
- Each operation maps to an HTTP method and a SQL statement
- WellBegun implements CRUD identically for every entity type through a router -> service -> model layered architecture
- Understanding the Notes CRUD gives you the template for every other entity

---

## Core Concepts

### The Four Operations

| CRUD | HTTP Method | SQL Statement | What it does |
|------|------------|---------------|--------------|
| **C**reate | POST | INSERT | Add a new record |
| **R**ead | GET | SELECT | Retrieve one or many records |
| **U**pdate | PUT | UPDATE | Modify an existing record |
| **D**elete | DELETE | DELETE | Remove a record |

### How WellBegun Layers CRUD

Each CRUD operation flows through three layers:

```
Frontend (fetch)  -->  Router (HTTP endpoint)  -->  Service (business logic)  -->  Model (database)
```

1. **Router** (`src/wellbegun/routers/notes.py`) -- defines HTTP endpoints, validates input via Pydantic schemas, returns HTTP responses
2. **Service** (`src/wellbegun/services/note_service.py`) -- contains business logic, interacts with the database via SQLAlchemy
3. **Model** (`src/wellbegun/models/note.py`) -- defines the database table structure as a Python class

This separation means the router never touches the database directly, and the service never deals with HTTP status codes.

### Create = POST = INSERT

Creating a note sends JSON from the frontend, validates it, creates a database row, and returns the new record:

```python
# Router: src/wellbegun/routers/notes.py:24-26
@router.post("/", response_model=NoteOut, status_code=201)
def create_note(data: NoteCreate, db: Session = Depends(get_db)):
    return note_service.create(db, title=data.title, content=data.content)
```

```python
# Service: src/wellbegun/services/note_service.py:16-27
def create(
    db: Session,
    title: str,
    content: str | None = None,
) -> Note:
    note = Note(title=title, content=content)
    db.add(note)
    db.flush()
    create_entity_tag(db, title, "note", "note", note.id)
    db.commit()
    db.refresh(note)
    return note
```

The equivalent SQL would be:
```sql
INSERT INTO notes (title, content) VALUES ('My Note', 'Some text');
```

### Read = GET = SELECT

Reading comes in two flavors: list all, or get one by ID.

```python
# List all: src/wellbegun/routers/notes.py:11-13
@router.get("/", response_model=list[NoteOut])
def list_notes(db: Session = Depends(get_db)):
    return note_service.get_all(db)

# Get one: src/wellbegun/routers/notes.py:16-21
@router.get("/{note_id}", response_model=NoteOut)
def get_note(note_id: int, db: Session = Depends(get_db)):
    note = note_service.get_by_id(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note
```

```python
# Service: src/wellbegun/services/note_service.py:8-13
def get_all(db: Session) -> list[Note]:
    return db.query(Note).order_by(Note.created_at.desc()).all()

def get_by_id(db: Session, note_id: int) -> Note | None:
    return db.query(Note).filter(Note.id == note_id).first()
```

The equivalent SQL:
```sql
SELECT * FROM notes ORDER BY created_at DESC;
SELECT * FROM notes WHERE id = 5;
```

### Update = PUT = UPDATE

Updating accepts partial data (only the fields you want to change) and applies them:

```python
# Router: src/wellbegun/routers/notes.py:29-35
@router.put("/{note_id}", response_model=NoteOut)
def update_note(note_id: int, data: NoteUpdate, db: Session = Depends(get_db)):
    updates = data.model_dump(exclude_unset=True)
    note = note_service.update(db, note_id, **updates)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note
```

```python
# Service: src/wellbegun/services/note_service.py:30-41
def update(db: Session, note_id: int, **kwargs) -> Note | None:
    note = get_by_id(db, note_id)
    if not note:
        return None
    for key, value in kwargs.items():
        if hasattr(note, key):
            setattr(note, key, value)
    if "title" in kwargs and kwargs["title"] is not None:
        update_entity_tag(db, "note", note_id, kwargs["title"])
    db.commit()
    db.refresh(note)
    return note
```

The key detail: `data.model_dump(exclude_unset=True)` ensures only fields the client actually sent get updated. If the client sends `{"title": "New Title"}`, the content remains unchanged.

Equivalent SQL:
```sql
UPDATE notes SET title = 'New Title' WHERE id = 5;
```

### Delete = DELETE = DELETE

Deleting removes the record and cleans up related data:

```python
# Router: src/wellbegun/routers/notes.py:38-42
@router.delete("/{note_id}")
def delete_note(note_id: int, db: Session = Depends(get_db)):
    if not note_service.delete(db, note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return {"ok": True}
```

```python
# Service: src/wellbegun/services/note_service.py:44-52
def delete(db: Session, note_id: int) -> bool:
    note = get_by_id(db, note_id)
    if not note:
        return False
    delete_entity_tag(db, "note", note_id)
    delete_entity_graph_data(db, "note", note_id)
    db.delete(note)
    db.commit()
    return True
```

Notice the service cleans up related entity tags and knowledge graph data before deleting the note itself. This prevents orphaned references.

Equivalent SQL:
```sql
DELETE FROM entity_tags WHERE target_type = 'note' AND target_id = 5;
DELETE FROM knowledge_triples WHERE (subject_type = 'note' AND subject_id = 5) OR (object_type = 'note' AND object_id = 5);
DELETE FROM notes WHERE id = 5;
```

---

## In This Project

### The Pydantic Schemas Define the Contract

Each CRUD operation uses different Pydantic schemas to control what data goes in and what comes out:

```python
# From src/wellbegun/schemas/note.py
class NoteCreate(BaseModel):      # What the client sends to CREATE
    title: str
    content: str | None = None

class NoteUpdate(BaseModel):      # What the client sends to UPDATE
    title: str | None = None
    content: str | None = None

class NoteOut(BaseModel):          # What the server returns for all operations
    id: int
    title: str
    content: str | None = None
    is_active: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

Notice the differences:
- `NoteCreate` requires `title` (you must name a note when creating it)
- `NoteUpdate` makes everything optional (you might only update the content)
- `NoteOut` includes server-generated fields like `id`, `created_at`, timestamps

### The SQLAlchemy Model Defines the Table

```python
# From src/wellbegun/models/note.py
class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
```

The `id` is auto-generated (primary key). The `created_at` and `updated_at` are set automatically by SQLAlchemy. The client never needs to provide these.

### The Frontend Mirrors the Four Operations

```typescript
// From frontend/src/lib/api/notes.ts
export async function getNotes(): Promise<Note[]> { ... }                    // Read all
export async function getNote(id: number): Promise<Note> { ... }             // Read one
export async function createNote(data: { title: string; content?: string }): Promise<Note> { ... }  // Create
export async function updateNote(id: number, data: Partial<Note>): Promise<Note> { ... }            // Update
export async function deleteNote(id: number): Promise<void> { ... }          // Delete
```

---

## Guided Examples

### Example: Full CRUD Lifecycle for a Note

Let us walk through the entire lifecycle of a note, from creation to deletion.

**1. Create** -- A user types "Meeting Notes" and clicks save.

```typescript
// Frontend: frontend/src/lib/api/notes.ts:15-22
const note = await createNote({ title: "Meeting Notes", content: "Discussed roadmap" });
// note = { id: 42, title: "Meeting Notes", content: "Discussed roadmap", ... }
```

The frontend sends `POST /api/notes/` with `{"title": "Meeting Notes", "content": "Discussed roadmap"}`. The backend returns the note with `id: 42`.

**2. Read** -- The note list page loads and fetches all notes.

```typescript
// Frontend: frontend/src/lib/api/notes.ts:5-8
const allNotes = await getNotes();
// allNotes = [{ id: 42, title: "Meeting Notes", ... }, { id: 41, ... }, ...]
```

The frontend sends `GET /api/notes/`. The backend queries `SELECT * FROM notes ORDER BY created_at DESC` and returns the full list.

**3. Update** -- The user edits the title.

```typescript
// Frontend: frontend/src/lib/api/notes.ts:24-31
const updated = await updateNote(42, { title: "Q1 Meeting Notes" });
// updated = { id: 42, title: "Q1 Meeting Notes", content: "Discussed roadmap", ... }
```

The frontend sends `PUT /api/notes/42` with `{"title": "Q1 Meeting Notes"}`. Only the title changes; content is preserved because `exclude_unset=True` in the service layer ignores fields not sent.

**4. Delete** -- The user removes the note.

```typescript
// Frontend: frontend/src/lib/api/notes.ts:33-35
await deleteNote(42);
```

The frontend sends `DELETE /api/notes/42`. The backend removes the note, its entity tags, and any knowledge graph references, then returns `{"ok": true}`.

---

## Exercises

### Exercise 1: Identify CRUD in Another Entity

**Task**: Open `src/wellbegun/routers/sources.py` and `src/wellbegun/services/source_service.py`. Identify the function names for each CRUD operation. How do they compare to the notes equivalents?

<details>
<summary>Hint</summary>
Look for functions matching the pattern: <code>list_*</code> / <code>get_*</code> (Read), <code>create_*</code> (Create), <code>update_*</code> (Update), <code>delete_*</code> (Delete). The naming convention is identical across all entity types.
</details>

<details>
<summary>Answer</summary>
The pattern is identical across entities. In the router: <code>list_sources</code> (GET /), <code>get_source</code> (GET /{id}), <code>create_source</code> (POST /), <code>update_source</code> (PUT /{id}), <code>delete_source</code> (DELETE /{id}). In the service: <code>get_all</code>, <code>get_by_id</code>, <code>create</code>, <code>update</code>, <code>delete</code>. The only differences are entity-specific fields (e.g., <code>author</code> for sources).
</details>

### Exercise 2: Trace the Update Path

**Task**: When the frontend sends `PUT /api/notes/42` with `{"content": "Updated text"}`, what SQL statement does SQLAlchemy generate? What value does `data.model_dump(exclude_unset=True)` return?

<details>
<summary>Hint</summary>
<code>exclude_unset=True</code> means only fields explicitly provided in the JSON body are included. Since only <code>content</code> was sent, <code>title</code> is excluded.
</details>

<details>
<summary>Answer</summary>
<code>data.model_dump(exclude_unset=True)</code> returns <code>{"content": "Updated text"}</code> (title is excluded because it was not sent). SQLAlchemy generates: <code>UPDATE notes SET content = 'Updated text', updated_at = '...' WHERE id = 42</code>. The <code>updated_at</code> changes automatically due to <code>onupdate=datetime.utcnow</code> on the column.
</details>

### Exercise 3: Add a Field

**Task**: Suppose you want to add a `priority` field (integer, optional, defaults to 0) to Notes. Which three files would you need to modify, and what would you add to each?

<details>
<summary>Hint</summary>
Think about the three layers: model (database table), schema (API contract), and potentially the service (if the new field needs special handling during create/update).
</details>

<details>
<summary>Answer</summary>

1. **Model** (<code>src/wellbegun/models/note.py</code>) -- add <code>priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)</code>
2. **Schemas** (<code>src/wellbegun/schemas/note.py</code>) -- add <code>priority: int = 0</code> to <code>NoteCreate</code>, <code>priority: int | None = None</code> to <code>NoteUpdate</code>, <code>priority: int</code> to <code>NoteOut</code>
3. The **service** and **router** do not need changes because the service uses <code>**kwargs</code> and <code>setattr</code>, so new fields flow through automatically.
</details>

---

## Knowledge Check

**Q1**: Which HTTP method corresponds to the "Update" operation in CRUD?
- A) POST
- B) GET
- C) PUT
- D) DELETE

<details>
<summary>Answer</summary>
<strong>C) PUT</strong> -- PUT is used to update an existing resource. In WellBegun, <code>PUT /api/notes/{id}</code> updates a note (<code>src/wellbegun/routers/notes.py:29</code>).
</details>

**Q2**: What does `data.model_dump(exclude_unset=True)` do in the update endpoint?
- A) Removes all None values from the data
- B) Returns only the fields the client explicitly included in the request
- C) Converts the Pydantic model to a SQLAlchemy model
- D) Validates that all required fields are present

<details>
<summary>Answer</summary>
<strong>B) Returns only the fields the client explicitly included in the request.</strong> This is how partial updates work -- if the client only sends <code>{"title": "New"}</code>, the content field is not included in the dict and therefore not overwritten.
</details>

**Q3**: Why does the delete service function clean up entity tags and graph data before deleting the note?
- A) SQLAlchemy requires it for all delete operations
- B) To prevent orphaned references in related tables
- C) To make the delete operation slower and safer
- D) The tags and graph data are stored in the same table

<details>
<summary>Answer</summary>
<strong>B) To prevent orphaned references in related tables.</strong> The <code>entity_tags</code> and <code>knowledge_triples</code> tables reference notes by type and ID. Deleting the note without cleaning these up would leave dangling references (<code>src/wellbegun/services/note_service.py:44-52</code>).
</details>

**Q4**: Which SQL statement is equivalent to `db.query(Note).filter(Note.id == 5).first()`?
- A) INSERT INTO notes VALUES (5)
- B) SELECT * FROM notes WHERE id = 5 LIMIT 1
- C) UPDATE notes SET id = 5
- D) DELETE FROM notes WHERE id = 5

<details>
<summary>Answer</summary>
<strong>B) SELECT * FROM notes WHERE id = 5 LIMIT 1</strong> -- <code>.filter(Note.id == 5)</code> adds the WHERE clause, and <code>.first()</code> limits to one result (returning <code>None</code> if no match).
</details>

**Q5**: In WellBegun, why are there separate NoteCreate and NoteUpdate schemas instead of one shared schema?
- A) FastAPI requires separate schemas for each HTTP method
- B) Create requires title (mandatory), while Update makes all fields optional for partial updates
- C) One is for the frontend and the other is for the backend
- D) They have different security permissions

<details>
<summary>Answer</summary>
<strong>B) Create requires title (mandatory), while Update makes all fields optional for partial updates.</strong> <code>NoteCreate</code> has <code>title: str</code> (required) because every note needs a name. <code>NoteUpdate</code> has <code>title: str | None = None</code> because you might only want to change the content.
</details>

---

## Further Reading
- [MDN: HTTP Request Methods](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods) -- official-docs
- [FastAPI Tutorial: Request Body](https://fastapi.tiangolo.com/tutorial/body/) -- tutorial
- [SQLAlchemy ORM Tutorial](https://docs.sqlalchemy.org/en/20/orm/quickstart.html) -- official-docs
- [Pydantic: Model Methods](https://docs.pydantic.dev/latest/concepts/serialization/) -- official-docs

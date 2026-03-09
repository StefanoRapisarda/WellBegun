# API Design

> **Category**: concept | **Difficulty**: beginner | **Time**: ~20 min
> **Prerequisites**: client-server-architecture, crud-operations

## Overview

API design is the practice of defining how software components communicate with each other. In a web application like WellBegun, the API is the contract between the frontend (what the user sees) and the backend (where data lives). Good API design means consistent, predictable, and self-documenting endpoints -- when you see `GET /api/notes/42`, you can guess what it does without reading any documentation.

As a data scientist, you have consumed APIs (calling endpoints to fetch data), but you may not have thought deeply about why they are structured the way they are. This course covers the conventions and reasoning behind WellBegun's API design so you can extend it confidently for new entity types.

**Key takeaways:**
- API endpoints use nouns (resources) in URLs, not verbs -- the HTTP method provides the verb
- Consistent naming conventions make APIs predictable and self-documenting
- HTTP status codes communicate the outcome of each request
- Pydantic schemas validate input and shape output, acting as a contract between frontend and backend
- Good API design separates what the client sends (create/update schemas) from what the server returns (output schemas)

---

## Core Concepts

### Resource Naming: Nouns, Not Verbs

REST APIs identify resources (things) with URL paths and use HTTP methods (GET, POST, PUT, DELETE) for actions. The URL should be a noun:

| Correct | Incorrect |
|---------|-----------|
| `GET /api/notes` | `GET /api/getNotes` |
| `POST /api/notes` | `POST /api/createNote` |
| `DELETE /api/notes/5` | `POST /api/deleteNote?id=5` |

WellBegun follows this convention: each entity type gets a plural noun as its URL prefix (`/notes`, `/projects`, `/sources`, `/actors`, etc.).

### HTTP Methods as Verbs

The HTTP method tells the server what to do with the resource:

| Method | Purpose | Idempotent? | Request Body? |
|--------|---------|-------------|---------------|
| GET | Retrieve resource(s) | Yes | No |
| POST | Create a new resource | No | Yes |
| PUT | Update an existing resource | Yes | Yes |
| DELETE | Remove a resource | Yes | No |

**Idempotent** means calling it multiple times has the same effect as calling it once. GET, PUT, and DELETE are idempotent; POST is not (calling POST twice creates two resources).

### Status Codes: Telling the Client What Happened

Status codes are three-digit numbers that convey the result:

| Code | Meaning | When Used in WellBegun |
|------|---------|----------------------|
| **200** | OK | Successful GET, PUT, DELETE |
| **201** | Created | Successful POST (new resource created) |
| **404** | Not Found | Resource with given ID does not exist |
| **422** | Unprocessable Entity | Request body fails validation |

In WellBegun, the router explicitly sets `status_code=201` on POST endpoints. For errors, it raises `HTTPException` with the appropriate code.

### Request and Response Bodies

Not every HTTP request needs a body. GET and DELETE typically have no body -- the URL contains all needed information. POST and PUT carry JSON in the request body describing what to create or change.

The response body varies too:
- **GET /api/notes** returns a JSON array of all notes
- **GET /api/notes/5** returns a single JSON object
- **POST /api/notes** returns the newly created note (with its server-generated `id`)
- **DELETE /api/notes/5** returns a simple confirmation `{"ok": true}`

### Content Negotiation

The `Content-Type: application/json` header on requests tells the server "I am sending JSON." FastAPI reads this and automatically deserializes the JSON body into the Pydantic schema. The server always responds with JSON (FastAPI's default).

---

## In This Project

WellBegun's notes router in `src/wellbegun/routers/notes.py` demonstrates all these conventions:

```python
# From src/wellbegun/routers/notes.py
router = APIRouter(prefix="/notes", tags=["notes"])

@router.get("/", response_model=list[NoteOut])          # List all notes
def list_notes(db: Session = Depends(get_db)):
    return note_service.get_all(db)

@router.get("/{note_id}", response_model=NoteOut)        # Get one note
def get_note(note_id: int, db: Session = Depends(get_db)):
    note = note_service.get_by_id(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

@router.post("/", response_model=NoteOut, status_code=201)  # Create
def create_note(data: NoteCreate, db: Session = Depends(get_db)):
    return note_service.create(db, title=data.title, content=data.content)

@router.put("/{note_id}", response_model=NoteOut)        # Update
def update_note(note_id: int, data: NoteUpdate, db: Session = Depends(get_db)):
    updates = data.model_dump(exclude_unset=True)
    note = note_service.update(db, note_id, **updates)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

@router.delete("/{note_id}")                              # Delete
def delete_note(note_id: int, db: Session = Depends(get_db)):
    if not note_service.delete(db, note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return {"ok": True}
```

Notice the pattern: every endpoint that takes an ID checks whether the resource exists and returns 404 if not. This is consistent across all entity routers in the project.

The `response_model` parameter tells FastAPI what shape the response JSON should have. FastAPI uses this to both validate the response and generate API documentation automatically.

The Pydantic schemas in `src/wellbegun/schemas/note.py` define three distinct shapes:

```python
# From src/wellbegun/schemas/note.py
class NoteCreate(BaseModel):       # What the client sends to create
    title: str
    content: str | None = None

class NoteUpdate(BaseModel):       # What the client sends to update
    title: str | None = None
    content: str | None = None

class NoteOut(BaseModel):          # What the server returns
    id: int
    title: str
    content: str | None = None
    is_active: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

`NoteCreate` requires a `title` -- you must provide one when creating. `NoteUpdate` makes everything optional -- you only send the fields you want to change. `NoteOut` includes server-managed fields like `id`, `created_at`, and `is_active` that the client never sets directly.

---

## Guided Examples

### Example 1: How NoteCreate Validates Input

When the frontend sends `POST /api/notes` with this body:

```json
{"title": "My new note"}
```

FastAPI automatically deserializes the JSON into a `NoteCreate` object. If the `title` field were missing, FastAPI would return a **422 Unprocessable Entity** response with details about what went wrong -- before your code even runs.

```python
# The router function receives a validated NoteCreate object:
@router.post("/", response_model=NoteOut, status_code=201)
def create_note(data: NoteCreate, db: Session = Depends(get_db)):
    return note_service.create(db, title=data.title, content=data.content)
```

The `data` parameter is already a validated Python object. You access `data.title` and `data.content` knowing they conform to the schema.

### Example 2: How NoteOut Shapes Output

The service returns a SQLAlchemy `Note` ORM object, but the client receives JSON. The `response_model=NoteOut` tells FastAPI to serialize the response using the `NoteOut` schema. The `model_config = {"from_attributes": True}` allows Pydantic to read attributes directly from the ORM object (e.g., `note.id`, `note.title`).

This means:
- Fields on the ORM model that are not in `NoteOut` are excluded from the response
- The response shape is guaranteed to match `NoteOut`, regardless of what the ORM model looks like internally

### Example 3: Partial Updates with exclude_unset

```python
@router.put("/{note_id}", response_model=NoteOut)
def update_note(note_id: int, data: NoteUpdate, db: Session = Depends(get_db)):
    updates = data.model_dump(exclude_unset=True)
    note = note_service.update(db, note_id, **updates)
```

If the frontend sends `{"title": "Updated title"}` (without `content`), `model_dump(exclude_unset=True)` produces `{"title": "Updated title"}` -- not `{"title": "Updated title", "content": None}`. This prevents accidentally overwriting `content` with NULL when the client only intended to change the title.

---

## Exercises

### Exercise 1: Design Endpoints for a New Entity

**Task**: Imagine WellBegun adds a new entity type called "Bookmark" with fields: `url` (required string), `label` (optional string), and `is_favorite` (boolean, defaults to false). Design the five standard REST endpoints: list all, get one, create, update, delete. For each, specify: the HTTP method, the URL path, the expected status code on success, and what the request/response body contains.

<details>
<summary>Hint</summary>
Follow the same pattern as notes: GET /api/bookmarks (list, 200), GET /api/bookmarks/{id} (single, 200 or 404), POST /api/bookmarks (create, 201, body has url + optional label), PUT /api/bookmarks/{id} (update, 200 or 404, body has optional fields), DELETE /api/bookmarks/{id} (delete, 200 or 404).
</details>

### Exercise 2: Identify Status Codes

**Task**: For each scenario below, identify the correct HTTP status code:
1. Client sends GET /api/notes/999 and note 999 does not exist
2. Client sends POST /api/notes with `{"title": "Hello"}` and it succeeds
3. Client sends POST /api/notes with `{}` (missing required title field)
4. Client sends PUT /api/notes/5 with `{"title": "Updated"}` and it succeeds
5. Client sends DELETE /api/notes/5 and it succeeds

<details>
<summary>Hint</summary>
1) 404 Not Found, 2) 201 Created, 3) 422 Unprocessable Entity (FastAPI's automatic validation), 4) 200 OK, 5) 200 OK. Look at the status_code parameters and HTTPException raises in src/wellbegun/routers/notes.py.
</details>

---

## Knowledge Check

**Q1**: Why do REST APIs use nouns in URLs (e.g., `/api/notes`) instead of verbs (e.g., `/api/getNotes`)?
- A) Verbs are not allowed in URLs
- B) The HTTP method (GET, POST, etc.) already provides the verb, so the URL identifies the resource
- C) Nouns are shorter to type
- D) Browsers only support noun-based URLs

<details>
<summary>Answer</summary>
**B) The HTTP method already provides the verb, so the URL identifies the resource** -- Combining `GET` + `/api/notes` means "retrieve notes." Putting the verb in the URL would be redundant and inconsistent (e.g., would DELETE use `/api/deleteNotes` or `/api/removeNotes`?).
</details>

**Q2**: What is the purpose of separate NoteCreate and NoteOut schemas?
- A) NoteCreate is for the database, NoteOut is for Python
- B) NoteCreate defines what the client sends; NoteOut defines what the server returns, including server-managed fields like id and timestamps
- C) NoteCreate is for POST requests, NoteOut is for GET requests only
- D) They are interchangeable

<details>
<summary>Answer</summary>
**B) NoteCreate defines what the client sends; NoteOut defines what the server returns** -- The client should not set fields like `id`, `created_at`, or `is_active` -- those are managed by the server. Separate schemas enforce this boundary clearly.
</details>

**Q3**: What does `model_dump(exclude_unset=True)` do in the update endpoint?
- A) Removes all None values from the dictionary
- B) Only includes fields that the client explicitly provided, preventing accidental overwrites of unmentioned fields
- C) Converts the model to a database query
- D) Excludes the id field from the update

<details>
<summary>Answer</summary>
**B) Only includes fields that the client explicitly provided** -- If the client sends `{"title": "New"}` without mentioning `content`, `exclude_unset=True` ensures `content` is not included in the update dictionary. Without this, `content` would be set to `None`, accidentally erasing it.
</details>

**Q4**: Why does the POST /api/notes endpoint return status code 201 instead of 200?
- A) 201 is faster than 200
- B) 200 means the request succeeded; 201 specifically means a new resource was created -- it gives the client more precise information
- C) FastAPI requires 201 for POST
- D) 200 is only for GET requests

<details>
<summary>Answer</summary>
**B) 200 means the request succeeded; 201 specifically means a new resource was created** -- Using precise status codes makes the API more informative. A client can distinguish between "I updated something" (200) and "I created something new" (201) without inspecting the response body.
</details>

**Q5**: What happens if a client sends `POST /api/notes` with an empty body `{}`?
- A) A note is created with empty title
- B) The server crashes
- C) FastAPI returns 422 Unprocessable Entity because the required `title` field is missing
- D) The server returns 404

<details>
<summary>Answer</summary>
**C) FastAPI returns 422 Unprocessable Entity** -- The `NoteCreate` schema requires `title: str`. FastAPI validates the request body against this schema before your code runs. Missing required fields trigger an automatic 422 response with error details.
</details>

---

## Further Reading
- [RESTful API Design Best Practices](https://restfulapi.net/resource-naming/) -- tutorial
- [FastAPI Request Body Documentation](https://fastapi.tiangolo.com/tutorial/body/) -- official-docs
- [Pydantic Model Documentation](https://docs.pydantic.dev/latest/concepts/models/) -- official-docs
- [HTTP Status Codes Reference](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status) -- official-docs
- [Microsoft REST API Guidelines](https://github.com/microsoft/api-guidelines) -- reference

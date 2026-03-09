# Client-Server Architecture

> **Category**: concept | **Difficulty**: beginner | **Time**: ~20 min
> **Prerequisites**: None

## Overview
Client-server architecture is the fundamental design pattern behind WellBegun. The "client" is the Svelte frontend running in your browser -- it displays the UI, captures your input, and renders data. The "server" is the FastAPI backend running as a Python process -- it stores data, enforces business rules, and responds to requests from the client.

As a data scientist, you already use this pattern: when you call `requests.get("https://api.example.com/data")`, your script is the client and the remote service is the server. WellBegun works the same way, except both sides live on your machine and you built both of them.

**Key takeaways:**
- Client-server separates presentation (what users see) from logic and storage (what the system does)
- The frontend (client) and backend (server) communicate over HTTP using JSON
- Each side can be developed, tested, and changed independently
- The server is the single source of truth for data; the client is a view of that data

---

## Core Concepts

### Request/Response Cycle

Every interaction in WellBegun follows the same cycle:

1. **User action** -- you click "Save" on a note in the browser
2. **Client sends request** -- the frontend sends an HTTP request (e.g., `POST /api/notes/`) with JSON data
3. **Server processes** -- FastAPI receives the request, validates the data, writes to the database
4. **Server sends response** -- FastAPI returns JSON (the saved note with its new `id`) and an HTTP status code
5. **Client updates UI** -- the frontend reads the JSON response and updates the page

This cycle happens for every data operation -- creating, reading, updating, and deleting entities.

### HTTP as the Transport Protocol

The client and server speak HTTP. This is the same protocol your browser uses to load any website. In WellBegun:

- The frontend runs on `http://localhost:5173` (Vite dev server)
- The backend runs on `http://localhost:8000` (Uvicorn/FastAPI)
- The frontend's `fetch()` calls cross from port 5173 to port 8000
- CORS middleware on the backend permits these cross-origin requests

```python
# From src/wellbegun/main.py:436-442
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Separation of Concerns

The frontend and backend have distinct responsibilities:

| **Frontend (Client)** | **Backend (Server)** |
|------------------------|----------------------|
| Renders HTML/CSS | Stores data in SQLite |
| Captures user input | Validates incoming data |
| Sends HTTP requests | Processes business logic |
| Manages UI state (Svelte stores) | Manages data persistence (SQLAlchemy) |
| Written in TypeScript/Svelte | Written in Python/FastAPI |

This separation means you could replace the Svelte frontend with a CLI tool, a mobile app, or a Jupyter notebook -- as long as it speaks HTTP and JSON, the backend does not care.

### Stateless Communication

Each HTTP request from the client is self-contained. The server does not remember previous requests. There is no "session" linking one request to the next. If the frontend needs a note, it sends `GET /api/notes/5` -- the server looks it up fresh from the database every time.

In WellBegun, this is visible in how every endpoint receives a fresh database session:

```python
# From src/wellbegun/routers/notes.py:11-13
@router.get("/", response_model=list[NoteOut])
def list_notes(db: Session = Depends(get_db)):
    return note_service.get_all(db)
```

The `Depends(get_db)` creates a new database session for each request and closes it when done:

```python
# From src/wellbegun/database.py:16-21
def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## In This Project

WellBegun is split into two directory trees that mirror the client-server split:

```
WellBegun/
  frontend/           <-- CLIENT (Svelte + TypeScript)
    src/lib/api/      <-- HTTP calls to the server
    src/lib/stores/   <-- UI state management
    src/lib/components/ <-- Visual components
  src/wellbegun/      <-- SERVER (Python + FastAPI)
    routers/          <-- HTTP endpoint definitions
    services/         <-- Business logic
    models/           <-- Database table definitions
    schemas/          <-- Request/response data shapes
    main.py           <-- Wires everything together
```

The frontend API layer (`frontend/src/lib/api/notes.ts`) is the bridge between client and server:

```typescript
// From frontend/src/lib/api/notes.ts:1-8
import type { Note } from '$lib/types';

const BASE = '/api/notes';

export async function getNotes(): Promise<Note[]> {
    const res = await fetch(`${BASE}/`);
    return res.json();
}
```

This function sends `GET /api/notes/` to the backend. The backend router handles it:

```python
# From src/wellbegun/routers/notes.py:8-13
router = APIRouter(prefix="/notes", tags=["notes"])

@router.get("/", response_model=list[NoteOut])
def list_notes(db: Session = Depends(get_db)):
    return note_service.get_all(db)
```

The router prefix `/notes` combined with the app prefix `/api` (set in `main.py`) forms the full URL `/api/notes/`.

```python
# From src/wellbegun/main.py:448
app.include_router(notes.router, prefix="/api")
```

---

## Guided Examples

### Example 1: Creating a Note -- Full Round Trip

Let us trace what happens when you create a note in WellBegun, from button click to database row and back.

**Step 1: Frontend sends the request**

```typescript
// From frontend/src/lib/api/notes.ts:15-22
export async function createNote(data: { title: string; content?: string }): Promise<Note> {
    const res = await fetch(`${BASE}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    return res.json();
}
```

The frontend serializes `{ title: "My Note", content: "Some text" }` into JSON, sets the `Content-Type` header, and sends a `POST` request to `/api/notes/`.

**Step 2: Backend receives and validates**

```python
# From src/wellbegun/routers/notes.py:24-26
@router.post("/", response_model=NoteOut, status_code=201)
def create_note(data: NoteCreate, db: Session = Depends(get_db)):
    return note_service.create(db, title=data.title, content=data.content)
```

FastAPI automatically parses the JSON body into a `NoteCreate` Pydantic schema:

```python
# From src/wellbegun/schemas/note.py:6-8
class NoteCreate(BaseModel):
    title: str
    content: str | None = None
```

If the JSON is missing `title` or has the wrong type, FastAPI returns a `422 Unprocessable Entity` error automatically -- the endpoint code never runs.

**Step 3: Service layer writes to the database**

```python
# From src/wellbegun/services/note_service.py:16-27
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

The service creates a `Note` SQLAlchemy object, adds it to the database session, commits, and returns the object with its new auto-generated `id`.

**Step 4: Backend sends the response**

FastAPI serializes the returned `Note` object into JSON using the `NoteOut` schema:

```python
# From src/wellbegun/schemas/note.py:16-25
class NoteOut(BaseModel):
    id: int
    title: str
    content: str | None = None
    is_active: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

The response body looks like:
```json
{
  "id": 42,
  "title": "My Note",
  "content": "Some text",
  "is_active": false,
  "is_archived": false,
  "created_at": "2026-03-05T10:30:00",
  "updated_at": "2026-03-05T10:30:00"
}
```

**Step 5: Frontend receives and updates UI**

Back in the frontend, `res.json()` parses this JSON into a TypeScript `Note` object. The UI component then updates the Svelte store:

```typescript
// From frontend/src/lib/stores/notes.ts:1-13
import { writable } from 'svelte/store';
import type { Note } from '$lib/types';
import { getNotes } from '$lib/api/notes';

export const notes = writable<Note[]>([]);

export async function loadNotes() {
    try {
        notes.set(await getNotes());
    } catch (e) {
        console.warn('Failed to load notes:', e);
    }
}
```

### Example 2: What the Server Does NOT Know

Notice that the server has no idea what the UI looks like. It does not know whether the note list is displayed as cards, a table, or a tree. It does not know if the user typed the title or pasted it. All it receives is:

```
POST /api/notes/ HTTP/1.1
Content-Type: application/json

{"title": "My Note", "content": "Some text"}
```

This is the power of client-server separation: you could write a Python script that creates the same note:

```python
import requests
requests.post("http://localhost:8000/api/notes/", json={"title": "My Note", "content": "Some text"})
```

The backend would handle it identically.

---

## Exercises

### Exercise 1: Trace a GET Request End-to-End

**Task**: Starting from `frontend/src/lib/api/notes.ts`, trace a `GET /api/notes/5` request through every layer until the database query, and then back to the frontend. List each file and function involved.

<details>
<summary>Hint 1</summary>
Start with <code>getNote(id)</code> in <code>frontend/src/lib/api/notes.ts</code> (line 10-13).
</details>

<details>
<summary>Hint 2</summary>
Follow the route to <code>get_note()</code> in <code>src/wellbegun/routers/notes.py</code> (line 16-21), then to <code>get_by_id()</code> in <code>src/wellbegun/services/note_service.py</code> (line 12-13).
</details>

<details>
<summary>Answer</summary>

1. `frontend/src/lib/api/notes.ts` -- `getNote(5)` calls `fetch("/api/notes/5")`
2. `src/wellbegun/routers/notes.py` -- `get_note(note_id=5)` receives the request
3. `src/wellbegun/database.py` -- `get_db()` provides a fresh database session
4. `src/wellbegun/services/note_service.py` -- `get_by_id(db, 5)` runs `db.query(Note).filter(Note.id == 5).first()`
5. `src/wellbegun/models/note.py` -- the `Note` SQLAlchemy class maps to the `notes` table
6. The database returns the row; SQLAlchemy hydrates it into a `Note` object
7. `src/wellbegun/schemas/note.py` -- `NoteOut` serializes the object to JSON
8. The HTTP response (status 200, JSON body) travels back to the frontend
9. `frontend/src/lib/api/notes.ts` -- `res.json()` parses the JSON into a TypeScript `Note`
</details>

### Exercise 2: Identify the Client and Server in Another Context

**Task**: Think of a tool you use daily (e.g., Jupyter notebooks, `pip install`, GitHub). Identify which part is the "client" and which is the "server." What protocol do they use to communicate?

<details>
<summary>Answer (Jupyter example)</summary>

- **Client**: Your web browser displaying the notebook UI
- **Server**: The Jupyter kernel process running Python code
- **Protocol**: HTTP (WebSocket for real-time cell execution updates)

This is the same pattern as WellBegun: browser = client, Python process = server, HTTP = transport.
</details>

### Exercise 3: What Would Break?

**Task**: If you changed the backend router prefix from `"/notes"` to `"/my-notes"` in `src/wellbegun/routers/notes.py`, what would happen when the frontend tries to create a note? What would you need to change on the frontend side?

<details>
<summary>Answer</summary>

The frontend would get a 404 error because it still calls <code>fetch("/api/notes/")</code>, but the server now expects <code>/api/my-notes/</code>. You would need to update the <code>BASE</code> constant in <code>frontend/src/lib/api/notes.ts</code> from <code>'/api/notes'</code> to <code>'/api/my-notes'</code>. This illustrates that the URL is a contract between client and server -- both sides must agree on it.
</details>

---

## Knowledge Check

**Q1**: In WellBegun, which part is the "client" and which is the "server"?
- A) The Svelte frontend is the server; the FastAPI backend is the client
- B) The Svelte frontend is the client; the FastAPI backend is the server
- C) Both are servers that talk to each other
- D) The SQLite database is the server; everything else is the client

<details>
<summary>Answer</summary>
<strong>B) The Svelte frontend is the client; the FastAPI backend is the server.</strong> The frontend initiates requests; the backend listens, processes, and responds.
</details>

**Q2**: Why does each backend endpoint receive a fresh database session via `Depends(get_db)` instead of sharing one global session?
- A) Python does not support global variables
- B) It enforces statelessness -- each request is independent and self-contained
- C) SQLite can only handle one session at a time
- D) It is required by the FastAPI framework with no alternative

<details>
<summary>Answer</summary>
<strong>B) It enforces statelessness -- each request is independent and self-contained.</strong> A fresh session per request means no leftover state from a previous request can leak into the next one. This is visible in <code>src/wellbegun/database.py:16-21</code> where the session is created, yielded, and then closed.
</details>

**Q3**: What allows the frontend (port 5173) to make HTTP requests to the backend (port 8000)?
- A) They share the same port in production
- B) CORS middleware configured on the backend
- C) The frontend proxies all requests through Node.js
- D) HTTP requests do not have port restrictions

<details>
<summary>Answer</summary>
<strong>B) CORS middleware configured on the backend.</strong> Cross-Origin Resource Sharing (CORS) is configured in <code>src/wellbegun/main.py:436-442</code>. Without it, the browser would block requests from one origin (port 5173) to another (port 8000) as a security measure.
</details>

**Q4**: If you wanted to create a note without using the Svelte frontend, which of these would work?
- A) Insert directly into the SQLite file -- the frontend will pick it up
- B) Send a POST request to `http://localhost:8000/api/notes/` with JSON from any HTTP client
- C) Call `note_service.create()` from a Python script importing the module
- D) Both B and C would work

<details>
<summary>Answer</summary>
<strong>D) Both B and C would work.</strong> Option B uses the server's HTTP interface (just like the frontend does). Option C bypasses the HTTP layer entirely and uses the service functions directly. Both are valid because client-server architecture separates the interface from the implementation.
</details>

**Q5**: What is the main advantage of separating the frontend and backend into distinct applications?
- A) It makes the code run faster
- B) Each side can be developed, tested, deployed, and replaced independently
- C) It uses less memory than a single application
- D) It is required by Python and JavaScript to be in separate processes

<details>
<summary>Answer</summary>
<strong>B) Each side can be developed, tested, deployed, and replaced independently.</strong> You could swap the Svelte frontend for a React one, or replace SQLite with PostgreSQL, without rewriting the other side -- as long as the HTTP/JSON contract between them is maintained.
</details>

---

## Further Reading
- [MDN: Client-Server Overview](https://developer.mozilla.org/en-US/docs/Learn/Server-side/First_steps/Client-Server_overview) -- official-docs
- [FastAPI Tutorial: First Steps](https://fastapi.tiangolo.com/tutorial/first-steps/) -- tutorial
- [MDN: Using Fetch](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch) -- official-docs
- [Wikipedia: Client-Server Model](https://en.wikipedia.org/wiki/Client%E2%80%93server_model) -- reference

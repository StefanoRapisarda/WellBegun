# REST APIs & HTTP Fundamentals

> **Category**: concept | **Difficulty**: beginner | **Time**: ~20 min
> **Prerequisites**: None

## Overview
REST (Representational State Transfer) is the architectural style your WellBegun app uses for the frontend (Svelte) to communicate with the backend (FastAPI). Think of it as a standardized contract: the frontend sends HTTP requests to specific URLs, and the backend responds with JSON data.

If you've used Python's `requests` library to call APIs, you've already used REST — you just may not have built the server side before.

**Key takeaways:**
- REST APIs use standard HTTP methods (GET, POST, PUT, DELETE) to perform CRUD operations
- URLs identify resources (like `/api/collections/5`), not actions
- The server is stateless — each request contains all the info needed to process it
- JSON is the lingua franca for data exchange between frontend and backend

---

## Core Concepts

### HTTP Methods Map to CRUD Operations

In Python, you might write functions like `get_collection()`, `create_collection()`, `delete_collection()`. REST maps these to HTTP methods:

| HTTP Method | CRUD Operation | Example |
|------------|----------------|---------|
| GET | Read | Fetch all collections |
| POST | Create | Create a new collection |
| PUT | Update | Modify collection title |
| DELETE | Delete | Remove a collection |

In WellBegun, you can see this pattern in `src/wellbegun/routers/collections.py`:

```python
# From src/wellbegun/routers/collections.py:18-20
@router.get("/", response_model=list[CollectionOut])
def list_collections(category_id: int | None = None, db: Session = Depends(get_db)):
    return collection_service.get_all(db, category_id=category_id)
```

And the matching frontend call in `frontend/src/lib/api/collections.ts`:

```typescript
// From frontend/src/lib/api/collections.ts:5-9
export async function getCollections(categoryId?: number): Promise<Collection[]> {
    const url = categoryId != null ? `${BASE}/?category_id=${categoryId}` : `${BASE}/`;
    const res = await fetch(url);
    return res.json();
}
```

### URLs as Resource Identifiers

REST URLs describe *what* you're working with, not *what you're doing*. Instead of `/api/deleteCollection?id=5`, REST uses `DELETE /api/collections/5`.

WellBegun's URL structure follows this convention:
- `/api/collections/` — the collection list (GET = list all, POST = create)
- `/api/collections/5` — a specific collection (GET = fetch, PUT = update, DELETE = remove)
- `/api/collections/5/items` — items within collection 5 (POST = add item)
- `/api/collections/5/activate` — lifecycle action on collection 5

### Request and Response Bodies

When creating or updating resources, data travels as JSON in the request body. When reading, the server returns JSON in the response body.

```typescript
// From frontend/src/lib/api/collections.ts:16-23
export async function createCollection(data: { title: string; category_id: number; description?: string }): Promise<Collection> {
    const res = await fetch(`${BASE}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    return res.json();
}
```

The `Content-Type: application/json` header tells the server "this request body is JSON". The server responds with JSON containing the created resource (including its new `id`).

### HTTP Status Codes

Status codes tell the client what happened:
- **200** OK — Success (used for GET, PUT)
- **201** Created — Resource created (used for POST)
- **404** Not Found — Resource doesn't exist
- **422** Unprocessable Entity — Validation error

```python
# From src/wellbegun/routers/collections.py:31-38
@router.post("/", response_model=CollectionOut, status_code=201)
def create_collection(data: CollectionCreate, db: Session = Depends(get_db)):
    return collection_service.create(
        db,
        title=data.title,
        category_id=data.category_id,
        description=data.description,
    )
```

Notice `status_code=201` — FastAPI returns 201 for successful creation instead of the default 200.

### Statelessness

Each HTTP request is self-contained. The server doesn't remember previous requests. In WellBegun, every request includes all the context it needs — the collection ID is in the URL, the data is in the body, and the database session is freshly created via `Depends(get_db)`.

---

## In This Project

WellBegun's REST API lives in `src/wellbegun/routers/` with one file per resource type. The main app at `src/wellbegun/main.py` wires them together:

```python
# From src/wellbegun/main.py:444-465
app.include_router(health.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(notes.router, prefix="/api")
app.include_router(sources.router, prefix="/api")
app.include_router(actors.router, prefix="/api")
app.include_router(activities.router, prefix="/api")

app.include_router(plans.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(active_context.router, prefix="/api")
app.include_router(assistant.router, prefix="/api")
app.include_router(scaffolding.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")
app.include_router(web_proxy.router, prefix="/api")
app.include_router(journal.router, prefix="/api")
app.include_router(coffee.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(collections.router, prefix="/api")
app.include_router(documents.router)
app.include_router(workspaces.router, prefix="/api")
```

Each router handles a resource type. The `prefix="/api"` means all routes start with `/api/`. Combined with the router's own prefix (`prefix="/collections"`), the full URL becomes `/api/collections/`.

The frontend mirrors this structure in `frontend/src/lib/api/`, where each file contains functions that call the corresponding backend endpoints.

---

## Guided Examples

### Example 1: Full CRUD Lifecycle

Here's the complete lifecycle of a collection in WellBegun, showing the REST pattern end-to-end:

```python
# Backend: src/wellbegun/routers/collections.py

# CREATE — POST /api/collections/
@router.post("/", response_model=CollectionOut, status_code=201)  # line 31
def create_collection(data: CollectionCreate, db: Session = Depends(get_db)):
    return collection_service.create(db, title=data.title, ...)

# READ — GET /api/collections/{id}
@router.get("/{collection_id}", response_model=CollectionOut)     # line 23
def get_collection(collection_id: int, db: Session = Depends(get_db)):
    collection = collection_service.get_by_id(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection

# UPDATE — PUT /api/collections/{id}
@router.put("/{collection_id}", response_model=CollectionOut)     # line 41
def update_collection(collection_id: int, data: CollectionUpdate, ...):
    ...

# DELETE — DELETE /api/collections/{id}
@router.delete("/{collection_id}")                                 # line 52
def delete_collection(collection_id: int, db: Session = Depends(get_db)):
    if not collection_service.delete(db, collection_id):
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"ok": True}
```

### Example 2: Error Handling with Status Codes

```python
# From src/wellbegun/routers/collections.py:95-111
@router.post("/{collection_id}/items", response_model=CollectionItemOut, status_code=201)
def add_item(
    collection_id: int, data: CollectionItemCreate, db: Session = Depends(get_db)
):
    try:
        return collection_service.add_item(
            db,
            collection_id=collection_id,
            member_entity_type=data.member_entity_type,
            member_entity_id=data.member_entity_id,
            position=data.position,
            status=data.status,
            notes=data.notes,
            header=data.header,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
```

The service layer raises `ValueError` for business logic errors (e.g., invalid status). The router catches it and converts it to a 422 HTTP response. The frontend handles this:

```typescript
// From frontend/src/lib/api/collections.ts:58-69
export async function addItem(collectionId: number, data: { member_entity_type: string; member_entity_id: number; position?: number; status?: string; notes?: string; header?: string }): Promise<CollectionItem> {
    const res = await fetch(`${BASE}/${collectionId}/items`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to add item (${res.status})`);
    }
    return res.json();
}
```

---

## Exercises

### Exercise 1: Trace a Request

**Task**: Open `frontend/src/lib/api/collections.ts` and `src/wellbegun/routers/collections.py` side by side. For the `deleteCollection` function, trace the full request path: What URL does the frontend call? What HTTP method? What does the backend return?

<details>
<summary>Hint</summary>
Look at lines 34-36 in the frontend file and lines 52-56 in the router file. The frontend uses `fetch` with `method: 'DELETE'`, and the backend returns `{"ok": True}`.
</details>

### Exercise 2: Spot the Pattern

**Task**: Look at the lifecycle endpoints in `src/wellbegun/routers/collections.py` (lines 61-90). These use `POST` instead of `PUT`. Why might `POST /collections/5/activate` be used instead of `PUT /collections/5` with `{is_active: true}` in the body?

<details>
<summary>Hint</summary>
Actions like "activate" and "archive" are state transitions with side effects (e.g., archiving also deactivates). Using a dedicated POST endpoint makes the intent explicit and lets the server handle the logic, rather than requiring the client to know which fields to update together.
</details>

---

## Knowledge Check

**Q1**: Which HTTP method should you use to create a new resource?
- A) GET
- B) POST
- C) PUT
- D) DELETE

<details>
<summary>Answer</summary>
**B) POST** — POST is used to create new resources. In WellBegun, `POST /api/collections/` creates a new collection.
</details>

**Q2**: What does a 404 status code mean?
- A) The request was successful
- B) The request body had invalid data
- C) The requested resource was not found
- D) The server encountered an internal error

<details>
<summary>Answer</summary>
**C) The requested resource was not found** — In WellBegun, the routers raise `HTTPException(status_code=404)` when a collection or item doesn't exist in the database.
</details>

**Q3**: Why does `DELETE /api/collections/5` include the ID in the URL rather than in the request body?
- A) DELETE requests can't have a body
- B) REST convention: the URL identifies the resource being acted upon
- C) It's faster for the server to parse
- D) The frontend doesn't support request bodies

<details>
<summary>Answer</summary>
**B) REST convention: the URL identifies the resource being acted upon** — In REST, the URL path identifies the resource. The HTTP method says what to do with it. This makes the API self-documenting: `DELETE /api/collections/5` clearly means "delete collection 5".
</details>

**Q4**: In WellBegun, what header must be included when sending JSON data in a request body?
- A) Accept: text/html
- B) Authorization: Bearer token
- C) Content-Type: application/json
- D) X-Request-ID: uuid

<details>
<summary>Answer</summary>
**C) Content-Type: application/json** — This header tells the server the request body is JSON. You can see it in `frontend/src/lib/api/collections.ts:19` where POST and PUT requests include `headers: { 'Content-Type': 'application/json' }`.
</details>

---

## Further Reading
- [MDN HTTP Overview](https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview) — official-docs
- [REST API Tutorial](https://restfulapi.net/) — tutorial
- [FastAPI Tutorial: First Steps](https://fastapi.tiangolo.com/tutorial/first-steps/) — tutorial
- [HTTP Status Codes Reference](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status) — official-docs

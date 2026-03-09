# FastAPI for Python Developers

> **Category**: framework | **Difficulty**: beginner | **Time**: ~25 min
> **Prerequisites**: REST APIs & HTTP Fundamentals

## Overview

FastAPI is a modern Python web framework that lets you build REST APIs using the same Python type hints you already use every day. If you have written a Python function with type hints, you already know 80% of what FastAPI needs. Where Flask requires you to manually parse request bodies and validate parameters, FastAPI reads your function signatures and does that work for you -- turning Python type annotations into automatic request validation, serialization, and interactive API documentation.

WellBegun's entire backend is a FastAPI application. Every button click in the UI ultimately calls a FastAPI endpoint, which validates the request, delegates to a service function, and returns a typed response.

**Key takeaways:**

- FastAPI uses Python type hints to auto-validate requests and generate docs
- Routers group related endpoints (like Python modules group related functions)
- Dependency injection (`Depends`) replaces global state -- similar to how pytest fixtures inject test dependencies
- Async support is built in for I/O-bound operations like calling an LLM

---

## Core Concepts

### 1. Decorators Define Routes

In Python, decorators add behavior to functions without changing their code. You have likely used `@pytest.mark.parametrize` to run a test with multiple inputs, or `@property` to make a method behave like an attribute. FastAPI uses the same pattern: a decorator like `@router.get("/")` takes a normal Python function and registers it as an HTTP endpoint.

Here is how WellBegun lists all collections:

```python
# src/wellbegun/routers/collections.py, lines 18-20

@router.get("/", response_model=list[CollectionOut])
def list_collections(category_id: int | None = None, db: Session = Depends(get_db)):
    return collection_service.get_all(db, category_id=category_id)
```

The decorator `@router.get("/")` says: "When a GET request arrives at this router's base path, call this function." The `response_model=list[CollectionOut]` tells FastAPI to validate and serialize the return value as a list of `CollectionOut` Pydantic models before sending it back as JSON.

The function body is just normal Python -- call a service, return the result. FastAPI handles the HTTP plumbing.

### 2. Path and Query Parameters

FastAPI reads your function signature to decide where each parameter comes from. There are two main sources:

**Query parameters** appear in the URL after a `?` (e.g., `/collections?category_id=3`). Any parameter with a default value becomes a query parameter automatically:

```python
# src/wellbegun/routers/collections.py, lines 18-20

@router.get("/", response_model=list[CollectionOut])
def list_collections(category_id: int | None = None, db: Session = Depends(get_db)):
    return collection_service.get_all(db, category_id=category_id)
```

Here `category_id: int | None = None` is optional. If the client sends `GET /collections?category_id=3`, FastAPI parses `"3"` into the integer `3`. If the client sends `GET /collections` with no query param, `category_id` is `None`. If the client sends `?category_id=abc`, FastAPI returns a 422 validation error automatically -- you never write that validation code.

**Path parameters** are part of the URL itself (e.g., `/collections/7`). Any parameter whose name matches a `{placeholder}` in the route path is extracted from the URL:

```python
# src/wellbegun/routers/collections.py, lines 23-28

@router.get("/{collection_id}", response_model=CollectionOut)
def get_collection(collection_id: int, db: Session = Depends(get_db)):
    collection = collection_service.get_by_id(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection
```

The `{collection_id}` in the route path matches the `collection_id: int` parameter. A request to `GET /collections/7` passes `7` as an integer. Notice that the type hint `int` is doing double duty: it tells Python what type to expect *and* tells FastAPI to validate and convert the URL segment.

### 3. Request/Response Models (Pydantic)

For POST and PUT requests, the client sends a JSON body. FastAPI uses Pydantic models to parse and validate that body. If you have used dataclasses, Pydantic models will feel familiar -- they are classes with typed fields, but they also validate data at runtime.

```python
# src/wellbegun/routers/collections.py, lines 31-38

@router.post("/", response_model=CollectionOut, status_code=201)
def create_collection(data: CollectionCreate, db: Session = Depends(get_db)):
    return collection_service.create(
        db,
        title=data.title,
        category_id=data.category_id,
        description=data.description,
    )
```

The parameter `data: CollectionCreate` tells FastAPI to read the request body as JSON and validate it against the `CollectionCreate` schema. Here is what that schema looks like:

```python
# src/wellbegun/schemas/collection.py, lines 37-40

class CollectionCreate(BaseModel):
    title: str
    category_id: int
    description: str | None = None
```

If a client sends `{"title": "My List", "category_id": 5}`, FastAPI creates a `CollectionCreate` instance with those values and `description=None`. If the client omits `title`, FastAPI returns a 422 error before your function ever runs. No manual `if "title" not in request.json` checks needed.

The `response_model=CollectionOut` works the other direction: FastAPI takes whatever your function returns, validates it against `CollectionOut`, strips any extra fields, and serializes it to JSON. The `status_code=201` overrides the default 200 to indicate "resource created."

For updates, WellBegun uses `model_dump(exclude_unset=True)` to convert only the fields the client actually sent into a dictionary of keyword arguments:

```python
# src/wellbegun/routers/collections.py, lines 41-49

@router.put("/{collection_id}", response_model=CollectionOut)
def update_collection(
    collection_id: int, data: CollectionUpdate, db: Session = Depends(get_db)
):
    updates = data.model_dump(exclude_unset=True)
    collection = collection_service.update(db, collection_id, **updates)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection
```

The `exclude_unset=True` means if the client sends `{"title": "New Name"}` without a `description` field, only `title` is included in the `updates` dict. This prevents accidentally overwriting `description` with `None`.

### 4. Dependency Injection

In data science, you might have functions that need a database connection, a configuration object, or an authenticated user. Often these are passed as global variables or module-level singletons. FastAPI offers a cleaner pattern called dependency injection.

If you have used pytest fixtures, the concept is identical. In pytest, you write:

```python
@pytest.fixture
def db_session():
    session = create_session()
    yield session
    session.close()

def test_something(db_session):  # pytest injects it
    db_session.query(...)
```

FastAPI's `Depends` works the same way:

```python
# src/wellbegun/database.py, lines 16-21

def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

```python
# Used in every endpoint:
def list_collections(category_id: int | None = None, db: Session = Depends(get_db)):
```

When FastAPI sees `db: Session = Depends(get_db)`, it calls `get_db()` before the endpoint runs, provides the yielded `Session` object as `db`, and after the endpoint finishes (or raises an exception), it runs the `finally` block to close the session. You never manually open or close database connections in your endpoint code.

This pattern is used consistently throughout WellBegun. Every endpoint that needs a database session declares `db: Session = Depends(get_db)`.

### 5. Error Handling with HTTPException

When something goes wrong, FastAPI uses exceptions to communicate HTTP errors. The `HTTPException` class lets you return standard HTTP status codes with a detail message:

```python
# src/wellbegun/routers/collections.py, lines 23-28

@router.get("/{collection_id}", response_model=CollectionOut)
def get_collection(collection_id: int, db: Session = Depends(get_db)):
    collection = collection_service.get_by_id(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection
```

Raising `HTTPException(status_code=404)` stops the function and sends a `{"detail": "Collection not found"}` JSON response with HTTP status 404. No try/except needed at the caller level -- FastAPI catches it and formats the response.

For validation errors from the service layer, WellBegun catches Python exceptions and translates them to HTTP errors:

```python
# src/wellbegun/routers/collections.py, lines 95-111

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

The service layer raises a plain `ValueError` (e.g., "Invalid status 'xyz'"). The router catches it and translates it to an HTTP 422 (Unprocessable Entity). This keeps the service layer free of HTTP concerns -- it just raises Python exceptions, and the router decides which HTTP status code to use.

---

## In This Project

WellBegun follows a three-layer architecture that keeps code organized and testable:

```
main.py (application setup)
  |
  +-- Registers routers via app.include_router()
  |
  +-- routers/ (HTTP layer)
  |     collections.py, plans.py, notes.py, ...
  |     - Defines endpoints with decorators
  |     - Validates input (via Pydantic models)
  |     - Translates errors to HTTP status codes
  |
  +-- services/ (business logic)
  |     collection_service.py, plan_service.py, ...
  |     - Pure Python functions
  |     - No HTTP concepts (no status codes, no request objects)
  |     - Raises ValueError for invalid operations
  |
  +-- models/ (database layer)
        Collection, Plan, Note, ...
        - SQLAlchemy ORM models
```

**Application setup** (`main.py`, line 434): The `FastAPI()` instance is created with a lifespan handler that runs database migrations and health checks at startup:

```python
# src/wellbegun/main.py, lines 411-434

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    _run_migrations(engine)
    db = SessionLocal()
    try:
        seed_wild_tags(db)
        seed_categories(db)
        _migrate_plan_collections(db)
    finally:
        db.close()
    try:
        healthy = await llm_service.check_health()
        if healthy:
            print("[WellBegun] Ollama is reachable")
        else:
            print("[WellBegun] Ollama is not reachable — Journal/Coffee Table features will be unavailable")
    except Exception:
        print("[WellBegun] Ollama health check failed")
    yield

app = FastAPI(title="WellBegun", lifespan=lifespan)
```

**CORS middleware** (`main.py`, lines 436-442) allows the Svelte frontend (running on a different port) to call the API:

```python
# src/wellbegun/main.py, lines 436-442

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Router registration** (`main.py`, lines 444-465) connects each router module to the app, adding a `/api` prefix to every route:

```python
# src/wellbegun/main.py, lines 444-465

app.include_router(health.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
# ... 18 more routers ...
app.include_router(collections.router, prefix="/api")
app.include_router(workspaces.router, prefix="/api")
```

Since the collections router already has `prefix="/collections"` and main.py adds `prefix="/api"`, the final URL becomes `/api/collections/`. Each router is an independent module that can be developed and tested separately.

---

## Guided Examples

### Example 1: A Complete Request Journey (Creating a Collection)

Let us trace what happens when the frontend sends `POST /api/collections` with `{"title": "Research Papers", "category_id": 2}`.

**Step 1 -- Routing.** FastAPI matches the URL `/api/collections` + method `POST` to the `create_collection` function in `collections.py`:

```python
# src/wellbegun/routers/collections.py, lines 31-38

@router.post("/", response_model=CollectionOut, status_code=201)
def create_collection(data: CollectionCreate, db: Session = Depends(get_db)):
    return collection_service.create(
        db,
        title=data.title,
        category_id=data.category_id,
        description=data.description,
    )
```

**Step 2 -- Dependency injection.** Before calling `create_collection`, FastAPI calls `get_db()` to open a database session and passes it as `db`.

**Step 3 -- Request validation.** FastAPI parses the JSON body and validates it against `CollectionCreate`. The `title` field is required (`str` with no default), `category_id` is a required `int`, and `description` is optional. If any field is missing or the wrong type, FastAPI returns a 422 error automatically.

**Step 4 -- Service layer.** The router calls `collection_service.create()`:

```python
# src/wellbegun/services/collection_service.py, lines 30-46

def create(
    db: Session,
    title: str,
    category_id: int,
    description: str | None = None,
) -> Collection:
    collection = Collection(
        title=title,
        category_id=category_id,
        description=description,
    )
    db.add(collection)
    db.flush()
    create_entity_tag(db, title, "collection", "collection", collection.id)
    db.commit()
    db.refresh(collection)
    return collection
```

Notice that the service function is pure Python -- no HTTP concepts, no request objects, no status codes. It receives typed arguments, interacts with the database through SQLAlchemy, and returns a `Collection` ORM object.

**Step 5 -- Response serialization.** FastAPI takes the returned `Collection` object, validates it against `CollectionOut` (which includes nested `items`), and serializes it to JSON with a 201 status code.

**Step 6 -- Cleanup.** After the response is sent, FastAPI runs the `finally` block of `get_db()`, closing the database session.

### Example 2: Async Patterns in the LLM Service

Most WellBegun endpoints are synchronous (plain `def`), which is fine for database queries. But calling an external LLM service over HTTP can take seconds, and blocking during that time would prevent the server from handling other requests. This is where `async def` comes in.

**Single-shot generation** makes one HTTP call and waits for the full response:

```python
# src/wellbegun/services/llm_service.py, lines 52-72

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

The key patterns here:
- `async def` declares the function as a coroutine, allowing `await` inside it
- `async with httpx.AsyncClient()` creates a non-blocking HTTP client
- `await client.post(...)` suspends this function while waiting for the LLM, freeing the event loop to handle other requests
- The `try/except` catches connection errors and wraps them in a domain-specific exception

**Streaming generation** uses an async iterator to yield tokens as they arrive, so the frontend can display them in real time:

```python
# src/wellbegun/services/llm_service.py, lines 75-102

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

This is an async generator (it uses `yield` inside an `async def`). The `async for line in response.aiter_lines()` reads the HTTP response line by line as the LLM produces tokens, and each token is yielded to the caller immediately. If you have used Python generators for processing large datasets lazily, this is the async equivalent.

---

## Exercises

### Exercise 1: Compare Plans and Collections Routers

Open `src/wellbegun/routers/plans.py` and compare it with `src/wellbegun/routers/collections.py`. Answer these questions:

1. Both routers define the standard CRUD endpoints (GET list, GET by ID, POST, PUT, DELETE). What extra parameter does the plans `DELETE` endpoint accept that collections does not? What does it do?
2. The plans router has a `cascade` query parameter on delete. How does this change the behavior compared to the collections delete?
3. Plans has additional nested endpoints like `/{plan_id}/sources/{source_id}` and `/{plan_id}/activity-group`. What pattern do these follow -- are they separate routers or nested under the same router?
4. Look at how both routers handle the service layer returning `None`. Is the pattern consistent?

<details>
<summary>Hints</summary>

- Look at `plans.py` line 60: `def delete_plan(plan_id: int, cascade: bool = False, ...)` -- the `cascade` parameter is a query parameter with a default of `False`.
- The nested endpoints are all on the same `plans` router. FastAPI does not require nested routers for nested URLs -- you can define any path pattern on a single router.
- Both routers consistently check `if not result: raise HTTPException(status_code=404, ...)`.
</details>

### Exercise 2: Trace the Dependency Injection Chain

Starting from any endpoint in `collections.py`, trace the dependency injection chain:

1. Open `src/wellbegun/database.py`. The `get_db` function is a generator that yields a `Session`. How is this similar to a pytest fixture with `yield`?
2. What happens if the endpoint raises an exception -- does the database session still get closed? Look at the `finally` block.
3. The `get_db` function uses `SessionLocal()`, which is created from `sessionmaker(bind=engine)`. Where is `engine` configured? (Hint: check `database.py` and `config.py`.)
4. Could you add a second dependency -- say, a function that checks for an API key in the request headers? How would you declare it in an endpoint signature?

<details>
<summary>Hints</summary>

- The `finally` block in `get_db` guarantees `db.close()` runs even if an exception occurs -- exactly like a pytest `yield` fixture.
- To add another dependency, you would write a function like `def verify_api_key(x_api_key: str = Header(...))` and add `key: str = Depends(verify_api_key)` to the endpoint signature. FastAPI resolves dependencies in order.
</details>

---

## Knowledge Check

**1. What does `response_model=CollectionOut` do in a FastAPI endpoint decorator?**

a) It validates the request body against the CollectionOut schema
b) It validates and serializes the return value, stripping extra fields before sending JSON
c) It generates a CollectionOut object automatically from the database
d) It imports the CollectionOut class from the schemas module

<details><summary>Answer</summary>b) The response_model validates the function's return value against the schema and serializes it to JSON, filtering out any fields not defined in the model.</details>

**2. How does FastAPI decide whether a function parameter is a path parameter or a query parameter?**

a) Path parameters use uppercase names, query parameters use lowercase
b) You must explicitly annotate each parameter with `Path()` or `Query()`
c) Parameters matching `{placeholders}` in the route path become path params; others with defaults become query params
d) All parameters are query parameters by default

<details><summary>Answer</summary>c) FastAPI matches parameter names to `{placeholders}` in the route path. Parameters that match become path parameters; remaining parameters with default values become query parameters.</details>

**3. What problem does `Depends(get_db)` solve compared to using a global database session?**

a) It makes the code run faster by caching database connections
b) It ensures each request gets its own session with automatic cleanup, preventing shared state bugs
c) It encrypts the database connection for security
d) It allows the database to be queried asynchronously

<details><summary>Answer</summary>b) Dependency injection via `Depends` ensures each request gets a fresh database session that is automatically closed after the request completes, preventing issues with shared mutable state across concurrent requests.</details>

**4. In this code, what happens if the client sends `{"category_id": "not_a_number"}`?**

```python
@router.post("/", response_model=CollectionOut, status_code=201)
def create_collection(data: CollectionCreate, db: Session = Depends(get_db)):
    ...
```

a) Python raises a TypeError inside the function
b) FastAPI returns a 422 Unprocessable Entity error before the function runs
c) FastAPI silently converts "not_a_number" to 0
d) The request succeeds with category_id set to None

<details><summary>Answer</summary>b) Pydantic validation runs before the endpoint function is called. Since `category_id` is typed as `int` in `CollectionCreate`, the string "not_a_number" fails validation and FastAPI returns a 422 error with details about which field failed.</details>

**5. Why does `stream_generate` use `async def` with `yield` instead of a regular `def`?**

a) Because all FastAPI functions must be async
b) To allow the server to handle other requests while waiting for LLM tokens, and to deliver tokens incrementally as they arrive
c) Because `yield` only works inside async functions
d) To make the function run on a separate thread

<details><summary>Answer</summary>b) The `async def` with `yield` creates an async generator that suspends while waiting for each LLM token (freeing the event loop for other requests) and yields each token as it arrives, enabling real-time streaming to the client.</details>

---

## Further Reading

- [FastAPI Official Tutorial](https://fastapi.tiangolo.com/tutorial/) -- The step-by-step tutorial covers all the concepts above with interactive examples
- [FastAPI Path Parameters](https://fastapi.tiangolo.com/tutorial/path-params/) -- Deep dive into path parameter types and validation
- [FastAPI Query Parameters](https://fastapi.tiangolo.com/tutorial/query-params/) -- Optional parameters, defaults, and type coercion
- [FastAPI Request Body (Pydantic)](https://fastapi.tiangolo.com/tutorial/body/) -- How Pydantic models validate JSON request bodies
- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/) -- The dependency injection system explained with examples
- [FastAPI Middleware](https://fastapi.tiangolo.com/tutorial/middleware/) -- How middleware (like CORS) wraps every request
- [Pydantic V2 Documentation](https://docs.pydantic.dev/latest/) -- The data validation library that powers FastAPI's type system

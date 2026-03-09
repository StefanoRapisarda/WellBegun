# ORM Concepts

> **Category**: concept | **Difficulty**: beginner | **Time**: ~20 min
> **Prerequisites**: entity-relationship-modeling

## Overview

An ORM (Object-Relational Mapper) bridges two worlds you already know separately: Python objects and SQL database tables. Instead of writing raw SQL strings to store and retrieve data, an ORM lets you work with regular Python classes. You define a class, and the ORM translates attribute access, object creation, and method calls into the corresponding SQL statements behind the scenes.

As a data scientist, you have likely used pandas DataFrames as an in-memory abstraction over tabular data. An ORM serves a similar purpose for persistent storage: it gives you a Pythonic interface so you can think in objects rather than in SQL strings. The ORM used in WellBegun is SQLAlchemy, the most widely adopted ORM in the Python ecosystem.

**Key takeaways:**
- An ORM maps Python classes to database tables and instances to rows
- Column definitions on the class correspond to columns in the SQL table
- You create, query, update, and delete records using Python objects, not raw SQL
- A session manages the conversation between your code and the database, grouping operations into transactions

---

## Core Concepts

### Mapping Classes to Tables

The fundamental idea: one Python class = one database table. The class name is for your Python code; the `__tablename__` attribute tells the ORM which SQL table it corresponds to.

```python
class Note(Base):
    __tablename__ = "notes"
```

This declares that the `Note` class maps to the `notes` table in the database. `Base` is a shared base class that all ORM models inherit from, which registers them with SQLAlchemy's metadata system.

### Columns as Attributes

Each attribute on the class represents a column in the table. The Python type annotation (`Mapped[str]`) declares the Python-side type, while the `mapped_column(...)` call declares the SQL-side type and constraints:

```python
title: Mapped[str] = mapped_column(String(255), nullable=False)
```

This line means: "the `title` attribute is a Python `str` that maps to a `VARCHAR(255)` column that cannot be NULL."

Here is how Python types map to SQL column types in practice:

| Python Type | SQLAlchemy Type | SQL Column Type |
|-------------|----------------|-----------------|
| `Mapped[int]` | `Integer` | `INTEGER` |
| `Mapped[str]` | `String(255)` | `VARCHAR(255)` |
| `Mapped[str]` | `Text` | `TEXT` |
| `Mapped[bool]` | `Boolean` | `BOOLEAN` |
| `Mapped[datetime]` | `DateTime` | `DATETIME` |

### Relationships as Object References

Beyond simple columns, ORMs can express foreign-key relationships as Python object references. For example, if a `Note` belonged to a `Project`, you could navigate from a note object directly to its project object without writing a JOIN query. WellBegun uses knowledge triples for most relationships, but the concept applies broadly.

### Sessions and Transactions

A **session** is the ORM's unit of work. It tracks which objects have been created, modified, or deleted, and when you call `commit()`, it flushes all pending changes to the database in a single transaction. If something goes wrong, the transaction rolls back automatically.

```python
db.add(note)      # Stage the new object (not yet in DB)
db.commit()       # Write all staged changes to the database
db.refresh(note)  # Reload the object from DB (e.g., to get auto-generated id)
```

Think of the session as a staging area, similar to how `git add` stages files before `git commit` writes them.

### Identity Map

The session maintains an **identity map**: if you query for the same row twice within one session, you get back the exact same Python object, not a copy. This prevents inconsistencies where two different objects represent the same database row with different attribute values.

---

## In This Project

WellBegun defines its ORM models in `src/wellbegun/models/`, one file per entity type. The `Note` model in `src/wellbegun/models/note.py` is a clean example:

```python
# From src/wellbegun/models/note.py
from sqlalchemy.orm import Mapped, mapped_column
from wellbegun.models.base import Base

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

This class translates to:

```sql
CREATE TABLE notes (
    id INTEGER PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    is_active BOOLEAN NOT NULL DEFAULT 0,
    is_archived BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
```

Notice the `onupdate=datetime.utcnow` on `updated_at` -- this tells the ORM to automatically refresh the timestamp whenever any attribute on the row is modified, without you writing any explicit update logic.

The database session is created in `src/wellbegun/database.py` via a generator function that FastAPI's dependency injection system calls for each request:

```python
# From src/wellbegun/database.py
def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Each HTTP request gets its own session, ensuring isolation between concurrent requests.

---

## Guided Examples

### Example 1: Creating a Note (Python Objects to SQL INSERT)

When the service layer creates a note, here is what happens at each step:

```python
# From src/wellbegun/services/note_service.py:16-27
def create(db: Session, title: str, content: str | None = None) -> Note:
    note = Note(title=title, content=content)   # 1. Create Python object
    db.add(note)                                  # 2. Stage it in the session
    db.flush()                                    # 3. Send INSERT to DB (gets id)
    create_entity_tag(db, title, "note", "note", note.id)  # 4. Use the new id
    db.commit()                                   # 5. Commit the transaction
    db.refresh(note)                              # 6. Reload to get final state
    return note
```

Step by step, the ORM translates this into:

| Python Code | SQL Equivalent |
|------------|---------------|
| `Note(title="My Idea", content="...")` | (Constructs an in-memory object, no SQL yet) |
| `db.add(note)` | (Marks the object as pending, no SQL yet) |
| `db.flush()` | `INSERT INTO notes (title, content, is_active, is_archived, created_at, updated_at) VALUES ('My Idea', '...', 0, 0, '2026-03-05...', '2026-03-05...')` |
| `db.commit()` | `COMMIT` |
| `db.refresh(note)` | `SELECT * FROM notes WHERE id = 1` |

The distinction between `flush()` and `commit()` is important: `flush()` sends the SQL to the database so you can use auto-generated values (like `id`), but `commit()` makes it permanent. If an error occurs between flush and commit, the transaction rolls back.

### Example 2: Querying Notes (SQL SELECT to Python Objects)

```python
# From src/wellbegun/services/note_service.py:8-9
def get_all(db: Session) -> list[Note]:
    return db.query(Note).order_by(Note.created_at.desc()).all()
```

This translates to:

```sql
SELECT * FROM notes ORDER BY created_at DESC;
```

The result is not a list of tuples or dictionaries -- it is a list of `Note` objects. You access values as `note.title`, `note.content`, etc. The ORM hydrates each row into a fully typed Python object.

### Example 3: Updating a Note (Python Attribute Assignment to SQL UPDATE)

```python
# From src/wellbegun/services/note_service.py:30-41
def update(db: Session, note_id: int, **kwargs) -> Note | None:
    note = get_by_id(db, note_id)
    if not note:
        return None
    for key, value in kwargs.items():
        if hasattr(note, key):
            setattr(note, key, value)
    db.commit()
    db.refresh(note)
    return note
```

Because the session tracks the `note` object, simply setting `note.title = "New Title"` via `setattr` is enough. When `db.commit()` runs, the ORM detects the change and generates:

```sql
UPDATE notes SET title = 'New Title', updated_at = '2026-03-05...' WHERE id = 42;
```

No explicit `UPDATE` statement needed in Python -- the ORM figures out which columns changed.

---

## Exercises

### Exercise 1: Map a Model to SQL

**Task**: Open `src/wellbegun/models/project.py` and examine the `Project` class. For each attribute (`id`, `title`, `description`, `status`, `is_active`, `is_archived`, `start_date`, `created_at`, `updated_at`), write down: (a) the Python type, (b) the SQL column type, and (c) whether it can be NULL.

<details>
<summary>Hint</summary>
Look at each `mapped_column(...)` call. The first argument is the SQL type (e.g., `String(50)`, `Text`, `Boolean`). The `nullable` keyword tells you whether NULL is allowed. `Mapped[str | None]` on the Python side means the value can be `None` (i.e., NULL in SQL).
</details>

### Exercise 2: Predict the SQL

**Task**: Given the following Python code, write the SQL statement the ORM would generate:

```python
project = Project(title="WellBegun", description="A note-taking app", status="in_progress")
db.add(project)
db.commit()
```

<details>
<summary>Hint</summary>
This is an INSERT statement. The columns are title, description, status, plus any columns with default values (is_active, is_archived, created_at, updated_at). The defaults for is_active and is_archived are False (0 in SQL).
</details>

---

## Knowledge Check

**Q1**: What does `__tablename__ = "notes"` do in a SQLAlchemy model class?
- A) Creates a Python variable named "notes"
- B) Maps the class to a database table called "notes"
- C) Imports the notes module
- D) Sets the display name for the admin interface

<details>
<summary>Answer</summary>
**B) Maps the class to a database table called "notes"** -- This tells SQLAlchemy which SQL table the Python class corresponds to. Without it, the ORM would not know where to store or retrieve data for this class.
</details>

**Q2**: What is the difference between `db.flush()` and `db.commit()`?
- A) They are identical
- B) `flush()` sends SQL to the database but does not finalize; `commit()` makes changes permanent
- C) `flush()` is for reads, `commit()` is for writes
- D) `flush()` only works with INSERT, `commit()` works with all operations

<details>
<summary>Answer</summary>
**B) `flush()` sends SQL to the database but does not finalize; `commit()` makes changes permanent** -- `flush()` executes the SQL (so auto-generated values like `id` become available) but the transaction remains open. `commit()` finalizes the transaction. If an error occurs after flush but before commit, changes roll back.
</details>

**Q3**: In the Note model, `content: Mapped[str | None] = mapped_column(Text, nullable=True)`. What does `nullable=True` mean?
- A) The column must always have a value
- B) The column can store NULL (i.e., no value) in the database
- C) The column will be automatically filled with an empty string
- D) The column is optional in Python but required in SQL

<details>
<summary>Answer</summary>
**B) The column can store NULL (i.e., no value) in the database** -- `nullable=True` means the SQL column allows NULL values. The Python-side `Mapped[str | None]` mirrors this by allowing the attribute to be `None`.
</details>

**Q4**: Why does the `update` function in note_service.py not need an explicit SQL UPDATE statement?
- A) It uses raw SQL internally
- B) The ORM session tracks changes to loaded objects and generates UPDATE statements on commit
- C) FastAPI handles the database updates automatically
- D) The `setattr` function writes directly to the database

<details>
<summary>Answer</summary>
**B) The ORM session tracks changes to loaded objects and generates UPDATE statements on commit** -- When you modify attributes on an ORM object that is tracked by the session, SQLAlchemy detects the changes ("dirty" state) and generates the appropriate UPDATE SQL when `commit()` is called.
</details>

---

## Further Reading
- [SQLAlchemy ORM Tutorial](https://docs.sqlalchemy.org/en/20/tutorial/) -- official-docs
- [SQLAlchemy Mapped Column Documentation](https://docs.sqlalchemy.org/en/20/orm/mapped_attributes.html) -- official-docs
- [FastAPI with SQLAlchemy](https://fastapi.tiangolo.com/tutorial/sql-databases/) -- tutorial
- [ORM Patterns: Identity Map](https://martinfowler.com/eaaCatalog/identityMap.html) -- article

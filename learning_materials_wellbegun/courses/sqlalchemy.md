# SQLAlchemy ORM

> **Category**: library | **Difficulty**: beginner | **Time**: ~25 min
> **Prerequisites**: None

## Overview

If you have used pandas DataFrames, think of SQLAlchemy models as DataFrames with stricter column types that are backed by a real database. Each Python class is a table, each instance is a row, and each attribute is a column. Instead of `df["name"]`, you write `model.name`, and instead of `pd.read_csv()`, you ask a *Session* to query the database for you.

SQLAlchemy is Python's most widely used Object-Relational Mapper (ORM). It lets you define your database schema as ordinary Python classes and interact with rows as Python objects, without writing raw SQL.

**Key takeaways:**

- SQLAlchemy maps Python classes to database tables (the ORM pattern)
- Column types (`String`, `Integer`, `Boolean`, `DateTime`) mirror Python types
- Relationships define how tables connect (like foreign keys in a spreadsheet)
- The Session manages transactions: add, flush, commit, refresh

---

## Core Concepts

### 1. Models as Python Classes

Every database table is represented by a Python class that inherits from a base class. In WellBegun, all models ultimately descend from `Base`, which is SQLAlchemy's `DeclarativeBase`:

```python
# src/wellbegun/models/base.py (lines 1-5)
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

Here is the `Category` model, a straightforward example of a complete table definition:

```python
# src/wellbegun/models/collection.py (lines 12-32)
class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    member_entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    statuses: Mapped[list["CategoryStatus"]] = relationship(...)
    collections: Mapped[list["Collection"]] = relationship(...)
```

**What to notice:**

- `__tablename__` sets the actual SQL table name.
- `Mapped[int]` is the modern SQLAlchemy 2.x type annotation syntax. It tells both Python type-checkers and SQLAlchemy what type the column holds.
- `mapped_column(...)` configures each column: its SQL type, whether it is a primary key, whether it allows null values, and any defaults.
- `default=datetime.utcnow` means "if no value is provided when inserting, call this function." `onupdate=datetime.utcnow` means "also call it whenever the row is updated."

**Pandas analogy:** Think of `__tablename__` as the CSV filename, `mapped_column` as `dtype` specifications in `pd.read_csv()`, and `nullable=False` as the equivalent of ensuring a column has no `NaN` values.

### 2. Column Types and Constraints

SQLAlchemy provides SQL column types that map to Python types:

| SQLAlchemy Type | Python Type | Example from WellBegun |
|----------------|-------------|----------------------|
| `Integer` | `int` | `id`, `position`, `category_id` |
| `String(n)` | `str` | `slug` (max 50 chars), `title` (max 255) |
| `Text` | `str` | `notes`, `description` (unlimited length) |
| `Boolean` | `bool` | `is_default`, `is_active`, `is_archived` |
| `DateTime` | `datetime` | `created_at`, `updated_at` |

**Constraints** enforce data integrity rules at the database level. WellBegun uses `UniqueConstraint` to prevent duplicate rows:

```python
# src/wellbegun/models/collection.py (lines 48-50) - CategoryStatus
__table_args__ = (
    UniqueConstraint("category_id", "value"),
)
```

This means no two statuses can have the same `(category_id, value)` pair. If you try to insert a duplicate, the database will reject it.

```python
# src/wellbegun/models/collection.py (lines 98-100) - CollectionItem
__table_args__ = (
    UniqueConstraint("collection_id", "member_entity_type", "member_entity_id"),
)
```

This three-column constraint ensures the same entity cannot be added to the same collection twice.

The `KnowledgeTriple` model uses a similar pattern with a named constraint:

```python
# src/wellbegun/models/knowledge_triple.py (lines 11-16)
__table_args__ = (
    UniqueConstraint(
        "subject_type", "subject_id", "object_type", "object_id",
        name="uq_knowledge_triple",
    ),
)
```

### 3. Relationships

Relationships define how tables are connected. They let you navigate between related objects in Python without writing JOIN queries yourself.

**ForeignKey** declares the database-level link:

```python
# src/wellbegun/models/collection.py (lines 39-41)
category_id: Mapped[int] = mapped_column(
    Integer, ForeignKey("categories.id"), nullable=False
)
```

This tells the database: "the `category_id` column in this table must reference an existing `id` in the `categories` table."

**relationship()** creates a Python-level attribute that loads the related objects:

```python
# src/wellbegun/models/collection.py (lines 26-32) - on Category
statuses: Mapped[list["CategoryStatus"]] = relationship(
    "CategoryStatus", back_populates="category", cascade="all, delete-orphan",
    order_by="CategoryStatus.position",
)
collections: Mapped[list["Collection"]] = relationship(
    "Collection", back_populates="category",
)
```

```python
# src/wellbegun/models/collection.py (line 46) - on CategoryStatus
category: Mapped["Category"] = relationship("Category", back_populates="statuses")
```

**What the parameters mean:**

- `back_populates` creates a two-way link. `Category.statuses` gives you the list of statuses; `CategoryStatus.category` gives you back the parent category. Both sides stay in sync.
- `cascade="all, delete-orphan"` means: when you delete a category, automatically delete all its statuses too. "Delete-orphan" also means if you remove a status from the list, it gets deleted from the database.
- `order_by` controls the default ordering when you access the list.

**Pandas analogy:** Relationships are like doing `pd.merge(categories_df, statuses_df, on="category_id")`, except SQLAlchemy does it lazily (only when you access the attribute) and keeps both directions linked automatically.

### 4. Inheritance (Polymorphic Identity)

WellBegun uses SQLAlchemy's *single-table inheritance* pattern so that different entity types (projects, activities, collections, notes) can share a common `entities` table while having their own specialized tables.

The parent class defines the discriminator:

```python
# src/wellbegun/models/entity.py (lines 9-28)
class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # ... timestamps ...

    __mapper_args__ = {
        "polymorphic_on": "entity_type",
        "polymorphic_identity": "entity",
    }
```

The child class inherits and specializes:

```python
# src/wellbegun/models/collection.py (lines 53-71)
class Collection(Entity):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(
        Integer, ForeignKey("entities.id"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=False
    )

    category: Mapped["Category"] = relationship("Category", back_populates="collections")
    items: Mapped[list["CollectionItem"]] = relationship(
        "CollectionItem", back_populates="collection", cascade="all, delete-orphan",
        order_by="CollectionItem.position",
    )

    __mapper_args__ = {
        "polymorphic_identity": "collection",
    }
```

**How it works:**

- `polymorphic_on = "entity_type"` tells SQLAlchemy to use the `entity_type` column to decide which Python class to instantiate when loading rows.
- `polymorphic_identity = "collection"` means: rows where `entity_type == "collection"` become `Collection` instances.
- `Collection` gets all the columns from `Entity` (title, description, is_active, etc.) plus its own (category_id, items).
- The child's `id` column has a `ForeignKey` pointing back to `entities.id`, creating a joined-table inheritance pattern.

**Pandas analogy:** Imagine a single DataFrame with a `type` column. Instead of filtering with `df[df.type == "collection"]` and remembering which columns are relevant, SQLAlchemy gives you a proper Python class with only the attributes that matter.

### 5. Session Operations (CRUD)

The `Session` is your connection to the database. All reads and writes go through it. Think of it as a transaction manager that batches your changes and sends them to the database when you say so.

**Create pattern** (add, flush, commit, refresh):

```python
# src/wellbegun/services/collection_service.py (lines 30-46)
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
    db.add(collection)          # Stage the object (like git add)
    db.flush()                  # Send INSERT to DB, get auto-generated id
    create_entity_tag(db, title, "collection", "collection", collection.id)
    db.commit()                 # Make it permanent
    db.refresh(collection)      # Reload from DB to get any DB-generated values
    return collection
```

**The four steps explained:**

| Step | What It Does | Git Analogy |
|------|-------------|-------------|
| `db.add(obj)` | Mark object for insertion | `git add` |
| `db.flush()` | Send SQL to DB (within transaction), auto-generated IDs now available | `git stage` |
| `db.commit()` | Finalize the transaction, make changes permanent | `git commit` |
| `db.refresh(obj)` | Reload the object from DB to pick up any defaults or triggers | `git pull` after push |

Why flush before commit? Because `flush()` assigns the auto-generated `id` so you can use it immediately (e.g., to create the entity tag), while `commit()` makes everything permanent as a single atomic operation.

**Query patterns:**

```python
# src/wellbegun/services/collection_service.py (lines 10-18)
def get_all(db: Session, category_id: int | None = None) -> list[Collection]:
    q = (
        db.query(Collection)
        .options(joinedload(Collection.items))
        .order_by(Collection.created_at.desc())
    )
    if category_id is not None:
        q = q.filter(Collection.category_id == category_id)
    return q.all()
```

**What to notice:**

- `db.query(Collection)` starts a query for all Collection rows.
- `.options(joinedload(Collection.items))` tells SQLAlchemy to load related items in the same SQL query (a JOIN), avoiding the "N+1 problem" where accessing each collection's items would trigger a separate query.
- `.filter(...)` adds a WHERE clause. Filters can be chained conditionally.
- `.order_by(...)` sorts results. `.desc()` gives descending order.
- `.all()` returns a list; `.first()` returns one result or `None`.

**Filter with or_:**

```python
# src/wellbegun/services/knowledge_service.py (lines 18-33)
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

`or_()` combines conditions with SQL OR. The `&` operator is SQL AND. This query finds all triples where the entity appears as either subject or object.

**Upsert pattern** (check existing, then update or create):

```python
# src/wellbegun/services/knowledge_service.py (lines 36-74)
def create_triple(
    db: Session,
    subject_type: str, subject_id: int,
    predicate: str,
    object_type: str, object_id: int,
) -> KnowledgeTriple:
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

This is a common pattern: query first to see if the row already exists. If it does, update only the changed field. If it does not, create a new one. This avoids violating the `UniqueConstraint` on the table.

**Update pattern** (setattr loop):

```python
# src/wellbegun/services/collection_service.py (lines 49-60)
def update(db: Session, collection_id: int, **kwargs) -> Collection | None:
    collection = get_by_id(db, collection_id)
    if not collection:
        return None
    for key, value in kwargs.items():
        if hasattr(collection, key):
            setattr(collection, key, value)
    # ... additional logic ...
    db.commit()
    db.refresh(collection)
    return collection
```

Because SQLAlchemy tracks changes to mapped objects automatically, you just set Python attributes and then commit. The ORM generates the UPDATE SQL for you.

**Delete pattern:**

```python
# src/wellbegun/services/collection_service.py (lines 63-71)
def delete(db: Session, collection_id: int) -> bool:
    collection = get_by_id(db, collection_id)
    if not collection:
        return False
    delete_entity_tag(db, "collection", collection_id)
    delete_entity_graph_data(db, "collection", collection_id)
    db.delete(collection)
    db.commit()
    return True
```

Before deleting the main object, the code cleans up related data in other tables. Then `db.delete()` marks the object for removal, and `db.commit()` makes it permanent. Note that `cascade="all, delete-orphan"` on the `items` relationship means `CollectionItem` rows are deleted automatically.

---

## In This Project

WellBegun follows a layered architecture where SQLAlchemy plays a specific role:

```
Router (API endpoint)
  --> Service (business logic, receives Session)
    --> Model (SQLAlchemy class, defines schema)
      --> Database (SQLite file)
```

- **Models** (`src/wellbegun/models/`) define the database schema: tables, columns, relationships, and constraints.
- **Services** (`src/wellbegun/services/`) contain the business logic. Each service function receives a `Session` object, uses it to query or modify the database, and returns model instances.
- **Routers** (`src/wellbegun/routers/`) define the API endpoints. They receive HTTP requests, call service functions, and return responses.

The Session is created by FastAPI's dependency injection system and passed to service functions. You will see `db: Session` as the first parameter of almost every service function.

---

## Guided Examples

### Example 1: Tracing a Collection from Model to CRUD

Start with the model definition. Open `src/wellbegun/models/collection.py` and look at the `Collection` class (lines 53-71). It inherits from `Entity`, meaning it gets `title`, `description`, `is_active`, `is_archived`, `created_at`, and `updated_at` for free. It adds `category_id` and relationships to `Category` and `CollectionItem`.

Now open `src/wellbegun/services/collection_service.py`. Walk through the lifecycle:

1. **Create** (lines 30-46): A new `Collection` is instantiated with keyword arguments, added to the session, flushed to get its `id`, then committed.
2. **Read** (lines 10-18): `get_all()` builds a query with `joinedload` to eagerly fetch items, optionally filters by `category_id`, and returns all results.
3. **Read one** (lines 21-27): `get_by_id()` is nearly identical but uses `.first()` instead of `.all()`.
4. **Update** (lines 49-60): Fetches the object, loops over kwargs to set attributes, commits.
5. **Delete** (lines 63-71): Fetches the object, cleans up related data, calls `db.delete()`, commits.

Notice how every function follows the same rhythm: get the object (or create it), make changes, commit, refresh if needed.

### Example 2: Querying with or_ and the Upsert Pattern

Open `src/wellbegun/services/knowledge_service.py`. The `KnowledgeTriple` model represents a relationship between two entities (subject-predicate-object, like "project contains note").

Look at `get_triples_for_entity()` (lines 18-33). This function needs to find all triples where a given entity appears on *either* side of the relationship. It uses `or_()` to combine two conditions:
- The entity is the subject (left side), OR
- The entity is the object (right side)

Each condition uses `&` to combine type and id checks. This translates to SQL like:
```sql
WHERE (subject_type = 'project' AND subject_id = 5)
   OR (object_type = 'project' AND object_id = 5)
```

Now look at `create_triple()` (lines 36-74). It demonstrates the upsert pattern:
1. Query for an existing triple matching the same subject and object.
2. If found and the predicate differs, update just the predicate and flush.
3. If not found, create a new triple, add, commit, and refresh.

This pattern is essential when you have a `UniqueConstraint` and want "create if new, update if existing" behavior.

---

## Exercises

1. **Read the CollectionItem model** (`collection.py`, lines 74-101). Identify all column types used and explain what the `UniqueConstraint` on lines 98-100 prevents.

2. **Trace the add_item function** (`collection_service.py`, lines 117-178). List every database operation (query, add, flush, commit, refresh) in order and explain why each is needed.

3. **Write a hypothetical query** that finds all `CollectionItem` rows where `status` is not null, ordered by `position`. Use the patterns you have seen in the service files.

4. **Compare create() and create_triple()**. The `create()` function in `collection_service.py` always creates a new row. The `create_triple()` function in `knowledge_service.py` checks for an existing row first. Why does `create_triple()` need the upsert pattern while `create()` does not?

---

## Knowledge Check

1. **What does `mapped_column(String(50), unique=True, nullable=False)` mean?**
   A string column with a maximum of 50 characters, where every value must be unique across the table, and null values are not allowed.

2. **What is the difference between `db.flush()` and `db.commit()`?**
   `flush()` sends the SQL to the database but keeps the transaction open (changes can still be rolled back). `commit()` finalizes the transaction, making changes permanent. Use `flush()` when you need auto-generated values (like an id) before the transaction is complete.

3. **What does `cascade="all, delete-orphan"` on a relationship mean?**
   When the parent object is deleted, all related child objects are automatically deleted too ("all"). Additionally, if a child is removed from the parent's collection without being explicitly deleted, SQLAlchemy will delete it from the database ("delete-orphan").

4. **Why does `get_all()` use `joinedload(Collection.items)`?**
   Without it, accessing `collection.items` for each collection would trigger a separate SQL query (the N+1 problem). `joinedload` tells SQLAlchemy to load all items in a single JOIN query, which is much more efficient.

5. **In the upsert pattern, why query `.first()` before inserting?**
   The `KnowledgeTriple` table has a `UniqueConstraint` on `(subject_type, subject_id, object_type, object_id)`. Inserting a duplicate would raise a database error. Checking first lets us update the existing row's predicate instead.

---

## Further Reading

- [SQLAlchemy 2.0 Tutorial](https://docs.sqlalchemy.org/en/20/tutorial/) -- The official tutorial, start with "Working with Data" and "Working with ORM Related Objects"
- [SQLAlchemy ORM Mapped Column](https://docs.sqlalchemy.org/en/20/orm/mapped_attributes.html) -- Detailed reference for `Mapped` and `mapped_column`
- [SQLAlchemy Relationship Patterns](https://docs.sqlalchemy.org/en/20/orm/relationships.html) -- One-to-many, many-to-many, and cascade options
- [SQLAlchemy Inheritance Mapping](https://docs.sqlalchemy.org/en/20/orm/inheritance.html) -- Polymorphic identity and joined-table inheritance
- [Session Basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html) -- How add, flush, commit, and refresh work together

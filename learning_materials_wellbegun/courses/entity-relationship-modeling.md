# Entity-Relationship Modeling

> **Category**: concept | **Difficulty**: beginner | **Time**: ~20 min
> **Prerequisites**: None

## Overview
Entity-Relationship (ER) modeling is a way of designing how your data is structured and how different pieces of data relate to each other. If you have worked with pandas DataFrames, you have worked with entities (each DataFrame is like a table) and relationships (merging two DataFrames on a shared column). ER modeling formalizes this process.

WellBegun manages eight entity types -- Note, Project, Source, Actor, Activity, Plan, Collection, and Log -- each stored in its own database table. The interesting part is how these entities connect: a Plan can have Activities, Sources can be linked to Projects, and any entity can be tagged. These connections are the "relationships" in ER modeling.

Understanding ER modeling helps you see why the database has the tables it has, why some tables exist solely to link other tables together, and how the knowledge graph (using subject-predicate-object triples) provides a flexible relationship mechanism beyond traditional foreign keys.

**Key takeaways:**
- Entities are the "things" in your application (Note, Project, Source, etc.), each stored in a database table
- Attributes are the properties of an entity (title, content, created_at)
- Relationships connect entities: one-to-many (a Plan has many Activities), many-to-many (entities have many Tags, tags apply to many entities)
- Primary keys uniquely identify rows; foreign keys link rows across tables
- WellBegun uses both traditional foreign keys and a flexible KnowledgeTriple system for relationships

---

## Core Concepts

### Entities and Attributes

An **entity** is a distinct "thing" your application tracks. In WellBegun, each entity type maps to a SQLAlchemy model class and a database table:

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

Each column is an **attribute**. The `id` column is the **primary key** -- a unique identifier for each row. The `nullable=False` constraint means the attribute is required.

### Relationships

Relationships describe how entities connect to each other. There are three main types:

**One-to-Many**: One entity owns many of another. In WellBegun, a Plan has many Activities:

```python
# From src/wellbegun/models/plan.py:34-39
activities: Mapped[list["Activity"]] = relationship(
    "Activity",
    foreign_keys="Activity.plan_id",
    order_by="Activity.position",
    lazy="joined",
)
```

The Activity table has a `plan_id` foreign key pointing back to the Plan:

```
plans table                    activities table
+----+----------------+       +----+----------+---------+
| id | title          |       | id | title    | plan_id |
+----+----------------+       +----+----------+---------+
|  1 | Learn FastAPI  |       | 10 | Read docs|    1    |
|  2 | Build Frontend |       | 11 | Write API|    1    |
+----+----------------+       | 12 | Add tests|    2    |
                               +----+----------+---------+
```

Plan 1 has Activities 10 and 11. Plan 2 has Activity 12. Each activity belongs to at most one plan.

**Many-to-Many**: Entities on both sides can have multiple connections. In WellBegun, any entity can have multiple tags, and any tag can be applied to multiple entities. This requires a **junction table** (`entity_tags`):

```python
# From src/wellbegun/models/tag.py:26-42
class EntityTag(Base):
    __tablename__ = "entity_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tag_id: Mapped[int] = mapped_column(Integer, nullable=False)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("tag_id", "target_type", "target_id"),
    )
```

```
tags table              entity_tags table           notes table
+----+--------+        +--------+-------------+----+ +----+----------+
| id | name   |        | tag_id | target_type | target_id | | id | title    |
+----+--------+        +--------+-------------+-----------+ +----+----------+
|  1 | Python |        |   1    | note        |     5     | |  5 | API tips |
|  2 | Web    |        |   1    | project     |     3     | |  6 | DB notes |
+----+--------+        |   2    | note        |     5     | +----+----------+
                        +--------+-------------+-----------+
```

Note 5 has tags "Python" and "Web". Tag "Python" is applied to both Note 5 and Project 3.

### Primary Keys and Foreign Keys

- **Primary key** (`id`): uniquely identifies each row in a table. Every entity in WellBegun has an `id` column as its primary key.
- **Foreign key** (`plan_id`, `tag_id`): a column that references the primary key of another table. It creates a link between rows in different tables.

The foreign key enforces **referential integrity** -- you cannot create an Activity with `plan_id = 99` if Plan 99 does not exist.

### Polymorphic References

WellBegun has a twist: the `entity_tags` table uses `target_type` + `target_id` instead of a traditional foreign key. This means a single table can reference rows in *any* entity table:

- `target_type = "note"`, `target_id = 5` points to Note #5
- `target_type = "project"`, `target_id = 3` points to Project #3

This is sometimes called a "polymorphic association." It trades the database-enforced referential integrity of foreign keys for flexibility -- one junction table works for all entity types.

---

## In This Project

### WellBegun's Entity Types

WellBegun has eight primary entity types, each with its own table:

| Entity | Table | Purpose |
|--------|-------|---------|
| Note | `notes` | Quick thoughts, snippets |
| Project | `projects` | Ongoing work with goals |
| Source | `sources` | Books, papers, URLs |
| Actor | `actors` | People, organizations |
| Activity | `activities` | Tasks, actions |
| Plan | `plans` | Structured sequences of activities |
| Collection | `collections` | Grouped lists of entities |
| Log | `logs` | Daily entries, diary |

### KnowledgeTriple: A Flexible Relationship System

Beyond traditional foreign keys, WellBegun uses a **knowledge graph** built on subject-predicate-object triples:

```python
# From src/wellbegun/models/knowledge_triple.py
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

A triple reads like a sentence: **Subject** -- *predicate* -- **Object**. For example:

```
Plan #1   "has activities"   Collection #7
Plan #1   "has sources"      Collection #8
Plan #1   "has actors"       Collection #9
```

This means Plan 1 is linked to three collections -- one for its activities, one for its sources, and one for its actors.

### Collections as Ordered Groups

Collections group entities together with ordering and status:

```python
# From src/wellbegun/models/collection.py:74-100
class CollectionItem(Base):
    __tablename__ = "collection_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    collection_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("entities.id"), nullable=False
    )
    member_entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    member_entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    header: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint("collection_id", "member_entity_type", "member_entity_id"),
    )
```

Like `entity_tags`, `CollectionItem` uses `member_entity_type` + `member_entity_id` to reference any entity type. But it adds `position`, `status`, and `notes` -- metadata about the relationship itself.

### The entity_tags Table

Tags provide a labeling system across all entities:

```python
# From src/wellbegun/models/tag.py:9-23
class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    full_tag: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
```

Tags have two roles: "wild" tags (generic labels like "Python", "Urgent") where `entity_type` and `entity_id` are null, and "entity" tags (auto-created when an entity is created) that reference a specific entity.

---

## Guided Examples

### Example: How a Plan Relates to Activities, Sources, and Actors

A Plan in WellBegun is a structured sequence of work. It connects to other entities through multiple mechanisms:

**Step 1: Direct foreign key (one-to-many)**

Activities can belong to a Plan via a direct `plan_id` foreign key:

```python
# From src/wellbegun/models/plan.py:34-39
activities: Mapped[list["Activity"]] = relationship(
    "Activity",
    foreign_keys="Activity.plan_id",
    order_by="Activity.position",
    lazy="joined",
)
```

This is the simplest relationship: each Activity row has a `plan_id` column.

**Step 2: Knowledge triples link to collections**

For more complex relationships, a Plan uses knowledge triples to point to Collection entities:

```
knowledge_triples table:
| subject_type | subject_id | predicate        | object_type | object_id |
|-------------|------------|------------------|-------------|-----------|
| plan        | 1          | has activities   | collection  | 7         |
| plan        | 1          | has sources      | collection  | 8         |
| plan        | 1          | has actors       | collection  | 9         |
```

**Step 3: Collections hold the actual members**

Each Collection groups entities via CollectionItem:

```
collection_items table (for Collection #7, "activities"):
| collection_id | member_entity_type | member_entity_id | position | status |
|--------------|-------------------|-----------------|----------|--------|
| 7            | activity          | 10              | 0        | done   |
| 7            | activity          | 11              | 1        | todo   |

collection_items table (for Collection #8, "sources"):
| collection_id | member_entity_type | member_entity_id | position | status |
|--------------|-------------------|-----------------|----------|--------|
| 8            | source            | 3               | 0        | null   |
```

So the full relationship chain is:
```
Plan #1  --[has activities]--> Collection #7 --[contains]--> Activity #10, Activity #11
Plan #1  --[has sources]----> Collection #8 --[contains]--> Source #3
Plan #1  --[has actors]-----> Collection #9 --[contains]--> Actor #2
```

### Why Two Relationship Mechanisms?

WellBegun uses both foreign keys and knowledge triples because they serve different needs:

- **Foreign keys** (like `Activity.plan_id`) are fast, database-enforced, and simple. Use them for fixed, well-known relationships.
- **Knowledge triples** are flexible and can express *any* relationship between *any* two entity types without schema changes. Use them for relationships that may evolve or that connect arbitrary entity types.

---

## Exercises

### Exercise 1: Draw the ER Diagram

**Task**: Draw an ER diagram (boxes and lines on paper or a whiteboard) showing the relationships between these three entities: `Plan`, `Activity`, and `Source`. Include the `knowledge_triples` and `collection_items` tables that connect them. Show primary keys and foreign keys.

<details>
<summary>Hint 1</summary>
Start with the Plan and Activity boxes. Activity has a <code>plan_id</code> foreign key -- that is a direct one-to-many line from Plan to Activity.
</details>

<details>
<summary>Hint 2</summary>
For the Plan-to-Source relationship, draw the intermediate tables: Plan connects to KnowledgeTriple (via subject_type="plan"), KnowledgeTriple connects to Collection (via object_type="collection"), Collection connects to CollectionItem, and CollectionItem references Source (via member_entity_type="source").
</details>

<details>
<summary>Answer</summary>

```
[Plan] --1:N-- [Activity]          (via Activity.plan_id FK)

[Plan] --subject-- [KnowledgeTriple] --object-- [Collection]
                   predicate: "has sources"

[Collection] --1:N-- [CollectionItem] --polymorphic-- [Source]
                      member_entity_type: "source"
                      member_entity_id: source.id
```

Key insight: the Plan-to-Source path goes through four tables because it uses the flexible knowledge graph + collection pattern.
</details>

### Exercise 2: Identify Relationship Types

**Task**: For each of the following, identify whether it is a one-to-many, many-to-many, or polymorphic relationship:

1. A Plan has many PlanItems
2. A Tag is applied to many entities via entity_tags
3. A Collection has many CollectionItems
4. A KnowledgeTriple links a subject entity to an object entity

<details>
<summary>Answer</summary>

1. **One-to-many** -- PlanItem has a `plan_id` foreign key. Each PlanItem belongs to exactly one Plan.
2. **Many-to-many (polymorphic)** -- entity_tags is a junction table using `target_type` + `target_id` to connect any tag to any entity type.
3. **One-to-many** -- CollectionItem has a `collection_id` foreign key. Each item belongs to one Collection.
4. **Polymorphic relationship** -- KnowledgeTriple uses `subject_type`/`subject_id` and `object_type`/`object_id` to link any two entities of any type.
</details>

### Exercise 3: Trace a Tag

**Task**: When a Note is created, the service calls `create_entity_tag(db, title, "note", "note", note.id)`. What rows does this create in the `tags` and `entity_tags` tables? Why does deleting a Note call both `delete_entity_tag` and `delete_entity_graph_data`?

<details>
<summary>Hint</summary>
Look at how <code>create_entity_tag</code> works -- it creates a Tag row with <code>entity_type="note"</code> and <code>entity_id=note.id</code>, then creates an EntityTag row linking that tag to the note.
</details>

<details>
<summary>Answer</summary>

Creating Note #5 with title "API Tips" creates:
- **tags row**: `{name: "API Tips", category: "note", entity_type: "note", entity_id: 5, ...}`
- **entity_tags row**: `{tag_id: <new tag id>, target_type: "note", target_id: 5}`

Deleting calls both cleanup functions because the note can appear in two places:
- `delete_entity_tag` removes the auto-created tag and its entity_tags links
- `delete_entity_graph_data` removes any KnowledgeTriple rows where the note is the subject or object (e.g., if the note was linked to a project via the knowledge graph)
</details>

---

## Knowledge Check

**Q1**: What is a primary key?
- A) The first column defined in a table
- B) A column that uniquely identifies each row in a table
- C) A column that links to another table
- D) The most important attribute of an entity

<details>
<summary>Answer</summary>
<strong>B) A column that uniquely identifies each row in a table.</strong> In WellBegun, every entity has an <code>id</code> column as its primary key, auto-generated by the database.
</details>

**Q2**: Why does WellBegun use `target_type` + `target_id` in `entity_tags` instead of separate foreign key columns for each entity type?
- A) SQLite does not support foreign keys
- B) It allows one junction table to connect tags to any entity type without schema changes
- C) It makes queries faster
- D) Pydantic requires this pattern

<details>
<summary>Answer</summary>
<strong>B) It allows one junction table to connect tags to any entity type without schema changes.</strong> Instead of needing <code>note_id</code>, <code>project_id</code>, <code>source_id</code> columns (one per entity type), the polymorphic pattern uses two columns to reference any table.
</details>

**Q3**: What does a KnowledgeTriple represent?
- A) A three-column database table
- B) A subject-predicate-object relationship between two entities
- C) Three related entities
- D) A triple-encrypted security token

<details>
<summary>Answer</summary>
<strong>B) A subject-predicate-object relationship between two entities.</strong> For example, (Plan #1, "has activities", Collection #7) means Plan 1 is linked to Collection 7 as its activities list. The triple reads like a sentence.
</details>

**Q4**: What type of relationship does a foreign key like `Activity.plan_id` represent?
- A) Many-to-many
- B) One-to-one
- C) One-to-many (one Plan has many Activities)
- D) Polymorphic

<details>
<summary>Answer</summary>
<strong>C) One-to-many (one Plan has many Activities).</strong> Each Activity has at most one <code>plan_id</code>, but a Plan can have many Activities pointing to it. This is defined in <code>src/wellbegun/models/plan.py:34-39</code>.
</details>

**Q5**: Why does WellBegun use Collections as an intermediate layer between Plans and their Sources, rather than a direct Plan-to-Source foreign key?
- A) SQLite limits the number of foreign keys per table
- B) Collections add ordering, status, and notes to each relationship, and work with any entity type
- C) Direct foreign keys are slower than collections
- D) The frontend cannot display direct relationships

<details>
<summary>Answer</summary>
<strong>B) Collections add ordering, status, and notes to each relationship, and work with any entity type.</strong> A <code>CollectionItem</code> has <code>position</code>, <code>status</code>, and <code>notes</code> fields, which a simple foreign key cannot provide. And since it uses <code>member_entity_type</code> + <code>member_entity_id</code>, the same mechanism works for activities, sources, actors, or any future entity type.
</details>

---

## Further Reading
- [SQLAlchemy ORM Relationships](https://docs.sqlalchemy.org/en/20/orm/relationships.html) -- official-docs
- [Wikipedia: Entity-Relationship Model](https://en.wikipedia.org/wiki/Entity%E2%80%93relationship_model) -- reference
- [Database Design Tutorial](https://www.lucidchart.com/pages/database-diagram/database-design) -- tutorial
- [SQLAlchemy: Mapped Column Configuration](https://docs.sqlalchemy.org/en/20/orm/mapped_attributes.html) -- official-docs

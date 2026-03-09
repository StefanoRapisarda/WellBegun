# Graph Data Modeling

> **Category**: concept | **Difficulty**: beginner | **Time**: ~15 min
> **Prerequisites**: Entity-Relationship Modeling

## Overview

If you've worked with relational databases or pandas DataFrames, you think in tables: rows and columns, foreign keys linking tables together. Graph data modeling offers a different perspective: instead of tables, you think in **nodes** (entities) and **edges** (relationships between them). It's like a network diagram where each entity is a dot and each relationship is a line connecting two dots.

When is a graph better than flat tables? When your data is fundamentally about connections. If you frequently ask "what is related to X?" or "how is A connected to B?", traversing a graph is more natural and often more efficient than joining multiple tables. Social networks, recommendation engines, and knowledge bases are classic graph use cases.

**Python analogy:** If you've used NetworkX, you already know graph data modeling. A NetworkX graph has nodes (entities) and edges (relationships). Graph data modeling is the same idea, but applied to how you structure and store your application's data rather than just analyze it.

**Key takeaways:**
- A graph stores data as nodes (entities) and edges (relationships)
- Edges can be directed (A -> B is different from B -> A) and carry properties (like a label or type)
- Subject-predicate-object triples are the simplest way to represent graph data: (Node A) --[relationship]--> (Node B)
- Graphs excel at answering "what is connected to X?" -- a question that requires multiple JOINs in relational databases

---

## Core Concepts

### 1. Nodes and Edges

A **node** (also called a vertex) represents an entity -- a thing in your domain. In WellBegun, nodes are the entity types: Note, Project, Source, Actor, Activity, Plan, Collection.

An **edge** (also called a link or relationship) connects two nodes and describes how they relate. In WellBegun, edges represent relationships like "contains", "has activities", "cites", "assigned to".

```
[Project: "ML Research"] --contains--> [Note: "Literature Review"]
[Plan: "Sprint 1"]       --has activities--> [Collection: "Sprint Tasks"]
[Note: "Paper Summary"]  --cites--> [Source: "Smith et al. 2024"]
```

**Python/pandas comparison:** In a relational/tabular world, you'd represent these with foreign key columns or junction tables. In a graph, relationships are first-class citizens -- they exist as explicit objects, not just column values.

### 2. Directed vs. Undirected Graphs

In a **directed graph**, edges have a direction: A -> B is different from B -> A. "Project contains Note" is not the same as "Note contains Project."

In an **undirected graph**, edges have no direction: A -- B is the same as B -- A. "Alice knows Bob" implies "Bob knows Alice."

WellBegun's knowledge graph is **directed**. Each triple has a subject and an object, and the direction matters: `Project(id=1) --"contains"--> Note(id=3)` means the project contains the note, not the other way around.

### 3. Properties and Labels

Nodes and edges can carry additional data:

- **Node properties**: Each node has a type (e.g., "Project", "Note") and an ID. In WellBegun, the full entity data (title, content, dates) lives in the relational database tables; the graph just references nodes by type and ID.
- **Edge properties/labels**: Each edge has a predicate (relationship type) like "contains", "has activities", or "cites". This label gives the relationship meaning.

This is a common hybrid approach: use a relational database for entity data (efficient for CRUD operations) and a graph structure for relationships (efficient for traversal queries).

### 4. Subject-Predicate-Object Triples

The simplest way to represent graph data is as **triples**: (subject, predicate, object). Each triple is one fact:

| Subject | Predicate | Object |
|---------|-----------|--------|
| Project(id=1) | contains | Note(id=3) |
| Plan(id=2) | has activities | Collection(id=5) |
| Note(id=3) | cites | Source(id=7) |
| Activity(id=4) | assigned to | Actor(id=1) |

Each row is one edge in the graph. The subject and object are nodes; the predicate is the edge label.

This is the same structure used in RDF (Resource Description Framework), the W3C standard for knowledge graphs. In WellBegun, triples are stored in a single database table rather than as a separate graph database -- a pragmatic choice that keeps the architecture simple.

**Python comparison:** A triple is like a row in a DataFrame with three columns: `subject`, `predicate`, `object`. The entire knowledge graph is a DataFrame of such rows. But unlike a regular DataFrame, you can traverse from node to node by following edges.

### 5. Graph Traversal

**Traversal** means following edges from one node to discover connected nodes. Starting from a node, you can:

- **Find neighbors**: All nodes directly connected to a given node
- **Find paths**: A chain of edges connecting two nodes
- **Filter by predicate**: Only follow edges of a specific type

For example, starting from `Project(id=1)`:
1. Follow "contains" edges to find all Notes in the project
2. From each Note, follow "cites" edges to find all Sources cited
3. Result: all Sources transitively connected to the project

In SQL, this would require multiple JOINs. In a graph, it's a natural traversal.

**Python comparison:** In NetworkX, this is `nx.neighbors(G, node)` or `nx.shortest_path(G, source, target)`. Same concept, different context.

---

## In This Project

WellBegun implements its knowledge graph using a single database table called `knowledge_triples`:

```python
# From src/wellbegun/models/knowledge_triple.py
class KnowledgeTriple(Base):
    __tablename__ = "knowledge_triples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(20))   # e.g., "Project"
    subject_id: Mapped[int] = mapped_column(Integer)         # e.g., 1
    predicate: Mapped[str] = mapped_column(String(100))      # e.g., "contains"
    object_type: Mapped[str] = mapped_column(String(20))     # e.g., "Note"
    object_id: Mapped[int] = mapped_column(Integer)          # e.g., 3
```

Each row is one triple: a subject entity (identified by type + ID), a predicate (relationship label), and an object entity (type + ID). This is a **polymorphic** design -- the `subject_type` and `object_type` columns let any entity type connect to any other entity type, without needing a separate junction table for each combination.

**On the frontend**, the `knowledgeGraph.ts` store holds triples and board nodes:

```typescript
// frontend/src/lib/stores/knowledgeGraph.ts
export const boardNodes = writable<BoardNode[]>([]);
export const triples = writable<Triple[]>([]);
export const hiddenGraphEntities = writable<Set<string>>(new Set());
```

The `KnowledgeGraph.svelte` component renders these as a visual graph: nodes are positioned on a board, and edges (triples) are drawn as lines between them. Users can interact with the graph -- clicking nodes, hiding entities, exploring connections.

**Example relationships in WellBegun:**
- `Plan(id=1) --"has activities"--> Collection(id=5)` -- A plan organizes its activities through a collection
- `Project(id=2) --"contains"--> Note(id=3)` -- A project contains notes
- `Note(id=4) --"cites"--> Source(id=7)` -- A note references a source
- `Activity(id=6) --"assigned to"--> Actor(id=1)` -- An activity is assigned to a person

---

## Guided Examples

### Example 1: Reading a Triple

Consider this row in the `knowledge_triples` table:

| id | subject_type | subject_id | predicate | object_type | object_id |
|----|-------------|------------|-----------|-------------|-----------|
| 42 | Plan | 1 | has activities | Collection | 5 |

This triple says: **Plan #1 "has activities" in Collection #5**. In graph terms:
- Node: Plan(id=1) -- the subject
- Edge: "has activities" -- the predicate
- Node: Collection(id=5) -- the object
- Direction: Plan -> Collection (the plan has the activities, not the other way around)

To find all activities in Plan #1, you'd query: "Give me all triples where `subject_type='Plan'` and `subject_id=1` and `predicate='has activities'`." The result's `object_type` and `object_id` tell you which collection to look at.

### Example 2: Traversing Connections

Suppose you want to find everything connected to `Project(id=2)`. You'd query the triples table twice:

**As subject** (outgoing edges):
```sql
SELECT * FROM knowledge_triples
WHERE subject_type = 'Project' AND subject_id = 2;
```
Results: Project(2) --"contains"--> Note(3), Project(2) --"contains"--> Note(8)

**As object** (incoming edges):
```sql
SELECT * FROM knowledge_triples
WHERE object_type = 'Project' AND object_id = 2;
```
Results: Plan(1) --"relates to"--> Project(2)

Combining both queries gives you all neighbors: Note(3), Note(8), Plan(1). On the KnowledgeGraph board, these would appear as nodes connected to the Project node by labeled edges.

### Example 3: How Triples Become a Visual Graph

The frontend converts triples into a visual graph:

1. `loadTriples()` fetches all triples from `GET /api/knowledge-triples/`
2. `triples.set(data)` updates the store
3. `loadBoard()` fetches board node positions from `GET /api/board-nodes/`
4. `boardNodes.set(data)` updates the store
5. `KnowledgeGraph.svelte` reads `$triples` and `$boardNodes`, rendering each node as a positioned element and each triple as a line between two nodes

The component also imports entity stores (`$notes`, `$projects`, etc.) to display entity names and details on the graph nodes.

---

## Exercises

### Exercise 1: Model a New Relationship

**Task**: You want to represent that Actor(id=3) "authored" Note(id=10). Write out what the triple would look like as a row in the `knowledge_triples` table. What are the subject_type, subject_id, predicate, object_type, and object_id?

<details>
<summary>Hint</summary>
The actor is the subject (they performed the action), "authored" is the predicate, and the note is the object (the thing that was authored). So: subject_type="Actor", subject_id=3, predicate="authored", object_type="Note", object_id=10.
</details>

### Exercise 2: Query for All Neighbors

**Task**: Write a conceptual query (SQL or pseudocode) to find all entities connected to `Note(id=5)` -- both as subject and as object. How many queries do you need?

<details>
<summary>Hint</summary>
You need two queries: one where Note(id=5) is the subject (<code>subject_type='Note' AND subject_id=5</code>) and one where it's the object (<code>object_type='Note' AND object_id=5</code>). The union of both results gives all neighbors.
</details>

### Exercise 3: Graph vs. Relational

**Task**: In a traditional relational schema, how would you represent the relationship "Plan has activities in Collection"? Compare that to the triple representation. What are the trade-offs?

<details>
<summary>Hint</summary>
Relationally, you'd add a <code>collection_id</code> foreign key to the Plan table, or create a junction table <code>plan_collections</code>. The triple approach uses a single generic table for ALL relationships. Trade-off: the triple table is more flexible (any entity can relate to any other) but loses type safety and referential integrity that foreign keys provide.
</details>

---

## Knowledge Check

**Q1**: What are the two fundamental building blocks of a graph data model?
- A) Tables and columns
- B) Nodes (entities) and edges (relationships)
- C) Keys and values
- D) Classes and methods

<details>
<summary>Answer</summary>
<strong>B) Nodes (entities) and edges (relationships)</strong> -- A graph represents data as nodes (things) connected by edges (relationships between things). In WellBegun, nodes are entity types (Note, Project, Plan, etc.) and edges are the triples connecting them ("contains", "has activities", "cites").
</details>

**Q2**: In WellBegun's `KnowledgeTriple` model, what do `subject_type` and `subject_id` together represent?
- A) A database table name and primary key
- B) A node in the graph -- the entity on the "from" side of a relationship
- C) A predicate and its parameters
- D) A foreign key constraint

<details>
<summary>Answer</summary>
<strong>B) A node in the graph -- the entity on the "from" side of a relationship</strong> -- The combination of <code>subject_type</code> (e.g., "Project") and <code>subject_id</code> (e.g., 1) uniquely identifies which entity is the subject of the relationship. This is a polymorphic reference -- it can point to any entity type.
</details>

**Q3**: Why does WellBegun use a single `knowledge_triples` table instead of separate foreign keys for each relationship?
- A) It's faster for read queries
- B) It allows any entity type to relate to any other entity type through a single, flexible structure
- C) It uses less disk space
- D) SQLAlchemy requires it

<details>
<summary>Answer</summary>
<strong>B) It allows any entity type to relate to any other entity type through a single, flexible structure</strong> -- With separate foreign keys, you'd need a new column or junction table for each relationship type. The triple table can represent any relationship between any two entities (Project->Note, Plan->Collection, Note->Source) without schema changes.
</details>

**Q4**: What does "traversal" mean in graph data modeling?
- A) Deleting nodes from the graph
- B) Following edges from one node to discover connected nodes
- C) Sorting nodes alphabetically
- D) Converting a graph to a table

<details>
<summary>Answer</summary>
<strong>B) Following edges from one node to discover connected nodes</strong> -- Traversal is the fundamental graph operation. Starting from a node, you follow edges to find neighbors, then follow their edges to find further connections. This is how WellBegun answers "what is connected to this project?"
</details>

**Q5**: Given the triple `Plan(id=1) --"has activities"--> Collection(id=5)`, which SQL query finds this relationship?
- A) `SELECT * FROM knowledge_triples WHERE predicate = 'has activities'`
- B) `SELECT * FROM knowledge_triples WHERE subject_type = 'Plan' AND subject_id = 1 AND predicate = 'has activities'`
- C) `SELECT * FROM plans WHERE id = 1`
- D) `SELECT * FROM collections WHERE id = 5`

<details>
<summary>Answer</summary>
<strong>B) <code>SELECT * FROM knowledge_triples WHERE subject_type = 'Plan' AND subject_id = 1 AND predicate = 'has activities'</code></strong> -- This query finds all "has activities" relationships from Plan #1. The result's <code>object_type</code> and <code>object_id</code> columns tell you which entities are connected. Option A would find all "has activities" triples for every entity, not just Plan #1.
</details>

---

## Further Reading
- [Graph Data Modeling (Wikipedia)](https://en.wikipedia.org/wiki/Graph_database#Graph_data_modeling) -- reference
- [RDF and Knowledge Graphs (W3C)](https://www.w3.org/RDF/) -- official-docs
- [NetworkX Documentation](https://networkx.org/documentation/stable/) -- reference
- [Neo4j Graph Data Modeling Guide](https://neo4j.com/developer/data-modeling/) -- tutorial
- [Introduction to Knowledge Graphs](https://arxiv.org/abs/2003.02320) -- academic

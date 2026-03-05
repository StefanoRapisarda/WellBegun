"""Shared system prompt fragments describing the WellBegun data model.

Every LLM-facing feature (Coffee Table chat, Journal extraction, RAG)
should prepend DATA_MODEL_CONTEXT to its own system prompt so the model
always knows the full entity schema, status lifecycle, tag system, and
knowledge graph structure.
"""

DATA_MODEL_CONTEXT = """\
## WellBegun Data Model

WellBegun is a personal knowledge base for organising projects, daily logs,
activities, notes, sources, actors, and plans.

### Core Entities

**Project**
- Fields: title, description, status, start_date
- Status values: planned, in_progress, done, on_hold, cancelled (default: in_progress)
- Lifecycle flags: is_active, is_archived

**Log**
- Fields: title, content, location, mood, weather, day_theme
- Classification is done via tags (e.g. "Daily Log", "Work", "Travel", "Health")
- Lifecycle flags: is_active, is_archived

**Activity**
- Fields: title, description, duration (minutes), status, position, header
- Status values: todo, in_progress, done, on_hold, cancelled (default: todo)
- Lifecycle flags: is_active, is_archived
- Foreign keys: log_id, plan_id, source_id (all optional)
- Activities serve as the universal item type: a Plan's steps are Activities \
with plan_id set.

**Note**
- Fields: title, content
- Lifecycle flags: is_active, is_archived

**Source**
- Fields: title, description, author, content_url, source_type (book|article|video|podcast|website), status
- Status values: to_read, reading, reviewed (default: to_read)
- Lifecycle flags: is_active, is_archived

**Actor**
- Fields: full_name, role, affiliation, expertise, notes, email, url
- Lifecycle flags: is_active, is_archived

**Plan**
- Fields: title, description, motivation, outcome, start_date, end_date, status
- Status values: planned, in_progress, done, on_hold, cancelled (default: planned)
- Lifecycle flags: is_active, is_archived
- Contains Activities (via activity.plan_id) ordered by position, optionally \
grouped into sections via activity.header.

### Lifecycle Flags

Every entity has:
- **is_active** (bool): marks the entity as currently being worked on. \
Multiple entities can be active simultaneously.
- **is_archived** (bool): soft-delete; archived entities are hidden by \
default but not deleted.

Setting is_archived = true also sets is_active = false.

### Tag System

Tags provide flexible categorisation across all entity types.

**Tag structure:**
- name: the tag label (e.g. "Machine Learning")
- category: grouping (e.g. "topic", "wild", or an entity type like "project")
- entity_type + entity_id: if set, the tag is automatically linked to a \
specific entity (e.g. a "project" tag auto-created for Project #5)

**Tag categories:**
- **Entity tags** (category = entity type): auto-created when an entity is \
created. Attaching a project's entity tag to a note links that note to the project.
- **Wild tags** (category = "wild"): user-created free-form tags for any \
purpose (e.g. "Idea", "Meeting", "Research", "Question", "Follow-up").
- **Topic tags**, **type tags**, etc.: other curated categories.

**EntityTag** junction table links any tag to any entity via (tag_id, \
target_type, target_id).

Tags are NOT used for status. Status is always a dedicated column on the \
entity (Activity, Project, Plan, Source).

### Knowledge Graph

Entities can be linked via triples (subject → predicate → object):
- subject_type, subject_id → predicate → object_type, object_id
- Available predicates: participated_in, mentioned_by, related_to, \
references, suggested_by, authored_by, assigned_to, documents, \
created_by, contributes_to
- Custom predicates can also be defined by the user.

### Active Context

The "active context" is the set of entities with is_active = true. It \
represents what the user is currently focused on and is used to scope \
queries, auto-tag new entities, and provide relevant suggestions.
"""

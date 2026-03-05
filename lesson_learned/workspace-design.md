# Workspace Design — Discussion Summary

## The Problem

WellBegun's current interface is comprehensive but complicated. Too many panels, too many toggles, and the user has to mentally map which panels matter for their current work. The focus selection flow (Dashboard Home > pick projects > pick activities > "Let's Begin") is not smooth — it forces a Project > Activity hierarchy that doesn't match how people actually think about starting work.

## The Workspace Concept

A **workspace** is a named, persistent context that captures a task from beginning to end. It complements the current panel-based layout with a focused environment containing only the entities the user is working with.

### What a workspace is

- A **named set of entity references** — what the user is currently working with
- An **event timeline** — what happened while this workspace was active (entities created, modified, completed, added, removed)
- A **persistent context** — survives sessions, can be resumed with one click

### What a workspace is NOT

- Not a copy of entities — entities are shared, the workspace is a view
- Not a folder/container — it's a working context with history
- Not a mandatory gate — the user can skip directly to the workspace and use search

## Entity Ownership

All entities are **shared** across workspaces. No entity type is workspace-owned.

| Entity | Shared | Reasoning |
|--------|--------|-----------|
| Project | Yes | Large endeavors that multiple workspaces can serve |
| Plan | Yes | Can be referenced from different contexts |
| Activity | Yes | Tasks exist globally, may be relevant in multiple contexts |
| Note | Yes | Knowledge persists across contexts |
| Source | Yes | Reference material, used across contexts |
| Actor | Yes | People don't belong to one workspace |
| Log | Yes | Shared entity, but workspace context is captured via the event timeline |
| Collection | Yes | Organizational containers for shared entities |

The **event timeline** handles attribution. Instead of asking "does this log belong to workspace A or B?", the system records "this log was created while workspace A was active." The workspace knows what happened in it without owning the entities.

## Interface

The workspace has a single primary interface: the **knowledge graph**, augmented with a collapsable markdown editor, entity action buttons, and query panel to add entities to the workspace from the database.

### Why graph-first

- The graph already shows every entity and its relationships
- Card panels were a redundant way to browse what the graph already shows (lists vs nodes)
- For a workspace capturing a task from beginning to end, the graph tells the story spatially: the plan at the center, activities branching off, sources and notes clustering around the activities they support

### Challenges with graph-only

- **Bulk operations**: Scanning 15 activities and checking off 5 is fast in a list, slow in a graph
- **Information density**: A card shows title, status, description, tags in a compact rectangle. A graph node shows a label.
- **Structured entity creation**: Forms with fields are more direct than parsing markdown

### Possible mitigation

Graph nodes that **expand inline** into mini-cards. Double click a plan node and it expands to show its activities as a checklist right there. Double click a source and see title, author, status. The graph becomes a **spatial card view** — cards positioned by relationship rather than by entity type. An edit button on the expanded view would allow entity editing

## Workspace Population

### Auto-expansion rules

When the user adds an entity to the workspace, related entities are pulled in automatically (one level deep only):

| Added entity | Auto-expands to |
|---|---|
| Plan | Its activities (FK), collection members (sources/actors), role notes |
| Project | Its active/in-progress activities only |
| Activity | Its source (if any) |
| Collection | Its member items |
| Source, Actor, Note, Log | Nothing |

Deeper connections (source's author, activity's log) are NOT auto-expanded. The user pulls those in manually via search.
The number of not displayed connections will be displayes as a small number in the top right corner of a card. When double clicking on the number, the quey panel will automatically load all the entities connected to that entity and not shown in the graph.

### Home screen as workspace launcher

The Home screen becomes a workspace launcher with three tiers:

1. **Recent workspaces** — Named workspaces sorted by last opened, one click to resume. Each shows a summary (pending count, item count). Covers ~60% of sessions.
2. **Suggested workspaces** — Data-driven suggestions derived from the user's actual data: plans with overdue activities, sources marked "reading", stale in-progress items. Each suggestion is a pre-populated workspace snapshot.
3. **New workspace** — Creates an empty named workspace, populated via search.

The Home screen will keep its essential, mission control/dashboard style.

### In-workspace search

Always available. The user queries across all entities and adds results to the workspace. Also where entity creation happens. The workspace is never locked — entities can be added or removed at any time.

### Interactions with other tabs

In the other tabs, when multiple entities are selected, a pop up menu appears with options.
This menu will show another option: "Add to workspace". At click, the user will be asked to select an existing workspace or to create a new one. The selected entities, and their first connection, will be added to the selected workspace.

## Multiple Workspaces

- Only **one workspace is active** at a time. 
- The active workspace defines: what's shown, what new entities get linked to, what the context bar reflects
- Multitasking = **fast switching** between workspaces, not simultaneous views
- Workspaces are never auto-cleaned — the user archives or closes them when done
- A "clean up" action can remove completed/archived entities

## Entity Creation Inside a Workspace

- Creating an entity inside the workspace **auto-adds it** to the workspace
- The entity gets **auto-tagged** with the workspace's active context (plans, projects in the workspace)
- If the workspace contains a plan and the user creates an activity, it could auto-link to the plan (offer as quick action)

## Event Timeline

Every workspace action is recorded:

- Entity added/removed from workspace
- Entity created (with auto-add)
- Entity modified (status changed, content edited)
- Workspace opened/switched to

This gives:
- **Reconstruction** — Replay what a work session looked like
- **Attribution** — "This note was written during the Research workspace on Tuesday"
- **Progress tracking** — "4 activities completed in this workspace this week"
- **Narrative** — The timeline IS the story of the work

## Meetings

Meetings are **not a new entity type**. They are a usage pattern that emerges from existing entities:

- A **Activity** anchors the meeting (temporal event with location)
- **Actors** attend
- **Notes** capture decisions and content
- **Activities** are created as follow-ups

The workspace event timeline captures the temporal clustering — entities created in a short window with specific actors present. The graph shows the log node connected to actors, notes, and activities.

## Data Model (proposed)

```
Workspace
  - id
  - name
  - created_at
  - last_opened_at

WorkspaceItem
  - workspace_id
  - entity_type
  - entity_id

WorkspaceEvent
  - workspace_id
  - timestamp
  - event_type (added, removed, created, modified, opened, switched)
  - entity_type
  - entity_id
  - metadata (JSON, optional details)
```

## Key Design Principles

1. **O(1) clicks for the common case** — Resume last workspace or accept suggestion. Elaborate selection is for the exploratory 20%.
2. **The workspace is a place, not a filter** — The event timeline makes it feel like a place you return to, not a search result.
3. **Entities are shared, context is scoped** — No ownership complexity. The workspace curates, it doesn't contain.
4. **The graph is the interface** — Spatial relationships replace categorized lists.
5. **Never auto-remove** — The user controls what's in the workspace. Offer cleanup, don't force it.

# WellBegun vs Obsidian: Comparison, Identity, and Workspace Editor Design

**Date**: 2026-03-08

---

## 1. Architectural Comparison

WellBegun and Obsidian approach knowledge management from opposite ends:

| Aspect | WellBegun | Obsidian |
|--------|-----------|----------|
| **Philosophy** | Schema-first: typed entities with defined fields | Content-first: everything is a markdown file, structure emerges from links and metadata |
| **Storage** | SQLite relational database (`wellbegun.db`) | Plain `.md` files on the filesystem |
| **Relationships** | Explicit knowledge triples (subject → predicate → object) with typed predicates | Implicit via `[[wikilinks]]` and backlinks; untyped by default |
| **Architecture** | Client-server (FastAPI + SvelteKit) | Desktop app (Electron), local-first |
| **Extensibility** | Monolithic, developer-extended | Plugin ecosystem (2700+ community plugins) |

## 2. Where Obsidian Wins (Gaps in WellBegun)

- **Frictionless linking**: `[[wikilinks]]` let you link notes while writing. WellBegun requires creating knowledge triples separately.
- **Backlinks pane**: auto-shows "what links here" contextually while editing.
- **Data portability**: plain Markdown files are universally readable.
- **Plugin ecosystem**: 2700+ plugins cover almost any workflow.
- **Mobile native apps**: proper iOS/Android apps.
- **Search power**: regex, boolean operators, path filters, property queries.
- **Version history**: automatic file recovery snapshots.
- **Import pipeline**: from Notion, Evernote, Bear, Roam, etc.
- **Daily notes automation**: auto-create from templates on launch.

## 3. Where WellBegun Wins (Gaps in Obsidian)

- **Interactive graph**: create entities, drag-connect nodes, edit fields, change predicates — all on the canvas. Obsidian's graph is read-only visualization.
- **Typed entities**: the system knows what a Project, Activity, Source, Actor IS. Obsidian treats everything as a note.
- **Typed relationships**: knowledge triples with named predicates vs. Obsidian's untyped links.
- **Structured planning**: Plan entity with motivation, outcome, goal, date ranges, nested activities.
- **Collections with status workflows**: e.g., reading list with to-read/reading/read progression.
- **Activity tracking**: duration, outcome, status, linking to plans and logs.
- **AI with data context**: Coffee Table has RAG over actual typed entities and graph relationships.
- **Bulk entity creation**: Notepad syntax for creating multiple typed entities at once.

Notable: several of the most popular Obsidian plugins (Breadcrumbs for typed links, DB Folder for database views, Projects for structured data) are trying to recreate capabilities WellBegun has natively.

## 4. Most Significant Obsidian Plugins

### Data & Querying
- **Dataview**: SQL-like query engine over vault metadata. Most downloaded plugin.
- **DB Folder**: Notion-like database tables from folders with inline editing.
- **Obsidian Projects**: Multiple views (Table, Board, Calendar, Gallery) over notes.

### Task & Project Management
- **Tasks**: Track tasks across vault with due dates, recurring tasks, priority, queries.
- **Kanban**: Markdown-backed Kanban boards with drag-and-drop columns.
- **CardBoard**: Auto-groups tasks by due date or tags into Kanban boards.

### Templates & Automation
- **Templater**: Dynamic templates with logic, dates, prompts, JavaScript.
- **QuickAdd**: Quick capture — create notes, add to files, run macros from a hotkey.
- **Periodic Notes**: Auto-create daily/weekly/monthly/yearly notes from templates.

### Graph & Relationships
- **Breadcrumbs**: Typed links between notes (parent/child, related, sequence). Hierarchy visualization.
- **Graph Link Types**: Color-code graph edges by link type.
- **Excalidraw**: Full drawing/diagramming embedded in Obsidian.

### Writing & Navigation
- **Longform**: Multi-scene writing projects with compilation.
- **Quick Switcher++**: Enhanced Cmd+O — search by headings, symbols, bookmarks.
- **Calendar**: Visual calendar sidebar, click date to open/create daily note.
- **Autocomplete**: Suggests `[[links]]` as you type.

### Learning
- **Spaced Repetition**: Flashcards with cloze deletions, scheduled by forgetting curve.

## 5. Strategic Position: Is WellBegun Worth Developing?

**WellBegun is not reinventing the wheel.** The wheel is different.

Obsidian's philosophy is "dump first, structure later (maybe)." WellBegun's philosophy is "think first, then record." The structured entity model forces intentionality — creating an Activity with duration, outcome, and linking it to a Plan is an act of curation.

In the AI era, curated content is fundamental. LLMs generate text but can't judge what's worth keeping. WellBegun was conceived as a **data entry point** — a place where you archive what's worth preserving. The structured data model is the curation protocol.

### Where to invest
- **Double down on**: interactive graph editing, typed entities/relationships, structured planning, AI with semantic context, the workspace editor.
- **Don't build**: a general-purpose markdown editor, a plugin system, mobile native apps, spaced repetition, calendar widgets — these are commodity features.
- **Consider**: Obsidian interop (import/export markdown with frontmatter) rather than competition.

### On local-first and AI
The local-first constraint is a feature, not a limitation. Local LLMs (Ollama) can handle simple tasks (tag suggestions, summarization) but reliable entity extraction requires strong API models. The middle ground:
1. **Manual** (current) — user creates structured entities explicitly.
2. **Suggested** (achievable locally) — heuristic-based suggestions ("this looks like an Activity"), no LLM needed.
3. **AI-assisted** (optional) — API model for full entity extraction, opt-in toggle.

## 6. Workspace Editor Design

### Core Concept
Add a text editor pane to the Workspace tab, alongside the existing graph view. The editor can operate in two modes:
- **Generic content**: long-lived document (meeting notes, research, drafts)
- **Daily log**: creates a Log entity with date context and metadata

### The File Entity
A new entity type that acts as **metadata + pointer** to a markdown file on disk:

```
File entity (in SQLite)          Markdown file (on disk)
+-----------------------+        +------------------------+
| id, title, description|        |                        |
| file_path (pointer)   | -----> | # Actual markdown      |
| version               |        | content lives here     |
| tags, triples         |        |                        |
+-----------------------+        +------------------------+
```

Benefits:
- Markdown files are portable, readable outside WellBegun, version-controllable with git
- The entity handles WellBegun integration (tags, triples, graph, collections)
- Files stored in a `files/` directory next to `wellbegun.db`

### Three Mechanisms for Entity Creation in the Editor

#### 1. `[[wikilinks]]` — Reference existing entities inline
- Typing `[[` opens autocomplete searching all entity types
- Creates knowledge triples: File → mentions → Entity
- Referenced entities appear on the graph automatically

#### 2. `@entity` blocks — Create full entities with all fields
- Reuses existing Notepad parser syntax
- Python-style indentation scoping
- Entity appears on graph immediately upon creation

#### 3. Highlight-and-tag — Extract text into entities (preferred for inline)
- User writes naturally, no special syntax
- Highlights a passage, right-clicks or uses toolbar
- Context menu offers tag/entity type options
- A new entity is created with sensible defaults:
  - `content`: the highlighted text
  - `title`: auto-generated (e.g., "Definition — [first words]")
  - `tags`: the selected tag
  - Knowledge triple: File → contains → Entity
- The highlighted text gets a subtle visual indicator (underline/background)
- Clicking the highlight opens the entity panel for further curation
- **Original text is never modified**

This approach was chosen over inline syntax (e.g., `<door> @definition`) because:
- Zero syntax to learn
- Writing flow is uninterrupted
- Curation happens after creation (defaults first, refine later)
- The text stays clean

### Annotation Data Model

```
FileAnnotation (new model)
+-- file_id         -> File entity
+-- entity_type     -> "note", "actor", etc.
+-- entity_id       -> the created entity
+-- start_offset    -> character position in file
+-- end_offset      -> character position in file
+-- source_text     -> snapshot of highlighted text (for re-anchoring)
```

### Real-time Graph Sync
- Frontend parses the document live for graph preview (debounced, ~500ms after last keystroke)
- Backend reconciles entities on save
- Avoids creating half-finished entities on every keystroke

### Layout
```
+--------------------------------------------------+
| Workspace: "Sprint Planning"                 [+] |
+------------------------+-------------------------+
|                        |                         |
|   TEXT EDITOR          |   GRAPH VIEW            |
|                        |   (entities from text   |
|   Freeform markdown    |    appear here in       |
|   with [[links]],      |    real time)           |
|   @blocks, and         |                         |
|   highlighted regions  |   [Entity]--[Entity]    |
|                        |                         |
+------------------------+-------------------------+
```

---

## 7. Implementation Specifications

The following is a detailed list of implementation items to feed back for development:

### Phase 1: File Entity (Backend)

1. **Create `File` model** (`src/wellbegun/models/file.py`):
   - Fields: `id`, `title`, `description`, `file_path` (relative to files/ directory), `version` (integer, starts at 1), `created_at`, `updated_at`
   - Inherits from the polymorphic Entity base class (like Note, Log, etc.)
   - Supports tags and knowledge triples via existing mechanisms

2. **Create `FileAnnotation` model** (`src/wellbegun/models/file_annotation.py`):
   - Fields: `id`, `file_id` (FK to File), `entity_type`, `entity_id`, `start_offset` (int), `end_offset` (int), `source_text` (text snapshot), `created_at`
   - Unique constraint: `(file_id, entity_type, entity_id)`

3. **Create Pydantic schemas** (`src/wellbegun/schemas/file.py`):
   - `FileCreate`: title, description (optional)
   - `FileUpdate`: title, description, version
   - `FileRead`: all fields + tags + annotations
   - `FileAnnotationCreate`: entity_type, entity_id, start_offset, end_offset, source_text
   - `FileAnnotationRead`: all fields

4. **Create router** (`src/wellbegun/routers/files.py`):
   - `POST /files` — create File entity + empty `.md` file on disk in `files/` directory
   - `GET /files/{id}` — return File entity metadata
   - `GET /files/{id}/content` — read and return the markdown file content from disk
   - `PUT /files/{id}/content` — write markdown content to disk, increment version
   - `PUT /files/{id}` — update File entity metadata (title, description)
   - `DELETE /files/{id}` — delete entity + file on disk
   - `GET /files/{id}/annotations` — list all annotations for this file
   - `POST /files/{id}/annotations` — create annotation (link highlighted text to entity)
   - `DELETE /files/{id}/annotations/{annotation_id}` — remove annotation

5. **Create service** (`src/wellbegun/services/file_service.py`):
   - File CRUD operations
   - Disk I/O: create/read/write/delete `.md` files in `files/` directory
   - Annotation management
   - Version incrementing on content save

6. **Create `files/` directory** at project root alongside `wellbegun.db`

### Phase 2: Workspace Split View (Frontend)

7. **Create `WorkspaceEditor.svelte`** component:
   - Markdown text editor pane (use a textarea or lightweight editor library)
   - Two mode toggle: "Document" / "Daily Log"
   - In Daily Log mode, show Log-specific fields (mood, location, weather, day_theme) in a compact header
   - Auto-save with debounce (save content to backend every 2 seconds of inactivity)
   - File selector/creator in the toolbar

8. **Modify `WorkspaceTab.svelte`**:
   - Add split view layout: editor (left) + graph (right)
   - Resizable divider between panes
   - Toggle to show/hide editor pane
   - When editor is hidden, full-width graph (current behavior)

9. **Create frontend API functions** (`frontend/src/lib/api/files.ts`):
   - `createFile(data)`, `getFile(id)`, `updateFile(id, data)`, `deleteFile(id)`
   - `getFileContent(id)`, `saveFileContent(id, content)`
   - `getAnnotations(fileId)`, `createAnnotation(fileId, data)`, `deleteAnnotation(fileId, annotationId)`

10. **Create Svelte store** (`frontend/src/lib/stores/files.ts`):
    - `files` store, `loadFiles()`, `activeFile`

### Phase 3: `[[Wikilink]]` Autocomplete

11. **Add autocomplete popup component** (`frontend/src/lib/components/editor/EntityAutocomplete.svelte`):
    - Triggered when user types `[[`
    - Searches across all entity types via existing search API
    - Shows results grouped by entity type with icons/colors
    - On selection: inserts `[[Entity Title]]` in text + creates knowledge triple (File → mentions → Entity)
    - Dismissed on `Escape` or clicking outside

12. **Create knowledge triples on link insertion**:
    - When a `[[wikilink]]` is inserted, call `createTriple()` with subject=File, predicate="mentions", object=selected entity
    - Parse existing `[[...]]` in document content to maintain triple consistency on save

### Phase 4: `@entity` Block Parsing in Editor

13. **Adapt Notepad parser for embedded blocks**:
    - Detect `@entity_type` markers within freeform prose
    - Use indentation (Python-style) to determine block scope
    - Parse fields within the indented block using existing Notepad field parsing
    - On save: create/update entities from parsed blocks
    - On graph: show parsed entities as nodes in real-time (debounced)

14. **Visual block indicators in editor**:
    - Syntax highlighting for `@entity_type` markers
    - Subtle background color on indented block regions matching entity type colors

### Phase 5: Highlight-and-Tag

15. **Add selection context menu** (`frontend/src/lib/components/editor/SelectionMenu.svelte`):
    - Appears when user selects text in the editor
    - Shows two sections: "Create entity" (Note, Activity, Source, etc.) and "Tag as" (existing tags list)
    - On entity type selection: create entity with `content` = selected text, `title` = auto-generated, and tag from chosen tag
    - On tag selection: create a Note entity tagged with the selected tag
    - Create a FileAnnotation linking the text region to the new entity
    - Create knowledge triple: File → contains → new Entity

16. **Render annotation highlights in editor**:
    - Overlay colored highlights on annotated text regions based on entity type colors
    - Click on highlight to open EntityDetailPanel for that entity
    - Handle position drift: if document is edited above an annotation, recalculate offsets using `source_text` for re-anchoring

17. **Default title generation**:
    - For tag-based creation: `"{Tag name} — {first 5 words of selected text}..."`
    - For entity-type creation: `"{Entity type} — {first 5 words}..."`
    - User can immediately edit in the EntityDetailPanel

### Phase 6: Real-time Graph Sync

18. **Debounced document parser**:
    - On editor content change, debounce 500ms, then:
      - Parse all `[[wikilinks]]` → resolve to entities → show as nodes
      - Parse all `@entity` blocks → show as pending/draft nodes (different visual style until saved)
      - Show all FileAnnotation entities as nodes
    - Update graph node positions using existing auto-layout

19. **Graph-to-editor navigation**:
    - Clicking a node in the graph that originated from the document should scroll the editor to the relevant `[[link]]`, `@block`, or highlighted region

### Phase 7: Daily Log Mode

20. **Log mode behavior**:
    - When "Daily Log" mode is selected, create or find today's Log entity
    - Associate the File entity with the Log via knowledge triple (Log → has_document → File)
    - Show Log metadata fields (mood, location, weather, day_theme) as an editable header above the editor
    - On save: update both the File content on disk and the Log entity metadata
    - Auto-create on workspace open if daily log toggle is enabled

21. **Log template system**:
    - Allow users to define a default daily log template (stored as a template `.md` file)
    - New daily logs are initialized with the template content
    - Template can include placeholders: `{{date}}`, `{{day_of_week}}`

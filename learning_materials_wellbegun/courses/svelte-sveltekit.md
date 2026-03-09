# Svelte & SvelteKit

> **Category**: framework | **Difficulty**: beginner | **Time**: ~30 min
> **Prerequisites**: TypeScript Essentials

## Overview

If Python compiles your `.py` source to bytecode for the interpreter, Svelte compiles your `.svelte` components to efficient JavaScript at build time. There is no virtual DOM and no runtime framework shipped to the browser -- just small, fast JavaScript. Think of `.svelte` files as templates that get compiled into code, much like Jinja2 templates but with built-in reactivity.

SvelteKit is to Svelte what Django is to Python -- it adds routing, server-side rendering, and a project structure on top of the core component framework.

**Key takeaways:**
- Svelte is a compiler, not a runtime library -- components compile to efficient JavaScript
- Each `.svelte` file has three sections: `<script>` (logic), template (HTML), and optional `<style>` (CSS)
- Reactivity is built into the language -- variables update the DOM automatically
- SvelteKit adds file-based routing, SSR, and project structure on top of Svelte

---

## Core Concepts

### 1. Component Structure

Every `.svelte` file is a self-contained component with up to three sections. In Python terms, imagine if a single file held your class definition, its HTML template, and its stylesheet all together.

```svelte
<script lang="ts">
    // Logic goes here: imports, variables, functions
    import { onMount } from 'svelte';
    let count = $state(0);
</script>

<!-- Template (HTML) goes here -->
<button onclick={() => count++}>
    Clicked {count} times
</button>

<style>
    /* Scoped CSS -- only affects this component */
    button { background: #5c7a99; color: white; }
</style>
```

In WellBegun, `KnowledgeGraph.svelte` is a large example of this pattern. Its script block (lines 1-1716) imports from stores, API modules, and other components, then declares reactive state. The template (lines 1718-1940+) renders the graph UI. The style block at the end scopes CSS to this component only.

```typescript
// From frontend/src/lib/components/graph/KnowledgeGraph.svelte:1-13
<script lang="ts">
    import { onMount, untrack } from 'svelte';
    import type { KnowledgeTriple, BoardNode } from '$lib/types';
    import { boardNodes, triples, loadBoard, loadTriples, hiddenGraphEntities, graphFilterPanelOpen } from '$lib/stores/knowledgeGraph';
    import { focusSelection, isFocusActive } from '$lib/stores/focus';
    import { projects } from '$lib/stores/projects';
    import { logs } from '$lib/stores/logs';
    import { notes } from '$lib/stores/notes';
    import { activities } from '$lib/stores/activities';
    import { sources } from '$lib/stores/sources';
    import { actors } from '$lib/stores/actors';
    import { plans } from '$lib/stores/plans';
    import { collections } from '$lib/stores/collections';
```

### 2. Reactivity (Svelte 5 Runes)

WellBegun uses Svelte 5, which introduces "runes" -- special compiler directives that start with `$`. If you are familiar with Python's `@property` decorator or reactive frameworks like RxPY, the concept is similar: you declare variables that automatically trigger UI updates when they change.

**`$state()` -- Reactive Variables**

```typescript
// From frontend/src/lib/components/graph/KnowledgeGraph.svelte:88-92
let panX = $state(0);
let panY = $state(0);
let zoom = $state(1);
let canvasEl: HTMLDivElement | undefined = $state();
let viewportEl: HTMLDivElement | undefined = $state();
```

In Python terms, `$state()` is like making every variable a property with automatic change notification. When `zoom` changes, every piece of template that references `zoom` re-renders automatically.

**`$derived` -- Computed Values**

```typescript
// From frontend/src/lib/components/graph/KnowledgeGraph.svelte:114-120
let selectionCount = $derived(selectedCards.size);
let selectedEntities = $derived.by(() =>
    [...selectedCards].map(key => {
        const [type, idStr] = key.split(':');
        return { type, id: Number(idStr) };
    })
);
```

`$derived` is like Python's `@property` -- a value computed from other reactive values that stays in sync automatically. `$derived.by()` is the same thing for more complex expressions that need a function body.

**`$effect()` -- Side Effects**

```typescript
// From frontend/src/lib/components/graph/KnowledgeGraph.svelte:137-148
$effect(() => {
    // Re-run when board nodes or tag version changes
    const _nodes = $boardNodes;
    const _version = $entityTagsVersion;
    (async () => {
        try {
            nodeEntityTags = await getAllEntityTagsBulk();
        } catch {
            nodeEntityTags = {};
        }
    })();
});
```

`$effect()` runs a function whenever its reactive dependencies change -- like a "watcher." Think of it as an observer that automatically re-executes when any `$state` or `$derived` value it reads is updated. In the example above, it re-fetches entity tags whenever board nodes or the tag version change.

**`$props()` -- Component Inputs**

```typescript
// From frontend/src/routes/+layout.svelte:59
let { children } = $props();
```

`$props()` declares the inputs a component receives from its parent, similar to `__init__` parameters on a Python class.

### 3. Template Syntax

Svelte's template syntax lives directly in the HTML portion of a `.svelte` file. If you have used Jinja2, the logic blocks will feel familiar -- just with slightly different syntax.

**`{#each ...}` -- Looping (like Jinja2's `{% for %}` or Python's `for`)**

```svelte
<!-- From frontend/src/lib/components/graph/KnowledgeGraph.svelte:1792-1793 -->
{#each standaloneNodes as node (`${node.entity_type}:${node.entity_id}`)}
    {@const nodeData = getEntityData(node.entity_type, node.entity_id)}
    <!-- render each card -->
{/each}
```

The parenthesized key expression `` (`${node.entity_type}:${node.entity_id}`) `` is a unique identifier for each item -- it helps Svelte efficiently update the DOM when the list changes, similar to React's `key` prop.

**`{#if ...}` / `{:else if ...}` / `{:else}` -- Conditionals**

```svelte
<!-- From frontend/src/routes/+layout.svelte:513-533 -->
{#if $activeTab === 'dashboard'}
    <DashboardHome />
{:else if $activeTab === 'input'}
    {@render children()}
{:else if $activeTab === 'notepad'}
    <NotepadTab />
{:else if $activeTab === 'graph'}
    <KnowledgeGraph />
{:else if $activeTab === 'workspace'}
    <WorkspaceTab />
{/if}
```

This is the tab-switching logic in the main layout. Each `{:else if}` checks which tab is active and renders the matching component.

**`{@const ...}` -- Local Declarations Inside Blocks**

```svelte
<!-- From frontend/src/lib/components/graph/KnowledgeGraph.svelte:1826-1830 -->
{#if selectionRect}
    {@const left = Math.min(selectionRect.startX, selectionRect.currentX)}
    {@const top = Math.min(selectionRect.startY, selectionRect.currentY)}
    {@const width = Math.abs(selectionRect.currentX - selectionRect.startX)}
    {@const height = Math.abs(selectionRect.currentY - selectionRect.startY)}
    <!-- render marquee rectangle using these computed values -->
{/if}
```

`{@const}` declares a local variable inside a template block -- useful for intermediate calculations you do not want to clutter the script section with.

**Curly-Brace Expressions (like Python f-strings)**

```svelte
<!-- From frontend/src/lib/components/graph/KnowledgeGraph.svelte:1752 -->
<div style:transform="translate({panX}px, {panY}px) scale({zoom})">
```

Any JavaScript expression inside `{}` is evaluated and inserted into the template, much like `{variable}` in Python f-strings.

### 4. Component Props and Events

Components communicate in two directions: **props** flow data down (parent to child), and **event callbacks** flow signals up (child to parent).

```svelte
<!-- From frontend/src/lib/components/graph/KnowledgeGraph.svelte:1719-1733 -->
<GraphToolbar
    {zoom}
    filterOpen={filterPanelOpen}
    editorOpen={graphEditorOpen}
    onAddEntity={handleAddEntity}
    onZoomIn={zoomIn}
    onZoomOut={zoomOut}
    onZoomFit={zoomFit}
    onToggleFilter={toggleFilterPanel}
    onToggleEditor={() => graphEditorOpen = !graphEditorOpen}
    onSwitchToCards={() => activeTab.set('input')}
    onScreenshot={handleScreenshot}
    selectActive={selectMode}
    onToggleSelect={() => (selectMode = !selectMode)}
/>
```

Here `{zoom}` is shorthand for `zoom={zoom}` -- when the prop name matches the variable name, you can abbreviate it. Props like `onZoomIn` pass callback functions that the child component calls when the user clicks a button.

**DOM Event Handlers**

Svelte 5 uses lowercase DOM event attributes directly:

```svelte
<!-- From frontend/src/lib/components/graph/KnowledgeGraph.svelte:1741-1748 -->
<div
    class="viewport"
    bind:this={viewportEl}
    onpointerdown={handleCanvasPointerDown}
    onpointermove={handlePointerMove}
    onpointerup={handlePointerUp}
    onwheel={handleWheel}
>
```

`bind:this` captures a reference to the DOM element (like Python's `self.element = ...`). The `on*` attributes attach event handler functions directly.

### 5. SvelteKit File-Based Routing

SvelteKit uses the filesystem to define routes. Each `+page.svelte` in the `src/routes/` directory becomes a URL path:

```
frontend/src/routes/
  +layout.svelte    --> wraps every page (navbar, toolbar, global state loading)
  +page.svelte      --> the "/" root page (Cards panel grid)
```

WellBegun currently uses a single-page architecture with tab-based navigation. The `+layout.svelte` file (lines 1-833) handles all global setup: loading stores on mount, rendering the tab bar, and conditionally showing the active tab's component. The `+page.svelte` file (lines 1-209) renders the Cards panel grid, which is the default tab content.

The layout loads all application data on startup:

```typescript
// From frontend/src/routes/+layout.svelte:281-317
onMount(async () => {
    // On a fresh session (new tab/window), deactivate everything and clear tag memory
    if (freshSession) {
        clearAllLastUsedTags();
        await Promise.allSettled([
            deactivateAllProjects(),
            deactivateAllActivities()
        ]);
    }

    Promise.allSettled([
        loadProjects(),
        loadLogs(),
        loadNotes(),
        loadSources(),
        loadActors(),
        loadActivities(),
        loadPlans(),
        loadCollections(),
        loadCategories(),
        loadTags(),
        loadWorkspaces()
    ]).then((results) => {
        // ...
    });
});
```

`onMount` runs once after the component is first rendered in the browser -- like Python's `__init__` but for the DOM lifecycle.

### 6. The Store & API Pattern

WellBegun uses a clear three-layer data flow: **Stores** hold shared state, **API functions** handle HTTP calls, and **Components** read from stores and trigger API actions.

**Layer 1: The Store** -- A writable store is like a shared global variable with built-in reactivity.

```typescript
// From frontend/src/lib/stores/collections.ts:1-13
import { writable } from 'svelte/store';
import type { Collection } from '$lib/types';
import { getCollections } from '$lib/api/collections';

export const collections = writable<Collection[]>([]);

export async function loadCollections(categoryId?: number) {
    try {
        collections.set(await getCollections(categoryId));
    } catch (e) {
        console.warn('Failed to load collections:', e);
    }
}
```

`writable<Collection[]>([])` creates a reactive container initialized with an empty array. `collections.set(...)` replaces its value, automatically updating any component that reads it.

**Layer 2: The API Client** -- Pure async functions that call the backend.

```typescript
// From frontend/src/lib/api/collections.ts:5-9
export async function getCollections(categoryId?: number): Promise<Collection[]> {
    const url = categoryId != null ? `${BASE}/?category_id=${categoryId}` : `${BASE}/`;
    const res = await fetch(url);
    return res.json();
}
```

**Layer 3: The Component** -- Reads stores with the `$` prefix and calls load functions.

```svelte
<!-- In a component's <script> block -->
<script lang="ts">
    import { collections } from '$lib/stores/collections';
    import { loadCollections } from '$lib/stores/collections';
</script>

<!-- In the template, $collections auto-subscribes to the store -->
{#each $collections as collection}
    <p>{collection.title}</p>
{/each}
```

The `$` prefix before a store name is Svelte's auto-subscription syntax: `$collections` always holds the current value of the `collections` store, and the template re-renders whenever it changes.

**More Complex Stores** use `derived` for computed values:

```typescript
// From frontend/src/lib/stores/workspaces.ts:1-7
import { writable, derived } from 'svelte/store';
import type { Workspace, WorkspaceDetail } from '$lib/types';
import { getWorkspaces, getWorkspace, openWorkspace } from '$lib/api/workspaces';

export const workspaces = writable<Workspace[]>([]);
export const activeWorkspace = writable<WorkspaceDetail | null>(null);
export const activeWorkspaceId = derived(activeWorkspace, ($ws) => $ws?.id ?? null);
```

`derived` creates a read-only store whose value is computed from another store -- like a `$derived` rune, but at the module level for shared state.

---

## In This Project

WellBegun's frontend is a SvelteKit application in the `frontend/` directory. Here is the architecture:

```
frontend/src/
  routes/
    +layout.svelte          App shell: toolbar, tab bar, global data loading (834 lines)
    +page.svelte            Cards tab: panel grid with drag-and-drop (209 lines)
  lib/
    types.ts                TypeScript interfaces for all entities (270 lines)
    components/
      graph/
        KnowledgeGraph.svelte   Interactive knowledge graph canvas (1940+ lines)
        GraphCard.svelte        Individual entity cards on the graph
        GraphConnections.svelte SVG connection lines between nodes
        GraphToolbar.svelte     Graph view toolbar controls
      panels/                   Card-based panels (ProjectPanel, LogPanel, etc.)
      forms/                    Entity edit forms (ProjectForm, NoteForm, etc.)
      shared/                   Reusable components (Modal, TagInput, etc.)
      workspace/                Workspace management tab
      notepad/                  Notepad text editing tab
    stores/
      collections.ts        writable store + load function (13 lines)
      workspaces.ts         writable + derived stores (45 lines)
      projects.ts           project store and loaders
      logs.ts, notes.ts, activities.ts, sources.ts, actors.ts, plans.ts
      knowledgeGraph.ts     graph board nodes and triples
      activeTab.ts          current tab selection
      panels.ts             panel visibility and layout
      tags.ts               tag store and management
      dateFilter.ts         shared date/tag/active filtering
      (30 store files total)
    api/
      collections.ts        fetch-based API client (83 lines)
      workspaces.ts         workspace API calls
      projects.ts, logs.ts, notes.ts, activities.ts, sources.ts, actors.ts, plans.ts
      knowledge.ts          knowledge graph API
      tags.ts               tag management API
      search.ts             search API
      (15 API files total)
```

The data flow for every entity type follows the same pattern:
1. `lib/types.ts` defines the TypeScript interface (e.g., `Collection` at lines 213-224)
2. `lib/api/collections.ts` provides fetch functions (`getCollections`, `createCollection`, etc.)
3. `lib/stores/collections.ts` wraps a writable store and exposes `loadCollections()`
4. Components import the store and call load functions on mount or in response to user actions

---

## Guided Examples

### Example 1: Data Flow -- From Backend to UI

Let's trace how collection data flows from the server to the screen.

**Step 1: The type is defined** in `frontend/src/lib/types.ts`:

```typescript
// From frontend/src/lib/types.ts:213-224
export interface Collection {
    id: number;
    entity_type: string;
    title: string;
    description: string | null;
    category_id: number;
    is_active: boolean;
    is_archived: boolean;
    created_at: string;
    updated_at: string;
    items: CollectionItem[];
}
```

**Step 2: The API function fetches data** from `frontend/src/lib/api/collections.ts`:

```typescript
// From frontend/src/lib/api/collections.ts:3-9
const BASE = '/api/collections';

export async function getCollections(categoryId?: number): Promise<Collection[]> {
    const url = categoryId != null ? `${BASE}/?category_id=${categoryId}` : `${BASE}/`;
    const res = await fetch(url);
    return res.json();
}
```

**Step 3: The store wraps and shares the data** from `frontend/src/lib/stores/collections.ts`:

```typescript
// From frontend/src/lib/stores/collections.ts:1-13
import { writable } from 'svelte/store';
import type { Collection } from '$lib/types';
import { getCollections } from '$lib/api/collections';

export const collections = writable<Collection[]>([]);

export async function loadCollections(categoryId?: number) {
    try {
        collections.set(await getCollections(categoryId));
    } catch (e) {
        console.warn('Failed to load collections:', e);
    }
}
```

**Step 4: The layout loads data on startup** from `frontend/src/routes/+layout.svelte`:

```typescript
// From frontend/src/routes/+layout.svelte:291-302
Promise.allSettled([
    loadProjects(),
    loadLogs(),
    loadNotes(),
    loadSources(),
    loadActors(),
    loadActivities(),
    loadPlans(),
    loadCollections(),   // <-- triggers the whole chain
    loadCategories(),
    loadTags(),
    loadWorkspaces()
]);
```

**Step 5: Components read the store** -- any component that imports `collections` and uses `$collections` in its template will automatically display the latest data.

### Example 2: KnowledgeGraph.svelte -- A Complex Component

The `KnowledgeGraph.svelte` component shows how a large component integrates multiple stores and API modules.

**Imports from many stores** (lines 6-13):

```typescript
// From frontend/src/lib/components/graph/KnowledgeGraph.svelte:6-13
import { projects } from '$lib/stores/projects';
import { logs } from '$lib/stores/logs';
import { notes } from '$lib/stores/notes';
import { activities } from '$lib/stores/activities';
import { sources } from '$lib/stores/sources';
import { actors } from '$lib/stores/actors';
import { plans } from '$lib/stores/plans';
import { collections } from '$lib/stores/collections';
```

**Reactive state management** -- canvas position, zoom level, drag state, and selection are all reactive (lines 88-129):

```typescript
// From frontend/src/lib/components/graph/KnowledgeGraph.svelte:88-92
let panX = $state(0);
let panY = $state(0);
let zoom = $state(1);
```

**Derived filtering** -- the visible nodes are computed from board nodes plus all filter criteria (lines 276-307):

```typescript
// From frontend/src/lib/components/graph/KnowledgeGraph.svelte:276-307
let visibleNodes = $derived(
    $boardNodes.filter(n => {
        if (!isEntityVisible(n.entity_type, n.entity_id)) return false;
        if (hiddenByCollapse.has(`${n.entity_type}:${n.entity_id}`)) return false;
        const entityData = getEntityData(n.entity_type, n.entity_id);
        if (!entityData) return false;
        if (!$showArchived && entityData.is_archived) return false;
        // ... more filter checks
        return true;
    })
);
```

**Lifecycle initialization** with `onMount` (lines 1387-1390):

```typescript
// From frontend/src/lib/components/graph/KnowledgeGraph.svelte:1387-1390
onMount(() => {
    loadPredicates();
    populateAll().then(() => {
        Promise.allSettled([loadBoard(), loadTriples()]).then(async () => {
```

This pattern -- load data on mount, store it reactively, derive filtered views, render in the template -- is the core of every component in WellBegun.

---

## Exercises

### Exercise 1: Read a Store File

**Task**: Open `frontend/src/lib/stores/workspaces.ts` (45 lines). Identify the following:
1. Which stores are `writable` and which are `derived`?
2. What is `activeWorkspaceId` derived from, and what does it compute?
3. How does `setActiveWorkspace` coordinate multiple async operations?

<details>
<summary>Hint</summary>
Lines 5-7 declare the stores. `workspaces` and `activeWorkspace` are writable (they hold data you set directly). `activeWorkspaceId` is derived from `activeWorkspace` -- it extracts just the `.id` property (or null). `setActiveWorkspace` (lines 17-27) opens a workspace, fetches its detail, sets the store, and refreshes the list -- all in sequence with `await`.
</details>

### Exercise 2: Trace an Event Handler

**Task**: In `KnowledgeGraph.svelte`, the viewport div (line 1744) has `onpointerdown={handleCanvasPointerDown}`. Without reading the handler implementation, predict: what should happen when the user clicks and drags on the empty canvas background? What about clicking and dragging on a card?

<details>
<summary>Hint</summary>
Canvas background clicks should start panning (moving the entire view). Card clicks should start dragging that individual card. The handler likely checks whether the click target is a card or the background to decide which behavior to activate. Look at the state variables: `isPanning` (line 101) and `draggingCard` (line 100) suggest these two modes.
</details>

### Exercise 3: Modify Template Logic

**Task**: Look at the tab-switching logic in `+layout.svelte` (lines 513-533). If you wanted to add a new "Analytics" tab, what three things would you need to add?

<details>
<summary>Hint</summary>
1. A new `<button>` in the tab bar (around line 330) with `onclick={() => activeTab.set('analytics')}`.
2. A new `{:else if $activeTab === 'analytics'}` block (around line 532) that renders your `<AnalyticsTab />` component.
3. The actual `AnalyticsTab.svelte` component file in `lib/components/`.
</details>

---

## Knowledge Check

**Q1**: What are the three sections of a `.svelte` file?
- A) imports, exports, template
- B) script, template, style
- C) head, body, footer
- D) data, methods, render

<details>
<summary>Answer</summary>
**B) script, template, style** -- The `<script>` block contains logic, the template contains HTML markup, and the optional `<style>` block contains component-scoped CSS. You can see this structure in every `.svelte` file in the project.
</details>

**Q2**: What does `$state(0)` do in Svelte 5?
- A) Creates a constant with value 0
- B) Creates a reactive variable initialized to 0 that triggers UI updates when changed
- C) Fetches state from the server
- D) Declares a CSS variable

<details>
<summary>Answer</summary>
**B) Creates a reactive variable initialized to 0 that triggers UI updates when changed** -- `$state()` is a Svelte 5 rune. When the value changes, any template expression that references it automatically re-renders. See `KnowledgeGraph.svelte:88-90` where `panX`, `panY`, and `zoom` use this pattern.
</details>

**Q3**: In `$collections`, what does the `$` prefix do?
- A) It marks the variable as private
- B) It auto-subscribes to a Svelte store, providing the current value reactively
- C) It converts the value to a string
- D) It creates a new store

<details>
<summary>Answer</summary>
**B) It auto-subscribes to a Svelte store, providing the current value reactively** -- When you use `$storeName` in a Svelte component, the compiler sets up a subscription automatically. The value stays in sync, and the template re-renders when the store updates. See how `$collections`, `$projects`, etc. are used throughout `KnowledgeGraph.svelte`.
</details>

**Q4**: What is the role of `onMount` in a Svelte component?
- A) It runs before the component is created
- B) It runs once after the component is first rendered in the browser
- C) It runs on every state change
- D) It defines the component's template

<details>
<summary>Answer</summary>
**B) It runs once after the component is first rendered in the browser** -- `onMount` is a lifecycle function. In WellBegun, `+layout.svelte` uses `onMount` (line 281) to load all application data from the backend when the app first opens. `KnowledgeGraph.svelte` uses it (line 1387) to load graph data.
</details>

**Q5**: How does WellBegun's store pattern relate to the API layer?
- A) Stores call the backend directly using SQL
- B) Stores import API functions which use `fetch()` to call the backend, then update their reactive value with the response
- C) The API layer bypasses stores and writes directly to the DOM
- D) Stores and API functions are the same thing

<details>
<summary>Answer</summary>
**B) Stores import API functions which use `fetch()` to call the backend, then update their reactive value with the response** -- For example, `stores/collections.ts` imports `getCollections` from `api/collections.ts`, calls it, and uses `collections.set(...)` to update the reactive store with the response data (lines 7-12).
</details>

---

## Further Reading
- [Svelte 5 Official Tutorial](https://svelte.dev/tutorial/svelte/welcome-to-svelte) -- tutorial
- [Svelte 5 Runes Documentation](https://svelte.dev/docs/svelte/$state) -- official-docs
- [SvelteKit Documentation](https://svelte.dev/docs/kit/introduction) -- official-docs
- [Svelte Store Documentation](https://svelte.dev/docs/svelte/stores) -- official-docs
- [SvelteKit Routing](https://svelte.dev/docs/kit/routing) -- official-docs

# Reactive Stores & State Management

> **Category**: pattern | **Difficulty**: beginner | **Time**: ~20 min
> **Prerequisites**: Svelte & SvelteKit

## Overview

If you've used Python's `Observable` pattern -- for example, event listeners in GUI frameworks like tkinter's `StringVar`, or callbacks in matplotlib widgets -- Svelte stores are the same idea: a value that notifies listeners when it changes. But simpler. Think of a store as a variable that automatically updates every component that uses it, without you having to wire up any event handlers.

In a typical Python data science workflow, you might pass DataFrames between functions explicitly. In a web UI, multiple components on the same page need to share state (for example, the sidebar listing workspaces and the main panel showing the active workspace). Stores solve this: you put the shared state in one place, and every component that cares about it gets notified whenever it changes.

**Key takeaways:**
- Stores are reactive containers -- change the value, and all subscribers update automatically
- `writable` stores can be set from anywhere (like a global variable, but safer)
- `derived` stores compute values from other stores (like a spreadsheet formula)
- The `$` prefix auto-subscribes in Svelte components (no manual subscribe/unsubscribe)

---

## Core Concepts

### 1. writable() -- The Basic Store

The simplest store is a `writable`: a container that holds a value and lets you replace it. Here's how WellBegun creates one:

```typescript
// From frontend/src/lib/stores/collections.ts:5
export const collections = writable<Collection[]>([]);
```

Breaking this down:
- `writable<Collection[]>` creates a store that holds an array of `Collection` objects. The `<Collection[]>` part is a TypeScript generic -- it declares the type of data the store holds, similar to `list[Collection]` in Python type hints.
- `([])` passes an empty array as the initial value.
- `export const` makes the store importable from any other file.

**Python comparison**: Imagine a global variable wrapped in a class that calls `notify()` on every assignment:

```python
# Python equivalent (conceptual)
class WritableStore:
    def __init__(self, initial):
        self._value = initial
        self._listeners = []

    def set(self, new_value):
        self._value = new_value
        for callback in self._listeners:
            callback(new_value)

    def subscribe(self, callback):
        self._listeners.append(callback)
        callback(self._value)  # Immediate call with current value
```

WellBegun's workspace store shows how you can create multiple writable stores for related data:

```typescript
// From frontend/src/lib/stores/workspaces.ts:5-6
export const workspaces = writable<Workspace[]>([]);
export const activeWorkspace = writable<WorkspaceDetail | null>(null);
```

The `| null` means the store can hold either a `WorkspaceDetail` object or `null` (no active workspace selected). This is like Python's `Optional[WorkspaceDetail]`.

### 2. Reading and Writing Stores

**Writing** -- You have two main methods:

`.set(value)` replaces the store's value entirely:

```typescript
// From frontend/src/lib/stores/collections.ts:9
collections.set(await getCollections(categoryId));
```

This fetches collections from the API and replaces whatever was in the store with the new array.

`.update(fn)` lets you modify the current value. It takes a callback that receives the current value and returns the new one:

```typescript
// Hypothetical example (not in project, but common pattern)
collections.update(current => [...current, newCollection]);
```

This is like `list.append()` but immutable -- you return a new array rather than mutating the old one.

**Reading** -- In Svelte components, you prefix the store name with `$` to auto-subscribe:

```svelte
<!-- In a Svelte component -->
{#each $collections as collection}
    <div>{collection.title}</div>
{/each}
```

The `$collections` prefix does three things automatically:
1. Subscribes to the store when the component mounts
2. Updates the component whenever the store value changes
3. Unsubscribes when the component is destroyed (preventing memory leaks)

Without the `$` prefix, you'd need to manage subscriptions manually.

### 3. derived() -- Computed Stores

A `derived` store automatically computes its value from one or more other stores. It's read-only -- you can't `.set()` it directly. When the source store changes, the derived store recomputes.

```typescript
// From frontend/src/lib/stores/workspaces.ts:7
export const activeWorkspaceId = derived(activeWorkspace, ($ws) => $ws?.id ?? null);
```

Breaking this down:
- `derived(activeWorkspace, ...)` says "this store depends on `activeWorkspace`"
- `($ws) => $ws?.id ?? null` is the computation: extract the `id` from the active workspace, or return `null` if there's no active workspace
- `$ws?.id` is optional chaining (like Python's `getattr(ws, 'id', None)` but for nested access)
- `??` is the nullish coalescing operator (like Python's `or`, but only triggers on `null`/`undefined`, not on `0` or `""`)

**Python comparison**: This is like a `@property` on a class, or a computed column in pandas:

```python
# Python equivalent (conceptual)
@property
def active_workspace_id(self):
    ws = self.active_workspace
    return ws.id if ws is not None else None
```

The key difference: in Python, a property recomputes every time you access it. A derived store recomputes only when its source changes, then caches the result.

### 4. The Store + API Pattern

WellBegun uses a consistent pattern: each store file pairs the store with async functions that fetch data from the API and update the store. This is the bridge between the REST API (server data) and reactive UI updates.

Here's the pattern in collections:

```typescript
// From frontend/src/lib/stores/collections.ts:5-13
export const collections = writable<Collection[]>([]);

export async function loadCollections(categoryId?: number) {
    try {
        collections.set(await getCollections(categoryId));
    } catch (e) {
        console.warn('Failed to load collections:', e);
    }
}
```

The data flow is:
1. A component calls `loadCollections()`
2. `getCollections()` makes a `fetch()` call to `GET /api/collections/`
3. The API returns JSON data
4. `collections.set(...)` updates the store with the new data
5. Every component using `$collections` re-renders automatically

The workspace store shows a more complex version of this pattern:

```typescript
// From frontend/src/lib/stores/workspaces.ts:9-15
export async function loadWorkspaces() {
    try {
        workspaces.set(await getWorkspaces());
    } catch (e) {
        console.warn('Failed to load workspaces:', e);
    }
}
```

And `setActiveWorkspace` chains multiple operations -- calling the API, updating the active workspace, then refreshing the list:

```typescript
// From frontend/src/lib/stores/workspaces.ts:17-27
export async function setActiveWorkspace(id: number) {
    try {
        await openWorkspace(id);
        const detail = await getWorkspace(id);
        activeWorkspace.set(detail);
        // Refresh the list to update last_opened_at
        await loadWorkspaces();
    } catch (e) {
        console.warn('Failed to set active workspace:', e);
    }
}
```

Notice the cascade: `activeWorkspace.set(detail)` updates one store, then `loadWorkspaces()` updates another. Any component subscribed to either store will re-render.

### 5. subscribe() for Imperative Code

The `$` prefix only works inside Svelte components (`.svelte` files). In plain TypeScript files (like store modules themselves), you need `.subscribe()` to read a store's value.

Here's a pattern from the workspace store:

```typescript
// From frontend/src/lib/stores/workspaces.ts:33-44
export async function refreshActiveWorkspace() {
    let currentId: number | null = null;
    activeWorkspace.subscribe(ws => { currentId = ws?.id ?? null; })();
    if (currentId !== null) {
        try {
            const detail = await getWorkspace(currentId);
            activeWorkspace.set(detail);
        } catch (e) {
            console.warn('Failed to refresh workspace:', e);
        }
    }
}
```

The critical line is:

```typescript
activeWorkspace.subscribe(ws => { currentId = ws?.id ?? null; })();
```

This does three things in one expression:
1. `.subscribe(callback)` registers a listener and immediately calls it with the current value. It returns an unsubscribe function.
2. The trailing `()` immediately calls that unsubscribe function.
3. Net effect: read the current value once, then stop listening.

**Python comparison**: This is like peeking at a value without setting up a permanent observer:

```python
# Python equivalent (conceptual)
current_id = store.get_current_value()
```

It's a bit awkward in Svelte because stores are designed for reactive subscriptions, not imperative reads. But this "subscribe-and-immediately-unsubscribe" pattern is the standard idiom when you need a one-time read outside a component.

---

## In This Project

WellBegun uses stores extensively. The architecture follows a consistent pattern across entity types:

**Store files** (`frontend/src/lib/stores/`): Each entity type has its own store file:
- `collections.ts` -- collection list
- `workspaces.ts` -- workspace list + active workspace
- `projects.ts` -- project list
- `logs.ts` -- log entries
- `notes.ts` -- notes
- `sources.ts`, `actors.ts`, `activities.ts`, `plans.ts` -- other entity types
- `knowledgeGraph.ts` -- graph data (board nodes, triples)
- Plus UI-focused stores: `panels.ts`, `focus.ts`, `selectedEntity.ts`, `activeTab.ts`, etc.

**API files** (`frontend/src/lib/api/`): Each entity type has API functions that make `fetch()` calls to the backend.

**Components** import from both stores and API files. For example, the KnowledgeGraph component imports stores from 8 different store files:

```typescript
// From frontend/src/lib/components/graph/KnowledgeGraph.svelte:4-13
import { boardNodes, triples, loadBoard, loadTriples } from '$lib/stores/knowledgeGraph';
import { projects } from '$lib/stores/projects';
import { logs } from '$lib/stores/logs';
import { notes } from '$lib/stores/notes';
import { activities } from '$lib/stores/activities';
import { sources } from '$lib/stores/sources';
import { actors } from '$lib/stores/actors';
import { plans } from '$lib/stores/plans';
import { collections } from '$lib/stores/collections';
```

This illustrates the power of stores: the KnowledgeGraph component can display data from many different entity types, and it automatically stays in sync when any of them change -- without passing data through props or managing event listeners.

---

## Guided Examples

### Example 1: Trace Data Flow from Backend to UI

Let's trace exactly what happens when the user opens WellBegun and the collections load:

**Step 1 -- Component calls the load function:**
```svelte
<!-- In a Svelte component's onMount -->
<script>
    import { collections, loadCollections } from '$lib/stores/collections';
    import { onMount } from 'svelte';

    onMount(() => {
        loadCollections();
    });
</script>
```

**Step 2 -- Load function calls the API and updates the store:**
```typescript
// frontend/src/lib/stores/collections.ts:7-13
export async function loadCollections(categoryId?: number) {
    try {
        collections.set(await getCollections(categoryId));
    } catch (e) {
        console.warn('Failed to load collections:', e);
    }
}
```

**Step 3 -- The API function makes an HTTP request:**
```typescript
// frontend/src/lib/api/collections.ts
export async function getCollections(categoryId?: number): Promise<Collection[]> {
    const url = categoryId != null ? `${BASE}/?category_id=${categoryId}` : `${BASE}/`;
    const res = await fetch(url);
    return res.json();
}
```

**Step 4 -- The store notifies all subscribers, and the component re-renders:**
```svelte
<!-- The component's template automatically updates -->
{#each $collections as collection}
    <CollectionCard {collection} />
{/each}
```

The entire chain is: `onMount` -> `loadCollections()` -> `fetch()` -> JSON response -> `collections.set(data)` -> UI re-renders. Every component using `$collections` updates simultaneously.

### Example 2: The Workspace Store -- writable, derived, and Orchestration

The workspace store (`frontend/src/lib/stores/workspaces.ts`) demonstrates all the store concepts working together:

**Two writable stores hold the data:**
```typescript
// Lines 5-6: raw data
export const workspaces = writable<Workspace[]>([]);       // all workspaces
export const activeWorkspace = writable<WorkspaceDetail | null>(null);  // currently open one
```

**A derived store extracts a convenient value:**
```typescript
// Line 7: computed from activeWorkspace
export const activeWorkspaceId = derived(activeWorkspace, ($ws) => $ws?.id ?? null);
```

Components that only need the ID (not the full detail object) can subscribe to `activeWorkspaceId` instead. This is more efficient -- the component won't re-render when other workspace fields change, only when the ID changes.

**`setActiveWorkspace` orchestrates multiple updates:**
```typescript
// Lines 17-27: API call + two store updates
export async function setActiveWorkspace(id: number) {
    try {
        await openWorkspace(id);                // 1. Tell backend to mark it as opened
        const detail = await getWorkspace(id);  // 2. Fetch full details
        activeWorkspace.set(detail);            // 3. Update active workspace store
        await loadWorkspaces();                 // 4. Refresh list (updates last_opened_at)
    } catch (e) {
        console.warn('Failed to set active workspace:', e);
    }
}
```

This single function call triggers updates to two stores (`activeWorkspace` and `workspaces`), and by extension to the derived store (`activeWorkspaceId`). Every component subscribed to any of these stores re-renders with the new data.

**`clearActiveWorkspace` is the simplest possible store operation:**
```typescript
// Lines 29-31
export function clearActiveWorkspace() {
    activeWorkspace.set(null);
}
```

Setting to `null` causes `activeWorkspaceId` to recompute to `null`, and any component checking `$activeWorkspace` will see that no workspace is selected.

---

## Exercises

### Exercise 1: Read a Store File

**Task**: Open `frontend/src/lib/stores/projects.ts`. It follows the same pattern as `collections.ts`. Identify: (a) What type does the store hold? (b) What is the initial value? (c) What API function populates it?

<details>
<summary>Hint</summary>
The file is only 13 lines long and follows the exact same structure as collections.ts. Look at the writable generic type, the initial value in parentheses, and the function called inside <code>set()</code>.
</details>

### Exercise 2: Trace a Derived Store

**Task**: In `frontend/src/lib/stores/workspaces.ts`, the `activeWorkspaceId` is derived from `activeWorkspace`. If `activeWorkspace` is set to `{ id: 42, name: "Research", ... }`, what will `activeWorkspaceId` hold? What if `activeWorkspace` is set to `null`?

<details>
<summary>Hint</summary>
Look at the derivation function: <code>($ws) => $ws?.id ?? null</code>. When the workspace object exists, <code>$ws?.id</code> extracts the <code>id</code> field. When <code>$ws</code> is null, the optional chaining (<code>?.</code>) short-circuits to <code>undefined</code>, and the <code>??</code> operator converts that to <code>null</code>.
</details>

### Exercise 3: Predict the Update Cascade

**Task**: When `setActiveWorkspace(7)` is called in `workspaces.ts`, list every store that changes value. Which components would re-render?

<details>
<summary>Hint</summary>
The function calls <code>activeWorkspace.set(detail)</code> (updating one store, which also triggers <code>activeWorkspaceId</code> to recompute) and then <code>loadWorkspaces()</code> (which calls <code>workspaces.set(...)</code>). So three stores change: <code>activeWorkspace</code>, <code>activeWorkspaceId</code>, and <code>workspaces</code>. Any component using <code>$activeWorkspace</code>, <code>$activeWorkspaceId</code>, or <code>$workspaces</code> will re-render.
</details>

---

## Knowledge Check

**Q1**: What is the difference between `writable` and `derived` stores?
- A) `writable` stores are private, `derived` stores are public
- B) `writable` stores can be set directly, `derived` stores compute their value from other stores
- C) `derived` stores are faster than `writable` stores
- D) `writable` stores hold arrays, `derived` stores hold single values

<details>
<summary>Answer</summary>
<strong>B) writable stores can be set directly, derived stores compute their value from other stores</strong> -- A <code>writable</code> store has <code>.set()</code> and <code>.update()</code> methods. A <code>derived</code> store is read-only and automatically recomputes when its source store(s) change. In WellBegun, <code>activeWorkspace</code> is writable (you set it with workspace data) while <code>activeWorkspaceId</code> is derived (it automatically extracts the ID).
</details>

**Q2**: In a Svelte component, what does the `$` prefix do when used with a store?
- A) It marks the variable as constant
- B) It converts the store to a string
- C) It auto-subscribes to the store and provides the current value reactively
- D) It creates a copy of the store

<details>
<summary>Answer</summary>
<strong>C) It auto-subscribes to the store and provides the current value reactively</strong> -- The <code>$</code> prefix is Svelte syntactic sugar. Writing <code>$collections</code> in a component automatically subscribes when the component mounts, updates whenever the store value changes, and unsubscribes when the component is destroyed.
</details>

**Q3**: In `collections.ts`, what does `collections.set(await getCollections(categoryId))` do?
- A) It appends new collections to the existing list
- B) It replaces the entire store value with the API response
- C) It filters the collections by category
- D) It creates a new store

<details>
<summary>Answer</summary>
<strong>B) It replaces the entire store value with the API response</strong> -- <code>.set()</code> replaces the store's value entirely. The <code>await getCollections(categoryId)</code> fetches data from the backend API, and then the entire result becomes the new store value. If you wanted to append instead, you'd use <code>.update(current => [...current, ...newItems])</code>.
</details>

**Q4**: Why does `refreshActiveWorkspace` use the pattern `activeWorkspace.subscribe(ws => { ... })()`?
- A) It creates a permanent subscription to track changes
- B) It reads the current value once by subscribing and immediately unsubscribing
- C) It resets the store to its initial value
- D) It triggers all other subscribers to re-run

<details>
<summary>Answer</summary>
<strong>B) It reads the current value once by subscribing and immediately unsubscribing</strong> -- <code>.subscribe()</code> calls the callback immediately with the current value and returns an unsubscribe function. The trailing <code>()</code> calls that unsubscribe function right away. The net effect is a one-time read of the store's current value. This pattern is needed in plain TypeScript files where the <code>$</code> prefix isn't available.
</details>

**Q5**: In the WellBegun project, what consistent pattern do store files follow?
- A) Each store file contains a single writable store and nothing else
- B) Each store file exports a writable store paired with async functions that fetch data from the API and update the store
- C) Store files only contain derived stores
- D) Store files connect directly to the database

<details>
<summary>Answer</summary>
<strong>B) Each store file exports a writable store paired with async functions that fetch data from the API and update the store</strong> -- This is WellBegun's consistent architecture: <code>collections.ts</code> exports <code>collections</code> (writable) and <code>loadCollections()</code> (async fetch + set). <code>workspaces.ts</code> exports <code>workspaces</code>, <code>activeWorkspace</code>, and functions like <code>loadWorkspaces()</code>, <code>setActiveWorkspace()</code>, etc. This pattern separates data storage from data fetching while keeping them co-located.
</details>

---

## Further Reading
- [Svelte Stores Documentation](https://svelte.dev/docs/svelte/stores) -- official-docs
- [Svelte Tutorial: Stores](https://learn.svelte.dev/tutorial/writable-stores) -- tutorial
- [Svelte Reactive Declarations](https://svelte.dev/docs/svelte/$state) -- official-docs
- [State Management Patterns in Svelte](https://kit.svelte.dev/docs/state-management) -- official-docs

# Reactive UI Programming

> **Category**: concept | **Difficulty**: beginner | **Time**: ~15 min
> **Prerequisites**: Event-Driven UI

## Overview

If you've done data science in Python, you're used to imperative programming: you tell the computer each step in order. "Load the data. Filter it. Plot it." In imperative DOM manipulation (the traditional way to build web UIs), you do the same thing: "Find the div. Change its text. Add a CSS class. Remove the old row."

Reactive programming flips this around. Instead of telling the UI what to do step by step, you declare what the UI should look like given some data, and the framework handles the updates when that data changes. It's like the difference between manually updating every cell in a spreadsheet vs. writing a formula and letting the spreadsheet recalculate automatically.

**Python analogy:** Imagine you have a matplotlib plot that automatically re-draws every time the underlying DataFrame changes -- no need to call `plt.draw()` or clear the axes. That's what reactive UI programming gives you.

**Key takeaways:**
- Reactive UIs update automatically when the underlying data (state) changes
- You declare what the UI should look like, not how to update it step by step
- Data binding connects state to UI elements -- changes in one are reflected in the other
- Svelte uses reactive primitives (`$state` in Svelte 5, `writable` stores) to track changes and trigger re-renders

---

## Core Concepts

### 1. Imperative vs. Declarative UI

In **imperative** DOM manipulation (vanilla JavaScript), you manually find and update elements:

```javascript
// Imperative: you manage every update yourself
const list = document.getElementById('note-list');
list.innerHTML = '';  // clear old content
for (const note of notes) {
    const li = document.createElement('li');
    li.textContent = note.title;
    list.appendChild(li);
}
```

In **declarative/reactive** code (Svelte), you describe the desired result:

```svelte
<!-- Declarative: Svelte handles the DOM updates -->
{#each $notes as note}
    <li>{note.title}</li>
{/each}
```

When `$notes` changes, Svelte automatically figures out what DOM elements to add, remove, or update. You never touch the DOM directly.

**Python comparison:** This is similar to how pandas lets you write `df[df.score > 80]` (declarative) instead of manually looping through rows and building a new list (imperative). You describe the result, not the steps.

### 2. Data Binding

Data binding is the mechanism that connects your application state (variables, stores) to the UI. When the state changes, the UI updates. In some frameworks, binding is two-way: when the user types in an input field, the state updates too.

In Svelte, data binding happens through:
- **One-way binding**: Displaying a store or variable value in the template. When the value changes, the display updates.
- **Two-way binding**: Using `bind:value` on input elements. The variable updates when the user types, and the input updates when the variable changes programmatically.

```svelte
<script>
    let title = $state('');
</script>

<!-- Two-way binding: typing updates `title`, and setting `title` updates the input -->
<input bind:value={title} />

<!-- One-way binding: displays current value of `title` -->
<p>You typed: {title}</p>
```

**Python comparison:** Two-way binding is like tkinter's `StringVar` -- link it to an Entry widget, and changes flow both ways.

### 3. Automatic Re-rendering on State Change

The core promise of reactive programming: when state changes, every piece of UI that depends on that state re-renders automatically. You don't call any "refresh" or "redraw" function.

In Svelte 5, `$state` marks a variable as reactive:

```svelte
<script>
    let count = $state(0);
</script>

<button onclick={() => count++}>
    Clicked {count} times
</button>
```

When `count` changes, the button text updates. No manual DOM manipulation needed.

For shared state across components, Svelte uses `writable` stores:

```typescript
// From frontend/src/lib/stores/notes.ts
export const notes = writable<Note[]>([]);
```

Any component that reads `$notes` will re-render whenever `notes.set()` or `notes.update()` is called -- from anywhere in the application.

### 4. Reactive Primitives

Svelte provides two main mechanisms for reactivity:

**`$state` (Svelte 5 runes)** -- for local component state:
```svelte
<script>
    let searchTerm = $state('');
    let isOpen = $state(false);
</script>
```

**`writable` stores** -- for shared state across components:
```typescript
import { writable } from 'svelte/store';
export const notes = writable<Note[]>([]);
```

The key difference: `$state` lives inside a single component and is destroyed when that component unmounts. A `writable` store lives in a module file and persists as long as the application runs. Multiple components can import and subscribe to the same store.

**Python comparison:** `$state` is like an instance variable on a class -- local to that instance. A `writable` store is like a module-level variable that multiple objects can observe.

---

## In This Project

WellBegun's frontend is built entirely on reactive principles. The architecture follows a clear pattern:

1. **Stores** (`frontend/src/lib/stores/`) hold shared state as `writable` stores
2. **API functions** (`frontend/src/lib/api/`) fetch data from the backend
3. **Load functions** bridge the two: fetch data via API, then call `store.set()` to update the store
4. **Components** subscribe to stores using the `$` prefix and re-render automatically

For example, `frontend/src/lib/stores/notes.ts` defines:

```typescript
import { writable } from 'svelte/store';
import type { Note } from '$lib/types';
import { getNotes } from '$lib/api/notes';

export const notes = writable<Note[]>([]);

export async function loadNotes() {
    notes.set(await getNotes());
}
```

The `notes` store is the single source of truth for note data. When `loadNotes()` is called, it fetches notes from the backend API and calls `notes.set()` with the result. Every component using `$notes` -- whether it's a sidebar list, a detail panel, or the knowledge graph -- re-renders with the new data instantly.

This is reactive programming in action: no component needs to know about any other component. They all just subscribe to the same store, and the framework handles the rest.

---

## Guided Examples

### Example 1: The Reactive Chain -- From `loadNotes()` to UI Update

Let's trace the reactivity chain when notes are loaded:

**Step 1 -- Something triggers `loadNotes()`** (e.g., the app starts, or the user navigates to a view):
```typescript
// A component calls:
loadNotes();
```

**Step 2 -- `loadNotes()` fetches data and updates the store:**
```typescript
// frontend/src/lib/stores/notes.ts
export async function loadNotes() {
    notes.set(await getNotes());  // getNotes() calls fetch('/api/notes/')
}
```

**Step 3 -- `notes.set()` replaces the store value and notifies all subscribers.** Any component using `$notes` re-renders:

```svelte
<!-- Component A: a list of notes -->
{#each $notes as note}
    <div>{note.title}</div>
{/each}

<!-- Component B: a note count badge -->
<span>{$notes.length} notes</span>
```

Both Component A and Component B update simultaneously. Neither knows about the other. They both just react to the same store changing.

**Key insight:** The reactive chain is: **data source (API) -> store update (`set()`) -> automatic UI re-render**. You only need to update the store; the framework handles propagating the change to every subscriber.

### Example 2: Comparing Imperative vs. Reactive Approaches

Imagine you want to display a filtered list of notes. Here's how you'd do it imperatively vs. reactively:

**Imperative (manual DOM updates):**
```javascript
function updateNoteList(notes, filter) {
    const container = document.getElementById('notes');
    container.innerHTML = '';  // clear everything
    for (const note of notes) {
        if (note.title.includes(filter)) {
            const div = document.createElement('div');
            div.textContent = note.title;
            container.appendChild(div);
        }
    }
}
// Must call this every time notes OR filter changes
```

**Reactive (Svelte):**
```svelte
<script>
    import { notes } from '$lib/stores/notes';
    let filter = $state('');
</script>

<input bind:value={filter} />

{#each $notes.filter(n => n.title.includes(filter)) as note}
    <div>{note.title}</div>
{/each}
```

In the reactive version, the list updates automatically when either `$notes` changes (new data from the API) or `filter` changes (user types in the input). You never call an update function -- the framework detects the dependencies and re-renders.

---

## Exercises

### Exercise 1: Predict the Reactive Update

**Task**: The `notes` store currently holds `[{title: "Meeting"}, {title: "Ideas"}]`. A component displays:
```svelte
<p>You have {$notes.length} notes</p>
```
Now `loadNotes()` is called and the API returns `[{title: "Meeting"}, {title: "Ideas"}, {title: "Todo"}]`. What happens to the paragraph element?

<details>
<summary>Hint</summary>
The <code>notes.set()</code> call replaces the store value. Since <code>$notes.length</code> changes from 2 to 3, the paragraph re-renders to show "You have 3 notes".
</details>

### Exercise 2: Trace the Reactivity Chain

**Task**: Open `frontend/src/lib/stores/notes.ts`. Trace the full reactive chain from when `loadNotes()` is called to when a component displaying `$notes` updates. List each step in order.

<details>
<summary>Hint</summary>
The chain is: (1) <code>loadNotes()</code> is called, (2) <code>getNotes()</code> makes a <code>fetch()</code> call to the backend API, (3) the API returns JSON data, (4) <code>notes.set(data)</code> replaces the store value and notifies all subscribers, (5) every component using <code>$notes</code> re-renders with the new data.
</details>

### Exercise 3: Imperative to Reactive

**Task**: Rewrite this imperative code as a reactive Svelte snippet:
```javascript
const el = document.getElementById('status');
if (notes.length === 0) {
    el.textContent = 'No notes yet';
} else {
    el.textContent = `${notes.length} notes`;
}
```

<details>
<summary>Hint</summary>
In Svelte, you use <code>{#if}</code> blocks and store subscriptions:
<pre><code>{#if $notes.length === 0}
    &lt;p&gt;No notes yet&lt;/p&gt;
{:else}
    &lt;p&gt;{$notes.length} notes&lt;/p&gt;
{/if}</code></pre>
The template re-renders automatically when <code>$notes</code> changes.
</details>

---

## Knowledge Check

**Q1**: What is the main difference between imperative and reactive UI programming?
- A) Imperative is faster, reactive is slower
- B) In imperative, you manually update the DOM step by step; in reactive, you declare the desired UI state and the framework handles updates
- C) Reactive programming only works with stores
- D) Imperative programming doesn't use JavaScript

<details>
<summary>Answer</summary>
<strong>B) In imperative, you manually update the DOM step by step; in reactive, you declare the desired UI state and the framework handles updates</strong> -- Imperative code says "find this element, change its text, add this child." Reactive code says "the UI should look like this given this data" and the framework handles the DOM diffing and patching.
</details>

**Q2**: In WellBegun's `notes.ts`, what triggers all subscribed components to re-render?
- A) Calling `getNotes()` from the API module
- B) Calling `notes.set()` with new data
- C) Importing the `notes` store in a component
- D) Using the `$` prefix in a template

<details>
<summary>Answer</summary>
<strong>B) Calling <code>notes.set()</code> with new data</strong> -- The <code>.set()</code> method replaces the store value and notifies all subscribers. <code>getNotes()</code> only fetches data but doesn't update the store. Importing the store and using <code>$</code> are about subscribing, not triggering updates.
</details>

**Q3**: What is data binding in the context of reactive UI?
- A) Linking a database table to a UI component
- B) The mechanism that connects application state to UI elements so changes propagate automatically
- C) A way to validate form inputs
- D) A method for caching API responses

<details>
<summary>Answer</summary>
<strong>B) The mechanism that connects application state to UI elements so changes propagate automatically</strong> -- Data binding is the bridge between your data (stores, variables) and the UI. When the data changes, the UI updates. With two-way binding (like Svelte's <code>bind:value</code>), user input also flows back to the data.
</details>

**Q4**: What is the difference between `$state` and a `writable` store in Svelte?
- A) `$state` is for numbers, `writable` is for arrays
- B) `$state` is local to a component; `writable` stores are shared across components via module imports
- C) `writable` stores are deprecated in Svelte 5
- D) There is no difference

<details>
<summary>Answer</summary>
<strong>B) <code>$state</code> is local to a component; <code>writable</code> stores are shared across components via module imports</strong> -- <code>$state</code> creates reactive state within a single component. A <code>writable</code> store is defined in a separate module file and can be imported by any component, enabling shared state across the application. WellBegun uses stores for entity data (notes, projects, etc.) that multiple components need.
</details>

---

## Further Reading
- [Svelte Reactivity Documentation](https://svelte.dev/docs/svelte/$state) -- official-docs
- [Svelte Tutorial: Reactivity](https://learn.svelte.dev/tutorial/state) -- tutorial
- [Reactive Programming (Wikipedia)](https://en.wikipedia.org/wiki/Reactive_programming) -- reference
- [Svelte Stores Documentation](https://svelte.dev/docs/svelte/stores) -- official-docs

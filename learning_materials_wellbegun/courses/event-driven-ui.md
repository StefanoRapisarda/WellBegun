# Event-Driven UI

> **Category**: concept | **Difficulty**: beginner | **Time**: ~15 min
> **Prerequisites**: Client-Server Architecture

## Overview

If you've used Python callback functions -- for example, registering a function to run when a button is clicked in tkinter, or attaching a callback to a matplotlib widget -- you already understand the core idea of event-driven UI programming. The user does something (clicks, types, submits a form), the browser generates an event, and your code runs a function in response.

In a traditional script, code executes top to bottom. In an event-driven UI, your code mostly sits idle, waiting. When the user interacts with the page, the browser fires events, and your registered handlers execute. This is the fundamental model of all interactive web applications, including WellBegun.

**Python analogy:** Think of a Jupyter notebook where cells run when you press Shift+Enter. The notebook is idle until you act. Now imagine every widget, button, and text field in a web page works the same way -- idle until the user triggers an event.

**Key takeaways:**
- User actions (click, type, submit) produce events that the browser dispatches to your code
- Event handlers are functions you register to run when a specific event occurs on a specific element
- Events propagate through the DOM tree (bubbling), allowing parent elements to catch child events
- In component-based frameworks like Svelte, the pattern is "props down, events up" -- parents pass data down, children notify parents via events

---

## Core Concepts

### 1. Events and Event Handlers

An **event** is a signal that something happened: the user clicked a button, submitted a form, pressed a key, or moved the mouse. The browser creates an event object with details (which element was clicked, what key was pressed, the mouse position).

An **event handler** is a function you attach to an element to run when a specific event occurs:

```svelte
<button onclick={() => console.log('clicked!')}>
    Click me
</button>
```

In Svelte 5, event handlers are passed as properties using the standard `on<event>` naming convention. When the user clicks the button, the browser fires a `click` event, and Svelte calls your handler function.

**Python comparison:** This is exactly like tkinter's `button.config(command=my_function)` or matplotlib's `button.on_clicked(my_function)`. You register a callback, and the framework calls it when the event occurs.

### 2. Common Event Types

Web browsers support dozens of event types. The most common in WellBegun:

| Event | Trigger | Typical Use |
|-------|---------|-------------|
| `click` | User clicks an element | Buttons, links, selection |
| `submit` | User submits a form | Creating/updating entities |
| `input` | User types in a field | Real-time filtering, validation |
| `keydown` | User presses a key | Keyboard shortcuts |
| `change` | User changes a select/checkbox | Dropdown selections |
| `mouseenter`/`mouseleave` | Mouse enters/leaves an element | Tooltips, hover effects |

Each event carries an event object with properties like `event.target` (the element that fired the event) and methods like `event.preventDefault()` (stop the browser's default behavior, e.g., prevent a form from reloading the page).

### 3. Event Propagation (Bubbling)

When an event fires on an element, it doesn't just stay there -- it **bubbles up** through the DOM tree. If you click a `<button>` inside a `<div>` inside a `<form>`, the click event fires on the button first, then the div, then the form, then the body, all the way to the document root.

```
click event path:  button -> div -> form -> body -> document
```

This is useful: you can attach a single handler to a parent element to catch events from all its children, instead of attaching handlers to each child individually.

You can stop propagation with `event.stopPropagation()` if you don't want the event to bubble further.

**Python comparison:** There's no direct Python equivalent, but it's similar to exception handling where an exception propagates up the call stack until something catches it.

### 4. Component Communication: Props Down, Events Up

In component-based frameworks like Svelte, the standard pattern is:

- **Props down**: Parent components pass data to children as properties (props)
- **Events up**: Children notify parents that something happened by dispatching custom events

```svelte
<!-- Parent component -->
<NoteCard
    note={myNote}
    ondelete={() => handleDelete(myNote.id)}
/>

<!-- Child component (NoteCard.svelte) -->
<script>
    let { note, ondelete } = $props();
</script>

<div>
    <h3>{note.title}</h3>
    <button onclick={ondelete}>Delete</button>
</div>
```

The parent passes the `note` data down (props) and a callback function `ondelete` that the child calls when the delete button is clicked (events up). The child doesn't know how deletion works -- it just notifies the parent.

**Python comparison:** This is like the Strategy pattern in OOP -- the parent injects behavior (the delete function) into the child. The child calls the function without knowing its implementation.

### 5. Form Submission Events

Forms are a special and important case. When a user submits a form, the browser fires a `submit` event. In WellBegun, forms create and update entities:

```svelte
<form onsubmit={(e) => {
    e.preventDefault();  // Stop the browser from reloading the page
    createNote({ title, content });
}}>
    <input bind:value={title} />
    <textarea bind:value={content}></textarea>
    <button type="submit">Create Note</button>
</form>
```

The `e.preventDefault()` call is critical. Without it, the browser would reload the page (the default form submission behavior from the 1990s). In a modern single-page app like WellBegun, you want to handle the submission in JavaScript and update the UI reactively.

---

## In This Project

WellBegun uses event-driven patterns throughout its frontend:

**Entity creation forms**: When the user fills in a form and clicks "Create", a `submit` event fires. The handler calls an API function (e.g., `createNote()`), which sends a `POST` request to the backend. After the API call succeeds, the store is updated (e.g., `loadNotes()`), and all subscribed components re-render.

**Graph interactions**: The KnowledgeGraph component (`frontend/src/lib/components/graph/KnowledgeGraph.svelte`) handles click events on graph nodes. Clicking a node selects that entity and may open a detail panel.

**Panel and tab navigation**: Click events on sidebar items and tabs switch the active view by updating stores (e.g., `activeTab.set('notes')`).

**The full event chain for creating a note:**
1. User types in form fields (input events update local state via `bind:value`)
2. User clicks "Create" button (submit event fires)
3. Handler calls `e.preventDefault()` to stop page reload
4. Handler calls `createNote({ title, content })` (API function sends POST request)
5. Backend creates the note and returns it
6. Handler calls `loadNotes()` to refresh the store
7. `notes.set(newData)` updates the store
8. All components using `$notes` re-render

This chain connects three concepts: events (user action), client-server communication (API call), and reactivity (store update triggers re-render).

---

## Guided Examples

### Example 1: The Full Event Chain -- Creating a Note

Let's trace what happens from the moment the user clicks "Create Note" to the UI updating:

**Step 1 -- The user clicks the submit button.** The browser fires a `submit` event on the `<form>` element.

**Step 2 -- The event handler runs:**
```svelte
<form onsubmit={async (e) => {
    e.preventDefault();
    await createNote({ title, content });
    await loadNotes();
}}>
```

`e.preventDefault()` prevents the browser from reloading the page. Then `createNote()` sends a POST request to the API.

**Step 3 -- The API function sends the request:**
```typescript
// frontend/src/lib/api/notes.ts
export async function createNote(data: NoteCreate): Promise<Note> {
    const res = await fetch(`${BASE}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    return res.json();
}
```

**Step 4 -- After the API call succeeds, `loadNotes()` refreshes the store:**
```typescript
// frontend/src/lib/stores/notes.ts
export async function loadNotes() {
    notes.set(await getNotes());
}
```

**Step 5 -- Every component using `$notes` re-renders with the new list that includes the just-created note.**

The entire chain: **user click -> submit event -> preventDefault -> API POST -> store refresh -> reactive UI update**.

### Example 2: Props Down, Events Up -- Component Communication

Consider a parent component rendering a list of notes, where each note card has a delete button:

**Parent component:**
```svelte
<script>
    import { notes, loadNotes } from '$lib/stores/notes';
    import { deleteNote } from '$lib/api/notes';

    async function handleDelete(id: number) {
        await deleteNote(id);
        await loadNotes();
    }
</script>

{#each $notes as note}
    <NoteCard {note} ondelete={() => handleDelete(note.id)} />
{/each}
```

**Child component (NoteCard):**
```svelte
<script>
    let { note, ondelete } = $props();
</script>

<div>
    <h3>{note.title}</h3>
    <button onclick={ondelete}>Delete</button>
</div>
```

Data flows **down** (the parent passes `note` as a prop). Events flow **up** (the child calls the `ondelete` callback when clicked). The child has no idea that clicking "Delete" triggers an API call and store refresh -- it just calls the function the parent provided.

---

## Exercises

### Exercise 1: Trace the Event Flow

**Task**: A user clicks a "Delete" button inside a `NoteCard` component. The `NoteCard` is inside a `NoteList` component, which is inside the main `App` component. Describe the event flow: which component handles the click? How does the parent know the note was deleted?

<details>
<summary>Hint</summary>
The click event fires on the button inside NoteCard. NoteCard's handler calls the <code>ondelete</code> callback prop, which was passed by the parent (NoteList or App). The parent's callback calls the API to delete the note, then refreshes the store. This is the "props down, events up" pattern.
</details>

### Exercise 2: Why preventDefault()?

**Task**: What would happen if you removed `e.preventDefault()` from a form's submit handler? Why is it necessary in a single-page app like WellBegun?

<details>
<summary>Hint</summary>
Without <code>preventDefault()</code>, the browser's default form submission behavior kicks in: it would attempt to send the form data to the server via a full page navigation (GET or POST request). This would reload the page, destroying all the client-side state (stores, component state) and giving a poor user experience. In a single-page app, you handle form submission in JavaScript instead.
</details>

### Exercise 3: Design an Event Chain

**Task**: Design the event chain for editing an existing note. Starting from the user clicking "Save" on an edit form, list every step through the API call and store update to the UI re-rendering.

<details>
<summary>Hint</summary>
The chain is: (1) User clicks "Save" (submit event), (2) Handler calls <code>e.preventDefault()</code>, (3) Handler calls <code>updateNote(id, { title, content })</code> (API function sends PUT/PATCH request), (4) Backend updates the note and returns it, (5) Handler calls <code>loadNotes()</code>, (6) <code>notes.set(newData)</code> updates the store, (7) All components using <code>$notes</code> re-render with the updated note.
</details>

---

## Knowledge Check

**Q1**: What is an event in the context of web UI programming?
- A) A scheduled task that runs at a specific time
- B) A signal that something happened (user click, key press, form submit) that triggers registered handler functions
- C) A message sent from the server to the client
- D) A CSS animation trigger

<details>
<summary>Answer</summary>
<strong>B) A signal that something happened (user click, key press, form submit) that triggers registered handler functions</strong> -- Events are the browser's way of telling your code that something happened. The browser creates an event object with details and dispatches it to registered handlers.
</details>

**Q2**: What does `e.preventDefault()` do in a form submit handler?
- A) Prevents the form from being displayed
- B) Prevents other event handlers from running
- C) Stops the browser's default behavior (page reload on form submit) so you can handle it in JavaScript
- D) Prevents the event from bubbling up

<details>
<summary>Answer</summary>
<strong>C) Stops the browser's default behavior (page reload on form submit) so you can handle it in JavaScript</strong> -- By default, submitting a form causes a full page navigation. In a single-page app like WellBegun, you want to handle submission with JavaScript (API call + store update) instead of reloading the page.
</details>

**Q3**: What does "props down, events up" mean in component-based frameworks?
- A) Data is stored in props, events are stored in the DOM
- B) Parent components pass data to children via props, and children notify parents by calling event callbacks
- C) Props flow from the server down, events flow from the client up
- D) Events must always be defined before props

<details>
<summary>Answer</summary>
<strong>B) Parent components pass data to children via props, and children notify parents by calling event callbacks</strong> -- The parent passes data (like a note object) down as a prop. The child notifies the parent when something happens (like a delete click) by calling a callback function that the parent provided. This creates a clear, predictable data flow.
</details>

**Q4**: What is event bubbling?
- A) Events fire multiple times on the same element
- B) Events propagate from the target element up through its ancestor elements in the DOM tree
- C) Events are delayed until the next render cycle
- D) Events are converted to store updates automatically

<details>
<summary>Answer</summary>
<strong>B) Events propagate from the target element up through its ancestor elements in the DOM tree</strong> -- When you click a button inside a div inside a form, the click event fires on the button first, then bubbles up to the div, then the form, and so on. This allows parent elements to catch events from their children.
</details>

**Q5**: In WellBegun, what is the complete event chain when a user creates a note via a form?
- A) Click -> page reload -> database update
- B) Submit event -> preventDefault -> API POST request -> store refresh (loadNotes) -> reactive UI update
- C) Click -> direct DOM update -> database sync
- D) Submit event -> store update -> API call

<details>
<summary>Answer</summary>
<strong>B) Submit event -> preventDefault -> API POST request -> store refresh (loadNotes) -> reactive UI update</strong> -- The form submit fires, preventDefault stops the page reload, the API function sends a POST request to the backend, then loadNotes() refreshes the store, and all subscribed components re-render with the new data.
</details>

---

## Further Reading
- [MDN: Introduction to Events](https://developer.mozilla.org/en-US/docs/Learn/JavaScript/Building_blocks/Events) -- tutorial
- [MDN: Event Bubbling](https://developer.mozilla.org/en-US/docs/Learn/JavaScript/Building_blocks/Event_bubbling) -- reference
- [Svelte Tutorial: Events](https://learn.svelte.dev/tutorial/dom-events) -- tutorial
- [Svelte 5 Event Handlers](https://svelte.dev/docs/svelte/event-handlers) -- official-docs

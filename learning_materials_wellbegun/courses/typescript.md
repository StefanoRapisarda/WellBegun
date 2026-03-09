# TypeScript Essentials

> **Category**: language | **Difficulty**: beginner | **Time**: ~20 min
> **Prerequisites**: None

## Overview

TypeScript adds type annotations to JavaScript, much like Python's type hints (PEP 484). If you write `def greet(name: str) -> str:` in Python, you will feel right at home with TypeScript's `function greet(name: string): string`. The key difference: Python's type hints are optional and ignored at runtime, while TypeScript's annotations are checked at compile time and stripped from the JavaScript that actually runs in the browser.

**Key takeaways:**

- TypeScript = JavaScript + type annotations (like Python + type hints, but enforced at compile time)
- Interfaces define object shapes (like Python's TypedDict or dataclass)
- Generics let you parameterize types (like Python's `list[int]` or `dict[str, Any]`)
- Union types (`string | null`) handle nullable values (like Python's `str | None`)

---

## Core Concepts

### 1. Type Annotations

In Python, you write type hints on function signatures:

```python
def get_collection(id: int) -> Collection | None:
    ...
```

In TypeScript, the syntax is similar but the annotation follows a colon after the parameter name, and the return type comes after the parameter list:

```typescript
// frontend/src/lib/api/collections.ts, line 11
export async function getCollection(id: number): Promise<Collection> {
    const res = await fetch(`${BASE}/${id}`);
    return res.json();
}
```

Notice three differences from Python:

| Concept | Python | TypeScript |
|---------|--------|------------|
| Integer type | `int` | `number` |
| String type | `str` | `string` |
| Boolean type | `bool` | `boolean` |

TypeScript has no separate `int` and `float` -- everything numeric is `number`. Dates are typically represented as `string` (ISO format) rather than a dedicated `datetime` type.

Optional parameters use the `?` suffix. Compare this function signature:

```typescript
// frontend/src/lib/api/collections.ts, line 5
export async function getCollections(categoryId?: number): Promise<Collection[]> {
    const url = categoryId != null ? `${BASE}/?category_id=${categoryId}` : `${BASE}/`;
    const res = await fetch(url);
    return res.json();
}
```

The `categoryId?: number` means the parameter is optional. In Python, you would write `category_id: int | None = None`.

### 2. Interfaces vs Python Dataclasses

An interface defines the shape of an object -- what fields it has and what types those fields are. This is the TypeScript equivalent of a Python dataclass or Pydantic model.

Here is the `Collection` interface from WellBegun:

```typescript
// frontend/src/lib/types.ts, lines 213-224
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

Compare this side-by-side with the Pydantic schema that the Python backend uses to serialize the same data:

```python
# src/wellbegun/schemas/collection.py, lines 49-61
class CollectionOut(BaseModel):
    id: int
    entity_type: str
    title: str
    description: str | None = None
    category_id: int
    is_active: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    items: list[CollectionItemOut] = []

    model_config = {"from_attributes": True}
```

The correspondence is almost one-to-one:

| Python (Pydantic) | TypeScript (Interface) |
|---|---|
| `id: int` | `id: number` |
| `title: str` | `title: string` |
| `description: str \| None = None` | `description: string \| null` |
| `is_active: bool` | `is_active: boolean` |
| `items: list[CollectionItemOut] = []` | `items: CollectionItem[]` |

Key difference: interfaces exist only at compile time. They produce zero runtime code -- there is no `Collection` class you can instantiate. They are purely a contract that the compiler checks against.

### 3. Generics

You already use generics in Python when you write `list[int]` or `dict[str, Any]`. TypeScript generics work the same way, with angle brackets instead of square brackets.

From the collections store:

```typescript
// frontend/src/lib/stores/collections.ts, line 5
export const collections = writable<Collection[]>([]);
```

Here, `writable<Collection[]>` creates a Svelte store that holds an array of `Collection` objects. The `<Collection[]>` is a generic parameter that tells the store what type of data it contains.

The Python equivalent would be:

```python
collections: Writable[list[Collection]] = Writable([])
```

Another common generic in WellBegun is `Promise<T>`, which is TypeScript's equivalent of Python's `Awaitable[T]` or what you get back from an `async def`:

```typescript
// frontend/src/lib/api/collections.ts, line 5
export async function getCollections(categoryId?: number): Promise<Collection[]> { ... }
```

In Python, you would simply annotate the return type directly:

```python
async def get_collections(category_id: int | None = None) -> list[Collection]:
    ...
```

### 4. Union Types and Optional Properties

Union types combine multiple possible types with the `|` operator, exactly as in modern Python (3.10+):

```typescript
// frontend/src/lib/types.ts, lines 48-65
export interface Activity {
    id: number;
    log_id: number | null;       // might not belong to a log
    plan_id: number | null;      // might not belong to a plan
    source_id: number | null;
    title: string;
    description: string | null;  // optional text
    duration: number | null;     // optional duration
    position: number;
    header: string | null;
    status: string;
    activity_date: string | null;
    is_active: boolean;
    is_archived: boolean;
    created_at: string;
    updated_at: string;
}
```

In Python, the same pattern appears in the SQLAlchemy model:

```python
status: Mapped[str | None] = mapped_column(String(50), nullable=True)
```

There is a subtle distinction between `string | null` (union with null) and `?` (optional property):

- `description: string | null` -- the field must be present, but its value can be `null`
- `categoryId?: number` -- the field might not be present at all (it is `undefined`)

This matters for function parameters. In `getCollections(categoryId?: number)`, you can call the function with no argument at all: `getCollections()`. But for interface fields marked `string | null`, you must explicitly provide the field (even if the value is `null`).

### 5. The `import type` Syntax

Look at the top of the API client:

```typescript
// frontend/src/lib/api/collections.ts, line 1
import type { Collection, CollectionItem } from '$lib/types';
```

The `import type` keyword tells TypeScript: "I only need these for type checking -- do not include them in the final JavaScript." Since interfaces like `Collection` do not exist at runtime (they produce no code), importing them as `type` makes that intention explicit and can help bundlers produce smaller output.

Compare the store file, which imports a runtime value alongside a type:

```typescript
// frontend/src/lib/stores/collections.ts, lines 1-3
import { writable } from 'svelte/store';         // runtime value
import type { Collection } from '$lib/types';      // type only
import { getCollections } from '$lib/api/collections';  // runtime value
```

`writable` and `getCollections` are actual functions that exist at runtime. `Collection` is a type that is erased. The `import type` syntax makes this distinction clear.

---

## In This Project

The file `frontend/src/lib/types.ts` (270 lines) acts as the contract between the frontend and backend. Every interface in that file mirrors a Pydantic schema (or SQLAlchemy model) on the Python side. When the backend returns JSON from an API endpoint, the frontend casts that JSON to the appropriate TypeScript interface.

This creates a chain of type safety:

```
SQLAlchemy Model (Python)  -->  Pydantic Schema (Python)  -->  JSON (wire)  -->  TypeScript Interface (frontend)
```

For example:
- `models/collection.py` defines `Collection(Entity)` with database columns
- `schemas/collection.py` defines `CollectionOut(BaseModel)` for serialization
- `types.ts` defines `Collection` interface for the frontend
- `api/collections.ts` uses `Promise<Collection>` to type the API responses
- `stores/collections.ts` uses `writable<Collection[]>([])` to hold the state

The `tagCategoryPrefix` function (types.ts, lines 141-149) shows that `types.ts` is not limited to interfaces -- it also contains utility functions that work with those types:

```typescript
export function tagCategoryPrefix(tag: Tag): string {
    if (tag.entity_id !== null && tag.entity_id !== undefined) {
        return tag.category;
    }
    if (tag.category === 'wild') {
        return 'tag';
    }
    return `wd-${tag.category}`;
}
```

This function takes a `Tag` and returns a `string`. The TypeScript compiler ensures you cannot pass an `Activity` where a `Tag` is expected, and ensures the function always returns a `string` (never `null` or `undefined`).

---

## Guided Examples

### Example 1: Reading the Collection Interface

Let us trace how the `Collection` type flows through the project.

**Step 1: The interface definition** (types.ts, lines 200-224)

`CollectionItem` is defined first (lines 200-211), then `Collection` (lines 213-224). Notice that `Collection` has a field `items: CollectionItem[]` -- an array of collection items. This is how TypeScript expresses "a list of CollectionItem objects."

**Step 2: Compare to the Python model** (models/collection.py, lines 53-71)

The SQLAlchemy model has `items: Mapped[list["CollectionItem"]]` defined as a relationship. The TypeScript interface does not know about database relationships -- it just sees the flat JSON that arrives over the network.

**Step 3: The API client uses it** (api/collections.ts, lines 11-14)

```typescript
export async function getCollection(id: number): Promise<Collection> {
    const res = await fetch(`${BASE}/${id}`);
    return res.json();
}
```

The return type `Promise<Collection>` tells every caller exactly what shape of data they will receive. If you try to access `collection.nonexistent_field`, TypeScript will flag it as an error before the code ever runs.

### Example 2: Walking Through API Function Signatures

The `api/collections.ts` file demonstrates progressively more complex type annotations.

**Simple return type** (line 11):
```typescript
async function getCollection(id: number): Promise<Collection>
```
One parameter (`id: number`), returns a promise that resolves to a `Collection`.

**Optional parameter** (line 5):
```typescript
async function getCollections(categoryId?: number): Promise<Collection[]>
```
The `?` makes `categoryId` optional. Returns an array of collections.

**Object parameter type** (line 16):
```typescript
async function createCollection(data: {
    title: string;
    category_id: number;
    description?: string
}): Promise<Collection>
```
The parameter `data` is an inline object type -- like passing a Python `TypedDict`. The `description` field is optional (note the `?`).

**Partial utility type** (line 25):
```typescript
async function updateCollection(id: number, data: Partial<Collection>): Promise<Collection>
```
`Partial<Collection>` makes every field in `Collection` optional. This is a built-in TypeScript utility type. Python's closest equivalent would be making every field in a dataclass optional, which is what `CollectionUpdate` does manually in the Pydantic schema.

**Void return** (line 34):
```typescript
async function deleteCollection(id: number): Promise<void>
```
`void` means the function returns nothing meaningful -- like Python's `-> None`.

**Error handling** (lines 58-69):
```typescript
export async function addItem(
    collectionId: number,
    data: {
        member_entity_type: string;
        member_entity_id: number;
        position?: number;
        status?: string;
        notes?: string;
        header?: string
    }
): Promise<CollectionItem> {
    const res = await fetch(`${BASE}/${collectionId}/items`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to add item (${res.status})`);
    }
    return res.json();
}
```

This function shows error handling with typed parameters. The `data` parameter has several optional fields (with `?`). The `.catch(() => ({}))` is a fallback if the error response is not valid JSON -- `({})` is an empty object literal (the parentheses prevent JavaScript from interpreting `{}` as a code block).

---

## Exercises

### Exercise 1: Write an Interface

Write a TypeScript interface for a `Bookmark` that has:
- An `id` (number)
- A `url` (string)
- A `title` (string)
- An optional `notes` field (string or null)
- A `created_at` (string)
- A list of `tags` (array of strings)

<details>
<summary>Solution</summary>

```typescript
export interface Bookmark {
    id: number;
    url: string;
    title: string;
    notes: string | null;
    created_at: string;
    tags: string[];
}
```

</details>

### Exercise 2: Write a Function Signature

Write the TypeScript signature (not the body) for an async function `getBookmark` that takes a numeric `id` and returns a `Promise<Bookmark>`.

<details>
<summary>Solution</summary>

```typescript
export async function getBookmark(id: number): Promise<Bookmark> {
    // ...
}
```

</details>

### Exercise 3: Translate Python to TypeScript

Convert this Python Pydantic model to a TypeScript interface:

```python
class Experiment(BaseModel):
    id: int
    name: str
    description: str | None = None
    parameters: dict[str, float]
    is_complete: bool
    results: list[float]
    created_at: datetime
```

<details>
<summary>Solution</summary>

```typescript
export interface Experiment {
    id: number;
    name: string;
    description: string | null;
    parameters: Record<string, number>;
    is_complete: boolean;
    results: number[];
    created_at: string;
}
```

Note: `dict[str, float]` becomes `Record<string, number>`, and `datetime` becomes `string` (since JSON serializes dates as ISO strings).

</details>

### Exercise 4: Spot the Difference

Look at the `Plan` interface in `types.ts` (lines 118-134). It has two array fields: `items: PlanItem[]` and `activities: Activity[]`. The `Collection` interface also has an `items` field. What is the difference between how `Plan` and `Collection` use nested arrays?

<details>
<summary>Solution</summary>

`Plan` has two nested arrays (`items: PlanItem[]` and `activities: Activity[]`), while `Collection` has one (`items: CollectionItem[]`). Both use the same pattern: an array of typed objects. The difference is that `Plan` nests two different entity types, showing that interfaces can compose freely -- there is no limit to how many typed arrays an interface can contain. On the Python side, these correspond to two separate SQLAlchemy relationships on the `Plan` model.

</details>

---

## Knowledge Check

**Q1: What is the TypeScript equivalent of Python's `str | None`?**

<details>
<summary>Answer</summary>

`string | null`

TypeScript uses `null` where Python uses `None`. Note that TypeScript also has `undefined`, which is a separate concept (the value of a variable that has been declared but not assigned).

</details>

**Q2: What does `import type` do, and why is it used instead of a regular `import`?**

<details>
<summary>Answer</summary>

`import type` tells the TypeScript compiler that the imported symbol is only used for type checking and should be completely removed from the compiled JavaScript output. It is used for interfaces and type aliases that have no runtime representation. This makes the developer's intent explicit and can help with tree-shaking (removing unused code from the final bundle).

</details>

**Q3: In `writable<Collection[]>([])`, what do the angle brackets and square brackets each mean?**

<details>
<summary>Answer</summary>

`<Collection[]>` is a generic type parameter telling `writable` that the store holds an array of `Collection` objects (equivalent to Python's `list[Collection]`). The `([])` is the initial value passed to the function: an empty array. So the full expression creates a reactive store initialized with an empty list that is typed to hold `Collection` objects.

</details>

**Q4: What is the difference between `description?: string` and `description: string | null`?**

<details>
<summary>Answer</summary>

`description?: string` means the property is optional -- it may be absent entirely (its value would be `undefined` if accessed). `description: string | null` means the property must be present, but its value can be either a string or `null`. In practice, JSON APIs typically use `null` (not `undefined`) for missing values, so interface fields that correspond to nullable database columns are usually typed as `string | null`.

</details>

**Q5: Why does TypeScript use `string` for dates (like `created_at: string`) instead of a `Date` type?**

<details>
<summary>Answer</summary>

When data arrives from the backend as JSON, date values are serialized as ISO-format strings (e.g., `"2026-03-05T10:30:00"`). JSON has no native date type. The TypeScript interface describes the shape of the JSON as it arrives over the network, so it uses `string`. If you needed to perform date operations, you would parse it into a `Date` object in your code: `new Date(collection.created_at)`.

</details>

---

## Further Reading

- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/) -- the official guide, start with "The Basics"
- [TypeScript for Python Developers](https://www.typescriptlang.org/docs/handbook/typescript-in-5-minutes.html) -- a quick-start overview
- [Utility Types Reference](https://www.typescriptlang.org/docs/handbook/utility-types.html) -- `Partial<T>`, `Record<K, V>`, `Pick<T, K>`, and more
- WellBegun's `frontend/src/lib/types.ts` -- the full set of interfaces used in the project (270 lines, all readable after this course)

import { writable } from 'svelte/store';
import type { SearchResult } from '$lib/api/search';

/**
 * When set, the workspace query panel will open automatically
 * and display these injected results (e.g. entities tagged with selected topics).
 */
export const workspaceInjectedResults = writable<{ results: SearchResult[]; label: string } | null>(null);

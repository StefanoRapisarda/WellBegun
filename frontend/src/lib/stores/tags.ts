import { writable } from 'svelte/store';
import type { Tag } from '$lib/types';
import { getAllTags, searchTags as apiSearch } from '$lib/api/tags';

export const tags = writable<Tag[]>([]);

// Signal that entity tags should be refreshed (increments on each tag change)
export const entityTagsVersion = writable(0);

export async function loadTags() {
	try {
		tags.set(await getAllTags());
	} catch (e) {
		console.warn('Failed to load tags:', e);
	}
}

export function triggerEntityTagsRefresh() {
	entityTagsVersion.update(v => v + 1);
}

export async function searchTagsStore(q: string): Promise<Tag[]> {
	return apiSearch(q);
}

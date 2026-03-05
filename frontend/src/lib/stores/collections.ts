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

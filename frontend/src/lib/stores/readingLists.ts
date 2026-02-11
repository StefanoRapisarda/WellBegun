import { writable } from 'svelte/store';
import type { ReadingList } from '$lib/types';
import { getReadingLists } from '$lib/api/readingLists';

export const readingLists = writable<ReadingList[]>([]);

export async function loadReadingLists() {
	try {
		readingLists.set(await getReadingLists());
	} catch (e) {
		console.warn('Failed to load reading lists:', e);
	}
}

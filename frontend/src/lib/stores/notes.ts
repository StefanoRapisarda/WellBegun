import { writable } from 'svelte/store';
import type { Note } from '$lib/types';
import { getNotes } from '$lib/api/notes';

export const notes = writable<Note[]>([]);

export async function loadNotes() {
	try {
		notes.set(await getNotes());
	} catch (e) {
		console.warn('Failed to load notes:', e);
	}
}

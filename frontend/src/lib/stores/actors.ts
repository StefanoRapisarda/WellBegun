import { writable } from 'svelte/store';
import type { Actor } from '$lib/types';
import { getActors } from '$lib/api/actors';

export const actors = writable<Actor[]>([]);

export async function loadActors() {
	try {
		actors.set(await getActors());
	} catch (e) {
		console.warn('Failed to load actors:', e);
	}
}

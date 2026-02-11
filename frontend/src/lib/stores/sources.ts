import { writable } from 'svelte/store';
import type { Source } from '$lib/types';
import { getSources } from '$lib/api/sources';

export const sources = writable<Source[]>([]);

export async function loadSources() {
	try {
		sources.set(await getSources());
	} catch (e) {
		console.warn('Failed to load sources:', e);
	}
}

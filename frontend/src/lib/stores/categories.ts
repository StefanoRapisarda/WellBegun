import { writable } from 'svelte/store';
import type { Category } from '$lib/types';
import { getCategories } from '$lib/api/categories';

export const categories = writable<Category[]>([]);

export async function loadCategories() {
	try {
		categories.set(await getCategories());
	} catch (e) {
		console.warn('Failed to load categories:', e);
	}
}

import { writable, get } from 'svelte/store';
import type { CustomPredicate } from '$lib/types';
import { getPredicates } from '$lib/api/knowledge';

export const structuralPredicates = writable<Record<string, string>>({});
export const semanticRelations = writable<
	Record<string, { key: string; forward: string; reverse: string }[]>
>({});
export const customPredicates = writable<CustomPredicate[]>([]);

let loaded = false;

export async function loadPredicates() {
	if (loaded) return;
	try {
		const data = await getPredicates();
		structuralPredicates.set(data.structural);
		semanticRelations.set(data.semantic);
		customPredicates.set(data.custom ?? []);
		loaded = true;
	} catch (e) {
		console.warn('Failed to load predicates:', e);
	}
}

export async function reloadPredicates() {
	loaded = false;
	await loadPredicates();
}

export function getStructuralPredicate(sourceType: string, targetType: string): string {
	return get(structuralPredicates)[`${sourceType}:${targetType}`] ?? 'related to';
}

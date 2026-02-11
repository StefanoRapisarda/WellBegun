import { writable, get } from 'svelte/store';
import { getPredicates } from '$lib/api/knowledge';

export const structuralPredicates = writable<Record<string, string>>({});
export const semanticRelations = writable<
	Record<string, { key: string; forward: string; reverse: string }[]>
>({});

let loaded = false;

export async function loadPredicates() {
	if (loaded) return;
	try {
		const data = await getPredicates();
		structuralPredicates.set(data.structural);
		semanticRelations.set(data.semantic);
		loaded = true;
	} catch (e) {
		console.warn('Failed to load predicates:', e);
	}
}

export function getStructuralPredicate(sourceType: string, targetType: string): string {
	return get(structuralPredicates)[`${sourceType}:${targetType}`] ?? 'related to';
}

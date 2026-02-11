import { writable } from 'svelte/store';
import type { KnowledgeTriple, BoardNode } from '$lib/types';
import { getBoardNodes, getTriples } from '$lib/api/knowledge';

export const boardNodes = writable<BoardNode[]>([]);
export const triples = writable<KnowledgeTriple[]>([]);

export async function loadBoard() {
	try {
		boardNodes.set(await getBoardNodes());
	} catch (e) {
		console.warn('Failed to load board nodes:', e);
	}
}

export async function loadTriples() {
	try {
		triples.set(await getTriples());
	} catch (e) {
		console.warn('Failed to load triples:', e);
	}
}

export function clearGraph() {
	boardNodes.set([]);
	triples.set([]);
}

// Persistent graph filter state (survives tab switches)
export const hiddenGraphEntities = writable<Set<string>>(new Set());
export const graphFilterPanelOpen = writable<boolean>(false);

export function clearGraphFilters() {
	hiddenGraphEntities.set(new Set());
	graphFilterPanelOpen.set(false);
}

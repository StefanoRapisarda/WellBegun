import { writable } from 'svelte/store';

export interface GraphInitialPayload {
	entities: { type: string; id: number }[];
	pulsingKeys: string[];   // "type:id" keys of originally-selected entities
	showRelated?: boolean;   // expand to include neighbors via triples
}

/**
 * Temporary store used to pass an initial selection into the Graph tab.
 * Coffee (or any other tab) writes here before switching to graph.
 * KnowledgeGraph reads and clears it on mount.
 */
export const graphInitialSelection = writable<GraphInitialPayload | null>(null);

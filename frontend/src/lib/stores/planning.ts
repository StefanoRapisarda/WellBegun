import { writable } from 'svelte/store';
import type { Plan, Note, Source, Actor, KnowledgeTriple } from '$lib/types';
import { getPlan } from '$lib/api/plans';
import { getNote } from '$lib/api/notes';
import { getSource } from '$lib/api/sources';
import { getActor } from '$lib/api/actors';
import { getCollection } from '$lib/api/collections';
import { getTriplesForEntity } from '$lib/api/knowledge';

// Currently selected plan (null = create-new mode)
export const selectedPlanId = writable<number | null>(null);

// Loaded plan data (refreshed when selectedPlanId changes)
export const planData = writable<Plan | null>(null);

// The predicates used to link plans to role notes
export const PLAN_NOTE_PREDICATES: Record<string, string> = {
	motivation: 'has motivation',
	goal: 'has goal',
	outcome: 'has outcome'
};

// Tagged notes for this plan — each role can have multiple notes
export const planNotes = writable<Record<string, Note[]>>({
	motivation: [],
	goal: [],
	outcome: []
});

// Sources linked to this plan via triples
export const planSources = writable<Source[]>([]);

// Actors linked to this plan via triples
export const planActors = writable<Actor[]>([]);

// Knowledge triples for the graph view
export const planTriples = writable<KnowledgeTriple[]>([]);

/**
 * Discover notes linked to a plan via knowledge triples with specific predicates.
 */
async function discoverPlanNotes(planId: number, triples: KnowledgeTriple[]): Promise<Record<string, Note[]>> {
	const result: Record<string, Note[]> = { motivation: [], goal: [], outcome: [] };
	for (const triple of triples) {
		if (triple.subject_type === 'plan' && triple.subject_id === planId && triple.object_type === 'note') {
			for (const [role, predicate] of Object.entries(PLAN_NOTE_PREDICATES)) {
				if (triple.predicate === predicate) {
					try {
						const note = await getNote(triple.object_id);
						result[role].push(note);
					} catch {
						// Note may have been deleted
					}
				}
			}
		}
	}
	return result;
}

/**
 * Discover sources linked to a plan via collection triples.
 */
async function discoverPlanSources(planId: number, triples: KnowledgeTriple[]): Promise<Source[]> {
	const results: Source[] = [];
	for (const triple of triples) {
		if (
			triple.subject_type === 'plan' &&
			triple.subject_id === planId &&
			triple.object_type === 'collection'
		) {
			try {
				const coll = await getCollection(triple.object_id);
				for (const item of coll.items ?? []) {
					if (item.member_entity_type === 'source') {
						try {
							results.push(await getSource(item.member_entity_id));
						} catch { /* deleted */ }
					}
				}
			} catch { /* collection deleted */ }
		}
	}
	return results;
}

/**
 * Discover actors linked to a plan via collection triples.
 */
async function discoverPlanActors(planId: number, triples: KnowledgeTriple[]): Promise<Actor[]> {
	const results: Actor[] = [];
	for (const triple of triples) {
		if (
			triple.subject_type === 'plan' &&
			triple.subject_id === planId &&
			triple.object_type === 'collection'
		) {
			try {
				const coll = await getCollection(triple.object_id);
				for (const item of coll.items ?? []) {
					if (item.member_entity_type === 'actor') {
						try {
							results.push(await getActor(item.member_entity_id));
						} catch { /* deleted */ }
					}
				}
			} catch { /* collection deleted */ }
		}
	}
	return results;
}

/**
 * Load all data for a plan: plan itself, tagged notes, sources, actors, and knowledge triples.
 */
export async function loadPlanData(planId: number) {
	try {
		const [plan, triplesData] = await Promise.all([
			getPlan(planId),
			getTriplesForEntity('plan', planId)
		]);
		planData.set(plan);
		planTriples.set(triplesData);
		// Discover linked entities from the triples we just loaded
		const [notes, sources, actors] = await Promise.all([
			discoverPlanNotes(planId, triplesData),
			discoverPlanSources(planId, triplesData),
			discoverPlanActors(planId, triplesData)
		]);
		planNotes.set(notes);
		planSources.set(sources);
		planActors.set(actors);
	} catch (e) {
		console.warn('Failed to load plan data:', e);
	}
}

/**
 * Reload triples only (e.g. after adding a connection).
 */
export async function refreshPlanGraph(planId: number) {
	try {
		planTriples.set(await getTriplesForEntity('plan', planId));
	} catch (e) {
		console.warn('Failed to refresh plan graph:', e);
	}
}

/**
 * Reload tagged notes and triples (e.g. after creating/deleting a note).
 */
export async function refreshPlanNotes(planId: number) {
	try {
		const triplesData = await getTriplesForEntity('plan', planId);
		planTriples.set(triplesData);
		planNotes.set(await discoverPlanNotes(planId, triplesData));
	} catch (e) {
		console.warn('Failed to refresh plan notes:', e);
	}
}

/**
 * Reset all planning stores to defaults (for create-new mode).
 */
export function clearPlanning() {
	selectedPlanId.set(null);
	planData.set(null);
	planNotes.set({ motivation: [], goal: [], outcome: [] });
	planSources.set([]);
	planActors.set([]);
	planTriples.set([]);
}

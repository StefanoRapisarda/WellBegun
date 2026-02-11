import { writable, get } from 'svelte/store';
import type { Tag } from '$lib/types';

export type EntityType = 'note' | 'log' | 'activity' | 'project' | 'source' | 'actor';

// Store last used tags per entity type, persisted to localStorage
const STORAGE_KEY = 'lastUsedTags';

function loadFromStorage(): Record<EntityType, Tag[]> {
	if (typeof localStorage === 'undefined') {
		return { note: [], log: [], activity: [], project: [], source: [], actor: [] };
	}
	try {
		const stored = localStorage.getItem(STORAGE_KEY);
		if (stored) {
			return JSON.parse(stored);
		}
	} catch {
		// Ignore parse errors
	}
	return { note: [], log: [], activity: [], project: [], source: [], actor: [] };
}

function saveToStorage(data: Record<EntityType, Tag[]>) {
	if (typeof localStorage !== 'undefined') {
		localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
	}
}

export const lastUsedTags = writable<Record<EntityType, Tag[]>>(loadFromStorage());

// Subscribe to changes and persist
lastUsedTags.subscribe(value => {
	saveToStorage(value);
});

// Update last used tags for an entity type
export function setLastUsedTags(entityType: EntityType, tags: Tag[]) {
	lastUsedTags.update(state => ({
		...state,
		[entityType]: tags
	}));
}

// Get last used tags for an entity type, filtering out inactive source entities
export function getLastUsedTags(entityType: EntityType, activeProjects: { id: number }[], activeActivities: { id: number }[]): Tag[] {
	const state = get(lastUsedTags);
	const tags = state[entityType] || [];

	// Filter out tags whose source entity is inactive
	return tags.filter(tag => {
		// If tag is not from an entity, keep it
		if (!tag.entity_type || !tag.entity_id) return true;

		// Check if source project is active
		if (tag.entity_type === 'project') {
			return activeProjects.some(p => p.id === tag.entity_id);
		}

		// Check if source activity is active
		if (tag.entity_type === 'activity') {
			return activeActivities.some(a => a.id === tag.entity_id);
		}

		// Keep other entity-linked tags
		return true;
	});
}

// Clear last used tags for an entity type
export function clearLastUsedTags(entityType: EntityType) {
	lastUsedTags.update(state => ({
		...state,
		[entityType]: []
	}));
}

// Clear last used tags for all entity types
export function clearAllLastUsedTags() {
	lastUsedTags.set({ note: [], log: [], activity: [], project: [], source: [], actor: [] });
}

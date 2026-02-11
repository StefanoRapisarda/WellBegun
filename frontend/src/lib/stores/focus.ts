import { writable, get } from 'svelte/store';
import type { Tag, Project, Activity } from '$lib/types';
import { clearFilterTags, resetToAll, addFilterTag, setFilterDays } from '$lib/stores/dateFilter';
import { activeTab } from '$lib/stores/activeTab';
import { configurePanels } from '$lib/stores/panels';
import { populateFromFocus } from '$lib/api/knowledge';
import { loadBoard, loadTriples, clearGraph, clearGraphFilters } from '$lib/stores/knowledgeGraph';

export interface FocusSelection {
	projectIds: number[];
	activityIds: number[];
}

const STORAGE_KEY = 'focusSelection';

function loadFromStorage(): FocusSelection {
	if (typeof localStorage === 'undefined') {
		return { projectIds: [], activityIds: [] };
	}
	try {
		const stored = localStorage.getItem(STORAGE_KEY);
		if (stored) {
			return JSON.parse(stored);
		}
	} catch {
		// Ignore parse errors
	}
	return { projectIds: [], activityIds: [] };
}

function saveToStorage(data: FocusSelection) {
	if (typeof localStorage !== 'undefined') {
		localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
	}
}

export const focusSelection = writable<FocusSelection>(loadFromStorage());

// Persist on change
focusSelection.subscribe(value => {
	saveToStorage(value);
});

export function setFocus(selection: FocusSelection) {
	focusSelection.set(selection);
}

export function clearFocus() {
	focusSelection.set({ projectIds: [], activityIds: [] });
}

/**
 * Full focus teardown: clears selection, filters, panels, and graph.
 * Used when the user clears focus from any panel.
 */
export function deactivateFocus() {
	clearFocus();
	clearFilterTags();
	resetToAll();
	configurePanels(
		['project', 'activity', 'log', 'note'],
		['project', 'log', 'note', 'activity']
	);
	clearGraph();
	clearGraphFilters();
}

export function isFocusActive(selection: FocusSelection): boolean {
	return selection.projectIds.length > 0 || selection.activityIds.length > 0;
}

/**
 * Orchestrates focus activation:
 * 1. Persists selection
 * 2. Finds matching tags from allTags by entity_type + entity_id
 * 3. Sets filter tags
 * 4. Calculates days from oldest selected entity's created_at to today
 * 5. Sets filter days
 * 6. Switches to input tab
 */
export async function activateFocus(
	selection: FocusSelection,
	allTags: Tag[],
	allProjects: Project[],
	allActivities: Activity[]
) {
	// 0. Reset graph filters from previous focus
	clearGraphFilters();

	// 1. Persist selection
	setFocus(selection);

	// 2. Find matching tags
	const matchingTags = allTags.filter(tag => {
		if (tag.entity_type === 'project' && tag.entity_id != null) {
			return selection.projectIds.includes(tag.entity_id);
		}
		if (tag.entity_type === 'activity' && tag.entity_id != null) {
			return selection.activityIds.includes(tag.entity_id);
		}
		return false;
	});

	// 3. Set filter tags
	clearFilterTags();
	for (const tag of matchingTags) {
		addFilterTag(tag);
	}

	// 4. Calculate days from oldest selected entity's created_at to today
	const selectedProjects = allProjects.filter(p => selection.projectIds.includes(p.id));
	const selectedActivities = allActivities.filter(a => selection.activityIds.includes(a.id));
	const allEntities = [...selectedProjects, ...selectedActivities];

	let days = 7; // default
	if (allEntities.length > 0) {
		const oldest = allEntities.reduce((min, entity) => {
			const d = new Date(entity.created_at).getTime();
			return d < min ? d : min;
		}, Infinity);
		const now = new Date();
		now.setHours(0, 0, 0, 0);
		const diffDays = Math.ceil((now.getTime() - oldest) / 86400000) + 1;
		days = Math.max(1, Math.min(365, diffDays));
	}

	// 5. Set filter days
	setFilterDays(days);

	// 6. Configure panels based on selection
	// Base layout: project + activity left, log center, note right
	const visibleIds = ['project', 'activity', 'log', 'note'];
	const slotOrder = ['project', 'log', 'note', 'activity'];

	// If any selected activity looks like a reading activity, add source + readinglist
	const READING_KEYWORDS = ['reading', 'read', 'study', 'studying'];
	const hasReadingActivity = selectedActivities.some(a =>
		READING_KEYWORDS.some(kw => a.title.toLowerCase().includes(kw))
	);
	if (hasReadingActivity) {
		visibleIds.push('source', 'readinglist');
		// source + readinglist go below log and note (slots 4, 5 → col 1, col 2 row 2)
		slotOrder.push('source', 'readinglist');
	}

	configurePanels(visibleIds, slotOrder);

	// 7. Populate the knowledge graph with focused entities
	try {
		await populateFromFocus(selection.projectIds, selection.activityIds);
		await Promise.allSettled([loadBoard(), loadTriples()]);
	} catch (e) {
		console.warn('Failed to populate graph from focus:', e);
	}

	// 8. Switch to input tab
	activeTab.set('input');
}

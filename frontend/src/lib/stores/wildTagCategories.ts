import { writable, get } from 'svelte/store';
import { browser } from '$app/environment';

const STORAGE_KEY = 'wildTagCategories';
const DEFAULT_CATEGORY = 'Default';

function load(): Record<string, number[]> {
	if (!browser) return { [DEFAULT_CATEGORY]: [] };
	const raw = localStorage.getItem(STORAGE_KEY);
	const cats: Record<string, number[]> = raw ? JSON.parse(raw) : {};
	if (!cats[DEFAULT_CATEGORY]) cats[DEFAULT_CATEGORY] = [];
	return cats;
}

function save(cats: Record<string, number[]>) {
	if (!browser) return;
	localStorage.setItem(STORAGE_KEY, JSON.stringify(cats));
}

export const wildTagCategories = writable<Record<string, number[]>>(load());

wildTagCategories.subscribe((val) => save(val));

export function addCategory(name: string) {
	wildTagCategories.update((cats) => {
		if (cats[name]) return cats;
		return { ...cats, [name]: [] };
	});
}

export function renameCategory(oldName: string, newName: string) {
	if (oldName === DEFAULT_CATEGORY || oldName === newName) return;
	wildTagCategories.update((cats) => {
		if (!cats[oldName] || cats[newName]) return cats;
		const updated: Record<string, number[]> = {};
		for (const [key, val] of Object.entries(cats)) {
			updated[key === oldName ? newName : key] = val;
		}
		return updated;
	});
}

export function deleteCategory(name: string) {
	if (name === DEFAULT_CATEGORY) return;
	wildTagCategories.update((cats) => {
		if (!cats[name]) return cats;
		const tagsToMove = cats[name];
		const updated = { ...cats };
		updated[DEFAULT_CATEGORY] = [...updated[DEFAULT_CATEGORY], ...tagsToMove];
		delete updated[name];
		return updated;
	});
}

export function assignTag(tagId: number, category: string) {
	wildTagCategories.update((cats) => {
		const updated: Record<string, number[]> = {};
		for (const [key, val] of Object.entries(cats)) {
			updated[key] = val.filter((id) => id !== tagId);
		}
		if (!updated[category]) updated[category] = [];
		updated[category] = [...updated[category], tagId];
		return updated;
	});
}

export function unassignTag(tagId: number) {
	wildTagCategories.update((cats) => {
		const updated: Record<string, number[]> = {};
		for (const [key, val] of Object.entries(cats)) {
			updated[key] = val.filter((id) => id !== tagId);
		}
		return updated;
	});
}

export function cleanupStaleIds(validTagIds: Set<number>) {
	wildTagCategories.update((cats) => {
		const updated: Record<string, number[]> = {};
		for (const [key, val] of Object.entries(cats)) {
			updated[key] = val.filter((id) => validTagIds.has(id));
		}
		return updated;
	});
}

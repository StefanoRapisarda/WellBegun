import { writable, derived, get } from 'svelte/store';
import type { Tag } from '$lib/types';
import { tags } from './tags';
import { projects } from './projects';
import { activities } from './activities';

function todayISO(): string {
	return new Date().toISOString().slice(0, 10);
}

function yesterdayISO(): string {
	const d = new Date();
	d.setDate(d.getDate() - 1);
	return d.toISOString().slice(0, 10);
}

export type FilterMode = 'all' | 'single' | 'range';

export interface DateFilterState {
	mode: FilterMode;
	date: string;       // used when mode === 'single'
	days: number;       // used when mode === 'range' (last X days including today)
}

export const dateFilter = writable<DateFilterState>({
	mode: 'range',
	date: todayISO(),
	days: 2
});

// Show archived items toggle
export const showArchived = writable<boolean>(false);

// Show only entities related to active projects/activities
export const showActiveRelated = writable<boolean>(false);

export const activeEntityTagIds = derived(
	[tags, projects, activities],
	([$tags, $projects, $activities]) => {
		const activeProjectIds = new Set($projects.filter(p => p.is_active).map(p => p.id));
		const activeActivityIds = new Set($activities.filter(a => a.is_active).map(a => a.id));
		return new Set(
			$tags.filter(t =>
				(t.entity_type === 'project' && t.entity_id !== null && activeProjectIds.has(t.entity_id)) ||
				(t.entity_type === 'activity' && t.entity_id !== null && activeActivityIds.has(t.entity_id))
			).map(t => t.id)
		);
	}
);

export function isActiveRelated(
	itemTags: Tag[],
	activeTagIds: Set<number>,
	isSelfActive: boolean = false
): boolean {
	if (isSelfActive) return true;
	return itemTags.some(tag => activeTagIds.has(tag.id));
}

// Tag filter store - selected tags for filtering
export const selectedFilterTags = writable<Tag[]>([]);

export function addFilterTag(tag: Tag) {
	selectedFilterTags.update(tags => {
		if (tags.some(t => t.id === tag.id)) return tags;
		return [...tags, tag];
	});
}

export function removeFilterTag(tagId: number) {
	selectedFilterTags.update(tags => tags.filter(t => t.id !== tagId));
}

export function clearFilterTags() {
	selectedFilterTags.set([]);
}

export function setFilterDate(date: string) {
	dateFilter.update(f => ({ ...f, mode: 'single', date }));
}

export function setFilterDays(days: number) {
	dateFilter.update(f => ({ ...f, mode: 'range', days }));
}

export function resetToToday() {
	dateFilter.set({ mode: 'single', date: todayISO(), days: 7 });
}

export function resetToAll() {
	dateFilter.set({ mode: 'all', date: todayISO(), days: 7 });
}

export function isDateVisible(item: { created_at: string; updated_at?: string }, filter: DateFilterState): boolean {
	if (filter.mode === 'all') return true;

	const createdDate = item.created_at.slice(0, 10);

	if (filter.mode === 'single') {
		return createdDate === filter.date;
	} else {
		// Range mode: check if created within last X days
		const today = new Date(todayISO());
		const startDate = new Date(today);
		startDate.setDate(today.getDate() - filter.days + 1);
		const startISO = startDate.toISOString().slice(0, 10);

		return createdDate >= startISO && createdDate <= todayISO();
	}
}

// Check if item's tags match the selected filter tags (OR logic - any match)
export function isTagVisible(itemTags: Tag[], filterTags: Tag[]): boolean {
	// If no filter tags selected, show all items
	if (filterTags.length === 0) return true;
	// Show item if it has ANY of the selected filter tags
	return itemTags.some(itemTag => filterTags.some(filterTag => filterTag.id === itemTag.id));
}

// Check if entity is the source of any selected filter tag (for Project/Activity auto-created tags)
export function isEntitySourceOfFilterTag(entityType: string, entityId: number, filterTags: Tag[]): boolean {
	if (filterTags.length === 0) return true;
	return filterTags.some(tag => tag.entity_type === entityType && tag.entity_id === entityId);
}

// Combined visibility check (for backwards compatibility)
export function isItemVisible(item: { created_at: string; updated_at?: string }, filter: DateFilterState): boolean {
	return isDateVisible(item, filter);
}

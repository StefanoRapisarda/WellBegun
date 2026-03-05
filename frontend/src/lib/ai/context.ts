import { get } from 'svelte/store';
import { panels } from '$lib/stores/panels';
import { projects } from '$lib/stores/projects';
import { activities } from '$lib/stores/activities';
import { notes } from '$lib/stores/notes';
import { logs } from '$lib/stores/logs';
import { sources } from '$lib/stores/sources';
import { actors } from '$lib/stores/actors';
import { tags } from '$lib/stores/tags';
import { dateFilter, selectedFilterTags } from '$lib/stores/dateFilter';

export interface AppContext {
	visiblePanels: string[];
	activeProjects: { id: number; title: string }[];
	activeActivities: { id: number; title: string; status: string }[];
	allProjects: { id: number; title: string; is_active: boolean }[];
	allActivities: { id: number; title: string; is_active: boolean; status: string }[];
	recentNotes: { id: number; content: string }[];
	recentLogs: { id: number; title: string }[];
	tagCount: number;
	sourceCount: number;
	actorCount: number;
	currentFilters: {
		dateRange: string;
		selectedTags: string[];
	};
}

export function getAppContext(): AppContext {
	const panelList = get(panels);
	const projectList = get(projects);
	const activityList = get(activities);
	const noteList = get(notes);
	const logList = get(logs);
	const sourceList = get(sources);
	const actorList = get(actors);
	const tagList = get(tags);
	const filter = get(dateFilter);
	const filterTags = get(selectedFilterTags);

	return {
		visiblePanels: panelList.filter(p => p.visible).map(p => p.id),
		activeProjects: projectList
			.filter(p => p.is_active)
			.map(p => ({ id: p.id, title: p.title })),
		activeActivities: activityList
			.filter(a => a.is_active)
			.map(a => ({ id: a.id, title: a.title, status: a.status })),
		allProjects: projectList.map(p => ({
			id: p.id,
			title: p.title,
			is_active: p.is_active
		})),
		allActivities: activityList.map(a => ({
			id: a.id,
			title: a.title,
			is_active: a.is_active,
			status: a.status
		})),
		recentNotes: noteList.slice(0, 5).map(n => ({
			id: n.id,
			content: n.content?.substring(0, 100) || ''
		})),
		recentLogs: logList.slice(0, 5).map(l => ({
			id: l.id,
			title: l.title
		})),
		tagCount: tagList.length,
		sourceCount: sourceList.length,
		actorCount: actorList.length,
		currentFilters: {
			dateRange: filter,
			selectedTags: filterTags.map(t => `${t.category}:${t.name}`)
		}
	};
}

export function formatContextForAI(context: AppContext): string {
	const lines: string[] = [];

	lines.push('=== Current App State ===');
	lines.push(`Visible panels: ${context.visiblePanels.join(', ')}`);

	if (context.activeProjects.length > 0) {
		lines.push(`Active projects: ${context.activeProjects.map(p => p.title).join(', ')}`);
	} else {
		lines.push('No active projects');
	}

	if (context.activeActivities.length > 0) {
		lines.push(`Active activities: ${context.activeActivities.map(a => `${a.title} (${a.status})`).join(', ')}`);
	} else {
		lines.push('No active activities');
	}

	lines.push(`Available projects: ${context.allProjects.map(p => p.title).join(', ')}`);
	lines.push(`Available activities: ${context.allActivities.map(a => a.title).join(', ')}`);

	if (context.recentNotes.length > 0) {
		lines.push('Recent notes:');
		context.recentNotes.forEach(n => lines.push(`  - ${n.content}`));
	}

	if (context.recentLogs.length > 0) {
		lines.push('Recent logs:');
		context.recentLogs.forEach(l => lines.push(`  - ${l.title}`));
	}

	lines.push(`Stats: ${context.tagCount} tags, ${context.sourceCount} sources, ${context.actorCount} actors`);

	if (context.currentFilters.selectedTags.length > 0) {
		lines.push(`Active filters: ${context.currentFilters.selectedTags.join(', ')}`);
	}

	return lines.join('\n');
}

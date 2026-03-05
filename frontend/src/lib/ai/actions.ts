import { panels } from '$lib/stores/panels';
import { projects, loadProjects } from '$lib/stores/projects';
import { activities, loadActivities } from '$lib/stores/activities';
import { notes, loadNotes } from '$lib/stores/notes';
import { logs, loadLogs } from '$lib/stores/logs';
import { sources, loadSources } from '$lib/stores/sources';
import { actors, loadActors } from '$lib/stores/actors';
import { selectedFilterTags } from '$lib/stores/dateFilter';
import { activateProject, deactivateProject } from '$lib/api/projects';
import { activateActivity, deactivateActivity } from '$lib/api/activities';
import { createNote } from '$lib/api/notes';
import { createLog } from '$lib/api/logs';
import { get } from 'svelte/store';

export interface ActionResult {
	success: boolean;
	message: string;
	data?: unknown;
}

// Action definitions for the AI
export const actionDefinitions = [
	{
		name: 'switch_panel',
		description: 'Show or hide a specific panel. Available panels: project, activity, note, log, source, actor, plan, wildtag',
		parameters: {
			panel_id: { type: 'string', description: 'The panel ID to toggle' },
			visible: { type: 'boolean', description: 'Whether to show (true) or hide (false) the panel' }
		}
	},
	{
		name: 'activate_project',
		description: 'Set a project as active. Active projects auto-tag new items.',
		parameters: {
			project_name: { type: 'string', description: 'Name or partial name of the project to activate' }
		}
	},
	{
		name: 'deactivate_project',
		description: 'Deactivate a project',
		parameters: {
			project_name: { type: 'string', description: 'Name or partial name of the project to deactivate' }
		}
	},
	{
		name: 'activate_activity',
		description: 'Set an activity as active',
		parameters: {
			activity_name: { type: 'string', description: 'Name or partial name of the activity to activate' }
		}
	},
	{
		name: 'deactivate_activity',
		description: 'Deactivate an activity',
		parameters: {
			activity_name: { type: 'string', description: 'Name or partial name of the activity to deactivate' }
		}
	},
	{
		name: 'create_note',
		description: 'Create a new quick note',
		parameters: {
			content: { type: 'string', description: 'The note content' }
		}
	},
	{
		name: 'create_log',
		description: 'Create a new log entry',
		parameters: {
			title: { type: 'string', description: 'Log title' },
			content: { type: 'string', description: 'Log content' }
		}
	},
	{
		name: 'show_panels_for_focus',
		description: 'Configure panels for a specific focus mode',
		parameters: {
			mode: { type: 'string', description: 'Focus mode: research, writing, planning, review, minimal' }
		}
	},
	{
		name: 'get_summary',
		description: 'Get a summary of current app state',
		parameters: {}
	}
];

// Action implementations
export const actions = {
	switch_panel: async (args: { panel_id: string; visible: boolean }): Promise<ActionResult> => {
		panels.update(list =>
			list.map(p => p.id === args.panel_id ? { ...p, visible: args.visible } : p)
		);
		return {
			success: true,
			message: `Panel "${args.panel_id}" is now ${args.visible ? 'visible' : 'hidden'}`
		};
	},

	activate_project: async (args: { project_name: string }): Promise<ActionResult> => {
		const projectList = get(projects);
		const project = projectList.find(p =>
			p.title.toLowerCase().includes(args.project_name.toLowerCase())
		);
		if (!project) {
			return { success: false, message: `Project "${args.project_name}" not found` };
		}
		await activateProject(project.id);
		await loadProjects();
		return { success: true, message: `Activated project "${project.title}"` };
	},

	deactivate_project: async (args: { project_name: string }): Promise<ActionResult> => {
		const projectList = get(projects);
		const project = projectList.find(p =>
			p.title.toLowerCase().includes(args.project_name.toLowerCase())
		);
		if (!project) {
			return { success: false, message: `Project "${args.project_name}" not found` };
		}
		await deactivateProject(project.id);
		await loadProjects();
		return { success: true, message: `Deactivated project "${project.title}"` };
	},

	activate_activity: async (args: { activity_name: string }): Promise<ActionResult> => {
		const activityList = get(activities);
		const activity = activityList.find(a =>
			a.title.toLowerCase().includes(args.activity_name.toLowerCase())
		);
		if (!activity) {
			return { success: false, message: `Activity "${args.activity_name}" not found` };
		}
		await activateActivity(activity.id);
		await loadActivities();
		return { success: true, message: `Activated activity "${activity.title}"` };
	},

	deactivate_activity: async (args: { activity_name: string }): Promise<ActionResult> => {
		const activityList = get(activities);
		const activity = activityList.find(a =>
			a.title.toLowerCase().includes(args.activity_name.toLowerCase())
		);
		if (!activity) {
			return { success: false, message: `Activity "${args.activity_name}" not found` };
		}
		await deactivateActivity(activity.id);
		await loadActivities();
		return { success: true, message: `Deactivated activity "${activity.title}"` };
	},

	create_note: async (args: { content: string }): Promise<ActionResult> => {
		await createNote({ content: args.content });
		await loadNotes();
		return { success: true, message: 'Note created' };
	},

	create_log: async (args: { title: string; content: string }): Promise<ActionResult> => {
		await createLog({
			title: args.title,
			content: args.content
		});
		await loadLogs();
		return { success: true, message: `Log "${args.title}" created` };
	},

	show_panels_for_focus: async (args: { mode: string }): Promise<ActionResult> => {
		const focusModes: Record<string, string[]> = {
			research: ['project', 'note', 'source', 'log'],
			writing: ['note', 'log', 'project'],
			planning: ['project', 'activity', 'note'],
			review: ['project', 'activity', 'log', 'note'],
			minimal: ['note', 'log']
		};

		const panelsToShow = focusModes[args.mode.toLowerCase()];
		if (!panelsToShow) {
			return { success: false, message: `Unknown focus mode "${args.mode}". Available: research, writing, planning, review, minimal` };
		}

		panels.update(list =>
			list.map(p => ({ ...p, visible: panelsToShow.includes(p.id) }))
		);
		return { success: true, message: `Switched to ${args.mode} mode` };
	},

	get_summary: async (): Promise<ActionResult> => {
		const projectList = get(projects);
		const activityList = get(activities);
		const noteList = get(notes);
		const logList = get(logs);

		const activeProjects = projectList.filter(p => p.is_active);
		const activeActivities = activityList.filter(a => a.is_active);

		return {
			success: true,
			message: `You have ${projectList.length} projects (${activeProjects.length} active), ` +
				`${activityList.length} activities (${activeActivities.length} active), ` +
				`${noteList.length} notes, and ${logList.length} logs.`,
			data: {
				activeProjects: activeProjects.map(p => p.title),
				activeActivities: activeActivities.map(a => a.title),
				recentNotes: noteList.slice(0, 3).map(n => n.content?.substring(0, 50)),
				recentLogs: logList.slice(0, 3).map(l => l.title)
			}
		};
	}
};

export async function executeAction(name: string, args: Record<string, unknown>): Promise<ActionResult> {
	const action = actions[name as keyof typeof actions];
	if (!action) {
		return { success: false, message: `Unknown action: ${name}` };
	}
	try {
		return await action(args as never);
	} catch (error) {
		return { success: false, message: `Error executing ${name}: ${error}` };
	}
}

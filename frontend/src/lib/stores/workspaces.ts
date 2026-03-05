import { writable, derived } from 'svelte/store';
import type { Workspace, WorkspaceDetail } from '$lib/types';
import { getWorkspaces, getWorkspace, openWorkspace } from '$lib/api/workspaces';

export const workspaces = writable<Workspace[]>([]);
export const activeWorkspace = writable<WorkspaceDetail | null>(null);
export const activeWorkspaceId = derived(activeWorkspace, ($ws) => $ws?.id ?? null);

export async function loadWorkspaces() {
	try {
		workspaces.set(await getWorkspaces());
	} catch (e) {
		console.warn('Failed to load workspaces:', e);
	}
}

export async function setActiveWorkspace(id: number) {
	try {
		await openWorkspace(id);
		const detail = await getWorkspace(id);
		activeWorkspace.set(detail);
		// Refresh the list to update last_opened_at
		await loadWorkspaces();
	} catch (e) {
		console.warn('Failed to set active workspace:', e);
	}
}

export function clearActiveWorkspace() {
	activeWorkspace.set(null);
}

export async function refreshActiveWorkspace() {
	let currentId: number | null = null;
	activeWorkspace.subscribe(ws => { currentId = ws?.id ?? null; })();
	if (currentId !== null) {
		try {
			const detail = await getWorkspace(currentId);
			activeWorkspace.set(detail);
		} catch (e) {
			console.warn('Failed to refresh workspace:', e);
		}
	}
}

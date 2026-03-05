import type { Workspace, WorkspaceDetail, WorkspaceItem, WorkspaceEvent } from '$lib/types';

const BASE = '/api/workspaces';

export async function getWorkspaces(includeArchived = false): Promise<Workspace[]> {
	const url = includeArchived ? `${BASE}/?include_archived=true` : `${BASE}/`;
	const res = await fetch(url);
	return res.json();
}

export async function getWorkspace(id: number): Promise<WorkspaceDetail> {
	const res = await fetch(`${BASE}/${id}`);
	return res.json();
}

export async function createWorkspace(data: { name: string; description?: string }): Promise<Workspace> {
	const res = await fetch(`${BASE}/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function updateWorkspace(id: number, data: { name?: string; description?: string }): Promise<Workspace> {
	const res = await fetch(`${BASE}/${id}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function deleteWorkspace(id: number): Promise<void> {
	await fetch(`${BASE}/${id}`, { method: 'DELETE' });
}

export async function archiveWorkspace(id: number): Promise<Workspace> {
	const res = await fetch(`${BASE}/${id}/archive`, { method: 'POST' });
	return res.json();
}

export async function openWorkspace(id: number): Promise<Workspace> {
	const res = await fetch(`${BASE}/${id}/open`, { method: 'POST' });
	return res.json();
}

export async function addWorkspaceItem(
	workspaceId: number,
	data: { entity_type: string; entity_id: number; x?: number; y?: number }
): Promise<WorkspaceItem> {
	const res = await fetch(`${BASE}/${workspaceId}/items`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function removeWorkspaceItem(
	workspaceId: number,
	entityType: string,
	entityId: number
): Promise<void> {
	await fetch(`${BASE}/${workspaceId}/items/${entityType}/${entityId}`, { method: 'DELETE' });
}

export async function updateWorkspaceItem(
	itemId: number,
	data: { x?: number; y?: number; collapsed?: boolean }
): Promise<WorkspaceItem> {
	const res = await fetch(`${BASE}/items/${itemId}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function bulkUpdatePositions(
	workspaceId: number,
	items: { entity_type: string; entity_id: number; x: number; y: number }[]
): Promise<void> {
	await fetch(`${BASE}/${workspaceId}/items/bulk-positions`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ items })
	});
}

export async function getWorkspaceEvents(workspaceId: number, limit = 50): Promise<WorkspaceEvent[]> {
	const res = await fetch(`${BASE}/${workspaceId}/events?limit=${limit}`);
	return res.json();
}

export async function recordWorkspaceEvent(
	workspaceId: number,
	data: { event_type: string; entity_type?: string; entity_id?: number; metadata?: Record<string, unknown> }
): Promise<WorkspaceEvent> {
	const res = await fetch(`${BASE}/${workspaceId}/events`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function expandEntityInWorkspace(
	workspaceId: number,
	entityType: string,
	entityId: number
): Promise<Workspace> {
	const res = await fetch(`${BASE}/${workspaceId}/expand/${entityType}/${entityId}`, {
		method: 'POST'
	});
	return res.json();
}

import type { Activity } from '$lib/types';

const BASE = '/api/activities';

export async function getActivities(): Promise<Activity[]> {
	const res = await fetch(`${BASE}/`);
	return res.json();
}

export async function getActivity(id: number): Promise<Activity> {
	const res = await fetch(`${BASE}/${id}`);
	return res.json();
}

export async function createActivity(data: { title: string; description?: string; duration?: number; log_id?: number }): Promise<Activity> {
	const res = await fetch(`${BASE}/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function updateActivity(id: number, data: Partial<Activity>): Promise<Activity> {
	const res = await fetch(`${BASE}/${id}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function deleteActivity(id: number): Promise<void> {
	await fetch(`${BASE}/${id}`, { method: 'DELETE' });
}

export async function activateActivity(id: number): Promise<Activity> {
	const res = await fetch(`${BASE}/${id}/activate`, { method: 'POST' });
	return res.json();
}

export async function deactivateActivity(id: number): Promise<Activity> {
	const res = await fetch(`${BASE}/${id}/deactivate`, { method: 'POST' });
	return res.json();
}

export async function deactivateAllActivities(): Promise<void> {
	await fetch(`${BASE}/deactivate-all`, { method: 'POST' });
}

export async function archiveActivity(id: number): Promise<Activity> {
	const res = await fetch(`${BASE}/${id}/archive`, { method: 'POST' });
	return res.json();
}

export async function unarchiveActivity(id: number): Promise<Activity> {
	const res = await fetch(`${BASE}/${id}/unarchive`, { method: 'POST' });
	return res.json();
}

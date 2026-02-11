import type { Actor } from '$lib/types';

const BASE = '/api/actors';

export async function getActors(): Promise<Actor[]> {
	const res = await fetch(`${BASE}/`);
	return res.json();
}

export async function getActor(id: number): Promise<Actor> {
	const res = await fetch(`${BASE}/${id}`);
	return res.json();
}

export async function createActor(data: { full_name: string; role?: string; affiliation?: string; expertise?: string; notes?: string; email?: string; url?: string }): Promise<Actor> {
	const res = await fetch(`${BASE}/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function updateActor(id: number, data: Partial<Actor>): Promise<Actor> {
	const res = await fetch(`${BASE}/${id}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function deleteActor(id: number): Promise<void> {
	await fetch(`${BASE}/${id}`, { method: 'DELETE' });
}

export async function activateActor(id: number): Promise<Actor> {
	const res = await fetch(`${BASE}/${id}/activate`, { method: 'POST' });
	return res.json();
}

export async function deactivateActor(id: number): Promise<Actor> {
	const res = await fetch(`${BASE}/${id}/deactivate`, { method: 'POST' });
	return res.json();
}

export async function archiveActor(id: number): Promise<Actor> {
	const res = await fetch(`${BASE}/${id}/archive`, { method: 'POST' });
	return res.json();
}

export async function unarchiveActor(id: number): Promise<Actor> {
	const res = await fetch(`${BASE}/${id}/unarchive`, { method: 'POST' });
	return res.json();
}

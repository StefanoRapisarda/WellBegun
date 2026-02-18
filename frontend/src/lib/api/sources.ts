import type { Source } from '$lib/types';

const BASE = '/api/sources';

export async function getSources(): Promise<Source[]> {
	const res = await fetch(`${BASE}/`);
	return res.json();
}

export async function getSource(id: number): Promise<Source> {
	const res = await fetch(`${BASE}/${id}`);
	return res.json();
}

export async function createSource(data: { title: string; description?: string; author?: string; content_url?: string; source_type?: string }): Promise<Source> {
	const res = await fetch(`${BASE}/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function updateSource(id: number, data: Partial<Source>): Promise<Source> {
	const res = await fetch(`${BASE}/${id}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function deleteSource(id: number): Promise<void> {
	await fetch(`${BASE}/${id}`, { method: 'DELETE' });
}

export async function activateSource(id: number): Promise<Source> {
	const res = await fetch(`${BASE}/${id}/activate`, { method: 'POST' });
	return res.json();
}

export async function deactivateSource(id: number): Promise<Source> {
	const res = await fetch(`${BASE}/${id}/deactivate`, { method: 'POST' });
	return res.json();
}

export async function archiveSource(id: number): Promise<Source> {
	const res = await fetch(`${BASE}/${id}/archive`, { method: 'POST' });
	return res.json();
}

export async function unarchiveSource(id: number): Promise<Source> {
	const res = await fetch(`${BASE}/${id}/unarchive`, { method: 'POST' });
	return res.json();
}

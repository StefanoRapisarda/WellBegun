import type { Log } from '$lib/types';

const BASE = '/api/logs';

export async function getLogs(): Promise<Log[]> {
	const res = await fetch(`${BASE}/`);
	return res.json();
}

export async function getLog(id: number): Promise<Log> {
	const res = await fetch(`${BASE}/${id}`);
	return res.json();
}

export async function createLog(data: { log_type: string; title: string; content?: string }): Promise<Log> {
	const res = await fetch(`${BASE}/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function updateLog(id: number, data: Partial<Log>): Promise<Log> {
	const res = await fetch(`${BASE}/${id}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function deleteLog(id: number): Promise<void> {
	await fetch(`${BASE}/${id}`, { method: 'DELETE' });
}

export async function activateLog(id: number): Promise<Log> {
	const res = await fetch(`${BASE}/${id}/activate`, { method: 'POST' });
	return res.json();
}

export async function deactivateLog(id: number): Promise<Log> {
	const res = await fetch(`${BASE}/${id}/deactivate`, { method: 'POST' });
	return res.json();
}

export async function archiveLog(id: number): Promise<Log> {
	const res = await fetch(`${BASE}/${id}/archive`, { method: 'POST' });
	return res.json();
}

export async function unarchiveLog(id: number): Promise<Log> {
	const res = await fetch(`${BASE}/${id}/unarchive`, { method: 'POST' });
	return res.json();
}

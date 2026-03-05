import type { Note } from '$lib/types';

const BASE = '/api/notes';

export async function getNotes(): Promise<Note[]> {
	const res = await fetch(`${BASE}/`);
	return res.json();
}

export async function getNote(id: number): Promise<Note> {
	const res = await fetch(`${BASE}/${id}`);
	return res.json();
}

export async function createNote(data: { title: string; content?: string }): Promise<Note> {
	const res = await fetch(`${BASE}/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function updateNote(id: number, data: Partial<Note>): Promise<Note> {
	const res = await fetch(`${BASE}/${id}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function deleteNote(id: number): Promise<void> {
	await fetch(`${BASE}/${id}`, { method: 'DELETE' });
}

export async function activateNote(id: number): Promise<Note> {
	const res = await fetch(`${BASE}/${id}/activate`, { method: 'POST' });
	return res.json();
}

export async function deactivateNote(id: number): Promise<Note> {
	const res = await fetch(`${BASE}/${id}/deactivate`, { method: 'POST' });
	return res.json();
}

export async function archiveNote(id: number): Promise<Note> {
	const res = await fetch(`${BASE}/${id}/archive`, { method: 'POST' });
	return res.json();
}

export async function unarchiveNote(id: number): Promise<Note> {
	const res = await fetch(`${BASE}/${id}/unarchive`, { method: 'POST' });
	return res.json();
}

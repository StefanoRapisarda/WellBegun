import type { ReadingList, ReadingListItem } from '$lib/types';

const BASE = '/api/reading-lists';

export async function getReadingLists(): Promise<ReadingList[]> {
	const res = await fetch(`${BASE}/`);
	return res.json();
}

export async function getReadingList(id: number): Promise<ReadingList> {
	const res = await fetch(`${BASE}/${id}`);
	return res.json();
}

export async function createReadingList(data: { title: string; description?: string }): Promise<ReadingList> {
	const res = await fetch(`${BASE}/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function updateReadingList(id: number, data: Partial<ReadingList>): Promise<ReadingList> {
	const res = await fetch(`${BASE}/${id}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function deleteReadingList(id: number): Promise<void> {
	await fetch(`${BASE}/${id}`, { method: 'DELETE' });
}

export async function activateReadingList(id: number): Promise<ReadingList> {
	const res = await fetch(`${BASE}/${id}/activate`, { method: 'POST' });
	return res.json();
}

export async function deactivateReadingList(id: number): Promise<ReadingList> {
	const res = await fetch(`${BASE}/${id}/deactivate`, { method: 'POST' });
	return res.json();
}

export async function addItem(listId: number, data: { source_id: number; position?: number; status?: string; notes?: string }): Promise<ReadingListItem> {
	const res = await fetch(`${BASE}/${listId}/items`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function updateItem(itemId: number, data: { position?: number; status?: string; notes?: string }): Promise<ReadingListItem> {
	const res = await fetch(`${BASE}/items/${itemId}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function removeItem(itemId: number): Promise<void> {
	await fetch(`${BASE}/items/${itemId}`, { method: 'DELETE' });
}

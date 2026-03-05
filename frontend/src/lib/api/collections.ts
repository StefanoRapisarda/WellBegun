import type { Collection, CollectionItem } from '$lib/types';

const BASE = '/api/collections';

export async function getCollections(categoryId?: number): Promise<Collection[]> {
	const url = categoryId != null ? `${BASE}/?category_id=${categoryId}` : `${BASE}/`;
	const res = await fetch(url);
	return res.json();
}

export async function getCollection(id: number): Promise<Collection> {
	const res = await fetch(`${BASE}/${id}`);
	return res.json();
}

export async function createCollection(data: { title: string; category_id: number; description?: string }): Promise<Collection> {
	const res = await fetch(`${BASE}/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function updateCollection(id: number, data: Partial<Collection>): Promise<Collection> {
	const res = await fetch(`${BASE}/${id}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function deleteCollection(id: number): Promise<void> {
	await fetch(`${BASE}/${id}`, { method: 'DELETE' });
}

export async function activateCollection(id: number): Promise<Collection> {
	const res = await fetch(`${BASE}/${id}/activate`, { method: 'POST' });
	return res.json();
}

export async function deactivateCollection(id: number): Promise<Collection> {
	const res = await fetch(`${BASE}/${id}/deactivate`, { method: 'POST' });
	return res.json();
}

export async function archiveCollection(id: number): Promise<Collection> {
	const res = await fetch(`${BASE}/${id}/archive`, { method: 'POST' });
	return res.json();
}

export async function unarchiveCollection(id: number): Promise<Collection> {
	const res = await fetch(`${BASE}/${id}/unarchive`, { method: 'POST' });
	return res.json();
}

export async function addItem(collectionId: number, data: { member_entity_type: string; member_entity_id: number; position?: number; status?: string; notes?: string; header?: string }): Promise<CollectionItem> {
	const res = await fetch(`${BASE}/${collectionId}/items`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	if (!res.ok) {
		const err = await res.json().catch(() => ({}));
		throw new Error(err.detail || `Failed to add item (${res.status})`);
	}
	return res.json();
}

export async function updateItem(itemId: number, data: { position?: number; status?: string; notes?: string; header?: string | null }): Promise<CollectionItem> {
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

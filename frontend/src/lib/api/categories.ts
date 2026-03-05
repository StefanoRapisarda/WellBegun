import type { Category, CategoryStatus } from '$lib/types';

const BASE = '/api/categories';

export async function getCategories(): Promise<Category[]> {
	const res = await fetch(`${BASE}/`);
	return res.json();
}

export async function getCategory(id: number): Promise<Category> {
	const res = await fetch(`${BASE}/${id}`);
	return res.json();
}

export async function createCategory(data: { slug: string; display_name: string; member_entity_type: string }): Promise<Category> {
	const res = await fetch(`${BASE}/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function updateCategory(id: number, data: Partial<Category>): Promise<Category> {
	const res = await fetch(`${BASE}/${id}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function deleteCategory(id: number): Promise<void> {
	await fetch(`${BASE}/${id}`, { method: 'DELETE' });
}

export async function getStatuses(categoryId: number): Promise<CategoryStatus[]> {
	const res = await fetch(`${BASE}/${categoryId}/statuses`);
	return res.json();
}

export async function addStatus(categoryId: number, data: { value: string; position?: number; is_default?: boolean }): Promise<CategoryStatus> {
	const res = await fetch(`${BASE}/${categoryId}/statuses`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function updateStatus(statusId: number, data: { value?: string; position?: number; is_default?: boolean }): Promise<CategoryStatus> {
	const res = await fetch(`${BASE}/statuses/${statusId}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function deleteStatus(statusId: number): Promise<void> {
	await fetch(`${BASE}/statuses/${statusId}`, { method: 'DELETE' });
}

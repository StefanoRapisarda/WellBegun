import type { Project } from '$lib/types';

const BASE = '/api/projects';

export async function getProjects(): Promise<Project[]> {
	const res = await fetch(`${BASE}/`);
	return res.json();
}

export async function getProject(id: number): Promise<Project> {
	const res = await fetch(`${BASE}/${id}`);
	return res.json();
}

export async function createProject(data: { title: string; description?: string; status?: string; start_date?: string }): Promise<Project> {
	const res = await fetch(`${BASE}/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function updateProject(id: number, data: Partial<Project>): Promise<Project> {
	const res = await fetch(`${BASE}/${id}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function deleteProject(id: number): Promise<void> {
	await fetch(`${BASE}/${id}`, { method: 'DELETE' });
}

export async function activateProject(id: number): Promise<Project> {
	const res = await fetch(`${BASE}/${id}/activate`, { method: 'POST' });
	return res.json();
}

export async function deactivateProject(id: number): Promise<Project> {
	const res = await fetch(`${BASE}/${id}/deactivate`, { method: 'POST' });
	return res.json();
}

export async function deactivateAllProjects(): Promise<void> {
	await fetch(`${BASE}/deactivate-all`, { method: 'POST' });
}

export async function archiveProject(id: number): Promise<Project> {
	const res = await fetch(`${BASE}/${id}/archive`, { method: 'POST' });
	return res.json();
}

export async function unarchiveProject(id: number): Promise<Project> {
	const res = await fetch(`${BASE}/${id}/unarchive`, { method: 'POST' });
	return res.json();
}

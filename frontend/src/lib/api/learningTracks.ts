import type { LearningGoal, LearningTrack, LearningTrackItem } from '$lib/types';

const BASE = '/api/learning-tracks';

export async function getLearningTracks(): Promise<LearningTrack[]> {
	const res = await fetch(`${BASE}/`);
	return res.json();
}

export async function getLearningTrack(id: number): Promise<LearningTrack> {
	const res = await fetch(`${BASE}/${id}`);
	return res.json();
}

export async function createLearningTrack(data: { title: string; description?: string }): Promise<LearningTrack> {
	const res = await fetch(`${BASE}/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function updateLearningTrack(id: number, data: Partial<LearningTrack>): Promise<LearningTrack> {
	const res = await fetch(`${BASE}/${id}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function deleteLearningTrack(id: number): Promise<void> {
	await fetch(`${BASE}/${id}`, { method: 'DELETE' });
}

export async function activateLearningTrack(id: number): Promise<LearningTrack> {
	const res = await fetch(`${BASE}/${id}/activate`, { method: 'POST' });
	return res.json();
}

export async function deactivateLearningTrack(id: number): Promise<LearningTrack> {
	const res = await fetch(`${BASE}/${id}/deactivate`, { method: 'POST' });
	return res.json();
}

export async function addItem(trackId: number, data: { source_id: number; position?: number; status?: string; notes?: string }): Promise<LearningTrackItem> {
	const res = await fetch(`${BASE}/${trackId}/items`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function updateItem(itemId: number, data: { position?: number; status?: string; notes?: string }): Promise<LearningTrackItem> {
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

// Goal functions

export async function addGoal(trackId: number, description: string): Promise<LearningGoal> {
	const res = await fetch(`${BASE}/${trackId}/goals`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ description })
	});
	return res.json();
}

export async function updateGoal(goalId: number, data: { description?: string; is_completed?: boolean }): Promise<LearningGoal> {
	const res = await fetch(`${BASE}/goals/${goalId}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function toggleGoal(goalId: number): Promise<LearningGoal> {
	const res = await fetch(`${BASE}/goals/${goalId}/toggle`, { method: 'POST' });
	return res.json();
}

export async function removeGoal(goalId: number): Promise<void> {
	await fetch(`${BASE}/goals/${goalId}`, { method: 'DELETE' });
}

import type { Plan } from '$lib/types';

const BASE = '/api/plans';

export async function getPlans(): Promise<Plan[]> {
	const res = await fetch(`${BASE}/`);
	return res.json();
}

export async function getPlan(id: number): Promise<Plan> {
	const res = await fetch(`${BASE}/${id}`);
	return res.json();
}

export async function createPlan(data: {
	title: string;
	description?: string;
	motivation?: string;
	outcome?: string;
	goal?: string;
	start_date?: string;
	end_date?: string;
	status?: string;
}): Promise<Plan> {
	const res = await fetch(`${BASE}/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function updatePlan(id: number, data: Partial<Plan>): Promise<Plan> {
	const res = await fetch(`${BASE}/${id}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function deletePlan(id: number, cascade: boolean = false): Promise<void> {
	const params = cascade ? '?cascade=true' : '';
	await fetch(`${BASE}/${id}${params}`, { method: 'DELETE' });
}

export async function activatePlan(id: number): Promise<Plan> {
	const res = await fetch(`${BASE}/${id}/activate`, { method: 'POST' });
	return res.json();
}

export async function deactivatePlan(id: number): Promise<Plan> {
	const res = await fetch(`${BASE}/${id}/deactivate`, { method: 'POST' });
	return res.json();
}

export async function archivePlan(id: number): Promise<Plan> {
	const res = await fetch(`${BASE}/${id}/archive`, { method: 'POST' });
	return res.json();
}

export async function addPlanRoleNote(
	planId: number,
	data: { role: string; content: string }
): Promise<{ note_id: number; role: string; title: string; content: string | null }> {
	const res = await fetch(`${BASE}/${planId}/role-notes`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function removePlanRoleNote(planId: number, noteId: number): Promise<void> {
	await fetch(`${BASE}/${planId}/role-notes/${noteId}`, { method: 'DELETE' });
}

export async function addPlanSource(planId: number, sourceId: number, collectionId?: number): Promise<{ ok: boolean; collection_id: number }> {
	const params = collectionId != null ? `?collection_id=${collectionId}` : '';
	const res = await fetch(`${BASE}/${planId}/sources/${sourceId}${params}`, { method: 'POST' });
	return res.json();
}

export async function removePlanSource(planId: number, sourceId: number): Promise<void> {
	await fetch(`${BASE}/${planId}/sources/${sourceId}`, { method: 'DELETE' });
}

export async function addPlanActor(planId: number, actorId: number, collectionId?: number): Promise<{ ok: boolean; collection_id: number }> {
	const params = collectionId != null ? `?collection_id=${collectionId}` : '';
	const res = await fetch(`${BASE}/${planId}/actors/${actorId}${params}`, { method: 'POST' });
	return res.json();
}

export async function removePlanActor(planId: number, actorId: number): Promise<void> {
	await fetch(`${BASE}/${planId}/actors/${actorId}`, { method: 'DELETE' });
}

export interface PlanCollectionInfo {
	collection_id: number;
	title: string;
	predicate: string;
	category_id: number | null;
	items: Array<{
		item_id: number;
		member_entity_type: string;
		member_entity_id: number;
		status: string | null;
		position: number;
		header: string | null;
	}>;
}

export async function createPlanCollection(
	planId: number,
	data: { title: string }
): Promise<{ collection_id: number; title: string }> {
	const res = await fetch(`${BASE}/${planId}/collections`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function createTypedPlanCollection(
	planId: number,
	data: { title: string; member_type: string }
): Promise<{ collection_id: number; title: string }> {
	const res = await fetch(`${BASE}/${planId}/typed-collections`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function getPlanCollections(planId: number): Promise<PlanCollectionInfo[]> {
	const res = await fetch(`${BASE}/${planId}/collections`);
	return res.json();
}

export async function addActivityToGroup(
	planId: number,
	activityId: number,
	header: string
): Promise<{ ok: boolean; collection_id: number }> {
	const res = await fetch(`${BASE}/${planId}/activity-group`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ activity_id: activityId, header })
	});
	return res.json();
}

export async function removeActivityFromGroup(planId: number, activityId: number): Promise<void> {
	await fetch(`${BASE}/${planId}/activity-group/${activityId}`, { method: 'DELETE' });
}

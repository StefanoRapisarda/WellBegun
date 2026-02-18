import type { Plan, PlanItem } from '$lib/types';

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
	start_date?: string;
	end_date?: string;
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

export async function deletePlan(id: number): Promise<void> {
	await fetch(`${BASE}/${id}`, { method: 'DELETE' });
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

export async function addPlanItem(
	planId: number,
	data: { activity_id: number; position?: number; is_done?: boolean; notes?: string; header?: string }
): Promise<PlanItem> {
	const res = await fetch(`${BASE}/${planId}/items`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function updatePlanItem(
	itemId: number,
	data: { position?: number; is_done?: boolean; notes?: string; header?: string | null }
): Promise<PlanItem> {
	const res = await fetch(`${BASE}/items/${itemId}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function removePlanItem(itemId: number): Promise<void> {
	await fetch(`${BASE}/items/${itemId}`, { method: 'DELETE' });
}

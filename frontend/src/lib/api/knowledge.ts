import type { KnowledgeTriple, BoardNode } from '$lib/types';

const BASE = '/api/knowledge';

// ── Triples ──────────────────────────────────────────────────────────────────

export async function getTriples(): Promise<KnowledgeTriple[]> {
	const res = await fetch(`${BASE}/triples`);
	if (!res.ok) throw new Error(`GET /triples failed: ${res.status}`);
	return res.json();
}

export async function getTriplesForEntity(
	entityType: string,
	entityId: number
): Promise<KnowledgeTriple[]> {
	const res = await fetch(`${BASE}/triples/${entityType}/${entityId}`);
	return res.json();
}

export async function createTriple(data: {
	subject_type: string;
	subject_id: number;
	predicate: string;
	object_type: string;
	object_id: number;
}): Promise<KnowledgeTriple> {
	const res = await fetch(`${BASE}/triples`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function swapTripleDirection(id: number): Promise<KnowledgeTriple> {
	const res = await fetch(`${BASE}/triples/${id}/swap`, { method: 'PUT' });
	if (!res.ok) throw new Error(`PUT /triples/${id}/swap failed: ${res.status}`);
	return res.json();
}

export async function updateTriple(
	id: number,
	predicate: string
): Promise<KnowledgeTriple> {
	const res = await fetch(`${BASE}/triples/${id}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ predicate })
	});
	return res.json();
}

export async function deleteTriple(id: number): Promise<void> {
	await fetch(`${BASE}/triples/${id}`, { method: 'DELETE' });
}

// ── Board nodes ──────────────────────────────────────────────────────────────

export async function getBoardNodes(): Promise<BoardNode[]> {
	const res = await fetch(`${BASE}/board`);
	if (!res.ok) throw new Error(`GET /board failed: ${res.status}`);
	return res.json();
}

export async function upsertBoardNode(data: {
	entity_type: string;
	entity_id: number;
	x: number;
	y: number;
}): Promise<BoardNode> {
	const res = await fetch(`${BASE}/board`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function bulkUpsertBoardNodes(
	nodes: { entity_type: string; entity_id: number; x: number; y: number }[]
): Promise<void> {
	await fetch(`${BASE}/board/bulk`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ nodes })
	});
}

export async function updateBoardNode(
	entityType: string,
	entityId: number,
	data: { collapsed?: boolean; x?: number; y?: number }
): Promise<BoardNode> {
	const res = await fetch(`${BASE}/board/${entityType}/${entityId}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function deleteBoardNode(
	entityType: string,
	entityId: number
): Promise<void> {
	await fetch(`${BASE}/board/${entityType}/${entityId}`, { method: 'DELETE' });
}

// ── Populate from focus ──────────────────────────────────────────────────────

export async function populateAll(): Promise<{
	entities_total: number;
	nodes_created: number;
	triples_created: number;
}> {
	const res = await fetch(`${BASE}/populate-all`, { method: 'POST' });
	if (!res.ok) throw new Error(`POST /populate-all failed: ${res.status}`);
	return res.json();
}

export async function populateFromFocus(
	projectIds: number[],
	activityIds: number[]
): Promise<{ entities_total: number; nodes_created: number; triples_created: number }> {
	const res = await fetch(`${BASE}/populate`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ project_ids: projectIds, activity_ids: activityIds })
	});
	if (!res.ok) throw new Error(`POST /populate failed: ${res.status}`);
	return res.json();
}

// ── Predicates ──────────────────────────────────────────────────────────────

export async function getPredicates(): Promise<{
	structural: Record<string, string>;
	semantic: Record<string, { key: string; forward: string; reverse: string }[]>;
}> {
	const res = await fetch(`${BASE}/predicates`);
	if (!res.ok) throw new Error(`GET /predicates failed: ${res.status}`);
	return res.json();
}

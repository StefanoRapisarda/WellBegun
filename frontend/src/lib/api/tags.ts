import type { Tag, EntityTag } from '$lib/types';

const BASE = '/api/tags';

export async function searchTags(q: string): Promise<Tag[]> {
	const res = await fetch(`${BASE}/search?q=${encodeURIComponent(q)}`);
	return res.json();
}

export async function getAllTags(): Promise<Tag[]> {
	const res = await fetch(`${BASE}/`);
	return res.json();
}

export async function getTagsByCategory(category: string): Promise<Tag[]> {
	const res = await fetch(`${BASE}/category/${encodeURIComponent(category)}`);
	return res.json();
}

export async function getEntityTags(targetType: string, targetId: number): Promise<Tag[]> {
	const res = await fetch(`${BASE}/entity/${targetType}/${targetId}`);
	return res.json();
}

export async function getAllEntityTagsBulk(): Promise<Record<string, Tag[]>> {
	const res = await fetch(`${BASE}/entity-tags-bulk`);
	if (!res.ok) throw new Error(`GET /entity-tags-bulk failed: ${res.status}`);
	return res.json();
}

export async function createWildTag(name: string, description?: string, category: string = 'wild', color?: string): Promise<Tag> {
	const res = await fetch(`${BASE}/wild`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ name, description: description || undefined, category, color: color || undefined })
	});
	return res.json();
}

export async function updateWildTag(tagId: number, data: { description?: string | null; category?: string; color?: string | null }): Promise<Tag> {
	const res = await fetch(`${BASE}/wild/${tagId}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	return res.json();
}

export async function moveCategory(fromCategory: string, toCategory: string): Promise<{ ok: boolean; moved: number }> {
	const res = await fetch(`${BASE}/move-category`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ from_category: fromCategory, to_category: toCategory })
	});
	return res.json();
}

export async function deleteWildTag(tagId: number): Promise<void> {
	await fetch(`${BASE}/wild/${tagId}`, { method: 'DELETE' });
}

export async function attachTag(tagId: number, targetType: string, targetId: number): Promise<EntityTag> {
	const res = await fetch(`${BASE}/attach`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ tag_id: tagId, target_type: targetType, target_id: targetId })
	});
	return res.json();
}

export async function detachTag(tagId: number, targetType: string, targetId: number): Promise<void> {
	await fetch(`${BASE}/detach`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ tag_id: tagId, target_type: targetType, target_id: targetId })
	});
}

export interface TagLink {
	entity_type: string;
	entity_id: number;
	direction: 'tags' | 'tagged_by';
	tag_name: string;
	tag_id: number;
	entity_tag_id: number;
}

export async function getTagLinks(entityType: string, entityId: number): Promise<TagLink[]> {
	const res = await fetch(`${BASE}/links/${entityType}/${entityId}`);
	if (!res.ok) throw new Error(`Failed to load tag links: ${res.status}`);
	return res.json();
}

export async function getTagUsageCounts(): Promise<Record<number, number>> {
	const res = await fetch(`${BASE}/usage-counts`);
	if (!res.ok) throw new Error(`GET /usage-counts failed: ${res.status}`);
	return res.json();
}

export async function syncHashtags(content: string, targetType: string, targetId: number): Promise<Tag[]> {
	const res = await fetch(`${BASE}/sync-hashtags`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ content, target_type: targetType, target_id: targetId })
	});
	return res.json();
}

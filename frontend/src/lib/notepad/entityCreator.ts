import type { ParsedEntity } from './types';
import { createNote, updateNote } from '$lib/api/notes';
import { createProject, updateProject } from '$lib/api/projects';
import { createLog, updateLog } from '$lib/api/logs';
import { createActivity, updateActivity } from '$lib/api/activities';
import { createSource, updateSource } from '$lib/api/sources';
import { createActor, updateActor } from '$lib/api/actors';
import { createReadingList, updateReadingList } from '$lib/api/readingLists';
import { createPlan, updatePlan } from '$lib/api/plans';
import { addPlanItem } from '$lib/api/plans';
import { searchTags, createWildTag, attachTag } from '$lib/api/tags';

async function commitTags(tagsStr: string, entityType: string, entityId: number) {
	const names = tagsStr.split(',').map(t => t.trim()).filter(Boolean);
	for (const name of names) {
		const results = await searchTags(name);
		const exact = results.find(t => t.name.toLowerCase() === name.toLowerCase());
		const tag = exact ?? await createWildTag(name, undefined, entityType);
		await attachTag(tag.id, entityType, entityId);
	}
}

export async function commitEntity(entity: ParsedEntity): Promise<{ entityType: string; entityId: number }> {
	const f = entity.fields;
	let result: { entityType: string; entityId: number };

	switch (entity.type) {
		case 'note': {
			const r = await createNote({ title: f.title, content: f.content });
			result = { entityType: 'note', entityId: r.id };
			break;
		}
		case 'project': {
			const r = await createProject({
				title: f.title,
				description: f.description,
				status: f.status,
				start_date: f.start_date
			});
			result = { entityType: 'project', entityId: r.id };
			break;
		}
		case 'log': {
			const r = await createLog({
				log_type: f.log_type ?? 'diary',
				title: f.title,
				content: f.content,
				location: f.location,
				mood: f.mood,
				weather: f.weather,
				day_theme: f.day_theme
			});
			result = { entityType: 'log', entityId: r.id };
			break;
		}
		case 'activity': {
			const duration = f.duration ? Number(f.duration) : undefined;
			const r = await createActivity({
				title: f.title,
				description: f.description,
				duration
			});
			result = { entityType: 'activity', entityId: r.id };
			break;
		}
		case 'source': {
			const r = await createSource({
				title: f.title,
				description: f.description,
				author: f.author,
				content_url: f.content_url,
				source_type: f.source_type
			});
			result = { entityType: 'source', entityId: r.id };
			break;
		}
		case 'actor': {
			const r = await createActor({
				full_name: f.full_name,
				role: f.role,
				affiliation: f.affiliation,
				expertise: f.expertise,
				notes: f.notes,
				email: f.email,
				url: f.url
			});
			result = { entityType: 'actor', entityId: r.id };
			break;
		}
		case 'reading_list': {
			const r = await createReadingList({
				title: f.title,
				description: f.description
			});
			result = { entityType: 'reading_list', entityId: r.id };
			break;
		}
		case 'plan': {
			const r = await createPlan({
				title: f.title,
				description: f.description,
				motivation: f.motivation,
				outcome: f.outcome,
				start_date: f.start_date,
				end_date: f.end_date
			});
			// Create activities from plan items and add them
			if (entity.items && entity.items.length > 0) {
				// Find or create ToDo tag once for all items
				const todoResults = await searchTags('ToDo');
				const todoTag = todoResults.find(t => t.name.toLowerCase() === 'todo') ?? await createWildTag('ToDo', undefined, 'activity');
				// Find plan's entity tag
				const planTagResults = await searchTags(f.title);
				const planTag = planTagResults.find(t => t.entity_type === 'plan' && t.entity_id === r.id);
				for (let i = 0; i < entity.items.length; i++) {
					const item = entity.items[i];
					const activity = await createActivity({ title: item.title });
					await attachTag(todoTag.id, 'activity', activity.id);
					if (planTag) await attachTag(planTag.id, 'activity', activity.id);
					await addPlanItem(r.id, {
						activity_id: activity.id,
						position: i,
						is_done: item.is_done,
						header: item.header ?? undefined
					});
				}
			}
			result = { entityType: 'plan', entityId: r.id };
			break;
		}
	}

	if (f.tags?.trim()) {
		await commitTags(f.tags, result.entityType, result.entityId);
	}

	return result;
}

export async function commitAll(entities: ParsedEntity[]): Promise<Array<{ entityType: string; entityId: number }>> {
	const results: Array<{ entityType: string; entityId: number }> = [];
	for (const entity of entities) {
		if (entity.virtual) continue; // Virtual entities (plan items) are committed by their parent plan
		results.push(await commitEntity(entity));
	}
	return results;
}

async function updateEntity(entity: ParsedEntity): Promise<{ entityType: string; entityId: number }> {
	const f = entity.fields;
	const id = entity.dbId!;

	switch (entity.type) {
		case 'note':
			await updateNote(id, { title: f.title, content: f.content ?? null });
			break;
		case 'project':
			await updateProject(id, {
				title: f.title,
				description: f.description,
				status: f.status,
				start_date: f.start_date
			});
			break;
		case 'log':
			await updateLog(id, {
				log_type: f.log_type ?? 'diary',
				title: f.title,
				content: f.content,
				location: f.location,
				mood: f.mood,
				weather: f.weather,
				day_theme: f.day_theme
			});
			break;
		case 'activity': {
			const duration = f.duration ? Number(f.duration) : undefined;
			await updateActivity(id, {
				title: f.title,
				description: f.description,
				duration
			});
			break;
		}
		case 'source':
			await updateSource(id, {
				title: f.title,
				description: f.description,
				author: f.author,
				content_url: f.content_url,
				source_type: f.source_type
			});
			break;
		case 'actor':
			await updateActor(id, {
				full_name: f.full_name,
				role: f.role,
				affiliation: f.affiliation,
				expertise: f.expertise,
				notes: f.notes,
				email: f.email,
				url: f.url
			});
			break;
		case 'reading_list':
			await updateReadingList(id, {
				title: f.title,
				description: f.description
			});
			break;
		case 'plan':
			await updatePlan(id, {
				title: f.title,
				description: f.description,
				motivation: f.motivation,
				outcome: f.outcome,
				start_date: f.start_date,
				end_date: f.end_date
			});
			break;
	}

	if (f.tags?.trim()) {
		await commitTags(f.tags, entity.type, id);
	}

	return { entityType: entity.type, entityId: id };
}

export async function saveAll(entities: ParsedEntity[]): Promise<Array<{ entityType: string; entityId: number }>> {
	const results: Array<{ entityType: string; entityId: number }> = [];
	for (const entity of entities) {
		if (entity.virtual) continue;
		if (entity.dbId != null) {
			results.push(await updateEntity(entity));
		} else {
			results.push(await commitEntity(entity));
		}
	}
	return results;
}

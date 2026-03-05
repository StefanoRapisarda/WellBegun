import type { ParsedEntity, NotepadEntityType } from './types';
import { ENTITY_CONFIG, PLAN_SUB_SECTIONS } from './types';
import { createNote, updateNote } from '$lib/api/notes';
import { createProject, updateProject } from '$lib/api/projects';
import { createLog, updateLog } from '$lib/api/logs';
import { createActivity, updateActivity } from '$lib/api/activities';
import { createSource, updateSource } from '$lib/api/sources';
import { createActor, updateActor } from '$lib/api/actors';
import { createPlan, updatePlan } from '$lib/api/plans';
import { createCollection, updateCollection, addItem as addCollectionItem } from '$lib/api/collections';
import { getCategories, createCategory } from '$lib/api/categories';
import { createTriple } from '$lib/api/knowledge';
import { searchTags, createWildTag, attachTag } from '$lib/api/tags';

async function commitTags(tagsStr: string, entityType: string, entityId: number) {
	const names = tagsStr.split(',').map(t => t.trim()).filter(Boolean);
	for (const name of names) {
		const results = await searchTags(name);
		const exact = results.find(t => t.name.toLowerCase() === name.toLowerCase());
		const tag = exact ?? await createWildTag(name);
		await attachTag(tag.id, entityType, entityId);
	}
}

/**
 * Pluralize a plan sub-section name for auto-generated collection titles.
 */
function pluralizeSection(section: string): string {
	if (section.endsWith('y') && !section.endsWith('ay') && !section.endsWith('ey') && !section.endsWith('oy')) {
		return section.slice(0, -1) + 'ies'; // activity → activities
	}
	return section + 's'; // motivation → motivations, goal → goals
}

/**
 * Create an entity of any type from a fields record.
 * Routes to the appropriate API create function.
 */
async function createEntityOfType(type: NotepadEntityType, fields: Record<string, string>): Promise<{ entityType: string; entityId: number }> {
	switch (type) {
		case 'note': {
			const r = await createNote({ title: fields.title, content: fields.content });
			return { entityType: 'note', entityId: r.id };
		}
		case 'project': {
			const r = await createProject({
				title: fields.title,
				description: fields.description,
				status: fields.status,
				start_date: fields.start_date
			});
			return { entityType: 'project', entityId: r.id };
		}
		case 'log': {
			const r = await createLog({
				title: fields.title,
				content: fields.content,
				location: fields.location,
				mood: fields.mood,
				weather: fields.weather,
				day_theme: fields.day_theme
			});
			return { entityType: 'log', entityId: r.id };
		}
		case 'activity': {
			const duration = fields.duration ? Number(fields.duration) : undefined;
			const r = await createActivity({
				title: fields.title,
				description: fields.description,
				duration,
				activity_date: fields.date ? fields.date + 'T00:00:00' : undefined
			});
			return { entityType: 'activity', entityId: r.id };
		}
		case 'source': {
			const r = await createSource({
				title: fields.title,
				description: fields.description,
				author: fields.author,
				content_url: fields.content_url,
				source_type: fields.source_type
			});
			return { entityType: 'source', entityId: r.id };
		}
		case 'actor': {
			const r = await createActor({
				full_name: fields.full_name,
				role: fields.role,
				affiliation: fields.affiliation,
				expertise: fields.expertise,
				notes: fields.notes,
				email: fields.email,
				url: fields.url
			});
			return { entityType: 'actor', entityId: r.id };
		}
		case 'plan': {
			const r = await createPlan({
				title: fields.title,
				description: fields.description,
				motivation: fields.motivation,
				outcome: fields.outcome,
				start_date: fields.start_date,
				end_date: fields.end_date
			});
			return { entityType: 'plan', entityId: r.id };
		}
		case 'collection': {
			const categories = await getCategories();
			const cat = categories[0];
			if (!cat) throw new Error('No categories exist');
			const r = await createCollection({ title: fields.title, category_id: cat.id, description: fields.description });
			return { entityType: 'collection', entityId: r.id };
		}
	}
}

/**
 * Find or create a Category for the given member_entity_type.
 * Returns the category so it can be used for collection creation.
 */
async function ensureCategory(memberEntityType: string): Promise<{ id: number; slug: string; statuses?: Array<{ value: string; is_default?: boolean }> }> {
	const categories = await getCategories();
	const existing = categories.find(c => c.member_entity_type === memberEntityType);
	if (existing) return existing;

	// Create a new category for this entity type
	const config = ENTITY_CONFIG[memberEntityType as NotepadEntityType];
	const displayName = memberEntityType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) + 's';
	const slug = memberEntityType + 's';
	return await createCategory({ slug, display_name: displayName, member_entity_type: memberEntityType });
}

/**
 * For non-container entity types with items: create a Collection wrapping the child entities.
 */
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
				duration,
				activity_date: f.date ? f.date + 'T00:00:00' : undefined
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
		case 'plan': {
			const r = await createPlan({
				title: f.title,
				description: f.description,
				motivation: f.motivation,
				outcome: f.outcome,
				start_date: f.start_date,
				end_date: f.end_date
			});
			if (entity.items && entity.items.length > 0) {
				// Group items by sub-section
				const groups = new Map<string | undefined, typeof entity.items>();
				for (const item of entity.items) {
					const key = item.subSection;
					if (!groups.has(key)) groups.set(key, []);
					groups.get(key)!.push(item);
				}

				// Helper: create a child entity, deriving type from the item's own subSection
				async function createPlanChild(
					item: { title: string; fields?: Record<string, string>; header?: string | null; is_done: boolean; subSection?: string },
					position: number
				): Promise<{ entityType: string; entityId: number }> {
					const sub = item.subSection;
					const childType: NotepadEntityType = sub
						? (PLAN_SUB_SECTIONS[sub] ?? 'activity')
						: 'activity';
					if (childType === 'activity') {
						const act = await createActivity({
							title: item.title,
							description: item.fields?.description,
							duration: item.fields?.duration ? Number(item.fields.duration) : undefined,
							plan_id: r.id,
							position,
							status: item.is_done ? 'done' : 'todo',
							header: item.header ?? undefined
						});
						return { entityType: 'activity', entityId: act.id };
					}
					const itemConfig = ENTITY_CONFIG[childType];
					const itemFields = item.fields ?? { [itemConfig.primaryField]: item.title };
					return createEntityOfType(childType, itemFields);
				}

				for (const [section, sectionItems] of groups) {
					const entityType: NotepadEntityType = section
						? (PLAN_SUB_SECTIONS[section] ?? 'activity')
						: 'activity';
					const predicate = section ? `has ${section}` : 'has activity';

					if (sectionItems.length === 1) {
						// Single item → standalone entity linked directly to plan
						const item = sectionItems[0];
						const child = await createPlanChild(item, 0);

						// Activities are linked via plan_id FK; only create graph triples for other entity types
						if (child.entityType !== 'activity') {
							await createTriple({
								subject_type: 'plan',
								subject_id: r.id,
								predicate,
								object_type: child.entityType,
								object_id: child.entityId
							});
						}
						// Tag child with its sub-section name (e.g. "motivation" on a note),
						// but skip when the tag would be redundant (e.g. "activity" on an activity)
						if (item.subSection && item.subSection !== child.entityType) {
							await commitTags(item.subSection, child.entityType, child.entityId);
						}
					} else {
						// Multiple items → create collection with auto-generated name
						const sectionPlural = pluralizeSection(section ?? 'activity');
						const collTitle = `${f.title} ${sectionPlural}`;
						const collDesc = `${sectionPlural.charAt(0).toUpperCase() + sectionPlural.slice(1)} of the plan ${f.title}`;

						const cat = await ensureCategory(entityType);
						const coll = await createCollection({
							title: collTitle,
							category_id: cat.id,
							description: collDesc
						});

						// Link collection to plan
						await createTriple({
							subject_type: 'plan',
							subject_id: r.id,
							predicate,
							object_type: 'collection',
							object_id: coll.id
						});

						for (let i = 0; i < sectionItems.length; i++) {
							const item = sectionItems[i];
							const child = await createPlanChild(item, i);

							const defaultStatus = (cat.statuses as Array<{ value: string; is_default?: boolean }> | undefined)
								?.find(s => s.is_default)?.value
								?? (cat.statuses as Array<{ value: string }> | undefined)?.[0]?.value;
							await addCollectionItem(coll.id, {
								member_entity_type: entityType,
								member_entity_id: child.entityId,
								position: i,
								status: defaultStatus,
								header: item.header ?? undefined
							});

							await createTriple({
								subject_type: 'collection',
								subject_id: coll.id,
								predicate: 'contains',
								object_type: child.entityType,
								object_id: child.entityId
							});

							// Tag child with its sub-section name, skip redundant tags
							if (item.subSection && item.subSection !== child.entityType) {
								await commitTags(item.subSection, child.entityType, child.entityId);
							}
						}
					}
				}
			}
			result = { entityType: 'plan', entityId: r.id };
			break;
		}
		case 'collection': {
			// member_type is set by the parser when a non-container type has items
			// (e.g. @note with - items becomes a collection with member_type: 'note')
			const memberType = (f.member_type as NotepadEntityType | undefined) ?? undefined;

			// Resolve category: use explicit slug, or find/create one matching member_type
			let cat: Awaited<ReturnType<typeof ensureCategory>> | undefined;
			if (f.category) {
				const categories = await getCategories();
				cat = categories.find(c => c.slug === f.category) ?? categories[0];
			} else if (memberType) {
				cat = await ensureCategory(memberType);
			} else {
				const categories = await getCategories();
				cat = categories[0];
			}
			if (!cat) throw new Error('No categories exist — create a category first');

			const r = await createCollection({
				title: f.title,
				category_id: cat.id,
				description: f.description
			});
			if (entity.items && entity.items.length > 0) {
				const itemEntityType = memberType ?? (cat as { member_entity_type?: string }).member_entity_type ?? 'source';
				for (let i = 0; i < entity.items.length; i++) {
					const item = entity.items[i];
					const itemConfig = ENTITY_CONFIG[itemEntityType as NotepadEntityType];
					const itemFields = item.fields ?? { [itemConfig?.primaryField ?? 'title']: item.title };

					// Create the member entity using the generic helper
					const child = await createEntityOfType(itemEntityType as NotepadEntityType, itemFields);

					const defaultStatus = (cat.statuses as Array<{ value: string; is_default?: boolean }> | undefined)
						?.find(s => s.is_default)?.value
						?? (cat.statuses as Array<{ value: string }> | undefined)?.[0]?.value;
					await addCollectionItem(r.id, {
						member_entity_type: itemEntityType,
						member_entity_id: child.entityId,
						position: i,
						status: defaultStatus,
						header: item.header ?? undefined
					});

					// Knowledge triple: collection "contains" child entity
					await createTriple({
						subject_type: 'collection',
						subject_id: r.id,
						predicate: 'contains',
						object_type: itemEntityType,
						object_id: child.entityId
					});
				}
			}
			result = { entityType: 'collection', entityId: r.id };
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
		if (entity.virtual) continue; // Virtual entities are committed by their parent
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
				duration,
				activity_date: f.date ? f.date + 'T00:00:00' : undefined
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
		case 'collection':
			await updateCollection(id, {
				title: f.title,
				description: f.description
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

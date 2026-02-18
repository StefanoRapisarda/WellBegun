<script lang="ts">
	import type { KnowledgeTriple } from '$lib/types';
	import { selectedEntity, clearSelectedEntity } from '$lib/stores/selectedEntity';
	import { triples, loadTriples } from '$lib/stores/knowledgeGraph';
	import { projects } from '$lib/stores/projects';
	import { logs } from '$lib/stores/logs';
	import { notes } from '$lib/stores/notes';
	import { activities } from '$lib/stores/activities';
	import { sources } from '$lib/stores/sources';
	import { actors } from '$lib/stores/actors';
	import { readingLists } from '$lib/stores/readingLists';
	import { entityTagsVersion } from '$lib/stores/tags';
	import { triggerEntityTagsRefresh } from '$lib/stores/tags';
	import { updateTriple, deleteTriple, createTriple } from '$lib/api/knowledge';
	import { getTagLinks, detachTag, type TagLink } from '$lib/api/tags';
	import PanelContainer from '../shared/PanelContainer.svelte';
	import ConfirmDialog from '../shared/ConfirmDialog.svelte';
	import { onMount } from 'svelte';
	import { structuralPredicates, loadPredicates, semanticRelations, customPredicates } from '$lib/stores/predicates';

	const ENTITY_COLORS: Record<string, string> = {
		project: '#5c7a99',
		log: '#8b7355',
		note: '#6b8e6b',
		activity: '#b5838d',
		source: '#c9a227',
		actor: '#8b4557',
		reading_list: '#5f9ea0'
	};

	interface UnifiedLink {
		key: string;
		otherType: string;
		otherId: number;
		otherTitle: string;
		direction: 'outgoing' | 'incoming';
		predicate: string;
		tripleId: number | null;
		hasTag: boolean;
		tagName: string | null;
		tagId: number | null;
		entityTagId: number | null;
		tagDirection: 'tags' | 'tagged_by' | null;
	}

	let confirmDeleteKey: string | null = $state(null);
	let showPredicateMenuKey: string | null = $state(null);
	let tagLinks = $state<TagLink[]>([]);

	function getEntityTitle(type: string, id: number): string {
		switch (type) {
			case 'project': return $projects.find(e => e.id === id)?.title ?? `Project #${id}`;
			case 'log': return $logs.find(e => e.id === id)?.title ?? `Log #${id}`;
			case 'note': return $notes.find(e => e.id === id)?.title ?? `Note #${id}`;
			case 'activity': return $activities.find(e => e.id === id)?.title ?? `Activity #${id}`;
			case 'source': return $sources.find(e => e.id === id)?.title ?? `Source #${id}`;
			case 'actor': return $actors.find(e => e.id === id)?.full_name ?? `Actor #${id}`;
			case 'reading_list': return $readingLists.find(e => e.id === id)?.title ?? `ReadingList #${id}`;
			default: return `${type} #${id}`;
		}
	}

	function formatType(type: string): string {
		return type.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
	}

	// Reload tag links when entity changes or tags change
	async function loadTagLinks() {
		if (!$selectedEntity) {
			tagLinks = [];
			return;
		}
		try {
			tagLinks = await getTagLinks($selectedEntity.type, $selectedEntity.id);
		} catch (e) {
			console.warn('Failed to load tag links:', e);
			tagLinks = [];
		}
	}

	// React to selectedEntity changes
	$effect(() => {
		if ($selectedEntity) {
			loadTagLinks();
		} else {
			tagLinks = [];
		}
	});

	// React to entity tag changes (when tags are attached/detached in other panels)
	$effect(() => {
		$entityTagsVersion;
		if ($selectedEntity) {
			loadTagLinks();
		}
	});

	// Get triples involving the selected entity
	let entityTriples = $derived.by(() => {
		if (!$selectedEntity || !Array.isArray($triples)) return [];
		const { type, id } = $selectedEntity;
		return $triples.filter(t =>
			(t.subject_type === type && t.subject_id === id) ||
			(t.object_type === type && t.object_id === id)
		);
	});

	// Unified link list: merge tag links and graph triples
	let unifiedLinks = $derived.by((): UnifiedLink[] => {
		if (!$selectedEntity) return [];
		const { type: selType, id: selId } = $selectedEntity;

		// Build map of graph links keyed by "otherType:otherId"
		const graphMap = new Map<string, { triple: KnowledgeTriple; otherType: string; otherId: number; direction: 'outgoing' | 'incoming'; predicate: string }>();
		for (const t of entityTriples) {
			const isSubject = t.subject_type === selType && t.subject_id === selId;
			const otherType = isSubject ? t.object_type : t.subject_type;
			const otherId = isSubject ? t.object_id : t.subject_id;
			const key = `${otherType}:${otherId}`;
			graphMap.set(key, {
				triple: t,
				otherType,
				otherId,
				direction: isSubject ? 'outgoing' : 'incoming',
				predicate: t.predicate
			});
		}

		// Build map of tag links keyed by "otherType:otherId"
		const tagMap = new Map<string, TagLink>();
		for (const tl of tagLinks) {
			const key = `${tl.entity_type}:${tl.entity_id}`;
			tagMap.set(key, tl);
		}

		// Merge into unified links
		const allKeys = new Set([...graphMap.keys(), ...tagMap.keys()]);
		const links: UnifiedLink[] = [];

		for (const key of allKeys) {
			const graph = graphMap.get(key);
			const tag = tagMap.get(key);

			if (graph && tag) {
				// Both exist: use triple's predicate and direction, mark hasTag
				links.push({
					key,
					otherType: graph.otherType,
					otherId: graph.otherId,
					otherTitle: getEntityTitle(graph.otherType, graph.otherId),
					direction: graph.direction,
					predicate: graph.predicate,
					tripleId: graph.triple.id,
					hasTag: true,
					tagName: tag.tag_name,
					tagId: tag.tag_id,
					entityTagId: tag.entity_tag_id,
					tagDirection: tag.direction
				});
			} else if (tag) {
				// Tag-only: infer direction from tag direction
				const direction: 'outgoing' | 'incoming' = tag.direction === 'tags' ? 'outgoing' : 'incoming';
				const subjectType = direction === 'outgoing' ? selType : tag.entity_type;
				const objectType = direction === 'outgoing' ? tag.entity_type : selType;
				const defaultPred = $structuralPredicates[`${subjectType}:${objectType}`] ?? 'related to';
				links.push({
					key,
					otherType: tag.entity_type,
					otherId: tag.entity_id,
					otherTitle: getEntityTitle(tag.entity_type, tag.entity_id),
					direction,
					predicate: defaultPred,
					tripleId: null,
					hasTag: true,
					tagName: tag.tag_name,
					tagId: tag.tag_id,
					entityTagId: tag.entity_tag_id,
					tagDirection: tag.direction
				});
			} else if (graph) {
				// Triple-only
				links.push({
					key,
					otherType: graph.otherType,
					otherId: graph.otherId,
					otherTitle: getEntityTitle(graph.otherType, graph.otherId),
					direction: graph.direction,
					predicate: graph.predicate,
					tripleId: graph.triple.id,
					hasTag: false,
					tagName: null,
					tagId: null,
					entityTagId: null,
					tagDirection: null
				});
			}
		}

		// Sort by entity type then title
		links.sort((a, b) => {
			const typeCmp = a.otherType.localeCompare(b.otherType);
			if (typeCmp !== 0) return typeCmp;
			return a.otherTitle.localeCompare(b.otherTitle);
		});

		return links;
	});

	let hasAnyLinks = $derived(unifiedLinks.length > 0);

	// Get suggested predicates for a link based on direction and entity types
	function getSuggestedPredicates(link: UnifiedLink): { label: string; group?: string }[] {
		if (!$selectedEntity) return [{ label: 'related to' }];
		const selType = $selectedEntity.type;
		const subjectType = link.direction === 'outgoing' ? selType : link.otherType;
		const objectType = link.direction === 'outgoing' ? link.otherType : selType;
		const key1 = `${subjectType}:${objectType}`;
		const key2 = `${objectType}:${subjectType}`;
		const results: { label: string; group?: string }[] = [];
		// Structural defaults first
		if ($structuralPredicates[key1]) results.push({ label: $structuralPredicates[key1], group: 'Structural' });
		if ($structuralPredicates[key2] && $structuralPredicates[key2] !== $structuralPredicates[key1]) {
			results.push({ label: $structuralPredicates[key2], group: 'Structural' });
		}
		results.push({ label: 'related to', group: 'Structural' });
		// Semantic relations by category
		for (const [category, predicates] of Object.entries($semanticRelations)) {
			for (const pred of predicates) {
				results.push({ label: pred.forward, group: category });
			}
		}
		// Custom predicates
		for (const cp of $customPredicates) {
			results.push({ label: cp.forward, group: cp.category });
		}
		return results;
	}

	// ── Edit predicate handler ──────────────────────────────────────────────

	async function handleSelectPredicate(link: UnifiedLink, predicate: string) {
		if (!$selectedEntity) return;
		if (link.tripleId !== null) {
			await updateTriple(link.tripleId, predicate);
		} else {
			// Tag-only: create a new triple
			const selType = $selectedEntity.type;
			const selId = $selectedEntity.id;
			const subjectType = link.direction === 'outgoing' ? selType : link.otherType;
			const subjectId = link.direction === 'outgoing' ? selId : link.otherId;
			const objectType = link.direction === 'outgoing' ? link.otherType : selType;
			const objectId = link.direction === 'outgoing' ? link.otherId : selId;
			await createTriple({
				subject_type: subjectType,
				subject_id: subjectId,
				predicate,
				object_type: objectType,
				object_id: objectId
			});
		}
		await loadTriples();
		showPredicateMenuKey = null;
	}

	// ── Flip direction handler ──────────────────────────────────────────────

	async function handleFlipDirection(link: UnifiedLink) {
		if (!$selectedEntity) return;
		const selType = $selectedEntity.type;
		const selId = $selectedEntity.id;

		if (link.tripleId !== null) {
			// Delete old triple and create new one with swapped subject/object
			await deleteTriple(link.tripleId);
			const newSubjectType = link.direction === 'outgoing' ? link.otherType : selType;
			const newSubjectId = link.direction === 'outgoing' ? link.otherId : selId;
			const newObjectType = link.direction === 'outgoing' ? selType : link.otherType;
			const newObjectId = link.direction === 'outgoing' ? selId : link.otherId;
			const newPredicate = $structuralPredicates[`${newSubjectType}:${newObjectType}`] ?? 'related to';
			await createTriple({
				subject_type: newSubjectType,
				subject_id: newSubjectId,
				predicate: newPredicate,
				object_type: newObjectType,
				object_id: newObjectId
			});
		} else {
			// Tag-only: create a triple in the flipped direction
			const subjectType = link.direction === 'outgoing' ? link.otherType : selType;
			const subjectId = link.direction === 'outgoing' ? link.otherId : selId;
			const objectType = link.direction === 'outgoing' ? selType : link.otherType;
			const objectId = link.direction === 'outgoing' ? selId : link.otherId;
			const newPredicate = $structuralPredicates[`${subjectType}:${objectType}`] ?? 'related to';
			await createTriple({
				subject_type: subjectType,
				subject_id: subjectId,
				predicate: newPredicate,
				object_type: objectType,
				object_id: objectId
			});
		}
		await loadTriples();
	}

	// ── Delete handler ──────────────────────────────────────────────────────

	async function handleDelete(link: UnifiedLink) {
		// Use one operation — backend sync handles the other side
		if (link.hasTag && link.tagId !== null) {
			if (link.tagDirection === 'tags') {
				await detachTag(link.tagId, link.otherType, link.otherId);
			} else if (link.tagDirection === 'tagged_by' && $selectedEntity) {
				await detachTag(link.tagId, $selectedEntity.type, $selectedEntity.id);
			}
		} else if (link.tripleId !== null) {
			await deleteTriple(link.tripleId);
		}
		triggerEntityTagsRefresh();
		await loadTagLinks();
		await loadTriples();
		confirmDeleteKey = null;
	}

	onMount(() => { loadPredicates(); loadTriples(); });
</script>

<PanelContainer title="Links" panelId="links" color="#6b7280">
	{#if !$selectedEntity}
		<p class="empty">Click on any entity in a panel to see its links.</p>
	{:else}
		<div class="selected-header">
			<span class="selected-dot" style:background={ENTITY_COLORS[$selectedEntity.type] ?? '#888'}></span>
			<span class="selected-type">{formatType($selectedEntity.type)}</span>
			<span class="selected-title">{$selectedEntity.title}</span>
			<button class="btn-clear" onclick={clearSelectedEntity} title="Clear selection">&times;</button>
		</div>

		{#if !hasAnyLinks}
			<p class="empty">No links found. Tag entities or connect them in the Graph tab.</p>
		{/if}

		{#each unifiedLinks as link (link.key)}
			<div class="link-item">
				<div class="link-row">
					<button
						class="link-direction-btn"
						onclick={() => handleFlipDirection(link)}
						title={link.direction === 'outgoing' ? 'Outgoing — click to flip' : 'Incoming — click to flip'}
					>
						{link.direction === 'outgoing' ? '→' : '←'}
					</button>
					<span class="link-dot" style:background={ENTITY_COLORS[link.otherType] ?? '#888'}></span>
					<span class="link-type">{formatType(link.otherType)}</span>
					<span class="link-title">{link.otherTitle}</span>
					{#if link.hasTag}
						<span class="tag-badge" title="via tag: {link.tagName}">tag</span>
					{/if}
				</div>
				<div class="link-predicate-row">
					<button
						class="predicate-label"
						onclick={() => showPredicateMenuKey = showPredicateMenuKey === link.key ? null : link.key}
						title="Click to change predicate"
					>
						{link.predicate}
						<span class="predicate-caret">▾</span>
					</button>
					<button
						class="btn-remove"
						onclick={() => (confirmDeleteKey = link.key)}
						title="Remove link"
					>
						×
					</button>
				</div>
				{#if showPredicateMenuKey === link.key}
					{@const preds = getSuggestedPredicates(link)}
					{@const groups = [...new Set(preds.map(p => p.group).filter(Boolean))]}
					<div class="predicate-menu">
						{#each groups as group}
							<div class="predicate-group-label">{group}</div>
							{#each preds.filter(p => p.group === group) as pred}
								<button
									class="menu-item"
									class:active={link.predicate === pred.label}
									onclick={() => handleSelectPredicate(link, pred.label)}
								>
									{pred.label}
								</button>
							{/each}
						{/each}
					</div>
				{/if}
			</div>
		{/each}
	{/if}
</PanelContainer>

<ConfirmDialog
	open={confirmDeleteKey !== null}
	message="Remove this link?"
	onConfirm={() => {
		const link = unifiedLinks.find(l => l.key === confirmDeleteKey);
		if (link) handleDelete(link);
	}}
	onCancel={() => (confirmDeleteKey = null)}
/>

<style>
	.selected-header {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 8px 10px;
		background: #f3f4f6;
		border: 1px solid #e5e7eb;
		border-radius: 6px;
		margin-bottom: 12px;
	}
	.selected-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.selected-type {
		font-size: 0.65rem;
		color: #9ca3af;
		text-transform: uppercase;
		letter-spacing: 0.3px;
		font-weight: 600;
	}
	.selected-title {
		font-size: 0.85rem;
		font-weight: 500;
		color: #1f2937;
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.btn-clear {
		background: none;
		border: none;
		cursor: pointer;
		font-size: 1.1rem;
		color: #9ca3af;
		padding: 0 2px;
		line-height: 1;
	}
	.btn-clear:hover {
		color: #ef4444;
	}

	.link-item {
		padding: 8px 0;
		border-bottom: 1px solid #e5e7eb;
	}
	.link-item:last-child {
		border-bottom: none;
	}
	.link-row {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.link-direction-btn {
		font-size: 0.85rem;
		color: #9ca3af;
		width: 20px;
		height: 20px;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		background: none;
		border: 1px solid transparent;
		border-radius: 3px;
		cursor: pointer;
		padding: 0;
		transition: all 0.15s;
	}
	.link-direction-btn:hover {
		color: #374151;
		border-color: #d1d5db;
		background: #f9fafb;
	}
	.link-dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.link-type {
		font-size: 0.6rem;
		color: #9ca3af;
		text-transform: uppercase;
		letter-spacing: 0.3px;
		font-weight: 600;
		flex-shrink: 0;
	}
	.link-title {
		font-size: 0.82rem;
		color: #374151;
		font-weight: 500;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.tag-badge {
		font-size: 0.55rem;
		color: #9ca3af;
		background: #f3f4f6;
		border: 1px solid #e5e7eb;
		border-radius: 3px;
		padding: 1px 4px;
		flex-shrink: 0;
		text-transform: uppercase;
		letter-spacing: 0.3px;
		font-weight: 600;
	}

	.link-predicate-row {
		display: flex;
		align-items: center;
		gap: 4px;
		margin-top: 4px;
		margin-left: 26px;
	}
	.predicate-label {
		font-size: 0.75rem;
		color: #6b7280;
		background: #f9fafb;
		border: 1px solid #e5e7eb;
		border-radius: 4px;
		padding: 2px 8px;
		cursor: pointer;
		transition: all 0.15s;
	}
	.predicate-label:hover {
		border-color: #9ca3af;
		color: #374151;
	}
	.predicate-caret {
		font-size: 0.65rem;
		color: #9ca3af;
		margin-left: 2px;
	}
	.btn-remove {
		font-size: 0.85rem;
		padding: 0 4px;
		background: none;
		border: 1px solid #fecaca;
		border-radius: 3px;
		cursor: pointer;
		color: #f87171;
		line-height: 1.2;
	}
	.btn-remove:hover {
		background: #fee2e2;
		color: #ef4444;
	}

	.predicate-menu {
		margin-top: 4px;
		margin-left: 26px;
		padding: 4px;
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 6px;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
		display: flex;
		flex-wrap: wrap;
		gap: 3px;
		max-height: 240px;
		overflow-y: auto;
	}
	.predicate-group-label {
		width: 100%;
		font-size: 0.6rem;
		font-weight: 600;
		color: #9ca3af;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		padding: 4px 4px 1px;
		margin-top: 2px;
	}
	.menu-item {
		font-size: 0.7rem;
		padding: 3px 8px;
		border: 1px solid #e5e7eb;
		border-radius: 4px;
		background: #f9fafb;
		cursor: pointer;
		color: #6b7280;
		transition: all 0.12s;
	}
	.menu-item:hover {
		background: #e5e7eb;
		color: #374151;
	}
	.menu-item.active {
		background: #6b7280;
		color: white;
		border-color: #6b7280;
	}

	.empty {
		text-align: center;
		color: #9ca3af;
		font-size: 0.85rem;
		padding: 16px 0;
	}
</style>

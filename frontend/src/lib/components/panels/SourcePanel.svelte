<script lang="ts">
	import type { Tag, Source } from '$lib/types';
	import { sources, loadSources } from '$lib/stores/sources';
	import { tags, loadTags, entityTagsVersion } from '$lib/stores/tags';
	import { projects } from '$lib/stores/projects';
	import { activities } from '$lib/stores/activities';
	import { dateFilter, isItemVisible, selectedFilterTags, isTagVisible, showArchived, showActiveRelated, activeEntityTagIds, isActiveRelated } from '$lib/stores/dateFilter';
	import { getLastUsedTags, setLastUsedTags } from '$lib/stores/lastUsedTags';
	import { deleteSource, activateSource, deactivateSource, archiveSource } from '$lib/api/sources';
	import { getEntityTags, attachTag, detachTag } from '$lib/api/tags';
	import PanelContainer from '../shared/PanelContainer.svelte';
	import ConfirmDialog from '../shared/ConfirmDialog.svelte';
	import SourceForm from '../forms/SourceForm.svelte';
	import TagInput from '../shared/TagInput.svelte';
	import TagBadge from '../shared/TagBadge.svelte';
	import Timestamp from '../shared/Timestamp.svelte';
	import { selectEntity } from '$lib/stores/selectedEntity';
	import { selectable } from '$lib/actions/selectable';

	// Panel-level tag filter state
	let panelSelectedTagIds = $state<number[]>([]);
	let panelFilterMode = $state<'or' | 'and'>('or');

	let availablePanelTags = $derived(() => {
		const tagMap = new Map<number, Tag>();
		for (const source of $sources) {
			const sourceTags = entityTags[source.id] || [];
			for (const tag of sourceTags) {
				tagMap.set(tag.id, tag);
			}
		}
		return Array.from(tagMap.values()).sort((a, b) =>
			`${a.category}:${a.name}`.localeCompare(`${b.category}:${b.name}`)
		);
	});

	function passesPanelFilter(itemTags: Tag[]): boolean {
		if (panelSelectedTagIds.length === 0) return true;
		if (panelFilterMode === 'or') {
			return itemTags.some(t => panelSelectedTagIds.includes(t.id));
		} else {
			return panelSelectedTagIds.every(id => itemTags.some(t => t.id === id));
		}
	}

	let filteredSources = $derived($sources.filter(s =>
		($showArchived || !s.is_archived) &&
		isItemVisible(s, $dateFilter) &&
		isTagVisible(entityTags[s.id] || [], $selectedFilterTags) &&
		passesPanelFilter(entityTags[s.id] || []) &&
		(!$showActiveRelated || isActiveRelated(entityTags[s.id] || [], $activeEntityTagIds))
	));

	let showForm = $state(false);
	let editingIds = $state<Set<number>>(new Set());
	let confirmDelete: number | null = $state(null);
	let expandedId: number | null = $state(null);
	let entityTags = $state<Record<number, Tag[]>>({});

	function handlePanelTagToggle(tagId: number) {
		if (panelSelectedTagIds.includes(tagId)) {
			panelSelectedTagIds = panelSelectedTagIds.filter(id => id !== tagId);
		} else {
			panelSelectedTagIds = [...panelSelectedTagIds, tagId];
		}
	}

	function handlePanelModeToggle() {
		panelFilterMode = panelFilterMode === 'or' ? 'and' : 'or';
	}

	async function handleDelete(id: number) {
		await deleteSource(id);
		await Promise.all([loadSources(), loadTags()]);
		confirmDelete = null;
	}

	async function toggleActive(id: number, isActive: boolean) {
		if (isActive) { await deactivateSource(id); } else { await activateSource(id); }
		await loadSources();
	}

	async function handleArchive(id: number) {
		await archiveSource(id);
		await loadSources();
	}

	async function toggleExpand(id: number) {
		if (expandedId === id) { expandedId = null; return; }
		expandedId = id;
		if (!entityTags[id]) {
			entityTags[id] = await getEntityTags('source', id);
		}
	}

	async function handleAttach(sourceId: number, tag: Tag) {
		await attachTag(tag.id, 'source', sourceId);
		entityTags[sourceId] = await getEntityTags('source', sourceId);
		setLastUsedTags('source', entityTags[sourceId]);
	}

	async function handleDetach(sourceId: number, tag: Tag) {
		await detachTag(tag.id, 'source', sourceId);
		entityTags[sourceId] = await getEntityTags('source', sourceId);
		setLastUsedTags('source', entityTags[sourceId]);
	}

	async function handleCreate(sourceId: number) {
		// Get tags for active projects and activities
		const activeProjectIds = $projects.filter(p => p.is_active).map(p => p.id);
		const activeActivityIds = $activities.filter(a => a.is_active).map(a => a.id);

		const activeEntityTags = $tags.filter(t =>
			(t.entity_type === 'project' && t.entity_id && activeProjectIds.includes(t.entity_id)) ||
			(t.entity_type === 'activity' && t.entity_id && activeActivityIds.includes(t.entity_id))
		);

		// Also get last-used tags (filtering out inactive ones)
		const activeProjectsList = $projects.filter(p => p.is_active);
		const activeActivitiesList = $activities.filter(a => a.is_active);
		const lastUsed = getLastUsedTags('source', activeProjectsList, activeActivitiesList);

		// Combine and deduplicate
		const allTags = [...activeEntityTags];
		for (const tag of lastUsed) {
			if (!allTags.some(t => t.id === tag.id)) {
				allTags.push(tag);
			}
		}

		for (const tag of allTags) {
			try {
				await attachTag(tag.id, 'source', sourceId);
			} catch (e) {
				console.warn(`Failed to attach tag ${tag.id} to source ${sourceId}:`, e);
			}
		}

		if (allTags.length > 0) {
			entityTags[sourceId] = await getEntityTags('source', sourceId);
		}
	}

	async function loadAllTags() {
		const entries = await Promise.all(
			$sources.map(async (source) => [source.id, await getEntityTags('source', source.id)] as const)
		);
		const updated: Record<number, Tag[]> = {};
		for (const [id, tags] of entries) updated[id] = tags;
		entityTags = updated;
	}

	$effect(() => {
		const _ = $entityTagsVersion;  // Subscribe to version changes
		if ($sources) loadAllTags();
	});
</script>

<PanelContainer
	title="Sources"
	panelId="source"
	color="#c9a227"
	onAdd={() => (showForm = !showForm)}
	availableTags={availablePanelTags()}
	selectedTagIds={panelSelectedTagIds}
	filterMode={panelFilterMode}
	onTagToggle={handlePanelTagToggle}
	onModeToggle={handlePanelModeToggle}
>
	{#if showForm}
		<div class="inline-form">
			<SourceForm onDone={() => (showForm = false)} onCreate={handleCreate} />
		</div>
	{/if}

	{#each filteredSources as source (source.id)}
		{#if editingIds.has(source.id)}
			<div class="inline-form">
				<SourceForm editData={source} onDone={() => { editingIds.delete(source.id); editingIds = new Set(editingIds); }} />
			</div>
		{:else}
			<div class="item" class:is-archived={source.is_archived} use:selectable={{ entityType: 'source', entityId: source.id }}>
				<div class="item-actions">
					<button class="btn-tags" onclick={() => toggleExpand(source.id)}>Tags</button>
					<button class="btn-active" class:active={source.is_active} onclick={() => toggleActive(source.id, source.is_active)}>
						{source.is_active ? 'Active' : 'Inactive'}
					</button>
					<button class="btn-archive" onclick={() => handleArchive(source.id)}>Archive</button>
					<button class="btn-delete" onclick={() => (confirmDelete = source.id)}>Delete</button>
				</div>
				<div class="item-card" ondblclick={() => selectEntity('source', source.id, source.title)} role="button" tabindex="-1">
					<div class="item-header">
						<button class="item-title" ondblclick={() => { editingIds.add(source.id); editingIds = new Set(editingIds); }}>{source.title}</button>
						{#if source.is_archived}<span class="archived-badge">archived</span>{/if}
						{#if source.source_type}
							<span class="type-badge">{source.source_type}</span>
						{/if}
					</div>
					{#if source.description}
						<p class="item-desc">{source.description}</p>
					{/if}
					{#if source.content_url}
						<a href={source.content_url} target="_blank" rel="noopener noreferrer" class="item-url">{source.content_url}</a>
					{/if}
					{#if entityTags[source.id]?.length}
						<div class="tag-badges">
							{#each entityTags[source.id] as tag (tag.id)}
								<TagBadge {tag} removable onRemove={() => handleDetach(source.id, tag)} />
							{/each}
						</div>
					{/if}
					<Timestamp date={source.created_at} />
				</div>
				{#if expandedId === source.id}
					<div class="tag-section">
						<TagInput
							attachedTags={entityTags[source.id] || []}
							targetType="source"
							targetId={source.id}
							onAttach={(tag) => handleAttach(source.id, tag)}
							onDetach={(tag) => handleDetach(source.id, tag)}
							onClose={() => (expandedId = null)}
						/>
					</div>
				{/if}
			</div>
		{/if}
	{/each}

	{#if $sources.length === 0}
		<p class="empty">No sources yet.</p>
	{:else if filteredSources.length === 0}
		<p class="empty">No sources match current filters.</p>
	{/if}
</PanelContainer>

<ConfirmDialog
	open={confirmDelete !== null}
	message="Delete this source?"
	onConfirm={() => confirmDelete && handleDelete(confirmDelete)}
	onCancel={() => (confirmDelete = null)}
/>

<style>
	.inline-form { padding: 10px; background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; margin-bottom: 12px; }
	.item { padding: 12px 0; border-bottom: 1px solid #e5e7eb; }
	.item-actions { display: flex; gap: 6px; margin-bottom: 6px; }
	.item-card { padding: 10px 12px; background: #fafafa; border: 1px solid #e5e7eb; border-radius: 8px; }
	.item-header { display: flex; align-items: center; gap: 8px; }
	.item-title { flex: 1; background: none; border: none; cursor: pointer; font-weight: 500; font-size: 0.9rem; text-align: left; padding: 0; color: #111827; }
	.item-desc { font-size: 0.8rem; color: #6b7280; margin: 8px 0 0; }
	.item-url { font-size: 0.75rem; color: #3b82f6; display: block; margin-top: 4px; }
	.type-badge { font-size: 0.7rem; padding: 2px 6px; background: #fef3c7; border-radius: 4px; color: #92400e; }
	.btn-active { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #f3f4f6; color: #6b7280; }
	.btn-active.active { background: #dcfce7; color: #16a34a; border-color: #bbf7d0; }
	.tag-badges { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
	.btn-tags { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #f9fafb; color: #6b7280; }
	.btn-archive { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #fef3c7; color: #92400e; }
	.btn-delete { font-size: 0.75rem; padding: 2px 8px; background: #fee2e2; color: #ef4444; border: 1px solid #fecaca; border-radius: 4px; cursor: pointer; }
	.tag-section { margin-top: 8px; padding: 8px; background: #f9fafb; border-radius: 6px; }
	.empty { text-align: center; color: #9ca3af; font-size: 0.875rem; }
	.is-archived .item-card { opacity: 0.55; border-style: dashed; }
	.archived-badge { font-size: 0.55rem; padding: 1px 5px; background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; border-radius: 3px; text-transform: uppercase; letter-spacing: 0.3px; font-weight: 600; flex-shrink: 0; }
</style>

<script lang="ts">
	import type { Tag, Actor } from '$lib/types';
	import { actors, loadActors } from '$lib/stores/actors';
	import { tags, loadTags, entityTagsVersion } from '$lib/stores/tags';
	import { projects } from '$lib/stores/projects';
	import { activities } from '$lib/stores/activities';
	import { dateFilter, isItemVisible, selectedFilterTags, isTagVisible, showArchived, showActiveRelated, activeEntityTagIds, isActiveRelated } from '$lib/stores/dateFilter';
	import { getLastUsedTags, setLastUsedTags } from '$lib/stores/lastUsedTags';
	import { deleteActor, activateActor, deactivateActor, archiveActor } from '$lib/api/actors';
	import { getEntityTags, attachTag, detachTag } from '$lib/api/tags';
	import PanelContainer from '../shared/PanelContainer.svelte';
	import ConfirmDialog from '../shared/ConfirmDialog.svelte';
	import ActorForm from '../forms/ActorForm.svelte';
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
		for (const actor of $actors) {
			const actorTags = entityTags[actor.id] || [];
			for (const tag of actorTags) {
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

	let filteredActors = $derived($actors.filter(a =>
		($showArchived || !a.is_archived) &&
		isItemVisible(a, $dateFilter) &&
		isTagVisible(entityTags[a.id] || [], $selectedFilterTags) &&
		passesPanelFilter(entityTags[a.id] || []) &&
		(!$showActiveRelated || isActiveRelated(entityTags[a.id] || [], $activeEntityTagIds))
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
		await deleteActor(id);
		await Promise.all([loadActors(), loadTags()]);
		confirmDelete = null;
	}

	async function toggleActive(id: number, isActive: boolean) {
		if (isActive) { await deactivateActor(id); } else { await activateActor(id); }
		await loadActors();
	}

	async function handleArchive(id: number) {
		await archiveActor(id);
		await loadActors();
	}

	async function toggleExpand(id: number) {
		if (expandedId === id) { expandedId = null; return; }
		expandedId = id;
		if (!entityTags[id]) {
			entityTags[id] = await getEntityTags('actor', id);
		}
	}

	async function handleAttach(actorId: number, tag: Tag) {
		await attachTag(tag.id, 'actor', actorId);
		entityTags[actorId] = await getEntityTags('actor', actorId);
		setLastUsedTags('actor', entityTags[actorId]);
	}

	async function handleDetach(actorId: number, tag: Tag) {
		await detachTag(tag.id, 'actor', actorId);
		entityTags[actorId] = await getEntityTags('actor', actorId);
		setLastUsedTags('actor', entityTags[actorId]);
	}

	async function handleCreate(actorId: number) {
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
		const lastUsed = getLastUsedTags('actor', activeProjectsList, activeActivitiesList);

		// Combine and deduplicate
		const allTags = [...activeEntityTags];
		for (const tag of lastUsed) {
			if (!allTags.some(t => t.id === tag.id)) {
				allTags.push(tag);
			}
		}

		for (const tag of allTags) {
			try {
				await attachTag(tag.id, 'actor', actorId);
			} catch (e) {
				console.warn(`Failed to attach tag ${tag.id} to actor ${actorId}:`, e);
			}
		}

		if (allTags.length > 0) {
			entityTags[actorId] = await getEntityTags('actor', actorId);
		}
	}

	async function loadAllTags() {
		const entries = await Promise.all(
			$actors.map(async (actor) => [actor.id, await getEntityTags('actor', actor.id)] as const)
		);
		const updated: Record<number, Tag[]> = {};
		for (const [id, tags] of entries) updated[id] = tags;
		entityTags = updated;
	}

	$effect(() => {
		const _ = $entityTagsVersion;  // Subscribe to version changes
		if ($actors) loadAllTags();
	});
</script>

<PanelContainer
	title="Actors"
	panelId="actor"
	color="#8b4557"
	onAdd={() => (showForm = !showForm)}
	availableTags={availablePanelTags()}
	selectedTagIds={panelSelectedTagIds}
	filterMode={panelFilterMode}
	onTagToggle={handlePanelTagToggle}
	onModeToggle={handlePanelModeToggle}
>
	{#if showForm}
		<div class="inline-form">
			<ActorForm onDone={() => (showForm = false)} onCreate={handleCreate} />
		</div>
	{/if}

	{#each filteredActors as actor (actor.id)}
		{#if editingIds.has(actor.id)}
			<div class="inline-form">
				<ActorForm editData={actor} onDone={() => { editingIds.delete(actor.id); editingIds = new Set(editingIds); }} />
			</div>
		{:else}
			<div class="item" class:is-archived={actor.is_archived} use:selectable={{ entityType: 'actor', entityId: actor.id }}>
				<div class="item-actions">
					<button class="btn-tags" onclick={() => toggleExpand(actor.id)}>Tags</button>
					<button class="btn-active" class:active={actor.is_active} onclick={() => toggleActive(actor.id, actor.is_active)}>
						{actor.is_active ? 'Active' : 'Inactive'}
					</button>
					<button class="btn-archive" onclick={() => handleArchive(actor.id)}>Archive</button>
					<button class="btn-delete" onclick={() => (confirmDelete = actor.id)}>Delete</button>
				</div>
				<div class="item-card" ondblclick={() => selectEntity('actor', actor.id, actor.full_name)} role="button" tabindex="-1">
					<div class="item-header">
						<button class="item-title" ondblclick={() => { editingIds.add(actor.id); editingIds = new Set(editingIds); }}>{actor.full_name}</button>
						{#if actor.is_archived}<span class="archived-badge">archived</span>{/if}
						{#if actor.role}
							<span class="role-badge">{actor.role}</span>
						{/if}
					</div>
					{#if actor.affiliation}
						<p class="item-desc">{actor.affiliation}</p>
					{/if}
					{#if entityTags[actor.id]?.length}
						<div class="tag-badges">
							{#each entityTags[actor.id] as tag (tag.id)}
								<TagBadge {tag} removable onRemove={() => handleDetach(actor.id, tag)} />
							{/each}
						</div>
					{/if}
					<Timestamp date={actor.created_at} />
				</div>
				{#if expandedId === actor.id}
					<div class="tag-section">
						<TagInput
							attachedTags={entityTags[actor.id] || []}
							targetType="actor"
							targetId={actor.id}
							onAttach={(tag) => handleAttach(actor.id, tag)}
							onDetach={(tag) => handleDetach(actor.id, tag)}
							onClose={() => (expandedId = null)}
						/>
					</div>
				{/if}
			</div>
		{/if}
	{/each}

	{#if $actors.length === 0}
		<p class="empty">No actors yet.</p>
	{:else if filteredActors.length === 0}
		<p class="empty">No actors match current filters.</p>
	{/if}
</PanelContainer>

<ConfirmDialog
	open={confirmDelete !== null}
	message="Delete this actor?"
	onConfirm={() => confirmDelete && handleDelete(confirmDelete)}
	onCancel={() => (confirmDelete = null)}
/>

<style>
	.inline-form { padding: 10px; background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; margin-bottom: 12px; }
	.item { padding: 12px 0; border-bottom: 1px solid #e5e7eb; }
	.item-actions { display: flex; gap: 6px; margin-bottom: 6px; }
	.item-card { padding: 10px 12px; background: #fafafa; border: 1px solid #e5e7eb; border-radius: 8px; }
	.item-header { display: flex; align-items: center; gap: 8px; }
	.item-title { flex: 1; background: none; border: none; cursor: pointer; font-weight: 500; font-size: 0.9rem; text-align: left; padding: 0; color: #111827; }
	.item-desc { font-size: 0.8rem; color: #6b7280; margin: 8px 0 0; }
	.role-badge { font-size: 0.7rem; padding: 2px 6px; background: #fee2e2; border-radius: 4px; color: #991b1b; }
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

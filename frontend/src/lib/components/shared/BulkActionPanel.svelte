<script lang="ts">
	import { get } from 'svelte/store';
	import { panelSelection, selectedCount, selectedEntities, type EntityType } from '$lib/stores/panelSelection';
	import { projects, loadProjects } from '$lib/stores/projects';
	import { logs, loadLogs } from '$lib/stores/logs';
	import { notes, loadNotes } from '$lib/stores/notes';
	import { activities, loadActivities } from '$lib/stores/activities';
	import { sources, loadSources } from '$lib/stores/sources';
	import { actors, loadActors } from '$lib/stores/actors';
	import { collections, loadCollections } from '$lib/stores/collections';
	import { loadTags, triggerEntityTagsRefresh } from '$lib/stores/tags';
	import { pendingCollectionMembers } from '$lib/stores/pendingCollection';
	import { panels, togglePanel } from '$lib/stores/panels';

	import { deleteProject, activateProject, deactivateProject, archiveProject } from '$lib/api/projects';
	import { deleteLog, activateLog, deactivateLog, archiveLog } from '$lib/api/logs';
	import { deleteNote, archiveNote } from '$lib/api/notes';
	import { deleteActivity, activateActivity, deactivateActivity, archiveActivity } from '$lib/api/activities';
	import { deleteSource, activateSource, deactivateSource, archiveSource } from '$lib/api/sources';
	import { deleteActor, activateActor, deactivateActor, archiveActor } from '$lib/api/actors';
	import { deleteCollection, activateCollection, deactivateCollection } from '$lib/api/collections';
	import { getEntityTags, attachTag, detachTag } from '$lib/api/tags';

	import ConfirmDialog from './ConfirmDialog.svelte';
	import TagInput from './TagInput.svelte';
	import type { Tag } from '$lib/types';

	const SUPPORTS_ACTIVE: EntityType[] = ['project', 'log', 'activity', 'source', 'actor', 'collection'];
	const SUPPORTS_ARCHIVE: EntityType[] = ['project', 'log', 'note', 'activity', 'source', 'actor'];

	let showConfirmDelete = $state(false);
	let showCollectionDeleteChoice = $state(false);
	let showTagInput = $state(false);
	let bulkTags = $state<Tag[]>([]);
	let busy = $state(false);

	let count = $derived($selectedCount);
	let entities = $derived($selectedEntities);

	let allActivatable = $derived(entities.every(e => SUPPORTS_ACTIVE.includes(e.entityType)));
	let allArchivable = $derived(entities.every(e => SUPPORTS_ARCHIVE.includes(e.entityType)));

	async function reloadAllStores() {
		await Promise.all([
			loadProjects(),
			loadLogs(),
			loadNotes(),
			loadActivities(),
			loadSources(),
			loadActors(),
			loadCollections(),
			loadTags()
		]);
		triggerEntityTagsRefresh();
	}

	const activators: Record<EntityType, ((id: number) => Promise<any>) | null> = {
		project: activateProject,
		log: activateLog,
		note: null,
		activity: activateActivity,
		source: activateSource,
		actor: activateActor,
		plan: null,
		collection: activateCollection,
	};

	const deactivators: Record<EntityType, ((id: number) => Promise<any>) | null> = {
		project: deactivateProject,
		log: deactivateLog,
		note: null,
		activity: deactivateActivity,
		source: deactivateSource,
		actor: deactivateActor,
		plan: null,
		collection: deactivateCollection,
	};

	const archivers: Record<EntityType, ((id: number) => Promise<any>) | null> = {
		project: archiveProject,
		log: archiveLog,
		note: archiveNote,
		activity: archiveActivity,
		source: archiveSource,
		actor: archiveActor,
		plan: null,
		collection: null,
	};

	const deleters: Record<EntityType, (id: number) => Promise<void>> = {
		project: deleteProject,
		log: deleteLog,
		note: deleteNote,
		activity: deleteActivity,
		source: deleteSource,
		actor: deleteActor,
		plan: async (id) => { const { deletePlan } = await import('$lib/api/plans'); await deletePlan(id); },
		collection: deleteCollection,
	};

	async function bulkActivate() {
		busy = true;
		for (const e of entities) {
			const fn = activators[e.entityType];
			if (fn) await fn(e.entityId);
		}
		await reloadAllStores();
		panelSelection.clear();
		busy = false;
	}

	async function bulkDeactivate() {
		busy = true;
		for (const e of entities) {
			const fn = deactivators[e.entityType];
			if (fn) await fn(e.entityId);
		}
		await reloadAllStores();
		panelSelection.clear();
		busy = false;
	}

	async function bulkArchive() {
		busy = true;
		for (const e of entities) {
			const fn = archivers[e.entityType];
			if (fn) await fn(e.entityId);
		}
		await reloadAllStores();
		panelSelection.clear();
		busy = false;
	}

	let hasCollections = $derived(entities.some(e => e.entityType === 'collection'));

	function requestBulkDelete() {
		if (hasCollections) {
			showCollectionDeleteChoice = true;
		} else {
			showConfirmDelete = true;
		}
	}

	async function bulkDeleteCollectionMembers() {
		const collectionEntities = entities.filter(e => e.entityType === 'collection');
		for (const ce of collectionEntities) {
			const col = get(collections).find((c: any) => c.id === ce.entityId);
			if (!col) continue;
			for (const item of col.items) {
				if (item.member_entity_type === 'source') await deleteSource(item.member_entity_id);
				else if (item.member_entity_type === 'activity') await deleteActivity(item.member_entity_id);
				else if (item.member_entity_type === 'note') await deleteNote(item.member_entity_id);
			}
		}
	}

	async function bulkDelete(deleteCollectionMembers = false) {
		busy = true;
		if (deleteCollectionMembers) {
			await bulkDeleteCollectionMembers();
		}
		for (const e of entities) {
			await deleters[e.entityType](e.entityId);
		}
		await reloadAllStores();
		panelSelection.clear();
		showConfirmDelete = false;
		showCollectionDeleteChoice = false;
		busy = false;
	}

	function handleTagsClick() {
		showTagInput = !showTagInput;
		if (showTagInput && entities.length > 0) {
			loadFirstEntityTags();
		}
	}

	async function loadFirstEntityTags() {
		const first = entities[0];
		bulkTags = await getEntityTags(first.entityType, first.entityId);
	}

	async function handleBulkAttach(tag: Tag) {
		busy = true;
		for (const e of entities) {
			await attachTag(tag.id, e.entityType, e.entityId);
		}
		bulkTags = [...bulkTags, tag];
		await reloadAllStores();
		busy = false;
	}

	async function handleBulkDetach(tag: Tag) {
		busy = true;
		for (const e of entities) {
			await detachTag(tag.id, e.entityType, e.entityId);
		}
		bulkTags = bulkTags.filter(t => t.id !== tag.id);
		await reloadAllStores();
		busy = false;
	}

	// Resolve entity titles from stores
	const TITLE_FIELDS: Record<EntityType, string> = {
		project: 'title',
		log: 'title',
		note: 'title',
		activity: 'title',
		source: 'title',
		actor: 'full_name',
		plan: 'title',
		collection: 'title',
	};

	let allSameType = $derived(
		entities.length >= 2 && entities.every(e => e.entityType === entities[0].entityType)
	);

	function getEntityTitle(type: EntityType, id: number): string {
		const store = storeMap[type];
		if (!store) return `${type} #${id}`;
		const items = get(store) as any[];
		const entity = items.find((item: any) => item.id === id);
		if (!entity) return `${type} #${id}`;
		const field = TITLE_FIELDS[type];
		return entity[field] ?? `${type} #${id}`;
	}

	function makeCollection() {
		if (!allSameType) return;
		const members = entities.map(e => ({
			entityType: e.entityType,
			entityId: e.entityId,
			title: getEntityTitle(e.entityType, e.entityId)
		}));
		pendingCollectionMembers.set(members);
		// Open collection panel if not visible
		const currentPanels = get(panels);
		const collectionPanel = currentPanels.find(p => p.id === 'collection');
		if (collectionPanel && !collectionPanel.visible) {
			togglePanel('collection');
		}
		panelSelection.clear();
	}

	const storeMap: Record<EntityType, any> = {
		project: projects,
		log: logs,
		note: notes,
		activity: activities,
		source: sources,
		actor: actors,
		plan: null,
		collection: collections,
	};

</script>

{#if count >= 2}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="bulk-panel" onclick={(e) => e.stopPropagation()}>
		<span class="count">{count} selected</span>
		<div class="divider"></div>
		<button class="bulk-btn tags" onclick={handleTagsClick} disabled={busy}>Tags</button>
		{#if allSameType}
			<button class="bulk-btn collect" onclick={makeCollection} disabled={busy}>Collect</button>
		{/if}
		{#if allActivatable}
			<button class="bulk-btn inactive" onclick={bulkDeactivate} disabled={busy}>Inactive</button>
		{/if}
		{#if allArchivable}
			<button class="bulk-btn archive" onclick={bulkArchive} disabled={busy}>Archive</button>
		{/if}
		<button class="bulk-btn delete" onclick={requestBulkDelete} disabled={busy}>Delete</button>
		<div class="divider"></div>
		<button class="bulk-btn clear" onclick={() => panelSelection.clear()} disabled={busy}>Clear</button>

		{#if showTagInput}
			<div class="tag-input-row">
				<TagInput
					attachedTags={bulkTags}
					targetType={entities[0]?.entityType ?? 'project'}
					targetId={entities[0]?.entityId ?? 0}
					onAttach={handleBulkAttach}
					onDetach={handleBulkDetach}
					onClose={() => (showTagInput = false)}
				/>
			</div>
		{/if}
	</div>
{/if}

<ConfirmDialog
	open={showConfirmDelete}
	message={`Delete ${count} selected entities? This cannot be undone.`}
	onConfirm={() => bulkDelete(false)}
	onCancel={() => (showConfirmDelete = false)}
/>

{#if showCollectionDeleteChoice}
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<div class="coll-dialog-overlay" onclick={() => showCollectionDeleteChoice = false} onkeydown={(e) => e.key === 'Escape' && (showCollectionDeleteChoice = false)} role="dialog" tabindex="-1">
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<div class="coll-dialog-content" onclick={(e) => e.stopPropagation()} role="document">
			<p class="coll-dialog-title">Delete {count} selected entities?</p>
			<p class="coll-dialog-message">Some selected items are collections. Do you also want to delete the member entities inside those collections?</p>
			<div class="coll-dialog-actions">
				<button class="coll-btn coll-btn-cancel" onclick={() => showCollectionDeleteChoice = false}>Cancel</button>
				<button class="coll-btn coll-btn-keep" onclick={() => bulkDelete(false)}>Keep members</button>
				<button class="coll-btn coll-btn-delete-all" onclick={() => bulkDelete(true)}>Delete all</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.bulk-panel {
		position: fixed;
		bottom: 24px;
		left: 50%;
		transform: translateX(-50%);
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 10px 16px;
		background: white;
		border: 1px solid #d1d5db;
		border-radius: 12px;
		box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
		z-index: 1000;
		flex-wrap: wrap;
	}
	.count {
		font-size: 0.85rem;
		font-weight: 600;
		color: #374151;
		white-space: nowrap;
	}
	.divider {
		width: 1px;
		height: 20px;
		background: #e5e7eb;
	}
	.bulk-btn {
		font-size: 0.8rem;
		padding: 5px 12px;
		border-radius: 6px;
		border: 1px solid #d1d5db;
		cursor: pointer;
		background: #f9fafb;
		color: #374151;
		white-space: nowrap;
	}
	.bulk-btn:hover:not(:disabled) { background: #f3f4f6; }
	.bulk-btn:disabled { opacity: 0.5; cursor: not-allowed; }
	.bulk-btn.tags { background: #f9fafb; color: #6b7280; }
	.bulk-btn.collect { background: #f5f3fa; color: #7c6f9e; border-color: #d4cfe6; }
	.bulk-btn.inactive { background: #f3f4f6; color: #6b7280; }
	.bulk-btn.archive { background: #fef3c7; color: #92400e; border-color: #fde68a; }
	.bulk-btn.delete { background: #fee2e2; color: #ef4444; border-color: #fecaca; }
	.bulk-btn.clear { background: white; color: #9ca3af; border-color: #e5e7eb; }
	.tag-input-row {
		width: 100%;
		margin-top: 4px;
	}
	/* ── Collection delete dialog ── */
	.coll-dialog-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.4);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1100;
	}
	.coll-dialog-content {
		background: white;
		border-radius: 8px;
		padding: 24px;
		min-width: 340px;
		box-shadow: 0 8px 30px rgba(0, 0, 0, 0.2);
	}
	.coll-dialog-title {
		font-size: 0.95rem;
		font-weight: 600;
		margin: 0 0 8px;
		color: #111827;
	}
	.coll-dialog-message {
		font-size: 0.85rem;
		color: #6b7280;
		margin: 0 0 20px;
	}
	.coll-dialog-actions {
		display: flex;
		gap: 8px;
		justify-content: flex-end;
	}
	.coll-btn {
		padding: 8px 14px;
		border-radius: 6px;
		border: 1px solid #d1d5db;
		cursor: pointer;
		font-size: 0.82rem;
		font-weight: 500;
	}
	.coll-btn-cancel { background: white; color: #374151; }
	.coll-btn-cancel:hover { background: #f3f4f6; }
	.coll-btn-keep { background: #f0fdf4; color: #16a34a; border-color: #bbf7d0; }
	.coll-btn-keep:hover { background: #dcfce7; }
	.coll-btn-delete-all { background: #ef4444; color: white; border-color: #ef4444; }
	.coll-btn-delete-all:hover { background: #dc2626; }
</style>

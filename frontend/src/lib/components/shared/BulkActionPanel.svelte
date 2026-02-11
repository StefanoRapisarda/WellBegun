<script lang="ts">
	import { panelSelection, selectedCount, selectedEntities, type EntityType } from '$lib/stores/panelSelection';
	import { loadProjects } from '$lib/stores/projects';
	import { loadLogs } from '$lib/stores/logs';
	import { loadNotes } from '$lib/stores/notes';
	import { loadActivities } from '$lib/stores/activities';
	import { loadSources } from '$lib/stores/sources';
	import { loadActors } from '$lib/stores/actors';
	import { loadReadingLists } from '$lib/stores/readingLists';
	import { loadLearningTracks } from '$lib/stores/learningTracks';
	import { loadTags, triggerEntityTagsRefresh } from '$lib/stores/tags';

	import { deleteProject, activateProject, deactivateProject, archiveProject } from '$lib/api/projects';
	import { deleteLog, activateLog, deactivateLog, archiveLog } from '$lib/api/logs';
	import { deleteNote, archiveNote } from '$lib/api/notes';
	import { deleteActivity, activateActivity, deactivateActivity, archiveActivity } from '$lib/api/activities';
	import { deleteSource, activateSource, deactivateSource, archiveSource } from '$lib/api/sources';
	import { deleteActor, activateActor, deactivateActor, archiveActor } from '$lib/api/actors';
	import { deleteReadingList, activateReadingList, deactivateReadingList } from '$lib/api/readingLists';
	import { deleteLearningTrack, activateLearningTrack, deactivateLearningTrack } from '$lib/api/learningTracks';
	import { getEntityTags, attachTag, detachTag } from '$lib/api/tags';

	import ConfirmDialog from './ConfirmDialog.svelte';
	import TagInput from './TagInput.svelte';
	import type { Tag } from '$lib/types';

	const SUPPORTS_ACTIVE: EntityType[] = ['project', 'log', 'activity', 'source', 'actor', 'reading_list', 'learning_track'];
	const SUPPORTS_ARCHIVE: EntityType[] = ['project', 'log', 'note', 'activity', 'source', 'actor'];

	let showConfirmDelete = $state(false);
	let showTagInput = $state(false);
	let bulkTags = $state<Tag[]>([]);
	let busy = $state(false);

	let count = $derived($selectedCount);
	let entities = $derived($selectedEntities);

	let hasActivatable = $derived(entities.some(e => SUPPORTS_ACTIVE.includes(e.entityType)));
	let hasArchivable = $derived(entities.some(e => SUPPORTS_ARCHIVE.includes(e.entityType)));

	async function reloadAllStores() {
		await Promise.all([
			loadProjects(),
			loadLogs(),
			loadNotes(),
			loadActivities(),
			loadSources(),
			loadActors(),
			loadReadingLists(),
			loadLearningTracks(),
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
		reading_list: activateReadingList,
		learning_track: activateLearningTrack,
	};

	const deactivators: Record<EntityType, ((id: number) => Promise<any>) | null> = {
		project: deactivateProject,
		log: deactivateLog,
		note: null,
		activity: deactivateActivity,
		source: deactivateSource,
		actor: deactivateActor,
		reading_list: deactivateReadingList,
		learning_track: deactivateLearningTrack,
	};

	const archivers: Record<EntityType, ((id: number) => Promise<any>) | null> = {
		project: archiveProject,
		log: archiveLog,
		note: archiveNote,
		activity: archiveActivity,
		source: archiveSource,
		actor: archiveActor,
		reading_list: null,
		learning_track: null,
	};

	const deleters: Record<EntityType, (id: number) => Promise<void>> = {
		project: deleteProject,
		log: deleteLog,
		note: deleteNote,
		activity: deleteActivity,
		source: deleteSource,
		actor: deleteActor,
		reading_list: deleteReadingList,
		learning_track: deleteLearningTrack,
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

	async function bulkDelete() {
		busy = true;
		for (const e of entities) {
			await deleters[e.entityType](e.entityId);
		}
		await reloadAllStores();
		panelSelection.clear();
		showConfirmDelete = false;
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
</script>

{#if count >= 2}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="bulk-panel" onclick={(e) => e.stopPropagation()}>
		<span class="count">{count} selected</span>
		<div class="divider"></div>
		<button class="bulk-btn tags" onclick={handleTagsClick} disabled={busy}>Tags</button>
		{#if hasActivatable}
			<button class="bulk-btn active" onclick={bulkActivate} disabled={busy}>Active</button>
			<button class="bulk-btn inactive" onclick={bulkDeactivate} disabled={busy}>Inactive</button>
		{/if}
		{#if hasArchivable}
			<button class="bulk-btn archive" onclick={bulkArchive} disabled={busy}>Archive</button>
		{/if}
		<button class="bulk-btn delete" onclick={() => (showConfirmDelete = true)} disabled={busy}>Delete</button>
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
	onConfirm={bulkDelete}
	onCancel={() => (showConfirmDelete = false)}
/>

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
	.bulk-btn.active { background: #dcfce7; color: #16a34a; border-color: #bbf7d0; }
	.bulk-btn.inactive { background: #f3f4f6; color: #6b7280; }
	.bulk-btn.archive { background: #fef3c7; color: #92400e; border-color: #fde68a; }
	.bulk-btn.delete { background: #fee2e2; color: #ef4444; border-color: #fecaca; }
	.bulk-btn.clear { background: white; color: #9ca3af; border-color: #e5e7eb; }
	.tag-input-row {
		width: 100%;
		margin-top: 4px;
	}
</style>

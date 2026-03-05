<script lang="ts">
	import type { Tag, Log } from '$lib/types';
	import { logs, loadLogs } from '$lib/stores/logs';
	import { tags, loadTags, entityTagsVersion } from '$lib/stores/tags';
	import { projects } from '$lib/stores/projects';
	import { activities } from '$lib/stores/activities';
	import { dateFilter, isItemVisible, selectedFilterTags, isTagVisible, showArchived, showActiveRelated, activeEntityTagIds, isActiveRelated } from '$lib/stores/dateFilter';
	import { setLastUsedTags } from '$lib/stores/lastUsedTags';
	import { deleteLog, activateLog, deactivateLog, archiveLog } from '$lib/api/logs';
	import { getEntityTags, attachTag, detachTag } from '$lib/api/tags';
	import PanelContainer from '../shared/PanelContainer.svelte';
	import ConfirmDialog from '../shared/ConfirmDialog.svelte';
	import DiaryForm from '../forms/DiaryForm.svelte';
	import TagInput from '../shared/TagInput.svelte';
	import TagBadge from '../shared/TagBadge.svelte';
	import MarkdownContent from '../shared/MarkdownContent.svelte';
	import Timestamp from '../shared/Timestamp.svelte';
	import { selectEntity } from '$lib/stores/selectedEntity';
	import { selectable } from '$lib/actions/selectable';


	// Panel-level tag filter state
	let panelSelectedTagIds = $state<number[]>([]);
	let panelFilterMode = $state<'or' | 'and'>('or');

	let availablePanelTags = $derived(() => {
		const tagMap = new Map<number, Tag>();
		for (const log of $logs) {
			const logTags = entityTags[log.id] || [];
			for (const tag of logTags) {
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

	let filteredLogs = $derived($logs.filter(l =>
		($showArchived || !l.is_archived) &&
		isItemVisible(l, $dateFilter) &&
		isTagVisible(entityTags[l.id] || [], $selectedFilterTags) &&
		passesPanelFilter(entityTags[l.id] || []) &&
		(!$showActiveRelated || isActiveRelated(entityTags[l.id] || [], $activeEntityTagIds))
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
		await deleteLog(id);
		await Promise.all([loadLogs(), loadTags()]);
		confirmDelete = null;
	}

	async function toggleActive(id: number, isActive: boolean) {
		if (isActive) { await deactivateLog(id); } else { await activateLog(id); }
		await loadLogs();
	}

	async function handleArchive(id: number) {
		await archiveLog(id);
		await loadLogs();
	}

	async function toggleExpand(id: number) {
		if (expandedId === id) { expandedId = null; return; }
		expandedId = id;
		entityTags[id] = await getEntityTags('log', id);
	}

	async function handleAttach(logId: number, tag: Tag) {
		await attachTag(tag.id, 'log', logId);
		entityTags[logId] = await getEntityTags('log', logId);
		setLastUsedTags('log', entityTags[logId]);
	}

	async function handleDetach(logId: number, tag: Tag) {
		await detachTag(tag.id, 'log', logId);
		entityTags[logId] = await getEntityTags('log', logId);
		setLastUsedTags('log', entityTags[logId]);
	}

	async function handleCreate(logId: number) {
		// Get tags for active projects and activities
		const activeProjectIds = $projects.filter(p => p.is_active && !p.is_archived).map(p => p.id);
		const activeActivityIds = $activities.filter(a => a.is_active && !a.is_archived).map(a => a.id);

		const activeEntityTags = $tags.filter(t =>
			(t.entity_type === 'project' && t.entity_id && activeProjectIds.includes(t.entity_id)) ||
			(t.entity_type === 'activity' && t.entity_id && activeActivityIds.includes(t.entity_id))
		);

		for (const tag of activeEntityTags) {
			try {
				await attachTag(tag.id, 'log', logId);
			} catch (e) {
				console.warn(`Failed to attach tag ${tag.id} to log ${logId}:`, e);
			}
		}

		if (activeEntityTags.length > 0) {
			entityTags[logId] = await getEntityTags('log', logId);
		}
	}

	async function loadAllTags() {
		const entries = await Promise.all(
			$logs.map(async (log) => [log.id, await getEntityTags('log', log.id)] as const)
		);
		const updated: Record<number, Tag[]> = {};
		for (const [id, tags] of entries) updated[id] = tags;
		entityTags = updated;
	}

	$effect(() => {
		const _ = $entityTagsVersion;  // Subscribe to version changes
		if ($logs) loadAllTags();
	});
</script>

<PanelContainer
	title="Logs"
	panelId="log"
	color="#8b7355"
	onAdd={() => (showForm = !showForm)}
	availableTags={availablePanelTags()}
	selectedTagIds={panelSelectedTagIds}
	filterMode={panelFilterMode}
	onTagToggle={handlePanelTagToggle}
	onModeToggle={handlePanelModeToggle}
>
	{#if showForm}
		<div class="inline-form">
			<DiaryForm onCreate={handleCreate} onDone={() => (showForm = false)} />
		</div>
	{/if}

	{#each filteredLogs as log (log.id)}
		{#if editingIds.has(log.id)}
			<DiaryForm editData={log} onDone={() => { editingIds.delete(log.id); editingIds = new Set(editingIds); }} />
		{:else}
			<div class="item" class:is-archived={log.is_archived} use:selectable={{ entityType: 'log', entityId: log.id }}>
				<div class="item-actions">
					<button class="btn-tags" onclick={() => toggleExpand(log.id)}>Tags</button>
					<button class="btn-active" class:active={log.is_active} onclick={() => toggleActive(log.id, log.is_active)}>
						{log.is_active ? 'Active' : 'Inactive'}
					</button>
					<button class="btn-archive" onclick={() => handleArchive(log.id)}>Archive</button>
					<button class="btn-delete" onclick={() => (confirmDelete = log.id)}>Delete</button>
				</div>
				<div class="item-card" ondblclick={() => selectEntity('log', log.id, log.title)} role="button" tabindex="-1">
					<div class="item-header">
						<button class="item-title" ondblclick={() => { editingIds.add(log.id); editingIds = new Set(editingIds); }}>{log.title}</button>
						{#if log.is_archived}<span class="archived-badge">archived</span>{/if}
						{#if log.mood}<span class="log-emoji">{log.mood}</span>{/if}
						{#if log.weather}<span class="log-emoji">{log.weather}</span>{/if}
						{#if log.day_theme}<span class="log-emoji">{log.day_theme}</span>{/if}
					</div>
					{#if log.location}
						<p class="item-location">{log.location}</p>
					{/if}
					{#if log.content}
						<MarkdownContent text={log.content} />
					{/if}
					{#if entityTags[log.id]?.length}
						<div class="tag-badges">
							{#each entityTags[log.id] as tag (tag.id)}
								<TagBadge {tag} removable onRemove={() => handleDetach(log.id, tag)} />
							{/each}
						</div>
					{/if}
					<Timestamp date={log.created_at} />
				</div>
				{#if expandedId === log.id}
					<div class="tag-section">
						<TagInput
							attachedTags={entityTags[log.id] || []}
							targetType="log"
							targetId={log.id}
							onAttach={(tag) => handleAttach(log.id, tag)}
							onDetach={(tag) => handleDetach(log.id, tag)}
							onClose={() => (expandedId = null)}
						/>
					</div>
				{/if}
			</div>
		{/if}
	{/each}

	{#if $logs.length === 0}
		<p class="empty">No logs yet.</p>
	{:else if filteredLogs.length === 0}
		<p class="empty">No logs match current filters.</p>
	{/if}
</PanelContainer>

<ConfirmDialog
	open={confirmDelete !== null}
	message="Delete this log?"
	onConfirm={() => confirmDelete && handleDelete(confirmDelete)}
	onCancel={() => (confirmDelete = null)}
/>

<style>
	.inline-form { padding: 10px; background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 8px; margin-bottom: 12px; }
	.item { padding: 12px 0; border-bottom: 1px solid #e5e7eb; }
	.item-actions { display: flex; gap: 6px; margin-bottom: 6px; }
	.item-card { padding: 10px 12px; background: #fafafa; border: 1px solid #e5e7eb; border-radius: 8px; }
	.item-header { display: flex; align-items: center; gap: 8px; }
	.item-title { flex: 1; background: none; border: none; cursor: pointer; font-weight: 500; font-size: 0.9rem; text-align: left; padding: 0; color: #111827; }
	.item-location { font-size: 0.75rem; color: #92400e; margin: 4px 0 0; font-style: italic; }
	.log-emoji { font-size: 0.85rem; }
	.item-desc { font-size: 0.8rem; color: #6b7280; margin: 8px 0 0; }
	.type-badge { font-size: 0.7rem; padding: 2px 6px; background: #e5e7eb; border-radius: 4px; color: #6b7280; }
	.btn-active { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #f3f4f6; color: #6b7280; }
	.btn-active.active { background: #dcfce7; color: #16a34a; border-color: #bbf7d0; }
	.btn-tags { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #f9fafb; color: #6b7280; }
	.btn-archive { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #fef3c7; color: #92400e; }
	.btn-delete { font-size: 0.75rem; padding: 2px 8px; background: #fee2e2; color: #ef4444; border: 1px solid #fecaca; border-radius: 4px; cursor: pointer; }
	.tag-badges { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
	.tag-section { margin-top: 8px; padding: 8px; background: #f9fafb; border-radius: 6px; }
	.empty { text-align: center; color: #9ca3af; font-size: 0.875rem; }
	.is-archived .item-card { opacity: 0.55; border-style: dashed; }
	.archived-badge { font-size: 0.55rem; padding: 1px 5px; background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; border-radius: 3px; text-transform: uppercase; letter-spacing: 0.3px; font-weight: 600; flex-shrink: 0; }
	.btn-icon-nav { width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; border: 1px solid #d1d5db; border-radius: 4px; background: white; cursor: pointer; color: #9ca3af; transition: all 0.15s; }
	.btn-icon-nav:hover { border-color: #9ca3af; color: #6b7280; background: #f3f4f6; }
</style>

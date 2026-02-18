<script lang="ts">
	import type { Tag, Activity } from '$lib/types';
	import { activities, loadActivities } from '$lib/stores/activities';
	import { loadPlans } from '$lib/stores/plans';
	import { tags, loadTags, entityTagsVersion } from '$lib/stores/tags';
	import { projects } from '$lib/stores/projects';
	import { dateFilter, isItemVisible, selectedFilterTags, isTagVisible, isEntitySourceOfFilterTag, showArchived, showActiveRelated, activeEntityTagIds, isActiveRelated } from '$lib/stores/dateFilter';
	import { setLastUsedTags } from '$lib/stores/lastUsedTags';
	import { deleteActivity, activateActivity, deactivateActivity, archiveActivity } from '$lib/api/activities';
	import { getEntityTags, attachTag, detachTag } from '$lib/api/tags';
	import PanelContainer from '../shared/PanelContainer.svelte';
	import ConfirmDialog from '../shared/ConfirmDialog.svelte';
	import ActivityForm from '../forms/ActivityForm.svelte';
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
		for (const activity of $activities) {
			const activityTags = entityTags[activity.id] || [];
			for (const tag of activityTags) {
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

	let filteredActivities = $derived($activities.filter(a =>
		($showArchived || !a.is_archived) &&
		isItemVisible(a, $dateFilter) &&
		(isTagVisible(entityTags[a.id] || [], $selectedFilterTags) || isEntitySourceOfFilterTag('activity', a.id, $selectedFilterTags)) &&
		passesPanelFilter(entityTags[a.id] || []) &&
		(!$showActiveRelated || isActiveRelated(entityTags[a.id] || [], $activeEntityTagIds, a.is_active))
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
		await deleteActivity(id);
		await Promise.all([loadActivities(), loadTags(), loadPlans()]);
		confirmDelete = null;
	}

	async function toggleActive(id: number, isActive: boolean) {
		if (isActive) { await deactivateActivity(id); } else { await activateActivity(id); }
		await loadActivities();
	}

	async function handleArchive(id: number) {
		await archiveActivity(id);
		await loadActivities();
	}

	async function toggleExpand(id: number) {
		if (expandedId === id) { expandedId = null; return; }
		expandedId = id;
		if (!entityTags[id]) {
			entityTags[id] = await getEntityTags('activity', id);
		}
	}

	async function handleAttach(activityId: number, tag: Tag) {
		await attachTag(tag.id, 'activity', activityId);
		entityTags[activityId] = await getEntityTags('activity', activityId);
		setLastUsedTags('activity', entityTags[activityId]);
	}

	async function handleDetach(activityId: number, tag: Tag) {
		await detachTag(tag.id, 'activity', activityId);
		entityTags[activityId] = await getEntityTags('activity', activityId);
		setLastUsedTags('activity', entityTags[activityId]);
	}

	async function handleCreate(activityId: number) {
		// Get tags for active projects and activities
		const activeProjectIds = $projects.filter(p => p.is_active).map(p => p.id);
		const activeActivityIds = $activities.filter(a => a.is_active).map(a => a.id);

		const activeEntityTags = $tags.filter(t =>
			(t.entity_type === 'project' && t.entity_id && activeProjectIds.includes(t.entity_id)) ||
			(t.entity_type === 'activity' && t.entity_id && activeActivityIds.includes(t.entity_id))
		);

		for (const tag of activeEntityTags) {
			try {
				await attachTag(tag.id, 'activity', activityId);
			} catch (e) {
				console.warn(`Failed to attach tag ${tag.id} to activity ${activityId}:`, e);
			}
		}

		if (activeEntityTags.length > 0) {
			entityTags[activityId] = await getEntityTags('activity', activityId);
		}
	}

	async function loadAllTags() {
		const entries = await Promise.all(
			$activities.map(async (activity) => [activity.id, await getEntityTags('activity', activity.id)] as const)
		);
		const updated: Record<number, Tag[]> = {};
		for (const [id, tags] of entries) updated[id] = tags;
		entityTags = updated;
	}

	$effect(() => {
		const _ = $entityTagsVersion;  // Subscribe to version changes
		if ($activities) loadAllTags();
	});
</script>

<PanelContainer
	title="Activities"
	panelId="activity"
	color="#b5838d"
	onAdd={() => (showForm = !showForm)}
	availableTags={availablePanelTags()}
	selectedTagIds={panelSelectedTagIds}
	filterMode={panelFilterMode}
	onTagToggle={handlePanelTagToggle}
	onModeToggle={handlePanelModeToggle}
>
	{#if showForm}
		<div class="inline-form">
			<ActivityForm onDone={() => (showForm = false)} onCreate={handleCreate} />
		</div>
	{/if}

	{#each filteredActivities as activity (activity.id)}
		{#if editingIds.has(activity.id)}
			<div class="inline-form">
				<ActivityForm editData={activity} onDone={() => { editingIds.delete(activity.id); editingIds = new Set(editingIds); }} />
			</div>
		{:else}
			<div class="item" class:is-archived={activity.is_archived} use:selectable={{ entityType: 'activity', entityId: activity.id }}>
				<div class="item-actions">
					<button class="btn-tags" onclick={() => toggleExpand(activity.id)}>Tags</button>
					<button class="btn-active" class:active={activity.is_active} onclick={() => toggleActive(activity.id, activity.is_active)}>
						{activity.is_active ? 'Active' : 'Inactive'}
					</button>
					<button class="btn-archive" onclick={() => handleArchive(activity.id)}>Archive</button>
					<button class="btn-delete" onclick={() => (confirmDelete = activity.id)}>Delete</button>
				</div>
				<div class="item-card" ondblclick={() => selectEntity('activity', activity.id, activity.title)} role="button" tabindex="-1">
					<div class="item-header">
						<button class="item-title" ondblclick={() => { editingIds.add(activity.id); editingIds = new Set(editingIds); }}>{activity.title}</button>
						{#if activity.is_archived}<span class="archived-badge">archived</span>{/if}
						{#if activity.duration}
							<span class="duration-badge">{activity.duration} min</span>
						{/if}
					</div>
					{#if activity.description}
						<p class="item-desc">{activity.description}</p>
					{/if}
					{#if entityTags[activity.id]?.length}
						<div class="tag-badges">
							{#each entityTags[activity.id] as tag (tag.id)}
								<TagBadge {tag} removable onRemove={() => handleDetach(activity.id, tag)} />
							{/each}
						</div>
					{/if}
					<Timestamp date={activity.created_at} />
				</div>
				{#if expandedId === activity.id}
					<div class="tag-section">
						<TagInput
							attachedTags={entityTags[activity.id] || []}
							targetType="activity"
							targetId={activity.id}
							onAttach={(tag) => handleAttach(activity.id, tag)}
							onDetach={(tag) => handleDetach(activity.id, tag)}
							onClose={() => (expandedId = null)}
						/>
					</div>
				{/if}
			</div>
		{/if}
	{/each}

	{#if $activities.length === 0}
		<p class="empty">No activities yet.</p>
	{:else if filteredActivities.length === 0}
		<p class="empty">No activities match current filters.</p>
	{/if}
</PanelContainer>

<ConfirmDialog
	open={confirmDelete !== null}
	message="Delete this activity? Its tag will be removed from all entities."
	onConfirm={() => confirmDelete && handleDelete(confirmDelete)}
	onCancel={() => (confirmDelete = null)}
/>

<style>
	.inline-form { padding: 10px; background: #faf5ff; border: 1px solid #e9d5ff; border-radius: 8px; margin-bottom: 12px; }
	.item { padding: 12px 0; border-bottom: 1px solid #e5e7eb; }
	.item-actions { display: flex; gap: 6px; margin-bottom: 6px; }
	.item-card { padding: 10px 12px; background: #fafafa; border: 1px solid #e5e7eb; border-radius: 8px; }
	.item-header { display: flex; align-items: center; gap: 8px; }
	.item-title { flex: 1; background: none; border: none; cursor: pointer; font-weight: 500; font-size: 0.9rem; text-align: left; padding: 0; color: #111827; }
	.item-desc { font-size: 0.8rem; color: #6b7280; margin: 8px 0 0; white-space: pre-wrap; }
	.duration-badge { font-size: 0.7rem; padding: 2px 6px; background: #f0fdf4; border-radius: 4px; color: #15803d; }
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

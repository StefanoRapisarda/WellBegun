<script lang="ts">
	import type { Activity } from '$lib/types';
	import { createActivity, updateActivity } from '$lib/api/activities';
	import { loadActivities } from '$lib/stores/activities';
	import { loadTags } from '$lib/stores/tags';
	import { syncHashtags, attachTag } from '$lib/api/tags';
	import HashtagTextarea from '../shared/HashtagTextarea.svelte';
	import DefaultTagSuggestions from '../shared/DefaultTagSuggestions.svelte';

	let { onDone, editData, onCreate }: { onDone: () => void; editData?: Activity; onCreate?: (id: number) => void } = $props();

	let title = $state(editData?.title ?? '');
	let description = $state(editData?.description ?? '');
	let duration = $state(editData?.duration?.toString() ?? '');
	let activityDate = $state(editData?.activity_date ? editData.activity_date.slice(0, 10) : '');
	let selectedTagIds = $state<number[]>([]);

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!title.trim()) return;
		const data = {
			title: title.trim(),
			description: description.trim() || undefined,
			duration: duration ? parseInt(duration, 10) : undefined,
			activity_date: activityDate ? activityDate + 'T00:00:00' : null
		};
		let activityId: number;
		if (editData) {
			await updateActivity(editData.id, data);
			activityId = editData.id;
		} else {
			const created = await createActivity(data);
			activityId = created.id;
			for (const tagId of selectedTagIds) {
				await attachTag(tagId, 'activity', activityId);
			}
		}
		if (description.includes('#')) {
			await syncHashtags(description, 'activity', activityId);
		}
		await Promise.all([loadActivities(), loadTags()]);
		if (!editData) {
			onCreate?.(activityId);
		}
		onDone();
	}
</script>

<form onsubmit={handleSubmit} class="widget" class:editing={!!editData}>
	<input type="text" bind:value={title} required placeholder="Activity title..." class="title-input" />
	<div class="field-row">
		<input type="number" bind:value={duration} min="0" placeholder="Duration (min)" class="field-input" />
		<input type="date" bind:value={activityDate} class="field-input" title="Activity date" />
	</div>
	<HashtagTextarea bind:value={description} rows={3} autoSize={!!editData} placeholder="Description (optional) — type # to insert tags..." />
	{#if !editData}
		<DefaultTagSuggestions category="activity" bind:selectedTagIds {title} />
	{/if}
	<div class="button-row">
		<button type="button" class="btn-cancel" onclick={onDone}>Cancel</button>
		<button type="submit" class="btn-save">{editData ? 'Save' : 'Create'}</button>
	</div>
</form>

<style>
	.widget { display: flex; flex-direction: column; gap: 6px; padding: 10px; background: #f5f3ff; border: 1px solid #ddd6fe; border-radius: 8px; margin-bottom: 12px; }
	.widget.editing { background: #fefce8; border-color: #fde68a; }
	.title-input { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.field-row { display: flex; gap: 6px; }
	.button-row { display: flex; justify-content: flex-end; gap: 6px; padding-top: 4px; }
	.field-input { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.btn-save { padding: 6px 14px; background: #8b5cf6; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-save:hover { background: #7c3aed; }
	.btn-cancel { padding: 6px 14px; background: white; color: #6b7280; border: 1px solid #d1d5db; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-cancel:hover { background: #f3f4f6; }
</style>

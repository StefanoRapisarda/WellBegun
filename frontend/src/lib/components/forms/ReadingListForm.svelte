<script lang="ts">
	import type { ReadingList } from '$lib/types';
	import { createReadingList, updateReadingList } from '$lib/api/readingLists';
	import { loadReadingLists } from '$lib/stores/readingLists';
	import { loadTags } from '$lib/stores/tags';
	import { attachTag } from '$lib/api/tags';
	import DefaultTagSuggestions from '../shared/DefaultTagSuggestions.svelte';

	let { onDone, editData }: { onDone: () => void; editData?: ReadingList } = $props();

	let title = $state(editData?.title ?? '');
	let description = $state(editData?.description ?? '');
	let selectedTagIds = $state<number[]>([]);

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!title.trim()) return;
		const data = {
			title: title.trim(),
			description: description.trim() || undefined
		};
		if (editData) {
			await updateReadingList(editData.id, data);
		} else {
			const created = await createReadingList(data);
			for (const tagId of selectedTagIds) {
				await attachTag(tagId, 'readinglist', created.id);
			}
		}
		await Promise.all([loadReadingLists(), loadTags()]);
		onDone();
	}
</script>

<form onsubmit={handleSubmit} class="form">
	<label>
		Title *
		<input type="text" bind:value={title} required />
	</label>
	<label>
		Description
		<textarea bind:value={description} rows="3"></textarea>
	</label>
	{#if !editData}
		<DefaultTagSuggestions category="readinglist" bind:selectedTagIds />
	{/if}
	<div class="form-actions">
		<button type="button" class="btn btn-cancel" onclick={onDone}>Cancel</button>
		<button type="submit" class="btn btn-primary">{editData ? 'Save' : 'Create'}</button>
	</div>
</form>

<style>
	.form { display: flex; flex-direction: column; gap: 12px; }
	label { display: flex; flex-direction: column; gap: 4px; font-size: 0.875rem; font-weight: 500; color: #374151; }
	input, textarea { padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.875rem; }
	.form-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 8px; }
	.btn { padding: 8px 16px; border-radius: 6px; border: 1px solid #d1d5db; cursor: pointer; font-size: 0.875rem; }
	.btn-cancel { background: white; }
	.btn-primary { background: #06b6d4; color: white; border-color: #06b6d4; }
</style>

<script lang="ts">
	import type { ReadingList } from '$lib/types';
	import { createReadingList, updateReadingList } from '$lib/api/readingLists';
	import { loadReadingLists } from '$lib/stores/readingLists';
	import { loadTags } from '$lib/stores/tags';
	import { attachTag } from '$lib/api/tags';
	import DefaultTagSuggestions from '../shared/DefaultTagSuggestions.svelte';
	import { onMount } from 'svelte';

	let { onDone, editData }: { onDone: () => void; editData?: ReadingList } = $props();

	let title = $state(editData?.title ?? '');
	let description = $state(editData?.description ?? '');
	let selectedTagIds = $state<number[]>([]);

	let descEl: HTMLTextAreaElement | undefined = $state();

	onMount(() => {
		if (editData && descEl) {
			const maxH = window.innerHeight * 0.45;
			descEl.style.height = 'auto';
			descEl.style.height = Math.min(descEl.scrollHeight, maxH) + 'px';
		}
	});

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

<form onsubmit={handleSubmit} class="widget" class:editing={!!editData}>
	<input type="text" bind:value={title} required placeholder="Reading list title..." class="title-input" />
	<textarea bind:this={descEl} bind:value={description} rows="2" placeholder="Description (optional)" class="field-textarea"></textarea>
	{#if !editData}
		<DefaultTagSuggestions category="readinglist" bind:selectedTagIds />
	{/if}
	<div class="button-row">
		<button type="button" class="btn-cancel" onclick={onDone}>Cancel</button>
		<button type="submit" class="btn-save">{editData ? 'Save' : 'Create'}</button>
	</div>
</form>

<style>
	.widget { display: flex; flex-direction: column; gap: 6px; padding: 10px; background: #ecfeff; border: 1px solid #a5f3fc; border-radius: 8px; margin-bottom: 12px; }
	.widget.editing { background: #fefce8; border-color: #fde68a; }
	.title-input { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.button-row { display: flex; justify-content: flex-end; gap: 6px; padding-top: 4px; }
	.field-textarea { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; resize: vertical; font-family: inherit; }
	.btn-save { padding: 6px 14px; background: #06b6d4; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-save:hover { background: #0891b2; }
	.btn-cancel { padding: 6px 14px; background: white; color: #6b7280; border: 1px solid #d1d5db; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-cancel:hover { background: #f3f4f6; }
</style>

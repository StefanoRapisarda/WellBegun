<script lang="ts">
	import type { Collection, Category } from '$lib/types';
	import { createCollection, updateCollection } from '$lib/api/collections';
	import { loadCollections } from '$lib/stores/collections';
	import { categories } from '$lib/stores/categories';
	import { loadTags } from '$lib/stores/tags';
	import { attachTag } from '$lib/api/tags';
	import DefaultTagSuggestions from '../shared/DefaultTagSuggestions.svelte';
	import { onMount } from 'svelte';

	let { onDone, editData }: { onDone: (createdId?: number) => void; editData?: Collection } = $props();

	let title = $state(editData?.title ?? '');
	let description = $state(editData?.description ?? '');
	let categoryId = $state<number | null>(editData?.category_id ?? null);
	let selectedTagIds = $state<number[]>([]);

	let descEl: HTMLTextAreaElement | undefined = $state();

	let availableCategories = $derived($categories);
	let showCategorySelect = $derived(availableCategories.length > 1);

	onMount(() => {
		// Auto-select first category if none chosen
		if (categoryId === null && availableCategories.length > 0) {
			categoryId = availableCategories[0].id;
		}
		if (editData && descEl) {
			const maxH = window.innerHeight * 0.45;
			descEl.style.height = 'auto';
			descEl.style.height = Math.min(descEl.scrollHeight, maxH) + 'px';
		}
	});

	$effect(() => {
		if (categoryId === null && availableCategories.length > 0) {
			categoryId = availableCategories[0].id;
		}
	});

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!title.trim() || categoryId === null) return;
		const data = {
			title: title.trim(),
			category_id: categoryId,
			description: description.trim() || undefined
		};
		let createdId: number | undefined;
		if (editData) {
			await updateCollection(editData.id, data);
		} else {
			const created = await createCollection(data);
			createdId = created.id;
			for (const tagId of selectedTagIds) {
				await attachTag(tagId, 'collection', created.id);
			}
		}
		await Promise.all([loadCollections(), loadTags()]);
		onDone(createdId);
	}
</script>

<form onsubmit={handleSubmit} class="widget" class:editing={!!editData}>
	<input type="text" bind:value={title} required placeholder="Collection title..." class="title-input" />
	<textarea bind:this={descEl} bind:value={description} rows="2" placeholder="Description (optional)" class="field-textarea"></textarea>
	{#if showCategorySelect}
		<select bind:value={categoryId} class="field-select">
			{#each availableCategories as cat (cat.id)}
				<option value={cat.id}>{cat.display_name}</option>
			{/each}
		</select>
	{/if}
	{#if !editData}
		<DefaultTagSuggestions category="collection" bind:selectedTagIds {title} />
	{/if}
	<div class="button-row">
		<button type="button" class="btn-cancel" onclick={onDone}>Cancel</button>
		<button type="submit" class="btn-save">{editData ? 'Save' : 'Create'}</button>
	</div>
</form>

<style>
	.widget { display: flex; flex-direction: column; gap: 6px; padding: 10px; background: #f5f3fa; border: 1px solid #d4cfe6; border-radius: 8px; margin-bottom: 12px; }
	.widget.editing { background: #fefce8; border-color: #fde68a; }
	.title-input { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.field-textarea { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; resize: vertical; font-family: inherit; }
	.field-select { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.button-row { display: flex; justify-content: flex-end; gap: 6px; padding-top: 4px; }
	.btn-save { padding: 6px 14px; background: #7c6f9e; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-save:hover { background: #685d87; }
	.btn-cancel { padding: 6px 14px; background: white; color: #6b7280; border: 1px solid #d1d5db; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-cancel:hover { background: #f3f4f6; }
</style>

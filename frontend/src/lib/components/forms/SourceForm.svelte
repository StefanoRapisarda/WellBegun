<script lang="ts">
	import type { Source } from '$lib/types';
	import { createSource, updateSource } from '$lib/api/sources';
	import { loadSources } from '$lib/stores/sources';
	import { loadTags } from '$lib/stores/tags';
	import { attachTag } from '$lib/api/tags';
	import DefaultTagSuggestions from '../shared/DefaultTagSuggestions.svelte';
	import { onMount } from 'svelte';

	let { onDone, editData, onCreate }: { onDone: () => void; editData?: Source; onCreate?: (id: number) => void } = $props();

	let title = $state(editData?.title ?? '');
	let author = $state(editData?.author ?? '');
	let description = $state(editData?.description ?? '');
	let contentUrl = $state(editData?.content_url ?? '');
	let sourceType = $state(editData?.source_type ?? '');
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
			description: description.trim() || undefined,
			author: author.trim() || undefined,
			content_url: contentUrl.trim() || undefined,
			source_type: sourceType.trim() || undefined
		};
		let sourceId: number;
		if (editData) {
			await updateSource(editData.id, data);
			sourceId = editData.id;
		} else {
			const created = await createSource(data);
			sourceId = created.id;
			for (const tagId of selectedTagIds) {
				await attachTag(tagId, 'source', sourceId);
			}
		}
		await Promise.all([loadSources(), loadTags()]);
		if (!editData) {
			onCreate?.(sourceId);
		}
		onDone();
	}
</script>

<form onsubmit={handleSubmit} class="widget" class:editing={!!editData}>
	<input type="text" bind:value={title} required placeholder="Source title..." class="title-input" />
	<input type="text" bind:value={author} placeholder="Author" class="field-input" />
	<input type="text" bind:value={sourceType} placeholder="Type (e.g. book, article, video)" class="field-input" />
	<input type="url" bind:value={contentUrl} placeholder="URL (https://...)" class="field-input" />
	<textarea bind:this={descEl} bind:value={description} rows="2" placeholder="Description (optional)" class="field-textarea"></textarea>
	{#if !editData}
		<DefaultTagSuggestions category="source" bind:selectedTagIds {title} />
	{/if}
	<div class="button-row">
		<button type="button" class="btn-cancel" onclick={onDone}>Cancel</button>
		<button type="submit" class="btn-save">{editData ? 'Save' : 'Create'}</button>
	</div>
</form>

<style>
	.widget { display: flex; flex-direction: column; gap: 6px; padding: 10px; background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; margin-bottom: 12px; }
	.widget.editing { background: #fefce8; border-color: #fde68a; }
	.title-input { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.button-row { display: flex; justify-content: flex-end; gap: 6px; padding-top: 4px; }
	.field-input { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.field-textarea { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; resize: vertical; font-family: inherit; }
	.btn-save { padding: 6px 14px; background: #f59e0b; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-save:hover { background: #d97706; }
	.btn-cancel { padding: 6px 14px; background: white; color: #6b7280; border: 1px solid #d1d5db; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-cancel:hover { background: #f3f4f6; }
</style>

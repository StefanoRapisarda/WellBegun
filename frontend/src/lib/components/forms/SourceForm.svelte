<script lang="ts">
	import type { Source } from '$lib/types';
	import { createSource, updateSource } from '$lib/api/sources';
	import { loadSources } from '$lib/stores/sources';
	import { loadTags } from '$lib/stores/tags';
	import { attachTag } from '$lib/api/tags';
	import DefaultTagSuggestions from '../shared/DefaultTagSuggestions.svelte';

	let { onDone, editData, onCreate }: { onDone: () => void; editData?: Source; onCreate?: (id: number) => void } = $props();

	let title = $state(editData?.title ?? '');
	let description = $state(editData?.description ?? '');
	let contentUrl = $state(editData?.content_url ?? '');
	let sourceType = $state(editData?.source_type ?? '');
	let selectedTagIds = $state<number[]>([]);

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!title.trim()) return;
		const data = {
			title: title.trim(),
			description: description.trim() || undefined,
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

<form onsubmit={handleSubmit} class="form">
	<label>
		Title *
		<input type="text" bind:value={title} required />
	</label>
	<label>
		Description
		<textarea bind:value={description} rows="3"></textarea>
	</label>
	<label>
		URL
		<input type="url" bind:value={contentUrl} placeholder="https://..." />
	</label>
	<label>
		Source Type
		<input type="text" bind:value={sourceType} placeholder="e.g. book, article, video" />
	</label>
	{#if !editData}
		<DefaultTagSuggestions category="source" bind:selectedTagIds />
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
	.btn-primary { background: #f59e0b; color: white; border-color: #f59e0b; }
</style>

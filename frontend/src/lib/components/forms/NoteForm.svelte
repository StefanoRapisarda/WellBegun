<script lang="ts">
	import type { Note } from '$lib/types';
	import { createNote, updateNote } from '$lib/api/notes';
	import { loadNotes } from '$lib/stores/notes';
	import { loadTags } from '$lib/stores/tags';
	import { attachTag } from '$lib/api/tags';
	import HashtagTextarea from '../shared/HashtagTextarea.svelte';
	import DefaultTagSuggestions from '../shared/DefaultTagSuggestions.svelte';

	let { onDone, editData, onCreate, initialTitle, initialContent }: {
		onDone: () => void;
		editData?: Note;
		onCreate?: (id: number) => void;
		initialTitle?: string;
		initialContent?: string;
	} = $props();

	let title = $state(editData?.title ?? initialTitle ?? '');
	let content = $state(editData?.content ?? initialContent ?? '');
	let selectedTagIds = $state<number[]>([]);

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!title.trim()) return;
		const data = {
			title: title.trim(),
			content: content.trim() || undefined
		};
		let noteId: number;
		if (editData) {
			await updateNote(editData.id, data);
			noteId = editData.id;
		} else {
			const created = await createNote(data);
			noteId = created.id;
			for (const tagId of selectedTagIds) {
				await attachTag(tagId, 'note', noteId);
			}
		}
		await Promise.all([loadNotes(), loadTags()]);
		if (!editData) {
			onCreate?.(noteId);
		}
		onDone();
	}
</script>

<form onsubmit={handleSubmit} class="widget" class:editing={!!editData}>
	<input type="text" bind:value={title} required placeholder="Note title..." class="title-input" />
	<HashtagTextarea bind:value={content} rows={editData ? 4 : 2} autoSize={!!editData} placeholder="Content (optional) — type # to insert tags..." />
	{#if !editData}
		<DefaultTagSuggestions category="note" bind:selectedTagIds {title} />
	{/if}
	<div class="button-row">
		<button type="button" class="btn-cancel" onclick={onDone}>Cancel</button>
		<button type="submit" class="btn-save">{editData ? 'Save' : 'Create'}</button>
	</div>
</form>

<style>
	.widget { display: flex; flex-direction: column; gap: 6px; padding: 10px; background: #ecfdf5; border: 1px solid #d1fae5; border-radius: 8px; margin-bottom: 12px; }
	.widget.editing { background: #fefce8; border-color: #fde68a; }
	.title-input { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.button-row { display: flex; justify-content: flex-end; gap: 6px; padding-top: 4px; }
	.btn-save { padding: 6px 14px; background: #10b981; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-save:hover { background: #059669; }
	.btn-cancel { padding: 6px 14px; background: white; color: #6b7280; border: 1px solid #d1d5db; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-cancel:hover { background: #f3f4f6; }
</style>

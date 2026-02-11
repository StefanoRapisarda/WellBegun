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

<form onsubmit={handleSubmit} class="form">
	<label>
		Title *
		<input type="text" bind:value={title} required />
	</label>
	<label>
		Content
		<HashtagTextarea bind:value={content} rows={5} placeholder="Type # to insert tags..." />
	</label>
	{#if !editData}
		<DefaultTagSuggestions category="note" bind:selectedTagIds />
	{/if}
	<div class="form-actions">
		<button type="button" class="btn btn-cancel" onclick={onDone}>Cancel</button>
		<button type="submit" class="btn btn-primary">{editData ? 'Save' : 'Create'}</button>
	</div>
</form>

<style>
	.form { display: flex; flex-direction: column; gap: 12px; }
	label { display: flex; flex-direction: column; gap: 4px; font-size: 0.875rem; font-weight: 500; color: #374151; }
	input { padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.875rem; }
	.form-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 8px; }
	.btn { padding: 8px 16px; border-radius: 6px; border: 1px solid #d1d5db; cursor: pointer; font-size: 0.875rem; }
	.btn-cancel { background: white; }
	.btn-primary { background: #10b981; color: white; border-color: #10b981; }
</style>

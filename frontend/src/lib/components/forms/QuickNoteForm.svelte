<script lang="ts">
	import type { Note } from '$lib/types';
	import { createNote, updateNote } from '$lib/api/notes';
	import { loadNotes } from '$lib/stores/notes';
	import { loadTags } from '$lib/stores/tags';
	import { syncHashtags, attachTag } from '$lib/api/tags';
	import { getDraft, setDraft, clearDraft } from '$lib/stores/formDrafts';
	import HashtagTextarea from '../shared/HashtagTextarea.svelte';
	import DefaultTagSuggestions from '../shared/DefaultTagSuggestions.svelte';
	import { onMount } from 'svelte';

	let { editData = undefined, onDone = undefined, onCreate = undefined }: { editData?: Note; onDone?: () => void; onCreate?: (id: number) => void } =
		$props();

	let title = $state(editData?.title ?? '');
	let content = $state(editData?.content ?? '');
	let selectedTagIds = $state<number[]>([]);

	// Load draft on mount (only for new entries, not editing)
	onMount(() => {
		if (!editData) {
			const draft = getDraft('note');
			title = draft.title || '';
			content = draft.content || '';
		}
	});

	// Save draft as user types (only for new entries)
	$effect(() => {
		if (!editData) {
			setDraft('note', 'title', title);
			setDraft('note', 'content', content);
		}
	});

	$effect(() => {
		if (editData) {
			title = editData.title;
			content = editData.content ?? '';
		}
	});

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
		if (content.includes('#')) {
			await syncHashtags(content, 'note', noteId);
		}
		await Promise.all([loadNotes(), loadTags()]);
		// Notify parent of new item creation (not editing)
		if (!editData) {
			onCreate?.(noteId);
			clearDraft('note');
		}
		title = '';
		content = '';
		selectedTagIds = [];
		onDone?.();
	}

	function handleCancel() {
		title = '';
		content = '';
		onDone?.();
	}
</script>

<form onsubmit={handleSubmit} class="note-widget" class:editing={!!editData}>
	<div class="note-row">
		<input type="text" bind:value={title} placeholder="Note title..." class="note-title" required />
		<button type="submit" class="note-save">{editData ? 'Update' : 'Save'}</button>
		{#if editData}
			<button type="button" class="note-cancel" onclick={handleCancel}>Cancel</button>
		{/if}
	</div>
	<HashtagTextarea bind:value={content} rows={2} placeholder="Content (optional) — type # to insert tags" />
	{#if !editData}
		<DefaultTagSuggestions category="note" bind:selectedTagIds />
	{/if}
</form>

<style>
	.note-widget { display: flex; flex-direction: column; gap: 6px; padding: 10px; background: #ecfdf5; border: 1px solid #d1fae5; border-radius: 8px; margin-bottom: 12px; }
	.note-widget.editing { background: #fefce8; border-color: #fde68a; }
	.note-row { display: flex; gap: 6px; align-items: center; }
	.note-title { flex: 1; padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.note-save { padding: 6px 14px; background: #10b981; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.note-save:hover { background: #059669; }
	.note-cancel { padding: 6px 14px; background: white; color: #6b7280; border: 1px solid #d1d5db; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.note-cancel:hover { background: #f3f4f6; }
</style>

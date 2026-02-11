<script lang="ts">
	import type { Log } from '$lib/types';
	import { createLog, updateLog } from '$lib/api/logs';
	import { loadLogs } from '$lib/stores/logs';
	import { loadTags } from '$lib/stores/tags';
	import { syncHashtags, attachTag } from '$lib/api/tags';
	import { getDraft, setDraft, clearDraft } from '$lib/stores/formDrafts';
	import HashtagTextarea from '../shared/HashtagTextarea.svelte';
	import DefaultTagSuggestions from '../shared/DefaultTagSuggestions.svelte';
	import { onMount } from 'svelte';

	let { editData = undefined, onDone = undefined, onCreate = undefined }: { editData?: Log; onDone?: () => void; onCreate?: (id: number) => void } =
		$props();

	let title = $state('');
	let content = $state('');
	let selectedTagIds = $state<number[]>([]);

	// Load draft on mount (only for new entries, not editing)
	onMount(() => {
		if (!editData) {
			const draft = getDraft('log');
			title = draft.title || '';
			content = draft.content || '';
		}
	});

	// Save draft as user types (only for new entries)
	$effect(() => {
		if (!editData) {
			setDraft('log', 'title', title);
			setDraft('log', 'content', content);
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
		let logId: number;
		if (editData) {
			await updateLog(editData.id, {
				title: title.trim(),
				content: content.trim() || undefined
			});
			logId = editData.id;
		} else {
			const created = await createLog({
				log_type: 'diary',
				title: title.trim(),
				content: content.trim() || undefined
			});
			logId = created.id;
			for (const tagId of selectedTagIds) {
				await attachTag(tagId, 'log', logId);
			}
		}
		if (content.includes('#')) {
			await syncHashtags(content, 'log', logId);
		}
		await Promise.all([loadLogs(), loadTags()]);
		if (!editData) {
			onCreate?.(logId);
			clearDraft('log');
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

<form onsubmit={handleSubmit} class="diary-widget" class:editing={!!editData}>
	<div class="diary-row">
		<input type="text" bind:value={title} placeholder="Log title..." class="diary-title" required />
		<button type="submit" class="diary-save">{editData ? 'Update' : 'Save'}</button>
		{#if editData}
			<button type="button" class="diary-cancel" onclick={handleCancel}>Cancel</button>
		{/if}
	</div>
	<HashtagTextarea bind:value={content} rows={editData ? Math.max(8, Math.min(20, content.split('\n').length + 2)) : 2} placeholder="Content (optional) — type # to insert tags" />
	{#if !editData}
		<DefaultTagSuggestions category="log" bind:selectedTagIds />
	{/if}
</form>

<style>
	.diary-widget { display: flex; flex-direction: column; gap: 6px; padding: 10px; background: #faf8f5; border: 1px solid #e8e0d4; border-radius: 8px; margin-bottom: 12px; }
	.diary-widget.editing { background: #fefce8; border-color: #fde68a; }
	.diary-row { display: flex; gap: 6px; align-items: center; }
	.diary-title { flex: 1; padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.diary-save { padding: 6px 14px; background: #8b7355; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.diary-save:hover { background: #74603f; }
	.diary-cancel { padding: 6px 14px; background: white; color: #6b7280; border: 1px solid #d1d5db; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.diary-cancel:hover { background: #f3f4f6; }
</style>

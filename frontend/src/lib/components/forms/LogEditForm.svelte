<script lang="ts">
	import type { Log } from '$lib/types';
	import { updateLog } from '$lib/api/logs';
	import { loadLogs } from '$lib/stores/logs';
	import { loadTags } from '$lib/stores/tags';

	let { onDone, editData }: { onDone: () => void; editData: Log } = $props();

	let title = $state(editData.title);
	let content = $state(editData.content ?? '');

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!title.trim()) return;
		await updateLog(editData.id, {
			title: title.trim(),
			content: content.trim() || undefined
		});
		await Promise.all([loadLogs(), loadTags()]);
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
		<textarea bind:value={content} rows="3"></textarea>
	</label>
	<div class="form-actions">
		<button type="button" class="btn btn-cancel" onclick={onDone}>Cancel</button>
		<button type="submit" class="btn btn-primary">Save</button>
	</div>
</form>

<style>
	.form { display: flex; flex-direction: column; gap: 12px; }
	label { display: flex; flex-direction: column; gap: 4px; font-size: 0.875rem; font-weight: 500; color: #374151; }
	input, textarea { padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.875rem; }
	.form-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 8px; }
	.btn { padding: 8px 16px; border-radius: 6px; border: 1px solid #d1d5db; cursor: pointer; font-size: 0.875rem; }
	.btn-cancel { background: white; }
	.btn-primary { background: #8b5cf6; color: white; border-color: #8b5cf6; }
</style>

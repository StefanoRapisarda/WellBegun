<script lang="ts">
	import type { Project } from '$lib/types';
	import { createProject, updateProject } from '$lib/api/projects';
	import { loadProjects } from '$lib/stores/projects';
	import { loadTags } from '$lib/stores/tags';
	import { attachTag } from '$lib/api/tags';
	import DefaultTagSuggestions from '../shared/DefaultTagSuggestions.svelte';

	let { onDone, editData, onCreate }: { onDone: () => void; editData?: Project; onCreate?: (id: number) => void } = $props();

	let title = $state(editData?.title ?? '');
	let description = $state(editData?.description ?? '');
	let status = $state(editData?.status ?? 'in_progress');
	let selectedTagIds = $state<number[]>([]);
	function todayLocal(): string {
		const now = new Date();
		now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
		return now.toISOString().slice(0, 16);
	}
	let startDate = $state(editData?.start_date ?? todayLocal());

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!title.trim()) return;
		const data = {
			title: title.trim(),
			description: description.trim() || undefined,
			status,
			start_date: startDate || undefined
		};
		let projectId: number;
		if (editData) {
			await updateProject(editData.id, data);
			projectId = editData.id;
		} else {
			const created = await createProject(data);
			projectId = created.id;
			for (const tagId of selectedTagIds) {
				await attachTag(tagId, 'project', projectId);
			}
		}
		await Promise.all([loadProjects(), loadTags()]);
		if (!editData) {
			onCreate?.(projectId);
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
		Status
		<select bind:value={status}>
			<option value="in_progress">In Progress</option>
			<option value="on_hold">On Hold</option>
			<option value="completed">Completed</option>
			<option value="archived">Archived</option>
		</select>
	</label>
	<label>
		Start Date
		<input type="datetime-local" bind:value={startDate} />
	</label>
	{#if !editData}
		<DefaultTagSuggestions category="project" bind:selectedTagIds />
	{/if}
	<div class="form-actions">
		<button type="button" class="btn btn-cancel" onclick={onDone}>Cancel</button>
		<button type="submit" class="btn btn-primary">{editData ? 'Save' : 'Create'}</button>
	</div>
</form>

<style>
	.form { display: flex; flex-direction: column; gap: 12px; }
	label { display: flex; flex-direction: column; gap: 4px; font-size: 0.875rem; font-weight: 500; color: #374151; }
	input, textarea, select { padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.875rem; }
	.form-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 8px; }
	.btn { padding: 8px 16px; border-radius: 6px; border: 1px solid #d1d5db; cursor: pointer; font-size: 0.875rem; }
	.btn-cancel { background: white; }
	.btn-primary { background: #3b82f6; color: white; border-color: #3b82f6; }
</style>

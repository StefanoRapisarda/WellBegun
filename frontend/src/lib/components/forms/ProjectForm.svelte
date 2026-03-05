<script lang="ts">
	import type { Project } from '$lib/types';
	import { createProject, updateProject } from '$lib/api/projects';
	import { loadProjects } from '$lib/stores/projects';
	import { loadTags } from '$lib/stores/tags';
	import { attachTag } from '$lib/api/tags';
	import DefaultTagSuggestions from '../shared/DefaultTagSuggestions.svelte';
	import { onMount } from 'svelte';

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

<form onsubmit={handleSubmit} class="widget" class:editing={!!editData}>
	<input type="text" bind:value={title} required placeholder="Project title..." class="title-input" />
	<div class="fields-row">
		<select bind:value={status} class="field-select">
			<option value="in_progress">In Progress</option>
			<option value="on_hold">On Hold</option>
			<option value="completed">Completed</option>
			<option value="archived">Archived</option>
		</select>
		<input type="datetime-local" bind:value={startDate} class="field-input" />
	</div>
	<textarea bind:this={descEl} bind:value={description} rows="2" placeholder="Description (optional)" class="field-textarea"></textarea>
	{#if !editData}
		<DefaultTagSuggestions category="project" bind:selectedTagIds {title} />
	{/if}
	<div class="button-row">
		<button type="button" class="btn-cancel" onclick={onDone}>Cancel</button>
		<button type="submit" class="btn-save">{editData ? 'Save' : 'Create'}</button>
	</div>
</form>

<style>
	.widget { display: flex; flex-direction: column; gap: 6px; padding: 10px; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; margin-bottom: 12px; }
	.widget.editing { background: #fefce8; border-color: #fde68a; }
	.title-input { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.button-row { display: flex; justify-content: flex-end; gap: 6px; padding-top: 4px; }
	.fields-row { display: flex; gap: 6px; }
	.field-input { flex: 1; padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.field-select { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.field-textarea { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; resize: vertical; font-family: inherit; }
	.btn-save { padding: 6px 14px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-save:hover { background: #2563eb; }
	.btn-cancel { padding: 6px 14px; background: white; color: #6b7280; border: 1px solid #d1d5db; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-cancel:hover { background: #f3f4f6; }
</style>

<script lang="ts">
	import { createWildTag } from '$lib/api/tags';
	import { loadTags } from '$lib/stores/tags';
	import { wildTagCategories, assignTag } from '$lib/stores/wildTagCategories';

	let { onDone }: { onDone: () => void } = $props();

	let name = $state('');
	let description = $state('');
	let selectedCategory = $state('wild');
	let color = $state('');

	// Entity categories that will make the tag appear as a default suggestion
	const ENTITY_CATEGORIES = [
		{ value: 'wild', label: 'General (no default)' },
		{ value: 'activity', label: 'Activity' },
		{ value: 'note', label: 'Note' },
		{ value: 'log', label: 'Log' },
		{ value: 'source', label: 'Source' },
		{ value: 'actor', label: 'Actor' },
		{ value: 'project', label: 'Project' },
		{ value: 'readinglist', label: 'Reading List' },
		{ value: 'plan', label: 'Plan' },
	];

	let displayCategoryNames = $derived(Object.keys($wildTagCategories));

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!name.trim()) return;
		const tag = await createWildTag(name.trim(), description.trim() || undefined, selectedCategory, color || undefined);
		// Also assign to display category if one is selected (for visual grouping in WildTagPanel)
		if (displayCategoryNames.length > 0) {
			assignTag(tag.id, displayCategoryNames[0]);
		}
		await loadTags();
		onDone();
	}
</script>

<form onsubmit={handleSubmit} class="form">
	<label>
		Tag Name *
		<input type="text" bind:value={name} required placeholder="e.g. urgent, review" />
	</label>
	<label>
		Description
		<textarea bind:value={description} rows="2" placeholder="Optional description for this tag"></textarea>
	</label>
	<label>
		Default for Entity Type
		<select bind:value={selectedCategory}>
			{#each ENTITY_CATEGORIES as cat (cat.value)}
				<option value={cat.value}>{cat.label}</option>
			{/each}
		</select>
		<span class="hint">Tags will appear as suggestions when creating this entity type</span>
	</label>
	<label class="color-label">
		Color
		<div class="color-row">
			<input type="color" bind:value={color} class="color-picker" />
			{#if color}
				<span class="color-preview" style="background: {color}"></span>
				<button type="button" class="btn-clear-color" onclick={() => (color = '')}>Clear</button>
			{:else}
				<span class="hint">Default (based on category)</span>
			{/if}
		</div>
	</label>
	<div class="form-actions">
		<button type="button" class="btn btn-cancel" onclick={onDone}>Cancel</button>
		<button type="submit" class="btn btn-primary">Create</button>
	</div>
</form>

<style>
	.form { display: flex; flex-direction: column; gap: 12px; }
	label { display: flex; flex-direction: column; gap: 4px; font-size: 0.875rem; font-weight: 500; color: #374151; }
	input, select, textarea { padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.875rem; font-family: inherit; }
	textarea { resize: vertical; }
	.hint { font-size: 0.7rem; color: #9ca3af; font-weight: 400; }
	.form-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 8px; }
	.btn { padding: 8px 16px; border-radius: 6px; border: 1px solid #d1d5db; cursor: pointer; font-size: 0.875rem; }
	.btn-cancel { background: white; }
	.btn-primary { background: #6b7280; color: white; border-color: #6b7280; }
	.color-label { display: flex; flex-direction: column; gap: 4px; font-size: 0.875rem; font-weight: 500; color: #374151; }
	.color-row { display: flex; align-items: center; gap: 8px; }
	.color-picker { width: 36px; height: 30px; padding: 1px; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; background: none; }
	.color-preview { width: 20px; height: 20px; border-radius: 4px; flex-shrink: 0; }
	.btn-clear-color { font-size: 0.75rem; padding: 2px 8px; border: 1px solid #d1d5db; border-radius: 4px; background: white; cursor: pointer; color: #6b7280; }
	.btn-clear-color:hover { background: #f3f4f6; }
</style>

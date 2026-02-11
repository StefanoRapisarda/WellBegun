<script lang="ts">
	import { type Tag, tagCategoryPrefix } from '$lib/types';

	let {
		availableTags = [],
		selectedTagIds = [],
		filterMode = 'or',
		onTagToggle,
		onModeToggle
	}: {
		availableTags: Tag[];
		selectedTagIds: number[];
		filterMode: 'or' | 'and';
		onTagToggle: (tagId: number) => void;
		onModeToggle: () => void;
	} = $props();
</script>

{#if availableTags.length > 0}
	<div class="panel-filter">
		<div class="filter-tags">
			{#each availableTags as tag (tag.id)}
				<button
					class="filter-chip"
					class:selected={selectedTagIds.includes(tag.id)}
					onclick={() => onTagToggle(tag.id)}
				>
					<span class="chip-category">{tagCategoryPrefix(tag)}:</span>{tag.name}
				</button>
			{/each}
		</div>
		{#if selectedTagIds.length > 1}
			<button class="mode-toggle" onclick={onModeToggle}>
				<span class:active={filterMode === 'or'}>OR</span>
				<span class="separator">|</span>
				<span class:active={filterMode === 'and'}>AND</span>
			</button>
		{/if}
		{#if selectedTagIds.length > 0}
			<button class="clear-filter" onclick={() => selectedTagIds.forEach(id => onTagToggle(id))}>
				Clear
			</button>
		{/if}
	</div>
{:else}
	<p class="no-tags">No tags available</p>
{/if}

<style>
	.panel-filter {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px;
		padding: 8px 0;
		border-bottom: 1px solid #e5e7eb;
	}
	.filter-tags {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		flex: 1;
	}
	.filter-chip {
		padding: 3px 8px;
		border: 1px solid #d1d5db;
		border-radius: 12px;
		background: white;
		font-size: 0.7rem;
		cursor: pointer;
		transition: all 0.15s;
		color: #6b7280;
	}
	.filter-chip:hover {
		border-color: #9ca3af;
	}
	.filter-chip.selected {
		background: #374151;
		color: white;
		border-color: #374151;
	}
	.chip-category {
		opacity: 0.7;
		margin-right: 2px;
	}
	.mode-toggle {
		padding: 3px 8px;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		background: #f9fafb;
		font-size: 0.65rem;
		cursor: pointer;
		color: #9ca3af;
		font-weight: 500;
	}
	.mode-toggle span.active {
		color: #111827;
		font-weight: 600;
	}
	.mode-toggle .separator {
		margin: 0 4px;
		color: #d1d5db;
	}
	.clear-filter {
		padding: 3px 8px;
		border: 1px solid #fecaca;
		border-radius: 4px;
		background: #fef2f2;
		font-size: 0.65rem;
		cursor: pointer;
		color: #ef4444;
	}
	.clear-filter:hover {
		background: #fee2e2;
	}
	.no-tags {
		font-size: 0.75rem;
		color: #9ca3af;
		margin: 0;
		padding: 4px 0;
	}
</style>

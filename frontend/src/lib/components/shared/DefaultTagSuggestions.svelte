<script lang="ts">
	import type { Tag } from '$lib/types';
	import { getTagsByCategory } from '$lib/api/tags';
	import { onMount } from 'svelte';

	let {
		category,
		selectedTagIds = $bindable([]),
		keywordMatches = [],
	}: {
		category: string;
		selectedTagIds: number[];
		keywordMatches?: string[];
	} = $props();

	let availableTags = $state<Tag[]>([]);
	let loading = $state(true);
	// Track manual overrides: tags user explicitly clicked
	let manuallySelected = $state<Set<number>>(new Set());
	let manuallyDeselected = $state<Set<number>>(new Set());

	onMount(async () => {
		const allCategoryTags = await getTagsByCategory(category);
		// Only show default tags (entity_id is null), not entity-linked tags
		availableTags = allCategoryTags.filter(t => t.entity_id === null);
		loading = false;
	});

	// Compute auto-matched tag IDs from keywords
	let autoMatchedIds = $derived.by(() => {
		if (availableTags.length === 0) return new Set<number>();
		return new Set(
			availableTags
				.filter(t => keywordMatches.some(kw => t.name.toLowerCase() === kw.toLowerCase()))
				.map(t => t.id)
		);
	});

	// Final selection = (auto-matched + manually selected) - manually deselected
	$effect(() => {
		const finalIds = new Set<number>();
		// Add auto-matched
		for (const id of autoMatchedIds) {
			if (!manuallyDeselected.has(id)) {
				finalIds.add(id);
			}
		}
		// Add manually selected
		for (const id of manuallySelected) {
			finalIds.add(id);
		}
		selectedTagIds = [...finalIds];
	});

	function toggleTag(tagId: number) {
		const isCurrentlySelected = selectedTagIds.includes(tagId);
		const isAutoMatched = autoMatchedIds.has(tagId);

		if (isCurrentlySelected) {
			// Deselecting
			if (isAutoMatched) {
				// Mark as manually deselected (overrides auto-match)
				manuallyDeselected = new Set([...manuallyDeselected, tagId]);
			}
			manuallySelected = new Set([...manuallySelected].filter(id => id !== tagId));
		} else {
			// Selecting
			manuallySelected = new Set([...manuallySelected, tagId]);
			manuallyDeselected = new Set([...manuallyDeselected].filter(id => id !== tagId));
		}
	}

	function isSelected(tagId: number): boolean {
		return selectedTagIds.includes(tagId);
	}
</script>

{#if !loading && availableTags.length > 0}
	<div class="tag-suggestions">
		<span class="label">Tags:</span>
		<div class="tags">
			{#each availableTags as tag (tag.id)}
				<button
					type="button"
					class="tag-chip"
					class:selected={isSelected(tag.id)}
					onclick={() => toggleTag(tag.id)}
				>
					{tag.name}
				</button>
			{/each}
		</div>
	</div>
{/if}

<style>
	.tag-suggestions {
		display: flex;
		align-items: flex-start;
		gap: 8px;
		padding: 8px 0;
	}
	.label {
		font-size: 0.75rem;
		color: #6b7280;
		padding-top: 4px;
		flex-shrink: 0;
	}
	.tags {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.tag-chip {
		padding: 4px 10px;
		border: 1px solid #d1d5db;
		border-radius: 12px;
		background: #f9fafb;
		cursor: pointer;
		font-size: 0.75rem;
		color: #374151;
		transition: all 0.15s;
	}
	.tag-chip:hover {
		background: #e5e7eb;
	}
	.tag-chip.selected {
		background: #3b82f6;
		color: white;
		border-color: #3b82f6;
	}
</style>

<script lang="ts">
	import type { Tag } from '$lib/types';
	import { tagCategoryPrefix } from '$lib/types';
	import { getTagsByCategory } from '$lib/api/tags';
	import { searchTagsStore } from '$lib/stores/tags';
	import { matchTagsToTitle } from '$lib/utils/tagMatcher';
	import { onMount } from 'svelte';

	let {
		category,
		selectedTagIds = $bindable([]),
		title = '',
	}: {
		category: string;
		selectedTagIds: number[];
		title?: string;
	} = $props();

	let availableTags = $state<Tag[]>([]);
	let loading = $state(true);
	// Track manual overrides: tags user explicitly clicked
	let manuallySelected = $state<Set<number>>(new Set());
	let manuallyDeselected = $state<Set<number>>(new Set());
	// Extra tags added via search (not in default category)
	let extraTags = $state<Tag[]>([]);

	// Search state
	let searchValue = $state('');
	let suggestions = $state<Tag[]>([]);
	let showDropdown = $state(false);

	onMount(async () => {
		const allCategoryTags = await getTagsByCategory(category);
		// Only show default tags (entity_id is null), not entity-linked tags
		availableTags = allCategoryTags.filter(t => t.entity_id === null);
		loading = false;
	});

	// Compute auto-matched tag IDs from title
	let autoMatchedIds = $derived.by(() => {
		if (availableTags.length === 0 || !title.trim()) return new Set<number>();
		const matchedNames = matchTagsToTitle(title, availableTags, category);
		return new Set(
			availableTags
				.filter(t => matchedNames.includes(t.name))
				.map(t => t.id)
		);
	});

	// All known tag IDs (defaults + extras)
	let allKnownIds = $derived(new Set([...availableTags.map(t => t.id), ...extraTags.map(t => t.id)]));

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

	async function handleSearchInput() {
		const query = searchValue.trim();
		if (query.length > 0) {
			const results = await searchTagsStore(query);
			// Filter out tags already shown as default chips or extra chips
			suggestions = results.filter(s => !allKnownIds.has(s.id));
			showDropdown = suggestions.length > 0;
		} else {
			showDropdown = false;
			suggestions = [];
		}
	}

	function selectSuggestion(tag: Tag) {
		// Add to extras so it appears as a chip
		extraTags = [...extraTags, tag];
		// Select it
		manuallySelected = new Set([...manuallySelected, tag.id]);
		manuallyDeselected = new Set([...manuallyDeselected].filter(id => id !== tag.id));
		searchValue = '';
		showDropdown = false;
		suggestions = [];
	}

	function handleSearchBlur() {
		setTimeout(() => { showDropdown = false; }, 200);
	}
</script>

{#if !loading}
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
			{#each extraTags as tag (tag.id)}
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
		<div class="search-container">
			<input
				type="text"
				bind:value={searchValue}
				oninput={handleSearchInput}
				onblur={handleSearchBlur}
				placeholder="Search tags..."
				class="tag-search"
			/>
			{#if showDropdown}
				<ul class="suggestions">
					{#each suggestions as tag (tag.id)}
						<li>
							<button onmousedown={(e) => { e.preventDefault(); selectSuggestion(tag); }}>
								<span class="suggestion-category">{tagCategoryPrefix(tag)}</span>
								{tag.name}
							</button>
						</li>
					{/each}
				</ul>
			{/if}
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
	.search-container {
		position: relative;
		flex-shrink: 0;
	}
	.tag-search {
		width: 120px;
		padding: 4px 8px;
		border: 1px solid #d1d5db;
		border-radius: 12px;
		font-size: 0.75rem;
		background: white;
		outline: none;
	}
	.tag-search:focus {
		border-color: #3b82f6;
		box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
	}
	.suggestions {
		position: absolute;
		top: 100%;
		left: 0;
		right: 0;
		min-width: 180px;
		background: white;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		list-style: none;
		padding: 0;
		margin: 2px 0 0;
		max-height: 200px;
		overflow-y: auto;
		z-index: 100;
		box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
	}
	.suggestions li button {
		display: block;
		width: 100%;
		text-align: left;
		padding: 6px 10px;
		border: none;
		background: none;
		cursor: pointer;
		font-size: 0.8rem;
	}
	.suggestions li button:hover {
		background: #f3f4f6;
	}
	.suggestion-category {
		display: inline-block;
		font-size: 0.65rem;
		color: #9ca3af;
		margin-right: 4px;
		text-transform: uppercase;
	}
</style>

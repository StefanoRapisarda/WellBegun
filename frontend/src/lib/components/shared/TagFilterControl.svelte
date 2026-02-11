<script lang="ts">
	import { type Tag, tagCategoryPrefix } from '$lib/types';
	import { selectedFilterTags, addFilterTag, removeFilterTag, clearFilterTags } from '$lib/stores/dateFilter';
	import { searchTagsStore } from '$lib/stores/tags';
	import TagBadge from './TagBadge.svelte';

	let inputValue = $state('');
	let suggestions = $state<Tag[]>([]);
	let showDropdown = $state(false);
	let inputEl: HTMLInputElement | undefined = $state();

	async function handleInput() {
		let query = inputValue.trim();
		if (query.startsWith('#')) {
			query = query.slice(1);
		}
		if (query.length > 0 || inputValue === '#') {
			suggestions = await searchTagsStore(query);
			// Filter out already selected tags
			suggestions = suggestions.filter(
				(s) => !$selectedFilterTags.some((t) => t.id === s.id)
			);
			showDropdown = suggestions.length > 0;
		} else {
			showDropdown = false;
			suggestions = [];
		}
	}

	function selectSuggestion(tag: Tag) {
		addFilterTag(tag);
		inputValue = '';
		showDropdown = false;
		suggestions = [];
		requestAnimationFrame(() => {
			inputEl?.focus();
		});
	}

	function handleBlur() {
		setTimeout(() => {
			showDropdown = false;
		}, 200);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			inputValue = '';
			showDropdown = false;
		}
	}
</script>

<div class="tag-filter">
	<span class="filter-label">Tags:</span>
	<div class="filter-input-wrapper">
		<div class="selected-tags">
			{#each $selectedFilterTags as tag (tag.id)}
				<TagBadge {tag} removable onRemove={() => removeFilterTag(tag.id)} />
			{/each}
			<input
				bind:this={inputEl}
				type="text"
				bind:value={inputValue}
				oninput={handleInput}
				onblur={handleBlur}
				onkeydown={handleKeydown}
				placeholder={$selectedFilterTags.length > 0 ? "+" : "Filter by tags..."}
				class="tag-input"
			/>
		</div>
		{#if showDropdown}
			<ul class="suggestions">
				{#each suggestions as tag (tag.id)}
					<li>
						<button onmousedown={(e: MouseEvent) => { e.preventDefault(); selectSuggestion(tag); }}>
							<span class="tag-category">{tagCategoryPrefix(tag)}</span>
							{tag.name}
						</button>
					</li>
				{/each}
			</ul>
		{/if}
	</div>
	{#if $selectedFilterTags.length > 0}
		<button class="clear-btn" onclick={clearFilterTags}>Clear</button>
	{/if}
</div>

<style>
	.tag-filter {
		display: flex;
		align-items: center;
		gap: 6px;
		min-width: 0;
	}
	.filter-label {
		font-size: 0.7rem;
		color: #6b7280;
		font-weight: 500;
		flex-shrink: 0;
	}
	.filter-input-wrapper {
		position: relative;
		min-width: 0;
	}
	.selected-tags {
		display: flex;
		flex-wrap: nowrap;
		align-items: center;
		gap: 3px;
		padding: 2px 6px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		background: white;
		min-height: 26px;
		min-width: 120px;
		overflow: hidden;
	}
	.selected-tags:focus-within {
		border-color: #3b82f6;
		box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
	}
	.tag-input {
		flex: 1;
		min-width: 60px;
		padding: 2px 4px;
		border: none;
		outline: none;
		font-size: 0.7rem;
		background: transparent;
	}
	.suggestions {
		position: absolute;
		top: 100%;
		left: 0;
		right: 0;
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
	.tag-category {
		display: inline-block;
		font-size: 0.65rem;
		color: #9ca3af;
		margin-right: 4px;
		text-transform: uppercase;
	}
	.clear-btn {
		padding: 3px 6px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		background: #f9fafb;
		color: #6b7280;
		font-size: 0.65rem;
		cursor: pointer;
		transition: all 0.15s;
		flex-shrink: 0;
		white-space: nowrap;
	}
	.clear-btn:hover {
		background: #fee2e2;
		color: #ef4444;
		border-color: #fecaca;
	}
</style>

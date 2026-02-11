<script lang="ts">
	import { type Tag, tagCategoryPrefix } from '$lib/types';
	import { getTagsByCategory } from '$lib/api/tags';
	import { searchTagsStore } from '$lib/stores/tags';
	import TagBadge from './TagBadge.svelte';
	import { onMount } from 'svelte';

	let { attachedTags = [], targetType, targetId, onAttach, onDetach, onClose }: {
		attachedTags: Tag[];
		targetType: string;
		targetId: number;
		onAttach: (tag: Tag) => void;
		onDetach: (tag: Tag) => void;
		onClose?: () => void;
	} = $props();

	// Map targetType to tag category
	const TARGET_TO_CATEGORY: Record<string, string> = {
		'learning_track': 'learningtrack',
		'reading_list': 'readinglist',
	};

	let category = $derived(TARGET_TO_CATEGORY[targetType] || targetType);

	let categoryTags = $state<Tag[]>([]);
	let inputValue = $state('');
	let suggestions = $state<Tag[]>([]);
	let showDropdown = $state(false);
	let inputEl: HTMLInputElement | undefined = $state();

	// Tags selected in the input bar (not yet attached)
	let pendingTags = $state<Tag[]>([]);

	// Load default tags for this category
	onMount(async () => {
		const allCategoryTags = await getTagsByCategory(category);
		// Only show standalone (wild) tags, not entity-linked tags
		categoryTags = allCategoryTags.filter(t => t.entity_id === null);
	});

	// Filter out already-attached tags from the default chips
	let availableDefaults = $derived(
		categoryTags.filter(t =>
			!attachedTags.some(a => a.id === t.id) &&
			!pendingTags.some(p => p.id === t.id)
		)
	);

	function toggleDefault(tag: Tag) {
		if (pendingTags.some(p => p.id === tag.id)) {
			pendingTags = pendingTags.filter(p => p.id !== tag.id);
		} else {
			pendingTags = [...pendingTags, tag];
		}
	}

	async function handleInput() {
		let query = inputValue.trim();
		if (query.startsWith('#')) {
			query = query.slice(1);
		}
		if (query.length > 0 || inputValue === '#') {
			suggestions = await searchTagsStore(query);
			// Filter out already attached, pending, and visible default tags
			suggestions = suggestions.filter(
				(s) => !attachedTags.some((t) => t.id === s.id) &&
				       !pendingTags.some((t) => t.id === s.id)
			);
			showDropdown = suggestions.length > 0;
		} else {
			showDropdown = false;
			suggestions = [];
		}
	}

	function selectSuggestion(tag: Tag) {
		pendingTags = [...pendingTags, tag];
		inputValue = '';
		showDropdown = false;
		suggestions = [];
		requestAnimationFrame(() => {
			inputEl?.focus();
		});
	}

	function removePendingTag(tag: Tag) {
		pendingTags = pendingTags.filter(t => t.id !== tag.id);
	}

	function attachPendingTags() {
		for (const tag of pendingTags) {
			onAttach(tag);
		}
		pendingTags = [];
		inputValue = '';
	}

	function handleBlur() {
		setTimeout(() => {
			showDropdown = false;
		}, 200);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			attachPendingTags();
			onClose?.();
		} else if (e.key === 'Escape') {
			pendingTags = [];
			inputValue = '';
			onClose?.();
		} else if (e.key === 'Backspace' && inputValue === '' && pendingTags.length > 0) {
			pendingTags = pendingTags.slice(0, -1);
		}
	}
</script>

<div class="tag-input-wrapper">
	{#if availableDefaults.length > 0}
		<div class="default-tags">
			{#each availableDefaults as tag (tag.id)}
				<button
					type="button"
					class="default-chip"
					class:selected={pendingTags.some(p => p.id === tag.id)}
					onclick={() => toggleDefault(tag)}
				>
					{tag.name}
				</button>
			{/each}
		</div>
	{/if}
	<div class="input-container">
		<div class="input-with-pills">
			{#each pendingTags as tag (tag.id)}
				<TagBadge {tag} removable onRemove={() => removePendingTag(tag)} />
			{/each}
			<input
				bind:this={inputEl}
				type="text"
				bind:value={inputValue}
				oninput={handleInput}
				onblur={handleBlur}
				onkeydown={handleKeydown}
				placeholder={pendingTags.length > 0 ? "Enter to add, type for more..." : "Search tags..."}
				class="tag-search-input"
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
</div>

<style>
	.tag-input-wrapper {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.default-tags {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.default-chip {
		padding: 3px 10px;
		border: 1px solid #d1d5db;
		border-radius: 12px;
		background: #f9fafb;
		cursor: pointer;
		font-size: 0.75rem;
		color: #374151;
		transition: all 0.15s;
	}
	.default-chip:hover {
		background: #e5e7eb;
	}
	.default-chip.selected {
		background: #3b82f6;
		color: white;
		border-color: #3b82f6;
	}
	.input-container {
		position: relative;
	}
	.input-with-pills {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 4px;
		padding: 4px 6px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		background: white;
		min-height: 34px;
	}
	.input-with-pills:focus-within {
		border-color: #3b82f6;
		box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
	}
	.tag-search-input {
		flex: 1;
		min-width: 120px;
		padding: 2px 4px;
		border: none;
		outline: none;
		font-size: 0.875rem;
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
		font-size: 0.875rem;
	}
	.suggestions li button:hover {
		background: #f3f4f6;
	}
	.tag-category {
		display: inline-block;
		font-size: 0.7rem;
		color: #9ca3af;
		margin-right: 4px;
		text-transform: uppercase;
	}
</style>

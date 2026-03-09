<script lang="ts">
	import { onMount } from 'svelte';
	import { searchEntities, type SearchResult } from '$lib/api/search';
	import { tags } from '$lib/stores/tags';
	import { type Tag, tagCategoryPrefix } from '$lib/types';
	import TagBadge from './TagBadge.svelte';

	const ENTITY_TYPES = [
		{ value: 'note', label: 'Note' },
		{ value: 'log', label: 'Log' },
		{ value: 'project', label: 'Project' },
		{ value: 'activity', label: 'Activity' },
		{ value: 'source', label: 'Source' },
		{ value: 'actor', label: 'Actor' },
		{ value: 'plan', label: 'Plan' },
		{ value: 'collection', label: 'Collection' },
	];

	const TYPE_COLORS: Record<string, string> = {
		project: '#5c7a99',
		log: '#8b7355',
		note: '#6b8e6b',
		activity: '#b5838d',
		source: '#c9a227',
		actor: '#8b4557',
		plan: '#6b8ba3',
		collection: '#7c6f9e',
	};

	export interface QueryPanelState {
		results: SearchResult[];
		includeArchived: boolean;
		showActiveRelated: boolean;
		hasActiveFilters: boolean;
	}

	let {
		open,
		onClose,
		onResultClick,
		onStateChange,
		resultActionLabel = 'Select',
		showArchivedToggle = false,
		showActiveRelatedToggle = false,
		selectionMode = false,
		boardEntityKeys,
		injectedResults,
		injectedLabel,
		onClearInjected,
	}: {
		open: boolean;
		onClose?: () => void;
		onResultClick: (result: SearchResult) => void;
		onStateChange?: (state: QueryPanelState) => void;
		resultActionLabel?: string;
		showArchivedToggle?: boolean;
		showActiveRelatedToggle?: boolean;
		selectionMode?: boolean;
		boardEntityKeys?: Set<string>;
		injectedResults?: SearchResult[];
		injectedLabel?: string;
		onClearInjected?: () => void;
	} = $props();

	// Internal state
	let queryText = $state('');
	let startDate = $state('');
	let endDate = $state('');
	let selectedTypes = $state<Set<string>>(new Set());
	let selectedTagIds = $state<Set<number>>(new Set());
	let tagFilterMode = $state<'or' | 'and'>('or');
	let includeArchived = $state(false);
	let showActiveRelated = $state(false);
	let results = $state<SearchResult[]>([]);
	let loading = $state(false);
	let showTagFilter = $state(false);
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;

	// "Related to" filter — entity tags
	let relatedToInput = $state('');
	let relatedToTags = $state<Tag[]>([]);
	let showRelatedDropdown = $state(false);
	let relatedInputEl: HTMLInputElement | undefined = $state();

	let entityTags = $derived($tags.filter(t => t.entity_type != null));
	let relatedToIds = $derived(new Set(relatedToTags.map(t => t.id)));
	let entityTagSuggestions = $derived.by(() => {
		const q = relatedToInput.trim().toLowerCase();
		if (!q) return [];
		return entityTags
			.filter(t => !relatedToIds.has(t.id) && t.name.toLowerCase().includes(q))
			.slice(0, 20);
	});

	function selectRelatedEntity(tag: Tag) {
		relatedToTags = [...relatedToTags, tag];
		relatedToInput = '';
		showRelatedDropdown = false;
		debouncedSearch();
	}

	function removeRelatedEntity(tagId: number) {
		relatedToTags = relatedToTags.filter(t => t.id !== tagId);
		debouncedSearch();
	}

	function clearRelatedTo() {
		relatedToTags = [];
		debouncedSearch();
	}

	// When injected results are provided, show those (excluding on-board entities); otherwise show search results
	let displayResults = $derived.by(() => {
		if (injectedResults && injectedResults.length > 0) {
			return injectedResults.filter(r => !isOnBoard(r));
		}
		return results;
	});

	let showingInjected = $derived(!!(injectedResults && injectedResults.length > 0));

	let activeFilters = $derived(!!(queryText || startDate || endDate || selectedTypes.size > 0 || selectedTagIds.size > 0 || relatedToTags.length > 0));

	// Notify parent of state changes
	$effect(() => {
		onStateChange?.({
			results,
			includeArchived,
			showActiveRelated,
			hasActiveFilters: activeFilters,
		});
	});

	let wildTags = $derived($tags.filter(t => !t.entity_type));
	let tagsByCategory = $derived.by(() => {
		const grouped = new Map<string, Tag[]>();
		for (const tag of wildTags) {
			const category = tag.category || 'uncategorized';
			if (!grouped.has(category)) grouped.set(category, []);
			grouped.get(category)!.push(tag);
		}
		const sorted = new Map([...grouped.entries()].sort((a, b) => a[0].localeCompare(b[0])));
		for (const [, tagList] of sorted) {
			tagList.sort((a, b) => a.name.localeCompare(b.name));
		}
		return sorted;
	});

	function toggleType(type: string) {
		if (selectedTypes.has(type)) {
			selectedTypes.delete(type);
		} else {
			selectedTypes.add(type);
		}
		selectedTypes = new Set(selectedTypes);
		debouncedSearch();
	}

	function toggleTag(tagId: number) {
		if (selectedTagIds.has(tagId)) {
			selectedTagIds.delete(tagId);
		} else {
			selectedTagIds.add(tagId);
		}
		selectedTagIds = new Set(selectedTagIds);
		debouncedSearch();
	}

	function toggleTagMode() {
		tagFilterMode = tagFilterMode === 'or' ? 'and' : 'or';
		debouncedSearch();
	}

	function clearTagFilter() {
		selectedTagIds = new Set();
		debouncedSearch();
	}

	function debouncedSearch() {
		if (debounceTimer) clearTimeout(debounceTimer);
		onClearInjected?.();
		debounceTimer = setTimeout(() => doSearch(), 300);
	}

	export function refresh() {
		doSearch();
	}

	async function doSearch() {
		loading = true;
		// Combine wild tag IDs and entity tag IDs (from "Related to")
		const allTagIds = [...selectedTagIds, ...relatedToTags.map(t => t.id)];
		results = await searchEntities({
			q: queryText || undefined,
			types: selectedTypes.size > 0 ? [...selectedTypes] : undefined,
			start_date: startDate || undefined,
			end_date: endDate || undefined,
			tag_ids: allTagIds.length > 0 ? allTagIds : undefined,
			tag_mode: allTagIds.length > 1 ? tagFilterMode : undefined,
			include_archived: includeArchived || undefined,
		});
		loading = false;
	}

	function resultKey(r: SearchResult): string {
		return `${r.type}:${r.id}`;
	}

	function isOnBoard(r: SearchResult): boolean {
		return boardEntityKeys?.has(resultKey(r)) ?? false;
	}

	// --- Selection mode ---
	let selectedKeys = $state<Set<string>>(new Set());

	function handleResultClick(result: SearchResult, e: MouseEvent) {
		if (!selectionMode) {
			onResultClick(result);
			return;
		}
		const key = resultKey(result);
		if (e.metaKey || e.ctrlKey) {
			// Toggle in multi-select
			const next = new Set(selectedKeys);
			if (next.has(key)) next.delete(key);
			else next.add(key);
			selectedKeys = next;
		} else {
			// Single select (toggle if already selected)
			selectedKeys = selectedKeys.has(key) && selectedKeys.size === 1
				? new Set()
				: new Set([key]);
		}
	}

	function handleResultDblClick(result: SearchResult) {
		if (!selectionMode) return; // already handled by onclick
		onResultClick(result);
		selectedKeys = new Set();
	}

	export function clearSelection() {
		selectedKeys = new Set();
	}

	function buildDragData(result: SearchResult): string {
		if (!selectionMode || selectedKeys.size === 0) {
			return JSON.stringify([{ type: result.type, id: result.id, title: result.title }]);
		}
		// Include the dragged item + all selected items
		const keys = new Set(selectedKeys);
		keys.add(resultKey(result));
		const items = displayResults
			.filter(r => keys.has(resultKey(r)))
			.map(r => ({ type: r.type, id: r.id, title: r.title }));
		return JSON.stringify(items);
	}

	onMount(() => {
		doSearch();
	});
</script>

{#if open}
	<div class="query-panel">
		{#if onClose}
			<button class="btn-slide-close" onclick={onClose} title="Close panel">
				<svg width="10" height="16" viewBox="0 0 10 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<polyline points="2 2 8 8 2 14"></polyline>
				</svg>
			</button>
		{/if}
		<div class="qp-header">
			<span class="qp-title">Search</span>
		</div>
		<div class="qp-body">
			<!-- Text search -->
			<div class="qp-section">
				<input
					type="text"
					class="qp-search-input"
					placeholder="Search..."
					bind:value={queryText}
					oninput={debouncedSearch}
				/>
			</div>

			<!-- Date range -->
			<div class="qp-section">
				<div class="qp-section-label">Date Range</div>
				<div class="qp-date-row">
					<input type="date" class="qp-date-input" bind:value={startDate} onchange={debouncedSearch} />
					<span class="qp-date-sep">to</span>
					<input type="date" class="qp-date-input" bind:value={endDate} onchange={debouncedSearch} />
				</div>
			</div>

			<!-- Entity types -->
			<div class="qp-section">
				<div class="qp-section-label">Types</div>
				<div class="qp-type-grid">
					{#each ENTITY_TYPES as et}
						<label class="qp-type-check" style:--type-color={TYPE_COLORS[et.value]}>
							<input
								type="checkbox"
								checked={selectedTypes.has(et.value)}
								onchange={() => toggleType(et.value)}
							/>
							{et.label}
						</label>
					{/each}
				</div>
			</div>

			<!-- Related to (entity relationship filter) -->
			<div class="qp-section">
				<div class="qp-section-label">Related to</div>
				{#if relatedToTags.length > 0}
					<div class="qp-related-pills">
						{#each relatedToTags as tag (tag.id)}
							<span class="qp-related-pill" style:--pill-color={TYPE_COLORS[tag.entity_type ?? ''] ?? '#888'}>
								<span class="qp-related-type">{tag.entity_type}</span>
								<span class="qp-related-name">{tag.name}</span>
								<button class="qp-remove-tag" onclick={() => removeRelatedEntity(tag.id)}>&times;</button>
							</span>
						{/each}
						{#if relatedToTags.length > 1}
							<button class="qp-mode-toggle" onclick={toggleTagMode}>
								<span class:active={tagFilterMode === 'or'}>OR</span>
								<span class="qp-mode-sep">|</span>
								<span class:active={tagFilterMode === 'and'}>AND</span>
							</button>
						{/if}
						<button class="qp-clear-tags" onclick={clearRelatedTo}>Clear</button>
					</div>
				{/if}
				<div class="qp-related-search-wrapper">
					<input
						type="text"
						class="qp-search-input"
						placeholder="Search entity..."
						bind:value={relatedToInput}
						bind:this={relatedInputEl}
						onfocus={() => showRelatedDropdown = true}
						oninput={() => showRelatedDropdown = true}
						onblur={() => setTimeout(() => showRelatedDropdown = false, 200)}
					/>
					{#if showRelatedDropdown && entityTagSuggestions.length > 0}
						<div class="qp-related-dropdown">
							{#each entityTagSuggestions as suggestion (suggestion.id)}
								<button
									class="qp-related-option"
									onmousedown={(e) => { e.preventDefault(); selectRelatedEntity(suggestion); }}
								>
									<span class="qp-type-badge" style:background={TYPE_COLORS[suggestion.entity_type ?? ''] ?? '#888'}>
										{suggestion.entity_type}
									</span>
									<span class="qp-related-option-name">{suggestion.name}</span>
								</button>
							{/each}
						</div>
					{/if}
				</div>
			</div>

			<!-- Tags -->
			<div class="qp-section">
				<button
					class="qp-tag-toggle"
					class:active={showTagFilter || selectedTagIds.size > 0}
					onclick={() => (showTagFilter = !showTagFilter)}
				>
					Tags
					{#if selectedTagIds.size > 0}
						<span class="qp-tag-count">{selectedTagIds.size}</span>
					{/if}
				</button>

				{#if selectedTagIds.size > 0}
					<div class="qp-selected-tags">
						{#each [...selectedTagIds] as tagId}
							{@const tag = $tags.find(t => t.id === tagId)}
							{#if tag}
								<span class="qp-filter-tag">
									<span class="qp-tag-cat">{tagCategoryPrefix(tag)}:</span>{tag.name}
									<button class="qp-remove-tag" onclick={() => toggleTag(tagId)}>&times;</button>
								</span>
							{/if}
						{/each}
						{#if selectedTagIds.size > 1}
							<button class="qp-mode-toggle" onclick={toggleTagMode}>
								<span class:active={tagFilterMode === 'or'}>OR</span>
								<span class="qp-mode-sep">|</span>
								<span class:active={tagFilterMode === 'and'}>AND</span>
							</button>
						{/if}
						<button class="qp-clear-tags" onclick={clearTagFilter}>Clear</button>
					</div>
				{/if}

				{#if showTagFilter}
					<div class="qp-tag-panel">
						{#if wildTags.length === 0}
							<p class="qp-no-tags">No tags available.</p>
						{:else}
							{#each [...tagsByCategory] as [category, categoryTags] (category)}
								<div class="qp-tag-group">
									<span class="qp-cat-label">{category}</span>
									<div class="qp-cat-tags">
										{#each categoryTags as tag (tag.id)}
											<button
												class="qp-tag-chip"
												class:selected={selectedTagIds.has(tag.id)}
												onclick={() => toggleTag(tag.id)}
											>
												{tag.name}
											</button>
										{/each}
									</div>
								</div>
							{/each}
						{/if}
					</div>
				{/if}
			</div>

			<!-- Extra toggles -->
			{#if showArchivedToggle || showActiveRelatedToggle}
				<div class="qp-section qp-toggles">
					{#if showArchivedToggle}
						<label class="qp-toggle">
							<input type="checkbox" bind:checked={includeArchived} onchange={debouncedSearch} />
							Show archived
						</label>
					{/if}
					{#if showActiveRelatedToggle}
						<label class="qp-toggle">
							<input type="checkbox" bind:checked={showActiveRelated} />
							Active related
						</label>
					{/if}
				</div>
			{/if}

			<!-- Results -->
			<div class="qp-results">
				{#if showingInjected && injectedLabel}
					<div class="qp-injected-header">
						<span class="qp-injected-label">{injectedLabel}</span>
						<button class="qp-injected-clear" onclick={() => onClearInjected?.()}>Back to search</button>
					</div>
				{/if}
				{#if loading && !showingInjected}
					<div class="qp-status">Searching...</div>
				{:else if displayResults.length === 0}
					<div class="qp-status">{showingInjected ? 'All connections are on the board' : 'No results'}</div>
				{:else}
					{#each displayResults as result (resultKey(result))}
						<button
							class="qp-result"
							class:on-board={isOnBoard(result)}
							class:selected={selectionMode && selectedKeys.has(resultKey(result))}
							onclick={(e) => handleResultClick(result, e)}
							ondblclick={() => handleResultDblClick(result)}
							draggable="true"
							ondragstart={(e) => {
								e.dataTransfer?.setData("application/wb-entity", buildDragData(result));
								e.dataTransfer!.effectAllowed = "copy";
							}}
							ondragend={() => { if (selectionMode) selectedKeys = new Set(); }}
						>
							<div class="qp-result-header">
								<span class="qp-drag-handle" title="Drag to workspace">&#x2630;</span>
								<span class="qp-type-badge" style:background={TYPE_COLORS[result.type] ?? '#888'}>{result.type}</span>
								<span class="qp-result-title">{result.title}</span>
								{#if isOnBoard(result)}
									<span class="qp-on-board-dot" title="On board"></span>
								{/if}
							</div>
							{#if result.tags.length > 0}
								<div class="qp-result-tags">
									{#each result.tags.slice(0, 3) as tag (tag.id)}
										<TagBadge {tag} />
									{/each}
									{#if result.tags.length > 3}
										<span class="qp-more-tags">+{result.tags.length - 3}</span>
									{/if}
								</div>
							{/if}
						</button>
					{/each}
				{/if}
			</div>
		</div>
	</div>
{/if}

<style>
	.query-panel {
		position: absolute;
		top: 0;
		right: 0;
		width: 280px;
		height: 100%;
		background: white;
		border-left: 1px solid #e5e7eb;
		box-shadow: -2px 0 12px rgba(0, 0, 0, 0.06);
		z-index: 50;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}
	.btn-slide-close {
		position: absolute;
		left: 0;
		top: 50%;
		transform: translateY(-50%);
		z-index: 10;
		width: 16px;
		height: 48px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: 1px solid #e5e7eb;
		border-left: none;
		border-radius: 0 6px 6px 0;
		background: #f9fafb;
		cursor: pointer;
		color: #9ca3af;
		opacity: 0;
		transition: opacity 0.2s, background 0.15s, color 0.15s;
		padding: 0;
	}
	.query-panel:hover .btn-slide-close {
		opacity: 1;
	}
	.btn-slide-close:hover {
		background: #e5e7eb;
		color: #374151;
	}
	.qp-header {
		display: flex;
		align-items: center;
		padding: 12px 14px;
		border-bottom: 1px solid #e5e7eb;
		flex-shrink: 0;
	}
	.qp-title {
		font-size: 0.8rem;
		font-weight: 600;
		color: #374151;
	}
	.qp-body {
		flex: 1;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
	}
	.qp-section {
		padding: 8px 14px;
		border-bottom: 1px solid #f3f4f6;
	}
	.qp-section-label {
		font-size: 0.7rem;
		font-weight: 600;
		color: #9ca3af;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		margin-bottom: 6px;
	}
	.qp-search-input {
		width: 100%;
		padding: 6px 10px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 0.8rem;
		outline: none;
		box-sizing: border-box;
	}
	.qp-search-input:focus {
		border-color: #9ca3af;
	}
	.qp-date-row {
		display: flex;
		align-items: center;
		gap: 4px;
	}
	.qp-date-input {
		flex: 1;
		padding: 4px 6px;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		font-size: 0.72rem;
		min-width: 0;
	}
	.qp-date-sep {
		font-size: 0.7rem;
		color: #9ca3af;
	}
	.qp-type-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 2px 8px;
	}
	.qp-type-check {
		display: flex;
		align-items: center;
		gap: 4px;
		font-size: 0.72rem;
		color: #374151;
		cursor: pointer;
	}
	.qp-type-check input[type="checkbox"] {
		accent-color: var(--type-color);
		width: 12px;
		height: 12px;
	}

	/* Related to */
	.qp-related-pills {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		margin-bottom: 6px;
	}
	.qp-related-pill {
		display: inline-flex;
		align-items: center;
		gap: 3px;
		padding: 2px 6px;
		background: var(--pill-color, #374151);
		border-radius: 10px;
		font-size: 0.65rem;
		color: white;
	}
	.qp-related-type {
		opacity: 0.8;
		font-size: 0.58rem;
		text-transform: uppercase;
	}
	.qp-related-name {
		max-width: 120px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.qp-related-search-wrapper {
		position: relative;
	}
	.qp-related-dropdown {
		position: absolute;
		top: 100%;
		left: 0;
		right: 0;
		background: white;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
		z-index: 60;
		max-height: 180px;
		overflow-y: auto;
	}
	.qp-related-option {
		display: flex;
		align-items: center;
		gap: 6px;
		width: 100%;
		padding: 6px 10px;
		border: none;
		background: none;
		cursor: pointer;
		text-align: left;
		font-size: 0.75rem;
		color: #374151;
	}
	.qp-related-option:hover {
		background: #f3f4f6;
	}
	.qp-related-option-name {
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	/* Tag filter */
	.qp-tag-toggle {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 4px 10px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		background: white;
		cursor: pointer;
		font-size: 0.72rem;
		color: #6b7280;
		width: 100%;
		box-sizing: border-box;
	}
	.qp-tag-toggle.active {
		border-color: #3b82f6;
		color: #3b82f6;
		background: #eff6ff;
	}
	.qp-tag-count {
		background: #3b82f6;
		color: white;
		font-size: 0.6rem;
		padding: 0 5px;
		border-radius: 10px;
		font-weight: 600;
	}
	.qp-selected-tags {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		margin-top: 6px;
	}
	.qp-filter-tag {
		display: inline-flex;
		align-items: center;
		gap: 2px;
		padding: 2px 6px;
		background: #374151;
		border-radius: 10px;
		font-size: 0.65rem;
		color: white;
	}
	.qp-tag-cat {
		opacity: 0.7;
		margin-right: 1px;
	}
	.qp-remove-tag {
		background: none;
		border: none;
		cursor: pointer;
		font-size: 0.8rem;
		color: rgba(255,255,255,0.7);
		padding: 0 1px;
		line-height: 1;
	}
	.qp-remove-tag:hover {
		color: white;
	}
	.qp-mode-toggle {
		padding: 2px 6px;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		background: #f9fafb;
		font-size: 0.6rem;
		cursor: pointer;
		color: #9ca3af;
		font-weight: 500;
	}
	.qp-mode-toggle span.active {
		color: #111827;
		font-weight: 600;
	}
	.qp-mode-sep {
		margin: 0 2px;
		color: #d1d5db;
	}
	.qp-clear-tags {
		padding: 2px 6px;
		border: 1px solid #fecaca;
		border-radius: 4px;
		background: #fef2f2;
		font-size: 0.65rem;
		cursor: pointer;
		color: #ef4444;
	}
	.qp-tag-panel {
		background: #f9fafb;
		border: 1px solid #e5e7eb;
		border-radius: 6px;
		padding: 8px;
		margin-top: 6px;
		max-height: 160px;
		overflow-y: auto;
	}
	.qp-no-tags {
		font-size: 0.72rem;
		color: #9ca3af;
		margin: 0;
		text-align: center;
	}
	.qp-tag-group {
		margin-bottom: 6px;
	}
	.qp-tag-group:last-child {
		margin-bottom: 0;
	}
	.qp-cat-label {
		font-size: 0.65rem;
		font-weight: 600;
		color: #6b7280;
		text-transform: uppercase;
		letter-spacing: 0.4px;
		display: block;
		margin-bottom: 3px;
	}
	.qp-cat-tags {
		display: flex;
		flex-wrap: wrap;
		gap: 3px;
	}
	.qp-tag-chip {
		padding: 2px 8px;
		border: 1px solid #d1d5db;
		border-radius: 12px;
		background: white;
		font-size: 0.68rem;
		cursor: pointer;
		color: #374151;
	}
	.qp-tag-chip:hover {
		border-color: #9ca3af;
		background: #f3f4f6;
	}
	.qp-tag-chip.selected {
		background: #374151;
		color: white;
		border-color: #374151;
	}

	/* Toggles */
	.qp-toggles {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.qp-toggle {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 0.72rem;
		color: #4b5563;
		cursor: pointer;
	}
	.qp-toggle input[type="checkbox"] {
		width: 13px;
		height: 13px;
		accent-color: #6b7280;
		cursor: pointer;
	}

	/* Injected results header */
	.qp-injected-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 6px 14px;
		background: #eff6ff;
		border-bottom: 1px solid #dbeafe;
	}
	.qp-injected-label {
		font-size: 0.7rem;
		font-weight: 600;
		color: #3b82f6;
	}
	.qp-injected-clear {
		font-size: 0.65rem;
		padding: 2px 8px;
		border: 1px solid #bfdbfe;
		border-radius: 4px;
		background: white;
		color: #3b82f6;
		cursor: pointer;
	}
	.qp-injected-clear:hover {
		background: #dbeafe;
	}

	/* Results */
	.qp-results {
		flex: 1;
		overflow-y: auto;
		padding: 4px 0;
		min-height: 100px;
	}
	.qp-status {
		text-align: center;
		color: #9ca3af;
		font-size: 0.75rem;
		padding: 20px 14px;
	}
	.qp-result {
		display: block;
		width: 100%;
		text-align: left;
		padding: 8px 14px;
		background: none;
		border: none;
		border-bottom: 1px solid #f3f4f6;
		cursor: pointer;
		transition: background 0.1s;
	}
	.qp-result:hover {
		background: #f9fafb;
	}
	.qp-result.on-board {
		background: #f0fdf4;
	}
	.qp-result.selected {
		background: #dbeafe;
		border-left: 3px solid #3b82f6;
		padding-left: 11px;
	}
	.qp-drag-handle {
		font-size: 0.7rem;
		color: #d1d5db;
		cursor: grab;
		flex-shrink: 0;
		line-height: 1;
	}
	.qp-result:hover .qp-drag-handle {
		color: #9ca3af;
	}
	.qp-result-header {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.qp-type-badge {
		font-size: 0.6rem;
		padding: 1px 6px;
		border-radius: 3px;
		color: white;
		font-weight: 500;
		text-transform: capitalize;
		white-space: nowrap;
		flex-shrink: 0;
	}
	.qp-result-title {
		flex: 1;
		font-size: 0.78rem;
		font-weight: 500;
		color: #111827;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.qp-on-board-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: #22c55e;
		flex-shrink: 0;
	}
	.qp-result-tags {
		display: flex;
		flex-wrap: wrap;
		gap: 3px;
		margin-top: 4px;
	}
	.qp-more-tags {
		font-size: 0.6rem;
		color: #9ca3af;
		align-self: center;
	}
</style>

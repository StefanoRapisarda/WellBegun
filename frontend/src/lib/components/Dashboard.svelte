<script lang="ts">
	import { type Tag, type Note, type Log, type Project, type Activity, type Source, type Actor, tagCategoryPrefix } from '$lib/types';
	import { searchEntities, type SearchResult } from '$lib/api/search';
	import { getNote } from '$lib/api/notes';
	import { getLog } from '$lib/api/logs';
	import { getProject } from '$lib/api/projects';
	import { getActivity } from '$lib/api/activities';
	import { getSource } from '$lib/api/sources';
	import { getActor } from '$lib/api/actors';
	import { loadNotes } from '$lib/stores/notes';
	import { loadLogs } from '$lib/stores/logs';
	import { loadProjects } from '$lib/stores/projects';
	import { loadActivities } from '$lib/stores/activities';
	import { loadSources } from '$lib/stores/sources';
	import { loadActors } from '$lib/stores/actors';
	import { tags, loadTags } from '$lib/stores/tags';
	import QuickNoteForm from './forms/QuickNoteForm.svelte';
	import DiaryForm from './forms/DiaryForm.svelte';
	import ProjectForm from './forms/ProjectForm.svelte';
	import ActivityForm from './forms/ActivityForm.svelte';
	import SourceForm from './forms/SourceForm.svelte';
	import ActorForm from './forms/ActorForm.svelte';
	import TagBadge from './shared/TagBadge.svelte';
	import { onMount } from 'svelte';

	const ENTITY_TYPES = [
		{ value: 'note', label: 'Notes' },
		{ value: 'log', label: 'Logs' },
		{ value: 'project', label: 'Projects' },
		{ value: 'activity', label: 'Activities' },
		{ value: 'source', label: 'Sources' },
		{ value: 'actor', label: 'Actors' },
	];

	const TYPE_COLORS: Record<string, string> = {
		note: '#10b981',
		log: '#8b5cf6',
		project: '#3b82f6',
		activity: '#a855f7',
		source: '#f59e0b',
		actor: '#ef4444',
	};

	let queryText = $state('');
	let startDate = $state('');
	let endDate = $state('');
	let selectedTypes = $state<Set<string>>(new Set());
	let selectedTagIds = $state<Set<number>>(new Set());
	let tagFilterMode = $state<'or' | 'and'>('or');
	let showTagFilter = $state(false);
	let results = $state<SearchResult[]>([]);
	let loading = $state(false);
	let editingKey = $state<string | null>(null);
	let editData = $state<any>(null);
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;
	let hasSearched = $state(false);

	// Get wild tags (tags without entity_type) grouped by category
	let wildTags = $derived($tags.filter(t => !t.entity_type));

	// Group tags by category for display
	let tagsByCategory = $derived.by(() => {
		const grouped = new Map<string, Tag[]>();
		for (const tag of wildTags) {
			const category = tag.category || 'uncategorized';
			if (!grouped.has(category)) {
				grouped.set(category, []);
			}
			grouped.get(category)!.push(tag);
		}
		// Sort categories alphabetically and tags within each category
		const sorted = new Map([...grouped.entries()].sort((a, b) => a[0].localeCompare(b[0])));
		for (const [cat, tagList] of sorted) {
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
		debounceTimer = setTimeout(() => doSearch(), 300);
	}

	async function doSearch() {
		loading = true;
		hasSearched = true;
		results = await searchEntities({
			q: queryText || undefined,
			types: selectedTypes.size > 0 ? [...selectedTypes] : undefined,
			start_date: startDate || undefined,
			end_date: endDate || undefined,
			tag_ids: selectedTagIds.size > 0 ? [...selectedTagIds] : undefined,
			tag_mode: selectedTagIds.size > 1 ? tagFilterMode : undefined,
		});
		loading = false;
	}

	function resultKey(r: SearchResult): string {
		return `${r.type}:${r.id}`;
	}

	async function startEdit(result: SearchResult) {
		const key = resultKey(result);
		if (editingKey === key) {
			editingKey = null;
			editData = null;
			return;
		}

		const fetchers: Record<string, (id: number) => Promise<any>> = {
			note: getNote,
			log: getLog,
			project: getProject,
			activity: getActivity,
			source: getSource,
			actor: getActor,
		};

		const fetcher = fetchers[result.type];
		if (fetcher) {
			editData = await fetcher(result.id);
			editingKey = key;
		}
	}

	async function handleEditDone() {
		editingKey = null;
		editData = null;
		// Refresh stores and re-search
		await Promise.all([
			loadNotes(), loadLogs(), loadProjects(),
			loadActivities(), loadSources(), loadActors(),
		]);
		await doSearch();
	}

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString(undefined, {
			year: 'numeric', month: 'short', day: 'numeric'
		});
	}

	onMount(() => {
		doSearch();
	});
</script>

<div class="dashboard">
	<div class="filter-bar">
		<div class="filter-row">
			<input
				type="text"
				class="search-input"
				placeholder="Search across all entities..."
				bind:value={queryText}
				oninput={debouncedSearch}
			/>
			<div class="date-range">
				<input type="date" class="date-input" bind:value={startDate} onchange={debouncedSearch} placeholder="Start" />
				<span class="date-sep">to</span>
				<input type="date" class="date-input" bind:value={endDate} onchange={debouncedSearch} placeholder="End" />
			</div>
		</div>

		<div class="filter-row">
			<div class="type-filters">
				{#each ENTITY_TYPES as et}
					<label class="type-check" style:--type-color={TYPE_COLORS[et.value]}>
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

		<div class="filter-row tag-filter-row">
			<button
				class="tag-filter-toggle"
				class:active={showTagFilter || selectedTagIds.size > 0}
				onclick={() => (showTagFilter = !showTagFilter)}
			>
				<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
				</svg>
				Filter by Tags
				{#if selectedTagIds.size > 0}
					<span class="tag-count">{selectedTagIds.size}</span>
				{/if}
			</button>

			{#if selectedTagIds.size > 0}
				<div class="selected-tags-summary">
					{#each [...selectedTagIds] as tagId}
						{@const tag = $tags.find(t => t.id === tagId)}
						{#if tag}
							<span class="filter-tag">
								<span class="tag-category">{tagCategoryPrefix(tag)}:</span>{tag.name}
								<button class="remove-tag" onclick={() => toggleTag(tagId)}>×</button>
							</span>
						{/if}
					{/each}
					{#if selectedTagIds.size > 1}
						<button class="mode-toggle-inline" onclick={toggleTagMode}>
							<span class:active={tagFilterMode === 'or'}>OR</span>
							<span class="sep">|</span>
							<span class:active={tagFilterMode === 'and'}>AND</span>
						</button>
					{/if}
					<button class="clear-tags-btn" onclick={clearTagFilter}>Clear</button>
				</div>
			{/if}
		</div>

		{#if showTagFilter}
			<div class="tag-filter-panel">
				{#if wildTags.length === 0}
					<p class="no-tags-msg">No tags available. Create tags to filter by them.</p>
				{:else}
					{#each [...tagsByCategory] as [category, categoryTags] (category)}
						<div class="tag-category-group">
							<span class="category-label">{category}</span>
							<div class="category-tags">
								{#each categoryTags as tag (tag.id)}
									<button
										class="tag-chip"
										class:selected={selectedTagIds.has(tag.id)}
										onclick={() => toggleTag(tag.id)}
									>
										{tag.name}
									</button>
								{/each}
							</div>
						</div>
					{/each}
					{#if selectedTagIds.size > 1}
						<div class="mode-toggle-row">
							<span class="mode-label">Combine tags with:</span>
							<button class="mode-toggle" onclick={toggleTagMode}>
								<span class:active={tagFilterMode === 'or'}>OR</span>
								<span class="separator">|</span>
								<span class:active={tagFilterMode === 'and'}>AND</span>
							</button>
						</div>
					{/if}
				{/if}
			</div>
		{/if}
	</div>

	<div class="results">
		{#if loading}
			<p class="status-msg">Searching...</p>
		{:else if results.length === 0 && hasSearched}
			<p class="status-msg">No results found.</p>
		{:else}
			{#each results as result (resultKey(result))}
				<div class="result-item">
					{#if editingKey === resultKey(result) && editData}
						<div class="edit-form" style:border-left-color={TYPE_COLORS[result.type]}>
							<div class="edit-header">
								<span class="type-badge" style:background={TYPE_COLORS[result.type]}>{result.type}</span>
								<button class="cancel-btn" onclick={() => { editingKey = null; editData = null; }}>Cancel</button>
							</div>
							{#if result.type === 'note'}
								<QuickNoteForm editData={editData} onDone={handleEditDone} />
							{:else if result.type === 'log'}
								<DiaryForm editData={editData} onDone={handleEditDone} />
							{:else if result.type === 'project'}
								<ProjectForm editData={editData} onDone={handleEditDone} />
							{:else if result.type === 'activity'}
								<ActivityForm editData={editData} onDone={handleEditDone} />
							{:else if result.type === 'source'}
								<SourceForm editData={editData} onDone={handleEditDone} />
							{:else if result.type === 'actor'}
								<ActorForm editData={editData} onDone={handleEditDone} />
							{/if}
						</div>
					{:else}
						<button class="result-content" onclick={() => startEdit(result)}>
							<div class="result-header">
								<span class="type-badge" style:background={TYPE_COLORS[result.type]}>{result.type}</span>
								<span class="result-title">{result.title}</span>
								<span class="result-date">{formatDate(result.updated_at)}</span>
							</div>
							{#if result.description}
								<p class="result-desc">{result.description.length > 150 ? result.description.slice(0, 150) + '...' : result.description}</p>
							{/if}
							{#if result.tags.length > 0}
								<div class="result-tags">
									{#each result.tags as tag (tag.id)}
										<TagBadge {tag} />
									{/each}
								</div>
							{/if}
						</button>
					{/if}
				</div>
			{/each}
		{/if}
	</div>
</div>

<style>
	.dashboard {
		max-width: 900px;
		margin: 0 auto;
	}
	.filter-bar {
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 10px;
		padding: 16px;
		margin-bottom: 16px;
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.filter-row {
		display: flex;
		gap: 12px;
		align-items: flex-start;
		flex-wrap: wrap;
	}
	.search-input {
		flex: 1;
		min-width: 200px;
		padding: 8px 12px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 0.9rem;
	}
	.date-range {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.date-input {
		padding: 7px 10px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 0.8rem;
		background: white;
	}
	.date-sep {
		font-size: 0.8rem;
		color: #9ca3af;
	}
	.type-filters {
		display: flex;
		gap: 10px;
		flex-wrap: wrap;
		align-items: center;
	}
	.type-check {
		display: flex;
		align-items: center;
		gap: 4px;
		font-size: 0.8rem;
		color: #374151;
		cursor: pointer;
	}
	.type-check input[type="checkbox"] {
		accent-color: var(--type-color);
	}

	/* Tag Filter Styles */
	.tag-filter-row {
		display: flex;
		align-items: center;
		gap: 12px;
		flex-wrap: wrap;
	}
	.tag-filter-toggle {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 6px 12px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		background: white;
		cursor: pointer;
		font-size: 0.8rem;
		color: #6b7280;
		transition: all 0.15s;
	}
	.tag-filter-toggle:hover {
		border-color: #9ca3af;
	}
	.tag-filter-toggle.active {
		border-color: #3b82f6;
		color: #3b82f6;
		background: #eff6ff;
	}
	.tag-count {
		background: #3b82f6;
		color: white;
		font-size: 0.65rem;
		padding: 1px 6px;
		border-radius: 10px;
		font-weight: 600;
	}
	.selected-tags-summary {
		display: flex;
		align-items: center;
		gap: 6px;
		flex-wrap: wrap;
	}
	.filter-tag {
		display: inline-flex;
		align-items: center;
		gap: 2px;
		padding: 3px 8px;
		background: #374151;
		border-radius: 12px;
		font-size: 0.7rem;
		color: white;
	}
	.filter-tag .tag-category {
		opacity: 0.7;
		margin-right: 2px;
	}
	.remove-tag {
		background: none;
		border: none;
		cursor: pointer;
		font-size: 0.85rem;
		color: rgba(255,255,255,0.7);
		padding: 0 2px;
		line-height: 1;
	}
	.remove-tag:hover {
		color: white;
	}
	.mode-toggle-inline {
		padding: 3px 8px;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		background: #f9fafb;
		font-size: 0.65rem;
		cursor: pointer;
		color: #9ca3af;
		font-weight: 500;
	}
	.mode-toggle-inline span.active {
		color: #111827;
		font-weight: 600;
	}
	.mode-toggle-inline .sep {
		margin: 0 3px;
		color: #d1d5db;
	}
	.clear-tags-btn {
		padding: 3px 8px;
		border: 1px solid #fecaca;
		border-radius: 4px;
		background: #fef2f2;
		font-size: 0.7rem;
		cursor: pointer;
		color: #ef4444;
	}
	.clear-tags-btn:hover {
		background: #fee2e2;
	}

	.tag-filter-panel {
		background: #f9fafb;
		border: 1px solid #e5e7eb;
		border-radius: 8px;
		padding: 12px;
		margin-top: 8px;
	}
	.no-tags-msg {
		font-size: 0.8rem;
		color: #9ca3af;
		margin: 0;
		text-align: center;
		padding: 8px;
	}
	.tag-category-group {
		margin-bottom: 10px;
	}
	.tag-category-group:last-child {
		margin-bottom: 0;
	}
	.category-label {
		font-size: 0.7rem;
		font-weight: 600;
		color: #6b7280;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		display: block;
		margin-bottom: 6px;
	}
	.category-tags {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
	}
	.tag-chip {
		padding: 4px 10px;
		border: 1px solid #d1d5db;
		border-radius: 14px;
		background: white;
		font-size: 0.75rem;
		cursor: pointer;
		transition: all 0.15s;
		color: #374151;
	}
	.tag-chip:hover {
		border-color: #9ca3af;
		background: #f3f4f6;
	}
	.tag-chip.selected {
		background: #374151;
		color: white;
		border-color: #374151;
	}
	.mode-toggle-row {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-top: 12px;
		padding-top: 10px;
		border-top: 1px solid #e5e7eb;
	}
	.mode-label {
		font-size: 0.75rem;
		color: #6b7280;
	}
	.mode-toggle {
		padding: 4px 10px;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		background: white;
		font-size: 0.7rem;
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

	.results {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.status-msg {
		text-align: center;
		color: #9ca3af;
		font-size: 0.9rem;
		margin-top: 40px;
	}
	.result-item {
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 8px;
		overflow: hidden;
	}
	.result-content {
		display: block;
		width: 100%;
		text-align: left;
		padding: 12px 16px;
		background: none;
		border: none;
		cursor: pointer;
		transition: background 0.1s;
	}
	.result-content:hover {
		background: #f9fafb;
	}
	.result-header {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.type-badge {
		font-size: 0.7rem;
		padding: 2px 8px;
		border-radius: 4px;
		color: white;
		font-weight: 500;
		text-transform: capitalize;
		white-space: nowrap;
	}
	.result-title {
		flex: 1;
		font-weight: 500;
		font-size: 0.9rem;
		color: #111827;
	}
	.result-date {
		font-size: 0.75rem;
		color: #9ca3af;
		white-space: nowrap;
	}
	.result-desc {
		font-size: 0.8rem;
		color: #6b7280;
		margin: 4px 0 0;
		white-space: pre-wrap;
	}
	.result-tags {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		margin-top: 6px;
	}

	.edit-form {
		padding: 16px;
		border-left: 3px solid;
		background: #fafafa;
	}
	.edit-header {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 10px;
	}
	.cancel-btn {
		font-size: 0.75rem;
		padding: 3px 10px;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		background: white;
		cursor: pointer;
		color: #6b7280;
		margin-left: auto;
	}
	.cancel-btn:hover {
		background: #f3f4f6;
	}
</style>

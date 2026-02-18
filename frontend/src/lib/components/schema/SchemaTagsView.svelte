<script lang="ts">
	import type { Tag } from '$lib/types';
	import { tags, loadTags } from '$lib/stores/tags';
	import { deleteWildTag, updateWildTag, moveCategory, createWildTag, getTagUsageCounts } from '$lib/api/tags';
	import Modal from '../shared/Modal.svelte';
	import ConfirmDialog from '../shared/ConfirmDialog.svelte';
	import WildTagForm from '../forms/WildTagForm.svelte';
	import TagBadge from '../shared/TagBadge.svelte';
	import { onMount } from 'svelte';

	let showCreateForm = $state(false);
	let showNewCategory = $state(false);
	let newCategoryName = $state('');
	let searchQuery = $state('');
	let confirmDelete: number | null = $state(null);
	let confirmDeleteCategory: string | null = $state(null);
	let collapsedSections = $state<Record<string, boolean>>({});
	let viewingTag: Tag | null = $state(null);
	let editDescription = $state('');
	let editCategory = $state('');
	let usageCounts = $state<Record<number, number>>({});

	const SYSTEM_CATEGORIES = ['status', 'activity', 'note', 'log', 'source', 'actor', 'project', 'readinglist', 'plan', 'wild'];

	const CATEGORY_LABELS: Record<string, string> = {
		status: 'Status',
		wild: 'General Custom',
		activity: 'Activity',
		note: 'Note',
		log: 'Log',
		source: 'Source',
		actor: 'Actor',
		project: 'Project',
		readinglist: 'Reading List',
		plan: 'Plan'
	};

	const ENTITY_CATEGORY_ORDER = ['status', 'activity', 'note', 'log', 'source', 'actor', 'project', 'readinglist', 'plan'];
	const CUSTOM_CATEGORY_ORDER = ['wild'];

	const CATEGORY_HINTS: Record<string, string> = {
		status: 'Only one status tag per entity. Applies to any entity type.',
	};

	let standaloneTags = $derived($tags.filter((t) => t.entity_id === null));

	let filteredTags = $derived.by(() => {
		if (!searchQuery.trim()) return standaloneTags;
		const q = searchQuery.trim().toLowerCase();
		return standaloneTags.filter((t) => t.name.toLowerCase().includes(q));
	});

	// Standard entity tag groups (top area)
	let entityTagGroups = $derived.by(() => {
		const groups: { name: string; category: string; tags: Tag[] }[] = [];
		const tagsByCategory = new Map<string, Tag[]>();
		for (const tag of filteredTags) {
			const cat = tag.category;
			if (!tagsByCategory.has(cat)) tagsByCategory.set(cat, []);
			tagsByCategory.get(cat)!.push(tag);
		}
		for (const category of ENTITY_CATEGORY_ORDER) {
			const catTags = tagsByCategory.get(category);
			if (catTags && catTags.length > 0) {
				groups.push({ name: CATEGORY_LABELS[category] || category, category, tags: catTags });
			}
		}
		return groups;
	});

	// Custom tag groups (bottom area): wild + any user-created categories
	let customTagGroups = $derived.by(() => {
		const groups: { name: string; category: string; tags: Tag[] }[] = [];
		const tagsByCategory = new Map<string, Tag[]>();
		for (const tag of filteredTags) {
			const cat = tag.category;
			if (!tagsByCategory.has(cat)) tagsByCategory.set(cat, []);
			tagsByCategory.get(cat)!.push(tag);
		}
		// Wild first
		for (const category of CUSTOM_CATEGORY_ORDER) {
			const catTags = tagsByCategory.get(category);
			if (catTags && catTags.length > 0) {
				groups.push({ name: CATEGORY_LABELS[category] || category, category, tags: catTags });
			}
		}
		// Then user-created categories
		for (const [category, catTags] of tagsByCategory) {
			if (!ENTITY_CATEGORY_ORDER.includes(category) && !CUSTOM_CATEGORY_ORDER.includes(category) && catTags.length > 0) {
				groups.push({ name: CATEGORY_LABELS[category] || category, category, tags: catTags });
			}
		}
		return groups;
	});

	// Combined for collapse/expand all
	let groupedTags = $derived([...entityTagGroups, ...customTagGroups]);

	let allCategories = $derived.by(() => {
		const cats = new Set<string>(SYSTEM_CATEGORIES);
		for (const tag of standaloneTags) cats.add(tag.category);
		return [...cats].sort();
	});

	let allCollapsed = $derived.by(() => {
		if (groupedTags.length === 0) return false;
		return groupedTags.every((g) => collapsedSections[g.category]);
	});

	function toggleSection(name: string) {
		collapsedSections = { ...collapsedSections, [name]: !collapsedSections[name] };
	}

	function toggleAll() {
		const newState: Record<string, boolean> = {};
		const collapse = !allCollapsed;
		for (const group of groupedTags) newState[group.category] = collapse;
		collapsedSections = newState;
	}

	async function refreshUsageCounts() {
		try {
			usageCounts = await getTagUsageCounts();
		} catch (e) {
			console.warn('Failed to load usage counts:', e);
		}
	}

	function getUsageCount(tagId: number): number {
		return usageCounts[tagId] ?? 0;
	}

	let deleteTagUsageCount = $derived(confirmDelete !== null ? getUsageCount(confirmDelete) : 0);
	let deleteTagName = $derived.by(() => {
		if (confirmDelete === null) return '';
		return standaloneTags.find((t) => t.id === confirmDelete)?.name ?? 'this tag';
	});

	async function handleDeleteTag(id: number) {
		await deleteWildTag(id);
		await loadTags();
		await refreshUsageCounts();
		confirmDelete = null;
	}

	async function handleMoveTag(tagId: number, newCategory: string) {
		await updateWildTag(tagId, { category: newCategory });
		await loadTags();
	}

	async function handleDeleteCategory() {
		if (!confirmDeleteCategory) return;
		await moveCategory(confirmDeleteCategory, 'wild');
		await loadTags();
		confirmDeleteCategory = null;
	}

	function isCustomCategory(category: string): boolean {
		return !SYSTEM_CATEGORIES.includes(category);
	}

	let editColor = $state('');

	function openTagDetail(tag: Tag) {
		viewingTag = tag;
		editDescription = tag.description ?? '';
		editCategory = tag.category;
		editColor = tag.color ?? '';
	}

	async function handleCreateCategory() {
		const name = newCategoryName.trim().toLowerCase();
		if (!name) return;
		if (allCategories.includes(name)) {
			showNewCategory = false;
			newCategoryName = '';
			return;
		}
		await createWildTag(name, undefined, name);
		await loadTags();
		showNewCategory = false;
		newCategoryName = '';
	}

	async function saveTagEdit() {
		if (!viewingTag) return;
		const updates: { description?: string | null; category?: string; color?: string | null } = {};
		const newDesc = editDescription.trim() || null;
		if (newDesc !== (viewingTag.description ?? null)) updates.description = newDesc;
		if (editCategory !== viewingTag.category) updates.category = editCategory;
		const newColor = editColor || null;
		if (newColor !== (viewingTag.color ?? null)) updates.color = newColor;
		if (Object.keys(updates).length > 0) {
			await updateWildTag(viewingTag.id, updates);
			await loadTags();
		}
		viewingTag = null;
	}

	async function handleFormDone() {
		showCreateForm = false;
		await refreshUsageCounts();
	}

	onMount(() => {
		refreshUsageCounts();
	});
</script>

<div class="schema-tags">
	<div class="toolbar">
		<button class="toolbar-btn primary" onclick={() => (showCreateForm = !showCreateForm)}>
			+ Create Tag
		</button>
		<button class="toolbar-btn" onclick={() => (showNewCategory = !showNewCategory)}>
			+ Category
		</button>
		<div class="search-box">
			<input
				type="text"
				placeholder="Search tags..."
				bind:value={searchQuery}
				class="search-input"
			/>
			{#if searchQuery}
				<button class="search-clear" onclick={() => (searchQuery = '')}>x</button>
			{/if}
		</div>
		{#if groupedTags.length > 0}
			<button class="toolbar-btn" onclick={toggleAll}>
				{allCollapsed ? 'Expand All' : 'Collapse All'}
			</button>
		{/if}
	</div>

	{#if showCreateForm}
		<div class="inline-form">
			<WildTagForm onDone={handleFormDone} />
		</div>
	{/if}

	{#if showNewCategory}
		<form class="new-category-form" onsubmit={(e) => { e.preventDefault(); handleCreateCategory(); }}>
			<input
				type="text"
				bind:value={newCategoryName}
				placeholder="Category name..."
				class="new-category-input"
				autofocus
			/>
			<button type="submit" class="btn-sm btn-primary">Create</button>
			<button type="button" class="btn-sm" onclick={() => { showNewCategory = false; newCategoryName = ''; }}>Cancel</button>
		</form>
	{/if}

	<!-- ═══ TOP AREA: Custom Tags ═══ -->
	<div class="area">
		<div class="area-header">
			<span class="area-title">Custom Tags</span>
			<span class="area-count">{customTagGroups.reduce((n, g) => n + g.tags.length, 0)}</span>
		</div>

		{#each customTagGroups as group (group.category)}
			<div class="category-section">
				<div class="category-header-row">
					<button class="category-header" onclick={() => toggleSection(group.category)}>
						<span class="chevron" class:collapsed={collapsedSections[group.category]}>&#9660;</span>
						<span class="category-name">{group.name}</span>
						<span class="tag-count">({group.tags.length})</span>
					</button>
					{#if isCustomCategory(group.category)}
						<button
							class="btn-delete-cat"
							onclick={() => (confirmDeleteCategory = group.category)}
							title="Delete category (tags move to General)"
						>x</button>
					{/if}
				</div>

				{#if !collapsedSections[group.category]}
					<div class="tag-grid">
						{#each group.tags as tag (tag.id)}
							<div class="tag-item">
								<button class="tag-clickable" onclick={() => openTagDetail(tag)}>
									<TagBadge {tag} />
								</button>
								<span class="usage-count" title="{getUsageCount(tag.id)} entities use this tag">
									({getUsageCount(tag.id)}x)
								</span>
								<div class="tag-actions">
									{#if !tag.is_system}
										<select
											class="select-category"
											value={tag.category}
											onchange={(e) => handleMoveTag(tag.id, (e.target as HTMLSelectElement).value)}
										>
											{#each allCategories as cat}
												<option value={cat}>{CATEGORY_LABELS[cat] || cat}</option>
											{/each}
										</select>
										<button class="btn-delete" onclick={() => (confirmDelete = tag.id)}>Delete</button>
									{:else}
										<span class="system-badge">default</span>
									{/if}
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/each}

		{#if customTagGroups.length === 0 && !searchQuery.trim()}
			<p class="empty-section">No custom tags yet. Click "+ Create Tag" to add one.</p>
		{:else if customTagGroups.length === 0 && searchQuery.trim()}
			<p class="empty-section">No custom tags match your search.</p>
		{/if}
	</div>

	<!-- ═══ DIVIDER ═══ -->
	<div class="area-divider"></div>

	<!-- ═══ BOTTOM AREA: Standard Entity Tags ═══ -->
	<div class="area">
		<div class="area-header">
			<span class="area-title">Entity Tags</span>
			<span class="system-area-badge">standard</span>
		</div>

		{#each entityTagGroups as group (group.category)}
			<div class="category-section">
				<div class="category-header-row">
					<button class="category-header" onclick={() => toggleSection(group.category)}>
						<span class="chevron" class:collapsed={collapsedSections[group.category]}>&#9660;</span>
						<span class="category-name">{group.name}</span>
						<span class="tag-count">({group.tags.length})</span>
					</button>
				</div>

				{#if !collapsedSections[group.category]}
					{#if CATEGORY_HINTS[group.category]}
						<p class="category-hint">{CATEGORY_HINTS[group.category]}</p>
					{/if}
					<div class="tag-grid">
						{#each group.tags as tag (tag.id)}
							<div class="tag-item">
								<button class="tag-clickable" onclick={() => openTagDetail(tag)}>
									<TagBadge {tag} />
								</button>
								<span class="usage-count" title="{getUsageCount(tag.id)} entities use this tag">
									({getUsageCount(tag.id)}x)
								</span>
								{#if tag.is_system}
									<span class="system-badge">default</span>
								{/if}
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/each}

		{#if entityTagGroups.length === 0 && searchQuery.trim()}
			<p class="empty-section">No entity tags match your search.</p>
		{/if}
	</div>

	{#if filteredTags.length === 0 && searchQuery.trim()}
		<p class="empty">No tags match "{searchQuery}".</p>
	{:else if standaloneTags.length === 0}
		<p class="empty">No tags yet. Create tags to see them here.</p>
	{/if}
</div>

<ConfirmDialog
	open={confirmDelete !== null}
	message={deleteTagUsageCount > 0
		? `Delete "${deleteTagName}"? This tag is used by ${deleteTagUsageCount} entit${deleteTagUsageCount === 1 ? 'y' : 'ies'}. It will be permanently removed.`
		: `Delete "${deleteTagName}"? It will be permanently removed.`}
	onConfirm={() => confirmDelete !== null && handleDeleteTag(confirmDelete)}
	onCancel={() => (confirmDelete = null)}
/>

<ConfirmDialog
	open={confirmDeleteCategory !== null}
	message={`Delete category "${confirmDeleteCategory}"? Tags will be moved to General Custom.`}
	onConfirm={handleDeleteCategory}
	onCancel={() => (confirmDeleteCategory = null)}
/>

<Modal open={viewingTag !== null} title={viewingTag?.name ?? 'Tag Detail'} onClose={() => (viewingTag = null)}>
	{#if viewingTag}
		<div class="tag-detail">
			<div class="tag-detail-row">
				<TagBadge tag={viewingTag} />
				{#if viewingTag.is_system}
					<span class="system-badge">default</span>
				{/if}
				<span class="usage-badge">{getUsageCount(viewingTag.id)} uses</span>
			</div>
			<label class="tag-detail-label">
				Description
				<textarea
					bind:value={editDescription}
					rows="3"
					placeholder="Add a description for this tag..."
					class="tag-detail-textarea"
				></textarea>
			</label>
			<label class="tag-detail-label">
				Category
				<select bind:value={editCategory} class="tag-detail-select">
					{#each allCategories as cat}
						<option value={cat}>{CATEGORY_LABELS[cat] || cat}</option>
					{/each}
				</select>
			</label>
			<div class="tag-detail-label">
				Color
				<div class="color-row">
					<input type="color" bind:value={editColor} class="color-picker" />
					{#if editColor}
						<span class="color-preview" style="background: {editColor}"></span>
						<button type="button" class="btn-clear-color" onclick={() => (editColor = '')}>Clear</button>
					{:else}
						<span class="color-hint">Default (based on category)</span>
					{/if}
				</div>
			</div>
			<div class="tag-detail-actions">
				<button class="btn-sm" onclick={() => (viewingTag = null)}>Cancel</button>
				<button class="btn-sm btn-primary" onclick={saveTagEdit}>Save</button>
			</div>
		</div>
	{/if}
</Modal>

<style>
	.schema-tags {
		max-width: 900px;
		margin: 0 auto;
	}
	.toolbar {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 16px;
		flex-wrap: wrap;
	}
	.toolbar-btn {
		padding: 6px 14px;
		font-size: 0.8rem;
		color: #6b7280;
		background: white;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		cursor: pointer;
		white-space: nowrap;
	}
	.toolbar-btn:hover {
		background: #f3f4f6;
		color: #374151;
	}
	.toolbar-btn.primary {
		background: #1f2937;
		color: white;
		border-color: #1f2937;
	}
	.toolbar-btn.primary:hover {
		background: #374151;
	}
	.search-box {
		display: flex;
		align-items: center;
		flex: 1;
		min-width: 160px;
		max-width: 300px;
		position: relative;
	}
	.search-input {
		width: 100%;
		padding: 6px 28px 6px 10px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 0.8rem;
		outline: none;
	}
	.search-input:focus {
		border-color: #9ca3af;
	}
	.search-clear {
		position: absolute;
		right: 6px;
		background: none;
		border: none;
		cursor: pointer;
		font-size: 0.75rem;
		color: #9ca3af;
		padding: 2px 4px;
	}
	.search-clear:hover {
		color: #374151;
	}

	.inline-form {
		padding: 16px;
		background: #f9fafb;
		border: 1px solid #e5e7eb;
		border-radius: 8px;
		margin-bottom: 16px;
	}

	.new-category-form {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 16px;
	}
	.new-category-input {
		flex: 1;
		max-width: 240px;
		padding: 6px 10px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 0.8rem;
	}

	.btn-sm {
		padding: 6px 12px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 0.8rem;
		cursor: pointer;
		background: white;
	}
	.btn-primary {
		background: #6b7280;
		color: white;
		border-color: #6b7280;
	}

	/* ── Areas ── */
	.area {
		padding: 12px 0;
	}
	.area-header {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 12px;
	}
	.area-title {
		font-size: 0.82rem;
		font-weight: 700;
		color: #374151;
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}
	.system-area-badge {
		font-size: 0.6rem;
		font-weight: 600;
		color: #9ca3af;
		background: #f3f4f6;
		border: 1px solid #e5e7eb;
		border-radius: 3px;
		padding: 1px 6px;
		text-transform: uppercase;
		letter-spacing: 0.3px;
	}
	.area-count {
		font-size: 0.7rem;
		color: #9ca3af;
		background: #f3f4f6;
		border-radius: 10px;
		padding: 1px 8px;
	}
	.area-divider {
		border-top: 1px solid #e5e7eb;
		margin: 4px 0;
	}
	.empty-section {
		color: #9ca3af;
		font-size: 0.82rem;
		padding: 12px 0;
	}

	.category-section {
		margin-bottom: 8px;
	}
	.category-header-row {
		display: flex;
		align-items: center;
		gap: 4px;
	}
	.category-header {
		display: flex;
		align-items: center;
		gap: 8px;
		flex: 1;
		padding: 8px 12px;
		background: #f9fafb;
		border: 1px solid #e5e7eb;
		border-radius: 6px;
		cursor: pointer;
		font-size: 0.9rem;
		font-weight: 600;
		color: #374151;
		text-align: left;
	}
	.category-header:hover {
		background: #f3f4f6;
	}
	.chevron {
		font-size: 0.65rem;
		transition: transform 0.15s;
		display: inline-block;
	}
	.chevron.collapsed {
		transform: rotate(-90deg);
	}
	.category-name {
		flex: 1;
	}
	.tag-count {
		font-weight: 400;
		color: #9ca3af;
		font-size: 0.8rem;
	}
	.btn-delete-cat {
		padding: 4px 8px;
		background: transparent;
		border: 1px solid #e5e7eb;
		border-radius: 6px;
		cursor: pointer;
		font-size: 0.8rem;
		color: #9ca3af;
	}
	.btn-delete-cat:hover {
		background: #fee2e2;
		color: #ef4444;
		border-color: #fecaca;
	}

	.category-hint {
		font-size: 0.72rem;
		color: #9ca3af;
		font-style: italic;
		margin: 0 0 4px 20px;
	}

	.tag-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 6px;
		padding: 8px 0 8px 20px;
	}
	@media (max-width: 700px) {
		.tag-grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}
	.tag-item {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 4px 6px;
		border: 1px solid #f3f4f6;
		border-radius: 5px;
		min-height: 28px;
		transition: background 0.1s;
	}
	.tag-item:hover {
		background: #f9fafb;
		border-color: #e5e7eb;
	}
	.tag-clickable {
		background: none;
		border: none;
		padding: 0;
		cursor: pointer;
	}
	.tag-clickable:hover {
		opacity: 0.8;
	}
	.usage-count {
		font-size: 0.7rem;
		color: #9ca3af;
		flex-shrink: 0;
	}
	.tag-actions {
		display: flex;
		align-items: center;
		gap: 6px;
		margin-left: auto;
	}
	.select-category {
		font-size: 0.75rem;
		padding: 3px 6px;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		background: white;
		color: #6b7280;
		max-width: 100px;
	}
	.btn-delete {
		font-size: 0.75rem;
		padding: 3px 8px;
		background: #fee2e2;
		color: #ef4444;
		border: 1px solid #fecaca;
		border-radius: 4px;
		cursor: pointer;
	}
	.btn-delete:hover {
		background: #fca5a5;
		color: #dc2626;
	}
	.system-badge {
		font-size: 0.65rem;
		padding: 2px 8px;
		background: #e5e7eb;
		color: #6b7280;
		border-radius: 4px;
	}
	.empty {
		text-align: center;
		color: #9ca3af;
		font-size: 0.9rem;
		padding: 32px 0;
	}

	.tag-detail {
		display: flex;
		flex-direction: column;
		gap: 14px;
	}
	.tag-detail-row {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.usage-badge {
		font-size: 0.7rem;
		padding: 2px 8px;
		background: #f0f9ff;
		color: #3b82f6;
		border: 1px solid #bfdbfe;
		border-radius: 4px;
	}
	.tag-detail-label {
		display: flex;
		flex-direction: column;
		gap: 4px;
		font-size: 0.875rem;
		font-weight: 500;
		color: #374151;
	}
	.tag-detail-textarea {
		padding: 8px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 0.875rem;
		font-family: inherit;
		resize: vertical;
	}
	.tag-detail-select {
		padding: 8px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 0.875rem;
	}
	.tag-detail-actions {
		display: flex;
		gap: 8px;
		justify-content: flex-end;
	}

	.color-row {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.color-picker {
		width: 36px;
		height: 30px;
		padding: 1px;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		cursor: pointer;
		background: none;
	}
	.color-preview {
		width: 20px;
		height: 20px;
		border-radius: 4px;
		flex-shrink: 0;
	}
	.color-hint {
		font-size: 0.75rem;
		color: #9ca3af;
		font-weight: 400;
	}
	.btn-clear-color {
		font-size: 0.75rem;
		padding: 2px 8px;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		background: white;
		cursor: pointer;
		color: #6b7280;
	}
	.btn-clear-color:hover {
		background: #f3f4f6;
	}
</style>

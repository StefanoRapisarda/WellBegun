<script lang="ts">
	import type { Tag } from '$lib/types';
	import { tags, loadTags } from '$lib/stores/tags';
	import { deleteWildTag, updateWildTag, moveCategory, createWildTag } from '$lib/api/tags';
	import PanelContainer from '../shared/PanelContainer.svelte';
	import Modal from '../shared/Modal.svelte';
	import ConfirmDialog from '../shared/ConfirmDialog.svelte';
	import WildTagForm from '../forms/WildTagForm.svelte';
	import TagBadge from '../shared/TagBadge.svelte';

	let showForm = $state(false);
	let showNewCategory = $state(false);
	let newCategoryName = $state('');
	let confirmDelete: number | null = $state(null);
	let confirmDeleteCategory: string | null = $state(null);
	let collapsedSections = $state<Record<string, boolean>>({});
	let viewingTag: Tag | null = $state(null);
	let editDescription = $state('');

	// System categories that cannot be deleted
	const SYSTEM_CATEGORIES = ['activity', 'note', 'log', 'source', 'actor', 'project', 'readinglist', 'learningtrack', 'wild'];

	// Get all tags that are "wild" (entity_id is null) - these are the default/standalone tags
	let standaloneTags = $derived($tags.filter((t) => t.entity_id === null));

	// Category display names for better readability
	const CATEGORY_LABELS: Record<string, string> = {
		'wild': 'General Custom',
		'activity': 'Activity',
		'note': 'Note',
		'log': 'Log',
		'source': 'Source',
		'actor': 'Actor',
		'project': 'Project',
		'readinglist': 'Reading List',
		'learningtrack': 'Learning Track',
	};

	// Order for categories
	const CATEGORY_ORDER = ['activity', 'note', 'log', 'source', 'actor', 'project', 'readinglist', 'learningtrack', 'wild'];

	// Derive grouped tags by their actual category
	let groupedTags = $derived.by(() => {
		const groups: { name: string; category: string; tags: typeof standaloneTags; isDefault: boolean }[] = [];

		// Group tags by their category
		const tagsByCategory = new Map<string, typeof standaloneTags>();
		for (const tag of standaloneTags) {
			const cat = tag.category;
			if (!tagsByCategory.has(cat)) {
				tagsByCategory.set(cat, []);
			}
			tagsByCategory.get(cat)!.push(tag);
		}

		// Create groups in the defined order
		for (const category of CATEGORY_ORDER) {
			const tags = tagsByCategory.get(category);
			if (tags && tags.length > 0) {
				groups.push({
					name: CATEGORY_LABELS[category] || category,
					category,
					tags,
					isDefault: false
				});
			}
		}

		// Add any other categories not in the predefined order
		for (const [category, tags] of tagsByCategory) {
			if (!CATEGORY_ORDER.includes(category) && tags.length > 0) {
				groups.push({
					name: CATEGORY_LABELS[category] || category,
					category,
					tags,
					isDefault: false
				});
			}
		}

		return groups;
	});

	// Get all unique categories for the move dropdown
	let allCategories = $derived.by(() => {
		const cats = new Set<string>(SYSTEM_CATEGORIES);
		for (const tag of standaloneTags) {
			cats.add(tag.category);
		}
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
		for (const group of groupedTags) {
			newState[group.category] = collapse;
		}
		collapsedSections = newState;
	}

	async function handleDeleteTag(id: number) {
		await deleteWildTag(id);
		await loadTags();
		confirmDelete = null;
	}

	async function handleMoveTag(tagId: number, newCategory: string) {
		await updateWildTag(tagId, { category: newCategory });
		await loadTags();
	}

	async function handleDeleteCategory() {
		if (!confirmDeleteCategory) return;
		// Move all tags from this category to "wild"
		await moveCategory(confirmDeleteCategory, 'wild');
		await loadTags();
		confirmDeleteCategory = null;
	}

	function isCustomCategory(category: string): boolean {
		return !SYSTEM_CATEGORIES.includes(category);
	}

	function openTagDetail(tag: Tag) {
		viewingTag = tag;
		editDescription = tag.description ?? '';
	}

	async function handleCreateCategory() {
		const name = newCategoryName.trim().toLowerCase();
		if (!name) return;
		if (allCategories.includes(name)) {
			// Category already exists, just close the form
			showNewCategory = false;
			newCategoryName = '';
			return;
		}
		// Create a starter tag in the new category
		await createWildTag(name, undefined, name);
		await loadTags();
		showNewCategory = false;
		newCategoryName = '';
	}

	async function saveDescription() {
		if (!viewingTag) return;
		await updateWildTag(viewingTag.id, { description: editDescription.trim() || null });
		await loadTags();
		viewingTag = null;
	}
</script>

<PanelContainer title="Tags" panelId="wildtag" color="#8b8b7a" onAdd={() => (showForm = !showForm)}>
	{#if showForm}
		<div class="inline-form">
			<WildTagForm onDone={() => (showForm = false)} />
		</div>
	{/if}

	<div class="toolbar-row">
		<button class="toolbar-btn" onclick={() => (showNewCategory = !showNewCategory)}>
			+ Category
		</button>
		{#if groupedTags.length > 0}
			<button class="toolbar-btn" onclick={toggleAll}>
				{allCollapsed ? 'Expand All' : 'Collapse All'}
			</button>
		{/if}
	</div>

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

	{#each groupedTags as group (group.category)}
		<div class="category-section">
			<div class="category-header-row">
				<button class="category-header" onclick={() => toggleSection(group.category)}>
					<span class="chevron" class:collapsed={collapsedSections[group.category]}>▼</span>
					<span class="category-name">{group.name}</span>
					<span class="tag-count">({group.tags.length})</span>
				</button>
				{#if isCustomCategory(group.category)}
					<button
						class="btn-delete-cat"
						onclick={() => (confirmDeleteCategory = group.category)}
						title="Delete category (tags move to General)"
					>×</button>
				{/if}
			</div>

			{#if !collapsedSections[group.category]}
				<div class="tag-list">
					{#each group.tags as tag (tag.id)}
						<div class="tag-item">
							<button class="tag-clickable" onclick={() => openTagDetail(tag)}><TagBadge {tag} /></button>
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

	{#if standaloneTags.length === 0}
		<p class="empty">No tags yet. Add tags to see them here.</p>
	{/if}
</PanelContainer>

<ConfirmDialog
	open={confirmDelete !== null}
	message="Delete this tag? It will be permanently removed from all entities where it is used."
	onConfirm={() => confirmDelete && handleDeleteTag(confirmDelete)}
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
			<div class="tag-detail-name">
				<TagBadge tag={viewingTag} />
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
			<div class="tag-detail-actions">
				<button class="btn-sm" onclick={() => (viewingTag = null)}>Cancel</button>
				<button class="btn-sm btn-primary" onclick={saveDescription}>Save</button>
			</div>
		</div>
	{/if}
</Modal>

<style>
	.inline-form { padding: 10px; background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 8px; margin-bottom: 12px; }
	.btn-sm { padding: 4px 8px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.8rem; cursor: pointer; background: white; }
	.btn-primary { background: #6b7280; color: white; border-color: #6b7280; }

	.toolbar-row { display: flex; justify-content: flex-end; gap: 6px; margin-bottom: 6px; }
	.toolbar-btn { padding: 2px 8px; font-size: 0.7rem; color: #6b7280; background: transparent; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; }
	.toolbar-btn:hover { background: #f3f4f6; color: #374151; }
	.new-category-form { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
	.new-category-input { flex: 1; padding: 4px 8px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.8rem; }

	.category-section { margin-bottom: 8px; }
	.category-header-row { display: flex; align-items: center; gap: 4px; }
	.category-header { display: flex; align-items: center; gap: 6px; flex: 1; padding: 6px 8px; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 4px; cursor: pointer; font-size: 0.85rem; font-weight: 600; color: #374151; text-align: left; }
	.category-header:hover { background: #f3f4f6; }
	.chevron { font-size: 0.7rem; transition: transform 0.15s; display: inline-block; }
	.chevron.collapsed { transform: rotate(-90deg); }
	.category-name { flex: 1; }
	.tag-count { font-weight: 400; color: #9ca3af; font-size: 0.75rem; }
	.btn-delete-cat { padding: 2px 6px; background: transparent; border: 1px solid #e5e7eb; border-radius: 4px; cursor: pointer; font-size: 0.8rem; color: #9ca3af; }
	.btn-delete-cat:hover { background: #fee2e2; color: #ef4444; border-color: #fecaca; }

	.tag-list { display: flex; flex-direction: column; gap: 4px; padding: 6px 0 6px 16px; }
	.tag-item { display: flex; align-items: center; justify-content: space-between; padding: 2px 0; gap: 8px; }
	.tag-actions { display: flex; align-items: center; gap: 4px; }
	.select-category { font-size: 0.7rem; padding: 2px 4px; border: 1px solid #d1d5db; border-radius: 3px; background: white; color: #6b7280; max-width: 80px; }
	.btn-delete { font-size: 0.7rem; padding: 2px 6px; background: #fee2e2; color: #ef4444; border: 1px solid #fecaca; border-radius: 4px; cursor: pointer; }
	.system-badge { font-size: 0.65rem; padding: 2px 6px; background: #e5e7eb; color: #6b7280; border-radius: 4px; }
	.empty { text-align: center; color: #9ca3af; font-size: 0.875rem; padding: 20px 0; }
	.tag-clickable { background: none; border: none; padding: 0; cursor: pointer; }
	.tag-clickable:hover { opacity: 0.8; }
	.tag-detail { display: flex; flex-direction: column; gap: 12px; }
	.tag-detail-name { margin-bottom: 4px; }
	.tag-detail-label { display: flex; flex-direction: column; gap: 4px; font-size: 0.875rem; font-weight: 500; color: #374151; }
	.tag-detail-textarea { padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.875rem; font-family: inherit; resize: vertical; }
	.tag-detail-actions { display: flex; gap: 8px; justify-content: flex-end; }
</style>

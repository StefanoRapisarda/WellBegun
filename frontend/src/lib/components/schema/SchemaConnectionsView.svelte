<script lang="ts">
	import type { CustomPredicate } from '$lib/types';
	import { structuralPredicates, semanticRelations, customPredicates, loadPredicates, reloadPredicates } from '$lib/stores/predicates';
	import { createCustomPredicate, updateCustomPredicate, deleteCustomPredicate } from '$lib/api/knowledge';
	import ConfirmDialog from '../shared/ConfirmDialog.svelte';
	import { onMount } from 'svelte';

	// ── Search ──────────────────────────────────────────────────────────────
	let searchText = $state('');

	// ── Create form ─────────────────────────────────────────────────────────
	let showCreateForm = $state(false);
	let createForward = $state('');
	let createReverse = $state('');
	let createCategory = $state('Custom');

	// ── Edit state ──────────────────────────────────────────────────────────
	let editingId: number | null = $state(null);
	let editForward = $state('');
	let editReverse = $state('');
	let editCategory = $state('');

	// ── Delete state ────────────────────────────────────────────────────────
	let confirmDeleteId: number | null = $state(null);

	// ── Collapse state ──────────────────────────────────────────────────────
	let structuralCollapsed = $state(false);

	// ── Search filter ───────────────────────────────────────────────────────
	function matchesSearch(text: string): boolean {
		if (!searchText.trim()) return true;
		return text.toLowerCase().includes(searchText.trim().toLowerCase());
	}

	// ── Structural predicates ───────────────────────────────────────────────
	let structuralEntries = $derived.by(() => {
		const entries = Object.entries($structuralPredicates);
		if (!searchText.trim()) return entries;
		const q = searchText.trim().toLowerCase();
		return entries.filter(([key, value]) =>
			key.toLowerCase().includes(q) || value.toLowerCase().includes(q)
		);
	});

	// ── Semantic relations (filtered, flat list with category) ──────────────
	let filteredSemanticFlat = $derived.by(() => {
		const items: { key: string; forward: string; reverse: string; category: string }[] = [];
		for (const [category, predicates] of Object.entries($semanticRelations)) {
			for (const p of predicates) {
				if (matchesSearch(p.forward) || matchesSearch(p.reverse) || matchesSearch(category)) {
					items.push({ ...p, category });
				}
			}
		}
		return items;
	});

	// ── Custom predicates (filtered) ────────────────────────────────────────
	let filteredCustomFlat = $derived.by(() => {
		const q = searchText.trim().toLowerCase();
		let items = $customPredicates;
		if (q) {
			items = items.filter(cp =>
				cp.forward.toLowerCase().includes(q) ||
				(cp.reverse?.toLowerCase().includes(q) ?? false) ||
				cp.category.toLowerCase().includes(q)
			);
		}
		return items;
	});

	// Group custom predicates by category for display
	let customByCategory = $derived.by(() => {
		const groups: Record<string, CustomPredicate[]> = {};
		for (const cp of filteredCustomFlat) {
			const cat = cp.category || 'Custom';
			if (!groups[cat]) groups[cat] = [];
			groups[cat].push(cp);
		}
		return groups;
	});

	// ── Handlers ────────────────────────────────────────────────────────────
	async function handleCreate() {
		if (!createForward.trim()) return;
		await createCustomPredicate({
			forward: createForward.trim(),
			reverse: createReverse.trim() || null,
			category: createCategory.trim() || 'Custom'
		});
		await reloadPredicates();
		createForward = '';
		createReverse = '';
		createCategory = 'Custom';
		showCreateForm = false;
	}

	function startEdit(cp: CustomPredicate) {
		editingId = cp.id;
		editForward = cp.forward;
		editReverse = cp.reverse ?? '';
		editCategory = cp.category;
	}

	async function saveEdit() {
		if (editingId === null || !editForward.trim()) return;
		await updateCustomPredicate(editingId, {
			forward: editForward.trim(),
			reverse: editReverse.trim() || null,
			category: editCategory.trim() || 'Custom'
		});
		await reloadPredicates();
		editingId = null;
	}

	function cancelEdit() {
		editingId = null;
	}

	async function handleDelete(id: number) {
		await deleteCustomPredicate(id);
		await reloadPredicates();
		confirmDeleteId = null;
	}

	function handleCreateKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') handleCreate();
		else if (e.key === 'Escape') { showCreateForm = false; }
	}

	function handleEditKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') saveEdit();
		else if (e.key === 'Escape') cancelEdit();
	}

	onMount(() => { loadPredicates(); });
</script>

<div class="schema-connections">
	<div class="toolbar">
		<button class="toolbar-btn primary" onclick={() => (showCreateForm = !showCreateForm)}>
			+ New Predicate
		</button>
		<div class="search-box">
			<input type="text" placeholder="Search predicates..." bind:value={searchText} class="search-input" />
			{#if searchText}
				<button class="search-clear" onclick={() => (searchText = '')}>x</button>
			{/if}
		</div>
	</div>

	{#if showCreateForm}
		<div class="create-form">
			<div class="create-fields">
				<label class="field">
					<span class="field-label">Forward label</span>
					<input
						type="text"
						bind:value={createForward}
						placeholder="e.g. derived from"
						class="field-input"
						onkeydown={handleCreateKeydown}
						autofocus
					/>
				</label>
				<label class="field">
					<span class="field-label">Reverse label <span class="optional">(optional)</span></span>
					<input
						type="text"
						bind:value={createReverse}
						placeholder="e.g. has derivative"
						class="field-input"
						onkeydown={handleCreateKeydown}
					/>
				</label>
				<label class="field">
					<span class="field-label">Category</span>
					<input
						type="text"
						bind:value={createCategory}
						placeholder="Custom"
						class="field-input"
						onkeydown={handleCreateKeydown}
					/>
				</label>
			</div>
			<div class="create-actions">
				<button class="btn-sm" onclick={() => (showCreateForm = false)}>Cancel</button>
				<button
					class="btn-sm btn-primary"
					disabled={!createForward.trim()}
					onclick={handleCreate}
				>Create</button>
			</div>
		</div>
	{/if}

	<!-- ═══ TOP AREA: Custom predicates ═══ -->
	<div class="area">
		<div class="area-header">
			<span class="area-title">Custom Predicates</span>
			<span class="area-count">{$customPredicates.length}</span>
		</div>

		{#if Object.keys(customByCategory).length > 0}
			{#each Object.entries(customByCategory) as [category, predicates] (category)}
				<div class="tag-group">
					<span class="tag-group-label">{category}</span>
					<div class="tag-grid">
						{#each predicates as cp (cp.id)}
							{#if editingId === cp.id}
								<div class="tag-chip editing-chip">
									<input
										type="text"
										class="edit-input"
										bind:value={editForward}
										placeholder="Forward"
										onkeydown={handleEditKeydown}
										autofocus
									/>
									<input
										type="text"
										class="edit-input"
										bind:value={editReverse}
										placeholder="Reverse"
										onkeydown={handleEditKeydown}
									/>
									<input
										type="text"
										class="edit-input edit-input-sm"
										bind:value={editCategory}
										placeholder="Category"
										onkeydown={handleEditKeydown}
									/>
									<button class="chip-action" onclick={saveEdit} title="Save">&#10003;</button>
									<button class="chip-action" onclick={cancelEdit} title="Cancel">&#10005;</button>
								</div>
							{:else}
								<div class="tag-chip custom-chip" title={cp.reverse ? `${cp.forward} ↔ ${cp.reverse}` : cp.forward}>
									<span class="tag-forward">{cp.forward}</span>
									{#if cp.reverse}
										<span class="tag-reverse">↔ {cp.reverse}</span>
									{/if}
									<div class="chip-actions">
										<button class="chip-action" onclick={() => startEdit(cp)} title="Edit">&#9998;</button>
										<button class="chip-action chip-action-danger" onclick={() => (confirmDeleteId = cp.id)} title="Delete">&times;</button>
									</div>
								</div>
							{/if}
						{/each}
					</div>
				</div>
			{/each}
		{:else if $customPredicates.length === 0 && !searchText.trim()}
			<p class="empty">No custom predicates yet. Click "+ New Predicate" to create one.</p>
		{:else if searchText.trim()}
			<p class="empty">No custom predicates match your search.</p>
		{/if}
	</div>

	<!-- ═══ DIVIDER ═══ -->
	<div class="area-divider"></div>

	<!-- ═══ BOTTOM AREA: Built-in / System predicates ═══ -->
	<div class="area">
		<div class="area-header">
			<span class="area-title">Built-in Predicates</span>
			<span class="system-badge">system</span>
		</div>

		<!-- Semantic relations as tags in columns, grouped by category -->
		{#each Object.entries($semanticRelations) as [category, predicates] (category)}
			{@const filtered = predicates.filter(p => matchesSearch(p.forward) || matchesSearch(p.reverse) || matchesSearch(category))}
			{#if filtered.length > 0}
				<div class="tag-group">
					<span class="tag-group-label">{category}</span>
					<div class="tag-grid">
						{#each filtered as pred (pred.key)}
							<div class="tag-chip system-chip" title={pred.reverse && pred.reverse !== pred.forward ? `${pred.forward} ↔ ${pred.reverse}` : pred.forward}>
								<span class="tag-forward">{pred.forward}</span>
								{#if pred.reverse && pred.reverse !== pred.forward}
									<span class="tag-reverse">↔ {pred.reverse}</span>
								{/if}
							</div>
						{/each}
					</div>
				</div>
			{/if}
		{/each}

		<!-- Structural defaults: collapsible reference -->
		<div class="structural-section">
			<button class="structural-toggle" onclick={() => (structuralCollapsed = !structuralCollapsed)}>
				<span class="collapse-icon">{structuralCollapsed ? '▸' : '▾'}</span>
				<span>Structural Defaults</span>
				<span class="section-count">({structuralEntries.length})</span>
			</button>
			{#if !structuralCollapsed}
				<div class="structural-grid">
					{#each structuralEntries as [key, value] (key)}
						<div class="structural-entry">
							<span class="structural-pair">{key.replace(':', ' → ')}</span>
							<span class="structural-value">"{value}"</span>
						</div>
					{/each}
					{#if structuralEntries.length === 0}
						<p class="section-empty">No matches.</p>
					{/if}
				</div>
			{/if}
		</div>
	</div>
</div>

<ConfirmDialog
	open={confirmDeleteId !== null}
	message="Delete this custom predicate? This cannot be undone."
	onConfirm={() => confirmDeleteId !== null && handleDelete(confirmDeleteId)}
	onCancel={() => (confirmDeleteId = null)}
/>

<style>
	.schema-connections {
		max-width: 960px;
		margin: 0 auto;
	}

	/* Toolbar */
	.toolbar {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 16px;
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
	.toolbar-btn:hover { background: #f3f4f6; color: #374151; }
	.toolbar-btn.primary { background: #1f2937; color: white; border-color: #1f2937; }
	.toolbar-btn.primary:hover { background: #374151; }

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
	.search-input:focus { border-color: #9ca3af; }
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

	/* Create form */
	.create-form {
		padding: 16px;
		background: #f9fafb;
		border: 1px solid #e5e7eb;
		border-radius: 8px;
		margin-bottom: 16px;
	}
	.create-fields {
		display: flex;
		gap: 12px;
		flex-wrap: wrap;
	}
	.field {
		display: flex;
		flex-direction: column;
		gap: 4px;
		flex: 1;
		min-width: 160px;
	}
	.field-label {
		font-size: 0.7rem;
		font-weight: 600;
		color: #6b7280;
		text-transform: uppercase;
		letter-spacing: 0.3px;
	}
	.optional {
		font-weight: 400;
		text-transform: none;
		color: #9ca3af;
	}
	.field-input {
		padding: 6px 8px;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		font-size: 0.8rem;
	}
	.create-actions {
		display: flex;
		gap: 8px;
		justify-content: flex-end;
		margin-top: 12px;
	}
	.btn-sm {
		padding: 6px 12px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 0.8rem;
		cursor: pointer;
		background: white;
	}
	.btn-primary { background: #6b7280; color: white; border-color: #6b7280; }
	.btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }

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
	.area-count {
		font-size: 0.7rem;
		color: #9ca3af;
		background: #f3f4f6;
		border-radius: 10px;
		padding: 1px 8px;
	}
	.system-badge {
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
	.area-divider {
		border-top: 1px solid #e5e7eb;
		margin: 4px 0;
	}

	/* ── Tag groups + grid ── */
	.tag-group {
		margin-bottom: 12px;
	}
	.tag-group-label {
		display: block;
		font-size: 0.68rem;
		font-weight: 600;
		color: #9ca3af;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		margin-bottom: 6px;
		padding-left: 2px;
	}
	.tag-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 6px;
	}
	@media (max-width: 700px) {
		.tag-grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}

	/* ── Tag chips ── */
	.tag-chip {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 5px 10px;
		border-radius: 5px;
		font-size: 0.78rem;
		min-height: 28px;
		transition: background 0.1s;
	}
	.system-chip {
		background: #f3f4f6;
		border: 1px solid #e5e7eb;
		color: #4b5563;
	}
	.custom-chip {
		background: white;
		border: 1px solid #d1d5db;
		color: #374151;
	}
	.custom-chip:hover {
		border-color: #9ca3af;
		background: #f9fafb;
	}
	.tag-forward {
		font-weight: 500;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.tag-reverse {
		font-size: 0.7rem;
		color: #9ca3af;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	/* ── Chip actions (edit/delete on custom) ── */
	.chip-actions {
		display: flex;
		gap: 2px;
		margin-left: auto;
		flex-shrink: 0;
		opacity: 0;
		transition: opacity 0.12s;
	}
	.custom-chip:hover .chip-actions {
		opacity: 1;
	}
	.chip-action {
		width: 20px;
		height: 20px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: none;
		border: 1px solid transparent;
		border-radius: 3px;
		cursor: pointer;
		font-size: 0.72rem;
		color: #9ca3af;
		padding: 0;
		transition: all 0.12s;
	}
	.chip-action:hover { color: #374151; border-color: #d1d5db; background: #f3f4f6; }
	.chip-action-danger:hover { color: #ef4444; border-color: #fecaca; background: #fee2e2; }

	/* ── Editing chip ── */
	.editing-chip {
		background: #f9fafb;
		border: 1px solid #9ca3af;
		grid-column: 1 / -1;
		gap: 6px;
		padding: 6px 10px;
	}
	.edit-input {
		padding: 3px 6px;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		font-size: 0.76rem;
		flex: 1;
		min-width: 0;
	}
	.edit-input-sm {
		max-width: 100px;
	}

	/* ── Structural collapsible ── */
	.structural-section {
		margin-top: 8px;
	}
	.structural-toggle {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 6px 2px;
		background: none;
		border: none;
		cursor: pointer;
		font-size: 0.75rem;
		color: #6b7280;
		transition: color 0.1s;
	}
	.structural-toggle:hover { color: #374151; }
	.collapse-icon {
		font-size: 0.7rem;
		color: #9ca3af;
		width: 12px;
		flex-shrink: 0;
	}
	.section-count {
		font-size: 0.7rem;
		color: #9ca3af;
	}
	.structural-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 4px;
		padding: 6px 0;
	}
	@media (max-width: 700px) {
		.structural-grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}
	.structural-entry {
		display: flex;
		flex-direction: column;
		padding: 4px 8px;
		background: #f9fafb;
		border: 1px solid #f3f4f6;
		border-radius: 4px;
		font-size: 0.72rem;
	}
	.structural-pair {
		color: #6b7280;
		font-family: monospace;
		font-size: 0.68rem;
	}
	.structural-value {
		color: #374151;
		font-style: italic;
		font-size: 0.74rem;
	}
	.section-empty {
		font-size: 0.75rem;
		color: #9ca3af;
		padding: 8px 0;
	}

	.empty {
		text-align: center;
		color: #9ca3af;
		font-size: 0.85rem;
		padding: 24px 0;
	}
</style>

<script lang="ts">
	import type { Tag, ReadingList, ReadingListItem } from '$lib/types';
	import { readingLists, loadReadingLists } from '$lib/stores/readingLists';
	import { sources } from '$lib/stores/sources';
	import { loadTags } from '$lib/stores/tags';
	import { dateFilter, isItemVisible } from '$lib/stores/dateFilter';
	import { deleteReadingList, activateReadingList, deactivateReadingList, addItem, updateItem, removeItem } from '$lib/api/readingLists';
	import { getEntityTags, attachTag, detachTag } from '$lib/api/tags';
	import PanelContainer from '../shared/PanelContainer.svelte';
	import ConfirmDialog from '../shared/ConfirmDialog.svelte';
	import ReadingListForm from '../forms/ReadingListForm.svelte';
	import TagInput from '../shared/TagInput.svelte';
	import TagBadge from '../shared/TagBadge.svelte';
	import { selectEntity } from '$lib/stores/selectedEntity';
	import { selectable } from '$lib/actions/selectable';

	const STATUS_CYCLE = ['unread', 'reading', 'done'];
	const STATUS_COLORS: Record<string, string> = {
		unread: '#9ca3af',
		reading: '#f59e0b',
		done: '#10b981',
	};

	let filteredLists = $derived($readingLists.filter(rl => isItemVisible(rl, $dateFilter)));
	let showForm = $state(false);
	let editingIds = $state<Set<number>>(new Set());
	let confirmDelete: number | null = $state(null);
	let expandedId: number | null = $state(null);
	let entityTags = $state<Record<number, Tag[]>>({});
	let sourceSearch = $state('');
	let addingToListId: number | null = $state(null);
	let editingNoteId: number | null = $state(null);
	let noteText = $state('');

	let filteredSources = $derived(
		sourceSearch.length >= 1
			? $sources.filter(s => s.title.toLowerCase().includes(sourceSearch.toLowerCase()))
			: []
	);

	async function handleDelete(id: number) {
		await deleteReadingList(id);
		await Promise.all([loadReadingLists(), loadTags()]);
		confirmDelete = null;
	}

	async function toggleActive(id: number, isActive: boolean) {
		if (isActive) { await deactivateReadingList(id); } else { await activateReadingList(id); }
		await loadReadingLists();
	}

	async function toggleExpand(id: number) {
		if (expandedId === id) { expandedId = null; addingToListId = null; return; }
		expandedId = id;
		addingToListId = null;
		if (!entityTags[id]) {
			entityTags[id] = await getEntityTags('reading_list', id);
		}
	}

	async function handleAttach(listId: number, tag: Tag) {
		await attachTag(tag.id, 'reading_list', listId);
		entityTags[listId] = await getEntityTags('reading_list', listId);
	}

	async function handleDetach(listId: number, tag: Tag) {
		await detachTag(tag.id, 'reading_list', listId);
		entityTags[listId] = await getEntityTags('reading_list', listId);
	}

	async function handleAddSource(listId: number, sourceId: number) {
		const list = $readingLists.find(rl => rl.id === listId);
		const position = list ? list.items.length : 0;
		await addItem(listId, { source_id: sourceId, position });
		sourceSearch = '';
		addingToListId = null;
		await loadReadingLists();
	}

	async function cycleStatus(item: ReadingListItem) {
		const idx = STATUS_CYCLE.indexOf(item.status);
		const next = STATUS_CYCLE[(idx + 1) % STATUS_CYCLE.length];
		await updateItem(item.id, { status: next });
		await loadReadingLists();
	}

	async function handleRemoveItem(itemId: number) {
		await removeItem(itemId);
		await loadReadingLists();
	}

	async function moveItemUp(listId: number, item: ReadingListItem) {
		const list = $readingLists.find(rl => rl.id === listId);
		if (!list) return;
		const sorted = [...list.items].sort((a, b) => a.position - b.position);
		const idx = sorted.findIndex(i => i.id === item.id);
		if (idx <= 0) return;
		await updateItem(sorted[idx].id, { position: sorted[idx - 1].position });
		await updateItem(sorted[idx - 1].id, { position: item.position });
		await loadReadingLists();
	}

	async function moveItemDown(listId: number, item: ReadingListItem) {
		const list = $readingLists.find(rl => rl.id === listId);
		if (!list) return;
		const sorted = [...list.items].sort((a, b) => a.position - b.position);
		const idx = sorted.findIndex(i => i.id === item.id);
		if (idx >= sorted.length - 1) return;
		await updateItem(sorted[idx].id, { position: sorted[idx + 1].position });
		await updateItem(sorted[idx + 1].id, { position: item.position });
		await loadReadingLists();
	}

	async function saveNote(itemId: number) {
		await updateItem(itemId, { notes: noteText || undefined });
		editingNoteId = null;
		noteText = '';
		await loadReadingLists();
	}

	function getSourceTitle(sourceId: number): string {
		const source = $sources.find(s => s.id === sourceId);
		return source ? source.title : `Source #${sourceId}`;
	}

	async function loadAllTags() {
		const entries = await Promise.all(
			$readingLists.map(async (list) => [list.id, await getEntityTags('reading_list', list.id)] as const)
		);
		const updated: Record<number, Tag[]> = {};
		for (const [id, tags] of entries) updated[id] = tags;
		entityTags = updated;
	}

	$effect(() => {
		if ($readingLists) loadAllTags();
	});
</script>

<PanelContainer title="Reading Lists" panelId="readinglist" color="#5f9ea0" onAdd={() => (showForm = !showForm)}>
	{#if showForm}
		<div class="inline-form">
			<ReadingListForm onDone={() => (showForm = false)} />
		</div>
	{/if}

	{#each filteredLists as list (list.id)}
		{#if editingIds.has(list.id)}
			<div class="inline-form">
				<ReadingListForm editData={list} onDone={() => { editingIds.delete(list.id); editingIds = new Set(editingIds); }} />
			</div>
		{:else}
			<div class="item" use:selectable={{ entityType: 'reading_list', entityId: list.id }} ondblclick={() => selectEntity('reading_list', list.id, list.title)} role="button" tabindex="-1">
				<div class="item-header">
					<button class="item-title" ondblclick={() => { editingIds.add(list.id); editingIds = new Set(editingIds); }}>{list.title}</button>
					<span class="item-count">{list.items.length} items</span>
					<button class="btn-expand" onclick={() => toggleExpand(list.id)}>
						{expandedId === list.id ? 'Collapse' : 'Expand'}
					</button>
					<button class="btn-active" class:active={list.is_active} onclick={() => toggleActive(list.id, list.is_active)}>
						{list.is_active ? 'Active' : 'Inactive'}
					</button>
					<button class="btn-delete" onclick={() => (confirmDelete = list.id)}>Delete</button>
				</div>
				{#if entityTags[list.id]?.length}
					<div class="tag-badges">
						{#each entityTags[list.id] as tag (tag.id)}
							<TagBadge {tag} />
						{/each}
					</div>
				{/if}
				{#if list.description}
					<p class="item-desc">{list.description}</p>
				{/if}

				{#if expandedId === list.id}
					<div class="expanded-section">
						<div class="items-list">
							{#each [...list.items].sort((a, b) => a.position - b.position) as item (item.id)}
								<div class="list-item">
									<div class="list-item-header">
										<div class="reorder-btns">
											<button class="btn-move" onclick={() => moveItemUp(list.id, item)}>&#9650;</button>
											<button class="btn-move" onclick={() => moveItemDown(list.id, item)}>&#9660;</button>
										</div>
										<span class="source-title">{getSourceTitle(item.source_id)}</span>
										<button
											class="status-badge"
											style:background={STATUS_COLORS[item.status] || '#9ca3af'}
											onclick={() => cycleStatus(item)}
										>
											{item.status}
										</button>
										<button class="btn-note" onclick={() => { editingNoteId = editingNoteId === item.id ? null : item.id; noteText = item.notes ?? ''; }}>
											Notes
										</button>
										<button class="btn-remove" onclick={() => handleRemoveItem(item.id)}>x</button>
									</div>
									{#if item.notes && editingNoteId !== item.id}
										<p class="item-note">{item.notes}</p>
									{/if}
									{#if editingNoteId === item.id}
										<div class="note-edit">
											<textarea bind:value={noteText} rows="2" placeholder="Add notes..."></textarea>
											<div class="note-actions">
												<button class="btn-save-note" onclick={() => saveNote(item.id)}>Save</button>
												<button class="btn-cancel-note" onclick={() => { editingNoteId = null; }}>Cancel</button>
											</div>
										</div>
									{/if}
								</div>
							{/each}
						</div>

						<div class="add-source">
							{#if addingToListId === list.id}
								<div class="source-search">
									<input
										type="text"
										placeholder="Search sources by title..."
										bind:value={sourceSearch}
										class="source-search-input"
									/>
									{#if filteredSources.length > 0}
										<div class="source-dropdown">
											{#each filteredSources.slice(0, 10) as source (source.id)}
												<button class="source-option" onclick={() => handleAddSource(list.id, source.id)}>
													{source.title}
												</button>
											{/each}
										</div>
									{/if}
									<button class="btn-cancel-add" onclick={() => { addingToListId = null; sourceSearch = ''; }}>Cancel</button>
								</div>
							{:else}
								<button class="btn-add-source" onclick={() => (addingToListId = list.id)}>+ Add Source</button>
							{/if}
						</div>

						<div class="tag-section">
							<TagInput
								attachedTags={entityTags[list.id] || []}
								targetType="reading_list"
								targetId={list.id}
								onAttach={(tag) => handleAttach(list.id, tag)}
								onDetach={(tag) => handleDetach(list.id, tag)}
							/>
						</div>
					</div>
				{/if}
			</div>
		{/if}
	{/each}

	{#if $readingLists.length === 0}
		<p class="empty">No reading lists yet.</p>
	{:else if filteredLists.length === 0}
		<p class="empty">No reading lists for this date.</p>
	{/if}
</PanelContainer>

<ConfirmDialog
	open={confirmDelete !== null}
	message="Delete this reading list? All items will be removed."
	onConfirm={() => confirmDelete && handleDelete(confirmDelete)}
	onCancel={() => (confirmDelete = null)}
/>

<style>
	.inline-form { padding: 10px; background: #ecfeff; border: 1px solid #a5f3fc; border-radius: 8px; margin-bottom: 12px; }
	.item { padding: 10px 0; border-bottom: 1px solid #f3f4f6; }
	.item-header { display: flex; align-items: center; gap: 8px; }
	.item-title { flex: 1; background: none; border: none; cursor: pointer; font-weight: 500; font-size: 0.9rem; text-align: left; padding: 0; color: #111827; }
	.item-desc { font-size: 0.8rem; color: #6b7280; margin: 4px 0 0; }
	.item-count { font-size: 0.7rem; padding: 2px 6px; background: #ecfeff; border-radius: 4px; color: #0891b2; }
	.btn-expand { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #f9fafb; color: #6b7280; }
	.btn-active { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #f3f4f6; color: #6b7280; }
	.btn-active.active { background: #dcfce7; color: #16a34a; border-color: #bbf7d0; }
	.tag-badges { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
	.btn-delete { font-size: 0.75rem; padding: 2px 8px; background: #fee2e2; color: #ef4444; border: 1px solid #fecaca; border-radius: 4px; cursor: pointer; }
	.tag-section { margin-top: 8px; padding: 8px; background: #f9fafb; border-radius: 6px; }
	.empty { text-align: center; color: #9ca3af; font-size: 0.875rem; }

	.expanded-section { margin-top: 8px; padding: 8px; background: #f9fafb; border-radius: 6px; }
	.items-list { display: flex; flex-direction: column; gap: 4px; }
	.list-item { background: white; border: 1px solid #e5e7eb; border-radius: 6px; padding: 6px 8px; }
	.list-item-header { display: flex; align-items: center; gap: 6px; }
	.reorder-btns { display: flex; flex-direction: column; gap: 0; }
	.btn-move { background: none; border: none; cursor: pointer; font-size: 0.6rem; padding: 0 2px; color: #9ca3af; line-height: 1; }
	.btn-move:hover { color: #374151; }
	.source-title { flex: 1; font-size: 0.8rem; font-weight: 500; color: #374151; }
	.status-badge { font-size: 0.65rem; padding: 2px 8px; border-radius: 10px; color: white; border: none; cursor: pointer; font-weight: 500; text-transform: capitalize; }
	.btn-note { font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #f9fafb; color: #6b7280; }
	.btn-remove { font-size: 0.7rem; background: none; border: none; cursor: pointer; color: #ef4444; padding: 0 4px; }
	.item-note { font-size: 0.75rem; color: #6b7280; margin: 4px 0 0 24px; font-style: italic; }
	.note-edit { margin-top: 4px; margin-left: 24px; }
	.note-edit textarea { width: 100%; padding: 4px 6px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.8rem; resize: vertical; }
	.note-actions { display: flex; gap: 4px; margin-top: 4px; }
	.btn-save-note { font-size: 0.7rem; padding: 2px 8px; background: #06b6d4; color: white; border: none; border-radius: 4px; cursor: pointer; }
	.btn-cancel-note { font-size: 0.7rem; padding: 2px 8px; background: white; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; }

	.add-source { margin-top: 8px; }
	.btn-add-source { font-size: 0.8rem; padding: 4px 12px; background: #ecfeff; color: #0891b2; border: 1px dashed #a5f3fc; border-radius: 6px; cursor: pointer; width: 100%; }
	.source-search { display: flex; flex-direction: column; gap: 4px; position: relative; }
	.source-search-input { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.8rem; }
	.source-dropdown { background: white; border: 1px solid #e5e7eb; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); max-height: 150px; overflow-y: auto; }
	.source-option { display: block; width: 100%; text-align: left; padding: 6px 10px; border: none; background: none; cursor: pointer; font-size: 0.8rem; color: #374151; }
	.source-option:hover { background: #f3f4f6; }
	.btn-cancel-add { font-size: 0.75rem; padding: 4px 8px; background: white; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; align-self: flex-start; }
</style>

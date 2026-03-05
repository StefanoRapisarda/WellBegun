<script lang="ts">
	import type { Tag, Collection, CollectionItem, Category } from '$lib/types';
	import { collections, loadCollections } from '$lib/stores/collections';
	import { categories, loadCategories } from '$lib/stores/categories';
	import { sources, loadSources } from '$lib/stores/sources';
	import { activities, loadActivities } from '$lib/stores/activities';
	import { notes, loadNotes } from '$lib/stores/notes';
	import { tags, loadTags, entityTagsVersion } from '$lib/stores/tags';
	import { dateFilter, isItemVisible, selectedFilterTags, isTagVisible, isEntitySourceOfFilterTag, showActiveRelated, activeEntityTagIds, isActiveRelated } from '$lib/stores/dateFilter';
	import { setLastUsedTags } from '$lib/stores/lastUsedTags';
	import { createCollection, deleteCollection, activateCollection, deactivateCollection, updateCollection, addItem, updateItem, removeItem } from '$lib/api/collections';
	import { createSource, deleteSource } from '$lib/api/sources';
	import { createActivity, deleteActivity } from '$lib/api/activities';
	import { createNote, deleteNote } from '$lib/api/notes';
	import { getEntityTags, attachTag, detachTag } from '$lib/api/tags';
	import PanelContainer from '../shared/PanelContainer.svelte';
	import TagInput from '../shared/TagInput.svelte';
	import TagBadge from '../shared/TagBadge.svelte';
	import Timestamp from '../shared/Timestamp.svelte';
	import { selectEntity } from '$lib/stores/selectedEntity';
	import { selectable } from '$lib/actions/selectable';

	import { pendingCollectionMembers, removePendingMember, clearPendingCollection } from '$lib/stores/pendingCollection';
	import { getCategories, createCategory } from '$lib/api/categories';

	// Panel-level tag filter state
	let panelSelectedTagIds = $state<number[]>([]);
	let panelFilterMode = $state<'or' | 'and'>('or');

	let availablePanelTags = $derived(() => {
		const tagMap = new Map<number, Tag>();
		for (const col of $collections) {
			const colTags = entityTags[col.id] || [];
			for (const tag of colTags) {
				tagMap.set(tag.id, tag);
			}
		}
		return Array.from(tagMap.values()).sort((a, b) =>
			`${a.category}:${a.name}`.localeCompare(`${b.category}:${b.name}`)
		);
	});

	function passesPanelFilter(itemTags: Tag[]): boolean {
		if (panelSelectedTagIds.length === 0) return true;
		if (panelFilterMode === 'or') {
			return itemTags.some(t => panelSelectedTagIds.includes(t.id));
		} else {
			return panelSelectedTagIds.every(id => itemTags.some(t => t.id === id));
		}
	}

	function handlePanelTagToggle(tagId: number) {
		if (panelSelectedTagIds.includes(tagId)) {
			panelSelectedTagIds = panelSelectedTagIds.filter(id => id !== tagId);
		} else {
			panelSelectedTagIds = [...panelSelectedTagIds, tagId];
		}
	}

	function handlePanelModeToggle() {
		panelFilterMode = panelFilterMode === 'or' ? 'and' : 'or';
	}

	let filteredCollections = $derived($collections.filter(col =>
		isItemVisible(col, $dateFilter) &&
		(isTagVisible(entityTags[col.id] || [], $selectedFilterTags) || isEntitySourceOfFilterTag('collection', col.id, $selectedFilterTags)) &&
		passesPanelFilter(entityTags[col.id] || []) &&
		(!$showActiveRelated || isActiveRelated(entityTags[col.id] || [], $activeEntityTagIds, col.is_active))
	));

	// Collection creation from selected entities
	let pendingMembers = $derived($pendingCollectionMembers);
	let showCreateForm = $derived(pendingMembers.length > 0);
	let createTitle = $state('');
	let createDescription = $state('');
	let creatingCollection = $state(false);

	async function handleCreateFromSelection() {
		if (!createTitle.trim() || pendingMembers.length === 0) return;
		creatingCollection = true;
		try {
			const memberType = pendingMembers[0].entityType;
			const cats = $categories.length > 0 ? $categories : await getCategories();
			let cat = cats.find(c => c.member_entity_type === memberType);
			if (!cat) {
				// No category for this entity type — auto-create one
				cat = await createCategory({
					slug: memberType,
					display_name: memberType.charAt(0).toUpperCase() + memberType.slice(1) + 's',
					member_entity_type: memberType
				});
				await loadCategories();
			}

			const col = await createCollection({
				title: createTitle.trim(),
				category_id: cat.id,
				description: createDescription.trim() || undefined
			});

			const defaultStatus = cat.statuses?.find(s => s.is_default)?.value ?? cat.statuses?.[0]?.value;
			for (let i = 0; i < pendingMembers.length; i++) {
				const m = pendingMembers[i];
				await addItem(col.id, {
					member_entity_type: memberType,
					member_entity_id: m.entityId,
					position: i,
					status: defaultStatus ?? undefined
				});
			}

			createTitle = '';
			createDescription = '';
			clearPendingCollection();
			await Promise.all([loadCollections(), loadSources(), loadActivities(), loadNotes()]);
		} finally {
			creatingCollection = false;
		}
	}

	let editFieldsColId: number | null = $state(null);
	let editFields = $state<{ title: string; description: string }>({ title: '', description: '' });
	let confirmDelete: number | null = $state(null);
	let entityTags = $state<Record<number, Tag[]>>({});
	let tagsExpandedId: number | null = $state(null);
	let inlineNewTitles = $state<Record<string, string>>({});
	let editingTitleItemId: number | null = $state(null);
	let editTitleText = $state('');
	let editingSectionKey: string | null = $state(null);
	let editSectionText = $state('');

	// Inline add — entity suggestions
	let activeSuggestKey: string | null = $state(null);
	let suggestResults = $state<{ id: number; title: string; type: string }[]>([]);

	// Drag-and-drop between sections
	let draggedItem = $state<{ colId: number; itemId: number; fromHeader: string | null } | null>(null);
	let dropTargetKey = $state<string | null>(null);

	function handleItemDragStart(colId: number, item: CollectionItem, e: DragEvent) {
		draggedItem = { colId, itemId: item.id, fromHeader: item.header ?? null };
		if (e.dataTransfer) {
			e.dataTransfer.effectAllowed = 'move';
			e.dataTransfer.setData('text/plain', '');
		}
	}

	function handleSectionDragOver(colId: number, header: string | null, e: DragEvent) {
		if (!draggedItem || draggedItem.colId !== colId) return;
		e.preventDefault();
		if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
		dropTargetKey = sectionKey(colId, header);
	}

	function handleSectionDragLeave(e: DragEvent) {
		const currentTarget = e.currentTarget as HTMLElement;
		const relatedTarget = e.relatedTarget as HTMLElement | null;
		if (!relatedTarget || !currentTarget.contains(relatedTarget)) {
			dropTargetKey = null;
		}
	}

	async function handleSectionDrop(colId: number, header: string | null, e: DragEvent) {
		e.preventDefault();
		dropTargetKey = null;
		if (!draggedItem || draggedItem.colId !== colId) return;
		if ((draggedItem.fromHeader ?? null) === (header ?? null)) {
			draggedItem = null;
			return;
		}
		await updateItem(draggedItem.itemId, { header: header });
		draggedItem = null;
		await loadCollections();
	}

	function handleDragEnd() {
		draggedItem = null;
		dropTargetKey = null;
	}

	// Status helpers
	function getCategory(col: Collection): Category | undefined {
		return $categories.find(c => c.id === col.category_id);
	}

	function getStatusCycle(col: Collection): string[] {
		const cat = getCategory(col);
		if (cat && cat.statuses.length > 0) {
			return [...cat.statuses].sort((a, b) => a.position - b.position).map(s => s.value);
		}
		return ['todo', 'in_progress', 'done'];
	}

	const STATUS_COLORS: Record<string, string> = {
		todo: '#9ca3af',
		unread: '#9ca3af',
		in_progress: '#f59e0b',
		reading: '#f59e0b',
		done: '#10b981',
		read: '#10b981',
	};

	function getStatusColor(status: string | null): string {
		if (!status) return '#9ca3af';
		return STATUS_COLORS[status] ?? '#7c6f9e';
	}

	function getDoneCount(col: Collection): number {
		const cycle = getStatusCycle(col);
		const lastStatus = cycle[cycle.length - 1];
		return col.items.filter(i => i.status === lastStatus).length;
	}

	function getProgressPercent(col: Collection): number {
		if (col.items.length === 0) return 0;
		return Math.round((getDoneCount(col) / col.items.length) * 100);
	}

	function getMemberTitle(item: CollectionItem): string {
		if (item.member_entity_type === 'source') {
			const s = $sources.find(s => s.id === item.member_entity_id);
			return s ? s.title : `Source #${item.member_entity_id}`;
		} else if (item.member_entity_type === 'activity') {
			const a = $activities.find(a => a.id === item.member_entity_id);
			return a ? a.title : `Activity #${item.member_entity_id}`;
		} else if (item.member_entity_type === 'note') {
			const n = $notes.find(n => n.id === item.member_entity_id);
			return n ? n.title : `Note #${item.member_entity_id}`;
		}
		return `${item.member_entity_type} #${item.member_entity_id}`;
	}

	interface SectionGroup {
		header: string | null;
		items: CollectionItem[];
	}

	function getGroupedItems(col: Collection): SectionGroup[] {
		const sorted = [...col.items].sort((a, b) => a.position - b.position);
		const groups: SectionGroup[] = [];
		const headerOrder: (string | null)[] = [];

		for (const item of sorted) {
			const h = item.header ?? null;
			if (!headerOrder.includes(h)) {
				headerOrder.push(h);
			}
		}

		const orderedHeaders = [
			...(headerOrder.includes(null) ? [null] : []),
			...headerOrder.filter(h => h !== null)
		];

		for (const h of orderedHeaders) {
			groups.push({
				header: h,
				items: sorted.filter(i => (i.header ?? null) === h)
			});
		}

		if (groups.length === 0) {
			groups.push({ header: null, items: [] });
		}

		return groups;
	}

	function sectionKey(colId: number, header: string | null): string {
		return `${colId}:${header ?? '__ungrouped__'}`;
	}

	function getInlineTitle(colId: number, header: string | null): string {
		return inlineNewTitles[sectionKey(colId, header)] ?? '';
	}

	function setInlineTitle(colId: number, header: string | null, value: string) {
		inlineNewTitles[sectionKey(colId, header)] = value;
		inlineNewTitles = { ...inlineNewTitles };
	}

	// Collection-level handlers
	async function handleDelete(id: number, deleteMembers: boolean) {
		const col = $collections.find(c => c.id === id);
		if (col) {
			for (const item of col.items) {
				if (deleteMembers) {
					await deleteMemberEntity(item);
				}
				await removeItem(item.id);
			}
		}
		await deleteCollection(id);
		await Promise.all([loadCollections(), loadSources(), loadActivities(), loadNotes(), loadTags()]);
		confirmDelete = null;
	}

	async function deleteMemberEntity(item: CollectionItem) {
		if (item.member_entity_type === 'source') {
			await deleteSource(item.member_entity_id);
		} else if (item.member_entity_type === 'activity') {
			await deleteActivity(item.member_entity_id);
		} else if (item.member_entity_type === 'note') {
			await deleteNote(item.member_entity_id);
		}
	}

	async function toggleActive(id: number, isActive: boolean) {
		if (isActive) { await deactivateCollection(id); } else { await activateCollection(id); }
		await loadCollections();
	}

	async function toggleTagsExpand(id: number) {
		if (tagsExpandedId === id) { tagsExpandedId = null; return; }
		tagsExpandedId = id;
		if (!entityTags[id]) {
			entityTags[id] = await getEntityTags('collection', id);
		}
	}

	async function handleAttach(colId: number, tag: Tag) {
		await attachTag(tag.id, 'collection', colId);
		entityTags[colId] = await getEntityTags('collection', colId);
		setLastUsedTags('collection', entityTags[colId]);
	}

	async function handleDetach(colId: number, tag: Tag) {
		await detachTag(tag.id, 'collection', colId);
		entityTags[colId] = await getEntityTags('collection', colId);
		setLastUsedTags('collection', entityTags[colId]);
	}

	// Inline field editing
	function startEditFields(col: Collection) {
		editFieldsColId = col.id;
		editFields = {
			title: col.title,
			description: col.description ?? ''
		};
	}

	async function saveEditFields() {
		if (!editFieldsColId || !editFields.title.trim()) return;
		await updateCollection(editFieldsColId, {
			title: editFields.title.trim(),
			description: editFields.description.trim() || undefined
		});
		editFieldsColId = null;
		await Promise.all([loadCollections(), loadTags()]);
	}

	// Inline add — search existing entities
	function getEntityStore(memberType: string): any[] {
		if (memberType === 'source') return $sources;
		if (memberType === 'activity') return $activities;
		if (memberType === 'note') return $notes;
		return [];
	}

	function getTitleField(memberType: string): string {
		return 'title'; // all member types use 'title'
	}

	function updateSuggestions(colId: number, header: string | null) {
		const key = sectionKey(colId, header);
		const query = getInlineTitle(colId, header).toLowerCase().trim();
		if (!query) {
			activeSuggestKey = null;
			suggestResults = [];
			return;
		}
		const col = $collections.find(c => c.id === colId);
		if (!col) return;
		const cat = getCategory(col);
		const memberType = cat?.member_entity_type ?? 'source';
		const store = getEntityStore(memberType);
		const field = getTitleField(memberType);
		// Exclude entities already in this collection
		const existingIds = new Set(col.items.map(i => i.member_entity_id));
		const matches = store
			.filter((e: any) => !existingIds.has(e.id) && (e[field] as string).toLowerCase().includes(query))
			.slice(0, 8)
			.map((e: any) => ({ id: e.id, title: e[field] as string, type: memberType }));
		suggestResults = matches;
		activeSuggestKey = matches.length > 0 ? key : null;
	}

	async function handleAddExisting(colId: number, entityId: number, header: string | null = null) {
		const col = $collections.find(c => c.id === colId);
		if (!col) return;
		const cat = getCategory(col);
		const memberType = cat?.member_entity_type ?? 'source';
		const position = col.items.length;
		const defaultStatus = cat?.statuses?.find(s => s.is_default)?.value ?? cat?.statuses?.[0]?.value;
		await addItem(colId, {
			member_entity_type: memberType,
			member_entity_id: entityId,
			position,
			status: defaultStatus ?? undefined,
			header: header ?? undefined
		});
		setInlineTitle(colId, header, '');
		activeSuggestKey = null;
		suggestResults = [];
		await loadCollections();
	}

	async function handleInlineCreate(colId: number, header: string | null = null) {
		const title = getInlineTitle(colId, header);
		if (!title.trim()) return;
		const col = $collections.find(c => c.id === colId);
		if (!col) return;
		const cat = getCategory(col);
		const memberType = cat?.member_entity_type ?? 'source';
		let memberId: number;

		if (memberType === 'source') {
			const s = await createSource({ title: title.trim() });
			memberId = s.id;
		} else if (memberType === 'activity') {
			const a = await createActivity({ title: title.trim() });
			memberId = a.id;
		} else if (memberType === 'note') {
			const n = await createNote({ title: title.trim() });
			memberId = n.id;
		} else {
			const s = await createSource({ title: title.trim() });
			memberId = s.id;
		}

		const position = col.items.length;
		const defaultStatus = cat?.statuses?.find(s => s.is_default)?.value ?? cat?.statuses?.[0]?.value;
		await addItem(colId, {
			member_entity_type: memberType,
			member_entity_id: memberId,
			position,
			status: defaultStatus ?? undefined,
			header: header ?? undefined
		});
		setInlineTitle(colId, header, '');
		activeSuggestKey = null;
		suggestResults = [];
		await Promise.all([loadCollections(), loadSources(), loadActivities(), loadNotes()]);
	}

	async function handleRenameSection(colId: number, oldHeader: string, newHeader: string) {
		if (!newHeader.trim() || newHeader === oldHeader) {
			editingSectionKey = null;
			return;
		}
		const col = $collections.find(c => c.id === colId);
		if (!col) return;
		const sectionItems = col.items.filter(i => i.header === oldHeader);
		await Promise.all(sectionItems.map(i => updateItem(i.id, { header: newHeader.trim() })));
		editingSectionKey = null;
		editSectionText = '';
		await loadCollections();
	}

	async function handleDeleteSection(colId: number, header: string) {
		const col = $collections.find(c => c.id === colId);
		if (!col) return;
		const sectionItems = col.items.filter(i => i.header === header);
		await Promise.all(sectionItems.map(i => updateItem(i.id, { header: null })));
		await loadCollections();
	}

	// Item handlers
	async function handleUpdateTitle(item: CollectionItem) {
		if (!editTitleText.trim()) { editingTitleItemId = null; return; }
		// Update the member entity title
		if (item.member_entity_type === 'source') {
			const { updateSource } = await import('$lib/api/sources');
			await updateSource(item.member_entity_id, { title: editTitleText.trim() });
		} else if (item.member_entity_type === 'activity') {
			const { updateActivity } = await import('$lib/api/activities');
			await updateActivity(item.member_entity_id, { title: editTitleText.trim() });
		} else if (item.member_entity_type === 'note') {
			const { updateNote } = await import('$lib/api/notes');
			await updateNote(item.member_entity_id, { title: editTitleText.trim() });
		}
		editingTitleItemId = null;
		editTitleText = '';
		await Promise.all([loadCollections(), loadSources(), loadActivities(), loadNotes()]);
	}

	async function cycleStatus(col: Collection, item: CollectionItem) {
		const cycle = getStatusCycle(col);
		const idx = cycle.indexOf(item.status ?? '');
		const next = cycle[(idx + 1) % cycle.length];
		await updateItem(item.id, { status: next });
		await loadCollections();
	}

	async function handleRemoveItem(item: CollectionItem, deleteEntity: boolean = false) {
		if (deleteEntity) {
			await deleteMemberEntity(item);
		}
		await removeItem(item.id);
		await Promise.all([loadCollections(), loadSources(), loadActivities(), loadNotes(), loadTags()]);
	}

	// Tag loading
	async function loadAllTags() {
		const entries = await Promise.all(
			$collections.map(async (col) => [col.id, await getEntityTags('collection', col.id)] as const)
		);
		const updated: Record<number, Tag[]> = {};
		for (const [id, tags] of entries) updated[id] = tags;
		entityTags = updated;
	}

	$effect(() => {
		const _ = $entityTagsVersion;
		if ($collections) loadAllTags();
	});
</script>

<PanelContainer
	title="Collections"
	panelId="collection"
	color="#7c6f9e"
	availableTags={availablePanelTags()}
	selectedTagIds={panelSelectedTagIds}
	filterMode={panelFilterMode}
	onTagToggle={handlePanelTagToggle}
	onModeToggle={handlePanelModeToggle}
>
	{#if showCreateForm}
		<div class="create-from-selection">
			<div class="create-form-header">
				<span class="create-form-label">New collection from {pendingMembers.length} {pendingMembers[0].entityType}s</span>
				<button class="btn-cancel-create" onclick={clearPendingCollection}>&times;</button>
			</div>
			<input type="text" class="title-input" bind:value={createTitle} placeholder="Collection title..." />
			<textarea class="field-textarea" bind:value={createDescription} rows="4" placeholder="Description (optional)"></textarea>
			<div class="pending-members">
				{#each pendingMembers as member (member.entityId)}
					<div class="pending-member-card">
						<span class="pending-member-title">{member.title}</span>
						<button class="btn-remove-pending" onclick={() => removePendingMember(member.entityId)}>&times;</button>
					</div>
				{/each}
			</div>
			<div class="create-actions">
				<button class="btn-cancel-edit" onclick={clearPendingCollection}>Cancel</button>
				<button class="btn-save-edit" onclick={handleCreateFromSelection} disabled={!createTitle.trim() || creatingCollection}>
					{creatingCollection ? 'Creating...' : 'Create'}
				</button>
			</div>
		</div>
	{/if}

	{#each filteredCollections as col (col.id)}
		<div class="item" use:selectable={{ entityType: 'collection', entityId: col.id }}>
			<div class="item-actions">
				<button class="btn-tags" onclick={() => toggleTagsExpand(col.id)}>Tags</button>
				<button class="btn-active" class:active={col.is_active} onclick={() => toggleActive(col.id, col.is_active)}>
					{col.is_active ? 'Active' : 'Inactive'}
				</button>
				<button class="btn-delete" onclick={() => (confirmDelete = col.id)}>Delete</button>
			</div>
			{#if tagsExpandedId === col.id}
				<div class="tag-section">
					<TagInput
						attachedTags={entityTags[col.id] || []}
						targetType="collection"
						targetId={col.id}
						onAttach={(tag) => handleAttach(col.id, tag)}
						onDetach={(tag) => handleDetach(col.id, tag)}
						onClose={() => (tagsExpandedId = null)}
					/>
				</div>
			{/if}
			<div class="item-card" ondblclick={() => selectEntity('collection', col.id, col.title)} role="button" tabindex="-1">
				{#if editFieldsColId === col.id}
					<div class="edit-fields-section">
						<input type="text" class="title-input" bind:value={editFields.title} placeholder="Collection title..." />
						<textarea class="field-textarea" bind:value={editFields.description} rows="4" placeholder="Description (optional)"></textarea>
						<div class="edit-fields-actions">
							<button class="btn-cancel-edit" onclick={() => editFieldsColId = null}>Cancel</button>
							<button class="btn-save-edit" onclick={saveEditFields}>Save</button>
						</div>
					</div>
				{:else}
					<div class="item-header">
						<button class="item-title" ondblclick={(e) => { e.stopPropagation(); startEditFields(col); }}>{col.title}</button>
						<span class="item-count">{getDoneCount(col)}/{col.items.length}</span>
					</div>

					{#if col.items.length > 0}
						<div class="progress-bar">
							<div class="progress-fill" style:width="{getProgressPercent(col)}%"></div>
						</div>
					{/if}

					{#if entityTags[col.id]?.length}
						<div class="tag-badges">
							{#each entityTags[col.id] as tag (tag.id)}
								<TagBadge {tag} removable onRemove={() => handleDetach(col.id, tag)} />
							{/each}
						</div>
					{/if}

					{#if col.description}
						<p class="item-desc">{col.description}</p>
					{/if}
				{/if}

					<!-- Items grouped by section -->
					{#each getGroupedItems(col) as group}
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<div
							class="section-drop-zone"
							class:drop-target={dropTargetKey === sectionKey(col.id, group.header) && draggedItem?.fromHeader !== (group.header ?? null)}
							ondragover={(e) => handleSectionDragOver(col.id, group.header, e)}
							ondragleave={handleSectionDragLeave}
							ondrop={(e) => handleSectionDrop(col.id, group.header, e)}
						>
							{#if group.header !== null}
								<div class="section-header-bar">
									{#if editingSectionKey === sectionKey(col.id, group.header)}
										<input
											type="text"
											class="edit-section-input"
											bind:value={editSectionText}
											onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleRenameSection(col.id, group.header!, editSectionText); } else if (e.key === 'Escape') { editingSectionKey = null; } }}
											onblur={() => handleRenameSection(col.id, group.header!, editSectionText)}
										/>
									{:else}
										<button class="section-header-name" onclick={() => { editingSectionKey = sectionKey(col.id, group.header); editSectionText = group.header!; }}>{group.header}</button>
									{/if}
									<button class="btn-delete-section" onclick={() => handleDeleteSection(col.id, group.header!)}>x</button>
								</div>
							{/if}
							<div class="items-list">
								{#each group.items as item (item.id)}
									<div
										class="list-item"
										class:done={item.status === getStatusCycle(col)[getStatusCycle(col).length - 1]}
										class:dragging={draggedItem?.itemId === item.id}
										draggable="true"
										ondragstart={(e) => handleItemDragStart(col.id, item, e)}
										ondragend={handleDragEnd}
									>
										<div class="list-item-row">
											<span class="drag-grip">&#10239;</span>
											<button
												class="status-badge"
												style:background={getStatusColor(item.status)}
												onclick={() => cycleStatus(col, item)}
											>
												{item.status ?? 'none'}
											</button>
											{#if editingTitleItemId === item.id}
												<input
													type="text"
													class="edit-title-input"
													bind:value={editTitleText}
													onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleUpdateTitle(item); } else if (e.key === 'Escape') { editingTitleItemId = null; } }}
													onblur={() => handleUpdateTitle(item)}
												/>
											{:else}
												<button
													class="source-title-btn"
													class:checked={item.status === getStatusCycle(col)[getStatusCycle(col).length - 1]}
													onclick={() => { editingTitleItemId = item.id; editTitleText = getMemberTitle(item); }}
												>{getMemberTitle(item)}</button>
											{/if}
											<button class="btn-remove-item" onclick={() => handleRemoveItem(item, true)}>-</button>
										</div>
									</div>
								{/each}
							</div>
							<div class="add-source">
								<div class="inline-create">
									<input
										type="text"
										placeholder="Add existing..."
										value={getInlineTitle(col.id, group.header)}
										oninput={(e) => { setInlineTitle(col.id, group.header, e.currentTarget.value); updateSuggestions(col.id, group.header); }}
										onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleInlineCreate(col.id, group.header); } else if (e.key === 'Escape') { activeSuggestKey = null; suggestResults = []; } }}
										onfocus={() => updateSuggestions(col.id, group.header)}
										onblur={() => { setTimeout(() => { activeSuggestKey = null; suggestResults = []; }, 150); }}
										class="inline-create-input"
									/>
									<button class="btn-inline-create" onclick={() => handleInlineCreate(col.id, group.header)}>+</button>
								</div>
								{#if activeSuggestKey === sectionKey(col.id, group.header) && suggestResults.length > 0}
									<div class="suggest-dropdown">
										{#each suggestResults as s (s.id)}
											<button class="suggest-item" onmousedown={() => handleAddExisting(col.id, s.id, group.header)}>
												{s.title}
											</button>
										{/each}
									</div>
								{/if}
							</div>
						</div>
					{/each}

					<Timestamp date={col.created_at} />
				</div>

		</div>
	{/each}

	{#if $collections.length === 0}
		<p class="empty">No collections yet.</p>
	{:else if filteredCollections.length === 0}
		<p class="empty">No collections match current filters.</p>
	{/if}
</PanelContainer>

{#if confirmDelete !== null}
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<div class="dialog-overlay" onclick={() => confirmDelete = null} onkeydown={(e) => e.key === 'Escape' && (confirmDelete = null)} role="dialog" tabindex="-1">
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<div class="dialog-content" onclick={(e) => e.stopPropagation()} role="document">
			<p class="dialog-title">Delete this collection?</p>
			<p class="dialog-message">Do you also want to delete all member entities contained in this collection?</p>
			<div class="dialog-actions">
				<button class="btn-dialog btn-dialog-cancel" onclick={() => confirmDelete = null}>Cancel</button>
				<button class="btn-dialog btn-dialog-keep" onclick={() => confirmDelete && handleDelete(confirmDelete, false)}>Keep entities</button>
				<button class="btn-dialog btn-dialog-delete-all" onclick={() => confirmDelete && handleDelete(confirmDelete, true)}>Delete all</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.item { padding: 12px 0; border-bottom: 1px solid #e5e7eb; }
	.item-actions { display: flex; gap: 6px; margin-bottom: 6px; }
	.item-card { padding: 10px 12px; background: #fafafa; border: 1px solid #e5e7eb; border-radius: 8px; }
	.item-header { display: flex; align-items: center; gap: 8px; }
	.item-title { flex: 1; background: none; border: none; cursor: pointer; font-weight: 500; font-size: 0.9rem; text-align: left; padding: 0; color: #111827; }
	.item-desc { font-size: 0.8rem; color: #6b7280; margin: 4px 0 0; white-space: pre-wrap; }
	.item-count { font-size: 0.7rem; padding: 2px 6px; background: #f5f3fa; border-radius: 4px; color: #7c6f9e; font-weight: 600; }
	.btn-active { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #f3f4f6; color: #6b7280; }
	.btn-active.active { background: #dcfce7; color: #16a34a; border-color: #bbf7d0; }
	.btn-tags { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #f9fafb; color: #6b7280; }
	.btn-delete { font-size: 0.75rem; padding: 2px 8px; background: #fee2e2; color: #ef4444; border: 1px solid #fecaca; border-radius: 4px; cursor: pointer; }
	.tag-badges { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
	.tag-section { margin-top: 8px; padding: 8px; background: #f9fafb; border-radius: 6px; }
	.empty { text-align: center; color: #9ca3af; font-size: 0.875rem; }

	.progress-bar { height: 4px; background: #e5e7eb; border-radius: 2px; margin-top: 6px; overflow: hidden; }
	.progress-fill { height: 100%; background: #7c6f9e; border-radius: 2px; transition: width 0.3s ease; }

	/* Item list */
	.items-list { display: flex; flex-direction: column; gap: 4px; margin-top: 6px; }
	.list-item { padding: 4px 8px; background: #fafafa; border: 1px solid #e5e7eb; border-radius: 6px; }
	.list-item.done { opacity: 0.6; }
	.list-item-row { display: flex; align-items: center; gap: 6px; }
	.source-title-btn { flex: 1; background: none; border: none; cursor: pointer; font-size: 0.8rem; font-weight: 500; color: #374151; text-align: left; padding: 0; }
	.source-title-btn.checked { text-decoration: line-through; color: #9ca3af; }
	.edit-title-input { flex: 1; padding: 2px 6px; border: 1px solid #7c6f9e; border-radius: 4px; font-size: 0.8rem; font-weight: 500; color: #374151; outline: none; }
	.status-badge { font-size: 0.6rem; padding: 2px 8px; border-radius: 10px; color: white; border: none; cursor: pointer; font-weight: 500; text-transform: capitalize; flex-shrink: 0; }
	.btn-remove-item { background: none; border: none; cursor: pointer; font-size: 1rem; font-weight: 700; color: #ef4444; padding: 0 4px; line-height: 1; }

	.add-source { margin-top: 4px; }
	.inline-create { display: flex; gap: 4px; }
	.inline-create-input { flex: 1; padding: 4px 8px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.78rem; }
	.btn-inline-create { padding: 3px 8px; background: #7c6f9e; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85rem; font-weight: 600; }

	/* Entity suggestions dropdown */
	.suggest-dropdown { margin-top: 2px; background: white; border: 1px solid #d1d5db; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); max-height: 160px; overflow-y: auto; }
	.suggest-item { display: block; width: 100%; padding: 5px 8px; border: none; background: none; cursor: pointer; font-size: 0.78rem; color: #374151; text-align: left; }
	.suggest-item:hover { background: #f5f3fa; color: #7c6f9e; }


	/* Section headers */
	.section-header-bar { display: flex; align-items: center; gap: 6px; margin-top: 8px; padding: 4px 8px; background: #f0eef6; border-radius: 4px; border-left: 3px solid #7c6f9e; }
	.section-header-name { flex: 1; background: none; border: none; cursor: pointer; font-size: 0.78rem; font-weight: 600; color: #374151; text-align: left; padding: 0; }
	.edit-section-input { flex: 1; padding: 2px 6px; border: 1px solid #7c6f9e; border-radius: 4px; font-size: 0.78rem; font-weight: 600; color: #374151; outline: none; }
	.btn-delete-section { background: none; border: none; cursor: pointer; font-size: 0.75rem; font-weight: 700; color: #9ca3af; padding: 0 4px; line-height: 1; }
	.btn-delete-section:hover { color: #ef4444; }

	/* Inline edit fields */
	.edit-fields-section { display: flex; flex-direction: column; gap: 6px; padding: 4px 0; }
	.edit-fields-section .title-input { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.field-textarea { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; resize: vertical; font-family: inherit; min-height: calc(4 * 0.85rem * 1.5 + 12px); width: 100%; box-sizing: border-box; }
	.edit-fields-actions { display: flex; justify-content: flex-end; gap: 6px; padding-top: 4px; }
	.btn-save-edit { padding: 6px 14px; background: #7c6f9e; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-save-edit:hover { background: #685d87; }
	.btn-cancel-edit { padding: 6px 14px; background: white; color: #6b7280; border: 1px solid #d1d5db; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-cancel-edit:hover { background: #f3f4f6; }

	/* Drag-and-drop */
	.section-drop-zone { border-radius: 6px; border: 2px solid transparent; transition: border-color 0.15s, background 0.15s; }
	.section-drop-zone.drop-target { border-color: #7c6f9e; background: rgba(124, 111, 158, 0.06); }
	.drag-grip { cursor: grab; color: #d1d5db; font-size: 0.7rem; user-select: none; line-height: 1; }
	.drag-grip:hover { color: #9ca3af; }
	.list-item[draggable="true"] { cursor: default; }
	.list-item.dragging { opacity: 0.4; }

	/* Create from selection */
	.create-from-selection { padding: 10px; background: #f5f3fa; border: 1px solid #d4cfe6; border-radius: 8px; margin-bottom: 12px; display: flex; flex-direction: column; gap: 6px; }
	.create-form-header { display: flex; align-items: center; justify-content: space-between; }
	.create-form-label { font-size: 0.8rem; font-weight: 600; color: #7c6f9e; }
	.btn-cancel-create { background: none; border: none; cursor: pointer; font-size: 1rem; color: #9ca3af; padding: 0 4px; line-height: 1; }
	.btn-cancel-create:hover { color: #ef4444; }
	.pending-members { display: flex; flex-direction: column; gap: 4px; }
	.pending-member-card { display: flex; align-items: center; gap: 6px; padding: 4px 8px; background: white; border: 1px solid #e5e7eb; border-radius: 6px; }
	.pending-member-title { flex: 1; font-size: 0.8rem; font-weight: 500; color: #374151; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.btn-remove-pending { background: none; border: none; cursor: pointer; font-size: 0.85rem; font-weight: 700; color: #9ca3af; padding: 0 4px; line-height: 1; flex-shrink: 0; }
	.btn-remove-pending:hover { color: #ef4444; }
	.create-actions { display: flex; justify-content: flex-end; gap: 6px; padding-top: 4px; }

	/* Delete dialog */
	.dialog-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.4); display: flex; align-items: center; justify-content: center; z-index: 1001; }
	.dialog-content { background: white; border-radius: 8px; padding: 24px; min-width: 340px; box-shadow: 0 8px 30px rgba(0, 0, 0, 0.2); }
	.dialog-title { margin: 0 0 8px; font-size: 0.95rem; font-weight: 600; color: #111827; }
	.dialog-message { margin: 0 0 16px; font-size: 0.85rem; color: #6b7280; }
	.dialog-actions { display: flex; gap: 8px; justify-content: flex-end; }
	.btn-dialog { padding: 8px 14px; border-radius: 6px; border: 1px solid #d1d5db; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-dialog-cancel { background: white; color: #6b7280; }
	.btn-dialog-cancel:hover { background: #f3f4f6; }
	.btn-dialog-keep { background: #7c6f9e; color: white; border-color: #7c6f9e; }
	.btn-dialog-keep:hover { background: #685d87; }
	.btn-dialog-delete-all { background: #ef4444; color: white; border-color: #ef4444; }
	.btn-dialog-delete-all:hover { background: #dc2626; }
	.btn-icon-nav { width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; border: 1px solid #d1d5db; border-radius: 4px; background: white; cursor: pointer; color: #9ca3af; transition: all 0.15s; }
	.btn-icon-nav:hover { border-color: #9ca3af; color: #6b7280; background: #f3f4f6; }
</style>

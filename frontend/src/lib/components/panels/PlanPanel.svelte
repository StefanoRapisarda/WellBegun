<script lang="ts">
	import type { Tag, Plan, PlanItem, Activity } from '$lib/types';
	import { plans, loadPlans } from '$lib/stores/plans';
	import { activities, loadActivities } from '$lib/stores/activities';
	import { tags, loadTags, entityTagsVersion } from '$lib/stores/tags';
	import { dateFilter, isItemVisible, selectedFilterTags, isTagVisible, isEntitySourceOfFilterTag, showArchived, showActiveRelated, activeEntityTagIds, isActiveRelated } from '$lib/stores/dateFilter';
	import { setLastUsedTags } from '$lib/stores/lastUsedTags';
	import { deletePlan, activatePlan, deactivatePlan, archivePlan, updatePlan, addPlanItem, updatePlanItem, removePlanItem } from '$lib/api/plans';
	import { createActivity, updateActivity, deleteActivity } from '$lib/api/activities';
	import { getEntityTags, attachTag, detachTag, searchTags, createWildTag } from '$lib/api/tags';
	import PanelContainer from '../shared/PanelContainer.svelte';
	import PlanForm from '../forms/PlanForm.svelte';
	import TagInput from '../shared/TagInput.svelte';
	import TagBadge from '../shared/TagBadge.svelte';
	import Timestamp from '../shared/Timestamp.svelte';
	import { selectEntity } from '$lib/stores/selectedEntity';
	import { selectable } from '$lib/actions/selectable';

	// Panel-level tag filter state
	let panelSelectedTagIds = $state<number[]>([]);
	let panelFilterMode = $state<'or' | 'and'>('or');

	let availablePanelTags = $derived(() => {
		const tagMap = new Map<number, Tag>();
		for (const plan of $plans) {
			const planTags = entityTags[plan.id] || [];
			for (const tag of planTags) {
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

	let filteredPlans = $derived($plans.filter(p =>
		($showArchived || !p.is_archived) &&
		isItemVisible(p, $dateFilter) &&
		(isTagVisible(entityTags[p.id] || [], $selectedFilterTags) || isEntitySourceOfFilterTag('plan', p.id, $selectedFilterTags)) &&
		passesPanelFilter(entityTags[p.id] || []) &&
		(!$showActiveRelated || isActiveRelated(entityTags[p.id] || [], $activeEntityTagIds, p.is_active))
	));

	let showForm = $state(false);
	let editFieldsPlanId: number | null = $state(null);
	let editFields = $state<{
		title: string;
		description: string;
		motivation: string;
		outcome: string;
		startDate: string;
		endDate: string;
	}>({ title: '', description: '', motivation: '', outcome: '', startDate: '', endDate: '' });
	let confirmDelete: number | null = $state(null);
	let expandedId: number | null = $state(null);
	let entityTags = $state<Record<number, Tag[]>>({});
	let tagsExpandedId: number | null = $state(null);
	let editingNoteId: number | null = $state(null);
	let noteText = $state('');
	let inlineNewTitles = $state<Record<string, string>>({});
	let editingTitleItemId: number | null = $state(null);
	let editTitleText = $state('');
	let addingSectionPlanId: number | null = $state(null);
	let newSectionName = $state('');
	let editingSectionKey: string | null = $state(null);
	let editSectionText = $state('');
	let pendingSections = $state<Record<number, string[]>>({});

	// Drag-and-drop between sections
	let draggedItem = $state<{ planId: number; itemId: number; fromHeader: string | null } | null>(null);
	let dropTargetKey = $state<string | null>(null);

	function handleItemDragStart(planId: number, item: PlanItem, e: DragEvent) {
		draggedItem = { planId, itemId: item.id, fromHeader: item.header ?? null };
		if (e.dataTransfer) {
			e.dataTransfer.effectAllowed = 'move';
			e.dataTransfer.setData('text/plain', '');
		}
	}

	function handleSectionDragOver(planId: number, header: string | null, e: DragEvent) {
		if (!draggedItem || draggedItem.planId !== planId) return;
		e.preventDefault();
		if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
		dropTargetKey = sectionKey(planId, header);
	}

	function handleSectionDragLeave(e: DragEvent) {
		const currentTarget = e.currentTarget as HTMLElement;
		const relatedTarget = e.relatedTarget as HTMLElement | null;
		if (!relatedTarget || !currentTarget.contains(relatedTarget)) {
			dropTargetKey = null;
		}
	}

	async function handleSectionDrop(planId: number, header: string | null, e: DragEvent) {
		e.preventDefault();
		dropTargetKey = null;
		if (!draggedItem || draggedItem.planId !== planId) return;
		if ((draggedItem.fromHeader ?? null) === (header ?? null)) {
			draggedItem = null;
			return;
		}
		await updatePlanItem(draggedItem.itemId, { header: header });
		draggedItem = null;
		await loadPlans();
	}

	function handleDragEnd() {
		draggedItem = null;
		dropTargetKey = null;
	}

	function getDoneCount(plan: Plan): number {
		return plan.items.filter(i => i.is_done).length;
	}

	function getProgressPercent(plan: Plan): number {
		if (plan.items.length === 0) return 0;
		return Math.round((getDoneCount(plan) / plan.items.length) * 100);
	}

	function getActivity(activityId: number): Activity | undefined {
		return $activities.find(a => a.id === activityId);
	}

	function getActivityTitle(activityId: number): string {
		const activity = getActivity(activityId);
		return activity ? activity.title : `Activity #${activityId}`;
	}

	interface SectionGroup {
		header: string | null;
		items: PlanItem[];
	}

	function getGroupedItems(plan: Plan): SectionGroup[] {
		const sorted = [...plan.items].sort((a, b) => a.position - b.position);
		const groups: SectionGroup[] = [];
		const headerOrder: (string | null)[] = [];

		// Walk items in position order; collect unique headers preserving order
		for (const item of sorted) {
			const h = item.header ?? null;
			if (!headerOrder.includes(h)) {
				headerOrder.push(h);
			}
		}

		// Put null (ungrouped) first if it exists
		const orderedHeaders = [
			...(headerOrder.includes(null) ? [null] : []),
			...headerOrder.filter(h => h !== null)
		];

		// Include pending (empty) sections
		const pending = pendingSections[plan.id] ?? [];
		for (const p of pending) {
			if (!orderedHeaders.includes(p)) {
				orderedHeaders.push(p);
			}
		}

		for (const h of orderedHeaders) {
			groups.push({
				header: h,
				items: sorted.filter(i => (i.header ?? null) === h)
			});
		}

		// If no groups at all, add a null group so the inline create input shows
		if (groups.length === 0) {
			groups.push({ header: null, items: [] });
		}

		return groups;
	}

	function sectionKey(planId: number, header: string | null): string {
		return `${planId}:${header ?? '__ungrouped__'}`;
	}

	function getInlineTitle(planId: number, header: string | null): string {
		return inlineNewTitles[sectionKey(planId, header)] ?? '';
	}

	function setInlineTitle(planId: number, header: string | null, value: string) {
		inlineNewTitles[sectionKey(planId, header)] = value;
		inlineNewTitles = { ...inlineNewTitles };
	}

	// Plan-level handlers
	async function handleDelete(id: number, deleteActivities: boolean) {
		const plan = $plans.find(p => p.id === id);
		if (deleteActivities && plan) {
			for (const item of plan.items) {
				await deleteActivity(item.activity_id);
			}
		}
		await deletePlan(id);
		await Promise.all([loadPlans(), loadActivities(), loadTags()]);
		confirmDelete = null;
	}

	async function toggleActive(id: number, isActive: boolean) {
		if (isActive) { await deactivatePlan(id); } else { await activatePlan(id); }
		await loadPlans();
	}

	async function handleArchive(id: number) {
		await archivePlan(id);
		await loadPlans();
	}

	async function toggleTagsExpand(id: number) {
		if (tagsExpandedId === id) { tagsExpandedId = null; return; }
		tagsExpandedId = id;
		if (!entityTags[id]) {
			entityTags[id] = await getEntityTags('plan', id);
		}
	}

	async function toggleExpand(id: number) {
		if (expandedId === id) { expandedId = null; return; }
		expandedId = id;
		if (!entityTags[id]) {
			entityTags[id] = await getEntityTags('plan', id);
		}
	}

	async function handleAttach(planId: number, tag: Tag) {
		await attachTag(tag.id, 'plan', planId);
		entityTags[planId] = await getEntityTags('plan', planId);
		setLastUsedTags('plan', entityTags[planId]);
	}

	async function handleDetach(planId: number, tag: Tag) {
		await detachTag(tag.id, 'plan', planId);
		entityTags[planId] = await getEntityTags('plan', planId);
		setLastUsedTags('plan', entityTags[planId]);
	}

	// Inline field editing
	function startEditFields(plan: Plan) {
		editFieldsPlanId = plan.id;
		editFields = {
			title: plan.title,
			description: plan.description ?? '',
			motivation: plan.motivation ?? '',
			outcome: plan.outcome ?? '',
			startDate: plan.start_date ?? '',
			endDate: plan.end_date ?? ''
		};
	}

	async function saveEditFields() {
		if (!editFieldsPlanId || !editFields.title.trim()) return;
		await updatePlan(editFieldsPlanId, {
			title: editFields.title.trim(),
			description: editFields.description.trim() || undefined,
			motivation: editFields.motivation.trim() || undefined,
			outcome: editFields.outcome.trim() || undefined,
			start_date: editFields.startDate || undefined,
			end_date: editFields.endDate || undefined
		});
		editFieldsPlanId = null;
		await Promise.all([loadPlans(), loadTags()]);
	}

	// Activity creation
	async function handleInlineCreate(planId: number, header: string | null = null) {
		const title = getInlineTitle(planId, header);
		if (!title.trim()) return;
		const activity = await createActivity({ title: title.trim() });
		// Attach ToDo tag
		const todoResults = await searchTags('ToDo');
		const todoTag = todoResults.find(t => t.name.toLowerCase() === 'todo') ?? await createWildTag('ToDo', undefined, 'activity');
		await attachTag(todoTag.id, 'activity', activity.id);
		// Attach plan's entity tag
		const plan = $plans.find(p => p.id === planId);
		if (plan) {
			const planTagResults = await searchTags(plan.title);
			const planTag = planTagResults.find(t => t.entity_type === 'plan' && t.entity_id === planId);
			if (planTag) await attachTag(planTag.id, 'activity', activity.id);
		}
		const position = plan ? plan.items.length : 0;
		await addPlanItem(planId, { activity_id: activity.id, position, header: header ?? undefined });
		setInlineTitle(planId, header, '');
		if (header) removePendingSection(planId, header);
		await Promise.all([loadPlans(), loadActivities()]);
	}

	// Section CRUD
	function addPendingSection(planId: number, name: string) {
		const current = pendingSections[planId] ?? [];
		if (!current.includes(name)) {
			pendingSections = { ...pendingSections, [planId]: [...current, name] };
		}
	}

	function removePendingSection(planId: number, name: string) {
		const current = pendingSections[planId] ?? [];
		pendingSections = { ...pendingSections, [planId]: current.filter(s => s !== name) };
	}

	async function handleRenameSection(planId: number, oldHeader: string, newHeader: string) {
		if (!newHeader.trim() || newHeader === oldHeader) {
			editingSectionKey = null;
			return;
		}
		const plan = $plans.find(p => p.id === planId);
		if (!plan) return;
		const sectionItems = plan.items.filter(i => i.header === oldHeader);
		await Promise.all(sectionItems.map(i => updatePlanItem(i.id, { header: newHeader.trim() })));
		editingSectionKey = null;
		editSectionText = '';
		await loadPlans();
	}

	async function handleDeleteSection(planId: number, header: string) {
		const plan = $plans.find(p => p.id === planId);
		if (!plan) return;
		const sectionItems = plan.items.filter(i => i.header === header);
		await Promise.all(sectionItems.map(i => updatePlanItem(i.id, { header: null })));
		await loadPlans();
	}

	// Activity item handlers
	async function handleUpdateTitle(itemId: number, activityId: number) {
		if (!editTitleText.trim()) { editingTitleItemId = null; return; }
		await updateActivity(activityId, { title: editTitleText.trim() });
		editingTitleItemId = null;
		editTitleText = '';
		await loadActivities();
	}

	async function toggleDone(item: PlanItem) {
		const nowDone = !item.is_done;
		await updatePlanItem(item.id, { is_done: nowDone });
		const completedResults = await searchTags('Completed');
		const completedTag = completedResults.find(t => t.name.toLowerCase() === 'completed') ?? await createWildTag('Completed', undefined, 'activity');
		if (nowDone) {
			await attachTag(completedTag.id, 'activity', item.activity_id);
		} else {
			await detachTag(completedTag.id, 'activity', item.activity_id);
		}
		await Promise.all([loadPlans(), loadActivities()]);
	}

	async function handleRemoveItem(itemId: number, activityId: number) {
		await removePlanItem(itemId);
		await deleteActivity(activityId);
		await Promise.all([loadPlans(), loadActivities(), loadTags()]);
	}

	// Reorder
	async function moveItemUp(planId: number, item: PlanItem) {
		const plan = $plans.find(p => p.id === planId);
		if (!plan) return;
		const sorted = [...plan.items].sort((a, b) => a.position - b.position);
		const idx = sorted.findIndex(i => i.id === item.id);
		if (idx <= 0) return;
		await updatePlanItem(sorted[idx].id, { position: sorted[idx - 1].position });
		await updatePlanItem(sorted[idx - 1].id, { position: item.position });
		await loadPlans();
	}

	async function moveItemDown(planId: number, item: PlanItem) {
		const plan = $plans.find(p => p.id === planId);
		if (!plan) return;
		const sorted = [...plan.items].sort((a, b) => a.position - b.position);
		const idx = sorted.findIndex(i => i.id === item.id);
		if (idx >= sorted.length - 1) return;
		await updatePlanItem(sorted[idx].id, { position: sorted[idx + 1].position });
		await updatePlanItem(sorted[idx + 1].id, { position: item.position });
		await loadPlans();
	}

	async function saveNote(itemId: number) {
		await updatePlanItem(itemId, { notes: noteText || undefined });
		editingNoteId = null;
		noteText = '';
		await loadPlans();
	}

	// Tag loading
	async function loadAllTags() {
		const entries = await Promise.all(
			$plans.map(async (plan) => [plan.id, await getEntityTags('plan', plan.id)] as const)
		);
		const updated: Record<number, Tag[]> = {};
		for (const [id, tags] of entries) updated[id] = tags;
		entityTags = updated;
	}

	$effect(() => {
		const _ = $entityTagsVersion;
		if ($plans) loadAllTags();
	});
</script>

<PanelContainer
	title="Plans"
	panelId="plan"
	color="#6b8ba3"
	onAdd={() => (showForm = !showForm)}
	availableTags={availablePanelTags()}
	selectedTagIds={panelSelectedTagIds}
	filterMode={panelFilterMode}
	onTagToggle={handlePanelTagToggle}
	onModeToggle={handlePanelModeToggle}
>
	{#if showForm}
		<div class="inline-form">
			<PlanForm onDone={(createdId) => { showForm = false; if (createdId) expandedId = createdId; }} />
		</div>
	{/if}

	{#each filteredPlans as plan (plan.id)}
		<div class="item" class:is-archived={plan.is_archived} use:selectable={{ entityType: 'plan', entityId: plan.id }}>
			<div class="item-actions">
				<button class="btn-tags" onclick={() => toggleTagsExpand(plan.id)}>Tags</button>
				<button class="btn-active" class:active={plan.is_active} onclick={() => toggleActive(plan.id, plan.is_active)}>
					{plan.is_active ? 'Active' : 'Inactive'}
				</button>
				<button class="btn-archive" onclick={() => handleArchive(plan.id)}>Archive</button>
				<button class="btn-delete" onclick={() => (confirmDelete = plan.id)}>Delete</button>
			</div>
			<div class="item-card" ondblclick={() => selectEntity('plan', plan.id, plan.title)} role="button" tabindex="-1">
				{#if editFieldsPlanId === plan.id}
					<div class="edit-fields-section">
						<input type="text" class="title-input" bind:value={editFields.title} placeholder="Plan title..." />
						<textarea class="field-textarea" bind:value={editFields.description} rows="2" placeholder="Description (optional)"></textarea>
						<input type="text" class="field-input" bind:value={editFields.motivation} placeholder="Motivation (optional)" />
						<input type="text" class="field-input" bind:value={editFields.outcome} placeholder="Expected outcome (optional)" />
						<div class="date-row">
							<label class="date-label">Start <input type="date" bind:value={editFields.startDate} class="date-input" /></label>
							<label class="date-label">End <input type="date" bind:value={editFields.endDate} class="date-input" /></label>
						</div>
						<div class="edit-fields-actions">
							<button class="btn-cancel-edit" onclick={() => editFieldsPlanId = null}>Cancel</button>
							<button class="btn-save-edit" onclick={saveEditFields}>Save</button>
						</div>
					</div>
				{:else}
					<div class="item-header">
						<button class="item-title" ondblclick={(e) => { e.stopPropagation(); startEditFields(plan); }}>{plan.title}</button>
						{#if plan.is_archived}<span class="archived-badge">archived</span>{/if}
						<span class="item-count">{getDoneCount(plan)}/{plan.items.length}</span>
						<button class="btn-expand" onclick={() => toggleExpand(plan.id)}>
							{expandedId === plan.id ? 'Less' : 'More'}
						</button>
					</div>

					{#if plan.items.length > 0}
						<div class="progress-bar">
							<div class="progress-fill" style:width="{getProgressPercent(plan)}%"></div>
						</div>
					{/if}

					{#if entityTags[plan.id]?.length}
						<div class="tag-badges">
							{#each entityTags[plan.id] as tag (tag.id)}
								<TagBadge {tag} removable onRemove={() => handleDetach(plan.id, tag)} />
							{/each}
						</div>
					{/if}

					{#if plan.description}
						<p class="item-desc">{plan.description}</p>
					{/if}
				{/if}

					<!-- Activities grouped by section -->
					{#each getGroupedItems(plan) as group}
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<div
							class="section-drop-zone"
							class:drop-target={dropTargetKey === sectionKey(plan.id, group.header) && draggedItem?.fromHeader !== (group.header ?? null)}
							ondragover={(e) => handleSectionDragOver(plan.id, group.header, e)}
							ondragleave={handleSectionDragLeave}
							ondrop={(e) => handleSectionDrop(plan.id, group.header, e)}
						>
							{#if group.header !== null}
								<div class="section-header-bar">
									{#if editingSectionKey === sectionKey(plan.id, group.header)}
										<input
											type="text"
											class="edit-section-input"
											bind:value={editSectionText}
											onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleRenameSection(plan.id, group.header!, editSectionText); } else if (e.key === 'Escape') { editingSectionKey = null; } }}
											onblur={() => handleRenameSection(plan.id, group.header!, editSectionText)}
										/>
									{:else}
										<button class="section-header-name" onclick={() => { editingSectionKey = sectionKey(plan.id, group.header); editSectionText = group.header!; }}>{group.header}</button>
									{/if}
									<button class="btn-delete-section" onclick={() => handleDeleteSection(plan.id, group.header!)}>x</button>
								</div>
							{/if}
							<div class="items-list">
								{#each group.items as item (item.id)}
									<div
										class="list-item"
										class:done={item.is_done}
										class:dragging={draggedItem?.itemId === item.id}
										draggable="true"
										ondragstart={(e) => handleItemDragStart(plan.id, item, e)}
										ondragend={handleDragEnd}
									>
										<div class="list-item-row">
											<span class="drag-grip">⠿</span>
											<input type="checkbox" checked={item.is_done} onchange={() => toggleDone(item)} />
											{#if editingTitleItemId === item.id}
												<input
													type="text"
													class="edit-title-input"
													bind:value={editTitleText}
													onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleUpdateTitle(item.id, item.activity_id); } else if (e.key === 'Escape') { editingTitleItemId = null; } }}
													onblur={() => handleUpdateTitle(item.id, item.activity_id)}
												/>
											{:else}
												<button
													class="activity-title-btn"
													class:checked={item.is_done}
													onclick={() => { editingTitleItemId = item.id; editTitleText = getActivityTitle(item.activity_id); }}
												>{getActivityTitle(item.activity_id)}</button>
											{/if}
											<button class="btn-remove-item" onclick={() => handleRemoveItem(item.id, item.activity_id)}>-</button>
										</div>
									</div>
								{/each}
							</div>
							<div class="add-activity">
								<div class="inline-create">
									<input
										type="text"
										placeholder="New activity..."
										value={getInlineTitle(plan.id, group.header)}
										oninput={(e) => setInlineTitle(plan.id, group.header, e.currentTarget.value)}
										onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleInlineCreate(plan.id, group.header); } }}
										class="inline-create-input"
									/>
									<button class="btn-inline-create" onclick={() => handleInlineCreate(plan.id, group.header)}>+</button>
								</div>
							</div>
						</div>
					{/each}

					{#if addingSectionPlanId === plan.id}
						<div class="add-section-input">
							<input
								type="text"
								placeholder="Section name..."
								bind:value={newSectionName}
								onkeydown={(e) => {
									if (e.key === 'Enter') {
										e.preventDefault();
										if (newSectionName.trim()) {
											addPendingSection(plan.id, newSectionName.trim());
											addingSectionPlanId = null;
											newSectionName = '';
										}
									} else if (e.key === 'Escape') {
										addingSectionPlanId = null;
										newSectionName = '';
									}
								}}
								class="inline-create-input"
							/>
							<button class="btn-cancel-note" onclick={() => { addingSectionPlanId = null; newSectionName = ''; }}>Cancel</button>
						</div>
					{:else}
						<button class="btn-add-section" onclick={() => { addingSectionPlanId = plan.id; newSectionName = ''; }}>+ Section</button>
					{/if}

					<Timestamp date={plan.created_at} />
				</div>

				{#if tagsExpandedId === plan.id}
					<div class="tag-section">
						<TagInput
							attachedTags={entityTags[plan.id] || []}
							targetType="plan"
							targetId={plan.id}
							onAttach={(tag) => handleAttach(plan.id, tag)}
							onDetach={(tag) => handleDetach(plan.id, tag)}
							onClose={() => (tagsExpandedId = null)}
						/>
					</div>
				{/if}

				<!-- Expanded details -->
				{#if expandedId === plan.id}
					<div class="expanded-section">
						{#if plan.motivation || plan.outcome || plan.start_date || plan.end_date}
							<div class="plan-meta">
								{#if plan.motivation}<p class="meta-line"><strong>Motivation:</strong> {plan.motivation}</p>{/if}
								{#if plan.outcome}<p class="meta-line"><strong>Outcome:</strong> {plan.outcome}</p>{/if}
								{#if plan.start_date || plan.end_date}
									<p class="meta-line"><strong>Period:</strong> {plan.start_date ?? '?'} &mdash; {plan.end_date ?? '?'}</p>
								{/if}
							</div>
						{/if}

						<!-- Reorder + notes for each item -->
						<div class="items-detail-list">
							{#each [...plan.items].sort((a, b) => a.position - b.position) as item (item.id)}
								<div class="detail-item">
									<div class="detail-item-header">
										<div class="reorder-btns">
											<button class="btn-move" onclick={() => moveItemUp(plan.id, item)}>&#9650;</button>
											<button class="btn-move" onclick={() => moveItemDown(plan.id, item)}>&#9660;</button>
										</div>
										<span class="detail-item-title" class:checked={item.is_done}>{getActivityTitle(item.activity_id)}</span>
										<button class="btn-note" onclick={() => { editingNoteId = editingNoteId === item.id ? null : item.id; noteText = item.notes ?? ''; }}>
											Notes
										</button>
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
					</div>
				{/if}
		</div>
	{/each}

	{#if $plans.length === 0}
		<p class="empty">No plans yet.</p>
	{:else if filteredPlans.length === 0}
		<p class="empty">No plans match current filters.</p>
	{/if}
</PanelContainer>

{#if confirmDelete !== null}
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<div class="dialog-overlay" onclick={() => confirmDelete = null} onkeydown={(e) => e.key === 'Escape' && (confirmDelete = null)} role="dialog" tabindex="-1">
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<div class="dialog-content" onclick={(e) => e.stopPropagation()} role="document">
			<p class="dialog-title">Delete this plan?</p>
			<p class="dialog-message">Do you also want to delete all activities contained in this plan?</p>
			<div class="dialog-actions">
				<button class="btn-dialog btn-dialog-cancel" onclick={() => confirmDelete = null}>Cancel</button>
				<button class="btn-dialog btn-dialog-keep" onclick={() => confirmDelete && handleDelete(confirmDelete, false)}>Keep activities</button>
				<button class="btn-dialog btn-dialog-delete-all" onclick={() => confirmDelete && handleDelete(confirmDelete, true)}>Delete all</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.inline-form { padding: 10px; background: #f0f7fa; border: 1px solid #b3d9e6; border-radius: 8px; margin-bottom: 12px; }
	.item { padding: 12px 0; border-bottom: 1px solid #e5e7eb; }
	.item-actions { display: flex; gap: 6px; margin-bottom: 6px; }
	.item-card { padding: 10px 12px; background: #fafafa; border: 1px solid #e5e7eb; border-radius: 8px; }
	.item-header { display: flex; align-items: center; gap: 8px; }
	.item-title { flex: 1; background: none; border: none; cursor: pointer; font-weight: 500; font-size: 0.9rem; text-align: left; padding: 0; color: #111827; }
	.item-desc { font-size: 0.8rem; color: #6b7280; margin: 4px 0 0; white-space: pre-wrap; }
	.item-count { font-size: 0.7rem; padding: 2px 6px; background: #f0f7fa; border-radius: 4px; color: #4a90a4; font-weight: 600; }
	.btn-expand { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #f9fafb; color: #6b7280; }
	.btn-active { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #f3f4f6; color: #6b7280; }
	.btn-active.active { background: #dcfce7; color: #16a34a; border-color: #bbf7d0; }
	.btn-tags { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #f9fafb; color: #6b7280; }
	.btn-archive { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #fef3c7; color: #92400e; }
	.btn-delete { font-size: 0.75rem; padding: 2px 8px; background: #fee2e2; color: #ef4444; border: 1px solid #fecaca; border-radius: 4px; cursor: pointer; }
	.tag-badges { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
	.tag-section { margin-top: 8px; padding: 8px; background: #f9fafb; border-radius: 6px; }
	.empty { text-align: center; color: #9ca3af; font-size: 0.875rem; }
	.is-archived .item-card { opacity: 0.55; border-style: dashed; }
	.archived-badge { font-size: 0.55rem; padding: 1px 5px; background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; border-radius: 3px; text-transform: uppercase; letter-spacing: 0.3px; font-weight: 600; flex-shrink: 0; }

	.progress-bar { height: 4px; background: #e5e7eb; border-radius: 2px; margin-top: 6px; overflow: hidden; }
	.progress-fill { height: 100%; background: #4a90a4; border-radius: 2px; transition: width 0.3s ease; }

	/* Activity items */
	.items-list { display: flex; flex-direction: column; gap: 4px; margin-top: 6px; }
	.list-item { padding: 4px 8px; background: #fafafa; border: 1px solid #e5e7eb; border-radius: 6px; }
	.list-item.done { opacity: 0.6; }
	.list-item-row { display: flex; align-items: center; gap: 6px; }
	.activity-title-btn { flex: 1; background: none; border: none; cursor: pointer; font-size: 0.8rem; font-weight: 500; color: #374151; text-align: left; padding: 0; }
	.activity-title-btn.checked { text-decoration: line-through; color: #9ca3af; }
	.edit-title-input { flex: 1; padding: 2px 6px; border: 1px solid #4a90a4; border-radius: 4px; font-size: 0.8rem; font-weight: 500; color: #374151; outline: none; }
	.btn-remove-item { background: none; border: none; cursor: pointer; font-size: 1rem; font-weight: 700; color: #ef4444; padding: 0 4px; line-height: 1; }

	.add-activity { margin-top: 4px; }
	.inline-create { display: flex; gap: 4px; }
	.inline-create-input { flex: 1; padding: 4px 8px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.78rem; }
	.btn-inline-create { padding: 3px 8px; background: #4a90a4; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85rem; font-weight: 600; }

	/* Expanded details */
	.expanded-section { margin-top: 8px; padding: 8px; background: #f9fafb; border-radius: 6px; }
	.plan-meta { margin-bottom: 8px; padding: 6px 8px; background: white; border: 1px solid #e5e7eb; border-radius: 6px; }
	.meta-line { margin: 2px 0; font-size: 0.78rem; color: #4b5563; }
	.meta-line strong { color: #374151; }

	.items-detail-list { display: flex; flex-direction: column; gap: 4px; }
	.detail-item { background: white; border: 1px solid #e5e7eb; border-radius: 6px; padding: 6px 8px; }
	.detail-item-header { display: flex; align-items: center; gap: 6px; }
	.detail-item-title { flex: 1; font-size: 0.8rem; font-weight: 500; color: #374151; }
	.detail-item-title.checked { text-decoration: line-through; color: #9ca3af; }
	.reorder-btns { display: flex; flex-direction: column; gap: 0; }
	.btn-move { background: none; border: none; cursor: pointer; font-size: 0.6rem; padding: 0 2px; color: #9ca3af; line-height: 1; }
	.btn-move:hover { color: #374151; }
	.btn-note { font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #f9fafb; color: #6b7280; }
	.item-note { font-size: 0.75rem; color: #6b7280; margin: 4px 0 0 24px; font-style: italic; }
	.note-edit { margin-top: 4px; margin-left: 24px; }
	.note-edit textarea { width: 100%; padding: 4px 6px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.8rem; resize: vertical; }
	.note-actions { display: flex; gap: 4px; margin-top: 4px; }
	.btn-save-note { font-size: 0.7rem; padding: 2px 8px; background: #4a90a4; color: white; border: none; border-radius: 4px; cursor: pointer; }
	.btn-cancel-note { font-size: 0.7rem; padding: 2px 8px; background: white; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; }

	/* Section headers */
	.section-header-bar { display: flex; align-items: center; gap: 6px; margin-top: 8px; padding: 4px 8px; background: #eef3f7; border-radius: 4px; border-left: 3px solid #4a90a4; }
	.section-header-name { flex: 1; background: none; border: none; cursor: pointer; font-size: 0.78rem; font-weight: 600; color: #374151; text-align: left; padding: 0; }
	.edit-section-input { flex: 1; padding: 2px 6px; border: 1px solid #4a90a4; border-radius: 4px; font-size: 0.78rem; font-weight: 600; color: #374151; outline: none; }
	.btn-delete-section { background: none; border: none; cursor: pointer; font-size: 0.75rem; font-weight: 700; color: #9ca3af; padding: 0 4px; line-height: 1; }
	.btn-delete-section:hover { color: #ef4444; }
	.btn-add-section { display: block; margin-top: 6px; padding: 3px 10px; font-size: 0.72rem; background: #f0f7fa; color: #4a90a4; border: 1px dashed #b3d9e6; border-radius: 4px; cursor: pointer; font-weight: 500; }
	.btn-add-section:hover { background: #e0eef5; }
	.add-section-input { display: flex; gap: 4px; margin-top: 6px; }

	/* Inline edit fields */
	.edit-fields-section { display: flex; flex-direction: column; gap: 6px; padding: 4px 0; }
	.edit-fields-section .title-input { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.edit-fields-section .field-textarea { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; resize: vertical; font-family: inherit; }
	.edit-fields-section .field-input { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.edit-fields-section .date-row { display: flex; gap: 8px; }
	.edit-fields-section .date-label { display: flex; align-items: center; gap: 4px; font-size: 0.8rem; color: #6b7280; }
	.edit-fields-section .date-input { padding: 4px 6px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.8rem; }
	.edit-fields-actions { display: flex; justify-content: flex-end; gap: 6px; padding-top: 4px; }
	.btn-save-edit { padding: 6px 14px; background: #4a90a4; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-save-edit:hover { background: #3d7a8c; }
	.btn-cancel-edit { padding: 6px 14px; background: white; color: #6b7280; border: 1px solid #d1d5db; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-cancel-edit:hover { background: #f3f4f6; }

	/* Drag-and-drop */
	.section-drop-zone { border-radius: 6px; border: 2px solid transparent; transition: border-color 0.15s, background 0.15s; }
	.section-drop-zone.drop-target { border-color: #4a90a4; background: rgba(74, 144, 164, 0.06); }
	.drag-grip { cursor: grab; color: #d1d5db; font-size: 0.7rem; user-select: none; line-height: 1; }
	.drag-grip:hover { color: #9ca3af; }
	.list-item[draggable="true"] { cursor: default; }
	.list-item.dragging { opacity: 0.4; }

	/* Delete dialog */
	.dialog-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.4); display: flex; align-items: center; justify-content: center; z-index: 1001; }
	.dialog-content { background: white; border-radius: 8px; padding: 24px; min-width: 340px; box-shadow: 0 8px 30px rgba(0, 0, 0, 0.2); }
	.dialog-title { margin: 0 0 8px; font-size: 0.95rem; font-weight: 600; color: #111827; }
	.dialog-message { margin: 0 0 16px; font-size: 0.85rem; color: #6b7280; }
	.dialog-actions { display: flex; gap: 8px; justify-content: flex-end; }
	.btn-dialog { padding: 8px 14px; border-radius: 6px; border: 1px solid #d1d5db; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-dialog-cancel { background: white; color: #6b7280; }
	.btn-dialog-cancel:hover { background: #f3f4f6; }
	.btn-dialog-keep { background: #4a90a4; color: white; border-color: #4a90a4; }
	.btn-dialog-keep:hover { background: #3d7a8c; }
	.btn-dialog-delete-all { background: #ef4444; color: white; border-color: #ef4444; }
	.btn-dialog-delete-all:hover { background: #dc2626; }
</style>

<script lang="ts">
	import type { Tag, Plan, Activity, Source, Actor } from '$lib/types';
	import { plans, loadPlans } from '$lib/stores/plans';
	import { activities, loadActivities } from '$lib/stores/activities';
	import { tags, loadTags, entityTagsVersion } from '$lib/stores/tags';
	import { loadNotes } from '$lib/stores/notes';
	import { sources, loadSources } from '$lib/stores/sources';
	import { actors as actorStore, loadActors } from '$lib/stores/actors';
	import { loadCollections } from '$lib/stores/collections';
	import { loadTriples } from '$lib/stores/knowledgeGraph';
	import { dateFilter, isItemVisible, selectedFilterTags, isTagVisible, isEntitySourceOfFilterTag, showArchived, showActiveRelated, activeEntityTagIds, isActiveRelated } from '$lib/stores/dateFilter';
	import { setLastUsedTags } from '$lib/stores/lastUsedTags';
	import { deletePlan, activatePlan, deactivatePlan, archivePlan, updatePlan, addPlanRoleNote, removePlanRoleNote, addPlanSource, removePlanSource, addPlanActor, removePlanActor, getPlanCollections, createTypedPlanCollection } from '$lib/api/plans';
	import type { PlanCollectionInfo } from '$lib/api/plans';
	import { getTriplesForEntity } from '$lib/api/knowledge';
	import { getNote, updateNote } from '$lib/api/notes';
	import { getSource, createSource } from '$lib/api/sources';
	import { getActor, createActor } from '$lib/api/actors';
	import { getCollection } from '$lib/api/collections';
	import { PLAN_NOTE_PREDICATES } from '$lib/stores/planning';
	import { createActivity, updateActivity, deleteActivity } from '$lib/api/activities';
	import { getEntityTags, attachTag, detachTag, searchTags, createWildTag } from '$lib/api/tags';
	import PanelContainer from '../shared/PanelContainer.svelte';
	import PlanForm from '../forms/PlanForm.svelte';
	import TagInput from '../shared/TagInput.svelte';
	import TagBadge from '../shared/TagBadge.svelte';
	import Timestamp from '../shared/Timestamp.svelte';
	import { selectEntity } from '$lib/stores/selectedEntity';
	import { selectable } from '$lib/actions/selectable';


	const PLAN_STATUS_CYCLE = ['planned', 'in_progress', 'done', 'on_hold', 'cancelled'];

	async function cyclePlanStatus(plan: Plan) {
		const idx = PLAN_STATUS_CYCLE.indexOf(plan.status);
		const next = PLAN_STATUS_CYCLE[(idx + 1) % PLAN_STATUS_CYCLE.length];
		await updatePlan(plan.id, { status: next });
		await loadPlans();
	}

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

	// Linked notes: planId → role → array of { id, content }
	let planLinkedNotes = $state<Record<number, Record<string, { id: number; content: string }[]>>>({});

	const ROLE_LABELS: Record<string, string> = {
		motivation: 'Motivation',
		goal: 'Goal',
		outcome: 'Outcome'
	};
	const ROLE_KEYS = ['motivation', 'goal', 'outcome'] as const;

	// Inline add inputs for role notes: keyed by `{planId}:{role}`
	let roleNoteInputs = $state<Record<string, string>>({});
	// Inline editing for role notes
	let editingRoleNoteId: number | null = $state(null);
	let editingRoleNoteText = $state('');

	function getRoleNoteInput(planId: number, role: string): string {
		return roleNoteInputs[`${planId}:${role}`] ?? '';
	}
	function setRoleNoteInput(planId: number, role: string, value: string) {
		roleNoteInputs = { ...roleNoteInputs, [`${planId}:${role}`]: value };
	}

	async function loadLinkedEntities(planId: number) {
		const triples = await getTriplesForEntity('plan', planId);
		const linkedNotes: Record<string, { id: number; content: string }[]> = {
			motivation: [], goal: [], outcome: []
		};
		const linkedSources: { source: Source; sourceId: number }[] = [];
		const linkedActors: { actor: Actor; actorId: number }[] = [];

		for (const t of triples) {
			if (t.subject_type === 'plan' && t.subject_id === planId) {
				// Notes (role notes — still triple-based)
				if (t.object_type === 'note') {
					for (const [role, predicate] of Object.entries(PLAN_NOTE_PREDICATES)) {
						if (t.predicate === predicate) {
							try {
								const note = await getNote(t.object_id);
								if (note.content) {
									linkedNotes[role].push({ id: note.id, content: note.content });
								}
							} catch {
								// Note may have been deleted
							}
						}
					}
				}
				// Collections — extract members by type
				if (t.object_type === 'collection') {
					try {
						const coll = await getCollection(t.object_id);
						for (const item of coll.items ?? []) {
							if (item.member_entity_type === 'source') {
								try {
									const source = await getSource(item.member_entity_id);
									linkedSources.push({ source, sourceId: source.id });
								} catch { /* deleted */ }
							} else if (item.member_entity_type === 'actor') {
								try {
									const actor = await getActor(item.member_entity_id);
									linkedActors.push({ actor, actorId: actor.id });
								} catch { /* deleted */ }
							}
						}
					} catch { /* collection deleted */ }
				}
			}
		}
		planLinkedNotes = { ...planLinkedNotes, [planId]: linkedNotes };
		planLinkedSources = { ...planLinkedSources, [planId]: linkedSources };
		planLinkedActors = { ...planLinkedActors, [planId]: linkedActors };

		// Load collections
		try {
			const colls = await getPlanCollections(planId);
			planCollections = { ...planCollections, [planId]: colls };
		} catch {
			planCollections = { ...planCollections, [planId]: [] };
		}
	}

	async function handleAddRoleNote(planId: number, role: string) {
		const content = getRoleNoteInput(planId, role);
		if (!content.trim()) return;
		await addPlanRoleNote(planId, { role, content: content.trim() });
		setRoleNoteInput(planId, role, '');
		await Promise.all([loadLinkedEntities(planId), loadNotes()]);
	}

	async function handleRemoveRoleNote(planId: number, noteId: number) {
		await removePlanRoleNote(planId, noteId);
		await Promise.all([loadLinkedEntities(planId), loadNotes()]);
	}

	async function handleEditRoleNote(noteId: number, content: string) {
		if (!content.trim()) { editingRoleNoteId = null; return; }
		await updateNote(noteId, { content: content.trim() });
		editingRoleNoteId = null;
		editingRoleNoteText = '';
		if (expandedId) await loadLinkedEntities(expandedId);
	}

	let showForm = $state(false);
	// Inline editing for plan title/desc in expanded view
	let editingPlanField: 'title' | 'desc' | 'goal' | 'motivation' | 'outcome' | null = $state(null);
	let editPlanFieldText = $state('');
	// Editable date fields
	let editDates = $state<{ start: string; end: string }>({ start: '', end: '' });
	// Linked sources/actors per plan (with entity ID for unlinking via collection)
	let planLinkedSources = $state<Record<number, { source: Source; sourceId: number }[]>>({});
	let planLinkedActors = $state<Record<number, { actor: Actor; actorId: number }[]>>({});
	// Input fields for adding sources/actors
	let newSourceInput = $state<Record<string, string>>({});
	let newActorInput = $state<Record<string, string>>({});
	// Collection-based state
	let planCollections = $state<Record<number, PlanCollectionInfo[]>>({});
	let addingCollectionType = $state<{ planId: number; memberType: string } | null>(null);
	let newCollectionName = $state('');
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
	let draggedItem = $state<{ planId: number; activityId: number; fromHeader: string | null } | null>(null);
	let dropTargetKey = $state<string | null>(null);

	function handleItemDragStart(planId: number, activity: Activity, e: DragEvent) {
		draggedItem = { planId, activityId: activity.id, fromHeader: activity.header ?? null };
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
		await updateActivity(draggedItem.activityId, { header: header });
		draggedItem = null;
		await loadPlans();
	}

	function handleDragEnd() {
		draggedItem = null;
		dropTargetKey = null;
	}

	function getDoneCount(plan: Plan): number {
		return plan.activities.filter(a => a.status === 'done').length;
	}

	function getProgressPercent(plan: Plan): number {
		if (plan.activities.length === 0) return 0;
		return Math.round((getDoneCount(plan) / plan.activities.length) * 100);
	}

	interface SectionGroup {
		header: string | null;
		activities: Activity[];
	}

	function getGroupedItems(plan: Plan): SectionGroup[] {
		const sorted = [...plan.activities].sort((a, b) => a.position - b.position);
		const groups: SectionGroup[] = [];
		const headerOrder: (string | null)[] = [];

		// Walk items in position order; collect unique headers preserving order
		for (const activity of sorted) {
			const h = activity.header ?? null;
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
				activities: sorted.filter(a => (a.header ?? null) === h)
			});
		}

		// If no groups at all, add a null group so the inline create input shows
		if (groups.length === 0) {
			groups.push({ header: null, activities: [] });
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
	async function handleDelete(id: number, cascade: boolean) {
		await deletePlan(id, cascade);
		if (cascade) {
			// Cascade deletes notes, sources, actors, collections, triples — refresh all
			await Promise.all([
				loadPlans(), loadActivities(), loadTags(),
				loadNotes(), loadSources(), loadActors(),
				loadCollections(), loadTriples()
			]);
		} else {
			await Promise.all([loadPlans(), loadActivities(), loadTags()]);
		}
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
		const plan = $plans.find(p => p.id === id);
		if (plan) {
			editDates = { start: plan.start_date ?? '', end: plan.end_date ?? '' };
		}
		await loadLinkedEntities(id);
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

	// Inline field editing (expanded view)
	async function handleSavePlanField(planId: number, field: 'title' | 'desc' | 'goal' | 'motivation' | 'outcome') {
		const keyMap: Record<string, string> = { title: 'title', desc: 'description', goal: 'goal', motivation: 'motivation', outcome: 'outcome' };
		const key = keyMap[field];
		const value = editPlanFieldText.trim();
		if (field === 'title' && !value) { editingPlanField = null; return; }
		await updatePlan(planId, { [key]: value || null });
		editingPlanField = null;
		editPlanFieldText = '';
		await Promise.all([loadPlans(), loadTags()]);
	}

	async function handleSaveDates(planId: number) {
		await updatePlan(planId, {
			start_date: editDates.start || undefined,
			end_date: editDates.end || undefined
		});
		await loadPlans();
	}

	// Linked sources CRUD
	async function handleAddSource(planId: number) {
		const title = (newSourceInput[planId] ?? '').trim();
		if (!title) return;

		// Check if already linked
		const linked = planLinkedSources[planId] || [];
		const existing = $sources.find(s => s.title.toLowerCase() === title.toLowerCase());
		if (existing && linked.some(ls => ls.source.id === existing.id)) {
			newSourceInput = { ...newSourceInput, [planId]: '' };
			return;
		}

		const sourceId = existing ? existing.id : (await createSource({ title })).id;
		if (!existing) await loadSources();

		await addPlanSource(planId, sourceId);
		newSourceInput = { ...newSourceInput, [planId]: '' };
		await loadLinkedEntities(planId);
	}

	async function handleRemoveSource(planId: number, sourceId: number) {
		await removePlanSource(planId, sourceId);
		await loadLinkedEntities(planId);
	}

	// Linked actors CRUD
	async function handleAddActor(planId: number) {
		const name = (newActorInput[planId] ?? '').trim();
		if (!name) return;

		const linked = planLinkedActors[planId] || [];
		const existing = $actorStore.find(a => a.full_name.toLowerCase() === name.toLowerCase());
		if (existing && linked.some(la => la.actor.id === existing.id)) {
			newActorInput = { ...newActorInput, [planId]: '' };
			return;
		}

		const actorId = existing ? existing.id : (await createActor({ full_name: name })).id;
		if (!existing) await loadActors();

		await addPlanActor(planId, actorId);
		newActorInput = { ...newActorInput, [planId]: '' };
		await loadLinkedEntities(planId);
	}

	async function handleRemoveActor(planId: number, actorId: number) {
		await removePlanActor(planId, actorId);
		await loadLinkedEntities(planId);
	}

	// Collection-based helpers
	function getCollectionsByType(planId: number, predicatePrefix: string): PlanCollectionInfo[] {
		const colls = planCollections[planId] || [];
		return colls.filter(c => c.predicate === predicatePrefix || c.predicate.startsWith(predicatePrefix + ':'));
	}

	function isDefaultCollection(predicate: string): boolean {
		return predicate === 'has activities' || predicate === 'has sources' || predicate === 'has actors';
	}

	function getCollectionDisplayTitle(coll: PlanCollectionInfo): string {
		if (isDefaultCollection(coll.predicate)) return '';
		// Extract the user-given title from the predicate suffix
		return coll.title;
	}

	async function handleCreateTypedCollection(planId: number, memberType: string) {
		const name = newCollectionName.trim();
		if (!name) return;
		await createTypedPlanCollection(planId, { title: name, member_type: memberType });
		addingCollectionType = null;
		newCollectionName = '';
		await loadLinkedEntities(planId);
	}

	async function handleAddSourceToCollection(planId: number, collectionId: number) {
		const title = (newSourceInput[`${planId}:${collectionId}`] ?? '').trim();
		if (!title) return;

		const existing = $sources.find(s => s.title.toLowerCase() === title.toLowerCase());
		const sourceId = existing ? existing.id : (await createSource({ title })).id;
		if (!existing) await loadSources();

		await addPlanSource(planId, sourceId, collectionId);
		newSourceInput = { ...newSourceInput, [`${planId}:${collectionId}`]: '' };
		await loadLinkedEntities(planId);
	}

	async function handleAddActorToCollection(planId: number, collectionId: number) {
		const name = (newActorInput[`${planId}:${collectionId}`] ?? '').trim();
		if (!name) return;

		const existing = $actorStore.find(a => a.full_name.toLowerCase() === name.toLowerCase());
		const actorId = existing ? existing.id : (await createActor({ full_name: name })).id;
		if (!existing) await loadActors();

		await addPlanActor(planId, actorId, collectionId);
		newActorInput = { ...newActorInput, [`${planId}:${collectionId}`]: '' };
		await loadLinkedEntities(planId);
	}

	// Activity creation — directly with plan_id
	async function handleInlineCreate(planId: number, header: string | null = null) {
		const title = getInlineTitle(planId, header);
		if (!title.trim()) return;
		const plan = $plans.find(p => p.id === planId);
		const position = plan ? plan.activities.length : 0;
		await createActivity({
			title: title.trim(),
			plan_id: planId,
			position,
			header: header ?? undefined,
			status: 'todo'
		});
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
		const sectionActivities = plan.activities.filter(a => a.header === oldHeader);
		await Promise.all(sectionActivities.map(a => updateActivity(a.id, { header: newHeader.trim() })));
		editingSectionKey = null;
		editSectionText = '';
		await loadPlans();
	}

	async function handleDeleteSection(planId: number, header: string) {
		const plan = $plans.find(p => p.id === planId);
		if (!plan) return;
		const sectionActivities = plan.activities.filter(a => a.header === header);
		await Promise.all(sectionActivities.map(a => updateActivity(a.id, { header: null })));
		await loadPlans();
	}

	// Activity item handlers
	async function handleUpdateTitle(activityId: number) {
		if (!editTitleText.trim()) { editingTitleItemId = null; return; }
		await updateActivity(activityId, { title: editTitleText.trim() });
		editingTitleItemId = null;
		editTitleText = '';
		await Promise.all([loadPlans(), loadActivities()]);
	}

	async function toggleDone(activity: Activity) {
		const newStatus = activity.status === 'done' ? 'todo' : 'done';
		await updateActivity(activity.id, { status: newStatus });
		await Promise.all([loadPlans(), loadActivities()]);
	}

	async function handleRemoveItem(activityId: number) {
		await deleteActivity(activityId);
		await Promise.all([loadPlans(), loadActivities(), loadTags()]);
	}

	// Reorder
	async function moveItemUp(planId: number, activity: Activity) {
		const plan = $plans.find(p => p.id === planId);
		if (!plan) return;
		const sorted = [...plan.activities].sort((a, b) => a.position - b.position);
		const idx = sorted.findIndex(a => a.id === activity.id);
		if (idx <= 0) return;
		await updateActivity(sorted[idx].id, { position: sorted[idx - 1].position });
		await updateActivity(sorted[idx - 1].id, { position: activity.position });
		await loadPlans();
	}

	async function moveItemDown(planId: number, activity: Activity) {
		const plan = $plans.find(p => p.id === planId);
		if (!plan) return;
		const sorted = [...plan.activities].sort((a, b) => a.position - b.position);
		const idx = sorted.findIndex(a => a.id === activity.id);
		if (idx >= sorted.length - 1) return;
		await updateActivity(sorted[idx].id, { position: sorted[idx + 1].position });
		await updateActivity(sorted[idx + 1].id, { position: activity.position });
		await loadPlans();
	}

	async function saveNote(activityId: number) {
		await updateActivity(activityId, { description: noteText || undefined });
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
			<div class="item-card" ondblclick={() => selectEntity('plan', plan.id, plan.title)} role="button" tabindex="-1">
				<div class="item-header">
					<span class="item-title">{plan.title}</span>
					{#if plan.is_archived}<span class="archived-badge">archived</span>{/if}
					{#if plan.status}
						<button class="status-btn" class:status-planned={plan.status === 'planned'} class:status-done={plan.status === 'done'} class:status-in-progress={plan.status === 'in_progress'} class:status-on-hold={plan.status === 'on_hold'} class:status-cancelled={plan.status === 'cancelled'} onclick={(e) => { e.stopPropagation(); cyclePlanStatus(plan); }}>{plan.status.replace('_', ' ')}</button>
					{/if}
					<span class="item-count">{getDoneCount(plan)}/{plan.activities.length}</span>
					<button class="btn-expand" onclick={() => toggleExpand(plan.id)}>
						{expandedId === plan.id ? 'Less' : 'More'}
					</button>
				</div>

				{#if plan.activities.length > 0}
					<div class="progress-bar">
						<div class="progress-fill" style:width="{getProgressPercent(plan)}%"></div>
					</div>
				{/if}

				{#if plan.goal || plan.motivation || plan.outcome}
					<div class="plan-summary">
						{#if plan.goal}<div class="summary-item"><span class="summary-label">Goal</span> {plan.goal}</div>{/if}
						{#if plan.motivation}<div class="summary-item"><span class="summary-label">Motivation</span> {plan.motivation}</div>{/if}
						{#if plan.outcome}<div class="summary-item"><span class="summary-label">Outcome</span> {plan.outcome}</div>{/if}
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

				<Timestamp date={plan.created_at} />
			</div>

			<!-- Expanded working view -->
			{#if expandedId === plan.id}
				{@const linked = planLinkedNotes[plan.id] || { motivation: [], goal: [], outcome: [] }}
				{@const linkedSources = planLinkedSources[plan.id] || []}
				{@const linkedActors = planLinkedActors[plan.id] || []}
				<div class="expanded-section">
					<!-- Inline title edit -->
					{#if editingPlanField === 'title'}
						<input
							type="text"
							class="editable-field-input"
							bind:value={editPlanFieldText}
							onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleSavePlanField(plan.id, 'title'); } else if (e.key === 'Escape') { editingPlanField = null; } }}
							onblur={() => handleSavePlanField(plan.id, 'title')}
						/>
					{:else}
						<button class="editable-field" onclick={() => { editingPlanField = 'title'; editPlanFieldText = plan.title; }}>{plan.title}</button>
					{/if}

					<!-- Inline description edit -->
					{#if editingPlanField === 'desc'}
						<textarea
							class="editable-field-textarea"
							bind:value={editPlanFieldText}
							rows="3"
							onkeydown={(e) => { if (e.key === 'Escape') { editingPlanField = null; } }}
							onblur={() => handleSavePlanField(plan.id, 'desc')}
						></textarea>
					{:else}
						<button class="editable-field editable-desc" onclick={() => { editingPlanField = 'desc'; editPlanFieldText = plan.description ?? ''; }}>{plan.description || 'Add description...'}</button>
					{/if}

					<!-- Editable model fields: goal, motivation, outcome -->
					{#each ['goal', 'motivation', 'outcome'] as field}
						<div class="model-field-row">
							<span class="model-field-label">{field.charAt(0).toUpperCase() + field.slice(1)}</span>
							{#if editingPlanField === field}
								<input
									type="text"
									class="editable-field-input model-field-input"
									bind:value={editPlanFieldText}
									onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleSavePlanField(plan.id, field as 'goal' | 'motivation' | 'outcome'); } else if (e.key === 'Escape') { editingPlanField = null; } }}
									onblur={() => handleSavePlanField(plan.id, field as 'goal' | 'motivation' | 'outcome')}
								/>
							{:else}
								<button class="editable-field model-field-value" onclick={() => { editingPlanField = field as 'goal' | 'motivation' | 'outcome'; editPlanFieldText = (plan as any)[field] ?? ''; }}>
									{(plan as any)[field] || `Add ${field}...`}
								</button>
							{/if}
						</div>
					{/each}

					<!-- Dates -->
					<div class="expanded-dates">
						<label class="date-label">Start <input type="date" bind:value={editDates.start} onchange={() => handleSaveDates(plan.id)} class="date-input" /></label>
						<label class="date-label">End <input type="date" bind:value={editDates.end} onchange={() => handleSaveDates(plan.id)} class="date-input" /></label>
					</div>

					<!-- Role note sections -->
					{#each ROLE_KEYS as role}
						<div class="role-section">
							<div class="role-section-header">{ROLE_LABELS[role]}</div>
							<div class="role-notes-list">
								{#each linked[role] || [] as rNote (rNote.id)}
									<div class="role-note-item">
										{#if editingRoleNoteId === rNote.id}
											<input
												type="text"
												class="role-note-edit-input"
												bind:value={editingRoleNoteText}
												onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleEditRoleNote(rNote.id, editingRoleNoteText); } else if (e.key === 'Escape') { editingRoleNoteId = null; } }}
												onblur={() => handleEditRoleNote(rNote.id, editingRoleNoteText)}
											/>
										{:else}
											<button class="role-note-content" onclick={() => { editingRoleNoteId = rNote.id; editingRoleNoteText = rNote.content; }}>{rNote.content}</button>
										{/if}
										<button class="btn-remove-item" onclick={() => handleRemoveRoleNote(plan.id, rNote.id)}>-</button>
									</div>
								{/each}
							</div>
							<div class="role-note-add">
								<input
									type="text"
									class="inline-create-input"
									placeholder="Add {ROLE_LABELS[role].toLowerCase()}..."
									value={getRoleNoteInput(plan.id, role)}
									oninput={(e) => setRoleNoteInput(plan.id, role, e.currentTarget.value)}
									onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddRoleNote(plan.id, role); } }}
								/>
								<button class="btn-inline-create" onclick={() => handleAddRoleNote(plan.id, role)}>+</button>
							</div>
						</div>
					{/each}

					<!-- Activities -->
					<div class="activities-section-header">Activities</div>
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
								{#each group.activities as activity (activity.id)}
									<div
										class="list-item"
										class:done={activity.status === 'done'}
										class:dragging={draggedItem?.activityId === activity.id}
										draggable="true"
										ondragstart={(e) => handleItemDragStart(plan.id, activity, e)}
										ondragend={handleDragEnd}
									>
										<div class="list-item-row">
											<span class="drag-grip">⠿</span>
											<input type="checkbox" checked={activity.status === 'done'} onchange={() => toggleDone(activity)} />
											{#if editingTitleItemId === activity.id}
												<input
													type="text"
													class="edit-title-input"
													bind:value={editTitleText}
													onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleUpdateTitle(activity.id); } else if (e.key === 'Escape') { editingTitleItemId = null; } }}
													onblur={() => handleUpdateTitle(activity.id)}
												/>
											{:else}
												<button
													class="activity-title-btn"
													class:checked={activity.status === 'done'}
													onclick={() => { editingTitleItemId = activity.id; editTitleText = activity.title; }}
												>{activity.title}</button>
											{/if}
											<div class="reorder-btns">
												<button class="btn-move" onclick={() => moveItemUp(plan.id, activity)}>&#9650;</button>
												<button class="btn-move" onclick={() => moveItemDown(plan.id, activity)}>&#9660;</button>
											</div>
											<button class="btn-note" onclick={() => { editingNoteId = editingNoteId === activity.id ? null : activity.id; noteText = activity.description ?? ''; }}>
												Notes
											</button>
											<button class="btn-remove-item" onclick={() => handleRemoveItem(activity.id)}>-</button>
										</div>
										{#if activity.description && editingNoteId !== activity.id}
											<p class="item-note">{activity.description}</p>
										{/if}
										{#if editingNoteId === activity.id}
											<div class="note-edit">
												<textarea bind:value={noteText} rows="2" placeholder="Add notes..."></textarea>
												<div class="note-actions">
													<button class="btn-save-note" onclick={() => saveNote(activity.id)}>Save</button>
													<button class="btn-cancel-note" onclick={() => { editingNoteId = null; }}>Cancel</button>
												</div>
											</div>
										{/if}
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

					<!-- Source collections -->
					<div class="linked-section-group">
						<div class="linked-section-group-header">Sources</div>
						{#each getCollectionsByType(plan.id, 'has sources') as coll (coll.collection_id)}
							<div class="linked-section">
								{#if !isDefaultCollection(coll.predicate)}
									<div class="collection-sub-header">{getCollectionDisplayTitle(coll)}</div>
								{/if}
								{#each coll.items as item (item.item_id)}
									{@const src = linkedSources.find(ls => ls.sourceId === item.member_entity_id)}
									{#if src}
										<div class="linked-item-row">
											<span class="linked-item-text">{src.source.title}</span>
											<button class="btn-remove-item" onclick={() => handleRemoveSource(plan.id, src.sourceId)}>-</button>
										</div>
									{/if}
								{:else}
									<p class="linked-empty">No items</p>
								{/each}
								<div class="inline-create">
									<input
										type="text"
										placeholder="Link source..."
										value={newSourceInput[`${plan.id}:${coll.collection_id}`] ?? ''}
										oninput={(e) => { newSourceInput = { ...newSourceInput, [`${plan.id}:${coll.collection_id}`]: e.currentTarget.value }; }}
										onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddSourceToCollection(plan.id, coll.collection_id); } }}
										class="inline-create-input"
									/>
									<button class="btn-inline-create" onclick={() => handleAddSourceToCollection(plan.id, coll.collection_id)}>+</button>
								</div>
							</div>
						{:else}
							<!-- Fallback: flat source list when no collections loaded yet -->
							<div class="linked-section">
								{#each linkedSources as ls (ls.sourceId)}
									<div class="linked-item-row">
										<span class="linked-item-text">{ls.source.title}</span>
										<button class="btn-remove-item" onclick={() => handleRemoveSource(plan.id, ls.sourceId)}>-</button>
									</div>
								{:else}
									<p class="linked-empty">No linked sources</p>
								{/each}
								<div class="inline-create">
									<input
										type="text"
										placeholder="Link source..."
										value={newSourceInput[plan.id] ?? ''}
										oninput={(e) => { newSourceInput = { ...newSourceInput, [plan.id]: e.currentTarget.value }; }}
										onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddSource(plan.id); } }}
										class="inline-create-input"
									/>
									<button class="btn-inline-create" onclick={() => handleAddSource(plan.id)}>+</button>
								</div>
							</div>
						{/each}
						{#if addingCollectionType?.planId === plan.id && addingCollectionType?.memberType === 'source'}
							<div class="add-section-input">
								<input
									type="text"
									placeholder="Collection name..."
									bind:value={newCollectionName}
									onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleCreateTypedCollection(plan.id, 'source'); } else if (e.key === 'Escape') { addingCollectionType = null; newCollectionName = ''; } }}
									class="inline-create-input"
								/>
								<button class="btn-cancel-note" onclick={() => { addingCollectionType = null; newCollectionName = ''; }}>Cancel</button>
							</div>
						{:else}
							<button class="btn-add-section" onclick={() => { addingCollectionType = { planId: plan.id, memberType: 'source' }; newCollectionName = ''; }}>+ Collection</button>
						{/if}
					</div>

					<!-- Actor collections -->
					<div class="linked-section-group">
						<div class="linked-section-group-header">Actors</div>
						{#each getCollectionsByType(plan.id, 'has actors') as coll (coll.collection_id)}
							<div class="linked-section">
								{#if !isDefaultCollection(coll.predicate)}
									<div class="collection-sub-header">{getCollectionDisplayTitle(coll)}</div>
								{/if}
								{#each coll.items as item (item.item_id)}
									{@const act = linkedActors.find(la => la.actorId === item.member_entity_id)}
									{#if act}
										<div class="linked-item-row">
											<span class="linked-item-text">{act.actor.full_name}{#if act.actor.role} &mdash; {act.actor.role}{/if}</span>
											<button class="btn-remove-item" onclick={() => handleRemoveActor(plan.id, act.actorId)}>-</button>
										</div>
									{/if}
								{:else}
									<p class="linked-empty">No items</p>
								{/each}
								<div class="inline-create">
									<input
										type="text"
										placeholder="Link actor..."
										value={newActorInput[`${plan.id}:${coll.collection_id}`] ?? ''}
										oninput={(e) => { newActorInput = { ...newActorInput, [`${plan.id}:${coll.collection_id}`]: e.currentTarget.value }; }}
										onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddActorToCollection(plan.id, coll.collection_id); } }}
										class="inline-create-input"
									/>
									<button class="btn-inline-create" onclick={() => handleAddActorToCollection(plan.id, coll.collection_id)}>+</button>
								</div>
							</div>
						{:else}
							<!-- Fallback: flat actor list when no collections loaded yet -->
							<div class="linked-section">
								{#each linkedActors as la (la.actorId)}
									<div class="linked-item-row">
										<span class="linked-item-text">{la.actor.full_name}{#if la.actor.role} &mdash; {la.actor.role}{/if}</span>
										<button class="btn-remove-item" onclick={() => handleRemoveActor(plan.id, la.actorId)}>-</button>
									</div>
								{:else}
									<p class="linked-empty">No linked actors</p>
								{/each}
								<div class="inline-create">
									<input
										type="text"
										placeholder="Link actor..."
										value={newActorInput[plan.id] ?? ''}
										oninput={(e) => { newActorInput = { ...newActorInput, [plan.id]: e.currentTarget.value }; }}
										onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddActor(plan.id); } }}
										class="inline-create-input"
									/>
									<button class="btn-inline-create" onclick={() => handleAddActor(plan.id)}>+</button>
								</div>
							</div>
						{/each}
						{#if addingCollectionType?.planId === plan.id && addingCollectionType?.memberType === 'actor'}
							<div class="add-section-input">
								<input
									type="text"
									placeholder="Collection name..."
									bind:value={newCollectionName}
									onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleCreateTypedCollection(plan.id, 'actor'); } else if (e.key === 'Escape') { addingCollectionType = null; newCollectionName = ''; } }}
									class="inline-create-input"
								/>
								<button class="btn-cancel-note" onclick={() => { addingCollectionType = null; newCollectionName = ''; }}>Cancel</button>
							</div>
						{:else}
							<button class="btn-add-section" onclick={() => { addingCollectionType = { planId: plan.id, memberType: 'actor' }; newCollectionName = ''; }}>+ Collection</button>
						{/if}
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
			<p class="dialog-message">Do you also want to delete all related entities (activities, collections, notes, sources)?</p>
			<div class="dialog-actions">
				<button class="btn-dialog btn-dialog-cancel" onclick={() => confirmDelete = null}>Cancel</button>
				<button class="btn-dialog btn-dialog-keep" onclick={() => confirmDelete && handleDelete(confirmDelete, false)}>Plan only</button>
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
	.item-title { flex: 1; font-weight: 500; font-size: 0.9rem; text-align: left; padding: 0; color: #111827; }
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
	.status-btn { font-size: 0.65rem; padding: 2px 6px; background: #f3f4f6; border-radius: 4px; color: #6b7280; flex-shrink: 0; border: 1px solid transparent; cursor: pointer; font-weight: 500; }
	.status-btn:hover { filter: brightness(0.95); }
	.status-btn.status-planned { background: #f3f4f6; color: #9ca3af; }
	.status-btn.status-done { background: #dcfce7; color: #16a34a; }
	.status-btn.status-in-progress { background: #fef3c7; color: #d97706; }
	.status-btn.status-on-hold { background: #fef9c3; color: #a16207; }
	.status-btn.status-cancelled { background: #fee2e2; color: #dc2626; }

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

	/* Editable fields in expanded view */
	.editable-field { display: block; width: 100%; background: none; border: 1px solid transparent; border-radius: 4px; cursor: pointer; font-size: 0.9rem; font-weight: 600; color: #111827; text-align: left; padding: 4px 6px; margin-bottom: 4px; }
	.editable-field:hover { border-color: #d1d5db; background: white; }
	.editable-desc { font-size: 0.8rem; font-weight: 400; color: #6b7280; white-space: pre-wrap; }
	.editable-field-input { display: block; width: 100%; padding: 4px 6px; border: 1px solid #4a90a4; border-radius: 4px; font-size: 0.9rem; font-weight: 600; color: #111827; outline: none; margin-bottom: 4px; box-sizing: border-box; }
	.editable-field-textarea { display: block; width: 100%; padding: 4px 6px; border: 1px solid #4a90a4; border-radius: 4px; font-size: 0.8rem; color: #374151; outline: none; resize: vertical; font-family: inherit; margin-bottom: 4px; box-sizing: border-box; }

	/* Dates in expanded view */
	.expanded-dates { display: flex; gap: 8px; margin-bottom: 8px; }
	.date-label { display: flex; align-items: center; gap: 4px; font-size: 0.8rem; color: #6b7280; }
	.date-input { padding: 4px 6px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.8rem; }

	/* Activities section header */
	.activities-section-header { font-size: 0.75rem; font-weight: 600; color: #4a90a4; text-transform: uppercase; letter-spacing: 0.03em; margin: 8px 0 4px; }

	/* Role note sections */
	.role-section { margin-bottom: 8px; padding: 6px 8px; background: white; border: 1px solid #e5e7eb; border-radius: 6px; }
	.role-section-header { font-size: 0.75rem; font-weight: 600; color: #4a90a4; text-transform: uppercase; letter-spacing: 0.03em; margin-bottom: 4px; }
	.role-notes-list { display: flex; flex-direction: column; gap: 3px; }
	.role-note-item { display: flex; align-items: center; gap: 6px; }
	.role-note-content { flex: 1; background: none; border: none; cursor: pointer; font-size: 0.8rem; color: #374151; text-align: left; padding: 2px 0; }
	.role-note-content:hover { color: #4a90a4; }
	.role-note-edit-input { flex: 1; padding: 2px 6px; border: 1px solid #4a90a4; border-radius: 4px; font-size: 0.8rem; color: #374151; outline: none; }
	.role-note-add { display: flex; gap: 4px; margin-top: 4px; }

	/* Reorder + notes */
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

	/* Linked entities */
	.linked-section { margin-top: 8px; padding: 6px 8px; background: white; border: 1px solid #e5e7eb; border-radius: 6px; }
	.linked-section-header { font-size: 0.75rem; font-weight: 600; color: #4a90a4; text-transform: uppercase; letter-spacing: 0.03em; margin-bottom: 4px; }
	.linked-item-row { display: flex; align-items: center; gap: 6px; }
	.linked-item-text { flex: 1; font-size: 0.8rem; color: #374151; padding: 2px 0; }
	.linked-empty { font-size: 0.78rem; color: #9ca3af; font-style: italic; margin: 2px 0; }

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

	/* Plan summary (card view) */
	.plan-summary { margin-top: 6px; display: flex; flex-direction: column; gap: 2px; }
	.summary-item { font-size: 0.78rem; color: #374151; line-height: 1.3; }
	.summary-label { font-weight: 600; color: #4a90a4; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.02em; margin-right: 4px; }

	/* Model field rows (expanded view) */
	.model-field-row { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
	.model-field-label { font-size: 0.72rem; font-weight: 600; color: #4a90a4; text-transform: uppercase; letter-spacing: 0.02em; min-width: 80px; flex-shrink: 0; }
	.model-field-value { font-size: 0.8rem; font-weight: 400; color: #374151; margin-bottom: 0; }
	.model-field-input { margin-bottom: 0; }

	/* Collection-based section groups */
	.linked-section-group { margin-top: 8px; }
	.linked-section-group-header { font-size: 0.75rem; font-weight: 600; color: #4a90a4; text-transform: uppercase; letter-spacing: 0.03em; margin-bottom: 4px; }
	.collection-sub-header { font-size: 0.73rem; font-weight: 600; color: #374151; padding: 3px 8px; background: #eef3f7; border-radius: 4px; border-left: 3px solid #4a90a4; margin-bottom: 4px; }
</style>

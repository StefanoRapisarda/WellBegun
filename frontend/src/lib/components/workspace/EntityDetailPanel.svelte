<script lang="ts">
	import { onMount } from 'svelte';
	import type { Tag } from '$lib/types';
	import { projects, loadProjects } from '$lib/stores/projects';
	import { logs, loadLogs } from '$lib/stores/logs';
	import { notes, loadNotes } from '$lib/stores/notes';
	import { activities, loadActivities } from '$lib/stores/activities';
	import { sources, loadSources } from '$lib/stores/sources';
	import { actors, loadActors } from '$lib/stores/actors';
	import { plans, loadPlans } from '$lib/stores/plans';
	import { collections, loadCollections } from '$lib/stores/collections';
	import { loadTriples } from '$lib/stores/knowledgeGraph';
	import { updateProject, deleteProject, activateProject, deactivateProject, archiveProject } from '$lib/api/projects';
	import { updateLog, deleteLog, activateLog, deactivateLog, archiveLog } from '$lib/api/logs';
	import { updateNote, deleteNote, activateNote, deactivateNote, archiveNote } from '$lib/api/notes';
	import { createActivity, updateActivity, deleteActivity, activateActivity, deactivateActivity, archiveActivity } from '$lib/api/activities';
	import { updateSource, deleteSource, activateSource, deactivateSource, archiveSource } from '$lib/api/sources';
	import { updateActor, deleteActor, activateActor, deactivateActor, archiveActor } from '$lib/api/actors';
	import { updatePlan, deletePlan, activatePlan, deactivatePlan, archivePlan, addPlanSource, removePlanSource, addPlanActor, removePlanActor, removeActivityFromGroup, createPlanCollection, getPlanCollections } from '$lib/api/plans';
	import { updateCollection, deleteCollection, activateCollection, deactivateCollection, archiveCollection, addItem, removeItem, updateItem } from '$lib/api/collections';
	import { createSource } from '$lib/api/sources';
	import { createActor } from '$lib/api/actors';
	import { getEntityTags, attachTag, detachTag } from '$lib/api/tags';
	import { loadTags } from '$lib/stores/tags';
	import { setLastUsedTags } from '$lib/stores/lastUsedTags';
	import { activeWorkspace, refreshActiveWorkspace } from '$lib/stores/workspaces';
	import { addWorkspaceItem } from '$lib/api/workspaces';
	import TagBadge from '$lib/components/shared/TagBadge.svelte';
	import TagInput from '$lib/components/shared/TagInput.svelte';
	import Timestamp from '$lib/components/shared/Timestamp.svelte';
	import EntityIcon from '$lib/components/shared/EntityIcon.svelte';
	import RichContent from '$lib/components/shared/RichContent.svelte';
	import ConfirmDialog from '$lib/components/shared/ConfirmDialog.svelte';

	let {
		entityType,
		entityId,
		onClose,
		onDeleted,
		nested = false,
		panelSize = 'normal'
	}: {
		entityType: string;
		entityId: number;
		onClose: () => void;
		onDeleted: () => void;
		nested?: boolean;
		panelSize?: 'normal' | 'small';
	} = $props();

	// ── Entity data from stores ──
	function getEntityData(type: string, id: number): any {
		switch (type) {
			case 'project': return $projects.find(e => e.id === id);
			case 'log': return $logs.find(e => e.id === id);
			case 'note': return $notes.find(e => e.id === id);
			case 'activity': return $activities.find(e => e.id === id);
			case 'source': return $sources.find(e => e.id === id);
			case 'actor': return $actors.find(e => e.id === id);
			case 'plan': return $plans.find(e => e.id === id);
			case 'collection': return $collections.find(e => e.id === id);
			default: return null;
		}
	}

	let data = $derived(getEntityData(entityType, entityId));

	// ── Field name helpers ──
	function getTitleField(type: string): string {
		return type === 'actor' ? 'full_name' : 'title';
	}
	function getTextField(type: string): string {
		switch (type) {
			case 'note': case 'log': return 'content';
			case 'actor': return 'notes';
			default: return 'description';
		}
	}
	function getTextPlaceholder(type: string): string {
		switch (type) {
			case 'note': case 'log': return 'Add content...';
			case 'actor': return 'Add notes...';
			default: return 'Add description...';
		}
	}

	let titleField = $derived(getTitleField(entityType));
	let textField = $derived(getTextField(entityType));
	let titleValue = $derived(data?.[titleField] ?? '');
	let textValue = $derived(data?.[textField] ?? '');

	// ── Status cycling ──
	const STATUS_CYCLES: Record<string, string[]> = {
		activity: ['todo', 'in_progress', 'done', 'on_hold', 'cancelled'],
		project: ['planned', 'in_progress', 'done', 'on_hold', 'cancelled'],
		plan: ['planned', 'in_progress', 'done', 'on_hold', 'cancelled'],
		source: ['to_read', 'reading', 'reviewed'],
	};
	const STATUS_STYLES: Record<string, { bg: string; color: string }> = {
		planned: { bg: '#f3f4f6', color: '#9ca3af' },
		todo: { bg: '#f3f4f6', color: '#9ca3af' },
		in_progress: { bg: '#fef3c7', color: '#d97706' },
		done: { bg: '#dcfce7', color: '#16a34a' },
		completed: { bg: '#dcfce7', color: '#16a34a' },
		on_hold: { bg: '#fef9c3', color: '#a16207' },
		cancelled: { bg: '#fee2e2', color: '#dc2626' },
		to_read: { bg: '#f3f4f6', color: '#9ca3af' },
		reading: { bg: '#fef3c7', color: '#d97706' },
		reviewed: { bg: '#dcfce7', color: '#16a34a' },
	};
	let hasStatus = $derived(entityType in STATUS_CYCLES);

	function getStatusStyle(status: string): { bg: string; color: string } {
		return STATUS_STYLES[status] ?? { bg: '#f3f4f6', color: '#6b7280' };
	}
	function formatStatus(status: string): string {
		return status.replace(/_/g, ' ');
	}

	async function cycleStatus() {
		if (!data || !hasStatus) return;
		const cycle = STATUS_CYCLES[entityType];
		const idx = cycle.indexOf(data.status);
		const next = cycle[(idx + 1) % cycle.length];
		await updateEntity({ status: next });
	}

	// ── Generic entity operations ──
	async function updateEntity(updates: Record<string, any>) {
		switch (entityType) {
			case 'project': await updateProject(entityId, updates); await loadProjects(); break;
			case 'log': await updateLog(entityId, updates); await loadLogs(); break;
			case 'note': await updateNote(entityId, updates); await loadNotes(); break;
			case 'activity': await updateActivity(entityId, updates); await loadActivities(); break;
			case 'source': await updateSource(entityId, updates); await loadSources(); break;
			case 'actor': await updateActor(entityId, updates); await loadActors(); break;
			case 'plan': await updatePlan(entityId, updates); await loadPlans(); break;
			case 'collection': await updateCollection(entityId, updates); await loadCollections(); break;
		}
	}

	async function toggleActive() {
		if (!data) return;
		const activate = !data.is_active;
		switch (entityType) {
			case 'project': activate ? await activateProject(entityId) : await deactivateProject(entityId); await loadProjects(); break;
			case 'log': activate ? await activateLog(entityId) : await deactivateLog(entityId); await loadLogs(); break;
			case 'note': activate ? await activateNote(entityId) : await deactivateNote(entityId); await loadNotes(); break;
			case 'activity': activate ? await activateActivity(entityId) : await deactivateActivity(entityId); await loadActivities(); break;
			case 'source': activate ? await activateSource(entityId) : await deactivateSource(entityId); await loadSources(); break;
			case 'actor': activate ? await activateActor(entityId) : await deactivateActor(entityId); await loadActors(); break;
			case 'plan': activate ? await activatePlan(entityId) : await deactivatePlan(entityId); await loadPlans(); break;
			case 'collection': activate ? await activateCollection(entityId) : await deactivateCollection(entityId); await loadCollections(); break;
		}
	}

	async function handleArchive() {
		switch (entityType) {
			case 'project': await archiveProject(entityId); await loadProjects(); break;
			case 'log': await archiveLog(entityId); await loadLogs(); break;
			case 'note': await archiveNote(entityId); await loadNotes(); break;
			case 'activity': await archiveActivity(entityId); await loadActivities(); break;
			case 'source': await archiveSource(entityId); await loadSources(); break;
			case 'actor': await archiveActor(entityId); await loadActors(); break;
			case 'plan': await archivePlan(entityId); await loadPlans(); break;
			case 'collection': await archiveCollection(entityId); await loadCollections(); break;
		}
		onClose();
	}

	let confirmDelete = $state(false);
	let collectionDeleteConfirm = $state<{ id: number; context: 'entity' | 'plan' | 'unified' } | null>(null);

	function requestDelete() {
		if (entityType === 'collection') {
			collectionDeleteConfirm = { id: entityId, context: 'entity' };
		} else {
			confirmDelete = true;
		}
	}

	async function handleDelete() {
		switch (entityType) {
			case 'project': await deleteProject(entityId); await loadProjects(); break;
			case 'log': await deleteLog(entityId); await loadLogs(); break;
			case 'note': await deleteNote(entityId); await loadNotes(); break;
			case 'activity': await deleteActivity(entityId); await loadActivities(); break;
			case 'source': await deleteSource(entityId); await loadSources(); break;
			case 'actor': await deleteActor(entityId); await loadActors(); break;
			case 'plan': await deletePlan(entityId); await loadPlans(); break;
			case 'collection': await deleteCollection(entityId); await loadCollections(); break;
		}
		await loadTags();
		confirmDelete = false;
		onDeleted();
	}

	async function deleteMemberEntity(memberType: string, memberId: number) {
		switch (memberType) {
			case 'source': await deleteSource(memberId); break;
			case 'activity': await deleteActivity(memberId); break;
			case 'note': await deleteNote(memberId); break;
		}
	}

	async function handleCollectionDeleteConfirm(deleteMembers: boolean) {
		const confirm = collectionDeleteConfirm;
		if (!confirm) return;
		const col = $collections.find(c => c.id === confirm.id);

		if (col && deleteMembers) {
			for (const item of col.items) {
				await deleteMemberEntity(item.member_entity_type, item.member_entity_id);
			}
		}

		if (confirm.context === 'plan' && !deleteMembers) {
			// Move items to default collection instead of deleting them
			const coll = planCollections.find(c => c.collectionId === confirm.id);
			if (coll && defaultActivityCollection) {
				for (const item of coll.items) {
					await removeItem(item.itemId);
					try {
						await addItem(defaultActivityCollection.collectionId, {
							member_entity_type: item.memberEntityType,
							member_entity_id: item.memberEntityId,
						});
					} catch { /* may already exist */ }
				}
			}
		}

		await deleteCollection(confirm.id);
		collectionDeleteConfirm = null;
		editingSectionKey = null;
		await Promise.all([loadCollections(), loadSources(), loadActivities(), loadNotes(), loadTags(), loadPlanCollections(), loadTriples()]);

		if (confirm.context === 'entity') {
			onDeleted();
		}
	}

	// ── Inline editing ──
	let editingField: string | null = $state(null);
	let editFieldText = $state('');

	function startEditTitle() {
		editingField = 'title';
		editFieldText = titleValue;
	}
	function startEditText() {
		editingField = 'text';
		editFieldText = textValue;
	}
	function startEditExtra(fieldName: string) {
		editingField = fieldName;
		editFieldText = data?.[fieldName] ?? '';
	}

	async function saveField(fieldOverride?: string) {
		const field = fieldOverride ?? editingField;
		if (!field) return;
		const value = editFieldText.trim();
		editingField = null;

		if (field === 'title') {
			if (!value) return; // don't save empty title
			if (value !== titleValue) {
				await updateEntity({ [titleField]: value });
			}
		} else if (field === 'text') {
			if (value !== textValue) {
				await updateEntity({ [textField]: value || null });
			}
		} else if (field === 'duration') {
			const numVal = value ? parseInt(value, 10) : null;
			if (numVal !== (data?.duration ?? null)) {
				await updateEntity({ duration: numVal });
			}
		} else if (field === 'activity_date') {
			const dateVal = value ? value + 'T00:00:00' : null;
			const oldVal = data?.activity_date ?? null;
			if (dateVal !== oldVal) {
				await updateEntity({ activity_date: dateVal });
			}
		} else if (field === 'start_date') {
			const dateVal = value || null;
			const oldVal = data?.start_date ?? null;
			if (dateVal !== oldVal) {
				await updateEntity({ start_date: dateVal });
			}
		} else {
			// Extra field (role, affiliation, email, url, etc.)
			const oldValue = data?.[field] ?? '';
			if (value !== oldValue) {
				await updateEntity({ [field]: value || null });
			}
		}
	}

	function cancelEdit() {
		editingField = null;
		editFieldText = '';
	}

	// ── Tags ──
	let entityTags = $state<Tag[]>([]);
	let tagsExpanded = $state(false);

	async function handleAttach(tag: Tag) {
		await attachTag(tag.id, entityType, entityId);
		entityTags = await getEntityTags(entityType, entityId);
		setLastUsedTags(entityType as any, entityTags);
	}
	async function handleDetach(tag: Tag) {
		await detachTag(tag.id, entityType, entityId);
		entityTags = await getEntityTags(entityType, entityId);
		setLastUsedTags(entityType as any, entityTags);
	}

	// ── Plan collections (real Collection entities linked via knowledge triples) ──
	interface PlanCollection {
		collectionId: number;
		title: string;
		predicate: string;
		items: Array<{
			itemId: number;
			memberEntityType: string;
			memberEntityId: number;
			status: string | null;
		}>;
	}
	let planCollections = $state<PlanCollection[]>([]);

	let defaultActivityCollection = $derived(planCollections.find(c => c.predicate === 'has activities'));
	let namedActivityCollections = $derived(planCollections.filter(c => c.predicate.startsWith('has activities:')));
	let sourcesCollection = $derived(planCollections.find(c => c.predicate === 'has sources'));
	let actorsCollection = $derived(planCollections.find(c => c.predicate === 'has actors'));

	// Section management
	let addingSectionFor: 'activity' | 'collection' | null = $state(null);
	let newSectionName = $state('');
	let editingSectionKey: string | null = $state(null);
	let editSectionText = $state('');

	// Per-section inline-create inputs (keyed by "entityType:header")
	let inlineCreateTexts = $state<Record<string, string>>({});

	// Search UI for sources/actors
	let addingSourceSearch = $state(false);
	let sourceSearchText = $state('');
	let addingActorSearch = $state(false);
	let actorSearchText = $state('');

	// Nested detail panel
	let nestedDetail: { type: string; id: number } | null = $state(null);

	async function loadPlanCollections() {
		if (entityType !== 'plan') return;
		const raw = await getPlanCollections(entityId);
		planCollections = raw.map(c => ({
			collectionId: c.collection_id,
			title: c.title,
			predicate: c.predicate,
			items: (c.items ?? []).map(i => ({
				itemId: i.item_id,
				memberEntityType: i.member_entity_type,
				memberEntityId: i.member_entity_id,
				status: i.status,
			})),
		}));
	}

	function openNestedDetail(type: string, id: number) {
		if (nested) return;
		nestedDetail = { type, id };
	}

	// ── Plan collection derived helpers ──
	// Derived: sources from the sources collection
	let planLinkedSources = $derived.by(() => {
		if (!sourcesCollection) return [];
		return sourcesCollection.items.map(i => {
			const s = getEntityData('source', i.memberEntityId);
			return { id: i.memberEntityId, itemId: i.itemId, title: s?.title ?? `source #${i.memberEntityId}` };
		});
	});
	// Derived: actors from the actors collection
	let planLinkedActors = $derived.by(() => {
		if (!actorsCollection) return [];
		return actorsCollection.items.map(i => {
			const a = getEntityData('actor', i.memberEntityId);
			return { id: i.memberEntityId, itemId: i.itemId, full_name: a?.full_name ?? `actor #${i.memberEntityId}`, role: a?.role ?? null };
		});
	});
	let sourcesCollectionId = $derived(sourcesCollection?.collectionId ?? null);
	let actorsCollectionId = $derived(actorsCollection?.collectionId ?? null);

	// Unified collections (mixed entity types)
	let unifiedCollections = $derived(
		planCollections.filter(c => c.predicate.startsWith('has collection:'))
	);

	// Default activity items — activities in the "has activities" collection
	let defaultActivityItems = $derived.by(() => {
		if (!defaultActivityCollection) return [];
		return defaultActivityCollection.items.map(i => {
			const a = getEntityData('activity', i.memberEntityId);
			return { ...a, id: i.memberEntityId, itemId: i.itemId, title: a?.title ?? `activity #${i.memberEntityId}`, status: a?.status ?? i.status };
		});
	});

	// Total activity count across all activity collections
	let totalActivityCount = $derived(
		(defaultActivityCollection?.items.length ?? 0) + namedActivityCollections.reduce((n, c) => n + c.items.length, 0)
	);

	// ── Collection items ──
	let collectionItems = $derived.by(() => {
		if (entityType !== 'collection' || !data?.items) return [];
		const items = data.items as Array<{ id: number; member_entity_type: string; member_entity_id: number; status: string | null; header: string | null; position: number }>;
		return [...items].sort((a, b) => a.position - b.position).map(item => {
			const member = getEntityData(item.member_entity_type, item.member_entity_id);
			return {
				itemId: item.id,
				type: item.member_entity_type,
				memberId: item.member_entity_id,
				title: member?.title ?? member?.full_name ?? `${item.member_entity_type} #${item.member_entity_id}`,
				status: item.status,
				header: item.header,
			};
		});
	});

	let addingItem = $state(false);
	let addSearch = $state('');
	let collectionMemberType = $derived(data?.entity_type ?? '');

	let addSearchResults = $derived.by(() => {
		if (!addingItem || !addSearch.trim() || !collectionMemberType) return [];
		const q = addSearch.toLowerCase();
		const existingIds = new Set((data?.items ?? []).map((i: any) => i.member_entity_id));
		let candidates: Array<{ id: number; title: string }> = [];
		switch (collectionMemberType) {
			case 'project': candidates = $projects.map(e => ({ id: e.id, title: e.title })); break;
			case 'log': candidates = $logs.map(e => ({ id: e.id, title: e.title })); break;
			case 'note': candidates = $notes.map(e => ({ id: e.id, title: e.title })); break;
			case 'activity': candidates = $activities.map(e => ({ id: e.id, title: e.title })); break;
			case 'source': candidates = $sources.map(e => ({ id: e.id, title: e.title })); break;
			case 'actor': candidates = $actors.map(e => ({ id: e.id, title: e.full_name })); break;
			case 'plan': candidates = $plans.map(e => ({ id: e.id, title: e.title })); break;
		}
		return candidates
			.filter(c => !existingIds.has(c.id) && c.title.toLowerCase().includes(q))
			.slice(0, 8);
	});

	async function handleAddItem(memberId: number) {
		await addItem(entityId, { member_entity_type: collectionMemberType, member_entity_id: memberId });
		await loadCollections();
		addSearch = '';
		addingItem = false;
	}
	async function handleRemoveItem(itemId: number) {
		await removeItem(itemId);
		await loadCollections();
	}

	// ── Plan source/actor search results ──
	let sourceSearchResults = $derived.by(() => {
		if (!addingSourceSearch || !sourceSearchText.trim()) return [];
		const q = sourceSearchText.toLowerCase();
		const linkedIds = new Set(planLinkedSources.map(s => s.id));
		return $sources
			.filter(s => !linkedIds.has(s.id) && s.title.toLowerCase().includes(q))
			.map(s => ({ id: s.id, title: s.title }))
			.slice(0, 8);
	});

	let actorSearchResults = $derived.by(() => {
		if (!addingActorSearch || !actorSearchText.trim()) return [];
		const q = actorSearchText.toLowerCase();
		const linkedIds = new Set(planLinkedActors.map(a => a.id));
		return $actors
			.filter(a => !linkedIds.has(a.id) && a.full_name.toLowerCase().includes(q))
			.map(a => ({ id: a.id, title: a.full_name }))
			.slice(0, 8);
	});

	// ── Section management helpers ──
	function collectionKey(collectionId: number): string {
		return `coll:${collectionId}`;
	}
	function getInlineText(collectionId: number): string {
		return inlineCreateTexts[collectionKey(collectionId)] ?? '';
	}
	function setInlineText(collectionId: number, value: string) {
		inlineCreateTexts[collectionKey(collectionId)] = value;
	}
	// For the default collection (no collectionId yet / inline create at top)
	function getDefaultInlineText(): string {
		return inlineCreateTexts['default'] ?? '';
	}
	function setDefaultInlineText(value: string) {
		inlineCreateTexts['default'] = value;
	}

	let creatingCollection = false;
	async function handleCreateCollection() {
		if (creatingCollection) return;
		const title = newSectionName.trim();
		if (!title) { addingSectionFor = null; return; }
		creatingCollection = true;
		try {
			const result = await createPlanCollection(entityId, { title });
			await placeOnWorkspaceNearPlan('collection', result.collection_id);
			await Promise.all([loadCollections(), loadPlanCollections(), loadTriples()]);
		} finally {
			creatingCollection = false;
			addingSectionFor = null;
			newSectionName = '';
		}
	}

	function startRenameCollection(collectionId: number, currentTitle: string) {
		editingSectionKey = collectionKey(collectionId);
		editSectionText = currentTitle;
	}
	async function handleRenameCollection(collectionId: number, newTitle: string) {
		const trimmed = newTitle.trim();
		if (!trimmed) { editingSectionKey = null; return; }
		await updateCollection(collectionId, { title: trimmed });
		editingSectionKey = null;
		await Promise.all([loadCollections(), loadPlanCollections()]);
	}
	function handleDeleteCollection(collectionId: number) {
		collectionDeleteConfirm = { id: collectionId, context: 'plan' };
	}

	// ── Workspace auto-placement ──
	// When creating/linking an entity from a plan, place it on the workspace near the plan
	async function placeOnWorkspaceNearPlan(childType: string, childId: number) {
		const ws = $activeWorkspace;
		if (!ws) return;
		const planItem = ws.items.find(i => i.entity_type === 'plan' && i.entity_id === entityId);
		if (!planItem) return; // plan not on this workspace
		// Check if already on workspace
		if (ws.items.some(i => i.entity_type === childType && i.entity_id === childId)) return;
		// Place with offset from plan position
		const offset = 40 + Math.random() * 80;
		const angle = Math.random() * Math.PI * 2;
		const x = Math.round(planItem.x + Math.cos(angle) * (180 + offset));
		const y = Math.round(planItem.y + Math.sin(angle) * (120 + offset));
		try {
			await addWorkspaceItem(ws.id, { entity_type: childType, entity_id: childId, x, y });
			await refreshActiveWorkspace();
		} catch { /* item may already exist */ }
	}

	// ── Activity handlers ──
	async function handleCreateActivityInDefaultCollection() {
		const title = getDefaultInlineText().trim();
		if (!title) return;
		// Create with plan_id, backend auto-adds to default collection
		const newActivity = await createActivity({ plan_id: entityId, title, status: 'todo' });
		setDefaultInlineText('');
		await Promise.all([loadActivities(), loadPlans(), loadCollections(), loadPlanCollections(), loadTriples()]);
		// Place the default activity collection container on workspace (may have just been created)
		if (defaultActivityCollection) {
			await placeOnWorkspaceNearPlan('collection', defaultActivityCollection.collectionId);
		}
		await placeOnWorkspaceNearPlan('activity', newActivity.id);
	}
	async function handleCreateActivityInCollection(collectionId: number) {
		const title = getInlineText(collectionId).trim();
		if (!title) return;
		// Find the collection title to use as header — prevents backend auto-adding to default collection
		const coll = namedActivityCollections.find(c => c.collectionId === collectionId);
		const header = coll?.title ?? '_';
		const newActivity = await createActivity({ plan_id: entityId, title, header, status: 'todo' });
		setInlineText(collectionId, '');
		// Add to the named collection
		await addItem(collectionId, { member_entity_type: 'activity', member_entity_id: newActivity.id });
		await Promise.all([loadActivities(), loadPlans(), loadCollections(), loadPlanCollections(), loadTriples()]);
		await placeOnWorkspaceNearPlan('collection', collectionId);
		await placeOnWorkspaceNearPlan('activity', newActivity.id);
	}
	async function handleToggleActivityDone(activity: any) {
		const next = activity.status === 'done' ? 'todo' : 'done';
		await updateActivity(activity.id, { status: next });
		await Promise.all([loadActivities(), loadPlans()]);
	}
	async function handleRemoveActivity(activityId: number) {
		await removeActivityFromGroup(entityId, activityId);
		await updateActivity(activityId, { plan_id: null });
		await Promise.all([loadActivities(), loadPlans(), loadCollections(), loadPlanCollections(), loadTriples()]);
	}

	// ── Plan panel: drag activities between collections ──
	// "default" = default activity collection, number = named collection ID
	let draggingActivityId: number | null = $state(null);
	let dragOverTarget: 'default' | number | null = $state(null);

	function handleActivityDragStart(e: DragEvent, activityId: number) {
		draggingActivityId = activityId;
		if (e.dataTransfer) {
			e.dataTransfer.effectAllowed = 'move';
			e.dataTransfer.setData('text/plain', String(activityId));
		}
	}
	function handleActivityDragEnd() {
		draggingActivityId = null;
		dragOverTarget = null;
	}
	function handleSectionDragOver(e: DragEvent, target: 'default' | number) {
		if (draggingActivityId == null) return;
		e.preventDefault();
		if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
		dragOverTarget = target;
	}
	function handleSectionDragLeave(target: 'default' | number) {
		if (dragOverTarget === target) dragOverTarget = null;
	}
	async function handleSectionDrop(e: DragEvent, target: 'default' | number) {
		e.preventDefault();
		dragOverTarget = null;
		if (draggingActivityId == null) return;
		const activityId = draggingActivityId;
		draggingActivityId = null;

		// Find which collection the activity currently belongs to
		let sourceCollId: number | null = null;
		let sourceItemId: number | null = null;
		for (const c of planCollections) {
			if (c.predicate === 'has activities' || c.predicate.startsWith('has activities:')) {
				const found = c.items.find(i => i.memberEntityType === 'activity' && i.memberEntityId === activityId);
				if (found) {
					sourceCollId = c.collectionId;
					sourceItemId = found.itemId;
					break;
				}
			}
		}

		const targetCollId = target === 'default' ? (defaultActivityCollection?.collectionId ?? null) : target;

		// No-op if same collection
		if (sourceCollId === targetCollId) return;

		// Remove from source collection
		if (sourceItemId != null) {
			await removeItem(sourceItemId);
		}

		// Add to target collection
		if (targetCollId != null) {
			try {
				await addItem(targetCollId, { member_entity_type: 'activity', member_entity_id: activityId });
			} catch { /* duplicate */ }
		}

		await Promise.all([loadCollections(), loadPlanCollections(), loadTriples()]);
	}

	// ── Plan add/remove handlers (sources) ──
	async function handleAddPlanSource(sourceId: number) {
		const result = await addPlanSource(entityId, sourceId);
		await placeOnWorkspaceNearPlan('collection', result.collection_id);
		await placeOnWorkspaceNearPlan('source', sourceId);
		await loadCollections();  // Must finish first — feeds collectionContainers
		await Promise.all([loadPlanCollections(), loadTriples()]);
		sourceSearchText = '';
		addingSourceSearch = false;
	}

	async function handleRemovePlanSource(itemId: number) {
		await removeItem(itemId);
		await Promise.all([loadCollections(), loadPlanCollections(), loadTriples()]);
	}

	async function handleAddPlanActor(actorId: number) {
		const result = await addPlanActor(entityId, actorId);
		await placeOnWorkspaceNearPlan('collection', result.collection_id);
		await placeOnWorkspaceNearPlan('actor', actorId);
		await loadCollections();  // Must finish first — feeds collectionContainers
		await Promise.all([loadPlanCollections(), loadTriples()]);
		actorSearchText = '';
		addingActorSearch = false;
	}

	async function handleRemovePlanActor(itemId: number) {
		await removeItem(itemId);
		await Promise.all([loadCollections(), loadPlanCollections(), loadTriples()]);
	}

	async function handleSourceSearchSubmit() {
		const title = sourceSearchText.trim();
		if (!title) return;
		const linkedIds = new Set(planLinkedSources.map(s => s.id));
		const existing = $sources.find(s => s.title.toLowerCase() === title.toLowerCase());
		if (existing && linkedIds.has(existing.id)) {
			sourceSearchText = '';
			addingSourceSearch = false;
			return;
		}
		const sourceId = existing ? existing.id : (await createSource({ title })).id;
		if (!existing) await loadSources();
		await handleAddPlanSource(sourceId);
	}

	async function handleActorSearchSubmit() {
		const name = actorSearchText.trim();
		if (!name) return;
		const linkedIds = new Set(planLinkedActors.map(a => a.id));
		const existing = $actors.find(a => a.full_name.toLowerCase() === name.toLowerCase());
		if (existing && linkedIds.has(existing.id)) {
			actorSearchText = '';
			addingActorSearch = false;
			return;
		}
		const actorId = existing ? existing.id : (await createActor({ full_name: name })).id;
		if (!existing) await loadActors();
		await handleAddPlanActor(actorId);
	}

	// ── Unified collection handlers ──
	async function handleCreateEntityInUnifiedCollection(collectionId: number) {
		const title = getInlineText(collectionId).trim();
		if (!title) return;
		const newActivity = await createActivity({ plan_id: entityId, title, header: '_', status: 'todo' });
		setInlineText(collectionId, '');
		await addItem(collectionId, { member_entity_type: 'activity', member_entity_id: newActivity.id });
		await placeOnWorkspaceNearPlan('activity', newActivity.id);
		await Promise.all([loadActivities(), loadPlans(), loadCollections(), loadPlanCollections(), loadTriples()]);
	}

	function handleDeleteUnifiedCollection(collectionId: number) {
		collectionDeleteConfirm = { id: collectionId, context: 'unified' };
	}

	async function handleRemoveUnifiedItem(itemId: number) {
		await removeItem(itemId);
		await Promise.all([loadCollections(), loadPlanCollections(), loadTriples()]);
	}

	// ── Keyboard ──
	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			if (nested) { e.stopImmediatePropagation(); onClose(); return; }
			if (editingField) { cancelEdit(); }
			else if (editingSectionKey) { editingSectionKey = null; }
			else if (addingSectionFor) { addingSectionFor = null; newSectionName = ''; }
			else if (addingSourceSearch) { addingSourceSearch = false; sourceSearchText = ''; }
			else if (addingActorSearch) { addingActorSearch = false; actorSearchText = ''; }
			else if (addingItem) { addingItem = false; addSearch = ''; }
			else if (nestedDetail) { nestedDetail = null; }
			else { onClose(); }
		}
	}

	// ── Init ──
	onMount(async () => {
		// If entity data is missing from the store, try reloading the relevant store
		if (!getEntityData(entityType, entityId)) {
			switch (entityType) {
				case 'collection': await loadCollections(); break;
				case 'activity': await loadActivities(); break;
				case 'source': await loadSources(); break;
				case 'actor': await loadActors(); break;
				case 'plan': await loadPlans(); break;
				case 'note': await loadNotes(); break;
				case 'project': await loadProjects(); break;
				case 'log': await loadLogs(); break;
			}
		}
		try { entityTags = await getEntityTags(entityType, entityId); } catch { /* ignore */ }
		if (entityType === 'plan') {
			try { await loadPlanCollections(); } catch (e) { console.error('Failed to load plan collections:', e); }
		}
	});
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div class="detail-overlay" class:nested-overlay={nested} onclick={onClose} role="dialog" tabindex="-1">
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div class="detail-panel" class:panel-small={panelSize === 'small'} onclick={(e) => e.stopPropagation()} role="document">
		{#if data}
			<div class="detail-widget {entityType}-widget">
				<!-- Title row -->
				<div class="title-row">
					{#if editingField === 'title'}
						<input
							type="text"
							class="title-input"
							bind:value={editFieldText}
							onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); saveField(); } else if (e.key === 'Escape') { e.stopPropagation(); cancelEdit(); } }}
							onblur={() => saveField()}
							autofocus
						/>
					{:else}
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<span class="title-display" onclick={startEditTitle}>{titleValue}</span>
					{/if}

					{#if hasStatus && data.status}
						{@const ss = getStatusStyle(data.status)}
						<button class="status-btn" style:background={ss.bg} style:color={ss.color} onclick={cycleStatus}>
							{formatStatus(data.status)}
						</button>
					{/if}
					<button class="btn-close" onclick={onClose}>&times;</button>
				</div>

				<!-- Action buttons -->
				<div class="action-bar">
					<button class="btn-action btn-tags" onclick={() => tagsExpanded = !tagsExpanded}>Tags</button>
					<button class="btn-action btn-active" class:active={data.is_active} onclick={toggleActive}>
						{data.is_active ? 'Active' : 'Inactive'}
					</button>
					<button class="btn-action btn-archive" onclick={handleArchive}>Archive</button>
					<button class="btn-action btn-delete" onclick={requestDelete}>Delete</button>
				</div>

				<!-- Tag input (expandable) -->
				{#if tagsExpanded}
					<div class="tag-section">
						<TagInput
							attachedTags={entityTags}
							targetType={entityType}
							targetId={entityId}
							onAttach={handleAttach}
							onDetach={handleDetach}
							onClose={() => tagsExpanded = false}
						/>
					</div>
				{/if}

				<!-- Scrollable content area -->
				<div class="content-area">
					<!-- Main text field -->
					{#if editingField === 'text'}
						<textarea
							class="text-input"
							rows="4"
							bind:value={editFieldText}
							onkeydown={(e) => { if (e.key === 'Escape') { e.stopPropagation(); cancelEdit(); } }}
							onblur={() => saveField()}
							autofocus
						></textarea>
					{:else}
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<div class="text-display" onclick={startEditText}>
							{#if textValue}
								<RichContent text={textValue} />
							{:else}
								<span class="text-placeholder">{getTextPlaceholder(entityType)}</span>
							{/if}
						</div>
					{/if}

					<!-- Entity-specific extras (read-only) -->
					{#if entityType === 'source'}
						{@const sourceFields = [
							{ key: 'author', label: 'Author', placeholder: 'Add author...' },
							{ key: 'source_type', label: 'Type', placeholder: 'Add type...' },
							{ key: 'content_url', label: 'URL', placeholder: 'Add URL...', inputType: 'url' },
						]}
						{#each sourceFields as field}
							<div class="extra-line editable-field">
								<span class="extra-label">{field.label}</span>
								{#if editingField === field.key}
									<input
										type={field.inputType ?? 'text'}
										class="extra-field-input"
										bind:value={editFieldText}
										placeholder={field.placeholder}
										onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); saveField(); } else if (e.key === 'Escape') { e.stopPropagation(); cancelEdit(); } }}
										onblur={() => saveField()}
										autofocus
									/>
								{:else}
									<!-- svelte-ignore a11y_no_static_element_interactions -->
									<span class="extra-field-value" class:empty={!data[field.key]} onclick={() => startEditExtra(field.key)}>
										{#if field.key === 'content_url' && data[field.key]}
											<a href={data[field.key]} target="_blank" rel="noopener noreferrer" class="link" onclick={(e) => e.stopPropagation()}>{data[field.key]}</a>
										{:else if data[field.key]}
											{data[field.key]}
										{:else}
											<span class="text-placeholder">{field.placeholder}</span>
										{/if}
									</span>
								{/if}
							</div>
						{/each}
					{:else if entityType === 'actor'}
						{@const actorFields = [
							{ key: 'role', label: 'Role', placeholder: 'Add role...' },
							{ key: 'affiliation', label: 'Affiliation', placeholder: 'Add affiliation...' },
							{ key: 'expertise', label: 'Expertise', placeholder: 'Add expertise...' },
							{ key: 'email', label: 'Email', placeholder: 'Add email...', inputType: 'email' },
							{ key: 'url', label: 'URL', placeholder: 'Add URL...', inputType: 'url' },
						]}
						{#each actorFields as field}
							<div class="extra-line editable-field">
								<span class="extra-label">{field.label}</span>
								{#if editingField === field.key}
									<input
										type={field.inputType ?? 'text'}
										class="extra-field-input"
										bind:value={editFieldText}
										placeholder={field.placeholder}
										onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); saveField(); } else if (e.key === 'Escape') { e.stopPropagation(); cancelEdit(); } }}
										onblur={() => saveField()}
										autofocus
									/>
								{:else}
									<!-- svelte-ignore a11y_no_static_element_interactions -->
									<span class="extra-field-value" class:empty={!data[field.key]} onclick={() => startEditExtra(field.key)}>
										{#if field.key === 'email' && data[field.key]}
											<a href="mailto:{data[field.key]}" class="link" onclick={(e) => e.stopPropagation()}>{data[field.key]}</a>
										{:else if field.key === 'url' && data[field.key]}
											<a href={data[field.key]} target="_blank" rel="noopener noreferrer" class="link" onclick={(e) => e.stopPropagation()}>{data[field.key]}</a>
										{:else if data[field.key]}
											{data[field.key]}
										{:else}
											<span class="text-placeholder">{field.placeholder}</span>
										{/if}
									</span>
								{/if}
							</div>
						{/each}
					{:else if entityType === 'log'}
						<div class="extra-line editable-field">
							<span class="extra-label">Location</span>
							{#if editingField === 'location'}
								<input
									type="text"
									class="extra-field-input"
									bind:value={editFieldText}
									placeholder="Location"
									onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); saveField('location'); } else if (e.key === 'Escape') { e.stopPropagation(); editingField = null; } }}
									onblur={() => saveField('location')}
									autofocus
								/>
							{:else}
								<!-- svelte-ignore a11y_no_static_element_interactions -->
								<span class="extra-field-value" class:empty={!data.location} onclick={() => { editingField = 'location'; editFieldText = data.location ?? ''; }}>
									{data.location || 'Add location...'}
								</span>
							{/if}
						</div>
						<div class="emoji-picker-row">
							<span class="emoji-picker-label">Mood</span>
							<div class="emoji-chips">
								{#each ['😊', '😃', '😌', '😐', '😔', '😢', '😤', '😴', '🤔', '😎'] as e}
									<button type="button" class="emoji-chip" class:selected={data.mood === e} onclick={() => updateEntity({ mood: data.mood === e ? null : e })}>{e}</button>
								{/each}
							</div>
						</div>
						<div class="emoji-picker-row">
							<span class="emoji-picker-label">Weather</span>
							<div class="emoji-chips">
								{#each ['☀️', '🌤️', '⛅', '☁️', '🌧️', '⛈️', '🌨️', '🌬️', '🌫️', '🌈'] as e}
									<button type="button" class="emoji-chip" class:selected={data.weather === e} onclick={() => updateEntity({ weather: data.weather === e ? null : e })}>{e}</button>
								{/each}
							</div>
						</div>
						<div class="emoji-picker-row">
							<span class="emoji-picker-label">Theme</span>
							<div class="emoji-chips">
								{#each ['💼', '📚', '🏃', '🎨', '🧘', '🎉', '❤️', '🌱', '🍳', '✈️'] as e}
									<button type="button" class="emoji-chip" class:selected={data.day_theme === e} onclick={() => updateEntity({ day_theme: data.day_theme === e ? null : e })}>{e}</button>
								{/each}
							</div>
						</div>
					{:else if entityType === 'activity'}
						<div class="extra-line editable-field">
							<span class="extra-label">Duration</span>
							{#if editingField === 'duration'}
								<input
									type="number"
									class="extra-field-input"
									bind:value={editFieldText}
									min="0"
									placeholder="minutes"
									onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); saveField('duration'); } else if (e.key === 'Escape') { e.stopPropagation(); editingField = null; } }}
									onblur={() => saveField('duration')}
									autofocus
								/>
							{:else}
								<!-- svelte-ignore a11y_no_static_element_interactions -->
								<span class="extra-field-value" class:empty={!data.duration} onclick={() => { editingField = 'duration'; editFieldText = data.duration?.toString() ?? ''; }}>
									{data.duration ? `${data.duration}m` : 'Add duration...'}
								</span>
							{/if}
						</div>
						<div class="extra-line editable-field">
							<span class="extra-label">Date</span>
							{#if editingField === 'activity_date'}
								<input
									type="date"
									class="extra-field-input"
									bind:value={editFieldText}
									onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); saveField('activity_date'); } else if (e.key === 'Escape') { e.stopPropagation(); editingField = null; } }}
									onblur={() => saveField('activity_date')}
									autofocus
								/>
							{:else}
								<!-- svelte-ignore a11y_no_static_element_interactions -->
								<span class="extra-field-value" class:empty={!data.activity_date} onclick={() => { editingField = 'activity_date'; editFieldText = data.activity_date ? data.activity_date.slice(0, 10) : ''; }}>
									{data.activity_date ? new Date(data.activity_date).toLocaleDateString() : 'Add date...'}
								</span>
							{/if}
						</div>
						<div class="extra-line editable-field">
							<span class="extra-label">Outcome</span>
							{#if editingField === 'outcome'}
								<textarea
									class="extra-field-input"
									bind:value={editFieldText}
									rows="2"
									placeholder="Describe the outcome..."
									onkeydown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); saveField('outcome'); } else if (e.key === 'Escape') { e.stopPropagation(); editingField = null; } }}
									onblur={() => saveField('outcome')}
									autofocus
								></textarea>
							{:else}
								<!-- svelte-ignore a11y_no_static_element_interactions -->
								<span class="extra-field-value" class:empty={!data.outcome} onclick={() => { editingField = 'outcome'; editFieldText = data.outcome ?? ''; }}>
									{data.outcome || 'Add outcome...'}
								</span>
							{/if}
						</div>
					{:else if entityType === 'project'}
						<div class="extra-line editable-field">
							<span class="extra-label">Status</span>
							{#if editingField === 'status'}
								<select
									class="extra-field-input"
									bind:value={editFieldText}
									onchange={() => { updateEntity({ status: editFieldText }); editingField = null; }}
									onblur={() => { editingField = null; }}
									autofocus
								>
									<option value="in_progress">In Progress</option>
									<option value="on_hold">On Hold</option>
									<option value="completed">Completed</option>
									<option value="archived">Archived</option>
									<option value="planned">Planned</option>
									<option value="cancelled">Cancelled</option>
								</select>
							{:else}
								<!-- svelte-ignore a11y_no_static_element_interactions -->
								<span class="extra-field-value status-value" onclick={() => { editingField = 'status'; editFieldText = data.status ?? 'in_progress'; }}>
									{(data.status ?? 'in_progress').replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())}
								</span>
							{/if}
						</div>
						<div class="extra-line editable-field">
							<span class="extra-label">Started</span>
							{#if editingField === 'start_date'}
								<input
									type="datetime-local"
									class="extra-field-input"
									bind:value={editFieldText}
									onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); saveField('start_date'); } else if (e.key === 'Escape') { e.stopPropagation(); editingField = null; } }}
									onblur={() => saveField('start_date')}
									autofocus
								/>
							{:else}
								<!-- svelte-ignore a11y_no_static_element_interactions -->
								<span class="extra-field-value" class:empty={!data.start_date} onclick={() => { editingField = 'start_date'; editFieldText = data.start_date ? data.start_date.slice(0, 16) : ''; }}>
									{data.start_date ? new Date(data.start_date).toLocaleString() : 'Add start date...'}
								</span>
							{/if}
						</div>
					{:else if entityType === 'plan'}
						{#if data.start_date || data.end_date}
							<div class="extra-line">
								{#if data.start_date}<span class="extra-label">Start</span> {data.start_date}{/if}
								{#if data.start_date && data.end_date}<span class="extra-sep">&mdash;</span>{/if}
								{#if data.end_date}<span class="extra-label">End</span> {data.end_date}{/if}
							</div>
						{/if}
						{#if data.motivation}<div class="extra-line"><span class="extra-label">Motivation</span> {data.motivation}</div>{/if}
						{#if data.outcome}<div class="extra-line"><span class="extra-label">Outcome</span> {data.outcome}</div>{/if}

						<!-- Activities — default collection -->
						<div class="plan-collection-section">
							<div class="plan-collection-header">
								{#if defaultActivityCollection && editingSectionKey === collectionKey(defaultActivityCollection.collectionId)}
									<input
										type="text"
										class="edit-section-input"
										bind:value={editSectionText}
										onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleRenameCollection(defaultActivityCollection.collectionId, editSectionText); } else if (e.key === 'Escape') { e.stopPropagation(); editingSectionKey = null; } }}
										onblur={() => handleRenameCollection(defaultActivityCollection.collectionId, editSectionText)}
										autofocus
									/>
								{:else}
									<!-- svelte-ignore a11y_click_events_have_key_events -->
									<!-- svelte-ignore a11y_no_static_element_interactions -->
									<span class="items-label" onclick={() => { if (defaultActivityCollection) startRenameCollection(defaultActivityCollection.collectionId, defaultActivityCollection.title); }}>{defaultActivityCollection?.title ?? 'Activities'}</span>
								{/if}
								{#if totalActivityCount > 0}
									<span class="plan-collection-count">{totalActivityCount}</span>
								{/if}
							</div>
							<!-- Default activities (no named collection) -->
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<div
								class="drop-zone"
								class:drop-zone-active={dragOverTarget === 'default'}
								ondragover={(e) => handleSectionDragOver(e, 'default')}
								ondragleave={() => handleSectionDragLeave('default')}
								ondrop={(e) => handleSectionDrop(e, 'default')}
							>
								{#each defaultActivityItems as activity (activity.id)}
									<!-- svelte-ignore a11y_no_static_element_interactions -->
									<div
										class="plan-entity-row"
										class:dragging={draggingActivityId === activity.id}
										draggable="true"
										ondragstart={(e) => handleActivityDragStart(e, activity.id)}
										ondragend={handleActivityDragEnd}
									>
										<span class="drag-handle">⠿</span>
										<input type="checkbox" checked={activity.status === 'done'} onchange={() => handleToggleActivityDone(activity)} />
										<!-- svelte-ignore a11y_click_events_have_key_events -->
										<span
											class="plan-entity-name"
											class:done={activity.status === 'done'}
											onclick={() => openNestedDetail('activity', activity.id)}
										>{activity.title}</span>
										<button class="btn-remove-item" onclick={() => handleRemoveActivity(activity.id)}>&times;</button>
									</div>
								{/each}
								<div class="inline-create">
									<input
										type="text"
										class="inline-create-input"
										placeholder="New activity..."
										value={getDefaultInlineText()}
										oninput={(e) => setDefaultInlineText(e.currentTarget.value)}
										onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleCreateActivityInDefaultCollection(); } }}
									/>
								</div>
							</div>
							<!-- Named activity collections -->
							{#each namedActivityCollections as coll (coll.collectionId)}
								<div class="section-header-bar">
									{#if editingSectionKey === collectionKey(coll.collectionId)}
										<input
											type="text"
											class="edit-section-input"
											bind:value={editSectionText}
											onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleRenameCollection(coll.collectionId, editSectionText); } else if (e.key === 'Escape') { e.stopPropagation(); editingSectionKey = null; } }}
											onblur={() => handleRenameCollection(coll.collectionId, editSectionText)}
											autofocus
										/>
									{:else}
										<!-- svelte-ignore a11y_click_events_have_key_events -->
										<!-- svelte-ignore a11y_no_static_element_interactions -->
										<span class="section-header-name" onclick={() => startRenameCollection(coll.collectionId, coll.title)}>{coll.title}</span>
									{/if}
									<button class="btn-delete-section" onclick={() => handleDeleteCollection(coll.collectionId)}>&times;</button>
								</div>
								<!-- svelte-ignore a11y_no_static_element_interactions -->
								<div
									class="drop-zone"
									class:drop-zone-active={dragOverTarget === coll.collectionId}
									ondragover={(e) => handleSectionDragOver(e, coll.collectionId)}
									ondragleave={() => handleSectionDragLeave(coll.collectionId)}
									ondrop={(e) => handleSectionDrop(e, coll.collectionId)}
								>
									{#each coll.items as item (item.itemId)}
										{@const activity = getEntityData('activity', item.memberEntityId)}
										{#if activity}
											<!-- svelte-ignore a11y_no_static_element_interactions -->
											<div
												class="plan-entity-row"
												class:dragging={draggingActivityId === activity.id}
												draggable="true"
												ondragstart={(e) => handleActivityDragStart(e, activity.id)}
												ondragend={handleActivityDragEnd}
											>
												<span class="drag-handle">⠿</span>
												<input type="checkbox" checked={activity.status === 'done'} onchange={() => handleToggleActivityDone(activity)} />
												<!-- svelte-ignore a11y_click_events_have_key_events -->
												<span
													class="plan-entity-name"
													class:done={activity.status === 'done'}
													onclick={() => openNestedDetail('activity', activity.id)}
												>{activity.title}</span>
												<button class="btn-remove-item" onclick={() => handleRemoveActivity(activity.id)}>&times;</button>
											</div>
										{/if}
									{/each}
									{#if coll.items.length === 0 && draggingActivityId != null}
										<div class="drop-zone-hint">Drop here</div>
									{/if}
									<div class="inline-create">
										<input
											type="text"
											class="inline-create-input"
											placeholder="New activity..."
											value={getInlineText(coll.collectionId)}
											oninput={(e) => setInlineText(coll.collectionId, e.currentTarget.value)}
											onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleCreateActivityInCollection(coll.collectionId); } }}
										/>
									</div>
								</div>
							{/each}
						</div>

						<!-- Sources collection -->
						<div class="plan-collection-section">
							<div class="plan-collection-header">
								{#if sourcesCollection && editingSectionKey === collectionKey(sourcesCollection.collectionId)}
									<input
										type="text"
										class="edit-section-input"
										bind:value={editSectionText}
										onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleRenameCollection(sourcesCollection.collectionId, editSectionText); } else if (e.key === 'Escape') { e.stopPropagation(); editingSectionKey = null; } }}
										onblur={() => handleRenameCollection(sourcesCollection.collectionId, editSectionText)}
										autofocus
									/>
								{:else}
									<!-- svelte-ignore a11y_click_events_have_key_events -->
									<!-- svelte-ignore a11y_no_static_element_interactions -->
									<span class="items-label" onclick={() => { if (sourcesCollection) startRenameCollection(sourcesCollection.collectionId, sourcesCollection.title); }}>{sourcesCollection?.title ?? 'Sources'}</span>
								{/if}
								{#if planLinkedSources.length > 0}
									<span class="plan-collection-count">{planLinkedSources.length}</span>
								{/if}
							</div>
							{#each planLinkedSources as source (source.id)}
								<div class="plan-entity-row">
									<!-- svelte-ignore a11y_click_events_have_key_events -->
									<!-- svelte-ignore a11y_no_static_element_interactions -->
									<span class="plan-entity-name" onclick={() => openNestedDetail('source', source.id)}>{source.title}</span>
									<button class="btn-remove-item" onclick={() => handleRemovePlanSource(source.itemId)}>&times;</button>
								</div>
							{/each}
							{#if addingSourceSearch}
								<div class="add-item-form">
									<input
										type="text"
										class="add-item-input"
										placeholder="Search or create source..."
										bind:value={sourceSearchText}
										onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); handleSourceSearchSubmit(); } else if (e.key === 'Escape') { e.stopPropagation(); addingSourceSearch = false; sourceSearchText = ''; } }}
										autofocus
									/>
									{#if sourceSearchResults.length > 0}
										<div class="add-item-results">
											{#each sourceSearchResults as result}
												<button class="add-item-result" onclick={() => handleAddPlanSource(result.id)}>
													{result.title}
												</button>
											{/each}
										</div>
									{/if}
								</div>
							{:else}
								<button class="btn-add-entity" onclick={() => { addingSourceSearch = true; sourceSearchText = ''; }}>+ Add source</button>
							{/if}
						</div>

						<!-- Actors collection -->
						<div class="plan-collection-section">
							<div class="plan-collection-header">
								{#if actorsCollection && editingSectionKey === collectionKey(actorsCollection.collectionId)}
									<input
										type="text"
										class="edit-section-input"
										bind:value={editSectionText}
										onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleRenameCollection(actorsCollection.collectionId, editSectionText); } else if (e.key === 'Escape') { e.stopPropagation(); editingSectionKey = null; } }}
										onblur={() => handleRenameCollection(actorsCollection.collectionId, editSectionText)}
										autofocus
									/>
								{:else}
									<!-- svelte-ignore a11y_click_events_have_key_events -->
									<!-- svelte-ignore a11y_no_static_element_interactions -->
									<span class="items-label" onclick={() => { if (actorsCollection) startRenameCollection(actorsCollection.collectionId, actorsCollection.title); }}>{actorsCollection?.title ?? 'Actors'}</span>
								{/if}
								{#if planLinkedActors.length > 0}
									<span class="plan-collection-count">{planLinkedActors.length}</span>
								{/if}
							</div>
							{#each planLinkedActors as actor (actor.id)}
								<div class="plan-entity-row">
									<!-- svelte-ignore a11y_click_events_have_key_events -->
									<!-- svelte-ignore a11y_no_static_element_interactions -->
									<span class="plan-entity-name" onclick={() => openNestedDetail('actor', actor.id)}>
										{actor.full_name}{#if actor.role}<span class="plan-actor-role"> &middot; {actor.role}</span>{/if}
									</span>
									<button class="btn-remove-item" onclick={() => handleRemovePlanActor(actor.itemId)}>&times;</button>
								</div>
							{/each}
							{#if addingActorSearch}
								<div class="add-item-form">
									<input
										type="text"
										class="add-item-input"
										placeholder="Search or create actor..."
										bind:value={actorSearchText}
										onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); handleActorSearchSubmit(); } else if (e.key === 'Escape') { e.stopPropagation(); addingActorSearch = false; actorSearchText = ''; } }}
										autofocus
									/>
									{#if actorSearchResults.length > 0}
										<div class="add-item-results">
											{#each actorSearchResults as result}
												<button class="add-item-result" onclick={() => handleAddPlanActor(result.id)}>
													{result.title}
												</button>
											{/each}
										</div>
									{/if}
								</div>
							{:else}
								<button class="btn-add-entity" onclick={() => { addingActorSearch = true; actorSearchText = ''; }}>+ Add actor</button>
							{/if}
						</div>

						<!-- Unified collections (mixed entity types) -->
						{#each unifiedCollections as coll (coll.collectionId)}
							<div class="plan-collection-section">
								<div class="section-header-bar">
									{#if editingSectionKey === collectionKey(coll.collectionId)}
										<input type="text" class="edit-section-input"
											bind:value={editSectionText}
											onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleRenameCollection(coll.collectionId, editSectionText); } else if (e.key === 'Escape') { e.stopPropagation(); editingSectionKey = null; } }}
											onblur={() => handleRenameCollection(coll.collectionId, editSectionText)}
											autofocus />
									{:else}
										<!-- svelte-ignore a11y_click_events_have_key_events -->
										<!-- svelte-ignore a11y_no_static_element_interactions -->
										<span class="section-header-name" onclick={() => startRenameCollection(coll.collectionId, coll.title)}>{coll.title}</span>
									{/if}
									<button class="btn-delete-section" onclick={() => handleDeleteUnifiedCollection(coll.collectionId)}>&times;</button>
								</div>
								<!-- Mixed items -->
								{#each coll.items as item (item.itemId)}
									{@const entity = getEntityData(item.memberEntityType, item.memberEntityId)}
									{#if entity}
										<div class="plan-entity-row">
											{#if item.memberEntityType === 'activity'}
												<input type="checkbox" checked={entity.status === 'done'} onchange={() => handleToggleActivityDone(entity)} />
											{/if}
											<EntityIcon type={item.memberEntityType} size={10} />
											<!-- svelte-ignore a11y_click_events_have_key_events -->
											<!-- svelte-ignore a11y_no_static_element_interactions -->
											<span class="plan-entity-name" onclick={() => openNestedDetail(item.memberEntityType, item.memberEntityId)}>
												{item.memberEntityType === 'actor' ? entity.full_name : entity.title}
											</span>
											<button class="btn-remove-item" onclick={() => handleRemoveUnifiedItem(item.itemId)}>&times;</button>
										</div>
									{/if}
								{/each}
								<!-- Inline create activity -->
								<div class="inline-create">
									<input type="text" class="inline-create-input" placeholder="New activity..."
										value={getInlineText(coll.collectionId)}
										oninput={(e) => setInlineText(coll.collectionId, e.currentTarget.value)}
										onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleCreateEntityInUnifiedCollection(coll.collectionId); } }} />
								</div>
							</div>
						{/each}

						{#if addingSectionFor === 'collection'}
							<div class="inline-create">
								<input type="text" class="inline-create-input" placeholder="Collection name..."
									bind:value={newSectionName}
									onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleCreateCollection(); } else if (e.key === 'Escape') { e.stopPropagation(); addingSectionFor = null; newSectionName = ''; } }}
									onblur={handleCreateCollection}
									autofocus />
							</div>
						{:else}
							<button class="btn-add-section" onclick={() => { addingSectionFor = 'collection'; newSectionName = ''; }}>+ Collection</button>
						{/if}
					{/if}

					<!-- Collection items -->
					{#if entityType === 'collection'}
						<div class="items-section">
							<div class="items-header-row">
								<span class="items-label">Items</span>
								<button class="btn-add-item" onclick={() => { addingItem = !addingItem; addSearch = ''; }}>+</button>
							</div>
							{#if addingItem}
								<div class="add-item-form">
									<input
										type="text"
										class="add-item-input"
										placeholder="Search {collectionMemberType}s..."
										bind:value={addSearch}
										onkeydown={(e) => { if (e.key === 'Escape') { e.stopPropagation(); addingItem = false; addSearch = ''; } }}
										autofocus
									/>
									{#if addSearchResults.length > 0}
										<div class="add-item-results">
											{#each addSearchResults as result}
												<button class="add-item-result" onclick={() => handleAddItem(result.id)}>
													{result.title}
												</button>
											{/each}
										</div>
									{/if}
								</div>
							{/if}
							{#each collectionItems as item}
								<div class="collection-item">
									<span class="collection-item-title">{item.title}</span>
									{#if item.status}
										{@const ss = getStatusStyle(item.status)}
										<span class="status-badge-small" style:background={ss.bg} style:color={ss.color}>{formatStatus(item.status)}</span>
									{/if}
									<button class="btn-remove-item" onclick={() => handleRemoveItem(item.itemId)}>&times;</button>
								</div>
							{/each}
						</div>
					{/if}

					<!-- Tag badges -->
					{#if entityTags.length > 0}
						<div class="tag-badges">
							{#each entityTags as tag (tag.id)}
								<TagBadge {tag} removable onRemove={() => handleDetach(tag)} />
							{/each}
						</div>
					{/if}
				</div>

				<!-- Timestamp -->
				{#if data.created_at}
					<Timestamp date={data.created_at} />
				{/if}
			</div>
		{:else}
			<div class="detail-widget">
				<p class="not-found">Entity not found.</p>
				<button class="btn-close" onclick={onClose}>&times;</button>
			</div>
		{/if}
	</div>
</div>

<ConfirmDialog
	open={confirmDelete}
	message="Delete this {entityType}? This cannot be undone."
	onConfirm={handleDelete}
	onCancel={() => confirmDelete = false}
/>

{#if collectionDeleteConfirm !== null}
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<div class="coll-dialog-overlay" onclick={() => collectionDeleteConfirm = null} onkeydown={(e) => e.key === 'Escape' && (collectionDeleteConfirm = null)} role="dialog" tabindex="-1">
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<div class="coll-dialog-content" onclick={(e) => e.stopPropagation()} role="document">
			<p class="coll-dialog-title">Delete this collection?</p>
			<p class="coll-dialog-message">Do you also want to delete all member entities inside this collection?</p>
			<div class="coll-dialog-actions">
				<button class="coll-btn coll-btn-cancel" onclick={() => collectionDeleteConfirm = null}>Cancel</button>
				<button class="coll-btn coll-btn-keep" onclick={() => handleCollectionDeleteConfirm(false)}>Keep entities</button>
				<button class="coll-btn coll-btn-delete-all" onclick={() => handleCollectionDeleteConfirm(true)}>Delete all</button>
			</div>
		</div>
	</div>
{/if}

{#if nestedDetail && !nested}
	<svelte:self
		entityType={nestedDetail.type}
		entityId={nestedDetail.id}
		onClose={() => nestedDetail = null}
		onDeleted={async () => { nestedDetail = null; await Promise.all([loadPlanCollections(), loadPlans(), loadActivities(), loadCollections()]); }}
		nested={true}
		panelSize="small"
	/>
{/if}

<style>
	.detail-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.4);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}
	.nested-overlay {
		z-index: 1100;
		background: rgba(0, 0, 0, 0.3);
	}
	.detail-panel {
		width: 500px;
		height: 70vh;
		display: flex;
		flex-direction: column;
	}
	.panel-small {
		width: 450px;
		height: 60vh;
	}

	/* Colored frame per entity type — matching Card tab / NotepadEditPanel */
	.detail-widget {
		display: flex;
		flex-direction: column;
		gap: 8px;
		padding: 12px 14px;
		border-radius: 8px;
		box-shadow: 0 8px 30px rgba(0, 0, 0, 0.2);
		flex: 1;
		min-height: 0;
		overflow: hidden;
		background: white;
		border: 1px solid #e5e7eb;
	}
	.note-widget { background: #ecfdf5; border: 1px solid #d1fae5; }
	.activity-widget { background: #f5f3ff; border: 1px solid #ddd6fe; }
	.source-widget { background: #fffbeb; border: 1px solid #fde68a; }
	.plan-widget { background: #f0f7fa; border: 1px solid #b3d9e6; }
	.project-widget { background: #eff6ff; border: 1px solid #bfdbfe; }
	.log-widget { background: #faf8f5; border: 1px solid #e8e0d4; }
	.actor-widget { background: #fef2f2; border: 1px solid #fecaca; }
	.collection-widget { background: #f5f3fa; border: 1px solid #d4cfe6; }

	/* ── Title row ── */
	.title-row {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.title-display {
		flex: 1;
		font-weight: 600;
		font-size: 0.95rem;
		color: #111827;
		cursor: text;
		padding: 4px 6px;
		border: 1px solid transparent;
		border-radius: 4px;
	}
	.title-input {
		flex: 1;
		padding: 4px 6px;
		border: 1px solid #4a90a4;
		border-radius: 4px;
		font-size: 0.95rem;
		font-weight: 600;
		color: #111827;
		outline: none;
		box-sizing: border-box;
		background: white;
	}
	.status-btn {
		font-size: 0.65rem;
		padding: 2px 8px;
		border-radius: 4px;
		flex-shrink: 0;
		border: 1px solid transparent;
		cursor: pointer;
		font-weight: 500;
	}
	.status-btn:hover { filter: brightness(0.95); }
	.btn-close {
		padding: 2px 6px;
		font-size: 1.1rem;
		color: #9ca3af;
		background: none;
		border: none;
		cursor: pointer;
		line-height: 1;
		flex-shrink: 0;
	}
	.btn-close:hover { color: #ef4444; }

	/* ── Action bar ── */
	.action-bar {
		display: flex;
		gap: 6px;
	}
	.btn-action {
		font-size: 0.7rem;
		padding: 2px 8px;
		border-radius: 4px;
		border: 1px solid #d1d5db;
		cursor: pointer;
	}
	.btn-tags { background: #f9fafb; color: #6b7280; }
	.btn-active { background: #f3f4f6; color: #6b7280; }
	.btn-active.active { background: #dcfce7; color: #16a34a; border-color: #bbf7d0; }
	.btn-archive { background: #fef3c7; color: #92400e; }
	.btn-delete { background: #fee2e2; color: #ef4444; border-color: #fecaca; }

	/* ── Tag section ── */
	.tag-section {
		padding: 8px;
		background: rgba(255,255,255,0.5);
		border-radius: 6px;
	}

	/* ── Scrollable content area ── */
	.content-area {
		display: flex;
		flex-direction: column;
		gap: 8px;
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		padding: 8px;
		background: rgba(255,255,255,0.4);
		border-radius: 6px;
	}

	/* Text display / edit */
	.text-display {
		font-size: 0.82rem;
		color: #374151;
		white-space: pre-wrap;
		line-height: 1.5;
		cursor: text;
		padding: 4px 6px;
		border: 1px solid transparent;
		border-radius: 4px;
		flex: 0 0 auto;
	}
	.text-placeholder {
		color: #9ca3af;
		font-style: italic;
	}
	.text-input {
		padding: 4px 6px;
		border: 1px solid #4a90a4;
		border-radius: 4px;
		font-size: 0.82rem;
		color: #374151;
		outline: none;
		resize: vertical;
		font-family: inherit;
		box-sizing: border-box;
		background: white;
		line-height: 1.5;
		width: 100%;
		height: 88px;
		flex: 0 0 auto;
	}

	/* ── Extra fields ── */
	.extra-line {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 0.78rem;
		color: #4b5563;
		flex-wrap: wrap;
	}
	.extra-line.editable-field {
		min-height: 28px;
	}
	.extra-label {
		font-size: 0.65rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.03em;
		color: #9ca3af;
		flex-shrink: 0;
		width: 70px;
	}
	.extra-field-value {
		flex: 1;
		min-width: 0;
		cursor: pointer;
		padding: 2px 4px;
		border-radius: 4px;
		transition: background 0.12s;
		word-break: break-word;
	}
	.extra-field-value:hover {
		background: #f3f4f6;
	}
	.extra-field-value.empty {
		color: #d1d5db;
	}
	.extra-field-input {
		flex: 1;
		min-width: 0;
		padding: 3px 6px;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		font-size: 0.78rem;
		outline: none;
		font-family: inherit;
	}
	.extra-field-input:focus {
		border-color: #6b7280;
	}
	.extra-sep { color: #9ca3af; }
	.link { color: #3b82f6; text-decoration: none; word-break: break-all; }
	.link:hover { text-decoration: underline; }
	.emoji-row { display: flex; gap: 8px; font-size: 1.1rem; }
	.emoji-picker-row { display: flex; align-items: center; gap: 4px; padding: 2px 0; }
	.emoji-picker-label { font-size: 0.7rem; color: #6b7280; font-weight: 500; min-width: 50px; flex-shrink: 0; }
	.emoji-chips { display: flex; gap: 2px; flex-wrap: wrap; }
	.emoji-chip { font-size: 0.9rem; padding: 1px 3px; border: 1px solid transparent; border-radius: 4px; background: none; cursor: pointer; line-height: 1; transition: all 0.1s; }
	.emoji-chip:hover { background: #f3f4f6; }
	.emoji-chip.selected { border-color: #3b82f6; background: #eff6ff; }
	.status-value { font-weight: 500; color: #374151; }

	/* ── Items section (plan activities, collection items) ── */
	.items-section {
		display: flex;
		flex-direction: column;
		gap: 3px;
		margin-top: 4px;
	}
	.items-header-row {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.items-label {
		font-size: 0.7rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.03em;
		color: #9ca3af;
		cursor: pointer;
	}
	.items-label:hover {
		color: #6b7280;
	}
	.group-header {
		font-size: 0.72rem;
		font-weight: 600;
		color: #6b7280;
		margin-top: 6px;
		padding-bottom: 2px;
		border-bottom: 1px solid rgba(0,0,0,0.08);
	}
	.list-item {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 2px 0;
		font-size: 0.78rem;
	}
	.list-item input[type="checkbox"] { pointer-events: none; margin: 0; }
	.list-item-text { color: #374151; }
	.list-item-text.done { text-decoration: line-through; color: #9ca3af; }

	/* ── Plan collection sections ── */
	.plan-collection-section {
		padding: 8px;
		background: rgba(255,255,255,0.35);
		border-radius: 6px;
		display: flex;
		flex-direction: column;
		gap: 3px;
	}
	.plan-collection-header {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.plan-collection-count {
		font-size: 0.6rem;
		font-weight: 600;
		background: rgba(0,0,0,0.08);
		color: #6b7280;
		padding: 1px 5px;
		border-radius: 8px;
	}
	.plan-entity-row {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 2px 0;
		font-size: 0.78rem;
	}
	.plan-entity-name {
		flex: 1;
		color: #374151;
		cursor: pointer;
		padding: 1px 4px;
		border-radius: 3px;
	}
	.plan-entity-name:hover { background: rgba(0,0,0,0.05); }
	.plan-entity-name.done { text-decoration: line-through; color: #9ca3af; }
	.plan-actor-role {
		font-size: 0.7rem;
		color: #9ca3af;
	}
	.plan-collection-empty {
		font-size: 0.75rem;
		font-style: italic;
		color: #9ca3af;
		padding: 2px 0;
	}

	/* Drag and drop */
	.drag-handle {
		cursor: grab;
		color: #d1d5db;
		font-size: 0.7rem;
		line-height: 1;
		user-select: none;
		flex-shrink: 0;
	}
	.drag-handle:hover { color: #9ca3af; }
	.plan-entity-row.dragging { opacity: 0.4; }
	.drop-zone {
		min-height: 8px;
		border-radius: 4px;
		border: 1px solid transparent;
		padding: 1px 0;
		transition: background 0.15s, border-color 0.15s;
	}
	.drop-zone-active {
		background: rgba(74, 144, 164, 0.08);
		border-color: rgba(74, 144, 164, 0.3);
	}
	.drop-zone-hint {
		text-align: center;
		font-size: 0.7rem;
		color: #9ca3af;
		padding: 4px 0;
		font-style: italic;
	}

	/* Section management */
	.section-header-bar {
		display: flex;
		align-items: center;
		gap: 4px;
		margin-top: 6px;
		padding: 3px 6px;
		background: rgba(0,0,0,0.04);
		border-left: 3px solid #4a90a4;
		border-radius: 0 4px 4px 0;
	}
	.section-header-name {
		flex: 1;
		font-size: 0.72rem;
		font-weight: 600;
		color: #4b5563;
		cursor: pointer;
		padding: 1px 2px;
		border-radius: 3px;
	}
	.section-header-name:hover { background: rgba(0,0,0,0.06); }
	.edit-section-input {
		flex: 1;
		padding: 2px 4px;
		border: 1px solid #4a90a4;
		border-radius: 3px;
		font-size: 0.72rem;
		font-weight: 600;
		color: #4b5563;
		outline: none;
		background: white;
	}
	.btn-delete-section {
		background: none;
		border: none;
		cursor: pointer;
		color: #9ca3af;
		font-size: 0.8rem;
		padding: 0 3px;
		line-height: 1;
		flex-shrink: 0;
	}
	.btn-delete-section:hover { color: #ef4444; }
	.btn-add-section {
		padding: 3px 8px;
		font-size: 0.7rem;
		font-weight: 500;
		background: transparent;
		border: 1px dashed #d1d5db;
		border-radius: 4px;
		cursor: pointer;
		color: #9ca3af;
		margin-top: 4px;
		align-self: flex-start;
	}
	.btn-add-section:hover { border-color: #9ca3af; color: #6b7280; background: rgba(0,0,0,0.02); }
	.btn-add-entity {
		width: 100%;
		padding: 4px 8px;
		font-size: 0.75rem;
		font-weight: 500;
		background: rgba(255,255,255,0.5);
		border: 1px dashed #d1d5db;
		border-radius: 4px;
		cursor: pointer;
		color: #9ca3af;
		margin-top: 2px;
		text-align: left;
	}
	.btn-add-entity:hover { border-color: #9ca3af; color: #6b7280; background: rgba(255,255,255,0.8); }
	.inline-create {
		margin-top: 2px;
	}
	.inline-create-input {
		width: 100%;
		padding: 4px 8px;
		border: 1px dashed #d1d5db;
		border-radius: 4px;
		font-size: 0.75rem;
		color: #374151;
		outline: none;
		background: rgba(255,255,255,0.5);
		box-sizing: border-box;
	}
	.inline-create-input::placeholder { color: #9ca3af; }
	.inline-create-input:focus { border-style: solid; border-color: #4a90a4; background: white; }

	/* Collection items */
	.collection-item {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 3px 0;
		font-size: 0.78rem;
	}
	.collection-item-title { flex: 1; color: #374151; }
	.status-badge-small {
		font-size: 0.6rem;
		padding: 1px 5px;
		border-radius: 3px;
		font-weight: 500;
		flex-shrink: 0;
	}
	.btn-remove-item {
		background: none;
		border: none;
		cursor: pointer;
		color: #ef4444;
		font-size: 0.85rem;
		padding: 0 4px;
		line-height: 1;
		flex-shrink: 0;
	}
	.btn-remove-item:hover { color: #dc2626; }

	/* Add item */
	.btn-add-item {
		padding: 1px 8px;
		font-size: 0.75rem;
		font-weight: 600;
		background: rgba(255,255,255,0.6);
		border: 1px solid #d1d5db;
		border-radius: 4px;
		cursor: pointer;
		color: #6b7280;
	}
	.btn-add-item:hover { background: white; }
	.add-item-form {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.add-item-input {
		padding: 4px 8px;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		font-size: 0.78rem;
		outline: none;
		background: white;
	}
	.add-item-input:focus { border-color: #4a90a4; }
	.add-item-results {
		display: flex;
		flex-direction: column;
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 4px;
		max-height: 150px;
		overflow-y: auto;
	}
	.add-item-result {
		padding: 4px 8px;
		font-size: 0.78rem;
		text-align: left;
		background: none;
		border: none;
		cursor: pointer;
		color: #374151;
	}
	.add-item-result:hover { background: #f3f4f6; }

	/* ── Tag badges ── */
	.tag-badges {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		margin-top: 4px;
	}

	.not-found {
		text-align: center;
		color: #9ca3af;
		font-size: 0.85rem;
	}

	/* ── Entity type dot (unified collections) ── */
	.entity-type-dot {
		display: inline-block;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
		margin-right: 4px;
	}
	.entity-type-dot.activity { background: #3b82f6; }
	.entity-type-dot.source { background: #8b5cf6; }
	.entity-type-dot.actor { background: #f59e0b; }
	/* ── Collection delete dialog ── */
	.coll-dialog-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.4);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1100;
	}
	.coll-dialog-content {
		background: white;
		border-radius: 8px;
		padding: 24px;
		min-width: 340px;
		box-shadow: 0 8px 30px rgba(0, 0, 0, 0.2);
	}
	.coll-dialog-title {
		font-size: 0.95rem;
		font-weight: 600;
		margin: 0 0 8px;
		color: #111827;
	}
	.coll-dialog-message {
		font-size: 0.85rem;
		color: #6b7280;
		margin: 0 0 20px;
	}
	.coll-dialog-actions {
		display: flex;
		gap: 8px;
		justify-content: flex-end;
	}
	.coll-btn {
		padding: 8px 14px;
		border-radius: 6px;
		border: 1px solid #d1d5db;
		cursor: pointer;
		font-size: 0.82rem;
		font-weight: 500;
	}
	.coll-btn-cancel { background: white; color: #374151; }
	.coll-btn-cancel:hover { background: #f3f4f6; }
	.coll-btn-keep { background: #f0fdf4; color: #16a34a; border-color: #bbf7d0; }
	.coll-btn-keep:hover { background: #dcfce7; }
	.coll-btn-delete-all { background: #ef4444; color: white; border-color: #ef4444; }
	.coll-btn-delete-all:hover { background: #dc2626; }
</style>

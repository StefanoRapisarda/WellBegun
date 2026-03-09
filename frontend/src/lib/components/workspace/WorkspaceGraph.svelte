<script lang="ts">
	import { onMount } from 'svelte';
	import type { KnowledgeTriple, BoardNode } from '$lib/types';
	import { activeWorkspace, refreshActiveWorkspace } from '$lib/stores/workspaces';
	import { triples, loadTriples } from '$lib/stores/knowledgeGraph';
	import { projects, loadProjects } from '$lib/stores/projects';
	import { logs, loadLogs } from '$lib/stores/logs';
	import { notes, loadNotes } from '$lib/stores/notes';
	import { activities, loadActivities } from '$lib/stores/activities';
	import { sources, loadSources } from '$lib/stores/sources';
	import { actors, loadActors } from '$lib/stores/actors';
	import { plans, loadPlans } from '$lib/stores/plans';
	import { collections, loadCollections } from '$lib/stores/collections';
	import { bulkUpdatePositions, removeWorkspaceItem, addWorkspaceItem, expandEntityInWorkspace, updateWorkspaceItem } from '$lib/api/workspaces';
	import { createProject, updateProject, deleteProject } from '$lib/api/projects';
	import { createLog, updateLog, deleteLog } from '$lib/api/logs';
	import { createNote, updateNote, deleteNote } from '$lib/api/notes';
	import { createActivity, updateActivity, deleteActivity } from '$lib/api/activities';
	import { createSource, updateSource, deleteSource } from '$lib/api/sources';
	import { createActor, updateActor, deleteActor } from '$lib/api/actors';
	import { createPlan, updatePlan, deletePlan } from '$lib/api/plans';
	import { activeTab } from '$lib/stores/activeTab';
	import { panelSelection, type EntityType as PanelEntityType } from '$lib/stores/panelSelection';
	import { panels, togglePanel } from '$lib/stores/panels';
	import { get } from 'svelte/store';
	import { createCollection, updateCollection, addItem, removeItem, updateItem } from '$lib/api/collections';
	import { categories } from '$lib/stores/categories';
	import { attachTag, detachTag, getEntityTags } from '$lib/api/tags';
	import { tags, loadTags, triggerEntityTagsRefresh } from '$lib/stores/tags';
	import { workspaceInjectedResults } from '$lib/stores/workspaceQueryInjection';
	import type { Tag } from '$lib/types';
	import GraphCard from '$lib/components/graph/GraphCard.svelte';
	import GraphConnections from '$lib/components/graph/GraphConnections.svelte';
	import CollectionContainer from '$lib/components/graph/CollectionContainer.svelte';
	import {
		MINI_CARD_W, MINI_CARD_H, MINI_GAP, COLS,
		TITLE_BAR_H, CONTAINER_PADDING,
		containerWidth as ccWidth, containerHeight as ccHeight,
		containerHeightNested as ccHeightNested,
		buildVisualRows, NESTED_INDENT,
		type ContainerMember
	} from '$lib/components/graph/collectionLayout';
	import QueryPanel from '$lib/components/shared/QueryPanel.svelte';
	import GraphEditorPanel from '$lib/components/graph/GraphEditorPanel.svelte';
	import type { SearchResult } from '$lib/api/search';
	import EntityDetailPanel from '$lib/components/workspace/EntityDetailPanel.svelte';
	import ConfirmDialog from '$lib/components/shared/ConfirmDialog.svelte';
	import TagInput from '$lib/components/shared/TagInput.svelte';
	import { updateTriple, swapTripleDirection, deleteTriple } from '$lib/api/knowledge';
	import { captureGraphScreenshot } from '$lib/utils/graphScreenshot';

	const ENTITY_COLORS: Record<string, string> = {
		project: '#5c7a99',
		log: '#8b7355',
		note: '#6b8e6b',
		activity: '#b5838d',
		source: '#c9a227',
		actor: '#8b4557',
		plan: '#6b8ba3',
		collection: '#7c6f9e'
	};

	// --- Props ---
	let {
		zoom = $bindable(1),
		queryPanelOpen = $bindable(false),
		editorOpen = $bindable(false),
		selectMode = $bindable(false),
	}: {
		zoom?: number;
		queryPanelOpen?: boolean;
		editorOpen?: boolean;
		selectMode?: boolean;
	} = $props();

	// --- Canvas state ---
	let panX = $state(0);
	let panY = $state(0);
	let canvasEl: HTMLDivElement | undefined = $state();
	let viewportEl: HTMLDivElement | undefined = $state();

	// --- Drag state ---
	const DRAG_THRESHOLD = 5;
	let dragStarted = $state(false);
	let draggingCard: { type: string; id: number; startX: number; startY: number; origX: number; origY: number } | null = $state(null);
	let isPanning = $state(false);
	let panStart = $state({ x: 0, y: 0, panX: 0, panY: 0 });
	let draggingKey: string | null = $state(null);

	// --- Z-index management (bring-to-front on interact) ---
	let topZKey: string | null = $state(null);
	let zCounter = $state(1);

	// --- Drop target for drag-to-connect ---
	let dropTarget: { type: string; id: number } | null = $state(null);

	// --- Member dwell: after hovering over a member inside a collection, switch target to that member ---
	let memberDwellKey: string | null = $state(null);
	let memberDwellFired = $state(false);
	let memberDwellTimer: ReturnType<typeof setTimeout> | null = null;
	const MEMBER_DWELL_MS = 700;

	// --- Multi-selection ---
	let selectedCards = $state<Set<string>>(new Set());
	let selectionCount = $derived(selectedCards.size);
	let selectedEntities = $derived.by(() =>
		[...selectedCards].map(key => {
			const [type, idStr] = key.split(':');
			return { type, id: Number(idStr) };
		})
	);
	let groupDragOrigPositions: Map<string, { x: number; y: number }> | null = $state(null);
	let selectionRect: { startX: number; startY: number; currentX: number; currentY: number } | null = $state(null);

	// --- Bulk action state ---
	let bulkActionInProgress = $state(false);
	let showBulkDelete = $state(false);
	let showBulkTagInput = $state(false);
	let bulkTags = $state<Tag[]>([]);
	let queryPanelRef: { refresh: () => void; clearSelection: () => void } | undefined = $state();
	let queryPanelState = $state<{ results: SearchResult[]; includeArchived: boolean; showActiveRelated: boolean; hasActiveFilters: boolean }>({
		results: [],
		includeArchived: false,
		showActiveRelated: false,
		hasActiveFilters: false,
	});

	// --- Hidden connections injection ---
	let hiddenConnectionsFor: { type: string; id: number } | null = $state(null);

	let injectedResults = $derived.by(() => {
		// Priority: external injection from dashboard topics > hidden connections
		const ext = $workspaceInjectedResults;
		if (ext) return ext.results;

		if (!hiddenConnectionsFor) return undefined;
		const nodeKey = `${hiddenConnectionsFor.type}:${hiddenConnectionsFor.id}`;
		const seen = new Set<string>();
		const hiddenKeys: Array<{ type: string; id: number }> = [];
		for (const t of $triples) {
			const sk = `${t.subject_type}:${t.subject_id}`;
			const ok = `${t.object_type}:${t.object_id}`;
			if (sk === nodeKey && !boardEntityKeySet.has(ok) && !seen.has(ok)) {
				seen.add(ok);
				hiddenKeys.push({ type: t.object_type, id: t.object_id });
			}
			if (ok === nodeKey && !boardEntityKeySet.has(sk) && !seen.has(sk)) {
				seen.add(sk);
				hiddenKeys.push({ type: t.subject_type, id: t.subject_id });
			}
		}
		return hiddenKeys.map(e => ({
			type: e.type,
			id: e.id,
			title: getEntityTitle(e.type, e.id),
			description: getEntityData(e.type, e.id)?.description ?? null,
			created_at: getEntityData(e.type, e.id)?.created_at ?? '',
			updated_at: getEntityData(e.type, e.id)?.updated_at ?? '',
			tags: [] as import('$lib/types').Tag[],
		}));
	});

	// --- Detail panel ---
	let detailEntity: { type: string; id: number } | null = $state(null);

	// --- Context menu ---
	let contextMenu: { type: string; id: number; x: number; y: number } | null = $state(null);

	// --- Confirm delete ---
	let showConfirmDelete = $state(false);
	let deleteTarget: { type: string; id: number } | null = $state(null);

	// --- Pulsing ---
	let pulsingCards = $state<Set<string>>(new Set());

	// --- Save positions debounce ---
	let saveTimer: ReturnType<typeof setTimeout> | null = null;

	// --- Derived data from workspace items ---
	let wsItems = $derived($activeWorkspace?.items ?? []);
	let wsId = $derived($activeWorkspace?.id ?? 0);

	// Node map for positions
	let nodeMap = $derived.by(() => {
		const map = new Map<string, { entity_type: string; entity_id: number; x: number; y: number; collapsed: boolean; id: number }>();
		for (const item of wsItems) {
			map.set(`${item.entity_type}:${item.entity_id}`, item);
		}
		return map;
	});

	// Workspace entity key set for query panel
	let boardEntityKeySet = $derived(new Set(wsItems.map(n => `${n.entity_type}:${n.entity_id}`)));

	// Extended entity set: workspace items + contained collection members
	let visibleEntityKeys = $derived.by(() => {
		const s = new Set(boardEntityKeySet);
		for (const coll of $collections) {
			const collKey = `collection:${coll.id}`;
			if (!boardEntityKeySet.has(collKey)) continue;
			for (const item of (coll.items || [])) {
				s.add(`${item.member_entity_type}:${item.member_entity_id}`);
			}
		}
		return s;
	});

	// Visible triples: only those where BOTH endpoints are in workspace or rendered as collection members
	let visibleTriples = $derived(
		$triples.filter(t =>
			visibleEntityKeys.has(`${t.subject_type}:${t.subject_id}`) &&
			visibleEntityKeys.has(`${t.object_type}:${t.object_id}`)
		)
	);

	// Hidden connections count per node (unique off-board entities connected via triples)
	// Excludes collection members that are rendered inside their container
	let hiddenConnectionCounts = $derived.by(() => {
		// Build set of entity keys rendered as collection members
		const renderedMembers = new Set<string>();
		for (const coll of $collections) {
			const collKey = `collection:${coll.id}`;
			if (!boardEntityKeySet.has(collKey)) continue;
			for (const item of (coll.items || [])) {
				const data = getEntityData(item.member_entity_type, item.member_entity_id);
				if (data) {
					renderedMembers.add(`${item.member_entity_type}:${item.member_entity_id}`);
				}
			}
		}

		const neighbors = new Map<string, Set<string>>();
		for (const t of $triples) {
			const sk = `${t.subject_type}:${t.subject_id}`;
			const ok = `${t.object_type}:${t.object_id}`;
			const sIn = boardEntityKeySet.has(sk);
			const oIn = boardEntityKeySet.has(ok);
			if (sIn && !oIn && !renderedMembers.has(ok)) {
				if (!neighbors.has(sk)) neighbors.set(sk, new Set());
				neighbors.get(sk)!.add(ok);
			}
			if (oIn && !sIn && !renderedMembers.has(sk)) {
				if (!neighbors.has(ok)) neighbors.set(ok, new Set());
				neighbors.get(ok)!.add(sk);
			}
		}
		const counts = new Map<string, number>();
		for (const [key, set] of neighbors) {
			counts.set(key, set.size);
		}
		return counts;
	});

	let injectedLabel = $derived.by(() => {
		const ext = $workspaceInjectedResults;
		if (ext) return ext.label;

		const target = hiddenConnectionsFor;
		if (!target) return undefined;
		const count = hiddenConnectionCounts.get(`${target.type}:${target.id}`) ?? 0;
		return `${count} hidden connections`;
	});

	// Collapse support — only explicitly collapsed nodes suppress their own connections
	let collapsedNodes = $derived.by(() => {
		const explicit = new Set<string>();
		for (const item of wsItems) {
			if (item.collapsed) explicit.add(`${item.entity_type}:${item.entity_id}`);
		}
		return explicit;
	});

	let hiddenByCollapse = $derived.by(() => {
		const roots = new Set<string>();
		for (const item of wsItems) {
			if (item.collapsed) roots.add(`${item.entity_type}:${item.entity_id}`);
		}
		if (roots.size === 0) return new Set<string>();

		const children = new Map<string, string[]>();
		for (const t of visibleTriples) {
			const subKey = `${t.subject_type}:${t.subject_id}`;
			const objKey = `${t.object_type}:${t.object_id}`;
			if (!children.has(subKey)) children.set(subKey, []);
			children.get(subKey)!.push(objKey);
		}

		const descendants = new Set<string>();
		const queue = [...roots];
		while (queue.length > 0) {
			const key = queue.shift()!;
			const kids = children.get(key);
			if (!kids) continue;
			for (const child of kids) {
				if (!descendants.has(child)) {
					// Never hide explicit workspace items via triple-based collapse;
					// they were placed by the user and should remain visible.
					// Only collection member hiding (below) may hide workspace items.
					if (boardEntityKeySet.has(child)) continue;
					descendants.add(child);
					queue.push(child);
				}
			}
		}

		// Also hide members of collapsed collection containers
		// (since collection→member triples are filtered from visibleTriples)
		for (const coll of $collections) {
			const collKey = `collection:${coll.id}`;
			if (!roots.has(collKey)) continue;
			for (const item of coll.items ?? []) {
				const memberKey = `${item.member_entity_type}:${item.member_entity_id}`;
				if (boardEntityKeySet.has(memberKey)) {
					descendants.add(memberKey);
				}
			}
		}

		return descendants;
	});

	// Visible nodes — all items except hidden by collapse
	let visibleNodes = $derived(
		wsItems.filter(n => !hiddenByCollapse.has(`${n.entity_type}:${n.entity_id}`))
	);

	let visibleNodeKeys = $derived(new Set(visibleNodes.map(n => `${n.entity_type}:${n.entity_id}`)));

	// --- Collection container derivations ---
	// Nested collection expanded states (local UI state, collapsed by default)
	let nestedExpandedMap = $state<Record<number, boolean>>({});

	function handleNestedToggleCollapse(collectionId: number) {
		nestedExpandedMap = { ...nestedExpandedMap, [collectionId]: !nestedExpandedMap[collectionId] };
	}

	// Build member data for a collection, attaching nested info for collection-type members
	function buildMembers(collId: number): ContainerMember[] {
		const coll = $collections.find(c => c.id === collId);
		if (!coll) return [];
		const members: ContainerMember[] = [];
		for (const item of (coll.items || [])) {
			const data = getEntityData(item.member_entity_type, item.member_entity_id);
			if (!data) continue;
			const member: ContainerMember = {
				entityType: item.member_entity_type,
				entityId: item.member_entity_id,
				title: getEntityTitle(item.member_entity_type, item.member_entity_id),
				status: item.status ?? data.status,
				itemId: item.id,
			};
			if (item.member_entity_type === 'collection') {
				const nestedColl = $collections.find(c => c.id === item.member_entity_id);
				if (nestedColl) {
					member.nestedMembers = buildMembers(nestedColl.id);
					member.nestedExpanded = !!nestedExpandedMap[nestedColl.id];
					member.nestedStatusCycle = getStatusCycle(nestedColl.id);
				}
			}
			members.push(member);
		}
		return members;
	}

	// Map collection key → { collectionId, members[] } for collections with workspace members
	let collectionContainers = $derived.by(() => {
		const map = new Map<string, { collectionId: number; members: ContainerMember[] }>();
		for (const coll of $collections) {
			const collKey = `collection:${coll.id}`;
			if (!boardEntityKeySet.has(collKey)) continue;
			const members = buildMembers(coll.id);
			// Always add — even empty collections render as containers (title bar only)
			map.set(collKey, { collectionId: coll.id, members });
		}
		return map;
	});

	function getStatusCycle(collectionId: number): string[] {
		const coll = $collections.find(c => c.id === collectionId);
		if (!coll) return ['todo', 'in_progress', 'done'];
		const cat = $categories.find(c => c.id === coll.category_id);
		if (cat && cat.statuses.length > 0) {
			return [...cat.statuses].sort((a, b) => a.position - b.position).map(s => s.value);
		}
		return ['todo', 'in_progress', 'done'];
	}

	async function handleStatusChange(itemId: number, newStatus: string) {
		await updateItem(itemId, { status: newStatus });

		// Sync the underlying entity's own status to stay consistent
		for (const col of $collections) {
			const ci = col.items.find(i => i.id === itemId);
			if (ci) {
				if (ci.member_entity_type === 'activity') {
					await updateActivity(ci.member_entity_id, { status: newStatus });
					await loadActivities();
				} else if (ci.member_entity_type === 'source') {
					await updateSource(ci.member_entity_id, { status: newStatus });
					await loadSources();
				}
				break;
			}
		}

		await loadCollections();
	}

	// Keys of entities rendered inside containers (not standalone)
	// Exclude the currently-dragged member so it pops out as a standalone card during drag
	let containedMemberKeys = $derived.by(() => {
		const s = new Set<string>();
		for (const [, entry] of collectionContainers) {
			for (const m of entry.members) {
				const mk = `${m.entityType}:${m.entityId}`;
				if (mk === draggingKey && !groupDragOrigPositions) continue; // dragging member solo
				s.add(mk);
			}
		}
		return s;
	});

	// Filtered containers for rendering — excludes dragged member from its container
	let renderContainers = $derived.by(() => {
		if (!draggingKey || groupDragOrigPositions) return collectionContainers;
		const filtered = new Map<string, { collectionId: number; members: ContainerMember[] }>();
		for (const [k, entry] of collectionContainers) {
			const filteredMembers = entry.members.filter(m => `${m.entityType}:${m.entityId}` !== draggingKey);
			filtered.set(k, { ...entry, members: filteredMembers });
		}
		return filtered;
	});

	// Keys of collections rendered as containers
	let containerCollectionKeys = $derived(new Set(collectionContainers.keys()));

	// Standalone nodes = visible minus contained members minus container collections
	let standaloneNodes = $derived(
		visibleNodes.filter(n => {
			const key = `${n.entity_type}:${n.entity_id}`;
			return !containedMemberKeys.has(key) && !containerCollectionKeys.has(key);
		})
	);

	// Container nodes = visible nodes matching container collection keys
	let containerNodes = $derived(
		visibleNodes.filter(n => {
			const key = `${n.entity_type}:${n.entity_id}`;
			return containerCollectionKeys.has(key) && !containedMemberKeys.has(key);
		})
	);

	// Augmented nodeMap with container and member dimensions
	// Uses renderContainers so dragged members are excluded from layout
	let augmentedNodeMap = $derived.by(() => {
		const map = new Map<string, BoardNode>();
		// Copy all from base nodeMap — workspace items have the right shape
		for (const [key, val] of nodeMap) {
			map.set(key, { ...val, w: undefined, h: undefined, created_at: (val as any).added_at ?? '', updated_at: '' });
		}
		// Override container collection entries with computed dimensions
		for (const [collKey, entry] of renderContainers) {
			const existing = map.get(collKey);
			if (existing) {
				existing.w = ccWidth();
				existing.h = ccHeightNested(entry.members, existing.collapsed);
			}
		}
		// Set member entries with absolute positions inside their container
		// Uses buildVisualRows so expanded nested collections push subsequent rows down
		for (const [collKey, entry] of renderContainers) {
			const container = map.get(collKey);
			if (!container) continue;
			const rows = buildVisualRows(entry.members);
			rows.forEach((row, i) => {
				const m = row.member;
				const memberKey = `${m.entityType}:${m.entityId}`;
				const mx = container.x + CONTAINER_PADDING + row.indent * NESTED_INDENT;
				const my = container.y + TITLE_BAR_H + CONTAINER_PADDING + i * (MINI_CARD_H + MINI_GAP);
				const mw = MINI_CARD_W - row.indent * NESTED_INDENT;
				let memberNode = map.get(memberKey);
				if (!memberNode) {
					memberNode = {
						id: -m.entityId, entity_type: m.entityType, entity_id: m.entityId,
						x: mx, y: my, w: mw, h: MINI_CARD_H,
						collapsed: false, created_at: '', updated_at: ''
					};
					map.set(memberKey, memberNode);
				} else {
					memberNode.x = mx;
					memberNode.y = my;
					memberNode.w = mw;
					memberNode.h = MINI_CARD_H;
				}
			});
		}
		return map;
	});

	// Map each contained member to its container collection key
	let memberToContainerKey = $derived.by(() => {
		const map = new Map<string, string>();
		for (const [collKey, entry] of collectionContainers) {
			for (const m of entry.members) {
				map.set(`${m.entityType}:${m.entityId}`, collKey);
			}
		}
		return map;
	});

	// Filtered visible triples: hide structural collection↔member connections
	let filteredVisibleTriples = $derived.by(() => {
		return visibleTriples.filter(t => {
			const sk = `${t.subject_type}:${t.subject_id}`;
			const ok = `${t.object_type}:${t.object_id}`;
			// Hide collection→member triples when collection is rendered as container
			// (these are structural — the container itself shows membership)
			if (containerCollectionKeys.has(sk) && containedMemberKeys.has(ok)) return false;
			if (containerCollectionKeys.has(ok) && containedMemberKeys.has(sk)) return false;
			return true;
		});
	});

	// --- Entity resolution ---
	function getEntityTitle(type: string, id: number): string {
		switch (type) {
			case 'project': return $projects.find(e => e.id === id)?.title ?? `Project #${id}`;
			case 'log': return $logs.find(e => e.id === id)?.title ?? `Log #${id}`;
			case 'note': return $notes.find(e => e.id === id)?.title ?? `Note #${id}`;
			case 'activity': return $activities.find(e => e.id === id)?.title ?? `Activity #${id}`;
			case 'source': return $sources.find(e => e.id === id)?.title ?? `Source #${id}`;
			case 'actor': return $actors.find(e => e.id === id)?.full_name ?? `Actor #${id}`;
			case 'plan': return $plans.find(e => e.id === id)?.title ?? `Plan #${id}`;
			case 'collection': return $collections.find(e => e.id === id)?.title ?? `Collection #${id}`;
			default: return `${type} #${id}`;
		}
	}

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

	// --- Position persistence (debounced) ---
	function scheduleSavePositions() {
		if (saveTimer) clearTimeout(saveTimer);
		saveTimer = setTimeout(async () => {
			if (!wsId) return;
			const items = wsItems.map(item => ({
				entity_type: item.entity_type,
				entity_id: item.entity_id,
				x: item.x,
				y: item.y,
			}));
			try {
				await bulkUpdatePositions(wsId, items);
			} catch (err) {
				console.error('Failed to save positions:', err);
			}
		}, 500);
	}

	// --- Card drag handlers ---
	function handleCardPointerDown(type: string, id: number, e: PointerEvent) {
		if (e.button !== 0) return;
		e.stopPropagation();
		e.preventDefault();

		const key = `${type}:${id}`;

		// Bring card to front
		topZKey = key;
		zCounter++;

		if (e.metaKey || e.ctrlKey) {
			const next = new Set(selectedCards);
			if (next.has(key)) next.delete(key);
			else next.add(key);
			selectedCards = next;
			return;
		}

		const isInMultiSelection = selectedCards.size >= 2 && selectedCards.has(key);
		if (!isInMultiSelection) {
			selectedCards = new Set([key]);
		}

		const node = nodeMap.get(key);
		if (!node) return;
		dragStarted = false;
		draggingCard = { type, id, startX: e.clientX, startY: e.clientY, origX: node.x, origY: node.y };
		draggingKey = `${type}:${id}`;

		if (selectedCards.size >= 2 && selectedCards.has(key)) {
			const origPositions = new Map<string, { x: number; y: number }>();
			for (const selKey of selectedCards) {
				const n = nodeMap.get(selKey);
				if (n) origPositions.set(selKey, { x: n.x, y: n.y });
			}
			groupDragOrigPositions = origPositions;
		} else {
			groupDragOrigPositions = null;
		}

		document.addEventListener('pointermove', handleDragMove);
		document.addEventListener('pointerup', handleDragUp);
	}

	function handleMemberPointerDown(type: string, id: number, e: PointerEvent) {
		// Drag a single member OUT of its container (not group drag)
		if (e.button !== 0) return;
		e.stopPropagation();
		e.preventDefault();

		const key = `${type}:${id}`;
		selectedCards = new Set([key]);

		const node = nodeMap.get(key);
		if (!node) return;
		dragStarted = false;
		draggingCard = { type, id, startX: e.clientX, startY: e.clientY, origX: node.x, origY: node.y };
		// Don't set draggingKey yet — defer until drag threshold is crossed
		// so the member stays visually inside the container on a simple click
		draggingKey = null;
		groupDragOrigPositions = null; // single-card drag, not group

		document.addEventListener('pointermove', handleDragMove);
		document.addEventListener('pointerup', handleDragUp);
	}

	function handleContainerPointerDown(type: string, id: number, e: PointerEvent) {
		if (e.button !== 0) return;
		e.stopPropagation();
		e.preventDefault();

		const key = `${type}:${id}`;
		selectedCards = new Set([key]);

		const node = nodeMap.get(key);
		if (!node) return;
		dragStarted = false;
		draggingCard = { type, id, startX: e.clientX, startY: e.clientY, origX: node.x, origY: node.y };
		draggingKey = key;

		// Group drag: collection + all its members
		const origPositions = new Map<string, { x: number; y: number }>();
		origPositions.set(key, { x: node.x, y: node.y });
		const entry = collectionContainers.get(key);
		if (entry) {
			for (const m of entry.members) {
				const mk = `${m.entityType}:${m.entityId}`;
				const mn = nodeMap.get(mk);
				if (mn) origPositions.set(mk, { x: mn.x, y: mn.y });
			}
		}
		groupDragOrigPositions = origPositions;

		document.addEventListener('pointermove', handleDragMove);
		document.addEventListener('pointerup', handleDragUp);
	}

	function handleDragMove(e: PointerEvent) {
		if (!draggingCard) return;

		if (!dragStarted) {
			const dist = Math.hypot(e.clientX - draggingCard.startX, e.clientY - draggingCard.startY);
			if (dist < DRAG_THRESHOLD) return;
			dragStarted = true;
			// Set draggingKey now so the member pops out of its container only on actual drag
			if (!draggingKey) {
				draggingKey = `${draggingCard.type}:${draggingCard.id}`;
			}
		}

		const dx = (e.clientX - draggingCard.startX) / zoom;
		const dy = (e.clientY - draggingCard.startY) / zoom;

		if (groupDragOrigPositions && groupDragOrigPositions.size >= 2) {
			// Group drag
			activeWorkspace.update(ws => {
				if (!ws) return ws;
				return {
					...ws,
					items: ws.items.map(item => {
						const nKey = `${item.entity_type}:${item.entity_id}`;
						const orig = groupDragOrigPositions!.get(nKey);
						if (orig) return { ...item, x: orig.x + dx, y: orig.y + dy };
						return item;
					})
				};
			});
			// Drop target detection for group drag (based on lead card)
			const leadX = draggingCard.origX + dx;
			const leadY = draggingCard.origY + dy;
			const leadAug = augmentedNodeMap.get(`${draggingCard.type}:${draggingCard.id}`);
			const leadW = leadAug?.w ?? 150;
			const leadH = leadAug?.h ?? 60;
			const centerX = leadX + leadW / 2;
			const centerY = leadY + leadH / 2;
			let found: { type: string; id: number } | null = null;
			// Collections first
			for (const node of visibleNodes) {
				if (node.entity_type !== 'collection') continue;
				const nk = `${node.entity_type}:${node.entity_id}`;
				if (selectedCards.has(nk)) continue;
				const an = augmentedNodeMap.get(nk);
				const nx = an?.x ?? node.x;
				const ny = an?.y ?? node.y;
				const nw = an?.w ?? 150;
				const nh = an?.h ?? 60;
				if (centerX >= nx && centerX <= nx + nw &&
					centerY >= ny && centerY <= ny + nh) {
					found = { type: node.entity_type, id: node.entity_id };
					break;
				}
			}
			// Then other nodes
			if (!found) {
				for (const node of visibleNodes) {
					if (node.entity_type === 'collection') continue;
					const nk = `${node.entity_type}:${node.entity_id}`;
					if (selectedCards.has(nk)) continue;
					const nw = augmentedNodeMap.get(nk)?.w ?? 150;
					const nh = augmentedNodeMap.get(nk)?.h ?? 60;
					if (centerX >= node.x && centerX <= node.x + nw &&
						centerY >= node.y && centerY <= node.y + nh) {
						found = { type: node.entity_type, id: node.entity_id };
						break;
					}
				}
			}
			dropTarget = found;
		} else {
			const newX = draggingCard.origX + dx;
			const newY = draggingCard.origY + dy;
			activeWorkspace.update(ws => {
				if (!ws) return ws;
				return {
					...ws,
					items: ws.items.map(item =>
						item.entity_type === draggingCard!.type && item.entity_id === draggingCard!.id
							? { ...item, x: newX, y: newY }
							: item
					)
				};
			});

			// Drop target detection (dimension-aware, collections prioritized)
			const dragNodeW = augmentedNodeMap.get(`${draggingCard.type}:${draggingCard.id}`)?.w ?? 150;
			const dragNodeH = augmentedNodeMap.get(`${draggingCard.type}:${draggingCard.id}`)?.h ?? 60;
			const centerX = newX + dragNodeW / 2;
			const centerY = newY + dragNodeH / 2;
			let found: { type: string; id: number } | null = null;
			let hoveredMemberKey: string | null = null;
			// First pass: check collection containers (priority targets for drag-drop)
			for (const node of visibleNodes) {
				if (node.entity_type !== 'collection') continue;
				if (node.entity_type === draggingCard.type && node.entity_id === draggingCard.id) continue;
				const nk = `${node.entity_type}:${node.entity_id}`;
				const an = augmentedNodeMap.get(nk);
				const nx = an?.x ?? node.x;
				const ny = an?.y ?? node.y;
				const nw = an?.w ?? 150;
				const nh = an?.h ?? 60;
				if (centerX >= nx && centerX <= nx + nw &&
					centerY >= ny && centerY <= ny + nh) {
					found = { type: node.entity_type, id: node.entity_id };
					// Check if cursor is over a specific member inside this collection
					const entry = renderContainers.get(nk);
					if (entry && !node.collapsed) {
						entry.members.forEach((m, mi) => {
							if (hoveredMemberKey) return; // already found
							const mk = `${m.entityType}:${m.entityId}`;
							const col = mi % COLS;
							const row = Math.floor(mi / COLS);
							const mx = nx + CONTAINER_PADDING + col * (MINI_CARD_W + MINI_GAP);
							const my = ny + TITLE_BAR_H + CONTAINER_PADDING + row * (MINI_CARD_H + MINI_GAP);
							if (centerX >= mx && centerX <= mx + MINI_CARD_W &&
								centerY >= my && centerY <= my + MINI_CARD_H) {
								hoveredMemberKey = mk;
							}
						});
					}
					break;
				}
			}
			// Second pass: other nodes
			if (!found) {
				for (const node of visibleNodes) {
					if (node.entity_type === 'collection') continue;
					if (node.entity_type === draggingCard.type && node.entity_id === draggingCard.id) continue;
					const nk = `${node.entity_type}:${node.entity_id}`;
					const nw = augmentedNodeMap.get(nk)?.w ?? 150;
					const nh = augmentedNodeMap.get(nk)?.h ?? 60;
					if (centerX >= node.x && centerX <= node.x + nw &&
						centerY >= node.y && centerY <= node.y + nh) {
						found = { type: node.entity_type, id: node.entity_id };
						break;
					}
				}
			}

			// Member dwell logic: when hovering over a member inside a collection,
			// after MEMBER_DWELL_MS switch the drop target to that specific member
			const stillInCollection = found?.type === 'collection';
			if (hoveredMemberKey && hoveredMemberKey !== memberDwellKey) {
				// Started hovering over a new member — reset timer
				if (memberDwellTimer) clearTimeout(memberDwellTimer);
				memberDwellKey = hoveredMemberKey;
				memberDwellFired = false;
				memberDwellTimer = setTimeout(() => {
					if (memberDwellKey) {
						const [mType, mIdStr] = memberDwellKey.split(':');
						dropTarget = { type: mType, id: Number(mIdStr) };
						memberDwellFired = true;
					}
					memberDwellTimer = null;
				}, MEMBER_DWELL_MS);
				dropTarget = found;
			} else if (!hoveredMemberKey && memberDwellKey && !memberDwellFired) {
				// Timer hasn't fired yet and cursor moved off member — cancel
				if (memberDwellTimer) clearTimeout(memberDwellTimer);
				memberDwellKey = null;
				memberDwellTimer = null;
				dropTarget = found ?? null;
			} else if (!hoveredMemberKey && memberDwellFired && !stillInCollection) {
				// Dwell already fired but cursor left the collection entirely — clear
				if (memberDwellTimer) clearTimeout(memberDwellTimer);
				memberDwellKey = null;
				memberDwellFired = false;
				memberDwellTimer = null;
				dropTarget = found ?? null;
			} else if (memberDwellFired && memberDwellKey) {
				// Dwell fired and cursor is still in the collection — keep member target
			} else {
				dropTarget = found ?? null;
			}
		}
	}

	async function handleDragUp(_e: PointerEvent) {
		document.removeEventListener('pointermove', handleDragMove);
		document.removeEventListener('pointerup', handleDragUp);

		if (!draggingCard) return;
		const { type, id, origX, origY } = draggingCard;
		const wasGroupDrag = groupDragOrigPositions && groupDragOrigPositions.size >= 2;

		if (!dragStarted) {
			if (wasGroupDrag) {
				selectedCards = new Set([`${type}:${id}`]);
			}
			draggingCard = null;
			draggingKey = null;
			groupDragOrigPositions = null;
			return;
		}

		if (wasGroupDrag && dropTarget) {
			// Group drag onto a target
			const dt = dropTarget;
			const savedPositions = groupDragOrigPositions!;
			try {
				if (dt.type === 'collection') {
					// Ensure collection accepts any entity type
					const coll = $collections.find(c => c.id === dt.id);
					if (coll) {
						const cat = $categories.find(c => c.id === coll.category_id);
						if (cat && cat.member_entity_type !== '*') {
							const wildcard = $categories.find(c => c.member_entity_type === '*');
							if (wildcard) {
								await updateCollection(dt.id, { category_id: wildcard.id } as any);
							}
						}
					}
					// Skip entities already in this collection
					const existingKeys = new Set(
						(coll?.items || []).map((i: any) => `${i.member_entity_type}:${i.member_entity_id}`)
					);
					for (const selKey of selectedCards) {
						if (existingKeys.has(selKey)) continue;
						const [sType, sIdStr] = selKey.split(':');
						// Skip dropping a collection into itself
						if (sType === 'collection' && Number(sIdStr) === dt.id) continue;
						await addItem(dt.id, { member_entity_type: sType, member_entity_id: Number(sIdStr) });
					}
					await loadCollections();
					await refreshActiveWorkspace();
				} else {
					// Connect all selected: snap back positions, then attach tags
					activeWorkspace.update(ws => {
						if (!ws) return ws;
						return {
							...ws,
							items: ws.items.map(item => {
								const nk = `${item.entity_type}:${item.entity_id}`;
								const orig = savedPositions.get(nk);
								if (orig) return { ...item, x: orig.x, y: orig.y, collapsed: false };
								if (item.entity_type === dt.type && item.entity_id === dt.id)
									return { ...item, collapsed: false };
								return item;
							})
						};
					});
					for (const selKey of selectedCards) {
						const [sType, sIdStr] = selKey.split(':');
						const subjectTag = $tags.find(t => t.entity_type === sType && t.entity_id === Number(sIdStr));
						if (subjectTag) {
							await attachTag(subjectTag.id, dt.type, dt.id);
						}
					}
					await loadTags();
				}
				await loadTriples();
			} catch (err) {
				console.error('Failed to interact with drop target:', err);
			}
			scheduleSavePositions();
			dropTarget = null;
		} else if (wasGroupDrag) {
			scheduleSavePositions();
		} else if (dropTarget) {
			if (dropTarget.type === 'collection') {
				// Drop onto a collection container → move entity into collection
				// Clear dragging state first so containedMemberKeys includes the
				// newly-added member (the exclusion at line 367 checks draggingKey)
				const dtId = dropTarget.id;
				draggingCard = null;
				draggingKey = null;
				try {
					// If already in a different collection, remove first
					const dragKey = `${type}:${id}`;
					const oldContainerKey = memberToContainerKey.get(dragKey);
					if (oldContainerKey) {
						const oldCollId = collectionContainers.get(oldContainerKey)?.collectionId;
						if (oldCollId && oldCollId !== dtId) {
							const oldColl = $collections.find(c => c.id === oldCollId);
							const oldItem = oldColl?.items?.find((i: any) => i.member_entity_type === type && i.member_entity_id === id);
							if (oldItem) await removeItem(oldItem.id);
						}
					}
					await addItem(dtId, { member_entity_type: type, member_entity_id: id });
					await loadCollections();
					await loadTriples();
				} catch (err) {
					console.error('Failed to add to collection:', err);
				}
			} else {
				// Reset position and create connection (existing tag-attach behavior)
				activeWorkspace.update(ws => {
					if (!ws) return ws;
					return {
						...ws,
						items: ws.items.map(item => {
							// Reset dragged card position
							if (item.entity_type === type && item.entity_id === id)
								return { ...item, x: origX, y: origY, collapsed: false };
							// Un-collapse the drop target so the new connection is visible
							if (item.entity_type === dropTarget!.type && item.entity_id === dropTarget!.id)
								return { ...item, collapsed: false };
							return item;
						})
					};
				});
				try {
					const subjectTag = $tags.find(t => t.entity_type === type && t.entity_id === id);
					if (subjectTag) {
						await attachTag(subjectTag.id, dropTarget.type, dropTarget.id);
						await loadTags();
					}
				} catch (err) {
					console.error('Failed to attach tag:', err);
				}
				await loadTriples();
				// Persist the un-collapsed state
				scheduleSavePositions();
			}
			dropTarget = null;
		} else {
			// No drop target — check if entity was dragged out of a collection container
			const dragKey = `${type}:${id}`;
			const containerKey = memberToContainerKey.get(dragKey);
			if (containerKey) {
				const container = augmentedNodeMap.get(containerKey);
				const ws = $activeWorkspace;
				const wsItem = ws?.items.find(i => i.entity_type === type && i.entity_id === id);
				if (container && wsItem) {
					const cw = container.w ?? 150;
					const ch = container.h ?? 60;
					const outside = wsItem.x + 75 < container.x || wsItem.x > container.x + cw ||
						wsItem.y + 30 < container.y || wsItem.y > container.y + ch;
					if (outside) {
						const collId = collectionContainers.get(containerKey)?.collectionId;
						if (collId) {
							// Find the CollectionItem ID for this member
							const coll = $collections.find(c => c.id === collId);
							const item = coll?.items?.find((i: any) => i.member_entity_type === type && i.member_entity_id === id);
							if (item) {
								try {
									await removeItem(item.id);
									await loadCollections();
									await loadTriples();
								} catch (err) {
									console.error('Failed to remove from collection:', err);
								}
							}
						}
					}
				}
			}
			scheduleSavePositions();
		}

		draggingCard = null;
		draggingKey = null;
		groupDragOrigPositions = null;
		// Clear member dwell state
		if (memberDwellTimer) clearTimeout(memberDwellTimer);
		memberDwellKey = null;
		memberDwellFired = false;
		memberDwellTimer = null;
	}

	// --- Canvas pan/zoom ---
	function handleCanvasPointerDown(e: PointerEvent) {
		if (e.button !== 0) return;

		if (selectMode || e.metaKey || e.ctrlKey || e.shiftKey) {
			selectionRect = { startX: e.clientX, startY: e.clientY, currentX: e.clientX, currentY: e.clientY };
			return;
		}

		if (selectedCards.size > 0) selectedCards = new Set();
		isPanning = true;
		panStart = { x: e.clientX, y: e.clientY, panX, panY };
	}

	function handlePointerMove(e: PointerEvent) {
		if (isPanning) {
			panX = panStart.panX + (e.clientX - panStart.x);
			panY = panStart.panY + (e.clientY - panStart.y);
		} else if (selectionRect) {
			selectionRect = { ...selectionRect, currentX: e.clientX, currentY: e.clientY };
		}
	}

	function handlePointerUp(_e: PointerEvent) {
		if (isPanning) {
			isPanning = false;
		} else if (selectionRect) {
			const rect = viewportEl?.getBoundingClientRect();
			if (rect) {
				const x1 = (Math.min(selectionRect.startX, selectionRect.currentX) - rect.left - panX) / zoom;
				const y1 = (Math.min(selectionRect.startY, selectionRect.currentY) - rect.top - panY) / zoom;
				const x2 = (Math.max(selectionRect.startX, selectionRect.currentX) - rect.left - panX) / zoom;
				const y2 = (Math.max(selectionRect.startY, selectionRect.currentY) - rect.top - panY) / zoom;

				const next = new Set<string>();
				for (const node of visibleNodes) {
					const nk = `${node.entity_type}:${node.entity_id}`;
					const nw = augmentedNodeMap.get(nk)?.w ?? 150;
					const nh = augmentedNodeMap.get(nk)?.h ?? 60;
					if (node.x + nw >= x1 && node.x <= x2 && node.y + nh >= y1 && node.y <= y2) {
						next.add(nk);
					}
				}
				if (next.size > 0) selectedCards = next;
			}
			selectionRect = null;
		}
	}

	function handleWheel(e: WheelEvent) {
		e.preventDefault();
		const oldZoom = zoom;
		const factor = 1 + e.deltaY * -0.001;
		const newZoom = Math.min(3, Math.max(0.2, zoom * factor));

		const rect = viewportEl!.getBoundingClientRect();
		const cursorX = e.clientX - rect.left;
		const cursorY = e.clientY - rect.top;
		panX = cursorX - (cursorX - panX) * (newZoom / oldZoom);
		panY = cursorY - (cursorY - panY) * (newZoom / oldZoom);
		zoom = newZoom;
	}

	// --- Exported zoom/layout functions ---
	export function screenshot() {
		if (!canvasEl) return;
		const rects = visibleNodes.map(n => {
			const nk = `${n.entity_type}:${n.entity_id}`;
			const aug = augmentedNodeMap.get(nk);
			return { x: n.x, y: n.y, w: aug?.w ?? 150, h: aug?.h ?? 60 };
		});
		const name = $activeWorkspace?.name ?? 'workspace';
		const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
		captureGraphScreenshot(canvasEl, rects, slug || 'workspace', {
			title: name,
			description: $activeWorkspace?.description ?? undefined
		});
	}
	export function zoomIn() { zoom = Math.min(3, zoom * 1.2); }
	export function zoomOut() { zoom = Math.max(0.2, zoom / 1.2); }
	export function zoomFit() {
		if (visibleNodes.length === 0) { panX = 0; panY = 0; zoom = 1; return; }
		let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
		for (const node of visibleNodes) {
			const nk = `${node.entity_type}:${node.entity_id}`;
			const nw = augmentedNodeMap.get(nk)?.w ?? 150;
			const nh = augmentedNodeMap.get(nk)?.h ?? 60;
			minX = Math.min(minX, node.x);
			minY = Math.min(minY, node.y);
			maxX = Math.max(maxX, node.x + nw);
			maxY = Math.max(maxY, node.y + nh);
		}
		const rect = viewportEl?.getBoundingClientRect();
		if (!rect) return;
		const padding = 60;
		const contentW = maxX - minX + padding * 2;
		const contentH = maxY - minY + padding * 2;
		const scaleX = rect.width / contentW;
		const scaleY = rect.height / contentH;
		zoom = Math.min(Math.max(Math.min(scaleX, scaleY), 0.2), 2);
		panX = (rect.width - contentW * zoom) / 2 - (minX - padding) * zoom;
		panY = (rect.height - contentH * zoom) / 2 - (minY - padding) * zoom;
	}

	function findNonOverlappingPosition(
		baseX: number,
		baseY: number,
		newW = 150,
		newH = 60,
		extraRects: Array<{ x: number; y: number; w: number; h: number }> = []
	): { x: number; y: number } {
		const DEFAULT_W = 150;
		const DEFAULT_H = 60;
		const GAP = 20;

		function overlapsAny(x: number, y: number): boolean {
			for (const node of wsItems) {
				const aug = augmentedNodeMap.get(`${node.entity_type}:${node.entity_id}`);
				const nw = aug?.w ?? DEFAULT_W;
				const nh = aug?.h ?? DEFAULT_H;
				if (x < node.x + nw + GAP && x + newW + GAP > node.x &&
					y < node.y + nh + GAP && y + newH + GAP > node.y) {
					return true;
				}
			}
			for (const rect of extraRects) {
				if (x < rect.x + rect.w + GAP && x + newW + GAP > rect.x &&
					y < rect.y + rect.h + GAP && y + newH + GAP > rect.y) {
					return true;
				}
			}
			return false;
		}

		if (!overlapsAny(baseX, baseY)) return { x: baseX, y: baseY };

		const step = Math.max(newW, newH) + GAP;
		for (let ring = 1; ring <= 20; ring++) {
			const offset = ring * step;
			const candidates = [
				{ x: baseX + offset, y: baseY },
				{ x: baseX - offset, y: baseY },
				{ x: baseX, y: baseY + offset },
				{ x: baseX, y: baseY - offset },
				{ x: baseX + offset, y: baseY + offset },
				{ x: baseX - offset, y: baseY - offset },
			];
			for (const pos of candidates) {
				if (!overlapsAny(pos.x, pos.y)) return pos;
			}
		}
		return { x: baseX + 500, y: baseY };
	}

	export function hierarchicalLayout() {
		const DEFAULT_W = 150;
		const DEFAULT_H = 70;
		const GAP_X = 80;
		const GAP_Y = 120;

		const TYPE_PRIORITY: Record<string, number> = {
			plan: 0, project: 1, log: 2, activity: 3, note: 4,
			collection: 5, source: 6, actor: 7,
		};

		// Only position standalone + container nodes (skip contained members)
		const layoutNodes = visibleNodes.filter(n => {
			const key = `${n.entity_type}:${n.entity_id}`;
			return !containedMemberKeys.has(key);
		});

		const nodeKeySet = new Set(layoutNodes.map(n => `${n.entity_type}:${n.entity_id}`));
		const adj = new Map<string, Set<string>>();
		for (const t of visibleTriples) {
			const sk = `${t.subject_type}:${t.subject_id}`;
			const ok = `${t.object_type}:${t.object_id}`;
			if (!nodeKeySet.has(sk) || !nodeKeySet.has(ok)) continue;
			if (!adj.has(sk)) adj.set(sk, new Set());
			if (!adj.has(ok)) adj.set(ok, new Set());
			adj.get(sk)!.add(ok);
			adj.get(ok)!.add(sk);
		}

		// Find roots: prefer plans/projects, else pick nodes with most connections
		const rootKeys = new Set<string>();
		for (const n of layoutNodes) {
			if (n.entity_type === 'plan' || n.entity_type === 'project') {
				rootKeys.add(`${n.entity_type}:${n.entity_id}`);
			}
		}
		if (rootKeys.size === 0 && layoutNodes.length > 0) {
			rootKeys.add(`${layoutNodes[0].entity_type}:${layoutNodes[0].entity_id}`);
		}

		const layerOf = new Map<string, number>();
		const queue: string[] = [];
		for (const key of rootKeys) {
			if (nodeKeySet.has(key)) {
				layerOf.set(key, 0);
				queue.push(key);
			}
		}
		let qi = 0;
		while (qi < queue.length) {
			const current = queue[qi++];
			const depth = layerOf.get(current)!;
			for (const neighbor of adj.get(current) ?? []) {
				if (!layerOf.has(neighbor)) {
					layerOf.set(neighbor, depth + 1);
					queue.push(neighbor);
				}
			}
		}
		const maxLayer = Math.max(0, ...layerOf.values());
		for (const n of layoutNodes) {
			const key = `${n.entity_type}:${n.entity_id}`;
			if (!layerOf.has(key)) layerOf.set(key, maxLayer + 1);
		}

		const layers = new Map<number, typeof layoutNodes>();
		for (const n of layoutNodes) {
			const key = `${n.entity_type}:${n.entity_id}`;
			const layer = layerOf.get(key) ?? maxLayer + 1;
			if (!layers.has(layer)) layers.set(layer, []);
			layers.get(layer)!.push(n);
		}
		for (const [, nodes] of layers) {
			nodes.sort((a, b) => {
				const pa = TYPE_PRIORITY[a.entity_type] ?? 99;
				const pb = TYPE_PRIORITY[b.entity_type] ?? 99;
				return pa !== pb ? pa - pb : a.entity_id - b.entity_id;
			});
		}

		// Helper to get real node dimensions from augmentedNodeMap
		function nodeDims(n: { entity_type: string; entity_id: number }) {
			const an = augmentedNodeMap.get(`${n.entity_type}:${n.entity_id}`);
			return { w: an?.w ?? DEFAULT_W, h: an?.h ?? DEFAULT_H };
		}

		const newPos = new Map<string, { x: number; y: number }>();
		const sortedLayers = [...layers.keys()].sort((a, b) => a - b);

		// Calculate per-row width using actual node widths
		const rowWidths = new Map<number, number>();
		for (const layer of sortedLayers) {
			const nodes = layers.get(layer)!;
			let w = 0;
			for (const n of nodes) w += nodeDims(n).w + GAP_X;
			rowWidths.set(layer, w - GAP_X);
		}
		const maxRowWidth = Math.max(0, ...rowWidths.values());

		// Calculate per-row max height for vertical spacing
		let cumulativeY = 0;
		for (const layer of sortedLayers) {
			const nodes = layers.get(layer)!;
			const rowWidth = rowWidths.get(layer)!;
			const offsetX = (maxRowWidth - rowWidth) / 2;
			let curX = offsetX;
			let maxH = 0;
			for (const n of nodes) {
				const { w, h } = nodeDims(n);
				newPos.set(`${n.entity_type}:${n.entity_id}`, { x: curX, y: cumulativeY });
				curX += w + GAP_X;
				if (h > maxH) maxH = h;
			}
			cumulativeY += maxH + GAP_Y;
		}

		activeWorkspace.update(ws => {
			if (!ws) return ws;
			return {
				...ws,
				items: ws.items.map(item => {
					const pos = newPos.get(`${item.entity_type}:${item.entity_id}`);
					return pos ? { ...item, x: pos.x, y: pos.y } : item;
				})
			};
		});
		scheduleSavePositions();
		requestAnimationFrame(() => zoomFit());
	}

	export function quadrantLayout() {
		const DEFAULT_W = 150;
		const DEFAULT_H = 70;
		const GAP_X = 170;
		const GAP_Y = 120;
		const QUADRANT_GAP = 250;

		// Quadrant assignment by entity type
		// TL: plans + projects, TR: sources + actors, BL: activities, BR: notes + logs
		const QUADRANT_MAP: Record<string, number> = {
			plan: 0, project: 0,
			source: 1, actor: 1,
			activity: 2,
			note: 3, log: 3,
		};

		// Only position standalone + container nodes (skip contained members)
		const layoutNodes = visibleNodes.filter(n => {
			const key = `${n.entity_type}:${n.entity_id}`;
			return !containedMemberKeys.has(key);
		});

		// Helper to get real node dimensions
		function nodeDims(n: { entity_type: string; entity_id: number }) {
			const an = augmentedNodeMap.get(`${n.entity_type}:${n.entity_id}`);
			return { w: an?.w ?? DEFAULT_W, h: an?.h ?? DEFAULT_H };
		}

		// Assign collection containers to quadrant based on primary member type
		function getQuadrant(n: { entity_type: string; entity_id: number }): number {
			if (n.entity_type !== 'collection') return QUADRANT_MAP[n.entity_type] ?? 0;
			const collKey = `collection:${n.entity_id}`;
			const entry = collectionContainers.get(collKey);
			if (!entry || entry.members.length === 0) return 0;
			// Use the most common member type
			const typeCounts = new Map<string, number>();
			for (const m of entry.members) {
				typeCounts.set(m.entityType, (typeCounts.get(m.entityType) ?? 0) + 1);
			}
			let bestType = entry.members[0].entityType;
			let bestCount = 0;
			for (const [t, c] of typeCounts) {
				if (c > bestCount) { bestType = t; bestCount = c; }
			}
			return QUADRANT_MAP[bestType] ?? 0;
		}

		// Group nodes into 4 quadrants
		const quadrants: Array<typeof layoutNodes> = [[], [], [], []];
		for (const n of layoutNodes) {
			quadrants[getQuadrant(n)].push(n);
		}

		// Arrange each quadrant as a grid, returning bounding dimensions
		function arrangeGrid(nodes: typeof layoutNodes) {
			if (nodes.length === 0) return { positions: new Map<string, { x: number; y: number }>(), w: 0, h: 0 };
			const positions = new Map<string, { x: number; y: number }>();
			// Determine grid columns: roughly square layout
			const cols = Math.max(1, Math.ceil(Math.sqrt(nodes.length)));
			let totalW = 0;
			let totalH = 0;
			let curX = 0;
			let curY = 0;
			let rowMaxH = 0;
			let rowW = 0;
			for (let i = 0; i < nodes.length; i++) {
				const n = nodes[i];
				const { w, h } = nodeDims(n);
				if (i > 0 && i % cols === 0) {
					// New row
					if (rowW > totalW) totalW = rowW;
					curX = 0;
					curY += rowMaxH + GAP_Y;
					rowMaxH = 0;
					rowW = 0;
				}
				positions.set(`${n.entity_type}:${n.entity_id}`, { x: curX, y: curY });
				curX += w + GAP_X;
				rowW = curX - GAP_X;
				if (h > rowMaxH) rowMaxH = h;
			}
			if (rowW > totalW) totalW = rowW;
			totalH = curY + rowMaxH;
			return { positions, w: totalW, h: totalH };
		}

		const results = quadrants.map(q => arrangeGrid(q));

		// Compute quadrant origins:
		// TL at (0,0), TR at (maxLeftW + QUADRANT_GAP, 0)
		// BL at (0, maxTopH + QUADRANT_GAP), BR at (maxLeftW + QUADRANT_GAP, maxTopH + QUADRANT_GAP)
		const leftW = Math.max(results[0].w, results[2].w);
		const topH = Math.max(results[0].h, results[1].h);
		const origins = [
			{ x: 0, y: 0 },                                           // TL
			{ x: leftW + QUADRANT_GAP, y: 0 },                        // TR
			{ x: 0, y: topH + QUADRANT_GAP },                         // BL
			{ x: leftW + QUADRANT_GAP, y: topH + QUADRANT_GAP },      // BR
		];

		const newPos = new Map<string, { x: number; y: number }>();
		for (let q = 0; q < 4; q++) {
			const origin = origins[q];
			for (const [key, pos] of results[q].positions) {
				newPos.set(key, { x: origin.x + pos.x, y: origin.y + pos.y });
			}
		}

		activeWorkspace.update(ws => {
			if (!ws) return ws;
			return {
				...ws,
				items: ws.items.map(item => {
					const pos = newPos.get(`${item.entity_type}:${item.entity_id}`);
					return pos ? { ...item, x: pos.x, y: pos.y } : item;
				})
			};
		});
		scheduleSavePositions();
		requestAnimationFrame(() => zoomFit());
	}

	// --- Double-click to edit ---
	function handleCardDblClick(type: string, id: number) {
		detailEntity = { type, id };
	}

	async function handleEntityDeleted() {
		if (!detailEntity) return;
		const { type, id } = detailEntity;
		detailEntity = null;
		// Remove from workspace
		if (wsId) {
			try {
				await removeWorkspaceItem(wsId, type, id);
				await refreshActiveWorkspace();
			} catch { /* ignore */ }
		}
		// Refresh query panel so deleted entities disappear from results
		queryPanelRef?.refresh();
	}

	// --- Context menu ---
	function handleCardContextMenu(type: string, id: number, e: MouseEvent) {
		e.preventDefault();
		e.stopPropagation();
		contextMenu = { type, id, x: e.clientX, y: e.clientY };
	}

	function closeContextMenu() {
		contextMenu = null;
	}

	$effect(() => {
		if (contextMenu) {
			const handler = () => closeContextMenu();
			document.addEventListener('click', handler);
			return () => document.removeEventListener('click', handler);
		}
	});

	// --- Remove from workspace ---
	async function handleRemoveFromWorkspace(type: string, id: number) {
		if (!wsId) return;
		try {
			await removeWorkspaceItem(wsId, type, id);
			await refreshActiveWorkspace();
		} catch (err) {
			console.error('Failed to remove item:', err);
		}
	}

	// --- Clear all items ---
	export async function clearAll() {
		if (!wsId) return;
		if (!confirm('Remove all items from this workspace?')) return;
		for (const item of wsItems) {
			await removeWorkspaceItem(wsId, item.entity_type, item.entity_id);
		}
		selectedCards = new Set();
		await refreshActiveWorkspace();
	}

	// --- Bulk actions ---
	async function handleBulkRemove() {
		if (!wsId) return;
		bulkActionInProgress = true;
		for (const key of selectedCards) {
			const [type, idStr] = key.split(':');
			await removeWorkspaceItem(wsId, type, Number(idStr));
		}
		selectedCards = new Set();
		await refreshActiveWorkspace();
		bulkActionInProgress = false;
	}

	function deleteEntity(type: string, id: number): Promise<any> {
		switch (type) {
			case 'project': return deleteProject(id);
			case 'log': return deleteLog(id);
			case 'note': return deleteNote(id);
			case 'activity': return deleteActivity(id);
			case 'source': return deleteSource(id);
			case 'actor': return deleteActor(id);
			case 'plan': return deletePlan(id);
			default: return Promise.resolve();
		}
	}

	async function handleBulkDelete() {
		if (!wsId) return;
		bulkActionInProgress = true;
		await Promise.allSettled(
			selectedEntities.map(({ type, id }) => deleteEntity(type, id))
		);
		// Also remove from workspace
		for (const { type, id } of selectedEntities) {
			try { await removeWorkspaceItem(wsId, type, id); } catch {}
		}
		await Promise.all([
			refreshActiveWorkspace(),
			loadProjects(), loadLogs(), loadNotes(), loadActivities(),
			loadSources(), loadActors(), loadPlans(), loadCollections(),
			loadTags(), loadTriples()
		]);
		selectedCards = new Set();
		showBulkDelete = false;
		bulkActionInProgress = false;
	}

	function handleBulkTagsClick() {
		showBulkTagInput = !showBulkTagInput;
		if (showBulkTagInput && selectedEntities.length > 0) {
			loadFirstEntityTags();
		}
	}

	async function loadFirstEntityTags() {
		const first = selectedEntities[0];
		try {
			bulkTags = await getEntityTags(first.type, first.id);
		} catch {
			bulkTags = [];
		}
	}

	async function handleBulkAttachTag(tag: Tag) {
		bulkActionInProgress = true;
		await Promise.allSettled(
			selectedEntities.map(({ type, id }) => attachTag(tag.id, type, id))
		);
		await Promise.all([loadTags(), loadTriples()]);
		triggerEntityTagsRefresh();
		bulkActionInProgress = false;
	}

	async function handleBulkDetachTag(tag: Tag) {
		bulkActionInProgress = true;
		await Promise.allSettled(
			selectedEntities.map(({ type, id }) => detachTag(tag.id, type, id))
		);
		await Promise.all([loadTags(), loadTriples()]);
		triggerEntityTagsRefresh();
		bulkActionInProgress = false;
	}

	function handleOpenInCards() {
		const entityTypes = new Set(selectedEntities.map(e => e.type));
		const currentPanels = get(panels);
		for (const type of entityTypes) {
			const panel = currentPanels.find(p => p.id === type);
			if (panel && !panel.visible) {
				togglePanel(type);
			}
		}
		panelSelection.setMany(
			selectedEntities.map(e => ({ type: e.type as PanelEntityType, id: e.id }))
		);
		activeTab.set('input');
		selectedCards = new Set();
	}

	// --- Toggle collapse ---
	async function handleToggleCollapse(type: string, id: number) {
		const item = wsItems.find(i => i.entity_type === type && i.entity_id === id);
		if (!item) return;
		try {
			await updateWorkspaceItem(item.id, { collapsed: !item.collapsed });
			await refreshActiveWorkspace();
		} catch (err) {
			console.error('Failed to toggle collapse:', err);
		}
	}

	// --- Connection handlers ---
	async function handlePredicateSelect(tripleId: number, predicate: string) {
		await updateTriple(tripleId, predicate);
		await loadTriples();
	}

	async function handleConnectionSwap(tripleId: number) {
		await swapTripleDirection(tripleId);
		await loadTriples();
	}

	async function handleConnectionDelete(tripleId: number) {
		await deleteTriple(tripleId);
		await loadTriples();
		triggerEntityTagsRefresh();
	}

	// --- Query panel ---
	export function toggleQueryPanel() {
		queryPanelOpen = !queryPanelOpen;
		if (!queryPanelOpen) hiddenConnectionsFor = null;
	}

	// --- Editor panel ---
	export function toggleEditor() {
		editorOpen = !editorOpen;
	}

	async function handleEditorCommit(results: Array<{ entityType: string; entityId: number }>) {
		if (!wsId) return;
		const rect = viewportEl?.getBoundingClientRect();
		const vw = rect?.width ?? 800;
		const vh = rect?.height ?? 600;
		let baseX = (-panX + vw / 2) / zoom;
		let baseY = (-panY + vh / 2) / zoom;

		const DEFAULT_W = 150;
		const DEFAULT_H = 60;
		const placedRects: Array<{ x: number; y: number; w: number; h: number }> = [];

		for (const r of results) {
			let w = DEFAULT_W;
			let h = DEFAULT_H;
			if (r.entityType === 'collection') {
				const coll = $collections.find(c => c.id === r.entityId);
				const memberCount = coll?.items?.length ?? 0;
				w = ccWidth();
				h = ccHeight(memberCount, false);
			}

			const { x, y } = findNonOverlappingPosition(baseX, baseY, w, h, placedRects);
			await addWorkspaceItem(wsId, { entity_type: r.entityType, entity_id: r.entityId, x, y });
			placedRects.push({ x, y, w, h });
			baseX = x + w + 20;
		}

		await refreshActiveWorkspace();
		await loadTriples();
	}

	function handleQueryStateChange(state: typeof queryPanelState) {
		queryPanelState = state;
	}

	async function handleQueryResult(result: SearchResult) {
		if (!wsId) return;
		const key = `${result.type}:${result.id}`;
		const existingItem = wsItems.find(n => n.entity_type === result.type && n.entity_id === result.id);

		if (existingItem) {
			// Pan to it
			const rect = viewportEl?.getBoundingClientRect();
			if (rect) {
				panX = rect.width / 2 - existingItem.x * zoom;
				panY = rect.height / 2 - existingItem.y * zoom;
			}
			selectedCards = new Set([key]);
		} else {
			// Add just this entity at viewport center
			try {
				const rect = viewportEl?.getBoundingClientRect();
				const vw = rect?.width ?? 800;
				const vh = rect?.height ?? 600;
				const baseX = (-panX + vw / 2) / zoom;
				const baseY = (-panY + vh / 2) / zoom;
				const { x, y } = findNonOverlappingPosition(baseX, baseY);

				await addWorkspaceItem(wsId, { entity_type: result.type, entity_id: result.id, x, y });
				await refreshActiveWorkspace();
				await loadTriples();

				pulsingCards = new Set([key]);
				setTimeout(() => { pulsingCards = new Set(); }, 2000);
			} catch (err) {
				console.error('Failed to add entity to workspace:', err);
			}
		}
	}

	// --- Add new entity ---
	export async function handleAddEntity(entityType: string) {
		if (!wsId) return;
		try {
			let entity: any;
			const title = `New ${entityType}`;
			switch (entityType) {
				case 'project': entity = await createProject({ title, status: 'active' }); await loadProjects(); break;
				case 'log': entity = await createLog({ title }); await loadLogs(); break;
				case 'note': entity = await createNote({ title, content: '' }); await loadNotes(); break;
				case 'activity': entity = await createActivity({ title }); await loadActivities(); break;
				case 'source': entity = await createSource({ title }); await loadSources(); break;
				case 'actor': entity = await createActor({ full_name: title }); await loadActors(); break;
				case 'plan': entity = await createPlan({ title }); await loadPlans(); break;
				case 'collection': {
					const cats = get(categories);
					const wildcard = cats.find(c => c.member_entity_type === '*');
					const catId = wildcard?.id ?? (cats.length > 0 ? cats[0].id : null);
					if (catId === null) { console.error('No categories available'); return; }
					entity = await createCollection({ title, category_id: catId });
					await loadCollections(); break;
				}
				default: return;
			}
			await loadTags();

			// Position in center of viewport
			const rect = viewportEl?.getBoundingClientRect();
			const vw = rect?.width ?? 800;
			const vh = rect?.height ?? 600;
			const baseX = (-panX + vw / 2) / zoom;
			const baseY = (-panY + vh / 2) / zoom;
			const { x, y } = findNonOverlappingPosition(baseX, baseY);

			await addWorkspaceItem(wsId, { entity_type: entityType, entity_id: entity.id, x, y });
			await refreshActiveWorkspace();
			await loadTriples();

			const key = `${entityType}:${entity.id}`;
			pulsingCards = new Set([key]);
			setTimeout(() => { pulsingCards = new Set(); }, 2000);

			// Open edit modal for the new entity
			handleCardDblClick(entityType, entity.id);
		} catch (err) {
			console.error('Failed to create entity:', err);
		}
	}

	// --- Hidden connections badge click ---
	function handleHiddenConnectionsClick(type: string, id: number) {
		hiddenConnectionsFor = { type, id };
		queryPanelOpen = true;
	}

	// Clear selection
	function clearSelection() {
		selectedCards = new Set();
		showBulkTagInput = false;
		bulkTags = [];
		selectMode = false;
	}

	// --- Drag-from-query-panel drop handlers ---
	function handleViewportDragOver(e: DragEvent) {
		if (e.dataTransfer?.types.includes('application/wb-entity')) {
			e.preventDefault();
			e.dataTransfer.dropEffect = 'copy';
		}
	}

	async function handleViewportDrop(e: DragEvent) {
		e.preventDefault();
		const raw = e.dataTransfer?.getData('application/wb-entity');
		if (!raw || !wsId) return;

		let entities: Array<{ type: string; id: number; title: string }>;
		try {
			const parsed = JSON.parse(raw);
			// Support both array format (new) and single object (legacy)
			entities = Array.isArray(parsed) ? parsed : [parsed];
		} catch { return; }

		// Convert screen coords to canvas coords
		const rect = viewportEl?.getBoundingClientRect();
		if (!rect) return;
		const dropX = (e.clientX - rect.left - panX) / zoom;
		const dropY = (e.clientY - rect.top - panY) / zoom;

		const newKeys = new Set<string>();
		const GAP = 30;
		const CARD_W = 150;
		let offsetX = 0;
		let offsetY = 0;
		const COL_MAX = 4;
		let col = 0;

		try {
			for (const data of entities) {
				const key = `${data.type}:${data.id}`;
				const existingItem = wsItems.find(n => n.entity_type === data.type && n.entity_id === data.id);

				if (existingItem) {
					// Move existing item to drop position
					activeWorkspace.update(ws => {
						if (!ws) return ws;
						return {
							...ws,
							items: ws.items.map(item =>
								item.entity_type === data.type && item.entity_id === data.id
									? { ...item, x: dropX + offsetX, y: dropY + offsetY }
									: item
							)
						};
					});
					newKeys.add(key);
				} else {
					// Add entity at position
					await addWorkspaceItem(wsId, {
						entity_type: data.type,
						entity_id: data.id,
						x: dropX + offsetX,
						y: dropY + offsetY,
					});
					newKeys.add(key);
				}

				// Grid layout for multiple entities
				col++;
				offsetX += CARD_W + GAP;
				if (col >= COL_MAX) {
					col = 0;
					offsetX = 0;
					offsetY += 80 + GAP;
				}
			}

			await refreshActiveWorkspace();
			scheduleSavePositions();
			await loadTriples();

			if (newKeys.size > 0) {
				pulsingCards = new Set(newKeys);
				setTimeout(() => { pulsingCards = new Set(); }, 2000);
			}
		} catch (err) {
			console.error('Failed to drop entities onto workspace:', err);
		}
	}

	// --- Init ---
	onMount(async () => {
		await loadTriples();
		if (visibleNodes.length > 0) {
			requestAnimationFrame(() => zoomFit());
		}
	});

	// Auto-open query panel when external injection arrives (e.g. from dashboard topics)
	$effect(() => {
		if ($workspaceInjectedResults) {
			queryPanelOpen = true;
		}
	});
</script>

<div class="workspace-graph">
	<div class="viewport-wrapper">
		<GraphEditorPanel
			open={editorOpen}
			onClose={() => editorOpen = false}
			onCommit={handleEditorCommit}
		/>
		<div
			class="viewport"
			bind:this={viewportEl}
			onpointerdown={handleCanvasPointerDown}
			onpointermove={handlePointerMove}
			onpointerup={handlePointerUp}
			onwheel={handleWheel}
			ondragover={handleViewportDragOver}
			ondrop={handleViewportDrop}
		>
			<div
				class="canvas"
				bind:this={canvasEl}
				style:transform="translate({panX}px, {panY}px) scale({zoom})"
			>
				{#each containerNodes as node (`${node.entity_type}:${node.entity_id}`)}
					{@const entry = renderContainers.get(`${node.entity_type}:${node.entity_id}`)}
					{#if entry}
						{@const collKey = `${node.entity_type}:${node.entity_id}`}
						{@const memberDwellActive = memberDwellFired && memberDwellKey !== null && entry.members.some(m => `${m.entityType}:${m.entityId}` === memberDwellKey)}
						<CollectionContainer
							collectionId={node.entity_id}
							title={getEntityTitle(node.entity_type, node.entity_id)}
							x={node.x}
							y={node.y}
							color={ENTITY_COLORS['collection']}
							collapsed={node.collapsed}
							archived={getEntityData(node.entity_type, node.entity_id)?.is_archived ?? false}
							selected={selectedCards.has(collKey)}
							pulsing={pulsingCards.has(collKey)}
							highlighted={
								!memberDwellActive && (
									(dropTarget !== null && dropTarget.type === node.entity_type && dropTarget.id === node.entity_id) ||
									(dropTarget !== null && draggingKey === collKey)
								)
							}
							highlightedMemberKey={memberDwellActive ? memberDwellKey : null}
							members={entry.members}
							statusCycle={getStatusCycle(node.entity_id)}
							onPointerDown={(e) => handleContainerPointerDown(node.entity_type, node.entity_id, e)}
							onDblClick={() => handleCardDblClick(node.entity_type, node.entity_id)}
							onMemberDblClick={(type, id) => handleCardDblClick(type, id)}
							onMemberPointerDown={(type, id, e) => handleMemberPointerDown(type, id, e)}
							onStatusChange={handleStatusChange}
							onToggleCollapse={() => handleToggleCollapse(node.entity_type, node.entity_id)}
							onNestedToggleCollapse={handleNestedToggleCollapse}
							onContextMenu={(e) => handleCardContextMenu(node.entity_type, node.entity_id, e)}
						/>
						{#if (hiddenConnectionCounts.get(`${node.entity_type}:${node.entity_id}`) ?? 0) > 0}
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<div
								class="hidden-connections-badge"
								style:transform="translate({node.x + ccWidth() - 10}px, {node.y - 6}px)"
								onpointerdown={(e) => e.stopPropagation()}
								onclick={(e) => { e.stopPropagation(); handleHiddenConnectionsClick(node.entity_type, node.entity_id); }}
								title="Click to show hidden connections"
							>
								{hiddenConnectionCounts.get(`${node.entity_type}:${node.entity_id}`)}
							</div>
						{/if}
					{/if}
				{/each}

				<GraphConnections
					triples={filteredVisibleTriples}
					nodeMap={augmentedNodeMap}
					{collapsedNodes}
					onConnectionSwap={handleConnectionSwap}
					onConnectionDelete={handleConnectionDelete}
					onPredicateSelect={handlePredicateSelect}
				/>

				{#each standaloneNodes as node (`${node.entity_type}:${node.entity_id}`)}
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<div oncontextmenu={(e) => handleCardContextMenu(node.entity_type, node.entity_id, e)}>
						<GraphCard
							entityType={node.entity_type}
							entityId={node.entity_id}
							title={getEntityTitle(node.entity_type, node.entity_id)}
							x={node.x}
							y={node.y}
							color={ENTITY_COLORS[node.entity_type] ?? '#888'}
							collapsed={node.collapsed}
							archived={getEntityData(node.entity_type, node.entity_id)?.is_archived ?? false}
							status={getEntityData(node.entity_type, node.entity_id)?.status ?? ''}
							selected={selectedCards.has(`${node.entity_type}:${node.entity_id}`)}
							pulsing={pulsingCards.has(`${node.entity_type}:${node.entity_id}`)}
							highlighted={
								(dropTarget !== null && dropTarget.type === node.entity_type && dropTarget.id === node.entity_id) ||
								(dropTarget !== null && draggingKey === `${node.entity_type}:${node.entity_id}`)
							}
							zIndex={topZKey === `${node.entity_type}:${node.entity_id}` ? zCounter : 0}
							onPointerDown={(e) => handleCardPointerDown(node.entity_type, node.entity_id, e)}
							onDblClick={() => handleCardDblClick(node.entity_type, node.entity_id)}
							onToggleCollapse={() => handleToggleCollapse(node.entity_type, node.entity_id)}
						/>
						{#if (hiddenConnectionCounts.get(`${node.entity_type}:${node.entity_id}`) ?? 0) > 0}
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<div
								class="hidden-connections-badge"
								style:transform="translate({node.x + 140}px, {node.y - 6}px)"
								onpointerdown={(e) => e.stopPropagation()}
								onclick={(e) => { e.stopPropagation(); handleHiddenConnectionsClick(node.entity_type, node.entity_id); }}
								title="Click to show hidden connections"
							>
								{hiddenConnectionCounts.get(`${node.entity_type}:${node.entity_id}`)}
							</div>
						{/if}
					</div>
				{/each}
			</div>
		</div>

		{#if selectionRect}
			{@const left = Math.min(selectionRect.startX, selectionRect.currentX)}
			{@const top = Math.min(selectionRect.startY, selectionRect.currentY)}
			{@const width = Math.abs(selectionRect.currentX - selectionRect.startX)}
			{@const height = Math.abs(selectionRect.currentY - selectionRect.startY)}
			<div
				class="selection-marquee"
				style:left="{left}px"
				style:top="{top}px"
				style:width="{width}px"
				style:height="{height}px"
			></div>
		{/if}

		{#if selectionCount >= 2}
			<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
			<div class="selection-bar" onclick={(e) => e.stopPropagation()}>
				<span class="selection-count">{selectionCount} selected</span>
				<div class="selection-divider"></div>
				<button class="sel-btn sel-btn-remove" onclick={handleBulkRemove} disabled={bulkActionInProgress} title="Remove from workspace (keep in database)">Remove</button>
				<button class="sel-btn sel-btn-delete" onclick={() => (showBulkDelete = true)} disabled={bulkActionInProgress} title="Permanently delete entities">Delete</button>
				<div class="selection-divider"></div>
				<button class="sel-btn sel-btn-tags" onclick={handleBulkTagsClick} disabled={bulkActionInProgress} title="Manage tags">Tags</button>
				<button class="sel-btn sel-btn-cards" onclick={handleOpenInCards} disabled={bulkActionInProgress} title="Open in Cards panel">Cards</button>
				<div class="selection-divider"></div>
				<button class="sel-btn sel-btn-clear" onclick={clearSelection} disabled={bulkActionInProgress}>Clear</button>

				{#if showBulkTagInput}
					<div class="selection-tag-row">
						<TagInput
							attachedTags={bulkTags}
							targetType={selectedEntities[0]?.type ?? 'project'}
							targetId={selectedEntities[0]?.id ?? 0}
							onAttach={handleBulkAttachTag}
							onDetach={handleBulkDetachTag}
							onClose={() => (showBulkTagInput = false)}
						/>
					</div>
				{/if}
			</div>
		{/if}

		{#if selectMode && selectionCount < 2}
			<!-- Show select mode indicator when no items are selected yet -->
			<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
			<div class="selection-bar" onclick={(e) => e.stopPropagation()}>
				<span class="selection-count">Select mode — drag to select</span>
				<div class="selection-divider"></div>
				<button class="sel-btn sel-btn-clear" onclick={() => (selectMode = false)}>Exit</button>
			</div>
		{/if}

		{#if contextMenu}
			<div
				class="context-menu"
				style:left="{contextMenu.x}px"
				style:top="{contextMenu.y}px"
			>
				<button onclick={() => { handleCardDblClick(contextMenu!.type, contextMenu!.id); closeContextMenu(); }}>
					View
				</button>
				<button onclick={() => { handleRemoveFromWorkspace(contextMenu!.type, contextMenu!.id); closeContextMenu(); }}>
					Remove from workspace
				</button>
			</div>
		{/if}
	</div>

	<QueryPanel
		bind:this={queryPanelRef}
		open={queryPanelOpen}
		onClose={() => { queryPanelOpen = false; hiddenConnectionsFor = null; workspaceInjectedResults.set(null); }}
		onResultClick={handleQueryResult}
		onStateChange={handleQueryStateChange}
		resultActionLabel="Add to workspace"
		showArchivedToggle={false}
		showActiveRelatedToggle={false}
		selectionMode={true}
		boardEntityKeys={boardEntityKeySet}
		{injectedResults}
		{injectedLabel}
		onClearInjected={() => { hiddenConnectionsFor = null; workspaceInjectedResults.set(null); }}
	/>
</div>

{#if detailEntity}
	<EntityDetailPanel
		entityType={detailEntity.type}
		entityId={detailEntity.id}
		onClose={() => detailEntity = null}
		onDeleted={handleEntityDeleted}
	/>
{/if}

<ConfirmDialog
	open={showBulkDelete}
	message={`Delete ${selectionCount} selected entities? This cannot be undone.`}
	onConfirm={handleBulkDelete}
	onCancel={() => (showBulkDelete = false)}
/>

<style>
	.workspace-graph {
		flex: 1;
		display: flex;
		min-width: 0;
		min-height: 0;
		overflow: hidden;
		position: relative;
	}
	.viewport-wrapper {
		flex: 1;
		position: relative;
		overflow: hidden;
	}
	.viewport {
		width: 100%;
		height: 100%;
		overflow: hidden;
		cursor: grab;
		touch-action: none;
	}
	.viewport:active {
		cursor: grabbing;
	}
	.canvas {
		position: absolute;
		top: 0;
		left: 0;
		transform-origin: 0 0;
		will-change: transform;
	}
	.hidden-connections-badge {
		position: absolute;
		width: 20px;
		height: 20px;
		border-radius: 50%;
		background: #ef4444;
		color: white;
		font-size: 0.6rem;
		font-weight: 700;
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		z-index: 10;
		box-shadow: 0 1px 3px rgba(0,0,0,0.2);
		transition: box-shadow 0.15s, background 0.15s;
	}
	.hidden-connections-badge:hover {
		background: #dc2626;
		box-shadow: 0 0 0 3px rgba(239,68,68,0.3), 0 1px 3px rgba(0,0,0,0.2);
	}
	.selection-marquee {
		position: fixed;
		border: 1px dashed #3b82f6;
		background: rgba(59, 130, 246, 0.08);
		pointer-events: none;
		z-index: 30;
	}
	.selection-bar {
		position: absolute;
		bottom: 16px;
		left: 50%;
		transform: translateX(-50%);
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 8px;
		padding: 8px 16px;
		background: #1f2937;
		color: white;
		border-radius: 10px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
		z-index: 40;
		max-width: 90vw;
	}
	.selection-count {
		font-size: 0.78rem;
		font-weight: 500;
	}
	.selection-divider {
		width: 1px;
		height: 16px;
		background: rgba(255, 255, 255, 0.2);
	}
	.sel-btn {
		padding: 4px 10px;
		border: 1px solid rgba(255,255,255,0.2);
		border-radius: 6px;
		background: transparent;
		color: white;
		cursor: pointer;
		font-size: 0.72rem;
		font-weight: 500;
		transition: background 0.15s;
	}
	.sel-btn:hover {
		background: rgba(255,255,255,0.15);
	}
	.sel-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	.sel-btn-remove:hover {
		background: #b45309;
	}
	.sel-btn-delete:hover {
		background: #dc2626;
	}
	.sel-btn-tags:hover {
		background: rgba(255,255,255,0.2);
	}
	.sel-btn-cards:hover {
		background: #3b82f6;
	}
	.selection-tag-row {
		width: 100%;
		padding-top: 6px;
		border-top: 1px solid rgba(255,255,255,0.15);
	}
	.context-menu {
		position: fixed;
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 8px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
		z-index: 100;
		min-width: 160px;
		padding: 4px 0;
	}
	.context-menu button {
		display: block;
		width: 100%;
		padding: 8px 16px;
		border: none;
		background: none;
		cursor: pointer;
		font-size: 0.8rem;
		color: #374151;
		text-align: left;
		transition: background 0.1s;
	}
	.context-menu button:hover {
		background: #f3f4f6;
	}
</style>

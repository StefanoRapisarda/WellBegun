<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import type { KnowledgeTriple, BoardNode } from '$lib/types';
	import { boardNodes, triples, loadBoard, loadTriples, hiddenGraphEntities, graphFilterPanelOpen } from '$lib/stores/knowledgeGraph';
	import { focusSelection, isFocusActive } from '$lib/stores/focus';
	import { projects } from '$lib/stores/projects';
	import { logs } from '$lib/stores/logs';
	import { notes } from '$lib/stores/notes';
	import { activities } from '$lib/stores/activities';
	import { sources } from '$lib/stores/sources';
	import { actors } from '$lib/stores/actors';
	import { plans } from '$lib/stores/plans';
	import { collections } from '$lib/stores/collections';
	import { loadProjects } from '$lib/stores/projects';
	import { loadLogs } from '$lib/stores/logs';
	import { loadNotes } from '$lib/stores/notes';
	import { loadActivities } from '$lib/stores/activities';
	import { loadSources } from '$lib/stores/sources';
	import { loadActors } from '$lib/stores/actors';
	import { loadPlans } from '$lib/stores/plans';
	import { loadCollections } from '$lib/stores/collections';
	import { updateItem, updateCollection, createCollection, addItem, removeItem } from '$lib/api/collections';
	import { categories } from '$lib/stores/categories';
	import {
		upsertBoardNode,
		updateBoardNode,
		deleteBoardNode,
		updateTriple,
		swapTripleDirection,
		deleteTriple,
		populateAll,
		getTriplesForEntity
	} from '$lib/api/knowledge';
	import { createProject, archiveProject, unarchiveProject, deleteProject, activateProject, deactivateProject } from '$lib/api/projects';
	import { createLog, archiveLog, unarchiveLog, deleteLog, activateLog, deactivateLog } from '$lib/api/logs';
	import { createNote, archiveNote, unarchiveNote, deleteNote } from '$lib/api/notes';
	import { createActivity, archiveActivity, unarchiveActivity, deleteActivity, activateActivity, deactivateActivity } from '$lib/api/activities';
	import { createSource, archiveSource, unarchiveSource, deleteSource, activateSource, deactivateSource } from '$lib/api/sources';
	import { createActor, archiveActor, unarchiveActor, deleteActor, activateActor, deactivateActor } from '$lib/api/actors';
	import { createPlan, deletePlan, activatePlan, deactivatePlan, archivePlan } from '$lib/api/plans';
	import { attachTag, detachTag, getEntityTags, getAllEntityTagsBulk } from '$lib/api/tags';
	import { tags, loadTags, triggerEntityTagsRefresh, entityTagsVersion } from '$lib/stores/tags';
	import { activeEntityTagIds, isActiveRelated, showArchived, showActiveRelated, dateFilter, selectedFilterTags, isDateVisible, isTagVisible, isEntitySourceOfFilterTag } from '$lib/stores/dateFilter';
	import { activeTab } from '$lib/stores/activeTab';
	import { panelSelection, type EntityType as PanelEntityType } from '$lib/stores/panelSelection';
	import { panels, togglePanel } from '$lib/stores/panels';
	import type { Tag } from '$lib/types';
	import GraphCard from './GraphCard.svelte';
	import CollectionContainer from './CollectionContainer.svelte';
	import {
		containerWidth as ccWidth, containerHeight as ccHeight,
		containerHeightNested as ccHeightNested,
		type ContainerMember,
	} from './collectionLayout';
	import GraphConnections from './GraphConnections.svelte';
	import GraphToolbar from './GraphToolbar.svelte';
	import GraphEditorPanel from './GraphEditorPanel.svelte';
	import QueryPanel from '$lib/components/shared/QueryPanel.svelte';
	import type { SearchResult } from '$lib/api/search';
	import Modal from '$lib/components/shared/Modal.svelte';
	import ProjectForm from '$lib/components/forms/ProjectForm.svelte';
	import NoteForm from '$lib/components/forms/NoteForm.svelte';
	import LogEditForm from '$lib/components/forms/LogEditForm.svelte';
	import ActivityForm from '$lib/components/forms/ActivityForm.svelte';
	import SourceForm from '$lib/components/forms/SourceForm.svelte';
	import ActorForm from '$lib/components/forms/ActorForm.svelte';
	import PlanForm from '$lib/components/forms/PlanForm.svelte';
	import TagInput from '$lib/components/shared/TagInput.svelte';
	import TagBadge from '$lib/components/shared/TagBadge.svelte';
	import ConfirmDialog from '$lib/components/shared/ConfirmDialog.svelte';
	import { bulkUpsertBoardNodes } from '$lib/api/knowledge';
	import { structuralPredicates, loadPredicates, getStructuralPredicate } from '$lib/stores/predicates';
	import { graphInitialSelection } from '$lib/stores/graphInitialSelection';
	import { get } from 'svelte/store';
	import { captureGraphScreenshot } from '$lib/utils/graphScreenshot';

	// Color map matching panels store
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

	// ── Canvas state ──
	let panX = $state(0);
	let panY = $state(0);
	let zoom = $state(1);
	let canvasEl: HTMLDivElement | undefined = $state();
	let viewportEl: HTMLDivElement | undefined = $state();

	// ── Graph editor panel state ──
	let graphEditorOpen = $state(false);

	// ── Drag state ──
	const DRAG_THRESHOLD = 5;
	let dragStarted = $state(false);
	let draggingCard: { type: string; id: number; startX: number; startY: number; origX: number; origY: number } | null = $state(null);
	let isPanning = $state(false);
	let panStart = $state({ x: 0, y: 0, panX: 0, panY: 0 });

	// ── Connect state (drag-to-connect) ──
	let dropTarget: { type: string; id: number } | null = $state(null);
	let draggingKey: string | null = $state(null);

	// ── Member drag-out state ──
	// Tracks when a member is being dragged out of a collection container
	let draggingFromCollection: { collectionId: number; memberType: string; memberId: number; itemId?: number } | null = $state(null);

	// ── Z-index management (bring-to-front on interact) ──
	let topZKey: string | null = $state(null);
	let zCounter = $state(1);

	// ── Multi-selection state ──
	let selectedCards = $state<Set<string>>(new Set());
	let selectionCount = $derived(selectedCards.size);
	let selectedEntities = $derived.by(() =>
		[...selectedCards].map(key => {
			const [type, idStr] = key.split(':');
			return { type, id: Number(idStr) };
		})
	);
	let selectionCommonTags = $state<Tag[]>([]);
	let bulkActionInProgress = $state(false);
	let showConfirmDelete = $state(false);
	let showBulkTagInput = $state(false);
	let bulkTags = $state<Tag[]>([]);

	// ── Rectangle (marquee) selection state ──
	let selectMode = $state(false);
	let selectionRect: { startX: number; startY: number; currentX: number; currentY: number } | null = $state(null);

	// ── Group drag state ──
	let groupDragOrigPositions: Map<string, { x: number; y: number }> | null = $state(null);

	// ── Entity tags for filtering ──
	let nodeEntityTags = $state<Record<string, Tag[]>>({});

	$effect(() => {
		// Re-run when board nodes or tag version changes
		const _nodes = $boardNodes;
		const _version = $entityTagsVersion;
		(async () => {
			try {
				nodeEntityTags = await getAllEntityTagsBulk();
			} catch {
				nodeEntityTags = {};
			}
		})();
	});

	// ── Compute common tags across selected cards ──
	$effect(() => {
		const _tags = nodeEntityTags;
		const _sel = selectedCards;
		if (_sel.size === 0) { selectionCommonTags = []; return; }
		const tagSets = [..._sel].map(key => new Set((_tags[key] || []).map((t: Tag) => t.id)));
		const intersection = tagSets.reduce((acc, s) => new Set([...acc].filter(id => s.has(id))));
		const firstTags = _tags[[..._sel][0]] || [];
		selectionCommonTags = firstTags.filter((t: Tag) => intersection.has(t.id));
	});

	// ── Prune selection when nodes become invisible ──
	$effect(() => {
		if (selectedCards.size > 0) {
			const pruned = new Set([...selectedCards].filter(key => visibleNodeKeys.has(key)));
			if (pruned.size !== selectedCards.size) {
				selectedCards = pruned;
			}
		}
	});

	// ── Filter panel state (backed by persistent stores) ──
	let filterPanelOpen = $derived($graphFilterPanelOpen);
	let hiddenEntities = $derived($hiddenGraphEntities);

	function toggleFilterPanel() {
		graphFilterPanelOpen.update(v => !v);
	}

	// ── QueryPanel integration ──
	let boardEntityKeySet = $derived(new Set($boardNodes.map(n => `${n.entity_type}:${n.entity_id}`)));
	let queryPanelState = $state<{ results: SearchResult[]; includeArchived: boolean; showActiveRelated: boolean; hasActiveFilters: boolean }>({
		results: [],
		includeArchived: false,
		showActiveRelated: false,
		hasActiveFilters: false,
	});

	function handleQueryStateChange(state: typeof queryPanelState) {
		queryPanelState = state;
	}

	async function handleQueryResult(result: SearchResult) {
		const key = `${result.type}:${result.id}`;
		const existingNode = $boardNodes.find(n => n.entity_type === result.type && n.entity_id === result.id);

		if (existingNode) {
			// Pan/focus to the existing node
			const rect = viewportEl?.getBoundingClientRect();
			if (rect) {
				panX = rect.width / 2 - existingNode.x * zoom;
				panY = rect.height / 2 - existingNode.y * zoom;
			}
			selectedCards = new Set([key]);
		} else {
			// Add entity to the board
			const rect = viewportEl?.getBoundingClientRect();
			const vw = rect?.width ?? 800;
			const vh = rect?.height ?? 600;
			const baseX = (-panX + vw / 2) / zoom;
			const baseY = (-panY + vh / 2) / zoom;
			const { x: cx, y: cy } = findNonOverlappingPosition(baseX, baseY);

			try {
				await upsertBoardNode({ entity_type: result.type, entity_id: result.id, x: cx, y: cy });
				await reloadBoard();
			} catch (err) {
				console.error('Failed to add entity to board:', err);
			}
		}
	}

	// Check if a board node passes the filter criteria (archived, active-related)
	function passesUpperFilters(n: BoardNode): boolean {
		const entityData = getEntityData(n.entity_type, n.entity_id);
		if (!entityData) return false;
		if (!$showArchived && entityData.is_archived) return false;
		if ($showActiveRelated) {
			const key = `${n.entity_type}:${n.entity_id}`;
			const nodeTags = nodeEntityTags[key] || [];
			const isSelfActive = (n.entity_type === 'project' && entityData.is_active) ||
				(n.entity_type === 'activity' && entityData.is_active);
			if (!isActiveRelated(nodeTags, $activeEntityTagIds, isSelfActive)) return false;
		}
		return true;
	}

	function isEntityVisible(type: string, id: number): boolean {
		return !hiddenEntities.has(`${type}:${id}`);
	}

	function toggleEntity(key: string) {
		hiddenGraphEntities.update(current => {
			const next = new Set(current);
			if (next.has(key)) {
				next.delete(key);
			} else {
				next.add(key);
			}
			return next;
		});
	}

	function toggleType(type: string) {
		const nodesOfType = $boardNodes.filter(n => n.entity_type === type && passesUpperFilters(n));
		hiddenGraphEntities.update(current => {
			const allHidden = nodesOfType.every(n => current.has(`${n.entity_type}:${n.entity_id}`));
			const next = new Set(current);
			if (allHidden) {
				for (const n of nodesOfType) {
					next.delete(`${n.entity_type}:${n.entity_id}`);
				}
			} else {
				for (const n of nodesOfType) {
					next.add(`${n.entity_type}:${n.entity_id}`);
				}
			}
			return next;
		});
	}

	// QueryPanel search result keys — used to filter board visibility when query is active
	let queryResultKeys = $derived(new Set(queryPanelState.results.map(r => `${r.type}:${r.id}`)));
	let queryHasActiveFilters = $derived(queryPanelState.hasActiveFilters);

	// Filtered data for rendering
	let visibleNodes = $derived(
		$boardNodes.filter(n => {
			if (!isEntityVisible(n.entity_type, n.entity_id)) return false;
			if (hiddenByCollapse.has(`${n.entity_type}:${n.entity_id}`)) return false;
			const entityData = getEntityData(n.entity_type, n.entity_id);
			if (!entityData) return false;
			// Archived filter (shared store)
			if (!$showArchived && entityData.is_archived) return false;
			// Active-related filter (shared store)
			if ($showActiveRelated) {
				const key = `${n.entity_type}:${n.entity_id}`;
				const nodeTags = nodeEntityTags[key] || [];
				const isSelfActive = (n.entity_type === 'project' && entityData.is_active) ||
					(n.entity_type === 'activity' && entityData.is_active);
				if (!isActiveRelated(nodeTags, $activeEntityTagIds, isSelfActive)) return false;
			}
			// Date filter (shared store)
			if (!isDateVisible(entityData, $dateFilter)) return false;
			// Tag filter (shared store)
			{
				const key = `${n.entity_type}:${n.entity_id}`;
				const nodeTags = nodeEntityTags[key] || [];
				if (!isTagVisible(nodeTags, $selectedFilterTags) && !isEntitySourceOfFilterTag(n.entity_type, n.entity_id, $selectedFilterTags)) return false;
			}
			// When query panel has active filters, only show matching board nodes
			if (filterPanelOpen && queryHasActiveFilters) {
				const key = `${n.entity_type}:${n.entity_id}`;
				if (!queryResultKeys.has(key)) return false;
			}
			return true;
		})
	);

	let visibleNodeKeys = $derived(new Set(visibleNodes.map(n => `${n.entity_type}:${n.entity_id}`)));

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

	// Build collection containers: collection nodes with their member entities
	let collectionContainerMap = $derived.by(() => {
		const map = new Map<string, { collectionId: number; members: ContainerMember[] }>();
		for (const node of visibleNodes) {
			if (node.entity_type !== 'collection') continue;
			const members = buildMembers(node.entity_id);
			if (members.length > 0) {
				map.set(`collection:${node.entity_id}`, { collectionId: node.entity_id, members });
			}
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
		await loadCollections();
	}

	// Keys of entities rendered inside containers (not standalone)
	// Exclude the currently-dragged member so it pops out as a standalone card during drag
	let containedMemberKeys = $derived.by(() => {
		const s = new Set<string>();
		function addMembers(members: ContainerMember[]) {
			for (const m of members) {
				const mk = `${m.entityType}:${m.entityId}`;
				if (mk === draggingKey && !groupDragOrigPositions) continue;
				s.add(mk);
				if (m.nestedMembers) {
					addMembers(m.nestedMembers);
				}
			}
		}
		for (const [, entry] of collectionContainerMap) {
			addMembers(entry.members);
		}
		return s;
	});

	// Filtered containers for rendering — excludes dragged member from its container
	let renderContainers = $derived.by(() => {
		if (!draggingKey || groupDragOrigPositions) return collectionContainerMap;
		const filtered = new Map<string, { collectionId: number; members: ContainerMember[] }>();
		for (const [k, entry] of collectionContainerMap) {
			const filteredMembers = entry.members.filter(m => `${m.entityType}:${m.entityId}` !== draggingKey);
			filtered.set(k, { ...entry, members: filteredMembers });
		}
		return filtered;
	});

	// Split visible nodes into containers (collections with members) and standalone
	let containerCollectionKeys = $derived(new Set(collectionContainerMap.keys()));
	let containerNodes = $derived(visibleNodes.filter(n => {
		const key = `${n.entity_type}:${n.entity_id}`;
		return containerCollectionKeys.has(key) && !containedMemberKeys.has(key);
	}));
	let standaloneNodes = $derived(
		visibleNodes.filter(n => {
			const key = `${n.entity_type}:${n.entity_id}`;
			return !containedMemberKeys.has(key) && !containerCollectionKeys.has(key);
		})
	);

	// Augmented node map that includes container dimensions for collections
	let augmentedNodeMap = $derived.by(() => {
		const map = new Map<string, BoardNode>();
		for (const node of $boardNodes) {
			map.set(`${node.entity_type}:${node.entity_id}`, node);
		}
		for (const [collKey, entry] of collectionContainerMap) {
			const existing = map.get(collKey);
			if (existing) {
				map.set(collKey, { ...existing, w: ccWidth(), h: ccHeightNested(entry.members, existing.collapsed) });
			}
		}
		return map;
	});

	let visibleTriples = $derived(
		$triples.filter(t => {
			if (!visibleNodeKeys.has(`${t.subject_type}:${t.subject_id}`)) return false;
			if (!visibleNodeKeys.has(`${t.object_type}:${t.object_id}`)) return false;
			// Hide collection→member structural triples when collection is rendered as container
			const sk = `${t.subject_type}:${t.subject_id}`;
			const ok = `${t.object_type}:${t.object_id}`;
			if (containerCollectionKeys.has(sk) && containedMemberKeys.has(ok)) return false;
			if (containerCollectionKeys.has(ok) && containedMemberKeys.has(sk)) return false;
			return true;
		})
	);

	// ── Edit modal state ──
	let editModal: { type: string; id: number; data: any } | null = $state(null);
	let modalTags = $state<Tag[]>([]);

	// ── Derived data ──
	let nodeMap = $derived.by(() => {
		const map = new Map<string, BoardNode>();
		for (const node of $boardNodes) {
			map.set(`${node.entity_type}:${node.entity_id}`, node);
		}
		return map;
	});

	// Only explicitly collapsed nodes suppress their own connections
	let collapsedNodes = $derived.by(() => {
		const explicit = new Set<string>();
		for (const node of $boardNodes) {
			if (node.collapsed) explicit.add(`${node.entity_type}:${node.entity_id}`);
		}
		return explicit;
	});

	// Nodes hidden because they are descendants of a collapsed node
	// (the collapsed node itself stays visible, only its children/descendants hide)
	let hiddenByCollapse = $derived.by(() => {
		const roots = new Set<string>();
		for (const node of $boardNodes) {
			if (node.collapsed) roots.add(`${node.entity_type}:${node.entity_id}`);
		}
		if (roots.size === 0) return new Set<string>();

		const children = new Map<string, string[]>();
		for (const t of $triples) {
			const subKey = `${t.subject_type}:${t.subject_id}`;
			const objKey = `${t.object_type}:${t.object_id}`;
			if (!children.has(subKey)) children.set(subKey, []);
			children.get(subKey)!.push(objKey);
		}

		// BFS from roots, collect only descendants (roots stay visible)
		const descendants = new Set<string>();
		const queue = [...roots];
		while (queue.length > 0) {
			const key = queue.shift()!;
			const kids = children.get(key);
			if (!kids) continue;
			for (const child of kids) {
				if (!descendants.has(child)) {
					// Never hide explicit board nodes; they were placed by the user
					if (boardEntityKeySet.has(child)) continue;
					descendants.add(child);
					queue.push(child);
				}
			}
		}
		return descendants;
	});

	// Resolve entity titles from their stores
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

	// ── Card interactions ──

	function handleCardPointerDown(type: string, id: number, e: PointerEvent) {
		if (e.button !== 0) return;
		e.stopPropagation();
		e.preventDefault();

		const key = `${type}:${id}`;

		// Bring card to front
		topZKey = key;
		zCounter++;

		// Cmd+Click (Mac) or Ctrl+Click (non-Mac): toggle selection
		if (e.metaKey || e.ctrlKey) {
			const next = new Set(selectedCards);
			if (next.has(key)) {
				next.delete(key);
			} else {
				next.add(key);
			}
			selectedCards = next;
			return;
		}

		// If clicking a card that's already part of a multi-selection, keep the selection for group drag
		const isInMultiSelection = selectedCards.size >= 2 && selectedCards.has(key);
		if (!isInMultiSelection) {
			selectedCards = new Set([key]);
		}

		const node = nodeMap.get(key);
		if (!node) return;
		dragStarted = false;
		draggingCard = {
			type,
			id,
			startX: e.clientX,
			startY: e.clientY,
			origX: node.x,
			origY: node.y
		};
		draggingKey = `${type}:${id}`;

		// Snapshot original positions of all selected cards for group drag
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

	function handleMemberPointerDown(containerCollectionId: number, memberType: string, memberId: number, e: PointerEvent) {
		if (e.button !== 0) return;
		e.stopPropagation();
		e.preventDefault();

		// Find the container node to compute a starting position for the member
		const containerNode = nodeMap.get(`collection:${containerCollectionId}`);
		if (!containerNode) return;

		// Find the collection item id for later removal
		const coll = $collections.find(c => c.id === containerCollectionId);
		const item = coll?.items?.find((i: any) => i.member_entity_type === memberType && i.member_entity_id === memberId);

		// Create a temporary board node at the container position so the standard drag works
		const tempX = containerNode.x;
		const tempY = containerNode.y;
		boardNodes.update(nodes => {
			// Remove any existing node for this entity first
			const filtered = nodes.filter(n => !(n.entity_type === memberType && n.entity_id === memberId));
			return [...filtered, {
				id: -1,
				entity_type: memberType,
				entity_id: memberId,
				x: tempX,
				y: tempY,
				collapsed: memberType === 'collection' ? false : true,
				created_at: new Date().toISOString(),
				updated_at: new Date().toISOString(),
			} as any];
		});

		draggingFromCollection = {
			collectionId: containerCollectionId,
			memberType,
			memberId,
			itemId: item?.id,
		};

		// Now kick off the standard card drag
		const key = `${memberType}:${memberId}`;
		topZKey = key;
		zCounter++;
		selectedCards = new Set([key]);
		dragStarted = false;
		draggingCard = {
			type: memberType,
			id: memberId,
			startX: e.clientX,
			startY: e.clientY,
			origX: tempX,
			origY: tempY,
		};
		draggingKey = key;
		groupDragOrigPositions = null;

		document.addEventListener('pointermove', handleDragMove);
		document.addEventListener('pointerup', handleDragUp);
	}

	function handleDragMove(e: PointerEvent) {
		if (!draggingCard) return;

		// Check movement threshold before starting actual drag
		if (!dragStarted) {
			const dist = Math.hypot(e.clientX - draggingCard.startX, e.clientY - draggingCard.startY);
			if (dist < DRAG_THRESHOLD) return;
			dragStarted = true;
		}

		const dx = (e.clientX - draggingCard.startX) / zoom;
		const dy = (e.clientY - draggingCard.startY) / zoom;

		// Group drag: move all selected cards together
		if (groupDragOrigPositions && groupDragOrigPositions.size >= 2) {
			boardNodes.update(nodes =>
				nodes.map(n => {
					const nKey = `${n.entity_type}:${n.entity_id}`;
					const orig = groupDragOrigPositions!.get(nKey);
					if (orig) {
						return { ...n, x: orig.x + dx, y: orig.y + dy };
					}
					return n;
				})
			);
			// Drop target detection for group drag (based on lead card position)
			const leadX = draggingCard.origX + dx;
			const leadY = draggingCard.origY + dy;
			const leadAug = augmentedNodeMap.get(`${draggingCard.type}:${draggingCard.id}`);
			const leadW = leadAug?.w ?? 150;
			const leadH = leadAug?.h ?? 60;
			const centerX = leadX + leadW / 2;
			const centerY = leadY + leadH / 2;
			let found: { type: string; id: number } | null = null;
			for (const node of visibleNodes) {
				const nk = `${node.entity_type}:${node.entity_id}`;
				if (selectedCards.has(nk)) continue;
				const an = augmentedNodeMap.get(nk);
				const nw = an?.w ?? 150;
				const nh = an?.h ?? 60;
				if (centerX >= node.x && centerX <= node.x + nw &&
					centerY >= node.y && centerY <= node.y + nh) {
					found = { type: node.entity_type, id: node.entity_id };
					break;
				}
			}
			dropTarget = found;
		} else {
			// Single card drag
			const newX = draggingCard.origX + dx;
			const newY = draggingCard.origY + dy;

			boardNodes.update(nodes =>
				nodes.map(n =>
					n.entity_type === draggingCard!.type && n.entity_id === draggingCard!.id
						? { ...n, x: newX, y: newY }
						: n
				)
			);

			// Check for drop target: dragged card's center must land inside a visible card
			const DEF_W = 150;
			const DEF_H = 60;
			const centerX = newX + DEF_W / 2;
			const centerY = newY + DEF_H / 2;
			let found: { type: string; id: number } | null = null;
			for (const node of visibleNodes) {
				if (node.entity_type === draggingCard.type && node.entity_id === draggingCard.id) continue;
				const nk = `${node.entity_type}:${node.entity_id}`;
				const aug = augmentedNodeMap.get(nk);
				const nw = aug?.w ?? DEF_W;
				const nh = aug?.h ?? DEF_H;
				if (centerX >= node.x && centerX <= node.x + nw &&
					centerY >= node.y && centerY <= node.y + nh) {
					found = { type: node.entity_type, id: node.entity_id };
					break;
				}
			}
			dropTarget = found;
		}
	}

	async function handleDragUp(_e: PointerEvent) {
		document.removeEventListener('pointermove', handleDragMove);
		document.removeEventListener('pointerup', handleDragUp);

		if (!draggingCard) return;
		const { type, id, origX, origY } = draggingCard;
		const wasGroupDrag = groupDragOrigPositions && groupDragOrigPositions.size >= 2;

		if (!dragStarted) {
			// Click (no drag): if was part of multi-selection, select just this card
			if (wasGroupDrag) {
				selectedCards = new Set([`${type}:${id}`]);
			}
			// If this was a member click (no drag), remove the temp board node
			if (draggingFromCollection) {
				boardNodes.update(nodes => nodes.filter(n => !(n.entity_type === type && n.entity_id === id && (n as any).id === -1)));
				draggingFromCollection = null;
			}
			draggingCard = null;
			draggingKey = null;
			groupDragOrigPositions = null;
			return;
		}

		// Actual drag happened
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
					// Delete board nodes — entities now render inside the collection container
					for (const selKey of selectedCards) {
						const [sType, sIdStr] = selKey.split(':');
						if (sType === 'collection' && Number(sIdStr) === dt.id) continue;
						try { await deleteBoardNode(sType, Number(sIdStr)); } catch {}
					}
					await loadCollections();
					await loadBoard();
				} else {
					// Connect all selected: snap back positions, then attach tags
					boardNodes.update(nodes =>
						nodes.map(n => {
							const nk = `${n.entity_type}:${n.entity_id}`;
							const orig = savedPositions.get(nk);
							if (orig) return { ...n, x: orig.x, y: orig.y, collapsed: false };
							if (n.entity_type === dt.type && n.entity_id === dt.id)
								return { ...n, collapsed: false };
							return n;
						})
					);
					for (const selKey of selectedCards) {
						const [sType, sIdStr] = selKey.split(':');
						const subjectTag = $tags.find(t => t.entity_type === sType && t.entity_id === Number(sIdStr));
						if (subjectTag) {
							await attachTag(subjectTag.id, dt.type, dt.id);
						}
					}
					await loadTags();
					// Save snapped-back positions
					const nodesToSave: { entity_type: string; entity_id: number; x: number; y: number }[] = [];
					for (const selKey of selectedCards) {
						const orig = savedPositions.get(selKey);
						if (orig) {
							const [sType, sIdStr] = selKey.split(':');
							nodesToSave.push({ entity_type: sType, entity_id: Number(sIdStr), x: orig.x, y: orig.y });
						}
					}
					try { await bulkUpsertBoardNodes(nodesToSave); } catch {}
				}
				await loadTriples();
			} catch (err) {
				console.error('Failed to interact with drop target:', err);
			}
			dropTarget = null;
		} else if (wasGroupDrag) {
			// Group drag: save all moved positions
			const nodesToSave: { entity_type: string; entity_id: number; x: number; y: number }[] = [];
			for (const selKey of selectedCards) {
				const n = nodeMap.get(selKey);
				if (n) {
					nodesToSave.push({ entity_type: n.entity_type, entity_id: n.entity_id, x: n.x, y: n.y });
				}
			}
			try {
				await bulkUpsertBoardNodes(nodesToSave);
			} catch (err) {
				console.error('Failed to save group positions:', err);
			}
		} else if (dropTarget) {
			const dt = dropTarget;
			// If dragged from another collection, remove from source collection first
			if (draggingFromCollection?.itemId) {
				try { await removeItem(draggingFromCollection.itemId); } catch {}
			}
			if (dt.type === 'collection' && !(type === 'collection' && id === dt.id)) {
				// Drop onto a collection: add as member and remove from board
				try {
					const coll = $collections.find(c => c.id === dt.id);
					if (coll) {
						const cat = $categories.find(c => c.id === coll.category_id);
						if (cat && cat.member_entity_type !== '*') {
							const wildcard = $categories.find(c => c.member_entity_type === '*');
							if (wildcard) {
								await updateCollection(dt.id, { category_id: wildcard.id } as any);
							}
						}
						const existingKeys = new Set(
							(coll.items || []).map((i: any) => `${i.member_entity_type}:${i.member_entity_id}`)
						);
						if (!existingKeys.has(`${type}:${id}`)) {
							await addItem(dt.id, { member_entity_type: type, member_entity_id: id });
						}
						try { await deleteBoardNode(type, id); } catch {}
						await loadCollections();
						await loadBoard();
					}
				} catch (err) {
					console.error('Failed to add to collection:', err);
				}
			} else {
				// Drag-to-connect: snap card back and un-collapse both endpoints
				boardNodes.update(nodes =>
					nodes.map(n => {
						if (n.entity_type === type && n.entity_id === id)
							return { ...n, x: origX, y: origY, collapsed: false };
						if (n.entity_type === dt.type && n.entity_id === dt.id)
							return { ...n, collapsed: false };
						return n;
					})
				);

				try {
					const subjectTag = $tags.find(
						t => t.entity_type === type && t.entity_id === id
					);
					if (subjectTag) {
						await attachTag(subjectTag.id, dt.type, dt.id);
						await loadTags();
					}
				} catch (err) {
					console.error('Failed to attach tag:', err);
				}
				await loadTriples();

				try {
					await upsertBoardNode({ entity_type: type, entity_id: id, x: origX, y: origY });
					await updateBoardNode(type, id, { collapsed: false });
					await updateBoardNode(dt.type, dt.id, { collapsed: false });
				} catch {}
			}
			dropTarget = null;
		} else {
			// Single card drag — save new position
			const node = nodeMap.get(`${type}:${id}`);
			if (node) {
				try {
					// If dragged out of a collection, remove from collection and persist board node
					if (draggingFromCollection) {
						const dfc = draggingFromCollection;
						if (dfc.itemId) {
							await removeItem(dfc.itemId);
						}
						// Persist board node — collections are restored expanded
						const shouldExpand = type === 'collection';
						await upsertBoardNode({ entity_type: type, entity_id: id, x: node.x, y: node.y });
						if (shouldExpand) {
							await updateBoardNode(type, id, { collapsed: false });
						}
						await Promise.all([loadCollections(), loadBoard()]);
					} else {
						await upsertBoardNode({ entity_type: type, entity_id: id, x: node.x, y: node.y });
					}
				} catch (err) {
					console.error('Failed to save node position:', err);
				}
			}
		}
		draggingFromCollection = null;
		draggingCard = null;
		draggingKey = null;
		groupDragOrigPositions = null;
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
			// Compute the rectangle in canvas coordinates and select cards within it
			const rect = viewportEl?.getBoundingClientRect();
			if (rect) {
				const x1 = (Math.min(selectionRect.startX, selectionRect.currentX) - rect.left - panX) / zoom;
				const y1 = (Math.min(selectionRect.startY, selectionRect.currentY) - rect.top - panY) / zoom;
				const x2 = (Math.max(selectionRect.startX, selectionRect.currentX) - rect.left - panX) / zoom;
				const y2 = (Math.max(selectionRect.startY, selectionRect.currentY) - rect.top - panY) / zoom;

				const CARD_W = 150;
				const CARD_H = 60;
				const next = new Set<string>();
				for (const node of visibleNodes) {
					// Card is selected if it overlaps the selection rectangle
					if (node.x + CARD_W >= x1 && node.x <= x2 &&
						node.y + CARD_H >= y1 && node.y <= y2) {
						next.add(`${node.entity_type}:${node.entity_id}`);
					}
				}
				if (next.size > 0) {
					selectedCards = next;
				}
			}
			selectionRect = null;
		}
	}

	// ── Canvas pan / rectangle selection ──

	function handleCanvasPointerDown(e: PointerEvent) {
		if (e.button !== 0) return;

		// selectMode toggle or Cmd/Ctrl+drag or Shift+drag on canvas: rectangle selection
		if (selectMode || e.metaKey || e.ctrlKey || e.shiftKey) {
			selectionRect = {
				startX: e.clientX,
				startY: e.clientY,
				currentX: e.clientX,
				currentY: e.clientY
			};
			return;
		}

		// Normal click on canvas: clear selection, start panning
		if (selectedCards.size > 0) {
			selectedCards = new Set();
		}
		isPanning = true;
		panStart = { x: e.clientX, y: e.clientY, panX, panY };
	}

	// ── Zoom ──

	function handleWheel(e: WheelEvent) {
		e.preventDefault();
		const oldZoom = zoom;
		const factor = 1 + e.deltaY * -0.001;
		const newZoom = Math.min(3, Math.max(0.2, zoom * factor));

		// Zoom toward cursor
		const rect = viewportEl!.getBoundingClientRect();
		const cursorX = e.clientX - rect.left;
		const cursorY = e.clientY - rect.top;
		panX = cursorX - (cursorX - panX) * (newZoom / oldZoom);
		panY = cursorY - (cursorY - panY) * (newZoom / oldZoom);
		zoom = newZoom;
	}

	function zoomIn() {
		zoom = Math.min(3, zoom * 1.2);
	}

	function zoomOut() {
		zoom = Math.max(0.2, zoom / 1.2);
	}

	function zoomFit() {
		if (visibleNodes.length === 0) {
			panX = 0;
			panY = 0;
			zoom = 1;
			return;
		}
		let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
		for (const node of visibleNodes) {
			minX = Math.min(minX, node.x);
			minY = Math.min(minY, node.y);
			maxX = Math.max(maxX, node.x + 150);
			maxY = Math.max(maxY, node.y + 60);
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

	function handleScreenshot() {
		if (!canvasEl) return;
		const rects = visibleNodes.map(n => {
			const aug = augmentedNodeMap.get(`${n.entity_type}:${n.entity_id}`);
			return { x: n.x, y: n.y, w: aug?.w ?? 150, h: aug?.h ?? 60 };
		});
		captureGraphScreenshot(canvasEl, rects, 'knowledge-graph');
	}

	// ── Add entity from toolbar ──

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
			// Check existing board nodes using their actual dimensions
			for (const node of $boardNodes) {
				const aug = augmentedNodeMap.get(`${node.entity_type}:${node.entity_id}`);
				const nw = aug?.w ?? DEFAULT_W;
				const nh = aug?.h ?? DEFAULT_H;
				if (
					x < node.x + nw + GAP &&
					x + newW + GAP > node.x &&
					y < node.y + nh + GAP &&
					y + newH + GAP > node.y
				) {
					return true;
				}
			}
			// Check against entities placed earlier in the same batch
			for (const rect of extraRects) {
				if (
					x < rect.x + rect.w + GAP &&
					x + newW + GAP > rect.x &&
					y < rect.y + rect.h + GAP &&
					y + newH + GAP > rect.y
				) {
					return true;
				}
			}
			return false;
		}

		if (!overlapsAny(baseX, baseY)) return { x: baseX, y: baseY };

		// Spiral outward to find a free spot
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
		// Fallback — far right
		return { x: baseX + 500, y: baseY };
	}

	async function handleAddEntity(entityType: string) {
		const rect = viewportEl?.getBoundingClientRect();
		const vw = rect?.width ?? 800;
		const vh = rect?.height ?? 600;
		const baseX = (-panX + vw / 2) / zoom;
		const baseY = (-panY + vh / 2) / zoom;
		const { x: cx, y: cy } = findNonOverlappingPosition(baseX, baseY);

		let created: { id: number } | null = null;
		const now = new Date().toISOString().slice(0, 16).replace('T', ' ');
		try {
			switch (entityType) {
				case 'project': created = await createProject({ title: `New Project ${now}` }); await loadProjects(); await loadTags(); break;
				case 'log': created = await createLog({ title: `New Log ${now}` }); await loadLogs(); await loadTags(); break;
				case 'note': created = await createNote({ title: `New Note ${now}` }); await loadNotes(); await loadTags(); break;
				case 'activity': created = await createActivity({ title: `New Activity ${now}` }); await loadActivities(); await loadTags(); break;
				case 'source': created = await createSource({ title: `New Source ${now}` }); await loadSources(); await loadTags(); break;
				case 'actor': created = await createActor({ full_name: `New Actor ${now}` }); await loadActors(); await loadTags(); break;
				case 'plan': created = await createPlan({ title: `New Plan ${now}` }); await loadPlans(); await loadTags(); break;
				case 'collection': {
					const cats = get(categories);
					const wildcard = cats.find(c => c.member_entity_type === '*');
					const catId = wildcard?.id ?? (cats.length > 0 ? cats[0].id : null);
					if (catId === null) { console.error('No categories available'); return; }
					created = await createCollection({ title: `New Collection ${now}`, category_id: catId });
					await loadCollections(); await loadTags(); break;
				}
			}
		} catch (err) {
			console.error('Failed to create entity:', err);
			return;
		}

		if (created) {
			try {
				await upsertBoardNode({ entity_type: entityType, entity_id: created.id, x: cx, y: cy });
				await reloadBoard();
			} catch (err) {
				console.error('Failed to save board node:', err);
			}
		}
	}

	// ── Graph editor commit handler ──

	async function handleEditorCommit(results: Array<{ entityType: string; entityId: number }>) {
		const rect = viewportEl?.getBoundingClientRect();
		const vw = rect?.width ?? 800;
		const vh = rect?.height ?? 600;
		let baseX = (-panX + vw / 2) / zoom;
		let baseY = (-panY + vh / 2) / zoom;

		const DEFAULT_W = 150;
		const DEFAULT_H = 60;
		const placedRects: Array<{ x: number; y: number; w: number; h: number }> = [];

		for (const r of results) {
			// Determine actual dimensions for this entity
			let w = DEFAULT_W;
			let h = DEFAULT_H;
			if (r.entityType === 'collection') {
				const coll = $collections.find(c => c.id === r.entityId);
				const memberCount = coll?.items?.length ?? 0;
				w = ccWidth();
				h = ccHeight(memberCount, false);
			}

			const { x, y } = findNonOverlappingPosition(baseX, baseY, w, h, placedRects);
			await upsertBoardNode({ entity_type: r.entityType, entity_id: r.entityId, x, y });
			placedRects.push({ x, y, w, h });
			baseX = x + w + 20;
		}

		await reloadBoard();
	}

	// ── Toggle card collapse ──

	async function handleToggleCollapse(type: string, id: number) {
		const node = nodeMap.get(`${type}:${id}`);
		if (!node) return;
		const newCollapsed = !node.collapsed;
		// Optimistic local update
		boardNodes.update(nodes =>
			nodes.map(n =>
				n.entity_type === type && n.entity_id === id
					? { ...n, collapsed: newCollapsed }
					: n
			)
		);
		// Persist to backend
		try {
			await updateBoardNode(type, id, { collapsed: newCollapsed });
		} catch (err) {
			console.error('Failed to persist collapse state:', err);
		}
	}

	// ── Double-click → edit modal ──

	async function handleCardDblClick(type: string, id: number) {
		const data = getEntityData(type, id);
		if (!data) return;
		editModal = { type, id, data };
		try {
			modalTags = await getEntityTags(type, id);
		} catch {
			modalTags = [];
		}
	}

	async function handleModalAttachTag(tag: Tag) {
		if (!editModal) return;
		await attachTag(tag.id, editModal.type, editModal.id);
		modalTags = await getEntityTags(editModal.type, editModal.id);
		triggerEntityTagsRefresh();
	}

	async function handleModalDetachTag(tag: Tag) {
		if (!editModal) return;
		await detachTag(tag.id, editModal.type, editModal.id);
		modalTags = await getEntityTags(editModal.type, editModal.id);
		triggerEntityTagsRefresh();
	}

	async function closeEditModal() {
		if (editModal) {
			// Reload the relevant store
			switch (editModal.type) {
				case 'project': await Promise.all([loadProjects(), loadTags()]); break;
				case 'log': await Promise.all([loadLogs(), loadTags()]); break;
				case 'note': await Promise.all([loadNotes(), loadTags()]); break;
				case 'activity': await Promise.all([loadActivities(), loadTags()]); break;
				case 'source': await Promise.all([loadSources(), loadTags()]); break;
				case 'actor': await Promise.all([loadActors(), loadTags()]); break;
				case 'plan': await Promise.all([loadPlans(), loadTags()]); break;
			}
		}
		editModal = null;
		modalTags = [];
	}

	// ── Predicate editing ──

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

	// ── Reload board and preserve compact layout if archived is hidden ──

	async function reloadBoard() {
		await loadBoard();
		if (!$showArchived) {
			compactLayout();
		}
	}

	// ── Remove node from board (right-click context) ──

	async function handleRemoveFromBoard(type: string, id: number) {
		await deleteBoardNode(type, id);
		await reloadBoard();
	}

	// ── Context menu ──
	let contextMenu: { x: number; y: number; type: string; id: number } | null = $state(null);

	function handleCardContextMenu(type: string, id: number, e: MouseEvent) {
		e.preventDefault();
		contextMenu = { x: e.clientX, y: e.clientY, type, id };
	}

	function closeContextMenu() {
		contextMenu = null;
	}

	// ── Pulsing state for graph cards ──
	let pulsingCards = $state<Set<string>>(new Set());

	// ── Lifecycle ──

	let hasFocus = $derived(isFocusActive($focusSelection));

	// Compact layout when hiding archived, restore when showing
	let prevShowArchived = $state(false);
	let savedPositions = $state<Map<string, { x: number; y: number }> | null>(null);
	let boardLoadedInMount = $state(false);
	let initialSelectionApplied = $state(false);

	/**
	 * Hierarchical layout: places root entities at top, then layers of
	 * related entities below, using triples to determine connectivity.
	 * Respects a semantic type ordering within each layer.
	 * Takes explicit sets so it works inside onMount without reactivity.
	 * If previouslyVisible is provided, only repositions NEW nodes and
	 * offsets them to the right of existing visible nodes.
	 */
	function hierarchicalLayout(rootKeys: Set<string>, wantedKeys: Set<string>, previouslyVisible?: Set<string>) {
		const CARD_W = 150;
		const CARD_H = 70;
		const GAP_X = 40;
		const GAP_Y = 80;

		// Type priority within a layer (lower = further left)
		const TYPE_PRIORITY: Record<string, number> = {
			plan: 0, project: 1, log: 2, activity: 3, note: 4,
			collection: 5, source: 6, actor: 7,
		};

		// Get the nodes to layout (filter board nodes by wantedKeys)
		const currentNodes = get(boardNodes).filter(n => wantedKeys.has(`${n.entity_type}:${n.entity_id}`));
		const nodeKeySet = new Set(currentNodes.map(n => `${n.entity_type}:${n.entity_id}`));

		// Build adjacency from triples (only within wantedKeys)
		const adj = new Map<string, Set<string>>();
		for (const t of get(triples)) {
			const sk = `${t.subject_type}:${t.subject_id}`;
			const ok = `${t.object_type}:${t.object_id}`;
			if (!nodeKeySet.has(sk) || !nodeKeySet.has(ok)) continue;
			if (!adj.has(sk)) adj.set(sk, new Set());
			if (!adj.has(ok)) adj.set(ok, new Set());
			adj.get(sk)!.add(ok);
			adj.get(ok)!.add(sk);
		}

		// BFS from roots to assign layers
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
		// Any orphan nodes not reached by BFS go to the last layer + 1
		const maxLayer = Math.max(0, ...layerOf.values());
		for (const n of currentNodes) {
			const key = `${n.entity_type}:${n.entity_id}`;
			if (!layerOf.has(key)) layerOf.set(key, maxLayer + 1);
		}

		// Group nodes by layer, sort within layer by type priority then id
		const layers = new Map<number, typeof currentNodes>();
		for (const n of currentNodes) {
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

		// Compute X offset: if there are already visible nodes, place new
		// cluster to the right with a gap
		let originX = 0;
		if (previouslyVisible && previouslyVisible.size > 0) {
			let maxX = 0;
			for (const n of get(boardNodes)) {
				const key = `${n.entity_type}:${n.entity_id}`;
				if (previouslyVisible.has(key)) {
					maxX = Math.max(maxX, n.x + CARD_W);
				}
			}
			originX = maxX + GAP_X * 3; // generous gap between clusters
		}

		// Compute positions: each layer is a row, centered horizontally
		const newPos = new Map<string, { x: number; y: number }>();
		const sortedLayers = [...layers.keys()].sort((a, b) => a - b);
		let maxRowWidth = 0;
		for (const layer of sortedLayers) {
			const nodes = layers.get(layer)!;
			maxRowWidth = Math.max(maxRowWidth, nodes.length * (CARD_W + GAP_X) - GAP_X);
		}

		for (const layer of sortedLayers) {
			const nodes = layers.get(layer)!;
			const rowWidth = nodes.length * (CARD_W + GAP_X) - GAP_X;
			const offsetX = originX + (maxRowWidth - rowWidth) / 2;
			const y = layer * (CARD_H + GAP_Y);
			for (let i = 0; i < nodes.length; i++) {
				const n = nodes[i];
				newPos.set(`${n.entity_type}:${n.entity_id}`, {
					x: offsetX + i * (CARD_W + GAP_X),
					y,
				});
			}
		}

		boardNodes.update(nodes =>
			nodes.map(n => {
				const pos = newPos.get(`${n.entity_type}:${n.entity_id}`);
				return pos ? { ...n, x: pos.x, y: pos.y } : n;
			})
		);
	}

	function compactLayout() {
		const CARD_W = 150;
		const CARD_H = 70;
		const GAP_X = 120;
		const GAP_Y = 60;
		const TYPE_ORDER = [
			'project', 'activity', 'log', 'note',
			'source', 'actor', 'plan', 'collection'
		];

		const newPos = new Map<string, { x: number; y: number }>();
		let colX = 0;

		for (const type of TYPE_ORDER) {
			const nodesOfType = visibleNodes
				.filter(n => n.entity_type === type)
				.sort((a, b) => a.y - b.y);
			if (nodesOfType.length === 0) continue;

			let rowY = 0;
			for (const n of nodesOfType) {
				newPos.set(`${n.entity_type}:${n.entity_id}`, { x: colX, y: rowY });
				rowY += CARD_H + GAP_Y;
			}
			colX += CARD_W + GAP_X;
		}

		boardNodes.update(nodes =>
			nodes.map(n => {
				const pos = newPos.get(`${n.entity_type}:${n.entity_id}`);
				return pos ? { ...n, x: pos.x, y: pos.y } : n;
			})
		);
	}

	$effect(() => {
		const current = $showArchived;
		if (current !== prevShowArchived) {
			prevShowArchived = current;
			untrack(() => {
				if (!current) {
					// Hiding archived: save original positions, then compact
					savedPositions = new Map();
					for (const n of $boardNodes) {
						savedPositions.set(`${n.entity_type}:${n.entity_id}`, { x: n.x, y: n.y });
					}
					compactLayout();
				} else {
					// Showing archived: restore original positions
					if (savedPositions) {
						boardNodes.update(nodes =>
							nodes.map(n => {
								const key = `${n.entity_type}:${n.entity_id}`;
								const pos = savedPositions!.get(key);
								return pos ? { ...n, x: pos.x, y: pos.y } : n;
							})
						);
						savedPositions = null;
					}
				}
				requestAnimationFrame(() => zoomFit());
			});
		}
	});

	// On initial load: compact layout once board + tags are ready and archived is hidden
	// Skip if hierarchicalLayout was already applied via initial selection
	$effect(() => {
		if (boardLoadedInMount && !initialSelectionApplied && !$showArchived && $boardNodes.length > 0 && Object.keys(nodeEntityTags).length > 0) {
			boardLoadedInMount = false;
			untrack(() => {
				savedPositions = new Map();
				for (const n of $boardNodes) {
					savedPositions.set(`${n.entity_type}:${n.entity_id}`, { x: n.x, y: n.y });
				}
				compactLayout();
				requestAnimationFrame(() => zoomFit());
			});
		}
	});

	onMount(() => {
		loadPredicates();
		populateAll().then(() => {
			Promise.allSettled([loadBoard(), loadTriples()]).then(async () => {
				boardLoadedInMount = true;
				// Apply initial selection passed from Cards (or other tabs)
				const payload = get(graphInitialSelection);
				if (payload && payload.entities.length > 0) {
					// Reload triples (populateAll may have created new FK-based ones)
					await loadTriples();

					const wantedKeys = new Set(payload.entities.map(e => `${e.type}:${e.id}`));

					// Expand with related entities if requested (BFS, 2 levels deep)
					if (payload.showRelated) {
						let frontier = payload.entities.map(e => ({ type: e.type, id: e.id }));
						const visited = new Set(frontier.map(e => `${e.type}:${e.id}`));
						for (let depth = 0; depth < 2 && frontier.length > 0; depth++) {
							const allTriples = await Promise.all(
								frontier.map(e => getTriplesForEntity(e.type, e.id))
							);
							const nextFrontier: { type: string; id: number }[] = [];
							for (const triples of allTriples) {
								for (const t of triples) {
									for (const [etype, eid] of [
										[t.subject_type, t.subject_id],
										[t.object_type, t.object_id]
									] as [string, number][]) {
										const key = `${etype}:${eid}`;
										wantedKeys.add(key);
										if (!visited.has(key)) {
											visited.add(key);
											nextFrontier.push({ type: etype, id: eid });
										}
									}
								}
							}
							frontier = nextFrontier;
						}
					}

					// Additive visibility: unhide wanted keys from the current hidden set.
					// If no filter is active yet (empty hidden set = show all), start
					// by hiding everything, then unhide only the wanted keys.
					const currentHidden = get(hiddenGraphEntities);
					const allBoardKeys = new Set(get(boardNodes).map(n => `${n.entity_type}:${n.entity_id}`));
					let newHidden: Set<string>;
					let previouslyVisible: Set<string> | undefined;
					if (currentHidden.size === 0) {
						// First use: hide everything except wanted
						newHidden = new Set<string>();
						for (const key of allBoardKeys) {
							if (!wantedKeys.has(key)) newHidden.add(key);
						}
					} else {
						// Subsequent use: compute what was already visible
						previouslyVisible = new Set<string>();
						for (const key of allBoardKeys) {
							if (!currentHidden.has(key)) previouslyVisible.add(key);
						}
						// Keep previous visible, also unhide wanted
						newHidden = new Set(currentHidden);
						for (const key of wantedKeys) {
							newHidden.delete(key);
						}
					}
					hiddenGraphEntities.set(newHidden);
					selectedCards = new Set(payload.pulsingKeys);

					// Apply pulsing to originally-selected entities
					if (payload.pulsingKeys.length > 0) {
						pulsingCards = new Set(payload.pulsingKeys);
						setTimeout(() => { pulsingCards = new Set(); }, 2500);
					}

					graphInitialSelection.set(null);
					initialSelectionApplied = true;

					// Apply hierarchical layout: only reposition new nodes,
					// offset to the right of existing visible nodes if additive
					const rootKeys = new Set(payload.entities.map(e => `${e.type}:${e.id}`));
					hierarchicalLayout(rootKeys, wantedKeys, previouslyVisible);
					requestAnimationFrame(() => zoomFit());
				} else if (payload) {
					// Payload with no entities (e.g. pulsing only)
					if (payload.pulsingKeys.length > 0) {
						pulsingCards = new Set(payload.pulsingKeys);
						selectedCards = new Set(payload.pulsingKeys);
						setTimeout(() => { pulsingCards = new Set(); }, 2500);
					}
					graphInitialSelection.set(null);
					requestAnimationFrame(() => zoomFit());
				}
			});
		});

		function handleGlobalClick() {
			if (contextMenu) contextMenu = null;
		}
		function handleKeydown(e: KeyboardEvent) {
			if (e.key === 'Escape' && selectedCards.size > 0 && !editModal) {
				const target = e.target as HTMLElement;
				if (target.closest('.selection-bar') || target.tagName === 'INPUT') return;
				selectedCards = new Set();
			}
		}
		document.addEventListener('click', handleGlobalClick);
		document.addEventListener('keydown', handleKeydown);
		return () => {
			document.removeEventListener('click', handleGlobalClick);
			document.removeEventListener('keydown', handleKeydown);
			// Clean up drag listeners if component unmounts mid-drag
			document.removeEventListener('pointermove', handleDragMove);
			document.removeEventListener('pointerup', handleDragUp);
		};
	});

	// ── Bulk tag operations ──

	const SUPPORTS_ACTIVE = ['project', 'log', 'activity', 'source', 'actor', 'plan'];
	const SUPPORTS_ARCHIVE = ['project', 'log', 'note', 'activity', 'source', 'actor', 'plan'];

	let hasActivatable = $derived(selectedEntities.some(e => SUPPORTS_ACTIVE.includes(e.type)));
	let hasArchivable = $derived(selectedEntities.some(e => SUPPORTS_ARCHIVE.includes(e.type)));

	async function handleBulkAttachTag(tag: Tag) {
		bulkActionInProgress = true;
		await Promise.allSettled(
			selectedEntities.map(({ type, id }) => attachTag(tag.id, type, id))
		);
		bulkTags = [...bulkTags, tag];
		await Promise.all([loadTags(), loadTriples()]);
		triggerEntityTagsRefresh();
		bulkActionInProgress = false;
	}

	async function handleBulkDetachTag(tag: Tag) {
		bulkActionInProgress = true;
		await Promise.allSettled(
			selectedEntities.map(({ type, id }) => detachTag(tag.id, type, id))
		);
		bulkTags = bulkTags.filter(t => t.id !== tag.id);
		await Promise.all([loadTags(), loadTriples()]);
		triggerEntityTagsRefresh();
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

	// ── Bulk action helpers ──

	function activateEntity(type: string, id: number): Promise<any> {
		switch (type) {
			case 'project': return activateProject(id);
			case 'log': return activateLog(id);
			case 'activity': return activateActivity(id);
			case 'source': return activateSource(id);
			case 'actor': return activateActor(id);
			case 'plan': return activatePlan(id);
			default: return Promise.resolve();
		}
	}

	function deactivateEntity(type: string, id: number): Promise<any> {
		switch (type) {
			case 'project': return deactivateProject(id);
			case 'log': return deactivateLog(id);
			case 'activity': return deactivateActivity(id);
			case 'source': return deactivateSource(id);
			case 'actor': return deactivateActor(id);
			case 'plan': return deactivatePlan(id);
			default: return Promise.resolve();
		}
	}

	function archiveEntity(type: string, id: number): Promise<any> {
		switch (type) {
			case 'project': return archiveProject(id);
			case 'log': return archiveLog(id);
			case 'note': return archiveNote(id);
			case 'activity': return archiveActivity(id);
			case 'source': return archiveSource(id);
			case 'actor': return archiveActor(id);
			case 'plan': return archivePlan(id);
			default: return Promise.resolve();
		}
	}

	function unarchiveEntity(type: string, id: number): Promise<any> {
		switch (type) {
			case 'project': return unarchiveProject(id);
			case 'log': return unarchiveLog(id);
			case 'note': return unarchiveNote(id);
			case 'activity': return unarchiveActivity(id);
			case 'source': return unarchiveSource(id);
			case 'actor': return unarchiveActor(id);
			default: return Promise.resolve();
		}
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

	async function reloadAllStores() {
		await Promise.all([
			loadProjects(), loadLogs(), loadNotes(), loadActivities(),
			loadSources(), loadActors(),
			loadPlans(), loadTags()
		]);
		triggerEntityTagsRefresh();
	}

	function handleOpenInCards() {
		// Ensure the relevant entity type panels are visible
		const entityTypes = new Set(selectedEntities.map(e => e.type));
		const currentPanels = get(panels);
		for (const type of entityTypes) {
			const panel = currentPanels.find(p => p.id === type);
			if (panel && !panel.visible) {
				togglePanel(type);
			}
		}
		// Select these entities in the panel selection store
		panelSelection.setMany(
			selectedEntities.map(e => ({ type: e.type as PanelEntityType, id: e.id }))
		);
		// Switch to Cards tab
		activeTab.set('input');
		selectedCards = new Set();
	}

	async function handleBulkRemove() {
		bulkActionInProgress = true;
		await Promise.allSettled(
			selectedEntities.map(({ type, id }) => deleteBoardNode(type, id))
		);
		await reloadBoard();
		selectedCards = new Set();
		bulkActionInProgress = false;
	}

	async function handleBulkActivate() {
		bulkActionInProgress = true;
		await Promise.allSettled(
			selectedEntities.map(({ type, id }) => activateEntity(type, id))
		);
		await reloadAllStores();
		bulkActionInProgress = false;
	}

	async function handleBulkDeactivate() {
		bulkActionInProgress = true;
		await Promise.allSettled(
			selectedEntities.map(({ type, id }) => deactivateEntity(type, id))
		);
		await reloadAllStores();
		bulkActionInProgress = false;
	}

	async function handleBulkArchive() {
		bulkActionInProgress = true;
		await Promise.allSettled(
			selectedEntities.map(({ type, id }) => archiveEntity(type, id))
		);
		await reloadAllStores();
		selectedCards = new Set();
		bulkActionInProgress = false;
	}

	async function handleBulkUnarchive() {
		bulkActionInProgress = true;
		await Promise.allSettled(
			selectedEntities.map(({ type, id }) => unarchiveEntity(type, id))
		);
		await reloadAllStores();
		selectedCards = new Set();
		bulkActionInProgress = false;
	}

	async function handleBulkDelete() {
		bulkActionInProgress = true;
		await Promise.allSettled(
			selectedEntities.map(({ type, id }) => deleteEntity(type, id))
		);
		// Also remove from board
		await Promise.allSettled(
			selectedEntities.map(({ type, id }) => deleteBoardNode(type, id))
		);
		await reloadAllStores();
		await reloadBoard();
		selectedCards = new Set();
		showConfirmDelete = false;
		bulkActionInProgress = false;
	}

	function clearSelection() {
		selectedCards = new Set();
		showBulkTagInput = false;
		bulkTags = [];
	}

	function editModalTitle(): string {
		if (!editModal) return '';
		return `Edit ${editModal.type.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}`;
	}
</script>

<div class="knowledge-graph">
	<GraphToolbar
		{zoom}
		filterOpen={filterPanelOpen}
		editorOpen={graphEditorOpen}
		onAddEntity={handleAddEntity}
		onZoomIn={zoomIn}
		onZoomOut={zoomOut}
		onZoomFit={zoomFit}
		onToggleFilter={toggleFilterPanel}
		onToggleEditor={() => graphEditorOpen = !graphEditorOpen}
		onSwitchToCards={() => activeTab.set('input')}
		onScreenshot={handleScreenshot}
		selectActive={selectMode}
		onToggleSelect={() => (selectMode = !selectMode)}
	/>

	<div class="viewport-wrapper">
	<GraphEditorPanel
		open={graphEditorOpen}
		onCommit={handleEditorCommit}
	/>
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="viewport"
		bind:this={viewportEl}
		onpointerdown={handleCanvasPointerDown}
		onpointermove={handlePointerMove}
		onpointerup={handlePointerUp}
		onwheel={handleWheel}
	>
		<div
			class="canvas"
			bind:this={canvasEl}
			style:transform="translate({panX}px, {panY}px) scale({zoom})"
		>
			<GraphConnections
				triples={visibleTriples}
				nodeMap={augmentedNodeMap}
				{collapsedNodes}
				onConnectionSwap={handleConnectionSwap}
				onConnectionDelete={handleConnectionDelete}
				onPredicateSelect={handlePredicateSelect}
			/>

			{#each containerNodes as node (`${node.entity_type}:${node.entity_id}`)}
				{@const entry = renderContainers.get(`${node.entity_type}:${node.entity_id}`)}
				{#if entry}
					<CollectionContainer
						collectionId={node.entity_id}
						title={getEntityTitle(node.entity_type, node.entity_id)}
						x={node.x}
						y={node.y}
						color={ENTITY_COLORS['collection']}
						collapsed={node.collapsed}
						archived={getEntityData(node.entity_type, node.entity_id)?.is_archived ?? false}
						selected={selectedCards.has(`${node.entity_type}:${node.entity_id}`)}
						pulsing={pulsingCards.has(`${node.entity_type}:${node.entity_id}`)}
						highlighted={
							(dropTarget !== null && dropTarget.type === node.entity_type && dropTarget.id === node.entity_id) ||
							(dropTarget !== null && draggingKey === `${node.entity_type}:${node.entity_id}`)
						}
						members={entry.members}
						statusCycle={getStatusCycle(node.entity_id)}
						onPointerDown={(e) => handleCardPointerDown(node.entity_type, node.entity_id, e)}
						onDblClick={() => handleCardDblClick(node.entity_type, node.entity_id)}
						onMemberDblClick={(type, id) => handleCardDblClick(type, id)}
						onMemberPointerDown={(type, id, e) => handleMemberPointerDown(node.entity_id, type, id, e)}
						onStatusChange={handleStatusChange}
						onToggleCollapse={() => handleToggleCollapse(node.entity_type, node.entity_id)}
						onNestedToggleCollapse={handleNestedToggleCollapse}
						onContextMenu={(e) => handleCardContextMenu(node.entity_type, node.entity_id, e)}
					/>
				{/if}
			{/each}

			{#each standaloneNodes as node (`${node.entity_type}:${node.entity_id}`)}
				{@const nodeData = getEntityData(node.entity_type, node.entity_id)}
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
						archived={nodeData?.is_archived ?? false}
						status={nodeData?.status ?? ''}
						mood={node.entity_type === 'log' ? (nodeData?.mood ?? '') : ''}
						weather={node.entity_type === 'log' ? (nodeData?.weather ?? '') : ''}
						dayTheme={node.entity_type === 'log' ? (nodeData?.day_theme ?? '') : ''}
						zIndex={topZKey === `${node.entity_type}:${node.entity_id}` ? zCounter : 0}
						selected={selectedCards.has(`${node.entity_type}:${node.entity_id}`)}
						pulsing={pulsingCards.has(`${node.entity_type}:${node.entity_id}`)}
						highlighted={
						(dropTarget !== null && dropTarget.type === node.entity_type && dropTarget.id === node.entity_id) ||
						(dropTarget !== null && draggingKey === `${node.entity_type}:${node.entity_id}`)
					}
						onPointerDown={(e) => handleCardPointerDown(node.entity_type, node.entity_id, e)}
						onDblClick={() => handleCardDblClick(node.entity_type, node.entity_id)}
						onToggleCollapse={() => handleToggleCollapse(node.entity_type, node.entity_id)}
					/>
				</div>
			{/each}
		</div>
	</div>

	<!-- Marquee selection rectangle -->
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

	<!-- Selection bar (BulkActionPanel style) -->
	{#if selectionCount >= 2}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="selection-bar" onclick={(e) => e.stopPropagation()}>
		<span class="selection-count">{selectionCount} selected</span>
		<div class="selection-divider"></div>
		<button class="sel-btn sel-btn-remove" onclick={handleBulkRemove} disabled={bulkActionInProgress} title="Remove from workspace (keep in database)">Remove</button>
		<button class="sel-btn sel-btn-delete" onclick={() => (showConfirmDelete = true)} disabled={bulkActionInProgress} title="Permanently delete entities">Delete</button>
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

	<ConfirmDialog
		open={showConfirmDelete}
		message={`Delete ${selectionCount} selected entities? This cannot be undone.`}
		onConfirm={handleBulkDelete}
		onCancel={() => (showConfirmDelete = false)}
	/>

	<!-- Context menu -->
	{#if contextMenu}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<div
			class="context-menu"
			style:left="{contextMenu.x}px"
			style:top="{contextMenu.y}px"
		>
			<button onclick={() => { handleCardDblClick(contextMenu!.type, contextMenu!.id); closeContextMenu(); }}>
				Edit
			</button>
			<button onclick={() => { handleRemoveFromBoard(contextMenu!.type, contextMenu!.id); closeContextMenu(); }}>
				Remove from board
			</button>
		</div>
	{/if}
	</div>

	<!-- Query/Filter panel -->
	<QueryPanel
		open={filterPanelOpen}
		onClose={() => graphFilterPanelOpen.set(false)}
		onResultClick={handleQueryResult}
		onStateChange={handleQueryStateChange}
		resultActionLabel="Add to board"
		showArchivedToggle={false}
		showActiveRelatedToggle={false}
		boardEntityKeys={boardEntityKeySet}
	/>
</div>

<!-- Edit modal -->
<Modal open={editModal !== null} title={editModalTitle()} onClose={closeEditModal}>
	{#if editModal?.type === 'project'}
		<ProjectForm editData={editModal.data} onDone={closeEditModal} />
	{:else if editModal?.type === 'note'}
		<NoteForm editData={editModal.data} onDone={closeEditModal} />
	{:else if editModal?.type === 'log'}
		<LogEditForm editData={editModal.data} onDone={closeEditModal} />
	{:else if editModal?.type === 'activity'}
		<ActivityForm editData={editModal.data} onDone={closeEditModal} />
	{:else if editModal?.type === 'source'}
		<SourceForm editData={editModal.data} onDone={closeEditModal} />
	{:else if editModal?.type === 'actor'}
		<ActorForm editData={editModal.data} onDone={closeEditModal} />
	{:else if editModal?.type === 'plan'}
		<PlanForm editData={editModal.data} onDone={closeEditModal} />
	{/if}

	{#if editModal}
		<div class="modal-tags-section">
			<div class="modal-tags-label">Tags</div>
			{#if modalTags.length > 0}
				<div class="modal-tag-badges">
					{#each modalTags as tag (tag.id)}
						<TagBadge {tag} removable onRemove={() => handleModalDetachTag(tag)} />
					{/each}
				</div>
			{/if}
			<TagInput
				attachedTags={modalTags}
				targetType={editModal.type}
				targetId={editModal.id}
				onAttach={handleModalAttachTag}
				onDetach={handleModalDetachTag}
			/>
		</div>
	{/if}
</Modal>

<style>
	.knowledge-graph {
		display: flex;
		flex-direction: column;
		height: calc(100vh - 100px);
		position: relative;
	}
	.graph-empty-state {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.graph-empty-state p {
		color: #9ca3af;
		font-size: 0.9rem;
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
		position: relative;
		cursor: grab;
		background:
			radial-gradient(circle, #e5e7eb 1px, transparent 1px);
		background-size: 20px 20px;
	}
	.viewport:active {
		cursor: grabbing;
	}
	.canvas {
		position: absolute;
		top: 0;
		left: 0;
		transform-origin: 0 0;
		/* Effectively infinite canvas */
		width: 1px;
		height: 1px;
	}
	.context-menu {
		position: fixed;
		z-index: 100;
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 6px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
		overflow: hidden;
	}
	.context-menu button {
		display: block;
		width: 100%;
		padding: 8px 16px;
		border: none;
		background: none;
		text-align: left;
		cursor: pointer;
		font-size: 0.8rem;
		color: #374151;
	}
	.context-menu button:hover {
		background: #f3f4f6;
	}

	.modal-tags-section {
		margin-top: 16px;
		padding-top: 16px;
		border-top: 1px solid #e5e7eb;
	}
	.modal-tags-label {
		font-size: 0.75rem;
		font-weight: 600;
		color: #6b7280;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		margin-bottom: 8px;
	}
	.modal-tag-badges {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		margin-bottom: 8px;
	}

	/* ── Marquee selection rectangle ── */
	.selection-marquee {
		position: fixed;
		border: 2px dashed #3b82f6;
		background: rgba(59, 130, 246, 0.08);
		z-index: 100;
		pointer-events: none;
	}

	/* ── Selection bar (BulkActionPanel style) ── */
	.selection-bar {
		position: absolute;
		bottom: 16px;
		left: 50%;
		transform: translateX(-50%);
		z-index: 60;
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 10px 16px;
		background: white;
		border: 1px solid #d1d5db;
		border-radius: 12px;
		box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
		flex-wrap: wrap;
	}
	.selection-count {
		font-size: 0.85rem;
		font-weight: 600;
		color: #374151;
		white-space: nowrap;
	}
	.selection-divider {
		width: 1px;
		height: 20px;
		background: #e5e7eb;
	}
	.sel-btn {
		font-size: 0.8rem;
		padding: 5px 12px;
		border-radius: 6px;
		border: 1px solid #d1d5db;
		cursor: pointer;
		background: #f9fafb;
		color: #374151;
		white-space: nowrap;
	}
	.sel-btn:hover:not(:disabled) { background: #f3f4f6; }
	.sel-btn:disabled { opacity: 0.5; cursor: not-allowed; }
	.sel-btn-tags { background: #f9fafb; color: #6b7280; }
	.sel-btn-active { background: #dcfce7; color: #16a34a; border-color: #bbf7d0; }
	.sel-btn-inactive { background: #f3f4f6; color: #6b7280; }
	.sel-btn-archive { background: #fef3c7; color: #92400e; border-color: #fde68a; }
	.sel-btn-delete { background: #fee2e2; color: #ef4444; border-color: #fecaca; }
	.sel-btn-remove { background: #fef3c7; color: #92400e; border-color: #fde68a; }
	.sel-btn-cards { background: #eff6ff; color: #3b82f6; border-color: #bfdbfe; }
	.sel-btn-clear { background: white; color: #9ca3af; border-color: #e5e7eb; }
	.selection-tag-row {
		width: 100%;
		margin-top: 4px;
	}
</style>

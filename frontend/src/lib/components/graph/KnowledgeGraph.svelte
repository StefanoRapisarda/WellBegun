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
	import { readingLists } from '$lib/stores/readingLists';
	import { learningTracks } from '$lib/stores/learningTracks';
	import { loadProjects } from '$lib/stores/projects';
	import { loadLogs } from '$lib/stores/logs';
	import { loadNotes } from '$lib/stores/notes';
	import { loadActivities } from '$lib/stores/activities';
	import { loadSources } from '$lib/stores/sources';
	import { loadActors } from '$lib/stores/actors';
	import { loadReadingLists } from '$lib/stores/readingLists';
	import { loadLearningTracks } from '$lib/stores/learningTracks';
	import {
		upsertBoardNode,
		updateBoardNode,
		deleteBoardNode,
		updateTriple,
		swapTripleDirection,
		deleteTriple,
		populateAll
	} from '$lib/api/knowledge';
	import { createProject, archiveProject, unarchiveProject, deleteProject } from '$lib/api/projects';
	import { createLog, archiveLog, unarchiveLog, deleteLog } from '$lib/api/logs';
	import { createNote, archiveNote, unarchiveNote, deleteNote } from '$lib/api/notes';
	import { createActivity, archiveActivity, unarchiveActivity, deleteActivity } from '$lib/api/activities';
	import { createSource, archiveSource, unarchiveSource, deleteSource } from '$lib/api/sources';
	import { createActor, archiveActor, unarchiveActor, deleteActor } from '$lib/api/actors';
	import { createReadingList, deleteReadingList } from '$lib/api/readingLists';
	import { createLearningTrack, deleteLearningTrack } from '$lib/api/learningTracks';
	import { attachTag, detachTag, getEntityTags, getAllEntityTagsBulk } from '$lib/api/tags';
	import { tags, loadTags, triggerEntityTagsRefresh, entityTagsVersion } from '$lib/stores/tags';
	import { dateFilter, isDateVisible, selectedFilterTags, isTagVisible, isEntitySourceOfFilterTag, showArchived, showActiveRelated, activeEntityTagIds, isActiveRelated } from '$lib/stores/dateFilter';
	import type { Tag } from '$lib/types';
	import GraphCard from './GraphCard.svelte';
	import GraphConnections from './GraphConnections.svelte';
	import GraphToolbar from './GraphToolbar.svelte';
	import DateFilterControl from '$lib/components/shared/DateFilterControl.svelte';
	import TagFilterControl from '$lib/components/shared/TagFilterControl.svelte';
	import Modal from '$lib/components/shared/Modal.svelte';
	import ProjectForm from '$lib/components/forms/ProjectForm.svelte';
	import NoteForm from '$lib/components/forms/NoteForm.svelte';
	import LogEditForm from '$lib/components/forms/LogEditForm.svelte';
	import ActivityForm from '$lib/components/forms/ActivityForm.svelte';
	import SourceForm from '$lib/components/forms/SourceForm.svelte';
	import ActorForm from '$lib/components/forms/ActorForm.svelte';
	import ReadingListForm from '$lib/components/forms/ReadingListForm.svelte';
	import LearningTrackForm from '$lib/components/forms/LearningTrackForm.svelte';
	import TagInput from '$lib/components/shared/TagInput.svelte';
	import TagBadge from '$lib/components/shared/TagBadge.svelte';
	import { structuralPredicates, loadPredicates, getStructuralPredicate } from '$lib/stores/predicates';

	// Color map matching panels store
	const ENTITY_COLORS: Record<string, string> = {
		project: '#5c7a99',
		log: '#8b7355',
		note: '#6b8e6b',
		activity: '#b5838d',
		source: '#c9a227',
		actor: '#8b4557',
		reading_list: '#5f9ea0',
		learning_track: '#7b6b8d'
	};

	// ── Canvas state ──
	let panX = $state(0);
	let panY = $state(0);
	let zoom = $state(1);
	let canvasEl: HTMLDivElement | undefined = $state();
	let viewportEl: HTMLDivElement | undefined = $state();

	// ── Drag state ──
	const DRAG_THRESHOLD = 5;
	let dragStarted = $state(false);
	let draggingCard: { type: string; id: number; startX: number; startY: number; origX: number; origY: number } | null = $state(null);
	let isPanning = $state(false);
	let panStart = $state({ x: 0, y: 0, panX: 0, panY: 0 });

	// ── Connect state (drag-to-connect) ──
	let dropTarget: { type: string; id: number } | null = $state(null);
	let draggingKey: string | null = $state(null);

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

	// Svelte action to set indeterminate property on checkbox
	function setIndeterminate(node: HTMLInputElement, value: boolean) {
		node.indeterminate = value;
		return {
			update(newValue: boolean) {
				node.indeterminate = newValue;
			}
		};
	}

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

	// Group board nodes by entity type for the filter panel
	let entityGroups = $derived.by(() => {
		const TYPE_ORDER = [
			'project', 'activity', 'log', 'note',
			'source', 'actor', 'reading_list', 'learning_track'
		];
		const TYPE_LABELS: Record<string, string> = {
			project: 'Projects',
			activity: 'Activities',
			log: 'Logs',
			note: 'Notes',
			source: 'Sources',
			actor: 'Actors',
			reading_list: 'Reading Lists',
			learning_track: 'Learning Tracks'
		};
		const groups: { type: string; label: string; color: string; items: { key: string; id: number; title: string; visible: boolean }[] }[] = [];
		for (const type of TYPE_ORDER) {
			const nodesOfType = $boardNodes.filter(n => n.entity_type === type);
			if (nodesOfType.length === 0) continue;
			const items = nodesOfType.map(n => {
				const key = `${n.entity_type}:${n.entity_id}`;
				return {
					key,
					id: n.entity_id,
					title: getEntityTitle(n.entity_type, n.entity_id),
					visible: !hiddenEntities.has(key)
				};
			}).sort((a, b) => a.title.localeCompare(b.title));
			groups.push({
				type,
				label: TYPE_LABELS[type] ?? type,
				color: ENTITY_COLORS[type] ?? '#888',
				items
			});
		}
		return groups;
	});

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
		const nodesOfType = $boardNodes.filter(n => n.entity_type === type);
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

	function showAll() {
		hiddenGraphEntities.set(new Set());
	}

	function hideAll() {
		hiddenGraphEntities.set(new Set($boardNodes.map(n => `${n.entity_type}:${n.entity_id}`)));
	}

	// Filtered data for rendering
	let visibleNodes = $derived(
		$boardNodes.filter(n => {
			if (!isEntityVisible(n.entity_type, n.entity_id)) return false;
			if (hiddenByCollapse.has(`${n.entity_type}:${n.entity_id}`)) return false;
			// Skip nodes whose entity no longer exists
			const entityData = getEntityData(n.entity_type, n.entity_id);
			if (!entityData) return false;
			// Archived filter
			if (!$showArchived && entityData.is_archived) return false;
			// Date filter
			if (!isDateVisible(entityData, $dateFilter)) return false;
			// Tag filter
			const key = `${n.entity_type}:${n.entity_id}`;
			const nodeTags = nodeEntityTags[key] || [];
			if (!isTagVisible(nodeTags, $selectedFilterTags) && !isEntitySourceOfFilterTag(n.entity_type, n.entity_id, $selectedFilterTags)) return false;
			// Active-related filter
			if ($showActiveRelated) {
				const isSelfActive = (n.entity_type === 'project' && entityData.is_active) ||
					(n.entity_type === 'activity' && entityData.is_active);
				if (!isActiveRelated(nodeTags, $activeEntityTagIds, isSelfActive)) return false;
			}
			return true;
		})
	);

	let visibleNodeKeys = $derived(new Set(visibleNodes.map(n => `${n.entity_type}:${n.entity_id}`)));

	let visibleTriples = $derived(
		$triples.filter(t =>
			visibleNodeKeys.has(`${t.subject_type}:${t.subject_id}`) &&
			visibleNodeKeys.has(`${t.object_type}:${t.object_id}`)
		)
	);

	// ── Predicate editing state ──
	let editingTripleId: number | null = $state(null);
	let editingPredicate = $state('');

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

	let collapsedNodes = $derived.by(() => {
		// Start with explicitly collapsed nodes
		const explicit = new Set<string>();
		for (const node of $boardNodes) {
			if (node.collapsed) explicit.add(`${node.entity_type}:${node.entity_id}`);
		}
		if (explicit.size === 0) return explicit;

		// Build adjacency: subject → [object keys] from triples
		const children = new Map<string, string[]>();
		for (const t of $triples) {
			const subKey = `${t.subject_type}:${t.subject_id}`;
			const objKey = `${t.object_type}:${t.object_id}`;
			if (!children.has(subKey)) children.set(subKey, []);
			children.get(subKey)!.push(objKey);
		}

		// BFS to find all descendants of explicitly collapsed nodes
		const result = new Set(explicit);
		const queue = [...explicit];
		while (queue.length > 0) {
			const key = queue.shift()!;
			const kids = children.get(key);
			if (!kids) continue;
			for (const child of kids) {
				if (!result.has(child)) {
					result.add(child);
					queue.push(child);
				}
			}
		}
		return result;
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
			case 'reading_list': return $readingLists.find(e => e.id === id)?.title ?? `ReadingList #${id}`;
			case 'learning_track': return $learningTracks.find(e => e.id === id)?.title ?? `LearnTrack #${id}`;
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
			case 'reading_list': return $readingLists.find(e => e.id === id);
			case 'learning_track': return $learningTracks.find(e => e.id === id);
			default: return null;
		}
	}

	// ── Card interactions ──

	function handleCardPointerDown(type: string, id: number, e: PointerEvent) {
		if (e.button !== 0) return;
		e.stopPropagation();
		e.preventDefault();

		const key = `${type}:${id}`;

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

		// Normal click: select this card immediately (cleared if drag starts)
		selectedCards = new Set([key]);

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
		// Attach to document so drag works even if pointer leaves the card/viewport
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
			// Clear selection when drag actually starts
			if (selectedCards.size > 0) {
				selectedCards = new Set();
			}
		}

		const dx = (e.clientX - draggingCard.startX) / zoom;
		const dy = (e.clientY - draggingCard.startY) / zoom;
		const newX = draggingCard.origX + dx;
		const newY = draggingCard.origY + dy;

		// Update local store optimistically
		boardNodes.update(nodes =>
			nodes.map(n =>
				n.entity_type === draggingCard!.type && n.entity_id === draggingCard!.id
					? { ...n, x: newX, y: newY }
					: n
			)
		);

		// Check for drop target: dragged card's center must land inside a visible card
		const CARD_W = 150;
		const CARD_H = 60;
		const centerX = newX + CARD_W / 2;
		const centerY = newY + CARD_H / 2;
		let found: { type: string; id: number } | null = null;
		for (const node of visibleNodes) {
			if (node.entity_type === draggingCard.type && node.entity_id === draggingCard.id) continue;
			if (centerX >= node.x && centerX <= node.x + CARD_W &&
				centerY >= node.y && centerY <= node.y + CARD_H) {
				found = { type: node.entity_type, id: node.entity_id };
				break;
			}
		}
		dropTarget = found;
	}

	async function handleDragUp(_e: PointerEvent) {
		document.removeEventListener('pointermove', handleDragMove);
		document.removeEventListener('pointerup', handleDragUp);

		if (!draggingCard) return;
		const { type, id, origX, origY } = draggingCard;

		if (!dragStarted) {
			// Click (no drag): selection already set in handleCardPointerDown
			draggingCard = null;
			draggingKey = null;
			return;
		}

		// Actual drag happened
		if (dropTarget) {
			// Drag-to-connect: snap card back to original position
			boardNodes.update(nodes =>
				nodes.map(n =>
					n.entity_type === type && n.entity_id === id
						? { ...n, x: origX, y: origY }
						: n
				)
			);

			// Only attach tag — backend sync creates the triple
			try {
				const subjectTag = $tags.find(
					t => t.entity_type === type && t.entity_id === id
				);
				if (subjectTag) {
					await attachTag(subjectTag.id, dropTarget.type, dropTarget.id);
					await loadTags();
				}
			} catch (err) {
				console.error('Failed to attach tag:', err);
			}
			await loadTriples();

			try {
				await upsertBoardNode({ entity_type: type, entity_id: id, x: origX, y: origY });
			} catch {}
			dropTarget = null;
		} else {
			// Normal drag — save new position to DB without reloading
			// (store is already updated optimistically during drag)
			const node = nodeMap.get(`${type}:${id}`);
			if (node) {
				try {
					await upsertBoardNode({ entity_type: type, entity_id: id, x: node.x, y: node.y });
				} catch (err) {
					console.error('Failed to save node position:', err);
				}
			}
		}
		draggingCard = null;
		draggingKey = null;
	}

	function handlePointerMove(e: PointerEvent) {
		if (isPanning) {
			panX = panStart.panX + (e.clientX - panStart.x);
			panY = panStart.panY + (e.clientY - panStart.y);
		}
	}

	function handlePointerUp(_e: PointerEvent) {
		if (isPanning) {
			isPanning = false;
		}
	}

	// ── Canvas pan ──

	function handleCanvasPointerDown(e: PointerEvent) {
		// Only pan on left-click on empty canvas (not on cards)
		if (e.button !== 0) return;
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

	// ── Add entity from toolbar ──

	function findNonOverlappingPosition(baseX: number, baseY: number): { x: number; y: number } {
		const CARD_W = 150;
		const CARD_H = 60;
		const GAP = 20;

		function overlapsAny(x: number, y: number): boolean {
			for (const node of $boardNodes) {
				if (
					x < node.x + CARD_W + GAP &&
					x + CARD_W + GAP > node.x &&
					y < node.y + CARD_H + GAP &&
					y + CARD_H + GAP > node.y
				) {
					return true;
				}
			}
			return false;
		}

		if (!overlapsAny(baseX, baseY)) return { x: baseX, y: baseY };

		// Spiral outward to find a free spot
		for (let ring = 1; ring <= 10; ring++) {
			const offset = ring * (CARD_W + GAP);
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
		return { x: baseX + 200, y: baseY };
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
				case 'log': created = await createLog({ title: `New Log ${now}`, log_type: 'diary' }); await loadLogs(); await loadTags(); break;
				case 'note': created = await createNote({ title: `New Note ${now}` }); await loadNotes(); await loadTags(); break;
				case 'activity': created = await createActivity({ title: `New Activity ${now}` }); await loadActivities(); await loadTags(); break;
				case 'source': created = await createSource({ title: `New Source ${now}` }); await loadSources(); await loadTags(); break;
				case 'actor': created = await createActor({ full_name: `New Actor ${now}` }); await loadActors(); await loadTags(); break;
				case 'reading_list': created = await createReadingList({ title: `New Reading List ${now}` }); await loadReadingLists(); await loadTags(); break;
				case 'learning_track': created = await createLearningTrack({ title: `New Learning Track ${now}` }); await loadLearningTracks(); await loadTags(); break;
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
				case 'reading_list': await Promise.all([loadReadingLists(), loadTags()]); break;
				case 'learning_track': await Promise.all([loadLearningTracks(), loadTags()]); break;
			}
		}
		editModal = null;
		modalTags = [];
	}

	// ── Predicate editing ──

	function handlePredicateClick(tripleId: number, currentPredicate: string) {
		editingTripleId = tripleId;
		editingPredicate = currentPredicate;
	}

	function handlePredicateChange(value: string) {
		editingPredicate = value;
	}

	async function handlePredicateBlur() {
		if (editingTripleId !== null && editingPredicate.trim()) {
			await updateTriple(editingTripleId, editingPredicate.trim());
			await loadTriples();
		}
		editingTripleId = null;
		editingPredicate = '';
	}

	function handlePredicateKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			(e.target as HTMLElement).blur();
		} else if (e.key === 'Escape') {
			editingTripleId = null;
			editingPredicate = '';
		}
	}

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

	// ── Lifecycle ──

	let hasFocus = $derived(isFocusActive($focusSelection));

	// Compact layout when hiding archived, restore when showing
	let prevShowArchived = $state($showArchived);
	let savedPositions = $state<Map<string, { x: number; y: number }> | null>(null);
	let boardLoadedInMount = $state(false);

	function compactLayout() {
		const CARD_W = 150;
		const CARD_H = 70;
		const GAP_X = 120;
		const GAP_Y = 60;
		const TYPE_ORDER = [
			'project', 'activity', 'log', 'note',
			'source', 'actor', 'reading_list', 'learning_track'
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
	$effect(() => {
		if (boardLoadedInMount && !$showArchived && $boardNodes.length > 0 && Object.keys(nodeEntityTags).length > 0) {
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
			Promise.allSettled([loadBoard(), loadTriples()]).then(() => {
				boardLoadedInMount = true;
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

	// ── Bulk action helpers ──

	function archiveEntity(type: string, id: number): Promise<any> {
		switch (type) {
			case 'project': return archiveProject(id);
			case 'log': return archiveLog(id);
			case 'note': return archiveNote(id);
			case 'activity': return archiveActivity(id);
			case 'source': return archiveSource(id);
			case 'actor': return archiveActor(id);
			default: return Promise.resolve(); // reading_list, learning_track have no archive
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

	async function reloadAllStores() {
		await Promise.all([
			loadProjects(), loadLogs(), loadNotes(), loadActivities(),
			loadSources(), loadActors(), loadReadingLists(), loadLearningTracks(),
			loadTags()
		]);
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

	function clearSelection() {
		selectedCards = new Set();
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
		onAddEntity={handleAddEntity}
		onZoomIn={zoomIn}
		onZoomOut={zoomOut}
		onZoomFit={zoomFit}
		onToggleFilter={toggleFilterPanel}
	/>

	<div class="viewport-wrapper">
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
				{nodeMap}
				{collapsedNodes}
				{editingTripleId}
				{editingPredicate}
				onPredicateDblClick={handlePredicateClick}
				onPredicateChange={handlePredicateChange}
				onPredicateBlur={handlePredicateBlur}
				onPredicateKeydown={handlePredicateKeydown}
				onConnectionSwap={handleConnectionSwap}
				onConnectionDelete={handleConnectionDelete}
				onPredicateSelect={handlePredicateSelect}
			/>

			{#each visibleNodes as node (`${node.entity_type}:${node.entity_id}`)}
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
						selected={selectedCards.has(`${node.entity_type}:${node.entity_id}`)}
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

	<!-- Filter panel -->
	{#if filterPanelOpen}
		<div class="filter-panel">
			<div class="filter-header">
				<span class="filter-title">Filters</span>
				<div class="filter-header-actions">
					<button class="filter-action-btn" onclick={showAll}>All</button>
					<button class="filter-action-btn" onclick={hideAll}>None</button>
				</div>
			</div>
			<div class="filter-body">
				<div class="filter-section">
					<label class="archived-toggle">
						<input type="checkbox" bind:checked={$showArchived} />
						Show archived
					</label>
					<label class="archived-toggle" style="margin-top: 6px;">
						<input type="checkbox" bind:checked={$showActiveRelated} />
						Active related
					</label>
				</div>
				<div class="filter-section">
					<div class="filter-section-label">Date</div>
					<div class="filter-section-content">
						<DateFilterControl />
					</div>
				</div>
				<div class="filter-section">
					<div class="filter-section-label">Tags</div>
					<div class="filter-section-content">
						<TagFilterControl />
					</div>
				</div>
				<div class="filter-section">
					<div class="filter-section-label">Entities</div>
				</div>
				{#each entityGroups as group}
					<div class="filter-group">
						<!-- svelte-ignore a11y_click_events_have_key_events -->
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<div class="filter-group-header" onclick={() => toggleType(group.type)}>
							<span class="filter-type-dot" style:background={group.color}></span>
							<span class="filter-group-label">{group.label}</span>
							<span class="filter-group-count">
								{group.items.filter(i => i.visible).length}/{group.items.length}
							</span>
							<input
								type="checkbox"
								checked={group.items.every(i => i.visible)}
								use:setIndeterminate={group.items.some(i => i.visible) && !group.items.every(i => i.visible)}
								onclick={(e) => e.stopPropagation()}
								onchange={() => toggleType(group.type)}
							/>
						</div>
						<div class="filter-group-items">
							{#each group.items as item (item.key)}
								<label class="filter-item">
									<input
										type="checkbox"
										checked={item.visible}
										onchange={() => toggleEntity(item.key)}
									/>
									<span class="filter-item-title">{item.title}</span>
								</label>
							{/each}
						</div>
					</div>
				{/each}
				{#if entityGroups.length === 0}
					<div class="filter-empty">No entities on the board</div>
				{/if}
			</div>
		</div>
	{/if}

	<!-- Selection bar -->
	{#if selectionCount >= 2}
	<div class="selection-bar">
		<span class="selection-count">{selectionCount} selected</span>
		<div class="selection-actions">
			<button class="sel-action-btn sel-action-remove" onclick={handleBulkRemove} title="Remove from board">Remove</button>
			<button class="sel-action-btn sel-action-archive" onclick={handleBulkArchive} title="Archive selected">Archive</button>
			<button class="sel-action-btn sel-action-active" onclick={handleBulkUnarchive} title="Set active">Active</button>
		</div>
		<div class="selection-tag-input">
			<span class="selection-tag-label">Tag all:</span>
			<TagInput
				attachedTags={selectionCommonTags}
				targetType="bulk"
				targetId={0}
				onAttach={handleBulkAttachTag}
				onDetach={handleBulkDetachTag}
			/>
		</div>
		{#if bulkActionInProgress}
			<span class="selection-spinner">Applying...</span>
		{/if}
		<button class="selection-clear-btn" onclick={clearSelection}>Clear</button>
	</div>
	{/if}

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
	{:else if editModal?.type === 'reading_list'}
		<ReadingListForm editData={editModal.data} onDone={closeEditModal} />
	{:else if editModal?.type === 'learning_track'}
		<LearningTrackForm editData={editModal.data} onDone={closeEditModal} />
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

	/* ── Filter panel ── */
	.filter-panel {
		position: absolute;
		top: 0;
		right: 0;
		width: 260px;
		height: 100%;
		background: white;
		border-left: 1px solid #e5e7eb;
		box-shadow: -2px 0 12px rgba(0, 0, 0, 0.06);
		z-index: 50;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}
	.filter-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 12px 14px;
		border-bottom: 1px solid #e5e7eb;
		flex-shrink: 0;
	}
	.filter-title {
		font-size: 0.8rem;
		font-weight: 600;
		color: #374151;
	}
	.filter-header-actions {
		display: flex;
		gap: 4px;
	}
	.filter-action-btn {
		padding: 2px 8px;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		background: white;
		cursor: pointer;
		font-size: 0.68rem;
		color: #6b7280;
	}
	.filter-action-btn:hover {
		background: #f3f4f6;
	}
	.filter-body {
		flex: 1;
		overflow-y: auto;
		padding: 8px 0;
	}
	.filter-group {
		margin-bottom: 4px;
	}
	.filter-group-header {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 6px 14px;
		cursor: pointer;
		user-select: none;
	}
	.filter-group-header:hover {
		background: #f9fafb;
	}
	.filter-type-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.filter-group-label {
		font-size: 0.75rem;
		font-weight: 600;
		color: #374151;
		flex: 1;
	}
	.filter-group-count {
		font-size: 0.65rem;
		color: #9ca3af;
	}
	.filter-group-header input[type='checkbox'] {
		width: 14px;
		height: 14px;
		accent-color: #374151;
		cursor: pointer;
		flex-shrink: 0;
	}
	.filter-group-items {
		padding-left: 28px;
	}
	.filter-item {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 3px 14px 3px 0;
		cursor: pointer;
		font-size: 0.72rem;
		color: #4b5563;
	}
	.filter-item:hover {
		color: #1f2937;
	}
	.filter-item input[type='checkbox'] {
		width: 13px;
		height: 13px;
		accent-color: #6b7280;
		cursor: pointer;
		flex-shrink: 0;
	}
	.filter-item-title {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.filter-empty {
		text-align: center;
		color: #9ca3af;
		font-size: 0.75rem;
		padding: 24px 14px;
	}
	.filter-section {
		padding: 8px 14px;
		border-bottom: 1px solid #f3f4f6;
	}
	.filter-section-label {
		font-size: 0.7rem;
		font-weight: 600;
		color: #9ca3af;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		margin-bottom: 6px;
	}
	.filter-section-content {
		padding: 2px 0;
	}
	.archived-toggle {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 0.75rem;
		color: #4b5563;
		cursor: pointer;
	}
	.archived-toggle input[type='checkbox'] {
		width: 13px;
		height: 13px;
		accent-color: #6b7280;
		cursor: pointer;
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

	/* ── Selection bar ── */
	.selection-bar {
		position: absolute;
		bottom: 16px;
		left: 50%;
		transform: translateX(-50%);
		z-index: 60;
		display: flex;
		align-items: center;
		gap: 12px;
		background: white;
		border: 1px solid #d1d5db;
		border-radius: 999px;
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
		padding: 8px 20px;
		white-space: nowrap;
	}
	.selection-count {
		font-size: 0.78rem;
		font-weight: 600;
		color: #3b82f6;
	}
	.selection-tag-input {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.selection-tag-label {
		font-size: 0.72rem;
		color: #6b7280;
		font-weight: 500;
	}
	.selection-spinner {
		font-size: 0.72rem;
		color: #9ca3af;
		font-style: italic;
	}
	.selection-clear-btn {
		padding: 4px 12px;
		border: 1px solid #d1d5db;
		border-radius: 999px;
		background: white;
		cursor: pointer;
		font-size: 0.72rem;
		color: #6b7280;
		font-weight: 500;
	}
	.selection-clear-btn:hover {
		background: #f3f4f6;
		color: #374151;
	}
	.selection-actions {
		display: flex;
		gap: 4px;
	}
	.sel-action-btn {
		padding: 4px 10px;
		border: 1px solid #d1d5db;
		border-radius: 999px;
		background: white;
		cursor: pointer;
		font-size: 0.72rem;
		font-weight: 500;
		color: #6b7280;
	}
	.sel-action-btn:hover {
		background: #f3f4f6;
		color: #374151;
	}
	.sel-action-remove {
		border-color: #fca5a5;
		color: #dc2626;
	}
	.sel-action-remove:hover {
		background: #fef2f2;
		color: #b91c1c;
	}
	.sel-action-archive {
		border-color: #fcd34d;
		color: #b45309;
	}
	.sel-action-archive:hover {
		background: #fffbeb;
		color: #92400e;
	}
	.sel-action-active {
		border-color: #86efac;
		color: #16a34a;
	}
	.sel-action-active:hover {
		background: #f0fdf4;
		color: #15803d;
	}
</style>

<script lang="ts">
	import type { KnowledgeTriple, BoardNode } from '$lib/types';
	import { ENTITY_CONFIG, type ParsedEntity, type StagedConnection } from '$lib/notepad/types';
	import BoardCard from '$lib/components/reader/BoardCard.svelte';
	import CollectionContainer from '$lib/components/graph/CollectionContainer.svelte';
	import { containerWidth as ccWidth, containerHeight as ccHeight } from '$lib/components/graph/collectionLayout';
	import GraphConnections from '$lib/components/graph/GraphConnections.svelte';

	const SLOT_W = 180;
	const SLOT_H = 90;
	const CARD_PAD = 12;
	const SNAP_START_X = 30;
	const SNAP_START_Y = 30;

	let {
		entities,
		positions,
		sizes,
		connections,
		onCardMove,
		onCardClick,
		onCardConnect,
		onCardDelete,
		onCardResize,
		onConnectionSwap,
		onConnectionDelete,
		onPredicateSelect
	}: {
		entities: ParsedEntity[];
		positions: Record<number, { x: number; y: number }>;
		sizes: Record<number, { colSpan: number; rowSpan: number }>;
		connections: StagedConnection[];
		onCardMove: (index: number, x: number, y: number) => void;
		onCardClick?: (index: number) => void;
		onCardConnect: (sourceIndex: number, targetIndex: number) => void;
		onCardDelete?: (index: number) => void;
		onCardResize?: (index: number, colSpan: number, rowSpan: number) => void;
		onConnectionSwap: (connIndex: number) => void;
		onConnectionDelete: (connIndex: number) => void;
		onPredicateSelect: (connIndex: number, predicate: string) => void;
	} = $props();

	// Compute card pixel dimensions from sizes
	function cardPixelWidth(index: number): number {
		const s = sizes[index];
		const colSpan = s?.colSpan ?? 1;
		return colSpan * SLOT_W - CARD_PAD;
	}

	function cardPixelHeight(index: number): number {
		const s = sizes[index];
		const rowSpan = s?.rowSpan ?? 1;
		return rowSpan * SLOT_H - CARD_PAD;
	}

	// Build SessionCard-compatible objects for BoardCard
	let cards = $derived(entities.map((entity, i) => {
		const config = ENTITY_CONFIG[entity.type];
		const pos = positions[i] ?? { x: 20, y: 20 };
		return {
			id: String(i),
			entityType: entity.type,
			entityId: i,
			title: entity.fields[config.primaryField] ?? config.defaultTitle,
			x: pos.x,
			y: pos.y
		};
	}));

	// ── Collection containers ──
	// Map collection entity index → array of child entity indices
	let collectionContainers = $derived.by(() => {
		const map = new Map<number, number[]>();
		for (let i = 0; i < entities.length; i++) {
			if (entities[i].type === 'collection') {
				map.set(i, []);
			}
		}
		for (let i = 0; i < entities.length; i++) {
			const e = entities[i];
			if (e.parentIndex != null && map.has(e.parentIndex)) {
				map.get(e.parentIndex)!.push(i);
			}
		}
		return map;
	});

	// Set of indices that are rendered inside a collection container
	let childOfCollection = $derived.by(() => {
		const set = new Set<number>();
		for (const children of collectionContainers.values()) {
			for (const idx of children) {
				set.add(idx);
			}
		}
		return set;
	});

	// Indices that should render as standalone cards (not containers and not children inside containers)
	let standaloneIndices = $derived(
		entities.map((_, i) => i).filter(i =>
			!collectionContainers.has(i) && !childOfCollection.has(i)
		)
	);

	// Collapse state for collection containers
	let collapsedCollections = $state<Set<number>>(new Set());

	// Build KnowledgeTriple-compatible objects for GraphConnections (use negative IDs for staged)
	// Skip connections between a collection container and its children (containment is visual)
	let triples = $derived(connections
		.filter(conn => {
			const srcChildren = collectionContainers.get(conn.sourceIndex);
			if (srcChildren?.includes(conn.targetIndex)) return false;
			const tgtChildren = collectionContainers.get(conn.targetIndex);
			if (tgtChildren?.includes(conn.sourceIndex)) return false;
			return true;
		})
		.map((conn, i) => ({
			id: -(i + 1),
			subject_type: entities[conn.sourceIndex]?.type ?? 'note',
			subject_id: conn.sourceIndex,
			predicate: conn.predicate,
			object_type: entities[conn.targetIndex]?.type ?? 'note',
			object_id: conn.targetIndex,
			created_at: '',
			updated_at: ''
		})) as KnowledgeTriple[]);

	// Build nodeMap for GraphConnections with per-node w/h
	let nodeMap = $derived.by(() => {
		const map = new Map<string, BoardNode>();
		for (const [i, card] of cards.entries()) {
			const key = `${card.entityType}:${card.entityId}`;
			// Use container dimensions for collection entities
			const isContainer = collectionContainers.has(i);
			const children = collectionContainers.get(i);
			const memberCount = children?.length ?? 0;
			const collapsed = collapsedCollections.has(i);
			map.set(key, {
				id: 0,
				entity_type: card.entityType,
				entity_id: card.entityId,
				x: card.x,
				y: card.y,
				w: isContainer ? ccWidth() : cardPixelWidth(i),
				h: isContainer ? ccHeight(memberCount, collapsed) : cardPixelHeight(i),
				collapsed: false,
				created_at: '',
				updated_at: ''
			});
		}
		return map;
	});

	const emptyCollapsed = new Set<string>();

	// Map negative triple IDs back to connection index
	function tripleIdToConnIndex(tripleId: number): number {
		return -(tripleId + 1);
	}

	// ── Snap helper ──
	function snapToGrid(x: number, y: number): { x: number; y: number } {
		const snappedX = Math.max(0, Math.round((x - SNAP_START_X) / SLOT_W) * SLOT_W + SNAP_START_X);
		const snappedY = Math.max(0, Math.round((y - SNAP_START_Y) / SLOT_H) * SLOT_H + SNAP_START_Y);
		return { x: snappedX, y: snappedY };
	}

	// ── Pointer-based card dragging ──
	let dragging: { index: number; startX: number; startY: number; origX: number; origY: number } | null = $state(null);
	let dragStarted = $state(false);
	let dropTarget: number | null = $state(null);
	let draggingIndex: number | null = $state(null);
	const DRAG_THRESHOLD = 4;

	function handleCardPointerDown(index: number, e: PointerEvent) {
		if (e.button !== 0) return;
		e.preventDefault();
		const pos = positions[index] ?? { x: 20, y: 20 };
		dragging = {
			index,
			startX: e.clientX,
			startY: e.clientY,
			origX: pos.x,
			origY: pos.y
		};
		draggingIndex = index;
		dragStarted = false;
		document.addEventListener('pointermove', handlePointerMove);
		document.addEventListener('pointerup', handlePointerUp);
	}

	function handlePointerMove(e: PointerEvent) {
		if (!dragging) return;
		const dx = e.clientX - dragging.startX;
		const dy = e.clientY - dragging.startY;
		if (!dragStarted) {
			if (Math.hypot(dx, dy) < DRAG_THRESHOLD) return;
			dragStarted = true;
		}
		const newX = dragging.origX + dx;
		const newY = dragging.origY + dy;
		onCardMove(dragging.index, newX, newY);

		// Overlap detection using per-card dimensions
		const isContainerDrag = collectionContainers.has(dragging.index);
		const dragW = isContainerDrag ? ccWidth() : cardPixelWidth(dragging.index);
		const dragH = isContainerDrag
			? ccHeight(collectionContainers.get(dragging.index)?.length ?? 0, collapsedCollections.has(dragging.index))
			: cardPixelHeight(dragging.index);
		const centerX = newX + dragW / 2;
		const centerY = newY + dragH / 2;
		let found: number | null = null;
		for (let i = 0; i < cards.length; i++) {
			if (i === dragging.index) continue;
			if (childOfCollection.has(i)) continue; // skip children inside containers
			const c = cards[i];
			const isContainer = collectionContainers.has(i);
			const cW = isContainer ? ccWidth() : cardPixelWidth(i);
			const cH = isContainer
				? ccHeight(collectionContainers.get(i)?.length ?? 0, collapsedCollections.has(i))
				: cardPixelHeight(i);
			if (centerX >= c.x && centerX <= c.x + cW &&
				centerY >= c.y && centerY <= c.y + cH) {
				found = i;
				break;
			}
		}
		dropTarget = found;
	}

	function handlePointerUp() {
		document.removeEventListener('pointermove', handlePointerMove);
		document.removeEventListener('pointerup', handlePointerUp);

		if (dragging && dragStarted && dropTarget !== null && draggingIndex !== null) {
			// Snap back and create connection
			onCardMove(dragging.index, dragging.origX, dragging.origY);
			onCardConnect(draggingIndex, dropTarget);
		} else if (dragging && dragStarted) {
			// Snap to grid on regular drag end
			const pos = positions[dragging.index];
			if (pos) {
				const snapped = snapToGrid(pos.x, pos.y);
				onCardMove(dragging.index, snapped.x, snapped.y);
			}
		}

		dragging = null;
		dragStarted = false;
		dropTarget = null;
		draggingIndex = null;
	}

	function getCardColor(entityType: string): string {
		return ENTITY_CONFIG[entityType as keyof typeof ENTITY_CONFIG]?.color ?? '#6b7280';
	}

	function isHighlighted(index: number): boolean {
		if (dropTarget === null) return false;
		return index === dropTarget || index === draggingIndex;
	}
</script>

<div class="preview-pane">
	{#if entities.length === 0}
		<div class="empty-state">
			<p class="empty-hint">Use <code>@entity_type</code> to define entities</p>
			<p class="empty-types">@note, @project, @log, @activity, @source, @actor, @plan, @collection</p>
			<p class="empty-hint">Drag a card onto another to create a connection</p>
		</div>
	{:else}
		<div class="board">
			{#if triples.length > 0}
				<GraphConnections
					{triples}
					{nodeMap}
					cardWidth={SLOT_W - CARD_PAD}
					cardHeight={SLOT_H - CARD_PAD}
					collapsedNodes={emptyCollapsed}
					onConnectionSwap={(tripleId) => onConnectionSwap(tripleIdToConnIndex(tripleId))}
					onConnectionDelete={(tripleId) => onConnectionDelete(tripleIdToConnIndex(tripleId))}
					onPredicateSelect={(tripleId, pred) => onPredicateSelect(tripleIdToConnIndex(tripleId), pred)}
				/>
			{/if}
			{#each [...collectionContainers] as [collIdx, childIndices] (collIdx)}
				{@const card = cards[collIdx]}
				{@const config = ENTITY_CONFIG[entities[collIdx].type]}
				{@const members = childIndices.map(ci => {
					const child = entities[ci];
					const childConfig = ENTITY_CONFIG[child.type];
					return {
						entityType: child.type,
						entityId: ci,
						title: child.fields[childConfig.primaryField] ?? childConfig.defaultTitle,
						status: child.fields.status
					};
				})}
				<CollectionContainer
					collectionId={collIdx}
					title={card.title}
					x={card.x}
					y={card.y}
					color={getCardColor('collection')}
					collapsed={collapsedCollections.has(collIdx)}
					highlighted={isHighlighted(collIdx)}
					members={members}
					onPointerDown={(e) => handleCardPointerDown(collIdx, e)}
					onDblClick={() => onCardClick?.(collIdx)}
					onMemberDblClick={(_type, id) => onCardClick?.(id)}
					onToggleCollapse={() => {
						const next = new Set(collapsedCollections);
						if (next.has(collIdx)) next.delete(collIdx); else next.add(collIdx);
						collapsedCollections = next;
					}}
				/>
			{/each}
			{#each standaloneIndices as i (i)}
				<BoardCard
					card={cards[i]}
					color={getCardColor(cards[i].entityType)}
					highlighted={isHighlighted(i)}
					width={cardPixelWidth(i)}
					height={cardPixelHeight(i)}
					onPointerDown={(e) => handleCardPointerDown(i, e)}
					onDblClick={() => onCardClick?.(i)}
					onDelete={() => onCardDelete?.(i)}
					onResizeEnd={onCardResize ? (colSpan, rowSpan) => onCardResize(i, colSpan, rowSpan) : undefined}
				/>
			{/each}
		</div>
	{/if}
</div>

<style>
	.preview-pane {
		flex: 1;
		min-width: 0;
		overflow: auto;
		background: #f3f4f6;
		border-left: 1px solid #e5e7eb;
	}
	.board {
		position: relative;
		min-width: 100%;
		min-height: 100%;
		background:
			radial-gradient(circle, #e0e0e0 1px, transparent 1px);
		background-size: 20px 20px;
	}
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100%;
		color: #9ca3af;
		text-align: center;
		gap: 6px;
	}
	.empty-hint {
		font-size: 0.82rem;
		margin: 0;
	}
	.empty-hint code {
		background: #e5e7eb;
		padding: 1px 5px;
		border-radius: 3px;
		font-size: 0.78rem;
	}
	.empty-types {
		font-size: 0.7rem;
		color: #b0b8c4;
		margin: 0;
	}
</style>

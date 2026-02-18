<script lang="ts">
	import type { KnowledgeTriple, BoardNode } from '$lib/types';
	import { ENTITY_CONFIG, type ParsedEntity, type StagedConnection } from '$lib/notepad/types';
	import BoardCard from '$lib/components/reader/BoardCard.svelte';
	import GraphConnections from '$lib/components/graph/GraphConnections.svelte';

	const CARD_W = 150;
	const CARD_H = 60;

	let {
		entities,
		positions,
		connections,
		onCardMove,
		onCardClick,
		onCardConnect,
		onCardDelete,
		onConnectionSwap,
		onConnectionDelete,
		onPredicateSelect
	}: {
		entities: ParsedEntity[];
		positions: Record<number, { x: number; y: number }>;
		connections: StagedConnection[];
		onCardMove: (index: number, x: number, y: number) => void;
		onCardClick?: (index: number) => void;
		onCardConnect: (sourceIndex: number, targetIndex: number) => void;
		onCardDelete?: (index: number) => void;
		onConnectionSwap: (connIndex: number) => void;
		onConnectionDelete: (connIndex: number) => void;
		onPredicateSelect: (connIndex: number, predicate: string) => void;
	} = $props();

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

	// Build KnowledgeTriple-compatible objects for GraphConnections (use negative IDs for staged)
	let triples = $derived(connections.map((conn, i) => ({
		id: -(i + 1),
		subject_type: entities[conn.sourceIndex]?.type ?? 'note',
		subject_id: conn.sourceIndex,
		predicate: conn.predicate,
		object_type: entities[conn.targetIndex]?.type ?? 'note',
		object_id: conn.targetIndex,
		created_at: '',
		updated_at: ''
	})) as KnowledgeTriple[]);

	// Build nodeMap for GraphConnections
	let nodeMap = $derived.by(() => {
		const map = new Map<string, BoardNode>();
		for (const card of cards) {
			const key = `${card.entityType}:${card.entityId}`;
			map.set(key, {
				id: 0,
				entity_type: card.entityType,
				entity_id: card.entityId,
				x: card.x,
				y: card.y,
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

	// ── Predicate editing state ──
	let editingTripleId = $state<number | null>(null);
	let editingPredicate = $state('');

	function handlePredicateDblClick(tripleId: number, currentPredicate: string) {
		editingTripleId = tripleId;
		editingPredicate = currentPredicate;
	}

	function handlePredicateChange(value: string) {
		editingPredicate = value;
	}

	function handlePredicateBlur() {
		if (editingTripleId !== null && editingPredicate.trim()) {
			onPredicateSelect(tripleIdToConnIndex(editingTripleId), editingPredicate.trim());
		}
		editingTripleId = null;
		editingPredicate = '';
	}

	function handlePredicateKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			(e.target as HTMLInputElement)?.blur();
		} else if (e.key === 'Escape') {
			editingTripleId = null;
			editingPredicate = '';
		}
	}

	// ── Pointer-based card dragging (same as CardBoard) ──
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

		// Overlap detection
		const centerX = newX + CARD_W / 2;
		const centerY = newY + CARD_H / 2;
		let found: number | null = null;
		for (let i = 0; i < cards.length; i++) {
			if (i === dragging.index) continue;
			const c = cards[i];
			if (centerX >= c.x && centerX <= c.x + CARD_W &&
				centerY >= c.y && centerY <= c.y + CARD_H) {
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
			<p class="empty-types">@note, @project, @log, @activity, @source, @actor, @reading_list, @plan</p>
			<p class="empty-hint">Drag a card onto another to create a connection</p>
		</div>
	{:else}
		<div class="board">
			{#if triples.length > 0}
				<GraphConnections
					{triples}
					{nodeMap}
					cardWidth={CARD_W}
					cardHeight={CARD_H}
					collapsedNodes={emptyCollapsed}
					{editingTripleId}
					{editingPredicate}
					onPredicateDblClick={handlePredicateDblClick}
					onPredicateChange={handlePredicateChange}
					onPredicateBlur={handlePredicateBlur}
					onPredicateKeydown={handlePredicateKeydown}
					onConnectionSwap={(tripleId) => onConnectionSwap(tripleIdToConnIndex(tripleId))}
					onConnectionDelete={(tripleId) => onConnectionDelete(tripleIdToConnIndex(tripleId))}
					onPredicateSelect={(tripleId, pred) => onPredicateSelect(tripleIdToConnIndex(tripleId), pred)}
				/>
			{/if}
			{#each cards as card, i (i)}
				<BoardCard
					{card}
					color={getCardColor(card.entityType)}
					highlighted={isHighlighted(i)}
					onPointerDown={(e) => handleCardPointerDown(i, e)}
					onDblClick={() => onCardClick?.(i)}
					onDelete={() => onCardDelete?.(i)}
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

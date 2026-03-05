<script lang="ts">
	import type { SessionCard } from './types';
	import type { KnowledgeTriple, BoardNode } from '$lib/types';
	import BoardCard from './BoardCard.svelte';
	import GraphConnections from '$lib/components/graph/GraphConnections.svelte';

	const ENTITY_COLORS: Record<string, string> = {
		project: '#5c7a99',
		log: '#8b7355',
		note: '#6b8e6b',
		activity: '#b5838d',
		source: '#c9a227',
		actor: '#8b4557',
		plan: '#6b8ba3'
	};

	const CARD_W = 150;
	const CARD_H = 60;

	let {
		cards,
		triples = [],
		onTextDrop,
		onCardMove,
		onCardDblClick,
		onCardDelete,
		onCardConnect,
		onConnectionSwap,
		onConnectionDelete,
		onPredicateSelect
	}: {
		cards: SessionCard[];
		triples?: KnowledgeTriple[];
		onTextDrop: (text: string, x: number, y: number) => void;
		onCardMove: (cardId: string, x: number, y: number) => void;
		onCardDblClick: (card: SessionCard) => void;
		onCardDelete: (card: SessionCard) => void;
		onCardConnect?: (sourceCard: SessionCard, targetCard: SessionCard) => void;
		onConnectionSwap?: (tripleId: number) => void;
		onConnectionDelete?: (tripleId: number) => void;
		onPredicateSelect?: (tripleId: number, predicate: string) => void;
	} = $props();

	let boardEl: HTMLDivElement | undefined = $state();
	let isDragOver = $state(false);

	// ── Overlap / drop-target state ──
	let dropTarget: SessionCard | null = $state(null);
	let draggingCardRef: SessionCard | null = $state(null);

	// ── Predicate editing state ──
	let editingTripleId = $state<number | null>(null);
	let editingPredicate = $state('');

	// ── Build nodeMap for GraphConnections ──
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

	// ── Filter triples to only those with both ends on the board ──
	let boardTriples = $derived.by(() => {
		if (!triples || triples.length === 0) return [];
		return triples.filter(t => {
			const sKey = `${t.subject_type}:${t.subject_id}`;
			const oKey = `${t.object_type}:${t.object_id}`;
			return nodeMap.has(sKey) && nodeMap.has(oKey);
		});
	});

	const emptyCollapsed = new Set<string>();

	// ── Pointer-based card dragging ──
	let dragging: { cardId: string; startX: number; startY: number; origX: number; origY: number } | null = $state(null);
	let dragStarted = $state(false);
	const DRAG_THRESHOLD = 4;

	function handleCardPointerDown(card: SessionCard, e: PointerEvent) {
		if (e.button !== 0) return;
		e.preventDefault();
		dragging = {
			cardId: card.id,
			startX: e.clientX,
			startY: e.clientY,
			origX: card.x,
			origY: card.y
		};
		draggingCardRef = card;
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
		onCardMove(dragging.cardId, newX, newY);

		// ── Overlap detection: check if dragged card center falls inside another card ──
		const centerX = newX + CARD_W / 2;
		const centerY = newY + CARD_H / 2;
		let found: SessionCard | null = null;
		for (const card of cards) {
			if (card.id === dragging.cardId) continue;
			if (centerX >= card.x && centerX <= card.x + CARD_W &&
				centerY >= card.y && centerY <= card.y + CARD_H) {
				found = card;
				break;
			}
		}
		dropTarget = found;
	}

	function handlePointerUp() {
		document.removeEventListener('pointermove', handlePointerMove);
		document.removeEventListener('pointerup', handlePointerUp);

		if (dragging && dragStarted && dropTarget && draggingCardRef) {
			// Snap dragged card back to original position
			onCardMove(dragging.cardId, dragging.origX, dragging.origY);
			// Create connection
			onCardConnect?.(draggingCardRef, dropTarget);
		}

		dragging = null;
		dragStarted = false;
		dropTarget = null;
		draggingCardRef = null;
	}

	// ── Predicate editing handlers ──
	function handlePredicateDblClick(tripleId: number, currentPredicate: string) {
		editingTripleId = tripleId;
		editingPredicate = currentPredicate;
	}

	function handlePredicateChange(value: string) {
		editingPredicate = value;
	}

	function handlePredicateBlur() {
		if (editingTripleId !== null && editingPredicate.trim()) {
			onPredicateSelect?.(editingTripleId, editingPredicate.trim());
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

	function handleConnectionSwap(tripleId: number) {
		onConnectionSwap?.(tripleId);
	}

	function handleConnectionDelete(tripleId: number) {
		onConnectionDelete?.(tripleId);
	}

	function handlePredicateSelect(tripleId: number, predicate: string) {
		onPredicateSelect?.(tripleId, predicate);
	}

	// ── Text drop from PDF ──
	function handleDragOver(e: DragEvent) {
		e.preventDefault();
		if (e.dataTransfer) {
			e.dataTransfer.dropEffect = 'copy';
		}
		isDragOver = true;
	}

	function handleDragLeave(e: DragEvent) {
		const relatedTarget = e.relatedTarget as HTMLElement | null;
		const currentTarget = e.currentTarget as HTMLElement;
		if (!relatedTarget || !currentTarget.contains(relatedTarget)) {
			isDragOver = false;
		}
	}

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		isDragOver = false;

		const text = e.dataTransfer?.getData('text/plain')?.trim();
		if (text && boardEl) {
			const rect = boardEl.getBoundingClientRect();
			const x = e.clientX - rect.left;
			const y = e.clientY - rect.top;
			onTextDrop(text, x, y);
		}
	}

	function getCardColor(entityType: string): string {
		return ENTITY_COLORS[entityType] ?? '#6b7280';
	}

	function isHighlighted(card: SessionCard): boolean {
		if (!dropTarget) return false;
		// Highlight the drop target card
		if (card.id === dropTarget.id) return true;
		// Highlight the dragged card itself during overlap
		if (draggingCardRef && card.id === draggingCardRef.id) return true;
		return false;
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	bind:this={boardEl}
	class="card-board"
	class:drag-over={isDragOver}
	ondragover={handleDragOver}
	ondragleave={handleDragLeave}
	ondrop={handleDrop}
>
	{#if isDragOver}
		<div class="drop-overlay">
			<div class="drop-label">Drop to create note</div>
		</div>
	{:else if cards.length === 0}
		<div class="empty-board">
			<p>Select text in a document and drag it here to create notes</p>
			<p class="empty-hint">Or use the toolbar buttons above</p>
		</div>
	{/if}
	<!-- SVG connections (rendered behind cards) -->
	{#if boardTriples.length > 0}
		<GraphConnections
			triples={boardTriples}
			{nodeMap}
			cardWidth={CARD_W}
			cardHeight={CARD_H}
			collapsedNodes={emptyCollapsed}
			onConnectionSwap={handleConnectionSwap}
			onConnectionDelete={handleConnectionDelete}
			onPredicateSelect={handlePredicateSelect}
		/>
	{/if}
	{#each cards as card (card.id)}
		<BoardCard
			{card}
			color={getCardColor(card.entityType)}
			highlighted={isHighlighted(card)}
			onPointerDown={(e) => handleCardPointerDown(card, e)}
			onDblClick={() => onCardDblClick(card)}
			onDelete={() => onCardDelete(card)}
		/>
	{/each}
</div>

<style>
	.card-board {
		flex: 1;
		position: relative;
		overflow: auto;
		transition: background 0.15s;
		background:
			radial-gradient(circle, #f0f0f0 1px, transparent 1px);
		background-size: 20px 20px;
	}
	.card-board.drag-over {
		background-color: rgba(59, 130, 246, 0.06);
		outline: 3px dashed #3b82f6;
		outline-offset: -3px;
	}
	.drop-overlay {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		pointer-events: none;
		z-index: 10;
	}
	.drop-label {
		padding: 12px 24px;
		background: rgba(59, 130, 246, 0.1);
		border: 2px dashed #3b82f6;
		border-radius: 12px;
		color: #3b82f6;
		font-size: 0.9rem;
		font-weight: 600;
	}
	.empty-board {
		position: absolute;
		inset: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		pointer-events: none;
	}
	.empty-board p {
		color: #9ca3af;
		font-size: 0.8rem;
		margin: 0;
	}
	.empty-hint {
		margin-top: 4px !important;
		font-size: 0.72rem !important;
		color: #d1d5db !important;
	}
</style>

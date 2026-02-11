<script lang="ts">
	import type { SessionCard } from './types';
	import BoardCard from './BoardCard.svelte';

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

	let {
		cards,
		onTextDrop,
		onCardMove,
		onCardDblClick,
		onCardDelete
	}: {
		cards: SessionCard[];
		onTextDrop: (text: string, x: number, y: number) => void;
		onCardMove: (cardId: string, x: number, y: number) => void;
		onCardDblClick: (card: SessionCard) => void;
		onCardDelete: (card: SessionCard) => void;
	} = $props();

	let boardEl: HTMLDivElement | undefined = $state();
	let isDragOver = $state(false);

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
		onCardMove(dragging.cardId, dragging.origX + dx, dragging.origY + dy);
	}

	function handlePointerUp() {
		dragging = null;
		dragStarted = false;
		document.removeEventListener('pointermove', handlePointerMove);
		document.removeEventListener('pointerup', handlePointerUp);
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
	{#each cards as card (card.id)}
		<BoardCard
			{card}
			color={getCardColor(card.entityType)}
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

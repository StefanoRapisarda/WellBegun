<script lang="ts">
	import type { SessionCard } from './types';
	import EntityIcon from '$lib/components/shared/EntityIcon.svelte';

	const SLOT_W = 180;
	const SLOT_H = 90;

	let {
		card,
		color,
		highlighted = false,
		width = 150,
		height = 60,
		onPointerDown,
		onDblClick,
		onDelete,
		onResizeEnd
	}: {
		card: SessionCard;
		color: string;
		highlighted?: boolean;
		width?: number;
		height?: number;
		onPointerDown: (e: PointerEvent) => void;
		onDblClick: () => void;
		onDelete: () => void;
		onResizeEnd?: (colSpan: number, rowSpan: number) => void;
	} = $props();

	let isLarge = $derived(width > 160 || height > 80);

	let displayTitle = $derived(
		isLarge ? card.title : (card.title.length > 40 ? card.title.slice(0, 38) + '...' : card.title)
	);

	let typeLabel = $derived(
		card.entityType.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())
	);

	// ── Resize handling ──
	let resizing = $state<{ startX: number; startY: number; origW: number; origH: number } | null>(null);

	function handleResizePointerDown(e: PointerEvent) {
		e.stopPropagation();
		e.preventDefault();
		resizing = {
			startX: e.clientX,
			startY: e.clientY,
			origW: width,
			origH: height
		};
		document.addEventListener('pointermove', handleResizeMove);
		document.addEventListener('pointerup', handleResizeUp);
	}

	function handleResizeMove(e: PointerEvent) {
		// Visual feedback could go here; for now we just track to compute on up
	}

	function handleResizeUp(e: PointerEvent) {
		document.removeEventListener('pointermove', handleResizeMove);
		document.removeEventListener('pointerup', handleResizeUp);
		if (!resizing || !onResizeEnd) { resizing = null; return; }

		const dx = e.clientX - resizing.startX;
		const dy = e.clientY - resizing.startY;
		const newW = resizing.origW + dx;
		const newH = resizing.origH + dy;

		// Snap to slot increments and clamp 1–3
		let colSpan = Math.round(newW / SLOT_W);
		let rowSpan = Math.round(newH / SLOT_H);
		colSpan = Math.max(1, Math.min(3, colSpan));
		rowSpan = Math.max(1, Math.min(3, rowSpan));

		onResizeEnd(colSpan, rowSpan);
		resizing = null;
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="board-card"
	class:highlighted
	class:large={isLarge}
	style:left="{card.x}px"
	style:top="{card.y}px"
	style:width="{width}px"
	style:height="{height}px"
	style:--card-color={color}
	onpointerdown={onPointerDown}
	ondblclick={onDblClick}
>
	<div class="card-header">
		<EntityIcon type={card.entityType} size={12} />
		<span class="type-label">{typeLabel}</span>
		<button
			class="delete-btn"
			onpointerdown={(e: PointerEvent) => e.stopPropagation()}
			onclick={(e: MouseEvent) => { e.stopPropagation(); onDelete(); }}
			title="Remove"
		>&times;</button>
	</div>
	<div class="card-title">{displayTitle}</div>
	{#if onResizeEnd}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="resize-handle"
			onpointerdown={handleResizePointerDown}
		></div>
	{/if}
</div>

<style>
	.board-card {
		position: absolute;
		border-radius: 6px;
		border-left: 4px solid var(--card-color);
		background: white;
		box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
		cursor: grab;
		user-select: none;
		padding: 8px 10px;
		display: flex;
		flex-direction: column;
		gap: 4px;
		transition: box-shadow 0.15s;
		touch-action: none;
		overflow: hidden;
		box-sizing: border-box;
	}
	.board-card:active {
		cursor: grabbing;
	}
	.board-card:hover {
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
	}
	.board-card.highlighted {
		box-shadow: 0 0 0 3px #3b82f6;
		opacity: 0.7;
	}
	.card-header {
		display: flex;
		align-items: center;
		gap: 5px;
	}
	.type-label {
		font-size: 0.6rem;
		color: #9ca3af;
		text-transform: uppercase;
		letter-spacing: 0.3px;
		font-weight: 600;
	}
	.delete-btn {
		margin-left: auto;
		background: none;
		border: none;
		font-size: 0.9rem;
		color: #d1d5db;
		cursor: pointer;
		padding: 0 2px;
		line-height: 1;
	}
	.delete-btn:hover {
		color: #ef4444;
	}
	.card-title {
		font-size: 0.78rem;
		color: #1f2937;
		font-weight: 500;
		line-height: 1.3;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.board-card:not(.large) .card-title {
		white-space: nowrap;
	}
	.board-card.large .card-title {
		display: -webkit-box;
		-webkit-line-clamp: 6;
		-webkit-box-orient: vertical;
	}
	.resize-handle {
		position: absolute;
		right: 0;
		bottom: 0;
		width: 14px;
		height: 14px;
		cursor: nwse-resize;
		background: linear-gradient(135deg, transparent 50%, #cbd5e1 50%);
		border-radius: 0 0 4px 0;
		opacity: 0;
		transition: opacity 0.15s;
	}
	.board-card:hover .resize-handle {
		opacity: 1;
	}
</style>

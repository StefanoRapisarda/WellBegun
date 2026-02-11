<script lang="ts">
	import type { SessionCard } from './types';

	let {
		card,
		color,
		onPointerDown,
		onDblClick,
		onDelete
	}: {
		card: SessionCard;
		color: string;
		onPointerDown: (e: PointerEvent) => void;
		onDblClick: () => void;
		onDelete: () => void;
	} = $props();

	let displayTitle = $derived(
		card.title.length > 40 ? card.title.slice(0, 38) + '...' : card.title
	);

	let typeLabel = $derived(
		card.entityType.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())
	);
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="board-card"
	style:left="{card.x}px"
	style:top="{card.y}px"
	style:--card-color={color}
	onpointerdown={onPointerDown}
	ondblclick={onDblClick}
>
	<div class="card-header">
		<span class="type-dot" style:background={color}></span>
		<span class="type-label">{typeLabel}</span>
		<button
			class="delete-btn"
			onpointerdown={(e: PointerEvent) => e.stopPropagation()}
			onclick={(e: MouseEvent) => { e.stopPropagation(); onDelete(); }}
			title="Remove"
		>&times;</button>
	</div>
	<div class="card-title">{displayTitle}</div>
</div>

<style>
	.board-card {
		position: absolute;
		width: 150px;
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
	}
	.board-card:active {
		cursor: grabbing;
	}
	.board-card:hover {
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
	}
	.card-header {
		display: flex;
		align-items: center;
		gap: 5px;
	}
	.type-dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		flex-shrink: 0;
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
	}
</style>

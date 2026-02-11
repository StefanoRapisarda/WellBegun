<script lang="ts">
	let {
		entityType,
		entityId,
		title,
		x,
		y,
		color,
		collapsed = false,
		highlighted = false,
		selected = false,
		archived = false,
		onPointerDown,
		onDblClick,
		onToggleCollapse
	}: {
		entityType: string;
		entityId: number;
		title: string;
		x: number;
		y: number;
		color: string;
		collapsed?: boolean;
		highlighted?: boolean;
		selected?: boolean;
		archived?: boolean;
		onPointerDown: (e: PointerEvent) => void;
		onDblClick: () => void;
		onToggleCollapse: () => void;
	} = $props();

	let displayTitle = $derived(
		title.length > 22 ? title.slice(0, 20) + '…' : title
	);

	let typeLabel = $derived(
		entityType.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())
	);
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="graph-card"
	class:highlighted
	class:selected
	class:archived
	style:left="{x}px"
	style:top="{y}px"
	style:--card-color={color}
	onpointerdown={onPointerDown}
	ondblclick={onDblClick}
>
	<div class="card-header">
		<span class="type-dot" style:background={color}></span>
		<span class="type-label">{typeLabel}</span>
		{#if archived}<span class="archived-badge">archived</span>{/if}
	</div>
	<div class="card-title">{displayTitle}</div>
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<button
		class="collapse-toggle"
		class:collapsed
		onpointerdown={(e: PointerEvent) => e.stopPropagation()}
		onclick={(e: MouseEvent) => { e.stopPropagation(); onToggleCollapse(); }}
		title={collapsed ? 'Expand connections' : 'Collapse connections'}
	>
		&#9656;
	</button>
</div>

<style>
	.graph-card {
		position: absolute;
		width: 150px;
		min-height: 50px;
		border-radius: 6px;
		border-left: 4px solid var(--card-color);
		background: white;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
		cursor: grab;
		user-select: none;
		padding: 8px 10px;
		display: flex;
		flex-direction: column;
		gap: 4px;
		transition: box-shadow 0.15s;
		touch-action: none;
	}
	.graph-card:active {
		cursor: grabbing;
	}
	.graph-card.archived {
		opacity: 0.55;
		border-left-style: dashed;
		background: #f9fafb;
	}
	.archived-badge {
		font-size: 0.5rem;
		padding: 1px 4px;
		background: #fef2f2;
		color: #b91c1c;
		border: 1px solid #fecaca;
		border-radius: 3px;
		text-transform: uppercase;
		letter-spacing: 0.3px;
		font-weight: 600;
		margin-left: auto;
	}
	.graph-card.highlighted {
		box-shadow:
			0 0 0 2px var(--card-color),
			0 4px 16px rgba(0, 0, 0, 0.15);
	}
	.graph-card.selected {
		box-shadow: 0 0 0 2px #3b82f6, 0 0 12px rgba(59, 130, 246, 0.3);
		background: #eff6ff;
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
	.card-title {
		font-size: 0.78rem;
		color: #1f2937;
		font-weight: 500;
		line-height: 1.3;
	}
	.collapse-toggle {
		position: absolute;
		right: -8px;
		top: 50%;
		transform: translateY(-50%);
		width: 16px;
		height: 16px;
		border-radius: 50%;
		border: 1px solid #d1d5db;
		background: white;
		font-size: 0.55rem;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		color: #9ca3af;
		transition: transform 0.15s, background 0.15s;
		padding: 0;
		line-height: 1;
	}
	.collapse-toggle:hover {
		background: #f3f4f6;
	}
	.collapse-toggle.collapsed {
		transform: translateY(-50%) rotate(180deg);
	}
</style>

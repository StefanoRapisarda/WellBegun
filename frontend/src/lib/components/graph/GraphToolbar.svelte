<script lang="ts">
	const ENTITY_BUTTONS: { type: string; label: string; color: string }[] = [
		{ type: 'project', label: '+Project', color: '#5c7a99' },
		{ type: 'log', label: '+Log', color: '#8b7355' },
		{ type: 'note', label: '+Note', color: '#6b8e6b' },
		{ type: 'activity', label: '+Activity', color: '#b5838d' },
		{ type: 'source', label: '+Source', color: '#c9a227' },
		{ type: 'actor', label: '+Actor', color: '#8b4557' },
		{ type: 'plan', label: '+Plan', color: '#6b8ba3' },
		{ type: 'collection', label: '+Collection', color: '#7c6f9e' }
	];

	let {
		zoom,
		filterOpen = false,
		editorOpen = false,
		selectActive = false,
		onAddEntity,
		onZoomIn,
		onZoomOut,
		onZoomFit,
		onToggleFilter,
		onToggleEditor,
		onSwitchToCards,
		onScreenshot,
		onToggleSelect
	}: {
		zoom: number;
		filterOpen?: boolean;
		editorOpen?: boolean;
		selectActive?: boolean;
		onAddEntity: (entityType: string) => void;
		onZoomIn: () => void;
		onZoomOut: () => void;
		onZoomFit: () => void;
		onToggleFilter: () => void;
		onToggleEditor?: () => void;
		onSwitchToCards?: () => void;
		onScreenshot?: () => void;
		onToggleSelect?: () => void;
	} = $props();

	let zoomPct = $derived(Math.round(zoom * 100));
</script>

<div class="graph-toolbar">
	<div class="entity-buttons">
		{#each ENTITY_BUTTONS as btn}
			<button
				class="entity-btn"
				style:--btn-color={btn.color}
				onclick={() => onAddEntity(btn.type)}
			>
				{btn.label}
			</button>
		{/each}
	</div>
	<div class="zoom-controls">
		<button class="zoom-btn" onclick={onZoomOut} title="Zoom out">−</button>
		<span class="zoom-pct">{zoomPct}%</span>
		<button class="zoom-btn" onclick={onZoomIn} title="Zoom in">+</button>
		<button class="zoom-btn fit-btn" onclick={onZoomFit} title="Fit to view">Fit</button>
		{#if onScreenshot}
			<button class="zoom-btn screenshot-btn" onclick={onScreenshot} title="Save as PNG">
				<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
					<circle cx="12" cy="13" r="4"/>
				</svg>
			</button>
		{/if}
		{#if onToggleSelect}
			<button
				class="zoom-btn select-btn"
				class:active={selectActive}
				onclick={onToggleSelect}
				title="Rectangular selection (or hold Shift)"
			>
				<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
					<rect x="1" y="1" width="12" height="12" stroke-dasharray="3 2" rx="1" />
					<path d="M10 7L13 10M13 10L10 13M13 10H8" stroke-linecap="round" stroke-linejoin="round" />
				</svg>
			</button>
		{/if}
		{#if onToggleEditor}
			<button
				class="zoom-btn editor-btn"
				class:active={editorOpen}
				onclick={onToggleEditor}
				title="Toggle card editor"
			>
				<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>
					<path d="m15 5 4 4"/>
				</svg>
			</button>
		{/if}
		<button
			class="zoom-btn filter-btn"
			class:active={filterOpen}
			onclick={onToggleFilter}
			title="Filter entities"
		>
			<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
			</svg>
		</button>
		{#if onSwitchToCards}
			<button
				class="zoom-btn cards-btn"
				onclick={onSwitchToCards}
				title="Switch to Cards view"
			>
				<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
					<rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
				</svg>
			</button>
		{/if}
	</div>
</div>

<style>
	.graph-toolbar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 8px 16px;
		background: #fafafa;
		border-bottom: 1px solid #e5e7eb;
		gap: 12px;
		flex-wrap: wrap;
	}
	.entity-buttons {
		display: flex;
		gap: 4px;
		flex-wrap: wrap;
	}
	.entity-btn {
		padding: 4px 10px;
		border: 1px solid var(--btn-color);
		border-radius: 6px;
		background: white;
		cursor: pointer;
		font-size: 0.72rem;
		color: var(--btn-color);
		font-weight: 500;
		transition: all 0.15s;
	}
	.entity-btn:hover {
		background: var(--btn-color);
		color: white;
	}
	.zoom-controls {
		display: flex;
		align-items: center;
		gap: 6px;
		flex-shrink: 0;
	}
	.zoom-btn {
		width: 28px;
		height: 28px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		background: white;
		cursor: pointer;
		font-size: 0.85rem;
		color: #374151;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: background 0.15s;
	}
	.zoom-btn:hover {
		background: #f3f4f6;
	}
	.fit-btn {
		width: auto;
		padding: 0 10px;
		font-size: 0.72rem;
		font-weight: 500;
	}
	.zoom-pct {
		font-size: 0.72rem;
		color: #6b7280;
		min-width: 40px;
		text-align: center;
	}
	.screenshot-btn {
		width: auto;
		padding: 0 6px;
		margin-left: 4px;
	}
	.select-btn {
		width: auto;
		padding: 0 6px;
		margin-left: 4px;
	}
	.select-btn.active {
		background: #3b82f6;
		color: white;
		border-color: #3b82f6;
	}
	.select-btn.active:hover {
		background: #2563eb;
	}
	.editor-btn {
		width: auto;
		padding: 0 6px;
		margin-left: 4px;
	}
	.editor-btn.active {
		background: #374151;
		color: white;
		border-color: #374151;
	}
	.editor-btn.active:hover {
		background: #4b5563;
	}
	.filter-btn {
		width: auto;
		padding: 0 6px;
		margin-left: 4px;
	}
	.filter-btn.active {
		background: #374151;
		color: white;
		border-color: #374151;
	}
	.filter-btn.active:hover {
		background: #4b5563;
	}
	.cards-btn {
		width: auto;
		padding: 0 6px;
		margin-left: 4px;
	}
</style>

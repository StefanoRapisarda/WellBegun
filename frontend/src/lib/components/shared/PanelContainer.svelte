<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { Tag } from '$lib/types';
	import PanelTagFilter from './PanelTagFilter.svelte';
	import { pulsingPanels } from '$lib/stores/highlights';
	import { togglePanel } from '$lib/stores/panels';

	let {
		title,
		panelId = '',
		grow = false,
		color = '',
		onAdd = undefined,
		availableTags = [],
		selectedTagIds = [],
		filterMode = 'or',
		onTagToggle = undefined,
		onModeToggle = undefined,
		children
	}: {
		title: string;
		panelId?: string;
		grow?: boolean;
		color?: string;
		onAdd?: () => void;
		availableTags?: Tag[];
		selectedTagIds?: number[];
		filterMode?: 'or' | 'and';
		onTagToggle?: (tagId: number) => void;
		onModeToggle?: () => void;
		children: Snippet;
	} = $props();

	let showFilter = $state(false);
	let collapsed = $state(false);
	let hasFilter = $derived(onTagToggle !== undefined && availableTags.length > 0);
	let isPulsing = $derived($pulsingPanels.has(panelId));
</script>

<section class="panel" class:panel-grow={grow && !collapsed} class:panel-collapsed={collapsed} class:pulsing={isPulsing} style:--panel-color={color || '#6b7280'} data-panel-id={panelId}>
	<header class="panel-header">
		<div class="header-left">
			{#if panelId}
				<button class="btn-header-close" onclick={() => togglePanel(panelId)} title="Close panel">&times;</button>
			{/if}
			<button class="btn-collapse" onclick={() => collapsed = !collapsed} title={collapsed ? 'Expand' : 'Collapse'}>
				<span class="collapse-chevron" class:collapsed>&#9660;</span>
			</button>
			<h2>{title}</h2>
		</div>
		<div class="header-actions">
			{#if !collapsed}
				{#if hasFilter}
					<button
						class="btn-header-filter"
						class:active={showFilter || selectedTagIds.length > 0}
						onclick={() => (showFilter = !showFilter)}
						title="Filter by tags"
					>
						<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
						</svg>
						{#if selectedTagIds.length > 0}
							<span class="filter-count">{selectedTagIds.length}</span>
						{/if}
					</button>
				{/if}
				{#if onAdd}
					<button class="btn-header-add" onclick={onAdd}>+</button>
				{/if}
			{/if}
		</div>
	</header>
	{#if !collapsed}
		{#if showFilter && hasFilter && onTagToggle && onModeToggle}
			<div class="filter-section">
				<PanelTagFilter
					{availableTags}
					{selectedTagIds}
					{filterMode}
					{onTagToggle}
					{onModeToggle}
				/>
			</div>
		{/if}
		<div class="panel-body">
			{@render children()}
		</div>
	{/if}
</section>

<style>
	.panel {
		background: color-mix(in srgb, var(--panel-color) 12%, white);
		border: 1px solid color-mix(in srgb, var(--panel-color) 40%, #e5e7eb);
		border-radius: 8px;
		display: flex;
		flex-direction: column;
		min-height: 200px;
		max-height: 70vh;
		overflow: hidden;
	}
	.panel-grow {
		flex: 1;
	}
	.panel-header {
		padding: 12px 16px;
		border-bottom: 1px solid color-mix(in srgb, var(--panel-color) 30%, #e5e7eb);
		background: color-mix(in srgb, var(--panel-color) 20%, #f9fafb);
		border-radius: 8px 8px 0 0;
		cursor: grab;
		display: flex;
		align-items: center;
		justify-content: space-between;
		flex-shrink: 0;
	}
	.header-left {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.panel-header h2 {
		margin: 0;
		font-size: 1rem;
		font-weight: 600;
		color: color-mix(in srgb, var(--panel-color) 80%, #111827);
	}
	.header-actions {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.btn-header-filter {
		width: 24px;
		height: 24px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		background: white;
		cursor: pointer;
		color: #9ca3af;
		transition: all 0.15s;
		position: relative;
	}
	.btn-header-filter:hover {
		border-color: #9ca3af;
		color: #6b7280;
	}
	.btn-header-filter.active {
		border-color: var(--panel-color);
		color: var(--panel-color);
		background: color-mix(in srgb, var(--panel-color) 10%, white);
	}
	.filter-count {
		position: absolute;
		top: -4px;
		right: -4px;
		background: var(--panel-color);
		color: white;
		font-size: 0.6rem;
		width: 14px;
		height: 14px;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-weight: 600;
	}
	.btn-header-add {
		width: 24px;
		height: 24px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: 1px solid var(--panel-color);
		border-radius: 4px;
		background: white;
		cursor: pointer;
		font-size: 1rem;
		font-weight: 600;
		line-height: 1;
		color: var(--panel-color);
		transition: all 0.15s;
	}
	.btn-header-add:hover {
		background: var(--panel-color);
		color: white;
	}
	.panel-collapsed {
		min-height: auto;
		max-height: none;
	}
	.panel-collapsed .panel-header {
		border-bottom: none;
		border-radius: 8px;
	}
	.btn-collapse {
		width: 18px;
		height: 18px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: none;
		border-radius: 3px;
		background: transparent;
		cursor: pointer;
		padding: 0;
		color: #c9cdd3;
		transition: all 0.15s;
	}
	.btn-collapse:hover {
		color: #6b7280;
	}
	.collapse-chevron {
		font-size: 0.55rem;
		display: inline-block;
		transition: transform 0.15s;
	}
	.collapse-chevron.collapsed {
		transform: rotate(-90deg);
	}
	.btn-header-close {
		width: 18px;
		height: 18px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: none;
		border-radius: 3px;
		background: transparent;
		cursor: pointer;
		font-size: 0.9rem;
		line-height: 1;
		color: #c9cdd3;
		transition: all 0.15s;
	}
	.btn-header-close:hover {
		background: #fee2e2;
		color: #dc2626;
	}
	.filter-section {
		padding: 8px 16px;
		background: color-mix(in srgb, var(--panel-color) 5%, white);
		border-bottom: 1px solid color-mix(in srgb, var(--panel-color) 20%, #e5e7eb);
	}
	.panel-body {
		padding: 16px;
		overflow-y: auto;
		flex: 1;
		min-height: 0;
	}
	/* Custom scrollbar styling */
	.panel-body::-webkit-scrollbar {
		width: 8px;
	}
	.panel-body::-webkit-scrollbar-track {
		background: #f1f1f1;
		border-radius: 4px;
	}
	.panel-body::-webkit-scrollbar-thumb {
		background: #c1c1c1;
		border-radius: 4px;
	}
	.panel-body::-webkit-scrollbar-thumb:hover {
		background: #a1a1a1;
	}
	/* Pulsing animation for AI highlights */
	.panel.pulsing {
		animation: pulse-glow 0.5s ease-in-out 3;
	}
	@keyframes pulse-glow {
		0%, 100% {
			box-shadow: 0 0 0 0 color-mix(in srgb, var(--panel-color) 50%, transparent);
		}
		50% {
			box-shadow: 0 0 20px 5px color-mix(in srgb, var(--panel-color) 60%, transparent);
		}
	}
</style>

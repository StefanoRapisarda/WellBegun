<script lang="ts">
	import { panels, panelSlots, movePanel } from '$lib/stores/panels';
	import { focusSelection, isFocusActive } from '$lib/stores/focus';
	import { panelSelection } from '$lib/stores/panelSelection';
	import BulkActionPanel from '$lib/components/shared/BulkActionPanel.svelte';
	import { onMount, onDestroy } from 'svelte';
	import ProjectPanel from '$lib/components/panels/ProjectPanel.svelte';
	import LogPanel from '$lib/components/panels/LogPanel.svelte';
	import NotePanel from '$lib/components/panels/NotePanel.svelte';
	import WildTagPanel from '$lib/components/panels/WildTagPanel.svelte';
	import SourcePanel from '$lib/components/panels/SourcePanel.svelte';
	import ActorPanel from '$lib/components/panels/ActorPanel.svelte';
	import ActivityPanel from '$lib/components/panels/ActivityPanel.svelte';
	import ReadingListPanel from '$lib/components/panels/ReadingListPanel.svelte';
	import LearningTrackPanel from '$lib/components/panels/LearningTrackPanel.svelte';
	import LinksPanel from '$lib/components/panels/LinksPanel.svelte';

	const panelComponents: Record<string, any> = {
		project: ProjectPanel,
		log: LogPanel,
		note: NotePanel,
		wildtag: WildTagPanel,
		source: SourcePanel,
		actor: ActorPanel,
		activity: ActivityPanel,
		readinglist: ReadingListPanel,
		learningtrack: LearningTrackPanel,
		links: LinksPanel
	};

	let visibleCount = $derived($panelSlots.filter((s) => s !== null).length);
	let cols = $derived(Math.min(Math.max(visibleCount, 1), 3));

	// Pad slots to fill current row + one extra row of empty drop targets
	let displaySlots = $derived.by(() => {
		const slots = [...$panelSlots];
		const rows = Math.ceil(slots.length / cols);
		const targetLen = (rows + 1) * cols;
		while (slots.length < targetLen) slots.push(null);
		return slots;
	});

	// Distribute flat slots into column arrays, each entry keeping its flat index
	let columns = $derived.by(() => {
		const result: { slotId: string | null; index: number }[][] = [];
		for (let c = 0; c < cols; c++) result.push([]);
		for (let i = 0; i < displaySlots.length; i++) {
			result[i % cols].push({ slotId: displaySlots[i], index: i });
		}
		return result;
	});

	let draggedIndex = $state<number | null>(null);
	let dragOverIndex = $state<number | null>(null);

	function handleDragStart(e: DragEvent, index: number) {
		draggedIndex = index;
		if (e.dataTransfer) {
			e.dataTransfer.effectAllowed = 'move';
		}
	}

	function handleDragOver(e: DragEvent, index: number) {
		e.preventDefault();
		if (draggedIndex !== null && draggedIndex !== index) {
			dragOverIndex = index;
		}
	}

	function handleDragLeave() {
		dragOverIndex = null;
	}

	function handleDrop(e: DragEvent, index: number) {
		e.preventDefault();
		if (draggedIndex !== null && draggedIndex !== index) {
			movePanel(draggedIndex, index);
		}
		draggedIndex = null;
		dragOverIndex = null;
	}

	function handleDragEnd() {
		draggedIndex = null;
		dragOverIndex = null;
	}

	function handleGridClick(e: MouseEvent) {
		const target = e.target as HTMLElement;
		if (!target.closest('[data-selectable]')) {
			panelSelection.clear();
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			panelSelection.clear();
		}
	}

	onMount(() => {
		document.addEventListener('keydown', handleKeydown);
	});

	onDestroy(() => {
		document.removeEventListener('keydown', handleKeydown);
		panelSelection.clear();
	});
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="panel-grid" style="--cols: {cols}" onclick={handleGridClick}>
	{#each columns as column}
		<div class="panel-column">
			{#each column as { slotId, index } (index)}
				{#if slotId && panelComponents[slotId]}
					{@const PanelComp = panelComponents[slotId]}
					<div
						class="panel-wrapper"
						class:dragging={draggedIndex === index}
						class:drag-over={dragOverIndex === index}
						draggable="true"
						ondragstart={(e) => handleDragStart(e, index)}
						ondragover={(e) => handleDragOver(e, index)}
						ondragleave={handleDragLeave}
						ondrop={(e) => handleDrop(e, index)}
						ondragend={handleDragEnd}
						role="listitem"
					>
						<PanelComp />
					</div>
				{:else}
					<div
						class="slot-empty"
						class:drag-over={dragOverIndex === index}
						ondragover={(e) => handleDragOver(e, index)}
						ondragleave={handleDragLeave}
						ondrop={(e) => handleDrop(e, index)}
						role="listitem"
					></div>
				{/if}
			{/each}
		</div>
	{/each}
</div>

<BulkActionPanel />

{#if visibleCount === 0}
	{#if !isFocusActive($focusSelection)}
		<p class="no-panels">Set a focus from the Home tab to begin, or toggle panels manually from the toolbar.</p>
	{:else}
		<p class="no-panels">No panels visible. Use the toolbar to toggle panels.</p>
	{/if}
{/if}

<style>
	.panel-grid {
		display: grid;
		grid-template-columns: repeat(var(--cols), 1fr);
		gap: 16px;
		min-height: calc(100vh - 80px);
		align-items: start;
	}
	.panel-column {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}
	.panel-wrapper {
		min-width: 0;
		display: flex;
		flex-direction: column;
		transition: opacity 0.15s ease;
	}
	.panel-wrapper.dragging {
		opacity: 0.4;
	}
	.panel-wrapper.drag-over {
		border: 2px dashed #3b82f6;
		border-radius: 8px;
	}
	.slot-empty {
		min-height: 60px;
		border: 2px dashed #e5e7eb;
		border-radius: 8px;
		transition: border-color 0.15s ease;
	}
	.slot-empty.drag-over {
		border-color: #3b82f6;
		background: #eff6ff;
	}
	.no-panels {
		text-align: center;
		color: #9ca3af;
		margin-top: 40px;
	}
	@media (max-width: 1024px) {
		.panel-grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}
	@media (max-width: 640px) {
		.panel-grid {
			grid-template-columns: 1fr;
		}
	}
</style>

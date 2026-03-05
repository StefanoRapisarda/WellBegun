<script lang="ts">
	import { updateWorkspace } from '$lib/api/workspaces';
	import { loadWorkspaces, refreshActiveWorkspace } from '$lib/stores/workspaces';

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
		workspaceName,
		workspaceDescription = null,
		workspaceId,
		zoom,
		timelineOpen = false,
		queryPanelOpen = false,
		editorOpen = false,
		onBack,
		onZoomIn,
		onZoomOut,
		onZoomFit,
		onHierarchical,
		onQuadrant,
		onToggleTimeline,
		onToggleQuery,
		onToggleEditor,
		onAddEntity,
		onClear,
		onScreenshot,
		selectActive = false,
		onToggleSelect
	}: {
		workspaceName: string;
		workspaceDescription?: string | null;
		workspaceId: number;
		zoom: number;
		timelineOpen?: boolean;
		queryPanelOpen?: boolean;
		editorOpen?: boolean;
		selectActive?: boolean;
		onBack?: () => void;
		onZoomIn: () => void;
		onZoomOut: () => void;
		onZoomFit: () => void;
		onHierarchical: () => void;
		onQuadrant: () => void;
		onToggleTimeline: () => void;
		onToggleQuery: () => void;
		onToggleEditor?: () => void;
		onAddEntity: (type: string) => void;
		onClear: () => void;
		onScreenshot?: () => void;
		onToggleSelect?: () => void;
	} = $props();

	// ── Name editing ──
	let editingName = $state(false);
	let editName = $state('');
	let zoomPct = $derived(Math.round(zoom * 100));

	function startEditName() {
		editName = workspaceName;
		editingName = true;
	}

	async function finishEditName() {
		if (editName.trim() && editName.trim() !== workspaceName) {
			await updateWorkspace(workspaceId, { name: editName.trim() });
			await loadWorkspaces();
			await refreshActiveWorkspace();
		}
		editingName = false;
	}

	function handleNameKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') finishEditName();
		if (e.key === 'Escape') { editingName = false; }
	}

	// ── Description editing ──
	let editingDesc = $state(false);
	let editDesc = $state('');

	function startEditDesc() {
		editDesc = workspaceDescription ?? '';
		editingDesc = true;
		requestAnimationFrame(() => {
			const input = document.querySelector('.desc-input') as HTMLInputElement;
			input?.focus();
		});
	}

	async function finishEditDesc() {
		const newDesc = editDesc.trim();
		const oldDesc = workspaceDescription ?? '';
		if (newDesc !== oldDesc) {
			await updateWorkspace(workspaceId, { description: newDesc });
			await loadWorkspaces();
			await refreshActiveWorkspace();
		}
		editingDesc = false;
	}

	function handleDescKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') finishEditDesc();
		if (e.key === 'Escape') { editingDesc = false; }
	}
</script>

<div class="workspace-toolbar">
	<!-- Row 1: Identity (name + description) -->
	<div class="toolbar-header">
		<div class="identity">
			{#if editingName}
				<input
					class="name-input"
					bind:value={editName}
					onblur={finishEditName}
					onkeydown={handleNameKeydown}
				/>
			{:else}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<span class="workspace-name" ondblclick={startEditName} title="Double-click to rename">{workspaceName}</span>
			{/if}
			<span class="desc-separator">&mdash;</span>
			{#if editingDesc}
				<input
					class="desc-input"
					bind:value={editDesc}
					onblur={finishEditDesc}
					onkeydown={handleDescKeydown}
					placeholder="Describe this workspace..."
				/>
			{:else}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<span
					class="workspace-desc"
					class:placeholder={!workspaceDescription}
					onclick={startEditDesc}
					title="Click to edit description"
				>
					{workspaceDescription || 'Add a description...'}
				</span>
			{/if}
		</div>
	</div>

	<!-- Row 2: All tools -->
	<div class="toolbar-actions">
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

		<div class="tool-group">
			<button class="tool-btn" onclick={onZoomOut} title="Zoom out">-</button>
			<span class="zoom-pct">{zoomPct}%</span>
			<button class="tool-btn" onclick={onZoomIn} title="Zoom in">+</button>
			<button class="tool-btn fit-btn" onclick={onZoomFit} title="Fit to view">Fit</button>
			{#if onScreenshot}
				<button class="tool-btn screenshot-btn" onclick={onScreenshot} title="Save as PNG">
					<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
						<circle cx="12" cy="13" r="4"/>
					</svg>
				</button>
			{/if}
			{#if onToggleSelect}
				<button
					class="tool-btn select-btn"
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
			<div class="separator"></div>
			<button class="tool-btn layout-btn" onclick={onHierarchical} title="Hierarchical layout">
				<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<rect x="8" y="2" width="8" height="4" rx="1"/><rect x="2" y="18" width="8" height="4" rx="1"/><rect x="14" y="18" width="8" height="4" rx="1"/><path d="M12 6v6m0 0-6 6m6-6 6 6"/>
				</svg>
			</button>
			<button class="tool-btn layout-btn" onclick={onQuadrant} title="Quadrant layout">
				<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
					<rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
				</svg>
			</button>
			<div class="separator"></div>
			{#if onToggleEditor}
				<button
					class="tool-btn"
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
				class="tool-btn"
				class:active={timelineOpen}
				onclick={onToggleTimeline}
				title="Toggle timeline"
			>
				<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
				</svg>
			</button>
			<button
				class="tool-btn"
				class:active={queryPanelOpen}
				onclick={onToggleQuery}
				title="Search & add entities"
			>
				<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
				</svg>
			</button>
			<div class="separator"></div>
			<button class="tool-btn clear-btn" onclick={onClear} title="Remove all items from workspace">
				Clear
			</button>
		</div>
	</div>
</div>

<style>
	.workspace-toolbar {
		display: flex;
		flex-direction: column;
		background: #fafafa;
		border-bottom: 1px solid #e5e7eb;
		flex-shrink: 0;
	}
	/* ── Row 1: Header (name + description) ── */
	.toolbar-header {
		display: flex;
		align-items: center;
		padding: 8px 16px 4px;
	}
	.identity {
		display: flex;
		align-items: center;
		gap: 0;
		min-width: 0;
		flex: 1;
	}
	.workspace-name {
		font-size: 0.88rem;
		font-weight: 600;
		color: #374151;
		cursor: default;
		white-space: nowrap;
		flex-shrink: 0;
	}
	.name-input {
		font-size: 0.88rem;
		font-weight: 600;
		color: #374151;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		padding: 1px 6px;
		outline: none;
		width: 180px;
		flex-shrink: 0;
	}
	.desc-separator {
		color: #d1d5db;
		margin: 0 8px;
		flex-shrink: 0;
		font-size: 0.8rem;
	}
	.workspace-desc {
		font-size: 0.78rem;
		color: #6b7280;
		cursor: pointer;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		min-width: 0;
		transition: color 0.15s;
	}
	.workspace-desc:hover {
		color: #374151;
	}
	.workspace-desc.placeholder {
		font-style: italic;
		color: #b0b7c3;
	}
	.workspace-desc.placeholder:hover {
		color: #9ca3af;
	}
	.desc-input {
		font-size: 0.78rem;
		color: #374151;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		padding: 1px 6px;
		outline: none;
		flex: 1;
		min-width: 120px;
	}
	.desc-input:focus {
		border-color: #6b7280;
	}
	/* ── Row 2: Actions (entity buttons + tools) ── */
	.toolbar-actions {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 4px 16px 6px;
		gap: 12px;
	}
	.entity-buttons {
		display: flex;
		gap: 4px;
		flex-wrap: wrap;
	}
	.entity-btn {
		padding: 3px 8px;
		border: 1px solid var(--btn-color);
		border-radius: 6px;
		background: white;
		cursor: pointer;
		font-size: 0.68rem;
		color: var(--btn-color);
		font-weight: 500;
		transition: all 0.15s;
	}
	.entity-btn:hover {
		background: var(--btn-color);
		color: white;
	}
	.tool-group {
		display: flex;
		align-items: center;
		gap: 5px;
		flex-shrink: 0;
	}
	.tool-btn {
		width: 26px;
		height: 26px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		background: white;
		cursor: pointer;
		font-size: 0.82rem;
		color: #374151;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.15s;
	}
	.tool-btn:hover {
		background: #f3f4f6;
	}
	.tool-btn.active {
		background: #374151;
		color: white;
		border-color: #374151;
	}
	.tool-btn.active:hover {
		background: #4b5563;
	}
	.clear-btn {
		width: auto;
		padding: 0 8px;
		font-size: 0.68rem;
		font-weight: 500;
		color: #dc2626;
		border-color: #fecaca;
	}
	.clear-btn:hover {
		background: #fee2e2;
		color: #dc2626;
	}
	.screenshot-btn {
		width: auto;
		padding: 0 6px;
	}
	.select-btn {
		width: auto;
		padding: 0 6px;
	}
	.select-btn.active {
		background: #3b82f6;
		color: white;
		border-color: #3b82f6;
	}
	.select-btn.active:hover {
		background: #2563eb;
	}
	.fit-btn, .layout-btn {
		width: auto;
		padding: 0 8px;
		font-size: 0.68rem;
		font-weight: 500;
	}
	.zoom-pct {
		font-size: 0.68rem;
		color: #6b7280;
		min-width: 32px;
		text-align: center;
	}
	.separator {
		width: 1px;
		height: 16px;
		background: #d1d5db;
		margin: 0 1px;
	}
</style>

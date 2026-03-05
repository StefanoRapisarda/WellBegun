<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { workspaces, activeWorkspace, setActiveWorkspace, loadWorkspaces } from '$lib/stores/workspaces';
	import { createWorkspace, deleteWorkspace, getWorkspaceEvents, getWorkspace } from '$lib/api/workspaces';
	import { createLog } from '$lib/api/logs';
	import { loadLogs } from '$lib/stores/logs';
	import { tags, loadTags } from '$lib/stores/tags';
	import { attachTag } from '$lib/api/tags';
	import type { Workspace, WorkspaceItem } from '$lib/types';
	import WorkspaceToolbar from './WorkspaceToolbar.svelte';
	import WorkspaceGraph from './WorkspaceGraph.svelte';
	import WorkspaceTimeline from './WorkspaceTimeline.svelte';

	let showTimeline = $state(false);
	let zoom = $state(1);

	let graphComponent: { zoomIn: () => void; zoomOut: () => void; zoomFit: () => void; hierarchicalLayout: () => void; quadrantLayout: () => void; handleAddEntity: (type: string) => void; toggleQueryPanel: () => void; toggleEditor: () => void; clearAll: () => void; screenshot: () => void } | undefined = $state();

	let queryPanelOpen = $state(false);
	let editorOpen = $state(false);
	let selectModeOpen = $state(false);

	// ── Stable tab order ──
	const STORAGE_KEY = 'wb-workspace-tab-order';
	let tabOrder = $state<number[]>([]);

	function loadTabOrder(): number[] {
		if (typeof localStorage === 'undefined') return [];
		try {
			const raw = localStorage.getItem(STORAGE_KEY);
			if (raw) return JSON.parse(raw);
		} catch {}
		return [];
	}

	function saveTabOrder(order: number[]) {
		if (typeof localStorage === 'undefined') return;
		try { localStorage.setItem(STORAGE_KEY, JSON.stringify(order)); } catch {}
	}

	function syncTabOrder(wsList: Workspace[]): number[] {
		const ids = new Set(wsList.map(w => w.id));
		const kept = tabOrder.filter(id => ids.has(id));
		const existing = new Set(kept);
		for (const ws of wsList) {
			if (!existing.has(ws.id)) kept.push(ws.id);
		}
		return kept;
	}

	// Derive ordered workspace list from tabOrder + store data
	let orderedWorkspaces = $derived.by(() => {
		const map = new Map<number, Workspace>();
		for (const ws of $workspaces) map.set(ws.id, ws);
		const result: Workspace[] = [];
		for (const id of tabOrder) {
			const ws = map.get(id);
			if (ws) result.push(ws);
		}
		return result;
	});

	// ── Drag-to-reorder ──
	let dragIdx: number | null = $state(null);
	let dragOverIdx: number | null = $state(null);

	function handleDragStart(idx: number, e: DragEvent) {
		dragIdx = idx;
		if (e.dataTransfer) {
			e.dataTransfer.effectAllowed = 'move';
			e.dataTransfer.setData('text/plain', String(idx));
		}
	}

	function handleDragOver(idx: number, e: DragEvent) {
		e.preventDefault();
		if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
		dragOverIdx = idx;
	}

	function handleDragLeave() {
		dragOverIdx = null;
	}

	function handleDrop(idx: number, e: DragEvent) {
		e.preventDefault();
		if (dragIdx !== null && dragIdx !== idx) {
			const updated = [...tabOrder];
			const [moved] = updated.splice(dragIdx, 1);
			updated.splice(idx, 0, moved);
			tabOrder = updated;
			saveTabOrder(updated);
		}
		dragIdx = null;
		dragOverIdx = null;
	}

	function handleDragEnd() {
		dragIdx = null;
		dragOverIdx = null;
	}

	// ── New workspace input ──
	let creating = $state(false);
	let newName = $state('');

	function startCreate() {
		creating = true;
		newName = '';
		requestAnimationFrame(() => {
			const input = document.querySelector('.new-ws-input') as HTMLInputElement;
			input?.focus();
		});
	}

	async function finishCreate() {
		const name = newName.trim();
		if (!name) {
			creating = false;
			return;
		}
		try {
			const ws = await createWorkspace({ name });
			creating = false;
			newName = '';
			await loadWorkspaces();
			const newOrder = syncTabOrder($workspaces);
			tabOrder = newOrder;
			saveTabOrder(newOrder);
			await setActiveWorkspace(ws.id);
		} catch (e) {
			console.error('Failed to create workspace:', e);
		}
	}

	function cancelCreate() {
		creating = false;
		newName = '';
	}

	function handleNewKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') finishCreate();
		if (e.key === 'Escape') cancelCreate();
	}

	// ── Build session log content ──
	function buildSessionLog(ws: { name: string; description: string | null }, logEntries: { timestamp: string; text: string }[]): { title: string; content: string } {
		const date = new Date().toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
		const title = `Session: ${ws.name} — ${date}`;

		const lines: string[] = [];

		if (ws.description) {
			lines.push(ws.description, '');
		}

		if (logEntries.length > 0) {
			for (const entry of logEntries) {
				const time = new Date(entry.timestamp).toLocaleString(undefined, {
					month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
				});
				lines.push(`**[${time}]** ${entry.text}`);
			}
			lines.push('');
		}

		return { title, content: lines.join('\n') };
	}

	async function handleCloseTab(id: number, e: MouseEvent) {
		e.stopPropagation();
		if (!confirm('Close this workspace? A session log will be saved.')) return;
		const wasActive = $activeWorkspace?.id === id;
		try {
			// Fetch full workspace details and events before deleting
			const detail = await getWorkspace(id);
			const events = await getWorkspaceEvents(id);

			// Extract log entries from events
			const logEntries: { timestamp: string; text: string }[] = [];
			for (const ev of events) {
				if (ev.event_type === 'log_entry' && ev.metadata_json) {
					try {
						const meta = JSON.parse(ev.metadata_json);
						if (meta.text) logEntries.push({ timestamp: ev.timestamp, text: meta.text });
					} catch {}
				}
			}

			// Create session log if there's anything worth saving
			if (detail.items.length > 0 || logEntries.length > 0 || detail.description) {
				const { title, content } = buildSessionLog(detail, logEntries);
				const newLog = await createLog({ title, content });

				// Tag the log with the "Workspace" system tag
				await loadTags();
				const allTags = get(tags);
				const workspaceTag = allTags.find(t => t.name === 'Workspace' && t.category === 'log');
				if (workspaceTag) {
					await attachTag(workspaceTag.id, 'log', newLog.id);
				}

				// Tag the log with entity-linked tags for each workspace item
				for (const item of detail.items) {
					const entityTag = allTags.find(t => t.entity_type === item.entity_type && t.entity_id === item.entity_id);
					if (entityTag) {
						await attachTag(entityTag.id, 'log', newLog.id);
					}
				}

				await loadLogs();
				await loadTags();
			}

			// Delete the workspace
			await deleteWorkspace(id);
			await loadWorkspaces();
			const newOrder = syncTabOrder($workspaces);
			tabOrder = newOrder;
			saveTabOrder(newOrder);
			if (wasActive) {
				if (newOrder.length > 0) {
					await setActiveWorkspace(newOrder[0]);
				} else {
					activeWorkspace.set(null);
				}
			}
		} catch (err) {
			console.error('Failed to close workspace:', err);
		}
	}

	onMount(async () => {
		tabOrder = loadTabOrder();
		await loadWorkspaces();
		const newOrder = syncTabOrder($workspaces);
		tabOrder = newOrder;
		saveTabOrder(newOrder);
		if ($activeWorkspace === null && newOrder.length > 0) {
			await setActiveWorkspace(newOrder[0]);
		}
	});
</script>

<div class="workspace-tab">
	<div class="ws-subtabs">
		<div class="subtab-list">
			{#each orderedWorkspaces as ws, idx (ws.id)}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					class="subtab"
					class:active={$activeWorkspace?.id === ws.id}
					class:drag-over={dragOverIdx === idx && dragIdx !== idx}
					class:dragging={dragIdx === idx}
					draggable="true"
					onclick={() => setActiveWorkspace(ws.id)}
					ondragstart={(e) => handleDragStart(idx, e)}
					ondragover={(e) => handleDragOver(idx, e)}
					ondragleave={handleDragLeave}
					ondrop={(e) => handleDrop(idx, e)}
					ondragend={handleDragEnd}
					title={ws.name}
				>
					<span class="subtab-name">{ws.name}</span>
					<span class="subtab-count">{ws.items.length}</span>
					<button
						class="subtab-close"
						onclick={(e) => handleCloseTab(ws.id, e)}
						title="Delete workspace"
					>&times;</button>
				</div>
			{/each}
			{#if creating}
				<div class="subtab new-tab-input">
					<input
						class="new-ws-input"
						type="text"
						placeholder="Name..."
						bind:value={newName}
						onkeydown={handleNewKeydown}
						onblur={cancelCreate}
					/>
				</div>
			{:else}
				<button class="subtab add-tab" onclick={startCreate} title="New workspace">+</button>
			{/if}
		</div>
	</div>

	{#if $activeWorkspace !== null}
		<WorkspaceToolbar
			workspaceName={$activeWorkspace.name}
			workspaceDescription={$activeWorkspace.description}
			workspaceId={$activeWorkspace.id}
			{zoom}
			timelineOpen={showTimeline}
			{queryPanelOpen}
			{editorOpen}
			onZoomIn={() => graphComponent?.zoomIn()}
			onZoomOut={() => graphComponent?.zoomOut()}
			onZoomFit={() => graphComponent?.zoomFit()}
			onHierarchical={() => graphComponent?.hierarchicalLayout()}
			onQuadrant={() => graphComponent?.quadrantLayout()}
			onToggleTimeline={() => (showTimeline = !showTimeline)}
			onToggleQuery={() => graphComponent?.toggleQueryPanel()}
			onToggleEditor={() => graphComponent?.toggleEditor()}
			onAddEntity={(type) => graphComponent?.handleAddEntity(type)}
			onClear={() => graphComponent?.clearAll()}
			onScreenshot={() => graphComponent?.screenshot()}
			selectActive={selectModeOpen}
			onToggleSelect={() => (selectModeOpen = !selectModeOpen)}
		/>
		<div class="workspace-body">
			<WorkspaceGraph
				bind:this={graphComponent}
				bind:zoom
				bind:queryPanelOpen
				bind:editorOpen
				bind:selectMode={selectModeOpen}
			/>
			{#if showTimeline}
				<WorkspaceTimeline
					workspaceId={$activeWorkspace.id}
					onClose={() => (showTimeline = false)}
				/>
			{/if}
		</div>
	{:else if $workspaces.length === 0}
		<div class="empty-state">
			<p class="empty-title">No workspaces yet</p>
			<button class="empty-create-btn" onclick={startCreate}>Create workspace</button>
		</div>
	{/if}
</div>

<style>
	.workspace-tab {
		display: flex;
		flex-direction: column;
		height: calc(100vh - 120px);
		overflow: hidden;
	}
	.ws-subtabs {
		display: flex;
		align-items: stretch;
		background: #f3f4f6;
		border-bottom: 1px solid #e5e7eb;
		flex-shrink: 0;
		min-height: 34px;
	}
	.subtab-list {
		display: flex;
		align-items: stretch;
		overflow-x: auto;
		scrollbar-width: none;
		gap: 0;
	}
	.subtab-list::-webkit-scrollbar {
		display: none;
	}
	.subtab {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 6px 12px;
		border: none;
		border-right: 1px solid #e5e7eb;
		background: transparent;
		cursor: pointer;
		font-size: 0.75rem;
		color: #6b7280;
		white-space: nowrap;
		transition: background 0.15s, color 0.15s;
		position: relative;
	}
	.subtab:hover {
		background: #e5e7eb;
		color: #374151;
	}
	.subtab.active {
		background: white;
		color: #111827;
		font-weight: 600;
		box-shadow: inset 0 -2px 0 #374151;
	}
	.subtab.dragging {
		opacity: 0.4;
	}
	.subtab.drag-over {
		box-shadow: inset 2px 0 0 #3b82f6;
	}
	.subtab-name {
		max-width: 140px;
		overflow: hidden;
		text-overflow: ellipsis;
		pointer-events: none;
	}
	.subtab-count {
		font-size: 0.6rem;
		background: #e5e7eb;
		color: #6b7280;
		padding: 1px 5px;
		border-radius: 8px;
		font-weight: 500;
		pointer-events: none;
	}
	.subtab.active .subtab-count {
		background: #dbeafe;
		color: #3b82f6;
	}
	.subtab-close {
		display: none;
		width: 16px;
		height: 16px;
		border: none;
		background: transparent;
		color: #9ca3af;
		cursor: pointer;
		font-size: 0.85rem;
		border-radius: 3px;
		padding: 0;
		line-height: 1;
		align-items: center;
		justify-content: center;
	}
	.subtab:hover .subtab-close {
		display: flex;
	}
	.subtab-close:hover {
		background: #fee2e2;
		color: #dc2626;
	}
	.add-tab {
		padding: 6px 14px;
		border: none;
		border-right: none;
		background: transparent;
		cursor: pointer;
		font-size: 0.95rem;
		color: #9ca3af;
		font-weight: 300;
		transition: all 0.15s;
	}
	.add-tab:hover {
		background: #e5e7eb;
		color: #374151;
	}
	.new-tab-input {
		padding: 4px 6px;
		border-right: 1px solid #e5e7eb;
	}
	.new-ws-input {
		width: 120px;
		padding: 3px 6px;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		font-size: 0.75rem;
		outline: none;
	}
	.new-ws-input:focus {
		border-color: #6b7280;
	}
	.workspace-body {
		flex: 1;
		display: flex;
		min-height: 0;
		overflow: hidden;
	}
	.empty-state {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		color: #9ca3af;
		gap: 4px;
	}
	.empty-title {
		font-size: 1rem;
		font-weight: 500;
		margin: 0;
	}
	.empty-create-btn {
		padding: 8px 20px;
		border: 1px solid #d1d5db;
		border-radius: 8px;
		background: white;
		color: #374151;
		font-size: 0.85rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s;
	}
	.empty-create-btn:hover {
		background: #374151;
		color: white;
		border-color: #374151;
	}
</style>

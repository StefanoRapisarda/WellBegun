<script lang="ts">
	import { get } from 'svelte/store';
	import { notepadText } from '$lib/stores/notepad';
	import { parseNotepadText, serializeEntity } from '$lib/notepad/parser';
	import { saveAll } from '$lib/notepad/entityCreator';
	import { createTriple } from '$lib/api/knowledge';
	import { projects } from '$lib/stores/projects';
	import { logs } from '$lib/stores/logs';
	import { notes } from '$lib/stores/notes';
	import { activities } from '$lib/stores/activities';
	import { sources } from '$lib/stores/sources';
	import { actors } from '$lib/stores/actors';
	import { readingLists } from '$lib/stores/readingLists';
	import { plans } from '$lib/stores/plans';
	import { loadProjects } from '$lib/stores/projects';
	import { loadLogs } from '$lib/stores/logs';
	import { loadNotes } from '$lib/stores/notes';
	import { loadSources } from '$lib/stores/sources';
	import { loadActors } from '$lib/stores/actors';
	import { loadActivities } from '$lib/stores/activities';
	import { loadReadingLists } from '$lib/stores/readingLists';
	import { loadPlans } from '$lib/stores/plans';
	import { loadTags } from '$lib/stores/tags';
	import { getEntityTags } from '$lib/api/tags';
	import { entityToNotepadFields } from '$lib/notepad/utils';
	import { type NotepadEntityType } from '$lib/notepad/types';
	import type { StagedConnection } from '$lib/notepad/types';
	import type { SearchResult } from '$lib/api/search';
	import NotepadEditor from './NotepadEditor.svelte';
	import NotepadPreview from './NotepadPreview.svelte';
	import NotepadEditPanel from './NotepadEditPanel.svelte';
	import QueryPanel from '$lib/components/shared/QueryPanel.svelte';

	let entities = $derived(parseNotepadText($notepadText));
	let realEntityCount = $derived(entities.filter(e => !e.virtual).length);
	let saving = $state(false);
	let saveMessage = $state('');
	let editingIndex = $state<number | null>(null);
	let editingEntity = $derived(editingIndex !== null ? entities[editingIndex] : null);

	// ── Query panel ──
	let queryPanelOpen = $state(false);

	const storeMap: Record<string, any> = {
		project: projects,
		log: logs,
		note: notes,
		activity: activities,
		source: sources,
		actor: actors,
		reading_list: readingLists,
		plan: plans,
	};

	async function handleQueryResult(result: SearchResult) {
		const store = storeMap[result.type];
		if (!store) return;
		const items = get(store) as any[];
		const entity = items.find((item: any) => item.id === result.id);
		if (!entity) return;

		const fields = entityToNotepadFields(result.type, entity);

		const tags = await getEntityTags(result.type, result.id);
		if (tags.length > 0) {
			fields.tags = tags.map(t => t.name).join(', ');
		}

		const block = serializeEntity(result.type as NotepadEntityType, fields, undefined, result.id);
		const current = $notepadText;
		notepadText.set(current.trim() ? current.trimEnd() + '\n\n' + block : block);
	}

	// ── Card positions (auto-layout new cards in a grid) ──
	let cardPositions = $state<Record<number, { x: number; y: number }>>({});
	let prevEntityCount = $state(0);

	$effect(() => {
		const count = entities.length;
		if (count > prevEntityCount) {
			// Auto-layout new entities in a grid
			const cols = 3;
			const gapX = 180;
			const gapY = 90;
			const startX = 30;
			const startY = 30;
			const updated = { ...cardPositions };
			for (let i = prevEntityCount; i < count; i++) {
				if (!updated[i]) {
					const col = i % cols;
					const row = Math.floor(i / cols);
					updated[i] = { x: startX + col * gapX, y: startY + row * gapY };
				}
			}
			cardPositions = updated;
		} else if (count < prevEntityCount) {
			// Entity removed — clean up stale positions and re-index
			const updated: Record<number, { x: number; y: number }> = {};
			for (let i = 0; i < count; i++) {
				updated[i] = cardPositions[i] ?? { x: 30 + (i % 3) * 180, y: 30 + Math.floor(i / 3) * 90 };
			}
			cardPositions = updated;
			// Clean up connections referencing removed indices
			stagedConnections = stagedConnections.filter(
				c => c.sourceIndex < count && c.targetIndex < count
			);
		}
		prevEntityCount = count;
	});

	// ── Staged connections ──
	let stagedConnections = $state<StagedConnection[]>([]);

	// ── Card handlers ──
	function handleCardMove(index: number, x: number, y: number) {
		cardPositions = { ...cardPositions, [index]: { x, y } };
	}

	function handleCardClick(index: number) {
		if (!entities[index]) return;
		editingIndex = index;
	}

	function handleCardConnect(sourceIndex: number, targetIndex: number) {
		// Don't duplicate existing connections
		const exists = stagedConnections.some(
			c => (c.sourceIndex === sourceIndex && c.targetIndex === targetIndex) ||
				 (c.sourceIndex === targetIndex && c.targetIndex === sourceIndex)
		);
		if (!exists) {
			stagedConnections = [...stagedConnections, { sourceIndex, targetIndex, predicate: 'related_to' }];
		}
	}

	function handleCardDelete(index: number) {
		const entity = entities[index];
		if (!entity) return;

		if (entity.virtual) {
			// Virtual entity (plan item) — remove it from the parent plan
			const planIndex = entities.findIndex(e => !e.virtual && e.type === 'plan' && e.startLine === entity.startLine);
			if (planIndex < 0) return;
			const plan = entities[planIndex];
			const itemIdx = index - planIndex - 1;
			const updatedItems = (plan.items ?? []).filter((_, i) => i !== itemIdx);
			const newBlock = serializeEntity(plan.type, plan.fields, updatedItems, plan.dbId);
			const lines = $notepadText.split('\n');
			const before = lines.slice(0, plan.startLine);
			const after = lines.slice(plan.endLine);
			notepadText.set([...before, newBlock, ...after].join('\n'));
			return;
		}

		const lines = $notepadText.split('\n');
		const before = lines.slice(0, entity.startLine);
		const after = lines.slice(entity.endLine);
		notepadText.set([...before, ...after].join('\n'));
	}

	// ── Connection handlers ──
	function handleConnectionSwap(connIndex: number) {
		const conn = stagedConnections[connIndex];
		if (!conn) return;
		const updated = [...stagedConnections];
		updated[connIndex] = { ...conn, sourceIndex: conn.targetIndex, targetIndex: conn.sourceIndex };
		stagedConnections = updated;
	}

	function handleConnectionDelete(connIndex: number) {
		stagedConnections = stagedConnections.filter((_, i) => i !== connIndex);
	}

	function handlePredicateSelect(connIndex: number, predicate: string) {
		const conn = stagedConnections[connIndex];
		if (!conn) return;
		const updated = [...stagedConnections];
		updated[connIndex] = { ...conn, predicate };
		stagedConnections = updated;
	}

	// ── Edit panel ──
	function handleEditClose() {
		editingIndex = null;
	}

	function handleEditSave(updatedFields: Record<string, string>, items?: Array<{ title: string; is_done: boolean }>) {
		if (editingIndex === null || !editingEntity) return;

		const entity = editingEntity;

		if (entity.virtual) {
			// Find the parent plan and update the specific item
			const planIndex = entities.findIndex(e => !e.virtual && e.type === 'plan' && e.startLine === entity.startLine);
			if (planIndex < 0) { editingIndex = null; return; }
			const plan = entities[planIndex];
			// Determine which item this virtual entity corresponds to (offset from plan)
			const itemIdx = editingIndex - planIndex - 1;
			const updatedItems = (plan.items ?? []).map((item, i) =>
				i === itemIdx ? { ...item, title: updatedFields.title ?? item.title } : item
			);
			const newBlock = serializeEntity(plan.type, plan.fields, updatedItems, plan.dbId);
			const lines = $notepadText.split('\n');
			const before = lines.slice(0, plan.startLine);
			const after = lines.slice(plan.endLine);
			notepadText.set([...before, newBlock, ...after].join('\n'));
			editingIndex = null;
			return;
		}

		const newBlock = serializeEntity(entity.type, updatedFields, items, entity.dbId);

		const lines = $notepadText.split('\n');
		const before = lines.slice(0, entity.startLine);
		const after = lines.slice(entity.endLine);
		const rebuilt = [...before, newBlock, ...after].join('\n');

		notepadText.set(rebuilt);
		editingIndex = null;
	}

	// ── Save ──
	async function handleSave() {
		if (entities.length === 0 || saving) return;
		saving = true;
		saveMessage = '';
		try {
			const realEntities = entities.filter(e => !e.virtual);

			// 1. Save all entities (create new, update existing)
			const results = await saveAll(entities);

			// 2. Save staged connections as triples using real entity IDs
			let triplesCreated = 0;
			for (const conn of stagedConnections) {
				const source = results[conn.sourceIndex];
				const target = results[conn.targetIndex];
				if (source && target) {
					await createTriple({
						subject_type: source.entityType,
						subject_id: source.entityId,
						predicate: conn.predicate,
						object_type: target.entityType,
						object_id: target.entityId
					});
					triplesCreated++;
				}
			}

			// 3. Update text to embed new IDs for freshly created entities
			let lines = $notepadText.split('\n');
			for (let i = 0; i < realEntities.length; i++) {
				const entity = realEntities[i];
				if (entity.dbId == null && results[i]) {
					const newId = results[i].entityId;
					lines[entity.startLine] = lines[entity.startLine]
						.replace(/^(\s*)@(\w+)/, `$1@$2#${newId}`);
				}
			}
			notepadText.set(lines.join('\n'));

			// 4. Clear staged connections (now saved as real triples)
			stagedConnections = [];

			// 5. Build status message
			const created = realEntities.filter(e => e.dbId == null).length;
			const updated = realEntities.filter(e => e.dbId != null).length;
			const parts: string[] = [];
			if (created > 0) parts.push(`${created} created`);
			if (updated > 0) parts.push(`${updated} updated`);
			if (triplesCreated > 0) parts.push(`${triplesCreated} connection${triplesCreated === 1 ? '' : 's'}`);
			saveMessage = `Saved: ${parts.join(', ')}`;

			await Promise.allSettled([
				loadProjects(),
				loadLogs(),
				loadNotes(),
				loadSources(),
				loadActors(),
				loadActivities(),
				loadReadingLists(),
				loadPlans(),
				loadTags()
			]);
		} catch (e) {
			saveMessage = `Error: ${e instanceof Error ? e.message : 'save failed'}`;
		} finally {
			saving = false;
			setTimeout(() => { saveMessage = ''; }, 3000);
		}
	}

	function handleClear() {
		if (!$notepadText.trim()) return;
		if (confirm('Clear all notepad text?')) {
			notepadText.set('');
			stagedConnections = [];
			cardPositions = {};
			prevEntityCount = 0;
		}
	}
</script>

<div class="notepad-tab">
	<div class="notepad-content">
		<div class="split-view">
			<NotepadEditor />
			<NotepadPreview
				{entities}
				positions={cardPositions}
				connections={stagedConnections}
				onCardMove={handleCardMove}
				onCardClick={handleCardClick}
				onCardConnect={handleCardConnect}
				onCardDelete={handleCardDelete}
				onConnectionSwap={handleConnectionSwap}
				onConnectionDelete={handleConnectionDelete}
				onPredicateSelect={handlePredicateSelect}
			/>
		</div>
		<QueryPanel
			open={queryPanelOpen}
			onResultClick={handleQueryResult}
			resultActionLabel="Insert"
		/>
	</div>
	<div class="bottom-toolbar">
		<span class="entity-count">
			{realEntityCount} entit{realEntityCount === 1 ? 'y' : 'ies'}
		</span>
		{#if stagedConnections.length > 0}
			<span class="conn-count">
				{stagedConnections.length} connection{stagedConnections.length === 1 ? '' : 's'}
			</span>
		{/if}
		{#if saveMessage}
			<span class="save-message" class:error={saveMessage.startsWith('Error')}>{saveMessage}</span>
		{/if}
		<div class="toolbar-actions">
			<button class="btn btn-query" class:active={queryPanelOpen} onclick={() => queryPanelOpen = !queryPanelOpen}>Search</button>
			<button class="btn btn-clear" onclick={handleClear} disabled={!$notepadText.trim()}>Clear</button>
			<button class="btn btn-save" onclick={handleSave} disabled={realEntityCount === 0 || saving}>
				{saving ? 'Saving...' : 'Save'}
			</button>
		</div>
	</div>
</div>

{#if editingEntity}
	{#key editingIndex}
		<NotepadEditPanel
			entity={editingEntity}
			onSave={handleEditSave}
			onClose={handleEditClose}
		/>
	{/key}
{/if}

<style>
	.notepad-tab {
		display: flex;
		flex-direction: column;
		height: calc(100vh - 120px);
	}
	.notepad-content {
		flex: 1;
		position: relative;
		display: flex;
		min-height: 0;
	}
	.split-view {
		flex: 1;
		display: flex;
		min-height: 0;
	}
	.bottom-toolbar {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 8px 16px;
		background: white;
		border-top: 1px solid #e5e7eb;
	}
	.entity-count {
		font-size: 0.75rem;
		color: #6b7280;
		background: #f3f4f6;
		padding: 3px 10px;
		border-radius: 10px;
		font-weight: 500;
	}
	.conn-count {
		font-size: 0.75rem;
		color: #3b82f6;
		background: #eff6ff;
		padding: 3px 10px;
		border-radius: 10px;
		font-weight: 500;
	}
	.save-message {
		font-size: 0.72rem;
		color: #059669;
		font-weight: 500;
	}
	.save-message.error {
		color: #dc2626;
	}
	.toolbar-actions {
		margin-left: auto;
		display: flex;
		gap: 8px;
	}
	.btn {
		padding: 5px 14px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 0.75rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s;
	}
	.btn:disabled {
		opacity: 0.4;
		cursor: default;
	}
	.btn-clear {
		background: white;
		color: #6b7280;
	}
	.btn-clear:hover:not(:disabled) {
		background: #f9fafb;
		border-color: #9ca3af;
	}
	.btn-save {
		background: #111827;
		color: white;
		border-color: #111827;
	}
	.btn-query {
		background: white;
		color: #6b7280;
	}
	.btn-query:hover:not(:disabled) {
		background: #f9fafb;
		border-color: #9ca3af;
	}
	.btn-query.active {
		background: #374151;
		color: white;
		border-color: #374151;
	}
	.btn-save:hover:not(:disabled) {
		background: #1f2937;
	}
</style>

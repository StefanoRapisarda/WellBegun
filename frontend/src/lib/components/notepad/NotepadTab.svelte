<script lang="ts">
	import { get } from 'svelte/store';
	import { notepadText, cardLayout } from '$lib/stores/notepad';
	import { parseNotepadText, serializeEntity } from '$lib/notepad/parser';
	import { saveAll } from '$lib/notepad/entityCreator';
	import { createTriple, getTriplesForEntity } from '$lib/api/knowledge';
	import type { KnowledgeTriple } from '$lib/types';
	import { projects } from '$lib/stores/projects';
	import { logs } from '$lib/stores/logs';
	import { notes } from '$lib/stores/notes';
	import { activities } from '$lib/stores/activities';
	import { sources } from '$lib/stores/sources';
	import { actors } from '$lib/stores/actors';
	import { plans } from '$lib/stores/plans';
	import { collections } from '$lib/stores/collections';
	import { loadProjects } from '$lib/stores/projects';
	import { loadLogs } from '$lib/stores/logs';
	import { loadNotes } from '$lib/stores/notes';
	import { loadSources } from '$lib/stores/sources';
	import { loadActors } from '$lib/stores/actors';
	import { loadActivities } from '$lib/stores/activities';
	import { loadPlans } from '$lib/stores/plans';
	import { loadCollections } from '$lib/stores/collections';
	import { loadTriples } from '$lib/stores/knowledgeGraph';
	import { loadTags } from '$lib/stores/tags';
	import { getEntityTags } from '$lib/api/tags';
	import { entityToNotepadFields } from '$lib/notepad/utils';
	import { ENTITY_CONFIG, type NotepadEntityType, type ParsedEntity } from '$lib/notepad/types';
	import type { StagedConnection } from '$lib/notepad/types';
	import type { SearchResult } from '$lib/api/search';
	import { pendingNotepadEntity } from '$lib/stores/pendingNotepadEntity';
	import { containerWidth as ccWidth, containerHeight as ccHeight } from '$lib/components/graph/collectionLayout';
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
		plan: plans,
		collection: collections,
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

	// ── Pending entity from external navigation ──
	$effect(() => {
		const pending = $pendingNotepadEntity;
		if (pending) {
			pendingNotepadEntity.set(null);
			handleQueryResult({ type: pending.type, id: pending.id, title: '', score: 0 });
		}
	});

	// ── Card layout (persisted positions + sizes) ──
	const SLOT_W = 180;
	const SLOT_H = 90;
	const START_X = 30;
	const START_Y = 30;

	let cardPositions = $derived($cardLayout.positions);
	let cardSizes = $derived($cardLayout.sizes);
	let prevEntityCount = $state(0);

	// Build collection container map from current entities
	function getCollectionInfo(ents: ParsedEntity[]): { containers: Map<number, number[]>; children: Set<number> } {
		const containers = new Map<number, number[]>();
		for (let i = 0; i < ents.length; i++) {
			if (ents[i].type === 'collection') containers.set(i, []);
		}
		for (let i = 0; i < ents.length; i++) {
			const e = ents[i];
			if (e.parentIndex != null && containers.has(e.parentIndex)) {
				containers.get(e.parentIndex)!.push(i);
			}
		}
		const children = new Set<number>();
		for (const kids of containers.values()) {
			for (const idx of kids) children.add(idx);
		}
		return { containers, children };
	}

	const CARD_GAP = 12;

	$effect(() => {
		const count = entities.length;
		if (count !== prevEntityCount) {
			const { containers, children } = getCollectionInfo(entities);

			// Collect indices that need a position: standalone cards + collection containers (not children)
			const toPlace: number[] = [];
			for (let i = 0; i < count; i++) {
				if (!children.has(i)) toPlace.push(i);
			}

			// Flow layout: place items left-to-right, wrapping rows based on actual dimensions
			const MAX_ROW_WIDTH = 600;
			let cursorX = START_X;
			let cursorY = START_Y;
			let rowMaxH = 0;

			const updatedPos = { ...$cardLayout.positions };
			const updatedSizes = { ...$cardLayout.sizes };

			for (const i of toPlace) {
				const isContainer = containers.has(i);
				const w = isContainer ? ccWidth() : SLOT_W;
				const h = isContainer ? ccHeight(containers.get(i)!.length, false) + CARD_GAP : SLOT_H;

				// Wrap to next row if this entity would exceed the row width
				if (cursorX > START_X && cursorX + w > START_X + MAX_ROW_WIDTH) {
					cursorX = START_X;
					cursorY += rowMaxH;
					rowMaxH = 0;
				}

				if (!updatedPos[i]) {
					updatedPos[i] = { x: cursorX, y: cursorY };
				}
				if (!updatedSizes[i]) {
					updatedSizes[i] = { colSpan: 1, rowSpan: 1 };
				}

				cursorX += w + CARD_GAP;
				rowMaxH = Math.max(rowMaxH, h);
			}

			// Children inside collections don't need meaningful positions
			for (const idx of children) {
				if (!updatedPos[idx]) updatedPos[idx] = { x: 0, y: 0 };
				if (!updatedSizes[idx]) updatedSizes[idx] = { colSpan: 1, rowSpan: 1 };
			}

			// Clean up positions for removed entities
			if (count < prevEntityCount) {
				const cleanedPos: Record<number, { x: number; y: number }> = {};
				const cleanedSizes: Record<number, { colSpan: number; rowSpan: number }> = {};
				for (let i = 0; i < count; i++) {
					cleanedPos[i] = updatedPos[i] ?? { x: START_X, y: START_Y };
					cleanedSizes[i] = updatedSizes[i] ?? { colSpan: 1, rowSpan: 1 };
				}
				cardLayout.set({ positions: cleanedPos, sizes: cleanedSizes });
				stagedConnections = stagedConnections.filter(
					c => c.sourceIndex < count && c.targetIndex < count
				);
			} else {
				cardLayout.set({ positions: updatedPos, sizes: updatedSizes });
			}
		}
		prevEntityCount = count;
	});

	// ── Staged connections ──
	let stagedConnections = $state<StagedConnection[]>([]);

	// Derive the predicate for a parent→child connection
	function deriveConnectionPredicate(parent: ParsedEntity, child: ParsedEntity): string {
		// Plan sub-section children get "has <section>" predicates
		if (child.subSection && parent.type === 'plan') {
			return `has ${child.subSection}`;
		}
		return 'contains';
	}

	// Implicit connections: parent entities → their virtual children
	let implicitConnections = $derived.by(() => {
		const conns: StagedConnection[] = [];
		for (let i = 0; i < entities.length; i++) {
			const entity = entities[i];

			// parentIndex-based connections (from plan sub-sections, collections)
			if (entity.virtual && entity.parentIndex != null) {
				const parent = entities[entity.parentIndex];
				const predicate = parent ? deriveConnectionPredicate(parent, entity) : 'contains';
				conns.push({ sourceIndex: entity.parentIndex, targetIndex: i, predicate });
				continue;
			}

			// Fallback: startLine-based connections for legacy/non-parentIndex entities
			if (!entity.items || entity.items.length === 0 || entity.virtual) continue;
			for (let j = 0; j < entities.length; j++) {
				if (i === j || !entities[j].virtual) continue;
				if (entities[j].parentIndex != null) continue; // Already handled above
				if (entities[j].startLine === entity.startLine) {
					conns.push({ sourceIndex: i, targetIndex: j, predicate: 'contains' });
				}
			}
		}
		return conns;
	});

	// ── Knowledge-graph connections for entities with dbId ──
	let knowledgeTriples = $state<KnowledgeTriple[]>([]);
	let prevDbIdKey = '';

	$effect(() => {
		const dbEntities = entities.filter(e => e.dbId != null);
		const key = dbEntities.map(e => `${e.type}:${e.dbId}`).sort().join(',');
		if (key === prevDbIdKey) return;
		prevDbIdKey = key;

		if (dbEntities.length === 0) {
			knowledgeTriples = [];
			return;
		}

		Promise.all(
			dbEntities.map(e => getTriplesForEntity(e.type, e.dbId!))
		).then(results => {
			knowledgeTriples = results.flat();
		});
	});

	let knowledgeConnections = $derived.by(() => {
		if (knowledgeTriples.length === 0) return [];

		// Map "type:dbId" → entity index
		const entityMap = new Map<string, number>();
		for (let i = 0; i < entities.length; i++) {
			if (entities[i].dbId != null) {
				entityMap.set(`${entities[i].type}:${entities[i].dbId}`, i);
			}
		}

		const conns: StagedConnection[] = [];
		const seen = new Set<string>();
		for (const triple of knowledgeTriples) {
			const srcIdx = entityMap.get(`${triple.subject_type}:${triple.subject_id}`);
			const tgtIdx = entityMap.get(`${triple.object_type}:${triple.object_id}`);
			if (srcIdx != null && tgtIdx != null) {
				const connKey = `${srcIdx}:${tgtIdx}`;
				if (!seen.has(connKey)) {
					seen.add(connKey);
					conns.push({ sourceIndex: srcIdx, targetIndex: tgtIdx, predicate: triple.predicate });
				}
			}
		}
		return conns;
	});

	let allConnections = $derived([...implicitConnections, ...knowledgeConnections, ...stagedConnections]);

	// ── Card handlers ──
	function handleCardMove(index: number, x: number, y: number) {
		cardLayout.update(l => ({
			...l,
			positions: { ...l.positions, [index]: { x, y } }
		}));
	}

	function handleCardResize(index: number, colSpan: number, rowSpan: number) {
		cardLayout.update(l => ({
			...l,
			sizes: { ...l.sizes, [index]: { colSpan, rowSpan } }
		}));
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
			// Traverse parentIndex chain to find the root non-virtual entity
			let rootIndex = index;
			while (entities[rootIndex]?.virtual && entities[rootIndex]?.parentIndex != null) {
				rootIndex = entities[rootIndex].parentIndex!;
			}
			// If root is still virtual (no parentIndex), fall back to startLine match
			if (entities[rootIndex]?.virtual) {
				rootIndex = entities.findIndex(e => !e.virtual && e.startLine === entity.startLine);
			}
			if (rootIndex < 0) return;
			const root = entities[rootIndex];

			// Virtual collection: remove all items belonging to that sub-section
			if (entity.type === 'collection' && entity.parentIndex != null) {
				const childSubSections = new Set(
					entities
						.filter(e => e.virtual && e.parentIndex === index)
						.map(e => (root.items ?? []).find(it =>
							(it.fields?.[ENTITY_CONFIG[e.type].primaryField] ?? it.title) ===
							e.fields[ENTITY_CONFIG[e.type].primaryField]
						)?.subSection)
						.filter(Boolean)
				);
				const updatedItems = (root.items ?? []).filter(it => !childSubSections.has(it.subSection));
				const newBlock = serializeEntity(root.type, root.fields, updatedItems, root.dbId);
				const lines = $notepadText.split('\n');
				const before = lines.slice(0, root.startLine);
				const after = lines.slice(root.endLine);
				notepadText.set([...before, newBlock, ...after].join('\n'));
				return;
			}

			// Virtual leaf entity: match by primary field value
			const primaryField = ENTITY_CONFIG[entity.type].primaryField;
			const entityPrimary = entity.fields[primaryField];
			const itemIdx = (root.items ?? []).findIndex(item => {
				const itemPrimary = item.fields?.[primaryField] ?? item.title;
				return itemPrimary === entityPrimary;
			});
			if (itemIdx < 0) return;
			const updatedItems = (root.items ?? []).filter((_, i) => i !== itemIdx);
			const newBlock = serializeEntity(root.type, root.fields, updatedItems, root.dbId);
			const lines = $notepadText.split('\n');
			const before = lines.slice(0, root.startLine);
			const after = lines.slice(root.endLine);
			notepadText.set([...before, newBlock, ...after].join('\n'));
			return;
		}

		if (entity.fromListBlock && entity.listBlockHeaderLine != null) {
			const lines = $notepadText.split('\n');
			// Remove the item's line
			lines.splice(entity.startLine, 1);
			// Check if any other items remain in this list block
			const headerLine = entity.listBlockHeaderLine;
			const siblingsRemain = entities.some(
				e => e !== entity && e.fromListBlock && e.listBlockHeaderLine === headerLine
			);
			if (!siblingsRemain) {
				// Remove the header line too (index may have shifted by 1 if item was after header)
				const headerIdx = entity.startLine > headerLine ? headerLine : headerLine - 1;
				lines.splice(headerIdx, 1);
			}
			notepadText.set(lines.join('\n'));
			return;
		}

		const lines = $notepadText.split('\n');
		const before = lines.slice(0, entity.startLine);
		const after = lines.slice(entity.endLine);
		notepadText.set([...before, ...after].join('\n'));
	}

	// ── Connection handlers ──
	// allConnections = [...implicitConnections, ...stagedConnections]
	// so staged index = connIndex - implicitConnections.length
	function toStagedIndex(connIndex: number): number | null {
		const offset = connIndex - implicitConnections.length;
		return offset >= 0 && offset < stagedConnections.length ? offset : null;
	}

	function handleConnectionSwap(connIndex: number) {
		const si = toStagedIndex(connIndex);
		if (si === null) return; // implicit connections can't be swapped
		const conn = stagedConnections[si];
		if (!conn) return;
		const updated = [...stagedConnections];
		updated[si] = { ...conn, sourceIndex: conn.targetIndex, targetIndex: conn.sourceIndex };
		stagedConnections = updated;
	}

	function handleConnectionDelete(connIndex: number) {
		const si = toStagedIndex(connIndex);
		if (si === null) return; // implicit connections can't be deleted
		stagedConnections = stagedConnections.filter((_, i) => i !== si);
	}

	function handlePredicateSelect(connIndex: number, predicate: string) {
		const si = toStagedIndex(connIndex);
		if (si === null) return; // implicit connections can't be edited
		const conn = stagedConnections[si];
		if (!conn) return;
		const updated = [...stagedConnections];
		updated[si] = { ...conn, predicate };
		stagedConnections = updated;
	}

	// ── Edit panel ──
	function handleEditClose() {
		editingIndex = null;
	}

	function handleEditSave(updatedFields: Record<string, string>, items?: Array<{ title: string; is_done: boolean; header?: string | null }>) {
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

		if (entity.fromListBlock && entity.listBlockHeaderLine != null) {
			const config = ENTITY_CONFIG[entity.type];
			const primaryField = config.primaryField;
			const newPrimary = updatedFields[primaryField] ?? '';

			// Check if only the primary field was set (no extra fields added)
			const hasExtraFields = Object.keys(updatedFields).some(
				k => k !== primaryField && updatedFields[k]?.trim()
			);

			const lines = $notepadText.split('\n');

			if (!hasExtraFields) {
				// Update in-place within the @@ block
				lines[entity.startLine] = newPrimary;
				notepadText.set(lines.join('\n'));
			} else {
				// Promote: remove from list, serialize as standalone block
				lines.splice(entity.startLine, 1);

				// Check if the list block is now empty
				const headerLine = entity.listBlockHeaderLine;
				const siblingsRemain = entities.some(
					e => e !== entity && e.fromListBlock && e.listBlockHeaderLine === headerLine
				);

				// Find where to insert the promoted block (after the @@ block)
				// Gather all sibling line indices to find the end of the @@ block
				let insertAfterLine: number;
				if (siblingsRemain) {
					const siblingLines = entities
						.filter(e => e !== entity && e.fromListBlock && e.listBlockHeaderLine === headerLine)
						.map(e => e.startLine);
					// After removing the item line, sibling lines after it shifted by -1
					insertAfterLine = Math.max(...siblingLines.map(l => l > entity.startLine ? l - 1 : l));
				} else {
					// List is now empty — remove header too
					const headerIdx = entity.startLine > headerLine ? headerLine : headerLine - 1;
					lines.splice(headerIdx, 1);
					insertAfterLine = headerIdx - 1;
				}

				const standaloneBlock = serializeEntity(entity.type, updatedFields, items, entity.dbId);
				lines.splice(insertAfterLine + 1, 0, '', standaloneBlock);
				notepadText.set(lines.join('\n'));
			}

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
					if (!entity.fromListBlock) {
						lines[entity.startLine] = lines[entity.startLine]
							.replace(/^(\s*)@(\w+)/, `$1@$2#${newId}`);
					}
				}
			}

			// 3b. Expand @@ list blocks into individual @type#id Name blocks
			// Group fromListBlock entities by their listBlockHeaderLine
			const listGroups = new Map<number, Array<{ entity: ParsedEntity; resultIndex: number }>>();
			for (let i = 0; i < realEntities.length; i++) {
				const entity = realEntities[i];
				if (entity.fromListBlock && entity.listBlockHeaderLine != null) {
					if (!listGroups.has(entity.listBlockHeaderLine)) {
						listGroups.set(entity.listBlockHeaderLine, []);
					}
					listGroups.get(entity.listBlockHeaderLine)!.push({ entity, resultIndex: i });
				}
			}

			// Process groups in reverse line order to preserve indices during splicing
			const sortedHeaders = [...listGroups.keys()].sort((a, b) => b - a);
			for (const headerLine of sortedHeaders) {
				const group = listGroups.get(headerLine)!;
				// Find the range: from header line to last item line
				const lastItemLine = Math.max(...group.map(g => g.entity.startLine));
				const blockLength = lastItemLine - headerLine + 1;

				// Build expanded blocks
				const expandedLines: string[] = [];
				for (let j = 0; j < group.length; j++) {
					const { entity, resultIndex } = group[j];
					const config = ENTITY_CONFIG[entity.type];
					const primaryValue = entity.fields[config.primaryField] ?? '';
					const newId = results[resultIndex]?.entityId;
					const idSuffix = newId != null ? `#${newId}` : (entity.dbId != null ? `#${entity.dbId}` : '');
					expandedLines.push(`@${entity.type}${idSuffix} ${primaryValue}`);
					if (j < group.length - 1) {
						expandedLines.push('');
					}
				}

				// Replace the @@ block with expanded lines
				lines.splice(headerLine, blockLength, ...expandedLines);
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
				loadPlans(),
				loadCollections(),
				loadTags(),
				loadTriples()
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
			cardLayout.set({ positions: {}, sizes: {} });
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
				sizes={cardSizes}
				connections={allConnections}
				onCardMove={handleCardMove}
				onCardClick={handleCardClick}
				onCardConnect={handleCardConnect}
				onCardDelete={handleCardDelete}
				onCardResize={handleCardResize}
				onConnectionSwap={handleConnectionSwap}
				onConnectionDelete={handleConnectionDelete}
				onPredicateSelect={handlePredicateSelect}
			/>
		</div>
		<QueryPanel
			open={queryPanelOpen}
			onClose={() => queryPanelOpen = false}
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

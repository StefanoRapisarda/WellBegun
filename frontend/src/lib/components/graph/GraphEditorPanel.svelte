<script lang="ts">
	import { notepadText } from '$lib/stores/notepad';
	import { parseNotepadText, serializeEntity } from '$lib/notepad/parser';
	import { saveAll } from '$lib/notepad/entityCreator';
	import { createTriple } from '$lib/api/knowledge';
	import { ENTITY_CONFIG, type ParsedEntity, type StagedConnection } from '$lib/notepad/types';
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
	import { containerWidth as ccWidth, containerHeight as ccHeight } from '$lib/components/graph/collectionLayout';
	import NotepadEditor from '$lib/components/notepad/NotepadEditor.svelte';
	import NotepadPreview from '$lib/components/notepad/NotepadPreview.svelte';

	let {
		open,
		onClose,
		onCommit
	}: {
		open: boolean;
		onClose?: () => void;
		onCommit: (results: Array<{ entityType: string; entityId: number }>) => void;
	} = $props();

	// ── Parsed entities from shared notepad text ──
	let entities = $derived(parseNotepadText($notepadText));
	let realEntityCount = $derived(entities.filter(e => !e.virtual).length);

	// ── Save state ──
	let saving = $state(false);
	let saveMessage = $state('');

	// ── Local card layout (NOT shared cardLayout store) ──
	const SLOT_W = 180;
	const SLOT_H = 90;
	const START_X = 30;
	const START_Y = 30;

	let cardPositions = $state<Record<number, { x: number; y: number }>>({});
	let cardSizes = $state<Record<number, { colSpan: number; rowSpan: number }>>({});
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

	// Get the actual pixel dimensions for an entity
	function entityWidth(index: number, containers: Map<number, number[]>): number {
		return containers.has(index) ? ccWidth() : SLOT_W;
	}

	function entityHeight(index: number, containers: Map<number, number[]>): number {
		if (containers.has(index)) {
			return ccHeight(containers.get(index)!.length, false) + CARD_GAP;
		}
		return SLOT_H;
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

			const updatedPos = { ...cardPositions };
			const updatedSizes = { ...cardSizes };

			for (const i of toPlace) {
				const w = entityWidth(i, containers);
				const h = entityHeight(i, containers);

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

			// Children inside collections don't need meaningful positions (rendered inside container)
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
				cardPositions = cleanedPos;
				cardSizes = cleanedSizes;
				stagedConnections = stagedConnections.filter(
					c => c.sourceIndex < count && c.targetIndex < count
				);
			} else {
				cardPositions = updatedPos;
				cardSizes = updatedSizes;
			}
		}
		prevEntityCount = count;
	});

	// ── Staged connections ──
	let stagedConnections = $state<StagedConnection[]>([]);

	// Implicit connections: parent entities → their virtual children
	let implicitConnections = $derived.by(() => {
		const conns: StagedConnection[] = [];
		for (let i = 0; i < entities.length; i++) {
			const entity = entities[i];
			if (entity.virtual && entity.parentIndex != null) {
				const parent = entities[entity.parentIndex];
				const predicate = parent && entity.subSection && parent.type === 'plan'
					? `has ${entity.subSection}`
					: 'contains';
				conns.push({ sourceIndex: entity.parentIndex, targetIndex: i, predicate });
				continue;
			}
			if (!entity.items || entity.items.length === 0 || entity.virtual) continue;
			for (let j = 0; j < entities.length; j++) {
				if (i === j || !entities[j].virtual) continue;
				if (entities[j].parentIndex != null) continue;
				if (entities[j].startLine === entity.startLine) {
					conns.push({ sourceIndex: i, targetIndex: j, predicate: 'contains' });
				}
			}
		}
		return conns;
	});

	let allConnections = $derived([...implicitConnections, ...stagedConnections]);

	// ── Card handlers ──
	function handleCardMove(index: number, x: number, y: number) {
		cardPositions = { ...cardPositions, [index]: { x, y } };
	}

	function handleCardResize(index: number, colSpan: number, rowSpan: number) {
		cardSizes = { ...cardSizes, [index]: { colSpan, rowSpan } };
	}

	function handleCardConnect(sourceIndex: number, targetIndex: number) {
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
			let rootIndex = index;
			while (entities[rootIndex]?.virtual && entities[rootIndex]?.parentIndex != null) {
				rootIndex = entities[rootIndex].parentIndex!;
			}
			if (entities[rootIndex]?.virtual) {
				rootIndex = entities.findIndex(e => !e.virtual && e.startLine === entity.startLine);
			}
			if (rootIndex < 0) return;
			const root = entities[rootIndex];
			const primaryField = ENTITY_CONFIG[entity.type].primaryField;
			const entityPrimary = entity.fields[primaryField];
			const updatedItems = (root.items ?? []).filter(item => {
				const itemPrimary = item.fields?.[primaryField] ?? item.title;
				return itemPrimary !== entityPrimary;
			});
			const newBlock = serializeEntity(root.type, root.fields, updatedItems, root.dbId);
			const lines = $notepadText.split('\n');
			const before = lines.slice(0, root.startLine);
			const after = lines.slice(root.endLine);
			notepadText.set([...before, newBlock, ...after].join('\n'));
			return;
		}

		if (entity.fromListBlock && entity.listBlockHeaderLine != null) {
			const lines = $notepadText.split('\n');
			lines.splice(entity.startLine, 1);
			const headerLine = entity.listBlockHeaderLine;
			const siblingsRemain = entities.some(
				e => e !== entity && e.fromListBlock && e.listBlockHeaderLine === headerLine
			);
			if (!siblingsRemain) {
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
	function toStagedIndex(connIndex: number): number | null {
		const offset = connIndex - implicitConnections.length;
		return offset >= 0 && offset < stagedConnections.length ? offset : null;
	}

	function handleConnectionSwap(connIndex: number) {
		const si = toStagedIndex(connIndex);
		if (si === null) return;
		const conn = stagedConnections[si];
		if (!conn) return;
		const updated = [...stagedConnections];
		updated[si] = { ...conn, sourceIndex: conn.targetIndex, targetIndex: conn.sourceIndex };
		stagedConnections = updated;
	}

	function handleConnectionDelete(connIndex: number) {
		const si = toStagedIndex(connIndex);
		if (si === null) return;
		stagedConnections = stagedConnections.filter((_, i) => i !== si);
	}

	function handlePredicateSelect(connIndex: number, predicate: string) {
		const si = toStagedIndex(connIndex);
		if (si === null) return;
		const conn = stagedConnections[si];
		if (!conn) return;
		const updated = [...stagedConnections];
		updated[si] = { ...conn, predicate };
		stagedConnections = updated;
	}

	// ── Resizable split ──
	let splitRatio = $state(0.5);
	let resizing = $state(false);
	let panelEl: HTMLDivElement | undefined = $state();

	function handleDividerPointerDown(e: PointerEvent) {
		e.preventDefault();
		resizing = true;
		document.addEventListener('pointermove', handleDividerMove);
		document.addEventListener('pointerup', handleDividerUp);
	}

	function handleDividerMove(e: PointerEvent) {
		if (!resizing || !panelEl) return;
		const rect = panelEl.getBoundingClientRect();
		// Account for the toolbar at bottom (~42px) and no header
		const contentTop = rect.top;
		const contentHeight = rect.height - 42;
		const ratio = (e.clientY - contentTop) / contentHeight;
		splitRatio = Math.max(0.15, Math.min(0.85, ratio));
	}

	function handleDividerUp() {
		resizing = false;
		document.removeEventListener('pointermove', handleDividerMove);
		document.removeEventListener('pointerup', handleDividerUp);
	}

	// ── Commit (save) flow — replicates NotepadTab.handleSave ──
	async function handleCommit() {
		if (entities.length === 0 || saving) return;
		saving = true;
		saveMessage = '';
		try {
			const realEntities = entities.filter(e => !e.virtual);

			// 1. Save all entities
			const results = await saveAll(entities);

			// 2. Save staged connections as triples
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

			// 3. Update text to embed new IDs
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

			// 3b. Expand @@ list blocks into individual blocks
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

			const sortedHeaders = [...listGroups.keys()].sort((a, b) => b - a);
			for (const headerLine of sortedHeaders) {
				const group = listGroups.get(headerLine)!;
				const lastItemLine = Math.max(...group.map(g => g.entity.startLine));
				const blockLength = lastItemLine - headerLine + 1;

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

				lines.splice(headerLine, blockLength, ...expandedLines);
			}

			notepadText.set(lines.join('\n'));

			// 4. Clear staged connections
			stagedConnections = [];

			// 5. Status message
			const created = realEntities.filter(e => e.dbId == null).length;
			const updated = realEntities.filter(e => e.dbId != null).length;
			const parts: string[] = [];
			if (created > 0) parts.push(`${created} created`);
			if (updated > 0) parts.push(`${updated} updated`);
			if (triplesCreated > 0) parts.push(`${triplesCreated} connection${triplesCreated === 1 ? '' : 's'}`);
			saveMessage = `Saved: ${parts.join(', ')}`;

			// 6. Reload stores
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

			// 7. Notify parent to create board nodes
			onCommit(results);
		} catch (e) {
			saveMessage = `Error: ${e instanceof Error ? e.message : 'save failed'}`;
		} finally {
			saving = false;
			setTimeout(() => { saveMessage = ''; }, 3000);
		}
	}
</script>

{#if open}
	<div class="graph-editor-panel" bind:this={panelEl}>
		{#if onClose}
			<button class="btn-slide-close" onclick={onClose} title="Close panel">
				<svg width="10" height="16" viewBox="0 0 10 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<polyline points="8 2 2 8 8 14"></polyline>
				</svg>
			</button>
		{/if}
		<div class="editor-section" style:flex="{splitRatio}">
			<NotepadEditor />
		</div>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="split-divider"
			onpointerdown={handleDividerPointerDown}
		></div>
		<div class="preview-section" style:flex="{1 - splitRatio}">
			<NotepadPreview
				{entities}
				positions={cardPositions}
				sizes={cardSizes}
				connections={allConnections}
				onCardMove={handleCardMove}
				onCardConnect={handleCardConnect}
				onCardDelete={handleCardDelete}
				onCardResize={handleCardResize}
				onConnectionSwap={handleConnectionSwap}
				onConnectionDelete={handleConnectionDelete}
				onPredicateSelect={handlePredicateSelect}
			/>
		</div>
		<div class="commit-toolbar">
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
			<button
				class="commit-btn"
				onclick={handleCommit}
				disabled={realEntityCount === 0 || saving}
			>
				{saving ? 'Saving...' : 'Commit to Graph'}
			</button>
		</div>
	</div>
{/if}

<style>
	.graph-editor-panel {
		position: absolute;
		top: 0;
		left: 0;
		bottom: 0;
		width: 380px;
		background: white;
		border-right: 1px solid #e5e7eb;
		box-shadow: 2px 0 12px rgba(0, 0, 0, 0.06);
		z-index: 50;
		display: flex;
		flex-direction: column;
	}
	.btn-slide-close {
		position: absolute;
		right: 0;
		top: 50%;
		transform: translateY(-50%);
		z-index: 10;
		width: 16px;
		height: 48px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: 1px solid #e5e7eb;
		border-right: none;
		border-radius: 6px 0 0 6px;
		background: #f9fafb;
		cursor: pointer;
		color: #9ca3af;
		opacity: 0;
		transition: opacity 0.2s, background 0.15s, color 0.15s;
		padding: 0;
	}
	.graph-editor-panel:hover .btn-slide-close {
		opacity: 1;
	}
	.btn-slide-close:hover {
		background: #e5e7eb;
		color: #374151;
	}
	.editor-section {
		min-height: 0;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}
	.split-divider {
		height: 5px;
		background: #e5e7eb;
		cursor: row-resize;
		flex-shrink: 0;
		transition: background 0.15s;
	}
	.split-divider:hover {
		background: #9ca3af;
	}
	.preview-section {
		min-height: 0;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}
	.commit-toolbar {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 8px 12px;
		background: white;
		border-top: 1px solid #e5e7eb;
		flex-shrink: 0;
	}
	.entity-count {
		font-size: 0.72rem;
		color: #6b7280;
		background: #f3f4f6;
		padding: 3px 8px;
		border-radius: 10px;
		font-weight: 500;
	}
	.conn-count {
		font-size: 0.72rem;
		color: #3b82f6;
		background: #eff6ff;
		padding: 3px 8px;
		border-radius: 10px;
		font-weight: 500;
	}
	.save-message {
		font-size: 0.68rem;
		color: #059669;
		font-weight: 500;
		flex: 1;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.save-message.error {
		color: #dc2626;
	}
	.commit-btn {
		margin-left: auto;
		padding: 5px 14px;
		background: #111827;
		color: white;
		border: 1px solid #111827;
		border-radius: 6px;
		font-size: 0.72rem;
		font-weight: 500;
		cursor: pointer;
		transition: background 0.15s;
		white-space: nowrap;
	}
	.commit-btn:hover:not(:disabled) {
		background: #1f2937;
	}
	.commit-btn:disabled {
		opacity: 0.4;
		cursor: default;
	}
</style>

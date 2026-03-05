<script lang="ts">
	import {
		readingSession,
		activeTab,
		addTab,
		removeTab,
		setActiveTab,
		loadPdfToTab,
		loadWebsiteToTab,
		updateTabPdfState,
		addCard,
		removeCard,
		moveCard,
		closeSession
	} from '$lib/stores/readingSession';
	import type { SessionCard } from './types';
	import type { Tag } from '$lib/types';
	import DocumentTabBar from './DocumentTabBar.svelte';
	import PdfViewer from './PdfViewer.svelte';
	import WebsiteViewer from './WebsiteViewer.svelte';
	import BoardToolbar from './BoardToolbar.svelte';
	import CardBoard from './CardBoard.svelte';
	import QueryPanel from '$lib/components/shared/QueryPanel.svelte';
	import Modal from '$lib/components/shared/Modal.svelte';
	import TagInput from '$lib/components/shared/TagInput.svelte';
	import TagBadge from '$lib/components/shared/TagBadge.svelte';
	import type { SearchResult } from '$lib/api/search';

	// Entity forms
	import ProjectForm from '$lib/components/forms/ProjectForm.svelte';
	import NoteForm from '$lib/components/forms/NoteForm.svelte';
	import LogEditForm from '$lib/components/forms/LogEditForm.svelte';
	import ActivityForm from '$lib/components/forms/ActivityForm.svelte';
	import SourceForm from '$lib/components/forms/SourceForm.svelte';
	import ActorForm from '$lib/components/forms/ActorForm.svelte';
	import PlanForm from '$lib/components/forms/PlanForm.svelte';

	// Stores
	import { projects } from '$lib/stores/projects';
	import { logs } from '$lib/stores/logs';
	import { notes } from '$lib/stores/notes';
	import { activities } from '$lib/stores/activities';
	import { sources } from '$lib/stores/sources';
	import { actors } from '$lib/stores/actors';
	import { plans } from '$lib/stores/plans';
	import { loadProjects } from '$lib/stores/projects';
	import { loadLogs } from '$lib/stores/logs';
	import { loadNotes } from '$lib/stores/notes';
	import { loadActivities } from '$lib/stores/activities';
	import { loadSources } from '$lib/stores/sources';
	import { loadActors } from '$lib/stores/actors';
	import { loadPlans } from '$lib/stores/plans';
	import { tags, loadTags, triggerEntityTagsRefresh } from '$lib/stores/tags';
	import { triples, loadTriples } from '$lib/stores/knowledgeGraph';
	import { loadPredicates } from '$lib/stores/predicates';
	import { updateTriple, swapTripleDirection, deleteTriple } from '$lib/api/knowledge';
	import { onMount } from 'svelte';

	// API
	import { createProject } from '$lib/api/projects';
	import { createLog } from '$lib/api/logs';
	import { createNote } from '$lib/api/notes';
	import { createActivity } from '$lib/api/activities';
	import { createSource } from '$lib/api/sources';
	import { createActor } from '$lib/api/actors';
	import { createPlan } from '$lib/api/plans';
	import { attachTag, detachTag, getEntityTags } from '$lib/api/tags';
	import { deleteNote } from '$lib/api/notes';
	import { deleteActivity } from '$lib/api/activities';
	import { deleteSource } from '$lib/api/sources';
	import { deleteProject } from '$lib/api/projects';
	import { deleteLog } from '$lib/api/logs';
	import { deleteActor } from '$lib/api/actors';
	import { deletePlan } from '$lib/api/plans';

	// ── State ──
	let editModal = $state<{ type: string; id: number; data: any } | null>(null);
	let modalTags = $state<Tag[]>([]);
	let fileInput: HTMLInputElement | undefined = $state();
	let nextCardY = $state(10);
	let queryPanelOpen = $state(false);

	function handleQueryResult(result: SearchResult) {
		const pos = nextCardPosition();
		addCard({
			entityType: result.type,
			entityId: result.id,
			title: result.title,
			x: pos.x,
			y: pos.y,
			fromTabId: currentTab?.id
		});
	}

	// ── Derived ──
	let currentTab = $derived($activeTab);
	let hasTabs = $derived($readingSession.tabs.length > 0);

	// ── Triples for board connections ──
	let boardTriples = $derived(
		$triples.filter(t => {
			const cards = $readingSession.cards;
			const hasSubject = cards.some(c => c.entityType === t.subject_type && c.entityId === t.subject_id);
			const hasObject = cards.some(c => c.entityType === t.object_type && c.entityId === t.object_id);
			return hasSubject && hasObject;
		})
	);

	// Load triples and predicates on mount
	onMount(() => {
		loadTriples();
		loadPredicates();
	});

	// ── Entity data lookup ──
	function getEntityData(type: string, id: number): any {
		switch (type) {
			case 'project': return $projects.find(e => e.id === id);
			case 'log': return $logs.find(e => e.id === id);
			case 'note': return $notes.find(e => e.id === id);
			case 'activity': return $activities.find(e => e.id === id);
			case 'source': return $sources.find(e => e.id === id);
			case 'actor': return $actors.find(e => e.id === id);
			case 'plan': return $plans.find(e => e.id === id);
			default: return null;
		}
	}

	// ── Auto-position for new cards from toolbar ──
	function nextCardPosition(): { x: number; y: number } {
		const pos = { x: 10, y: nextCardY };
		nextCardY += 70;
		return pos;
	}

	// ── Open document handlers ──
	async function handlePdfSelected(file: File) {
		const tabId = addTab('pdf');
		await loadPdfToTab(tabId, file);
	}

	async function handleUrlSubmitted(url: string) {
		const tabId = addTab('website');
		await loadWebsiteToTab(tabId, url);
	}

	function handleEmptyPdfClick() {
		fileInput?.click();
	}

	function handleEmptyFileInput(e: Event) {
		const input = e.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (file) {
			handlePdfSelected(file);
			input.value = '';
		}
	}

	let showEmptyUrlInput = $state(false);
	let emptyUrlValue = $state('');

	function handleEmptyUrlSubmit() {
		const url = emptyUrlValue.trim();
		if (!url) return;
		const finalUrl = url.match(/^https?:\/\//) ? url : `https://${url}`;
		handleUrlSubmitted(finalUrl);
		emptyUrlValue = '';
		showEmptyUrlInput = false;
	}

	// ── PDF callbacks ──
	function handlePageChange(page: number) {
		if (currentTab) {
			updateTabPdfState(currentTab.id, { currentPage: page });
		}
	}

	function handleTotalPages(count: number) {
		if (currentTab) {
			updateTabPdfState(currentTab.id, { totalPages: count });
		}
	}

	function handleTitleExtracted(title: string) {
		if (currentTab) {
			readingSession.update(s => ({
				...s,
				tabs: s.tabs.map(t => t.id === currentTab!.id ? { ...t, title } : t)
			}));
		}
	}

	function handleZoomOut() {
		if (currentTab) {
			const newScale = Math.max(0.5, (currentTab.scale ?? 1.5) - 0.25);
			updateTabPdfState(currentTab.id, { scale: newScale });
		}
	}

	function handleZoomIn() {
		if (currentTab) {
			const newScale = Math.min(3, (currentTab.scale ?? 1.5) + 0.25);
			updateTabPdfState(currentTab.id, { scale: newScale });
		}
	}

	// ── Entity creation from toolbar ──
	async function handleAddEntity(entityType: string) {
		const now = new Date().toISOString().slice(0, 16).replace('T', ' ');
		let created: any = null;

		try {
			switch (entityType) {
				case 'project': created = await createProject({ title: `New Project ${now}` }); await loadProjects(); break;
				case 'log': created = await createLog({ title: `New Log ${now}` }); await loadLogs(); break;
				case 'note': created = await createNote({ title: `New Note ${now}` }); await loadNotes(); break;
				case 'activity': created = await createActivity({ title: `New Activity ${now}` }); await loadActivities(); break;
				case 'source': created = await createSource({ title: `New Source ${now}` }); await loadSources(); break;
				case 'actor': created = await createActor({ full_name: `New Actor ${now}` }); await loadActors(); break;
				case 'plan': created = await createPlan({ title: `New Plan ${now}` }); await loadPlans(); break;
			}
			await loadTags();
		} catch (err) {
			console.error('Failed to create entity:', err);
			return;
		}

		if (created) {
			// Tag with the current reading activity's tag only
			if (currentTab?.activityTag) {
				try {
					await attachTag(currentTab.activityTag.id, entityType, created.id);
					await loadTags();
					triggerEntityTagsRefresh();
				} catch (err) {
					console.error('Failed to auto-tag:', err);
				}
			}

			const title = entityType === 'actor'
				? `New Actor ${now}`
				: `New ${entityType.charAt(0).toUpperCase() + entityType.slice(1)} ${now}`;

			const pos = nextCardPosition();
			addCard({
				entityType,
				entityId: created.id,
				title,
				x: pos.x,
				y: pos.y,
				fromTabId: currentTab?.id
			});

			// Open edit modal so user can fill in details
			// Use store data if available, otherwise use the API response directly
			const data = getEntityData(entityType, created.id) ?? created;
			if (data) {
				editModal = { type: entityType, id: created.id, data };
				try {
					modalTags = await getEntityTags(entityType, created.id);
				} catch {
					modalTags = [];
				}
			}
		}
	}

	// Clean up PDF text extraction artifacts: collapse runs of spaces,
	// join single-newline line breaks within a paragraph, rejoin hyphenated
	// words, and preserve intentional paragraph breaks (double newlines).
	function normalizePdfText(raw: string): string {
		return raw
			// Rejoin hyphenated line breaks (word-\n continuation)
			.replace(/-\s*\n\s*/g, '')
			// Preserve paragraph breaks: normalize 2+ newlines to a marker
			.replace(/\n{2,}/g, '\n\n')
			// Join remaining single newlines (intra-paragraph) with a space
			.replace(/\n/g, ' ')
			// Collapse multiple spaces into one
			.replace(/ {2,}/g, ' ')
			// Restore paragraph breaks
			.replace(/\n\n/g, '\n\n')
			.trim();
	}

	// ── Text drop → Note creation ──
	async function handleTextDrop(text: string, x: number, y: number) {
		try {
			const now = new Date().toISOString().slice(0, 16).replace('T', ' ');
			const note = await createNote({
				title: `Note ${now}`,
				content: normalizePdfText(text)
			});
			await loadNotes();

			// Only tag with the current reading activity's tag
			if (currentTab?.activityTag) {
				await attachTag(currentTab.activityTag.id, 'note', note.id);
			}
			await loadTags();
			triggerEntityTagsRefresh();

			addCard({
				entityType: 'note',
				entityId: note.id,
				title: `Note ${now}`,
				x,
				y,
				fromTabId: currentTab?.id
			});
		} catch (err) {
			console.error('Failed to create note from drop:', err);
		}
	}

	// ── Connection handlers ──
	async function handleCardConnect(sourceCard: SessionCard, targetCard: SessionCard) {
		try {
			const subjectTag = $tags.find(
				t => t.entity_type === sourceCard.entityType && t.entity_id === sourceCard.entityId
			);
			if (subjectTag) {
				await attachTag(subjectTag.id, targetCard.entityType, targetCard.entityId);
				await loadTags();
				await loadTriples();
				triggerEntityTagsRefresh();
			}
		} catch (err) {
			console.error('Failed to connect cards:', err);
		}
	}

	async function handlePredicateSelect(tripleId: number, predicate: string) {
		try {
			await updateTriple(tripleId, predicate);
			await loadTriples();
		} catch (err) {
			console.error('Failed to update predicate:', err);
		}
	}

	async function handleConnectionSwap(tripleId: number) {
		try {
			await swapTripleDirection(tripleId);
			await loadTriples();
		} catch (err) {
			console.error('Failed to swap connection:', err);
		}
	}

	async function handleConnectionDelete(tripleId: number) {
		try {
			await deleteTriple(tripleId);
			await loadTriples();
			triggerEntityTagsRefresh();
		} catch (err) {
			console.error('Failed to delete connection:', err);
		}
	}

	// ── Card interactions ──
	function handleCardMove(cardId: string, x: number, y: number) {
		moveCard(cardId, x, y);
	}

	async function handleCardDblClick(card: SessionCard) {
		const data = getEntityData(card.entityType, card.entityId);
		if (!data) return;
		editModal = { type: card.entityType, id: card.entityId, data };
		try {
			modalTags = await getEntityTags(card.entityType, card.entityId);
		} catch {
			modalTags = [];
		}
	}

	async function handleCardDelete(card: SessionCard) {
		try {
			switch (card.entityType) {
				case 'note': await deleteNote(card.entityId); await loadNotes(); break;
				case 'activity': await deleteActivity(card.entityId); await loadActivities(); break;
				case 'source': await deleteSource(card.entityId); await loadSources(); break;
				case 'project': await deleteProject(card.entityId); await loadProjects(); break;
				case 'log': await deleteLog(card.entityId); await loadLogs(); break;
				case 'actor': await deleteActor(card.entityId); await loadActors(); break;
				case 'plan': await deletePlan(card.entityId); await loadPlans(); break;
			}
			await loadTags();
			triggerEntityTagsRefresh();
		} catch (err) {
			console.error('Failed to delete entity:', err);
		}
		removeCard(card.id);
	}

	// ── Edit modal ──
	function editModalTitle(): string {
		if (!editModal) return '';
		return `Edit ${editModal.type.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}`;
	}

	async function closeEditModal() {
		if (editModal) {
			switch (editModal.type) {
				case 'project': await Promise.all([loadProjects(), loadTags()]); break;
				case 'log': await Promise.all([loadLogs(), loadTags()]); break;
				case 'note': await Promise.all([loadNotes(), loadTags()]); break;
				case 'activity': await Promise.all([loadActivities(), loadTags()]); break;
				case 'source': await Promise.all([loadSources(), loadTags()]); break;
				case 'actor': await Promise.all([loadActors(), loadTags()]); break;
				case 'plan': await Promise.all([loadPlans(), loadTags()]); break;
			}
			// Update card title from store
			const data = getEntityData(editModal.type, editModal.id);
			if (data) {
				const newTitle = data.title ?? data.full_name ?? '';
				readingSession.update(s => ({
					...s,
					cards: s.cards.map(c =>
						c.entityType === editModal!.type && c.entityId === editModal!.id
							? { ...c, title: newTitle }
							: c
					)
				}));
			}
		}
		editModal = null;
		modalTags = [];
	}

	async function handleModalAttachTag(tag: Tag) {
		if (!editModal) return;
		await attachTag(tag.id, editModal.type, editModal.id);
		modalTags = await getEntityTags(editModal.type, editModal.id);
		triggerEntityTagsRefresh();
	}

	async function handleModalDetachTag(tag: Tag) {
		if (!editModal) return;
		await detachTag(tag.id, editModal.type, editModal.id);
		modalTags = await getEntityTags(editModal.type, editModal.id);
		triggerEntityTagsRefresh();
	}
</script>

{#if !hasTabs}
	<!-- Empty state: direct PDF / URL buttons -->
	<div class="empty-state">
		<div class="empty-content">
			<p class="empty-title">Open a document to start reading</p>
			<div class="empty-buttons">
				<button class="open-btn pdf-open" onclick={handleEmptyPdfClick}>
					<span class="btn-dot pdf"></span>
					Open PDF
				</button>
				{#if showEmptyUrlInput}
					<div class="empty-url-row">
						<input
							type="text"
							class="empty-url-input"
							bind:value={emptyUrlValue}
							onkeydown={(e) => { if (e.key === 'Enter') handleEmptyUrlSubmit(); else if (e.key === 'Escape') { showEmptyUrlInput = false; emptyUrlValue = ''; } }}
							placeholder="https://..."
						/>
						<button class="open-btn url-go" onclick={handleEmptyUrlSubmit} disabled={!emptyUrlValue.trim()}>Go</button>
					</div>
				{:else}
					<button class="open-btn url-open" onclick={() => showEmptyUrlInput = true}>
						<span class="btn-dot url"></span>
						Browse URL
					</button>
				{/if}
			</div>
		</div>
	</div>
	<input
		bind:this={fileInput}
		type="file"
		accept=".pdf,application/pdf"
		onchange={handleEmptyFileInput}
		hidden
	/>
{:else}
	<div class="read-tab">
		<!-- Left Panel: Document viewer -->
		<div class="left-panel">
			<DocumentTabBar
				tabs={$readingSession.tabs}
				activeTabId={$readingSession.activeTabId}
				onTabClick={setActiveTab}
				onTabClose={removeTab}
				onPdfSelected={handlePdfSelected}
				onUrlSubmitted={handleUrlSubmitted}
			/>

			{#if currentTab}
				<!-- Document header with zoom controls -->
				{#if currentTab.type === 'pdf' && currentTab.pdfUrl}
					<div class="doc-header">
						<span class="doc-title">{currentTab.title}</span>
						{#if (currentTab.totalPages ?? 0) > 0}
							<span class="page-indicator">
								{currentTab.currentPage ?? 1} / {currentTab.totalPages}
							</span>
						{/if}
						<div class="header-controls">
							<button class="ctrl-btn" onclick={handleZoomOut}>-</button>
							<span class="zoom-label">{Math.round((currentTab.scale ?? 1.5) * 100)}%</span>
							<button class="ctrl-btn" onclick={handleZoomIn}>+</button>
						</div>
					</div>
				{/if}

				<!-- Active document viewer -->
				<div class="doc-viewer">
					{#key currentTab.id}
						{#if currentTab.type === 'pdf' && currentTab.pdfUrl}
							<PdfViewer
								pdfUrl={currentTab.pdfUrl}
								scale={currentTab.scale ?? 1.5}
								onPageChange={handlePageChange}
								onTotalPages={handleTotalPages}
								onTitleExtracted={handleTitleExtracted}
							/>
						{:else if currentTab.type === 'website' && currentTab.websiteUrl}
							<WebsiteViewer url={currentTab.websiteUrl} />
						{:else}
							<div class="doc-loading">Loading...</div>
						{/if}
					{/key}
				</div>
			{/if}
		</div>

		<!-- Right Panel: Card board -->
		<div class="right-panel">
			<BoardToolbar onAddEntity={handleAddEntity}>
				{#snippet extra()}
					<button
						class="query-toggle-btn"
						class:active={queryPanelOpen}
						onclick={() => queryPanelOpen = !queryPanelOpen}
						title="Search entities"
					>
						<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<circle cx="11" cy="11" r="8"></circle>
							<line x1="21" y1="21" x2="16.65" y2="16.65"></line>
						</svg>
					</button>
				{/snippet}
			</BoardToolbar>
			<div class="board-area">
				<CardBoard
					cards={$readingSession.cards}
					triples={boardTriples}
					onTextDrop={handleTextDrop}
					onCardMove={handleCardMove}
					onCardDblClick={handleCardDblClick}
					onCardDelete={handleCardDelete}
					onCardConnect={handleCardConnect}
					onConnectionSwap={handleConnectionSwap}
					onConnectionDelete={handleConnectionDelete}
					onPredicateSelect={handlePredicateSelect}
				/>
				<QueryPanel
					open={queryPanelOpen}
					onClose={() => queryPanelOpen = false}
					onResultClick={handleQueryResult}
					resultActionLabel="Add to board"
				/>
			</div>
		</div>
	</div>
{/if}

<!-- Edit Entity Modal -->
<Modal open={editModal !== null} title={editModalTitle()} onClose={closeEditModal}>
	{#if editModal?.type === 'project'}
		<ProjectForm editData={editModal.data} onDone={closeEditModal} />
	{:else if editModal?.type === 'note'}
		<NoteForm editData={editModal.data} onDone={closeEditModal} />
	{:else if editModal?.type === 'log'}
		<LogEditForm editData={editModal.data} onDone={closeEditModal} />
	{:else if editModal?.type === 'activity'}
		<ActivityForm editData={editModal.data} onDone={closeEditModal} />
	{:else if editModal?.type === 'source'}
		<SourceForm editData={editModal.data} onDone={closeEditModal} />
	{:else if editModal?.type === 'actor'}
		<ActorForm editData={editModal.data} onDone={closeEditModal} />
	{:else if editModal?.type === 'plan'}
		<PlanForm editData={editModal.data} onDone={closeEditModal} />
	{/if}

	{#if editModal}
		<div class="modal-tags-section">
			<div class="modal-tags-label">Tags</div>
			{#if modalTags.length > 0}
				<div class="modal-tag-badges">
					{#each modalTags as tag (tag.id)}
						<TagBadge {tag} removable onRemove={() => handleModalDetachTag(tag)} />
					{/each}
				</div>
			{/if}
			<TagInput
				attachedTags={modalTags}
				targetType={editModal.type}
				targetId={editModal.id}
				onAttach={handleModalAttachTag}
				onDetach={handleModalDetachTag}
			/>
		</div>
	{/if}
</Modal>

<style>
	/* ── Empty state ── */
	.empty-state {
		display: flex;
		align-items: center;
		justify-content: center;
		height: calc(100vh - 80px);
	}
	.empty-content {
		text-align: center;
	}
	.empty-title {
		font-size: 1.1rem;
		color: #374151;
		font-weight: 500;
		margin: 0 0 20px;
	}
	.empty-buttons {
		display: flex;
		flex-direction: column;
		gap: 10px;
		align-items: center;
	}
	.open-btn {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 10px 24px;
		border: 1px solid #d1d5db;
		border-radius: 8px;
		background: white;
		font-size: 0.9rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s;
		min-width: 160px;
		justify-content: center;
	}
	.pdf-open {
		color: #22c55e;
		border-color: #22c55e;
	}
	.pdf-open:hover {
		background: #22c55e;
		color: white;
	}
	.url-open {
		color: #3b82f6;
		border-color: #3b82f6;
	}
	.url-open:hover {
		background: #3b82f6;
		color: white;
	}
	.btn-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
	}
	.btn-dot.pdf {
		background: #22c55e;
	}
	.btn-dot.url {
		background: #3b82f6;
	}
	.empty-url-row {
		display: flex;
		gap: 6px;
	}
	.empty-url-input {
		padding: 8px 12px;
		border: 1px solid #3b82f6;
		border-radius: 8px;
		font-size: 0.875rem;
		outline: none;
		width: 220px;
	}
	.empty-url-input:focus {
		box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
	}
	.url-go {
		color: #3b82f6;
		border-color: #3b82f6;
		min-width: auto;
		padding: 8px 16px;
	}
	.url-go:hover:not(:disabled) {
		background: #3b82f6;
		color: white;
	}
	.url-go:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	/* ── Split layout ── */
	.read-tab {
		display: flex;
		height: calc(100vh - 80px);
	}
	.left-panel {
		flex: 6;
		display: flex;
		flex-direction: column;
		min-width: 0;
		overflow: hidden;
	}
	.right-panel {
		flex: 4;
		display: flex;
		flex-direction: column;
		border-left: 1px solid #e5e7eb;
		min-width: 0;
		overflow: hidden;
	}
	.board-area {
		flex: 1;
		position: relative;
		overflow: hidden;
	}
	:global(.query-toggle-btn) {
		padding: 4px 8px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		background: white;
		cursor: pointer;
		color: #6b7280;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.15s;
	}
	:global(.query-toggle-btn:hover) {
		background: #f3f4f6;
	}
	:global(.query-toggle-btn.active) {
		background: #374151;
		color: white;
		border-color: #374151;
	}

	/* ── Document header ── */
	.doc-header {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 6px 16px;
		border-bottom: 1px solid #e5e7eb;
		background: #fafafa;
		flex-shrink: 0;
	}
	.doc-title {
		font-size: 0.8rem;
		font-weight: 600;
		color: #374151;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		min-width: 0;
	}
	.page-indicator {
		font-size: 0.72rem;
		color: #6b7280;
		white-space: nowrap;
	}
	.header-controls {
		display: flex;
		align-items: center;
		gap: 4px;
		margin-left: auto;
		flex-shrink: 0;
	}
	.zoom-label {
		font-size: 0.72rem;
		color: #6b7280;
		min-width: 36px;
		text-align: center;
	}
	.ctrl-btn {
		padding: 2px 8px;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		background: white;
		color: #374151;
		font-size: 0.75rem;
		cursor: pointer;
		transition: background 0.15s;
	}
	.ctrl-btn:hover {
		background: #f3f4f6;
	}

	/* ── Document viewer ── */
	.doc-viewer {
		flex: 1;
		overflow: hidden;
	}
	.doc-loading {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100%;
		color: #9ca3af;
		font-size: 0.9rem;
	}

	/* ── Edit modal tags section ── */
	.modal-tags-section {
		margin-top: 16px;
		padding-top: 16px;
		border-top: 1px solid #e5e7eb;
	}
	.modal-tags-label {
		font-size: 0.8rem;
		font-weight: 600;
		color: #374151;
		margin-bottom: 8px;
	}
	.modal-tag-badges {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		margin-bottom: 8px;
	}
</style>

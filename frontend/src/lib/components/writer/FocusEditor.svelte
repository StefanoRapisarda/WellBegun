<script lang="ts">
	import { onMount } from 'svelte';
	import type { OpenDocument } from './types';
	import CommandPalette from './CommandPalette.svelte';
	import ReferencePanel from './ReferencePanel.svelte';
	import DocumentNavigator from './DocumentNavigator.svelte';
	import EditorPane from './EditorPane.svelte';

	// Document management
	let documents = $state<OpenDocument[]>([]);
	let activeDocId = $state<string | null>(null);

	// Split view
	let isSplit = $state(false);
	let topPaneDocs = $state<string[]>([]);
	let bottomPaneDocs = $state<string[]>([]);
	let topActiveId = $state<string | null>(null);
	let bottomActiveId = $state<string | null>(null);
	let activePane = $state<'top' | 'bottom'>('top');

	// UI state
	let viewMode = $state<'write' | 'preview'>('write');
	let showCommandPalette = $state(false);
	let showReferencePanel = $state(false);
	let showNavigator = $state(false);
	let showSaveDialog = $state(false);
	let savePathInput = $state('');
	let isSaving = $state(false);
	let saveMessage = $state<{ type: 'success' | 'error'; text: string } | null>(null);

	// Derived states
	let activeDoc = $derived(documents.find(d => d.id === activeDocId) || null);
	let currentActiveId = $derived(isSplit ? (activePane === 'top' ? topActiveId : bottomActiveId) : activeDocId);

	let topDocuments = $derived(
		isSplit ? documents.filter(d => topPaneDocs.includes(d.id)) : documents
	);
	let bottomDocuments = $derived(
		isSplit ? documents.filter(d => bottomPaneDocs.includes(d.id)) : []
	);

	function generateId(): string {
		return Math.random().toString(36).substring(2, 9);
	}

	function createNewDocument(): OpenDocument {
		return {
			id: generateId(),
			title: 'Untitled',
			content: '',
			filePath: null,
			hasChanges: false,
			originalContent: '',
		};
	}

	function addDocument(doc: OpenDocument) {
		documents = [...documents, doc];

		if (isSplit) {
			if (activePane === 'top') {
				topPaneDocs = [...topPaneDocs, doc.id];
				topActiveId = doc.id;
			} else {
				bottomPaneDocs = [...bottomPaneDocs, doc.id];
				bottomActiveId = doc.id;
			}
		} else {
			activeDocId = doc.id;
		}
	}

	function newDocument() {
		addDocument(createNewDocument());
	}

	function openFile(path: string, content: string, title: string) {
		// Check if already open
		const existing = documents.find(d => d.filePath === path);
		if (existing) {
			selectDocument(existing.id);
			return;
		}

		const doc: OpenDocument = {
			id: generateId(),
			title,
			content,
			filePath: path,
			hasChanges: false,
			originalContent: content,
		};
		addDocument(doc);
	}

	function selectDocument(docId: string) {
		if (isSplit) {
			if (topPaneDocs.includes(docId)) {
				topActiveId = docId;
				activePane = 'top';
			} else if (bottomPaneDocs.includes(docId)) {
				bottomActiveId = docId;
				activePane = 'bottom';
			}
		} else {
			activeDocId = docId;
		}
	}

	function closeDocument(docId: string) {
		const doc = documents.find(d => d.id === docId);
		if (doc?.hasChanges) {
			if (!confirm(`"${doc.title}" has unsaved changes. Close anyway?`)) {
				return;
			}
		}

		documents = documents.filter(d => d.id !== docId);

		if (isSplit) {
			topPaneDocs = topPaneDocs.filter(id => id !== docId);
			bottomPaneDocs = bottomPaneDocs.filter(id => id !== docId);

			if (topActiveId === docId) {
				topActiveId = topPaneDocs[0] || null;
			}
			if (bottomActiveId === docId) {
				bottomActiveId = bottomPaneDocs[0] || null;
			}
		} else {
			if (activeDocId === docId) {
				activeDocId = documents[0]?.id || null;
			}
		}
	}

	function updateContent(docId: string, content: string) {
		documents = documents.map(d => {
			if (d.id === docId) {
				return {
					...d,
					content,
					hasChanges: content !== d.originalContent,
				};
			}
			return d;
		});
	}

	function updateTitle(docId: string, title: string) {
		documents = documents.map(d => {
			if (d.id === docId) {
				return { ...d, title, hasChanges: true };
			}
			return d;
		});
	}

	function toggleSplit() {
		if (isSplit) {
			// Merge back to single pane
			isSplit = false;
			activeDocId = topActiveId || bottomActiveId || documents[0]?.id || null;
		} else {
			// Split the view
			isSplit = true;
			topPaneDocs = documents.map(d => d.id);
			bottomPaneDocs = [];
			topActiveId = activeDocId;
			bottomActiveId = null;
			activePane = 'top';
		}
	}

	function moveToOtherPane(docId: string) {
		if (!isSplit) return;

		if (topPaneDocs.includes(docId)) {
			topPaneDocs = topPaneDocs.filter(id => id !== docId);
			bottomPaneDocs = [...bottomPaneDocs, docId];
			if (topActiveId === docId) {
				topActiveId = topPaneDocs[0] || null;
			}
			bottomActiveId = docId;
		} else {
			bottomPaneDocs = bottomPaneDocs.filter(id => id !== docId);
			topPaneDocs = [...topPaneDocs, docId];
			if (bottomActiveId === docId) {
				bottomActiveId = bottomPaneDocs[0] || null;
			}
			topActiveId = docId;
		}
	}

	async function saveDocument(doc: OpenDocument, path?: string) {
		const savePath = path || doc.filePath;
		if (!savePath) {
			savePathInput = `~/${doc.title.replace(/[^a-zA-Z0-9_-]/g, '_')}.md`;
			showSaveDialog = true;
			return;
		}

		isSaving = true;
		saveMessage = null;

		try {
			const response = await fetch('/api/documents/save', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					path: savePath,
					content: doc.content,
					title: doc.title
				})
			});

			const result = await response.json();

			if (response.ok && result.success) {
				documents = documents.map(d => {
					if (d.id === doc.id) {
						return {
							...d,
							filePath: result.path,
							hasChanges: false,
							originalContent: d.content,
						};
					}
					return d;
				});
				saveMessage = { type: 'success', text: 'Saved' };
				showSaveDialog = false;
				setTimeout(() => saveMessage = null, 2000);
			} else {
				saveMessage = { type: 'error', text: result.detail || 'Failed to save' };
			}
		} catch (err) {
			saveMessage = { type: 'error', text: 'Failed to save' };
		} finally {
			isSaving = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		// Save: Cmd+S
		if ((e.metaKey || e.ctrlKey) && e.key === 's') {
			e.preventDefault();
			const doc = documents.find(d => d.id === currentActiveId);
			if (doc) saveDocument(doc);
			return;
		}
		// New: Cmd+N
		if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
			e.preventDefault();
			newDocument();
			return;
		}
		// Toggle navigator: Cmd+B
		if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
			e.preventDefault();
			showNavigator = !showNavigator;
			return;
		}
		// Toggle split: Cmd+\
		if ((e.metaKey || e.ctrlKey) && e.key === '\\') {
			e.preventDefault();
			toggleSplit();
			return;
		}
		// Command palette: Cmd+K
		if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
			e.preventDefault();
			showCommandPalette = true;
			return;
		}
		// Toggle view mode: Cmd+Shift+P
		if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'p') {
			e.preventDefault();
			viewMode = viewMode === 'write' ? 'preview' : 'write';
			return;
		}
		// Toggle reference panel: Cmd+Shift+R
		if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'r') {
			e.preventDefault();
			showReferencePanel = !showReferencePanel;
			return;
		}
		// Close current: Cmd+W
		if ((e.metaKey || e.ctrlKey) && e.key === 'w') {
			e.preventDefault();
			if (currentActiveId) closeDocument(currentActiveId);
			return;
		}
		// Escape
		if (e.key === 'Escape') {
			if (showSaveDialog) showSaveDialog = false;
			else if (showCommandPalette) showCommandPalette = false;
		}
	}

	function insertText(text: string) {
		// This would need to be more sophisticated with refs
		// For now, just append to content
		const doc = documents.find(d => d.id === currentActiveId);
		if (doc) {
			updateContent(doc.id, doc.content + text);
		}
	}

	function handlePaletteInsert(text: string) {
		insertText(text);
		showCommandPalette = false;
	}

	function handleReferenceInsert(text: string) {
		insertText(text);
	}

	onMount(() => {
		// Load draft or create new
		const saved = localStorage.getItem('focus-editor-documents');
		if (saved) {
			try {
				const data = JSON.parse(saved);
				documents = data.documents || [];
				activeDocId = data.activeDocId || null;
			} catch {}
		}

		if (documents.length === 0) {
			newDocument();
		}
	});

	// Auto-save to localStorage
	$effect(() => {
		localStorage.setItem('focus-editor-documents', JSON.stringify({
			documents,
			activeDocId,
		}));
	});
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="focus-editor" class:with-navigator={showNavigator} class:with-reference={showReferencePanel}>
	<header class="editor-header">
		<div class="header-left">
			{#if activeDoc}
				<input
					type="text"
					class="title-input"
					value={activeDoc.title}
					oninput={(e) => updateTitle(activeDoc!.id, e.currentTarget.value)}
					placeholder="Untitled"
				/>
				{#if activeDoc.filePath}
					<span class="file-path" title={activeDoc.filePath}>
						{activeDoc.filePath.split('/').slice(-2).join('/')}
					</span>
				{/if}
				{#if saveMessage}
					<span class="save-message" class:success={saveMessage.type === 'success'}>
						{saveMessage.text}
					</span>
				{/if}
			{:else}
				<span class="no-doc-title">No document</span>
			{/if}
		</div>

		<div class="header-actions">
			<div class="action-group">
				<button class="icon-btn" onclick={newDocument} title="New (Cmd+N)">
					<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
						<polyline points="14 2 14 8 20 8"/>
						<line x1="12" y1="18" x2="12" y2="12"/>
						<line x1="9" y1="15" x2="15" y2="15"/>
					</svg>
				</button>
				<div class="save-btn-wrap">
					{#if activeDoc?.hasChanges}
						<span class="unsaved-arrow">&#9656;</span>
					{/if}
					<button
						class="icon-btn"
						class:has-changes={activeDoc?.hasChanges}
						onclick={() => activeDoc && saveDocument(activeDoc)}
						disabled={isSaving || !activeDoc}
						title="Save (Cmd+S)"
					>
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
							<polyline points="17 21 17 13 7 13 7 21"/>
							<polyline points="7 3 7 8 15 8"/>
						</svg>
					</button>
				</div>
			</div>

			<div class="separator"></div>

			<div class="view-toggle">
				<button
					class="toggle-option"
					class:active={viewMode === 'write'}
					onclick={() => viewMode = 'write'}
				>Raw</button>
				<button
					class="toggle-option"
					class:active={viewMode === 'preview'}
					onclick={() => viewMode = 'preview'}
				>Rendered</button>
			</div>

			<div class="separator"></div>

			<button
				class="icon-btn"
				class:active={isSplit}
				onclick={toggleSplit}
				title="Split view (Cmd+\)"
			>
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<rect x="3" y="3" width="18" height="18" rx="2"/>
					<line x1="3" y1="12" x2="21" y2="12"/>
				</svg>
			</button>

			<button
				class="icon-btn"
				class:active={showNavigator}
				onclick={() => showNavigator = !showNavigator}
				title="File navigator (Cmd+B)"
			>
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
				</svg>
			</button>

			<button
				class="icon-btn"
				class:active={showReferencePanel}
				onclick={() => showReferencePanel = !showReferencePanel}
				title="References (Cmd+Shift+R)"
			>
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<rect x="3" y="3" width="18" height="18" rx="2"/>
					<line x1="9" y1="3" x2="9" y2="21"/>
				</svg>
			</button>

			<button
				class="icon-btn"
				onclick={() => showCommandPalette = true}
				title="Command palette (Cmd+K)"
			>
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<circle cx="11" cy="11" r="8"/>
					<line x1="21" y1="21" x2="16.65" y2="16.65"/>
				</svg>
			</button>
		</div>
	</header>

	<div class="editor-body">
		{#if isSplit}
			<div class="split-container">
				<div
					class="pane-wrapper"
					class:active={activePane === 'top'}
					onclick={() => activePane = 'top'}
				>
					<EditorPane
						documents={topDocuments}
						activeDocId={topActiveId}
						{viewMode}
						paneId="top"
						onSelectDoc={(id) => { topActiveId = id; activePane = 'top'; }}
						onCloseDoc={closeDocument}
						onContentChange={updateContent}
						onTitleChange={updateTitle}
					/>
				</div>
				<div class="split-divider"></div>
				<div
					class="pane-wrapper"
					class:active={activePane === 'bottom'}
					onclick={() => activePane = 'bottom'}
				>
					<EditorPane
						documents={bottomDocuments}
						activeDocId={bottomActiveId}
						{viewMode}
						paneId="bottom"
						onSelectDoc={(id) => { bottomActiveId = id; activePane = 'bottom'; }}
						onCloseDoc={closeDocument}
						onContentChange={updateContent}
						onTitleChange={updateTitle}
					/>
				</div>
			</div>
		{:else}
			<EditorPane
				{documents}
				activeDocId={activeDocId}
				{viewMode}
				paneId="main"
				onSelectDoc={selectDocument}
				onCloseDoc={closeDocument}
				onContentChange={updateContent}
				onTitleChange={updateTitle}
			/>
		{/if}
	</div>

	{#if showReferencePanel}
		<ReferencePanel
			onClose={() => showReferencePanel = false}
			onInsert={handleReferenceInsert}
		/>
	{/if}

	{#if showNavigator}
		<DocumentNavigator
			onOpenFile={openFile}
			onClose={() => showNavigator = false}
			currentDocument={documents.find(d => d.id === currentActiveId) || null}
			onSaveCurrentDocument={(path) => {
				const doc = documents.find(d => d.id === currentActiveId);
				if (doc) saveDocument(doc, path);
			}}
		/>
	{/if}
</div>

{#if showCommandPalette}
	<CommandPalette
		onClose={() => showCommandPalette = false}
		onInsert={handlePaletteInsert}
	/>
{/if}

{#if showSaveDialog}
	<div class="modal-overlay" onclick={() => showSaveDialog = false} role="dialog" aria-modal="true">
		<div class="save-dialog" onclick={(e) => e.stopPropagation()} role="document">
			<header class="save-header">
				<h3>Save Document</h3>
				<button class="close-btn-small" onclick={() => showSaveDialog = false}>x</button>
			</header>
			<div class="save-body">
				<label>
					<span>File path</span>
					<input
						type="text"
						bind:value={savePathInput}
						placeholder="~/Documents/my-document.md"
						onkeydown={(e) => e.key === 'Enter' && activeDoc && saveDocument(activeDoc, savePathInput)}
					/>
				</label>
				<p class="save-hint">Use .md, .markdown, or .txt extension</p>
			</div>
			<footer class="save-footer">
				<button class="btn-cancel" onclick={() => showSaveDialog = false}>Cancel</button>
				<button
					class="btn-save"
					onclick={() => activeDoc && saveDocument(activeDoc, savePathInput)}
					disabled={isSaving || !savePathInput.trim()}
				>
					{isSaving ? 'Saving...' : 'Save'}
				</button>
			</footer>
		</div>
	</div>
{/if}

<style>
	.focus-editor {
		display: flex;
		flex-direction: column;
		height: calc(100vh - 80px);
		background: #fafafa;
		transition: padding-left 0.2s ease, padding-right 0.2s ease;
	}
	.focus-editor.with-navigator {
		padding-left: 260px;
	}
	.focus-editor.with-reference {
		padding-right: 360px;
	}
	.focus-editor.with-navigator.with-reference {
		padding-left: 260px;
		padding-right: 360px;
	}

	.editor-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 10px 20px;
		border-bottom: 1px solid #e5e7eb;
		background: white;
		gap: 16px;
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 10px;
		flex: 1;
		min-width: 0;
	}

	.title-input {
		border: none;
		font-size: 1.2rem;
		font-weight: 600;
		color: #111827;
		background: transparent;
		outline: none;
		max-width: 300px;
		min-width: 80px;
	}
	.title-input::placeholder {
		color: #d1d5db;
	}

	.no-doc-title {
		font-size: 1rem;
		color: #9ca3af;
	}

	.file-path {
		font-size: 0.7rem;
		color: #9ca3af;
		font-family: 'SF Mono', monospace;
		max-width: 150px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.save-btn-wrap {
		position: relative;
		display: flex;
		align-items: center;
	}

	.unsaved-arrow {
		position: absolute;
		right: 100%;
		top: 50%;
		transform: translateY(-50%);
		color: #f59e0b;
		font-size: 0.85rem;
		line-height: 1;
		pointer-events: none;
	}

	.save-message {
		font-size: 0.7rem;
		padding: 2px 8px;
		border-radius: 4px;
		background: #fef2f2;
		color: #dc2626;
	}
	.save-message.success {
		background: #ecfdf5;
		color: #059669;
	}

	.header-actions {
		display: flex;
		gap: 6px;
		align-items: center;
	}

	.action-group {
		display: flex;
		gap: 2px;
	}

	.icon-btn {
		width: 32px;
		height: 32px;
		border: none;
		background: transparent;
		border-radius: 5px;
		cursor: pointer;
		color: #9ca3af;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.15s;
	}
	.icon-btn:hover {
		background: #f3f4f6;
		color: #374151;
	}
	.icon-btn.active {
		background: #111827;
		color: white;
	}
	.icon-btn.has-changes {
		color: #f59e0b;
	}
	.icon-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.separator {
		width: 1px;
		height: 20px;
		background: #e5e7eb;
		margin: 0 4px;
	}

	.view-toggle {
		display: flex;
		background: #f3f4f6;
		border-radius: 5px;
		padding: 2px;
	}
	.toggle-option {
		padding: 5px 12px;
		border: none;
		border-radius: 4px;
		background: transparent;
		cursor: pointer;
		font-size: 0.75rem;
		font-weight: 500;
		color: #6b7280;
	}
	.toggle-option:hover {
		color: #374151;
	}
	.toggle-option.active {
		background: white;
		color: #111827;
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
	}

	.editor-body {
		flex: 1;
		display: flex;
		flex-direction: column;
		min-height: 0;
	}

	.split-container {
		flex: 1;
		display: flex;
		flex-direction: column;
		min-height: 0;
	}

	.pane-wrapper {
		flex: 1;
		display: flex;
		flex-direction: column;
		min-height: 0;
		border: 2px solid transparent;
		transition: border-color 0.15s;
	}
	.pane-wrapper.active {
		border-color: rgba(92, 122, 153, 0.3);
	}

	.split-divider {
		height: 4px;
		background: #e5e7eb;
		cursor: row-resize;
	}
	.split-divider:hover {
		background: #d1d5db;
	}

	/* Save Dialog */
	.modal-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.4);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}

	.save-dialog {
		background: white;
		border-radius: 10px;
		width: 90%;
		max-width: 400px;
		box-shadow: 0 16px 48px rgba(0, 0, 0, 0.2);
	}

	.save-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 12px 16px;
		border-bottom: 1px solid #e5e7eb;
	}
	.save-header h3 {
		margin: 0;
		font-size: 0.9rem;
		font-weight: 600;
	}

	.close-btn-small {
		width: 24px;
		height: 24px;
		border: none;
		background: none;
		font-size: 1rem;
		color: #9ca3af;
		cursor: pointer;
		border-radius: 4px;
	}
	.close-btn-small:hover {
		background: #f3f4f6;
		color: #374151;
	}

	.save-body {
		padding: 16px;
	}
	.save-body label {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.save-body label span {
		font-size: 0.8rem;
		font-weight: 500;
		color: #374151;
	}
	.save-body input {
		padding: 9px 12px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 0.85rem;
		font-family: 'SF Mono', monospace;
	}
	.save-body input:focus {
		outline: none;
		border-color: #5c7a99;
	}
	.save-hint {
		margin: 8px 0 0;
		font-size: 0.7rem;
		color: #9ca3af;
	}

	.save-footer {
		display: flex;
		justify-content: flex-end;
		gap: 8px;
		padding: 12px 16px;
		border-top: 1px solid #e5e7eb;
	}

	.btn-cancel {
		padding: 7px 14px;
		border: 1px solid #d1d5db;
		border-radius: 5px;
		background: white;
		color: #374151;
		font-size: 0.8rem;
		cursor: pointer;
	}
	.btn-cancel:hover {
		background: #f3f4f6;
	}

	.btn-save {
		padding: 7px 16px;
		border: none;
		border-radius: 5px;
		background: #5c7a99;
		color: white;
		font-size: 0.8rem;
		cursor: pointer;
	}
	.btn-save:hover:not(:disabled) {
		background: color-mix(in srgb, #5c7a99 85%, #111827);
	}
	.btn-save:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
</style>

<script lang="ts">
	import type { OpenDocument } from './types';

	interface FileItem {
		name: string;
		path: string;
		type: 'file' | 'directory';
		modified?: string;
	}

	let {
		onOpenFile,
		onClose,
		onSaveCurrentDocument,
		currentDocument,
	}: {
		onOpenFile: (path: string, content: string, title: string) => void;
		onClose: () => void;
		onSaveCurrentDocument?: (path: string) => void;
		currentDocument?: OpenDocument | null;
	} = $props();

	let currentPath = $state('~');
	let parentPath = $state<string | null>(null);
	let directories = $state<FileItem[]>([]);
	let files = $state<FileItem[]>([]);
	let isLoading = $state(true);
	let error = $state('');
	let pathInput = $state('~');

	// Create dialogs
	let showCreateFileDialog = $state(false);
	let showCreateDirDialog = $state(false);
	let showSaveAsDialog = $state(false);
	let newItemName = $state('');
	let isCreating = $state(false);

	async function loadDirectory(path: string) {
		isLoading = true;
		error = '';

		try {
			const response = await fetch(`/api/documents/list?path=${encodeURIComponent(path)}`);
			const result = await response.json();

			if (!response.ok) {
				error = result.detail || 'Failed to load directory';
				return;
			}

			currentPath = result.current;
			parentPath = result.parent;
			directories = result.directories;
			files = result.files;
			pathInput = result.current;
		} catch (err) {
			error = 'Failed to connect to server';
		} finally {
			isLoading = false;
		}
	}

	async function openFile(path: string) {
		try {
			const response = await fetch(`/api/documents/load?path=${encodeURIComponent(path)}`);
			const result = await response.json();

			if (!response.ok) {
				error = result.detail || 'Failed to load file';
				return;
			}

			onOpenFile(result.path, result.content, result.title);
		} catch (err) {
			error = 'Failed to load file';
		}
	}

	async function createFile() {
		if (!newItemName.trim()) return;

		isCreating = true;
		try {
			const response = await fetch('/api/documents/create-file', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ path: currentPath, name: newItemName.trim() })
			});

			const result = await response.json();

			if (response.ok && result.success) {
				showCreateFileDialog = false;
				newItemName = '';
				await loadDirectory(currentPath);
				// Open the newly created file
				openFile(result.path);
			} else {
				error = result.detail || 'Failed to create file';
			}
		} catch (err) {
			error = 'Failed to create file';
		} finally {
			isCreating = false;
		}
	}

	async function createDirectory() {
		if (!newItemName.trim()) return;

		isCreating = true;
		try {
			const response = await fetch('/api/documents/create-directory', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ path: currentPath, name: newItemName.trim() })
			});

			const result = await response.json();

			if (response.ok && result.success) {
				showCreateDirDialog = false;
				newItemName = '';
				await loadDirectory(currentPath);
			} else {
				error = result.detail || 'Failed to create directory';
			}
		} catch (err) {
			error = 'Failed to create directory';
		} finally {
			isCreating = false;
		}
	}

	function saveCurrentHere() {
		if (currentDocument && onSaveCurrentDocument) {
			const fileName = currentDocument.title.replace(/[^a-zA-Z0-9_-]/g, '_') + '.md';
			const fullPath = `${currentPath}/${fileName}`;
			onSaveCurrentDocument(fullPath);
		}
	}

	function navigateTo(path: string) {
		loadDirectory(path);
	}

	function goUp() {
		if (parentPath) {
			loadDirectory(parentPath);
		}
	}

	function goToPath() {
		if (pathInput.trim()) {
			loadDirectory(pathInput.trim());
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && e.target instanceof HTMLInputElement) {
			if (showCreateFileDialog) createFile();
			else if (showCreateDirDialog) createDirectory();
			else goToPath();
		}
		if (e.key === 'Escape') {
			showCreateFileDialog = false;
			showCreateDirDialog = false;
			showSaveAsDialog = false;
			newItemName = '';
		}
	}

	function formatDate(isoString: string): string {
		const date = new Date(isoString);
		const now = new Date();
		const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

		if (diffDays === 0) return 'Today';
		if (diffDays === 1) return 'Yesterday';
		if (diffDays < 7) return `${diffDays}d ago`;
		return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
	}

	$effect(() => {
		loadDirectory('~');
	});
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="navigator-panel">
	<header class="navigator-header">
		<h3>Documents</h3>
		<button class="close-btn" onclick={onClose} title="Close panel">
			<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<line x1="18" y1="6" x2="6" y2="18"/>
				<line x1="6" y1="6" x2="18" y2="18"/>
			</svg>
		</button>
	</header>

	<div class="toolbar">
		<button
			class="tool-btn"
			onclick={() => { showCreateFileDialog = true; newItemName = ''; }}
			title="New file"
		>
			<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
				<polyline points="14 2 14 8 20 8"/>
				<line x1="12" y1="18" x2="12" y2="12"/>
				<line x1="9" y1="15" x2="15" y2="15"/>
			</svg>
			<span>File</span>
		</button>
		<button
			class="tool-btn"
			onclick={() => { showCreateDirDialog = true; newItemName = ''; }}
			title="New folder"
		>
			<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
				<line x1="12" y1="11" x2="12" y2="17"/>
				<line x1="9" y1="14" x2="15" y2="14"/>
			</svg>
			<span>Folder</span>
		</button>
		{#if currentDocument && onSaveCurrentDocument}
			<button
				class="tool-btn save-btn"
				onclick={saveCurrentHere}
				title="Save current document here"
			>
				<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
					<polyline points="17 21 17 13 7 13 7 21"/>
					<polyline points="7 3 7 8 15 8"/>
				</svg>
				<span>Save Here</span>
			</button>
		{/if}
	</div>

	<div class="path-bar">
		<button class="nav-btn" onclick={goUp} disabled={!parentPath} title="Go up">
			<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<polyline points="15 18 9 12 15 6"/>
			</svg>
		</button>
		<input
			type="text"
			class="path-input"
			bind:value={pathInput}
			onkeydown={(e) => e.key === 'Enter' && goToPath()}
			placeholder="Path..."
		/>
		<button class="nav-btn" onclick={() => loadDirectory(currentPath)} title="Refresh">
			<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<polyline points="23 4 23 10 17 10"/>
				<path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
			</svg>
		</button>
	</div>

	<!-- Create File Dialog -->
	{#if showCreateFileDialog}
		<div class="inline-dialog">
			<input
				type="text"
				bind:value={newItemName}
				placeholder="filename.md"
				class="dialog-input"
				autofocus
			/>
			<button class="dialog-btn confirm" onclick={createFile} disabled={isCreating || !newItemName.trim()}>
				{isCreating ? '...' : 'Create'}
			</button>
			<button class="dialog-btn cancel" onclick={() => { showCreateFileDialog = false; newItemName = ''; }}>
				Cancel
			</button>
		</div>
	{/if}

	<!-- Create Directory Dialog -->
	{#if showCreateDirDialog}
		<div class="inline-dialog">
			<input
				type="text"
				bind:value={newItemName}
				placeholder="folder name"
				class="dialog-input"
				autofocus
			/>
			<button class="dialog-btn confirm" onclick={createDirectory} disabled={isCreating || !newItemName.trim()}>
				{isCreating ? '...' : 'Create'}
			</button>
			<button class="dialog-btn cancel" onclick={() => { showCreateDirDialog = false; newItemName = ''; }}>
				Cancel
			</button>
		</div>
	{/if}

	<div class="file-list">
		{#if isLoading}
			<div class="status-msg">Loading...</div>
		{:else if error}
			<div class="status-msg error">{error}</div>
		{:else}
			{#if directories.length === 0 && files.length === 0}
				<div class="status-msg">No markdown files here</div>
			{/if}

			{#each directories as dir}
				<button class="file-item dir" onclick={() => navigateTo(dir.path)}>
					<svg class="item-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
					</svg>
					<span class="item-name">{dir.name}</span>
				</button>
			{/each}

			{#each files as file}
				<button class="file-item" ondblclick={() => openFile(file.path)}>
					<svg class="item-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
						<polyline points="14 2 14 8 20 8"/>
					</svg>
					<span class="item-name">{file.name}</span>
					{#if file.modified}
						<span class="item-date">{formatDate(file.modified)}</span>
					{/if}
				</button>
			{/each}
		{/if}
	</div>

	<footer class="navigator-footer">
		<span class="hint">Double-click to open</span>
	</footer>
</div>

<style>
	.navigator-panel {
		position: fixed;
		top: 80px;
		left: 0;
		width: 260px;
		height: calc(100vh - 80px);
		background: white;
		border-right: 1px solid #e5e7eb;
		display: flex;
		flex-direction: column;
		z-index: 100;
		box-shadow: 4px 0 12px rgba(0, 0, 0, 0.05);
	}

	.navigator-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 10px 12px;
		border-bottom: 1px solid #e5e7eb;
		background: #f9fafb;
	}
	.navigator-header h3 {
		margin: 0;
		font-size: 0.85rem;
		font-weight: 600;
		color: #374151;
	}
	.close-btn {
		width: 24px;
		height: 24px;
		border: none;
		background: none;
		cursor: pointer;
		color: #9ca3af;
		border-radius: 4px;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.close-btn:hover {
		background: #e5e7eb;
		color: #374151;
	}

	.toolbar {
		display: flex;
		gap: 4px;
		padding: 8px 10px;
		border-bottom: 1px solid #e5e7eb;
		background: #fafafa;
	}

	.tool-btn {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 5px 8px;
		border: 1px solid #e5e7eb;
		background: white;
		border-radius: 4px;
		cursor: pointer;
		font-size: 0.7rem;
		color: #6b7280;
	}
	.tool-btn:hover {
		background: #f3f4f6;
		color: #374151;
		border-color: #d1d5db;
	}
	.tool-btn.save-btn {
		margin-left: auto;
		color: #5c7a99;
		border-color: #5c7a99;
	}
	.tool-btn.save-btn:hover {
		background: color-mix(in srgb, #5c7a99 10%, white);
	}

	.path-bar {
		display: flex;
		gap: 4px;
		padding: 8px 10px;
		border-bottom: 1px solid #e5e7eb;
		background: white;
	}
	.nav-btn {
		width: 28px;
		height: 28px;
		border: 1px solid #e5e7eb;
		background: white;
		border-radius: 4px;
		cursor: pointer;
		color: #6b7280;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}
	.nav-btn:hover:not(:disabled) {
		background: #f3f4f6;
		color: #374151;
	}
	.nav-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
	.path-input {
		flex: 1;
		padding: 5px 8px;
		border: 1px solid #e5e7eb;
		border-radius: 4px;
		font-size: 0.7rem;
		font-family: 'SF Mono', monospace;
		min-width: 0;
	}
	.path-input:focus {
		outline: none;
		border-color: #5c7a99;
	}

	.inline-dialog {
		display: flex;
		gap: 4px;
		padding: 8px 10px;
		background: #fffef5;
		border-bottom: 1px solid #fef3c7;
	}
	.dialog-input {
		flex: 1;
		padding: 5px 8px;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		font-size: 0.75rem;
		min-width: 0;
	}
	.dialog-input:focus {
		outline: none;
		border-color: #5c7a99;
	}
	.dialog-btn {
		padding: 5px 10px;
		border: none;
		border-radius: 4px;
		font-size: 0.7rem;
		cursor: pointer;
	}
	.dialog-btn.confirm {
		background: #5c7a99;
		color: white;
	}
	.dialog-btn.confirm:hover:not(:disabled) {
		background: color-mix(in srgb, #5c7a99 85%, #111827);
	}
	.dialog-btn.confirm:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	.dialog-btn.cancel {
		background: #e5e7eb;
		color: #6b7280;
	}
	.dialog-btn.cancel:hover {
		background: #d1d5db;
	}

	.file-list {
		flex: 1;
		overflow-y: auto;
		padding: 6px;
	}

	.status-msg {
		padding: 20px;
		text-align: center;
		color: #9ca3af;
		font-size: 0.8rem;
	}
	.status-msg.error {
		color: #dc2626;
	}

	.file-item {
		display: flex;
		align-items: center;
		gap: 8px;
		width: 100%;
		padding: 7px 10px;
		border: none;
		background: none;
		cursor: pointer;
		border-radius: 5px;
		text-align: left;
		font-size: 0.8rem;
		color: #374151;
	}
	.file-item:hover {
		background: #f3f4f6;
	}
	.file-item.dir {
		color: #5c7a99;
	}
	.file-item.dir:hover {
		background: color-mix(in srgb, #5c7a99 8%, white);
	}

	.item-icon {
		flex-shrink: 0;
		opacity: 0.6;
	}
	.file-item.dir .item-icon {
		opacity: 0.8;
	}

	.item-name {
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.item-date {
		font-size: 0.65rem;
		color: #9ca3af;
		flex-shrink: 0;
	}

	.navigator-footer {
		padding: 8px 12px;
		border-top: 1px solid #e5e7eb;
		background: #f9fafb;
	}
	.hint {
		font-size: 0.7rem;
		color: #9ca3af;
	}
</style>

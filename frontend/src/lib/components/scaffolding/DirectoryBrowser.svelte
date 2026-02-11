<script lang="ts">
	interface Directory {
		name: string;
		path: string;
	}

	let {
		onSelect,
		onClose,
	}: {
		onSelect: (path: string) => void;
		onClose: () => void;
	} = $props();

	let currentPath = $state('~');
	let parentPath = $state<string | null>(null);
	let directories = $state<Directory[]>([]);
	let isLoading = $state(true);
	let error = $state('');
	let pathInput = $state('~');

	async function loadDirectories(path: string) {
		isLoading = true;
		error = '';

		try {
			const response = await fetch(`/api/scaffolding/list-directories?path=${encodeURIComponent(path)}`);
			const result = await response.json();

			if (!response.ok) {
				error = result.detail || 'Failed to load directories';
				return;
			}

			currentPath = result.current;
			parentPath = result.parent;
			directories = result.directories;
			pathInput = result.current;
		} catch (err) {
			error = 'Failed to connect to server';
		} finally {
			isLoading = false;
		}
	}

	function navigateTo(path: string) {
		loadDirectories(path);
	}

	function goUp() {
		if (parentPath) {
			loadDirectories(parentPath);
		}
	}

	function goToPath() {
		if (pathInput.trim()) {
			loadDirectories(pathInput.trim());
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			onClose();
		} else if (e.key === 'Enter' && e.target instanceof HTMLInputElement) {
			goToPath();
		}
	}

	function selectCurrent() {
		onSelect(currentPath);
	}

	// Load initial directory
	$effect(() => {
		loadDirectories('~');
	});
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="modal-overlay" onclick={onClose} role="dialog" aria-modal="true">
	<div class="browser-modal" onclick={(e) => e.stopPropagation()} role="document">
		<header class="browser-header">
			<h2>Select Directory</h2>
			<button class="close-btn" onclick={onClose}>×</button>
		</header>

		<div class="path-bar">
			<input
				type="text"
				class="path-input"
				bind:value={pathInput}
				onkeydown={(e) => e.key === 'Enter' && goToPath()}
				placeholder="Enter path..."
			/>
			<button class="go-btn" onclick={goToPath}>Go</button>
		</div>

		<div class="browser-content">
			{#if isLoading}
				<div class="loading">Loading...</div>
			{:else if error}
				<div class="error">{error}</div>
			{:else}
				<div class="directory-list">
					{#if parentPath}
						<button class="dir-item parent" onclick={goUp}>
							<span class="dir-icon">⬆️</span>
							<span class="dir-name">..</span>
						</button>
					{/if}

					{#if directories.length === 0}
						<p class="empty">No subdirectories</p>
					{:else}
						{#each directories as dir}
							<button class="dir-item" onclick={() => navigateTo(dir.path)}>
								<span class="dir-icon">📁</span>
								<span class="dir-name">{dir.name}</span>
							</button>
						{/each}
					{/if}
				</div>
			{/if}
		</div>

		<footer class="browser-footer">
			<div class="selected-path">
				<span class="label">Selected:</span>
				<span class="path">{currentPath}</span>
			</div>
			<div class="footer-actions">
				<button class="btn-cancel" onclick={onClose}>Cancel</button>
				<button class="btn-select" onclick={selectCurrent}>Select This Folder</button>
			</div>
		</footer>
	</div>
</div>

<style>
	.modal-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}

	.browser-modal {
		background: white;
		border-radius: 12px;
		width: 90%;
		max-width: 600px;
		max-height: 80vh;
		display: flex;
		flex-direction: column;
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
	}

	.browser-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 16px 20px;
		border-bottom: 1px solid #e5e7eb;
	}
	.browser-header h2 {
		margin: 0;
		font-size: 1.1rem;
		font-weight: 600;
	}

	.close-btn {
		width: 32px;
		height: 32px;
		border: none;
		background: none;
		font-size: 1.5rem;
		color: #9ca3af;
		cursor: pointer;
		border-radius: 6px;
	}
	.close-btn:hover {
		background: #f3f4f6;
		color: #374151;
	}

	.path-bar {
		display: flex;
		gap: 8px;
		padding: 12px 20px;
		background: #f9fafb;
		border-bottom: 1px solid #e5e7eb;
	}
	.path-input {
		flex: 1;
		padding: 8px 12px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 0.85rem;
		font-family: 'SF Mono', monospace;
	}
	.path-input:focus {
		outline: none;
		border-color: #5c7a99;
	}
	.go-btn {
		padding: 8px 16px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		background: white;
		cursor: pointer;
		font-size: 0.85rem;
	}
	.go-btn:hover {
		background: #f3f4f6;
	}

	.browser-content {
		flex: 1;
		overflow-y: auto;
		min-height: 300px;
		max-height: 400px;
	}

	.loading, .error, .empty {
		padding: 40px 20px;
		text-align: center;
		color: #6b7280;
	}
	.error {
		color: #dc2626;
	}

	.directory-list {
		padding: 8px;
	}

	.dir-item {
		display: flex;
		align-items: center;
		gap: 10px;
		width: 100%;
		padding: 10px 12px;
		border: none;
		background: none;
		cursor: pointer;
		border-radius: 6px;
		text-align: left;
		font-size: 0.9rem;
	}
	.dir-item:hover {
		background: #f3f4f6;
	}
	.dir-item.parent {
		color: #6b7280;
		border-bottom: 1px solid #e5e7eb;
		margin-bottom: 4px;
		border-radius: 0;
	}

	.dir-icon {
		font-size: 1.1rem;
	}
	.dir-name {
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.browser-footer {
		padding: 16px 20px;
		border-top: 1px solid #e5e7eb;
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.selected-path {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 8px 12px;
		background: #f3f4f6;
		border-radius: 6px;
		font-size: 0.8rem;
		overflow: hidden;
	}
	.selected-path .label {
		color: #6b7280;
		flex-shrink: 0;
	}
	.selected-path .path {
		font-family: 'SF Mono', monospace;
		color: #374151;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.footer-actions {
		display: flex;
		justify-content: flex-end;
		gap: 10px;
	}

	.btn-cancel {
		padding: 8px 16px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		background: white;
		color: #374151;
		font-size: 0.85rem;
		cursor: pointer;
	}
	.btn-cancel:hover {
		background: #f3f4f6;
	}

	.btn-select {
		padding: 8px 20px;
		border: none;
		border-radius: 6px;
		background: #5c7a99;
		color: white;
		font-size: 0.85rem;
		cursor: pointer;
	}
	.btn-select:hover {
		background: color-mix(in srgb, #5c7a99 85%, #111827);
	}
</style>

<script lang="ts">
	import { workspaces, setActiveWorkspace, loadWorkspaces } from '$lib/stores/workspaces';
	import { createWorkspace, deleteWorkspace } from '$lib/api/workspaces';
	import { onMount } from 'svelte';

	let newName = $state('');
	let creating = $state(false);

	function formatRelativeTime(dateStr: string): string {
		const date = new Date(dateStr);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.floor(diffMs / 60000);
		const diffHours = Math.floor(diffMs / 3600000);
		const diffDays = Math.floor(diffMs / 86400000);

		if (diffMins < 1) return 'just now';
		if (diffMins < 60) return `${diffMins}m ago`;
		if (diffHours < 24) return `${diffHours}h ago`;
		if (diffDays === 1) return 'yesterday';
		if (diffDays < 7) return `${diffDays}d ago`;
		return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
	}

	async function handleCreate() {
		if (!newName.trim()) return;
		creating = true;
		try {
			const ws = await createWorkspace({ name: newName.trim() });
			newName = '';
			await setActiveWorkspace(ws.id);
		} catch (e) {
			console.error('Failed to create workspace:', e);
		} finally {
			creating = false;
		}
	}

	async function handleDelete(id: number, e: MouseEvent) {
		e.stopPropagation();
		if (!confirm('Delete this workspace? This cannot be undone.')) return;
		try {
			await deleteWorkspace(id);
			await loadWorkspaces();
		} catch (err) {
			console.error('Failed to delete workspace:', err);
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') handleCreate();
	}

	onMount(() => {
		loadWorkspaces();
	});
</script>

<div class="launcher">
	<div class="launcher-inner">
		<h1 class="launcher-title">Workspaces</h1>
		<p class="launcher-subtitle">Resume a workspace or create a new one</p>

		<div class="create-row">
			<input
				type="text"
				class="create-input"
				placeholder="New workspace name..."
				bind:value={newName}
				onkeydown={handleKeydown}
			/>
			<button
				class="create-btn"
				onclick={handleCreate}
				disabled={creating || !newName.trim()}
			>
				Create
			</button>
		</div>

		{#if $workspaces.length > 0}
			<div class="workspace-list">
				{#each $workspaces as ws (ws.id)}
					<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
					<div class="workspace-card" onclick={() => setActiveWorkspace(ws.id)}>
						<div class="ws-info">
							<span class="ws-name">{ws.name}</span>
							{#if ws.description}
								<span class="ws-desc">{ws.description}</span>
							{/if}
						</div>
						<div class="ws-meta">
							<span class="ws-items">{ws.items.length} {ws.items.length === 1 ? 'item' : 'items'}</span>
							<span class="ws-time">{formatRelativeTime(ws.last_opened_at)}</span>
						</div>
						<button
							class="ws-delete"
							onclick={(e) => handleDelete(ws.id, e)}
							title="Delete workspace"
						>&times;</button>
					</div>
				{/each}
			</div>
		{:else}
			<p class="empty-msg">No workspaces yet. Create one to get started.</p>
		{/if}
	</div>
</div>

<style>
	.launcher {
		display: flex;
		justify-content: center;
		align-items: flex-start;
		padding: 60px 20px;
		height: 100%;
		overflow-y: auto;
	}
	.launcher-inner {
		max-width: 500px;
		width: 100%;
	}
	.launcher-title {
		font-size: 1.6rem;
		font-weight: 300;
		color: #374151;
		margin: 0 0 4px;
		text-align: center;
	}
	.launcher-subtitle {
		font-size: 0.85rem;
		color: #9ca3af;
		margin: 0 0 24px;
		text-align: center;
	}
	.create-row {
		display: flex;
		gap: 8px;
		margin-bottom: 24px;
	}
	.create-input {
		flex: 1;
		padding: 10px 14px;
		border: 1px solid #d1d5db;
		border-radius: 8px;
		font-size: 0.9rem;
		outline: none;
		transition: border-color 0.15s;
	}
	.create-input:focus {
		border-color: #6b7280;
	}
	.create-btn {
		padding: 10px 20px;
		border: none;
		border-radius: 8px;
		background: #374151;
		color: white;
		font-size: 0.85rem;
		font-weight: 500;
		cursor: pointer;
		transition: background 0.15s;
	}
	.create-btn:hover:not(:disabled) {
		background: #1f2937;
	}
	.create-btn:disabled {
		opacity: 0.5;
		cursor: default;
	}
	.workspace-list {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.workspace-card {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 14px 16px;
		border: 1px solid #e5e7eb;
		border-radius: 10px;
		background: white;
		cursor: pointer;
		transition: all 0.15s;
		text-align: left;
		width: 100%;
	}
	.workspace-card:hover {
		background: #f9fafb;
		border-color: #d1d5db;
	}
	.ws-info {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.ws-name {
		font-size: 0.95rem;
		font-weight: 500;
		color: #374151;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.ws-desc {
		font-size: 0.75rem;
		color: #9ca3af;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.ws-meta {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		gap: 2px;
		flex-shrink: 0;
	}
	.ws-items {
		font-size: 0.72rem;
		color: #6b7280;
	}
	.ws-time {
		font-size: 0.65rem;
		color: #9ca3af;
	}
	.ws-delete {
		flex-shrink: 0;
		width: 24px;
		height: 24px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: none;
		border-radius: 4px;
		background: transparent;
		color: #d1d5db;
		font-size: 1.1rem;
		cursor: pointer;
		transition: all 0.15s;
	}
	.ws-delete:hover {
		background: #fee2e2;
		color: #dc2626;
	}
	.empty-msg {
		font-size: 0.85rem;
		color: #9ca3af;
		text-align: center;
		padding: 32px 0;
	}
</style>

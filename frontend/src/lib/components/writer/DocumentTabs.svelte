<script lang="ts">
	import type { OpenDocument } from './types';

	let {
		documents,
		activeId,
		onSelect,
		onClose,
	}: {
		documents: OpenDocument[];
		activeId: string | null;
		onSelect: (id: string) => void;
		onClose: (id: string) => void;
	} = $props();
</script>

<div class="tabs-bar">
	{#if documents.length === 0}
		<span class="no-docs">No documents open</span>
	{:else}
		{#each documents as doc}
			<div
				class="tab"
				class:active={doc.id === activeId}
				onclick={() => onSelect(doc.id)}
				onkeydown={(e) => e.key === 'Enter' && onSelect(doc.id)}
				role="tab"
				tabindex="0"
			>
				<span class="tab-title">{doc.title}</span>
				{#if doc.hasChanges}
					<span class="unsaved-dot"></span>
				{/if}
				<button
					class="tab-close"
					onclick={(e) => { e.stopPropagation(); onClose(doc.id); }}
					title="Close"
				>
					<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
						<line x1="18" y1="6" x2="6" y2="18"/>
						<line x1="6" y1="6" x2="18" y2="18"/>
					</svg>
				</button>
			</div>
		{/each}
	{/if}
</div>

<style>
	.tabs-bar {
		display: flex;
		align-items: center;
		gap: 2px;
		padding: 4px 8px;
		background: #f3f4f6;
		border-top: 1px solid #e5e7eb;
		min-height: 32px;
		overflow-x: auto;
	}

	.no-docs {
		font-size: 0.75rem;
		color: #9ca3af;
		padding: 0 8px;
	}

	.tab {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 5px 8px 5px 12px;
		background: transparent;
		border-radius: 4px;
		cursor: pointer;
		font-size: 0.75rem;
		color: #6b7280;
		max-width: 160px;
		transition: all 0.1s;
		user-select: none;
	}
	.tab:hover {
		background: #e5e7eb;
		color: #374151;
	}
	.tab.active {
		background: white;
		color: #111827;
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
	}

	.tab-title {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.unsaved-dot {
		width: 6px;
		height: 6px;
		background: #f59e0b;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.tab-close {
		width: 16px;
		height: 16px;
		border: none;
		background: transparent;
		border-radius: 3px;
		cursor: pointer;
		color: #9ca3af;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		opacity: 0;
		transition: opacity 0.1s;
	}
	.tab:hover .tab-close {
		opacity: 1;
	}
	.tab-close:hover {
		background: #d1d5db;
		color: #374151;
	}
</style>

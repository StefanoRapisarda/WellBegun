<script lang="ts">
	import TreeEditor from './TreeEditor.svelte';

	interface TreeNode {
		id: string;
		name: string;
		type: 'file' | 'directory';
		description: string;
		content: string;
		children: TreeNode[];
		expanded: boolean;
	}

	let {
		tree,
		selectedNode,
		onSelect,
		onUpdate,
		onDelete,
		onAddChild,
		level = 0,
	}: {
		tree: TreeNode[];
		selectedNode: TreeNode | null;
		onSelect: (node: TreeNode | null) => void;
		onUpdate: (nodeId: string, updates: Partial<TreeNode>) => void;
		onDelete: (nodeId: string) => void;
		onAddChild: (parentId: string, type: 'file' | 'directory') => void;
		level?: number;
	} = $props();

	function toggleExpand(node: TreeNode) {
		onUpdate(node.id, { expanded: !node.expanded });
	}

	function handleKeydown(e: KeyboardEvent, node: TreeNode) {
		if (e.key === 'Delete' || e.key === 'Backspace') {
			if (e.target === e.currentTarget) {
				e.preventDefault();
				onDelete(node.id);
			}
		}
	}
</script>

<ul class="tree-list" style:--level={level}>
	{#each tree as node (node.id)}
		<li class="tree-node" class:selected={selectedNode?.id === node.id}>
			<div
				class="node-row"
				onclick={() => onSelect(node)}
				onkeydown={(e) => handleKeydown(e, node)}
				tabindex="0"
				role="treeitem"
				aria-selected={selectedNode?.id === node.id}
			>
				{#if node.type === 'directory'}
					<button
						class="expand-btn"
						onclick={(e) => { e.stopPropagation(); toggleExpand(node); }}
						aria-label={node.expanded ? 'Collapse' : 'Expand'}
					>
						<svg
							width="12"
							height="12"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							class:rotated={node.expanded}
						>
							<polyline points="9 18 15 12 9 6"></polyline>
						</svg>
					</button>
				{:else}
					<span class="expand-placeholder"></span>
				{/if}

				<span class="node-icon">
					{#if node.type === 'directory'}
						{node.expanded ? '📂' : '📁'}
					{:else}
						📄
					{/if}
				</span>

				<span class="node-name" class:has-description={!!node.description}>
					{node.name}
				</span>

				{#if node.description}
					<span class="node-hint" title={node.description}>💬</span>
				{/if}
				{#if node.type === 'file' && node.content}
					<span class="node-hint" title="Has content">📝</span>
				{/if}

				<div class="node-actions">
					{#if node.type === 'directory'}
						<button
							class="action-btn"
							onclick={(e) => { e.stopPropagation(); onAddChild(node.id, 'directory'); }}
							title="Add folder"
						>
							+📁
						</button>
						<button
							class="action-btn"
							onclick={(e) => { e.stopPropagation(); onAddChild(node.id, 'file'); }}
							title="Add file"
						>
							+📄
						</button>
					{/if}
					<button
						class="action-btn delete"
						onclick={(e) => { e.stopPropagation(); onDelete(node.id); }}
						title="Delete"
					>
						×
					</button>
				</div>
			</div>

			{#if node.type === 'directory' && node.expanded && node.children.length > 0}
				<TreeEditor
					tree={node.children}
					{selectedNode}
					{onSelect}
					{onUpdate}
					{onDelete}
					{onAddChild}
					level={level + 1}
				/>
			{/if}
		</li>
	{/each}
</ul>

<style>
	.tree-list {
		list-style: none;
		margin: 0;
		padding: 0;
		padding-left: calc(var(--level) * 20px);
	}

	.tree-node {
		margin: 0;
	}

	.node-row {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 6px 12px;
		cursor: pointer;
		border-radius: 4px;
		transition: background 0.1s;
	}
	.node-row:hover {
		background: #f3f4f6;
	}
	.tree-node.selected > .node-row {
		background: color-mix(in srgb, #5c7a99 8%, white);
		outline: 1px solid color-mix(in srgb, #5c7a99 30%, #e5e7eb);
	}
	.node-row:focus {
		outline: 2px solid #5c7a99;
		outline-offset: -2px;
	}

	.expand-btn {
		width: 20px;
		height: 20px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: none;
		background: none;
		cursor: pointer;
		color: #9ca3af;
		padding: 0;
		border-radius: 4px;
	}
	.expand-btn:hover {
		background: #e5e7eb;
		color: #374151;
	}
	.expand-btn svg {
		transition: transform 0.15s;
	}
	.expand-btn svg.rotated {
		transform: rotate(90deg);
	}

	.expand-placeholder {
		width: 20px;
	}

	.node-icon {
		font-size: 0.9rem;
	}

	.node-name {
		flex: 1;
		font-size: 0.85rem;
		color: #374151;
	}
	.node-name.has-description {
		font-style: italic;
	}

	.node-hint {
		font-size: 0.7rem;
		opacity: 0.6;
	}

	.node-actions {
		display: flex;
		gap: 2px;
		opacity: 0;
		transition: opacity 0.15s;
	}
	.node-row:hover .node-actions {
		opacity: 1;
	}

	.action-btn {
		padding: 2px 6px;
		border: none;
		background: none;
		cursor: pointer;
		font-size: 0.7rem;
		border-radius: 4px;
		color: #6b7280;
	}
	.action-btn:hover {
		background: #e5e7eb;
	}
	.action-btn.delete {
		color: #ef4444;
		font-size: 1rem;
		font-weight: bold;
	}
	.action-btn.delete:hover {
		background: #fee2e2;
	}
</style>

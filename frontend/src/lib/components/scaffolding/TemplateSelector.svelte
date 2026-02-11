<script lang="ts">
	interface TreeNode {
		id: string;
		name: string;
		type: 'file' | 'directory';
		description: string;
		content: string;
		children: TreeNode[];
		expanded: boolean;
	}

	interface Template {
		name: string;
		description: string;
		creator: string;
		version: string;
		tree: TreeNode[];
		metadata: { author: string; projectName: string; description: string };
		isCustom: boolean;
	}

	let {
		templates,
		onSelect,
		onClose,
		onDelete,
	}: {
		templates: Template[];
		onSelect: (template: Template) => void;
		onClose: () => void;
		onDelete: (templateName: string) => Promise<void>;
	} = $props();

	let searchQuery = $state('');
	let filter = $state<'all' | 'default' | 'custom'>('all');
	let selectedTemplate = $state<Template | null>(null);
	let isDeleting = $state(false);

	async function handleDelete(templateName: string) {
		if (!confirm(`Are you sure you want to delete the template "${templateName}"?`)) {
			return;
		}
		isDeleting = true;
		try {
			await onDelete(templateName);
			if (selectedTemplate?.name === templateName) {
				selectedTemplate = null;
			}
		} finally {
			isDeleting = false;
		}
	}

	let filteredTemplates = $derived(() => {
		let result = templates;

		if (filter === 'default') {
			result = result.filter(t => !t.isCustom);
		} else if (filter === 'custom') {
			result = result.filter(t => t.isCustom);
		}

		if (searchQuery.trim()) {
			const query = searchQuery.toLowerCase();
			result = result.filter(
				t =>
					t.name.toLowerCase().includes(query) ||
					t.description.toLowerCase().includes(query) ||
					t.creator.toLowerCase().includes(query)
			);
		}

		return result;
	});

	function generateTreePreview(nodes: TreeNode[], prefix: string = ''): string {
		let result = '';
		for (let i = 0; i < nodes.length; i++) {
			const node = nodes[i];
			const isLast = i === nodes.length - 1;
			const connector = isLast ? '└── ' : '├── ';
			const icon = node.type === 'directory' ? '📁' : '📄';
			result += `${prefix}${connector}${icon} ${node.name}\n`;
			if (node.children && node.children.length > 0) {
				const childPrefix = prefix + (isLast ? '    ' : '│   ');
				result += generateTreePreview(node.children, childPrefix);
			}
		}
		return result;
	}

	function handleSelect() {
		if (selectedTemplate) {
			onSelect(selectedTemplate);
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			onClose();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="modal-overlay" onclick={onClose} role="dialog" aria-modal="true">
	<div class="modal-content" onclick={(e) => e.stopPropagation()} role="document">
		<header class="modal-header">
			<h2>Load Template</h2>
			<button class="close-btn" onclick={onClose}>×</button>
		</header>

		<div class="modal-body">
			<div class="search-bar">
				<input
					type="text"
					bind:value={searchQuery}
					placeholder="Search templates..."
					class="search-input"
				/>
				<div class="filter-tabs">
					<button
						class="filter-tab"
						class:active={filter === 'all'}
						onclick={() => filter = 'all'}
					>
						All
					</button>
					<button
						class="filter-tab"
						class:active={filter === 'default'}
						onclick={() => filter = 'default'}
					>
						Default
					</button>
					<button
						class="filter-tab"
						class:active={filter === 'custom'}
						onclick={() => filter = 'custom'}
					>
						Custom
					</button>
				</div>
			</div>

			<div class="template-layout">
				<div class="template-list">
					{#if filteredTemplates().length === 0}
						<p class="no-templates">No templates found</p>
					{:else}
						{#each filteredTemplates() as template}
							<div
								class="template-item"
								class:selected={selectedTemplate?.name === template.name}
							>
								<button
									class="template-item-content"
									onclick={() => selectedTemplate = template}
								>
									<div class="template-header">
										<div class="template-badge" class:custom={template.isCustom}>
											{template.isCustom ? 'Custom' : 'Default'}
										</div>
										{#if template.isCustom}
											<button
												class="delete-btn"
												onclick={(e) => { e.stopPropagation(); handleDelete(template.name); }}
												disabled={isDeleting}
												title="Delete template"
											>
												×
											</button>
										{/if}
									</div>
									<h4>{template.name}</h4>
									<p class="template-desc">{template.description}</p>
									<div class="template-meta">
										<span>by {template.creator}</span>
										<span>v{template.version}</span>
									</div>
								</button>
							</div>
						{/each}
					{/if}
				</div>

				<div class="template-preview">
					{#if selectedTemplate}
						<h3>{selectedTemplate.name}</h3>
						<p>{selectedTemplate.description}</p>
						<div class="preview-section">
							<h4>Structure</h4>
							<pre class="tree-preview">{generateTreePreview(selectedTemplate.tree)}</pre>
						</div>
						{#if selectedTemplate.metadata.author}
							<div class="preview-meta">
								<span>Default Author: {selectedTemplate.metadata.author}</span>
							</div>
						{/if}
					{:else}
						<p class="no-selection">Select a template to preview</p>
					{/if}
				</div>
			</div>
		</div>

		<footer class="modal-footer">
			<button class="btn-cancel" onclick={onClose}>Cancel</button>
			<button
				class="btn-apply"
				onclick={handleSelect}
				disabled={!selectedTemplate}
			>
				Apply Template
			</button>
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

	.modal-content {
		background: white;
		border-radius: 12px;
		width: 90%;
		max-width: 900px;
		max-height: 80vh;
		display: flex;
		flex-direction: column;
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
	}

	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 16px 20px;
		border-bottom: 1px solid #e5e7eb;
	}
	.modal-header h2 {
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

	.modal-body {
		flex: 1;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		padding: 16px 20px;
	}

	.search-bar {
		display: flex;
		gap: 12px;
		margin-bottom: 16px;
	}
	.search-input {
		flex: 1;
		padding: 8px 14px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 0.85rem;
	}
	.search-input:focus {
		outline: none;
		border-color: #5c7a99;
	}

	.filter-tabs {
		display: flex;
		background: #f3f4f6;
		border-radius: 6px;
		padding: 3px;
	}
	.filter-tab {
		padding: 6px 14px;
		border: none;
		border-radius: 4px;
		background: transparent;
		font-size: 0.8rem;
		cursor: pointer;
		color: #6b7280;
	}
	.filter-tab:hover {
		color: #374151;
	}
	.filter-tab.active {
		background: white;
		color: #111827;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	.template-layout {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 16px;
		flex: 1;
		min-height: 0;
		overflow: hidden;
	}

	.template-list {
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.no-templates {
		text-align: center;
		color: #9ca3af;
		padding: 40px 20px;
	}

	.template-item {
		border: 1px solid #e5e7eb;
		border-radius: 8px;
		background: white;
		transition: all 0.15s;
	}
	.template-item:hover {
		border-color: #d1d5db;
		background: #f9fafb;
	}
	.template-item.selected {
		border-color: #5c7a99;
		background: color-mix(in srgb, #5c7a99 8%, white);
	}

	.template-item-content {
		display: block;
		width: 100%;
		text-align: left;
		padding: 12px 16px;
		border: none;
		background: none;
		cursor: pointer;
	}

	.template-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
	}

	.delete-btn {
		width: 24px;
		height: 24px;
		border: none;
		background: none;
		color: #9ca3af;
		font-size: 1.2rem;
		font-weight: bold;
		cursor: pointer;
		border-radius: 4px;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.delete-btn:hover:not(:disabled) {
		background: #fee2e2;
		color: #dc2626;
	}
	.delete-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.template-item h4 {
		margin: 4px 0;
		font-size: 0.9rem;
		font-weight: 600;
	}
	.template-desc {
		margin: 4px 0;
		font-size: 0.8rem;
		color: #6b7280;
	}
	.template-meta {
		display: flex;
		gap: 12px;
		font-size: 0.7rem;
		color: #9ca3af;
		margin-top: 8px;
	}

	.template-badge {
		display: inline-block;
		padding: 2px 8px;
		font-size: 0.65rem;
		font-weight: 600;
		border-radius: 10px;
		background: #e5e7eb;
		color: #6b7280;
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}
	.template-badge.custom {
		background: #fef3c7;
		color: #92400e;
	}

	.template-preview {
		overflow-y: auto;
		padding: 16px;
		background: #f9fafb;
		border-radius: 8px;
	}
	.template-preview h3 {
		margin: 0 0 8px;
		font-size: 1rem;
		font-weight: 600;
	}
	.template-preview > p {
		margin: 0 0 16px;
		font-size: 0.85rem;
		color: #6b7280;
	}

	.preview-section h4 {
		margin: 0 0 8px;
		font-size: 0.8rem;
		font-weight: 600;
		color: #374151;
	}

	.tree-preview {
		background: white;
		padding: 12px;
		border-radius: 6px;
		font-family: 'SF Mono', monospace;
		font-size: 0.75rem;
		line-height: 1.6;
		overflow-x: auto;
		margin: 0;
	}

	.preview-meta {
		margin-top: 12px;
		font-size: 0.75rem;
		color: #6b7280;
	}

	.no-selection {
		text-align: center;
		color: #9ca3af;
		padding: 40px 20px;
	}

	.modal-footer {
		display: flex;
		justify-content: flex-end;
		gap: 10px;
		padding: 16px 20px;
		border-top: 1px solid #e5e7eb;
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

	.btn-apply {
		padding: 8px 20px;
		border: none;
		border-radius: 6px;
		background: #5c7a99;
		color: white;
		font-size: 0.85rem;
		cursor: pointer;
	}
	.btn-apply:hover:not(:disabled) {
		background: color-mix(in srgb, #5c7a99 85%, #111827);
	}
	.btn-apply:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
</style>

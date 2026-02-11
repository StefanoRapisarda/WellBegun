<script lang="ts">
	import { onMount } from 'svelte';
	import TreeEditor from './TreeEditor.svelte';
	import TemplateSelector from './TemplateSelector.svelte';
	import TemplateDialog from './TemplateDialog.svelte';
	import DirectoryBrowser from './DirectoryBrowser.svelte';
	import MarkdownPreview from '../writer/MarkdownPreview.svelte';

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

	// Project metadata
	let author = $state('');
	let projectName = $state('');
	let projectDescription = $state('');
	let outputPath = $state('');
	let additionalReadmeContent = $state('');
	let showDirectoryBrowser = $state(false);
	let showReadmePreview = $state(false);

	function handleDirectorySelect(path: string) {
		outputPath = path;
		showDirectoryBrowser = false;
	}

	// Tree state
	let tree = $state<TreeNode[]>([]);

	// Templates
	let templates = $state<Template[]>([]);
	let showTemplateDialog = $state(false);
	let showTemplateSelector = $state(false);

	// UI state
	let selectedNode = $state<TreeNode | null>(null);
	let isCreating = $state(false);
	let createResult = $state<{ success: boolean; message: string } | null>(null);
	let validationErrors = $state<string[]>([]);

	// Edit form state - local copies that sync with tree
	let editName = $state('');
	let editDescription = $state('');
	let editContent = $state('');
	let editingNodeId = $state<string | null>(null);

	// Sync local edit state when selection changes
	$effect(() => {
		if (selectedNode && selectedNode.id !== editingNodeId) {
			editName = selectedNode.name;
			editDescription = selectedNode.description;
			editContent = selectedNode.content;
			editingNodeId = selectedNode.id;
		} else if (!selectedNode) {
			editName = '';
			editDescription = '';
			editContent = '';
			editingNodeId = null;
		}
	});

	// Update tree when edit fields change
	function syncName(value: string) {
		editName = value;
		if (editingNodeId) {
			updateNode(editingNodeId, { name: value });
		}
	}

	function syncDescription(value: string) {
		editDescription = value;
		if (editingNodeId) {
			updateNode(editingNodeId, { description: value });
		}
	}

	function syncContent(value: string) {
		editContent = value;
		if (editingNodeId) {
			updateNode(editingNodeId, { content: value });
		}
	}

	function generateId(): string {
		return Math.random().toString(36).substring(2, 9);
	}

	function generateUniqueName(baseName: string, type: 'file' | 'directory', siblings: TreeNode[]): string {
		// Get existing names of same type at this level
		const existingNames = new Set(
			siblings.filter(n => n.type === type).map(n => n.name)
		);

		if (!existingNames.has(baseName)) {
			return baseName;
		}

		// For files, handle extension separately
		let nameWithoutExt = baseName;
		let ext = '';
		if (type === 'file') {
			const lastDot = baseName.lastIndexOf('.');
			if (lastDot > 0) {
				nameWithoutExt = baseName.substring(0, lastDot);
				ext = baseName.substring(lastDot);
			}
		}

		// Find the next available number
		let counter = 2;
		while (existingNames.has(`${nameWithoutExt}${counter}${ext}`)) {
			counter++;
		}

		return `${nameWithoutExt}${counter}${ext}`;
	}

	function createNode(name: string, type: 'file' | 'directory'): TreeNode {
		return {
			id: generateId(),
			name,
			type,
			description: '',
			content: '',
			children: [],
			expanded: true,
		};
	}

	function addRootNode(type: 'file' | 'directory') {
		const baseName = type === 'directory' ? 'new_folder' : 'new_file.txt';
		const name = generateUniqueName(baseName, type, tree);
		tree = [...tree, createNode(name, type)];
	}

	function addNodeContextual(type: 'file' | 'directory') {
		// If a directory is selected, add as child of that directory
		if (selectedNode && selectedNode.type === 'directory') {
			addChild(selectedNode.id, type);
		} else {
			// Otherwise add to root
			addRootNode(type);
		}
	}

	function addChild(parentId: string, type: 'file' | 'directory') {
		const baseName = type === 'directory' ? 'new_folder' : 'new_file.txt';

		function addToParent(nodes: TreeNode[]): TreeNode[] {
			return nodes.map(node => {
				if (node.id === parentId) {
					const name = generateUniqueName(baseName, type, node.children);
					return {
						...node,
						children: [...node.children, createNode(name, type)],
						expanded: true,
					};
				}
				if (node.children.length > 0) {
					return { ...node, children: addToParent(node.children) };
				}
				return node;
			});
		}

		tree = addToParent(tree);
	}

	function updateNode(nodeId: string, updates: Partial<TreeNode>) {
		function update(nodes: TreeNode[]): TreeNode[] {
			return nodes.map(node => {
				if (node.id === nodeId) {
					return { ...node, ...updates };
				}
				if (node.children.length > 0) {
					return { ...node, children: update(node.children) };
				}
				return node;
			});
		}

		tree = update(tree);
		if (selectedNode?.id === nodeId) {
			selectedNode = { ...selectedNode, ...updates };
		}
	}

	function deleteNode(nodeId: string) {
		function remove(nodes: TreeNode[]): TreeNode[] {
			return nodes
				.filter(node => node.id !== nodeId)
				.map(node => ({
					...node,
					children: remove(node.children),
				}));
		}

		tree = remove(tree);
		if (selectedNode?.id === nodeId) {
			selectedNode = null;
		}
	}

	function selectNode(node: TreeNode | null) {
		selectedNode = node;
	}

	// Validation
	function validateTree(): string[] {
		const errors: string[] = [];

		function checkDuplicates(nodes: TreeNode[], path: string) {
			const names = new Map<string, number>();
			for (const node of nodes) {
				const key = `${node.type}:${node.name}`;
				names.set(key, (names.get(key) || 0) + 1);
			}
			for (const [key, count] of names) {
				if (count > 1) {
					const [type, name] = key.split(':');
					errors.push(`Duplicate ${type} "${name}" in ${path || 'root'}`);
				}
			}
			for (const node of nodes) {
				if (node.type === 'directory' && node.children.length > 0) {
					checkDuplicates(node.children, path ? `${path}/${node.name}` : node.name);
				}
			}
		}

		checkDuplicates(tree, '');

		if (!projectName.trim()) {
			errors.push('Project name is required');
		}
		if (!outputPath.trim()) {
			errors.push('Output path is required');
		}
		if (tree.length === 0) {
			errors.push('At least one file or directory is required');
		}

		return errors;
	}

	// Generate README content
	function generateReadme(): string {
		let readme = `# ${projectName}\n\n`;

		if (author) {
			readme += `**Author:** ${author}\n\n`;
		}

		readme += `## Project Description\n\n${projectDescription || 'No description provided.'}\n\n`;

		readme += `## Directory Tree\n\n\`\`\`\n`;
		readme += generateTreeString(tree, '');
		readme += `\`\`\`\n\n`;

		const directories: { path: string; description: string }[] = [];
		const files: { path: string; description: string }[] = [];

		function collectDescriptions(nodes: TreeNode[], path: string) {
			for (const node of nodes) {
				const nodePath = path ? `${path}/${node.name}` : node.name;
				if (node.description) {
					if (node.type === 'directory') {
						directories.push({ path: nodePath, description: node.description });
					} else {
						files.push({ path: nodePath, description: node.description });
					}
				}
				if (node.children.length > 0) {
					collectDescriptions(node.children, nodePath);
				}
			}
		}

		collectDescriptions(tree, '');

		if (directories.length > 0) {
			readme += `## Directories\n\n`;
			for (const dir of directories) {
				readme += `- **${dir.path}/**: ${dir.description}\n`;
			}
			readme += '\n';
		}

		if (files.length > 0) {
			readme += `## Files\n\n`;
			for (const file of files) {
				readme += `- **${file.path}**: ${file.description}\n`;
			}
			readme += '\n';
		}

		// Add additional custom content
		if (additionalReadmeContent.trim()) {
			readme += `${additionalReadmeContent.trim()}\n`;
		}

		return readme;
	}

	function generateTreeString(nodes: TreeNode[], prefix: string): string {
		let result = '';
		for (let i = 0; i < nodes.length; i++) {
			const node = nodes[i];
			const isLast = i === nodes.length - 1;
			const connector = isLast ? '└── ' : '├── ';
			const suffix = node.type === 'directory' ? '/' : '';
			result += `${prefix}${connector}${node.name}${suffix}\n`;

			if (node.children.length > 0) {
				const childPrefix = prefix + (isLast ? '    ' : '│   ');
				result += generateTreeString(node.children, childPrefix);
			}
		}
		return result;
	}

	// Create project
	async function createProject() {
		validationErrors = validateTree();
		if (validationErrors.length > 0) {
			return;
		}

		isCreating = true;
		createResult = null;

		try {
			const response = await fetch('/api/scaffolding/create', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					outputPath,
					projectName,
					tree,
					readme: generateReadme(),
				}),
			});

			const result = await response.json();
			createResult = result;

			if (result.success) {
				showTemplateDialog = true;
			}
		} catch (error) {
			createResult = { success: false, message: 'Failed to create project' };
		} finally {
			isCreating = false;
		}
	}

	// Template functions
	async function loadTemplates() {
		try {
			const response = await fetch('/api/scaffolding/templates');
			templates = await response.json();
		} catch (error) {
			console.error('Failed to load templates:', error);
		}
	}

	function applyTemplate(template: Template) {
		author = template.metadata.author || '';
		projectName = template.metadata.projectName || '';
		projectDescription = template.metadata.description || '';
		tree = JSON.parse(JSON.stringify(template.tree)); // Deep clone
		showTemplateSelector = false;
	}

	async function saveAsTemplate(templateData: { name: string; description: string; creator: string; version: string }) {
		try {
			const response = await fetch('/api/scaffolding/templates', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					...templateData,
					tree,
					metadata: { author, projectName, projectDescription },
				}),
			});

			const result = await response.json();
			if (result.success) {
				await loadTemplates();
			}
			return result;
		} catch (error) {
			return { success: false, message: 'Failed to save template' };
		}
	}

	async function deleteTemplate(templateName: string) {
		try {
			const response = await fetch(`/api/scaffolding/templates/${encodeURIComponent(templateName)}`, {
				method: 'DELETE',
			});

			if (response.ok) {
				await loadTemplates();
			}
		} catch (error) {
			console.error('Failed to delete template:', error);
		}
	}

	// Parse tree from text input
	function parseTreeText(text: string): TreeNode[] {
		const lines = text.split('\n').filter(line => line.trim());
		const root: TreeNode[] = [];
		const stack: { indent: number; children: TreeNode[] }[] = [{ indent: -1, children: root }];

		for (const line of lines) {
			const trimmed = line.replace(/^[—\-\t ]+/, '');
			const indent = line.length - line.trimStart().length;
			// Count dashes or tabs as indent levels
			const dashCount = (line.match(/^[—\-]+/) || [''])[0].length;
			const effectiveIndent = dashCount > 0 ? dashCount : Math.floor(indent / 4);

			const isDirectory = !trimmed.includes('.') || trimmed.endsWith('/');
			const name = trimmed.replace(/\/$/, '');

			const node = createNode(name, isDirectory ? 'directory' : 'file');

			// Find the right parent based on indent
			while (stack.length > 1 && stack[stack.length - 1].indent >= effectiveIndent) {
				stack.pop();
			}

			stack[stack.length - 1].children.push(node);

			if (isDirectory) {
				stack.push({ indent: effectiveIndent, children: node.children });
			}
		}

		return root;
	}

	let treeTextInput = $state('');
	let showTreeTextInput = $state(false);

	function importTreeFromText() {
		if (treeTextInput.trim()) {
			tree = parseTreeText(treeTextInput);
			showTreeTextInput = false;
			treeTextInput = '';
		}
	}

	onMount(() => {
		loadTemplates();
	});
</script>

<div class="scaffolding-panel">
	<header class="panel-header">
		<h2>Project Scaffolding</h2>
		<div class="header-actions">
			<button class="btn-secondary" onclick={() => showTemplateSelector = true}>
				Load Template
			</button>
		</div>
	</header>

	<div class="panel-content">
		<!-- Metadata Section -->
		<section class="metadata-section">
			<h3>Project Metadata</h3>
			<div class="form-grid">
				<label>
					<span>Project Name *</span>
					<input type="text" bind:value={projectName} placeholder="my-project" />
				</label>
				<label>
					<span>Author</span>
					<input type="text" bind:value={author} placeholder="Your Name" />
				</label>
				<label class="full-width">
					<span>Description</span>
					<textarea bind:value={projectDescription} rows="3" placeholder="Project description..."></textarea>
				</label>
				<label class="full-width">
					<span>Output Path *</span>
					<div class="input-with-button">
						<input type="text" bind:value={outputPath} placeholder="/path/to/create/project" />
						<button
							type="button"
							class="browse-btn"
							onclick={() => showDirectoryBrowser = true}
						>
							Browse
						</button>
					</div>
				</label>
			</div>
		</section>

		<!-- Tree Section -->
		<section class="tree-section">
			<div class="section-header">
				<h3>Directory Structure</h3>
				<div class="tree-actions">
					<button
						class="btn-small"
						onclick={() => addNodeContextual('directory')}
						title={selectedNode?.type === 'directory' ? `Add folder inside ${selectedNode.name}` : 'Add folder to root'}
					>
						+ Folder {#if selectedNode?.type === 'directory'}<span class="context-hint">in {selectedNode.name}</span>{/if}
					</button>
					<button
						class="btn-small"
						onclick={() => addNodeContextual('file')}
						title={selectedNode?.type === 'directory' ? `Add file inside ${selectedNode.name}` : 'Add file to root'}
					>
						+ File {#if selectedNode?.type === 'directory'}<span class="context-hint">in {selectedNode.name}</span>{/if}
					</button>
					<button class="btn-small" onclick={() => showTreeTextInput = !showTreeTextInput}>
						{showTreeTextInput ? 'Cancel' : 'Import Text'}
					</button>
					{#if selectedNode}
						<button class="btn-small btn-deselect" onclick={() => selectedNode = null}>
							Clear Selection
						</button>
					{/if}
				</div>
			</div>

			{#if showTreeTextInput}
				<div class="text-import">
					<textarea
						bind:value={treeTextInput}
						rows="8"
						placeholder="Paste directory structure here:&#10;&#10;src&#10;    components&#10;        App.svelte&#10;    main.ts&#10;README.md"
					></textarea>
					<button class="btn-primary" onclick={importTreeFromText}>Import</button>
				</div>
			{/if}

			<div class="tree-container">
				{#if tree.length === 0}
					<p class="empty-tree">No files or directories yet. Add some using the buttons above.</p>
				{:else}
					<TreeEditor
						{tree}
						{selectedNode}
						onSelect={selectNode}
						onUpdate={updateNode}
						onDelete={deleteNode}
						onAddChild={addChild}
					/>
				{/if}
			</div>
		</section>

		<!-- Node Details Section -->
		{#if selectedNode}
			<section class="details-section">
				<h3>{selectedNode.type === 'directory' ? 'Folder' : 'File'} Details</h3>
				<div class="form-grid">
					<label class="full-width">
						<span>Name</span>
						<input
							type="text"
							bind:value={editName}
							oninput={(e) => syncName(e.currentTarget.value)}
						/>
					</label>
					<label class="full-width">
						<span>Description</span>
						<textarea
							rows="2"
							bind:value={editDescription}
							oninput={(e) => syncDescription(e.currentTarget.value)}
							placeholder="Describe this {selectedNode.type}..."
						></textarea>
					</label>
					{#if selectedNode.type === 'file'}
						<label class="full-width">
							<span>Content</span>
							<textarea
								rows="8"
								bind:value={editContent}
								oninput={(e) => syncContent(e.currentTarget.value)}
								placeholder="File content..."
								class="code-textarea"
							></textarea>
						</label>
					{/if}
				</div>
			</section>
		{/if}

		<!-- Additional README Content -->
		<section class="readme-section">
			<h3>Additional README Content</h3>
			<p class="section-hint">Add any extra markdown content to be appended at the end of the generated README.</p>
			<textarea
				rows="6"
				bind:value={additionalReadmeContent}
				placeholder="## Usage&#10;&#10;```bash&#10;npm install&#10;npm run dev&#10;```&#10;&#10;## License&#10;&#10;MIT"
				class="readme-textarea"
			></textarea>
		</section>

		<!-- Validation Errors -->
		{#if validationErrors.length > 0}
			<div class="validation-errors">
				<h4>Please fix the following errors:</h4>
				<ul>
					{#each validationErrors as error}
						<li>{error}</li>
					{/each}
				</ul>
			</div>
		{/if}

		<!-- Create Result -->
		{#if createResult}
			<div class="create-result" class:success={createResult.success} class:error={!createResult.success}>
				{createResult.message}
			</div>
		{/if}

		<!-- Action Buttons -->
		<div class="create-section">
			<button class="btn-preview" onclick={() => showReadmePreview = true}>
				Preview README
			</button>
			<button class="btn-create" onclick={createProject} disabled={isCreating}>
				{isCreating ? 'Creating...' : 'Create Project'}
			</button>
		</div>
	</div>
</div>

<!-- Template Selector Modal -->
{#if showTemplateSelector}
	<TemplateSelector
		{templates}
		onSelect={applyTemplate}
		onClose={() => showTemplateSelector = false}
		onDelete={deleteTemplate}
	/>
{/if}

<!-- Save Template Dialog -->
{#if showTemplateDialog}
	<TemplateDialog
		onSave={saveAsTemplate}
		onSkip={() => showTemplateDialog = false}
		onClose={() => showTemplateDialog = false}
	/>
{/if}

<!-- Directory Browser Modal -->
{#if showDirectoryBrowser}
	<DirectoryBrowser
		onSelect={handleDirectorySelect}
		onClose={() => showDirectoryBrowser = false}
	/>
{/if}

<!-- README Preview Modal -->
{#if showReadmePreview}
	<div class="modal-overlay" onclick={() => showReadmePreview = false} role="dialog" aria-modal="true">
		<div class="preview-modal" onclick={(e) => e.stopPropagation()} role="document">
			<header class="preview-header">
				<h2>README Preview</h2>
				<button class="close-btn" onclick={() => showReadmePreview = false}>×</button>
			</header>
			<div class="preview-content">
				<MarkdownPreview content={generateReadme()} />
			</div>
			<footer class="preview-footer">
				<button class="btn-close" onclick={() => showReadmePreview = false}>Close</button>
			</footer>
		</div>
	</div>
{/if}

<style>
	.scaffolding-panel {
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 10px;
		overflow: hidden;
	}

	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 16px 20px;
		background: color-mix(in srgb, #5c7a99 20%, #f9fafb);
		border-bottom: 1px solid color-mix(in srgb, #5c7a99 30%, #e5e7eb);
	}
	.panel-header h2 {
		margin: 0;
		font-size: 1rem;
		font-weight: 600;
		color: color-mix(in srgb, #5c7a99 80%, #111827);
	}
	.header-actions {
		display: flex;
		gap: 8px;
	}

	.panel-content {
		padding: 20px;
		display: flex;
		flex-direction: column;
		gap: 24px;
	}

	section {
		border: 1px solid #e5e7eb;
		border-radius: 8px;
		padding: 16px;
	}
	section h3 {
		margin: 0 0 12px;
		font-size: 0.9rem;
		font-weight: 600;
		color: #374151;
	}

	.section-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 12px;
	}
	.section-header h3 {
		margin: 0;
	}

	.form-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 12px;
	}
	.form-grid label {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.form-grid label span {
		font-size: 0.8rem;
		font-weight: 500;
		color: #6b7280;
	}
	.form-grid label.full-width {
		grid-column: 1 / -1;
	}
	.form-grid input,
	.form-grid textarea {
		padding: 8px 12px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 0.85rem;
	}
	.form-grid input:focus,
	.form-grid textarea:focus {
		outline: none;
		border-color: #5c7a99;
		box-shadow: 0 0 0 2px rgba(92, 122, 153, 0.1);
	}

	.code-textarea {
		font-family: 'SF Mono', 'Fira Code', monospace;
		font-size: 0.8rem;
	}

	.input-with-button {
		display: flex;
		gap: 8px;
	}
	.input-with-button input {
		flex: 1;
	}
	.browse-btn {
		padding: 8px 16px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		background: #f9fafb;
		cursor: pointer;
		font-size: 0.85rem;
		color: #374151;
		white-space: nowrap;
	}
	.browse-btn:hover:not(:disabled) {
		background: #f3f4f6;
		border-color: #9ca3af;
	}
	.browse-btn:disabled {
		opacity: 0.6;
		cursor: wait;
	}

	.readme-section {
		background: #fffef5;
	}

	.section-hint {
		font-size: 0.8rem;
		color: #6b7280;
		margin: 0 0 12px;
	}

	.readme-textarea {
		width: 100%;
		padding: 12px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-family: 'SF Mono', 'Fira Code', monospace;
		font-size: 0.8rem;
		resize: vertical;
	}
	.readme-textarea:focus {
		outline: none;
		border-color: #5c7a99;
		box-shadow: 0 0 0 2px rgba(92, 122, 153, 0.1);
	}

	.tree-actions {
		display: flex;
		gap: 6px;
	}

	.btn-small {
		padding: 4px 10px;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		background: white;
		font-size: 0.75rem;
		cursor: pointer;
		color: #374151;
	}
	.btn-small:hover {
		background: #f3f4f6;
	}

	.context-hint {
		font-size: 0.65rem;
		color: #5c7a99;
		font-weight: 500;
		margin-left: 2px;
	}

	.btn-deselect {
		color: #9ca3af;
		border-style: dashed;
	}

	.btn-secondary {
		padding: 6px 14px;
		border: 1px solid color-mix(in srgb, #5c7a99 40%, #d1d5db);
		border-radius: 6px;
		background: white;
		color: #5c7a99;
		font-size: 0.8rem;
		cursor: pointer;
		font-weight: 500;
	}
	.btn-secondary:hover {
		background: color-mix(in srgb, #5c7a99 10%, white);
		border-color: #5c7a99;
	}

	.btn-primary {
		padding: 8px 16px;
		border: none;
		border-radius: 6px;
		background: #5c7a99;
		color: white;
		font-size: 0.85rem;
		cursor: pointer;
	}
	.btn-primary:hover {
		background: color-mix(in srgb, #5c7a99 85%, #111827);
	}

	.text-import {
		margin-bottom: 12px;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.text-import textarea {
		padding: 12px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-family: 'SF Mono', monospace;
		font-size: 0.8rem;
	}

	.tree-container {
		min-height: 150px;
		max-height: 400px;
		overflow-y: auto;
		border: 1px solid #e5e7eb;
		border-radius: 6px;
		background: #fafafa;
	}

	.empty-tree {
		padding: 40px 20px;
		text-align: center;
		color: #9ca3af;
		font-size: 0.85rem;
	}

	.details-section {
		background: #f9fafb;
	}

	.validation-errors {
		padding: 12px 16px;
		background: #fef2f2;
		border: 1px solid #fecaca;
		border-radius: 6px;
	}
	.validation-errors h4 {
		margin: 0 0 8px;
		font-size: 0.85rem;
		color: #dc2626;
	}
	.validation-errors ul {
		margin: 0;
		padding-left: 20px;
	}
	.validation-errors li {
		font-size: 0.8rem;
		color: #dc2626;
	}

	.create-result {
		padding: 12px 16px;
		border-radius: 6px;
		font-size: 0.85rem;
	}
	.create-result.success {
		background: #ecfdf5;
		border: 1px solid #a7f3d0;
		color: #065f46;
	}
	.create-result.error {
		background: #fef2f2;
		border: 1px solid #fecaca;
		color: #dc2626;
	}

	.create-section {
		display: flex;
		justify-content: center;
		gap: 12px;
		padding-top: 8px;
	}

	.btn-preview {
		padding: 12px 24px;
		border: 2px solid #5c7a99;
		border-radius: 8px;
		background: white;
		color: #5c7a99;
		font-size: 0.95rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s;
	}
	.btn-preview:hover {
		background: color-mix(in srgb, #5c7a99 8%, white);
	}

	.btn-create {
		padding: 12px 32px;
		border: none;
		border-radius: 8px;
		background: #5c7a99;
		color: white;
		font-size: 0.95rem;
		font-weight: 500;
		cursor: pointer;
		transition: transform 0.15s, box-shadow 0.15s;
	}
	.btn-create:hover:not(:disabled) {
		transform: translateY(-1px);
		box-shadow: 0 4px 12px rgba(92, 122, 153, 0.3);
		background: color-mix(in srgb, #5c7a99 85%, #111827);
	}
	.btn-create:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	/* README Preview Modal */
	.modal-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}

	.preview-modal {
		background: white;
		border-radius: 12px;
		width: 90%;
		max-width: 800px;
		max-height: 85vh;
		display: flex;
		flex-direction: column;
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
	}

	.preview-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 16px 20px;
		border-bottom: 1px solid #e5e7eb;
	}
	.preview-header h2 {
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

	.preview-content {
		flex: 1;
		overflow-y: auto;
		padding: 24px;
		background: #fffef5;
	}

	.preview-footer {
		display: flex;
		justify-content: flex-end;
		padding: 16px 20px;
		border-top: 1px solid #e5e7eb;
	}

	.btn-close {
		padding: 8px 20px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		background: white;
		color: #374151;
		font-size: 0.85rem;
		cursor: pointer;
	}
	.btn-close:hover {
		background: #f3f4f6;
	}
</style>

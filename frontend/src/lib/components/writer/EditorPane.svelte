<script lang="ts">
	import type { OpenDocument } from './types';
	import DocumentTabs from './DocumentTabs.svelte';
	import MarkdownPreview from './MarkdownPreview.svelte';

	let {
		documents,
		activeDocId,
		viewMode,
		paneId,
		onSelectDoc,
		onCloseDoc,
		onContentChange,
		onTitleChange,
	}: {
		documents: OpenDocument[];
		activeDocId: string | null;
		viewMode: 'write' | 'preview';
		paneId: string;
		onSelectDoc: (docId: string) => void;
		onCloseDoc: (docId: string) => void;
		onContentChange: (docId: string, content: string) => void;
		onTitleChange: (docId: string, title: string) => void;
	} = $props();

	let editorRef = $state<HTMLTextAreaElement | null>(null);

	let activeDoc = $derived(documents.find(d => d.id === activeDocId) || null);
	let wordCount = $derived(activeDoc?.content.trim() ? activeDoc.content.trim().split(/\s+/).length : 0);
	let charCount = $derived(activeDoc?.content.length || 0);

	function handleContentInput(e: Event) {
		const target = e.target as HTMLTextAreaElement;
		if (activeDocId) {
			onContentChange(activeDocId, target.value);
		}
	}

	function handleTitleInput(e: Event) {
		const target = e.target as HTMLInputElement;
		if (activeDocId) {
			onTitleChange(activeDocId, target.value);
		}
	}
</script>

<div class="editor-pane">
	<div class="pane-content">
		{#if activeDoc}
			<div class="editor-area" class:preview-mode={viewMode === 'preview'}>
				{#if viewMode === 'write'}
					<div class="typewriter-wrap">
						<textarea
							bind:this={editorRef}
							value={activeDoc.content}
							oninput={handleContentInput}
							class="typewriter-textarea"
							placeholder="Start writing in markdown..."
							spellcheck="true"
						></textarea>
					</div>
				{:else}
					<div class="preview-wrap">
						{#if activeDoc.content.trim()}
							<MarkdownPreview
								content={activeDoc.content}
								editable
								onEdit={(newContent) => onContentChange(activeDocId!, newContent)}
							/>
						{:else}
							<p class="empty-preview">Nothing to preview. Switch to Raw mode to start writing.</p>
						{/if}
					</div>
				{/if}
			</div>
		{:else}
			<div class="no-document">
				<p>No document selected</p>
				<p class="hint">Open a file from the navigator or create a new document</p>
			</div>
		{/if}
	</div>

	<div class="pane-footer">
		<DocumentTabs
			{documents}
			activeId={activeDocId}
			onSelect={onSelectDoc}
			onClose={onCloseDoc}
		/>
		{#if activeDoc}
			<div class="stats">
				<span>{wordCount} words</span>
				<span>{charCount} chars</span>
			</div>
		{/if}
	</div>
</div>

<style>
	.editor-pane {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		background: #fafafa;
	}

	.pane-content {
		flex: 1;
		display: flex;
		overflow: hidden;
	}

	.editor-area {
		flex: 1;
		display: flex;
		justify-content: center;
		overflow: hidden;
	}
	.editor-area.preview-mode {
		background: #fffef5;
	}

	.typewriter-wrap {
		position: relative;
		width: 100%;
		max-width: 720px;
		height: 100%;
		padding: 24px;
	}

	.typewriter-textarea {
		width: 100%;
		height: 100%;
		border: none;
		background: transparent;
		font-family: 'SF Mono', 'Fira Code', 'JetBrains Mono', monospace;
		font-size: 1rem;
		line-height: 1.75;
		color: #1f2937;
		resize: none;
		outline: none;
		padding: 0;
	}
	.typewriter-textarea::placeholder {
		color: #d1d5db;
	}

	.preview-wrap {
		width: 100%;
		max-width: 720px;
		height: 100%;
		padding: 24px;
		overflow-y: auto;
	}

	.empty-preview {
		color: #9ca3af;
		font-style: italic;
	}

	.no-document {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		color: #9ca3af;
	}
	.no-document p {
		margin: 4px 0;
	}
	.no-document .hint {
		font-size: 0.8rem;
	}

	.pane-footer {
		display: flex;
		align-items: stretch;
		border-top: 1px solid #e5e7eb;
		background: white;
	}

	.pane-footer :global(.tabs-bar) {
		flex: 1;
		border-top: none;
	}

	.stats {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 0 12px;
		font-size: 0.7rem;
		color: #9ca3af;
		border-left: 1px solid #e5e7eb;
		background: #f9fafb;
	}
</style>

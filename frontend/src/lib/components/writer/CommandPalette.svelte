<script lang="ts">
	import { notes } from '$lib/stores/notes';
	import { logs } from '$lib/stores/logs';
	import { sources } from '$lib/stores/sources';
	import { projects } from '$lib/stores/projects';
	import { activities } from '$lib/stores/activities';
	import type { Note, Log, Source, Project, Activity } from '$lib/types';
	import { onMount } from 'svelte';

	let { onClose, onInsert }: { onClose: () => void; onInsert: (text: string) => void } = $props();

	let query = $state('');
	let selectedIndex = $state(0);
	let inputRef = $state<HTMLInputElement | null>(null);
	let previewItem = $state<any>(null);

	interface SearchItem {
		type: 'note' | 'log' | 'source' | 'project' | 'activity' | 'action';
		id: number;
		title: string;
		content?: string;
		icon: string;
		data: any;
	}

	const actions: SearchItem[] = [
		{ type: 'action', id: -1, title: 'Insert timestamp', icon: '⏱', data: { action: 'timestamp' } },
		{ type: 'action', id: -2, title: 'Insert horizontal rule', icon: '—', data: { action: 'hr' } },
		{ type: 'action', id: -3, title: 'Insert heading 1', icon: 'H1', data: { action: 'h1' } },
		{ type: 'action', id: -4, title: 'Insert heading 2', icon: 'H2', data: { action: 'h2' } },
		{ type: 'action', id: -5, title: 'Insert code block', icon: '`', data: { action: 'code' } },
		{ type: 'action', id: -6, title: 'Insert quote block', icon: '"', data: { action: 'quote' } },
	];

	let results = $derived.by(() => {
		const items: SearchItem[] = [];
		const q = query.toLowerCase().trim();

		// Always show actions that match
		for (const action of actions) {
			if (!q || action.title.toLowerCase().includes(q)) {
				items.push(action);
			}
		}

		if (q.length < 1) {
			// Show recent items when no query
			for (const note of $notes.slice(0, 5)) {
				items.push({
					type: 'note',
					id: note.id,
					title: note.title,
					content: note.content,
					icon: '📝',
					data: note,
				});
			}
			for (const log of $logs.slice(0, 3)) {
				items.push({
					type: 'log',
					id: log.id,
					title: log.title,
					content: log.content,
					icon: '📓',
					data: log,
				});
			}
		} else {
			// Search all content
			for (const note of $notes) {
				if (note.title.toLowerCase().includes(q) || note.content?.toLowerCase().includes(q)) {
					items.push({
						type: 'note',
						id: note.id,
						title: note.title,
						content: note.content,
						icon: '📝',
						data: note,
					});
				}
			}
			for (const log of $logs) {
				if (log.title.toLowerCase().includes(q) || log.content?.toLowerCase().includes(q)) {
					items.push({
						type: 'log',
						id: log.id,
						title: log.title,
						content: log.content,
						icon: '📓',
						data: log,
					});
				}
			}
			for (const source of $sources) {
				if (source.title.toLowerCase().includes(q) || source.description?.toLowerCase().includes(q)) {
					items.push({
						type: 'source',
						id: source.id,
						title: source.title,
						content: source.description,
						icon: '🔗',
						data: source,
					});
				}
			}
			for (const project of $projects) {
				if (project.title.toLowerCase().includes(q) || project.description?.toLowerCase().includes(q)) {
					items.push({
						type: 'project',
						id: project.id,
						title: project.title,
						content: project.description,
						icon: '📁',
						data: project,
					});
				}
			}
			for (const activity of $activities) {
				if (activity.title.toLowerCase().includes(q) || activity.description?.toLowerCase().includes(q)) {
					items.push({
						type: 'activity',
						id: activity.id,
						title: activity.title,
						content: activity.description,
						icon: '⚡',
						data: activity,
					});
				}
			}
		}

		return items.slice(0, 15);
	});

	$effect(() => {
		// Reset selection when results change
		selectedIndex = 0;
		previewItem = results[0] || null;
	});

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			selectedIndex = Math.min(selectedIndex + 1, results.length - 1);
			previewItem = results[selectedIndex];
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			selectedIndex = Math.max(selectedIndex - 1, 0);
			previewItem = results[selectedIndex];
		} else if (e.key === 'Enter') {
			e.preventDefault();
			if (results[selectedIndex]) {
				selectItem(results[selectedIndex]);
			}
		} else if (e.key === 'Escape') {
			onClose();
		}
	}

	function selectItem(item: SearchItem) {
		if (item.type === 'action') {
			const action = item.data.action;
			if (action === 'timestamp') {
				onInsert(new Date().toLocaleString());
			} else if (action === 'hr') {
				onInsert('\n\n---\n\n');
			} else if (action === 'h1') {
				onInsert('\n# ');
			} else if (action === 'h2') {
				onInsert('\n## ');
			} else if (action === 'code') {
				onInsert('\n```\n\n```\n');
			} else if (action === 'quote') {
				onInsert('\n> ');
			}
		} else {
			// Insert reference to content
			const ref = `[[${item.type}:${item.id}]] **${item.title}**`;
			onInsert(ref);
		}
	}

	function insertContent(item: SearchItem) {
		// Insert the full content
		if (item.content) {
			onInsert(`\n\n> **From ${item.title}:**\n> ${item.content.split('\n').join('\n> ')}\n\n`);
		}
	}

	onMount(() => {
		inputRef?.focus();
	});
</script>

<div class="palette-overlay" onclick={onClose} role="button" tabindex="-1" aria-label="Close command palette">
	<div class="palette" onclick={(e) => e.stopPropagation()} role="dialog" aria-label="Command palette">
		<div class="palette-header">
			<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<circle cx="11" cy="11" r="8"/>
				<line x1="21" y1="21" x2="16.65" y2="16.65"/>
			</svg>
			<input
				bind:this={inputRef}
				type="text"
				class="palette-input"
				placeholder="Search notes, logs, sources... or type a command"
				bind:value={query}
				onkeydown={handleKeydown}
			/>
			<kbd class="kbd">esc</kbd>
		</div>

		<div class="palette-body">
			<div class="results-list">
				{#each results as item, i (item.type + item.id)}
					<button
						class="result-item"
						class:selected={i === selectedIndex}
						onclick={() => selectItem(item)}
						onmouseenter={() => { selectedIndex = i; previewItem = item; }}
					>
						<span class="item-icon">{item.icon}</span>
						<span class="item-title">{item.title}</span>
						<span class="item-type">{item.type}</span>
					</button>
				{/each}
				{#if results.length === 0}
					<p class="no-results">No results found</p>
				{/if}
			</div>

			{#if previewItem && previewItem.type !== 'action' && previewItem.content}
				<div class="preview-pane">
					<div class="preview-header">
						<span class="preview-icon">{previewItem.icon}</span>
						<span class="preview-title">{previewItem.title}</span>
					</div>
					<div class="preview-content">
						{previewItem.content.length > 500
							? previewItem.content.slice(0, 500) + '...'
							: previewItem.content}
					</div>
					<div class="preview-actions">
						<button class="preview-btn" onclick={() => selectItem(previewItem)}>
							Insert reference
						</button>
						<button class="preview-btn secondary" onclick={() => insertContent(previewItem)}>
							Insert content
						</button>
					</div>
				</div>
			{/if}
		</div>

		<div class="palette-footer">
			<span><kbd>↑↓</kbd> navigate</span>
			<span><kbd>↵</kbd> insert reference</span>
			<span><kbd>esc</kbd> close</span>
		</div>
	</div>
</div>

<style>
	.palette-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.4);
		display: flex;
		align-items: flex-start;
		justify-content: center;
		padding-top: 10vh;
		z-index: 100;
		backdrop-filter: blur(2px);
	}

	.palette {
		width: 700px;
		max-width: 90vw;
		background: white;
		border-radius: 12px;
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
		overflow: hidden;
	}

	.palette-header {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 16px 20px;
		border-bottom: 1px solid #e5e7eb;
		color: #9ca3af;
	}
	.palette-input {
		flex: 1;
		border: none;
		font-size: 1rem;
		outline: none;
		color: #111827;
	}
	.palette-input::placeholder {
		color: #d1d5db;
	}
	.kbd {
		padding: 2px 6px;
		background: #f3f4f6;
		border: 1px solid #e5e7eb;
		border-radius: 4px;
		font-size: 0.7rem;
		color: #6b7280;
		font-family: inherit;
	}

	.palette-body {
		display: flex;
		max-height: 400px;
	}

	.results-list {
		flex: 1;
		overflow-y: auto;
		border-right: 1px solid #e5e7eb;
	}
	.result-item {
		display: flex;
		align-items: center;
		gap: 10px;
		width: 100%;
		padding: 10px 16px;
		border: none;
		background: none;
		cursor: pointer;
		text-align: left;
		transition: background 0.1s;
	}
	.result-item:hover, .result-item.selected {
		background: #f3f4f6;
	}
	.item-icon {
		font-size: 1rem;
		width: 24px;
		text-align: center;
	}
	.item-title {
		flex: 1;
		font-size: 0.9rem;
		color: #111827;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.item-type {
		font-size: 0.7rem;
		color: #9ca3af;
		text-transform: uppercase;
	}
	.no-results {
		padding: 20px;
		text-align: center;
		color: #9ca3af;
		font-size: 0.9rem;
	}

	.preview-pane {
		width: 280px;
		padding: 16px;
		background: #f9fafb;
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.preview-header {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.preview-icon {
		font-size: 1.2rem;
	}
	.preview-title {
		font-weight: 600;
		font-size: 0.9rem;
		color: #111827;
	}
	.preview-content {
		flex: 1;
		font-size: 0.8rem;
		color: #6b7280;
		line-height: 1.5;
		overflow-y: auto;
		white-space: pre-wrap;
	}
	.preview-actions {
		display: flex;
		gap: 8px;
	}
	.preview-btn {
		flex: 1;
		padding: 8px 12px;
		border: 1px solid #111827;
		border-radius: 6px;
		background: #111827;
		color: white;
		font-size: 0.75rem;
		cursor: pointer;
		transition: all 0.15s;
	}
	.preview-btn:hover {
		background: #374151;
	}
	.preview-btn.secondary {
		background: white;
		color: #111827;
	}
	.preview-btn.secondary:hover {
		background: #f3f4f6;
	}

	.palette-footer {
		display: flex;
		gap: 16px;
		padding: 10px 16px;
		border-top: 1px solid #e5e7eb;
		background: #f9fafb;
		font-size: 0.75rem;
		color: #9ca3af;
	}
	.palette-footer kbd {
		margin-right: 4px;
	}
</style>

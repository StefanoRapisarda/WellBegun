<script lang="ts">
	import type { DocumentTab } from './types';

	let {
		tabs,
		activeTabId,
		onTabClick,
		onTabClose,
		onPdfSelected,
		onUrlSubmitted
	}: {
		tabs: DocumentTab[];
		activeTabId: string | null;
		onTabClick: (tabId: string) => void;
		onTabClose: (tabId: string) => void;
		onPdfSelected: (file: File) => void;
		onUrlSubmitted: (url: string) => void;
	} = $props();

	let fileInput: HTMLInputElement | undefined = $state();
	let showUrlInput = $state(false);
	let urlValue = $state('');

	function handleFileInput(e: Event) {
		const input = e.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (file) {
			onPdfSelected(file);
			input.value = '';
		}
	}

	function handleUrlKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			submitUrl();
		} else if (e.key === 'Escape') {
			showUrlInput = false;
			urlValue = '';
		}
	}

	function submitUrl() {
		const url = urlValue.trim();
		if (!url) return;
		const finalUrl = url.match(/^https?:\/\//) ? url : `https://${url}`;
		onUrlSubmitted(finalUrl);
		urlValue = '';
		showUrlInput = false;
	}
</script>

<div class="tab-bar">
	<div class="tabs-scroll">
		{#each tabs as tab (tab.id)}
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<div
				class="tab"
				class:active={tab.id === activeTabId}
				onclick={() => onTabClick(tab.id)}
				title={tab.title}
			>
				<span class="tab-dot" class:pdf={tab.type === 'pdf'} class:website={tab.type === 'website'}></span>
				<span class="tab-title">{tab.title.length > 20 ? tab.title.slice(0, 18) + '...' : tab.title}</span>
				<!-- svelte-ignore a11y_click_events_have_key_events -->
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<span
					class="tab-close"
					onclick={(e: MouseEvent) => { e.stopPropagation(); onTabClose(tab.id); }}
					title="Close tab"
				>&times;</span>
			</div>
		{/each}
	</div>

	<div class="tab-actions">
		{#if showUrlInput}
			<input
				type="text"
				class="url-inline-input"
				bind:value={urlValue}
				onkeydown={handleUrlKeydown}
				onblur={() => { if (!urlValue.trim()) showUrlInput = false; }}
				placeholder="https://..."
			/>
			<button class="action-btn go-btn" onclick={submitUrl} disabled={!urlValue.trim()}>Go</button>
		{:else}
			<button class="action-btn pdf-btn" onclick={() => fileInput?.click()} title="Open PDF">
				PDF
			</button>
			<button class="action-btn url-btn" onclick={() => { showUrlInput = true; }} title="Open URL">
				URL
			</button>
		{/if}
	</div>

	<input
		bind:this={fileInput}
		type="file"
		accept=".pdf,application/pdf"
		onchange={handleFileInput}
		hidden
	/>
</div>

<style>
	.tab-bar {
		display: flex;
		align-items: center;
		background: #f3f4f6;
		border-bottom: 1px solid #e5e7eb;
		flex-shrink: 0;
	}
	.tabs-scroll {
		display: flex;
		overflow-x: auto;
		flex: 1;
		gap: 1px;
	}
	.tabs-scroll::-webkit-scrollbar {
		height: 2px;
	}
	.tab {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 6px 10px;
		border: none;
		background: #e5e7eb;
		cursor: pointer;
		font-size: 0.75rem;
		color: #6b7280;
		white-space: nowrap;
		min-width: 0;
		transition: background 0.15s;
	}
	.tab:hover {
		background: #d1d5db;
	}
	.tab.active {
		background: white;
		color: #1f2937;
		font-weight: 500;
	}
	.tab-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.tab-dot.pdf {
		background: #22c55e;
	}
	.tab-dot.website {
		background: #3b82f6;
	}
	.tab-title {
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.tab-close {
		background: none;
		border: none;
		font-size: 0.85rem;
		color: #9ca3af;
		cursor: pointer;
		padding: 0 2px;
		line-height: 1;
		flex-shrink: 0;
	}
	.tab-close:hover {
		color: #ef4444;
	}

	/* ── Action buttons ── */
	.tab-actions {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 0 8px;
		flex-shrink: 0;
	}
	.action-btn {
		padding: 4px 10px;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		background: white;
		cursor: pointer;
		font-size: 0.7rem;
		font-weight: 600;
		transition: all 0.15s;
	}
	.pdf-btn {
		color: #22c55e;
		border-color: #22c55e;
	}
	.pdf-btn:hover {
		background: #22c55e;
		color: white;
	}
	.url-btn {
		color: #3b82f6;
		border-color: #3b82f6;
	}
	.url-btn:hover {
		background: #3b82f6;
		color: white;
	}
	.url-inline-input {
		width: 160px;
		padding: 3px 8px;
		border: 1px solid #3b82f6;
		border-radius: 4px;
		font-size: 0.72rem;
		outline: none;
	}
	.url-inline-input:focus {
		box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
	}
	.go-btn {
		color: #3b82f6;
		border-color: #3b82f6;
	}
	.go-btn:hover:not(:disabled) {
		background: #3b82f6;
		color: white;
	}
	.go-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
</style>

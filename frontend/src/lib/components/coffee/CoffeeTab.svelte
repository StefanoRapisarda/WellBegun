<script lang="ts">
	import { streamChat, fetchModels, switchModel, type ChatMessage, type EntityRef, type CurationSuggestion, type CoffeeEvent, type OllamaModel } from '$lib/api/coffee';
	import { ENTITY_CONFIG, type NotepadEntityType } from '$lib/notepad/types';
	import MarkdownContent from '$lib/components/shared/MarkdownContent.svelte';
	import EntityIcon from '$lib/components/shared/EntityIcon.svelte';
	import CurationCard from './CurationCard.svelte';
	import EntityPopup from './EntityPopup.svelte';
	import { activeTab } from '$lib/stores/activeTab';
	import { setPulsingSelection } from '$lib/stores/panelSelection';
	import { graphInitialSelection } from '$lib/stores/graphInitialSelection';
	import { selectedFilterTags } from '$lib/stores/dateFilter';
	import { resetToAll } from '$lib/stores/dateFilter';
	import { tags } from '$lib/stores/tags';
	import { coffeeMessages, coffeeHistory, resetCoffeeSession, type DisplayMessage } from '$lib/stores/coffee';
	import { get } from 'svelte/store';
	import { onMount } from 'svelte';

	let inputText = $state('');
	let streaming = $state(false);
	let abortController = $state<AbortController | null>(null);
	let chatAreaEl: HTMLDivElement | undefined = $state();
	let messages = $state<DisplayMessage[]>(get(coffeeMessages));

	// Model selector state
	let availableModels = $state<OllamaModel[]>([]);
	let currentModel = $state('');

	onMount(async () => {
		try {
			const data = await fetchModels();
			availableModels = data.models;
			currentModel = data.current;
		} catch {
			// Ollama not available — selector stays empty
		}
	});

	async function handleModelChange(e: Event) {
		const select = e.target as HTMLSelectElement;
		const model = select.value;
		if (!model || model === currentModel) return;
		try {
			await switchModel(model);
			currentModel = model;
		} catch {
			// revert on failure
			select.value = currentModel;
		}
	}

	// Keep local state synced with store
	coffeeMessages.subscribe(v => { messages = v; });

	const EXAMPLES = [
		'Help me plan my next steps for the week',
		'Review my active projects and suggest priorities',
		'Which entities need better tags or descriptions?',
		'Help me write a description for my current project'
	];

	function scrollToBottom() {
		if (chatAreaEl) {
			requestAnimationFrame(() => {
				chatAreaEl!.scrollTop = chatAreaEl!.scrollHeight;
			});
		}
	}

	function updateMessages(fn: (msgs: DisplayMessage[]) => DisplayMessage[]) {
		coffeeMessages.update(fn);
	}

	function handleSend() {
		const text = inputText.trim();
		if (!text || streaming) return;

		inputText = '';

		// Add user message + assistant placeholder
		updateMessages(msgs => [...msgs, { role: 'user', content: text }, { role: 'assistant', content: '' }]);
		streaming = true;
		scrollToBottom();

		let assistantContent = '';
		let entities: EntityRef[] = [];
		let curation: CurationSuggestion[] = [];
		const history = get(coffeeHistory);

		abortController = streamChat(text, history, (event: CoffeeEvent) => {
			switch (event.type) {
				case 'entities':
					entities = event.items;
					updateMessages(msgs => msgs.map((m, i) =>
						i === msgs.length - 1 ? { ...m, entities } : m
					));
					scrollToBottom();
					break;
				case 'token':
					assistantContent += event.content;
					updateMessages(msgs => msgs.map((m, i) =>
						i === msgs.length - 1 ? { ...m, content: assistantContent } : m
					));
					scrollToBottom();
					break;
				case 'curation':
					curation = event.suggestions;
					updateMessages(msgs => msgs.map((m, i) =>
						i === msgs.length - 1 ? { ...m, curation } : m
					));
					scrollToBottom();
					break;
				case 'error':
					updateMessages(msgs => msgs.map((m, i) =>
						i === msgs.length - 1 ? { ...m, content: `**Error:** ${event.message}` } : m
					));
					streaming = false;
					abortController = null;
					scrollToBottom();
					break;
				case 'done':
					streaming = false;
					abortController = null;
					coffeeHistory.update(h => [
						...h,
						{ role: 'user', content: text },
						{ role: 'assistant', content: assistantContent }
					]);
					scrollToBottom();
					break;
			}
		});
	}

	function handleStop() {
		if (abortController) {
			abortController.abort();
			abortController = null;
			streaming = false;
		}
	}

	function handleReset() {
		handleStop();
		resetCoffeeSession();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSend();
		}
	}

	function handleExampleClick(text: string) {
		inputText = text;
		handleSend();
	}

	function handleCurationAction(suggestion: CurationSuggestion) {
		popupEntity = { type: suggestion.entity_type, id: suggestion.entity_id, title: suggestion.title };
	}

	function handleEntityRefClick(type: string, id: number) {
		const key = `${type}:${id}`;
		const next = new Set(selectedChips);
		if (next.has(key)) {
			next.delete(key);
		} else {
			next.add(key);
		}
		selectedChips = next;
	}

	function handleEntityRefDblClick(type: string, id: number) {
		popupEntity = { type, id, title: '' };
	}

	function entityColor(type: string): string {
		return ENTITY_CONFIG[type as NotepadEntityType]?.color ?? '#6b7280';
	}

	function typeLabel(type: string): string {
		return type.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
	}

	// --- Entity multi-selection ---
	let selectedChips = $state<Set<string>>(new Set());
	let popupEntity = $state<{ type: string; id: number; title: string } | null>(null);

	function chipKey(ref: EntityRef): string {
		return `${ref.type}:${ref.id}`;
	}

	function isChipSelected(ref: EntityRef): boolean {
		return selectedChips.has(chipKey(ref));
	}

	function handleChipClick(ref: EntityRef) {
		const key = chipKey(ref);
		const next = new Set(selectedChips);
		if (next.has(key)) {
			next.delete(key);
		} else {
			next.add(key);
		}
		selectedChips = next;
	}

	function handleChipDblClick(ref: EntityRef) {
		popupEntity = { type: ref.type, id: ref.id, title: ref.title };
	}

	function clearSelection() {
		selectedChips = new Set();
	}

	let selectedList = $derived.by(() => {
		const items: EntityRef[] = [];
		for (const msg of messages) {
			if (msg.entities) {
				for (const ref of msg.entities) {
					if (ref.title && selectedChips.has(chipKey(ref))) {
						items.push(ref);
					}
				}
			}
		}
		// Deduplicate by key
		const seen = new Set<string>();
		return items.filter(r => {
			const k = chipKey(r);
			if (seen.has(k)) return false;
			seen.add(k);
			return true;
		});
	});

	let selectionCount = $derived(selectedList.length);

	function findEntityTags(selected: EntityRef[]) {
		const allTags = get(tags);
		return selected
			.map(r => allTags.find(t => t.entity_type === r.type && t.entity_id === r.id))
			.filter((t): t is NonNullable<typeof t> => t != null);
	}

	function openSelectedInCards() {
		const matchingTags = findEntityTags(selectedList);
		selectedFilterTags.set(matchingTags);
		resetToAll();
		setPulsingSelection(selectedList.map(r => `${r.type}:${r.id}`), 2500);
		activeTab.set('input');
	}

	function openSelectedInGraph() {
		const matchingTags = findEntityTags(selectedList);
		selectedFilterTags.set(matchingTags);
		resetToAll();
		graphInitialSelection.set({
			entities: [],
			pulsingKeys: selectedList.map(r => `${r.type}:${r.id}`),
		});
		activeTab.set('graph');
	}

	function openSelectedDetails() {
		if (selectedList.length === 1) {
			popupEntity = { type: selectedList[0].type, id: selectedList[0].id, title: selectedList[0].title };
		}
	}

	let isWelcome = $derived(messages.length === 0);
</script>

<div class="coffee-layout">
	{#if isWelcome}
		<div class="welcome">
			<div class="welcome-icon">&#9749;</div>
			<h2 class="welcome-title">Coffee Table</h2>
			<p class="welcome-subtitle">Plan, edit, and curate your knowledge base</p>
			<div class="example-buttons">
				{#each EXAMPLES as example}
					<button class="example-btn" onclick={() => handleExampleClick(example)}>
						{example}
					</button>
				{/each}
			</div>
		</div>
	{:else}
		<div class="chat-header">
			<span class="chat-header-title">&#9749; Coffee Table</span>
			{#if availableModels.length > 0}
				<select
					class="model-select"
					value={currentModel}
					onchange={handleModelChange}
					disabled={streaming}
				>
					{#each availableModels as m}
						<option value={m.name}>{m.name}</option>
					{/each}
				</select>
			{/if}
			<button class="btn-new-chat" onclick={handleReset} title="New conversation">
				<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
				</svg>
				New chat
			</button>
		</div>
		<div class="chat-area" bind:this={chatAreaEl}>
			{#each messages as msg, i (i)}
				{#if msg.role === 'user'}
					<div class="msg-row user-row">
						<div class="msg-bubble user-bubble">{msg.content}</div>
					</div>
				{:else}
					<div class="msg-row assistant-row">
						<div class="msg-bubble assistant-bubble">
							{#if msg.entities && msg.entities.length > 0}
								<div class="entity-chips">
									{#each msg.entities as ref}
										{#if ref.title}
											<button
												class="entity-chip"
												class:selected={isChipSelected(ref)}
												style:--chip-color={entityColor(ref.type)}
												onclick={() => handleChipClick(ref)}
												ondblclick={() => handleChipDblClick(ref)}
											>
												<EntityIcon type={ref.type} size={12} />
												<span class="chip-type">{typeLabel(ref.type)}</span>
												<span class="chip-title">{ref.title}</span>
											</button>
										{/if}
									{/each}
								</div>
							{/if}
							{#if msg.content}
								<MarkdownContent text={msg.content} onEntityClick={handleEntityRefClick} onEntityDblClick={handleEntityRefDblClick} selectedEntityKeys={selectedChips} />
							{:else if streaming && i === messages.length - 1}
								<span class="thinking">Thinking...</span>
							{/if}
							{#if msg.curation && msg.curation.length > 0}
								<div class="curation-section">
									<div class="curation-label">Suggestions</div>
									{#each msg.curation as suggestion}
										<CurationCard {suggestion} onAction={handleCurationAction} />
									{/each}
								</div>
							{/if}
						</div>
					</div>
				{/if}
			{/each}
		</div>
	{/if}

	{#if selectionCount > 0}
		<div class="selection-bar">
			<span class="sel-count">{selectionCount} selected</span>
			<div class="sel-actions">
				{#if selectionCount === 1}
					<button class="sel-btn" onclick={openSelectedDetails} title="View details">
						<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
						Details
					</button>
				{/if}
				<button class="sel-btn" onclick={openSelectedInCards} title="View in Cards">
					<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
					Cards
				</button>
				<button class="sel-btn" onclick={openSelectedInGraph} title="View in Graph">
					<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="6" cy="6" r="3"/><circle cx="18" cy="18" r="3"/><circle cx="18" cy="6" r="3"/><line x1="8.5" y1="7.5" x2="15.5" y2="16.5"/><line x1="15.5" y1="7.5" x2="8.5" y2="7.5"/></svg>
					Graph
				</button>
				<button class="sel-btn sel-clear" onclick={clearSelection} title="Clear selection">&times;</button>
			</div>
		</div>
	{/if}

	<div class="input-bar">
		<div class="input-wrapper">
			<input
				type="text"
				class="chat-input"
				bind:value={inputText}
				onkeydown={handleKeydown}
				placeholder="Ask anything..."
				disabled={streaming}
			/>
			{#if streaming}
				<button class="btn-stop" onclick={handleStop} title="Stop">
					<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
						<rect x="6" y="6" width="12" height="12" rx="2"/>
					</svg>
				</button>
			{:else}
				<button
					class="btn-send"
					onclick={handleSend}
					disabled={!inputText.trim()}
					title="Send"
				>
					<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
					</svg>
				</button>
			{/if}
		</div>
	</div>
</div>

{#if popupEntity}
	<EntityPopup
		entityType={popupEntity.type}
		entityId={popupEntity.id}
		onClose={() => popupEntity = null}
	/>
{/if}

<style>
	.coffee-layout {
		display: flex;
		flex-direction: column;
		height: calc(100vh - 90px);
		max-width: 760px;
		margin: 0 auto;
	}

	/* Welcome state */
	.welcome {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 8px;
		padding: 40px;
	}
	.welcome-icon {
		font-size: 3rem;
		margin-bottom: 8px;
	}
	.welcome-title {
		font-size: 1.3rem;
		font-weight: 600;
		color: #1f2937;
		margin: 0;
	}
	.welcome-subtitle {
		font-size: 0.85rem;
		color: #9ca3af;
		margin: 0 0 16px;
	}
	.example-buttons {
		display: flex;
		flex-direction: column;
		gap: 8px;
		width: 100%;
		max-width: 360px;
	}
	.example-btn {
		padding: 10px 16px;
		border: 1px solid #e5e7eb;
		border-radius: 8px;
		background: white;
		color: #374151;
		font-size: 0.8rem;
		cursor: pointer;
		text-align: left;
		transition: all 0.15s;
	}
	.example-btn:hover {
		background: #f9fafb;
		border-color: #d1d5db;
	}

	/* Chat header */
	.chat-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 8px 16px;
		border-bottom: 1px solid #e5e7eb;
	}
	.chat-header-title {
		font-size: 0.8rem;
		font-weight: 600;
		color: #6b7280;
	}
	.btn-new-chat {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		padding: 4px 10px;
		border-radius: 6px;
		border: 1px solid #d1d5db;
		background: white;
		color: #6b7280;
		font-size: 0.7rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s;
	}
	.btn-new-chat:hover {
		background: #f3f4f6;
		color: #374151;
		border-color: #9ca3af;
	}
	.model-select {
		padding: 3px 8px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		background: white;
		color: #6b7280;
		font-size: 0.65rem;
		font-weight: 500;
		cursor: pointer;
		outline: none;
		max-width: 180px;
		transition: border-color 0.15s;
	}
	.model-select:focus {
		border-color: #9ca3af;
	}
	.model-select:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	/* Chat area */
	.chat-area {
		flex: 1;
		overflow-y: auto;
		padding: 20px 16px;
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.msg-row {
		display: flex;
	}
	.user-row {
		justify-content: flex-end;
	}
	.assistant-row {
		justify-content: flex-start;
	}
	.msg-bubble {
		max-width: 80%;
		padding: 10px 14px;
		border-radius: 12px;
		font-size: 0.85rem;
		line-height: 1.5;
	}
	.user-bubble {
		background: #1f2937;
		color: white;
		border-bottom-right-radius: 4px;
	}
	.assistant-bubble {
		background: white;
		color: #1f2937;
		border: 1px solid #e5e7eb;
		border-bottom-left-radius: 4px;
	}

	/* Entity chips */
	.entity-chips {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		margin-bottom: 6px;
	}
	.entity-chip {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 3px 8px;
		border-radius: 10px;
		font-size: 0.65rem;
		color: var(--chip-color);
		background: color-mix(in srgb, var(--chip-color) 10%, white);
		border: 1px solid color-mix(in srgb, var(--chip-color) 25%, transparent);
		cursor: pointer;
		transition: all 0.15s;
	}
	.entity-chip:hover {
		background: color-mix(in srgb, var(--chip-color) 18%, white);
		border-color: color-mix(in srgb, var(--chip-color) 40%, transparent);
	}
	.entity-chip.selected {
		background: color-mix(in srgb, var(--chip-color) 22%, white);
		border-color: var(--chip-color);
		box-shadow: 0 0 0 1px var(--chip-color);
	}
	.chip-type {
		font-size: 0.55rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.3px;
		opacity: 0.7;
	}
	.chip-title {
		font-weight: 500;
	}

	/* Selection bar */
	.selection-bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 6px 16px;
		background: #f0f4ff;
		border-top: 1px solid #c7d2fe;
	}
	.sel-count {
		font-size: 0.7rem;
		font-weight: 600;
		color: #4338ca;
	}
	.sel-actions {
		display: flex;
		gap: 6px;
		align-items: center;
	}
	.sel-btn {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 3px 10px;
		border-radius: 4px;
		border: 1px solid #c7d2fe;
		background: white;
		color: #4338ca;
		font-size: 0.65rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s;
	}
	.sel-btn:hover {
		background: #e0e7ff;
		border-color: #818cf8;
	}
	.sel-clear {
		font-size: 1rem;
		padding: 1px 8px;
		color: #9ca3af;
		border-color: #d1d5db;
	}
	.sel-clear:hover {
		background: #fee2e2;
		color: #dc2626;
		border-color: #fca5a5;
	}

	.thinking {
		color: #9ca3af;
		font-style: italic;
		font-size: 0.8rem;
	}

	/* Curation section */
	.curation-section {
		margin-top: 10px;
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.curation-label {
		font-size: 0.65rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: #9ca3af;
	}

	/* Input bar */
	.input-bar {
		padding: 12px 16px 16px;
		border-top: 1px solid #e5e7eb;
	}
	.input-wrapper {
		display: flex;
		align-items: center;
		gap: 8px;
		background: white;
		border: 1px solid #d1d5db;
		border-radius: 24px;
		padding: 4px 4px 4px 16px;
		transition: border-color 0.15s;
	}
	.input-wrapper:focus-within {
		border-color: #9ca3af;
	}
	.chat-input {
		flex: 1;
		border: none;
		outline: none;
		font-size: 0.85rem;
		color: #1f2937;
		background: transparent;
		padding: 6px 0;
	}
	.chat-input::placeholder {
		color: #c4c8ce;
	}
	.btn-send,
	.btn-stop {
		width: 32px;
		height: 32px;
		border-radius: 50%;
		border: none;
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		flex-shrink: 0;
		transition: all 0.15s;
	}
	.btn-send {
		background: #1f2937;
		color: white;
	}
	.btn-send:disabled {
		opacity: 0.3;
		cursor: not-allowed;
	}
	.btn-send:hover:not(:disabled) {
		background: #111827;
	}
	.btn-stop {
		background: #dc2626;
		color: white;
	}
	.btn-stop:hover {
		background: #b91c1c;
	}
</style>

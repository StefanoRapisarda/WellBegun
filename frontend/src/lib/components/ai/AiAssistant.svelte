<script lang="ts">
	import { onMount } from 'svelte';
	import { actions, executeAction, actionDefinitions } from '$lib/ai/actions';
	import { getAppContext, formatContextForAI } from '$lib/ai/context';
	import { highlights, pulsePanel } from '$lib/stores/highlights';
	import { panels } from '$lib/stores/panels';
	import { loadActivities } from '$lib/stores/activities';
	import { loadLogs } from '$lib/stores/logs';
	import { loadNotes } from '$lib/stores/notes';
	import { loadTags, triggerEntityTagsRefresh } from '$lib/stores/tags';

	type ViewState = 'bubble' | 'compact' | 'expanded';

	interface Message {
		role: 'user' | 'assistant' | 'system';
		content: string;
		suggestions?: TagSuggestion[];
	}

	interface TagSuggestion {
		action: string;
		tag_name: string;
		tag_category: string;
		entity_type: string;
		entity_ids: number[];
		message: string;
	}

	let viewState = $state<ViewState>('bubble');
	let messages = $state<Message[]>([]);
	let inputText = $state('');
	let isLoading = $state(false);
	let pendingSuggestions = $state<TagSuggestion[]>([]);
	let position = $state({ x: 20, y: 20 });
	let isDragging = $state(false);
	let dragOffset = { x: 0, y: 0 };
	let messagesContainer: HTMLDivElement;

	// Load position from localStorage
	onMount(() => {
		const saved = localStorage.getItem('ai-assistant-position');
		if (saved) {
			try {
				position = JSON.parse(saved);
			} catch {}
		}

		const savedState = localStorage.getItem('ai-assistant-state');
		if (savedState) {
			viewState = savedState as ViewState;
		}
	});

	function savePosition() {
		localStorage.setItem('ai-assistant-position', JSON.stringify(position));
	}

	function saveState() {
		localStorage.setItem('ai-assistant-state', viewState);
	}

	function handleMouseDown(e: MouseEvent) {
		if ((e.target as HTMLElement).closest('.no-drag')) return;
		isDragging = true;
		dragOffset = {
			x: e.clientX - position.x,
			y: e.clientY - position.y
		};
	}

	function handleMouseMove(e: MouseEvent) {
		if (!isDragging) return;
		position = {
			x: Math.max(0, Math.min(window.innerWidth - 100, e.clientX - dragOffset.x)),
			y: Math.max(0, Math.min(window.innerHeight - 100, e.clientY - dragOffset.y))
		};
	}

	function handleMouseUp() {
		if (isDragging) {
			isDragging = false;
			savePosition();
		}
	}

	function toggleState() {
		if (viewState === 'bubble') {
			viewState = 'compact';
		} else if (viewState === 'compact') {
			viewState = 'expanded';
		} else {
			viewState = 'bubble';
		}
		saveState();
	}

	function expand() {
		viewState = 'expanded';
		saveState();
	}

	function collapse() {
		viewState = 'bubble';
		saveState();
	}

	// Detect if input is a question that should query the database
	function isQuestion(text: string): boolean {
		const lower = text.toLowerCase();
		const questionPatterns = [
			/^(did|do|does|have|has|had|was|were|is|are|can|could|what|when|where|which|who|how many|how much|any|show me|find|search|list)\b/,
			/\?$/,
			/\b(today|yesterday|this week|last week|this month)\b.*\b(meeting|note|log|activity|project|task)/,
			/\b(meeting|note|log|activity|project|task).*\b(today|yesterday|this week|last week|this month)\b/,
			// Entity type words combined with a status keyword → treat as a query
			/\b(activities|activity|tasks?|notes?|logs?|projects?|sources?|actors?|meetings?|plans?)\b.*\b(todo|in_progress|done|on_hold|cancelled|planned|active|completed|to_read|reading|read)\b/,
			/\b(todo|in_progress|done|on_hold|cancelled|planned|active|completed|to_read|reading|read)\b.*\b(activities|activity|tasks?|notes?|logs?|projects?|sources?|actors?|meetings?|plans?)\b/
		];
		return questionPatterns.some(p => p.test(lower));
	}

	// Handle UI actions from query response
	function handleUiActions(uiActions: Array<{ type: string; target?: string; ids?: number[]; duration?: number; panel?: string }>) {
		const panelsToScroll: string[] = [];

		for (const action of uiActions) {
			if (action.type === 'highlight' && action.target && action.ids) {
				const entityType = action.target as 'log' | 'note' | 'activity' | 'project' | 'source' | 'actor';
				highlights.highlight(entityType, action.ids, action.duration || 2000);
				pulsePanel(entityType, action.duration || 2000);
				panelsToScroll.push(entityType);
			}
			if (action.type === 'show_panel' && action.panel) {
				panels.update(list =>
					list.map(p => p.id === action.panel ? { ...p, visible: true } : p)
				);
				panelsToScroll.push(action.panel);
			}
		}

		// Scroll to the first highlighted panel after a short delay (to let DOM update)
		if (panelsToScroll.length > 0) {
			setTimeout(() => {
				const panelElement = document.querySelector(`[data-panel-id="${panelsToScroll[0]}"]`);
				if (panelElement) {
					panelElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
				}
			}, 100);
		}
	}

	// Execute a tag suggestion (create tag and/or attach to entities)
	async function executeSuggestion(suggestion: TagSuggestion) {
		isLoading = true;
		try {
			const response = await fetch('/api/assistant/execute-suggestion', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					action: suggestion.action,
					tag_name: suggestion.tag_name,
					tag_category: suggestion.tag_category,
					entity_type: suggestion.entity_type,
					entity_ids: suggestion.entity_ids
				})
			});

			if (response.ok) {
				const result = await response.json();
				if (result.success) {
					messages = [...messages, { role: 'assistant', content: `✅ ${result.message}` }];
					// Clear pending suggestions
					pendingSuggestions = [];

					// Reload data to show the new tags
					await loadTags();
					triggerEntityTagsRefresh();  // Signal panels to refresh their entity tags
				} else {
					messages = [...messages, { role: 'assistant', content: `❌ ${result.message}` }];
				}
			} else {
				messages = [...messages, { role: 'assistant', content: '❌ Failed to execute suggestion' }];
			}
		} catch (error) {
			messages = [...messages, { role: 'assistant', content: '❌ Error executing suggestion' }];
		}
		isLoading = false;

		setTimeout(() => {
			if (messagesContainer) {
				messagesContainer.scrollTop = messagesContainer.scrollHeight;
			}
		}, 10);
	}

	function dismissSuggestion() {
		pendingSuggestions = [];
		messages = [...messages, { role: 'assistant', content: 'OK, I won\'t tag those items.' }];
	}

	async function sendMessage() {
		if (!inputText.trim() || isLoading) return;

		const userMessage = inputText.trim();
		inputText = '';
		messages = [...messages, { role: 'user', content: userMessage }];
		isLoading = true;

		// Auto-expand if in bubble or compact mode for better readability
		if (viewState === 'bubble' || viewState === 'compact') {
			viewState = 'expanded';
			saveState();
		}

		// Scroll to bottom
		setTimeout(() => {
			if (messagesContainer) {
				messagesContainer.scrollTop = messagesContainer.scrollHeight;
			}
		}, 10);

		try {
			// Check if this is a question that should query the database
			if (isQuestion(userMessage)) {
				const queryResponse = await fetch('/api/assistant/query', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ question: userMessage })
				});

				if (queryResponse.ok) {
					const queryData = await queryResponse.json();

					// Handle UI actions (highlights, show panels)
					if (queryData.ui_actions && queryData.ui_actions.length > 0) {
						handleUiActions(queryData.ui_actions);
					}

					// Store suggestions for later action
					if (queryData.suggestions && queryData.suggestions.length > 0) {
						pendingSuggestions = queryData.suggestions;
					} else {
						pendingSuggestions = [];
					}

					// Show the answer with suggestions attached
					messages = [...messages, {
						role: 'assistant',
						content: queryData.answer,
						suggestions: queryData.suggestions
					}];
					isLoading = false;

					setTimeout(() => {
						if (messagesContainer) {
							messagesContainer.scrollTop = messagesContainer.scrollHeight;
						}
					}, 10);
					return;
				}
			}

			// Not a question or query failed - try chat endpoint
			const context = getAppContext();
			const response = await fetch('/api/assistant/chat', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					message: userMessage,
					context: context,
					history: messages.slice(-10)
				})
			});

			if (!response.ok) {
				throw new Error('Failed to get response');
			}

			const data = await response.json();

			// Execute any actions from backend
			if (data.actions && Array.isArray(data.actions)) {
				for (const action of data.actions) {
					const result = await executeAction(action.name, action.args || {});
					if (!result.success) {
						console.warn('Action failed:', result.message);
					}
				}
			}

			// If backend returned a response, use it; otherwise fall back to local
			if (data.response && data.response.trim()) {
				messages = [...messages, { role: 'assistant', content: data.response }];
			} else {
				const result = await handleLocalCommand(userMessage);
				messages = [...messages, { role: 'assistant', content: result }];
			}

		} catch (error) {
			// Fallback: local command handling
			const result = await handleLocalCommand(userMessage);
			messages = [...messages, { role: 'assistant', content: result }];
		}

		isLoading = false;

		// Scroll to bottom
		setTimeout(() => {
			if (messagesContainer) {
				messagesContainer.scrollTop = messagesContainer.scrollHeight;
			}
		}, 10);
	}

	// Local command handling (smart pattern matching without LLM)
	async function handleLocalCommand(input: string): Promise<string> {
		const lower = input.toLowerCase().trim();
		const context = getAppContext();

		// Help commands
		if (lower === 'help' || lower === '?' || lower === 'commands' || lower.includes('what can you do')) {
			return `I can help you control the app. Try:

• "show notes" / "hide projects" - Toggle panels
• "research mode" / "writing mode" - Focus presets
• "work on [project name]" - Activate a project
• "start [activity]" - Activate an activity
• "note: [text]" - Create a quick note
• "summary" - See what's active
• "list projects" - See available projects
• "clear" - Clear this chat

Or just mention a project/activity name and I'll try to activate it!`;
		}

		// Clear chat
		if (lower === 'clear' || lower === 'reset' || lower === 'clear chat') {
			messages = [];
			return "Chat cleared!";
		}

		// Summary / status
		if (lower.includes('summary') || lower.includes('status') || lower === 'what' || lower.includes('overview') || lower.includes('what is active')) {
			const result = await executeAction('get_summary', {});
			return result.message;
		}

		// List commands
		if (lower.includes('list project') || lower === 'projects') {
			const names = context.allProjects.map(p => `${p.title}${p.is_active ? ' (active)' : ''}`);
			return names.length > 0 ? `Projects: ${names.join(', ')}` : 'No projects yet.';
		}
		if (lower.includes('list activit') || lower === 'activities') {
			const names = context.allActivities.map(a => `${a.title}${a.is_active ? ' (active)' : ''}`);
			return names.length > 0 ? `Activities: ${names.join(', ')}` : 'No activities yet.';
		}

		// Focus modes - flexible matching
		const focusModes = ['research', 'writing', 'planning', 'review', 'minimal'];
		for (const mode of focusModes) {
			if (lower.includes(mode)) {
				const result = await executeAction('show_panels_for_focus', { mode });
				return result.message;
			}
		}

		// Panel visibility - flexible matching
		const panelNames = ['project', 'projects', 'note', 'notes', 'log', 'logs', 'activity', 'activities',
			'source', 'sources', 'actor', 'actors', 'plan', 'plans', 'wildtag', 'tag', 'tags'];

		for (const panel of panelNames) {
			if (lower.includes(panel)) {
				// Normalize panel name
				let panelId = panel;
				if (panel === 'projects') panelId = 'project';
				if (panel === 'notes') panelId = 'note';
				if (panel === 'logs') panelId = 'log';
				if (panel === 'activities') panelId = 'activity';
				if (panel === 'sources') panelId = 'source';
				if (panel === 'actors') panelId = 'actor';
				if (panel === 'plans') panelId = 'plan';
				if (panel === 'tag' || panel === 'tags') panelId = 'wildtag';

				if (lower.includes('show') || lower.includes('open') || lower.includes('display')) {
					const result = await executeAction('switch_panel', { panel_id: panelId, visible: true });
					return result.message;
				}
				if (lower.includes('hide') || lower.includes('close') || lower.includes('remove')) {
					const result = await executeAction('switch_panel', { panel_id: panelId, visible: false });
					return result.message;
				}
			}
		}

		// Create note
		if (lower.startsWith('note:') || lower.startsWith('note ') || lower.startsWith('remember:') || lower.startsWith('remember ')) {
			const content = input.replace(/^(note:|note |remember:|remember )\s*/i, '');
			if (content.trim()) {
				const result = await executeAction('create_note', { content: content.trim() });
				return result.message;
			}
		}

		// Create log
		if (lower.startsWith('log:') || lower.startsWith('diary:') || lower.startsWith('log ')) {
			const content = input.replace(/^(log:|diary:|log )\s*/i, '');
			if (content.trim()) {
				const result = await executeAction('create_log', {
					title: content.substring(0, 50),
					content: content
				});
				return result.message;
			}
		}

		// Deactivation patterns
		if (lower.includes('deactivate') || lower.includes('stop') || lower.includes('finish') || lower.includes('done with')) {
			// Try to find what to deactivate
			for (const project of context.allProjects) {
				if (lower.includes(project.title.toLowerCase())) {
					const result = await executeAction('deactivate_project', { project_name: project.title });
					return result.message;
				}
			}
			for (const activity of context.allActivities) {
				if (lower.includes(activity.title.toLowerCase())) {
					const result = await executeAction('deactivate_activity', { activity_name: activity.title });
					return result.message;
				}
			}
			// Deactivate all active
			if (lower.includes('all') || lower.includes('everything')) {
				const results: string[] = [];
				for (const p of context.activeProjects) {
					await executeAction('deactivate_project', { project_name: p.title });
					results.push(p.title);
				}
				for (const a of context.activeActivities) {
					await executeAction('deactivate_activity', { activity_name: a.title });
					results.push(a.title);
				}
				return results.length > 0 ? `Deactivated: ${results.join(', ')}` : 'Nothing was active.';
			}
		}

		// Activation patterns - check if input contains any project or activity name
		const activationKeywords = ['activate', 'start', 'begin', 'work on', 'working on', 'focus on', 'switch to', 'open'];
		const hasActivationKeyword = activationKeywords.some(kw => lower.includes(kw));

		// Try to match project names (fuzzy)
		for (const project of context.allProjects) {
			const projectLower = project.title.toLowerCase();
			if (lower.includes(projectLower) || projectLower.includes(lower.replace(/[^a-z0-9]/g, ''))) {
				const result = await executeAction('activate_project', { project_name: project.title });
				return result.message;
			}
		}

		// Try to match activity names (fuzzy)
		for (const activity of context.allActivities) {
			const activityLower = activity.title.toLowerCase();
			if (lower.includes(activityLower) || activityLower.includes(lower.replace(/[^a-z0-9]/g, ''))) {
				const result = await executeAction('activate_activity', { activity_name: activity.title });
				return result.message;
			}
		}

		// If they mentioned activation keywords but we didn't find a match, suggest
		if (hasActivationKeyword) {
			const projectNames = context.allProjects.map(p => p.title).join(', ');
			const activityNames = context.allActivities.map(a => a.title).join(', ');
			let response = "I couldn't find that project or activity.";
			if (projectNames) response += ` Projects: ${projectNames}.`;
			if (activityNames) response += ` Activities: ${activityNames}.`;
			return response;
		}

		// Default response with context-aware suggestions
		const suggestions: string[] = [];
		if (context.allProjects.length > 0) {
			suggestions.push(`work on ${context.allProjects[0].title}`);
		}
		suggestions.push('summary', 'help');

		return `I'm not sure what you mean. Try: "${suggestions[0]}" or type "help" for all commands.`;
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			sendMessage();
		}
	}
</script>

<svelte:window on:mousemove={handleMouseMove} on:mouseup={handleMouseUp} />

<div
	class="ai-assistant"
	class:bubble={viewState === 'bubble'}
	class:compact={viewState === 'compact'}
	class:expanded={viewState === 'expanded'}
	class:dragging={isDragging}
	style="left: {position.x}px; top: {position.y}px;"
>
	{#if viewState === 'bubble'}
		<button class="bubble-btn" onclick={toggleState} onmousedown={handleMouseDown}>
			<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
			</svg>
		</button>
	{:else if viewState === 'compact'}
		<div class="compact-container" onmousedown={handleMouseDown}>
			<div class="compact-header">
				<span class="compact-title">AI Assistant</span>
				<div class="compact-buttons no-drag">
					<button onclick={expand} title="Expand">
						<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<polyline points="15 3 21 3 21 9"/>
							<polyline points="9 21 3 21 3 15"/>
							<line x1="21" y1="3" x2="14" y2="10"/>
							<line x1="3" y1="21" x2="10" y2="14"/>
						</svg>
					</button>
					<button onclick={collapse} title="Minimize">
						<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<line x1="5" y1="12" x2="19" y2="12"/>
						</svg>
					</button>
				</div>
			</div>
			<div class="compact-input no-drag">
				<input
					type="text"
					bind:value={inputText}
					onkeydown={handleKeydown}
					placeholder="Ask me anything..."
					disabled={isLoading}
				/>
				<button onclick={sendMessage} disabled={isLoading || !inputText.trim()}>
					{#if isLoading}
						<span class="spinner"></span>
					{:else}
						↵
					{/if}
				</button>
			</div>
		</div>
	{:else}
		<div class="expanded-container" onmousedown={handleMouseDown}>
			<div class="expanded-header">
				<span class="expanded-title">AI Assistant</span>
				<div class="expanded-buttons no-drag">
					<button onclick={() => { viewState = 'compact'; saveState(); }} title="Compact">
						<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<polyline points="4 14 10 14 10 20"/>
							<polyline points="20 10 14 10 14 4"/>
							<line x1="14" y1="10" x2="21" y2="3"/>
							<line x1="3" y1="21" x2="10" y2="14"/>
						</svg>
					</button>
					<button onclick={collapse} title="Minimize">
						<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<line x1="5" y1="12" x2="19" y2="12"/>
						</svg>
					</button>
				</div>
			</div>

			<div class="messages" bind:this={messagesContainer}>
				{#if messages.length === 0}
					<div class="welcome">
						<p>Hi! I'm your AI assistant. I can help you:</p>
						<ul>
							<li>Switch between panels and focus modes</li>
							<li>Activate projects and activities</li>
							<li>Create notes and logs</li>
							<li>Navigate your workspace</li>
						</ul>
						<p>Try: "Focus on research" or "Working on thesis"</p>
					</div>
				{/if}
				{#each messages as msg}
					<div class="message {msg.role}">
						<div class="message-content">{msg.content}</div>
						{#if msg.suggestions && msg.suggestions.length > 0}
							<div class="suggestion-buttons">
								{#each msg.suggestions as suggestion}
									<button
										class="btn-suggestion yes"
										onclick={() => executeSuggestion(suggestion)}
										disabled={isLoading}
									>
										Yes, tag them
									</button>
									<button
										class="btn-suggestion no"
										onclick={dismissSuggestion}
										disabled={isLoading}
									>
										No thanks
									</button>
								{/each}
							</div>
						{/if}
					</div>
				{/each}
				{#if isLoading}
					<div class="message assistant">
						<div class="message-content typing">
							<span></span><span></span><span></span>
						</div>
					</div>
				{/if}
			</div>

			<div class="input-area no-drag">
				<input
					type="text"
					bind:value={inputText}
					onkeydown={handleKeydown}
					placeholder="Tell me what you want to do..."
					disabled={isLoading}
				/>
				<button onclick={sendMessage} disabled={isLoading || !inputText.trim()}>
					{#if isLoading}
						<span class="spinner"></span>
					{:else}
						Send
					{/if}
				</button>
			</div>
		</div>
	{/if}
</div>

<style>
	.ai-assistant {
		position: fixed;
		z-index: 9999;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
	}

	.ai-assistant.dragging {
		cursor: grabbing;
		user-select: none;
	}

	/* Bubble state */
	.bubble-btn {
		width: 56px;
		height: 56px;
		border-radius: 50%;
		background: #5c7a99;
		border: none;
		cursor: grab;
		display: flex;
		align-items: center;
		justify-content: center;
		color: white;
		box-shadow: 0 4px 15px rgba(92, 122, 153, 0.4);
		transition: transform 0.2s, box-shadow 0.2s;
	}

	.bubble-btn:hover {
		transform: scale(1.05);
		box-shadow: 0 6px 20px rgba(92, 122, 153, 0.5);
	}

	.bubble-btn:active {
		cursor: grabbing;
	}

	/* Compact state */
	.compact-container {
		width: 280px;
		background: white;
		border-radius: 12px;
		box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
		overflow: hidden;
		cursor: grab;
	}

	.compact-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 8px 12px;
		background: #5c7a99;
		color: white;
	}

	.compact-title {
		font-size: 0.85rem;
		font-weight: 500;
	}

	.compact-buttons {
		display: flex;
		gap: 4px;
	}

	.compact-buttons button {
		background: rgba(255, 255, 255, 0.2);
		border: none;
		border-radius: 4px;
		padding: 4px;
		cursor: pointer;
		color: white;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.compact-buttons button:hover {
		background: rgba(255, 255, 255, 0.3);
	}

	.compact-input {
		display: flex;
		padding: 8px;
		gap: 6px;
	}

	.compact-input input {
		flex: 1;
		padding: 8px 10px;
		border: 1px solid #e5e7eb;
		border-radius: 6px;
		font-size: 0.85rem;
		outline: none;
	}

	.compact-input input:focus {
		border-color: #5c7a99;
	}

	.compact-input button {
		padding: 8px 12px;
		background: #5c7a99;
		color: white;
		border: none;
		border-radius: 6px;
		cursor: pointer;
		font-weight: 500;
	}

	.compact-input button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	/* Expanded state */
	.expanded-container {
		width: 360px;
		height: 480px;
		background: white;
		border-radius: 12px;
		box-shadow: 0 4px 25px rgba(0, 0, 0, 0.2);
		display: flex;
		flex-direction: column;
		overflow: hidden;
		cursor: grab;
	}

	.expanded-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 12px 16px;
		background: #5c7a99;
		color: white;
	}

	.expanded-title {
		font-size: 0.95rem;
		font-weight: 600;
	}

	.expanded-buttons {
		display: flex;
		gap: 6px;
	}

	.expanded-buttons button {
		background: rgba(255, 255, 255, 0.2);
		border: none;
		border-radius: 4px;
		padding: 6px;
		cursor: pointer;
		color: white;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.expanded-buttons button:hover {
		background: rgba(255, 255, 255, 0.3);
	}

	.messages {
		flex: 1;
		overflow-y: auto;
		padding: 12px;
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	.welcome {
		color: #6b7280;
		font-size: 0.85rem;
		line-height: 1.5;
	}

	.welcome ul {
		margin: 8px 0;
		padding-left: 20px;
	}

	.welcome li {
		margin: 4px 0;
	}

	.message {
		max-width: 85%;
		padding: 10px 14px;
		border-radius: 12px;
		font-size: 0.85rem;
		line-height: 1.4;
	}

	.message.user {
		align-self: flex-end;
		background: #5c7a99;
		color: white;
		border-bottom-right-radius: 4px;
	}

	.message.assistant {
		align-self: flex-start;
		background: #f3f4f6;
		color: #1f2937;
		border-bottom-left-radius: 4px;
	}

	.message-content {
		white-space: pre-wrap;
	}

	.typing {
		display: flex;
		gap: 4px;
		padding: 4px 0;
	}

	.typing span {
		width: 6px;
		height: 6px;
		background: #9ca3af;
		border-radius: 50%;
		animation: bounce 1.4s infinite ease-in-out;
	}

	.typing span:nth-child(1) { animation-delay: -0.32s; }
	.typing span:nth-child(2) { animation-delay: -0.16s; }

	@keyframes bounce {
		0%, 80%, 100% { transform: scale(0); }
		40% { transform: scale(1); }
	}

	.input-area {
		display: flex;
		padding: 12px;
		gap: 8px;
		border-top: 1px solid #e5e7eb;
		background: #fafafa;
	}

	.input-area input {
		flex: 1;
		padding: 10px 14px;
		border: 1px solid #e5e7eb;
		border-radius: 8px;
		font-size: 0.9rem;
		outline: none;
	}

	.input-area input:focus {
		border-color: #5c7a99;
	}

	.input-area button {
		padding: 10px 18px;
		background: #5c7a99;
		color: white;
		border: none;
		border-radius: 8px;
		cursor: pointer;
		font-weight: 500;
		font-size: 0.9rem;
	}

	.input-area button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.spinner {
		display: inline-block;
		width: 14px;
		height: 14px;
		border: 2px solid rgba(255, 255, 255, 0.3);
		border-top-color: white;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.no-drag {
		cursor: default;
	}

	/* Suggestion buttons */
	.suggestion-buttons {
		display: flex;
		gap: 8px;
		margin-top: 10px;
		padding-top: 10px;
		border-top: 1px solid #e5e7eb;
	}

	.btn-suggestion {
		padding: 6px 14px;
		border-radius: 6px;
		font-size: 0.8rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s;
	}

	.btn-suggestion.yes {
		background: #5c7a99;
		color: white;
		border: none;
	}

	.btn-suggestion.yes:hover {
		opacity: 0.9;
		transform: translateY(-1px);
	}

	.btn-suggestion.no {
		background: white;
		color: #6b7280;
		border: 1px solid #d1d5db;
	}

	.btn-suggestion.no:hover {
		background: #f9fafb;
		border-color: #9ca3af;
	}

	.btn-suggestion:disabled {
		opacity: 0.5;
		cursor: not-allowed;
		transform: none;
	}
</style>

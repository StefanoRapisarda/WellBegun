<script lang="ts">
	import { onMount } from 'svelte';
	import { getWorkspaceEvents, recordWorkspaceEvent } from '$lib/api/workspaces';
	import { projects } from '$lib/stores/projects';
	import { logs } from '$lib/stores/logs';
	import { notes } from '$lib/stores/notes';
	import { activities } from '$lib/stores/activities';
	import { sources } from '$lib/stores/sources';
	import { actors } from '$lib/stores/actors';
	import { plans } from '$lib/stores/plans';
	import { collections } from '$lib/stores/collections';
	import type { WorkspaceEvent } from '$lib/types';

	let {
		workspaceId,
		onClose
	}: {
		workspaceId: number;
		onClose: () => void;
	} = $props();

	let events = $state<WorkspaceEvent[]>([]);
	let loading = $state(true);
	let logsOnly = $state(false);

	let filteredEvents = $derived(
		logsOnly ? events.filter(e => e.event_type === 'log_entry') : events
	);

	// ── Log input state ──
	let logText = $state('');
	let submitting = $state(false);

	function getEntityTitle(type: string | null, id: number | null): string {
		if (!type || !id) return '';
		switch (type) {
			case 'project': return $projects.find(e => e.id === id)?.title ?? `Project #${id}`;
			case 'log': return $logs.find(e => e.id === id)?.title ?? `Log #${id}`;
			case 'note': return $notes.find(e => e.id === id)?.title ?? `Note #${id}`;
			case 'activity': return $activities.find(e => e.id === id)?.title ?? `Activity #${id}`;
			case 'source': return $sources.find(e => e.id === id)?.title ?? `Source #${id}`;
			case 'actor': return $actors.find(e => e.id === id)?.full_name ?? `Actor #${id}`;
			case 'plan': return $plans.find(e => e.id === id)?.title ?? `Plan #${id}`;
			case 'collection': return $collections.find(e => e.id === id)?.title ?? `Collection #${id}`;
			default: return `${type} #${id}`;
		}
	}

	const EVENT_ICONS: Record<string, string> = {
		opened: 'O',
		entity_added: '+',
		entity_removed: '-',
		entity_created: '*',
		entity_modified: '~',
		log_entry: 'L',
	};

	const EVENT_COLORS: Record<string, string> = {
		opened: '#3b82f6',
		entity_added: '#10b981',
		entity_removed: '#ef4444',
		entity_created: '#8b5cf6',
		entity_modified: '#f59e0b',
		log_entry: '#6366f1',
	};

	function parseMetadata(event: WorkspaceEvent): Record<string, unknown> | null {
		if (!event.metadata_json) return null;
		try { return JSON.parse(event.metadata_json); } catch { return null; }
	}

	function formatEventDescription(event: WorkspaceEvent): string {
		if (event.event_type === 'log_entry') {
			const meta = parseMetadata(event);
			return (meta?.text as string) ?? 'Log entry';
		}
		const entityName = event.entity_type ? getEntityTitle(event.entity_type, event.entity_id) : '';
		switch (event.event_type) {
			case 'opened': return 'Workspace opened';
			case 'entity_added': return `Added ${event.entity_type}: ${entityName}`;
			case 'entity_removed': return `Removed ${event.entity_type}: ${entityName}`;
			case 'entity_created': return `Created ${event.entity_type}: ${entityName}`;
			case 'entity_modified': return `Modified ${event.entity_type}: ${entityName}`;
			default: return event.event_type;
		}
	}

	function formatTime(dateStr: string): string {
		// API may return UTC timestamps without 'Z' suffix — ensure UTC interpretation
		const utcStr = dateStr.endsWith('Z') || dateStr.includes('+') ? dateStr : dateStr + 'Z';
		const date = new Date(utcStr);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.floor(diffMs / 60000);
		const diffHours = Math.floor(diffMs / 3600000);

		if (diffMins < 1) return 'just now';
		if (diffMins < 60) return `${diffMins}m ago`;
		if (diffHours < 24) return `${diffHours}h ago`;
		return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
	}

	async function loadEvents() {
		loading = true;
		try {
			events = await getWorkspaceEvents(workspaceId);
		} catch (e) {
			console.warn('Failed to load events:', e);
		} finally {
			loading = false;
		}
	}

	async function handleAddLog() {
		const text = logText.trim();
		if (!text || submitting) return;
		submitting = true;
		try {
			await recordWorkspaceEvent(workspaceId, {
				event_type: 'log_entry',
				metadata: { text }
			});
			logText = '';
			await loadEvents();
		} catch (e) {
			console.warn('Failed to add log entry:', e);
		} finally {
			submitting = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleAddLog();
		}
	}

	onMount(() => {
		loadEvents();
	});
</script>

<div class="timeline-panel">
	<div class="timeline-header">
		<h3>Timeline</h3>
		<label class="logs-filter">
			<input type="checkbox" bind:checked={logsOnly} />
			Logs only
		</label>
		<button class="close-btn" onclick={onClose}>&times;</button>
	</div>
	<div class="log-input-area">
		<textarea
			class="log-input"
			placeholder="Add a log entry..."
			bind:value={logText}
			onkeydown={handleKeydown}
			disabled={submitting}
			rows="2"
		></textarea>
		<button
			class="log-submit"
			onclick={handleAddLog}
			disabled={!logText.trim() || submitting}
		>
			{submitting ? '...' : 'Log'}
		</button>
	</div>
	<div class="timeline-body">
		{#if loading}
			<p class="loading">Loading...</p>
		{:else if filteredEvents.length === 0}
			<p class="empty">{logsOnly ? 'No log entries yet' : 'No events yet'}</p>
		{:else}
			<div class="event-list">
				{#each filteredEvents as event (event.id)}
					<div class="event-item" class:log-entry={event.event_type === 'log_entry'}>
						<div
							class="event-icon"
							style:background={EVENT_COLORS[event.event_type] ?? '#6b7280'}
						>
							{EVENT_ICONS[event.event_type] ?? '?'}
						</div>
						<div class="event-content">
							<span class="event-desc" class:log-text={event.event_type === 'log_entry'}>
								{formatEventDescription(event)}
							</span>
							<span class="event-time">{formatTime(event.timestamp)}</span>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>

<style>
	.timeline-panel {
		width: 280px;
		border-left: 1px solid #e5e7eb;
		background: #fafafa;
		display: flex;
		flex-direction: column;
		flex-shrink: 0;
		overflow: hidden;
	}
	.timeline-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 12px 16px;
		border-bottom: 1px solid #e5e7eb;
	}
	.timeline-header h3 {
		font-size: 0.8rem;
		font-weight: 600;
		color: #374151;
		margin: 0;
	}
	.logs-filter {
		display: flex;
		align-items: center;
		gap: 4px;
		font-size: 0.68rem;
		color: #6b7280;
		cursor: pointer;
		user-select: none;
		white-space: nowrap;
	}
	.logs-filter input {
		margin: 0;
		cursor: pointer;
	}
	.close-btn {
		width: 24px;
		height: 24px;
		border: none;
		background: transparent;
		cursor: pointer;
		font-size: 1.1rem;
		color: #9ca3af;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 4px;
		transition: all 0.15s;
	}
	.close-btn:hover {
		background: #f3f4f6;
		color: #374151;
	}
	/* ── Log input area ── */
	.log-input-area {
		display: flex;
		gap: 6px;
		padding: 10px 12px;
		border-bottom: 1px solid #e5e7eb;
		background: white;
		align-items: flex-end;
	}
	.log-input {
		flex: 1;
		min-width: 0;
		border: 1px solid #e5e7eb;
		border-radius: 6px;
		padding: 6px 8px;
		font-size: 0.75rem;
		font-family: inherit;
		resize: none;
		line-height: 1.4;
		color: #374151;
		background: #f9fafb;
		transition: border-color 0.15s;
	}
	.log-input:focus {
		outline: none;
		border-color: #6366f1;
		background: white;
	}
	.log-input::placeholder {
		color: #9ca3af;
	}
	.log-submit {
		padding: 6px 10px;
		background: #6366f1;
		color: white;
		border: none;
		border-radius: 6px;
		font-size: 0.7rem;
		font-weight: 600;
		cursor: pointer;
		white-space: nowrap;
		transition: background 0.15s;
	}
	.log-submit:hover:not(:disabled) {
		background: #4f46e5;
	}
	.log-submit:disabled {
		opacity: 0.4;
		cursor: default;
	}
	/* ── Timeline body ── */
	.timeline-body {
		flex: 1;
		overflow-y: auto;
		padding: 12px 16px;
	}
	.loading, .empty {
		font-size: 0.8rem;
		color: #9ca3af;
		text-align: center;
		padding: 20px 0;
		margin: 0;
	}
	.event-list {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.event-item {
		display: flex;
		gap: 10px;
		align-items: flex-start;
	}
	.event-item.log-entry {
		padding: 8px;
		background: #f0f0ff;
		border-radius: 8px;
		margin: 0 -4px;
	}
	.event-icon {
		width: 22px;
		height: 22px;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.65rem;
		font-weight: 700;
		color: white;
		flex-shrink: 0;
	}
	.event-content {
		display: flex;
		flex-direction: column;
		gap: 1px;
		min-width: 0;
	}
	.event-desc {
		font-size: 0.78rem;
		color: #374151;
		line-height: 1.3;
	}
	.event-desc.log-text {
		white-space: pre-wrap;
		word-break: break-word;
	}
	.event-time {
		font-size: 0.65rem;
		color: #9ca3af;
	}
</style>

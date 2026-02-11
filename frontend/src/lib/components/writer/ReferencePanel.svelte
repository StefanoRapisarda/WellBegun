<script lang="ts">
	import { notes } from '$lib/stores/notes';
	import { logs } from '$lib/stores/logs';
	import { sources } from '$lib/stores/sources';
	import { projects } from '$lib/stores/projects';
	import { activities } from '$lib/stores/activities';
	import type { Note, Log, Source, Project, Activity } from '$lib/types';

	let { onClose, onInsert }: { onClose: () => void; onInsert: (text: string) => void } = $props();

	type TabType = 'notes' | 'logs' | 'sources' | 'projects' | 'activities';
	let activeTab = $state<TabType>('notes');
	let searchQuery = $state('');
	let expandedId = $state<string | null>(null);
	let pinnedItems = $state<Set<string>>(new Set());

	// Load pinned items from localStorage
	$effect(() => {
		const saved = localStorage.getItem('writer-pinned-items');
		if (saved) {
			try {
				pinnedItems = new Set(JSON.parse(saved));
			} catch {}
		}
	});

	// Save pinned items
	$effect(() => {
		localStorage.setItem('writer-pinned-items', JSON.stringify([...pinnedItems]));
	});

	function togglePin(key: string) {
		if (pinnedItems.has(key)) {
			pinnedItems.delete(key);
		} else {
			pinnedItems.add(key);
		}
		pinnedItems = new Set(pinnedItems);
	}

	function filterItems<T extends { title: string; content?: string; description?: string }>(items: T[]): T[] {
		if (!searchQuery.trim()) return items;
		const q = searchQuery.toLowerCase();
		return items.filter(item =>
			item.title.toLowerCase().includes(q) ||
			item.content?.toLowerCase().includes(q) ||
			item.description?.toLowerCase().includes(q)
		);
	}

	let filteredNotes = $derived(filterItems($notes));
	let filteredLogs = $derived(filterItems($logs));
	let filteredSources = $derived(filterItems($sources as any));
	let filteredProjects = $derived(filterItems($projects as any));
	let filteredActivities = $derived(filterItems($activities as any));

	function insertReference(type: string, id: number, title: string) {
		onInsert(`[[${type}:${id}]] **${title}**`);
	}

	function insertQuote(title: string, content: string) {
		const quoted = content.split('\n').map(line => `> ${line}`).join('\n');
		onInsert(`\n\n**From "${title}":**\n${quoted}\n\n`);
	}

	function getItemKey(type: string, id: number): string {
		return `${type}:${id}`;
	}

	// Get pinned items data
	let pinnedItemsData = $derived.by(() => {
		const items: Array<{ type: string; id: number; title: string; content?: string }> = [];
		for (const key of pinnedItems) {
			const [type, idStr] = key.split(':');
			const id = parseInt(idStr);
			if (type === 'note') {
				const note = $notes.find(n => n.id === id);
				if (note) items.push({ type: 'note', id, title: note.title, content: note.content });
			} else if (type === 'log') {
				const log = $logs.find(l => l.id === id);
				if (log) items.push({ type: 'log', id, title: log.title, content: log.content });
			} else if (type === 'source') {
				const source = $sources.find(s => s.id === id);
				if (source) items.push({ type: 'source', id, title: source.title, content: source.description });
			} else if (type === 'project') {
				const project = $projects.find(p => p.id === id);
				if (project) items.push({ type: 'project', id, title: project.title, content: project.description });
			} else if (type === 'activity') {
				const activity = $activities.find(a => a.id === id);
				if (activity) items.push({ type: 'activity', id, title: activity.title, content: activity.description });
			}
		}
		return items;
	});

	const tabs: { id: TabType; label: string; icon: string }[] = [
		{ id: 'notes', label: 'Notes', icon: '📝' },
		{ id: 'logs', label: 'Logs', icon: '📓' },
		{ id: 'sources', label: 'Sources', icon: '🔗' },
		{ id: 'projects', label: 'Projects', icon: '📁' },
		{ id: 'activities', label: 'Activities', icon: '⚡' },
	];
</script>

<aside class="reference-panel">
	<header class="panel-header">
		<h3>References</h3>
		<button class="close-btn" onclick={onClose} aria-label="Close panel">
			<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<line x1="18" y1="6" x2="6" y2="18"/>
				<line x1="6" y1="6" x2="18" y2="18"/>
			</svg>
		</button>
	</header>

	<div class="search-bar">
		<input
			type="text"
			placeholder="Search..."
			bind:value={searchQuery}
		/>
	</div>

	{#if pinnedItemsData.length > 0}
		<section class="pinned-section">
			<h4>Pinned</h4>
			<div class="pinned-items">
				{#each pinnedItemsData as item (getItemKey(item.type, item.id))}
					<div class="pinned-item">
						<button class="pinned-title" onclick={() => insertReference(item.type, item.id, item.title)}>
							{item.title}
						</button>
						<button class="unpin-btn" onclick={() => togglePin(getItemKey(item.type, item.id))} aria-label="Unpin">
							<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" stroke="none">
								<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>
								<rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>
							</svg>
						</button>
					</div>
				{/each}
			</div>
		</section>
	{/if}

	<nav class="tabs">
		{#each tabs as tab (tab.id)}
			<button
				class="tab"
				class:active={activeTab === tab.id}
				onclick={() => activeTab = tab.id}
			>
				<span class="tab-icon">{tab.icon}</span>
				{tab.label}
			</button>
		{/each}
	</nav>

	<div class="items-list">
		{#if activeTab === 'notes'}
			{#each filteredNotes as note (note.id)}
				{@const key = getItemKey('note', note.id)}
				<div class="ref-item" class:expanded={expandedId === key}>
					<div class="item-header">
						<button class="item-title" onclick={() => expandedId = expandedId === key ? null : key}>
							{note.title}
						</button>
						<button class="pin-btn" class:pinned={pinnedItems.has(key)} onclick={() => togglePin(key)}>
							📌
						</button>
					</div>
					{#if expandedId === key && note.content}
						<div class="item-content">
							<p>{note.content.length > 300 ? note.content.slice(0, 300) + '...' : note.content}</p>
							<div class="item-actions">
								<button onclick={() => insertReference('note', note.id, note.title)}>Insert ref</button>
								<button onclick={() => insertQuote(note.title, note.content || '')}>Insert quote</button>
							</div>
						</div>
					{/if}
				</div>
			{/each}
			{#if filteredNotes.length === 0}
				<p class="empty">No notes found</p>
			{/if}
		{:else if activeTab === 'logs'}
			{#each filteredLogs as log (log.id)}
				{@const key = getItemKey('log', log.id)}
				<div class="ref-item" class:expanded={expandedId === key}>
					<div class="item-header">
						<button class="item-title" onclick={() => expandedId = expandedId === key ? null : key}>
							{log.title}
						</button>
						<button class="pin-btn" class:pinned={pinnedItems.has(key)} onclick={() => togglePin(key)}>
							📌
						</button>
					</div>
					{#if expandedId === key && log.content}
						<div class="item-content">
							<p>{log.content.length > 300 ? log.content.slice(0, 300) + '...' : log.content}</p>
							<div class="item-actions">
								<button onclick={() => insertReference('log', log.id, log.title)}>Insert ref</button>
								<button onclick={() => insertQuote(log.title, log.content || '')}>Insert quote</button>
							</div>
						</div>
					{/if}
				</div>
			{/each}
			{#if filteredLogs.length === 0}
				<p class="empty">No logs found</p>
			{/if}
		{:else if activeTab === 'sources'}
			{#each filteredSources as source (source.id)}
				{@const key = getItemKey('source', source.id)}
				<div class="ref-item" class:expanded={expandedId === key}>
					<div class="item-header">
						<button class="item-title" onclick={() => expandedId = expandedId === key ? null : key}>
							{source.title}
						</button>
						<button class="pin-btn" class:pinned={pinnedItems.has(key)} onclick={() => togglePin(key)}>
							📌
						</button>
					</div>
					{#if expandedId === key}
						<div class="item-content">
							{#if source.description}
								<p>{source.description.length > 300 ? source.description.slice(0, 300) + '...' : source.description}</p>
							{/if}
							{#if source.content_url}
								<a href={source.content_url} target="_blank" rel="noopener" class="source-link">{source.content_url}</a>
							{/if}
							<div class="item-actions">
								<button onclick={() => insertReference('source', source.id, source.title)}>Insert ref</button>
								{#if source.content_url}
									<button onclick={() => onInsert(`[${source.title}](${source.content_url})`)}>Insert link</button>
								{/if}
							</div>
						</div>
					{/if}
				</div>
			{/each}
			{#if filteredSources.length === 0}
				<p class="empty">No sources found</p>
			{/if}
		{:else if activeTab === 'projects'}
			{#each filteredProjects as project (project.id)}
				{@const key = getItemKey('project', project.id)}
				<div class="ref-item" class:expanded={expandedId === key}>
					<div class="item-header">
						<button class="item-title" onclick={() => expandedId = expandedId === key ? null : key}>
							{project.title}
						</button>
						<button class="pin-btn" class:pinned={pinnedItems.has(key)} onclick={() => togglePin(key)}>
							📌
						</button>
					</div>
					{#if expandedId === key && project.description}
						<div class="item-content">
							<p>{project.description}</p>
							<div class="item-actions">
								<button onclick={() => insertReference('project', project.id, project.title)}>Insert ref</button>
							</div>
						</div>
					{/if}
				</div>
			{/each}
			{#if filteredProjects.length === 0}
				<p class="empty">No projects found</p>
			{/if}
		{:else if activeTab === 'activities'}
			{#each filteredActivities as activity (activity.id)}
				{@const key = getItemKey('activity', activity.id)}
				<div class="ref-item" class:expanded={expandedId === key}>
					<div class="item-header">
						<button class="item-title" onclick={() => expandedId = expandedId === key ? null : key}>
							{activity.title}
						</button>
						<button class="pin-btn" class:pinned={pinnedItems.has(key)} onclick={() => togglePin(key)}>
							📌
						</button>
					</div>
					{#if expandedId === key && activity.description}
						<div class="item-content">
							<p>{activity.description}</p>
							<div class="item-actions">
								<button onclick={() => insertReference('activity', activity.id, activity.title)}>Insert ref</button>
							</div>
						</div>
					{/if}
				</div>
			{/each}
			{#if filteredActivities.length === 0}
				<p class="empty">No activities found</p>
			{/if}
		{/if}
	</div>
</aside>

<style>
	.reference-panel {
		position: fixed;
		top: 0;
		right: 0;
		width: 350px;
		height: 100vh;
		background: white;
		border-left: 1px solid #e5e7eb;
		display: flex;
		flex-direction: column;
		z-index: 40;
		box-shadow: -4px 0 20px rgba(0, 0, 0, 0.05);
	}

	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 16px 20px;
		border-bottom: 1px solid #e5e7eb;
	}
	.panel-header h3 {
		margin: 0;
		font-size: 1rem;
		font-weight: 600;
		color: #111827;
	}
	.close-btn {
		padding: 4px;
		border: none;
		background: none;
		cursor: pointer;
		color: #9ca3af;
		border-radius: 4px;
	}
	.close-btn:hover {
		background: #f3f4f6;
		color: #6b7280;
	}

	.search-bar {
		padding: 12px 16px;
		border-bottom: 1px solid #e5e7eb;
	}
	.search-bar input {
		width: 100%;
		padding: 8px 12px;
		border: 1px solid #e5e7eb;
		border-radius: 6px;
		font-size: 0.85rem;
		outline: none;
	}
	.search-bar input:focus {
		border-color: #9ca3af;
	}

	.pinned-section {
		padding: 12px 16px;
		background: #fefce8;
		border-bottom: 1px solid #fde68a;
	}
	.pinned-section h4 {
		margin: 0 0 8px;
		font-size: 0.7rem;
		text-transform: uppercase;
		color: #92400e;
		letter-spacing: 0.5px;
	}
	.pinned-items {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.pinned-item {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.pinned-title {
		flex: 1;
		text-align: left;
		padding: 4px 8px;
		border: none;
		background: white;
		border-radius: 4px;
		font-size: 0.8rem;
		color: #111827;
		cursor: pointer;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.pinned-title:hover {
		background: #fef3c7;
	}
	.unpin-btn {
		padding: 4px;
		border: none;
		background: none;
		cursor: pointer;
		color: #d97706;
		font-size: 0.8rem;
	}

	.tabs {
		display: flex;
		padding: 8px 12px;
		gap: 4px;
		border-bottom: 1px solid #e5e7eb;
		overflow-x: auto;
	}
	.tab {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 6px 10px;
		border: none;
		background: none;
		border-radius: 6px;
		font-size: 0.75rem;
		color: #6b7280;
		cursor: pointer;
		white-space: nowrap;
		transition: all 0.15s;
	}
	.tab:hover {
		background: #f3f4f6;
	}
	.tab.active {
		background: #111827;
		color: white;
	}
	.tab-icon {
		font-size: 0.9rem;
	}

	.items-list {
		flex: 1;
		overflow-y: auto;
		padding: 8px 0;
	}

	.ref-item {
		border-bottom: 1px solid #f3f4f6;
	}
	.item-header {
		display: flex;
		align-items: center;
		padding: 10px 16px;
	}
	.item-title {
		flex: 1;
		text-align: left;
		border: none;
		background: none;
		font-size: 0.85rem;
		color: #111827;
		cursor: pointer;
		padding: 0;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.item-title:hover {
		color: #3b82f6;
	}
	.pin-btn {
		padding: 4px;
		border: none;
		background: none;
		cursor: pointer;
		font-size: 0.8rem;
		opacity: 0.3;
		transition: opacity 0.15s;
	}
	.pin-btn:hover, .pin-btn.pinned {
		opacity: 1;
	}

	.item-content {
		padding: 0 16px 12px;
	}
	.item-content p {
		margin: 0 0 8px;
		font-size: 0.8rem;
		color: #6b7280;
		line-height: 1.5;
		white-space: pre-wrap;
	}
	.source-link {
		display: block;
		font-size: 0.75rem;
		color: #3b82f6;
		margin-bottom: 8px;
		word-break: break-all;
	}
	.item-actions {
		display: flex;
		gap: 6px;
	}
	.item-actions button {
		padding: 4px 10px;
		border: 1px solid #e5e7eb;
		border-radius: 4px;
		background: white;
		font-size: 0.7rem;
		color: #374151;
		cursor: pointer;
	}
	.item-actions button:hover {
		background: #f3f4f6;
	}

	.empty {
		text-align: center;
		padding: 40px 20px;
		color: #9ca3af;
		font-size: 0.85rem;
	}
</style>

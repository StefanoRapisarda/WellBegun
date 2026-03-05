<script lang="ts">
	import { onMount } from 'svelte';
	import { notes } from '$lib/stores/notes';
	import { logs } from '$lib/stores/logs';
	import { projects } from '$lib/stores/projects';
	import { activities } from '$lib/stores/activities';
	import { sources } from '$lib/stores/sources';
	import { actors } from '$lib/stores/actors';
	import { plans } from '$lib/stores/plans';
	import { workspaces, setActiveWorkspace } from '$lib/stores/workspaces';
	import { createWorkspace } from '$lib/api/workspaces';
	import { activeTab } from '$lib/stores/activeTab';
	import type { Note, Project, Activity, Source, Actor, Log, Plan, Workspace } from '$lib/types';

	// Only render data grid after mount to avoid SSR issues
	let ready = $state(false);

	// Local state copies of store data
	let projectsData = $state<Project[]>([]);
	let activitiesData = $state<Activity[]>([]);
	let notesData = $state<Note[]>([]);
	let logsData = $state<Log[]>([]);
	let sourcesData = $state<Source[]>([]);
	let actorsData = $state<Actor[]>([]);
	let plansData = $state<Plan[]>([]);

	// Workspaces state
	let workspacesData = $state<Workspace[]>([]);
	let newWsName = $state('');

	// Pick random fact on client only to avoid SSR hydration mismatch
	let factIndex = $state(-1);

	// Activity history chart: count entity creations per day over last 14 days
	let activityHistory = $derived.by(() => {
		const today = new Date();
		today.setHours(0, 0, 0, 0);
		const days: { date: string; label: string; count: number }[] = [];

		for (let i = 13; i >= 0; i--) {
			const d = new Date(today);
			d.setDate(today.getDate() - i);
			const iso = d.toISOString().slice(0, 10);
			const label = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });

			let count = 0;
			for (const item of logsData) {
				if (item.created_at.slice(0, 10) === iso) count++;
			}
			for (const item of notesData) {
				if (item.created_at.slice(0, 10) === iso) count++;
			}
			for (const item of sourcesData) {
				if (item.created_at.slice(0, 10) === iso) count++;
			}
			for (const item of actorsData) {
				if (item.created_at.slice(0, 10) === iso) count++;
			}
			days.push({ date: iso, label, count });
		}
		return days;
	});

	let maxCount = $derived(Math.max(1, ...activityHistory.map(d => d.count)));

	// ── Recent Activity Feed ──
	const TYPE_COLORS: Record<string, string> = {
		project: '#5c7a99',
		activity: '#8b7355',
		note: '#e6b800',
		log: '#6366f1',
		source: '#059669',
		actor: '#8b5cf6',
		plan: '#ec4899',
	};

	const TYPE_LABELS: Record<string, string> = {
		project: 'Project',
		activity: 'Activity',
		note: 'Note',
		log: 'Log',
		source: 'Source',
		actor: 'Actor',
		plan: 'Plan',
	};

	let recentItems = $derived.by(() => {
		const items: Array<{ type: string; title: string; date: string }> = [];

		for (const p of projectsData) {
			items.push({ type: 'project', title: p.title, date: p.updated_at || p.created_at });
		}
		for (const a of activitiesData) {
			items.push({ type: 'activity', title: a.title, date: a.updated_at || a.created_at });
		}
		for (const n of notesData) {
			items.push({ type: 'note', title: n.title || (n.content || '').slice(0, 50) || 'Untitled', date: n.updated_at || n.created_at });
		}
		for (const l of logsData) {
			items.push({ type: 'log', title: l.title || 'Untitled log', date: l.updated_at || l.created_at });
		}
		for (const s of sourcesData) {
			items.push({ type: 'source', title: s.title, date: s.updated_at || s.created_at });
		}
		for (const a of actorsData) {
			items.push({ type: 'actor', title: a.full_name, date: a.updated_at || a.created_at });
		}
		for (const p of plansData) {
			items.push({ type: 'plan', title: p.title, date: p.updated_at || p.created_at });
		}

		items.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
		return items.slice(0, 12);
	});

	// ── "Today" summary for momentum card ──
	let todaySummary = $derived.by(() => {
		const todayIso = new Date().toISOString().slice(0, 10);
		let created = 0;
		let modified = 0;

		const countItem = (createdAt: string, updatedAt: string) => {
			if (createdAt.slice(0, 10) === todayIso) created++;
			else if (updatedAt.slice(0, 10) === todayIso) modified++;
		};

		for (const p of projectsData) countItem(p.created_at, p.updated_at);
		for (const a of activitiesData) countItem(a.created_at, a.updated_at);
		for (const n of notesData) countItem(n.created_at, n.updated_at);
		for (const l of logsData) countItem(l.created_at, l.updated_at);
		for (const s of sourcesData) countItem(s.created_at, s.updated_at);
		for (const a of actorsData) countItem(a.created_at, a.updated_at);
		for (const p of plansData) countItem(p.created_at, p.updated_at);

		return { created, modified, total: created + modified };
	});

	// Total entities across all types
	let totalEntities = $derived(
		projectsData.length + activitiesData.length + notesData.length +
		logsData.length + sourcesData.length + actorsData.length + plansData.length
	);

	async function handleOpenWorkspace(id: number) {
		await setActiveWorkspace(id);
		activeTab.set('workspace');
	}

	async function handleCreateWorkspace() {
		if (!newWsName.trim()) return;
		try {
			const ws = await createWorkspace({ name: newWsName.trim() });
			newWsName = '';
			await setActiveWorkspace(ws.id);
			activeTab.set('workspace');
		} catch (e) {
			console.error('Failed to create workspace:', e);
		}
	}

	function handleWsKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') handleCreateWorkspace();
	}

	onMount(() => {
		// Pick fact on client to ensure consistency
		factIndex = Math.floor(Math.random() * FACTS.length);

		// Subscribe to stores only on client
		const unsubs = [
			workspaces.subscribe(v => workspacesData = v ?? []),
			projects.subscribe(v => projectsData = v ?? []),
			activities.subscribe(v => activitiesData = v ?? []),
			notes.subscribe(v => notesData = v ?? []),
			logs.subscribe(v => logsData = v ?? []),
			sources.subscribe(v => sourcesData = v ?? []),
			actors.subscribe(v => actorsData = v ?? []),
			plans.subscribe(v => plansData = v ?? []),
		];
		ready = true;
		return () => unsubs.forEach(u => u());
	});

	// Interesting facts and stories
	const FACTS = [
		{ text: "Honey never spoils. Archaeologists have found 3,000-year-old honey in Egyptian tombs that was still edible.", category: "Nature" },
		{ text: "Octopuses have three hearts and blue blood. Two hearts pump blood to the gills, while the third pumps it to the rest of the body.", category: "Biology" },
		{ text: "The inventor of the Pringles can is buried in one. Fredric Baur's ashes were placed in a Pringles can after his death in 2008.", category: "History" },
		{ text: "A day on Venus is longer than its year. Venus takes 243 Earth days to rotate but only 225 days to orbit the Sun.", category: "Space" },
		{ text: "The shortest war in history lasted 38 minutes. It was between Britain and Zanzibar on August 27, 1896.", category: "History" },
		{ text: "Bananas are berries, but strawberries aren't. Botanically, berries come from a single ovary—bananas qualify, strawberries don't.", category: "Science" },
		{ text: "Cleopatra lived closer in time to the Moon landing than to the construction of the Great Pyramid.", category: "History" },
		{ text: "There are more possible chess games than atoms in the observable universe. The Shannon number estimates 10^120 possible games.", category: "Math" },
		{ text: "Crows can recognize human faces and hold grudges. They can remember a threatening person for years.", category: "Nature" },
		{ text: "The Eiffel Tower can grow by up to 6 inches in summer due to thermal expansion of the iron.", category: "Engineering" },
		{ text: "A group of flamingos is called a 'flamboyance'. They also sleep on one leg to conserve body heat.", category: "Nature" },
		{ text: "The first computer programmer was Ada Lovelace in the 1840s, over a century before electronic computers existed.", category: "Technology" },
		{ text: "Trees can communicate through an underground fungal network nicknamed the 'Wood Wide Web'.", category: "Nature" },
		{ text: "Scotland's national animal is the unicorn. It has been a Scottish heraldic symbol since the 12th century.", category: "Culture" },
		{ text: "A jiffy is an actual unit of time: 1/100th of a second in computer engineering.", category: "Technology" },
	];

	function getGreeting(): string {
		const hour = new Date().getHours();
		if (hour < 12) return 'Good morning';
		if (hour < 17) return 'Good afternoon';
		return 'Good evening';
	}

	function formatRelativeTime(dateStr: string): string {
		const date = new Date(dateStr);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.floor(diffMs / 60000);
		const diffHours = Math.floor(diffMs / 3600000);
		const diffDays = Math.floor(diffMs / 86400000);

		if (diffMins < 1) return 'just now';
		if (diffMins < 60) return `${diffMins}m ago`;
		if (diffHours < 24) return `${diffHours}h ago`;
		if (diffDays === 1) return 'yesterday';
		if (diffDays < 7) return `${diffDays}d ago`;
		return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
	}

</script>

<div class="dashboard-home">
	{#if ready}
	<header class="greeting">
		<h1>{getGreeting()}</h1>
		{#if factIndex >= 0}
			<p class="fact"><span class="fact-icon">💡</span> {FACTS[factIndex].text} <span class="category">{FACTS[factIndex].category}</span></p>
		{/if}
	</header>
		<div class="dashboard-grid">
			<!-- Workspaces Quick Access -->
			<section class="card workspaces-card">
				<div class="workspaces-header">
					<h2>Workspaces</h2>
					{#if workspacesData.length > 0}
						<button class="ws-view-all" onclick={() => activeTab.set('workspace')}>View all</button>
					{/if}
				</div>
				{#if workspacesData.length === 0}
					<div class="ws-empty">
						<p class="ws-empty-text">No workspaces yet. Create one to start organising your knowledge.</p>
						<div class="ws-new-row ws-new-centered">
							<input
								type="text"
								class="ws-new-input"
								placeholder="Workspace name..."
								bind:value={newWsName}
								onkeydown={handleWsKeydown}
							/>
							<button class="ws-new-btn" onclick={handleCreateWorkspace} disabled={!newWsName.trim()}>+</button>
						</div>
					</div>
				{:else}
					<div class="ws-cards">
						{#each workspacesData as ws (ws.id)}
							<button class="ws-card-item" onclick={() => handleOpenWorkspace(ws.id)}>
								<span class="ws-card-name">{ws.name}</span>
								<span class="ws-card-meta">{ws.items.length} items &middot; {formatRelativeTime(ws.last_opened_at)}</span>
								{#if ws.description}
									<span class="ws-card-desc">{ws.description.length > 60 ? ws.description.slice(0, 60) + '...' : ws.description}</span>
								{/if}
							</button>
						{/each}
						<div class="ws-new-row">
							<input
								type="text"
								class="ws-new-input"
								placeholder="New workspace..."
								bind:value={newWsName}
								onkeydown={handleWsKeydown}
							/>
							<button class="ws-new-btn" onclick={handleCreateWorkspace} disabled={!newWsName.trim()}>+</button>
						</div>
					</div>
				{/if}
			</section>

			<!-- Stats Overview -->
			<section class="card stats-card">
				<h2>Overview</h2>
				<div class="stats-grid">
					<div class="stat">
						<span class="stat-value">{projectsData.filter(p => p.status === 'in_progress' || p.is_active).length}</span>
						<span class="stat-label">In-Progress Projects</span>
					</div>
					<div class="stat">
						<span class="stat-value">{activitiesData.filter(a => a.status === 'in_progress').length}</span>
						<span class="stat-label">In-Progress Activities</span>
					</div>
					<div class="stat">
						<span class="stat-value">{plansData.filter(p => p.status === 'in_progress' || p.is_active).length}</span>
						<span class="stat-label">In-Progress Plans</span>
					</div>
				</div>
				<div class="stats-secondary">
					<span>{notesData.length} notes</span>
					<span>{logsData.length} logs</span>
					<span>{sourcesData.length} sources</span>
					<span>{actorsData.length} actors</span>
				</div>
			</section>

			<!-- Today's Momentum + Recent Activity -->
			<section class="card momentum-card">
				<div class="momentum-header">
					<h2>Knowledge Pulse</h2>
					<div class="momentum-today">
						{#if todaySummary.total > 0}
							<span class="pulse-badge">
								{todaySummary.created > 0 ? `${todaySummary.created} created` : ''}
								{todaySummary.created > 0 && todaySummary.modified > 0 ? ' · ' : ''}
								{todaySummary.modified > 0 ? `${todaySummary.modified} updated` : ''}
								today
							</span>
						{:else}
							<span class="pulse-badge quiet">Nothing yet today</span>
						{/if}
						<span class="pulse-total">{totalEntities} total items</span>
					</div>
				</div>
				{#if recentItems.length === 0}
					<p class="empty-msg">No activity yet. Start capturing your knowledge!</p>
				{:else}
					<div class="activity-feed">
						{#each recentItems as item}
							<div class="feed-item">
								<span class="feed-dot" style:background={TYPE_COLORS[item.type] ?? '#9ca3af'}></span>
								<span class="feed-type" style:color={TYPE_COLORS[item.type] ?? '#9ca3af'}>{TYPE_LABELS[item.type] ?? item.type}</span>
								<span class="feed-title">{item.title}</span>
								<span class="feed-time">{formatRelativeTime(item.date)}</span>
							</div>
						{/each}
					</div>
				{/if}
			</section>

			<!-- Recent Notes -->
			<section class="card notes-card">
				<h2>Recent Notes</h2>
				{#if notesData.length === 0}
					<p class="empty-msg">No notes yet. Capture your thoughts!</p>
				{:else}
					<div class="notes-list">
						{#each [...notesData].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()).slice(0, 5) as note}
							<div class="note-item">
								<span class="note-content">{(note.content || '').length > 60 ? (note.content || '').slice(0, 60) + '...' : (note.content || '')}</span>
								<span class="note-time">{formatRelativeTime(note.updated_at)}</span>
							</div>
						{/each}
					</div>
				{/if}
			</section>

			<!-- Activity History -->
			<section class="card history-card">
				<h2>Activity History (14 days)</h2>
				<div class="chart">
					{#each activityHistory as day}
						<div class="chart-bar-wrapper" title="{day.label}: {day.count} items">
							<div class="chart-bar" style="height: {(day.count / maxCount) * 100}%"></div>
							<span class="chart-label">{day.label.split(' ')[1]}</span>
						</div>
					{/each}
				</div>
			</section>

		</div>
	{:else}
		<div class="loading">Loading dashboard...</div>
	{/if}
</div>

<style>
	.dashboard-home {
		max-width: 1000px;
		margin: 0 auto;
		padding: 20px 0;
	}

	.loading {
		text-align: center;
		padding: 40px;
		color: #9ca3af;
	}

	.greeting {
		text-align: center;
		margin-bottom: 32px;
	}
	.greeting h1 {
		font-size: 1.8rem;
		font-weight: 300;
		color: #374151;
		margin: 0 0 12px;
	}
	.fact {
		font-size: 0.9rem;
		color: #6b7280;
		margin: 0;
		max-width: 700px;
		margin-left: auto;
		margin-right: auto;
		line-height: 1.5;
	}
	.fact-icon {
		margin-right: 6px;
	}
	.category {
		display: inline-block;
		font-size: 0.7rem;
		padding: 2px 8px;
		background: #f3f4f6;
		color: #6b7280;
		border-radius: 10px;
		margin-left: 8px;
		vertical-align: middle;
	}

	.dashboard-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 16px;
	}

	.card {
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 10px;
		padding: 16px;
	}
	.card h2 {
		font-size: 0.8rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: #9ca3af;
		margin: 0 0 12px;
	}

	.empty-msg {
		font-size: 0.85rem;
		color: #9ca3af;
		text-align: center;
		padding: 16px 0;
		margin: 0;
	}

	/* Stats Card */
	.stats-card {
		grid-column: span 3;
	}
	.stats-grid {
		display: flex;
		gap: 24px;
		justify-content: center;
		margin-bottom: 12px;
	}
	.stat {
		text-align: center;
		min-width: 100px;
	}
	.stat-value {
		display: block;
		font-size: 2rem;
		font-weight: 300;
		color: #111827;
	}
	.stat-label {
		font-size: 0.75rem;
		color: #6b7280;
	}
	.stats-secondary {
		display: flex;
		justify-content: center;
		gap: 16px;
		font-size: 0.7rem;
		color: #9ca3af;
		border-top: 1px solid #f3f4f6;
		padding-top: 10px;
	}

	/* Knowledge Pulse / Momentum Card */
	.momentum-card {
		grid-column: span 2;
	}
	.momentum-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 4px;
	}
	.momentum-header h2 {
		margin-bottom: 0;
	}
	.momentum-today {
		display: flex;
		align-items: center;
		gap: 10px;
	}
	.pulse-badge {
		font-size: 0.7rem;
		font-weight: 500;
		color: #059669;
		background: #ecfdf5;
		padding: 3px 10px;
		border-radius: 10px;
	}
	.pulse-badge.quiet {
		color: #9ca3af;
		background: #f9fafb;
	}
	.pulse-total {
		font-size: 0.65rem;
		color: #9ca3af;
	}
	.activity-feed {
		display: flex;
		flex-direction: column;
		gap: 2px;
		max-height: 340px;
		overflow-y: auto;
	}
	.feed-item {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 6px 8px;
		border-radius: 6px;
		transition: background 0.12s;
	}
	.feed-item:hover {
		background: #f9fafb;
	}
	.feed-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.feed-type {
		font-size: 0.65rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.3px;
		width: 56px;
		flex-shrink: 0;
	}
	.feed-title {
		flex: 1;
		min-width: 0;
		font-size: 0.82rem;
		color: #374151;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.feed-time {
		font-size: 0.65rem;
		color: #9ca3af;
		flex-shrink: 0;
		white-space: nowrap;
	}

	/* Notes Card */
	.notes-card {
		grid-column: span 1;
	}
	.notes-list {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.note-item {
		display: flex;
		flex-direction: column;
		gap: 2px;
		padding: 8px;
		background: #fffef5;
		border-radius: 6px;
		border-left: 2px solid #fef3c7;
	}
	.note-content {
		font-size: 0.8rem;
		color: #374151;
		line-height: 1.4;
	}
	.note-time {
		font-size: 0.65rem;
		color: #9ca3af;
	}

	/* History Card */
	.history-card {
		grid-column: span 3;
	}
	.chart {
		display: flex;
		align-items: flex-end;
		gap: 4px;
		height: 80px;
		padding-top: 8px;
	}
	.chart-bar-wrapper {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		height: 100%;
		justify-content: flex-end;
	}
	.chart-bar {
		width: 100%;
		min-height: 2px;
		background: #3b82f6;
		border-radius: 3px 3px 0 0;
		transition: height 0.3s;
	}
	.chart-label {
		font-size: 0.55rem;
		color: #9ca3af;
		margin-top: 4px;
	}

	/* Workspaces Card */
	.workspaces-card {
		grid-column: span 3;
	}
	.workspaces-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}
	.workspaces-header h2 {
		margin-bottom: 0;
	}
	.ws-view-all {
		border: none;
		background: none;
		cursor: pointer;
		font-size: 0.72rem;
		color: #3b82f6;
		font-weight: 500;
		transition: color 0.15s;
	}
	.ws-view-all:hover {
		color: #2563eb;
	}
	.ws-cards {
		display: flex;
		gap: 8px;
		flex-wrap: wrap;
		margin-top: 10px;
	}
	.ws-card-item {
		display: flex;
		flex-direction: column;
		gap: 4px;
		padding: 10px 14px;
		border: 1px solid #e5e7eb;
		border-radius: 8px;
		background: white;
		cursor: pointer;
		transition: all 0.15s;
		text-align: left;
		min-width: 140px;
	}
	.ws-card-item:hover {
		background: #f9fafb;
		border-color: #d1d5db;
	}
	.ws-card-name {
		font-size: 0.85rem;
		font-weight: 500;
		color: #374151;
	}
	.ws-card-meta {
		font-size: 0.65rem;
		color: #9ca3af;
	}
	.ws-card-desc {
		font-size: 0.7rem;
		color: #9ca3af;
		line-height: 1.3;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.ws-empty {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 12px;
		padding: 16px 0 8px;
	}
	.ws-empty-text {
		font-size: 0.85rem;
		color: #9ca3af;
		margin: 0;
	}
	.ws-new-centered {
		justify-content: center;
	}
	.ws-new-row {
		display: flex;
		gap: 4px;
		align-items: center;
	}
	.ws-new-input {
		padding: 8px 10px;
		border: 1px dashed #d1d5db;
		border-radius: 8px;
		font-size: 0.8rem;
		outline: none;
		width: 140px;
		transition: border-color 0.15s;
	}
	.ws-new-input:focus {
		border-color: #6b7280;
		border-style: solid;
	}
	.ws-new-btn {
		width: 30px;
		height: 30px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		background: white;
		cursor: pointer;
		font-size: 1rem;
		color: #6b7280;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.15s;
	}
	.ws-new-btn:hover:not(:disabled) {
		background: #374151;
		color: white;
		border-color: #374151;
	}
	.ws-new-btn:disabled {
		opacity: 0.4;
		cursor: default;
	}

	@media (max-width: 800px) {
		.dashboard-grid {
			grid-template-columns: 1fr;
		}
		.stats-card, .history-card, .workspaces-card {
			grid-column: span 1;
		}
		.momentum-card {
			grid-column: span 1;
		}
		.stats-grid {
			flex-wrap: wrap;
		}
	}
</style>

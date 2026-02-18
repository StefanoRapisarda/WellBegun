<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { panels, togglePanel, configurePanels, freshSession } from '$lib/stores/panels';
	import { deactivateAllProjects, deactivateProject } from '$lib/api/projects';
	import { deactivateAllActivities, deactivateActivity } from '$lib/api/activities';
	import { deactivateLog } from '$lib/api/logs';
	import { deactivateSource } from '$lib/api/sources';
	import { deactivateActor } from '$lib/api/actors';
	import { deactivateReadingList } from '$lib/api/readingLists';
	import { clearAllLastUsedTags } from '$lib/stores/lastUsedTags';
	import { loadProjects } from '$lib/stores/projects';
	import { loadLogs } from '$lib/stores/logs';
	import { loadNotes } from '$lib/stores/notes';
	import { loadSources } from '$lib/stores/sources';
	import { loadActors } from '$lib/stores/actors';
	import { loadActivities } from '$lib/stores/activities';
	import { loadReadingLists } from '$lib/stores/readingLists';
	import { loadPlans } from '$lib/stores/plans';
	import { loadTags } from '$lib/stores/tags';
	import { activeTab } from '$lib/stores/activeTab';
	import { get } from 'svelte/store';
	import { focusSelection, isFocusActive } from '$lib/stores/focus';
	import { projects } from '$lib/stores/projects';
	import { logs } from '$lib/stores/logs';
	import { activities } from '$lib/stores/activities';
	import { sources } from '$lib/stores/sources';
	import { actors } from '$lib/stores/actors';
	import { readingLists } from '$lib/stores/readingLists';
	import { plans } from '$lib/stores/plans';
	import { deactivatePlan } from '$lib/api/plans';
	import { showArchived, showActiveRelated } from '$lib/stores/dateFilter';
	import DateFilterControl from '$lib/components/shared/DateFilterControl.svelte';
	import TagFilterControl from '$lib/components/shared/TagFilterControl.svelte';
	import DashboardHome from '$lib/components/DashboardHome.svelte';
	import FocusEditor from '$lib/components/writer/FocusEditor.svelte';
	import ProjectScaffoldingPanel from '$lib/components/scaffolding/ProjectScaffoldingPanel.svelte';
	import AiAssistant from '$lib/components/ai/AiAssistant.svelte';
	import KnowledgeGraph from '$lib/components/graph/KnowledgeGraph.svelte';
	import ReadTab from '$lib/components/reader/ReadTab.svelte';
	import NotepadTab from '$lib/components/notepad/NotepadTab.svelte';
	import SchemaTab from '$lib/components/schema/SchemaTab.svelte';
	import Logo from '$lib/components/shared/Logo.svelte';

	let { children } = $props();

	// Tools menu state
	const toolsTabs = ['write', 'read', 'schema', 'scaffold'];
	let showToolsMenu = $state(false);
	let toolsBtnEl: HTMLButtonElement | undefined = $state();
	let isToolsActive = $derived(toolsTabs.includes($activeTab));

	function toggleToolsMenu() {
		showToolsMenu = !showToolsMenu;
	}

	function handleToolsClickOutside(e: MouseEvent) {
		if (toolsBtnEl && !toolsBtnEl.contains(e.target as Node)) {
			showToolsMenu = false;
		}
	}

	$effect(() => {
		if (showToolsMenu) {
			document.addEventListener('click', handleToolsClickOutside, true);
			return () => document.removeEventListener('click', handleToolsClickOutside, true);
		}
	});

	function selectToolsTab(tab: string) {
		activeTab.set(tab);
		showToolsMenu = false;
	}

	// "Working on..." bar — derived from active projects, activities & plans
	function truncate(s: string, max: number): string {
		return s.length > max ? s.slice(0, max - 1) + '\u2026' : s;
	}
	let activeProjects = $derived($projects.filter((p) => p.is_active));
	let activeLogs = $derived($logs.filter((l) => l.is_active));
	let activeActivities = $derived($activities.filter((a) => a.is_active));
	let activeSources = $derived($sources.filter((s) => s.is_active));
	let activeActors = $derived($actors.filter((a) => a.is_active));
	let activeReadingLists = $derived($readingLists.filter((r) => r.is_active));
	let activePlans = $derived($plans.filter((p) => p.is_active));

	const ENTITY_COLORS: Record<string, string> = {
		project: '#5c7a99',
		log: '#8b7355',
		note: '#6b8e6b',
		activity: '#b5838d',
		source: '#c9a227',
		actor: '#8b4557',
		reading_list: '#5f9ea0',
		plan: '#6b8ba3'
	};

	// All active entity items for the "Working on..." bar, with colors
	let activeItems = $derived.by(() => {
		const items: { name: string; color: string }[] = [];
		for (const p of activeProjects) items.push({ name: truncate(p.title, 30), color: ENTITY_COLORS.project });
		for (const a of activeActivities) items.push({ name: truncate(a.title, 30), color: ENTITY_COLORS.activity });
		for (const p of activePlans) items.push({ name: truncate(p.title, 30), color: ENTITY_COLORS.plan });
		for (const l of activeLogs) items.push({ name: truncate(l.title, 30), color: ENTITY_COLORS.log });
		for (const s of activeSources) items.push({ name: truncate(s.title, 30), color: ENTITY_COLORS.source });
		for (const a of activeActors) items.push({ name: truncate(a.full_name, 30), color: ENTITY_COLORS.actor });
		for (const r of activeReadingLists) items.push({ name: truncate(r.title, 30), color: ENTITY_COLORS.reading_list });
		return items;
	});

	let hasActiveItems = $derived(activeItems.length > 0);

	// "Working on" panel state
	let showWorkingOnPanel = $state(false);
	let workingOnBarEl: HTMLDivElement | undefined = $state();

	function toggleWorkingOnPanel() {
		showWorkingOnPanel = !showWorkingOnPanel;
	}

	function handleWorkingOnPanelClickOutside(e: MouseEvent) {
		if (workingOnBarEl && !workingOnBarEl.contains(e.target as Node)) {
			showWorkingOnPanel = false;
		}
	}

	async function handleDeactivateProject(id: number) {
		await deactivateProject(id);
		await loadProjects();
	}

	async function handleDeactivateLog(id: number) {
		await deactivateLog(id);
		await loadLogs();
	}

	async function handleDeactivateActivity(id: number) {
		await deactivateActivity(id);
		await loadActivities();
	}

	async function handleDeactivateSource(id: number) {
		await deactivateSource(id);
		await loadSources();
	}

	async function handleDeactivateActor(id: number) {
		await deactivateActor(id);
		await loadActors();
	}

	async function handleDeactivateReadingList(id: number) {
		await deactivateReadingList(id);
		await loadReadingLists();
	}

	async function handleDeactivatePlan(id: number) {
		await deactivatePlan(id);
		await loadPlans();
	}

	$effect(() => {
		if (showWorkingOnPanel) {
			document.addEventListener('click', handleWorkingOnPanelClickOutside, true);
			return () => document.removeEventListener('click', handleWorkingOnPanelClickOutside, true);
		}
	});

	// Load all stores on app start
	onMount(async () => {
		// On a fresh session (new tab/window), deactivate everything and clear tag memory
		if (freshSession) {
			clearAllLastUsedTags();
			await Promise.allSettled([
				deactivateAllProjects(),
				deactivateAllActivities()
			]);
		}

		Promise.allSettled([
			loadProjects(),
			loadLogs(),
			loadNotes(),
			loadSources(),
			loadActors(),
			loadActivities(),
			loadReadingLists(),
			loadPlans(),
			loadTags()
		]).then((results) => {
			for (const r of results) {
				if (r.status === 'rejected') {
					console.warn('Store load failed:', r.reason);
				}
			}
			// If no focus is active on startup, show default panels
			if (!isFocusActive(get(focusSelection))) {
				configurePanels(
					['project', 'activity', 'log', 'note'],
					['project', 'log', 'note', 'activity']
				);
			}
		});
	});
</script>

<div class="app">
	<header class="toolbar">
		<div class="brand-row">
			<div class="app-brand">
				<Logo size={32} />
				<h1 class="app-title">WellBegun</h1>
			</div>
		</div>
		<div class="tab-row">
			<nav class="tab-bar">
				<button class="tab-btn" class:active={$activeTab === 'dashboard'} onclick={() => activeTab.set('dashboard')}>Home</button>
				<button class="tab-btn" class:active={$activeTab === 'input'} onclick={() => activeTab.set('input')}>Cards</button>
				<button class="tab-btn" class:active={$activeTab === 'notepad'} onclick={() => activeTab.set('notepad')}>Notepad</button>
				<button class="tab-btn" class:active={$activeTab === 'graph'} onclick={() => activeTab.set('graph')}>Graph</button>
				<div class="tools-wrapper">
					<button
						class="tab-btn"
						class:active={isToolsActive}
						bind:this={toolsBtnEl}
						onclick={toggleToolsMenu}
					>Tools</button>
					{#if showToolsMenu}
						<div class="tools-menu">
							<button class="tools-menu-item" class:active={$activeTab === 'write'} onclick={() => selectToolsTab('write')}>Write</button>
							<button class="tools-menu-item" class:active={$activeTab === 'read'} onclick={() => selectToolsTab('read')}>Read</button>
							<button class="tools-menu-item" class:active={$activeTab === 'schema'} onclick={() => selectToolsTab('schema')}>Schema</button>
							<button class="tools-menu-item" class:active={$activeTab === 'scaffold'} onclick={() => selectToolsTab('scaffold')}>Scaffold</button>
						</div>
					{/if}
				</div>
			</nav>
		</div>
		{#if hasActiveItems}
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div class="working-on-bar" bind:this={workingOnBarEl} onclick={toggleWorkingOnPanel}>
				<span class="working-on-text">
					<span class="working-on-label">Working on</span>
					{#each activeItems as item, i}
						{#if i > 0}<span class="working-on-sep">,&nbsp;</span>{/if}
						<span class="working-on-entity" style:color={item.color}>{item.name}</span>
					{/each}
				</span>
				<span class="working-on-chevron" class:open={showWorkingOnPanel}>&#x25BE;</span>
			</div>
			{#if showWorkingOnPanel}
				<div class="working-on-panel">
					{#if activeProjects.length > 0}
						<div class="wop-group">
							<h4 class="wop-group-label">Projects</h4>
							{#each activeProjects as project (project.id)}
								<div class="wop-item">
									<span class="wop-item-title">{project.title}</span>
									<button class="wop-deactivate" onclick={(e) => { e.stopPropagation(); handleDeactivateProject(project.id); }} title="Deactivate">&times;</button>
								</div>
							{/each}
						</div>
					{/if}
					{#if activeActivities.length > 0}
						<div class="wop-group">
							<h4 class="wop-group-label">Activities</h4>
							{#each activeActivities as activity (activity.id)}
								<div class="wop-item">
									<span class="wop-item-title">{activity.title}</span>
									<button class="wop-deactivate" onclick={(e) => { e.stopPropagation(); handleDeactivateActivity(activity.id); }} title="Deactivate">&times;</button>
								</div>
							{/each}
						</div>
					{/if}
					{#if activePlans.length > 0}
						<div class="wop-group">
							<h4 class="wop-group-label">Plans</h4>
							{#each activePlans as plan (plan.id)}
								<div class="wop-item">
									<span class="wop-item-title">{plan.title}</span>
									<button class="wop-deactivate" onclick={(e) => { e.stopPropagation(); handleDeactivatePlan(plan.id); }} title="Deactivate">&times;</button>
								</div>
							{/each}
						</div>
					{/if}
					{#if activeLogs.length > 0}
						<div class="wop-group">
							<h4 class="wop-group-label">Logs</h4>
							{#each activeLogs as log (log.id)}
								<div class="wop-item">
									<span class="wop-item-title">{log.title}</span>
									<button class="wop-deactivate" onclick={(e) => { e.stopPropagation(); handleDeactivateLog(log.id); }} title="Deactivate">&times;</button>
								</div>
							{/each}
						</div>
					{/if}
					{#if activeSources.length > 0}
						<div class="wop-group">
							<h4 class="wop-group-label">Sources</h4>
							{#each activeSources as source (source.id)}
								<div class="wop-item">
									<span class="wop-item-title">{source.title}</span>
									<button class="wop-deactivate" onclick={(e) => { e.stopPropagation(); handleDeactivateSource(source.id); }} title="Deactivate">&times;</button>
								</div>
							{/each}
						</div>
					{/if}
					{#if activeActors.length > 0}
						<div class="wop-group">
							<h4 class="wop-group-label">Actors</h4>
							{#each activeActors as actor (actor.id)}
								<div class="wop-item">
									<span class="wop-item-title">{actor.full_name}</span>
									<button class="wop-deactivate" onclick={(e) => { e.stopPropagation(); handleDeactivateActor(actor.id); }} title="Deactivate">&times;</button>
								</div>
							{/each}
						</div>
					{/if}
					{#if activeReadingLists.length > 0}
						<div class="wop-group">
							<h4 class="wop-group-label">Reading Lists</h4>
							{#each activeReadingLists as rl (rl.id)}
								<div class="wop-item">
									<span class="wop-item-title">{rl.title}</span>
									<button class="wop-deactivate" onclick={(e) => { e.stopPropagation(); handleDeactivateReadingList(rl.id); }} title="Deactivate">&times;</button>
								</div>
							{/each}
						</div>
					{/if}
				</div>
			{/if}
		{/if}
		{#if $activeTab === 'input' || $activeTab === 'graph'}
			<div class="input-bar">
				{#if $activeTab === 'input'}
					<nav class="panel-toggles">
						{#each $panels as panel (panel.id)}
							<button
								class="toggle-btn"
								class:active={panel.visible}
								style:--panel-color={panel.color}
								onclick={() => togglePanel(panel.id)}
							>
								{panel.label}
							</button>
						{/each}
					</nav>
				{/if}
				<div class="filters" class:filters-full={$activeTab === 'graph'}>
					<label class="archived-toggle">
						<input type="checkbox" bind:checked={$showArchived} />
						Archived
					</label>
					<label class="archived-toggle">
						<input type="checkbox" bind:checked={$showActiveRelated} />
						Active Related
					</label>
					<DateFilterControl />
					<TagFilterControl />
					{#if $activeTab === 'input'}
						<button class="view-switch-btn" onclick={() => activeTab.set('graph')} title="Switch to Graph view">
							<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
								<circle cx="6" cy="6" r="3"/><circle cx="18" cy="18" r="3"/><circle cx="18" cy="6" r="3"/>
								<line x1="8.5" y1="7.5" x2="15.5" y2="16.5"/><line x1="15.5" y1="6" x2="8.5" y2="6"/>
							</svg>
							Graph
						</button>
					{:else if $activeTab === 'graph'}
						<button class="view-switch-btn" onclick={() => activeTab.set('input')} title="Switch to Cards view">
							<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
								<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
								<rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
							</svg>
							Cards
						</button>
					{/if}
				</div>
			</div>
		{/if}
	</header>
	<main class:no-padding={$activeTab === 'write' || $activeTab === 'read' || $activeTab === 'graph' || $activeTab === 'notepad' || $activeTab === 'schema'}>
		{#if $activeTab === 'dashboard'}
			<DashboardHome />
		{:else if $activeTab === 'input'}
			{@render children()}
		{:else if $activeTab === 'notepad'}
			<NotepadTab />
		{:else if $activeTab === 'write'}
			<FocusEditor />
		{:else if $activeTab === 'read'}
			<ReadTab />
		{:else if $activeTab === 'scaffold'}
			<ProjectScaffoldingPanel />
		{:else if $activeTab === 'graph'}
			<KnowledgeGraph />
		{:else if $activeTab === 'schema'}
			<SchemaTab />
		{/if}
	</main>
</div>

<AiAssistant />

<style>
	.app {
		min-height: 100vh;
	}
	.toolbar {
		display: flex;
		flex-direction: column;
		background: white;
		position: sticky;
		top: 0;
		z-index: 50;
	}

	/* Brand row — logo top-left */
	.brand-row {
		padding: 10px 20px 0;
	}
	.app-brand {
		display: flex;
		align-items: center;
		gap: 10px;
	}
	.app-title {
		font-size: 1.15rem;
		font-weight: 700;
		color: #374151;
		margin: 0;
		white-space: nowrap;
		letter-spacing: -0.5px;
	}

	/* Tab row — centered tabs sitting on a divider line */
	.tab-row {
		display: flex;
		justify-content: center;
		padding: 12px 20px 0;
		border-bottom: 1px solid #1f2937;
	}
	.tab-bar {
		display: flex;
		gap: 0;
		position: relative;
		bottom: -1px; /* overlap the border */
	}
	.tab-btn {
		padding: 8px 20px;
		border: none;
		border-bottom: 2px solid transparent;
		background: transparent;
		cursor: pointer;
		font-size: 0.8rem;
		color: #9ca3af;
		font-weight: 500;
		transition: all 0.15s;
	}
	.tab-btn:hover {
		color: #6b7280;
	}
	.tab-btn.active {
		color: #111827;
		border-bottom-color: #111827;
	}
	.tab-separator {
		width: 1px;
		height: 16px;
		background: #d1d5db;
		align-self: center;
		margin: 0 14px;
		flex-shrink: 0;
	}
	.tools-wrapper {
		position: relative;
	}
	.tools-menu {
		position: absolute;
		top: calc(100% + 3px);
		left: 50%;
		transform: translateX(-50%);
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 6px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
		min-width: 120px;
		z-index: 60;
		padding: 4px 0;
	}
	.tools-menu-item {
		display: block;
		width: 100%;
		padding: 8px 16px;
		border: none;
		background: none;
		cursor: pointer;
		font-size: 0.8rem;
		color: #6b7280;
		text-align: left;
		transition: all 0.1s;
	}
	.tools-menu-item:hover {
		background: #f3f4f6;
		color: #374151;
	}
	.tools-menu-item.active {
		color: #111827;
		font-weight: 600;
	}

	/* Working-on bar — global context indicator */
	.working-on-bar {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 6px;
		padding: 6px 20px;
		background: white;
		border-bottom: 1px solid #e5e7eb;
		cursor: pointer;
		transition: background 0.15s;
	}
	.working-on-bar:hover {
		background: #f9fafb;
	}
	.working-on-text {
		font-size: 0.8rem;
		color: #9ca3af;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.working-on-label {
		color: #9ca3af;
	}
	.working-on-sep {
		color: #d1d5db;
	}
	.working-on-entity {
		font-weight: 500;
	}
	.working-on-chevron {
		font-size: 0.75rem;
		color: #9ca3af;
		transition: transform 0.15s;
	}
	.working-on-chevron.open {
		transform: rotate(180deg);
	}

	/* Working-on dropdown panel */
	.working-on-panel {
		background: white;
		border-bottom: 1px solid #e5e7eb;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
		padding: 10px 20px;
		display: flex;
		gap: 24px;
		justify-content: center;
	}
	.wop-group {
		min-width: 140px;
		max-width: 280px;
	}
	.wop-group-label {
		font-size: 0.65rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: #9ca3af;
		margin: 0 0 6px;
	}
	.wop-item {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		padding: 4px 8px;
		border-radius: 6px;
		transition: background 0.1s;
	}
	.wop-item:hover {
		background: #f9fafb;
	}
	.wop-item-title {
		font-size: 0.8rem;
		color: #374151;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.wop-deactivate {
		flex-shrink: 0;
		width: 20px;
		height: 20px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: none;
		border-radius: 4px;
		background: transparent;
		color: #9ca3af;
		font-size: 1rem;
		cursor: pointer;
		transition: all 0.15s;
	}
	.wop-deactivate:hover {
		background: #fee2e2;
		color: #dc2626;
	}

	/* Input sub-bar — panel toggles left, filters right */
	.input-bar {
		display: flex;
		align-items: center;
		padding: 8px 20px;
		background: #fafafa;
		border-bottom: 1px solid #e5e7eb;
	}
	.panel-toggles {
		display: flex;
		gap: 4px;
		flex-shrink: 0;
	}
	.toggle-btn {
		padding: 4px 8px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		background: white;
		cursor: pointer;
		font-size: 0.7rem;
		color: #6b7280;
		transition: all 0.15s;
		white-space: nowrap;
	}
	.toggle-btn.active {
		background: var(--panel-color, #111827);
		color: white;
		border-color: var(--panel-color, #111827);
	}
	.filters {
		display: flex;
		align-items: center;
		gap: 10px;
		flex-shrink: 1;
		min-width: 0;
		margin-left: auto;
		padding-left: 16px;
		border-left: 1px solid #d1d5db;
	}

	main {
		padding: 20px;
	}
	main.no-padding {
		padding: 0;
	}
	.filters-full {
		margin-left: 0;
		padding-left: 0;
		border-left: none;
	}
	.view-switch-btn {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 4px 10px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		background: white;
		cursor: pointer;
		font-size: 0.7rem;
		color: #6b7280;
		white-space: nowrap;
		flex-shrink: 0;
		transition: all 0.15s;
	}
	.view-switch-btn:hover {
		background: #f3f4f6;
		color: #374151;
	}
	.archived-toggle {
		display: flex;
		align-items: center;
		gap: 4px;
		font-size: 0.7rem;
		color: #6b7280;
		cursor: pointer;
		white-space: nowrap;
		flex-shrink: 0;
	}
	.archived-toggle input[type='checkbox'] {
		width: 13px;
		height: 13px;
		accent-color: #6b7280;
		cursor: pointer;
	}
</style>

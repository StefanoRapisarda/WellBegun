<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { panels, togglePanel, configurePanels, freshSession } from '$lib/stores/panels';
	import { deactivateAllProjects, deactivateProject } from '$lib/api/projects';
	import { deactivateAllActivities, deactivateActivity } from '$lib/api/activities';
	import { clearAllLastUsedTags } from '$lib/stores/lastUsedTags';
	import { loadProjects } from '$lib/stores/projects';
	import { loadLogs } from '$lib/stores/logs';
	import { loadNotes } from '$lib/stores/notes';
	import { loadSources } from '$lib/stores/sources';
	import { loadActors } from '$lib/stores/actors';
	import { loadActivities } from '$lib/stores/activities';
	import { loadReadingLists } from '$lib/stores/readingLists';
	import { loadLearningTracks } from '$lib/stores/learningTracks';
	import { loadTags } from '$lib/stores/tags';
	import { activeTab } from '$lib/stores/activeTab';
	import { get } from 'svelte/store';
	import { focusSelection, isFocusActive, deactivateFocus } from '$lib/stores/focus';
	import { projects } from '$lib/stores/projects';
	import { activities } from '$lib/stores/activities';
	import { showArchived, showActiveRelated } from '$lib/stores/dateFilter';
	import DateFilterControl from '$lib/components/shared/DateFilterControl.svelte';
	import TagFilterControl from '$lib/components/shared/TagFilterControl.svelte';
	import Dashboard from '$lib/components/Dashboard.svelte';
	import DashboardHome from '$lib/components/DashboardHome.svelte';
	import FocusEditor from '$lib/components/writer/FocusEditor.svelte';
	import ProjectScaffoldingPanel from '$lib/components/scaffolding/ProjectScaffoldingPanel.svelte';
	import AiAssistant from '$lib/components/ai/AiAssistant.svelte';
	import KnowledgeGraph from '$lib/components/graph/KnowledgeGraph.svelte';
	import ReadTab from '$lib/components/reader/ReadTab.svelte';
	import Logo from '$lib/components/shared/Logo.svelte';

	let { children } = $props();

	// "Working on..." bar — derived from active projects & activities
	function truncate(s: string, max: number): string {
		return s.length > max ? s.slice(0, max - 1) + '\u2026' : s;
	}
	let activeProjects = $derived($projects.filter((p) => p.is_active));
	let activeActivities = $derived($activities.filter((a) => a.is_active));
	let activeProjectNames = $derived(activeProjects.map((p) => truncate(p.title, 30)));
	let activeActivityNames = $derived(activeActivities.map((a) => truncate(a.title, 30)));
	let workingOnText = $derived.by(() => {
		const hasProjects = activeProjectNames.length > 0;
		const hasActivities = activeActivityNames.length > 0;
		if (!hasProjects && !hasActivities) return '';
		const projectsPart = hasProjects ? activeProjectNames.join(', ') : '';
		const activitiesPart = hasActivities ? activeActivityNames.join(', ') : '';
		const combined = hasProjects && hasActivities
			? `${projectsPart} and ${activitiesPart}`
			: projectsPart || activitiesPart;
		return `Working on ${combined}`;
	});

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

	async function handleDeactivateActivity(id: number) {
		await deactivateActivity(id);
		await loadActivities();
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
			loadLearningTracks(),
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
				<button class="tab-btn" class:active={$activeTab === 'input'} onclick={() => activeTab.set('input')}>Input</button>
				<button class="tab-btn" class:active={$activeTab === 'graph'} onclick={() => activeTab.set('graph')}>Graph</button>
				<button class="tab-btn" class:active={$activeTab === 'query'} onclick={() => activeTab.set('query')}>Query</button>
				<button class="tab-btn" class:active={$activeTab === 'write'} onclick={() => activeTab.set('write')}>Write</button>
				<button class="tab-btn" class:active={$activeTab === 'read'} onclick={() => activeTab.set('read')}>Read</button>
				<button class="tab-btn" class:active={$activeTab === 'scaffold'} onclick={() => activeTab.set('scaffold')}>Scaffold</button>
			</nav>
		</div>
		{#if workingOnText}
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div class="working-on-bar" bind:this={workingOnBarEl} onclick={toggleWorkingOnPanel}>
				<span class="working-on-text">{workingOnText}</span>
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
				</div>
			{/if}
		{/if}
		{#if $activeTab === 'input'}
			<div class="input-bar">
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
				<div class="filters">
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
					{#if isFocusActive($focusSelection)}
						<button class="clear-focus-btn" onclick={deactivateFocus}>
							Clear Focus
						</button>
					{/if}
				</div>
			</div>
		{/if}
	</header>
	<main class:no-padding={$activeTab === 'write' || $activeTab === 'read' || $activeTab === 'graph'}>
		{#if $activeTab === 'dashboard'}
			<DashboardHome />
		{:else if $activeTab === 'input'}
			{@render children()}
		{:else if $activeTab === 'query'}
			<Dashboard />
		{:else if $activeTab === 'write'}
			<FocusEditor />
		{:else if $activeTab === 'read'}
			<ReadTab />
		{:else if $activeTab === 'scaffold'}
			<ProjectScaffoldingPanel />
		{:else if $activeTab === 'graph'}
			<KnowledgeGraph />
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

	/* Working-on bar — global context indicator */
	.working-on-bar {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 6px;
		padding: 6px 20px;
		background: #fffbeb;
		border-bottom: 1px solid #e5e0d0;
		cursor: pointer;
		transition: background 0.15s;
	}
	.working-on-bar:hover {
		background: #fef9c3;
	}
	.working-on-text {
		font-family: 'Georgia', 'Times New Roman', 'Palatino', serif;
		font-size: 0.92rem;
		color: #78716c;
		font-style: italic;
		letter-spacing: 0.2px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
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
		overflow: hidden;
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
	.clear-focus-btn {
		padding: 3px 8px;
		border: 1px solid #fecaca;
		border-radius: 6px;
		background: #fef2f2;
		color: #dc2626;
		font-size: 0.7rem;
		cursor: pointer;
		font-weight: 500;
		transition: all 0.15s;
		flex-shrink: 0;
		white-space: nowrap;
	}
	.clear-focus-btn:hover {
		background: #fee2e2;
	}
</style>

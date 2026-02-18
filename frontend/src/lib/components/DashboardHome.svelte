<script lang="ts">
	import { onMount } from 'svelte';
	import { notes } from '$lib/stores/notes';
	import { logs } from '$lib/stores/logs';
	import { projects } from '$lib/stores/projects';
	import { activities } from '$lib/stores/activities';
	import { sources } from '$lib/stores/sources';
	import { actors } from '$lib/stores/actors';
	import { readingLists } from '$lib/stores/readingLists';
	import { tags } from '$lib/stores/tags';
	import { focusSelection, activateFocus, isFocusActive, deactivateFocus } from '$lib/stores/focus';
	import { getEntityTags } from '$lib/api/tags';
	import { activateProject } from '$lib/api/projects';
	import { activateActivity } from '$lib/api/activities';
	import { loadProjects } from '$lib/stores/projects';
	import { loadActivities } from '$lib/stores/activities';
	import type { Note, Project, Activity, Source, Actor, ReadingListItem, Log, Tag } from '$lib/types';

	// Only render data grid after mount to avoid SSR issues
	let ready = $state(false);

	// Local state copies of store data
	let projectsData = $state<Project[]>([]);
	let activitiesData = $state<Activity[]>([]);
	let notesData = $state<Note[]>([]);
	let logsData = $state<Log[]>([]);
	let sourcesData = $state<Source[]>([]);
	let actorsData = $state<Actor[]>([]);
	let readingListsData = $state<ReadingListItem[]>([]);
	let tagsData = $state<Tag[]>([]);

	// Focus selection state
	let selectedProjectIds = $state<number[]>([]);
	let selectedActivityIds = $state<number[]>([]);

	// Map: activityId -> set of projectIds it's tagged with
	let activityProjectMap = $state<Record<number, number[]>>({});

	// Map: projectId -> project-category tags (e.g. Personal, Work)
	let projectTagMap = $state<Record<number, Tag[]>>({});

	// Pick random fact on client only to avoid SSR hydration mismatch
	let factIndex = $state(-1);

	// Non-archived projects and activities for focus card
	let focusProjects = $derived(projectsData.filter(p => !p.is_archived));
	let allFocusActivities = $derived(activitiesData.filter(a => !a.is_archived));

	// Visible activities depend on selected projects
	let visibleActivities = $derived.by(() => {
		if (selectedProjectIds.length === 0) {
			// No project selected: show activities not tagged to any project
			return allFocusActivities.filter(a => {
				const projIds = activityProjectMap[a.id];
				return !projIds || projIds.length === 0;
			});
		}
		// Project(s) selected: show activities tagged with any selected project
		return allFocusActivities.filter(a => {
			const projIds = activityProjectMap[a.id];
			if (!projIds) return false;
			return projIds.some(pid => selectedProjectIds.includes(pid));
		});
	});

	// Project filter by tag (All / Personal / Work / etc.)
	let projectFilter = $state<string | null>(null);

	// Fixed project filter options
	const projectFilterOptions = ['Personal', 'Work'];

	// Filtered projects based on selected filter
	let filteredFocusProjects = $derived.by(() => {
		if (!projectFilter) return focusProjects;
		return focusProjects.filter(p => {
			const tags = projectTagMap[p.id] || [];
			return tags.some(t => t.name === projectFilter);
		});
	});

	let hasSelection = $derived(selectedProjectIds.length > 0 || selectedActivityIds.length > 0);

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

	function toggleProject(id: number) {
		if (selectedProjectIds.includes(id)) {
			selectedProjectIds = selectedProjectIds.filter(x => x !== id);
		} else {
			selectedProjectIds = [...selectedProjectIds, id];
		}
		// Clear activity selection when project selection changes (activities list changes)
		selectedActivityIds = [];
		// If nothing is selected, clear the focus entirely
		if (selectedProjectIds.length === 0) {
			deactivateFocus();
		}
	}

	function toggleActivity(id: number) {
		if (selectedActivityIds.includes(id)) {
			selectedActivityIds = selectedActivityIds.filter(x => x !== id);
		} else {
			selectedActivityIds = [...selectedActivityIds, id];
		}
		// If nothing is selected, clear the focus entirely
		if (selectedProjectIds.length === 0 && selectedActivityIds.length === 0) {
			deactivateFocus();
		}
	}

	async function handleLetsBegin() {
		// Activate any selected inactive projects/activities
		const inactiveProjects = projectsData.filter(p => selectedProjectIds.includes(p.id) && !p.is_active);
		const inactiveActivities = activitiesData.filter(a => selectedActivityIds.includes(a.id) && !a.is_active);

		await Promise.allSettled([
			...inactiveProjects.map(p => activateProject(p.id)),
			...inactiveActivities.map(a => activateActivity(a.id)),
		]);

		// Reload stores so Input panels see updated is_active state
		if (inactiveProjects.length > 0) await loadProjects();
		if (inactiveActivities.length > 0) await loadActivities();

		await activateFocus(
			{ projectIds: selectedProjectIds, activityIds: selectedActivityIds },
			tagsData,
			projectsData,
			activitiesData
		);
	}

	// Fetch project-category tags (Personal, Work, etc.) for each project
	async function loadProjectTagMap(projectList: Project[]) {
		const map: Record<number, Tag[]> = {};
		await Promise.all(
			projectList.filter(p => !p.is_archived).map(async (project) => {
				try {
					const pTags = await getEntityTags('project', project.id);
					// Keep only project-category tags (not entity-linked tags from other entities)
					map[project.id] = pTags.filter(t => t.category === 'project' && t.entity_id === null);
				} catch {
					map[project.id] = [];
				}
			})
		);
		projectTagMap = map;
	}

	// Fetch activity-project tag mappings
	async function loadActivityProjectMap(activityList: Activity[]) {
		const map: Record<number, number[]> = {};
		await Promise.all(
			activityList.filter(a => !a.is_archived).map(async (activity) => {
				try {
					const actTags = await getEntityTags('activity', activity.id);
					const projIds = actTags
						.filter(t => t.entity_type === 'project' && t.entity_id != null)
						.map(t => t.entity_id as number);
					map[activity.id] = projIds;
				} catch {
					map[activity.id] = [];
				}
			})
		);
		activityProjectMap = map;
	}

	onMount(() => {
		// Pick fact on client to ensure consistency
		factIndex = Math.floor(Math.random() * FACTS.length);

		// Subscribe to stores only on client
		const unsubs = [
			projects.subscribe(v => {
				projectsData = v ?? [];
				if (v && v.length > 0) {
					loadProjectTagMap(v);
				}
			}),
			activities.subscribe(v => {
				activitiesData = v ?? [];
				// Reload activity-project map when activities change
				if (v && v.length > 0) {
					loadActivityProjectMap(v);
				}
			}),
			notes.subscribe(v => notesData = v ?? []),
			logs.subscribe(v => logsData = v ?? []),
			sources.subscribe(v => sourcesData = v ?? []),
			actors.subscribe(v => actorsData = v ?? []),
			readingLists.subscribe(v => readingListsData = v ?? []),
			tags.subscribe(v => tagsData = v ?? []),
			focusSelection.subscribe(v => {
				// Sync local selection with store
				if (isFocusActive(v)) {
					selectedProjectIds = v.projectIds;
					selectedActivityIds = v.activityIds;
				} else {
					selectedProjectIds = [];
					selectedActivityIds = [];
				}
			}),
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
			<!-- Stats Overview -->
			<section class="card stats-card">
				<h2>Overview</h2>
				<div class="stats-grid">
					<div class="stat">
						<span class="stat-value">{projectsData.filter(p => p.is_active).length}</span>
						<span class="stat-label">Active Projects</span>
					</div>
					<div class="stat">
						<span class="stat-value">{activitiesData.filter(a => a.is_active).length}</span>
						<span class="stat-label">Active Activities</span>
					</div>
					<div class="stat">
						<span class="stat-value">{notesData.length}</span>
						<span class="stat-label">Notes</span>
					</div>
					<div class="stat">
						<span class="stat-value">{logsData.length}</span>
						<span class="stat-label">Logs</span>
					</div>
				</div>
				<div class="stats-secondary">
					<span>{projectsData.length} projects</span>
					<span>{sourcesData.length} sources</span>
					<span>{actorsData.length} actors</span>
					<span>{readingListsData.length} reading</span>
				</div>
			</section>

			<!-- Focus Launcher -->
			<section class="card focus-card">
				<div class="focus-header">
					<h2>What would you like to work on today?</h2>
					{#if hasSelection}
						<button class="lets-begin-btn" onclick={handleLetsBegin}>
							Let's Begin
						</button>
					{/if}
				</div>
				{#if focusProjects.length === 0 && allFocusActivities.length === 0}
					<p class="empty-msg">No projects or activities. Start something new!</p>
				{:else}
					<div class="focus-content">
						<div class="focus-group">
							<div class="focus-group-header">
								<h3>Projects</h3>
								<div class="project-filters">
									<button
										class="filter-chip"
										class:active={projectFilter === null}
										onclick={() => (projectFilter = null)}
									>All</button>
									{#each projectFilterOptions as opt}
										<button
											class="filter-chip"
											class:active={projectFilter === opt}
											onclick={() => (projectFilter = projectFilter === opt ? null : opt)}
										>{opt}</button>
									{/each}
								</div>
							</div>
							{#if filteredFocusProjects.length > 0}
								<div class="focus-cards-scroll">
									<div class="focus-cards">
										{#each filteredFocusProjects as project (project.id)}
											<button
												class="focus-card-item project"
												class:selected={selectedProjectIds.includes(project.id)}
												onclick={() => toggleProject(project.id)}
											>
												<span class="focus-card-title">{project.title}</span>
												{#if projectTagMap[project.id]?.length}
													{#each projectTagMap[project.id] as tag (tag.id)}
														<span class="project-tag">{tag.name}</span>
													{/each}
												{/if}
											</button>
										{/each}
									</div>
								</div>
							{:else}
								<p class="empty-msg">{projectFilter ? `No ${projectFilter} projects` : 'No projects yet'}</p>
							{/if}
						</div>
						<div class="focus-group">
							<h3>Activities {#if selectedProjectIds.length > 0}<span class="filter-hint">(filtered by project)</span>{/if}</h3>
							{#if visibleActivities.length > 0}
								<div class="focus-cards-scroll">
									<div class="focus-cards">
										{#each visibleActivities as activity (activity.id)}
											<button
												class="focus-card-item activity"
												class:selected={selectedActivityIds.includes(activity.id)}
												onclick={() => toggleActivity(activity.id)}
											>
												<span class="focus-card-title">{activity.title}</span>
											</button>
										{/each}
									</div>
								</div>
							{:else}
								<p class="empty-msg">{selectedProjectIds.length > 0 ? 'No activities for selected project' : 'No unlinked activities'}</p>
							{/if}
						</div>
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

			<!-- Reading -->
			<section class="card inspire-card">
				<h2>Things to Explore</h2>
				<div class="inspire-content">
					{#if readingListsData.filter(r => r.status !== 'completed').length > 0}
						<div class="inspire-group">
							<h3>Reading</h3>
							{#each readingListsData.filter(r => r.status !== 'completed').slice(0, 3) as item}
								<div class="inspire-item">
									<span class="inspire-icon">R</span>
									<span class="inspire-title">{item.title}</span>
								</div>
							{/each}
						</div>
					{/if}
					{#if readingListsData.filter(r => r.status !== 'completed').length === 0}
						<p class="empty-msg">Add items to your reading list!</p>
					{/if}
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

	/* Focus Card */
	.focus-card {
		grid-column: span 2;
	}
	.focus-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 0;
	}
	.focus-header h2 {
		margin-bottom: 0;
		text-transform: none;
		font-size: 0.95rem;
		color: #374151;
		letter-spacing: 0;
	}
	.lets-begin-btn {
		padding: 6px 16px;
		border: none;
		border-radius: 6px;
		background: #3b82f6;
		color: white;
		font-size: 0.8rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.15s;
	}
	.lets-begin-btn:hover {
		background: #2563eb;
	}
	.focus-content {
		display: flex;
		gap: 24px;
		margin-top: 12px;
	}
	.focus-group {
		flex: 1;
		min-width: 0;
	}
	.focus-group-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 8px;
	}
	.focus-group-header h3 {
		margin: 0;
	}
	.focus-group h3 {
		font-size: 0.7rem;
		color: #9ca3af;
		margin: 0 0 8px;
		font-weight: 500;
	}
	.project-filters {
		display: flex;
		gap: 4px;
	}
	.filter-chip {
		padding: 2px 8px;
		border: 1px solid #e5e7eb;
		border-radius: 10px;
		background: white;
		cursor: pointer;
		font-size: 0.65rem;
		color: #9ca3af;
		transition: all 0.15s;
	}
	.filter-chip:hover {
		background: #f3f4f6;
		color: #6b7280;
	}
	.filter-chip.active {
		background: #374151;
		color: white;
		border-color: #374151;
	}
	.filter-hint {
		font-style: italic;
		color: #d1d5db;
	}
	.focus-cards-scroll {
		max-height: calc(100vh - 350px);
		overflow-y: auto;
	}
	.focus-cards {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.focus-card-item {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 8px 12px;
		border: 1px solid #e5e7eb;
		border-radius: 8px;
		background: white;
		cursor: pointer;
		transition: all 0.15s;
		text-align: left;
		width: 100%;
	}
	.focus-card-item:hover {
		background: #f9fafb;
	}
	.focus-card-item.project {
		border-left: 3px solid #5c7a99;
	}
	.focus-card-item.activity {
		border-left: 3px solid #8b7355;
	}
	.focus-card-item.selected {
		background: #eff6ff;
		border-color: #3b82f6;
		box-shadow: 0 0 0 1px #3b82f6;
	}
	.focus-card-item.selected.project {
		border-left-color: #3b82f6;
	}
	.focus-card-item.selected.activity {
		border-left-color: #3b82f6;
	}
	.focus-card-title {
		font-size: 0.85rem;
		color: #374151;
		flex: 1;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.project-tag {
		font-size: 0.6rem;
		padding: 2px 7px;
		border-radius: 8px;
		font-weight: 500;
		flex-shrink: 0;
		background: #f0f4f8;
		color: #5c7a99;
		border: 1px solid #dbe4ee;
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

	/* Inspire Card */
	.inspire-card {
		grid-column: span 3;
	}
	.inspire-content {
		display: flex;
		gap: 32px;
	}
	.inspire-group {
		flex: 1;
	}
	.inspire-group h3 {
		font-size: 0.7rem;
		color: #9ca3af;
		margin: 0 0 8px;
		font-weight: 500;
	}
	.inspire-item {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 6px 0;
	}
	.inspire-icon {
		width: 20px;
		height: 20px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: #e5e7eb;
		border-radius: 4px;
		font-size: 0.65rem;
		font-weight: 600;
		color: #6b7280;
	}
	.inspire-title {
		font-size: 0.85rem;
		color: #374151;
	}

	@media (max-width: 800px) {
		.dashboard-grid {
			grid-template-columns: 1fr;
		}
		.stats-card, .inspire-card, .history-card {
			grid-column: span 1;
		}
		.focus-card {
			grid-column: span 1;
		}
		.stats-grid {
			flex-wrap: wrap;
		}
		.inspire-content, .focus-content {
			flex-direction: column;
			gap: 16px;
		}
	}
</style>

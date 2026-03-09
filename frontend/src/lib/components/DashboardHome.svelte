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
	import { collections } from '$lib/stores/collections';
	import { createWorkspace } from '$lib/api/workspaces';
	import { activeTab } from '$lib/stores/activeTab';
	import { tags } from '$lib/stores/tags';
	import { getTagUsageCounts, getAllEntityTagsBulk } from '$lib/api/tags';
	import { searchEntities, type SearchResult } from '$lib/api/search';
	import { selectedFilterTags, resetToAll } from '$lib/stores/dateFilter';
	import { graphInitialSelection } from '$lib/stores/graphInitialSelection';
	import { workspaceInjectedResults } from '$lib/stores/workspaceQueryInjection';
	import type { Note, Project, Activity, Source, Actor, Log, Plan, Workspace, Tag, Collection } from '$lib/types';

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

	// Workspaces & collections state
	let workspacesData = $state<Workspace[]>([]);
	let collectionsData = $state<Collection[]>([]);
	let newWsName = $state('');

	// Tags state
	let tagsData = $state<Tag[]>([]);
	let tagUsageCounts = $state<Record<number, number>>({});
	// Bulk entity tags: { "entity_type:entity_id": Tag[] }
	let entityTagsBulk = $state<Record<string, { id: number }[]>>({});

	// Multi-select topics (array for reliable Svelte 5 reactivity)
	let selectedTopicIds = $state<number[]>([]);
	// Stats popup (double click)
	let popupTopicId = $state<number | null>(null);
	let popupX = $state(0);
	let popupY = $state(0);

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

	// ── Todo Activities & Resources to Read ──
	// IDs of entities marked done in any collection (overrides their own status)
	let doneInCollection = $derived.by(() => {
		const done = new Set<string>();
		for (const col of collectionsData) {
			for (const item of col.items) {
				if (item.status === 'done') {
					done.add(`${item.member_entity_type}:${item.member_entity_id}`);
				}
			}
		}
		return done;
	});

	let todoActivities = $derived(
		activitiesData
			.filter(a =>
				(a.status === 'todo' || a.status === 'in_progress') &&
				!a.is_archived &&
				!doneInCollection.has(`activity:${a.id}`)
			)
			.sort((a, b) => {
				if (a.status === 'in_progress' && b.status !== 'in_progress') return -1;
				if (b.status === 'in_progress' && a.status !== 'in_progress') return 1;
				return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
			})
			.slice(0, 8)
	);

	let toReadSources = $derived(
		sourcesData
			.filter(s =>
				(s.status === 'to_read' || s.status === 'reading') &&
				!s.is_archived &&
				!doneInCollection.has(`source:${s.id}`)
			)
			.sort((a, b) => {
				if (a.status === 'reading' && b.status !== 'reading') return -1;
				if (b.status === 'reading' && a.status !== 'reading') return 1;
				return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
			})
			.slice(0, 6)
	);

	// ── Topics cloud plot from general (wild) tags ──
	interface PlacedTopic {
		tag: Tag;
		count: number;
		fontSize: number;
		x: number;
		y: number;
		w: number;
		h: number;
		color: string;
		textColor: string;
	}

	const CLOUD_W = 960;
	const CLOUD_H = 220;

	const TOPIC_COLORS = [
		'#dbeafe', '#fce7f3', '#d1fae5', '#fef3c7', '#ede9fe',
		'#ffedd5', '#e0e7ff', '#cffafe', '#fecdd3', '#d9f99d',
		'#f5d0fe', '#ccfbf1'
	];
	const TOPIC_TEXT_COLORS = [
		'#1e40af', '#9d174d', '#065f46', '#92400e', '#5b21b6',
		'#9a3412', '#3730a3', '#155e75', '#9f1239', '#3f6212',
		'#86198f', '#115e59'
	];

	let placedTopics = $derived.by((): PlacedTopic[] => {
		const generalTags = tagsData.filter(t => t.entity_id === null || t.entity_id === undefined);
		if (generalTags.length === 0) return [];

		const ranked = generalTags
			.map(t => ({ tag: t, count: tagUsageCounts[t.id] ?? 0 }))
			.filter(b => b.count > 0)
			.sort((a, b) => b.count - a.count)
			.slice(0, 30);

		if (ranked.length === 0) return [];

		const maxC = Math.max(...ranked.map(b => b.count));
		const minC = Math.min(...ranked.map(b => b.count));
		const range = maxC - minC || 1;

		// Assign font sizes (12–28px based on count)
		const items = ranked.map((b, i) => {
			const t = (b.count - minC) / range;
			const fontSize = 12 + t * 16;
			// Rough text width estimate: chars * fontSize * 0.6
			const w = b.tag.name.length * fontSize * 0.6 + 20;
			const h = fontSize + 12;
			return {
				tag: b.tag,
				count: b.count,
				fontSize,
				w,
				h,
				x: 0,
				y: 0,
				color: TOPIC_COLORS[i % TOPIC_COLORS.length],
				textColor: TOPIC_TEXT_COLORS[i % TOPIC_TEXT_COLORS.length],
			};
		});

		// Place using Archimedean spiral from center
		const cx = CLOUD_W / 2;
		const cy = CLOUD_H / 2;
		const placed: PlacedTopic[] = [];

		function overlaps(x: number, y: number, w: number, h: number): boolean {
			for (const p of placed) {
				if (
					x < p.x + p.w + 4 &&
					x + w + 4 > p.x &&
					y < p.y + p.h + 2 &&
					y + h + 2 > p.y
				) return true;
			}
			return false;
		}

		for (const item of items) {
			let found = false;
			for (let step = 0; step < 600; step++) {
				const angle = step * 0.15;
				const radius = 3 + step * 0.8;
				const tx = cx + radius * Math.cos(angle) - item.w / 2;
				const ty = cy + radius * Math.sin(angle) - item.h / 2;

				if (tx < 0 || ty < 0 || tx + item.w > CLOUD_W || ty + item.h > CLOUD_H) continue;
				if (!overlaps(tx, ty, item.w, item.h)) {
					item.x = tx;
					item.y = ty;
					placed.push(item);
					found = true;
					break;
				}
			}
			if (!found) {
				// Skip items that don't fit
			}
		}

		return placed;
	});

	// ── Selected topic breakdown ──
	interface TopicBreakdown {
		tag: Tag;
		totalCount: number;
		byType: { type: string; label: string; count: number; color: string }[];
	}

	const ENTITY_TYPE_META: Record<string, { label: string; color: string }> = {
		project: { label: 'Projects', color: '#5c7a99' },
		activity: { label: 'Activities', color: '#8b7355' },
		note: { label: 'Notes', color: '#e6b800' },
		log: { label: 'Logs', color: '#6366f1' },
		source: { label: 'Sources', color: '#059669' },
		actor: { label: 'Actors', color: '#8b5cf6' },
		plan: { label: 'Plans', color: '#ec4899' },
	};

	let popupTopicBreakdown = $derived.by((): TopicBreakdown | null => {
		if (popupTopicId === null) return null;

		const tag = tagsData.find(t => t.id === popupTopicId);
		if (!tag) return null;

		const counts: Record<string, number> = {};
		for (const [key, tagList] of Object.entries(entityTagsBulk)) {
			if (tagList.some(t => t.id === popupTopicId)) {
				const entityType = key.split(':')[0];
				counts[entityType] = (counts[entityType] ?? 0) + 1;
			}
		}

		const byType = Object.entries(counts)
			.map(([type, count]) => ({
				type,
				label: ENTITY_TYPE_META[type]?.label ?? type,
				count,
				color: ENTITY_TYPE_META[type]?.color ?? '#9ca3af',
			}))
			.sort((a, b) => b.count - a.count);

		const totalCount = byType.reduce((s, b) => s + b.count, 0);

		return { tag, totalCount, byType };
	});

	// Selected topic Tag objects (for navigation actions)
	let selectedTopicTags = $derived(
		tagsData.filter(t => selectedTopicIds.includes(t.id))
	);

	function handleTopicClick(tagId: number) {
		const idx = selectedTopicIds.indexOf(tagId);
		if (idx >= 0) {
			selectedTopicIds = selectedTopicIds.filter(id => id !== tagId);
			if (popupTopicId === tagId) popupTopicId = null;
		} else {
			selectedTopicIds = [...selectedTopicIds, tagId];
		}
	}

	function handleTopicDblClick(e: MouseEvent, tagId: number) {
		// Ensure it's selected
		if (!selectedTopicIds.includes(tagId)) {
			selectedTopicIds = [...selectedTopicIds, tagId];
		}
		// Position popup
		const card = (e.currentTarget as SVGElement).closest('.topics-card') as HTMLElement;
		if (card) {
			const rect = card.getBoundingClientRect();
			popupX = e.clientX - rect.left;
			popupY = e.clientY - rect.top;
		}
		popupTopicId = popupTopicId === tagId ? null : tagId;
	}

	function clearTopicSelection() {
		selectedTopicIds = [];
		popupTopicId = null;
	}

	// ── Navigation actions for selected topics ──
	function openInCards() {
		selectedFilterTags.set(selectedTopicTags);
		resetToAll();
		activeTab.set('input');
		clearTopicSelection();
	}

	function openInNotepad() {
		activeTab.set('notepad');
		clearTopicSelection();
	}

	function openInGraph() {
		selectedFilterTags.set(selectedTopicTags);
		resetToAll();
		// Load tagged entities onto the graph
		const tagIds = [...selectedTopicIds];
		const entityKeys: { type: string; id: number }[] = [];
		for (const [key, tagList] of Object.entries(entityTagsBulk)) {
			if (tagList.some(t => tagIds.includes(t.id))) {
				const [type, idStr] = key.split(':');
				entityKeys.push({ type, id: Number(idStr) });
			}
		}
		graphInitialSelection.set({
			entities: entityKeys,
			pulsingKeys: entityKeys.map(e => `${e.type}:${e.id}`),
			showRelated: true,
		});
		activeTab.set('graph');
		clearTopicSelection();
	}

	async function openInWorkspace() {
		const tagIds = [...selectedTopicIds];
		const tagNames = selectedTopicTags.map(t => t.name).join(', ');
		try {
			const results = await searchEntities({ tag_ids: tagIds, tag_mode: 'or', limit: 200 });
			workspaceInjectedResults.set({
				results,
				label: `Tagged: ${tagNames}`,
			});
		} catch {
			workspaceInjectedResults.set(null);
		}
		activeTab.set('workspace');
		clearTopicSelection();
	}

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
			collections.subscribe(v => collectionsData = v ?? []),
			tags.subscribe(v => tagsData = v ?? []),
		];

		// Load tag usage counts and bulk entity tags
		(async () => {
			try {
				const [counts, bulk] = await Promise.all([getTagUsageCounts(), getAllEntityTagsBulk()]);
				tagUsageCounts = counts;
				entityTagsBulk = bulk;
			} catch (e) {
				console.warn('Failed to load tag data:', e);
			}
		})();

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

			<!-- Topics Cloud Plot -->
			<section class="card topics-card">
				<div class="topics-header">
					<h2>Topics</h2>
					{#if selectedTopicIds.length > 0}
						<div class="topic-actions">
							<span class="topic-actions-count">{selectedTopicIds.length} selected</span>
							<button class="topic-action-btn" title="Open in Cards" onclick={openInCards}>Cards</button>
							<button class="topic-action-btn" title="Open in Notepad" onclick={openInNotepad}>Notepad</button>
							<button class="topic-action-btn" title="Open in Graph" onclick={openInGraph}>Graph</button>
							<button class="topic-action-btn" title="Query in Workspace" onclick={openInWorkspace}>Workspace</button>
							<button class="topic-action-clear" title="Clear selection" onclick={clearTopicSelection}>&times;</button>
						</div>
					{/if}
				</div>
				{#if placedTopics.length === 0}
					<p class="empty-msg">Tag your entities to see topics emerge here.</p>
				{:else}
					<div class="topics-cloud-wrap">
						<svg viewBox="0 0 {CLOUD_W} {CLOUD_H}" class="topics-svg">
							{#each placedTopics as t, i}
								<!-- svelte-ignore a11y_click_events_have_key_events -->
								<g
									class="cloud-word"
									class:selected={selectedTopicIds.includes(t.tag.id)}
									onclick={() => handleTopicClick(t.tag.id)}
									ondblclick={(e) => handleTopicDblClick(e, t.tag.id)}
									role="button"
									tabindex="0"
								>
									<rect
										x={t.x}
										y={t.y}
										width={t.w}
										height={t.h}
										rx="12"
										fill={t.color}
										opacity={selectedTopicIds.length === 0 || selectedTopicIds.includes(t.tag.id) ? 0.7 : 0.3}
									/>
									<text
										x={t.x + t.w / 2}
										y={t.y + t.h / 2}
										text-anchor="middle"
										dominant-baseline="central"
										font-size={t.fontSize}
										font-weight={selectedTopicIds.includes(t.tag.id) ? '700' : '500'}
										fill={t.textColor}
										opacity={selectedTopicIds.length === 0 || selectedTopicIds.includes(t.tag.id) ? 1 : 0.4}
									>{t.tag.name}</text>
								</g>
							{/each}
						</svg>
					</div>

					{#if popupTopicBreakdown}
						<!-- svelte-ignore a11y_click_events_have_key_events -->
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<div class="topic-popup-backdrop" onclick={() => popupTopicId = null}></div>
						<div class="topic-popup" style="left: {popupX}px; top: {popupY}px;">
							<div class="topic-popup-header">
								<h3 class="topic-popup-name">{popupTopicBreakdown.tag.name}</h3>
								<span class="topic-popup-total">{popupTopicBreakdown.totalCount} {popupTopicBreakdown.totalCount === 1 ? 'entity' : 'entities'}</span>
								<button class="topic-popup-close" onclick={() => popupTopicId = null}>&times;</button>
							</div>
							{#if popupTopicBreakdown.byType.length > 0}
								<div class="topic-popup-bars">
									{#each popupTopicBreakdown.byType as entry}
										<div class="topic-bar-row">
											<span class="topic-bar-label">{entry.label}</span>
											<div class="topic-bar-track">
												<div
													class="topic-bar-fill"
													style="width: {(entry.count / popupTopicBreakdown.totalCount) * 100}%; background: {entry.color};"
												></div>
											</div>
											<span class="topic-bar-count">{entry.count}</span>
										</div>
									{/each}
								</div>
							{/if}
						</div>
					{/if}
				{/if}
			</section>

			<!-- To Do & Reading List -->
			<section class="card todo-card">
				<h2>Up Next</h2>
				{#if todoActivities.length === 0 && toReadSources.length === 0}
					<p class="empty-msg">All caught up! No pending activities or readings.</p>
				{:else}
					<div class="todo-sections">
						{#if todoActivities.length > 0}
							<div class="todo-section">
								<h3 class="todo-section-title">Activities</h3>
								<div class="todo-list">
									{#each todoActivities as activity}
										<div class="todo-item">
											<span class="todo-check" class:in-progress={activity.status === 'in_progress'}>{activity.status === 'in_progress' ? '...' : ' '}</span>
											<span class="todo-title">{activity.title}</span>
											<span class="todo-status" class:status-in-progress={activity.status === 'in_progress'}>{activity.status.replace('_', ' ')}</span>
										</div>
									{/each}
								</div>
							</div>
						{/if}
						{#if toReadSources.length > 0}
							<div class="todo-section">
								<h3 class="todo-section-title">Reading List</h3>
								<div class="todo-list">
									{#each toReadSources as source}
										<div class="todo-item">
											<span class="todo-check reading" class:in-progress={source.status === 'reading'}>{source.status === 'reading' ? '...' : ' '}</span>
											<div class="todo-source-info">
												<span class="todo-title">{source.title}</span>
												{#if source.author}
													<span class="todo-author">by {source.author}</span>
												{/if}
											</div>
											<span class="todo-status" class:status-reading={source.status === 'reading'}>{source.status.replace('_', ' ')}</span>
										</div>
									{/each}
								</div>
							</div>
						{/if}
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

	/* To Do Card */
	.todo-card {
		grid-column: span 2;
	}
	.todo-sections {
		display: flex;
		flex-direction: column;
		gap: 14px;
	}
	.todo-section-title {
		font-size: 0.7rem;
		font-weight: 600;
		color: #6b7280;
		margin: 0 0 6px;
		text-transform: uppercase;
		letter-spacing: 0.3px;
	}
	.todo-list {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.todo-item {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 7px 10px;
		border-radius: 6px;
		transition: background 0.12s;
	}
	.todo-item:hover {
		background: #f9fafb;
	}
	.todo-check {
		width: 18px;
		height: 18px;
		border: 1.5px solid #d1d5db;
		border-radius: 4px;
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.55rem;
		color: #9ca3af;
		background: white;
	}
	.todo-check.in-progress {
		border-color: #3b82f6;
		color: #3b82f6;
		background: #eff6ff;
	}
	.todo-check.reading.in-progress {
		border-color: #059669;
		color: #059669;
		background: #ecfdf5;
	}
	.todo-title {
		flex: 1;
		min-width: 0;
		font-size: 0.82rem;
		color: #374151;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.todo-source-info {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 1px;
	}
	.todo-author {
		font-size: 0.68rem;
		color: #9ca3af;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.todo-status {
		font-size: 0.6rem;
		font-weight: 500;
		color: #9ca3af;
		background: #f3f4f6;
		padding: 2px 8px;
		border-radius: 8px;
		flex-shrink: 0;
		text-transform: capitalize;
	}
	.todo-status.status-in-progress {
		color: #2563eb;
		background: #eff6ff;
	}
	.todo-status.status-reading {
		color: #059669;
		background: #ecfdf5;
	}

	/* Topics Cloud Plot */
	.topics-card {
		grid-column: span 3;
		position: relative;
	}
	.topics-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		flex-wrap: wrap;
		gap: 8px;
	}
	.topics-header h2 {
		margin-bottom: 0;
	}
	.topic-actions {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.topic-actions-count {
		font-size: 0.68rem;
		color: #6b7280;
		margin-right: 2px;
	}
	.topic-action-btn {
		border: 1px solid #d1d5db;
		background: white;
		border-radius: 6px;
		padding: 4px 10px;
		font-size: 0.7rem;
		font-weight: 500;
		color: #374151;
		cursor: pointer;
		transition: all 0.12s;
	}
	.topic-action-btn:hover {
		background: #374151;
		color: white;
		border-color: #374151;
	}
	.topic-action-clear {
		border: none;
		background: none;
		font-size: 1rem;
		color: #9ca3af;
		cursor: pointer;
		padding: 0 4px;
		line-height: 1;
	}
	.topic-action-clear:hover {
		color: #374151;
	}
	.topics-cloud-wrap {
		width: 100%;
		overflow: hidden;
	}
	.topics-svg {
		width: 100%;
		height: auto;
		display: block;
	}
	.cloud-word {
		cursor: pointer;
		transition: opacity 0.15s;
	}
	.cloud-word:hover rect {
		opacity: 1 !important;
	}
	.cloud-word:hover text {
		font-weight: 700;
	}
	.cloud-word.selected rect {
		opacity: 0.95 !important;
		filter: brightness(0.92);
	}

	/* Topic Popup */
	.topic-popup-backdrop {
		position: fixed;
		inset: 0;
		z-index: 99;
	}
	.topic-popup {
		position: absolute;
		z-index: 100;
		width: 260px;
		padding: 14px 16px;
		background: white;
		border-radius: 10px;
		border: 1px solid #e5e7eb;
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12), 0 2px 6px rgba(0, 0, 0, 0.06);
		transform: translate(-50%, 8px);
		animation: popup-in 0.15s ease-out;
	}
	@keyframes popup-in {
		from { opacity: 0; transform: translate(-50%, 0); }
		to { opacity: 1; transform: translate(-50%, 8px); }
	}
	.topic-popup-header {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 10px;
	}
	.topic-popup-name {
		font-size: 0.92rem;
		font-weight: 600;
		color: #111827;
		margin: 0;
	}
	.topic-popup-total {
		font-size: 0.65rem;
		color: #6b7280;
		background: #f3f4f6;
		padding: 2px 7px;
		border-radius: 8px;
	}
	.topic-popup-close {
		margin-left: auto;
		border: none;
		background: none;
		font-size: 1.1rem;
		color: #9ca3af;
		cursor: pointer;
		padding: 0 2px;
		line-height: 1;
	}
	.topic-popup-close:hover {
		color: #374151;
	}
	.topic-popup-bars {
		display: flex;
		flex-direction: column;
		gap: 5px;
	}
	.topic-bar-row {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.topic-bar-label {
		font-size: 0.7rem;
		color: #374151;
		width: 64px;
		flex-shrink: 0;
		text-align: right;
	}
	.topic-bar-track {
		flex: 1;
		height: 12px;
		background: #f3f4f6;
		border-radius: 6px;
		overflow: hidden;
	}
	.topic-bar-fill {
		height: 100%;
		border-radius: 6px;
		transition: width 0.3s ease;
		min-width: 4px;
	}
	.topic-bar-count {
		font-size: 0.7rem;
		font-weight: 600;
		color: #374151;
		width: 20px;
		text-align: right;
		flex-shrink: 0;
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
		.stats-card, .history-card, .workspaces-card, .topics-card {
			grid-column: span 1;
		}
		.todo-card {
			grid-column: span 1;
		}
		.stats-grid {
			flex-wrap: wrap;
		}
	}
</style>

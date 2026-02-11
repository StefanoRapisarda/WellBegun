import { writable, derived, get } from 'svelte/store';
import type { Tag } from '$lib/types';
import type { DocumentTab, SessionCard, ReadingSessionState } from '$lib/components/reader/types';
import { createActivity, activateActivity } from '$lib/api/activities';
import { createSource } from '$lib/api/sources';
import { attachTag } from '$lib/api/tags';
import { loadActivities } from '$lib/stores/activities';
import { loadSources } from '$lib/stores/sources';
import { tags, loadTags } from '$lib/stores/tags';

const initialState: ReadingSessionState = {
	tabs: [],
	activeTabId: null,
	cards: []
};

export const readingSession = writable<ReadingSessionState>({ ...initialState });

export const activeTab = derived(readingSession, ($s) =>
	$s.tabs.find((t) => t.id === $s.activeTabId) ?? null
);

// ── Tab management ──

export function addTab(type: 'pdf' | 'website'): string {
	const id = crypto.randomUUID();
	const tab: DocumentTab = {
		id,
		type,
		title: type === 'pdf' ? 'New PDF' : 'New Website',
		scale: 1.5,
		currentPage: 1,
		totalPages: 0
	};
	readingSession.update((s) => ({
		...s,
		tabs: [...s.tabs, tab],
		activeTabId: id
	}));
	return id;
}

export function removeTab(tabId: string) {
	const state = get(readingSession);
	const tab = state.tabs.find((t) => t.id === tabId);
	if (tab?.pdfUrl) {
		URL.revokeObjectURL(tab.pdfUrl);
	}

	const remaining = state.tabs.filter((t) => t.id !== tabId);
	let newActiveId = state.activeTabId;
	if (state.activeTabId === tabId) {
		const idx = state.tabs.findIndex((t) => t.id === tabId);
		newActiveId = remaining[Math.min(idx, remaining.length - 1)]?.id ?? null;
	}

	readingSession.update((s) => ({
		...s,
		tabs: remaining,
		activeTabId: newActiveId
	}));
}

export function setActiveTab(tabId: string) {
	readingSession.update((s) => ({ ...s, activeTabId: tabId }));
}

// ── PDF loading ──

export async function loadPdfToTab(tabId: string, file: File) {
	const url = URL.createObjectURL(file);
	const title = file.name.replace(/\.pdf$/i, '');

	readingSession.update((s) => ({
		...s,
		tabs: s.tabs.map((t) =>
			t.id === tabId ? { ...t, pdfFile: file, pdfUrl: url, title } : t
		)
	}));

	await initTabActivity(tabId, title, 'pdf');
}

// ── Website loading ──

export async function loadWebsiteToTab(tabId: string, url: string) {
	let title: string;
	try {
		const hostname = new URL(url).hostname;
		title = hostname.replace(/^www\./, '');
	} catch {
		title = url.slice(0, 40);
	}

	readingSession.update((s) => ({
		...s,
		tabs: s.tabs.map((t) =>
			t.id === tabId ? { ...t, websiteUrl: url, title } : t
		)
	}));

	await initTabActivity(tabId, title, 'website');
}

// ── Init activity + source for a tab ──

async function initTabActivity(tabId: string, title: string, sourceType: string) {
	try {
		const activity = await createActivity({
			title: `Reading ${title}`,
			description: `Reading session for "${title}"`
		});
		await activateActivity(activity.id);

		const source = await createSource({
			title,
			source_type: sourceType
		});

		// Reload tags so we can find the activity's own entity tag
		await Promise.all([loadActivities(), loadSources(), loadTags()]);

		// The activity's entity tag is a Tag where entity_type='activity' and entity_id=activity.id
		const allTags = get(tags);
		const entityTag =
			allTags.find(
				(t: Tag) => t.entity_type === 'activity' && t.entity_id === activity.id
			) ?? null;

		if (entityTag) {
			await attachTag(entityTag.id, 'source', source.id);
			await loadTags();
		}

		readingSession.update((s) => ({
			...s,
			tabs: s.tabs.map((t) =>
				t.id === tabId
					? { ...t, activityId: activity.id, activityTag: entityTag, sourceId: source.id }
					: t
			)
		}));
	} catch (err) {
		console.error('Failed to init tab activity:', err);
	}
}

// ── Tab PDF state updates ──

export function updateTabPdfState(tabId: string, patch: Partial<Pick<DocumentTab, 'currentPage' | 'totalPages' | 'scale'>>) {
	readingSession.update((s) => ({
		...s,
		tabs: s.tabs.map((t) =>
			t.id === tabId ? { ...t, ...patch } : t
		)
	}));
}

// ── Card management ──

export function addCard(card: Omit<SessionCard, 'id'>) {
	const newCard: SessionCard = {
		id: crypto.randomUUID(),
		entityType: card.entityType,
		entityId: card.entityId,
		title: card.title,
		x: card.x,
		y: card.y,
		fromTabId: card.fromTabId
	};
	readingSession.update((s) => ({
		...s,
		cards: [...s.cards, newCard]
	}));
	return newCard;
}

export function removeCard(cardId: string) {
	readingSession.update((s) => ({
		...s,
		cards: s.cards.filter((c) => c.id !== cardId)
	}));
}

export function moveCard(cardId: string, x: number, y: number) {
	readingSession.update((s) => ({
		...s,
		cards: s.cards.map((c) =>
			c.id === cardId ? { ...c, x, y } : c
		)
	}));
}

// ── Session management ──

export function closeSession() {
	const state = get(readingSession);
	for (const tab of state.tabs) {
		if (tab.pdfUrl) {
			URL.revokeObjectURL(tab.pdfUrl);
		}
	}
	readingSession.set({ ...initialState });
}

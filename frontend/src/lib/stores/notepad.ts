import { writable } from 'svelte/store';

const STORAGE_KEY = 'notepad-text';

function loadFromStorage(): string {
	if (typeof window === 'undefined') return '';
	return localStorage.getItem(STORAGE_KEY) ?? '';
}

export const notepadText = writable<string>(loadFromStorage());

notepadText.subscribe((value) => {
	if (typeof window !== 'undefined') {
		localStorage.setItem(STORAGE_KEY, value);
	}
});

// ── Persisted card layout store ──

export interface CardLayout {
	positions: Record<number, { x: number; y: number }>;
	sizes: Record<number, { colSpan: number; rowSpan: number }>;
}

const LAYOUT_KEY = 'notepad-card-layout';

function loadLayout(): CardLayout {
	if (typeof window === 'undefined') return { positions: {}, sizes: {} };
	try {
		const raw = localStorage.getItem(LAYOUT_KEY);
		return raw ? JSON.parse(raw) : { positions: {}, sizes: {} };
	} catch {
		return { positions: {}, sizes: {} };
	}
}

export const cardLayout = writable<CardLayout>(loadLayout());

cardLayout.subscribe((v) => {
	if (typeof window !== 'undefined') {
		localStorage.setItem(LAYOUT_KEY, JSON.stringify(v));
	}
});

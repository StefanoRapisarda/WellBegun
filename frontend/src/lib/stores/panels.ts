import { writable, get } from 'svelte/store';

export interface PanelConfig {
	id: string;
	label: string;
	visible: boolean;
	color: string;
}

const SLOTS_KEY = 'panel-slots';
const VISIBILITY_KEY = 'panel-visibility';

const defaultPanels: PanelConfig[] = [
	{ id: 'project', label: 'Projects', visible: true, color: '#5c7a99' },      // dusty slate blue
	{ id: 'log', label: 'Logs', visible: true, color: '#8b7355' },              // warm sepia brown
	{ id: 'note', label: 'Notes', visible: true, color: '#6b8e6b' },            // sage green
	{ id: 'wildtag', label: 'Wild Tags', visible: false, color: '#8b8b7a' },    // olive gray
	{ id: 'source', label: 'Sources', visible: false, color: '#c9a227' },       // mustard ochre
	{ id: 'actor', label: 'Actors', visible: false, color: '#8b4557' },         // burgundy wine
	{ id: 'activity', label: 'Activities', visible: true, color: '#b5838d' },   // dusty rose
	{ id: 'readinglist', label: 'Reading Lists', visible: false, color: '#5f9ea0' },  // dusty teal
	{ id: 'learningtrack', label: 'Learning Tracks', visible: false, color: '#7b6b8d' }, // dusty plum
	{ id: 'links', label: 'Links', visible: false, color: '#6b7280' } // neutral gray
];

// Default slot order: project, activity stacked left; log center; note right
const defaultSlots = ['project', 'log', 'note', 'activity'];

function loadVisibility(): Map<string, boolean> | null {
	if (typeof localStorage === 'undefined') return null;
	try {
		const saved = localStorage.getItem(VISIBILITY_KEY);
		if (!saved) return null;
		return new Map(JSON.parse(saved));
	} catch {
		return null;
	}
}

function initPanels(): PanelConfig[] {
	const saved = loadVisibility();
	if (!saved) return defaultPanels;
	return defaultPanels.map((p) => ({
		...p,
		visible: saved.has(p.id) ? saved.get(p.id)! : p.visible
	}));
}

function loadSlots(visibleIds: string[]): (string | null)[] {
	if (typeof localStorage === 'undefined') return defaultSlots;
	try {
		const saved = localStorage.getItem(SLOTS_KEY);
		if (!saved) return defaultSlots;
		const slots: (string | null)[] = JSON.parse(saved);
		// Keep only visible panels and compact (remove nulls and hidden panels)
		const result = slots.filter((s): s is string => s !== null && visibleIds.includes(s));
		// Add any missing visible panels that weren't in saved slots
		const inResult = new Set(result);
		for (const id of visibleIds) {
			if (!inResult.has(id)) {
				result.push(id);
			}
		}
		return result;
	} catch {
		return visibleIds;
	}
}

function saveSlots(slots: (string | null)[]) {
	if (typeof localStorage === 'undefined') return;
	// Trim trailing nulls before saving
	const trimmed = [...slots];
	while (trimmed.length > 0 && trimmed[trimmed.length - 1] === null) {
		trimmed.pop();
	}
	localStorage.setItem(SLOTS_KEY, JSON.stringify(trimmed));
}

function saveVisibility(panelList: PanelConfig[]) {
	if (typeof localStorage === 'undefined') return;
	const entries = panelList.map((p): [string, boolean] => [p.id, p.visible]);
	localStorage.setItem(VISIBILITY_KEY, JSON.stringify(entries));
}

// Detect fresh session: use defaults when opening a new tab/window
function isNewSession(): boolean {
	if (typeof sessionStorage === 'undefined') return true;
	return !sessionStorage.getItem('panel-session-active');
}

function markSessionActive() {
	if (typeof sessionStorage !== 'undefined') {
		sessionStorage.setItem('panel-session-active', '1');
	}
}

export const freshSession = isNewSession();
markSessionActive();

const initialPanels = freshSession ? defaultPanels : initPanels();
const visibleIds = initialPanels.filter((p) => p.visible).map((p) => p.id);

export const panels = writable<PanelConfig[]>(initialPanels);
export const panelSlots = writable<(string | null)[]>(freshSession ? defaultSlots : loadSlots(visibleIds));

panels.subscribe(saveVisibility);
panelSlots.subscribe(saveSlots);

export function togglePanel(id: string) {
	panels.update((p) =>
		p.map((panel) => (panel.id === id ? { ...panel, visible: !panel.visible } : panel))
	);

	const current = get(panels);
	const panel = current.find((p) => p.id === id);
	if (!panel) return;

	if (panel.visible) {
		// Panel just became visible — append to end
		panelSlots.update((slots) => {
			// Filter out nulls and add the new panel
			const compacted = slots.filter((s): s is string => s !== null);
			return [...compacted, id];
		});
	} else {
		// Panel just became hidden — remove its slot and compact
		panelSlots.update((slots) => slots.filter((s) => s !== id));
	}
}

export function movePanel(fromIndex: number, toIndex: number) {
	if (fromIndex === toIndex) return;
	panelSlots.update((slots) => {
		const arr = [...slots];
		// Get the panel being moved
		const panel = arr[fromIndex];
		if (!panel) return arr;

		// If target is within bounds and has a panel, swap
		if (toIndex < arr.length && arr[toIndex] !== null) {
			const temp = arr[fromIndex];
			arr[fromIndex] = arr[toIndex];
			arr[toIndex] = temp;
			return arr;
		}

		// Otherwise, remove from old position and insert at new position
		arr.splice(fromIndex, 1);
		// Adjust toIndex if needed after removal
		const insertIdx = toIndex > fromIndex ? toIndex - 1 : toIndex;
		arr.splice(Math.min(insertIdx, arr.length), 0, panel);
		// Compact to remove any nulls
		return arr.filter((s): s is string => s !== null);
	});
}

/**
 * Programmatically set which panels are visible and their slot order.
 * Used by the Focus launcher to configure the Input tab layout.
 */
export function configurePanels(visibleIds: string[], slotOrder: string[]) {
	panels.update((p) =>
		p.map((panel) => ({ ...panel, visible: visibleIds.includes(panel.id) }))
	);
	panelSlots.set(slotOrder);
}

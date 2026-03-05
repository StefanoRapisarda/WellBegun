import { writable, derived } from 'svelte/store';

export type EntityType = 'project' | 'log' | 'note' | 'activity' | 'source' | 'actor' | 'plan' | 'collection';

export interface SelectedEntity {
	entityType: EntityType;
	entityId: number;
}

function makeKey(type: EntityType, id: number): string {
	return `${type}:${id}`;
}

function parseKey(key: string): SelectedEntity {
	const sep = key.lastIndexOf(':');
	return {
		entityType: key.slice(0, sep) as EntityType,
		entityId: Number(key.slice(sep + 1))
	};
}

function createPanelSelection() {
	const { subscribe, set, update } = writable<Set<string>>(new Set());

	return {
		subscribe,
		selectOne(type: EntityType, id: number) {
			set(new Set([makeKey(type, id)]));
		},
		toggle(type: EntityType, id: number) {
			update(s => {
				const key = makeKey(type, id);
				const next = new Set(s);
				if (next.has(key)) {
					next.delete(key);
				} else {
					next.add(key);
				}
				return next;
			});
		},
		setMany(items: { type: EntityType; id: number }[]) {
			set(new Set(items.map(i => makeKey(i.type, i.id))));
		},
		clear() {
			set(new Set());
		}
	};
}

export const panelSelection = createPanelSelection();

export const selectedCount = derived(panelSelection, ($sel) => $sel.size);

export const selectedEntities = derived(panelSelection, ($sel) =>
	Array.from($sel).map(parseKey)
);

// ── Pulsing selection (time-limited visual highlight) ──

export const pulsingSelection = writable<Set<string>>(new Set());

export function setPulsingSelection(keys: string[], duration = 2500) {
	pulsingSelection.set(new Set(keys));
	setTimeout(() => pulsingSelection.set(new Set()), duration);
}

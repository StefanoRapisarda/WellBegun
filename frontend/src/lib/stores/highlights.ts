import { writable, get } from 'svelte/store';

export interface HighlightState {
	log: Set<number>;
	note: Set<number>;
	activity: Set<number>;
	project: Set<number>;
	source: Set<number>;
	actor: Set<number>;
}

function createHighlightStore() {
	const { subscribe, set, update } = writable<HighlightState>({
		log: new Set(),
		note: new Set(),
		activity: new Set(),
		project: new Set(),
		source: new Set(),
		actor: new Set()
	});

	return {
		subscribe,

		highlight(entityType: keyof HighlightState, ids: number[], duration: number = 2000) {
			update(state => {
				const newState = { ...state };
				newState[entityType] = new Set([...state[entityType], ...ids]);
				return newState;
			});

			// Auto-clear after duration
			setTimeout(() => {
				update(state => {
					const newState = { ...state };
					const remaining = new Set(state[entityType]);
					ids.forEach(id => remaining.delete(id));
					newState[entityType] = remaining;
					return newState;
				});
			}, duration);
		},

		isHighlighted(entityType: keyof HighlightState, id: number): boolean {
			return get({ subscribe })[entityType].has(id);
		},

		clear(entityType?: keyof HighlightState) {
			if (entityType) {
				update(state => ({
					...state,
					[entityType]: new Set()
				}));
			} else {
				set({
					log: new Set(),
					note: new Set(),
					activity: new Set(),
					project: new Set(),
					source: new Set(),
					actor: new Set()
				});
			}
		}
	};
}

export const highlights = createHighlightStore();

// Pulse animation for panels
export const pulsingPanels = writable<Set<string>>(new Set());

export function pulsePanel(panelId: string, duration: number = 1000) {
	pulsingPanels.update(s => new Set([...s, panelId]));
	setTimeout(() => {
		pulsingPanels.update(s => {
			const newSet = new Set(s);
			newSet.delete(panelId);
			return newSet;
		});
	}, duration);
}

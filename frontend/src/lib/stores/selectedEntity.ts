import { writable } from 'svelte/store';

export interface SelectedEntity {
	type: string;
	id: number;
	title: string;
}

export const selectedEntity = writable<SelectedEntity | null>(null);

export function selectEntity(type: string, id: number, title: string) {
	selectedEntity.set({ type, id, title });
}

export function clearSelectedEntity() {
	selectedEntity.set(null);
}

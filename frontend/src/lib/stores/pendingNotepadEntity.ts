import { writable } from 'svelte/store';

export interface PendingNotepadEntity {
	type: string;
	id: number;
}

export const pendingNotepadEntity = writable<PendingNotepadEntity | null>(null);

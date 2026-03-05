import { writable } from 'svelte/store';
import type { EntityType } from './panelSelection';

export interface PendingMember {
	entityType: EntityType;
	entityId: number;
	title: string;
}

export const pendingCollectionMembers = writable<PendingMember[]>([]);

export function removePendingMember(entityId: number) {
	pendingCollectionMembers.update(members =>
		members.filter(m => m.entityId !== entityId)
	);
}

export function clearPendingCollection() {
	pendingCollectionMembers.set([]);
}

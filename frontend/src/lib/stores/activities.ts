import { writable } from 'svelte/store';
import type { Activity } from '$lib/types';
import { getActivities } from '$lib/api/activities';

export const activities = writable<Activity[]>([]);

export async function loadActivities() {
	try {
		activities.set(await getActivities());
	} catch (e) {
		console.warn('Failed to load activities:', e);
	}
}

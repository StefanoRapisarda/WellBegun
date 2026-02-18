import { writable } from 'svelte/store';
import type { Plan } from '$lib/types';
import { getPlans } from '$lib/api/plans';

export const plans = writable<Plan[]>([]);

export async function loadPlans() {
	try {
		plans.set(await getPlans());
	} catch (e) {
		console.warn('Failed to load plans:', e);
	}
}

import { writable } from 'svelte/store';
import type { Log } from '$lib/types';
import { getLogs } from '$lib/api/logs';

export const logs = writable<Log[]>([]);

export async function loadLogs() {
	try {
		logs.set(await getLogs());
	} catch (e) {
		console.warn('Failed to load logs:', e);
	}
}

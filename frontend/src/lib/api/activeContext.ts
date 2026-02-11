import type { ActiveContext } from '$lib/types';

export async function getActiveContext(): Promise<ActiveContext> {
	const res = await fetch('/api/active-context/');
	return res.json();
}

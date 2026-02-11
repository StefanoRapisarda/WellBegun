import { writable } from 'svelte/store';
import type { LearningTrack } from '$lib/types';
import { getLearningTracks } from '$lib/api/learningTracks';

export const learningTracks = writable<LearningTrack[]>([]);

export async function loadLearningTracks() {
	try {
		learningTracks.set(await getLearningTracks());
	} catch (e) {
		console.warn('Failed to load learning tracks:', e);
	}
}

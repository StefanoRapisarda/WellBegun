import { writable } from 'svelte/store';
import type { Project } from '$lib/types';
import { getProjects } from '$lib/api/projects';

export const projects = writable<Project[]>([]);

export async function loadProjects() {
	try {
		projects.set(await getProjects());
	} catch (e) {
		console.warn('Failed to load projects:', e);
	}
}

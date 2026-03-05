import { writable } from 'svelte/store';
import type { EntityRef, CurationSuggestion, ChatMessage } from '$lib/api/coffee';

export interface DisplayMessage {
	role: 'user' | 'assistant';
	content: string;
	entities?: EntityRef[];
	curation?: CurationSuggestion[];
}

export const coffeeMessages = writable<DisplayMessage[]>([]);
export const coffeeHistory = writable<ChatMessage[]>([]);

export function resetCoffeeSession() {
	coffeeMessages.set([]);
	coffeeHistory.set([]);
}

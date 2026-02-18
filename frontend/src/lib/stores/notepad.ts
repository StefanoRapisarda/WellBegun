import { writable } from 'svelte/store';

const STORAGE_KEY = 'notepad-text';

function loadFromStorage(): string {
	if (typeof window === 'undefined') return '';
	return localStorage.getItem(STORAGE_KEY) ?? '';
}

export const notepadText = writable<string>(loadFromStorage());

notepadText.subscribe((value) => {
	if (typeof window !== 'undefined') {
		localStorage.setItem(STORAGE_KEY, value);
	}
});

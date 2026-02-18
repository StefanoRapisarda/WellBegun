import { writable } from 'svelte/store';

export type TabId = 'dashboard' | 'input' | 'notepad' | 'write' | 'read' | 'scaffold' | 'graph' | 'schema';

export const activeTab = writable<TabId>('dashboard');

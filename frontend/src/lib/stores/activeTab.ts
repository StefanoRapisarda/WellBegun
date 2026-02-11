import { writable } from 'svelte/store';

export type TabId = 'dashboard' | 'input' | 'query' | 'write' | 'read' | 'scaffold' | 'graph';

export const activeTab = writable<TabId>('dashboard');

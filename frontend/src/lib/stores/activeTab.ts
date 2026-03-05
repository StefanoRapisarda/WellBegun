import { writable } from 'svelte/store';

export type TabId = 'dashboard' | 'input' | 'notepad' | 'coffee' | 'write' | 'read' | 'scaffold' | 'graph' | 'schema' | 'workspace';

export const activeTab = writable<TabId>('dashboard');

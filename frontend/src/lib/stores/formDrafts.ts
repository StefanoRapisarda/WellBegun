import { writable, get } from 'svelte/store';

export interface FormDraft {
	[key: string]: string;
}

// Store form drafts by form type (e.g., 'log', 'note', 'project')
const drafts = writable<Record<string, FormDraft>>({});

export function getDraft(formType: string): FormDraft {
	return get(drafts)[formType] || {};
}

export function setDraft(formType: string, field: string, value: string) {
	drafts.update(d => ({
		...d,
		[formType]: {
			...(d[formType] || {}),
			[field]: value
		}
	}));
}

export function clearDraft(formType: string) {
	drafts.update(d => {
		const { [formType]: _, ...rest } = d;
		return rest;
	});
}

export function hasDraft(formType: string): boolean {
	const draft = get(drafts)[formType];
	if (!draft) return false;
	return Object.values(draft).some(v => v.trim() !== '');
}

export { drafts };

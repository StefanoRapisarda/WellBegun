import { ENTITY_CONFIG, type NotepadEntityType } from './types';

export function entityToNotepadFields(entityType: string, entity: any): Record<string, string> {
	const config = ENTITY_CONFIG[entityType as NotepadEntityType];
	if (!config) return {};
	const fields: Record<string, string> = {};

	const primaryVal = entity[config.primaryField];
	if (primaryVal != null) fields[config.primaryField] = String(primaryVal);

	const textVal = entity[config.defaultTextField];
	if (textVal != null) fields[config.defaultTextField] = String(textVal);

	for (const key of config.explicitFields) {
		if (key === 'tags') continue;
		const val = entity[key];
		if (val != null) fields[key] = String(val);
	}

	return fields;
}

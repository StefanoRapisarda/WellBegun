import { ENTITY_CONFIG, type NotepadEntityType } from './types';

/**
 * Tokenize a line by splitting on commas, respecting single/double quotes.
 * Quoted strings preserve commas inside them; quotes are stripped from the result.
 */
function tokenize(line: string): string[] {
	const tokens: string[] = [];
	let current = '';
	let quoteChar: string | null = null;

	for (let i = 0; i < line.length; i++) {
		const ch = line[i];

		if (quoteChar) {
			if (ch === quoteChar) {
				quoteChar = null;
			} else {
				current += ch;
			}
		} else if (ch === '"' || ch === "'") {
			quoteChar = ch;
		} else if (ch === ',') {
			tokens.push(current.trim());
			current = '';
		} else {
			current += ch;
		}
	}
	if (current.trim()) {
		tokens.push(current.trim());
	}
	return tokens;
}

/**
 * Build the positional field order for an entity type:
 * Position 0 = primaryField, position 1 = defaultTextField,
 * then explicitFields excluding 'tags' and already-listed fields.
 */
function getPositionalFields(entityType: NotepadEntityType): string[] {
	const config = ENTITY_CONFIG[entityType];
	const fields = [config.primaryField, config.defaultTextField];
	for (const f of config.explicitFields) {
		if (f !== 'tags' && !fields.includes(f)) {
			fields.push(f);
		}
	}
	return fields;
}

/**
 * Parse an item line into entity fields using positional/keyword argument syntax.
 *
 * - Comma-separated values are positional args
 * - `fieldName: value` syntax overrides positional assignment
 * - Quoted strings preserve commas inside them
 * - `tags` is keyword-only (never positional)
 */
export function parseItemArgs(line: string, entityType: NotepadEntityType): Record<string, string> {
	const tokens = tokenize(line);
	const positionalFields = getPositionalFields(entityType);
	const allFields = new Set([
		...positionalFields,
		'tags',
		ENTITY_CONFIG[entityType].defaultTextField
	]);

	const result: Record<string, string> = {};
	const positionalValues: string[] = [];

	for (const token of tokens) {
		// Check for keyword arg: "fieldName: value"
		const colonIdx = token.indexOf(':');
		if (colonIdx > 0) {
			const key = token.slice(0, colonIdx).trim().toLowerCase().replace(/\s+/g, '_');
			if (allFields.has(key)) {
				result[key] = token.slice(colonIdx + 1).trim();
				continue;
			}
		}
		// Otherwise it's a positional arg
		positionalValues.push(token);
	}

	// Assign positional values to fields in order
	for (let i = 0; i < positionalValues.length && i < positionalFields.length; i++) {
		if (!(positionalFields[i] in result)) {
			result[positionalFields[i]] = positionalValues[i];
		}
	}

	return result;
}

/**
 * Serialize fields back to a comma-separated positional arg string.
 * Values containing commas are quoted.
 */
export function serializeItemFields(entityType: NotepadEntityType, item: { title: string; fields?: Record<string, string> }): string {
	if (!item.fields || Object.keys(item.fields).length === 0) {
		return item.title;
	}

	const positionalFields = getPositionalFields(entityType);
	const parts: string[] = [];

	for (const field of positionalFields) {
		const val = item.fields[field];
		if (val !== undefined) {
			// Quote values that contain commas
			parts.push(val.includes(',') ? `"${val}"` : val);
		} else {
			break; // Stop at the first missing positional field
		}
	}

	// Add any keyword-only fields (tags)
	if (item.fields.tags) {
		parts.push(`tags: ${item.fields.tags}`);
	}

	return parts.join(', ');
}

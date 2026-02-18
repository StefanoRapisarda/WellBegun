import { ENTITY_CONFIG, VALID_ENTITY_TYPES, type NotepadEntityType, type ParsedEntity } from './types';

export function serializeEntity(type: NotepadEntityType, fields: Record<string, string>, items?: Array<{ title: string; is_done: boolean; header?: string | null }>, dbId?: number): string {
	const config = ENTITY_CONFIG[type];
	const lines: string[] = [dbId != null ? `@${type}#${dbId}` : `@${type}`];

	// Primary field as first line
	const primary = fields[config.primaryField]?.trim();
	if (primary && primary !== config.defaultTitle) {
		lines.push(primary);
	}

	// Explicit fields
	for (const key of config.explicitFields) {
		const val = fields[key]?.trim();
		if (val) {
			lines.push(`${key}: ${val}`);
		}
	}

	// Default text field as remaining lines
	const defaultText = fields[config.defaultTextField]?.trim();
	if (defaultText) {
		lines.push(defaultText);
	}

	// Plan items grouped by header
	if (type === 'plan' && items && items.length > 0) {
		// Output ungrouped items first (null/undefined header)
		const ungrouped = items.filter(i => !i.header);
		for (const item of ungrouped) {
			lines.push(`- ${item.title}`);
		}
		// Group remaining items by header, preserving order of first occurrence
		const headers: string[] = [];
		for (const item of items) {
			if (item.header && !headers.includes(item.header)) {
				headers.push(item.header);
			}
		}
		for (const header of headers) {
			lines.push(`## ${header}`);
			for (const item of items.filter(i => i.header === header)) {
				lines.push(`- ${item.title}`);
			}
		}
	}

	return lines.join('\n');
}

export function parseNotepadText(text: string): ParsedEntity[] {
	const lines = text.split('\n');
	const entities: ParsedEntity[] = [];

	let currentType: NotepadEntityType | null = null;
	let currentDbId: number | undefined = undefined;
	let blockStartLine = 0;
	let blockEndLine = 0;
	let blockLines: string[] = [];

	function flushBlock() {
		if (currentType === null) return;

		const config = ENTITY_CONFIG[currentType];
		const fields: Record<string, string> = {};
		const planItems: Array<{ title: string; is_done: boolean; header?: string | null }> = [];

		// Find first non-empty line = primary field
		let primarySet = false;
		const remainingLines: string[] = [];
		let currentHeader: string | null = null;

		for (const line of blockLines) {
			const trimmed = line.trim();
			if (!trimmed) {
				if (primarySet) remainingLines.push(line);
				continue;
			}

			// Parse plan section headers: ## Header
			if (currentType === 'plan') {
				const headerMatch = trimmed.match(/^##\s+(.+)$/);
				if (headerMatch) {
					currentHeader = headerMatch[1];
					continue;
				}
			}

			// Parse plan items: any line starting with -
			if (currentType === 'plan') {
				const itemMatch = trimmed.match(/^-\s+(.+)$/);
				if (itemMatch) {
					planItems.push({
						is_done: false,
						title: itemMatch[1],
						header: currentHeader
					});
					continue;
				}
			}

			if (!primarySet) {
				fields[config.primaryField] = trimmed;
				primarySet = true;
				continue;
			}

			// Check for explicit field: value syntax
			const colonIdx = trimmed.indexOf(':');
			if (colonIdx > 0) {
				const fieldName = trimmed.slice(0, colonIdx).trim().toLowerCase().replace(/\s+/g, '_');
				const allFields = [config.primaryField, config.defaultTextField, ...config.explicitFields];
				if (allFields.includes(fieldName)) {
					fields[fieldName] = trimmed.slice(colonIdx + 1).trim();
					continue;
				}
			}

			remainingLines.push(line);
		}

		// Accumulate remaining lines into default text field
		const defaultText = remainingLines
			.join('\n')
			.trim();
		if (defaultText) {
			fields[config.defaultTextField] = defaultText;
		}

		// Apply default title if no primary field
		if (!fields[config.primaryField]) {
			fields[config.primaryField] = config.defaultTitle;
		}

		const entity: ParsedEntity = {
			type: currentType,
			fields,
			startLine: blockStartLine,
			endLine: blockEndLine,
			...(currentDbId != null && { dbId: currentDbId })
		};

		if (currentType === 'plan' && planItems.length > 0) {
			entity.items = planItems;
		}

		entities.push(entity);

		// Emit virtual activity entities for plan items (shown as cards, skipped on commit)
		if (currentType === 'plan' && planItems.length > 0) {
			for (const item of planItems) {
				entities.push({
					type: 'activity',
					fields: { title: item.title },
					startLine: blockStartLine,
					endLine: blockEndLine,
					virtual: true
				});
			}
		}
	}

	for (let i = 0; i < lines.length; i++) {
		const trimmed = lines[i].trim();
		// Match @tag or @tag#id, optionally followed by space and text
		const tagMatch = trimmed.match(/^@(\w+)(?:#(\d+))?(?:\s+(.+))?$/);

		if (tagMatch && VALID_ENTITY_TYPES.includes(tagMatch[1] as NotepadEntityType)) {
			flushBlock();
			currentType = tagMatch[1] as NotepadEntityType;
			currentDbId = tagMatch[2] ? parseInt(tagMatch[2], 10) : undefined;
			blockStartLine = i;
			blockEndLine = i + 1;
			blockLines = [];
			// If there's text after the tag on the same line, treat it as the first content line
			if (tagMatch[3]) {
				blockLines.push(tagMatch[3]);
			}
		} else if (currentType !== null) {
			blockLines.push(lines[i]);
			blockEndLine = i + 1;
		}
	}

	// Flush last block
	flushBlock();

	return entities;
}

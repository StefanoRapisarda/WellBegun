import { ENTITY_CONFIG, VALID_ENTITY_TYPES, PLAN_SUB_SECTIONS, type NotepadEntityType, type ParsedEntity } from './types';
import { parseItemArgs, serializeItemFields } from './argParser';

function pluralize(s: string): string {
	if (s.endsWith('y') && !s.endsWith('ay') && !s.endsWith('ey') && !s.endsWith('oy')) {
		return s.slice(0, -1) + 'ies';
	}
	if (s.endsWith('s')) return s;
	return s + 's';
}

export function serializeEntity(type: NotepadEntityType, fields: Record<string, string>, items?: Array<{ title: string; is_done: boolean; header?: string | null; fields?: Record<string, string>; subSection?: string }>, dbId?: number): string {
	// If this is a collection with member_type, serialize using the original entity tag
	const serializeType = (fields.member_type as NotepadEntityType) ?? type;
	const config = ENTITY_CONFIG[serializeType];
	const lines: string[] = [dbId != null ? `@${serializeType}#${dbId}` : `@${serializeType}`];

	// Primary field as first line
	// For collections with member_type, the title may be stored under 'title' rather than
	// the member type's primary field (e.g. 'full_name' for actors)
	const primary = (fields[config.primaryField] ?? fields.title)?.trim();
	if (primary && primary !== config.defaultTitle) {
		lines.push(primary);
	}

	// Explicit fields (skip member_type — internal only)
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

	// Items grouped by sub-section, then by header — all entity types
	if (items && items.length > 0) {
		const defaultItemType = (fields.member_type as NotepadEntityType) ?? type;

		// Collect sub-sections in order of first occurrence
		const subSections: (string | undefined)[] = [];
		for (const item of items) {
			if (!subSections.includes(item.subSection)) {
				subSections.push(item.subSection);
			}
		}

		for (const section of subSections) {
			const sectionItems = items.filter(i => i.subSection === section);
			const itemType = section ? (PLAN_SUB_SECTIONS[section] ?? defaultItemType) : defaultItemType;

			// Emit @@section marker (skip for items with no sub-section)
			if (section) {
				lines.push(`@@${section}`);
			}

			// Output ungrouped items first (null/undefined header)
			const ungrouped = sectionItems.filter(i => !i.header);
			for (const item of ungrouped) {
				lines.push(`- ${serializeItemFields(itemType, item)}`);
			}
			// Group remaining items by header, preserving order of first occurrence
			const headers: string[] = [];
			for (const item of sectionItems) {
				if (item.header && !headers.includes(item.header)) {
					headers.push(item.header);
				}
			}
			for (const header of headers) {
				lines.push(`## ${header}`);
				for (const item of sectionItems.filter(i => i.header === header)) {
					lines.push(`- ${serializeItemFields(itemType, item)}`);
				}
			}
		}
	}

	return lines.join('\n');
}

export function serializeListBlock(type: NotepadEntityType, itemNames: string[]): string {
	const lines = [`@@${type}`];
	for (const name of itemNames) {
		lines.push(name);
	}
	return lines.join('\n');
}

/**
 * Push inline text (after @tag on the same line) into blockLines.
 * If the text contains commas, parse with argParser and push as
 * individual field: value lines so flushBlock handles them correctly.
 */
function pushInlineText(text: string, type: NotepadEntityType, blockLines: string[]) {
	if (text.includes(',')) {
		const config = ENTITY_CONFIG[type];
		const fields = parseItemArgs(text, type);
		// Push primary field first (becomes the title line)
		if (fields[config.primaryField]) {
			blockLines.push(fields[config.primaryField]);
		}
		// Push remaining fields as field: value lines
		for (const [key, val] of Object.entries(fields)) {
			if (key !== config.primaryField && val) {
				blockLines.push(`${key}: ${val}`);
			}
		}
	} else {
		blockLines.push(text);
	}
}

export function parseNotepadText(text: string): ParsedEntity[] {
	const lines = text.split('\n');
	const entities: ParsedEntity[] = [];

	let currentType: NotepadEntityType | null = null;
	let currentDbId: number | undefined = undefined;
	let blockStartLine = 0;
	let blockEndLine = 0;
	let blockLines: string[] = [];

	// List block state
	let inListBlock = false;
	let listBlockType: NotepadEntityType | null = null;
	let listBlockHeaderLine = 0;
	let listBlockItems: Array<{ name: string; lineIndex: number }> = [];

	function flushListBlock() {
		if (!listBlockType) return;

		const config = ENTITY_CONFIG[listBlockType];
		// Compute the endLine as the line after the last item (or header if empty)
		const lastLine = listBlockItems.length > 0
			? listBlockItems[listBlockItems.length - 1].lineIndex
			: listBlockHeaderLine;

		for (const item of listBlockItems) {
			entities.push({
				type: listBlockType,
				fields: { [config.primaryField]: item.name },
				startLine: item.lineIndex,
				endLine: item.lineIndex + 1,
				fromListBlock: true,
				listBlockHeaderLine
			});
		}

		inListBlock = false;
		listBlockType = null;
		listBlockItems = [];
	}

	function flushBlock() {
		if (currentType === null) return;

		const config = ENTITY_CONFIG[currentType];
		const fields: Record<string, string> = {};
		const planItems: Array<{ title: string; is_done: boolean; header?: string | null; fields?: Record<string, string>; subSection?: string }> = [];

		// Find first non-empty line = primary field
		let primarySet = false;
		const remainingLines: string[] = [];
		let currentHeader: string | null = null;
		let currentSubSection: string | undefined = undefined;
		const subSectionText = new Map<string, string[]>();

		// Item regex: matches -, *, 1., 2., I., II., etc.
		const ITEM_RE = /^(?:-|\*|\d+\.|[IVXLCDM]+\.)\s+(.+)$/;

		// Pre-process blockLines: resolve quoted blocks (strip delimiters).
		// Quoted lines are plain text — items, headers, field:value are NOT parsed.
		const QUOTE_DELIMITERS = ['"""', "'''", '"', "'"];
		interface ResolvedLine { text: string; quoted: boolean }
		const resolvedLines: ResolvedLine[] = [];
		let qIdx = 0;
		while (qIdx < blockLines.length) {
			const trimmed = blockLines[qIdx].trim();
			let delim: string | null = null;
			for (const d of QUOTE_DELIMITERS) {
				if (trimmed.startsWith(d)) { delim = d; break; }
			}
			if (delim) {
				const afterOpen = trimmed.slice(delim.length);
				// Same-line close? e.g. "some text"
				if (afterOpen.endsWith(delim) && afterOpen.length >= delim.length) {
					resolvedLines.push({ text: afterOpen.slice(0, -delim.length), quoted: true });
				} else {
					// Multi-line: collect until closing delimiter
					if (afterOpen) resolvedLines.push({ text: afterOpen, quoted: true });
					qIdx++;
					while (qIdx < blockLines.length) {
						const lt = blockLines[qIdx].trim();
						if (lt.endsWith(delim!)) {
							const before = lt.slice(0, -delim!.length);
							if (before) resolvedLines.push({ text: before, quoted: true });
							break;
						}
						resolvedLines.push({ text: blockLines[qIdx], quoted: true });
						qIdx++;
					}
				}
			} else {
				resolvedLines.push({ text: blockLines[qIdx], quoted: false });
			}
			qIdx++;
		}

		for (const resolved of resolvedLines) {
			const trimmed = resolved.text.trim();
			if (!trimmed) {
				if (primarySet) {
					if (currentType === 'plan' && currentSubSection) {
						if (!subSectionText.has(currentSubSection)) subSectionText.set(currentSubSection, []);
						subSectionText.get(currentSubSection)!.push(resolved.text);
					} else {
						remainingLines.push(resolved.text);
					}
				}
				continue;
			}

			// Quoted lines: plain text only — skip all special parsing
			if (resolved.quoted) {
				if (!primarySet) {
					fields[config.primaryField] = trimmed;
					primarySet = true;
				} else {
					remainingLines.push(resolved.text);
				}
				continue;
			}

			// Parse @@sub-section markers inside plan blocks
			const subSectionMatch = trimmed.match(/^@@(\w+)$/);
			if (subSectionMatch && currentType === 'plan' && subSectionMatch[1] in PLAN_SUB_SECTIONS) {
				currentSubSection = subSectionMatch[1];
				currentHeader = null; // Reset header when entering a new sub-section
				continue;
			}

			// Parse section headers: ## Header — all types
			const headerMatch = trimmed.match(/^##\s+(.+)$/);
			if (headerMatch) {
				currentHeader = headerMatch[1];
				continue;
			}

			// Parse items: -, *, 1., I., etc. — all types
			const itemMatch = trimmed.match(ITEM_RE);
			if (itemMatch) {
				const rawText = itemMatch[1];
				// Use the sub-section's entity type for field parsing (e.g. source fields for @@source)
				const itemEntityType = currentSubSection ? (PLAN_SUB_SECTIONS[currentSubSection] ?? currentType) : currentType;
				const itemFields = parseItemArgs(rawText, itemEntityType);
				const itemConfig = ENTITY_CONFIG[itemEntityType];
				planItems.push({
					is_done: false,
					title: itemFields[itemConfig.primaryField] || rawText,
					header: currentHeader,
					fields: itemFields,
					subSection: currentSubSection
				});
				continue;
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

			if (currentType === 'plan' && currentSubSection) {
				if (!subSectionText.has(currentSubSection)) subSectionText.set(currentSubSection, []);
				subSectionText.get(currentSubSection)!.push(resolved.text);
			} else {
				remainingLines.push(resolved.text);
			}
		}

		// Accumulate remaining lines into default text field
		const defaultText = remainingLines
			.join('\n')
			.trim();
		if (defaultText) {
			fields[config.defaultTextField] = defaultText;
		}

		// Convert sub-section prose text into auto-titled plan items
		if (currentType === 'plan') {
			const planTitle = fields[config.primaryField] || config.defaultTitle;
			for (const [section, textLines] of subSectionText) {
				const text = textLines.join('\n').trim();
				if (!text) continue;
				const childType: NotepadEntityType = PLAN_SUB_SECTIONS[section] ?? 'activity';
				const childConfig = ENTITY_CONFIG[childType];
				const autoTitle = `${planTitle} ${section}`;
				planItems.push({
					is_done: false,
					title: autoTitle,
					header: null,
					fields: { [childConfig.primaryField]: autoTitle, [childConfig.defaultTextField]: text },
					subSection: section
				});
			}
		}

		// Apply default title if no primary field
		if (!fields[config.primaryField]) {
			fields[config.primaryField] = config.defaultTitle;
		}

		const isContainer = currentType === 'plan' || currentType === 'collection';

		const entity: ParsedEntity = {
			type: currentType,
			fields,
			startLine: blockStartLine,
			endLine: blockEndLine,
			...(currentDbId != null && { dbId: currentDbId })
		};

		if (planItems.length > 0) {
			entity.items = planItems;
		}

		if (!isContainer && planItems.length > 0) {
			// Non-container with items → emit as a collection (auto-created on save)
			// plus virtual children of the original type
			const collIdx = entities.length;
			const collFields: Record<string, string> = { ...fields, member_type: currentType };
			// Remap the original type's primary field to 'title' for the collection
			// (e.g. actor's 'full_name' → collection's 'title')
			if (config.primaryField !== 'title' && collFields[config.primaryField]) {
				collFields.title = collFields[config.primaryField];
				delete collFields[config.primaryField];
			}
			// If the user didn't specify a title, use "default" for the collection
			const collConfig = ENTITY_CONFIG['collection'];
			if (!collFields.title || collFields.title === config.defaultTitle) {
				collFields.title = collConfig.defaultTitle;
			}
			entities.push({
				type: 'collection',
				fields: collFields,
				startLine: blockStartLine,
				endLine: blockEndLine,
				items: planItems,
				...(currentDbId != null && { dbId: currentDbId })
			});
			for (const item of planItems) {
				entities.push({
					type: currentType,
					fields: item.fields ?? { [config.primaryField]: item.title },
					startLine: blockStartLine,
					endLine: blockEndLine,
					virtual: true,
					parentIndex: collIdx
				});
			}
		} else {
			entities.push(entity);

			// Emit virtual entities for items (shown as cards, skipped on commit)
			if (currentType === 'plan' && planItems.length > 0) {
				const planIdx = entities.length - 1; // plan was just pushed

				// Group items by sub-section
				const groups = new Map<string | undefined, typeof planItems>();
				for (const item of planItems) {
					const key = item.subSection;
					if (!groups.has(key)) groups.set(key, []);
					groups.get(key)!.push(item);
				}

				for (const [section, groupItems] of groups) {
					const virtualType: NotepadEntityType = section
						? (PLAN_SUB_SECTIONS[section] ?? 'activity')
						: 'activity';
					const virtualConfig = ENTITY_CONFIG[virtualType];

					if (groupItems.length > 1) {
						// Emit virtual collection for this sub-section
						const sectionLabel = section ? pluralize(section) : pluralize(virtualType);
						const planTitle = fields[config.primaryField] || config.defaultTitle;
						const collIdx = entities.length;
						entities.push({
							type: 'collection',
							fields: { title: `${planTitle} ${sectionLabel}` },
							startLine: blockStartLine,
							endLine: blockEndLine,
							virtual: true,
							parentIndex: planIdx,
							subSection: section
						});

						// Emit virtual items connected to the collection
						for (const item of groupItems) {
							const vFields = { ...(item.fields ?? { [virtualConfig.primaryField]: item.title }) };
							if (virtualType === 'activity') vFields.status = item.is_done ? 'done' : 'todo';
							entities.push({
								type: virtualType,
								fields: vFields,
								startLine: blockStartLine,
								endLine: blockEndLine,
								virtual: true,
								parentIndex: collIdx
							});
						}
					} else {
						// Single item: connect directly to plan
						const vFields = { ...(groupItems[0].fields ?? { [virtualConfig.primaryField]: groupItems[0].title }) };
						if (virtualType === 'activity') vFields.status = groupItems[0].is_done ? 'done' : 'todo';
						entities.push({
							type: virtualType,
							fields: vFields,
							startLine: blockStartLine,
							endLine: blockEndLine,
							virtual: true,
							parentIndex: planIdx,
							subSection: section
						});
					}
				}
			}
		}
	}

	for (let i = 0; i < lines.length; i++) {
		const trimmed = lines[i].trim();

		// Match @@type (list block header) — checked BEFORE single @
		const listMatch = trimmed.match(/^@@(\w+)$/);
		if (listMatch) {
			// Inside a @plan block, @@section markers are sub-sections (handled by flushBlock)
			if (currentType === 'plan' && listMatch[1] in PLAN_SUB_SECTIONS) {
				blockLines.push(lines[i]);
				blockEndLine = i + 1;
				continue;
			}

			if (VALID_ENTITY_TYPES.includes(listMatch[1] as NotepadEntityType)) {
				// Flush any previous block or list block
				flushBlock();
				currentType = null;
				currentDbId = undefined;
				blockLines = [];
				flushListBlock();

				inListBlock = true;
				listBlockType = listMatch[1] as NotepadEntityType;
				listBlockHeaderLine = i;
				listBlockItems = [];
				continue;
			}
		}

		// Inside a list block: collect items
		if (inListBlock) {
			// A single @ tag or another @@ tag ends the list block
			const singleTagMatch = trimmed.match(/^@(\w+)(?:#(\d+))?(?:[,\s]\s*(.+))?$/);
			if (singleTagMatch && VALID_ENTITY_TYPES.includes(singleTagMatch[1] as NotepadEntityType)) {
				flushListBlock();
				// Start a regular block
				currentType = singleTagMatch[1] as NotepadEntityType;
				currentDbId = singleTagMatch[2] ? parseInt(singleTagMatch[2], 10) : undefined;
				blockStartLine = i;
				blockEndLine = i + 1;
				blockLines = [];
				if (singleTagMatch[3]) {
					pushInlineText(singleTagMatch[3], currentType, blockLines);
				}
				continue;
			}

			// Non-empty line = list item
			if (trimmed) {
				listBlockItems.push({ name: trimmed, lineIndex: i });
			}
			continue;
		}

		// Match @tag or @tag#id, optionally followed by comma/space and text
		const tagMatch = trimmed.match(/^@(\w+)(?:#(\d+))?(?:[,\s]\s*(.+))?$/);

		if (tagMatch && VALID_ENTITY_TYPES.includes(tagMatch[1] as NotepadEntityType)) {
			flushBlock();
			currentType = tagMatch[1] as NotepadEntityType;
			currentDbId = tagMatch[2] ? parseInt(tagMatch[2], 10) : undefined;
			blockStartLine = i;
			blockEndLine = i + 1;
			blockLines = [];
			// If there's text after the tag on the same line, parse it
			if (tagMatch[3]) {
				pushInlineText(tagMatch[3], currentType, blockLines);
			}
		} else if (currentType !== null) {
			blockLines.push(lines[i]);
			blockEndLine = i + 1;
		}
	}

	// Flush last block or list block
	flushListBlock();
	flushBlock();

	return entities;
}

<script lang="ts">
	import { get } from 'svelte/store';
	import { notepadText } from '$lib/stores/notepad';
	import { VALID_ENTITY_TYPES, ENTITY_CONFIG, type NotepadEntityType } from '$lib/notepad/types';
	import { notes } from '$lib/stores/notes';
	import { projects } from '$lib/stores/projects';
	import { logs } from '$lib/stores/logs';
	import { activities } from '$lib/stores/activities';
	import { sources } from '$lib/stores/sources';
	import { actors } from '$lib/stores/actors';
	import { readingLists } from '$lib/stores/readingLists';
	import { plans } from '$lib/stores/plans';

	// ── Quick-add entity buttons ──
	const ENTITY_BUTTONS: { type: NotepadEntityType; label: string; color: string }[] = [
		{ type: 'note', label: '+Note', color: '#6b8e6b' },
		{ type: 'project', label: '+Project', color: '#5c7a99' },
		{ type: 'log', label: '+Log', color: '#8b7355' },
		{ type: 'activity', label: '+Activity', color: '#b5838d' },
		{ type: 'source', label: '+Source', color: '#c9a227' },
		{ type: 'actor', label: '+Actor', color: '#8b4557' },
		{ type: 'reading_list', label: '+ReadList', color: '#5f9ea0' },
		{ type: 'plan', label: '+Plan', color: '#6b8ba3' }
	];

	function generateTemplate(type: NotepadEntityType): string {
		const config = ENTITY_CONFIG[type];
		// Line 1: @type <title goes here>
		// Line 2: empty line for default text content (content/description/notes)
		// Remaining: explicit fields
		const lines: string[] = [`@${type} `, ''];
		for (const field of config.explicitFields) {
			lines.push(`${field}: `);
		}
		return lines.join('\n');
	}

	function insertTemplate(type: NotepadEntityType) {
		const template = generateTemplate(type);
		const pos = textareaEl?.selectionStart ?? value.length;
		const before = value.slice(0, pos);
		const after = value.slice(pos);

		// Ensure blank line separator if there's content before
		let separator = '';
		if (before.trim() && !before.endsWith('\n\n')) {
			separator = before.endsWith('\n') ? '\n' : '\n\n';
		}

		const newValue = before + separator + template + '\n' + after;
		value = newValue;
		notepadText.set(value);

		// Place cursor right after "@type " so user can type the title
		const cursorPos = before.length + separator.length + `@${type} `.length;
		requestAnimationFrame(() => {
			textareaEl?.focus();
			textareaEl?.setSelectionRange(cursorPos, cursorPos);
		});
	}

	interface Suggestion {
		label: string;
		detail?: string;
		color: string;
		insertValue: string;
	}

	let value = $state($notepadText);
	let textareaEl: HTMLTextAreaElement | undefined = $state();

	// Unified suggestion state
	let showSuggestions = $state(false);
	let suggestionMode = $state<'type' | 'entity'>('type');
	let suggestions = $state<Suggestion[]>([]);
	let selectedIndex = $state(0);
	let replaceStart = $state(-1);
	let dropdownTop = $state(0);
	let dropdownLeft = $state(0);

	$effect(() => {
		value = $notepadText;
	});

	function handleInput(e: Event) {
		const target = e.target as HTMLTextAreaElement;
		value = target.value;
		notepadText.set(value);
		checkSuggestions();
	}

	function checkSuggestions() {
		if (!textareaEl) return;
		// Try @type suggestions first, then entity name suggestions
		if (checkAtTypeSuggestion()) return;
		if (checkEntityNameSuggestion()) return;
		closeSuggestions();
	}

	// ── @type suggestions (e.g. typing "@no" suggests "@note") ──

	function checkAtTypeSuggestion(): boolean {
		if (!textareaEl) return false;
		const pos = textareaEl.selectionStart;
		const textBefore = value.slice(0, pos);
		const lastNewline = textBefore.lastIndexOf('\n');
		const lineStart = lastNewline + 1;
		const lineText = textBefore.slice(lineStart);

		const match = lineText.match(/^(\s*)@(\w*)$/);
		if (match) {
			const query = match[2].toLowerCase();
			const filtered = VALID_ENTITY_TYPES.filter(t => t.startsWith(query));
			if (filtered.length > 0) {
				replaceStart = lineStart + match[1].length;
				suggestions = filtered.map(t => ({
					label: `@${t}`,
					color: getColor(t),
					insertValue: `@${t}`
				}));
				selectedIndex = 0;
				suggestionMode = 'type';
				positionDropdown(replaceStart);
				showSuggestions = true;
				return true;
			}
		}
		return false;
	}

	// ── Entity name suggestions (typing title after @entity_type) ──

	function checkEntityNameSuggestion(): boolean {
		if (!textareaEl) return false;
		const pos = textareaEl.selectionStart;
		const textBefore = value.slice(0, pos);
		const lines = textBefore.split('\n');
		const currentLineIdx = lines.length - 1;
		const currentLineText = lines[currentLineIdx];
		const trimmed = currentLineText.trim();

		// Skip if empty, starts with @, or looks like field: value
		if (!trimmed || trimmed.startsWith('@') || /^\w[\w\s]*:/.test(trimmed)) return false;

		// Need at least 2 characters to search
		if (trimmed.length < 2) return false;

		// Scan backwards for the @tag that starts this block
		let entityType: NotepadEntityType | null = null;
		let tagLineIdx = -1;
		for (let i = currentLineIdx - 1; i >= 0; i--) {
			const tagMatch = lines[i].trim().match(/^@(\w+)/);
			if (tagMatch && VALID_ENTITY_TYPES.includes(tagMatch[1] as NotepadEntityType)) {
				entityType = tagMatch[1] as NotepadEntityType;
				tagLineIdx = i;
				break;
			}
		}
		if (!entityType || tagLineIdx === -1) return false;

		// Only suggest on the primary field line (first non-empty line after the tag)
		for (let i = tagLineIdx + 1; i < currentLineIdx; i++) {
			if (lines[i].trim()) {
				// There's already a non-empty line before this one — cursor is past the primary field
				return false;
			}
		}

		const config = ENTITY_CONFIG[entityType];
		const color = config.color;
		const filtered = searchEntities(entityType, trimmed);

		if (filtered.length > 0) {
			const lastNewline = textBefore.lastIndexOf('\n');
			const lineStart = lastNewline + 1;
			// Find start of actual text (skip leading whitespace)
			const leadingWs = currentLineText.match(/^(\s*)/)?.[1].length ?? 0;
			replaceStart = lineStart + leadingWs;
			suggestions = filtered;
			selectedIndex = 0;
			suggestionMode = 'entity';
			positionDropdown(replaceStart);
			showSuggestions = true;
			return true;
		}
		return false;
	}

	function searchEntities(entityType: NotepadEntityType, query: string): Suggestion[] {
		const q = query.toLowerCase();
		const color = ENTITY_CONFIG[entityType].color;
		const primaryField = ENTITY_CONFIG[entityType].primaryField;

		const mapFn = (item: { [key: string]: any }, detailField?: string): Suggestion => ({
			label: item[primaryField],
			detail: detailField && item[detailField] ? String(item[detailField]).slice(0, 50) : undefined,
			color,
			insertValue: item[primaryField]
		});

		switch (entityType) {
			case 'note':
				return get(notes).filter(n => n.title.toLowerCase().includes(q)).slice(0, 8)
					.map(n => mapFn(n, 'content'));
			case 'project':
				return get(projects).filter(p => p.title.toLowerCase().includes(q)).slice(0, 8)
					.map(p => ({ ...mapFn(p, 'description'), detail: p.status }));
			case 'log':
				return get(logs).filter(l => l.title.toLowerCase().includes(q)).slice(0, 8)
					.map(l => ({ ...mapFn(l, 'content'), detail: l.log_type }));
			case 'activity':
				return get(activities).filter(a => a.title.toLowerCase().includes(q)).slice(0, 8)
					.map(a => mapFn(a, 'description'));
			case 'source':
				return get(sources).filter(s => s.title.toLowerCase().includes(q)).slice(0, 8)
					.map(s => ({ ...mapFn(s), detail: s.author ?? undefined }));
			case 'actor':
				return get(actors).filter(a => a.full_name.toLowerCase().includes(q)).slice(0, 8)
					.map(a => ({ ...mapFn(a), detail: a.role ?? undefined }));
			case 'reading_list':
				return get(readingLists).filter(rl => rl.title.toLowerCase().includes(q)).slice(0, 8)
					.map(rl => mapFn(rl, 'description'));
			case 'plan':
				return get(plans).filter(p => p.title.toLowerCase().includes(q)).slice(0, 8)
					.map(p => mapFn(p, 'description'));
			default:
				return [];
		}
	}

	// ── Shared ──

	function closeSuggestions() {
		showSuggestions = false;
		suggestions = [];
	}

	function positionDropdown(anchorPos: number) {
		if (!textareaEl) return;

		const mirror = document.createElement('div');
		const style = window.getComputedStyle(textareaEl);
		const props = [
			'fontFamily', 'fontSize', 'fontWeight', 'lineHeight', 'letterSpacing',
			'paddingTop', 'paddingLeft', 'paddingRight', 'paddingBottom',
			'borderTopWidth', 'borderLeftWidth', 'boxSizing', 'wordWrap', 'whiteSpace'
		];
		mirror.style.position = 'absolute';
		mirror.style.visibility = 'hidden';
		mirror.style.overflow = 'hidden';
		mirror.style.width = style.width;
		for (const prop of props) {
			(mirror.style as any)[prop] = (style as any)[prop];
		}
		mirror.style.whiteSpace = 'pre-wrap';
		mirror.style.wordWrap = 'break-word';

		mirror.textContent = value.slice(0, anchorPos);
		const span = document.createElement('span');
		span.textContent = '|';
		mirror.appendChild(span);
		document.body.appendChild(mirror);

		const spanRect = span.getBoundingClientRect();
		const mirrorRect = mirror.getBoundingClientRect();

		dropdownTop = (spanRect.top - mirrorRect.top) - textareaEl.scrollTop + parseFloat(style.lineHeight || '20');
		dropdownLeft = spanRect.left - mirrorRect.left;

		document.body.removeChild(mirror);
	}

	function applySuggestion(suggestion: Suggestion) {
		if (!textareaEl) return;
		const pos = textareaEl.selectionStart;
		const before = value.slice(0, replaceStart);
		const after = value.slice(pos);
		value = before + suggestion.insertValue + after;
		notepadText.set(value);
		closeSuggestions();

		const newPos = replaceStart + suggestion.insertValue.length;
		requestAnimationFrame(() => {
			textareaEl?.focus();
			textareaEl?.setSelectionRange(newPos, newPos);
		});
	}

	function handleKeydown(e: KeyboardEvent) {
		if (!showSuggestions) return;

		if (e.key === 'ArrowDown') {
			e.preventDefault();
			selectedIndex = (selectedIndex + 1) % suggestions.length;
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			selectedIndex = (selectedIndex - 1 + suggestions.length) % suggestions.length;
		} else if (e.key === 'Enter' || e.key === 'Tab') {
			e.preventDefault();
			applySuggestion(suggestions[selectedIndex]);
		} else if (e.key === 'Escape') {
			closeSuggestions();
		}
	}

	function handleBlur() {
		setTimeout(() => { closeSuggestions(); }, 200);
	}

	function getColor(entityType: string): string {
		return ENTITY_CONFIG[entityType as keyof typeof ENTITY_CONFIG]?.color ?? '#6b7280';
	}
</script>

<div class="editor-pane">
	<div class="entity-toolbar">
		{#each ENTITY_BUTTONS as btn}
			<button
				class="entity-btn"
				style:--btn-color={btn.color}
				onclick={() => insertTemplate(btn.type)}
			>
				{btn.label}
			</button>
		{/each}
	</div>
	<div class="textarea-wrapper">
		<textarea
			bind:this={textareaEl}
			class="notepad-textarea"
			{value}
			oninput={handleInput}
			onkeydown={handleKeydown}
			onblur={handleBlur}
			placeholder={"@note Meeting Notes\nWe discussed the new API design.\ntags: work, meetings\n\n@actor John Smith\nVery knowledgeable about microservices.\nrole: Lead Developer\naffiliation: Acme Corp"}
			spellcheck="false"
		></textarea>
		{#if showSuggestions}
			<ul class="suggestions" class:wide={suggestionMode === 'entity'} style="top: {dropdownTop}px; left: {dropdownLeft}px;">
				{#each suggestions as s, i (s.label + i)}
					<li>
						<button
							class:selected={i === selectedIndex}
							onmousedown={(e) => { e.preventDefault(); applySuggestion(s); }}
						>
							<span class="type-dot" style="background: {s.color}"></span>
							<span class="suggestion-label">{s.label}</span>
							{#if s.detail}
								<span class="suggestion-detail">{s.detail}</span>
							{/if}
						</button>
					</li>
				{/each}
			</ul>
		{/if}
	</div>
</div>

<style>
	.editor-pane {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
	}
	.entity-toolbar {
		display: flex;
		gap: 4px;
		padding: 6px 10px;
		background: #fafafa;
		border-bottom: 1px solid #e5e7eb;
		flex-wrap: wrap;
	}
	.entity-btn {
		padding: 3px 8px;
		border: 1px solid var(--btn-color);
		border-radius: 6px;
		background: white;
		cursor: pointer;
		font-size: 0.68rem;
		color: var(--btn-color);
		font-weight: 500;
		transition: all 0.15s;
	}
	.entity-btn:hover {
		background: var(--btn-color);
		color: white;
	}
	.textarea-wrapper {
		position: relative;
		flex: 1;
		display: flex;
	}
	.notepad-textarea {
		width: 100%;
		height: 100%;
		border: none;
		outline: none;
		resize: none;
		padding: 16px;
		font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', 'Menlo', monospace;
		font-size: 0.82rem;
		line-height: 1.6;
		color: #1f2937;
		background: #fafafa;
	}
	.notepad-textarea::placeholder {
		color: #c8cdd3;
	}
	.suggestions {
		position: absolute;
		background: white;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		list-style: none;
		padding: 4px 0;
		margin: 0;
		min-width: 160px;
		max-width: 350px;
		z-index: 200;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
	}
	.suggestions.wide {
		min-width: 250px;
	}
	.suggestions li button {
		display: flex;
		align-items: center;
		gap: 8px;
		width: 100%;
		text-align: left;
		padding: 6px 12px;
		border: none;
		background: none;
		cursor: pointer;
		font-size: 0.82rem;
		font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', 'Menlo', monospace;
		color: #374151;
	}
	.suggestions li button:hover,
	.suggestions li button.selected {
		background: #f3f4f6;
	}
	.type-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.suggestion-label {
		flex: 1;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.suggestion-detail {
		font-size: 0.72rem;
		color: #9ca3af;
		flex-shrink: 0;
		max-width: 120px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
</style>

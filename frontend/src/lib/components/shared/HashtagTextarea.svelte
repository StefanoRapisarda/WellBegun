<script lang="ts">
	import { type Tag, tagCategoryPrefix } from '$lib/types';
	import { searchTagsStore } from '$lib/stores/tags';

	let { value = $bindable(''), rows = 4, placeholder = '', autoSize = false }: {
		value: string;
		rows?: number;
		placeholder?: string;
		autoSize?: boolean;
	} = $props();

	let textareaEl: HTMLTextAreaElement | undefined = $state();
	let suggestions = $state<Tag[]>([]);
	let showDropdown = $state(false);
	let dropdownTop = $state(0);
	let dropdownLeft = $state(0);
	let hashStart = $state(-1);

	function getHashtagQuery(): string | null {
		if (!textareaEl) return null;
		const pos = textareaEl.selectionStart;
		const text = value.slice(0, pos);
		const lastHash = text.lastIndexOf('#');
		if (lastHash === -1) return null;
		// Must be at start or preceded by whitespace/newline
		if (lastHash > 0 && !/\s/.test(text[lastHash - 1])) return null;
		const query = text.slice(lastHash + 1);
		// No spaces in tag query
		if (/\s/.test(query)) return null;
		hashStart = lastHash;
		return query;
	}

	function positionDropdown() {
		if (!textareaEl) return;
		// Create a mirror element to measure cursor position
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

		const textBefore = value.slice(0, hashStart);
		mirror.textContent = textBefore;
		const span = document.createElement('span');
		span.textContent = '#';
		mirror.appendChild(span);
		document.body.appendChild(mirror);

		const rect = textareaEl.getBoundingClientRect();
		const spanRect = span.getBoundingClientRect();
		const mirrorRect = mirror.getBoundingClientRect();

		dropdownTop = (spanRect.top - mirrorRect.top) - textareaEl.scrollTop + textareaEl.offsetHeight;
		dropdownLeft = spanRect.left - mirrorRect.left;

		// Clamp to textarea width
		if (dropdownLeft > textareaEl.offsetWidth - 200) {
			dropdownLeft = textareaEl.offsetWidth - 200;
		}
		if (dropdownLeft < 0) dropdownLeft = 0;

		document.body.removeChild(mirror);
	}

	async function handleInput() {
		const query = getHashtagQuery();
		if (query !== null) {
			suggestions = await searchTagsStore(query);
			if (suggestions.length > 0) {
				positionDropdown();
				showDropdown = true;
			} else {
				showDropdown = false;
			}
		} else {
			showDropdown = false;
			suggestions = [];
		}
	}

	function selectTag(tag: Tag) {
		if (!textareaEl) return;
		const pos = textareaEl.selectionStart;
		const before = value.slice(0, hashStart);
		const after = value.slice(pos);
		const insertion = `#${tag.name} `;
		value = before + insertion + after;
		showDropdown = false;
		suggestions = [];
		// Restore cursor position after the inserted tag
		const newPos = hashStart + insertion.length;
		requestAnimationFrame(() => {
			textareaEl?.focus();
			textareaEl?.setSelectionRange(newPos, newPos);
		});
	}

	function handleKeydown(e: KeyboardEvent) {
		if (!showDropdown) return;
		if (e.key === 'Escape') {
			showDropdown = false;
			e.preventDefault();
		}
	}

	function handleBlur() {
		setTimeout(() => { showDropdown = false; }, 200);
	}

	function resizeTextarea() {
		if (!autoSize || !textareaEl) return;
		const maxH = window.innerHeight * 0.45;
		textareaEl.style.height = 'auto';
		textareaEl.style.height = Math.min(textareaEl.scrollHeight, maxH) + 'px';
	}

	$effect(() => {
		if (autoSize && textareaEl) {
			// Track value changes to trigger resize
			void value;
			resizeTextarea();
		}
	});
</script>

<div class="hashtag-textarea-wrapper">
	<textarea
		bind:this={textareaEl}
		bind:value
		{rows}
		{placeholder}
		oninput={() => { handleInput(); resizeTextarea(); }}
		onkeydown={handleKeydown}
		onblur={handleBlur}
		class="hashtag-textarea"
		style={autoSize ? 'overflow-y: auto;' : ''}
	></textarea>
	{#if showDropdown}
		<ul class="suggestions" style="top: {dropdownTop}px; left: {dropdownLeft}px;">
			{#each suggestions as tag (tag.id)}
				<li>
					<button onmousedown={(e: MouseEvent) => { e.preventDefault(); selectTag(tag); }}>
						<span class="tag-category">{tagCategoryPrefix(tag)}</span>
						{tag.name}
					</button>
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.hashtag-textarea-wrapper {
		position: relative;
	}
	.hashtag-textarea {
		width: 100%;
		padding: 8px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 0.875rem;
		box-sizing: border-box;
		resize: vertical;
		font-family: inherit;
	}
	.suggestions {
		position: absolute;
		background: white;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		list-style: none;
		padding: 0;
		margin: 2px 0 0;
		max-height: 180px;
		min-width: 200px;
		overflow-y: auto;
		z-index: 200;
		box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
	}
	.suggestions li button {
		display: block;
		width: 100%;
		text-align: left;
		padding: 6px 10px;
		border: none;
		background: none;
		cursor: pointer;
		font-size: 0.85rem;
	}
	.suggestions li button:hover {
		background: #f3f4f6;
	}
	.tag-category {
		display: inline-block;
		font-size: 0.7rem;
		color: #9ca3af;
		margin-right: 4px;
		text-transform: uppercase;
	}
</style>

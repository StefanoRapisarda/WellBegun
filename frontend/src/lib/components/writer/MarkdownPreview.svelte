<script lang="ts">
	import { onMount, onDestroy } from 'svelte';

	let { content, editable = false, onEdit }: {
		content: string;
		editable?: boolean;
		onEdit?: (newContent: string) => void;
	} = $props();

	let previewRef = $state<HTMLElement | null>(null);
	let isEditing = $state(false);
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;
	let lastSyncedContent = $state('');

	// ── Selection containment ──
	// Prevent drag-selection from escaping the contenteditable and selecting the page.
	// Uses a requestAnimationFrame polling loop during drag for reliable timing —
	// selectionchange events can fire before the browser finalises its update.
	let selGuardActive = false;
	let lastMouseX = 0;
	let lastMouseY = 0;
	let rafId: number | null = null;

	function startSelectionGuard() {
		if (!editable) return;
		selGuardActive = true;
		document.addEventListener('mousemove', trackMouseForGuard, true);
		document.addEventListener('mouseup', stopSelectionGuard, { once: true });
		pollSelection();
	}

	function trackMouseForGuard(e: MouseEvent) {
		lastMouseX = e.clientX;
		lastMouseY = e.clientY;
	}

	function pollSelection() {
		if (!selGuardActive) return;
		clampSelection();
		rafId = requestAnimationFrame(pollSelection);
	}

	function stopSelectionGuard() {
		selGuardActive = false;
		document.removeEventListener('mousemove', trackMouseForGuard, true);
		if (rafId !== null) {
			cancelAnimationFrame(rafId);
			rafId = null;
		}
		// One final clamp after the browser finishes mouseup processing
		requestAnimationFrame(clampSelection);
	}

	function clampSelection() {
		if (!previewRef) return;
		const sel = window.getSelection();
		if (!sel || sel.rangeCount === 0 || !sel.anchorNode) return;
		// Only act when the selection started inside our element
		if (!previewRef.contains(sel.anchorNode)) return;

		// If focus is on a text node inside our element, everything is fine
		if (
			sel.focusNode &&
			sel.focusNode.nodeType === Node.TEXT_NODE &&
			previewRef.contains(sel.focusNode)
		) return;

		// Focus is either:
		//  - escaped outside the contenteditable
		//  - on the root <article> element (browser couldn't find a text node)
		//  - on a block-level element (e.g. <p>) instead of a text node
		const focusEscaped = !sel.focusNode || !previewRef.contains(sel.focusNode);

		let target: Text | null = null;
		let offset = 0;

		if (!focusEscaped && sel.focusNode) {
			// Focus is on an element node inside our tree — resolve to text node
			// within the appropriate block.
			let block: Node | null = sel.focusNode;
			if (sel.focusNode === previewRef) {
				// Root — use focusOffset (child index) to pick the block
				const idx = Math.min(sel.focusOffset, previewRef.childNodes.length - 1);
				block = previewRef.childNodes[idx] || previewRef.lastChild;
			}
			if (block) {
				const scope = block.nodeType === Node.ELEMENT_NODE ? block : previewRef;
				const walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT);
				while (walker.nextNode()) target = walker.currentNode as Text;
				if (target) offset = target.length;
			}
		} else {
			// Focus escaped outside — use mouse position to resolve
			const walker = document.createTreeWalker(previewRef, NodeFilter.SHOW_TEXT);
			const rect = previewRef.getBoundingClientRect();
			if (lastMouseY >= rect.bottom) {
				while (walker.nextNode()) target = walker.currentNode as Text;
				if (target) offset = target.length;
			} else if (lastMouseY <= rect.top) {
				target = walker.nextNode() as Text | null;
				offset = 0;
			} else {
				const clampedX = Math.max(rect.left + 1, Math.min(lastMouseX, rect.right - 1));
				const caretRange = document.caretRangeFromPoint?.(clampedX, lastMouseY);
				if (caretRange && previewRef.contains(caretRange.startContainer)) {
					target = caretRange.startContainer as Text;
					offset = caretRange.startOffset;
				} else {
					while (walker.nextNode()) target = walker.currentNode as Text;
					if (target) offset = target.length;
				}
			}
		}

		if (target) {
			// Use removeAllRanges + addRange for maximum reliability
			const anchorNode = sel.anchorNode!;
			const anchorOffset = sel.anchorOffset;
			try {
				sel.removeAllRanges();
				const r = document.createRange();
				// Determine correct range direction
				const cmp = anchorNode.compareDocumentPosition(target);
				const anchorIsAfter = cmp & Node.DOCUMENT_POSITION_PRECEDING;
				if (anchorIsAfter) {
					r.setStart(target, offset);
					r.setEnd(anchorNode, anchorOffset);
				} else {
					r.setStart(anchorNode, anchorOffset);
					r.setEnd(target, offset);
				}
				sel.addRange(r);
			} catch {
				// Last resort: try extend
				try { sel.extend(target, offset); } catch { /* give up */ }
			}
		}
	}

	// Inject invisible zero-width spaces at the end of every block element.
	// Without these, when the caret reaches the last character of a <p>,
	// the browser resolves focusNode to the <article> root, which makes
	// the entire document appear selected.  The ZWS gives the browser a
	// text node to land on *inside* the block.
	function ensureSelectionAnchors() {
		if (!previewRef || !editable) return;
		for (const block of previewRef.querySelectorAll('p, li, h1, h2, h3, blockquote')) {
			const last = block.lastChild;
			if (!last) {
				block.appendChild(document.createTextNode('\u200B'));
			} else if (last.nodeType === Node.TEXT_NODE) {
				if (!last.textContent?.endsWith('\u200B')) {
					last.textContent += '\u200B';
				}
			} else {
				block.appendChild(document.createTextNode('\u200B'));
			}
		}
	}

	onDestroy(() => {
		// Defensive cleanup
		document.removeEventListener('mousemove', trackMouseForGuard, true);
		document.removeEventListener('mouseup', stopSelectionGuard);
		if (rafId !== null) cancelAnimationFrame(rafId);
	});

	// Initialize and update innerHTML when content changes externally (not while editing)
	$effect(() => {
		if (!isEditing && previewRef) {
			// Only re-render if content changed from outside (not our own edits)
			if (content !== lastSyncedContent) {
				previewRef.innerHTML = parseMarkdown(content);
				lastSyncedContent = content;
				ensureSelectionAnchors();
			}
		}
	});

	// Convert HTML back to markdown (simplified)
	function htmlToMarkdown(html: string): string {
		let md = html
			// Strip zero-width spaces used as selection anchors
			.replace(/\u200B/g, '')
			// Handle divs and paragraphs as line breaks
			.replace(/<\/div><div>/gi, '\n')
			.replace(/<div>/gi, '\n')
			.replace(/<\/div>/gi, '')
			.replace(/<\/p><p>/gi, '\n\n')
			.replace(/<p>/gi, '')
			.replace(/<\/p>/gi, '')
			// Headers
			.replace(/<h1[^>]*>(.*?)<\/h1>/gi, '# $1\n')
			.replace(/<h2[^>]*>(.*?)<\/h2>/gi, '## $1\n')
			.replace(/<h3[^>]*>(.*?)<\/h3>/gi, '### $1\n')
			// Bold and italic
			.replace(/<strong><em>(.*?)<\/em><\/strong>/gi, '***$1***')
			.replace(/<em><strong>(.*?)<\/strong><\/em>/gi, '***$1***')
			.replace(/<strong>(.*?)<\/strong>/gi, '**$1**')
			.replace(/<b>(.*?)<\/b>/gi, '**$1**')
			.replace(/<em>(.*?)<\/em>/gi, '*$1*')
			.replace(/<i>(.*?)<\/i>/gi, '*$1*')
			// Strikethrough
			.replace(/<del>(.*?)<\/del>/gi, '~~$1~~')
			.replace(/<s>(.*?)<\/s>/gi, '~~$1~~')
			// Code
			.replace(/<pre><code[^>]*>([\s\S]*?)<\/code><\/pre>/gi, '```\n$1\n```')
			.replace(/<code>(.*?)<\/code>/gi, '`$1`')
			// Blockquotes
			.replace(/<blockquote>(.*?)<\/blockquote>/gi, '> $1\n')
			// Links
			.replace(/<a[^>]*href="([^"]*)"[^>]*>(.*?)<\/a>/gi, '[$2]($1)')
			// Lists
			.replace(/<li>(.*?)<\/li>/gi, '- $1\n')
			.replace(/<\/?ul>/gi, '\n')
			.replace(/<\/?ol>/gi, '\n')
			// Horizontal rule
			.replace(/<hr\s*\/?>/gi, '\n---\n')
			// Line breaks
			.replace(/<br\s*\/?>/gi, '\n')
			// Clean up remaining tags
			.replace(/<[^>]+>/g, '')
			// Decode HTML entities
			.replace(/&amp;/g, '&')
			.replace(/&lt;/g, '<')
			.replace(/&gt;/g, '>')
			.replace(/&nbsp;/g, ' ')
			.replace(/&quot;/g, '"')
			// Clean up extra whitespace
			.replace(/\n{3,}/g, '\n\n')
			.trim();

		return md;
	}

	function handleInput() {
		if (!previewRef || !onEdit) return;

		isEditing = true;

		// Debounce: only sync after user stops typing for 500ms
		if (debounceTimer) clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => {
			syncContent();
		}, 500);
	}

	function handleFocus() {
		isEditing = true;
		ensureSelectionAnchors();
	}

	function handleBlur() {
		// Sync immediately on blur
		if (debounceTimer) clearTimeout(debounceTimer);
		syncContent();
		isEditing = false;
	}

	function syncContent() {
		if (previewRef && onEdit) {
			const newMarkdown = htmlToMarkdown(previewRef.innerHTML);
			lastSyncedContent = newMarkdown;
			onEdit(newMarkdown);
		}
	}

	// Simple markdown to HTML conversion
	function parseMarkdown(md: string): string {
		let html = md
			// Escape HTML
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			// Headers
			.replace(/^### (.+)$/gm, '<h3>$1</h3>')
			.replace(/^## (.+)$/gm, '<h2>$1</h2>')
			.replace(/^# (.+)$/gm, '<h1>$1</h1>')
			// Bold and italic
			.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
			.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
			.replace(/\*(.+?)\*/g, '<em>$1</em>')
			.replace(/___(.+?)___/g, '<strong><em>$1</em></strong>')
			.replace(/__(.+?)__/g, '<strong>$1</strong>')
			.replace(/_(.+?)_/g, '<em>$1</em>')
			// Strikethrough
			.replace(/~~(.+?)~~/g, '<del>$1</del>')
			// Code blocks
			.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
			// Inline code
			.replace(/`(.+?)`/g, '<code>$1</code>')
			// Blockquotes
			.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>')
			// Horizontal rule
			.replace(/^---$/gm, '<hr>')
			.replace(/^\*\*\*$/gm, '<hr>')
			// Links
			.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
			// References (custom syntax)
			.replace(/\[\[(\w+):(\d+)\]\]/g, '<span class="reference" data-type="$1" data-id="$2">[$1:$2]</span>')
			// Unordered lists
			.replace(/^[\-\*] (.+)$/gm, '<li>$1</li>')
			// Ordered lists
			.replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
			// Paragraphs
			.replace(/\n\n/g, '</p><p>')
			// Line breaks
			.replace(/\n/g, '<br>');

		// Wrap in paragraph
		html = '<p>' + html + '</p>';

		// Fix consecutive list items
		html = html.replace(/(<li>.*?<\/li>)(<br>)?(<li>)/g, '$1$3');
		html = html.replace(/(<\/p><p>)?(<li>)/g, '<ul>$2');
		html = html.replace(/(<\/li>)(<\/p><p>|<br>|$)/g, '$1</ul>$2');

		// Fix consecutive blockquotes
		html = html.replace(/(<\/blockquote>)<br>(<blockquote>)/g, '$1$2');

		// Clean up empty paragraphs
		html = html.replace(/<p><\/p>/g, '');
		html = html.replace(/<p>(<h[123]>)/g, '$1');
		html = html.replace(/(<\/h[123]>)<\/p>/g, '$1');
		html = html.replace(/<p>(<pre>)/g, '$1');
		html = html.replace(/(<\/pre>)<\/p>/g, '$1');
		html = html.replace(/<p>(<hr>)<\/p>/g, '$1');
		html = html.replace(/<p>(<ul>)/g, '$1');
		html = html.replace(/(<\/ul>)<\/p>/g, '$1');
		html = html.replace(/<p>(<blockquote>)/g, '$1');
		html = html.replace(/(<\/blockquote>)<\/p>/g, '$1');

		return html;
	}

	// Only compute renderedHtml for non-editable (read-only) usage.
	// In editable mode the $effect above is the sole owner of innerHTML,
	// preventing Svelte's {#html} from replacing the DOM mid-edit and
	// destroying the user's active selection / ZWS anchors.
	let renderedHtml = $derived(!editable ? parseMarkdown(content) : '');
</script>

<article
	class="markdown-preview"
	class:editable
	bind:this={previewRef}
	contenteditable={editable}
	oninput={handleInput}
	onfocus={handleFocus}
	onblur={handleBlur}
	onmousedown={editable ? startSelectionGuard : undefined}
	role={editable ? "textbox" : undefined}
	aria-multiline={editable ? "true" : undefined}
>
	{#if !editable}
		{@html renderedHtml}
	{/if}
</article>

<style>
	.markdown-preview {
		font-family: 'Georgia', 'Times New Roman', serif;
		font-size: 1.15rem;
		line-height: 1.8;
		color: #1f2937;
		outline: none;
		min-height: 100%;
	}
	.markdown-preview.editable {
		cursor: text;
		user-select: text;
		-webkit-user-select: text;
	}
	.markdown-preview.editable:focus {
		outline: none;
	}

	.markdown-preview :global(h1) {
		font-size: 2rem;
		font-weight: 700;
		margin: 1.5em 0 0.5em;
		color: #111827;
		border-bottom: 1px solid #e5e7eb;
		padding-bottom: 0.3em;
	}
	.markdown-preview :global(h2) {
		font-size: 1.5rem;
		font-weight: 600;
		margin: 1.25em 0 0.5em;
		color: #111827;
	}
	.markdown-preview :global(h3) {
		font-size: 1.2rem;
		font-weight: 600;
		margin: 1em 0 0.5em;
		color: #374151;
	}

	.markdown-preview :global(p) {
		margin: 0;
		padding-bottom: 1em;
	}

	.markdown-preview :global(strong) {
		font-weight: 600;
		color: #111827;
	}

	.markdown-preview :global(em) {
		font-style: italic;
	}

	.markdown-preview :global(del) {
		text-decoration: line-through;
		color: #9ca3af;
	}

	.markdown-preview :global(code) {
		background: #f3f4f6;
		padding: 2px 6px;
		border-radius: 4px;
		font-size: 0.9em;
		color: #dc2626;
	}

	.markdown-preview :global(pre) {
		background: #1f2937;
		color: #e5e7eb;
		padding: 16px 20px;
		border-radius: 8px;
		overflow-x: auto;
		margin: 1em 0;
	}
	.markdown-preview :global(pre code) {
		background: none;
		padding: 0;
		color: inherit;
		font-size: 0.85rem;
	}

	.markdown-preview :global(blockquote) {
		border-left: 3px solid #d1d5db;
		margin: 1em 0;
		padding: 0.5em 0 0.5em 1em;
		color: #6b7280;
		font-style: italic;
	}

	.markdown-preview :global(hr) {
		border: none;
		border-top: 1px solid #e5e7eb;
		margin: 2em 0;
	}

	.markdown-preview :global(a) {
		color: #3b82f6;
		text-decoration: none;
	}
	.markdown-preview :global(a:hover) {
		text-decoration: underline;
	}

	.markdown-preview :global(ul),
	.markdown-preview :global(ol) {
		margin: 1em 0;
		padding-left: 1.5em;
	}
	.markdown-preview :global(li) {
		margin: 0.25em 0;
	}

	.markdown-preview :global(.reference) {
		background: #eff6ff;
		color: #1d4ed8;
		padding: 2px 6px;
		border-radius: 4px;
		font-size: 0.85em;
		cursor: pointer;
	}
	.markdown-preview :global(.reference:hover) {
		background: #dbeafe;
	}
</style>

<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import type { PDFDocumentProxy, PDFPageProxy } from 'pdfjs-dist';

	let {
		pdfDocument,
		pageNumber,
		scale
	}: {
		pdfDocument: PDFDocumentProxy;
		pageNumber: number;
		scale: number;
	} = $props();

	let canvasEl: HTMLCanvasElement | undefined = $state();
	let textLayerEl: HTMLDivElement | undefined = $state();
	let containerEl: HTMLDivElement | undefined = $state();
	let pageWidth = $state(0);
	let pageHeight = $state(0);
	let currentPage: PDFPageProxy | null = null;
	let rendering = false;
	let endOfContentDiv: HTMLDivElement | null = null;
	let prevRange: Range | null = null;
	let isPointerDown = false;

	async function renderPage() {
		if (!canvasEl || !textLayerEl || rendering) return;
		rendering = true;

		try {
			const page = await pdfDocument.getPage(pageNumber);
			currentPage = page;
			const viewport = page.getViewport({ scale });

			pageWidth = viewport.width;
			pageHeight = viewport.height;

			// Render canvas
			const canvas = canvasEl;
			canvas.width = viewport.width;
			canvas.height = viewport.height;

			await page.render({ canvas, viewport }).promise;

			// Render text layer
			textLayerEl.innerHTML = '';

			const textContent = await page.getTextContent();
			const { TextLayer } = await import('pdfjs-dist');
			const textLayer = new TextLayer({
				textContentSource: textContent,
				container: textLayerEl,
				viewport
			});
			await textLayer.render();

			// Add endOfContent div — official pdf.js technique that acts as a
			// selection barrier to prevent selection from overflowing to other pages.
			endOfContentDiv = document.createElement('div');
			endOfContentDiv.className = 'endOfContent';
			textLayerEl.appendChild(endOfContentDiv);
		} catch (e) {
			console.warn(`Failed to render page ${pageNumber}:`, e);
		} finally {
			rendering = false;
		}
	}

	// Reset endOfContent to its default position at the end of the text layer
	function resetEndOfContent() {
		if (!endOfContentDiv || !textLayerEl) return;
		textLayerEl.appendChild(endOfContentDiv);
		endOfContentDiv.style.width = '';
		endOfContentDiv.style.height = '';
		endOfContentDiv.style.userSelect = '';
		textLayerEl.classList.remove('selecting');
	}

	function handleMouseDown() {
		textLayerEl?.classList.add('selecting');
	}

	function handlePointerDown() {
		isPointerDown = true;
	}

	function handlePointerUp() {
		isPointerDown = false;
		resetEndOfContent();
		prevRange = null;
	}

	function handleWindowBlur() {
		isPointerDown = false;
		resetEndOfContent();
		prevRange = null;
	}

	function handleKeyUp() {
		if (!isPointerDown) {
			resetEndOfContent();
			prevRange = null;
		}
	}

	// Reposition endOfContent adjacent to the selection anchor on each
	// selectionchange — this is the core of the official pdf.js technique that
	// prevents selection overflow at paragraph boundaries.
	function handleSelectionChange() {
		const sel = document.getSelection();
		if (!sel || sel.rangeCount === 0 || !textLayerEl || !endOfContentDiv) {
			resetEndOfContent();
			return;
		}

		const range = sel.getRangeAt(0);
		if (!range.intersectsNode(textLayerEl)) {
			resetEndOfContent();
			return;
		}

		textLayerEl.classList.add('selecting');

		// Determine which end of the selection the user is actively dragging:
		// compare with previous range to detect if the start or end moved.
		const modifyStart =
			prevRange &&
			(range.compareBoundaryPoints(Range.END_TO_END, prevRange) === 0 ||
				range.compareBoundaryPoints(Range.START_TO_END, prevRange) === 0);

		let anchor: Node = modifyStart ? range.startContainer : range.endContainer;
		if (anchor.nodeType === Node.TEXT_NODE) {
			anchor = anchor.parentNode!;
		}

		// When endOffset is 0 the selection ends at the very start of an element,
		// so walk back to the previous sibling to find the real anchor.
		if (!modifyStart && range.endOffset === 0) {
			try {
				let node = anchor;
				while (!node.previousSibling) {
					node = node.parentNode!;
				}
				node = node.previousSibling;
				while (node.childNodes.length) {
					node = node.lastChild!;
				}
				anchor = node.parentNode ?? anchor;
			} catch {
				// Walk failed — keep current anchor
			}
		}

		const parentTextLayer = (anchor as Element).closest?.('.textLayer') ??
			(anchor as Element).parentElement?.closest('.textLayer');
		if (parentTextLayer !== textLayerEl) {
			prevRange = range.cloneRange();
			return;
		}

		// Move endOfContent right next to the anchor element and make it
		// selectable so the browser's selection flows into it instead of
		// jumping to distant text on other pages.
		endOfContentDiv.style.width = `${pageWidth}px`;
		endOfContentDiv.style.height = `${pageHeight}px`;
		endOfContentDiv.style.userSelect = 'text';
		const anchorEl = anchor as Element;
		anchorEl.parentElement?.insertBefore(
			endOfContentDiv,
			modifyStart ? anchorEl : anchorEl.nextSibling
		);

		prevRange = range.cloneRange();
	}

	onMount(() => {
		renderPage();
		document.addEventListener('pointerdown', handlePointerDown);
		document.addEventListener('pointerup', handlePointerUp);
		document.addEventListener('selectionchange', handleSelectionChange);
		document.addEventListener('keyup', handleKeyUp);
		window.addEventListener('blur', handleWindowBlur);
	});

	onDestroy(() => {
		document.removeEventListener('pointerdown', handlePointerDown);
		document.removeEventListener('pointerup', handlePointerUp);
		document.removeEventListener('selectionchange', handleSelectionChange);
		document.removeEventListener('keyup', handleKeyUp);
		window.removeEventListener('blur', handleWindowBlur);
	});

	// Re-render when scale changes
	$effect(() => {
		const _s = scale;
		if (canvasEl && textLayerEl) {
			renderPage();
		}
	});
</script>

<div
	bind:this={containerEl}
	class="pdf-page"
	style:width="{pageWidth}px"
	style:height="{pageHeight}px"
	data-page={pageNumber}
>
	<canvas bind:this={canvasEl}></canvas>
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div bind:this={textLayerEl} class="textLayer" onmousedown={handleMouseDown}></div>
</div>

<style>
	.pdf-page {
		position: relative;
		background: white;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
	}
	canvas {
		display: block;
	}

	/* pdfjs-dist 5.x textLayer CSS — matches official pdf_viewer.css */
	:global(.textLayer) {
		position: absolute;
		inset: 0;
		overflow: clip;
		opacity: 1;
		line-height: 1;
		text-size-adjust: none;
		forced-color-adjust: none;
		transform-origin: 0 0;
		z-index: 0;
		color-scheme: only light;

		--min-font-size: 1;
		--text-scale-factor: calc(var(--total-scale-factor) * var(--min-font-size));
		--min-font-size-inv: calc(1 / var(--min-font-size));
	}

	:global(.textLayer :is(span, br)) {
		color: transparent;
		position: absolute;
		white-space: pre;
		cursor: text;
		transform-origin: 0% 0%;
	}

	:global(.textLayer > :not(.markedContent)),
	:global(.textLayer .markedContent span:not(.markedContent)) {
		z-index: 1;
		--font-height: 0;
		font-size: calc(var(--text-scale-factor) * var(--font-height));
		--scale-x: 1;
		--rotate: 0deg;
		transform: rotate(var(--rotate)) scaleX(var(--scale-x)) scale(var(--min-font-size-inv));
	}

	:global(.textLayer .markedContent) {
		display: contents;
	}

	:global(.textLayer span[role='img']) {
		-webkit-user-select: none;
		-moz-user-select: none;
		user-select: none;
	}

	:global(.textLayer ::selection) {
		background: rgba(0, 0, 255, 0.25);
	}

	:global(.textLayer br::selection) {
		background: transparent;
	}

	/* endOfContent: catches mouse events in gaps between text spans during selection.
	   Normally hidden below the text layer (top: 100%).
	   When active (mousedown), expands to cover the full page to stabilize selection. */
	:global(.textLayer .endOfContent) {
		display: block;
		position: absolute;
		inset: 100% 0 0;
		z-index: 0;
		cursor: default;
		-webkit-user-select: none;
		-moz-user-select: none;
		user-select: none;
	}

	:global(.textLayer.selecting .endOfContent) {
		top: 0;
	}

</style>

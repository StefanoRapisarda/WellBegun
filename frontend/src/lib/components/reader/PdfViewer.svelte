<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { getPdfjsLib } from './pdfWorkerSetup';
	import type { PDFDocumentProxy } from 'pdfjs-dist';
	import PdfPage from './PdfPage.svelte';

	let {
		pdfUrl,
		scale,
		onPageChange,
		onTotalPages,
		onTitleExtracted
	}: {
		pdfUrl: string;
		scale: number;
		onPageChange?: (page: number) => void;
		onTotalPages?: (count: number) => void;
		onTitleExtracted?: (title: string) => void;
	} = $props();

	let pdfDocument = $state<PDFDocumentProxy | null>(null);
	let totalPages = $state(0);
	let scrollContainer: HTMLDivElement | undefined = $state();
	let observer: IntersectionObserver | null = null;
	let visiblePages = new Map<number, boolean>();

	// ── Selection frame state ──
	let selectionBox = $state<{ x: number; y: number; w: number; h: number } | null>(null);

	async function loadDocument() {
		try {
			const pdfjsLib = await getPdfjsLib();
			const doc = await pdfjsLib.getDocument({
				url: pdfUrl,
				cMapUrl: '/cmaps/',
				cMapPacked: true,
				standardFontDataUrl: '/standard_fonts/'
			}).promise;
			pdfDocument = doc;
			totalPages = doc.numPages;
			onTotalPages?.(doc.numPages);

			try {
				const metadata = await doc.getMetadata();
				const info = metadata?.info as Record<string, unknown> | undefined;
				const pdfTitle = info?.Title as string | undefined;
				if (pdfTitle && pdfTitle.trim()) {
					onTitleExtracted?.(pdfTitle.trim());
				}
			} catch {
				// Metadata extraction is optional
			}
		} catch (e) {
			console.error('Failed to load PDF:', e);
		}
	}

	function setupIntersectionObserver() {
		if (!scrollContainer) return;

		observer = new IntersectionObserver(
			(entries) => {
				for (const entry of entries) {
					const pageEl = entry.target as HTMLElement;
					const pageNum = parseInt(pageEl.dataset.pageRow || '0', 10);
					if (pageNum > 0) {
						if (entry.isIntersecting) {
							visiblePages.set(pageNum, true);
						} else {
							visiblePages.delete(pageNum);
						}
					}
				}
				if (visiblePages.size > 0) {
					const lowest = Math.min(...visiblePages.keys());
					onPageChange?.(lowest);
				}
			},
			{
				root: scrollContainer,
				threshold: 0.3
			}
		);
	}

	function observePages() {
		if (!observer || !scrollContainer) return;
		const pageElements = scrollContainer.querySelectorAll('[data-page-row]');
		pageElements.forEach((el) => observer!.observe(el));
	}

	onMount(() => {
		loadDocument();
		setupIntersectionObserver();
		document.addEventListener('selectionchange', handleSelectionChange);
	});

	$effect(() => {
		if (totalPages > 0 && scrollContainer) {
			requestAnimationFrame(() => observePages());
		}
	});

	// ── Selection frame: dotted border around selected text ──
	function handleSelectionChange() {
		const sel = window.getSelection();
		if (!sel || sel.isCollapsed || !scrollContainer) {
			selectionBox = null;
			return;
		}

		const range = sel.getRangeAt(0);
		if (!scrollContainer.contains(range.commonAncestorContainer)) {
			selectionBox = null;
			return;
		}

		const rawRects = Array.from(range.getClientRects());
		if (rawRects.length === 0) {
			selectionBox = null;
			return;
		}

		// Filter out tiny/degenerate rects and outliers that PDF.js can produce
		// with complex fonts (e.g. CID TrueType Identity-H)
		const valid = rawRects.filter((r) => r.width > 1 && r.height > 1);
		if (valid.length === 0) {
			selectionBox = null;
			return;
		}

		// Compute median Y center to filter rects that are wildly far from the selection
		const yCenters = valid.map((r) => r.top + r.height / 2).sort((a, b) => a - b);
		const medianY = yCenters[Math.floor(yCenters.length / 2)];

		// Keep rects within a generous vertical band around the selection
		// (allows multi-line but rejects rects that jumped to different pages)
		const maxSpread = Math.max(
			200,
			(yCenters[yCenters.length - 1] - yCenters[0]) * 1.2
		);
		const filtered = valid.filter((r) => {
			const cy = r.top + r.height / 2;
			return Math.abs(cy - medianY) <= maxSpread;
		});

		if (filtered.length === 0) {
			selectionBox = null;
			return;
		}

		const containerRect = scrollContainer.getBoundingClientRect();
		let minX = Infinity,
			minY = Infinity,
			maxX = -Infinity,
			maxY = -Infinity;
		for (const r of filtered) {
			minX = Math.min(minX, r.left);
			minY = Math.min(minY, r.top);
			maxX = Math.max(maxX, r.right);
			maxY = Math.max(maxY, r.bottom);
		}

		const pad = 4;
		selectionBox = {
			x: minX - containerRect.left + scrollContainer.scrollLeft - pad,
			y: minY - containerRect.top + scrollContainer.scrollTop - pad,
			w: maxX - minX + 2 * pad,
			h: maxY - minY + 2 * pad
		};
	}

	function handleScroll() {
		if (selectionBox) {
			handleSelectionChange();
		}
	}

	// ── Drag start: set text data + custom drag image ──
	function handleDragStart(e: DragEvent) {
		const selection = window.getSelection();
		const text = selection?.toString().trim();
		if (!text || !e.dataTransfer) return;

		e.dataTransfer.setData('text/plain', text);
		e.dataTransfer.effectAllowed = 'copy';

		// Create a dotted-border ghost as the drag image
		const ghost = document.createElement('div');
		const preview = text.length > 80 ? text.slice(0, 77) + '...' : text;
		ghost.textContent = preview;
		Object.assign(ghost.style, {
			position: 'fixed',
			top: '-1000px',
			left: '-1000px',
			padding: '8px 12px',
			border: '2px dashed #3b82f6',
			borderRadius: '6px',
			background: 'rgba(255, 255, 255, 0.95)',
			fontSize: '0.8rem',
			color: '#374151',
			maxWidth: '220px',
			overflow: 'hidden',
			textOverflow: 'ellipsis',
			whiteSpace: 'nowrap',
			fontFamily: 'system-ui, sans-serif',
			boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
			pointerEvents: 'none'
		});
		document.body.appendChild(ghost);
		e.dataTransfer.setDragImage(ghost, ghost.offsetWidth / 2, ghost.offsetHeight / 2);

		setTimeout(() => ghost.remove(), 0);
	}

	onDestroy(() => {
		observer?.disconnect();
		pdfDocument?.destroy();
		document.removeEventListener('selectionchange', handleSelectionChange);
	});
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	bind:this={scrollContainer}
	class="pdf-scroll-container"
	ondragstart={handleDragStart}
	onscroll={handleScroll}
>
	{#if pdfDocument}
		{#each Array(totalPages) as _, i}
			{@const pageNum = i + 1}
			<div class="page-row" data-page-row={pageNum}>
				<PdfPage {pdfDocument} pageNumber={pageNum} {scale} />
			</div>
		{/each}
	{:else}
		<div class="loading">Loading PDF...</div>
	{/if}

	{#if selectionBox}
		<div
			class="selection-frame"
			style:left="{selectionBox.x}px"
			style:top="{selectionBox.y}px"
			style:width="{selectionBox.w}px"
			style:height="{selectionBox.h}px"
		></div>
	{/if}
</div>

<style>
	.pdf-scroll-container {
		height: 100%;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 16px;
		padding: 20px 0;
		background: #e5e7eb;
		position: relative;
	}
	.page-row {
		display: flex;
		align-items: flex-start;
		flex-shrink: 0;
	}
	.loading {
		padding: 40px;
		color: #6b7280;
		font-size: 0.9rem;
	}
	.selection-frame {
		position: absolute;
		border: 2px dashed #3b82f6;
		border-radius: 3px;
		pointer-events: none;
		z-index: 10;
		background: rgba(59, 130, 246, 0.04);
	}
</style>

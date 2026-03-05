import { toPng } from 'html-to-image';

interface NodeRect {
	x: number;
	y: number;
	w: number;
	h: number;
}

export interface ScreenshotMeta {
	title?: string;
	description?: string;
}

const PADDING = 40;
const HEADER_PAD = 24;
const FONT_FAMILY = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';

export async function captureGraphScreenshot(
	canvasEl: HTMLDivElement,
	nodes: NodeRect[],
	filename: string,
	meta?: ScreenshotMeta
): Promise<void> {
	if (nodes.length === 0) return;

	// Compute bounding box of all nodes
	let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
	for (const n of nodes) {
		minX = Math.min(minX, n.x);
		minY = Math.min(minY, n.y);
		maxX = Math.max(maxX, n.x + n.w);
		maxY = Math.max(maxY, n.y + n.h);
	}

	minX -= PADDING;
	minY -= PADDING;
	const graphW = maxX - minX + PADDING;
	const graphH = maxY - minY + PADDING;

	// Capture graph using style overrides on the clone — no DOM mutation, no glitch
	const graphDataUrl = await toPng(canvasEl, {
		width: graphW,
		height: graphH,
		pixelRatio: window.devicePixelRatio || 2,
		backgroundColor: '#ffffff',
		style: {
			transform: `translate(${-minX}px, ${-minY}px)`,
			width: `${graphW}px`,
			height: `${graphH}px`
		}
	});

	// No metadata → download the graph image directly
	if (!meta?.title) {
		triggerDownload(graphDataUrl, filename);
		return;
	}

	// Compose header + graph onto an HTML5 Canvas
	const pr = window.devicePixelRatio || 2;
	const graphImg = await loadImage(graphDataUrl);

	const headerH = measureHeaderHeight(meta);
	const totalW = graphImg.width;
	const totalH = graphImg.height + headerH * pr;

	const canvas = document.createElement('canvas');
	canvas.width = totalW;
	canvas.height = totalH;
	const ctx = canvas.getContext('2d')!;

	// White background
	ctx.fillStyle = '#ffffff';
	ctx.fillRect(0, 0, totalW, totalH);

	// Draw header text
	drawHeader(ctx, meta, pr);

	// Draw graph below header
	ctx.drawImage(graphImg, 0, headerH * pr);

	triggerDownload(canvas.toDataURL('image/png'), filename);
}

function measureHeaderHeight(meta: ScreenshotMeta): number {
	let h = HEADER_PAD;
	if (meta.title) h += 22;
	if (meta.description) h += 16;
	h += 14; // date line
	h += HEADER_PAD;
	return h;
}

function drawHeader(ctx: CanvasRenderingContext2D, meta: ScreenshotMeta, pr: number) {
	const x = HEADER_PAD * pr;
	let y = HEADER_PAD * pr;

	// Title
	if (meta.title) {
		ctx.font = `600 ${14 * pr}px ${FONT_FAMILY}`;
		ctx.fillStyle = '#374151';
		ctx.fillText(meta.title, x, y + 14 * pr);
		y += 22 * pr;
	}

	// Description
	if (meta.description) {
		ctx.font = `400 ${11 * pr}px ${FONT_FAMILY}`;
		ctx.fillStyle = '#6b7280';
		ctx.fillText(meta.description, x, y + 11 * pr);
		y += 16 * pr;
	}

	// Date
	const date = new Date().toLocaleDateString(undefined, {
		year: 'numeric', month: 'long', day: 'numeric',
		hour: '2-digit', minute: '2-digit'
	});
	ctx.font = `400 ${10 * pr}px ${FONT_FAMILY}`;
	ctx.fillStyle = '#9ca3af';
	ctx.fillText(date, x, y + 10 * pr);
}

function loadImage(dataUrl: string): Promise<HTMLImageElement> {
	return new Promise((resolve, reject) => {
		const img = new Image();
		img.onload = () => resolve(img);
		img.onerror = reject;
		img.src = dataUrl;
	});
}

function triggerDownload(dataUrl: string, filename: string) {
	const link = document.createElement('a');
	link.download = `${filename}.png`;
	link.href = dataUrl;
	link.click();
}

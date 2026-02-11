import type * as PdfjsLib from 'pdfjs-dist';

let _pdfjsLib: typeof PdfjsLib | null = null;

/**
 * Lazily loads pdfjs-dist on the client side only.
 * Must be called from onMount or another browser-only context.
 */
export async function getPdfjsLib(): Promise<typeof PdfjsLib> {
	if (_pdfjsLib) return _pdfjsLib;

	const pdfjsLib = await import('pdfjs-dist');

	pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
		'pdfjs-dist/build/pdf.worker.mjs',
		import.meta.url
	).toString();

	_pdfjsLib = pdfjsLib;
	return pdfjsLib;
}

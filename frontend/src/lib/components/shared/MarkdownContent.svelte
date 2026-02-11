<script lang="ts">
	import { marked } from 'marked';

	let { text = '' }: { text: string } = $props();

	let rendered = $derived(marked.parse(text, { async: false }) as string);
</script>

<div class="rendered-content typewriter">
	{@html rendered}
</div>

<style>
	.rendered-content.typewriter {
		font-family: 'American Typewriter', 'Courier New', 'Courier', monospace;
		font-size: 0.85rem;
		line-height: 1.6;
		color: #1f2937;
		padding: 8px 0;
	}
	/* Markdown element styles */
	.rendered-content :global(h1),
	.rendered-content :global(h2),
	.rendered-content :global(h3),
	.rendered-content :global(h4) {
		font-family: 'American Typewriter', 'Courier New', 'Courier', monospace;
		margin: 0.8em 0 0.4em;
		font-weight: 600;
	}
	.rendered-content :global(h1) { font-size: 1.3em; }
	.rendered-content :global(h2) { font-size: 1.15em; }
	.rendered-content :global(h3) { font-size: 1.05em; }
	.rendered-content :global(p) {
		margin: 0.5em 0;
	}
	.rendered-content :global(ul),
	.rendered-content :global(ol) {
		margin: 0.5em 0;
		padding-left: 1.5em;
	}
	.rendered-content :global(li) {
		margin: 0.25em 0;
	}
	.rendered-content :global(code) {
		font-family: 'SF Mono', 'Monaco', monospace;
		background: #f3f4f6;
		padding: 0.15em 0.4em;
		border-radius: 3px;
		font-size: 0.9em;
	}
	.rendered-content :global(pre) {
		background: #1f2937;
		color: #e5e7eb;
		padding: 12px;
		border-radius: 6px;
		overflow-x: auto;
	}
	.rendered-content :global(pre code) {
		background: none;
		padding: 0;
		color: inherit;
	}
	.rendered-content :global(blockquote) {
		border-left: 3px solid #d1d5db;
		margin: 0.5em 0;
		padding-left: 1em;
		color: #6b7280;
		font-style: italic;
	}
	.rendered-content :global(a) {
		color: #3b82f6;
		text-decoration: underline;
	}
	.rendered-content :global(strong) {
		font-weight: 700;
	}
	.rendered-content :global(em) {
		font-style: italic;
	}
</style>

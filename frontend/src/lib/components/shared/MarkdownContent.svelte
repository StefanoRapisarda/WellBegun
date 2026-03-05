<script lang="ts">
	import { marked } from 'marked';
	import { ENTITY_CONFIG, type NotepadEntityType } from '$lib/notepad/types';

	let { text = '', onEntityClick, onEntityDblClick, selectedEntityKeys }: {
		text: string;
		onEntityClick?: (type: string, id: number) => void;
		onEntityDblClick?: (type: string, id: number) => void;
		selectedEntityKeys?: Set<string>;
	} = $props();

	let containerEl: HTMLDivElement | undefined = $state();

	const ENTITY_ICONS: Record<string, string> = {
		note: '<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',
		project: '<path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/>',
		log: '<path d="M2 3h6a4 4 0 014 4v14a3 3 0 00-3-3H2z"/><path d="M22 3h-6a4 4 0 00-4 4v14a3 3 0 013-3h7z"/>',
		activity: '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
		source: '<path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>',
		actor: '<path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/>',
		plan: '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
		collection: '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="3" x2="9" y2="21"/>',
	};

	const ENTITY_REF_RE = /\[(\w+)#(\d+)\]/g;

	function decorateEntityRefs(html: string, clickable: boolean): string {
		return html.replace(ENTITY_REF_RE, (match, type, id) => {
			const color = ENTITY_CONFIG[type as NotepadEntityType]?.color ?? '#6b7280';
			const iconPath = ENTITY_ICONS[type] ?? '<circle cx="12" cy="12" r="10"/>';
			const label = type.replace('_', ' ');
			const svg = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px;flex-shrink:0">${iconPath}</svg>`;
			if (clickable) {
				return `<button class="entity-ref entity-ref-btn" data-entity-type="${type}" data-entity-id="${id}" style="--ref-color:${color}">${svg}<span class="entity-ref-label">${label}#${id}</span></button>`;
			}
			return `<span class="entity-ref" style="--ref-color:${color}">${svg}<span class="entity-ref-label">${label}#${id}</span></span>`;
		});
	}

	$effect(() => {
		if (!containerEl || !selectedEntityKeys) return;
		const btns = containerEl.querySelectorAll('.entity-ref-btn');
		for (const btn of btns) {
			const el = btn as HTMLElement;
			const key = `${el.dataset.entityType}:${el.dataset.entityId}`;
			el.classList.toggle('selected', selectedEntityKeys.has(key));
		}
	});

	let isInteractive = $derived(!!onEntityClick || !!onEntityDblClick);
	let rendered = $derived(decorateEntityRefs(marked.parse(text, { async: false }) as string, isInteractive));

	function handleContainerClick(e: MouseEvent) {
		const btn = (e.target as HTMLElement).closest('.entity-ref-btn') as HTMLElement | null;
		if (!btn) return;
		const type = btn.dataset.entityType;
		const id = btn.dataset.entityId;
		if (!type || !id) return;
		if (e.detail === 2 && onEntityDblClick) {
			onEntityDblClick(type, Number(id));
		} else if (e.detail === 1 && onEntityClick) {
			onEntityClick(type, Number(id));
		}
	}
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="rendered-content typewriter" bind:this={containerEl} onclick={handleContainerClick}>
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

	/* Entity reference inline badges */
	.rendered-content :global(.entity-ref) {
		display: inline-flex;
		align-items: center;
		gap: 3px;
		padding: 1px 6px;
		border-radius: 8px;
		font-size: 0.75em;
		font-weight: 500;
		color: var(--ref-color);
		background: color-mix(in srgb, var(--ref-color) 10%, white);
		border: 1px solid color-mix(in srgb, var(--ref-color) 25%, transparent);
		white-space: nowrap;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
	}
	.rendered-content :global(.entity-ref-label) {
		text-transform: capitalize;
	}
	.rendered-content :global(.entity-ref-btn) {
		cursor: pointer;
		transition: background 0.15s, border-color 0.15s;
	}
	.rendered-content :global(.entity-ref-btn:hover) {
		background: color-mix(in srgb, var(--ref-color) 20%, white);
		border-color: color-mix(in srgb, var(--ref-color) 45%, transparent);
	}
	.rendered-content :global(.entity-ref-btn.selected) {
		background: color-mix(in srgb, var(--ref-color) 22%, white);
		border-color: var(--ref-color);
		box-shadow: 0 0 0 1px var(--ref-color);
	}
</style>

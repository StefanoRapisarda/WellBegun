<script lang="ts">
	import type { Tag } from '$lib/types';

	let { tag, removable = false, onRemove }: {
		tag: Tag;
		removable?: boolean;
		onRemove?: () => void;
	} = $props();

	const categoryColors: Record<string, string> = {
		project: '#3b82f6',
		log: '#8b5cf6',
		activity: '#a855f7',
		note: '#10b981',
		source: '#f59e0b',
		actor: '#ef4444',
		wild: '#6b7280'
	};

	// Special formatting for certain tag names
	const specialNames: Record<string, string> = {
		'todo': 'ToDo',
		'done': 'Done',
		'ideas': 'Ideas',
		'quote': 'Quote',
		'milestone': 'Milestone',
		'dreaming of': 'DreamingOf',
		'dreamingof': 'DreamingOf'
	};

	function formatTagName(name: string): string {
		const lower = name.toLowerCase();
		if (specialNames[lower]) {
			return specialNames[lower];
		}
		// Default: capitalize first letter
		return name.charAt(0).toUpperCase() + name.slice(1);
	}

	let color = $derived(categoryColors[tag.category] ?? '#6b7280');
	let displayName = $derived(formatTagName(tag.name));
</script>

<span class="tag-badge" style="--badge-color: {color}">
	{displayName}
	{#if removable && onRemove}
		<button class="remove-btn" onclick={(e: MouseEvent) => { e.stopPropagation(); onRemove!(); }}>&times;</button>
	{/if}
</span>

<style>
	.tag-badge {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 2px 8px;
		border-radius: 12px;
		font-size: 0.75rem;
		background: color-mix(in srgb, var(--badge-color) 15%, transparent);
		color: var(--badge-color);
		border: 1px solid color-mix(in srgb, var(--badge-color) 30%, transparent);
	}
	.remove-btn {
		background: none;
		border: none;
		color: inherit;
		cursor: pointer;
		padding: 0;
		font-size: 0.875rem;
		line-height: 1;
	}
</style>

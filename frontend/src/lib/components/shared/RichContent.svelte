<script lang="ts">
	import { tags } from '$lib/stores/tags';

	let { text }: { text: string } = $props();

	const categoryColors: Record<string, string> = {
		project: '#3b82f6',
		log: '#8b5cf6',
		activity: '#a855f7',
		note: '#10b981',
		source: '#f59e0b',
		actor: '#ef4444',
		wild: '#6b7280'
	};

	let segments = $derived.by(() => {
		const tagMap = new Map($tags.map((t) => [t.name.toLowerCase(), t]));
		const parts: { type: 'text' | 'tag'; value: string; color?: string }[] = [];
		const regex = /#([\w-]+)/g;
		let lastIndex = 0;
		let match;

		while ((match = regex.exec(text)) !== null) {
			if (match.index > lastIndex) {
				parts.push({ type: 'text', value: text.slice(lastIndex, match.index) });
			}
			const tagName = match[1];
			const tag = tagMap.get(tagName.toLowerCase());
			if (tag) {
				parts.push({ type: 'tag', value: tag.name, color: categoryColors[tag.category] ?? '#6b7280' });
			} else {
				parts.push({ type: 'text', value: match[0] });
			}
			lastIndex = regex.lastIndex;
		}

		if (lastIndex < text.length) {
			parts.push({ type: 'text', value: text.slice(lastIndex) });
		}

		return parts;
	});
</script>

<span class="rich-content">{#each segments as seg}{#if seg.type === 'tag'}<span class="inline-tag" style="--badge-color: {seg.color}">{seg.value}</span>{:else}{seg.value}{/if}{/each}</span>

<style>
	.rich-content { white-space: pre-wrap; }
	.inline-tag {
		display: inline-flex;
		align-items: center;
		padding: 1px 6px;
		border-radius: 10px;
		font-size: 0.75rem;
		background: color-mix(in srgb, var(--badge-color) 15%, transparent);
		color: var(--badge-color);
		border: 1px solid color-mix(in srgb, var(--badge-color) 30%, transparent);
		vertical-align: baseline;
	}
</style>

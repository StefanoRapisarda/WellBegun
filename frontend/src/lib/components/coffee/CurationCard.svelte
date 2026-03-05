<script lang="ts">
	import { ENTITY_CONFIG, type NotepadEntityType } from '$lib/notepad/types';
	import type { CurationSuggestion } from '$lib/api/coffee';
	import EntityIcon from '$lib/components/shared/EntityIcon.svelte';

	let {
		suggestion,
		onAction
	}: {
		suggestion: CurationSuggestion;
		onAction: (suggestion: CurationSuggestion) => void;
	} = $props();

	let entityColor = $derived(
		ENTITY_CONFIG[suggestion.entity_type as NotepadEntityType]?.color ?? '#6b7280'
	);

	let typeLabel = $derived(
		suggestion.entity_type.replace('_', ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())
	);

	let icon = $derived.by(() => {
		switch (suggestion.type) {
			case 'missing_tags': return 'tag';
			case 'short_content': return 'edit';
			case 'stale': return 'clock';
			default: return 'info';
		}
	});
</script>

<div class="curation-card" style:--entity-color={entityColor}>
	<div class="card-icons">
		<EntityIcon type={suggestion.entity_type} size={14} />
		<div class="suggestion-icon">
			{#if icon === 'tag'}
				<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
					<path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/>
				</svg>
			{:else if icon === 'edit'}
				<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
					<path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
				</svg>
			{:else if icon === 'clock'}
				<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
					<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
				</svg>
			{:else}
				<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
					<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
				</svg>
			{/if}
		</div>
	</div>
	<div class="card-body">
		<span class="card-type-label" style:color={entityColor}>{typeLabel}</span>
		<span class="card-message">{suggestion.message}</span>
	</div>
	<button class="card-action" onclick={() => onAction(suggestion)}>
		{suggestion.action}
	</button>
</div>

<style>
	.curation-card {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 8px 12px;
		border-radius: 8px;
		background: white;
		border: 1px solid #e5e7eb;
		border-left: 3px solid var(--entity-color);
	}
	.card-icons {
		flex-shrink: 0;
		display: flex;
		align-items: center;
		gap: 2px;
		position: relative;
	}
	.suggestion-icon {
		color: #9ca3af;
		display: flex;
		align-items: center;
	}
	.card-body {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 1px;
	}
	.card-type-label {
		font-size: 0.6rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.3px;
		opacity: 0.8;
	}
	.card-message {
		font-size: 0.75rem;
		color: #4b5563;
		line-height: 1.3;
	}
	.card-action {
		flex-shrink: 0;
		padding: 4px 10px;
		border: 1px solid var(--entity-color);
		border-radius: 4px;
		background: transparent;
		color: var(--entity-color);
		font-size: 0.7rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s;
		white-space: nowrap;
	}
	.card-action:hover {
		background: var(--entity-color);
		color: white;
	}
</style>

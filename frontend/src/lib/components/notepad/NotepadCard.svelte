<script lang="ts">
	import { ENTITY_CONFIG, type ParsedEntity } from '$lib/notepad/types';

	let { entity, onclick }: { entity: ParsedEntity; onclick?: () => void } = $props();

	let config = $derived(ENTITY_CONFIG[entity.type]);
	let color = $derived(config.color);
	let primaryValue = $derived(entity.fields[config.primaryField] ?? config.defaultTitle);
	let defaultTextValue = $derived(entity.fields[config.defaultTextField] ?? '');
	let typeLabel = $derived(entity.type.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase()));

	let truncatedText = $derived(
		defaultTextValue.length > 80 ? defaultTextValue.slice(0, 78) + '...' : defaultTextValue
	);

	let explicitFieldCount = $derived(
		config.explicitFields.filter((f) => entity.fields[f]).length
	);
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<div class="notepad-card" style:--card-color={color} onclick={onclick}>
	<div class="card-header">
		<span class="type-dot" style:background={color}></span>
		<span class="type-label">{typeLabel}</span>
		{#if explicitFieldCount > 0}
			<span class="field-count">{explicitFieldCount} field{explicitFieldCount > 1 ? 's' : ''}</span>
		{/if}
	</div>
	<div class="card-title">{primaryValue}</div>
	{#if truncatedText}
		<div class="card-preview">{truncatedText}</div>
	{/if}
</div>

<style>
	.notepad-card {
		width: 180px;
		border-radius: 6px;
		border-left: 4px solid var(--card-color);
		background: white;
		box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
		padding: 8px 10px;
		display: flex;
		flex-direction: column;
		gap: 4px;
		transition: box-shadow 0.15s;
		cursor: pointer;
	}
	.notepad-card:hover {
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
	}
	.card-header {
		display: flex;
		align-items: center;
		gap: 5px;
	}
	.type-dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.type-label {
		font-size: 0.6rem;
		color: #9ca3af;
		text-transform: uppercase;
		letter-spacing: 0.3px;
		font-weight: 600;
	}
	.field-count {
		margin-left: auto;
		font-size: 0.55rem;
		color: #b0b8c4;
		background: #f3f4f6;
		padding: 1px 5px;
		border-radius: 8px;
	}
	.card-title {
		font-size: 0.78rem;
		color: #1f2937;
		font-weight: 500;
		line-height: 1.3;
	}
	.card-preview {
		font-size: 0.68rem;
		color: #6b7280;
		line-height: 1.35;
		margin-top: 2px;
	}
</style>

<script lang="ts">
	import { ENTITY_CONFIG, PLAN_SUB_SECTIONS, type ParsedEntity, type NotepadEntityType } from '$lib/notepad/types';

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

	// Status badge for virtual activity cards
	let statusLabel = $derived(entity.type === 'activity' && entity.fields.status ? entity.fields.status : null);

	// Items: unique headers in order — all entity types
	let hasItems = $derived(entity.items != null && entity.items.length > 0);
	let itemCount = $derived(entity.items?.length ?? 0);

	// Per-sub-section breakdown for plans
	interface SectionSummary { section: string; entityType: NotepadEntityType; count: number; doneCount: number; color: string }
	let sectionSummaries = $derived.by((): SectionSummary[] => {
		if (entity.type !== 'plan' || !entity.items || entity.items.length === 0) return [];
		const counts = new Map<string | undefined, { total: number; done: number }>();
		for (const item of entity.items) {
			const key = item.subSection;
			const cur = counts.get(key) ?? { total: 0, done: 0 };
			cur.total++;
			if (item.is_done) cur.done++;
			counts.set(key, cur);
		}
		const result: SectionSummary[] = [];
		for (const [section, { total, done }] of counts) {
			const label = section ?? 'activity';
			const entityType = section ? (PLAN_SUB_SECTIONS[section] ?? 'activity') : 'activity';
			result.push({ section: label, entityType, count: total, doneCount: done, color: ENTITY_CONFIG[entityType].color });
		}
		return result;
	});

	function pluralize(s: string): string {
		if (s.endsWith('y') && !s.endsWith('ay') && !s.endsWith('ey') && !s.endsWith('oy')) {
			return s.slice(0, -1) + 'ies';
		}
		if (s.endsWith('s')) return s;
		return s + 's';
	}

	let itemLabel = $derived.by(() => {
		if (entity.type === 'collection') return itemCount === 1 ? 'item' : 'items';
		if (entity.type === 'plan') return itemCount === 1 ? 'item' : 'items';
		const name = entity.type.replace('_', ' ');
		return itemCount === 1 ? name : name + 's';
	});
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<div class="notepad-card" style:--card-color={color} onclick={onclick}>
	<div class="card-header">
		<span class="type-dot" style:background={color}></span>
		<span class="type-label">{typeLabel}</span>
		{#if statusLabel}
			<span class="status-badge" class:done={statusLabel === 'done'}>{statusLabel}</span>
		{:else if explicitFieldCount > 0}
			<span class="field-count">{explicitFieldCount} field{explicitFieldCount > 1 ? 's' : ''}</span>
		{/if}
	</div>
	<div class="card-title">{primaryValue}</div>
	{#if truncatedText}
		<div class="card-preview">{truncatedText}</div>
	{/if}
	{#if hasItems && itemCount > 0}
		<div class="card-plan-items">
			{#if sectionSummaries.length > 0}
				{#each sectionSummaries as s}
					<div class="section-indicator">
						<span class="section-dot" style:background={s.color}></span>
						<span class="section-label">
							{s.count} {s.count > 1 ? pluralize(s.section) : s.section}
							{#if s.entityType === 'activity'}
								<span class="status-count">({s.doneCount}/{s.count})</span>
							{/if}
						</span>
					</div>
				{/each}
			{:else}
				<div class="plan-item-count">{itemCount} {itemLabel}</div>
			{/if}
		</div>
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
	.status-badge {
		margin-left: auto;
		font-size: 0.55rem;
		color: #d97706;
		background: #fef3c7;
		padding: 1px 5px;
		border-radius: 8px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.3px;
	}
	.status-badge.done {
		color: #059669;
		background: #d1fae5;
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
	.card-plan-items {
		margin-top: 3px;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.section-indicator {
		display: flex;
		align-items: center;
		gap: 4px;
	}
	.section-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.section-label {
		font-size: 0.6rem;
		color: #6b7280;
	}
	.status-count {
		color: #9ca3af;
		font-weight: 500;
	}
	.plan-item-count {
		font-size: 0.58rem;
		color: #9ca3af;
	}
</style>

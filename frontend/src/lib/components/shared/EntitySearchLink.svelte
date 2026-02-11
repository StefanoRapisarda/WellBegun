<script lang="ts">
	import { onMount } from 'svelte';
	import { searchEntities, type SearchResult } from '$lib/api/search';
	import { getTagLinks, attachTag, detachTag, type TagLink } from '$lib/api/tags';
	import { tags } from '$lib/stores/tags';
	import { entityTagsVersion, triggerEntityTagsRefresh } from '$lib/stores/tags';

	const ENTITY_COLORS: Record<string, string> = {
		project: '#5c7a99',
		log: '#8b7355',
		note: '#6b8e6b',
		activity: '#b5838d',
		source: '#c9a227',
		actor: '#8b4557',
		reading_list: '#5f9ea0',
		learning_track: '#7b6b8d'
	};

	let { entityType, entityId }: { entityType: string; entityId: number } = $props();

	let query = $state('');
	let results = $state<SearchResult[]>([]);
	let showDropdown = $state(false);
	let links = $state<TagLink[]>([]);
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;

	async function loadLinks() {
		try {
			links = await getTagLinks(entityType, entityId);
		} catch {
			links = [];
		}
	}

	async function handleInput() {
		if (debounceTimer) clearTimeout(debounceTimer);
		if (!query.trim()) {
			results = [];
			showDropdown = false;
			return;
		}
		debounceTimer = setTimeout(async () => {
			try {
				results = await searchEntities({ q: query.trim(), limit: 10 });
				// Filter out self
				results = results.filter(
					r => !(r.type === entityType && r.id === entityId)
				);
				showDropdown = results.length > 0;
			} catch {
				results = [];
				showDropdown = false;
			}
		}, 200);
	}

	async function handleSelect(result: SearchResult) {
		const tag = $tags.find(
			t => t.entity_type === entityType && t.entity_id === entityId
		);
		if (tag) {
			await attachTag(tag.id, result.type, result.id);
		}
		query = '';
		results = [];
		showDropdown = false;
		triggerEntityTagsRefresh();
		await loadLinks();
	}

	async function handleRemove(link: TagLink) {
		if (link.direction === 'tags') {
			await detachTag(link.tag_id, link.entity_type, link.entity_id);
		} else {
			await detachTag(link.tag_id, entityType, entityId);
		}
		triggerEntityTagsRefresh();
		await loadLinks();
	}

	function formatType(t: string): string {
		return t.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
	}

	function handleBlur() {
		// Delay to allow click on dropdown
		setTimeout(() => { showDropdown = false; }, 150);
	}

	$effect(() => {
		$entityTagsVersion;
		loadLinks();
	});

	onMount(() => {
		loadLinks();
	});
</script>

<div class="entity-search-link">
	<label class="link-label">Link to...</label>
	<div class="search-wrapper">
		<input
			type="text"
			placeholder="Search entities to link..."
			bind:value={query}
			oninput={handleInput}
			onblur={handleBlur}
			onfocus={() => { if (results.length > 0) showDropdown = true; }}
		/>
		{#if showDropdown}
			{@const types = [...new Set(results.map(r => r.type))]}
			<div class="dropdown">
				{#each types as type}
					<div class="dropdown-group">
						<div class="dropdown-group-label" style="color: {ENTITY_COLORS[type] ?? '#6b7280'}">
							{formatType(type)}
						</div>
						{#each results.filter(r => r.type === type) as item}
							<button
								class="dropdown-item"
								onmousedown={(e) => { e.preventDefault(); handleSelect(item); }}
							>
								<span class="dot" style="background: {ENTITY_COLORS[item.type] ?? '#6b7280'}"></span>
								{item.title}
							</button>
						{/each}
					</div>
				{/each}
			</div>
		{/if}
	</div>

	{#if links.length > 0}
		<div class="linked-chips">
			{#each links as link}
				<span class="chip" style="border-color: {ENTITY_COLORS[link.entity_type] ?? '#d1d5db'}">
					<span class="chip-dot" style="background: {ENTITY_COLORS[link.entity_type] ?? '#6b7280'}"></span>
					<span class="chip-dir">{link.direction === 'tags' ? '\u2192' : '\u2190'}</span>
					<span class="chip-label">{link.tag_name}</span>
					<button class="chip-remove" onclick={() => handleRemove(link)} title="Remove link">&times;</button>
				</span>
			{/each}
		</div>
	{/if}
</div>

<style>
	.entity-search-link {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.link-label {
		font-size: 0.875rem;
		font-weight: 500;
		color: #374151;
	}
	.search-wrapper {
		position: relative;
	}
	.search-wrapper input {
		width: 100%;
		padding: 8px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 0.875rem;
		box-sizing: border-box;
	}
	.dropdown {
		position: absolute;
		top: 100%;
		left: 0;
		right: 0;
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 6px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
		z-index: 50;
		max-height: 240px;
		overflow-y: auto;
		margin-top: 2px;
	}
	.dropdown-group-label {
		font-size: 0.65rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		padding: 6px 10px 2px;
	}
	.dropdown-item {
		display: flex;
		align-items: center;
		gap: 6px;
		width: 100%;
		padding: 6px 10px;
		border: none;
		background: none;
		cursor: pointer;
		font-size: 0.8rem;
		color: #374151;
		text-align: left;
	}
	.dropdown-item:hover {
		background: #f3f4f6;
	}
	.dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.linked-chips {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
	}
	.chip {
		display: inline-flex;
		align-items: center;
		gap: 3px;
		padding: 2px 6px;
		border: 1px solid;
		border-radius: 12px;
		font-size: 0.7rem;
		color: #4b5563;
		background: #f9fafb;
	}
	.chip-dot {
		width: 5px;
		height: 5px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.chip-dir {
		font-size: 0.6rem;
		color: #9ca3af;
	}
	.chip-label {
		max-width: 120px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.chip-remove {
		background: none;
		border: none;
		cursor: pointer;
		color: #9ca3af;
		font-size: 0.8rem;
		padding: 0 2px;
		line-height: 1;
	}
	.chip-remove:hover {
		color: #ef4444;
	}
</style>

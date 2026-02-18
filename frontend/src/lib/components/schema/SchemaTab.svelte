<script lang="ts">
	import SchemaTagsView from './SchemaTagsView.svelte';
	import SchemaConnectionsView from './SchemaConnectionsView.svelte';

	let activeSubTab: 'tags' | 'connections' = $state('tags');
</script>

<div class="schema-tab">
	<div class="sub-tab-bar">
		<button
			class="pill"
			class:active={activeSubTab === 'tags'}
			onclick={() => (activeSubTab = 'tags')}
		>Tags</button>
		<button
			class="pill"
			class:active={activeSubTab === 'connections'}
			onclick={() => (activeSubTab = 'connections')}
		>Connections</button>
	</div>

	<div class="sub-tab-content">
		{#if activeSubTab === 'tags'}
			<SchemaTagsView />
		{:else}
			<SchemaConnectionsView />
		{/if}
	</div>
</div>

<style>
	.schema-tab {
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
	}
	.sub-tab-bar {
		display: flex;
		gap: 4px;
		padding: 16px 24px 12px;
		border-bottom: 1px solid #e5e7eb;
		background: #fafafa;
		flex-shrink: 0;
	}
	.pill {
		padding: 6px 18px;
		border: 1px solid #d1d5db;
		border-radius: 20px;
		background: white;
		cursor: pointer;
		font-size: 0.82rem;
		color: #6b7280;
		font-weight: 500;
		transition: all 0.15s;
	}
	.pill:hover {
		color: #374151;
		border-color: #9ca3af;
	}
	.pill.active {
		background: #1f2937;
		color: white;
		border-color: #1f2937;
	}
	.sub-tab-content {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		padding: 20px 24px;
	}
</style>

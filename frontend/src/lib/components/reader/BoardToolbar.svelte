<script lang="ts">
	const ENTITY_BUTTONS: { type: string; label: string; color: string }[] = [
		{ type: 'note', label: '+Note', color: '#6b8e6b' },
		{ type: 'activity', label: '+Activity', color: '#b5838d' },
		{ type: 'source', label: '+Source', color: '#c9a227' },
		{ type: 'project', label: '+Project', color: '#5c7a99' },
		{ type: 'log', label: '+Log', color: '#8b7355' },
		{ type: 'actor', label: '+Actor', color: '#8b4557' }
	];

	let {
		onAddEntity
	}: {
		onAddEntity: (entityType: string) => void;
	} = $props();
</script>

<div class="board-toolbar">
	<div class="entity-buttons">
		{#each ENTITY_BUTTONS as btn}
			<button
				class="entity-btn"
				style:--btn-color={btn.color}
				onclick={() => onAddEntity(btn.type)}
			>
				{btn.label}
			</button>
		{/each}
	</div>
</div>

<style>
	.board-toolbar {
		display: flex;
		align-items: center;
		padding: 8px 12px;
		background: #fafafa;
		border-bottom: 1px solid #e5e7eb;
	}
	.entity-buttons {
		display: flex;
		gap: 4px;
		flex-wrap: wrap;
	}
	.entity-btn {
		padding: 4px 10px;
		border: 1px solid var(--btn-color);
		border-radius: 6px;
		background: white;
		cursor: pointer;
		font-size: 0.72rem;
		color: var(--btn-color);
		font-weight: 500;
		transition: all 0.15s;
	}
	.entity-btn:hover {
		background: var(--btn-color);
		color: white;
	}
</style>

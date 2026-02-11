<script lang="ts">
	let { date }: { date: string } = $props();

	let formatted = $derived(() => {
		const d = new Date(date);
		return d.toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	});
</script>

<span class="timestamp">{formatted()}</span>

<style>
	.timestamp {
		font-size: 0.65rem;
		color: #9ca3af;
		display: block;
		margin-top: 6px;
		text-align: right;
	}
</style>

<script lang="ts">
	let { open = false, message = 'Are you sure?', onConfirm, onCancel }: {
		open: boolean;
		message?: string;
		onConfirm: () => void;
		onCancel: () => void;
	} = $props();
</script>

{#if open}
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<div class="dialog-overlay" onclick={onCancel} onkeydown={(e: KeyboardEvent) => e.key === 'Escape' && onCancel()} role="dialog" tabindex="-1">
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<div class="dialog-content" onclick={(e: MouseEvent) => e.stopPropagation()} role="document">
			<p>{message}</p>
			<div class="dialog-actions">
				<button class="btn btn-cancel" onclick={onCancel}>Cancel</button>
				<button class="btn btn-confirm" onclick={onConfirm}>Confirm</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.dialog-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.4);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1001;
	}
	.dialog-content {
		background: white;
		border-radius: 8px;
		padding: 24px;
		min-width: 300px;
		box-shadow: 0 8px 30px rgba(0, 0, 0, 0.2);
	}
	.dialog-content p {
		margin: 0 0 16px;
		font-size: 0.95rem;
	}
	.dialog-actions {
		display: flex;
		gap: 8px;
		justify-content: flex-end;
	}
	.btn {
		padding: 8px 16px;
		border-radius: 6px;
		border: 1px solid #d1d5db;
		cursor: pointer;
		font-size: 0.875rem;
	}
	.btn-cancel {
		background: white;
	}
	.btn-confirm {
		background: #ef4444;
		color: white;
		border-color: #ef4444;
	}
</style>

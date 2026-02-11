<script lang="ts">
	import type { Snippet } from 'svelte';

	let { open = false, title = '', onClose, children }: {
		open: boolean;
		title?: string;
		onClose: () => void;
		children: Snippet;
	} = $props();
</script>

{#if open}
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<div class="modal-overlay" onclick={onClose} onkeydown={(e: KeyboardEvent) => e.key === 'Escape' && onClose()} role="dialog" tabindex="-1">
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<div class="modal-content" onclick={(e: MouseEvent) => e.stopPropagation()} role="document">
			<header class="modal-header">
				<h3>{title}</h3>
				<button class="close-btn" onclick={onClose}>&times;</button>
			</header>
			<div class="modal-body">
				{@render children()}
			</div>
		</div>
	</div>
{/if}

<style>
	.modal-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.4);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}
	.modal-content {
		background: white;
		border-radius: 8px;
		min-width: 400px;
		max-width: 600px;
		max-height: 80vh;
		overflow-y: auto;
		box-shadow: 0 8px 30px rgba(0, 0, 0, 0.2);
	}
	.modal-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 16px;
		border-bottom: 1px solid #e5e7eb;
	}
	.modal-header h3 {
		margin: 0;
		font-size: 1.1rem;
	}
	.close-btn {
		background: none;
		border: none;
		font-size: 1.5rem;
		cursor: pointer;
		color: #6b7280;
	}
	.modal-body {
		padding: 16px;
	}
</style>
